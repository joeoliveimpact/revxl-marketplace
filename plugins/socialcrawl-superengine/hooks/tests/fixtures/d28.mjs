/*
 * Phase 3a (0.4.0) — D28/D28a: the guard never asks, the hard limit, the budget file, routine `allow`,
 * and the Post run removed. One fixture per item of List A in
 * "Phase 3a Checker Fixtures - Both Lists - 10.09.26.md" (A10 and A11 share one: an `allow` that must
 * appear in one place and nowhere else). Each was run red against the 0.3.1 guard (2cb14b1) before
 * it was run green here. The messages are checked whole, by equality (lib.mjs builds them from §c).
 *
 * Synchronous, every guard run in its own temp SC_REVXL_HOME (lib.mjs session()). Zero credits, zero
 * network: a balance read is answered by fake-fetch.mjs, and every other run has no key.
 */
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  session, V1, TSCRIPT, GUARD, COSTS, BALANCE, LIMIT, T, USE_BASH, M_NOTPLAIN, M_NOTBASH, M_LOST, mError, mLimit,
  ROUTINE, ROUTINES_ON, SRC_SESSION, SRC_FALLBACK, srcAuto, today, assert, assertDecision,
} from "../lib.mjs";
import { stateFault } from "./balance.mjs";

const UN = { CLAUDE_CODE_SESSION_ATTENDED: "0" };
const NOLOCAL = { GROQ_API_KEY: "", PATH: "" };
const HOOKS_JSON = resolve(dirname(GUARD), "hooks.json");
const DOCS = "https://docs." + "social" + "crawl" + ".dev";
const P = `${V1}prism/leads?query=x`;
const P50 = `curl -s "${P}"`;                                     // plain, flat 50
const P1 = `curl -s "${V1}amazon/shop?q=a"`;                      // plain, flat 1
const P200 = `curl -s "${V1}prism/share-of-voice?brands=a,b"`;    // plain, 200
const P500 = `curl -X POST "${V1}prism/post-stats" -d '{}'`;     // plain, 500 (the label worst case)
const FREE = `curl -s "${V1}credits/balance"`;                    // plain, free
const bal = (v) => ({ body: { data: { balance: v } } });
const KINDS = ["not-plain", "lost", "over-limit", "under-cap", "error"];
const FIELDS = ["ts", "session_id", "decision", "kind", "paths", "cmdWorst", "committed", "cap"];
const RON = { budget: ROUTINES_ON, env: ROUTINE };

/** A session seeded at `spent` (balance 800 unless `balance: null`), with an optional budget and day file. */
function open(o = {}) {
  const s = session(o.balance === null ? { balance: null } : {});
  s.seed(o.seed || { spent: 0 });
  if (o.budget !== undefined) s.budget(o.budget);
  if (o.day !== undefined) s.day(o.day);
  return s;
}
/** One run in a fresh session built by open(o); returns the result with the state, log and budget path. */
function once(cmd, o = {}) {
  const s = open(o);
  const r = s.run(cmd, { env: o.env, extra: o.extra, fetch: o.fetch, node: o.node, guard: o.guard, event: o.event });
  r.state = s.state();
  r.log = s.logLines();
  r.fetchCount = s.fetches().length;
  r.files = readdirSync(s.revxl).sort();
  s.cleanup();
  return r;
}
const spentOf = (r) => (r.state && typeof r.state.spent === "number" ? r.state.spent : 0);
/** The call record in a revxl folder (3d), its lines parsed; [] when there is none. */
const callRecord = (revxl) => { try { return readFileSync(join(revxl, "socialcrawl-calls.jsonl"), "utf8").split(String.fromCharCode(10)).filter(Boolean).map((l) => JSON.parse(l)); } catch { return []; } };
/** A preload that logs every readFileSync of a path under SPY_DIR into SPY_LOG (the guard's own reads). */
function readSpy() {
  const d = mkdtempSync(join(tmpdir(), "sc-p3a-spy-"));
  const f = join(d, "read-spy.mjs");
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `import { resolve } from "node:path";\n` +
    `const fs = createRequire(import.meta.url)("node:fs");\n` +
    `const read = fs.readFileSync, append = fs.appendFileSync;\n` +
    `const dir = resolve(process.env.SPY_DIR).toLowerCase();\n` +
    `fs.readFileSync = (p, ...a) => { if (typeof p === "string" && resolve(p).toLowerCase().startsWith(dir)) append(process.env.SPY_LOG, p + "\\n"); return read(p, ...a); };\n` +
    `syncBuiltinESMExports();\n`);
  return { url: pathToFileURL(f).href, dir: d };
}
/** A preload that makes a save of SAVE_FAIL throw EBUSY (the file left whole), as balance.mjs stateFault "busy". */
function saveThrows() {
  const d = mkdtempSync(join(tmpdir(), "sc-p3a-save-"));
  const f = join(d, "save-throws.mjs");
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `import { resolve } from "node:path";\n` +
    `const fs = createRequire(import.meta.url)("node:fs");\n` +
    `const write = fs.writeFileSync;\n` +
    `fs.writeFileSync = (p, ...a) => { if (typeof p === "string" && resolve(p).toLowerCase() === resolve(process.env.SAVE_FAIL).toLowerCase()) throw Object.assign(new Error("EBUSY, forced"), { code: "EBUSY" }); return write(p, ...a); };\n` +
    `syncBuiltinESMExports();\n`);
  return { url: pathToFileURL(f).href, dir: d };
}
/** A preload that makes path.join throw on a "sessions" segment: outside the guard's inner try. */
function outerThrows() {
  const d = mkdtempSync(join(tmpdir(), "sc-p3a-throw-"));
  const f = join(d, "outer-throws.mjs");
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `const path = createRequire(import.meta.url)("node:path");\n` +
    `const real = path.join;\n` +
    `path.join = (...a) => { if (a.includes("sessions")) throw new Error("forced"); return real(...a); };\n` +
    `syncBuiltinESMExports();\n`);
  return { url: pathToFileURL(f).href, dir: d };
}
/** A guard copy whose costs.json has _unpriced: 5: the cost lookup throws inside the inner try (balance.mjs's inner throw). */
function innerThrows() {
  const d = mkdtempSync(join(tmpdir(), "sc-p3f-inner-"));
  copyFileSync(GUARD, join(d, "credit-guard.mjs"));
  writeFileSync(join(d, "costs.json"), JSON.stringify({ ...JSON.parse(readFileSync(COSTS, "utf8")), _unpriced: 5 }));
  return { file: join(d, "credit-guard.mjs"), dir: d };
}
/** A mutant copy of the guard (with costs.json beside it): `anchor` must occur exactly once. */
function mutant(name, anchor, replacement) {
  const src = readFileSync(GUARD, "utf8");
  assert(src.split(anchor).length === 2, `mutant ${name}: its anchor must occur exactly once in credit-guard.mjs`);
  const d = mkdtempSync(join(tmpdir(), `sc-p3a-mut-${name}-`));
  writeFileSync(join(d, "credit-guard.mjs"), src.replace(anchor, replacement));
  copyFileSync(COSTS, join(d, "costs.json"));
  return { file: join(d, "credit-guard.mjs"), dir: d };
}

