/*
 * R14a — the silent session limit: the decision logic of hooks/credit-guard.mjs (D28 since 0.4.0).
 *
 * Within the limit (no budget file: min(500, 25% of the balance), else 500 when the balance can't
 * be read) nothing is emitted and the command's worst case is committed; a command that would take
 * the session past it is denied with M_LIMIT, and reaching it exactly passes. The can't-count calls
 * are counted at their known worst case (D28a), and every command that is not a plain curl is
 * denied with M_NOTPLAIN (R14a.2). The guard never asks. A deny is never counted (Joe, P1), and
 * the guard no longer runs after a command: there is no pending quote and no Post commit.
 *
 * Synchronous (P26), every guard run in its own seeded session (P21): balance 800 -> limit 200,
 * unless a fixture says otherwise; the balance-unknown group is its own fixture. Zero credits,
 * zero network — X1 opens one loopback socket to a server in its own driver process.
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { session, run, visible, V1, HOST, TSCRIPT, GUARD, COSTS, BALANCE, LIMIT, M_NOTPLAIN, M_LOST, mLimit, srcAuto, assert, assertDecision, assertNoMatch } from "../lib.mjs";

const UNATTENDED = { env: { CLAUDE_CODE_SESSION_ATTENDED: "0" } };
const NOLOCAL = { unsetEnv: ["GROQ_API_KEY"], env: { PATH: "" } };
const FLAT = `curl -s "${V1}prism/leads?query=x"`;             // flat 50
const METERED = `curl -s "${V1}search/news?query=x"`;           // metered 2-62, counted at 62
const SMALL = `curl -s "${V1}amazon/product?asin=B1"`;          // flat 5
const HEREDOC_PY = `python3 - <<'PY'\nimport urllib.request\nurllib.request.urlopen("${V1}amazon/product?asin=B1")\nPY`;
const HEREDOC_NOTE = `cat > notes.md <<'EOF'\nsee ${V1}amazon/product?asin=B1\nEOF`;
/** M7b's mutation: blank every heredoc body again, whatever reads it (the mask R14a.1 removed). */
function blankBodies(src) {
  return src.replace(/(<<-?[ \t]*(['"]?)\\?([\w.-]+)\2[^\n]*\n)([\s\S]*?)(\n\t*\3(?=\n|$))/g,
    (m, head, q, word, body, tail) => head + body.replace(/[^\n]/g, " ") + tail);
}
const sha = (c) => createHash("sha256").update(c).digest("hex");   // the key an older build saved a pending quote under
const row = (label, r, st) =>
  `    ${label.padEnd(44)} ${String(r.decision).padEnd(5)} spent=${(st && st.spent) || 0}`;
/** M_LIMIT for a session seeded at `spent` with `balance` cached and no budget file. */
const limitMsg = (r, spent, worst, balance = BALANCE) =>
  mLimit({ spent, worst, limit: Math.min(500, Math.floor(0.25 * balance)), src: srcAuto(balance), bf: r.bf });

/** One guard run in a fresh session seeded with `seed`; returns the result and the state after. */
function once(command, seed, opts = {}) {
  const s = session(opts);
  s.seed(seed);
  const r = s.run(command, opts);
  const st = s.state();
  s.cleanup();
  return { r, st };
}

export default [
  {
    id: "M1-main-grid",
    desc: "MATRIX (D28): {attended, unattended} x {within the limit, past it, further past it, balance 40 -> limit 10, balance 2000 -> limit 500 within it, balance 4000 -> limit 500 (not 1000) past it} x {flat, metered}: within, silent and committed; past, denied with exactly M_LIMIT and nothing counted, the same attended and unattended",
    fn() {
      const cols = [
        // [column, balance, flat seed/cmd/worst, metered seed/cmd/worst, expected decision]
        ["within the limit", 800, [0, FLAT, 50], [0, METERED, 62], null],
        ["past the limit", 800, [190, FLAT, 50], [190, METERED, 62], "deny"],
        ["further past it", 800, [390, FLAT, 50], [390, METERED, 62], "deny"],
        ["balance 40 -> limit 10", 40, [6, SMALL, 5], [0, METERED, 62], "deny"],
        // The 500 ceiling (R18-1, Q-c): 2000 and 4000 both give 500, so 490 + 50 is past it at 4000
        // (a 1000 limit would pass it), and at 2000 190 + 50 and 150 + 62 stay within 500 but are
        // past 200, so a limit of 200 would deny them (R18 H8).
        ["balance 2000 -> limit 500, within (200 would deny)", 2000, [190, FLAT, 50], [150, METERED, 62], null],
        ["balance 4000 -> limit 500 (not 1000), past it", 4000, [490, FLAT, 50], [490, METERED, 62], "deny"],
      ];
      const lines = [];
      for (const attended of [true, false]) {
        for (const [col, balance, flat, metered, want] of cols) {
          for (const [kind, [spent, cmd, worst]] of [["flat", flat], ["metered", metered]]) {
            const label = `${attended ? "attended" : "unattended"} / ${col} / ${kind}`;
            const { r, st } = once(cmd, { spent }, { balance, ...(attended ? {} : UNATTENDED) });
            lines.push(row(label, r, st));
            assert(r.exit === 0, `${label}: exit ${r.exit}`, r);
            if (want === null) {
              // Within the limit: silent, committed at once — attended or not.
              assertDecision(r, null, `${label}: within the limit no decision is made`);
              assert(r.raw === "", `${label}: within the limit nothing is emitted`, r);
              assert(st.spent === spent + worst, `${label}: committed ${worst}, read ${JSON.stringify(st)}`, r);
            } else {
              assertDecision(r, "deny", `${label}: past the limit is denied`);
              assert(r.message === limitMsg(r, spent, worst, balance), `${label}: exactly M_LIMIT, read ${r.message}`, r);
              assert(st.spent === spent, `${label}: a deny is never counted, read ${JSON.stringify(st)}`, r);
            }
          }
        }
      }
      console.log(`    ${"cell".padEnd(44)} decision / resulting state\n` + lines.join("\n"));
    },
  },
  {
    id: "M2-commit-semantics",
    desc: "COMMIT (Joe, P1; D28): a deny is never counted, so its retry is denied again, attended and unattended; within the limit each call is committed at once, reaching it exactly included, and the next paid call past it is denied",
    fn() {
      // (a) Denied, attended or unattended: nothing is counted, so the retry is denied again.
      for (const [who, o] of [["attended", {}], ["unattended", UNATTENDED]]) {
        const a = session().seed({ spent: 190 });
        assertDecision(a.run(FLAT, o), "deny", `(a) ${who}: 190 + 50 is past the 200 limit`);
        assertDecision(a.run(`curl -s "${V1}prism/leads?query=y"`, o), "deny", `(a) ${who}: the retry is denied again`);
        assert(a.state().spent === 190, `(a) ${who}: nothing committed, read ${a.stateRaw()}`);
        a.cleanup();
      }
      // (b) Within the limit: 100 -> 150 -> 200 are committed at once and silent (200 reaches the
      // limit exactly); the next 50cr command is denied and counts nothing.
      const b = session().seed({ spent: 100 });
      const next = (n) => `curl -s "${V1}prism/leads?query=n${n}"`;
      for (let n = 1; n <= 2; n++) assertDecision(b.run(next(n)), null, `(b) within the limit (call ${n})`);
      assert(b.state().spent === 200, `(b) two silent commits, read ${b.stateRaw()}`);
      const over = b.run(next(3));
      assertDecision(over, "deny", "(b) past the limit");
      assert(over.message === limitMsg(over, 200, 50) && b.state().spent === 200, `(b) M_LIMIT, nothing counted, read ${over.message} / ${b.stateRaw()}`, over);
      b.cleanup();
    },
  },
  {
    id: "M3-deny-retry-mutant",
    desc: "COMMIT (P1 killer, D28): a guard that counts the command it denies (commit-before-deny) denies the next call that is within the limit; this build counts nothing for the deny and passes that call",
    fn() {
      // The mutant: every deny commits the worst case first, as the pin's logic did for every
      // decision. Under the hard limit the leak runs the other way: the total runs past what was
      // spent, and an in-budget call is then denied.
      const dir = mkdtempSync(join(tmpdir(), "sc-guard-mutant-"));
      const src = readFileSync(GUARD, "utf8");
      const anchor = "  function deny(message, kind) {\n";
      assert(src.split(anchor).length === 2, "mutation anchor not found exactly once in credit-guard.mjs");
      writeFileSync(join(dir, "credit-guard.mjs"), src.replace(anchor, anchor + "    if (st) { st.spent += cmdWorst; writeState(st); }\n"));
      copyFileSync(COSTS, join(dir, "costs.json"));
      const mutant = join(dir, "credit-guard.mjs");
      const P150 = `curl -s "${V1}prism/leads?query=a" && curl -s "${V1}prism/leads?query=b" && curl -s "${V1}prism/leads?query=c"`;
      for (const [who, o] of [["attended", {}], ["unattended", UNATTENDED]]) {
        const m = session().seed({ spent: 100 });
        assertDecision(m.run(P150, { ...o, guard: mutant }), "deny", `mutant, ${who}: 100 + 150 is denied`);
        assertDecision(m.run(SMALL, { ...o, guard: mutant }), "deny", `mutant, ${who}: a 5cr call within the limit is denied (the total was counted past it)`);
        m.cleanup();
        const f = session().seed({ spent: 100 });
        assertDecision(f.run(P150, o), "deny", `fix, ${who}: 100 + 150 is denied`);
        assertDecision(f.run(SMALL, o), null, `fix, ${who}: the 5cr call within the limit passes`);
        assert(f.state().spent === 105, `fix, ${who}: only the passed call is counted, read ${f.stateRaw()}`);
        f.cleanup();
      }
      rmSync(dir, { recursive: true, force: true });
    },
  },
  {
    id: "M4-cant-count-six",
    desc: "CAN'T-COUNT (D28a): transcripts, cohorts, unreadable URLs and per-unit calls with no ceiling are counted at their known worst case (3, 0, the 50 floor, 0) and pass within the limit, attended and unattended; shell-variable URLs, split-quoted URLs and loops are not plain, so each is denied with M_NOTPLAIN and counts nothing (R14a.2)",
    fn() {
      const six = [
        ["transcript", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, 3],
        ["cohorts (unpriced)", `curl -s "${V1}cohorts?segment=a"`, 0],
        ["shell-variable URL (not plain)", `H=${HOST}; curl -s "https://$H/v1/prism/creator-vet?handle=a"`, "deny"],
        ["split-quoted URL (not plain)", `curl -s "${V1}prism/creator-v""et?h=a"`, "deny"],
        ["unreadable plain URL", `curl -s "${V1}prism/no-such-endpoint?h=a"`, 50],
        ["loop (not plain)", `for i in 1 2 3; do curl -s "${V1}amazon/shop?q=$i"; done`, "deny"],
        ["per-unit, no ceiling", `curl -X POST "${V1}web/batch-scrape" -d '{}'`, 0],
      ];
      const lines = [];
      for (const [label, cmd, want] of six) {
        for (const [who, env] of [["attended", NOLOCAL.env], ["unattended", { ...NOLOCAL.env, ...UNATTENDED.env }]]) {
          const x = once(cmd, { spent: 0 }, { ...NOLOCAL, env });
          lines.push(row(`${who} / ${label}`, x.r, x.st));
          if (want === "deny") {
            assertDecision(x.r, "deny", `${label}, ${who}: not plain, denied`);
            assert(x.r.message === M_NOTPLAIN && !x.st.spent, `${label}, ${who}: exactly M_NOTPLAIN and nothing counted, read ${JSON.stringify(x.st)}`, x.r);
          } else {
            assert(x.r.raw === "" && x.st.spent === want, `${label}, ${who}: counted ${want} and passed silently, read ${x.r.decision} / ${JSON.stringify(x.st)}`, x.r);
          }
        }
      }
      console.log(`    ${"cell".padEnd(44)} decision / resulting state\n` + lines.join("\n"));
    },
  },
  {
    id: "M5-stated-maximum",
    desc: "CAN'T-COUNT, stated max (Joe 09.28.26; D28a): investigate commits its budget or 200, web/sessions 20, economy/imports 20 (R18 H1); jobs, batch-scrape and monitors commit 0; each passes silently within the limit, is counted again on every run, and is denied past it",
    fn() {
      const cases = [
        [`curl -s "${V1}prism/investigate?goal=x&budget=120"`, 120, "investigate budget=120"],
        [`curl -s "${V1}prism/investigate?goal=x"`, 200, "investigate, no budget"],
        [`curl -X POST "${V1}web/sessions" -d '{}'`, 20, "web/sessions"],
        [`curl -s "${V1}economy/imports?company=x"`, 20, "economy/imports"],
        [`curl -X POST "${V1}prism/jobs" -d '{}'`, 0, "prism/jobs"],
        [`curl -X POST "${V1}web/batch-scrape" -d '{}'`, 0, "web/batch-scrape"],
        [`curl -X POST "${V1}web/monitors" -d '{}'`, 0, "web/monitors"],
      ];
      for (const [cmd, max, label] of cases) {
        const s = session().seed({ spent: 0 });
        const r = s.run(cmd);
        assert(r.raw === "" && s.state().spent === max, `${label}: commits ${max}, silently, read ${r.decision} / ${s.stateRaw()}`, r);
        // Counted again next time: within the limit it passes again; past it, it is denied.
        const again = s.run(cmd);
        if (2 * max <= LIMIT) assert(again.raw === "" && s.state().spent === 2 * max, `${label}: counted again, read ${s.stateRaw()}`, again);
        else assert(again.message === limitMsg(again, max, max) && s.state().spent === max, `${label}: past the limit the second time, M_LIMIT, read ${again.message}`, again);
        s.cleanup();
      }
      // Verb-exact: the free GET twin of web/sessions passes and commits nothing (D28a, A4).
      const twin = session().seed({ spent: 0 });
      const tr = twin.run(`curl -s "${V1}web/sessions"`);
      assert(tr.raw === "" && twin.state().spent === 0, `a twin verb never takes POST's stated maximum, read ${tr.decision} / ${twin.stateRaw()}`, tr);
      twin.cleanup();
      // Checkers X2/X3/X5: investigate commits a budget only as it is certainly sent. An encoded
      // `%26budget=` sends none (200); two budgets commit the larger. A #fragment, `curl -G` with
      // any data flag, or text glued on after the closing quote is not a plain curl (R14a.2), so
      // it is denied and counts nothing (D28).
      for (const [cmd, max, label] of [
        [`curl -s "${V1}prism/investigate?goal=x#&budget=1"`, "deny", "budget in the #fragment"],
        [`curl -s "${V1}prism/investigate?goal=x%26budget=1"`, 200, "budget inside a value (%26)"],
        [`curl -s "${V1}prism/investigate?goal=x&budget=1&budget=150"`, 150, "two budgets"],
        [`curl -sG "${V1}prism/investigate?budget=120" -d goal=x`, "deny", "curl -G, budget in the URL, other data"],
        [`curl -s -G "${V1}prism/investigate" --data-urlencode goal=x -d budget=150`, "deny", "curl -G, budget as data"],
        [`curl -s -G "${V1}prism/investigate?goal=x&budget=1" -d budget=150`, "deny", "curl -G, budget in the URL and as data (X5)"],
        [`curl -s "${V1}prism/investigate?goal=x&budget=1"50`, "deny", "50 glued after the quote sends budget=150 (X5)"],
      ]) {
        const s = session().seed({ spent: 0 });
        const r = s.run(cmd);
        if (max === "deny") assert(r.decision === "deny" && r.message === M_NOTPLAIN && s.state().spent === 0, `${label}: denied, nothing counted, read ${r.decision} / ${s.stateRaw()}`, r);
        else assert(r.raw === "" && s.state().spent === max, `${label}: commits ${max}, read ${r.decision} / ${s.stateRaw()}`, r);
        s.cleanup();
      }
    },
  },
  {
    id: "M6-post-commit",
    desc: "POST (D28a): the guard no longer runs after a command. A stray PostToolUse or PostToolUseFailure input — after a deny, after a silent pass, or for a non-SocialCrawl command — prints nothing, exits 0 and writes nothing (no state, no lock); a state file holding an older build's pending quote is read as a whole session (never lost), the quote is never counted, and the next save drops it",
    fn() {
      for (const failure of [false, true]) {
        const ev = failure ? "PostToolUseFailure" : "PostToolUse";
        const s = session().seed({ spent: 190 });
        assertDecision(s.run(FLAT), "deny", "190 + 50 is past the limit");
        const before = s.stateRaw();
        const p = s.post(FLAT, { failure });
        assert(p.raw === "" && p.exit === 0 && s.stateRaw() === before && !existsSync(`${s.stateFile}.lock`),
          `${ev} after a deny: nothing printed, exit 0, nothing written, read ${JSON.stringify(p.raw)} / ${s.stateRaw()}`, p);
        s.cleanup();
      }
      // A command that passed silently: its stray Post changes nothing either.
      const q = session().seed({ spent: 0 });
      assertDecision(q.run(SMALL), null, "a small call passes silently");
      for (const failure of [false, true]) assert(!q.post(SMALL, { failure }).stateWritten, "a stray Post writes nothing");
      assert(q.state().spent === 5, `counted once, before it ran, read ${q.stateRaw()}`);
      // A Post for a command that never touched SocialCrawl takes the fast path.
      assert(!q.post(`ls -la`).stateWritten, "a non-SocialCrawl Post writes nothing");
      q.cleanup();
      // An older build's pending quote (0.3.1 parked one per asked command): its Post never counts
      // it, the session is not lost, the same command is counted once, and the key is dropped.
      const d = session().seed({ spent: 0, pending: { [sha(FLAT)]: 50 } });
      const dp = d.post(FLAT);
      assert(dp.raw === "" && !dp.stateWritten, `a stray Post never counts the old quote, read ${d.stateRaw()}`, dp);
      assertDecision(d.run(FLAT), null, "within the limit the same command passes: the old key is not a lost total");
      const st = d.state();
      assert(st.spent === 50 && !("pending" in st) && !st.lost, `counted once, the old pending key gone, read ${d.stateRaw()}`);
      d.cleanup();
    },
  },
  {
    id: "M7-heredocs",
    desc: "HEREDOCS (Joe 09.28.26, supersedes P4; D28): no heredoc body is masked, so every SocialCrawl URL anywhere in a command is seen, whatever reads the body; a heredoc is never a plain curl, so each is denied with M_NOTPLAIN and counts nothing (R14a.2), and so are a note written with a URL and echo of a URL (mentions are denied, a stated LIMIT); the unattended log carries the body's visible 5",
    fn() {
      const PY = HEREDOC_PY;
      // A heredoc is not plain: it is denied every time, well within the limit or near it.
      for (const spent of [0, 198]) {
        const { r, st } = once(PY, { spent });
        assertDecision(r, "deny", `python3 heredoc at spent ${spent} is denied (not plain)`);
        assert(r.message === M_NOTPLAIN && st.spent === spent, `python3 heredoc at spent ${spent}: M_NOTPLAIN, nothing counted, read ${JSON.stringify(st)}`, r);
      }
      const pl = visible(PY);
      assert(pl && pl.cmdWorst === 5, `the python3 heredoc's body is seen at 5, read ${JSON.stringify(pl)}`);
      const piped = visible(`cat <<'EOF' | python3\nimport urllib.request\nurllib.request.urlopen("${V1}amazon/product?asin=B1")\nEOF`);
      assert(piped && piped.cmdWorst === 5, `a pipe into an interpreter keeps the body seen, read ${JSON.stringify(piped)}`);
      // A note written with a URL in it is denied, attended and unattended: the stated LIMIT
      // (Joe 09.28.26; R14a.2: mentions are not plain).
      for (const [label, cmd] of [["cat > notes.md <<'EOF'", HEREDOC_NOTE], ["cat <<'EOF' > notes.md", `cat <<'EOF' > notes.md\nsee ${V1}amazon/product?asin=B1\nEOF`]]) {
        for (const [who, o] of [["attended", {}], ["unattended", UNATTENDED]]) {
          const { r, st } = once(cmd, { spent: 0 }, o);
          assertDecision(r, "deny", `${label}, ${who}: a URL in the body is denied (LIMIT)`);
          assert(r.message === M_NOTPLAIN && st.spent === 0, `${label}, ${who}: M_NOTPLAIN, nothing counted, read ${JSON.stringify(st)}`, r);
        }
      }
      // Checkers X1 and X4: every mask tried let a body that runs pass at 0 — each of these ran
      // the URL, and each is denied, seen at the pin's 5.
      const PAID = `${V1}amazon/product?asin=B1`;
      const GET = `curl -s "${PAID}"`;
      const IMPORT = `import urllib.request\nurllib.request.urlopen("${PAID}")`;
      for (const [label, cmd] of [
        ["py -", `py - <<'PY'\n${IMPORT}\nPY`],
        ["py -3", `py -3 <<PY\n${IMPORT}\nPY`],
        ["powershell -Command -", `powershell -NoProfile -Command - <<'PS'\nInvoke-WebRequest "${PAID}"\nPS`],
        ["deno run -", `deno run --allow-net - <<'TS'\nawait fetch("${PAID}");\nTS`],
        ["bun -", `bun - <<'JS'\nawait fetch("${PAID}");\nJS`],
        ["uv run -", `uv run - <<'PY'\n${IMPORT}\nPY`],
        ["ssh host", `ssh box <<'EOF'\n${GET}\nEOF`],
        ["written, then ./x.sh", `cat > x.sh <<'EOF'\n${GET}\nEOF\nchmod +x x.sh && ./x.sh`],
        ["written, then source x.sh", `cat > x.sh <<'EOF'\n${GET}\nEOF\nsource x.sh`],
        ["written, then . ./x.sh", `cat > x.sh <<'EOF'\n${GET}\nEOF\n. ./x.sh`],
        ["written and run on the operator's line", `cat > x.sh <<'EOF' && chmod +x x.sh && ./x.sh\n${GET}\nEOF`],
        ["source /dev/stdin", `source /dev/stdin <<'EOF'\n${GET}\nEOF`],
        ["xargs curl", `xargs curl -s <<'EOF'\n${PAID}\nEOF`],
        ["wget -i -", `wget -q -i - <<'EOF'\n${PAID}\nEOF`],
        ["curl -K -", `curl -s -K - <<'EOF'\nurl = "${PAID}"\nEOF`],
        ["an unquoted delimiter runs $(...)", `cat > notes.md <<EOF\n$(${GET})\nEOF`],
        ["bash <<EOF", `bash <<EOF\n${GET}\nEOF`],
        ["> \"$(bash)\" redirect target", `cat <<'EOF' > "$(bash)"\n${GET}\nEOF`],
        ["backtick redirect target", `cat <<'EOF' > "\`bash\`"\n${GET}\nEOF`],
        ["escaped delimiter <<\\t\\r\\u\\e", `cat > f <<\\t\\r\\u\\e\ntrue\n${GET}\nt\\r\\u\\e`],
        ["backslash-in-double-quotes delimiter <<\"E\\\\OF\"", `cat > f <<"E\\\\OF"\nE\\OF\n${GET}\nE\\\\OF`],
        // Checker A25: a mask on `<<-` bodies, on bodies fed to tee, or on `>>` appends would each
        // re-open a 0-count leak; each of these runs the URL.
        ["<<- with a tab-indented body", `python3 - <<-PY\n\timport urllib.request\n\turllib.request.urlopen("${PAID}")\n\tPY`],
        ["tee x.sh <<'EOF', then bash x.sh", `tee x.sh <<'EOF'\n${GET}\nEOF\nbash x.sh`],
        ["cat >> x.sh <<'EOF', then bash x.sh", `cat >> x.sh <<'EOF'\n${GET}\nEOF\nbash x.sh`],
      ]) {
        const l = visible(cmd);
        assert(l && l.decision === "deny" && l.kind === "not-plain" && l.cmdWorst === 5, `${label}: denied, and the body is seen at 5, read ${JSON.stringify(l)}`);
      }
      const ECHO = `echo '${V1}amazon/product?asin=B1'`;
      const echo = once(ECHO, { spent: 0 });
      assertDecision(echo.r, "deny", "echo '<URL>' is denied (a mention, the stated LIMIT)");
      assert(echo.r.message === M_NOTPLAIN && echo.st.spent === 0, `echo '<URL>': M_NOTPLAIN, nothing counted, read ${JSON.stringify(echo.st)}`, echo.r);
    },
  },
  {
    id: "M7b-heredoc-mask-mutant",
    desc: "HEREDOCS (killer, D28): a guard that blanks heredoc bodies again sees the python3 heredoc and the note at 0 in the unattended log; this build denies both and sees each at 5",
    fn() {
      const dir = mkdtempSync(join(tmpdir(), "sc-guard-mutant-"));
      const src = readFileSync(GUARD, "utf8");
      const anchor = "  const cmd = rawCmd;\n";
      assert(src.includes(anchor), "mutation anchor not found in credit-guard.mjs");
      writeFileSync(join(dir, "credit-guard.mjs"), src.replace(anchor, `  ${blankBodies}\n  const cmd = blankBodies(rawCmd);\n`));
      copyFileSync(COSTS, join(dir, "costs.json"));
      const mutant = join(dir, "credit-guard.mjs");
      for (const [label, cmd] of [["python3 - heredoc", HEREDOC_PY], ["cat > notes.md heredoc", HEREDOC_NOTE]]) {
        const m = visible(cmd, { guard: mutant });
        assert(m && m.cmdWorst === 0, `mutant: ${label} is seen at 0 (the leak M7 catches), read ${JSON.stringify(m)}`);
        const f = visible(cmd);
        assert(f && f.kind === "not-plain" && f.cmdWorst === 5, `fix: ${label} is denied and seen at 5, read ${JSON.stringify(f)}`);
      }
      rmSync(dir, { recursive: true, force: true });
    },
  },
  {
    id: "M8-dry-runs",
    desc: "DRY RUNS, re-pointed (R14a.2 ruling (b), supersedes P8; D28): dry_run=1 is counted at its full label price everywhere, declared or not; a plain curl is counted silently, any other shape is denied with M_NOTPLAIN and seen at the same full figure",
    fn() {
      const LQ = `${V1}linkedin/search/posts?keyword=x&dry_run=1`;        // declares dryRun, 56 in full
      // Plain curls: counted in full, silently (they were free before R14a.2).
      for (const [label, cmd, want] of [
        ["declared, double-quoted", `curl -s "${LQ}"`, 56],
        ["control, no dry_run", `curl -s "${V1}linkedin/search/posts?keyword=x"`, 56],
        ["undeclared", `curl -s "${V1}search/news?query=x&dry_run=1"`, 62],
        ["declared, dry_run first, single-quoted", `curl -s '${V1}linkedin/search/posts?dry_run=1&keyword=x'`, 56],
        ["inside a value (%26)", `curl -s "${V1}linkedin/search/posts?keyword=x%26dry_run=1"`, 56],
        ["as DRY_RUN", `curl -s "${V1}linkedin/search/posts?keyword=x&DRY_RUN=1"`, 56],
        ["sent twice, once as 0", `curl -s "${V1}linkedin/search/posts?keyword=x&dry_run=1&dry_run=0"`, 56],
        ["continued, $SOCIALCRAWL_API_KEY header", `curl -s \\\n  -H "x-api-key: $SOCIALCRAWL_API_KEY" \\\n  "${LQ}"`, 56],
        ["$(cat key) header", `curl -s -H "x-api-key: $(cat ~/.config/socialcrawl/api_key)" "${LQ}"`, 56],
      ]) {
        const { r, st } = once(cmd, { spent: 0 });
        assert(r.raw === "" && st.spent === want, `${label}: counted ${want} silently, read ${JSON.stringify(st)}`, r);
      }
      // Not plain: denied, nothing counted, seen at the same full figure (checkers X2, X5, X11).
      for (const [label, cmd] of [
        ["in the #fragment", `curl -s "${V1}linkedin/search/posts?keyword=x#&dry_run=1"`],
        ["#top fragment", `curl -s '${LQ}#top'`],
        ["in an unquoted URL", `curl -s ${LQ}`],
        ["'&dry_run=0' glued after the quote", `curl -s "${LQ}"'&dry_run=0'`],
        ["0 glued after the quote (dry_run=10)", `curl -s "${LQ}"0`],
        ["-G -d dry_run=0", `curl -s -G "${LQ}" -d dry_run=0`],
        ["--url-query dry_run=0", `curl -s "${LQ}" --url-query dry_run=0`],
        ["-K c.cfg (X11)", `curl -s -K c.cfg "${LQ}"`],
        ["-G --expand-data dry_run=0 (X11)", `curl -s -G --expand-data dry_run=0 "${LQ}"`],
        ["${U%&dry_run=1}", `U="${LQ}"; curl -s "\${U%&dry_run=1}"`],
        ["$(echo … | sed …)", `curl -s "$(echo "${LQ}" | sed 's/&dry_run=1//')"`],
        ["python heredoc .replace()", `python3 - <<'PY'\nimport urllib.request\nurllib.request.urlopen("${LQ}".replace("&dry_run=1", ""))\nPY`],
      ]) {
        const { r, st } = once(cmd, { spent: 0 });
        assertDecision(r, "deny", `${label}: not plain, so it is denied`);
        assert(r.message === M_NOTPLAIN && st.spent === 0, `${label}: M_NOTPLAIN, nothing counted, read ${JSON.stringify(st)}`, r);
        const l = visible(cmd);
        assert(l && l.cmdWorst === 56, `${label}: seen at 56 in full, read ${JSON.stringify(l)}`);
      }
    },
  },
  {
    id: "M9-per-unit-post-stats",
    desc: "PER-UNIT (P3, Joe 09.28.26; D28): post-stats with 100 Instagram URLs is counted at its label worst case 500, a stated over-count (the batch holds 200 at 2 per Instagram URL), so at the 200 limit it is denied with M_LIMIT naming 500",
    fn() {
      const urls = Array.from({ length: 100 }, (_, i) => `"https://www.instagram.com/p/x${i}/"`).join(",");
      const cmd = `curl -X POST "${V1}prism/post-stats" -H "Content-Type: application/json" -d '{"urls":[${urls}]}'`;
      const { r, st } = once(cmd, { spent: 0 });
      assertDecision(r, "deny", "100 URLs, worst case 500, is past the 200 limit");
      assert(r.message === limitMsg(r, 0, 500) && st.spent === 0, `M_LIMIT names the label worst case 500, nothing counted, read ${r.message}`, r);
    },
  },
  {
    id: "M10-balance-unknown",
    desc: "BALANCE UNKNOWN (P5; D28a): no balance cached or readable means the fallback limit of 500, so the first paid call passes and is counted; an integer balance of 0 or more gives the automatic cap (0 and 3 give 0, so a paid call is denied with M_LIMIT naming that balance; 4 gives 1, which a 1cr call reaches exactly; 8 gives 2); a string, negative or fractional balance is no readable balance (the fallback 500)",
    fn() {
      const A = `curl -s "${V1}amazon/shop?q=a"`;
      const first = session({ balance: null });
      const r = first.run(A);
      assert(r.raw === "" && first.state().spent === 1, `the first paid call passes under the fallback 500, read ${r.decision} / ${first.stateRaw()}`, r);
      first.cleanup();
      for (const balance of [0, 3]) {
        const { r: b, st } = once(A, { spent: 0 }, { balance });
        assertDecision(b, "deny", `balance ${balance}: the automatic cap is 0`);
        assert(b.message === mLimit({ spent: 0, worst: 1, limit: 0, src: srcAuto(balance), bf: b.bf }) && st.spent === 0, `balance ${balance}: M_LIMIT at limit 0, read ${b.message}`, b);
      }
      for (const balance of ["1000", -5, 999.5]) {
        const { r: b, st } = once(A, { spent: 0 }, { balance });
        assert(b.raw === "" && st.spent === 1, `balance ${JSON.stringify(balance)}: no readable balance, so the fallback 500, and it passes, read ${b.decision} / ${JSON.stringify(st)}`, b);
      }
      const { r: four, st: s4 } = once(A, { spent: 0 }, { balance: 4 });
      assert(four.raw === "" && s4.spent === 1, `balance 4: limit floor(0.25 x 4) = 1, which a 1cr call reaches exactly, read ${four.decision} / ${JSON.stringify(s4)}`, four);
      const eight = session({ balance: 8 }).seed({ spent: 0 });
      assertDecision(eight.run(A), null, "balance 8, limit 2: 1 is within it");
      assertDecision(eight.run(`curl -s "${V1}amazon/shop?q=b"`), null, "balance 8, limit 2: 2 reaches it exactly");
      const third = eight.run(`curl -s "${V1}amazon/shop?q=c"`);
      assertDecision(third, "deny", "balance 8, limit 2: 3 is past it");
      assert(third.message === mLimit({ spent: 2, worst: 1, limit: 2, src: srcAuto(8), bf: third.bf }), `exactly M_LIMIT, read ${third.message}`, third);
      eight.cleanup();
    },
  },
  {
    id: "M11-state-files",
    desc: "STATE (D28): a corrupt state file is a lost total — every paid call is denied with M_LOST and the file is saved again as lost — and never crashes; an old {spent} file still reads: its spent is kept and counted on, under the fallback 500 when no balance is cached",
    fn() {
      const c = session();
      writeFileSync(c.stateFile, "{not json");
      const r = c.run(`curl -s "${V1}amazon/shop?q=a"`);
      assert(r.exit === 0, "rc 0 on a corrupt state file", r);
      assertDecision(r, "deny", "a corrupt file is a lost total: the call is denied");
      assert(r.message === M_LOST && c.state() && c.state().lost === true && c.state().spent === 0, `M_LOST, saved as lost, read ${r.message} / ${c.stateRaw()}`, r);
      c.cleanup();
      const old = session({ balance: null }).seed({ spent: 12 });
      const o = old.run(`curl -s "${V1}amazon/shop?q=a"`);
      assert(o.raw === "" && old.state().spent === 13, `the old file's spent is read and counted on: 12 + 1, read ${o.decision} / ${old.stateRaw()}`, o);
      old.cleanup();
    },
  },
  {
    id: "M12-repeats-under-the-cap",
    desc: "REPEATS, re-pointed (R14a.2; D28): a curl glob, a loop in interpreter code, find -exec, xargs/watch behind a prefix command and curl -g are each denied with M_NOTPLAIN within the limit, nothing counted; curl piped into python3 -m json.tool is tidy output, counted silently",
    fn() {
      const P = `${V1}prism/leads?query=x`;
      const G = `"${V1}prism/leads?query=x&page=[1-5]"`;
      for (const [label, cmd] of [
        ["glob + | sort -g", `curl -s ${G} | sort -g`],
        ["glob + && ls -lg", `curl -s ${G} && ls -lg`],
        ["list glob + | sort -g", `curl -s "${V1}prism/leads?query={a,b,c}" | sort -g`],
        ["python3 heredoc loop", `python3 - <<'PY'\nimport urllib.request\nfor q in ["a", "b", "c"]:\n    urllib.request.urlopen(f"${V1}prism/leads?query={q}")\nPY`],
        ["python3 -c loop", `python3 -c 'import urllib.request\nfor q in "abc": urllib.request.urlopen("${P}" + q)'`],
        ["node -e loop", `node -e 'for (const q of ["a", "b"]) fetch("${P}" + q)'`],
        ["find -exec curl", `find . -name "*.txt" -exec curl -s "${P}" \\;`],
        ["| nice xargs", `cat ids.txt | nice xargs -I{} curl -s "${P}{}"`],
        ["| timeout 60 xargs", `cat ids.txt | timeout 60 xargs -I{} curl -s "${P}{}"`],
        ["| command xargs", `cat ids.txt | command xargs -I{} curl -s "${P}{}"`],
        ["nice watch", `nice watch -n 5 curl -s "${P}"`],
        ["curl -sg glob (was silent before R14a.2)", `curl -sg ${G}`],
      ]) {
        const { r, st } = once(cmd, { spent: 0 });
        assertDecision(r, "deny", `${label}: denied within the limit`);
        assert(r.message === M_NOTPLAIN && st.spent === 0, `${label}: M_NOTPLAIN, nothing counted, read ${JSON.stringify(st)}`, r);
      }
      const { r, st } = once(`curl -s "${P}" | python3 -m json.tool`, { spent: 0 });
      assert(r.raw === "" && st.spent === 50, `curl piped into python3 -m json.tool: silent, counted 50, read ${JSON.stringify(st)}`, r);
    },
  },
  {
    id: "X1-rc0-keepalive-socket",
    desc: "EXIT (P2): rc 0 and the decision on stdout while a real keep-alive socket is open in the guard's process at exit",
    fn() {
      const d = mkdtempSync(join(tmpdir(), "sc-guard-p2-"));
      mkdirSync(join(d, "revxl", "sessions"), { recursive: true });   // the guard's session folder, SC_REVXL_HOME = d/revxl
      writeFileSync(join(d, "revxl", "sessions", "socialcrawl-p2.json"), JSON.stringify({ balance: 800, spent: 190 }));
      const pre = join(d, "keepalive.mjs");
      writeFileSync(pre, "const r = await fetch(process.env.P2_URL);\nawait r.text();\n");
      const drv = join(d, "driver.mjs");
      writeFileSync(
        drv,
        `import http from "node:http";\n` +
          `import { spawn } from "node:child_process";\n` +
          `let conns = 0, keep = false;\n` +
          `const server = http.createServer((req, res) => { keep = /keep-alive/i.test(req.headers.connection || ""); res.end("ok"); });\n` +
          `server.keepAliveTimeout = 60000;\n` +
          `server.on("connection", () => conns++);\n` +
          `server.listen(0, "127.0.0.1", () => {\n` +
          `  const env = { ...process.env, P2_URL: "http://127.0.0.1:" + server.address().port + "/", NO_PROXY: "127.0.0.1", HOME: ${JSON.stringify(d)}, USERPROFILE: ${JSON.stringify(d)}, SC_REVXL_HOME: ${JSON.stringify(join(d, "revxl"))}, TEMP: ${JSON.stringify(d)}, TMP: ${JSON.stringify(d)}, TMPDIR: ${JSON.stringify(d)} };\n` +
          `  delete env.CLAUDE_CODE_SESSION_ATTENDED;\n` +
          `  const c = spawn(process.execPath, ["--import", ${JSON.stringify(pathToFileURL(pre).href)}, ${JSON.stringify(GUARD)}], { env, stdio: ["pipe", "pipe", "pipe"] });\n` +
          `  let out = "", err = "";\n` +
          `  c.stdout.on("data", (b) => (out += b));\n` +
          `  c.stderr.on("data", (b) => (err += b));\n` +
          `  c.on("exit", (code) => { process.stdout.write(JSON.stringify({ code, out, err, conns, keep })); server.closeAllConnections(); server.close(); });\n` +
          `  c.stdin.end(${JSON.stringify(JSON.stringify({ session_id: "p2", hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: { command: FLAT } }))});\n` +
          `});\n`
      );
      const r = spawnSync(process.execPath, [drv], { encoding: "utf8", timeout: 60000 });
      const bf = join(d, "revxl", "socialcrawl-budget.json");
      rmSync(d, { recursive: true, force: true });
      let j = null;
      try { j = JSON.parse(String(r.stdout || "")); } catch {}
      assert(j !== null, `the driver reported nothing: ${String(r.stderr || "").slice(0, 300)}`);
      assert(j.conns === 1 && j.keep, `a real keep-alive connection was opened (connections ${j.conns}, keep-alive ${j.keep}); child stderr: ${j.err.slice(0, 200)}`);
      assert(j.code === 0, `the guard exited ${j.code}, wanted 0; stderr: ${j.err.slice(0, 300)}`);
      let out = null;
      try { out = JSON.parse(j.out); } catch {}
      // spent 190 + 50 is past the 200 limit (D28): the deny is the decision that must reach stdout.
      assert(out && out.hookSpecificOutput && out.hookSpecificOutput.permissionDecision === "deny" &&
        out.systemMessage === mLimit({ spent: 190, worst: 50, limit: LIMIT, src: srcAuto(BALANCE), bf }),
        `the decision reached stdout, read ${JSON.stringify(j.out).slice(0, 400)}`);
    },
  },
  {
    id: "X2-no-flat-price-wording-gone",
    desc: "X3 (R10 carry; D28): web/extract ('A flat 5 credits') is counted at its flat 5, never as a no-flat-price call counted at 0, and the blanket responseDetermined flag and the 'no flat price' text are gone from credit-guard.mjs",
    fn() {
      const r = run(`curl -s "${V1}web/extract?url=https://x.test"`, { balance: null });
      assert(r.raw === "" && r.state && r.state.spent === 5, `web/extract is counted at its flat 5, read ${r.decision} / ${r.stateRaw}`, r);
      assertNoMatch(r, /no flat price/i, "web/extract is labelled 'A flat 5 credits'");
      const src = readFileSync(GUARD, "utf8");
      assert(!/responseDetermined/.test(src), "no responseDetermined flag remains in credit-guard.mjs");
      assert(!/no flat price/.test(src), "no 'no flat price' message text remains in credit-guard.mjs");
    },
  },
  {
    id: "M13-monitors-free-per-call",
    desc: "MONITORS (R18-7, Q-h): every /v1/monitors call (list, get, create, update, delete, runs, timeseries, export) is priced 0 per call, so a plain one passes silently, counts nothing and is not logged, attended or unattended, even with no balance read; a mention is denied with M_NOTPLAIN (D28); cohorts and cohort-queries are unpriced: counted 0 and passed (D28a)",
    fn() {
      const M = `${V1}monitors`;
      const rows = [];
      for (const [label, cmd] of [
        ["GET list", `curl -s "${M}"`],
        ["GET one", `curl -s "${M}/mon_1"`],
        ["GET runs", `curl -s "${M}/mon_1/runs"`],
        ["GET timeseries", `curl -s "${M}/mon_1/timeseries?metric=x"`],
        ["GET export", `curl -s "${M}/mon_1/export"`],
        ["POST create", `curl -s -X POST "${M}" -H "content-type: application/json" -d '{"recipe":"x","cadence":"daily"}'`],
        ["PATCH pause", `curl -s -X PATCH "${M}/mon_1" -d '{"paused":true}'`],
        ["DELETE", `curl -s -X DELETE "${M}/mon_1"`],
      ]) {
        for (const [who, opts] of [["attended", {}], ["unattended", UNATTENDED], ["attended, no balance", { balance: null }]]) {
          const s = session(opts.balance === null ? { balance: null } : {});
          if (opts.balance !== null) s.seed({ spent: 190 });
          const before = s.stateRaw();
          const r = s.run(cmd, opts);
          rows.push(`    ${`${label}, ${who}`.padEnd(44)} ${String(r.decision)} state ${s.stateRaw() === before ? "unchanged" : s.stateRaw()} log ${s.logLines().length}`);
          assert(r.exit === 0 && r.raw === "" && s.stateRaw() === before && s.logLines().length === 0,
            `${label}, ${who}: a silent pass that counts nothing and logs nothing, read ${r.decision} / ${s.stateRaw()} / ${JSON.stringify(s.logLines())}`, r);
          s.cleanup();
        }
      }
      const mention = run(`echo '${M}/mon_1/runs'`, { seedState: { spent: 0 } });
      assertDecision(mention, "deny", "a mention of a monitors URL is not a plain curl");
      assert(mention.message === M_NOTPLAIN && mention.state.spent === 0, `M_NOTPLAIN, nothing counted, read ${mention.message}`, mention);
      for (const p of ["cohorts", "cohorts/c1/queries", "cohort-queries/q1/results"]) {
        const r = run(`curl -s "${V1}${p}"`, { seedState: { spent: 0 } });
        assert(r.raw === "" && r.state.spent === 0, `${p}: unpriced, counted 0 and passed, read ${r.decision} / ${r.stateRaw}`, r);
      }
      console.log(rows.join("\n"));
    },
  },
];
