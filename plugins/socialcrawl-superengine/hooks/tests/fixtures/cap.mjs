/*
 * R14a — the silent session cap: the decision logic of hooks/credit-guard.mjs.
 *
 * Under min(500, 25% of the balance) nothing is emitted and the command's worst case is
 * committed; a command that crosses the next cap step asks once; the can't-count calls ask every
 * time, and so does every command that is not a plain curl (R14a.2, the NOT A PLAIN CURL ask:
 * the loop and shell-variable asks are folded into it). Only a call that runs is counted (Joe, P1): an ask parks the worst case as pending
 * under sha256(command), the PostToolUse / PostToolUseFailure run commits it, and an unattended
 * deny is never counted and never pending.
 *
 * Synchronous (P26), every guard run in its own seeded session (P21): balance 800 -> cap 200,
 * unless a fixture says otherwise; the balance-unknown group is its own fixture. Zero credits,
 * zero network — X1 opens one loopback socket to a server in its own driver process.
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { session, run, V1, HOST, TSCRIPT, GUARD, COSTS, quoted, assert, assertDecision, assertMatch, assertNoMatch } from "../lib.mjs";

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
const sha = (c) => createHash("sha256").update(c).digest("hex");
const pendingOf = (st) => Object.values((st && st.pending) || {}).reduce((a, v) => a + v, 0);
const row = (label, r, st) =>
  `    ${label.padEnd(44)} ${String(r.decision).padEnd(5)} spent=${(st && st.spent) || 0} pending=${pendingOf(st)}`;

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
    desc: "MATRIX: {attended, unattended} x {under cap, first crossing, second crossing, balance 40 -> cap 10, balance 2000 -> cap 500 under it, balance 4000 -> cap 500 (not 1000) crossing} x {flat, metered}",
    fn() {
      const cols = [
        // [column, balance, flat seed/cmd/worst, metered seed/cmd/worst, expected decision (attended)]
        ["under cap", 800, [0, FLAT, 50], [0, METERED, 62], null],
        ["first crossing", 800, [190, FLAT, 50], [190, METERED, 62], "ask"],
        ["second crossing", 800, [390, FLAT, 50], [390, METERED, 62], "ask"],
        ["balance 40 -> cap 10", 40, [6, SMALL, 5], [0, METERED, 62], "ask"],
        // The 500 ceiling (R18-1, Q-c): 2000 and 4000 both give 500, so 490 + 50 crosses at 4000
        // (a 1000 cap would stay silent), and at 2000 190 + 50 and 150 + 62 stay under 500 but cross
        // a 200 step, so a cap of 200 would ask (R18 H8).
        ["balance 2000 -> cap 500, under (200 would cross)", 2000, [190, FLAT, 50], [150, METERED, 62], null],
        ["balance 4000 -> cap 500 (not 1000), crossing", 4000, [490, FLAT, 50], [490, METERED, 62], "ask"],
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
              // Under the cap: silent, committed at once — attended or not.
              assertDecision(r, null, `${label}: under the cap nothing is asked`);
              assert(r.raw === "", `${label}: under the cap nothing is emitted`, r);
              assert(st.spent === spent + worst && pendingOf(st) === 0, `${label}: committed ${worst}, read ${JSON.stringify(st)}`, r);
            } else if (attended) {
              assertDecision(r, "ask", `${label}: a crossing asks`);
              assertMatch(r, new RegExp(`worst case is ~${worst} credits`), `${label}: names the worst case`);
              assertMatch(r, new RegExp(`~${spent} credits are committed`), `${label}: names the committed total`);
              assertMatch(r, new RegExp(`The cap is ${Math.min(500, Math.floor(balance / 4))} credits`), `${label}: names the cap`);
              assertMatch(r, new RegExp(`your ${balance}-credit balance`), `${label}: names the balance`);
              assert(st.spent === spent && st.pending[sha(cmd)] === worst, `${label}: pending ${worst}, nothing committed, read ${JSON.stringify(st)}`, r);
            } else {
              assertDecision(r, "deny", `${label}: unattended, a crossing is denied`);
              assert(st.spent === spent && pendingOf(st) === 0, `${label}: a deny is never counted and never pending, read ${JSON.stringify(st)}`, r);
            }
          }
        }
      }
      console.log(`    ${"cell".padEnd(44)} decision / resulting state\n` + lines.join("\n"));
    },
  },
  {
    id: "M2-commit-semantics",
    desc: "COMMIT (Joe, P1): ask -> no Post -> the next command re-asks; ask -> Post -> silent until the next step; unattended deny -> retry -> deny again",
    fn() {
      // (a) Declined: no Post ever comes, so nothing is counted and the next paid command asks.
      const a = session().seed({ spent: 190 });
      assertDecision(a.run(FLAT), "ask", "(a) the crossing asks");
      assertDecision(a.run(`curl -s "${V1}prism/leads?query=y"`), "ask", "(a) no Post: the next command re-asks");
      assert(a.state().spent === 190, `(a) nothing committed, read ${a.stateRaw()}`);
      a.cleanup();
      // (b) Accepted: the Post run commits 50; the session is past the step, so the next three
      // 50cr commands are silent (290, 340, 390) and the fourth (440) asks at the 400 step.
      const b = session().seed({ spent: 190 });
      assertDecision(b.run(FLAT), "ask", "(b) the crossing asks");
      b.post(FLAT);
      assert(b.state().spent === 240 && pendingOf(b.state()) === 0, `(b) Post committed and cleared, read ${b.stateRaw()}`);
      const next = (n) => `curl -s "${V1}prism/leads?query=n${n}"`;
      for (let n = 1; n <= 3; n++) assertDecision(b.run(next(n)), null, `(b) silent until the next step (call ${n})`);
      assert(b.state().spent === 390, `(b) three silent commits, read ${b.stateRaw()}`);
      assertDecision(b.run(next(4)), "ask", "(b) the next step asks again");
      b.cleanup();
      // (c) Unattended: denied, never counted, so the retry is denied too.
      const c = session().seed({ spent: 190 });
      assertDecision(c.run(FLAT, UNATTENDED), "deny", "(c) unattended crossing is denied");
      assertDecision(c.run(FLAT, UNATTENDED), "deny", "(c) the retry is denied again");
      assert(c.state().spent === 190 && pendingOf(c.state()) === 0, `(c) never counted, never pending, read ${c.stateRaw()}`);
      c.cleanup();
    },
  },
  {
    id: "M3-deny-retry-mutant",
    desc: "COMMIT (P1 killer): a guard that counts the denied command (the pin's commit-before-decide) lets the retry through silently; this build denies it again",
    fn() {
      // The mutant: the unattended branch commits the worst case before denying, as the pin's
      // logic did for every decision. It must go silent on the retry — that is the leak.
      const dir = mkdtempSync(join(tmpdir(), "sc-guard-mutant-"));
      const src = readFileSync(GUARD, "utf8");
      const anchor = "    if (UNATTENDED) {\n";
      assert(src.includes(anchor), "mutation anchor not found in credit-guard.mjs");
      writeFileSync(join(dir, "credit-guard.mjs"), src.replace(anchor, anchor + "      if (st) { st.spent += worst; writeState(st); }\n"));
      copyFileSync(COSTS, join(dir, "costs.json"));
      const mutant = join(dir, "credit-guard.mjs");
      const m = session().seed({ spent: 190 });
      assertDecision(m.run(FLAT, { ...UNATTENDED, guard: mutant }), "deny", "mutant: the first attempt is denied");
      assertDecision(m.run(FLAT, { ...UNATTENDED, guard: mutant }), null, "mutant: the retry slips through silently (the P1 leak)");
      m.cleanup();
      const f = session().seed({ spent: 190 });
      assertDecision(f.run(FLAT, UNATTENDED), "deny", "fix: the first attempt is denied");
      assertDecision(f.run(FLAT, UNATTENDED), "deny", "fix: the retry is denied again");
      f.cleanup();
      rmSync(dir, { recursive: true, force: true });
    },
  },
  {
    id: "M4-cant-count-six",
    desc: "CAN'T-COUNT: transcripts, cohorts, unreadable URLs and per-unit calls with no ceiling ask attended and are denied unattended, even far under the cap; shell-variable URLs, split-quoted URLs and loops now take the not-plain ask (R14a.2)",
    fn() {
      const six = [
        ["transcript", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, 3, /TRANSCRIPT call/],
        ["cohorts (unpriced)", `curl -s "${V1}cohorts?segment=a"`, 0, /UNPRICED endpoint/],
        ["shell-variable URL (not plain)", `H=${HOST}; curl -s "https://$H/v1/prism/creator-vet?handle=a"`, 0, /NOT A PLAIN CURL/],
        ["split-quoted URL (not plain)", `curl -s "${V1}prism/creator-v""et?h=a"`, 50, /NOT A PLAIN CURL/],
        ["unreadable plain URL", `curl -s "${V1}prism/no-such-endpoint?h=a"`, 50, /UNREADABLE endpoint/],
        ["loop (not plain)", `for i in 1 2 3; do curl -s "${V1}amazon/shop?q=$i"; done`, 1, /NOT A PLAIN CURL/],
        ["per-unit, no ceiling", `curl -X POST "${V1}web/batch-scrape" -d '{}'`, 0, /NO computable ceiling/],
      ];
      const lines = [];
      for (const [label, cmd, worst, why] of six) {
        const at = once(cmd, { spent: 0 }, NOLOCAL);
        lines.push(row(`attended / ${label}`, at.r, at.st));
        assertDecision(at.r, "ask", `${label}: attended asks under the cap`);
        assertMatch(at.r, why, `${label}: which ask`);
        assert(at.st.spent === 0 && (worst ? at.st.pending[sha(cmd)] === worst : pendingOf(at.st) === 0),
          `${label}: pending ${worst}, nothing committed, read ${JSON.stringify(at.st)}`, at.r);
        const un = once(cmd, { spent: 0 }, { ...NOLOCAL, env: { ...NOLOCAL.env, ...UNATTENDED.env } });
        lines.push(row(`unattended / ${label}`, un.r, un.st));
        assertDecision(un.r, "deny", `${label}: unattended is denied`);
        assert(!un.st.spent && pendingOf(un.st) === 0, `${label}: a deny is never counted, read ${JSON.stringify(un.st)}`, un.r);
      }
      console.log(`    ${"cell".padEnd(44)} decision / resulting state\n` + lines.join("\n"));
    },
  },
  {
    id: "M5-stated-maximum",
    desc: "CAN'T-COUNT, stated max (Joe 09.28.26): investigate commits its budget or 200, web/sessions 20, economy/imports 20 (R18 H1); jobs, batch-scrape and monitors commit 0 and ask every time",
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
        assertDecision(r, "ask", `${label}: a can't-count call asks`);
        assertMatch(r, /NO computable ceiling/, `${label}: says no ceiling can be computed`);
        if (max) assertMatch(r, new RegExp(`stated maximum, ~${max} credits`), `${label}: names what it commits`);
        s.post(cmd);
        assert(s.state().spent === max && pendingOf(s.state()) === 0, `${label}: commits ${max} once it runs, read ${s.stateRaw()}`);
        assertDecision(s.run(cmd), "ask", `${label}: asks again next time`);
        s.cleanup();
      }
      // Verb-exact: the free GET twin of web/sessions asks (the path-only fallback) but commits nothing.
      const twin = session().seed({ spent: 0 });
      assertDecision(twin.run(`curl -s "${V1}web/sessions"`), "ask", "GET twin still asks");
      assert(pendingOf(twin.state()) === 0, `a twin verb never takes POST's stated maximum, read ${twin.stateRaw()}`);
      twin.cleanup();
      // Checkers X2/X3/X5: investigate commits a budget only as it is certainly sent. A #fragment
      // or an encoded `%26budget=` sends none (200); two budgets commit the larger; `curl -G` is a
      // GET, and any data flag may send a budget again, so a -G call with data commits 200 (an
      // over-count); text glued on after the closing quote changes the value curl sends (200).
      for (const [cmd, max, label] of [
        [`curl -s "${V1}prism/investigate?goal=x#&budget=1"`, 200, "budget in the #fragment"],
        [`curl -s "${V1}prism/investigate?goal=x%26budget=1"`, 200, "budget inside a value (%26)"],
        [`curl -s "${V1}prism/investigate?goal=x&budget=1&budget=150"`, 150, "two budgets"],
        [`curl -sG "${V1}prism/investigate?budget=120" -d goal=x`, 200, "curl -G, budget in the URL, other data (over-count)"],
        [`curl -s -G "${V1}prism/investigate" --data-urlencode goal=x -d budget=150`, 200, "curl -G, budget as data"],
        [`curl -s -G "${V1}prism/investigate?goal=x&budget=1" -d budget=150`, 200, "curl -G, budget in the URL and as data (X5)"],
        [`curl -s "${V1}prism/investigate?goal=x&budget=1"50`, 200, "50 glued after the quote sends budget=150 (X5)"],
      ]) {
        const s = session().seed({ spent: 0 });
        assertDecision(s.run(cmd), "ask", `${label}: asks`);
        s.post(cmd);
        assert(s.state().spent === max && pendingOf(s.state()) === 0, `${label}: commits ${max}, read ${s.stateRaw()}`);
        s.cleanup();
      }
    },
  },
  {
    id: "M6-post-commit",
    desc: "POST: PostToolUse and PostToolUseFailure commit a pending quote once; a non-pending or non-SocialCrawl command is left alone; a silent pass drops a stale pending quote",
    fn() {
      for (const failure of [false, true]) {
        const s = session().seed({ spent: 190 });
        assertDecision(s.run(FLAT), "ask", "the crossing asks");
        const p = s.post(FLAT, { failure });
        assert(p.raw === "" && p.exit === 0, `${failure ? "PostToolUseFailure" : "PostToolUse"} emits nothing, exit 0`, p);
        assert(s.state().spent === 240 && pendingOf(s.state()) === 0, `${failure ? "Failure" : "Post"}: commit + clear, read ${s.stateRaw()}`);
        const again = s.post(FLAT, { failure });
        assert(!again.stateWritten && s.state().spent === 240, `${failure ? "Failure" : "Post"}: a second Post counts nothing, read ${s.stateRaw()}`);
        s.cleanup();
      }
      // A command that passed silently has nothing pending: its Post changes nothing.
      const q = session().seed({ spent: 0 });
      assertDecision(q.run(SMALL), null, "a small call passes silently");
      for (const failure of [false, true]) assert(!q.post(SMALL, { failure }).stateWritten, "a non-pending Post writes nothing");
      assert(q.state().spent === 5, `counted once, in Pre, read ${q.stateRaw()}`);
      // A Post for a command that never touched SocialCrawl takes the fast path.
      assert(!q.post(`ls -la`).stateWritten, "a non-SocialCrawl Post writes nothing");
      q.cleanup();
      // A stale pending quote (an earlier declined ask of this same command) is dropped by the
      // silent pass that commits it in Pre, so its Post cannot count it twice.
      const d = session().seed({ spent: 0, pending: { [sha(FLAT)]: 50 } });
      assertDecision(d.run(FLAT), null, "under the cap the same command now passes");
      d.post(FLAT);
      assert(d.state().spent === 50 && pendingOf(d.state()) === 0, `counted once, not twice, read ${d.stateRaw()}`);
      d.cleanup();
    },
  },
  {
    id: "M7-heredocs",
    desc: "HEREDOCS (Joe 09.28.26, supersedes P4): no heredoc body is masked, so every SocialCrawl URL anywhere in a command is counted, whatever reads the body; a heredoc is never a plain curl, so each asks (R14a.2), and so do a note written with a URL and echo of a URL (mentions ask, a stated LIMIT)",
    fn() {
      const PY = HEREDOC_PY;
      // A heredoc is not plain: it asks every time, parked at the visible one-call figure.
      const counted = once(PY, { spent: 0 });
      assertDecision(counted.r, "ask", "python3 heredoc under the cap asks (not plain)");
      assert(counted.st.spent === 0 && counted.st.pending[sha(PY)] === 5, `python3 heredoc under the cap is parked at 5, read ${JSON.stringify(counted.st)}`, counted.r);
      const asked = once(PY, { spent: 198 });
      assertDecision(asked.r, "ask", "python3 heredoc at a cap step asks");
      assert(asked.st.pending[sha(PY)] === 5, `python3 heredoc is parked at 5, read ${JSON.stringify(asked.st)}`, asked.r);
      const piped = once(`cat <<'EOF' | python3\nimport urllib.request\nurllib.request.urlopen("${V1}amazon/product?asin=B1")\nEOF`, { spent: 0 });
      assert(quoted(piped.st) === 5, `a pipe into an interpreter keeps the body counted, read ${JSON.stringify(piped.st)}`, piped.r);
      // A note written with a URL in it asks, and is counted once it runs: the stated LIMIT, an
      // over-count (Joe 09.28.26; R14a.2: mentions ask, and are denied unattended).
      for (const [label, cmd] of [["cat > notes.md <<'EOF'", HEREDOC_NOTE], ["cat <<'EOF' > notes.md", `cat <<'EOF' > notes.md\nsee ${V1}amazon/product?asin=B1\nEOF`]]) {
        const { r, st } = once(cmd, { spent: 0 });
        assertDecision(r, "ask", `${label} with a URL in the body asks (LIMIT)`);
        assertMatch(r, /NOT A PLAIN CURL/, `${label}: the not-plain ask`);
        assert(st.spent === 0 && st.pending[sha(cmd)] === 5, `${label} with a URL in the body parks 5 (LIMIT), read ${JSON.stringify(st)}`, r);
        const un = once(cmd, { spent: 0 }, UNATTENDED);
        assertDecision(un.r, "deny", `${label}: denied unattended`);
      }
      // Checkers X1 and X4: every mask tried let a body that runs pass at 0 — each of these ran
      // the URL, and each was counted at the pin.
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
        const { r, st } = once(cmd, { spent: 0 });
        assert(quoted(st) === 5, `${label}: the body is counted, read ${JSON.stringify(st)}`, r);
        assertNoMatch(r, /assembled from shell variables/, `${label}: the URL is read, not guessed at`);
      }
      const ECHO = `echo '${V1}amazon/product?asin=B1'`;
      const echo = once(ECHO, { spent: 0 });
      assertDecision(echo.r, "ask", "echo '<URL>' asks (a mention, the stated LIMIT)");
      assert(echo.st.spent === 0 && echo.st.pending[sha(ECHO)] === 5, `echo '<URL>' parks 5 (the stated over-count LIMIT), read ${JSON.stringify(echo.st)}`, echo.r);
    },
  },
  {
    id: "M7b-heredoc-mask-mutant",
    desc: "HEREDOCS (killer): a guard that blanks heredoc bodies again counts the python3 heredoc and the note at 0; this build counts both at 5",
    fn() {
      const dir = mkdtempSync(join(tmpdir(), "sc-guard-mutant-"));
      const src = readFileSync(GUARD, "utf8");
      const anchor = "  const cmd = rawCmd;\n";
      assert(src.includes(anchor), "mutation anchor not found in credit-guard.mjs");
      writeFileSync(join(dir, "credit-guard.mjs"), src.replace(anchor, `  ${blankBodies}\n  const cmd = blankBodies(rawCmd);\n`));
      copyFileSync(COSTS, join(dir, "costs.json"));
      const mutant = join(dir, "credit-guard.mjs");
      for (const [label, cmd] of [["python3 - heredoc", HEREDOC_PY], ["cat > notes.md heredoc", HEREDOC_NOTE]]) {
        const m = once(cmd, { spent: 0 }, { guard: mutant });
        assert(quoted(m.st) === 0, `mutant: ${label} is counted at 0 (the leak M7 catches), read ${JSON.stringify(m.st)}`, m.r);
        const f = once(cmd, { spent: 0 });
        assert(quoted(f.st) === 5, `fix: ${label} is counted at 5, read ${JSON.stringify(f.st)}`, f.r);
      }
      rmSync(dir, { recursive: true, force: true });
    },
  },
  {
    id: "M8-dry-runs",
    desc: "DRY RUNS, re-pointed (R14a.2 ruling (b), supersedes P8): dry_run=1 is counted at its full label price everywhere, declared or not; a plain curl is counted silently, any other shape asks at the same figure",
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
        assert(r.raw === "" && st.spent === want && pendingOf(st) === 0, `${label}: counted ${want} silently, read ${JSON.stringify(st)}`, r);
      }
      // Not plain: the not-plain ask, parked at the same full figure (checkers X2, X5, X11).
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
        assertDecision(r, "ask", `${label}: not plain, so it asks`);
        assertMatch(r, /NOT A PLAIN CURL/, `${label}: the not-plain ask`);
        assert(st.spent === 0 && quoted(st) === 56, `${label}: parked at 56 in full, read ${JSON.stringify(st)}`, r);
      }
    },
  },
  {
    id: "M9-per-unit-post-stats",
    desc: "PER-UNIT (P3, Joe 09.28.26): post-stats with 100 Instagram URLs at cap 200 asks, counted at its label worst case 500: a stated over-count (the batch holds 200 at 2 per Instagram URL)",
    fn() {
      const urls = Array.from({ length: 100 }, (_, i) => `"https://www.instagram.com/p/x${i}/"`).join(",");
      const cmd = `curl -X POST "${V1}prism/post-stats" -H "Content-Type: application/json" -d '{"urls":[${urls}]}'`;
      const { r, st } = once(cmd, { spent: 0 });
      assertDecision(r, "ask", "100 URLs at cap 200 asks");
      assertMatch(r, /worst case is ~500 credits/, "the label worst case, 500: a stated over-count (the batch holds 200)");
      assert(st.pending[sha(cmd)] === 500, `parked at 500, read ${JSON.stringify(st)}`, r);
    },
  },
  {
    id: "M10-balance-unknown",
    desc: "BALANCE UNKNOWN (P5): no cached balance, or one that is not an integer >= 4, means no cap — the first paid call asks, saying the balance couldn't be read",
    fn() {
      const first = session({ balance: null });
      const r = first.run(`curl -s "${V1}amazon/shop?q=a"`);
      assertDecision(r, "ask", "the first paid call asks");
      assertMatch(r, /couldn't read your balance/, "says the balance couldn't be read");
      first.cleanup();
      for (const balance of [0, 3, "1000", -5, 999.5]) {
        const { r: b } = once(`curl -s "${V1}amazon/shop?q=a"`, { spent: 0 }, { balance });
        assertDecision(b, "ask", `balance ${JSON.stringify(balance)}: no cap, so it asks`);
        assertMatch(b, /couldn't read your balance/, `balance ${JSON.stringify(balance)}: treated as unreadable`);
      }
      const { r: four } = once(`curl -s "${V1}amazon/shop?q=a"`, { spent: 0 }, { balance: 4 });
      assertMatch(four, /The cap is 1 credits/, "balance 4 is the smallest valid one: cap floor(0.25 x 4) = 1");
      const eight = session({ balance: 8 }).seed({ spent: 0 });
      assertDecision(eight.run(`curl -s "${V1}amazon/shop?q=a"`), null, "balance 8, cap 2: 1 is under it");
      assertDecision(eight.run(`curl -s "${V1}amazon/shop?q=b"`), "ask", "balance 8, cap 2: 2 reaches it");
      eight.cleanup();
    },
  },
  {
    id: "M11-state-files",
    desc: "STATE: a corrupt state file and an old {spent} file both read, never crash, and fail safe (no balance -> ask)",
    fn() {
      const c = session();
      writeFileSync(c.stateFile, "{not json");
      const r = c.run(`curl -s "${V1}amazon/shop?q=a"`);
      assert(r.exit === 0, "rc 0 on a corrupt state file", r);
      assertDecision(r, "ask", "a corrupt file has no balance: the call asks");
      assert(c.state() && c.state().spent === 0 && pendingOf(c.state()) === 1, `rewritten as valid state, read ${c.stateRaw()}`);
      c.cleanup();
      const old = session({ balance: null }).seed({ spent: 12 });
      const o = old.run(`curl -s "${V1}amazon/shop?q=a"`);
      assertDecision(o, "ask", "an old {spent} file has no balance: the call asks");
      assertMatch(o, /~12 credits are committed/, "the old file's spent is still read");
      assert(old.state().spent === 12 && pendingOf(old.state()) === 1, `spent kept, the ask pending, read ${old.stateRaw()}`);
      old.cleanup();
    },
  },
  {
    id: "M12-repeats-under-the-cap",
    desc: "REPEATS, re-pointed (R14a.2): a curl glob, a loop in interpreter code, find -exec, xargs/watch behind a prefix command and curl -g each take the not-plain ask under the cap, parked at the one-call figure; curl piped into python3 -m json.tool is tidy output, counted silently",
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
        assertDecision(r, "ask", `${label}: asks under the cap`);
        assertMatch(r, /NOT A PLAIN CURL/, `${label}: the not-plain ask`);
        assert(st.spent === 0 && pendingOf(st) === 50, `${label}: parked at the one-call 50, read ${JSON.stringify(st)}`, r);
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
      writeFileSync(join(d, "sc-credit-guard-p2.json"), JSON.stringify({ balance: 800, spent: 190 }));
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
          `  const env = { ...process.env, P2_URL: "http://127.0.0.1:" + server.address().port + "/", NO_PROXY: "127.0.0.1", TEMP: ${JSON.stringify(d)}, TMP: ${JSON.stringify(d)}, TMPDIR: ${JSON.stringify(d)} };\n` +
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
      rmSync(d, { recursive: true, force: true });
      let j = null;
      try { j = JSON.parse(String(r.stdout || "")); } catch {}
      assert(j !== null, `the driver reported nothing: ${String(r.stderr || "").slice(0, 300)}`);
      assert(j.conns === 1 && j.keep, `a real keep-alive connection was opened (connections ${j.conns}, keep-alive ${j.keep}); child stderr: ${j.err.slice(0, 200)}`);
      assert(j.code === 0, `the guard exited ${j.code}, wanted 0; stderr: ${j.err.slice(0, 300)}`);
      let out = null;
      try { out = JSON.parse(j.out); } catch {}
      assert(out && out.hookSpecificOutput && out.hookSpecificOutput.permissionDecision === "ask",
        `the decision reached stdout, read ${JSON.stringify(j.out).slice(0, 200)}`);
    },
  },
  {
    id: "X2-no-flat-price-wording-gone",
    desc: "X3 (R10 carry): no guard message calls a flat-labelled entry 'no flat price' (web/extract, 'A flat 5 credits'), and the blanket responseDetermined flag is gone",
    fn() {
      const r = run(`curl -s "${V1}web/extract?url=https://x.test"`, { balance: null });
      assertDecision(r, "ask", "balance unknown, so the call asks and its message can be read");
      assertNoMatch(r, /no flat price/i, "web/extract is labelled 'A flat 5 credits'");
      const src = readFileSync(GUARD, "utf8");
      assert(!/responseDetermined/.test(src), "no responseDetermined flag remains in credit-guard.mjs");
      assert(!/no flat price/.test(src), "no 'no flat price' message text remains in credit-guard.mjs");
    },
  },
  {
    id: "M13-monitors-free-per-call",
    desc: "MONITORS (R18-7, Q-h): every /v1/monitors call (list, get, create, update, delete, runs, timeseries, export) is priced 0 per call, so a plain one passes silently, counts nothing and is not logged, attended or unattended, even with no balance read; a mention still takes the not-plain ask at 0; cohorts and cohort-queries still ask (unpriced)",
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
      assertDecision(mention, "ask", "a mention of a monitors URL is not a plain curl");
      assertMatch(mention, /Visible counted total: ~0 credits/, "and counts 0");
      for (const p of ["cohorts", "cohorts/c1/queries", "cohort-queries/q1/results"]) {
        const r = run(`curl -s "${V1}${p}"`, { seedState: { spent: 0 } });
        assertDecision(r, "ask", `${p}: cohorts still ask`);
        assertMatch(r, /UNPRICED/, `${p}: as unpriced`);
      }
      console.log(rows.join("\n"));
    },
  },
];
