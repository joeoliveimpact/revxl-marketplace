/*
 * R14a.2 — the allow-list (Joe 09.28.26, session 2). The guard stays silent (counted, under the
 * cap) only for a PLAIN command: plain literal curl calls in the plugin's template grammar plus
 * tidy output. Any other command carrying `socialcrawl.dev` gets the one NOT A PLAIN CURL ask,
 * naming the visible counted total, parked as pending attended and denied unattended (never
 * counted, never pending). Mentions (grep, echo, a note, a commit message, a docs URL) ask too,
 * and `dry_run=1` is counted at its full label price.
 *
 * Synchronous, every guard run in its own seeded session (balance 800 -> cap 200, spent 0).
 * Zero credits, zero network.
 */
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { session, V1, TSCRIPT, GUARD, COSTS, quoted, assert, assertDecision, assertMatch, assertNoMatch } from "../lib.mjs";

const UNATTENDED = { env: { CLAUDE_CODE_SESSION_ATTENDED: "0" } };
const NOLOCAL = { unsetEnv: ["GROQ_API_KEY"], env: { PATH: "" } };
const NP = /NOT A PLAIN CURL/;
const DOCS = "https://docs." + "social" + "crawl" + ".dev";
const P = `${V1}prism/leads?query=x`;                                  // flat 50
const LQ = `${V1}linkedin/search/posts?keyword=x&dry_run=1`;          // declares dryRun; 56 in full
const KEY = `-H "x-api-key: $SOCIALCRAWL_API_KEY"`;
const sha = (c) => createHash("sha256").update(c).digest("hex");
const pendingOf = (st) => Object.values((st && st.pending) || {}).reduce((a, v) => a + v, 0);
// 0.3.1 (a): a command through any tool but Bash (PowerShell first) is never plain.
const PS = { extra: { tool_name: "PowerShell" } };
const USE_BASH = /use the Bash tool/;
const END = "Nothing was counted. If it is needed, run it in an attended session, where it can be confirmed.";
const ATT = /run it only on a yes|run this only on an explicit yes|every paid call asks|Confirm with the user|Work out what it will cost|Show the user|Re-run it with the full literal URL/i;
const API = "https://api." + "social" + "crawl" + ".dev/v1/";
const MIXED = "https://www." + "Social" + "Crawl" + ".DEV/v1/";
/** A2 (i)-(vii): [label, command, visible worst]. (i) is a valid Bash plain curl. */
const PS_CASES = [
  ["(i) a valid Bash plain curl, -o out.json", `curl -s "${V1}instagram/profile?handle=x" -o out.json`, 1],
  ["(ii) $env: key header, api. host", `curl -s -H "x-api-key: $env:SOCIALCRAWL_API_KEY" "${API}prism/leads?q=a" -o out.json`, 50],
  ["(iii) curl.exe", `curl.exe -s "${P}" -o out.json`, 50],
  ["(iv) Invoke-RestMethod", `Invoke-RestMethod -Uri "${P}" -Headers @{"x-api-key"=$env:SOCIALCRAWL_API_KEY}`, 50],
  ["(v) iwr", `iwr "${P}" -Headers @{"x-api-key"=$env:SOCIALCRAWL_API_KEY} -OutFile out.json`, 50],
  ["(v) Invoke-WebRequest", `Invoke-WebRequest -Uri "${P}" -OutFile out.json`, 50],
  ["(vi) a free endpoint, plain curl", `curl -s "${V1}credits/balance"`, 0],
  ["(vii) a mixed-case host", `curl -s "${MIXED}prism/leads?query=x" -o out.json`, 50],
];

/** One guard run in a fresh session (spent `spent`); returns the result and the state after. */
function once(command, opts = {}, spent = 0) {
  const s = session(opts);
  s.seed({ spent });
  const r = s.run(command, opts);
  const st = s.state();
  s.cleanup();
  return { r, st };
}

/**
 * The not-plain contract for one shape: attended it asks with the marker, names the visible total
 * and parks it under sha256(command) with nothing committed; unattended it is denied and nothing
 * is counted or pending. Returns the two printed rows.
 */
function notPlain(label, cmd, want, opts = {}) {
  const a = once(cmd, opts);
  assertDecision(a.r, "ask", `${label}: attended, not plain, asks`);
  assertMatch(a.r, NP, `${label}: the not-plain ask`);
  assertMatch(a.r, new RegExp(`Visible counted total: ~${want} credits`), `${label}: names the visible total`);
  assert(!a.st.spent && (want ? a.st.pending[sha(cmd)] === want : pendingOf(a.st) === 0),
    `${label}: pending ${want}, nothing committed, read ${JSON.stringify(a.st)}`, a.r);
  const u = once(cmd, { ...opts, env: { ...(opts.env || {}), ...UNATTENDED.env } });
  assertDecision(u.r, "deny", `${label}: unattended, not plain, is denied`);
  assert(!u.st.spent && pendingOf(u.st) === 0, `${label}: a deny is never counted and never pending, read ${JSON.stringify(u.st)}`, u.r);
  const fmt = (m, x) => `${m} ${String(x.r.decision).padEnd(5)} spent=${x.st.spent || 0} pending=${pendingOf(x.st)}`;
  return `    ${label.padEnd(52)} ${fmt("att", a)} | ${fmt("unatt", u)}`;
}