export default [
  {
    id: "P3a-A1-no-ask-anywhere",
    desc: "A1/A23: credit-guard.mjs holds no \"ask\" decision literal and no line with the word ask/asks/asked, nor does hooks.json; driven attended and unattended through a loop, a pipe, PowerShell (paid and free), a transcript, cohorts, an unresolved literal path, GET web/monitors, a limit overrun, a null balance, a lost total and a routine, no run returns ask",
    fn() {
      const src = readFileSync(GUARD, "utf8");
      assert(!/["'`]ask["'`]/.test(src), "no \"ask\" literal in credit-guard.mjs");
      for (const [name, text] of [["credit-guard.mjs", src], ["hooks.json", readFileSync(HOOKS_JSON, "utf8")]]) {
        const lines = text.split("\n").map((l, i) => [i + 1, l]).filter(([, l]) => /\b(?:ask|asks|asked)\b/i.test(l));
        assert(!lines.length, `${name}: no line with ask/asks/asked, read ${JSON.stringify(lines.slice(0, 3))}`);
      }
      const shapes = [
        ["a loop", `for i in 1 2; do curl -s "${P}"; done`, {}],
        ["a pipe into a program", `curl -s "${P}" | sh`, {}],
        ["PowerShell, paid", P50, { extra: { tool_name: "PowerShell" } }],
        ["PowerShell, free", FREE, { extra: { tool_name: "PowerShell" } }],
        ["a transcript", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, { env: NOLOCAL }],
        ["cohorts", `curl -s "${V1}cohorts?segment=a"`, {}],
        ["an unresolved literal path", `curl -s "${V1}prism/no-such-endpoint?h=a"`, {}],
        ["GET web/monitors", `curl -s "${V1}web/monitors"`, {}],
        ["a limit overrun (190 + 50)", P50, { seed: { spent: 190 } }],
        ["a null balance", P50, { balance: null }],
        ["a lost total", P50, { seed: { spent: 0, lost: true } }],
        ["a routine, in budget", P50, RON],
      ];
      const seen = [];
      for (const [label, cmd, o] of shapes) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const r = once(cmd, { ...o, env: { ...(o.env || {}), ...env } });
          seen.push(`${label}/${who}=${r.decision || "pass"}`);
          assert(r.decision !== "ask" && r.exit === 0, `${label}, ${who}: never ask, read ${r.decision}`, r);
        }
      }
      console.log(`    ${seen.join(", ")}`);
    },
  },
  {
    id: "P3a-A2-not-plain-denied-before-any-io",
    desc: "A2: a command that is not plain (a mention with a visible worst case of 0 included) and any SocialCrawl command through a tool other than Bash (a free credits/balance included) is denied with exactly M_NOTPLAIN / M_NOTBASH, attended and unattended; a fresh SC_REVXL_HOME stays empty attended (only the unattended log appears unattended), no state, budget or day file is read (a read spy sees none, where a plain call's run reads the state and the budget), a garbage state file is left byte-identical, and no balance is fetched",
    fn() {
      const spy = readSpy();
      const cases = [
        ["echo '<URL>'", `echo '${P}'`, undefined, M_NOTPLAIN],
        ["a mention with no /v1/ URL (worst 0)", `echo see ${DOCS}/quickstart`, undefined, M_NOTPLAIN],
        ["a loop over credits/balance (worst 0)", `for i in 1 2; do curl -s "${V1}credits/balance"; done`, undefined, M_NOTPLAIN],
        ["PowerShell, a plain-shaped paid curl", P50, { tool_name: "PowerShell" }, M_NOTBASH],
        ["PowerShell, credits/balance (worst 0)", FREE, { tool_name: "PowerShell" }, M_NOTBASH],
        ["tool_name null", P50, { tool_name: null }, M_NOTBASH],
      ];
      const rows = [];
      for (const [label, cmd, extra, want] of cases) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const s = session({ balance: null });
          const home = join(s.dir, "fresh-revxl");
          mkdirSync(home);
          const log = join(s.dir, "spy.log");
          writeFileSync(log, "");
          const r = s.run(cmd, { extra, env: { ...env, SC_REVXL_HOME: home, SPY_DIR: home, SPY_LOG: log }, node: ["--import", spy.url], fetch: [bal(800)] });
          const files = readdirSync(home);
          const reads = readFileSync(log, "utf8").split("\n").filter(Boolean);
          rows.push(`    ${`${label}, ${who}`.padEnd(54)} ${r.decision} files ${JSON.stringify(files)} reads ${reads.length} fetches ${s.fetches().length}`);
          assert(r.decision === "deny" && r.message === want, `${label}, ${who}: exactly the deny, read ${r.decision} / ${r.message.slice(0, 160)}`, r);
          assert(JSON.stringify(files) === (who === "attended" ? "[]" : JSON.stringify(["credit-guard-unattended.jsonl"])), `${label}, ${who}: SC_REVXL_HOME gains no session, budget or day file, read ${JSON.stringify(files)}`);
          assert(reads.length === 0 && s.fetches().length === 0, `${label}, ${who}: nothing under SC_REVXL_HOME is read and no balance is fetched, read ${JSON.stringify(reads)} / ${s.fetches().length}`);
          s.cleanup();
        }
      }
      // A garbage state file, a budget and a day file beside it: the deny leaves all three as they were.
      const g = open({ budget: { sessionBudget: 1 }, day: "{not json" });
      writeFileSync(g.stateFile, "{garbage");
      const before = [g.stateRaw(), readFileSync(g.bf, "utf8"), readFileSync(g.df, "utf8")];
      const rg = g.run(`echo '${P}'`, { env: ROUTINE });
      assert(rg.message === M_NOTPLAIN && JSON.stringify([g.stateRaw(), readFileSync(g.bf, "utf8"), readFileSync(g.df, "utf8")]) === JSON.stringify(before) && !existsSync(`${g.stateFile}.lock`),
        `a garbage state file is left byte-identical and no lock is made, read ${g.stateRaw()}`, rg);
      g.cleanup();
      // Control: the spy does see a plain paid call read the state file and the budget file.
      const c = session();
      const clog = join(c.dir, "spy.log");
      writeFileSync(clog, "");
      c.run(P50, { env: { SPY_DIR: c.revxl, SPY_LOG: clog }, node: ["--import", spy.url] });
      const creads = readFileSync(clog, "utf8").split("\n").filter(Boolean).map((p) => p.split(/[\\/]/).pop());
      assert(creads.includes(`socialcrawl-${c.sid}.json`) && creads.includes("socialcrawl-budget.json"), `control: a plain call's reads are seen, read ${JSON.stringify(creads)}`);
      c.cleanup();
      rmSync(spy.dir, { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3a-A3-uncountable-classes-counted",
    desc: "A3 (D28a): a transcript, an unresolved literal path (each unresolved call at UNRESOLVED_FLOOR, 50), an uncomputable call with a stated maximum (web/sessions 20, investigate 200 or its budget) and one without (prism/jobs 0), and an unpriced call (cohorts 0) each pass within the limit and are counted at exactly that figure, attended and unattended, from spent 0 and from spent 100",
    fn() {
      const cases = [
        ["a YouTube transcript", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, 3],
        ["a TikTok transcript", `curl -s "${V1}tiktok/post/${TSCRIPT}?url=x"`, 10],
        ["one unresolved call", `curl -s "${V1}prism/no-such-endpoint?h=a"`, 50],
        ["two unresolved calls", `curl -s "${V1}prism/no-such-a?h=a" && curl -s "${V1}prism/no-such-b?h=b"`, 100],
        ["web/sessions (stated 20)", `curl -X POST "${V1}web/sessions" -d '{}'`, 20],
        ["investigate, no budget (stated 200)", `curl -s "${V1}prism/investigate?goal=x"`, 200],
        ["investigate budget=40", `curl -s "${V1}prism/investigate?goal=x&budget=40"`, 40],
        ["prism/jobs (no stated maximum)", `curl -X POST "${V1}prism/jobs" -d '{}'`, 0],
        ["cohorts (unpriced)", `curl -s "${V1}cohorts?segment=a"`, 0],
        ["a transcript and a flat 1 in one command", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a" && curl -s "${V1}amazon/shop?q=a"`, 4],
      ];
      for (const [label, cmd, worst] of cases) {
        for (const start of [0, 100]) {
          if (start + worst > LIMIT) continue;
          for (const [who, env] of [["attended", NOLOCAL], ["unattended", { ...NOLOCAL, ...UN }]]) {
            const r = once(cmd, { seed: { spent: start }, env });
            assert(r.raw === "" && r.exit === 0 && spentOf(r) === start + worst, `${label}, from ${start}, ${who}: passes and counts ${worst}, read ${r.decision} / ${JSON.stringify(r.state)}`, r);
          }
        }
      }
    },
  },
  {
    id: "P3a-A4-free-get-twins-pass",
    desc: "A4 (D28a): the path-only-fallback free GET twins GET prism/jobs, GET web/monitors and GET web/sessions pass silently and count 0, attended and unattended, and still pass at a committed total of exactly the limit",
    fn() {
      for (const p of ["prism/jobs", "web/monitors", "web/sessions"]) {
        for (const start of [0, LIMIT]) {
          for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
            const r = once(`curl -s "${V1}${p}"`, { seed: { spent: start }, env });
            assert(r.raw === "" && spentOf(r) === start, `GET ${p}, at ${start}, ${who}: passes, counted 0, read ${r.decision} / ${JSON.stringify(r.state)}`, r);
          }
        }
      }
    },
  },
  {
    id: "P3a-A5-boundary",
    desc: "A5: at a limit of 200 (the automatic cap of an 800 balance, and a session budget of 200), spent 0 + worst 200 passes and is committed, and spent 1 + worst 200 is denied with exactly M_LIMIT naming 1, 200, 200, the limit's source and the Budget pane",
    fn() {
      for (const [label, budget, src] of [["the automatic cap", undefined, srcAuto(BALANCE)], ["a session budget of 200", { sessionBudget: 200 }, SRC_SESSION]]) {
        const ok = once(P200, { seed: { spent: 0 }, budget });
        assert(ok.raw === "" && spentOf(ok) === 200, `${label}: 0 + 200 reaches the limit exactly and passes, read ${ok.decision} / ${JSON.stringify(ok.state)}`, ok);
        const s = open({ seed: { spent: 1 }, budget });
        const r = s.run(P200);
        const st = s.state();
        s.cleanup();
        assert(r.decision === "deny" && r.message === mLimit({ spent: 1, worst: 200, limit: 200, src, kind: "session", bf: r.bf }) && st.spent === 1,
          `${label}: 1 + 200 is past it, exactly M_LIMIT, nothing counted, read ${r.message}`, r);
      }
    },
  },
  {
    id: "P3a-A6-budget-validation",
    desc: "A6: a sessionBudget of 0, -5, \"500\", 1.5, 1e999 (Infinity), null, true or 20001, or none, is not a budget: a 500cr call is denied with M_LIMIT from the automatic cap; a valid 300 is the limit (M_LIMIT names your session budget) and a valid 20000 passes it; with a valid budget no balance is fetched even when none is cached (the limit is 20000 with the balance unreadable)",
    fn() {
      for (const [label, text] of [["0", '{"sessionBudget":0}'], ["-5", '{"sessionBudget":-5}'], ['"500"', '{"sessionBudget":"500"}'], ["1.5", '{"sessionBudget":1.5}'],
        ["1e999", '{"sessionBudget":1e999}'], ["null", '{"sessionBudget":null}'], ["true", '{"sessionBudget":true}'], ["20001", '{"sessionBudget":20001}'], ["missing", "{}"]]) {
        const r = once(P500, { budget: text });
        assert(r.decision === "deny" && r.message === mLimit({ spent: 0, worst: 500, limit: LIMIT, src: srcAuto(BALANCE), bf: r.bf }),
          `sessionBudget ${label}: not a budget, so the automatic cap, read ${r.message}`, r);
      }
      const v300 = once(P500, { budget: { sessionBudget: 300 } });
      assert(v300.message === mLimit({ spent: 0, worst: 500, limit: 300, src: SRC_SESSION, bf: v300.bf }), `sessionBudget 300: the limit, read ${v300.message}`, v300);
      const v20k = once(P500, { budget: { sessionBudget: 20000 } });
      assert(v20k.raw === "" && spentOf(v20k) === 500, `sessionBudget 20000: a 500cr call passes, read ${v20k.decision} / ${JSON.stringify(v20k.state)}`, v20k);
      // A valid budget needs no balance: none cached, a readable one on offer, and nothing is fetched.
      const nb = once(P500, { balance: null, budget: { sessionBudget: 20000 }, fetch: [bal(800)] });
      assert(nb.raw === "" && spentOf(nb) === 500 && nb.fetchCount === 0, `a valid budget, no balance cached: passes with no fetch, read ${nb.decision} / ${nb.fetchCount}`, nb);
      const over = once(P500, { balance: null, seed: { spent: 19600 }, budget: { sessionBudget: 20000 }, fetch: [bal(800)] });
      assert(over.message === mLimit({ spent: 19600, worst: 500, limit: 20000, src: SRC_SESSION, bf: over.bf }) && over.fetchCount === 0,
        `a valid budget, no balance: the limit is 20000 and nothing is fetched, read ${over.message} / ${over.fetchCount}`, over);
    },
  },
  {
    id: "P3a-A7-garbled-budget-file",
    desc: "A7: a budget file that is bad JSON, [], \"x\", empty or a folder is read exactly as no file: no throw, exit 0, never M_ERROR, a 50cr call passes and a 500cr call is denied with M_LIMIT from the automatic cap, attended and unattended",
    fn() {
      for (const [label, make] of [["no file", null], ["bad JSON", "{bad"], ["[]", "[]"], ['"x"', '"x"'], ["empty", ""], ["a folder", "DIR"]]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          for (const [cmd, worst] of [[P50, 50], [P500, 500]]) {
            const s = open();
            if (make === "DIR") mkdirSync(s.bf);
            else if (make !== null) s.budget(make);
            const r = s.run(cmd, { env });
            const st = s.state();
            s.cleanup();
            assert(r.exit === 0 && !r.stderr && r.message !== mError(), `${label}, ${who}: never an error, read ${r.message}`, r);
            if (worst <= LIMIT) assert(r.raw === "" && st.spent === worst, `${label}, ${who}: 50 passes, read ${r.decision} / ${JSON.stringify(st)}`, r);
            else assert(r.message === mLimit({ spent: 0, worst, limit: LIMIT, src: srcAuto(BALANCE), bf: r.bf }), `${label}, ${who}: the automatic cap, read ${r.message}`, r);
          }
        }
      }
    },
  },
  {
    id: "P3a-A8-null-balance-fallback-and-small-balance",
    desc: "A8 (D28a): with no budget and no readable balance the limit is the fallback 500 (named so in M_LIMIT): 0 + 500 passes, 480 + 50 is denied; a balance of 3 gives a limit of 0 (M_LIMIT names the 3-credit balance), so even a 1cr call is denied",
    fn() {
      const ok = once(P500, { balance: null });
      assert(ok.raw === "" && spentOf(ok) === 500, `no balance: 0 + 500 reaches the fallback 500, read ${ok.decision} / ${JSON.stringify(ok.state)}`, ok);
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const r = once(P50, { balance: null, seed: { spent: 480 }, env });
        assert(r.decision === "deny" && r.message === mLimit({ spent: 480, worst: 50, limit: 500, src: SRC_FALLBACK, bf: r.bf }), `no balance, ${who}: M_LIMIT from the fallback, read ${r.message}`, r);
      }
      const three = once(P1, { balance: null, seed: { balance: 3, spent: 0 } });
      assert(three.decision === "deny" && three.message === mLimit({ spent: 0, worst: 1, limit: 0, src: srcAuto(3), bf: three.bf }), `balance 3: limit 0, read ${three.message}`, three);
    },
  },
  {
    id: "P3a-A9-lost-denies",
    desc: "A9: a paid call in a lost session (a saved lost: true, or a damaged state file) is denied with exactly M_LOST, attended and unattended (logged lost), the session stays lost on every later call, and a free plain call still passes silently",
    fn() {
      for (const [label, prep] of [["lost: true", (s) => s.seed({ spent: 40, lost: true })], ["a damaged file", (s) => writeFileSync(s.stateFile, '{"spent":40,"pend')]]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const s = open();
          prep(s);
          const rs = [P50, P1, P50].map((c) => s.run(c, { env }));
          const free = s.run(FREE, { env });
          const st = s.state();
          const log = s.logLines();
          s.cleanup();
          assert(rs.every((r) => r.decision === "deny" && r.message === M_LOST), `${label}, ${who}: M_LOST every time, read ${rs.map((r) => r.decision).join(",")} / ${rs[0].message}`, rs[0]);
          assert(st && st.lost === true, `${label}, ${who}: the session stays lost, read ${JSON.stringify(st)}`);
          assert(free.raw === "", `${label}, ${who}: a free plain call passes, read ${free.decision}`, free);
          if (who === "unattended") assert(log.length === 3 && log.every((l) => l.kind === "lost" && l.decision === "deny"), `${label}: three lost denies logged, read ${JSON.stringify(log)}`);
        }
      }
    },
  },
  {
    id: "P3a-A10-A11-routine-allow-only-where-due",
    desc: "A10/A11 (D26/D27, as D55/D56 rewrite them): with CLAUDE_CODE_HOST_SCHEDULED_RUN exactly \"1\" and an old routines block in the budget file, an in-budget plain paid call is a silent pass, committed 50; no allow anywhere: not a routine, HOST_SCHEDULED_RUN \"true\", \"0\" or \"\", routines disabled or not exactly true, perRun \"2000\", perDay 0, \"4000\", 20001 or 1.5 (3b R10), past the limit, not plain, a free call, attended or claude -p",
    fn() {
      const yes = once(P50, RON);
      assert(yes.raw === "" && spentOf(yes) === 50, `the routine's in-budget call: a silent pass, and committed, read ${yes.raw} / ${JSON.stringify(yes.state)}`, yes);
      const silent = [
        ["not a routine, routines on", P50, { budget: ROUTINES_ON }],
        ['HOST_SCHEDULED_RUN "true"', P50, { budget: ROUTINES_ON, env: { CLAUDE_CODE_HOST_SCHEDULED_RUN: "true" } }],
        ['HOST_SCHEDULED_RUN "0"', P50, { budget: ROUTINES_ON, env: { CLAUDE_CODE_HOST_SCHEDULED_RUN: "0" } }],
        ['HOST_SCHEDULED_RUN ""', P50, { budget: ROUTINES_ON, env: { CLAUDE_CODE_HOST_SCHEDULED_RUN: "" } }],
        ["routines disabled", P50, { budget: { routines: { enabled: false, perRun: 2000, perDay: 4000 } }, env: ROUTINE }],
        ['routines enabled "true"', P50, { budget: { routines: { enabled: "true", perRun: 2000, perDay: 4000 } }, env: ROUTINE }],
        ['perRun "2000"', P50, { budget: { routines: { enabled: true, perRun: "2000", perDay: 4000 } }, env: ROUTINE }],
        ["perDay 0", P50, { budget: { routines: { enabled: true, perRun: 2000, perDay: 0 } }, env: ROUTINE }],
        ['perDay "4000"', P50, { budget: { routines: { enabled: true, perRun: 2000, perDay: "4000" } }, env: ROUTINE }],
        ["perDay 20001", P50, { budget: { routines: { enabled: true, perRun: 2000, perDay: 20001 } }, env: ROUTINE }],
        ["perDay 1.5", P50, { budget: { routines: { enabled: true, perRun: 2000, perDay: 1.5 } }, env: ROUTINE }],
        ["a free call in a routine", FREE, RON],
        ["claude -p (unattended), routines on", P50, { budget: ROUTINES_ON, env: UN }],
      ];
      for (const [label, cmd, o] of silent) {
        const r = once(cmd, o);
        assert(r.raw === "", `${label}: a silent pass, no allow, read ${r.raw}`, r);
      }
      const over = once(P50, { ...RON, seed: { spent: 1990 } });
      assert(over.decision === "deny" && !over.raw.includes('"allow"'), `past the routine's limit: a deny, no allow, read ${over.raw.slice(0, 120)}`, over);
      const np = once(`echo '${P}'`, RON);
      assert(np.decision === "deny" && np.message === M_NOTPLAIN, `not plain in a routine: M_NOTPLAIN, no allow, read ${np.raw.slice(0, 120)}`, np);
      const ps = once(P50, { ...RON, extra: { tool_name: "PowerShell" } });
      assert(ps.decision === "deny" && ps.message === M_NOTBASH, `PowerShell in a routine: M_NOTBASH, no allow, read ${ps.raw.slice(0, 120)}`, ps);
    },
  },
  {
    id: "P3a-A12-routine-per-run",
    desc: "A12 (replayed under D55): in a routine, a session budget of 2000 beside an old routines block is the one limit: 1960 + 50 is denied with exactly M_LIMIT naming 2000 and your session budget, nothing counted; 1950 + 50 reaches it exactly and is a silent pass",
    fn() {
      const o = { budget: { sessionBudget: 2000, ...ROUTINES_ON }, env: ROUTINE };
      const r = once(P50, { ...o, seed: { spent: 1960 } });
      assert(r.decision === "deny" && r.message === mLimit({ spent: 1960, worst: 50, limit: 2000, src: SRC_SESSION }) && spentOf(r) === 1960,
        `1960 + 50 past the one budget of 2000: exactly M_LIMIT, read ${r.message}`, r);
      const eq = once(P50, { ...o, seed: { spent: 1950 } });
      assert(eq.raw === "" && spentOf(eq) === 2000, `1950 + 50 reaches 2000 exactly: a silent pass, read ${eq.raw}`, eq);
    },
  },
  {
    id: "P3a-A14-routine-off-session-limit",
    desc: "A14: a routine with routines off (disabled, or invalid fields), or on (an old block, ignored, D55), gets the session limit (steps 3-5): M_LIMIT from the automatic cap or its session budget, the session kind, never allow",
    fn() {
      for (const [label, budget, src, limit] of [
        ["routines disabled, no session budget", { routines: { enabled: false, perRun: 2000, perDay: 4000 } }, srcAuto(BALANCE), LIMIT],
        ["routines on, no session budget", ROUTINES_ON, srcAuto(BALANCE), LIMIT],
        ["perRun invalid, session budget 300", { sessionBudget: 300, routines: { enabled: true, perRun: 0, perDay: 4000 } }, SRC_SESSION, 300],
      ]) {
        const r = once(P500, { budget, env: ROUTINE });
        assert(r.decision === "deny" && r.message === mLimit({ spent: 0, worst: 500, limit, src, kind: "session", bf: r.bf }), `${label}: the session limit, read ${r.message}`, r);
        const ok = once(P50, { budget, env: ROUTINE });
        assert(ok.raw === "" && spentOf(ok) === 50, `${label}: within it a silent pass, no allow, read ${ok.raw}`, ok);
      }
    },
  },
  {
    id: "P3a-A15-hooks-json",
    desc: "A15: hooks.json registers credit-guard.mjs exactly once — PreToolUse, matcher Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit (3c: the write-type tools for the guard's own files), timeout 10 — with no PostToolUse or PostToolUseFailure entry, and research-suggest.mjs on UserPromptSubmit exactly as before",
    fn() {
      const cfg = JSON.parse(readFileSync(HOOKS_JSON, "utf8"));
      assert(JSON.stringify(Object.keys(cfg.hooks).sort()) === JSON.stringify(["PreToolUse", "UserPromptSubmit"]), `exactly PreToolUse and UserPromptSubmit, read ${Object.keys(cfg.hooks)}`);
      const guardEntries = [];
      for (const [event, list] of Object.entries(cfg.hooks)) for (const m of list) for (const h of m.hooks || []) {
        if (String(h.command || "").includes("credit-guard.mjs")) guardEntries.push({ event, matcher: m.matcher, ...h });
      }
      assert(guardEntries.length === 1, `exactly one credit-guard entry, read ${JSON.stringify(guardEntries)}`);
      const [g] = guardEntries;
      assert(g.event === "PreToolUse" && g.matcher === "Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit" && g.timeout === 10 && g.type === "command" && g.command === 'node "${CLAUDE_PLUGIN_ROOT}/hooks/credit-guard.mjs"',
        `PreToolUse, Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit, timeout 10, read ${JSON.stringify(g)}`);
      const want = [{ hooks: [{ type: "command", command: 'node "${CLAUDE_PLUGIN_ROOT}/hooks/research-suggest.mjs"', timeout: 10 }] }];
      assert(JSON.stringify(cfg.hooks.UserPromptSubmit) === JSON.stringify(want), `research-suggest unchanged, read ${JSON.stringify(cfg.hooks.UserPromptSubmit)}`);
    },
  },
  {
    id: "P3a-A16-post-input-and-old-pending",
    desc: "A16 (D28a): a PostToolUse or PostToolUseFailure input — for a paid plain call, one whose old pending quote sits in the state file, or a command that is not plain — prints nothing, exits 0, writes nothing and logs nothing; the guard never writes a pending key (an old one is dropped on the next save); a state file carrying an old pending key reads as a whole session, never lost",
    fn() {
      for (const failure of [false, true]) {
        for (const [label, cmd] of [["a paid plain call", P50], ["not plain", `echo '${P}'`]]) {
          const s = open({ seed: { spent: 10, pending: { abc: 50, def: 7 } } });
          const before = s.stateRaw();
          const files = readdirSync(s.revxl).sort().join(",");
          const p = s.post(cmd, { failure, env: UN });
          assert(p.raw === "" && p.exit === 0 && s.stateRaw() === before && readdirSync(s.revxl).sort().join(",") === files && s.logLines().length === 0,
            `${failure ? "PostToolUseFailure" : "PostToolUse"}, ${label}: nothing printed, written or logged, read ${JSON.stringify(p.raw)} / ${s.stateRaw()}`, p);
          s.cleanup();
        }
      }
      // An older build parked this command's quote under its sha256: its Post input commits nothing.
      const s = open({ seed: { spent: 0, pending: { [createHash("sha256").update(P50).digest("hex")]: 50 } } });
      s.post(P50);
      assert(JSON.parse(s.stateRaw()).spent === 0, `the Post input never commits an old quote, read ${s.stateRaw()}`);
      const r = s.run(P1);
      const st = s.state();
      s.cleanup();
      assert(r.raw === "" && st.spent === 1 && !("pending" in st) && !st.lost, `the old key reads as a whole session and is dropped on the next save, read ${JSON.stringify(st)}`, r);
    },
  },
  {
    id: "P3a-A17-failed-and-recorded",
    desc: "A17: an error of the guard's own passes attended outside a routine (silent) and denies unattended with exactly M_ERROR, for Bash and for PowerShell (with \" For SocialCrawl calls, use the Bash tool.\"); recorded()'s refusal is byte-identical to 0.3.1's",
    fn() {
      const outer = outerThrows();
      for (const [who, extra, notBash] of [["Bash", undefined, false], ["PowerShell", { tool_name: "PowerShell" }, true]]) {
        const a = once(P50, { extra, node: ["--import", outer.url] });
        assert(a.raw === "" && a.exit === 0, `${who}, attended: an error passes silently, read ${a.raw}`, a);
        const u = once(P50, { extra, node: ["--import", outer.url], env: UN });
        assert(u.decision === "deny" && u.message === mError(notBash) && u.exit === 0, `${who}, unattended: exactly M_ERROR, read ${u.message}`, u);
        assert(u.log.length === 1 && u.log[0].kind === "error" && u.log[0].cap === null, `${who}, unattended: one error line, read ${JSON.stringify(u.log)}`);
      }
      rmSync(outer.dir, { recursive: true, force: true });
      // recorded(), 0.3.1 credit-guard.mjs:371-377, word for word.
      const save = saveThrows();
      const s = open();
      const r = s.run(P50, { node: ["--import", save.url], env: { SAVE_FAIL: s.stateFile } });
      const want =
        `SocialCrawl call not run: the credit guard couldn't record it, and a call it can't record ` +
        `would run uncounted (this command's worst case is ~50 credits). Reason: the session file could not be saved (EBUSY). ` +
        `Session file: ${s.stateFile}. Nothing was sent. Run the command again; if it is refused ` +
        `again, check that the session file and its folder exist and can be written.`;
      s.cleanup();
      rmSync(save.dir, { recursive: true, force: true });
      assert(r.decision === "deny" && r.message === want, `recorded(): byte-identical, read ${r.message}`, r);
      assert(!want.endsWith(T) && !want.includes(USE_BASH), "the 0.3.1 refusal carries neither the D28 tail nor the Bash line on a Bash call");
    },
  },
  {
    id: "P3f-routine-error-denies",
    desc: "3f A1-A4 (D44): an error of the guard's own in a Desktop routine (CLAUDE_CODE_HOST_SCHEDULED_RUN exactly \"1\", attended unset or 1) denies with exactly M_ERROR, exit 0, nothing counted and one error line (cap null) in the unattended log: from the outer catch (the session path's join throws; Bash and PowerShell; session_id null) and from the inner catch (costs.json _unpriced: 5; Bash; session_id the sid); attended outside a routine the same errors pass silently, unattended they deny as before, unattended in a routine they deny with one line, not two; any other value of the variable (0, true, empty, \" 1\", \"1 \") is not a routine",
    fn() {
      const outer = outerThrows();
      const inner = innerThrows();
      const OUT = { node: ["--import", outer.url] };
      const IN = { guard: inner.file };
      const go = (o) => {
        const s = open();
        const before = s.stateRaw();
        const r = s.run(P50, o);
        Object.assign(r, { sid: s.sid, counted: s.stateRaw() !== before, log: s.logLines() });
        s.cleanup();
        return r;
      };
      const denied = (r, label, notBash, sid) => {
        assert(r.decision === "deny" && r.message === mError(notBash) && r.exit === 0, `${label}: exactly M_ERROR, exit 0, read ${r.decision} / ${r.message}`, r);
        assert(!r.counted, `${label}: nothing counted, the session file unchanged`, r);
        assert(r.log.length === 1 && r.log[0].decision === "deny" && r.log[0].kind === "error" && r.log[0].cap === null && r.log[0].session_id === sid,
          `${label}: exactly one error line, cap null, session_id ${sid}, read ${JSON.stringify(r.log)}`, r);
      };
      // A1 (the outer catch) and A2 (the inner catch): a routine, attended unset and attended 1.
      for (const [att, env] of [["attended unset", ROUTINE], ["attended 1", { ...ROUTINE, CLAUDE_CODE_SESSION_ATTENDED: "1" }]]) {
        for (const [who, extra, notBash] of [["Bash", undefined, false], ["PowerShell", { tool_name: "PowerShell" }, true]]) {
          denied(go({ ...OUT, extra, env }), `A1 outer catch, routine, ${att}, ${who}`, notBash, null);
        }
        const r = go({ ...IN, env });
        denied(r, `A2 inner catch, routine, ${att}, Bash`, false, r.sid);
      }
      // A3: attended outside a routine a silent pass; unattended, and unattended in a routine, the deny.
      for (const [where, o] of [["outer", OUT], ["inner", IN]]) {
        const a = go(o);
        assert(a.raw === "" && a.exit === 0 && !a.counted && a.log.length === 0, `A3 ${where} catch, attended outside a routine: a silent pass, read ${a.raw}`, a);
        const u = go({ ...o, env: UN });
        denied(u, `A3 ${where} catch, unattended`, false, where === "outer" ? null : u.sid);
        const ur = go({ ...o, env: { ...UN, ...ROUTINE } });
        denied(ur, `A3 ${where} catch, unattended in a routine`, false, where === "outer" ? null : ur.sid);
      }
      // A4: ROUTINE is exactly "1"; any other value, with an attended error, is a silent pass.
      for (const v of ["0", "true", "", " 1", "1 "]) {
        const a = go({ ...OUT, env: { CLAUDE_CODE_HOST_SCHEDULED_RUN: v } });
        assert(a.raw === "" && a.exit === 0 && a.log.length === 0, `A4 CLAUDE_CODE_HOST_SCHEDULED_RUN=${JSON.stringify(v)}, attended: not a routine, a silent pass, read ${a.raw}`, a);
      }
      rmSync(outer.dir, { recursive: true, force: true });
      rmSync(inner.dir, { recursive: true, force: true });
    },
  },
  {
    id: "P3a-A18-unattended-log",
    desc: "A18: unattended, every deny is logged and every logged kind is one of not-plain, lost, over-limit, under-cap and error, each line holding exactly ts, session_id, decision, kind, paths, cmdWorst, committed, cap in that order; the former transcript, unreadable, uncomputable, unpriced and cap-step shapes log as passes or over-limit; attended, the same runs log nothing",
    fn() {
      const shapes = [
        ["not plain", `echo '${P}'`, {}],
        ["not Bash", P50, { extra: { tool_name: "PowerShell" } }],
        ["lost", P50, { seed: { spent: 0, lost: true } }],
        ["past the limit", P50, { seed: { spent: 190 } }],
        ["a pass", P1, {}],
        ["a routine pass", P1, RON],
        ["a transcript", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, { env: NOLOCAL }],
        ["unreadable", `curl -s "${V1}prism/no-such-endpoint?h=a"`, {}],
        ["uncomputable", `curl -X POST "${V1}web/batch-scrape" -d '{}'`, {}],
        ["unpriced", `curl -s "${V1}cohorts?segment=a"`, {}],
        ["the former cap step (199 + 1)", P1, { seed: { spent: 199 } }],
        ["the former cap step, no balance", P50, { balance: null }],
      ];
      let denies = 0;
      const lines = [];
      for (const [label, cmd, o] of shapes) {
        const u = once(cmd, { ...o, env: { ...(o.env || {}), ...UN } });
        if (u.decision === "deny") denies++;
        assert(u.log.length === 1, `${label}: one line, read ${JSON.stringify(u.log)}`, u);
        assert(JSON.stringify(Object.keys(u.log[0])) === JSON.stringify(FIELDS), `${label}: the field order, read ${Object.keys(u.log[0])}`);
        assert(KINDS.includes(u.log[0].kind) && u.log[0].decision === (u.decision === "deny" ? "deny" : "pass"), `${label}: a kind of §d, read ${JSON.stringify(u.log[0])}`);
        lines.push(u.log[0]);
        const a = once(cmd, { ...o });
        assert(a.log.length === 0, `${label}, attended: nothing logged, read ${JSON.stringify(a.log)}`, a);
      }
      assert(lines.filter((l) => l.decision === "deny").length === denies, `every deny is logged, read ${denies} denies / ${JSON.stringify(lines.map((l) => l.kind))}`);
      const pass = (i) => lines[i].decision === "pass" && lines[i].kind === "under-cap";
      assert(pass(6) && pass(7) && pass(8) && pass(9) && pass(10) && pass(11), `the former can't-count and cap-step shapes pass and log under-cap, read ${JSON.stringify(lines.slice(6).map((l) => l.kind))}`);
    },
  },
  {
    id: "P3a-A19-inline-budget-reader",
    desc: "A19: the budget reader is inline: credit-guard.mjs imports only node:fs, node:os, node:path and node:url (no new module; node:crypto is gone with the hash) and loads ledger.mjs only for the balance read; a copy of credit-guard.mjs alone, with no costs.json and no ledger.mjs beside it, reads a session budget",
    fn() {
      const src = readFileSync(GUARD, "utf8");
      const statics = [...src.matchAll(/^import\s.*?from\s+"([^"]+)";$/gm)].map((m) => m[1]).sort();
      const dynamics = [...src.matchAll(/\bimport\(\s*"([^"]+)"\s*\)/g)].map((m) => m[1]);
      assert(JSON.stringify(statics) === JSON.stringify(["node:fs", "node:os", "node:path", "node:url"]), `static imports, read ${JSON.stringify(statics)}`);
      assert(JSON.stringify(dynamics) === JSON.stringify(["./ledger.mjs"]), `dynamic imports, read ${JSON.stringify(dynamics)}`);
      const d = mkdtempSync(join(tmpdir(), "sc-p3a-alone-"));
      copyFileSync(GUARD, join(d, "credit-guard.mjs"));
      const r = once(P50, { budget: { sessionBudget: 30 }, guard: join(d, "credit-guard.mjs") });
      rmSync(d, { recursive: true, force: true });
      // With no costs.json the FALLBACK_BIG list prices prism/leads at 50.
      assert(r.decision === "deny" && r.message === mLimit({ spent: 0, worst: 50, limit: 30, src: SRC_SESSION, bf: r.bf }), `the guard alone reads the budget, read ${r.message}`, r);
    },
  },
  {
    id: "P3a-A20-mutants",
    desc: "A20: each mutant copy of the guard turns a probe red that this build passes — the clamp removed (a budget of 0 or 20001 accepted), the boundary set to >=, a null balance denied, ROUTINE always true (an attended error then denies), allow re-added at the commit for a routine, and the within-limit test dropped (a routine past its session budget of 2000)",
    fn() {
      const rows = [];
      const cases = [
        ["clamp removed", "  const valid = (v) => Number.isInteger(v) && v >= 1 && v <= 20000;\n", "  const valid = (v) => Number.isInteger(v);\n", () => [
          ["sessionBudget 20001, a 500cr call", P500, { budget: { sessionBudget: 20001 } }, (r) => r.decision === "deny"],
          ["sessionBudget 0, a 1cr call", P1, { budget: { sessionBudget: 0 } }, (r) => r.raw === ""],
        ]],
        ["boundary >=", "  if (cmdWorst > 0 && spent + cmdWorst > limit) {\n", "  if (cmdWorst > 0 && spent + cmdWorst >= limit) {\n", () => [
          ["0 + 200 at the 200 limit", P200, {}, (r) => r.raw === "" && spentOf(r) === 200],
        ]],
        ["null balance denied", "      limit = 500;\n", "      return deny(M_LOST, \"over-limit\");\n", () => [
          ["no balance, a 1cr call", P1, { balance: null }, (r) => r.raw === "" && spentOf(r) === 1],
        ]],
        ["ROUTINE always true", 'const ROUTINE = process.env.CLAUDE_CODE_HOST_SCHEDULED_RUN === "1";\n', "const ROUTINE = true;\n", () => [
          ["an attended error, not a routine", P50, { node: ["--import", outer.url] }, (r) => r.raw === "" && r.exit === 0],
        ]],
        ["allow re-added at the commit", "  return done();\n} catch {", '  if (ROUTINE) return done({ hookSpecificOutput: { permissionDecision: "allow", permissionDecisionReason: "SocialCrawl routine call within budget." } });\n  return done();\n} catch {', () => [
          ["a routine's in-budget call", P50, RON, (r) => r.raw === "" && spentOf(r) === 50],
        ]],
        ["the within-limit test dropped", "  if (cmdWorst > 0 && spent + cmdWorst > limit) {\n", "  if (false) {\n", () => [
          ["a routine past its session budget of 2000 (1990 + 50)", P50, { budget: { sessionBudget: 2000 }, env: ROUTINE, seed: { spent: 1990 } }, (r) => r.decision === "deny" && !r.raw.includes('"allow"')],
        ]],
      ];
      const outer = outerThrows();
      for (const [name, anchor, repl, probes] of cases) {
        const m = mutant(name.replace(/[^a-z0-9]+/gi, "-"), anchor, repl);
        for (const [label, cmd, o, ok] of probes()) {
          const fix = once(cmd, o);
          const mut = once(cmd, { ...o, guard: m.file });
          rows.push(`    ${name.padEnd(46)} ${label.padEnd(36)} build ${fix.decision || (fix.raw ? "allow" : "pass")} | mutant ${mut.decision || (mut.raw ? "allow" : "pass")}`);
          assert(ok(fix), `${name}, ${label}: the build behaves, read ${fix.raw.slice(0, 160)}`, fix);
          assert(!ok(mut), `${name}, ${label}: the mutant is caught (it behaves wrongly), read ${mut.raw.slice(0, 160)}`, mut);
        }
        rmSync(m.dir, { recursive: true, force: true });
      }
      rmSync(outer.dir, { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3g-A1-one-limit-every-run",
    desc: "3g A1 (D55): one limit for every kind of run. For no env, ATTENDED=1, ATTENDED=0, HOST_SCHEDULED_RUN=1, HOST=1 + ATTENDED=1 and HOST=1 + ATTENDED=0: with {sessionBudget: 300}, 250 + 50 is a silent pass, spent 300, and 260 + 50 is exactly M_LIMIT(260, 50, 300, your session budget), spent 260; with no budget file, 150 + 50 passes and 160 + 50 is exactly M_LIMIT at the automatic cap of an 800 balance; with no balance, the 500 fallback (450 + 50 passes, 460 + 50 is exactly M_LIMIT naming it); each call record line is a pass or a deny with the same limit in every env, and ends with routine, true exactly when HOST_SCHEDULED_RUN is \"1\" (D58)",
    fn() {
      const ENVS = [["no env", {}], ["ATTENDED=1", { CLAUDE_CODE_SESSION_ATTENDED: "1" }], ["ATTENDED=0", UN], ["HOST=1", ROUTINE],
        ["HOST=1, ATTENDED=1", { ...ROUTINE, CLAUDE_CODE_SESSION_ATTENDED: "1" }], ["HOST=1, ATTENDED=0", { ...ROUTINE, ...UN }]];
      // [label, open options, the exact deny or null for a silent pass, spent after, the limit]
      const cases = [
        ["{sessionBudget:300}, 250 + 50", { budget: { sessionBudget: 300 }, seed: { spent: 250 } }, null, 300, 300],
        ["{sessionBudget:300}, 260 + 50", { budget: { sessionBudget: 300 }, seed: { spent: 260 } }, mLimit({ spent: 260, worst: 50, limit: 300, src: SRC_SESSION }), 260, 300],
        ["no budget file, 150 + 50", { seed: { spent: 150 } }, null, 200, 200],
        ["no budget file, 160 + 50", { seed: { spent: 160 } }, mLimit({ spent: 160, worst: 50, limit: 200, src: srcAuto(BALANCE) }), 160, 200],
        ["no balance, 450 + 50", { balance: null, seed: { spent: 450 } }, null, 500, 500],
        ["no balance, 460 + 50", { balance: null, seed: { spent: 460 } }, mLimit({ spent: 460, worst: 50, limit: 500, src: SRC_FALLBACK }), 460, 500],
      ];
      const rows = [];
      for (const [label, o, deny, after, limit] of cases) {
        const seen = [];
        for (const [who, env] of ENVS) {
          const s = open(o);
          const r = s.run(P50, { env });
          const st = s.state();
          const rec = callRecord(s.revxl);
          s.cleanup();
          const l = rec[rec.length - 1] || {};
          seen.push(`${who}=${r.decision || (r.raw ? "?" : "pass")}/${l.limit}/${l.routine}`);
          if (deny === null) assert(r.raw === "" && r.exit === 0, `${label}, ${who}: a silent pass, read ${r.raw.slice(0, 200)}`, r);
          else assert(r.decision === "deny" && r.message === deny, `${label}, ${who}: exactly M_LIMIT, read ${r.message.slice(0, 260)}`, r);
          assert(st && st.spent === after, `${label}, ${who}: spent ${after}, read ${JSON.stringify(st)}`, r);
          assert(rec.length === 1 && l.decision === (deny === null ? "pass" : "deny") && l.limit === limit,
            `${label}, ${who}: one call record line, ${deny === null ? "pass" : "deny"} at limit ${limit}, read ${JSON.stringify(rec)}`, r);
          const keys = Object.keys(l);
          assert(keys[keys.length - 1] === "routine" && l.routine === (env.CLAUDE_CODE_HOST_SCHEDULED_RUN === "1"),
            `${label}, ${who}: the line ends with routine ${env.CLAUDE_CODE_HOST_SCHEDULED_RUN === "1"}, read ${JSON.stringify(l)}`, r);
        }
        rows.push(`    ${label.padEnd(34)} ${seen.join(" ")}`);
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3g-A2-no-allow-anywhere",
    desc: "3g A2 (D56): credit-guard.mjs holds no \"allow\" decision literal, and every P3a-A1 shape, attended, unattended, in a routine and in a routine unattended, prints nothing or a deny",
    fn() {
      const src = readFileSync(GUARD, "utf8");
      const hits = src.split("\n").map((l, i) => [i + 1, l]).filter(([, l]) => /["'`]allow["'`]/.test(l));
      assert(!hits.length, `no "allow" literal in credit-guard.mjs, read ${JSON.stringify(hits)}`);
      const shapes = [
        ["a loop", `for i in 1 2; do curl -s "${P}"; done`, {}],
        ["a pipe into a program", `curl -s "${P}" | sh`, {}],
        ["PowerShell, paid", P50, { extra: { tool_name: "PowerShell" } }],
        ["PowerShell, free", FREE, { extra: { tool_name: "PowerShell" } }],
        ["a transcript", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, { env: NOLOCAL }],
        ["cohorts", `curl -s "${V1}cohorts?segment=a"`, {}],
        ["an unresolved literal path", `curl -s "${V1}prism/no-such-endpoint?h=a"`, {}],
        ["GET web/monitors", `curl -s "${V1}web/monitors"`, {}],
        ["a limit overrun (190 + 50)", P50, { seed: { spent: 190 } }],
        ["a null balance", P50, { balance: null }],
        ["a lost total", P50, { seed: { spent: 0, lost: true } }],
        ["a routine, in budget", P50, RON],
      ];
      const seen = [];
      for (const [label, cmd, o] of shapes) {
        for (const [who, env] of [["attended", {}], ["unattended", UN], ["a routine", ROUTINE], ["a routine, unattended", { ...ROUTINE, ...UN }]]) {
          const r = once(cmd, { ...o, env: { ...(o.env || {}), ...env } });
          seen.push(`${label}/${who}=${r.decision || (r.raw ? "?" : "pass")}`);
          assert((r.raw === "" || r.decision === "deny") && !r.raw.includes('"allow"') && r.exit === 0, `${label}, ${who}: nothing or a deny, read ${r.raw.slice(0, 160)}`, r);
        }
      }
      console.log(`    ${seen.join(", ")}`);
    },
  },
  {
    id: "P3g-A3-old-fields-ignored",
    desc: "3g A3 (D55, no migration): an old routines block is never read. For routines on, routines disabled, routines with invalid fields, {sessionBudget: 300} beside routines on, and {sessionBudget: 300} beside routines with perRun 20, each of 50 at 0, 500 at 0 and 50 at 250, in a routine and outside, gives exactly the stdout and committed total of the same file with routines removed; routines on alone in a routine is the automatic cap (500 at 0 is exactly M_LIMIT at 200, never 2000); the 300 budget beside perRun 20 lets 250 + 50 pass in a routine",
    fn() {
      const P20 = { sessionBudget: 300, routines: { enabled: true, perRun: 20, perDay: 4000 } };
      const files = [
        ["routines on", ROUTINES_ON],
        ["routines disabled", { routines: { enabled: false, perRun: 2000, perDay: 4000 } }],
        ["routines with invalid fields", { routines: { enabled: "true", perRun: 0, perDay: "4000" } }],
        ["sessionBudget 300 beside routines on", { sessionBudget: 300, ...ROUTINES_ON }],
        ["sessionBudget 300 beside perRun 20", P20],
      ];
      const rows = [];
      for (const [label, b] of files) {
        const { routines, ...bare } = b;
        for (const [cmd, spent, what] of [[P50, 0, "50 at 0"], [P500, 0, "500 at 0"], [P50, 250, "50 at 250"]]) {
          for (const [who, env] of [["in a routine", ROUTINE], ["outside", {}]]) {
            const a = once(cmd, { budget: b, seed: { spent }, env });
            const z = once(cmd, { budget: bare, seed: { spent }, env });
            rows.push(`    ${`${label}, ${what}, ${who}`.padEnd(62)} ${a.decision || "pass"} ${spentOf(a)} | without routines ${z.decision || "pass"} ${spentOf(z)}`);
            assert(a.raw === z.raw && spentOf(a) === spentOf(z), `${label}, ${what}, ${who}: exactly as without routines, read ${a.raw.slice(0, 200)} / ${spentOf(a)} vs ${z.raw.slice(0, 200)} / ${spentOf(z)}`, a);
          }
        }
      }
      const auto = once(P500, { budget: ROUTINES_ON, env: ROUTINE });
      assert(auto.decision === "deny" && auto.message === mLimit({ spent: 0, worst: 500, limit: LIMIT, src: srcAuto(BALANCE) }) && spentOf(auto) === 0,
        `routines on alone, in a routine: the automatic cap of 200, never perRun 2000, read ${auto.message.slice(0, 260)}`, auto);
      const p20 = once(P50, { budget: P20, seed: { spent: 250 }, env: ROUTINE });
      assert(p20.raw === "" && spentOf(p20) === 300, `the 300 budget beside perRun 20, in a routine: 250 + 50 passes, read ${p20.raw.slice(0, 200)} / ${spentOf(p20)}`, p20);
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P3g-A5-the-message",
    desc: "3g A5 (D55): every over-limit deny (the automatic cap, a session budget, the 500 fallback) is exactly the new M_LIMIT, the same text attended, unattended, in a routine and in a routine unattended, and names neither the budget file's path nor its name; no string in credit-guard.mjs outside a comment and the tamper list's file names (K2, kept) holds routine, daily, day file, day lock, perRun or perDay, and no deny driven here (not plain, not Bash, lost, the session or budget file unreadable, recorded()'s refusal, the guard's own error, over the limit) holds one either",
    fn() {
      const ENVS = [["attended", {}], ["unattended", UN], ["a routine", ROUTINE], ["a routine, unattended", { ...ROUTINE, ...UN }]];
      const BANNED = /routine|daily|day file|day lock|perrun|perday/i;
      for (const [label, o, want] of [
        ["the automatic cap, 190 + 50", { seed: { spent: 190 } }, mLimit({ spent: 190, worst: 50, limit: 200, src: srcAuto(BALANCE) })],
        ["a session budget of 100, 80 + 50", { seed: { spent: 80 }, budget: { sessionBudget: 100, ...ROUTINES_ON } }, mLimit({ spent: 80, worst: 50, limit: 100, src: SRC_SESSION })],
        ["the 500 fallback, 480 + 50", { balance: null, seed: { spent: 480 } }, mLimit({ spent: 480, worst: 50, limit: 500, src: SRC_FALLBACK })],
      ]) {
        for (const [who, env] of ENVS) {
          const r = once(P50, { ...o, env });
          assert(r.decision === "deny" && r.message === want && !r.message.includes(r.bf) && !r.message.includes("socialcrawl-budget.json") && !BANNED.test(r.message),
            `${label}, ${who}: exactly the new M_LIMIT, no file named, read ${r.message.slice(0, 300)}`, r);
        }
      }
      // Every string literal outside a comment, but the tamper list's file names (GUARD_FILES, K2 kept by 3g).
      const lits = [];
      for (const [i, l] of readFileSync(GUARD, "utf8").split("\n").entries()) {
        const t = l.trim();
        if (t.startsWith("//") || t.startsWith("*") || t.startsWith("/*") || t.startsWith('["socialcrawl-')) continue;
        for (const m of l.replace(/\/\/ .*$/, "").matchAll(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`/g)) if (BANNED.test(m[0])) lits.push(`${i + 1}: ${m[0].slice(0, 120)}`);
      }
      assert(!lits.length, `no deny text in credit-guard.mjs names a routine or day budget, read ${JSON.stringify(lits)}`);
      // The other denies, driven in a routine and unattended.
      const outer = outerThrows();
      const save = saveThrows();
      const fault = stateFault();
      const drive = [
        ["not plain", `echo '${P}'`, {}, null],
        ["not Bash", P50, { extra: { tool_name: "PowerShell" } }, null],
        ["lost", P50, { seed: { spent: 0, lost: true } }, null],
        ["the session file unreadable", P50, {}, (s) => ({ node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["read", s.stateFile, "EACCES"]) } })],
        ["the budget file unreadable", P50, { budget: { sessionBudget: 300 } }, (s) => ({ node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["read", s.bf, "EBUSY"]) } })],
        ["recorded()'s refusal", P50, {}, (s) => ({ node: ["--import", save.url], env: { SAVE_FAIL: s.stateFile } })],
        ["the guard's own error", P50, {}, () => ({ node: ["--import", outer.url] })],
      ];
      for (const [label, cmd, o, prep] of drive) {
        for (const [who, env] of [["a routine", ROUTINE], ["unattended", UN]]) {
          const s = open(o);
          const p = prep ? prep(s) : {};
          const r = s.run(cmd, { extra: o.extra, node: p.node, env: { ...env, ...(p.env || {}) } });
          s.cleanup();
          assert(r.decision === "deny" && !BANNED.test(r.message), `${label}, ${who}: a deny naming no routine or day budget, read ${r.decision} / ${r.message.slice(0, 200)}`, r);
        }
      }
      rmSync(outer.dir, { recursive: true, force: true });
      rmSync(save.dir, { recursive: true, force: true });
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
    },
  },
  {
    id: "P3g-A6-lost-in-a-routine",
    desc: "3g A6 (replay): in a Desktop routine (attended unset and 0, with an old routines block in the budget file or none), a paid call in a lost session (a saved lost: true, or a damaged state file) is denied with exactly M_LOST every time, the session stays lost, and a free plain call still passes silently",
    fn() {
      for (const [label, prep] of [["lost: true", (s) => s.seed({ spent: 40, lost: true })], ["a damaged file", (s) => writeFileSync(s.stateFile, '{"spent":40,"pend')]]) {
        for (const [who, env] of [["attended unset", ROUTINE], ["attended 0", { ...ROUTINE, ...UN }]]) {
          for (const budget of [undefined, ROUTINES_ON]) {
            const s = open({ budget });
            prep(s);
            const rs = [P50, P1].map((c) => s.run(c, { env }));
            const free = s.run(FREE, { env });
            const st = s.state();
            s.cleanup();
            assert(rs.every((r) => r.decision === "deny" && r.message === M_LOST), `${label}, ${who}, ${budget ? "routines block" : "no budget"}: M_LOST every time, read ${rs.map((r) => r.decision).join(",")} / ${rs[0].message.slice(0, 120)}`, rs[0]);
            assert(st && st.lost === true && free.raw === "", `${label}, ${who}: stays lost, a free call passes, read ${JSON.stringify(st)} / ${free.raw}`);
          }
        }
      }
    },
  },
  {
    id: "P3g-A8-kinds",
    desc: "3g A8 (D55): driven unattended, outside and in a routine, through every deny (not plain, not Bash, lost, over the limit, the session or budget file unreadable, recorded()'s refusal, the guard's own error) and a pass: the unattended log's kinds are exactly not-plain, lost, over-limit, under-cap and error; the call record's are exactly lost, over-limit, under-cap and error (not-plain is decided before the lock); the decisions in both are exactly pass and deny",
    fn() {
      const outer = outerThrows();
      const save = saveThrows();
      const fault = stateFault();
      const drive = [
        ["not plain", `echo '${P}'`, {}, null],
        ["not Bash", P50, { extra: { tool_name: "PowerShell" } }, null],
        ["lost", P50, { seed: { spent: 0, lost: true } }, null],
        ["over the limit", P50, { seed: { spent: 190 } }, null],
        ["the session file unreadable", P50, {}, (s) => ({ node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["read", s.stateFile, "EACCES"]) } })],
        ["the budget file unreadable", P50, { budget: { sessionBudget: 300 } }, (s) => ({ node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["read", s.bf, "EBUSY"]) } })],
        ["recorded()'s refusal", P50, {}, (s) => ({ node: ["--import", save.url], env: { SAVE_FAIL: s.stateFile } })],
        ["the guard's own error", P50, {}, () => ({ node: ["--import", outer.url] })],
        ["a pass", P1, {}, null],
        ["a pass beside an old routines block", P1, { budget: ROUTINES_ON }, null],
      ];
      const logKinds = new Set(), recKinds = new Set(), decisions = new Set();
      for (const [label, cmd, o, prep] of drive) {
        for (const env of [UN, { ...ROUTINE, ...UN }]) {
          const s = open(o);
          const p = prep ? prep(s) : {};
          s.run(cmd, { extra: o.extra, node: p.node, env: { ...env, ...(p.env || {}) } });
          for (const l of s.logLines()) { logKinds.add(l.kind); decisions.add(l.decision); }
          for (const l of callRecord(s.revxl)) { recKinds.add(l.kind); decisions.add(l.decision); }
          s.cleanup();
        }
      }
      rmSync(outer.dir, { recursive: true, force: true });
      rmSync(save.dir, { recursive: true, force: true });
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(`    log ${JSON.stringify([...logKinds].sort())} record ${JSON.stringify([...recKinds].sort())} decisions ${JSON.stringify([...decisions].sort())}`);
      assert(JSON.stringify([...logKinds].sort()) === JSON.stringify([...KINDS].sort()), `the unattended log's kinds are exactly the 5, read ${JSON.stringify([...logKinds].sort())}`);
      assert(JSON.stringify([...recKinds].sort()) === JSON.stringify(["error", "lost", "over-limit", "under-cap"]), `the call record's kinds, read ${JSON.stringify([...recKinds].sort())}`);
      assert(JSON.stringify([...decisions].sort()) === JSON.stringify(["deny", "pass"]), `the decisions are exactly pass and deny, read ${JSON.stringify([...decisions].sort())}`);
    },
  },
];
