/*
 * 6b — the REVXL failure report: scripts/report_to_joe.py and the block in all three skills.
 *
 *   R1 the block: one per skill, identical apart from `--skill <folder>`, the live plugin version,
 *      `--plugin socialcrawl-superengine`, S1's sentence, S2's paragraph, its folders = DEFAULT_LOCAL_DIR
 *   R2 socialcrawl: the block sits in a canon-only pair, ends before byte 20,000, before ## First Use
 *   R3 the script: DEFAULT_LOCAL_DIR holds no revxl and equals the blocks' folder; KEY_FILES names
 *      the SocialCrawl key file
 *   R4 the real guard on the block's own commands: draft, send and skip silent, the body Write
 *      silent; a draft carrying the API address is refused as not plain (S1)
 *   R5 the scrub, run for real (needs `python`; "python not found" is a failure, never a pass)
 *   R7 provenance: the template's :24 and :27 put back give the template's sha256
 *
 * R6 is a gate, not a fixture: `python scripts/report_to_joe.py --selftest`.
 * Zero credits, zero network: R4 runs the guard offline (lib.mjs); R5 runs `draft` only, which never
 * sends, under a scratch HOME/USERPROFILE with dead proxies. The API address is built from pieces.
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { session, assert, assertNotPlain, V1 } from "../lib.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const PLUGIN = resolve(HERE, "..", "..", "..");
const SCRIPT = join(PLUGIN, "scripts", "report_to_joe.py");
const SKILLS = ["onboarding", "research-plays", "socialcrawl"];
const HEAD = "## Failure report (offer after any failure you can't fix in two tries)";
const BEGIN = "<!-- canon-only:begin -->";
const END = "<!-- canon-only:end -->";
const ws = (s) => s.replace(/\s+/g, " ");
const S1 = "and use no script names, web addresses or file paths (those go in the body file; a command " +
  "carrying the SocialCrawl address that isn't a plain `curl` is refused):";
const s2 = (dir) => `No \`python\`? Use \`python3\`. If neither runs, nothing was sent: tell the client the details are in ` +
  `\`${dir}/report-body.md\`, to email to Joe.`;

const skill = (s) => readFileSync(join(PLUGIN, "skills", s, "SKILL.md"), "utf8");
const version = () => JSON.parse(readFileSync(join(PLUGIN, ".claude-plugin", "plugin.json"), "utf8")).version;
const script = () => readFileSync(SCRIPT, "utf8");
/** The one DEFAULT_LOCAL_DIR assignment in the shipped script. */
function localDir() {
  const m = [...script().matchAll(/^DEFAULT_LOCAL_DIR = "([^"]*)"/gm)];
  assert(m.length === 1, `R3: exactly one DEFAULT_LOCAL_DIR line in the script, read ${m.length}`);
  return m[0][1];
}
/** The block in one skill: its heading to the next `## ` heading, a canon-only end marker or the end. */
function block(s) {
  const t = skill(s);
  const n = t.split(HEAD).length - 1;
  assert(n === 1, `R1: ${s} holds exactly one failure-report heading, read ${n}`);
  const a = t.indexOf(HEAD);
  const ends = [t.indexOf("\n## ", a + HEAD.length), t.indexOf("\n" + END, a)].filter((i) => i >= 0);
  return t.slice(a, ends.length ? Math.min(...ends) : undefined).replace(/\n+$/, "") + "\n";
}
/** The block's runnable lines: `python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" <sub> ...`. */
function commands(b) {
  const c = {};
  for (const m of b.matchAll(/^`(python "\$\{CLAUDE_PLUGIN_ROOT\}\/scripts\/report_to_joe\.py" (draft|send|skip) [^`\n]+)`$/gm)) c[m[2]] = m[1];
  assert(Object.keys(c).sort().join() === "draft,send,skip", `R4: the block holds the draft, send and skip lines, read ${Object.keys(c)}`);
  return c;
}

export default [
  {
    id: "6b-R1",
    desc: "the block: one per skill, identical apart from --skill <folder>, live version, plugin, S1, S2, folders = DEFAULT_LOCAL_DIR",
    fn() {
      const ver = version();
      const dir = localDir();
      const norm = {};
      for (const s of SKILLS) {
        const b = block(s);
        const sk = [...b.matchAll(/--skill (\S+)/g)].map((m) => m[1]);
        assert(sk.length === 1 && sk[0] === s, `R1: ${s}'s block names --skill ${s} once, read ${JSON.stringify(sk)}`);
        const pv = [...b.matchAll(/--plugin-version (\S+)/g)].map((m) => m[1]);
        assert(pv.length === 1 && pv[0] === ver, `R1: ${s}'s --plugin-version is plugin.json's ${ver}, read ${JSON.stringify(pv)}`);
        assert(b.includes("--plugin socialcrawl-superengine "), `R1: ${s}'s block holds --plugin socialcrawl-superengine`);
        assert(ws(b).includes(S1), `R1: ${s}'s block holds S1's sentence`);
        assert(ws(b).includes(s2(dir)), `R1: ${s}'s block holds S2's paragraph naming ${dir}`);
        const dirs = [...b.matchAll(/`?([\w./~-]+)\/report-body\.md/g)].map((m) => m[1]);
        assert(dirs.length >= 2 && dirs.every((d) => d === dir), `R1: ${s}'s block folders are all ${dir}, read ${JSON.stringify(dirs)}`);
        norm[s] = b.replace(/--skill \S+/, "--skill <skill>");
      }
      const [a, ...rest] = SKILLS.map((s) => norm[s]);
      rest.forEach((r, i) => assert(r === a, `R1: ${SKILLS[i + 1]}'s block equals onboarding's apart from --skill`));
    },
  },
  {
    id: "6b-R2",
    desc: "socialcrawl: the block is inside a canon-only pair, ends before byte 20,000 and comes before ## First Use",
    fn() {
      const t = skill("socialcrawl");
      const h = t.indexOf(HEAD);
      assert(h >= 0, "R2: socialcrawl holds the block");
      const b = t.lastIndexOf(BEGIN, h);
      assert(b >= 0 && !t.slice(b, h).includes(END) && /^<!-- canon-only:begin -->\n$/.test(t.slice(b, h)),
        `R2: a canon-only begin marker sits on the line right above the heading, read ${JSON.stringify(t.slice(Math.max(b, h - 60), h))}`);
      const e = t.indexOf(END, h);
      assert(e >= 0 && !t.slice(h, e).includes("<!-- canon-only:"), "R2: the block's own canon-only end marker closes it, with no marker inside");
      assert(!t.slice(h + HEAD.length, e).includes("\n## "), "R2: no other section sits inside the pair");
      const endByte = Buffer.byteLength(t.slice(0, e + END.length), "utf8");
      assert(endByte < 20000, `R2: the pair ends before byte 20,000, read ${endByte}`);
      const fu = t.indexOf("\n## First Use");
      assert(fu > e, `R2: the block comes before ## First Use (end ${e}, First Use ${fu})`);
    },
  },
  {
    id: "6b-R3",
    desc: "the script: DEFAULT_LOCAL_DIR holds no revxl and equals the blocks' folder; KEY_FILES names .config/socialcrawl/api_key",
    fn() {
      const dir = localDir();
      assert(!/revxl/i.test(dir), `R3: DEFAULT_LOCAL_DIR holds no revxl, read ${dir}`);
      for (const s of SKILLS) {
        const dirs = [...block(s).matchAll(/`?([\w./~-]+)\/report-body\.md/g)].map((m) => m[1]);
        assert(dirs.length && dirs.every((d) => d === dir), `R3: ${s}'s block folder equals DEFAULT_LOCAL_DIR ${dir}, read ${JSON.stringify(dirs)}`);
      }
      const k = [...script().matchAll(/^KEY_FILES = \[[^\n]*$/gm)];
      assert(k.length === 1 && k[0][0].includes('".config/socialcrawl/api_key"'), `R3: the KEY_FILES line names .config/socialcrawl/api_key, read ${k.map((m) => m[0])}`);
    },
  },
  {
    id: "6b-R4",
    desc: "the real guard on the block's own commands: draft, send, skip and the body Write are silent; a draft with the API address is refused",
    fn() {
      const dir = localDir();
      const s = session();
      try {
        for (const sk of SKILLS) {
          const c = commands(block(sk));
          const fill = (cmd) => cmd.replace("<step>", "balance read").replace("<the error line>", "exit 3").replace("<headline>", "the budget pane failed");
          const draft = fill(c.draft);
          const runs = [["draft", draft], ["draft, root expanded", draft.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN.split("\\").join("/"))]];
          for (const slug of ["socialcrawl-budget-pane-failed", "socialcrawl-calls-missing"]) {
            const p = `${dir}/drafts/20261030T000000Z-${slug}.json`;
            runs.push([`send ${slug}`, c.send.replace("<draft path>", p)], [`skip ${slug}`, c.skip.replace("<draft path>", p)]);
          }
          for (const [what, cmd] of runs) {
            const r = s.run(cmd);
            assert(r.exit === 0 && r.raw === "" && !r.stateWritten, `R4: ${sk} ${what} is silent: ${cmd}, read exit ${r.exit} ${JSON.stringify(r.raw).slice(0, 300)}`, r);
          }
          const bad = s.run(fill(c.draft.replace("<the error line>", "GET " + V1 + "instagram/profile returned 500")));
          assertNotPlain(bad, `R4: ${sk} draft with the API address in --error-line`);
        }
        for (const fp of [`${dir}/report-body.md`, `C:\\proj\\${dir.split("/").join("\\")}\\report-body.md`, `/home/u/proj/${dir}/report-body.md`]) {
          const r = s.run("", { extra: { tool_name: "Write", tool_input: { file_path: fp, content: "The step that failed: the balance read. Exit 3.\n" } } });
          assert(r.exit === 0 && r.raw === "" && !r.stateWritten, `R4: a Write of ${fp} is silent, read ${JSON.stringify(r.raw).slice(0, 300)}`, r);
        }
      } finally {
        s.cleanup();
      }
    },
  },
  {
    id: "6b-R5",
    desc: "the scrub, run for real: the SocialCrawl key file's value never reaches stdout or the draft",
    fn() {
      const d = mkdtempSync(join(tmpdir(), "sc-report-test-"));
      try {
        const FAKE = "sc_" + "R5fixtureNotAKeyQwz";   // never a real key; split so no scanner reads it as one
        mkdirSync(join(d, ".config", "socialcrawl"), { recursive: true });
        writeFileSync(join(d, ".config", "socialcrawl", "api_key"), FAKE + "\n");
        writeFileSync(join(d, "body.md"), `The step that failed: the balance read, with the key ${FAKE} in its output.\n`);
        const DEAD = "http://127.0.0.1:9";
        const env = { ...process.env, HOME: d, USERPROFILE: d, PYTHONUTF8: "1", HTTPS_PROXY: DEAD, HTTP_PROXY: DEAD, ALL_PROXY: DEAD };
        for (const k of Object.keys(env)) if (/^socialcrawl_api_key$/i.test(k)) delete env[k];
        const r = spawnSync("python", [SCRIPT, "draft", "--plugin", "socialcrawl-superengine", "--plugin-version", version(),
          "--skill", "socialcrawl", "--step", "r5", "--error-line", "r5", "--summary", "r5 scrub",
          "--body-file", join(d, "body.md"), "--local-dir", join(d, "reports")], { encoding: "utf8", input: "", env, timeout: 60000 });
        if (r.error && r.error.code === "ENOENT") throw new Error("R5: python not found — the scrub can't be checked (never a silent pass)");
        const out = String(r.stdout || "");
        assert(r.status === 0, `R5: draft exits 0, read ${r.status} ${String(r.stderr || "").slice(0, 300)}`);
        const m = out.match(/^DRAFT: (.+)$/m);
        assert(m, "R5: draft prints its DRAFT: path");
        const draft = readFileSync(m[1].trim(), "utf8");
        assert(!out.includes(FAKE), "R5: the fake key is absent from stdout");
        assert(!draft.includes(FAKE), "R5: the fake key is absent from the draft JSON");
        assert(draft.includes("[REDACTED]") && out.includes("[REDACTED]"), "R5: [REDACTED] is in the draft and the preview");
      } finally {
        rmSync(d, { recursive: true, force: true });
      }
    },
  },
  {
    id: "6b-R7",
    desc: "provenance: the template's :24 and :27 put back give the template's sha256; LF only",
    fn() {
      const b = readFileSync(SCRIPT);
      assert(!b.includes(13), "R7: the script is LF only");
      const L = b.toString("utf8").split("\n");
      L[23] = 'DEFAULT_LOCAL_DIR = "revxl/reports"  # the only plugin-specific line: each plugin sets its own folder';
      L[26] = 'KEY_FILES = [VAULT_KEY_FILE, ".config/openrouter/api_key"]  # scrubbed from reports; other plugins extend this list';
      const sha = createHash("sha256").update(L.join("\n"), "utf8").digest("hex");
      assert(sha === "62eb6b70d69a830f39584050dad0dc78a69c7bd556590330aefba79ef38a4fcb",
        `R7: the shipped script differs from the MK template (ecef422) only at :24 and :27, read sha256 ${sha}`);
    },
  },
];