/** The plain contract: silent attended and unattended, `want` committed at once, nothing pending. */
function plain(label, cmd, want) {
  const rows = [];
  for (const [mode, opts] of [["att", {}], ["unatt", UNATTENDED]]) {
    const { r, st } = once(cmd, opts);
    assert(r.exit === 0 && r.raw === "", `${label} (${mode}): a plain curl under the cap emits nothing`, r);
    assert((st.spent || 0) === want && pendingOf(st) === 0, `${label} (${mode}): committed ${want}, read ${JSON.stringify(st)}`, r);
    rows.push(`${mode} null  spent=${st.spent || 0}`);
  }
  return `    ${label.padEnd(52)} ${rows.join(" | ")}`;
}

/**
 * (a) 0.3.1: one SocialCrawl command through a tool that is not Bash. Attended it asks, names and parks
 * `want` under sha256(command) with nothing committed; unattended it is denied with nothing counted or
 * pending, its reason ending with the unattended line and carrying no attended instruction. Both
 * reasons say to use the Bash tool. Returns the printed row.
 */
function notBash(label, cmd, want, extra = PS.extra) {
  const a = once(cmd, { extra });
  assertDecision(a.r, "ask", `${label}: attended, a SocialCrawl command that is not Bash asks`);
  assertMatch(a.r, USE_BASH, `${label}: the ask says to use the Bash tool`);
  assertMatch(a.r, new RegExp(`Visible counted total: ~${want} credits`), `${label}: names the visible total`);
  assert(!a.st.spent && (want ? a.st.pending[sha(cmd)] === want : pendingOf(a.st) === 0),
    `${label}: pending ${want}, nothing committed, read ${JSON.stringify(a.st)}`, a.r);
  const u = once(cmd, { extra, env: UNATTENDED.env });
  assertDecision(u.r, "deny", `${label}: unattended, it is denied`);
  assertMatch(u.r, USE_BASH, `${label}: the deny says to use the Bash tool`);
  assert(u.r.message.endsWith(END) && !ATT.test(u.r.message),
    `${label}: the deny ends with the unattended line and carries no attended instruction, read …${u.r.message.slice(-160)}`, u.r);
  assert(!u.st.spent && pendingOf(u.st) === 0, `${label}: a deny is never counted and never pending, read ${JSON.stringify(u.st)}`, u.r);
  return `    ${label.padEnd(52)} att ${String(a.r.decision).padEnd(5)} pending=${pendingOf(a.st)} | unatt ${u.r.decision} spent=${u.st.spent || 0}`;
}

/** A mutant copy of the guard: `anchor` must be present exactly once and is replaced. */
function mutant(dir, name, anchor, replacement) {
  const src = readFileSync(GUARD, "utf8");
  assert(src.split(anchor).length === 2, `mutation anchor for ${name} not found exactly once in credit-guard.mjs`);
  const file = join(mkdtempSync(join(dir, name + "-")), "credit-guard.mjs");
  writeFileSync(file, src.replace(anchor, replacement));
  copyFileSync(COSTS, join(dirname(file), "costs.json"));
  return file;
}

// The plugin's own call templates (R14a.2 probe Q1): every `curl` line in a code block, joined
// with its backslash-continued lines, and every inline `curl …` code span.
function templates() {
  const PLUGIN = resolve(dirname(GUARD), "..");
  const CURATED = resolve(PLUGIN, "..", "..", "tools", "socialcrawl", "curated");
  const sources = [
    ["skills/socialcrawl/references", join(PLUGIN, "skills", "socialcrawl", "references")],
    ["skills/socialcrawl/SKILL.md", join(PLUGIN, "skills", "socialcrawl", "SKILL.md")],
    ["skills/onboarding (SKILL.md + references)", join(PLUGIN, "skills", "onboarding")],
    ["tools/socialcrawl/curated", CURATED],
  ];
  const mdFiles = (p) => (statSync(p).isDirectory()
    ? readdirSync(p).flatMap((n) => mdFiles(join(p, n)))
    : p.endsWith(".md") ? [p] : []);
  const out = [];
  for (const [name, root] of sources) {
    if (!existsSync(root)) { out.push({ name, absent: true, cmds: [] }); continue; }
    const cmds = [];
    for (const f of mdFiles(root)) {
      const lines = readFileSync(f, "utf8").split("\n");
      for (let i = 0; i < lines.length; i++) {
        if (/^\s*curl /.test(lines[i])) {
          let cmd = lines[i].trimStart();
          while (/\\$/.test(lines[i]) && i + 1 < lines.length) cmd += "\n" + lines[++i];
          cmds.push({ where: `${f.slice(PLUGIN.length - 30)}:${i + 1}`, cmd });
          continue;
        }
        for (const m of lines[i].matchAll(/`(curl [^`]+)`/g)) cmds.push({ where: `${f.slice(PLUGIN.length - 30)}:${i + 1}`, cmd: m[1] });
      }
    }
    // Placeholders substituted: <handle>, <key> and {platform}-style path params.
    for (const c of cmds) c.cmd = c.cmd.replace(/<[^<>\s]*>/g, "x").replace(/\{[A-Za-z_][A-Za-z0-9_]*\}/g, "x");
    out.push({ name, cmds });
  }
  return out;
}

export default [
  {
    id: "N1-x8-x11-shapes",
    desc: "R14a.1's red shapes X8-X11 (brace-list fan-outs, a loop hidden by an apostrophe or piped into bash, Python shelling out after &&, curl config and target options): each takes the not-plain ask attended at its visible total, and is denied unattended",
    fn() {
      const LOOP = `for i in 1 2 3; do curl -s "${P}"; done`;
      const NOTE = `cat > notes.md <<'EOF'\nJoe's plan\nEOF\n`;
      const rows = [
        notPlain("X8a brace list after the closing quote", `curl -s "${V1}prism/leads?query="{a,b,c}`, 50),
        notPlain("X8a brace list after a single quote", `curl -s '${V1}prism/leads?query='{a,b,c}`, 50),
        notPlain("X8b unquoted brace list with -sg", `curl -sg ${V1}prism/leads?query={a,b,c}`, 50),
        notPlain("X8c for …; { curl …; }", `for i in 1 2 3; { curl -s "${P}"; }`, 50),
        notPlain("X8d | /usr/bin/xargs", `cat ids.txt | /usr/bin/xargs -I{} curl -s "${V1}prism/leads?query={}"`, 50),
        notPlain("X8e $(printf …) format reuse", `curl -s $(printf "${V1}prism/leads?query=%s " a b c)`, 50),
        notPlain("X9a apostrophe note, then a for-loop", NOTE + LOOP, 50),
        notPlain("X9a echo $'it\\'s'; for-loop", `echo $'it\\'s'; ${LOOP}`, 50),
        notPlain("X9a apostrophe note, then a python3 loop", NOTE + `python3 - <<'PY'\nimport urllib.request\nfor q in ["a", "b", "c"]:\n    urllib.request.urlopen("${V1}prism/leads?query=" + q)\nPY`, 50),
        notPlain("X9b echo '<loop>' | bash", `echo '${LOOP}' | bash`, 50),
        notPlain("X9b bash <<< '<loop>'", `bash <<< '${LOOP}'`, 50),
        notPlain("X9b source <(echo '<loop>')", `source <(echo '${LOOP}')`, 50),
        notPlain("X10 subprocess.run(bash -c 'cd . && curl')", `python3 - <<'PY'\nimport subprocess\nfor q in ["a", "b", "c"]:\n    subprocess.run(["bash", "-c", "cd . && curl -sS -o /dev/null '${V1}prism/leads?query=" + q + "'"])\nPY`, 50),
        notPlain("X10 os.system('mkdir -p out && curl')", `python3 - <<'PY'\nimport os\nfor q in "abc":\n    os.system("mkdir -p out && curl -s '${V1}prism/leads?query=" + q + "'")\nPY`, 50),
        notPlain("X10 os.system('cd . & curl')", `python3 - <<'PY'\nimport os\nfor q in "abc":\n    os.system('cd . & curl -s "${V1}prism/leads?query=' + q + '"')\nPY`, 50),
        notPlain("X11 -K c.cfg", `curl -s -K c.cfg "${LQ}"`, 56),
        notPlain("X11 printf … | curl -K -", `printf 'url-query = "dry_run=0"\\n' | curl -s -K - "${LQ}"`, 56),
        notPlain("X11 --config c.cfg", `curl -s --config c.cfg "${LQ}"`, 56),
        notPlain("X11 export CURL_HOME=…; curl", `export CURL_HOME=$PWD/ch; curl -s "${LQ}"`, 56),
        notPlain("X11 -G --expand-data dry_run=0", `curl -s -G --expand-data dry_run=0 "${LQ}"`, 56),
        notPlain("X11 --request-target behind a free URL", `curl -s --request-target "/v1/prism/leads?query=x" "${V1}credits/balance"`, 0),
        notPlain("X11 budget: -K - with budget=1 in the URL", `printf 'url-query = "budget=150"\\n' | curl -s -K - "${V1}prism/investigate?goal=x&budget=1"`, 200, NOLOCAL),
        notPlain("X11 budget: -G --expand-data budget=150", `curl -s -G --expand-data budget=150 "${V1}prism/investigate?goal=x&budget=1"`, 200, NOLOCAL),
      ];
      console.log(`    ${"shape".padEnd(52)} decision / resulting state\n` + rows.join("\n"));
    },
  },
  {
    id: "N2-probe-q7-not-plain",
    desc: "Every not-plain shape in the R14a.2 probe's Q7 table takes the not-plain ask attended at its visible total, and is denied unattended",
    fn() {
      const rows = [
        notPlain("glob {a,b,c} inside the quoted URL", `curl -s "${V1}prism/leads?query={a,b,c}"`, 50),
        notPlain("glob [1-3] inside the quoted URL", `curl -s "${V1}prism/leads?query=x&page=[1-3]"`, 50),
        notPlain("the same with -g", `curl -g -s "${V1}prism/leads?query=x&page=[1-3]"`, 50),
        notPlain("the same with --globoff", `curl --globoff -s "${V1}prism/leads?query=x&page=[1-3]"`, 50),
        notPlain("the same with -sg", `curl -sg "${V1}prism/leads?query=x&page=[1-3]"`, 50),
        notPlain("bash brace range after the quote", `curl -s "${V1}prism/leads?query="{1..3}`, 50),
        notPlain("--next", `curl -s "${P}" --next "${V1}amazon/shop?q=a"`, 51),
        notPlain("-:", `curl -s "${P}" -: "${V1}amazon/shop?q=a"`, 51),
        notPlain("--variable … --expand-url behind credits/", `curl -s --variable p=../prism/leads --expand-url "${V1}credits/{{p}}"`, 0),
        notPlain("--url", `curl -s --url "${P}"`, 50),
        notPlain("--url-query", `curl -s --url-query query=y "${P}"`, 50),
        notPlain("-q", `curl -q -s "${P}"`, 50),
        notPlain("-G -d", `curl -s -G "${V1}prism/leads" -d query=x`, 50),
        notPlain("--data-urlencode", `curl -s -G "${V1}prism/leads" --data-urlencode "query=a b"`, 50),
        notPlain("-d @file", `curl -s -X POST "${V1}youtube/videos" -d @body.json`, 100),
        notPlain("--json", `curl -s --json '{"ids":["a"]}' "${V1}youtube/videos"`, 100),
        notPlain("alias curl=…; curl", `alias curl='curl -K c.cfg'; curl -s "${P}"`, 50),
        notPlain("curl(){…}; curl", `curl() { command curl -K c.cfg "$@"; }; curl -s "${P}"`, 50),
        notPlain("command curl", `command curl -s "${P}"`, 50),
        notPlain("sudo curl", `sudo curl -s "${P}"`, 50),
        notPlain("FOO=1 curl", `FOO=1 curl -s "${P}"`, 50),
        notPlain("time curl", `time curl -s "${P}"`, 50),
        notPlain("/usr/bin/curl", `/usr/bin/curl -s "${P}"`, 50),
        notPlain("curl.exe", `curl.exe -s "${P}"`, 50),
        notPlain("wget -qO-", `wget -qO- "${P}"`, 50),
        notPlain("backgrounded &", `curl -s "${P}" &`, 50),
        notPlain("subshell ( )", `(curl -s "${P}")`, 50),
        notPlain("R=$(curl …)", `R=$(curl -s "${P}")`, 50),
        notPlain("backticks", "R=`curl -s \"" + P + "\"`", 50),
        notPlain("two URLs in one curl", `curl -s "${P}" "${V1}amazon/shop?q=a"`, 51),
        notPlain("unquoted URL with &", `curl -s ${V1}prism/leads?query=x&page=2`, 50),
        notPlain("python3 -c loop, os.system('true && curl')", `python3 -c 'import os\nfor q in "abc": os.system("true && curl -s ${P}" + q)'`, 50),
        notPlain("bash -c 'curl …', a single call", `bash -c 'curl -s "${P}"'`, 50),
        notPlain("a loop around credits/*", `for i in 1 2 3; do curl -s "${V1}credits/balance"; done`, 0),
        notPlain("watch around credits/*", `watch -n1 curl -s "${V1}credits/balance"`, 0),
        // The plain definition's own edges.
        notPlain("a trailing comment", `curl -s "${P}" # note`, 50),
        notPlain("a comment carrying a URL is counted", `# see ${P}\ncurl -s "${V1}amazon/shop?q=a"`, 51),
        notPlain("a flag outside the set (-m 30)", `curl -s -m 30 "${P}"`, 50),
        notPlain("a header holding $(…) other than cat", `curl -s -H "x-api-key: $(security find-generic-password -w)" "${P}"`, 50),
        notPlain("a header holding a backtick", "curl -s -H \"x-api-key: `cat k`\" \"" + P + "\"", 50),
        notPlain("a header carrying a SocialCrawl URL", `curl -s -H "Referer: ${DOCS}" "${P}"`, 50),
        notPlain("a -d body carrying a SocialCrawl URL", `curl -s -X POST "${V1}youtube/videos" -d '{"u":"${V1}prism/leads"}'`, 150),
        notPlain("-d with an @", `curl -s -X POST "${V1}youtube/videos" -d '{"to":"a@b.c"}'`, 100),
        notPlain("-d double-quoted", `curl -s -X POST "${V1}youtube/videos" -d "{}"`, 100),
        notPlain("a % in the path", `curl -s "${V1}prism%2Fleads?query=x"`, 50),
        notPlain("a dot segment in the path", `curl -s "${V1}credits/../prism/leads?query=x"`, 50),
        notPlain("http://, not https://", `curl -s "http://www.${"social" + "crawl"}.dev/v1/prism/leads?query=x"`, 50),
        notPlain("a port on the host", `curl -s "https://www.${"social" + "crawl"}.dev:443/v1/prism/leads?query=x"`, 0),
        notPlain("||", `curl -s "${P}" || true`, 50),
        notPlain("| tee (another pipe)", `curl -s "${P}" | tee out.json`, 50),
        notPlain("| sh", `curl -s "${P}" | sh`, 50),
        notPlain("| jq with a $ argument", `curl -s "${P}" | jq ".data | $F"`, 50),
        notPlain("2> to a file", `curl -s "${P}" 2>err.txt`, 50),
        notPlain("< input redirect", `curl -s "${P}" < in.txt`, 50),
        notPlain("$'…' quoting", `curl -s $'${P}'`, 50),
        notPlain("an unbalanced quote", `curl -s "${P}`, 50),
      ];
      console.log(`    ${"shape".padEnd(52)} decision / resulting state\n` + rows.join("\n"));
    },
  },
  {
    id: "N3-mentions-ask",
    desc: "MENTIONS (Joe 09.28.26, supersedes R14b Design 3): grep, echo, a heredoc note, git commit -m and a docs.socialcrawl.dev URL each ask attended and are denied unattended; a URL-less mention names a 0 total and parks nothing",
    fn() {
      const rows = [
        notPlain("grep -rn '<URL>' notes/", `grep -rn "${P}" notes/`, 50),
        notPlain("echo '<URL>'", `echo '${P}'`, 50),
        notPlain("a heredoc note", `cat > notes.md <<'EOF'\nsee ${P}\nEOF`, 50),
        notPlain("git commit -m '<URL>'", `git commit -m "note: ${P}"`, 50),
        notPlain("curl a docs.socialcrawl.dev URL", `curl -s "${DOCS}/api/credits"`, 0),
        notPlain("echo a docs.socialcrawl.dev URL", `echo see ${DOCS}/quickstart`, 0),
      ];
      console.log(`    ${"shape".padEnd(52)} decision / resulting state\n` + rows.join("\n"));
    },
  },
  {
    id: "N4-plain-templates-and-tidy-output",
    desc: "PLAIN: the template shapes (probe Q1 A, B, C1-C8) and tidy output (| jq, | head, | python -m json.tool, > / >> file, 2>/dev/null, 2>&1, -o, -w, -sS --fail, --max-time), chains on && ; and newlines with sleep and full-line comments are counted and silent, attended and unattended",
    fn() {
      const rows = [
        plain("A: URL first, continued key header", `curl "${V1}instagram/profile?handle=x" \\\n  ${KEY}`, 1),
        plain("B: -X POST, headers, -d '<json>'", `curl -X POST "${V1}youtube/videos" \\\n  ${KEY} \\\n  -H "content-type: application/json" \\\n  -d '{"ids": ["a"]}'`, 100),
        plain("C1: -s, $(cat key) header, one line", `curl -s -H "x-api-key: $(cat ~/.config/socialcrawl/api_key)" "${P}"`, 50),
        plain("C2: URL first, $(cat key) header", `curl "${P}" -H "x-api-key: $(cat ~/.config/socialcrawl/api_key)"`, 50),
        plain("C3: -s, key header, continued URL", `curl -s ${KEY} \\\n  "${P}"`, 50),
        plain("C4: hand POST", `curl -s -X POST "${V1}youtube/videos" \\\n  ${KEY} \\\n  -H "content-type: application/json" \\\n  -d '{"ids":["a","b"]}'`, 100),
        plain("C5: Idempotency-Key header", `curl -s ${KEY} \\\n  -H "Idempotency-Key: run-42" \\\n  "${P}"`, 50),
        plain("C6: streaming -N, ${NAME} key", `curl -N -s -H "x-api-key: \${SOCIALCRAWL_API_KEY}" \\\n  -H "Accept: text/event-stream" \\\n  "${V1}search/news?query=x"`, 62),
        plain("C7: literal key", `curl -s -H "x-api-key: sc_your_api_key_here" \\\n  "${P}"`, 50),
        plain("C8: no key", `curl -s "${V1}amazon/shop?q=a"`, 1),
        plain("single-quoted URL", `curl -s '${P}'`, 50),
        plain("api. host (lint_curated's shape)", `curl -s -H "x-api-key: $KEY" "https://api.${"social" + "crawl"}.dev/v1/prism/leads?query=x"`, 50),
        plain("apex host", `curl -s "https://${"social" + "crawl"}.dev/v1/prism/leads?query=x"`, 50),
        plain("| jq '…'", `curl -s "${P}" | jq '.data[] | .name'`, 50),
        plain("| head -c 300", `curl -s "${P}" | head -c 300`, 50),
        plain("| python3 -m json.tool", `curl -s "${P}" | python3 -m json.tool`, 50),
        plain("| python -m json.tool", `curl -s "${P}" | python -m json.tool`, 50),
        plain("> out.json", `curl -s "${P}" > out.json`, 50),
        plain(">> out.json", `curl -s "${P}" >> out.json`, 50),
        plain("2>/dev/null", `curl -s "${P}" 2>/dev/null`, 50),
        plain("2>&1", `curl -s "${P}" 2>&1`, 50),
        plain("| jq -r … | head -5 > ids.txt 2>&1", `curl -s "${P}" | jq -r '.data[] | .id' | head -5 > ids.txt 2>&1`, 50),
        plain("-o out.json", `curl -s -o out.json "${P}"`, 50),
        plain("-w '%{http_code}'", `curl -s -w '%{http_code}' "${P}"`, 50),
        plain("-sS --fail --max-time 30", `curl -sS --fail --max-time 30 "${P}"`, 50),
        plain("-S -f -X GET", `curl -S -f -X GET "${P}"`, 50),
        plain("&& chain of two curls", `curl -s "${P}" && curl -s "${V1}amazon/shop?q=a"`, 51),
        plain("; sleep 2 ;", `curl -s "${V1}amazon/shop?q=a"; sleep 2; curl -s "${V1}amazon/shop?q=b"`, 2),
        plain("newlines and full-line comments", `# page 1\ncurl -s "${V1}amazon/shop?q=a"\n\n# page 2\ncurl -s "${V1}amazon/shop?q=b"\n`, 2),
      ];
      console.log(`    ${"shape".padEnd(52)} decision / resulting state\n` + rows.join("\n"));
    },
  },
  {
    id: "N5-free-calls-through-the-allow-list",
    desc: "FREE (R14a.2): a plain credits/* call is silent at 0 attended and unattended, with no state write (the unattended balance call in elicitation.md is plain); a non-plain free command asks, or is denied unattended",
    fn() {
      for (const cmd of [`curl -s "${V1}credits/balance"`, `curl -s ${KEY} "${V1}credits/balance"`, `curl -s "${V1}credits/transactions" | jq .`]) {
        for (const opts of [{}, UNATTENDED]) {
          const s = session().seed({ spent: 7 });
          const r = s.run(cmd, opts);
          assert(r.raw === "" && !r.stateWritten, `plain free ${JSON.stringify(cmd).slice(0, 80)}: silent, no write`, r);
          s.cleanup();
        }
      }
      console.log([
        notPlain("for-loop over credits/balance", `for i in 1 2 3; do curl -s "${V1}credits/balance"; done`, 0),
        notPlain("curl -K c.cfg credits/balance", `curl -s -K c.cfg "${V1}credits/balance"`, 0),
        notPlain("bash -c 'curl credits/balance'", `bash -c 'curl -s "${V1}credits/balance"'`, 0),
      ].join("\n"));
    },
  },
  {
    id: "N6-dry-run-counted-in-full",
    desc: "DRY RUN (R14a.2 ruling (b)): dry_run=1 on a declaring endpoint is counted at its full label price, silently in a plain curl and parked in full behind the not-plain ask; the ask then commits it once it runs",
    fn() {
      const C = JSON.parse(readFileSync(COSTS, "utf8"));
      assert(C["GET linkedin/search/posts"].dryRun === true, "the fixture endpoint still declares dryRun (the vendor fact stays in costs.json)");
      console.log([
        plain("declared dry_run=1, plain", `curl -s "${LQ}"`, 56),
        plain("declared dry_run=1, plain, key header", `curl -s ${KEY} "${LQ}"`, 56),
        notPlain("declared dry_run=1 in a loop", `for i in 1 2; do curl -s "${LQ}"; done`, 56),
      ].join("\n"));
      const s = session().seed({ spent: 0 });
      const cmd = `echo '${LQ}'`;
      assertDecision(s.run(cmd), "ask", "a mention of a dry run asks");
      s.post(cmd);
      assert(s.state().spent === 56 && pendingOf(s.state()) === 0, `the Post run commits the full 56, read ${s.stateRaw()}`);
      s.cleanup();
    },
  },
  {
    id: "N7-not-plain-commit-and-cap",
    desc: "NOT-PLAIN ASK: its pending total is committed by PostToolUse and PostToolUseFailure; declined, it is never counted; it names the cap step (committed total, cap, balance) only when its visible total crosses one, and the transcript price whenever a transcript URL is visible",
    fn() {
      const cmd = `echo '${P}'`;
      for (const failure of [false, true]) {
        const s = session().seed({ spent: 0 });
        assertDecision(s.run(cmd), "ask", "the mention asks");
        s.post(cmd, { failure });
        assert(s.state().spent === 50 && pendingOf(s.state()) === 0, `${failure ? "PostToolUseFailure" : "PostToolUse"} commits the visible 50, read ${s.stateRaw()}`);
        assert(!s.post(cmd, { failure }).stateWritten, "a second Post counts nothing");
        s.cleanup();
      }
      const declined = session().seed({ spent: 0 });
      declined.run(cmd);
      assertDecision(declined.run(`curl -s "${V1}amazon/shop?q=a"`), null, "declined: the next plain call is silent");
      assert(declined.state().spent === 1, `declined: the mention was never counted, read ${declined.stateRaw()}`);
      declined.cleanup();
      const under = once(cmd);
      assertNoMatch(under.r, /Session cap step|The cap is/, "under the cap: no cap step named");
      const cross = once(cmd, {}, 190);
      assertMatch(cross.r, /Session cap step: ~190 credits are committed this session/, "crossing: names the committed total");
      assertMatch(cross.r, /The cap is 200 credits \(the smaller of 500 and a quarter of your 800-credit balance\)/, "crossing: names the cap and the balance");
      const unknown = once(cmd, { balance: null });
      assertMatch(unknown.r, /couldn't read your balance/, "no balance: a paid visible total names the unread balance");
      const zero = once(`echo ${DOCS}`, { balance: null });
      assertNoMatch(zero.r, /couldn't read your balance/, "no balance: a 0 total names no cap step");
      const t = once(`for i in 1 2; do curl -s "${V1}youtube/video/${TSCRIPT}?id=$i"; done`, NOLOCAL);
      assertMatch(t.r, NP, "a transcript loop is not plain");
      assertMatch(t.r, /bills 3 credits PER video/, "the per-unit price rides in the not-plain ask");
      assertMatch(t.r, /Cheaper first/, "the cheaper route rides in the not-plain ask");
      for (const [label, r] of [["under", under.r], ["cross", cross.r], ["transcript", t.r]]) {
        assertNoMatch(r, /REPEAT DETECTED|PROGRAM CODE|assembled from shell variables/, `${label}: no retired phrase`);
      }
    },
  },
  {
    id: "N8-templates-machine-check",
    desc: "TEMPLATES: every curl template line in the plugin's socialcrawl and onboarding references and SKILL.md files and in tools/socialcrawl/curated, placeholders substituted, runs through the guard and none gets the not-plain ask",
    fn() {
      const lines = [];
      let total = 0;
      for (const src of templates()) {
        if (src.absent) { lines.push(`    ${src.name.padEnd(44)} ABSENT (not in this copy)`); continue; }
        const tally = { silent: 0, "cap-step ask": 0, "other ask": 0, "not plain": 0 };
        for (const { where, cmd } of src.cmds) {
          const { r } = once(cmd, NOLOCAL);
          assert(r.exit === 0, `${where}: exit ${r.exit}`, r);
          const k = NP.test(r.message) ? "not plain" : !r.decision ? "silent" : /session cap step/.test(r.message) ? "cap-step ask" : "other ask";
          tally[k]++;
          assert(k !== "not plain", `${where}: a plugin template got the not-plain ask: ${JSON.stringify(cmd)}`, r);
        }
        total += src.cmds.length;
        lines.push(`    ${src.name.padEnd(44)} ${String(src.cmds.length).padStart(4)} templates: ` +
          Object.entries(tally).map(([k, v]) => `${k} ${v}`).join(", "));
      }
      console.log(lines.join("\n") + `\n    total ${total} templates, 0 not plain`);
      assert(total >= 640, `expected the ~650 plugin templates, found ${total}`);
    },
  },
  {
    id: "N9-mutants",
    desc: "MUTANTS: each deleted piece of the allow-list lets a named shape through silently (or unattended); this build asks or denies on every one",
    fn() {
      const dir = mkdtempSync(join(tmpdir(), "sc-guard-np-mutants-"));
      const cases = [
        ["plain-always", "  try { plain = plainCommand(cmd); } catch {}", "  plain = true;",
          `curl -s "${V1}prism/leads?query="{a,b,c}`, {}],
        ["free-pass-first", "    plain &&\n    cmdWorst === 0 &&", "    cmdWorst === 0 &&",
          `for i in 1 2 3; do curl -s "${V1}credits/balance"; done`, {}],
        ["url-allows-globs", "/[\\s$`\\\\{}[\\]#\"']/.test(v)", "/[\\s$`\\\\#\"']/.test(v)",
          `curl -s "${V1}prism/leads?query={a,b,c}"`, {}],
        ["comments-ignored", "        toks.push({ comment: true, lineStart });\n", "",
          `curl -s "${P}" # for i in 1 2 3`, {}],
        ["no-occurrence-rule", "return inUrls > 0 && inUrls === (src.match(/socialcrawl\\.dev/gi) || []).length;", "return inUrls > 0;",
          `curl -s -H "Referer: ${DOCS}" "${P}"`, {}],
        ["header-any-subst", "\\(cat [A-Za-z0-9_.\\/~+,:@=-]+\\)", "\\([^)]*\\)",
          `curl -s -H "x-api-key: $(bash ./x.sh)" "${P}"`, {}],
        ["unattended-passes", "  if (!plain) {\n", "  if (!plain && !UNATTENDED) {\n",
          `echo '${P}'`, UNATTENDED],
      ];
      const rows = [];
      for (const [name, anchor, repl, cmd, opts] of cases) {
        const m = mutant(dir, name, anchor, repl);
        const mut = once(cmd, { ...opts, guard: m });
        const fix = once(cmd, opts);
        rows.push(`    ${name.padEnd(20)} mutant ${String(mut.r.decision).padEnd(5)} | fix ${fix.r.decision}`);
        assert(mut.r.decision === null, `mutant ${name}: the shape slips through silently (what this fixture catches), read ${mut.r.decision}`, mut.r);
        assert(fix.r.decision === (opts === UNATTENDED ? "deny" : "ask"), `fix: ${name}'s shape asks or denies, read ${fix.r.decision}`, fix.r);
      }
      // The dry-run reader restored: the declared dry run goes back to free.
      const dry = mutant(dir, "dry-run-reader",
        "    const flat = num(base) === null ? 0 : base;\n",
        "    { const e = COSTS && COSTS[`${VERB} ${p}`]; const dv = e && e.dryRun === true ? sentValues(found[i], \"dry_run\") : []; if (dv.length && dv.every((v) => v === \"1\")) return { p, kind: \"flat\", worst: 0 }; }\n    const flat = num(base) === null ? 0 : base;\n");
      const md = once(`curl -s "${LQ}"`, { guard: dry });
      const fd = once(`curl -s "${LQ}"`);
      rows.push(`    ${"dry-run-reader".padEnd(20)} mutant spent=${md.st.spent || 0} | fix spent=${fd.st.spent}`);
      assert(!md.st.spent && fd.st.spent === 56, `dry-run-reader: mutant 0, fix 56, read ${JSON.stringify(md.st)} / ${JSON.stringify(fd.st)}`);
      console.log(rows.join("\n"));
      rmSync(dir, { recursive: true, force: true });
    },
  },
  {
    id: "P2-A2-powershell-never-plain",
    desc: "POWERSHELL (0.3.1, A2-A4, A6, B1, B3): any tool_name but Bash is never plain. Each SocialCrawl command through PowerShell (a valid Bash plain curl, a $env: key header, curl.exe, Invoke-RestMethod, iwr, Invoke-WebRequest, a free credits/balance curl, a mixed-case host) asks attended with its visible total parked and is denied unattended with nothing counted, and every reason says to use the Bash tool; \"powershell\" and \"PowerShell7\" are not Bash either; a missing tool_name is Bash (silent and counted); a PowerShell command with no SocialCrawl URL returns nothing and touches no folder",
    fn() {
      const rows = [];
      const bad = [];
      const each = (f) => { try { rows.push(f()); } catch (e) { bad.push(String(e.message).split("\n")[0]); } };
      for (const [label, cmd, want] of PS_CASES) each(() => notBash(label, cmd, want));
      for (const name of ["powershell", "PowerShell7"]) each(() => notBash(`tool_name ${JSON.stringify(name)}, (i)`, PS_CASES[0][1], 1, { tool_name: name }));
      each(() => {                                        // B3: no tool_name is Bash, so (i) is plain
        const { r, st } = once(PS_CASES[0][1], { extra: { tool_name: undefined } });
        assert(r.exit === 0 && r.raw === "" && st.spent === 1 && pendingOf(st) === 0, `no tool_name: read as Bash, (i) silent and counted 1, read ${r.decision} / ${JSON.stringify(st)}`, r);
        return `    ${"no tool_name (Bash), (i)".padEnd(52)} att null  spent=${st.spent}`;
      });
      each(() => {                                        // B1: no SocialCrawl URL, the fast path
        const s = session();
        const home = join(s.dir, "not-made");
        const r = s.run(`Get-ChildItem -Path . | Select-Object -First 3`, { ...PS, env: { SC_REVXL_HOME: home } });
        s.cleanup();
        assert(r.exit === 0 && r.raw === "" && !r.stateWritten && !existsSync(home), `PowerShell, no SocialCrawl URL: nothing, read ${r.decision} / ${r.raw.slice(0, 80)}`, r);
        return `    ${"PowerShell, no SocialCrawl URL".padEnd(52)} att null  no folder made`;
      });
      console.log(rows.join("\n"));
      assert(!bad.length, `${bad.length} broken:\n      ${bad.join("\n      ")}`);
    },
  },
  {
    id: "P2-A5-powershell-post-counts",
    desc: "POWERSHELL (0.3.1, A5): an attended PowerShell ask parks its visible worst, and its PostToolUse or PostToolUseFailure run (tool_name PowerShell, the same command) commits exactly that, once; a not-plain command ends in the same state through either tool; a declined PowerShell ask is never counted",
    fn() {
      const cmd = PS_CASES[0][1];                         // (i): 1cr, plain only through Bash
      const IRM = PS_CASES[3][1];                         // (iv): 50cr, not plain through either tool
      const rows = [];
      for (const failure of [false, true]) {
        const ev = failure ? "PostToolUseFailure" : "PostToolUse";
        const s = session().seed({ spent: 0 });
        const a = s.run(cmd, PS);
        const parked = (s.state().pending || {})[sha(cmd)];
        s.post(cmd, { ...PS, failure });
        const after = s.state();
        const again = s.post(cmd, { ...PS, failure });
        s.cleanup();
        rows.push(`    ${`(i), ${ev}`.padEnd(40)} ${a.decision} parked ${parked} -> spent ${after.spent} pending ${pendingOf(after)} | second Post wrote ${again.stateWritten}`);
        assert(a.decision === "ask" && parked === 1 && after.spent === 1 && pendingOf(after) === 0 && !again.stateWritten,
          `(i), ${ev}: the ask parks 1 and its Post run commits it once, read ${a.decision} / ${parked} / ${JSON.stringify(after)}`, a);
        const states = [PS, {}].map((o) => {
          const t = session().seed({ spent: 0 });
          t.run(IRM, o);
          t.post(IRM, { ...o, failure });
          const st = t.state();
          t.cleanup();
          return JSON.stringify(st);
        });
        rows.push(`    ${`(iv), ${ev}`.padEnd(40)} PowerShell ${states[0]} | Bash ${states[1]}`);
        assert(states[0] === states[1] && JSON.parse(states[0]).spent === 50, `(iv), ${ev}: PowerShell and Bash end the same, 50 committed, read ${states.join(" / ")}`);
      }
      const d = session().seed({ spent: 0 });
      d.run(cmd, PS);
      const next = d.run(`curl -s "${V1}amazon/shop?q=a"`);
      const dst = d.state();
      d.cleanup();
      rows.push(`    ${"(i) declined, then a 1cr Bash call".padEnd(40)} next ${next.decision || "pass"}, spent ${dst.spent}, pending ${pendingOf(dst)}`);
      assert(next.raw === "" && dst.spent === 1 && pendingOf(dst) === 1, `declined: never counted, read ${JSON.stringify(dst)}`, next);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P2-A7-powershell-mutant",
    desc: "MUTANT (0.3.1, A7, the N9 pattern): with the tool-name check neutralised (every tool read as Bash), a valid Bash plain curl sent through PowerShell slips through silently and is committed, attended and unattended; this build asks attended and denies unattended",
    fn() {
      const dir = mkdtempSync(join(tmpdir(), "sc-guard-ps-mutant-"));
      const m = mutant(dir, "tool-check-gone", `NOT_BASH = input.tool_name !== undefined && input.tool_name !== "Bash";`, "NOT_BASH = false;");
      const cmd = PS_CASES[0][1];
      const rows = [];
      for (const [mode, opts, want] of [["att", PS, "ask"], ["unatt", { ...PS, ...UNATTENDED }, "deny"]]) {
        const mut = once(cmd, { ...opts, guard: m });
        const fix = once(cmd, opts);
        rows.push(`    ${mode.padEnd(6)} mutant ${String(mut.r.decision).padEnd(5)} spent=${mut.st.spent || 0} | fix ${fix.r.decision} spent=${fix.st.spent || 0}`);
        assert(mut.r.decision === null && mut.r.raw === "" && mut.st.spent === 1,
          `mutant (${mode}): the PowerShell call slips through silently and is committed (the leak this fixture catches), read ${mut.r.decision} / ${JSON.stringify(mut.st)}`, mut.r);
        assert(fix.r.decision === want && !fix.st.spent, `fix (${mode}): ${want}, nothing committed, read ${fix.r.decision} / ${JSON.stringify(fix.st)}`, fix.r);
      }
      console.log(rows.join("\n"));
      rmSync(dir, { recursive: true, force: true });
    },
  },
];
