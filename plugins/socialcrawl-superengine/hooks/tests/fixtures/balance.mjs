/*
 * R14b — the balance read, unattended mode, the log and the notice (D28 since 0.4.0).
 *
 * The guard reads the balance (GET /v1/credits/balance, 0 credits) on a plain command whose worst
 * case is above 0 when no balance is cached and no session budget is set; a command that is not
 * plain is denied before any read (J1; D28). A finite number at data.balance is cached whatever its
 * value; a failed try caches nothing and is counted, at most 3 a session (O3); an integer balance of
 * 0 or more gives the automatic cap min(500, 25%), anything else the fallback limit of 500 (D28a).
 * Every unattended decision past the fast path, except a plain free pass, is one line in
 * <revxl>/credit-guard-unattended.jsonl (J2, O5), and research-suggest.mjs reports each new batch
 * once on the next prompt (J3). An error inside the guard denies unattended or in a routine (3f)
 * and passes attended otherwise (O2). ledger.mjs exits through process.exitCode (O6). A state that can't be saved is never read
 * into and never passes a paid call silently (checker X1), and a stray Post input prints, logs and
 * writes nothing (checker X2; D28a: the guard no longer runs after a command). A state file that is
 * there but can't be read back is a lost total: every paid call is denied (M_LOST) and no balance is
 * read for the rest of the session (J4, checkers X3/X4). Every sc_ run in a logged path is masked
 * (J5, checker X5). Guard runs of one session take turns on a lock file (checker X7). A run that
 * can't record its commit (no lock within its wait, no session folder, a save that throws) refuses
 * the call, attended and unattended; a save that does not throw counts as recorded, with no
 * read-back (R18-3), so a save lost without an error loses its count (the stated LIMIT); the lock
 * create is tried again on any error but ENOENT, which ends the wait at once (R18-2), and a run that
 * ends normally leaves no lock behind (J6, checkers X8-X10).
 *
 * Synchronous (P26). Every balance request is answered by the fake-fetch.mjs preload (lib.mjs
 * `o.fetch`, with a fake key); every other run is offline (no key, a scratch home, dead proxies).
 * Zero credits, zero network: R14b-09 talks to a loopback server in its own driver process only.
 */
import { spawnSync } from "node:child_process";
import { appendFileSync, chmodSync, copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  session, V1, TSCRIPT, GUARD, COSTS, FAKE_FETCH, FAKE_KEY, T, M_NOTPLAIN, M_NOTBASH, M_LOST, mError, mLimit, mStateRead, srcAuto,
  SRC_FALLBACK, ROUTINE, ROUTINES_ON, assert, assertDecision, assertMatch,
} from "../lib.mjs";
import { ask } from "../lib-suggest.mjs";

const HOOKS = dirname(GUARD);
const LEDGER = join(HOOKS, "ledger.mjs");
const UN = { CLAUDE_CODE_SESSION_ATTENDED: "0" };
const NOLOCAL = { GROQ_API_KEY: "", PATH: "" };
const DOCS = "https://docs." + "social" + "crawl" + ".dev";
const P50 = `curl -s "${V1}prism/leads?query=x"`;           // flat 50, plain
const P1 = `curl -s "${V1}amazon/shop?q=a"`;                 // flat 1, plain
const P1B = `curl -s "${V1}amazon/shop?q=b"`;
const P50N = (i) => `curl -s "${V1}prism/leads?query=r${i}"`;   // flat 50, plain, one per run of a burst
const NP150 = `echo '${V1}prism/leads?query=a ${V1}prism/leads?query=b ${V1}prism/leads?query=c'`;  // not plain, 150 visible
const P150 = `curl -s "${V1}prism/leads?query=a" && curl -s "${V1}prism/leads?query=b" && curl -s "${V1}prism/leads?query=c"`;  // plain, 150
const lockOf = (s) => `${s.stateFile}.lock`;
const bal = (v) => ({ body: { data: { balance: v } } });
const FIELDS = ["ts", "session_id", "decision", "kind", "paths", "cmdWorst", "committed", "cap"];
/** M_LIMIT for session `s` (or a run result) under the automatic cap of `balance`. */
const limitOf = (s, spent, worst, balance = 800) =>
  mLimit({ spent, worst, limit: Math.min(500, Math.floor(0.25 * balance)), src: srcAuto(balance), bf: s.bf });
const LIMIT_RE = /^SocialCrawl call not run: it would take this session past its credit limit\./;
const short = (l) => (l ? `${l.decision}/${l.kind} paths=${JSON.stringify(l.paths)} w=${l.cmdWorst} c=${l.committed} cap=${l.cap}` : "none");
const cell = (label, parts) => `    ${label.padEnd(46)} ${parts.join(" | ")}`;

/** A fresh session with no balance cached; `seed` adds state fields (a balance among them). */
function fresh(seed) {
  const s = session({ balance: null });
  if (seed) s.seed(seed);
  return s;
}

/** A copy of hooks/ (guard, ledger, costs.json) in a temp dir, costs.json rewritten by `edit`. */
function hooksCopy(edit, withLedger = true) {
  const d = mkdtempSync(join(tmpdir(), "sc-r14b-hooks-"));
  copyFileSync(GUARD, join(d, "credit-guard.mjs"));
  if (withLedger) copyFileSync(LEDGER, join(d, "ledger.mjs"));
  const costs = JSON.parse(readFileSync(COSTS, "utf8"));
  writeFileSync(join(d, "costs.json"), JSON.stringify(edit ? edit(costs) : costs));
  return d;
}

/**
 * A preload that makes path.join throw on a "sessions" segment: inside the guard's main() and
 * outside its inner try, where the session file's path is built (the only join with that segment).
 * It was crypto.createHash until 0.4.0, which dropped the command's hash with the pending quote
 * (D28a), and os.tmpdir() until 0.3.1.
 */
function outerThrows() {
  const d = mkdtempSync(join(tmpdir(), "sc-r14b-throw-"));
  const f = join(d, "outer-throws.mjs");
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `const path = createRequire(import.meta.url)("node:path");\n` +
    `const real = path.join;\n` +
    `path.join = (...a) => { if (a.includes("sessions")) throw new Error("forced by the R14b fixture"); return real(...a); };\n` +
    `syncBuiltinESMExports();\n`);
  return pathToFileURL(f).href;
}

/** A preload, loaded after fake-fetch.mjs, that makes the state file RO_STATE read-only as the balance is read. */
function readOnlyOnFetch() {
  const d = mkdtempSync(join(tmpdir(), "sc-r14b-ro-"));
  const f = join(d, "read-only-on-fetch.mjs");
  writeFileSync(f,
    `import { chmodSync } from "node:fs";\n` +
    `const answer = globalThis.fetch;\n` +
    `globalThis.fetch = (...a) => { chmodSync(process.env.RO_STATE, 0o444); return answer(...a); };\n`);
  return pathToFileURL(f).href;
}

/**
 * A preload that faults the state file STATE_FAULT names, as JSON [mode, path, code, n, skip]: "read"
 * makes a read of it throw `code` (EACCES by default) while saves work; "empty" makes every read
 * of it come back empty and "torn" cut off at half its length (a read while it is being written);
 * "write" makes every save of it empty the file, then throw ENOSPC (a full disk: writeFileSync
 * truncates before it writes). J6: "busy" makes a save of it throw `code` (EBUSY by default) and
 * leave the file whole; "drop" makes a save of it do nothing and not throw (a save lost without an
 * error, which R18-3 no longer detects); "lock" makes the
 * exclusive create of its lock file throw `code` (EPERM by default); "unlink" makes the delete of its
 * lock file throw `code` (EBUSY by default). Those five fault the first `n` tries after `skip`
 * untouched ones, and every try when `n` is null (3b: "read" with `n` 1 is a read that fails once).
 * Exported for the 3b fixtures (d28b.mjs), which also point it at the budget, day and temp files.
 */
export function stateFault() {
  const d = mkdtempSync(join(tmpdir(), "sc-r14b-fault-"));
  const f = join(d, "state-fault.mjs");
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `import { resolve } from "node:path";\n` +
    `const fs = createRequire(import.meta.url)("node:fs");\n` +
    `const [mode, file, code, n, skip] = JSON.parse(process.env.STATE_FAULT);\n` +
    `const hit = (p, f = file) => typeof p === "string" && resolve(p).toLowerCase() === resolve(f).toLowerCase();\n` +
    `const fail = (code) => Object.assign(new Error(code + ", forced by the R14b fixture"), { code });\n` +
    `const read = fs.readFileSync, write = fs.writeFileSync, unlink = fs.unlinkSync;\n` +
    `let tries = 0;\n` +
    `const due = () => { const i = tries++ - (skip || 0); return i >= 0 && (n == null || i < n); };\n` +
    `if (mode === "busy") fs.writeFileSync = (p, ...a) => { if (hit(p) && due()) throw fail(code || "EBUSY"); return write(p, ...a); };\n` +
    `if (mode === "drop") fs.writeFileSync = (p, ...a) => (hit(p) && due() ? undefined : write(p, ...a));\n` +
    `if (mode === "lock") fs.writeFileSync = (p, ...a) => { if (hit(p, file + ".lock") && due()) throw fail(code || "EPERM"); return write(p, ...a); };\n` +
    `if (mode === "unlink") fs.unlinkSync = (p, ...a) => { if (hit(p, file + ".lock") && due()) throw fail(code || "EBUSY"); return unlink(p, ...a); };\n` +
    `if (mode === "read") fs.readFileSync = (p, ...a) => { if (hit(p) && due()) throw fail(code || "EACCES"); return read(p, ...a); };\n` +
    `if (mode === "empty") fs.readFileSync = (p, ...a) => (hit(p) ? "" : read(p, ...a));\n` +
    `if (mode === "torn") fs.readFileSync = (p, ...a) => { const s = read(p, ...a); return hit(p) ? String(s).slice(0, String(s).length >> 1) : s; };\n` +
    `if (mode === "write") fs.writeFileSync = (p, ...a) => { if (hit(p)) { write(p, ""); throw fail("ENOSPC"); } return write(p, ...a); };\n` +
    `syncBuiltinESMExports();\n`);
  return pathToFileURL(f).href;
}

/**
 * 0.3.1 (c): a preload that holds the guard's start for SLOW_START ms (a slow Node start: the guard's
 * clock, performance.now(), counts it), then, when SLOW_LOCK is set, deletes that lock file SLOW_RELEASE
 * ms later, as a live holder letting go would. The timer is unref'd, so it never keeps the run alive.
 */
function slowStart() {
  const d = mkdtempSync(join(tmpdir(), "sc-p2-slow-"));
  const f = join(d, "slow-start.mjs");
  writeFileSync(f,
    `import { unlinkSync } from "node:fs";\n` +
    `await new Promise((r) => setTimeout(r, Number(process.env.SLOW_START)));\n` +
    `if (process.env.SLOW_LOCK) setTimeout(() => { try { unlinkSync(process.env.SLOW_LOCK); } catch {} }, Number(process.env.SLOW_RELEASE)).unref();\n`);
  return pathToFileURL(f).href;
}
/** The guard's deadline D (0.3.1), read from its source: one `const D = <ms>;` line, NaN when there is none. */
const deadlineOf = (file) => Number((readFileSync(file, "utf8").match(/^const D = (\d+);$/m) || [])[1]);
const esc = (p) => p.replace(/[\\^$.*+?()[\]{}|]/g, "\\$&");

/** The guard's environment for session `s`, as lib.mjs builds it for one run (offline; `o.fetch` answers the read). */
function guardEnv(s, o = {}) {
  const env = { ...process.env, TEMP: s.dir, TMP: s.dir, TMPDIR: s.dir };
  delete env.CLAUDE_CODE_SESSION_ATTENDED;
  delete env.CLAUDE_CODE_HOST_SCHEDULED_RUN;
  for (const k of Object.keys(env)) if (/^(socialcrawl_api_key|no_proxy)$/i.test(k)) delete env[k];
  const dead = "http://127.0.0.1:9";
  Object.assign(env, { HOME: s.dir, USERPROFILE: s.dir, SC_REVXL_HOME: s.revxl, HTTPS_PROXY: dead, HTTP_PROXY: dead, ALL_PROXY: dead, NODE_USE_ENV_PROXY: "1" });
  if (o.fetch) Object.assign(env, { FAKE_FETCH: JSON.stringify(o.fetch), FAKE_FETCH_LOG: join(s.dir, "fetches.jsonl"), SOCIALCRAWL_API_KEY: FAKE_KEY });
  return Object.assign(env, o.env || {});
}

/**
 * Starts every run at the same moment, from a driver process of its own (the fixture itself stays
 * synchronous), and returns each run's decision ("pass" when silent), message, exit code, stderr
 * and time. A run is {s, command, o}: a session, a command and the options s.run() takes (`fetch`,
 * `env`, `node`, and `event: "PostToolUse"` for a Post run). `hold` = {s, ms, release}: the driver
 * first makes that session's lock file and removes it after `ms`, saving `release` as the state
 * first when one is given, as a guard run holding the lock would. Exported for the 3b fixtures.
 */
export function atOnce(runs, hold) {
  const f = join(runs[0].s.dir, "at-once.mjs");
  writeFileSync(f,
    `import { spawn } from "node:child_process";\n` +
    `import { readFileSync, unlinkSync, writeFileSync } from "node:fs";\n` +
    `const c = JSON.parse(readFileSync(0, "utf8"));\n` +
    `const t0 = Date.now();\n` +
    `if (c.hold) writeFileSync(c.hold.lock, "", { flag: "wx" });\n` +
    `const runs = c.runs.map((r) => new Promise((done) => {\n` +
    `  const p = spawn(process.execPath, r.args, { env: r.env });\n` +
    `  let out = "", err = "";\n` +
    `  p.stdout.on("data", (b) => (out += b));\n` +
    `  p.stderr.on("data", (b) => (err += b));\n` +
    `  p.on("close", (code) => done({ out, err, code, ms: Date.now() - t0 }));\n` +
    `  p.stdin.end(JSON.stringify(r.input));\n` +
    `}));\n` +
    `if (c.hold) setTimeout(() => { if (c.hold.release != null) writeFileSync(c.hold.state, c.hold.release); unlinkSync(c.hold.lock); }, c.hold.ms);\n` +
    `Promise.all(runs).then((r) => process.stdout.write(JSON.stringify(r)));\n`);
  const r = spawnSync(process.execPath, [f], {
    input: JSON.stringify({
      runs: runs.map(({ s, command, o = {} }) => ({
        args: [...(o.fetch ? ["--import", FAKE_FETCH] : []), ...(o.node || []), GUARD],
        env: guardEnv(s, o),
        input: { session_id: s.sid, hook_event_name: o.event || "PreToolUse", tool_name: "Bash", tool_input: { command },
          ...(o.event === "PostToolUse" ? { tool_response: { stdout: "", stderr: "", interrupted: false } } : {}) },
      })),
      hold: hold ? { lock: lockOf(hold.s), state: hold.s.stateFile, ms: hold.ms, release: hold.release == null ? null : hold.release } : null,
    }),
    encoding: "utf8",
    timeout: 60000,
  });
  return JSON.parse(r.stdout || "[]").map((x) => {
    let json = null;
    try { json = x.out.trim() ? JSON.parse(x.out) : null; } catch {}
    const hso = (json && json.hookSpecificOutput) || {};
    return { decision: x.out.trim() ? hso.permissionDecision || "?" : "pass", message: (json && json.systemMessage) || "", exit: x.code, stderr: x.err, ms: x.ms };
  });
}
/** One PreToolUse run per command of session `s`, started at once; `o.hold` ms and `o.release` as atOnce()'s `hold`. */
function together(s, commands, o = {}) {
  return atOnce(commands.map((command) => ({ s, command, o })), o.hold ? { s, ms: o.hold, release: o.release } : null);
}
/** The J6 refusal: a deny, attended or not, that gives the reason `why`, names the session file and says to run it again. */
const REFUSAL = /^SocialCrawl call not run: the credit guard couldn't record it/;
function assertRefused(r, file, why, label) {
  assert(r.decision === "deny" && r.exit === 0 && !r.stderr, `${label}: refused (a deny, exit 0, no stderr), read ${r.decision} / exit ${r.exit} / ${String(r.stderr).slice(0, 120)}`, r);
  assert(REFUSAL.test(r.message) && why.test(r.message) && r.message.includes(`Session file: ${file}.`) && /Run the command again/.test(r.message),
    `${label}: the refusal gives the reason /${why.source}/, names ${file} and says to run it again, read ${r.message.slice(0, 600)}`);
}
const decs = (rs) => rs.map((r) => r.decision).join(",");
/** A session's log lines, identical ones counted: "4 x deny/lost ...". */
const logSummary = (s) => {
  const l = s.logLines().map(short);
  return l.length ? [...new Set(l)].map((x) => `${l.filter((y) => y === x).length} x ${x}`).join(" ; ") : "none";
};

export default [
  {
    id: "R14b-01-balance-values",
    desc: "READ (O3; D28): a finite data.balance is cached whatever its value and never read again. An integer balance of 0 or more gives the automatic cap min(500, 25%): 800, 400 and 1000 give 200, 100 and 250, 2000 and 4000 the 500 ceiling (not 1000), so a 50cr call passes; 4 gives 1 (a 50cr call is denied, then a 1cr call reaches it exactly); 0 and 3 give 0 (both denied); -5 and 999.5 are no readable balance, so the fallback 500 (both pass). Every deny is exactly M_LIMIT, the same unattended, and logged there",
    fn() {
      const rows = [];
      for (const [v, limit] of [[800, 200], [400, 100], [1000, 250], [2000, 500], [4000, 500], [4, 1], [0, 0], [3, 0], [-5, 500], [999.5, 500]]) {
        const src = Number.isInteger(v) && v >= 0 ? srcAuto(v) : SRC_FALLBACK;
        const msg = (s, spent, worst) => mLimit({ spent, worst, limit, src, bf: s.bf });
        const a = fresh();
        const r1 = a.run(P50, { fetch: [bal(v)] });
        const st1 = a.state();
        const r2 = a.run(P1, { fetch: [bal(v)] });
        const st = a.state();
        const u = fresh();
        const ru = u.run(P50, { fetch: [bal(v)], env: UN });
        const lu = u.logLines();
        rows.push(cell(`balance ${v} (limit ${limit})`, [`att ${r1.decision}, then ${r2.decision}`, `unatt ${ru.decision}`,
          `fetches ${a.fetches().length}+${u.fetches().length}`, `committed ${(st || {}).spent}/${(u.state() || {}).spent}`, `log ${short(lu[0])}`]));
        assert(a.fetches().length === 1 && u.fetches().length === 1, `balance ${v}: one read per session, read ${a.fetches().length} and ${u.fetches().length}`);
        const f = a.fetches()[0];
        assert(f.url === "https://www." + "social" + "crawl.dev/v1/credits/balance" && f.key && f.signal, `balance ${v}: the documented balance URL, with the key header and an abort signal, read ${JSON.stringify(f)}`);
        assert(st.balance === v && (u.state() || {}).balance === v, `balance ${v}: cached as ${v}, read ${JSON.stringify(st)}`);
        assert(r1.exit === 0 && r2.exit === 0 && ru.exit === 0, `balance ${v}: exit 0`);
        const after50 = limit >= 50 ? 50 : 0;
        if (limit >= 50) {
          assert(r1.raw === "" && st1.spent === 50 && ru.raw === "", `balance ${v}: a 50cr call passes within ${limit}, read ${r1.decision} / ${JSON.stringify(st1)}`, r1);
          assert(lu.length === 1 && lu[0].decision === "pass" && lu[0].kind === "under-cap" && lu[0].cap === limit && lu[0].committed === 50, `balance ${v}: one pass logged at cap ${limit}, read ${JSON.stringify(lu)}`);
        } else {
          assert(r1.decision === "deny" && r1.message === msg(a, 0, 50) && st1.spent === 0, `balance ${v}: a 50cr call is denied with exactly M_LIMIT, read ${r1.message}`, r1);
          assert(ru.decision === "deny" && ru.message === msg(u, 0, 50), `balance ${v}: the same deny unattended, read ${ru.message}`, ru);
          assert(lu.length === 1 && lu[0].decision === "deny" && lu[0].kind === "over-limit" && lu[0].cap === limit && lu[0].committed === 0, `balance ${v}: one over-limit deny logged, read ${JSON.stringify(lu)}`);
        }
        if (after50 + 1 <= limit) assert(r2.raw === "" && st.spent === after50 + 1, `balance ${v}: the 1cr call passes, read ${r2.decision} / ${JSON.stringify(st)}`, r2);
        else assert(r2.decision === "deny" && r2.message === msg(a, after50, 1) && st.spent === after50, `balance ${v}: the 1cr call is denied, read ${r2.message}`, r2);
        a.cleanup();
        u.cleanup();
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-02-failed-reads",
    desc: "READ (O3/O4; D28a): a 500, a string balance, a missing field, a balance outside data, a non-JSON body, a network error, a hang (the 3 s timeout), no key and a failed import of ledger.mjs are each a failed try: nothing cached, one failure counted, and the call is held to the fallback limit of 500, so a 50cr call passes, attended and unattended (logged at cap 500); no key and no ledger.mjs send nothing",
    fn() {
      const rows = [];
      const noLedger = hooksCopy(null, false);
      for (const [label, reply, o] of [
        ["HTTP 500", { status: 500, body: { data: { balance: 800 } } }, {}],
        ["string \"800\"", bal("800"), {}],
        ["missing data.balance", { body: { data: {} } }, {}],
        ["balance outside data", { body: { balance: 800 } }, {}],
        ["non-JSON body", { body: "<html>busy</html>" }, {}],
        ["network error", { throw: true }, {}],
        ["hang (3 s timeout)", { hang: true }, {}],
        ["no key", bal(800), { unsetEnv: ["SOCIALCRAWL_API_KEY"] }],
        ["no ledger.mjs (a failed import)", bal(800), { guard: join(noLedger, "credit-guard.mjs") }],
      ]) {
        const a = fresh();
        const r = a.run(P50, { fetch: [reply], ...o });
        const st = a.state();
        const u = fresh();
        const ru = label.startsWith("hang") ? null : u.run(P50, { fetch: [reply], ...o, env: UN });
        const want = label === "no key" || label.startsWith("no ledger") ? 0 : 1;
        rows.push(cell(label, [`att ${r.decision} (${r.ms} ms)`, `unatt ${ru ? ru.decision : "-"}`, `fetches ${a.fetches().length}`,
          `committed ${st.spent}`, `balanceFails ${st.balanceFails}`, `log ${ru ? short(u.logLines()[0]) : "-"}`]));
        assert(r.exit === 0, `${label}: exit 0`, r);
        assert(a.fetches().length === want, `${label}: ${want} request(s), read ${a.fetches().length}`);
        assert(st.balance === undefined && st.balanceFails === 1, `${label}: nothing cached, one failed try counted, read ${JSON.stringify(st)}`);
        assert(r.raw === "" && st.spent === 50, `${label}: the fallback limit of 500, so the 50cr call passes, read ${r.decision} / ${JSON.stringify(st)}`, r);
        if (label.startsWith("hang")) assert(r.ms >= 2500 && r.ms < 9000, `${label}: the read gives up at ~3 s, under the 10 s hook timeout, took ${r.ms} ms`);
        if (ru) {
          assertDecision(ru, null, `${label}: unattended, it passes too`);
          const l = u.logLines();
          assert(l.length === 1 && l[0].decision === "pass" && l[0].kind === "under-cap" && l[0].cap === 500 && u.state().balanceFails === 1, `${label}: unattended, the failure is kept and the pass logged at cap 500, read ${JSON.stringify(u.state())} / ${JSON.stringify(l)}`);
        }
        a.cleanup();
        u.cleanup();
      }
      rmSync(noLedger, { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-03-timeout-then-success",
    desc: "READ (O3; D28a): a read that times out is retried on the next paid command (the first passes under the fallback 500); the second read succeeds and is cached, so a third paid command makes no request (2 requests in all)",
    fn() {
      const s = fresh();
      const replies = [{ hang: true }, bal(800)];
      const rows = [];
      const steps = [[P50, null], [P1, null], [P1B, null]];
      for (const [i, [cmd, want]] of steps.entries()) {
        const r = s.run(cmd, { fetch: replies });
        const st = s.state();
        rows.push(cell(`command ${i + 1}`, [`att ${r.decision} (${r.ms} ms)`, `fetches ${s.fetches().length}`, `committed ${st.spent}`, `balance ${st.balance}`, `balanceFails ${st.balanceFails}`]));
        assertDecision(r, want, `command ${i + 1}`);
      }
      const st = s.state();
      assert(s.fetches().length === 2 && st.balance === 800 && st.balanceFails === 1 && st.spent === 52, `timeout then success: 2 requests, cached 800, 52 committed, read ${JSON.stringify(st)}`);
      console.log(rows.join("\n"));
      s.cleanup();
    },
  },
  {
    id: "R14b-04-three-failures-then-no-more",
    desc: "READ (O3; D28a): after 3 failed tries a session sends no more requests, and every paid call is held to the fallback limit of 500, so the five calls (152 credits) pass, attended and unattended; unattended, each failure is kept; no key stops trying after 3 too",
    fn() {
      const rows = [];
      for (const [label, env, want] of [["attended", {}, null], ["unattended", UN, null]]) {
        const s = fresh();
        const counts = [];
        for (let i = 0; i < 5; i++) {
          const r = s.run(i % 2 ? P1 : P50, { fetch: [{ status: 500, body: {} }], env });
          assertDecision(r, want, `${label} command ${i + 1}`);
          counts.push(s.fetches().length);
        }
        rows.push(cell(`${label}, HTTP 500 every time`, [`decisions ${want} x5`, `fetches after each ${counts.join(",")}`, `balanceFails ${s.state().balanceFails}`, `log lines ${s.logLines().length}`]));
        assert(counts.join(",") === "1,2,3,3,3" && s.state().balanceFails === 3 && s.state().spent === 152, `${label}: 3 requests, then none, and all five counted, read ${counts} / ${JSON.stringify(s.state())}`);
        s.cleanup();
      }
      const k = fresh();
      for (let i = 0; i < 5; i++) k.run(P50, { fetch: [bal(800)], unsetEnv: ["SOCIALCRAWL_API_KEY"] });
      rows.push(cell("attended, no key", [`fetches ${k.fetches().length}`, `balanceFails ${k.state().balanceFails}`]));
      assert(k.fetches().length === 0 && k.state().balanceFails === 3, `no key: nothing sent, 3 tries counted, read ${JSON.stringify(k.state())}`);
      k.cleanup();
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-05-read-counts",
    desc: "READ (J1/O3; D28): one read on a paid plain command, attended or not; none on a command that is not plain, attended or not (it is denied before any read), a free call, a 0cr call, a command with no /v1/ URL, a Post input or a cached balance; a not-plain command's deny is the same whatever the balance",
    fn() {
      const P = `${V1}prism/leads?query=x`;
      const rows = [];
      for (const [label, cmd, env, want, o] of [
        ["plain paid, attended", P50, {}, 1],
        ["plain paid, unattended", P50, UN, 1],
        ["plain transcript (3cr), attended", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, NOLOCAL, 1],
        ["not plain, echo '<URL>', attended", `echo '${P}'`, {}, 0],
        ["not plain, a loop, attended", `for i in 1 2; do curl -s "${P}"; done`, {}, 0],
        ["plain free credits/balance, attended", `curl -s "${V1}credits/balance"`, {}, 0],
        ["plain free credits/balance, unattended", `curl -s "${V1}credits/balance"`, UN, 0],
        ["plain unpriced cohorts (0cr)", `curl -s "${V1}cohorts?segment=a"`, {}, 0],
        ["plain prism/jobs (0cr, no stated max)", `curl -X POST "${V1}prism/jobs" -d '{}'`, {}, 0],
        ["no /v1/ URL: echo a docs URL", `echo see ${DOCS}/quickstart`, {}, 0],
        ["no /v1/ URL: curl a docs URL", `curl -s "${DOCS}/api/credits"`, {}, 0],
        ["not plain, echo '<URL>', unattended", `echo '${P}'`, UN, 0],
        ["not plain, grep '<URL>', unattended", `grep -rn "${P}" notes/`, UN, 0],
        ["not plain, a loop, unattended", `for i in 1 2; do curl -s "${P}"; done`, UN, 0],
        ["PostToolUse of a paid call", P50, {}, 0, { event: "PostToolUse" }],
        ["PostToolUseFailure of a paid call", P50, {}, 0, { event: "PostToolUseFailure", extra: { error: "x" } }],
      ]) {
        const s = fresh();
        const r = s.run(cmd, { fetch: [bal(800)], env, ...(o || {}) });
        rows.push(cell(label, [`decision ${r.decision}`, `fetches ${s.fetches().length}`, `committed ${(s.state() || {}).spent}`, `log ${short(s.logLines()[0])}`]));
        assert(s.fetches().length === want, `${label}: ${want} read(s), read ${s.fetches().length}`, r);
        assert(r.exit === 0, `${label}: exit 0`, r);
        s.cleanup();
      }
      const c = session().seed({ spent: 0 });                         // balance 800 seeded = cached
      const rc = c.run(P50, { fetch: [bal(5)] });
      rows.push(cell("seeded balance 800, plain paid", [`decision ${rc.decision}`, `fetches ${c.fetches().length}`, `committed ${c.state().spent}`]));
      assert(c.fetches().length === 0 && rc.raw === "" && c.state().spent === 50 && c.state().balance === 800, `a seeded balance is cached: no read, read ${JSON.stringify(c.state())}`);
      c.cleanup();
      // Not plain, whatever the balance or the committed total: the same deny, and no read.
      for (const [label, s] of [["not plain, no balance cached, spent 0", fresh()], ["not plain, no balance cached, spent 190", fresh({ spent: 190 })], ["not plain, 800 cached, spent 190", session().seed({ spent: 190 })]]) {
        const r = s.run(`echo '${P}'`, { fetch: [bal(800)] });
        rows.push(cell(label, [`decision ${r.decision}`, `fetches ${s.fetches().length}`]));
        assert(r.decision === "deny" && r.message === M_NOTPLAIN && s.fetches().length === 0, `${label}: exactly M_NOTPLAIN and no read, read ${r.decision} / ${s.fetches().length}`, r);
        s.cleanup();
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-06-unattended-decisions",
    desc: "UNATTENDED (J1/O1/O2; D28): grep, echo and a docs URL are denied with exactly M_NOTPLAIN, no read and no state written, logged as not-plain with committed and cap null; a call past the limit after a read is denied with M_LIMIT, logged over-limit at that cap; a paid plain call within the limit after a good read passes silently and is committed; a forced throw inside the guard, in the inner try (a costs.json of the wrong shape) or outside it (the session path's join throws), denies unattended with exactly M_ERROR and passes attended, exit 0",
    fn() {
      const P = `${V1}prism/leads?query=x`;
      const rows = [];
      for (const [label, cmd, w] of [
        ["grep -rn '<URL>' notes/", `grep -rn "${P}" notes/`, 50],
        ["echo '<URL>'", `echo '${P}'`, 50],
        ["echo a docs URL", `echo see ${DOCS}/quickstart`, 0],
      ]) {
        const s = fresh();
        const r = s.run(cmd, { fetch: [bal(800)], env: UN });
        const l = s.logLines();
        rows.push(cell(`not plain: ${label}`, [`unatt ${r.decision}`, `fetches ${s.fetches().length}`, `state file ${s.stateExists()}`, `log ${short(l[0])}`]));
        assertDecision(r, "deny", `${label}: denied unattended`);
        assert(r.message === M_NOTPLAIN, `${label}: exactly M_NOTPLAIN, read ${r.message}`, r);
        assert(s.fetches().length === 0 && !s.stateExists() && l.length === 1 && l[0].kind === "not-plain" && l[0].cmdWorst === w && l[0].committed === null && l[0].cap === null,
          `${label}: no read (no request, no state written), one not-plain line at ${w}, read ${JSON.stringify(l)}`);
        s.cleanup();
      }
      const c = fresh();
      const rc = c.run(P50, { fetch: [bal(40)], env: UN });                 // limit 10: 50 is past it
      rows.push(cell("past the limit after a read of 40 (limit 10)", [`unatt ${rc.decision}`, `fetches ${c.fetches().length}`, `committed ${c.state().spent}`, `log ${short(c.logLines()[0])}`]));
      assertDecision(rc, "deny", "past the limit is denied unattended");
      assert(rc.message === limitOf(c, 0, 50, 40), `exactly M_LIMIT, read ${rc.message}`, rc);
      assert(c.logLines()[0].kind === "over-limit" && c.logLines()[0].cap === 10 && c.state().spent === 0, `logged over-limit at cap 10, nothing counted, read ${JSON.stringify(c.state())}`);
      c.cleanup();
      const p = fresh();
      const rp = p.run(P50, { fetch: [bal(800)], env: UN });
      const rp2 = p.run(P1, { fetch: [bal(800)], env: UN });
      rows.push(cell("under the cap after a read of 800", [`unatt ${rp.decision}, then ${rp2.decision}`, `fetches ${p.fetches().length}`, `committed ${p.state().spent}`, `log ${p.logLines().map(short).join(" ; ")}`]));
      assert(rp.raw === "" && rp2.raw === "" && p.state().spent === 51, `under the cap: silent, committed 51, read ${JSON.stringify(p.state())}`);
      assert(p.logLines().length === 2 && p.logLines().every((l) => l.decision === "pass" && l.kind === "under-cap"), `two paid passes logged, read ${JSON.stringify(p.logLines())}`);
      p.cleanup();
      // Forced throws. Inner: `_unpriced` a number makes the cost lookup throw inside the try.
      const d = hooksCopy((costs) => ({ ...costs, _unpriced: 5 }));
      const outer = outerThrows();
      for (const [label, o] of [["inner try (costs.json _unpriced: 5)", { guard: join(d, "credit-guard.mjs") }], ["outside the inner try (the session path's join throws)", { node: ["--import", outer] }]]) {
        const a = fresh();
        const att = a.run(P50, o);
        a.cleanup();
        const s = fresh();
        const un = s.run(P50, { ...o, env: UN });
        rows.push(cell(`forced throw, ${label}`, [`att ${att.decision} exit ${att.exit}`, `unatt ${un.decision} exit ${un.exit}`, `log ${short(s.logLines()[0])}`]));
        assert(att.exit === 0 && att.raw === "", `${label}: attended passes with exit 0, read exit ${att.exit}, stderr ${att.stderr.slice(0, 200)}`, att);
        assert(un.exit === 0 && un.decision === "deny" && un.message === mError(), `${label}: unattended denies with exactly M_ERROR, exit 0, read exit ${un.exit}, ${un.message}, stderr ${un.stderr.slice(0, 200)}`, un);
        const l = s.logLines();
        assert(l.length === 1 && l[0].decision === "deny" && l[0].kind === "error", `${label}: one error deny logged, read ${JSON.stringify(l)}`);
        s.cleanup();
      }
      rmSync(d, { recursive: true, force: true });
      rmSync(dirname(fileURLToPath(outer)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-07-the-log",
    desc: "LOG (J2/O5; D28): SC_REVXL_HOME is created when missing, else ~/.claude/revxl; each line has exactly ts, session_id, decision, kind, paths, cmdWorst, committed, cap; kind names the branch, one of exactly not-plain, lost, over-limit, under-cap and error, with cap the limit where one applies and null where none does; attended decisions and a plain free pass write nothing; no query string, comment, body or key is logged; a log that can't be written (its path a folder) changes no decision, exit code or stdout",
    fn() {
      const rows = [];
      // The folder: a missing nested SC_REVXL_HOME is created; with none, ~/.claude/revxl under HOME.
      const m = fresh();
      const nested = join(m.dir, "not", "yet", "revxl");
      m.run(`echo '${V1}prism/leads'`, { env: { ...UN, SC_REVXL_HOME: nested } });
      const home = fresh();
      home.run(`echo '${V1}prism/leads'`, { env: UN, unsetEnv: ["SC_REVXL_HOME"] });
      const fallback = join(home.dir, ".claude", "revxl", "credit-guard-unattended.jsonl");
      rows.push(cell("missing SC_REVXL_HOME / none set", [`created ${existsSync(join(nested, "credit-guard-unattended.jsonl"))}`, `~/.claude/revxl ${existsSync(fallback)}`]));
      assert(existsSync(join(nested, "credit-guard-unattended.jsonl")) && existsSync(fallback), "the log folder is created, and ~/.claude/revxl is the default");
      m.cleanup();
      home.cleanup();
      // One line per branch, each with exactly the eight fields. [committed, cap] per kind: the total as
      // read and the limit, each null where the branch decides before it exists (D28 §d).
      const costsCopy = hooksCopy((costs) => ({ ...costs, _unpriced: 5 }));
      for (const [kind, cmd, o, w, committed, cap] of [
        ["not-plain", `echo '${V1}prism/leads?query=x'`, {}, 50, null, null],
        ["lost", P50, { seed: { spent: 0, lost: true } }, 50, 0, null],
        ["over-limit", P50, { seed: { spent: 190 } }, 50, 190, 200],
        ["under-cap", P1, {}, 1, 1, 200],
        ["error", P50, { guard: join(costsCopy, "credit-guard.mjs") }, null, null, null],
      ]) {
        const s = session();
        s.seed(o.seed || { spent: 0 });
        if (o.budget) s.budget(o.budget);
        if (o.day) s.day(o.day);
        const r = s.run(cmd, { ...o, env: { ...(o.env || {}), ...UN } });
        const l = s.logLines();
        rows.push(cell(`kind ${kind}`, [`unatt ${r.decision}`, `line ${JSON.stringify(l[0])}`]));
        assert(l.length === 1, `${kind}: one line, read ${l.length}`, r);
        assert(JSON.stringify(Object.keys(l[0])) === JSON.stringify(FIELDS), `${kind}: exactly ${FIELDS.join(", ")}, read ${Object.keys(l[0])}`);
        assert(l[0].kind === kind && l[0].decision === (kind === "under-cap" ? "pass" : "deny") && l[0].cmdWorst === w, `${kind}: kind, decision and cmdWorst, read ${JSON.stringify(l[0])}`);
        assert(l[0].session_id === s.sid && !Number.isNaN(Date.parse(l[0].ts)) && Array.isArray(l[0].paths), `${kind}: the cleaned session id, an ISO ts and a paths array, read ${JSON.stringify(l[0])}`);
        assert(l[0].committed === committed && l[0].cap === cap, `${kind}: committed ${committed} and cap ${cap}, read ${JSON.stringify(l[0])}`);
        if (kind !== "error") {
          assert(l[0].paths.length === 1 && l[0].paths[0].startsWith("/v1/"), `${kind}: its path, read ${JSON.stringify(l[0])}`);
        }
        s.cleanup();
      }
      rmSync(costsCopy, { recursive: true, force: true });
      // Nothing logged: attended denies and passes, and an unattended plain free pass.
      const quiet = session().seed({ spent: 0 });
      for (const [cmd, env] of [[`echo '${V1}prism/leads'`, {}], [P1, {}], [P50, {}], [`curl -s "${V1}credits/balance"`, UN]]) quiet.run(cmd, { env });
      rows.push(cell("attended ask + silent pass, unattended free", [`log lines ${quiet.logLines().length}`, `revxl exists ${existsSync(quiet.revxl)}`]));
      assert(quiet.logLines().length === 0, `nothing logged, read ${JSON.stringify(quiet.logLines())}`);
      quiet.cleanup();
      // Canaries: a query string, a comment, a -d body and a key (in a header, a query and a path).
      const c = session().seed({ spent: 0 });
      const canaries = [
        `curl -s -H "x-api-key: sc_CANARYKEYHDR" "${V1}prism/leads?query=CANARYQS&api_key=sc_CANARYKEYQS"`,
        `echo '${V1}prism/leads?query=CANARYQS2' # CANARYCOMMENT`,
        `curl -s -X POST "${V1}youtube/videos" -d '{"ids":["CANARYBODY"]}' # CANARYCOMMENT2`,
        `curl -s "${V1}prism/leads/sc_CANARYKEYPATH"`,
      ];
      for (const cmd of canaries) c.run(cmd, { env: UN });
      const text = readFileSync(join(c.revxl, "credit-guard-unattended.jsonl"), "utf8");
      rows.push(cell("canaries (4 commands)", [`lines ${c.logLines().length}`, `paths ${c.logLines().map((l) => l.paths.join(",")).join(" ; ")}`]));
      assert(c.logLines().length === 4, `every canary command is logged, read ${c.logLines().length}`);
      assert(!/canary|curl|echo|x-api-key|sc_[a-z0-9]/i.test(text), `no command text, query, comment, body or key in the log:\n${text}`);
      c.cleanup();
      // The log can't be written (its path is a folder): the log write fails, and nothing else changes.
      // (Until 0.3.1 this made SC_REVXL_HOME a file; the session file now lives under it, so a file
      // there also leaves no session folder, which P2-A14 covers.)
      for (const [label, cmd] of [["a deny", `echo '${V1}prism/leads'`], ["a paid pass", P1]]) {
        const ok = session().seed({ spent: 0 });
        const good = ok.run(cmd, { env: UN });
        const bad = session().seed({ spent: 0 });
        const logPath = join(bad.revxl, "credit-guard-unattended.jsonl");
        mkdirSync(logPath, { recursive: true });
        const r = bad.run(cmd, { env: UN });
        rows.push(cell(`the log path is a folder, ${label}`, [`decision ${r.decision} (normal ${good.decision})`, `exit ${r.exit}`, `stdout same ${r.raw === good.raw}`, `committed ${bad.state().spent} (normal ${ok.state().spent})`]));
        assert(r.decision === good.decision && r.exit === 0 && r.raw === good.raw && bad.state().spent === ok.state().spent && statSync(logPath).isDirectory(),
          `${label}: the same decision, exit 0, stdout and count, read ${r.decision}/${r.exit}/${JSON.stringify(r.raw).slice(0, 80)}`);
        ok.cleanup();
        bad.cleanup();
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-08-notice",
    desc: "NOTICE (J3): the next prompt after new log lines carries 'N unattended denials (~Q credits blocked), M credits spent unattended since <date> → <log>' in systemMessage and additionalContext, once per batch; a triggering prompt keeps its suggestion (the jev line last); nothing new = silent; no S15-banned field",
    fn() {
      const P = `${V1}prism/leads?query=x`;
      const s = session().seed({ spent: 0 });
      for (const cmd of [`echo '${P}'`, `echo see ${DOCS}/quickstart`, P1]) s.run(cmd, { env: UN });   // deny 50, deny 0, pass 1
      const log = join(s.revxl, "credit-guard-unattended.jsonl");
      const lines = s.logLines();
      assert(lines.length === 3, `three unattended decisions logged, read ${lines.length}`);
      const day = lines[0].ts.slice(0, 16).replace("T", " ");
      const want = (n, q, m, since) => `${n} unattended denials (~${q} credits blocked), ${m} credits spent unattended since ${since} UTC → ${log}`;
      const env = { SC_REVXL_HOME: s.revxl };
      const banned = (r, label) => {
        const flat = JSON.stringify(r.json);
        for (const b of ["permissionDecision", '"decision"', '"deny"', '"block"', "stopReason", "updatedPrompt"]) assert(!flat.includes(b), `${label}: carries ${b}: ${flat.slice(0, 300)}`);
        assert(r.json.continue === undefined && r.json.suppressOutput === undefined && r.exit === 0, `${label}: no control field, exit 0`);
        assert(r.json.hookSpecificOutput.hookEventName === "UserPromptSubmit", `${label}: hookEventName`);
      };
      const rows = [];
      const first = ask("what's for lunch", { env });
      rows.push(cell("prompt 1 (3 new lines)", [`systemMessage ${JSON.stringify(first.json && first.json.systemMessage)}`]));
      assert(first.json && first.json.systemMessage === want(2, 50, 1, day) && first.context === want(2, 50, 1, day), `the notice, in both fields, read ${first.raw}`);
      banned(first, "prompt 1");
      const second = ask("what's for lunch", { env });
      rows.push(cell("prompt 2 (nothing new)", [`stdout ${JSON.stringify(second.raw)}`]));
      assert(second.raw === "" && second.exit === 0, `nothing new: silent, read ${second.raw}`);
      s.run(`curl -s "${V1}prism/leads?query=y"`, { env: UN });                      // a pass of 50 (under the cap)
      s.run(`grep -rn "${V1}amazon/product?asin=B1" notes/`, { env: UN });         // a deny of 5
      const day2 = s.logLines()[3].ts.slice(0, 16).replace("T", " ");
      const third = ask("socialcrawl this handle on ig", { env, roster: [] });
      rows.push(cell("prompt 3 (2 new lines, triggering)", [`systemMessage ${JSON.stringify(third.json && third.json.systemMessage)}`, `last line ${JSON.stringify(third.context.split("\n").pop())}`]));
      assert(third.json.systemMessage === want(1, 5, 50, day2), `only the new batch is counted, read ${third.raw}`);
      assert(/trigger: wake-word/.test(third.context) && third.context.includes(`\n${want(1, 5, 50, day2)}\n`) && third.context.split("\n").pop() === "jev: off",
        `the suggestion stays, with the notice before the jev line, read ${third.context}`);
      banned(third, "prompt 3");
      const fourth = ask("socialcrawl this handle on ig", { env, roster: [] });
      assert(fourth.json && fourth.json.systemMessage === undefined && !/unattended denials/.test(fourth.context), `a triggering prompt with nothing new has no notice, read ${fourth.raw}`);
      // A half-written line waits for its newline; the marker holds the bytes reported.
      appendFileSync(log, '{"ts":"2026-09-29T00:00:00.000Z","decision":"deny","cmdWorst":7');
      const partial = ask("what's for lunch", { env });
      appendFileSync(log, "}\n");
      const done = ask("what's for lunch", { env });
      rows.push(cell("a half-written line, then its end", [`stdout ${JSON.stringify(partial.raw)}`, `then ${JSON.stringify(done.json && done.json.systemMessage)}`]));
      assert(partial.raw === "" && done.json.systemMessage === want(1, 7, 0, "2026-09-29 00:00"), `a partial line is not read until whole, read ${partial.raw} / ${done.raw}`);
      assert(readFileSync(join(s.revxl, "credit-guard-unattended.seen"), "utf8") === String(statSync(log).size), "the marker holds the log's size");
      console.log(rows.join("\n"));
      s.cleanup();
    },
  },
  {
    id: "R14b-09-exit-codes",
    desc: "EXIT (O6): no process.exit( in credit-guard.mjs, ledger.mjs, jev.mjs or price.mjs; ledger.mjs exits 0 after a fetch (a loopback server) and 2 over a ceiling; the guard's decision reaches stdout with exit 0 after a balance read over a real loopback socket",
    fn() {
      const hits = ["credit-guard.mjs", "ledger.mjs", "jev.mjs", "price.mjs"].filter((f) => readFileSync(join(HOOKS, f), "utf8").includes("process.exit("));
      assert(!hits.length, `process.exit( found in ${hits.join(", ")}`);
      const d = mkdtempSync(join(tmpdir(), "sc-r14b-exit-"));
      const redirect = join(d, "redirect.mjs");
      writeFileSync(redirect, "const real = globalThis.fetch;\nglobalThis.fetch = (url, init) => { const u = new URL(String(url)); return real(process.env.LOOP + u.pathname + u.search, init); };\n");
      const state = join(d, "revxl", "sessions", "socialcrawl-r14b9.json");   // the guard's session file, SC_REVXL_HOME = d/revxl
      mkdirSync(dirname(state), { recursive: true });
      writeFileSync(state, JSON.stringify({ spent: 190 }));
      const drv = join(d, "driver.mjs");
      writeFileSync(drv,
        `import http from "node:http";\nimport { spawn } from "node:child_process";\n` +
        `const hits = [];\n` +
        `const server = http.createServer((req, res) => { hits.push(req.url); res.setHeader("content-type", "application/json");\n` +
        `  res.end(JSON.stringify(req.url.startsWith("/v1/credits/balance") ? { data: { balance: 800 } } : { data: { items: [], next_cursor: null }, credits_remaining: 800 })); });\n` +
        `server.keepAliveTimeout = 60000;\n` +
        `const run = (args, input) => new Promise((ok) => {\n` +
        `  const env = { ...process.env, LOOP: "http://127.0.0.1:" + server.address().port, NO_PROXY: "127.0.0.1", SOCIALCRAWL_API_KEY: ${JSON.stringify(FAKE_KEY)}, HOME: ${JSON.stringify(d)}, USERPROFILE: ${JSON.stringify(d)}, SC_REVXL_HOME: ${JSON.stringify(join(d, "revxl"))}, TEMP: ${JSON.stringify(d)}, TMP: ${JSON.stringify(d)}, TMPDIR: ${JSON.stringify(d)} };\n` +
        `  delete env.CLAUDE_CODE_SESSION_ATTENDED;\n` +
        `  const t0 = Date.now(); const c = spawn(process.execPath, ["--import", ${JSON.stringify(pathToFileURL(redirect).href)}, ...args], { env, stdio: ["pipe", "pipe", "pipe"] });\n` +
        `  let out = "", err = ""; c.stdout.on("data", (b) => (out += b)); c.stderr.on("data", (b) => (err += b));\n` +
        `  c.on("exit", (code) => ok({ code, out, err, ms: Date.now() - t0 })); c.stdin.end(input || "");\n` +
        `});\n` +
        `server.listen(0, "127.0.0.1", async () => {\n` +
        `  const ledger = await run([${JSON.stringify(LEDGER)}, "snapshot"]);\n` +
        `  const guard = await run([${JSON.stringify(GUARD)}], ${JSON.stringify(JSON.stringify({ session_id: "r14b9", hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: { command: P50 } }))});\n` +
        `  process.stdout.write(JSON.stringify({ ledger, guard, hits }));\n` +
        `  server.closeAllConnections(); server.close();\n` +
        `});\n`);
      const r = spawnSync(process.execPath, [drv], { encoding: "utf8", timeout: 60000 });
      let j = null;
      try { j = JSON.parse(String(r.stdout || "")); } catch {}
      const st = (() => { try { return JSON.parse(readFileSync(state, "utf8")); } catch { return null; } })();
      rmSync(d, { recursive: true, force: true });
      assert(j, `the driver reported nothing: ${String(r.stderr || "").slice(0, 300)}`);
      console.log(cell("ledger snapshot after a loopback fetch", [`exit ${j.ledger.code}`, `${j.ledger.ms} ms`, `stderr ${JSON.stringify(j.ledger.err.slice(0, 80))}`]));
      console.log(cell("guard, balance read over a loopback socket", [`exit ${j.guard.code}`, `${j.guard.ms} ms`, `stdout ${j.guard.out.slice(0, 60)}`, `state ${JSON.stringify(st)}`]));
      console.log(cell("loopback requests", [JSON.stringify(j.hits)]));
      assert(j.hits.some((h) => h.startsWith("/v1/credits/transactions")) && j.hits.includes("/v1/credits/balance"), `both requests reached the loopback server, read ${JSON.stringify(j.hits)}`);
      assert(j.ledger.code === 0 && /"items": \[\]/.test(j.ledger.out), `ledger snapshot: exit 0 after its fetch, read ${j.ledger.code} ${j.ledger.err.slice(0, 200)}`);
      let out = null;
      try { out = JSON.parse(j.guard.out); } catch {}
      assert(j.guard.code === 0 && out && out.hookSpecificOutput.permissionDecision === "deny" && LIMIT_RE.test(out.systemMessage || "") && st && st.balance === 800,
        `guard: exit 0 with its deny on stdout after the read (spent 190 + 50 is past the 200 limit), read ${j.guard.code} ${j.guard.out.slice(0, 120)} ${j.guard.err.slice(0, 200)}`);
      // Over the ceiling, no fetch (--after): exit 2 through process.exitCode.
      const e = mkdtempSync(join(tmpdir(), "sc-r14b-exit2-"));
      const snap = (items) => ({ takenAt: "2026-09-29T00:00:00.000Z", items, credits_remaining: 1 });
      writeFileSync(join(e, "b.json"), JSON.stringify(snap([])));
      writeFileSync(join(e, "a.json"), JSON.stringify(snap([{ id: "t1", type: "usage", amount: -40, endpoint: "/v1/prism/leads", request_id: "r1" }])));
      writeFileSync(join(e, "p.json"), JSON.stringify({ id: "o", endpoints: [{ call: "GET prism/leads", quoted: 15 }], ceiling: 35 }));
      const over = spawnSync(process.execPath, [LEDGER, "diff", join(e, "b.json"), "--after", join(e, "a.json"), "--plan", join(e, "p.json")], { encoding: "utf8", env: { ...process.env, SOCIALCRAWL_API_KEY: "", HOME: e, USERPROFILE: e } });
      rmSync(e, { recursive: true, force: true });
      console.log(cell("ledger diff over the ceiling", [`exit ${over.status}`]));
      assert(over.status === 2, `over the ceiling: exit 2, read ${over.status} ${String(over.stderr).slice(0, 200)}`);
    },
  },
  {
    id: "R14b-10-unsaved-state",
    desc: "STATE (checker X1, J6; R18-2, re-pointed 0.3.1; D28): a session state that can't be saved (no session folder, a read-only state file, or one that turns read-only as the balance is read) never lets a paid call pass silently or uncounted: each call is refused, attended and unattended (a deny that names the reason and the session file); a folder at the state path is a lost total, denied with M_LOST; a read is made only once its try is saved, so there is at most one. A <revxl>/sessions folder that can't be made is refused at once, with no lock wait, and the reason names the folder; a save that fails ENOENT is refused at once; a stray Post input ends at once",
    fn() {
      const rows = [];
      // No session folder (re-pointed from TEMP missing, 0.3.1 A14): <revxl>/sessions is a regular file, so
      // the guard can't make the folder; <revxl> itself stays a folder, so the unattended log still writes.
      const gone = (s) => {
        rmSync(dirname(s.stateFile), { recursive: true, force: true });
        writeFileSync(dirname(s.stateFile), "a regular file where the sessions folder goes");
        return {};
      };
      const goneFile = (s) => s.stateFile;
      const NOFOLDER = (s) => new RegExp(`the session folder ${esc(dirname(s.stateFile))} does not exist and can't be created \\(E[A-Z]+\\)`);
      const NOSAVE = /session file could not be saved \(E[A-Z]+\)/;
      // No session folder, the balance answering 800 (cap 200): attended 5 x 50cr, unattended 8 x 50cr. No
      // lock can be made there, so each run gives up at once (R18-2), not after a lock wait (the runs
      // are started at once).
      for (const [who, env, n] of [["attended", {}, 5], ["unattended", UN, 8]]) {
        const s = fresh();
        const rs = together(s, Array.from({ length: n }, () => P50), { fetch: [bal(800)], env: { ...env, ...gone(s) } });
        const l = s.logLines();
        const slow = Math.max(...rs.map((r) => r.ms));
        rows.push(cell(`no session folder, ${who}, ${n} x 50cr`, [`decisions ${decs(rs)}`, `fetches ${s.fetches().length}`, `slowest ${slow} ms`, `log ${l.length} x ${short(l[0])}`]));
        assert(rs.length === n && rs.every((r) => r.decision === "deny" && r.exit === 0) && s.fetches().length === 0, `no session folder, ${who}: deny x${n} and no read, read ${decs(rs)} / ${s.fetches().length} request(s)`, rs[0]);
        assert(slow < 3000, `no session folder, ${who}: no run waits out the lock wait, read ${slow} ms`);
        // No read can be saved, so the fallback limit of 500; the 50cr commit can't be saved: refused.
        for (const r of rs) assertRefused(r, goneFile(s), NOFOLDER(s), `no session folder, ${who}`);
        if (who === "unattended") {
          assert(l.length === n && l.every((x) => x.decision === "deny" && x.kind === "error" && x.cap === 500 && x.committed === 0 && x.cmdWorst === 50),
            `no session folder, unattended: ${n} error denies at the fallback cap 500, nothing committed, read ${JSON.stringify(l)}`);
        } else {
          assert(l.length === 0, `no session folder, attended: nothing logged, read ${JSON.stringify(l)}`);
        }
        s.cleanup();
      }
      // One run at a time (R18-2, checker A11): a Pre run with no session folder is refused at once, its
      // reason naming the folder, and a stray Post input there ends at once too.
      {
        const s = fresh();
        const pre = s.run(P50, { env: gone(s) });
        const post = s.post(P50, { env: gone(s) });
        rows.push(cell("no session folder, one Pre run, then a stray Post", [`Pre ${pre.decision} after ${pre.ms} ms`, `Post ${JSON.stringify(post.raw)} after ${post.ms} ms`]));
        assertRefused(pre, goneFile(s), NOFOLDER(s), "no session folder, one Pre run");
        assert(pre.ms < 1000 && post.raw === "" && post.exit === 0 && post.ms < 1000, `no session folder: Pre refused and Post done at once, read ${pre.ms} / ${post.ms} ms`, pre);
        s.cleanup();
      }
      // A save that fails ENOENT with the folder there (it went between the read and the save): the run
      // is refused at once naming the folder (R18-2, Q-d); run again it passes; a stray Post changes nothing.
      {
        const fault = stateFault();
        const s = session().seed({ spent: 0 });
        const pre = s.run(P50, { node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["busy", s.stateFile, "ENOENT"]) } });
        const ok = s.run(P50);
        const counted = s.stateRaw();
        const post = s.post(P50, { node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["busy", s.stateFile, "ENOENT"]) } });
        rows.push(cell("a save that throws ENOENT, then again, then a stray Post", [`first ${pre.decision} after ${pre.ms} ms`, `then ${ok.decision || "pass"}`, `Post ${JSON.stringify(post.raw)} after ${post.ms} ms`, `state ${s.stateRaw()}`]));
        assertRefused(pre, s.stateFile, new RegExp(`the session folder ${esc(dirname(s.stateFile))} does not exist \\(ENOENT\\)`), "a save that throws ENOENT");
        assert(pre.ms < 1000 && ok.raw === "" && JSON.parse(counted).spent === 50 && post.raw === "" && post.exit === 0 && post.ms < 1000 && s.stateRaw() === counted,
          `a save that throws ENOENT: refused at once, then counted, and the Post changes nothing, read ${pre.ms} / ${post.ms} ms / ${s.stateRaw()}`, post);
        s.cleanup();
        rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      }
      // A folder where the state file goes can't be read back: a lost total, denied with M_LOST at once.
      const fa = fresh();
      mkdirSync(fa.stateFile);
      const ra = [1, 2].map(() => fa.run(P50, { fetch: [bal(800)] }));
      rows.push(cell("a folder at the state path, attended, 2 x 50cr", [`decisions ${decs(ra)}`, `fetches ${fa.fetches().length}`, `slowest ${Math.max(...ra.map((r) => r.ms))} ms`, `lock left ${existsSync(lockOf(fa))}`]));
      assert(ra.every((r) => r.decision === "deny" && r.message === M_LOST), `a folder at the state path, attended: M_LOST, read ${decs(ra)} / ${ra[0].message}`, ra[0]);
      assert(fa.fetches().length === 0 && !existsSync(lockOf(fa)) && Math.max(...ra.map((r) => r.ms)) < 3000, `a folder at the state path, attended: no read, no lock left, no wait, read ${fa.fetches().length}`);
      fa.cleanup();
      const f = fresh();
      mkdirSync(f.stateFile);
      const rf = [];
      for (let i = 0; i < 5; i++) rf.push(f.run(P50, { fetch: [bal(800)], env: UN }));
      rows.push(cell("a folder at the state path, unattended, 5 x 50cr", [`decisions ${decs(rf)}`, `fetches ${f.fetches().length}`, `log ${f.logLines().length} x ${short(f.logLines()[0])}`]));
      assert(rf.every((r) => r.decision === "deny" && r.message === M_LOST) && f.fetches().length === 0 && f.logLines().length === 5 && f.logLines().every((x) => x.kind === "lost" && x.cap === null),
        `a folder at the state path: M_LOST x5, no read, read ${decs(rf)} / ${f.fetches().length} / ${JSON.stringify(f.logLines())}`);
      f.cleanup();
      // No session folder, the read failing: no try is made, so no request is sent and no hang is waited on.
      for (const [label, reply, n] of [["HTTP 500", { status: 500, body: {} }, 6], ["hang", { hang: true }, 3]]) {
        const s = fresh();
        const rs = together(s, Array.from({ length: n }, () => P50), { fetch: [reply], env: gone(s) });
        const slow = Math.max(...rs.map((r) => r.ms));
        rows.push(cell(`no session folder, ${label}, attended, ${n} x 50cr`, [`decisions ${decs(rs)}`, `fetches ${s.fetches().length}`, `slowest ${slow} ms`]));
        assert(rs.length === n && rs.every((r) => r.decision === "deny" && REFUSAL.test(r.message)) && s.fetches().length === 0 && slow < 3000,
          `no session folder, ${label}: refused, no request, no read waited on, read ${decs(rs)} / ${s.fetches().length} / ${slow} ms`);
        s.cleanup();
      }
      // A read-only state file with the balance cached (800, cap 200): a 1cr and a 50cr call, both under the cap.
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const s = session().seed({ spent: 0 });
        chmodSync(s.stateFile, 0o444);
        const rs = [s.run(P1, { env }), s.run(P50, { env })];
        chmodSync(s.stateFile, 0o666);
        const st = s.state();
        const l = s.logLines();
        rows.push(cell(`read-only state, 800 cached, ${who}, 1cr + 50cr`, [`decisions ${decs(rs)}`, `fetches ${s.fetches().length}`, `committed ${st.spent}`, `log ${l.map(short).join(" ; ") || "none"}`]));
        assert(st.spent === 0, `read-only, ${who}: nothing counted, read ${JSON.stringify(st)}`, rs[0]);
        for (const r of rs) assertRefused(r, s.stateFile, NOSAVE, `read-only, ${who}`);
        assertMatch(rs[0], /this command's worst case is ~1 credits/, `read-only, ${who}: names the figure`);
        if (who === "unattended") {
          assert(l.length === 2 && l.every((x) => x.decision === "deny" && x.kind === "error" && x.cap === 200 && x.committed === 0) && l[0].cmdWorst === 1 && l[1].cmdWorst === 50,
            `read-only, unattended: two error denies with their figures, read ${JSON.stringify(l)}`);
        } else assert(l.length === 0, `read-only, attended: nothing logged, read ${JSON.stringify(l)}`);
        s.cleanup();
      }
      // The state turns read-only as the balance is read (a disk that fills mid-read): neither the
      // balance nor the commit is saved, and the try already was, so no second read is made.
      const ro = readOnlyOnFetch();
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const s = fresh({ spent: 0 });
        const o = { fetch: [bal(800)], node: ["--import", ro], env: { ...env, RO_STATE: s.stateFile } };
        const rs = [s.run(P50, o), s.run(P50, o), s.run(P1, o)];
        const st = s.state();
        chmodSync(s.stateFile, 0o666);
        const l = s.logLines();
        rows.push(cell(`read-only once read, ${who}, 50 + 50 + 1cr`, [`decisions ${decs(rs)}`, `fetches ${s.fetches().length}`, `state ${JSON.stringify(st)}`, `log ${l.map((x) => `${x.decision}/${x.kind} cap=${x.cap}`).join(" ; ") || "none"}`]));
        assert(rs.every((r) => r.decision === "deny") && s.fetches().length === 1 && st.spent === 0 && st.balance === undefined && st.balanceFails === 1,
          `read-only once read, ${who}: deny x3, one read, nothing counted, read ${decs(rs)} / ${s.fetches().length} / ${JSON.stringify(st)}`, rs[0]);
        assertRefused(rs[0], s.stateFile, NOSAVE, `read-only once read, ${who}: the read balance's commit can't be saved`);
        // Then no balance can be saved or read: the fallback limit of 500, and each commit is refused.
        for (const r of rs.slice(1)) assertRefused(r, s.stateFile, NOSAVE, `read-only once read, ${who}: then the commit can't be saved`);
        if (who === "unattended") {
          assert(l.map((x) => `${x.decision}/${x.kind}/${x.cap}`).join(",") === "deny/error/200,deny/error/500,deny/error/500", `read-only once read, unattended: logged, read ${JSON.stringify(l)}`);
        }
        s.cleanup();
      }
      rmSync(dirname(fileURLToPath(ro)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-11-post-run-errors",
    desc: "POST (checker X2; D28a): a stray PostToolUse or PostToolUseFailure input, with an error forced outside the guard's inner try (the session path's join throws), prints nothing, logs nothing, writes nothing, adds nothing to the next notice and exits 0, attended or not; the same error before a command still denies unattended, with exactly M_ERROR",
    fn() {
      const rows = [];
      const outer = outerThrows();
      for (const [event, failure] of [["PostToolUse", false], ["PostToolUseFailure", true]]) {
        for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
          const s = fresh();
          const r = s.post(P50, { failure, node: ["--import", outer], env });
          const note = ask("what's for lunch", { env: { SC_REVXL_HOME: s.revxl } });
          rows.push(cell(`${event}, ${who}, the join throws`, [`exit ${r.exit}`, `stdout ${JSON.stringify(r.raw.slice(0, 60))}`, `log lines ${s.logLines().length}`, `next notice ${JSON.stringify(note.raw.slice(0, 60))}`]));
          assert(r.exit === 0 && r.raw === "" && !r.stateWritten && s.logLines().length === 0 && note.raw === "",
            `${event}, ${who}: exit 0, nothing printed, logged, written or noticed, read exit ${r.exit}, stdout ${r.raw.slice(0, 160)}, stderr ${r.stderr.slice(0, 160)}, log ${JSON.stringify(s.logLines())}`);
          s.cleanup();
        }
      }
      const s = fresh();
      const pre = s.run(P50, { node: ["--import", outer], env: UN });
      rows.push(cell("PreToolUse, unattended, the join throws", [`decision ${pre.decision}`, `exit ${pre.exit}`, `log ${short(s.logLines()[0])}`]));
      assert(pre.decision === "deny" && pre.message === mError() && pre.exit === 0 && s.logLines().length === 1 && s.logLines()[0].kind === "error", `PreToolUse, unattended: still denied with M_ERROR and logged, read ${pre.decision} / ${pre.message} / ${JSON.stringify(s.logLines())}`);
      s.cleanup();
      rmSync(dirname(fileURLToPath(outer)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-12-J4-damaged-state",
    desc: "LOST TOTAL (J4, checker X3; D28): a state file damaged after {spent 190, balance 800} (a save that empties it and then fails ENOSPC; torn JSON; empty; null; []; a string or null spent) is a lost total: no balance read, and 4 x 50cr are each denied with exactly M_LOST, attended and unattended (logged lost, cap null), and the state is saved again with lost: true",
    fn() {
      const rows = [];
      const fault = stateFault();
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        // A 1cr call within the limit whose commit save empties the file, then fails; then 4 x 50cr.
        const s = session().seed({ spent: 190 });
        const first = s.run(P1, { fetch: [bal(800)], node: ["--import", fault], env: { ...env, STATE_FAULT: JSON.stringify(["write", s.stateFile]) } });
        const left = s.stateRaw();
        const rs = [1, 2, 3, 4].map(() => s.run(P50, { fetch: [bal(800)], env }));
        const st = s.state();
        rows.push(cell(`save empties the file, ENOSPC, ${who}`, [`1cr ${first.decision} (file left ${JSON.stringify(left)})`, `then 4 x 50cr ${decs(rs)}`,
          `fetches ${s.fetches().length}`, `committed ${st && st.spent}, lost ${st && st.lost}`, `log ${logSummary(s)}`]));
        assert(left === "", `${who}: the failed save leaves the file empty, read ${JSON.stringify(left)}`, first);
        assertRefused(first, s.stateFile, /session file could not be saved \(ENOSPC\)/, `${who}: the commit that can't be saved`);
        assertMatch(first, /this command's worst case is ~1 credits/, `${who}: the refusal names its figure`);
        assert(rs.every((r) => r.decision === "deny" && r.message === M_LOST && r.exit === 0) && s.fetches().length === 0, `${who}: after the emptied file, M_LOST x4 and no balance read, read ${decs(rs)} / ${s.fetches().length} read(s)`, rs[0]);
        assert(st && st.lost === true && st.spent === 0 && !("pending" in st), `${who}: saved again as lost, read ${s.stateRaw()}`);
        if (who === "unattended") {
          const l = s.logLines();
          assert(l.length === 5 && l[0].kind === "error" && l[0].committed === 190 && l[0].cap === 200 && l.slice(1).every((x) => x.decision === "deny" && x.kind === "lost" && x.cap === null && x.cmdWorst === 50 && x.committed === 0),
            `unattended: the error deny, then 4 lost denies at cap null, read ${JSON.stringify(l)}`);
        }
        s.cleanup();
        // The file already damaged, each way, then 4 x 50cr with the balance answering 800.
        for (const [label, text] of [["torn JSON", '{"spent":190,"pend'], ["empty", ""], ["null", "null"], ["[]", "[]"],
          ["a string spent", '{"spent":"190"}'], ["a null spent, balance kept", '{"spent":null,"balance":800}']]) {
          const d = fresh();
          writeFileSync(d.stateFile, text);
          const rd = [1, 2, 3, 4].map(() => d.run(P50, { fetch: [bal(800)], env }));
          const sd = d.state();
          rows.push(cell(`${label}, ${who}`, [`4 x 50cr ${decs(rd)}`, `fetches ${d.fetches().length}`, `committed ${sd && sd.spent}, lost ${sd && sd.lost}`, `log ${logSummary(d)}`]));
          assert(rd.every((r) => r.decision === "deny" && r.message === M_LOST && r.exit === 0) && d.fetches().length === 0, `${label}, ${who}: M_LOST x4 and no balance read, read ${decs(rd)} / ${d.fetches().length} read(s)`, rd[0]);
          assert(sd && sd.lost === true && sd.spent === 0 && sd.balance === undefined, `${label}, ${who}: saved as lost, read ${d.stateRaw()}`);
          if (who === "unattended") {
            assert(d.logLines().length === 4 && d.logLines().every((x) => x.decision === "deny" && x.kind === "lost" && x.cap === null && x.committed === 0),
              `${label}: 4 lost denies at cap null, read ${JSON.stringify(d.logLines())}`);
          }
          d.cleanup();
        }
      }
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-13-J4-unreadable-state",
    desc: "UNREADABLE STATE (J4, checker X4; J6; D28; 3b R5, H1): a state file that can't be read (EACCES on every try) while saves work is never saved over: 6 x 50cr with the balance answering 800 make no read, and each is denied with exactly M_STATEREAD, attended and unattended (logged error, committed and cap null); the file is byte-identical afterwards",
    fn() {
      const rows = [];
      const fault = stateFault();
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const s = session().seed({ spent: 190 });
        const seeded = s.stateRaw();
        const o = { fetch: [bal(800)], node: ["--import", fault], env: { ...env, STATE_FAULT: JSON.stringify(["read", s.stateFile]) } };
        const rs = [1, 2, 3, 4, 5, 6].map(() => s.run(P50, o));
        rows.push(cell(`read throws EACCES, ${who}, 6 x 50cr`, [`decisions ${decs(rs)}`, `fetches ${s.fetches().length}`, `on disk ${s.stateRaw()}`, `log ${logSummary(s)}`]));
        assert(rs.every((r) => r.decision === "deny" && r.message === mStateRead(s.stateFile) && r.exit === 0) && s.fetches().length === 0, `${who}: M_STATEREAD x6 and no balance read, read ${decs(rs)} / ${s.fetches().length} read(s) / ${rs[0].message}`, rs[0]);
        assert(s.stateRaw() === seeded, `${who}: the file is never saved over, read ${s.stateRaw()}`);
        if (who === "unattended") {
          assert(s.logLines().length === 6 && s.logLines().every((x) => x.decision === "deny" && x.kind === "error" && x.cap === null && x.committed === null),
            `unattended: 6 error denies at cap and committed null, read ${JSON.stringify(s.logLines())}`);
        }
        s.cleanup();
      }
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-14-J4-lost-for-the-session",
    desc: "LOST TOTAL (J4; D28): a lost session stays lost: after a stray Post input (which writes nothing) and later calls that read a whole file again, every paid call is still denied with exactly M_LOST, attended and unattended, with no balance read, and a saved lost: true is denied beside a cached balance; another session id in the same sessions folder is not affected (one read, a silent pass)",
    fn() {
      const rows = [];
      const TORN = '{"spent":190,"pend';
      const o = { fetch: [bal(800)] };
      // Attended: the damaged file, a 50cr call, a stray Post, then a 1cr and a 50cr call.
      const a = fresh();
      writeFileSync(a.stateFile, TORN);
      const r1 = a.run(P50, o);
      const saved = a.stateRaw();
      const post = a.post(P50, o);
      const afterPost = a.state();
      const r2 = a.run(P1, o);
      const r3 = a.run(P50, o);
      const st = a.state();
      rows.push(cell("attended: damaged, 50cr, Post, 1cr, 50cr", [`decisions ${r1.decision}, post ${JSON.stringify(post.raw)}, ${r2.decision}, ${r3.decision}`, `fetches ${a.fetches().length}`,
        `after Post ${JSON.stringify(afterPost)}`, `end committed ${st.spent}, lost ${st.lost}`]));
      assert([r1, r2, r3].every((r) => r.decision === "deny" && r.message === M_LOST) && post.raw === "" && a.fetches().length === 0, `attended: M_LOST x3 and no read, read ${decs([r1, r2, r3])} / ${a.fetches().length}`, r2);
      assert(afterPost && afterPost.lost === true && afterPost.spent === 0 && a.stateRaw() !== null && JSON.stringify(afterPost) === saved, `the stray Post writes nothing and lost stays, read ${JSON.stringify(afterPost)}`);
      assert(st.lost === true && st.spent === 0 && st.balance === undefined, `the session stays lost, nothing read, read ${JSON.stringify(st)}`);
      // Another session id in the same sessions folder: its own state, one read, a silent pass.
      const before = a.fetches().length;
      const other = a.run(P50, { ...o, extra: { session_id: "otherj4" } });
      const ost = JSON.parse(readFileSync(join(dirname(a.stateFile), "socialcrawl-otherj4.json"), "utf8"));
      rows.push(cell("another session id, same sessions folder", [`decision ${other.decision}`, `fetches +${a.fetches().length - before}`, `its state ${JSON.stringify(ost)}`, `the lost one untouched ${JSON.stringify(a.state()) === JSON.stringify(st)}`]));
      assert(other.raw === "" && a.fetches().length - before === 1 && ost.balance === 800 && ost.spent === 50 && ost.lost === undefined, `another session: one read and a silent pass, read ${other.decision} / ${JSON.stringify(ost)}`, other);
      assert(JSON.stringify(a.state()) === JSON.stringify(st), `the lost session's file is untouched, read ${a.stateRaw()}`);
      a.cleanup();
      // Unattended: saved as lost on the first deny, and every later call is denied too.
      const u = fresh();
      writeFileSync(u.stateFile, TORN);
      const ru = [P50, P50, P1].map((c) => u.run(c, { ...o, env: UN }));
      rows.push(cell("unattended: damaged, 50 + 50 + 1cr", [`decisions ${decs(ru)}`, `fetches ${u.fetches().length}`, `state ${u.stateRaw()}`, `log ${logSummary(u)}`]));
      assert(ru.every((r) => r.decision === "deny" && r.message === M_LOST) && u.fetches().length === 0 && u.state() && u.state().lost === true, `unattended: M_LOST x3, no read, saved as lost, read ${decs(ru)} / ${u.stateRaw()}`);
      assert(u.logLines().length === 3 && u.logLines().every((x) => x.kind === "lost" && x.cap === null), `unattended: 3 lost denies at cap null, read ${JSON.stringify(u.logLines())}`);
      u.cleanup();
      // A saved lost: true beside a cached balance: still denied, and no read.
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const c = session().seed({ spent: 0, lost: true });
        const r = c.run(P1, { ...o, env });
        rows.push(cell(`lost: true beside balance 800, ${who}, 1cr`, [`decision ${r.decision}`, `fetches ${c.fetches().length}`, `log ${logSummary(c)}`]));
        assert(r.decision === "deny" && r.message === M_LOST && c.fetches().length === 0, `lost beside a balance, ${who}: M_LOST, no read, read ${r.decision} / ${c.fetches().length}`, r);
        c.cleanup();
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-15-J5-key-anywhere-in-a-path",
    desc: "LOG (J5, checker X5): every sc_ run anywhere in a logged path, in any case, up to the next /, ? or #, is logged as sc_… (mid-segment, uppercase SC_, a segment end, two segments, before ? and before #); the rest of the path is kept as it was",
    fn() {
      const K = "sc_" + "CANARYJ5KEY0000000000000000000000";
      const K2 = "sc_" + "SECONDJ5KEY1111111111111111111111";
      const rows = [];
      for (const [label, cmd, want] of [
        ["mid-segment", `curl -s "${V1}prism/leads/x${K}"`, ["/v1/prism/leads/xsc_…"]],
        ["uppercase SC_", `curl -s "${V1}prism/leads/x${K.toUpperCase()}"`, ["/v1/prism/leads/xsc_…"]],
        ["a segment end, path after it", `curl -s "${V1}prism/x${K}/leads"`, ["/v1/prism/xsc_…/leads"]],
        ["two segments", `curl -s "${V1}prism/a${K}/b${K2}"`, ["/v1/prism/asc_…/bsc_…"]],
        ["before ?", `curl -s "${V1}prism/leads/x${K}?query=a"`, ["/v1/prism/leads/xsc_…"]],
        ["before #", `echo '${V1}prism/leads/x${K}#part'`, ["/v1/prism/leads/xsc_…"]],
        ["a whole segment (control)", `curl -s "${V1}prism/leads/${K}"`, ["/v1/prism/leads/sc_…"]],
        ["no key (control)", `curl -s "${V1}prism/leads?query=a"`, ["/v1/prism/leads"]],
      ]) {
        const s = session().seed({ spent: 0 });
        const r = s.run(cmd, { env: UN });
        const l = s.logLines();
        const text = existsSync(join(s.revxl, "credit-guard-unattended.jsonl")) ? readFileSync(join(s.revxl, "credit-guard-unattended.jsonl"), "utf8") : "";
        rows.push(cell(label, [`unatt ${r.decision}`, `log ${l.map((x) => `${x.decision}/${x.kind} ${JSON.stringify(x.paths)}`).join(" ; ") || "none"}`]));
        assert(l.length === 1 && JSON.stringify(l[0].paths) === JSON.stringify(want), `${label}: logged ${JSON.stringify(want)}, read ${JSON.stringify(l)}`);
        assert(!/canaryj5|secondj5|sc_[a-z0-9]/i.test(text), `${label}: no key in the log:\n${text}`);
        s.cleanup();
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-16-J4-post-run",
    desc: "LOST TOTAL IN A POST RUN, GONE (J4, checker X6; D28a): the guard no longer runs after a command, so a stray PostToolUse or PostToolUseFailure input whose state read would fault (EBUSY, EPERM, an empty or cut-off read) reads and writes nothing: the session is never saved as lost (the wedge 0.3.1 pinned here), and the next paid calls count on from the same total, reaching the 200 limit exactly; the same holds unattended",
    fn() {
      const rows = [];
      const fault = stateFault();
      const o = { fetch: [bal(800)] };
      for (const [label, seeded, mode, code, failure] of [
        ["no balance cached, Post read EBUSY", false, "read", "EBUSY", false],
        ["no balance cached, Post read empty", false, "empty", null, false],
        ["{spent 0, balance 800}, PostToolUseFailure read EPERM", true, "read", "EPERM", true],
        ["{spent 0, balance 800}, Post read cut off", true, "torn", null, false],
      ]) {
        const s = seeded ? session().seed({ spent: 0 }) : fresh();
        const first = s.run(P50, o);
        const reads = s.fetches().length;
        const before = s.stateRaw();
        const post = s.post(P50, { ...o, failure, node: ["--import", fault], env: { STATE_FAULT: JSON.stringify([mode, s.stateFile, code]) } });
        const after = s.stateRaw();
        const rs = [1, 2, 3].map(() => s.run(P50, o));
        const st = s.state();
        rows.push(cell(`attended, ${label}`, [`50cr ${first.decision || "pass"}`, `Post ${JSON.stringify(post.raw)}, state unchanged ${after === before}`, `3 x 50cr ${rs.map((r) => r.decision || "pass").join(",")}`,
          `fetches ${s.fetches().length}`, `end committed ${st && st.spent}, lost ${st && st.lost}`]));
        assert(first.raw === "" && reads === (seeded ? 0 : 1), `${label}: the 50cr call passes, read ${first.decision} / ${reads} read(s)`, first);
        assert(post.raw === "" && post.exit === 0 && after === before, `${label}: the stray Post writes nothing, read ${after}`, post);
        assert(rs.every((r) => r.raw === "") && st && st.spent === 200 && !st.lost && s.fetches().length === reads,
          `${label}: never lost, so 3 x 50cr pass to 200 with no new read, read ${decs(rs)} / ${JSON.stringify(st)}`, rs[0]);
        s.cleanup();
      }
      // Unattended: a silent 50cr pass, its stray Post can't read the state (EBUSY), then 3 x 50cr.
      const u = session().seed({ spent: 0 });
      const pass = u.run(P50, { ...o, env: UN });
      const before = u.stateRaw();
      const upost = u.post(P50, { ...o, node: ["--import", fault], env: { ...UN, STATE_FAULT: JSON.stringify(["read", u.stateFile, "EBUSY"]) } });
      const after = u.stateRaw();
      const ru = [1, 2, 3].map(() => u.run(P50, { ...o, env: UN }));
      rows.push(cell("unattended, a pass, its Post read EBUSY", [`50cr ${pass.decision || "pass"}`, `Post ${JSON.stringify(upost.raw)}, state unchanged ${after === before}`, `3 x 50cr ${ru.map((r) => r.decision || "pass").join(",")}`,
        `fetches ${u.fetches().length}`, `log ${logSummary(u)}`]));
      assert(pass.raw === "" && upost.raw === "" && after === before, `unattended: a silent pass, then the stray Post writes nothing, read ${after}`, upost);
      assert(ru.every((r) => r.raw === "") && u.state().spent === 200 && !u.state().lost, `unattended: never lost, 3 x 50cr pass to 200, read ${decs(ru)} / ${u.stateRaw()}`, ru[0]);
      const ul = u.logLines();
      assert(ul.length === 4 && ul.every((x) => x.decision === "pass" && x.kind === "under-cap"), `unattended: 4 passes logged and nothing for the Post, read ${JSON.stringify(ul)}`);
      u.cleanup();
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-17-X7-one-run-at-a-time",
    desc: "LOCK (checker X7, J6; D28): guard runs of one session take turns on <state>.lock. A run that can't get a held lock within 4 s saves nothing, reads no balance, and refuses its paid call, attended and unattended; one that waits counts from the total the holder saved (and is denied with M_LIMIT past it); a lock older than 10 s is cleared; a stray Post input never waits on the lock and writes nothing; 12-16 runs started at once pass at most 4 x 50cr under the 200 limit (reaching it exactly), commit exactly what passed, deny or refuse the rest, and make one balance read between them",
    fn() {
      const rows = [];
      const o = { fetch: [bal(800)] };
      // A lock held the whole time, {spent 0, balance 800}: the 4 s wait runs out.
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const s = session().seed({ spent: 0 });
        const seeded = s.stateRaw();
        writeFileSync(`${s.stateFile}.lock`, "");
        const r = s.run(P50, { ...o, env });
        const l = s.logLines();
        rows.push(cell(`lock held throughout, ${who}, 50cr`, [`decision ${r.decision}`, `${r.ms} ms`, `fetches ${s.fetches().length}`, `state unchanged ${s.stateRaw() === seeded}`,
          `lock left ${existsSync(`${s.stateFile}.lock`)}`, `log ${logSummary(s)}`]));
        assert(r.ms >= 3900 && r.ms < 9000, `lock held, ${who}: refused after the 4 s wait, read ${r.decision} after ${r.ms} ms`, r);
        assertRefused(r, s.stateFile, /session lock .* could not be taken in 4 seconds \(EEXIST\)/, `lock held, ${who}`);
        assertMatch(r, /this command's worst case is ~50 credits/, `lock held, ${who}: names the figure`);
        assert(s.stateRaw() === seeded && s.fetches().length === 0 && existsSync(`${s.stateFile}.lock`), `lock held, ${who}: nothing saved, no read, the holder's lock kept, read ${s.stateRaw()} / ${s.fetches().length}`);
        if (who === "unattended") {
          assert(l.length === 1 && l[0].decision === "deny" && l[0].kind === "error" && l[0].cmdWorst === 50 && l[0].committed === 0 && l[0].cap === 200, `lock held, unattended: one error deny, read ${JSON.stringify(l)}`);
        }
        s.cleanup();
      }
      // The same with no balance cached: no read is made without the lock.
      const nb = fresh();
      writeFileSync(`${nb.stateFile}.lock`, "");
      const rnb = nb.run(P50, o);
      rows.push(cell("lock held throughout, no balance cached, 50cr", [`decision ${rnb.decision}`, `${rnb.ms} ms`, `fetches ${nb.fetches().length}`, `state ${JSON.stringify(nb.stateRaw())}`]));
      assert(rnb.ms >= 3900 && nb.fetches().length === 0 && nb.stateRaw() === null, `lock held, no balance: no read, nothing saved, read ${rnb.decision} / ${nb.fetches().length} / ${nb.stateRaw()}`, rnb);
      assertRefused(rnb, nb.stateFile, /session lock .* could not be taken in 4 seconds \(EEXIST\)/, "lock held, no balance");
      nb.cleanup();
      // A lock left by a killed run (60 s old) is cleared, and the call passes as usual.
      const k = session().seed({ spent: 0 });
      writeFileSync(`${k.stateFile}.lock`, "");
      const old = new Date(Date.now() - 60000);
      utimesSync(`${k.stateFile}.lock`, old, old);
      const rk = k.run(P50, o);
      rows.push(cell("a 60 s old lock, 50cr", [`decision ${rk.decision || "pass"}`, `${rk.ms} ms`, `committed ${k.state().spent}`, `lock left ${existsSync(`${k.stateFile}.lock`)}`]));
      assert(rk.raw === "" && rk.ms < 3000 && k.state().spent === 50 && !existsSync(`${k.stateFile}.lock`), `a stale lock: cleared, a silent pass, read ${rk.decision} / ${rk.ms} ms / ${k.stateRaw()} / lock ${existsSync(`${k.stateFile}.lock`)}`, rk);
      k.cleanup();
      // A holder saves {spent 190} and lets go after 1.5 s: the waiting run counts from 190, so 50cr is past the limit.
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const w = session().seed({ spent: 0 });
        const [r] = together(w, [P50], { ...o, env, hold: 1500, release: JSON.stringify({ balance: 800, spent: 190 }) });
        const st = w.state();
        rows.push(cell(`lock let go after 1.5 s at spent 190, ${who}`, [`decision ${r.decision}`, `${r.ms} ms`, `state ${JSON.stringify(st)}`, `log ${logSummary(w)}`]));
        assert(r.decision === "deny" && r.exit === 0 && r.ms >= 1400, `waited, ${who}: denied once the lock is let go, read ${r.decision} after ${r.ms} ms`, r);
        assert(r.message === limitOf(w, 190, 50), `waited, ${who}: M_LIMIT from the holder's 190, read ${r.message.slice(0, 400)}`);
        assert(st.spent === 190 && !existsSync(`${w.stateFile}.lock`), `waited, ${who}: 190 kept and the lock let go, read ${JSON.stringify(st)}`);
        w.cleanup();
      }
      // A stray Post input with the lock held throughout: it never waits on the lock and writes nothing.
      const p = session().seed({ spent: 190 });
      const deny1 = p.run(P50, o);
      writeFileSync(`${p.stateFile}.lock`, "");
      const before = p.stateRaw();
      const pr = p.post(P50, o);
      rows.push(cell("stray Post, lock held throughout", [`Pre ${deny1.decision}`, `Post ${pr.ms} ms`, `state unchanged ${p.stateRaw() === before}`, `lock left ${existsSync(`${p.stateFile}.lock`)}`]));
      assert(deny1.decision === "deny" && pr.raw === "" && pr.ms < 3000 && p.stateRaw() === before && existsSync(`${p.stateFile}.lock`),
        `stray Post: no wait, nothing written, the holder's lock left, read ${pr.ms} ms / ${p.stateRaw()}`, pr);
      p.cleanup();
      // Runs started at once: 16 attended and 12 unattended with {spent 0, balance 800}, 12 unattended with no balance cached.
      for (const [label, env, n, seeded] of [["16 attended", {}, 16, true], ["12 unattended", UN, 12, true], ["12 unattended, no balance cached", UN, 12, false]]) {
        const s = seeded ? session().seed({ spent: 0 }) : fresh();
        const rs = together(s, Array.from({ length: n }, (_, i) => P50N(i)), { ...o, env });
        const st = s.state() || {};
        const passes = rs.filter((r) => r.decision === "pass").length;
        const others = rs.filter((r) => r.decision !== "pass");
        const l = s.logLines();
        rows.push(cell(`${label} at once, 50cr each`, [`decisions ${rs.map((r) => (REFUSAL.test(r.message) ? "R" : r.decision[0])).join("")}`, `passes ${passes}`, `committed ${st.spent}, lost ${st.lost}`,
          `fetches ${s.fetches().length}`, `slowest ${Math.max(...rs.map((r) => r.ms))} ms`, `log ${l.length} lines`]));
        assert(rs.length === n && rs.every((r) => r.exit === 0 && r.stderr === ""), `${label}: every run exits 0 with no stderr, read ${JSON.stringify(rs.map((r) => [r.exit, r.stderr.slice(0, 80)]))}`);
        assert(passes <= 4 && st.spent === 50 * passes && !st.lost && !("pending" in st), `${label}: at most 4 silent passes and exactly those committed, read ${passes} passes / ${JSON.stringify(st)}`);
        assert(others.every((r) => r.decision === "deny" && (LIMIT_RE.test(r.message) || REFUSAL.test(r.message))), `${label}: every other run is denied past the limit or refused, read ${decs(others)}`);
        assert(s.fetches().length === (seeded ? 0 : 1) && !existsSync(`${s.stateFile}.lock`), `${label}: ${seeded ? "no" : "one"} balance read and no lock left, read ${s.fetches().length} / ${existsSync(`${s.stateFile}.lock`)}`);
        if (env === UN) {
          assert(l.length === n && l.filter((x) => x.decision === "pass").length === passes, `${label}: one log line per run, the passes among them, read ${l.length} / ${JSON.stringify(l.map((x) => x.decision))}`);
        }
        s.cleanup();
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-18-J6-cant-record-refuses",
    desc: "REFUSAL (J6, checkers X9/X10; D28): a run that can't record its commit (a lock left behind the whole 4 s wait, a save that throws with the file left whole) refuses the call, attended and unattended: a deny that gives the reason, names the session file and says to run it again, logged unattended as deny/error, with nothing saved and no balance read; a command that is not plain is denied before the lock, so it never waits on one. Run again once it can save, the call passes and is committed, so nothing later passes on a total that is missing it. Runs queued behind slow balance reads pass only with their commit saved; the ones whose wait runs out are refused",
    fn() {
      const rows = [];
      const fault = stateFault();
      const o = { fetch: [bal(800)] };
      const faulted = (s, spec, env = {}) => ({ ...o, node: ["--import", fault], env: { ...env, STATE_FAULT: JSON.stringify([spec[0], s.stateFile, ...spec.slice(1)]) } });
      const HELD = /session lock .* could not be taken in 4 seconds \(EEXIST\)/;
      // A lock a killed run left behind (younger than 10 s) the whole wait, {spent 0, balance 800}, a
      // plain 150cr chain: refused, attended and unattended; the same lock and a 150cr command that is
      // not plain: denied at once, before the lock. All four runs are started at once.
      const a = session().seed({ spent: 0 });
      const u = session().seed({ spent: 0 });
      const n = session().seed({ spent: 0 });
      const seeded = a.stateRaw();
      for (const s of [a, u, n]) writeFileSync(lockOf(s), "");
      const [ra, ru, rn] = atOnce([{ s: a, command: P150, o }, { s: u, command: P150, o: { ...o, env: UN } }, { s: n, command: NP150, o }]);
      rows.push(cell("a lock left behind, attended, 150cr", [`decision ${ra.decision}`, `${ra.ms} ms`, `fetches ${a.fetches().length}`, `state unchanged ${a.stateRaw() === seeded}`, `lock kept ${existsSync(lockOf(a))}`, "log none"]));
      rows.push(cell("a lock left behind, unattended, 150cr", [`decision ${ru.decision}`, `${ru.ms} ms`, `fetches ${u.fetches().length}`, `state unchanged ${u.stateRaw() === seeded}`, `log ${logSummary(u)}`]));
      rows.push(cell("a lock left behind, not plain, 150 visible", [`decision ${rn.decision}`, `${rn.ms} ms`, `state unchanged ${n.stateRaw() === seeded}`, `lock kept ${existsSync(lockOf(n))}`]));
      assert(ra.ms >= 3900 && ra.ms < 9000 && ru.ms >= 3900 && ru.ms < 9000, `a lock left behind: each plain run waits its 4 s, read ${ra.ms} / ${ru.ms} ms`);
      for (const [r, s, who] of [[ra, a, "attended"], [ru, u, "unattended"]]) {
        assertRefused(r, s.stateFile, HELD, `a lock left behind, ${who}`);
        assertMatch(r, /this command's worst case is ~150 credits/, `a lock left behind, ${who}: names the figure`);
        assert(s.stateRaw() === seeded && s.fetches().length === 0 && existsSync(lockOf(s)), `a lock left behind, ${who}: nothing saved or read, the lock untouched, read ${s.stateRaw()}`);
      }
      assert(a.logLines().length === 0, `a lock left behind, attended: nothing logged, read ${JSON.stringify(a.logLines())}`);
      const ul = u.logLines();
      assert(ul.length === 1 && ul[0].decision === "deny" && ul[0].kind === "error" && ul[0].cmdWorst === 150 && ul[0].committed === 0 && ul[0].cap === 200,
        `a lock left behind, unattended: one error deny, read ${JSON.stringify(ul)}`);
      assert(rn.decision === "deny" && rn.message === M_NOTPLAIN && rn.ms < 3000 && n.stateRaw() === seeded && existsSync(lockOf(n)),
        `not plain: denied at once, before the lock, read ${rn.decision} after ${rn.ms} ms`);
      u.cleanup();
      n.cleanup();
      // The lock gone, the same command run again: it passes and is committed; then 4 x 50cr: the first
      // reaches 200 exactly, the rest are denied.
      rmSync(lockOf(a));
      const again = a.run(P150, o);
      const afterAgain = a.state();
      const later = [1, 2, 3, 4].map(() => a.run(P50, o));
      rows.push(cell("  the lock gone: run again, then 4 x 50cr", [`decision ${again.decision || "pass"}, committed ${afterAgain.spent}`, `then ${later.map((r) => r.decision || "pass").join(",")}`, `fetches ${a.fetches().length}`]));
      assert(again.raw === "" && afterAgain.spent === 150, `run again: passes and is committed, read ${again.decision} / ${JSON.stringify(afterAgain)}`, again);
      assert(later[0].raw === "" && later.slice(1).every((r) => r.decision === "deny" && r.message === limitOf(a, 200, 50)) && a.state().spent === 200,
        `then 4 x 50cr: one to 200, three denied, read ${decs(later)} / ${a.stateRaw()}`);
      a.cleanup();
      // Six runs of a fresh session started at once, every balance read hanging to its 3 s timeout:
      // a run that gets the lock inside its 4 s wait reads, takes the fallback limit and passes with
      // its commit saved; the rest are refused.
      const q = fresh();
      const queued = Array.from({ length: 6 }, (_, i) => P50N(i));
      const qs = together(q, queued, { fetch: [{ hang: true }] });
      const qst = q.state() || {};
      const passed = qs.filter((r) => r.decision === "pass").length;
      const refused = qs.filter((r) => r.decision === "deny" && REFUSAL.test(r.message)).length;
      const slowest = Math.max(...qs.map((r) => r.ms));
      rows.push(cell("6 at once, fresh, every read hangs 3 s", [`${qs.map((r) => (REFUSAL.test(r.message) ? "R" : r.decision[0])).join("")}`, `passes ${passed}, refused ${refused}`,
        `committed ${qst.spent}`, `fetches ${q.fetches().length}`, `slowest ${slowest} ms`, `lock left ${existsSync(lockOf(q))}`]));
      assert(qs.length === 6 && qs.every((r) => r.exit === 0 && r.stderr === "") && passed >= 1 && passed + refused === 6, `slow reads: every run passes or is refused, read ${decs(qs)}`, qs[0]);
      assert(qst.spent === 50 * passed && !("pending" in qst), `slow reads: every pass is committed and nothing else, read ${passed} pass(es) / ${JSON.stringify(qst)}`);
      assert(q.fetches().length === passed && slowest < 9000 && !existsSync(lockOf(q)), `slow reads: only a run with the lock reads, every run ends under the 10 s hook timeout, no lock left, read ${q.fetches().length} / ${slowest} ms`);
      q.cleanup();
      // A save that fails while the file stays whole, {spent 0, balance 800}: at a 150cr commit and at
      // a 50cr commit.
      for (const [label, spec, why] of [
        ["a save that throws EBUSY, the file left whole", ["busy", "EBUSY"], /session file could not be saved \(EBUSY\)/],
      ]) {
        const p = session().seed({ spent: 0 });
        const park = p.run(P150, faulted(p, spec));
        rows.push(cell(`${label}: the 150cr commit`, [`att ${park.decision}`, `${park.ms} ms`, `fetches ${p.fetches().length}`, `state unchanged ${p.stateRaw() === seeded}`, `lock left ${existsSync(lockOf(p))}`]));
        assertRefused(park, p.stateFile, why, `${label}, the 150cr commit`);
        assert(p.stateRaw() === seeded && p.fetches().length === 0 && !existsSync(lockOf(p)) && park.ms < 3000, `${label}, the 150cr commit: nothing saved, no read, no lock left, no wait, read ${p.stateRaw()} / ${park.ms} ms`);
        p.cleanup();
        const c = session().seed({ spent: 0 });
        const commit = c.run(P50, faulted(c, spec));
        const left = c.stateRaw();
        const next = c.run(P50, o);
        rows.push(cell(`${label}: the 50cr silent commit`, [`att ${commit.decision}`, `${commit.ms} ms`, `state unchanged ${left === seeded}`, `run again ${next.decision || "pass"}, committed ${c.state().spent}`]));
        assertRefused(commit, c.stateFile, why, `${label}, the silent commit, attended`);
        assert(left === seeded && !existsSync(lockOf(c)), `${label}, the silent commit, attended: nothing committed, no lock left, read ${left}`);
        assert(next.raw === "" && c.state().spent === 50, `${label}: run again with the save working, a silent pass that is committed, read ${next.decision} / ${c.stateRaw()}`, next);
        c.cleanup();
        const n = session().seed({ spent: 0 });
        const un = n.run(P50, faulted(n, spec, UN));
        const nl = n.logLines();
        rows.push(cell(`${label}: the 50cr silent commit, unattended`, [`unatt ${un.decision}`, `${un.ms} ms`, `state unchanged ${n.stateRaw() === seeded}`, `log ${logSummary(n)}`]));
        assertRefused(un, n.stateFile, why, `${label}, the silent commit, unattended`);
        assert(n.stateRaw() === seeded && nl.length === 1 && nl[0].decision === "deny" && nl[0].kind === "error" && nl[0].cmdWorst === 50 && nl[0].committed === 0 && nl[0].cap === 200 && JSON.stringify(nl[0].paths) === '["/v1/prism/leads"]',
          `${label}, unattended: nothing committed, one error deny with the figures, read ${n.stateRaw()} / ${JSON.stringify(nl)}`);
        n.cleanup();
      }
      // The LIMIT (R18-3, Joe 10.06.26): a save lost without an error (dropped) counts as recorded, so
      // the call passes and is committed nowhere: that count is lost, undetected, attended and unattended.
      {
        const p = session().seed({ spent: 0 });
        const park = p.run(P150, faulted(p, ["drop"]));
        const c = session().seed({ spent: 0 });
        const commit = c.run(P50, faulted(c, ["drop"]));
        const un = session().seed({ spent: 0 });
        const ur = un.run(P50, faulted(un, ["drop"], UN));
        rows.push(cell("LIMIT: a save that is dropped, no error", [`150cr ${park.decision || "pass"}, committed ${p.state().spent}`, `50cr commit ${commit.decision || "pass"}, committed ${c.state().spent}`,
          `unattended ${ur.decision || "pass"}, log ${logSummary(un)}`]));
        assert(park.raw === "" && p.stateRaw() === seeded && !existsSync(lockOf(p)), `LIMIT, the 150cr commit: passes with nothing saved, read ${park.decision} / ${p.stateRaw()}`, park);
        assert(commit.raw === "" && c.stateRaw() === seeded && ur.raw === "" && un.stateRaw() === seeded && un.logLines().length === 1 && un.logLines()[0].decision === "pass",
          `LIMIT, the commit: a silent pass that is counted nowhere, attended and unattended, read ${c.stateRaw()} / ${un.stateRaw()} / ${JSON.stringify(un.logLines())}`, commit);
        p.cleanup();
        c.cleanup();
        un.cleanup();
      }
      // A fresh session (no balance cached): the read's two saves work; the commit, the third save, throws.
      const f = fresh();
      const r1 = f.run(P150, faulted(f, ["busy", "EBUSY", null, 2]));
      const left = f.state();
      const r2 = f.run(P150, o);
      const fp = f.state().spent;
      const rs = [1, 2, 3, 4, 5].map(() => f.run(P50, o));
      rows.push(cell("fresh session, the commit (3rd save) throws EBUSY", [`att ${r1.decision}`, `${r1.ms} ms`, `left ${JSON.stringify(left)}`, `run again ${r2.decision || "pass"}, committed ${fp}`, `then 5 x 50cr ${rs.map((r) => r.decision || "pass").join(",")}`, `fetches ${f.fetches().length}`, `end committed ${f.state().spent}`]));
      assertRefused(r1, f.stateFile, /session file could not be saved \(EBUSY\)/, "fresh session, the commit");
      assert(left && left.balance === 800 && left.spent === 0, `fresh session: the read balance is kept and nothing is committed, read ${JSON.stringify(left)}`);
      assert(r2.raw === "" && fp === 150 && rs[0].raw === "" && rs.slice(1).every((r) => r.decision === "deny") && f.fetches().length === 1 && f.state().spent === 200,
        `fresh session: run again it passes at 150, then one 50 to 200 and four denied on one read, read ${r2.decision} / ${fp} / ${decs(rs)} / ${f.fetches().length} / ${f.stateRaw()}`);
      f.cleanup();
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-19-J6-no-ask-without-a-saved-quote",
    desc: "NO UNCOUNTED PASS (J6; D28): every call that reaches the commit (a plain paid chain, a transcript, an unreadable endpoint, a stated maximum, and an unpriced or no-stated-maximum call at 0) passes only with its commit saved; when the commit can't be saved (the lock held, a save that throws) the call is refused and nothing is saved. A save that is dropped without an error is the R18-3 LIMIT: the call passes with nothing saved. A command that is not plain is denied before the lock and the state file, whatever they do, and a plain free call takes no lock. Every planted lock is refreshed right before the held runs start, so none ages past the 10 s stale limit under load (R18-4)",
    fn() {
      const rows = [];
      const fault = stateFault();
      const faulted = (s, spec, env = {}) => ({ node: ["--import", fault], env: { ...env, STATE_FAULT: JSON.stringify([spec[0], s.stateFile, ...spec.slice(1)]) } });
      const FAULTS = [["a save that throws", ["busy", "EBUSY"]]];
      const HELD = /session lock .* could not be taken in 4 seconds \(EEXIST\)/;
      const held = [];                                    // one lock-held run per command, all started at once below
      for (const [label, cmd, env, worst] of [
        ["a plain paid chain (150)", P150, {}, 150],
        ["a transcript (3)", `curl -s "${V1}youtube/video/${TSCRIPT}?id=a"`, NOLOCAL, 3],
        ["an unreadable endpoint (50)", `curl -s "${V1}prism/no-such-endpoint?h=a"`, {}, 50],
        ["a stated maximum, investigate budget=40", `curl -s "${V1}prism/investigate?goal=x&budget=40"`, {}, 40],
        ["a stated maximum, web/sessions (20)", `curl -X POST "${V1}web/sessions" -d '{}'`, {}, 20],
        ["unpriced cohorts (0)", `curl -s "${V1}cohorts?segment=a"`, {}, 0],
        ["prism/jobs, no stated maximum (0)", `curl -X POST "${V1}prism/jobs" -d '{}'`, {}, 0],
      ]) {
        const ok = session().seed({ spent: 0 });
        const r = ok.run(cmd, { env });
        const st = ok.state();
        const parts = [`saved: ${r.decision || "pass"}, committed ${st.spent}`];
        assert(r.raw === "" && st.spent === worst && !existsSync(lockOf(ok)), `${label}: passes with ${worst} committed, read ${r.decision} / ${JSON.stringify(st)}`, r);
        ok.cleanup();
        for (const [fl, spec] of FAULTS) {
          const s = session().seed({ spent: 0 });
          const before = s.stateRaw();
          const x = s.run(cmd, faulted(s, spec, env));
          parts.push(`${fl}: ${x.decision}`);
          assert(x.decision === "deny" && REFUSAL.test(x.message) && s.stateRaw() === before,
            `${label}, ${fl}: refused, and nothing saved, read ${x.decision} / ${s.stateRaw()} / ${x.message.slice(0, 200)}`, x);
          s.cleanup();
        }
        const d = session().seed({ spent: 0 });
        const dropBefore = d.stateRaw();
        const dx = d.run(cmd, faulted(d, ["drop"], env));
        parts.push(`a save that is dropped (LIMIT): ${dx.decision || "pass"}`);
        assert(dx.raw === "" && d.stateRaw() === dropBefore, `${label}, a dropped save (the R18-3 LIMIT): passes with nothing saved, read ${dx.decision} / ${d.stateRaw()}`, dx);
        d.cleanup();
        const h = session().seed({ spent: 0 });
        writeFileSync(lockOf(h), "");
        held.push({ s: h, command: cmd, o: { env }, label, before: h.stateRaw(), parts });
      }
      // A command that is not plain is denied before the lock and the state file: whatever they do.
      for (const [label, cmd] of [
        ["not plain, no /v1/ URL (0)", `echo see ${DOCS}/quickstart`],
        ["not plain, 150 visible", NP150],
      ]) {
        const parts = [];
        for (const [fl, spec] of FAULTS) {
          const s = session().seed({ spent: 0 });
          const before = s.stateRaw();
          const x = s.run(cmd, faulted(s, spec));
          parts.push(`${fl}: ${x.decision}`);
          assert(x.decision === "deny" && x.message === M_NOTPLAIN && s.stateRaw() === before, `${label}, ${fl}: M_NOTPLAIN, nothing saved, read ${x.decision} / ${s.stateRaw()}`, x);
          s.cleanup();
        }
        const h = session().seed({ spent: 0 });
        writeFileSync(lockOf(h), "");
        held.push({ s: h, command: cmd, o: {}, label, before: h.stateRaw(), parts, notPlain: true });
      }
      // R18-4: the locks were planted row by row, so the first can be seconds old by now; under CPU load
      // it could pass the guard's 10 s stale limit and be cleared. Refresh every one just before the start.
      const now = new Date();
      for (const h of held) utimesSync(lockOf(h.s), now, now);
      const hr = atOnce(held);
      held.forEach((h, i) => {
        const r = hr[i];
        rows.push(cell(h.label, [...h.parts, `the lock held: ${r.decision} after ${r.ms} ms`]));
        assert(h.s.stateRaw() === h.before && existsSync(lockOf(h.s)), `${h.label}, the lock held: nothing saved, the holder's lock kept, read ${h.s.stateRaw()}`);
        if (h.notPlain) assert(r.decision === "deny" && r.message === M_NOTPLAIN && r.ms < 3000, `${h.label}, the lock held: denied at once, never waiting, read ${r.decision} after ${r.ms} ms`, r);
        else {
          assert(r.ms >= 3900 && r.ms < 9000, `${h.label}, the lock held: the run waits its 4 s, read ${r.ms} ms`);
          assertRefused(r, h.s.stateFile, HELD, `${h.label}, the lock held`);
        }
        h.s.cleanup();
      });
      // A plain free call takes no lock and saves nothing: it passes at once.
      const free = session().seed({ spent: 0 });
      writeFileSync(lockOf(free), "");
      const fr = free.run(`curl -s "${V1}credits/balance"`);
      const fb = free.run(`curl -s "${V1}credits/balance"`, faulted(free, ["busy", "EBUSY"]));
      rows.push(cell("a plain free call", [`the lock held: ${fr.decision || "pass"} after ${fr.ms} ms`, `a save that throws: ${fb.decision || "pass"}`]));
      assert(fr.raw === "" && fr.ms < 3000 && fb.raw === "", `a plain free call passes at once whatever the lock or the state file does, read ${fr.decision} after ${fr.ms} ms / ${fb.decision}`, fr);
      free.cleanup();
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-20-X8-lock-create-retried",
    desc: "LOCK CREATE (J6, checker X8; D28): an exclusive create of the lock that fails with EPERM, EBUSY or EACCES (as it does while another run deletes the lock) is tried again inside the same 4 s wait, so the run still gets the lock: a 150cr call is committed and the limit then holds, and a silent pass is committed; a stray Post input never takes the lock and leaves a holder's save as it was. Only a create that fails the whole wait refuses",
    fn() {
      const rows = [];
      const fault = stateFault();
      const o = { fetch: [bal(800)] };
      const faulted = (s, spec, env = {}) => ({ ...o, node: ["--import", fault], env: { ...env, STATE_FAULT: JSON.stringify([spec[0], s.stateFile, ...spec.slice(1)]) } });
      // The first 3 creates fail, {spent 0, balance 800}: a 150cr call, then 4 x 50cr (one to 200, three past it).
      for (const code of ["EPERM", "EBUSY", "EACCES"]) {
        const s = session().seed({ spent: 0 });
        const r = s.run(P150, faulted(s, ["lock", code, 3]));
        const committed = s.state().spent;
        const lockLeft = existsSync(lockOf(s));
        const rs = [1, 2, 3, 4].map(() => s.run(P50, o));
        rows.push(cell(`3 creates fail ${code}, a 150cr call`, [`att ${r.decision || "pass"}`, `${r.ms} ms`, `committed ${committed}`, `lock left ${lockLeft}`, `then 4 x 50cr ${rs.map((x) => x.decision || "pass").join(",")}`]));
        assert(r.raw === "" && committed === 150 && !lockLeft && r.ms < 3000, `${code}: the run gets the lock on a later try and commits 150, read ${r.decision} / ${committed} / ${r.ms} ms`, r);
        assert(rs[0].raw === "" && rs.slice(1).every((x) => x.decision === "deny" && x.message === limitOf(s, 200, 50)) && s.state().spent === 200,
          `${code}: the 150 counts, so one 50 reaches 200 and three are denied, read ${decs(rs)} / ${s.stateRaw()}`);
        s.cleanup();
      }
      // A silent pass is committed, attended and unattended.
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const s = session().seed({ spent: 0 });
        const r = s.run(P50, faulted(s, ["lock", "EPERM", 3], env));
        rows.push(cell(`3 creates fail EPERM, a 50cr pass, ${who}`, [`decision ${r.decision || "pass"}`, `${r.ms} ms`, `committed ${s.state().spent}`, `lock left ${existsSync(lockOf(s))}`, `log ${logSummary(s)}`]));
        assert(r.raw === "" && r.exit === 0 && s.state().spent === 50 && !existsSync(lockOf(s)), `silent pass, ${who}: passes and is committed, read ${r.decision} / ${s.stateRaw()}`, r);
        if (who === "unattended") assert(s.logLines().length === 1 && s.logLines()[0].decision === "pass" && s.logLines()[0].committed === 50, `silent pass, unattended: logged as a pass, read ${JSON.stringify(s.logLines())}`);
        s.cleanup();
      }
      // A stray Post input whose first 3 creates would fail EPERM, while another run holds the lock for
      // 1.5 s and then saves {spent 200}: it never takes the lock, ends at once, and leaves the holder's save.
      const h = session();
      const state = (spent) => JSON.stringify({ balance: 800, spent });
      writeFileSync(h.stateFile, state(190));
      const [hp] = atOnce([{ s: h, command: P50, o: { event: "PostToolUse", ...faulted(h, ["lock", "EPERM", 3]) } }], { s: h, ms: 1500, release: state(200) });
      rows.push(cell("stray Post, 3 creates fail EPERM, a holder saves at 1.5 s", [`Post ${hp.decision} after ${hp.ms} ms`, `state ${h.stateRaw()}`, `lock left ${existsSync(lockOf(h))}`]));
      assert(hp.decision === "pass" && hp.exit === 0 && hp.ms < 1400 && h.stateRaw() === state(200) && !existsSync(lockOf(h)),
        `stray Post: no wait, nothing written, the holder's 200 stands, read ${hp.ms} ms / ${h.stateRaw()}`);
      h.cleanup();
      // A create that fails the whole wait: the call is refused, and the refusal names the error.
      const wa = session().seed({ spent: 0 });
      const wu = session().seed({ spent: 0 });
      const seeded = wa.stateRaw();
      const [ra, ru] = atOnce([{ s: wa, command: P50, o: faulted(wa, ["lock", "EPERM"]) }, { s: wu, command: P50, o: faulted(wu, ["lock", "EPERM"], UN) }]);
      rows.push(cell("every create fails EPERM, a 50cr call", [`att ${ra.decision} after ${ra.ms} ms`, `unatt ${ru.decision} after ${ru.ms} ms`, `state unchanged ${wa.stateRaw() === seeded && wu.stateRaw() === seeded}`, `log ${logSummary(wu)}`]));
      for (const [r, s, who] of [[ra, wa, "attended"], [ru, wu, "unattended"]]) {
        assertRefused(r, s.stateFile, /session lock .* could not be taken in 4 seconds \(EPERM\)/, `every create fails, ${who}`);
        assert(r.ms >= 3900 && r.ms < 9000 && s.stateRaw() === seeded && s.fetches().length === 0, `every create fails, ${who}: refused only once the wait runs out, nothing saved, read ${r.ms} ms / ${s.stateRaw()}`);
      }
      assert(wu.logLines().length === 1 && wu.logLines()[0].kind === "error" && wu.logLines()[0].decision === "deny" && wa.logLines().length === 0, `every create fails: the unattended refusal is one error deny, read ${JSON.stringify(wu.logLines())}`);
      wa.cleanup();
      wu.cleanup();
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-22-X8-no-lock-left-and-worst-time",
    desc: "UNLOCK AND TIME (J6, checker X8; D28): a run that ends normally leaves no lock file behind: a delete that fails (EBUSY, EPERM) is tried again, so after a silent pass, a deny past the limit and a refusal the lock is gone and the next run is not held up, and a stray Post input takes no lock at all. The slowest run (a lock freed at 3.8 s, then a balance read that hangs to its 3 s timeout, then every delete failing) still ends under the 10 s hook timeout, passing under the fallback limit",
    fn() {
      const rows = [];
      const fault = stateFault();
      const o = { fetch: [bal(800)] };
      const faulted = (s, spec) => ({ ...o, node: ["--import", fault], env: { STATE_FAULT: JSON.stringify([spec[0], s.stateFile, ...spec.slice(1)]) } });
      for (const [label, spent, code, want] of [
        ["a silent pass, 2 deletes fail EBUSY", 0, "EBUSY", null],
        ["a deny past the limit (190 + 50), 2 deletes fail EPERM", 190, "EPERM", "deny"],
      ]) {
        const s = session().seed({ spent });
        const r = s.run(P50, faulted(s, ["unlink", code, 2]));
        const lockLeft = existsSync(lockOf(s));
        const next = s.run(P1, o);
        rows.push(cell(label, [`decision ${r.decision || "pass"}`, `${r.ms} ms`, `lock left ${lockLeft}`, `next run ${next.decision || "pass"} after ${next.ms} ms`, `state ${s.stateRaw()}`]));
        assert(r.decision === want && r.exit === 0 && !lockLeft, `${label}: the decision stands and the lock is gone, read ${r.decision} / lock ${lockLeft}`, r);
        assert(next.raw === "" && next.ms < 3000 && s.state().spent === (want ? 191 : 51), `${label}: the next run is not held up and counts as usual, read ${next.ms} ms / ${s.stateRaw()}`, next);
        s.cleanup();
      }
      // A refusal (the save throws EBUSY; a dropped save is no longer one, R18-3) leaves no lock either,
      // and a stray Post input never takes one.
      const d = session().seed({ spent: 0 });
      const drop = d.run(P50, { ...o, node: ["--import", fault], env: { STATE_FAULT: JSON.stringify(["busy", d.stateFile, "EBUSY"]) } });
      rows.push(cell("a refusal (the save throws EBUSY)", [`decision ${drop.decision}`, `${drop.ms} ms`, `lock left ${existsSync(lockOf(d))}`]));
      assert(drop.decision === "deny" && REFUSAL.test(drop.message) && !existsSync(lockOf(d)), `a refusal leaves no lock, read ${drop.decision} / ${existsSync(lockOf(d))}`, drop);
      d.cleanup();
      const p = session().seed({ spent: 0 });
      const pass1 = p.run(P50, o);
      const before = p.stateRaw();
      const pr = p.post(P50, faulted(p, ["unlink", "EBUSY", 2]));
      rows.push(cell("a stray Post, 2 deletes would fail EBUSY", [`Pre ${pass1.decision || "pass"}`, `Post ${JSON.stringify(pr.raw)} after ${pr.ms} ms`, `state ${p.stateRaw()}`, `lock left ${existsSync(lockOf(p))}`]));
      assert(pass1.raw === "" && pr.raw === "" && p.stateRaw() === before && p.state().spent === 50 && !existsSync(lockOf(p)), `a stray Post: nothing written and no lock, read ${p.stateRaw()} / lock ${existsSync(lockOf(p))}`, pr);
      p.cleanup();
      // The slowest run: the lock is freed at 3.8 s, the balance read hangs to its 3 s timeout, and
      // every delete of the lock fails (10 tries). It must still end well under the 10 s hook timeout.
      const w = fresh();
      const [wr] = atOnce([{ s: w, command: P50, o: { ...faulted(w, ["unlink", "EBUSY"]), fetch: [{ hang: true }] } }], { s: w, ms: 3800 });
      const wst = w.state();
      rows.push(cell("slowest: lock freed at 3.8 s, read hangs, deletes fail", [`decision ${wr.decision}`, `${wr.ms} ms`, `fetches ${w.fetches().length}`, `state ${JSON.stringify(wst)}`, `lock left ${existsSync(lockOf(w))}`]));
      assert(wr.decision === "pass" && wr.exit === 0 && w.fetches().length === 1 && wst.spent === 50 && wst.balanceFails === 1, `slowest run: it waits, reads (a failed try), takes the fallback 500 and commits its 50, read ${wr.decision} / ${JSON.stringify(wst)}`, wr);
      assert(wr.ms >= 6500 && wr.ms < 9000, `slowest run: about 3.8 s + 3 s + the delete tries, under the 10 s hook timeout, read ${wr.ms} ms`);
      w.cleanup();
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R14b-23-J6-bursts",
    desc: "BURSTS (J6, checkers X7/X8; D28): 2, 3, 4, 8 and 16 runs of one session started at once, from {spent 0} and from {spent 150} (limit 200): at most 4 (from 0) or 1 (from 150) x 50cr pass silently, reaching 200 exactly, and exactly those are committed; every other run is denied with M_LIMIT or refused, no run is refused at 2-3, nothing is pending and no lock is left. The same holds when every run's first lock create fails EPERM, unattended (passes committed, every run logged) and from a fresh session (one balance read)",
    fn() {
      const rows = [];
      const fault = stateFault();
      const o = { fetch: [bal(800)] };
      function burst(label, n, seed, env = {}, spec = null) {
        const s = seed ? session().seed(seed) : fresh();
        const start = seed ? seed.spent : 0;
        const room = Math.max(0, (200 - start) / 50);
        const cmds = Array.from({ length: n }, (_, i) => P50N(i));
        const extra = spec ? { node: ["--import", fault] } : {};
        const rs = atOnce(cmds.map((command) => ({ s, command, o: { ...o, ...extra, env: spec ? { ...env, STATE_FAULT: JSON.stringify([spec[0], s.stateFile, ...spec.slice(1)]) } : env } })));
        const st = s.state() || {};
        const passes = rs.filter((r) => r.decision === "pass").length;
        const refused = rs.filter((r) => r.decision === "deny" && REFUSAL.test(r.message)).length;
        const denied = rs.filter((r) => r.decision === "deny" && LIMIT_RE.test(r.message)).length;
        const l = s.logLines();
        const lockLeft = existsSync(lockOf(s));
        const reads = s.fetches().length;
        rows.push(cell(`${label}: ${n} at once from ${start}`, [`${rs.map((r) => (REFUSAL.test(r.message) ? "R" : r.decision[0])).join("")}`, `passes ${passes}, denied ${denied}, refused ${refused}`,
          `committed ${st.spent}`, `fetches ${reads}`, `slowest ${Math.max(...rs.map((r) => r.ms))} ms`, `log ${l.length}`]));
        assert(rs.length === n && rs.every((r) => r.exit === 0 && r.stderr === ""), `${label} ${n}: every run exits 0 with no stderr, read ${JSON.stringify(rs.map((r) => [r.exit, r.stderr.slice(0, 80)]))}`);
        assert(passes + denied + refused === n, `${label} ${n}: every run passes, is denied past the limit or is refused, read ${decs(rs)}`);
        assert(passes <= room && st.spent === start + 50 * passes && !st.lost && !("pending" in st), `${label} ${n}: at most ${room} silent passes and exactly those committed, read ${passes} passes / ${JSON.stringify(st)}`);
        assert(n > 3 || refused === 0, `${label} ${n}: no run is refused at 2-3, read ${refused}`);
        assert(!lockLeft && reads === (seed ? 0 : 1), `${label} ${n}: no lock left and ${seed ? "no" : "one"} balance read, read lock ${lockLeft} / ${reads}`);
        if (env === UN) assert(l.length === n && l.filter((x) => x.decision === "pass").length === passes, `${label} ${n}: one log line per run, the passes among them, read ${l.length} / ${JSON.stringify(l.map((x) => x.decision))}`);
        s.cleanup();
      }
      for (const n of [2, 3, 4, 8, 16]) {
        burst("attended", n, { spent: 0 });
        burst("attended", n, { spent: 150 });
      }
      burst("attended, every first create fails EPERM", 8, { spent: 150 }, {}, ["lock", "EPERM", 1]);
      burst("attended, every first create fails EPERM", 3, { spent: 0 }, {}, ["lock", "EPERM", 1]);
      for (const n of [3, 8]) burst("unattended", n, { spent: 0 }, UN);
      for (const n of [3, 16]) burst("attended, no balance cached", n, null);
      rmSync(dirname(fileURLToPath(fault)), { recursive: true, force: true });
      console.log(rows.join("\n"));
    },
  },
  {
    id: "R18-W1-deny-and-ask-wording",
    desc: "WORDING (R18 Q-j, A19/A20; checker H5; D28): every deny — not plain, not Bash, past the automatic cap, past the fallback cap, past a session budget, past the one budget in a routine, a lost total — is the same attended and unattended, starts \"SocialCrawl call not run: \", ends with \" Nothing was sent and nothing was counted.\" and carries no approval wording (\"Confirm with the user\", \"run it only on a yes\", \"every paid call asks\", \"Unattended session:\"…); the error deny (unattended only) is exactly M_ERROR; the lost deny says the committed total was lost and never \"~0 credits\". Three guard mutants (an unattended-only prefix restored, the lost wording gone, the tail dropped from the limit deny) each turn these checks red",
    fn() {
      const ATT = /run it only on a yes|run this only on an explicit yes|every paid call asks|Confirm with the user|Work out what it will cost|Show the user|Re-run it with the full literal URL|Unattended session|\bask(?:s|ed)?\b/i;
      const cases = [
        ["not plain", `echo '${V1}prism/leads?query=x'`, {}],
        ["not Bash", P50, { extra: { tool_name: "PowerShell" } }],
        ["past the automatic cap (190 of 200)", P50, { seed: { spent: 190 } }],
        ["past the fallback cap (480 of 500)", P50, { seed: { spent: 480 }, nobalance: true }],
        ["past a session budget (30)", P50, { budget: { sessionBudget: 30 } }],
        ["past the one budget in a routine (1990 of 2000)", P50, { budget: { sessionBudget: 2000, ...ROUTINES_ON }, env: ROUTINE, seed: { spent: 1990 } }],
        ["a lost total", P50, { seed: { spent: 0, lost: true } }],
      ];
      const open = (c) => {
        const s = c.nobalance ? session({ balance: null }) : session();
        s.seed(c.seed || { spent: 0 });
        if (c.budget) s.budget(c.budget);
        if (c.day) s.day(c.day);
        return s;
      };
      function check(guard) {
        const bad = [];
        for (const [label, cmd, c] of cases) {
          // One session for both runs: a message names that session's own budget or day file, and a
          // deny changes nothing the second run reads (a lost total is saved lost, and stays lost).
          const s = open(c);
          const ru = s.run(cmd, { guard, extra: c.extra, env: { ...(c.env || {}), ...UN } });
          const ra = s.run(cmd, { guard, extra: c.extra, env: c.env || {} });
          s.cleanup();
          if (ra.decision !== "deny" || ru.decision !== "deny") bad.push(`${label}: not denied both ways, read ${ra.decision} / ${ru.decision}`);
          else if (ra.message !== ru.message) bad.push(`${label}: attended and unattended differ: ${ru.message.slice(0, 120)}`);
          else if (!ra.message.startsWith("SocialCrawl call not run: ") || !ra.message.endsWith(T) || ATT.test(ra.message)) bad.push(`${label}: wording: ${ra.message.slice(-160)}`);
        }
        const l = open({ seed: { spent: 0, lost: true } });
        const rl = l.run(P50, { guard });
        l.cleanup();
        if (!/committed total was lost/.test(rl.message) || /~0 credits/.test(rl.message)) bad.push(`lost session: ${rl.message.slice(0, 220)}`);
        return bad;
      }
      const control = check(GUARD);
      assert(control.length === 0, `the build's own wording: ${control.join(" | ")}`);
      const rows = [cell("this build", ["0 failures"])];
      // The error deny happens unattended only (attended an error passes): exactly M_ERROR, both NOT_BASH
      // variants (the outer throw is past the tool check). A costs.json of the wrong shape throws while
      // costing: a plain Bash call reaches M_ERROR, and the PowerShell form is still denied as not Bash.
      const outer = outerThrows();
      const d0 = hooksCopy((costs) => ({ ...costs, _unpriced: 5 }));
      for (const [who, extra, o, want] of [
        ["Bash, the outer throw", undefined, { node: ["--import", outer] }, mError(false)],
        ["PowerShell, the outer throw", { tool_name: "PowerShell" }, { node: ["--import", outer] }, mError(true)],
        ["Bash, costs.json of the wrong shape", undefined, { guard: join(d0, "credit-guard.mjs") }, mError(false)],
        ["PowerShell, costs.json of the wrong shape", { tool_name: "PowerShell" }, { guard: join(d0, "credit-guard.mjs") }, M_NOTBASH],
      ]) {
        const s = session().seed({ spent: 0 });
        const r = s.run(P50, { ...o, extra, env: UN });
        const att = s.run(P50, { ...o, extra });
        s.cleanup();
        rows.push(cell(`a forced error, ${who}`, [`unatt ${r.decision}`, `att ${att.decision || "pass"}`, r.message.slice(0, 60)]));
        assert(r.decision === "deny" && r.message === want && r.message.endsWith(T), `a forced error, ${who}: exactly the expected deny, read ${r.message}`, r);
        assert(want === M_NOTBASH ? att.message === M_NOTBASH : att.raw === "", `a forced error, ${who}: attended ${want === M_NOTBASH ? "the same deny" : "passes silently"}, read ${att.decision} / ${att.message}`, att);
      }
      rmSync(d0, { recursive: true, force: true });
      rmSync(dirname(fileURLToPath(outer)), { recursive: true, force: true });
      for (const [what, find, repl] of [
        ["an unattended-only prefix restored", "    return done({ hookSpecificOutput: { permissionDecision: \"deny\" }, systemMessage: message });\n",
          "    return done({ hookSpecificOutput: { permissionDecision: \"deny\" }, systemMessage: (UNATTENDED ? \"Unattended session: nobody can confirm this SocialCrawl call, so it was not run. \" : \"\") + message });\n"],
        ["the lost wording gone", "return deny(M_LOST, \"lost\");", "return deny(\"SocialCrawl call not run: ~0 credits are committed this session.\" + T, \"lost\");"],
        ["the tail dropped from the limit deny", "`(${src}). To go further, the person raises it in the SocialCrawl Budget pane.` + T,", "`(${src}). To go further, the person raises it in the SocialCrawl Budget pane.`,"],
      ]) {
        const d = hooksCopy(null);
        const f = join(d, "credit-guard.mjs");
        const src = readFileSync(f, "utf8");
        assert(src.split(find).length === 2, `mutant "${what}": its anchor must occur exactly once`);
        writeFileSync(f, src.replace(find, repl));
        const got = check(f);
        rmSync(d, { recursive: true, force: true });
        rows.push(cell(`mutant: ${what}`, [`${got.length} failure(s)`, got[0] ? got[0].slice(0, 90) : "SURVIVED"]));
        assert(got.length > 0, `DEAD FIXTURE: the mutant (${what}) passes every wording check`);
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P2-A10-sessions-folder-made",
    desc: "STATE (0.3.1, A9/A10; D28): the session file is <revxl>/sessions/socialcrawl-<sid>.json. In a fresh <revxl> with no sessions/ folder a plain free call makes nothing, and the first paid call is not refused: the guard makes the folder and counts the call there (a silent 50cr pass, attended and unattended); a command that is not plain makes nothing either (it is denied before any I/O); a blank SC_REVXL_HOME means ~/.claude/revxl",
    fn() {
      const rows = [];
      const fileOf = (home, sid) => join(home, "sessions", `socialcrawl-${sid}.json`);
      const read = (f) => { try { return JSON.parse(readFileSync(f, "utf8")); } catch { return null; } };
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const s = fresh();
        rmSync(s.revxl, { recursive: true, force: true });              // a fresh <revxl>: nothing there yet
        const free = s.run(`curl -s "${V1}credits/balance"`, { env });
        const afterFree = existsSync(join(s.revxl, "sessions"));
        const r = s.run(P50, { fetch: [bal(800)], env });
        const st = read(fileOf(s.revxl, s.sid));
        rows.push(cell(`fresh <revxl>, ${who}: free, then 50cr`, [`free ${free.decision || "pass"}, folder after it ${afterFree}`, `50cr ${r.decision || "pass"}`, `file ${JSON.stringify(st)}`]));
        assert(free.raw === "" && !afterFree, `${who}: a plain free call passes and makes no folder, read ${free.decision} / ${afterFree}`, free);
        assert(r.raw === "" && r.exit === 0 && st && st.spent === 50 && st.balance === 800,
          `${who}: the first paid call passes silently and is counted in ${fileOf(s.revxl, s.sid)}, read ${r.decision} / ${JSON.stringify(st)}`, r);
        s.cleanup();
      }
      const a = fresh();
      rmSync(a.revxl, { recursive: true, force: true });
      const ra = a.run(NP150, { fetch: [bal(800)] });
      rows.push(cell("fresh <revxl>, a command that is not plain", [`decision ${ra.decision}`, `<revxl> made ${existsSync(a.revxl)}`, `fetches ${a.fetches().length}`]));
      assert(ra.decision === "deny" && ra.message === M_NOTPLAIN && !existsSync(a.revxl) && a.fetches().length === 0,
        `not plain in a fresh <revxl>: denied with nothing made and no read, read ${ra.decision} / ${existsSync(a.revxl)} / ${a.fetches().length}`, ra);
      a.cleanup();
      const b = fresh();
      const rb = b.run(P50, { fetch: [bal(800)], env: { SC_REVXL_HOME: "   " } });
      const sb = read(fileOf(join(b.dir, ".claude", "revxl"), b.sid));
      rows.push(cell("SC_REVXL_HOME blank, 50cr", [`decision ${rb.decision || "pass"}`, `~/.claude/revxl file ${JSON.stringify(sb)}`]));
      assert(rb.raw === "" && sb && sb.spent === 50, `a blank SC_REVXL_HOME is ~/.claude/revxl (HOME), read ${rb.decision} / ${JSON.stringify(sb)}`, rb);
      b.cleanup();
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P2-A11-old-temp-file-ignored",
    desc: "STATE (0.3.1, A11): the old TEMP file is never read or written. A leftover sc-credit-guard-<sid>.json in TEMP holding {spent: 9999}, with no new file, reads as a fresh session (one balance read, a 50cr plain curl silent and counted 50); rewritten mid-session to {spent: 0}, as shortform 0.6.0's guard does, it leaves the new file's count as it was",
    fn() {
      const s = fresh();
      const old = join(s.dir, `sc-credit-guard-${s.sid}.json`);       // TEMP is the session folder (lib.mjs)
      writeFileSync(old, JSON.stringify({ spent: 9999 }));
      const r1 = s.run(P50, { fetch: [bal(800)] });
      const st1 = s.state();
      const r2 = s.run(P1, { fetch: [bal(800)] });
      const oldBefore = readFileSync(old, "utf8");
      writeFileSync(old, JSON.stringify({ spent: 0 }));            // the shortform-style rewrite of the old name
      const r3 = s.run(P1B, { fetch: [bal(800)] });
      const st3 = s.state();
      const oldAfter = readFileSync(old, "utf8");
      console.log([
        cell("leftover {spent 9999}, no new file: 50cr", [`decision ${r1.decision || "pass"}`, `fetches ${s.fetches().length}`, `new file ${JSON.stringify(st1)}`]),
        cell("then 1cr, old file rewritten {spent 0}, 1cr", [`${r2.decision || "pass"}, ${r3.decision || "pass"}`, `new file ${JSON.stringify(st3)}`, `old file ${oldBefore} -> ${oldAfter}`]),
      ].join("\n"));
      assert(r1.raw === "" && st1 && st1.spent === 50 && st1.balance === 800 && s.fetches().length === 1,
        `the leftover is not read: a fresh session, one read, silent and counted 50, read ${r1.decision} / ${JSON.stringify(st1)}`, r1);
      assert(r2.raw === "" && r3.raw === "" && st3.spent === 52 && oldBefore === JSON.stringify({ spent: 9999 }) && oldAfter === JSON.stringify({ spent: 0 }),
        `the rewrite changes nothing and the old file is never written, read ${JSON.stringify(st3)} / ${oldBefore} / ${oldAfter}`, r3);
      s.cleanup();
    },
  },
  {
    id: "P2-A14-no-sessions-folder",
    desc: "STATE (0.3.1, A14): when <revxl>/sessions can't be made (SC_REVXL_HOME under a regular file), a paid call is refused at once attended (a deny naming the folder, under 1 s) and denied at once unattended, and the Post run stops at once, printing nothing",
    fn() {
      const s = fresh();
      const file = join(s.dir, "a-file");
      writeFileSync(file, "a regular file");
      const folder = join(file, "revxl", "sessions");
      const env = { SC_REVXL_HOME: join(file, "revxl") };
      const pre = s.run(P50, { env });
      const un = s.run(P50, { env: { ...env, ...UN } });
      const post = s.post(P50, { env });
      console.log(cell("SC_REVXL_HOME under a file, 50cr", [`Pre ${pre.decision} after ${pre.ms} ms`, `unattended ${un.decision} after ${un.ms} ms`, `Post ${JSON.stringify(post.raw)} after ${post.ms} ms`]));
      assertRefused(pre, join(folder, `socialcrawl-${s.sid}.json`), new RegExp(`the session folder ${esc(folder)} does not exist and can't be created \\(E[A-Z]+\\)`), "no sessions folder, attended");
      assert(pre.ms < 1000 && un.decision === "deny" && un.exit === 0 && un.ms < 1000 && post.raw === "" && post.exit === 0 && post.stderr === "" && post.ms < 1000 && statSync(file).isFile(),
        `no sessions folder: Pre refused and denied at once, Post done at once, read ${pre.ms} / ${un.decision} ${un.ms} / ${post.ms} ms`, un);
      s.cleanup();
    },
  },
  {
    id: "P2-A15-no-temp-needed",
    desc: "STATE (0.3.1, A15): the guard no longer needs TEMP: with TEMP, TMP and TMPDIR at a folder that doesn't exist and a valid <revxl>, a plain 50cr Bash curl under the cap passes silently and is counted, attended and unattended",
    fn() {
      const rows = [];
      for (const [who, env] of [["attended", {}], ["unattended", UN]]) {
        const s = session().seed({ spent: 0 });
        const m = join(s.dir, "no-such-temp");
        const r = s.run(P50, { env: { ...env, TEMP: m, TMP: m, TMPDIR: m } });
        const st = s.state();
        rows.push(cell(`TEMP missing, ${who}, 50cr`, [`decision ${r.decision || "pass"}`, `state ${JSON.stringify(st)}`]));
        assert(r.raw === "" && r.exit === 0 && st && st.spent === 50 && !existsSync(m), `TEMP missing, ${who}: silent and counted 50, read ${r.decision} / ${JSON.stringify(st)}`, r);
        s.cleanup();
      }
      console.log(rows.join("\n"));
    },
  },
  {
    id: "P2-A16-deadline-slow-start",
    desc: "DEADLINE (0.3.1, A16/A18/A19; D28a): one time limit D <= 7000 ms from process start bounds the worst Pre run. Its start held 3 s (a slow Node start), a live lock let go 3.7 s after the guard starts waiting, a balance read that hangs: it still ends within D + 1 s of spawn, the read cut short being an unreadable balance, so the fallback limit of 500 and a silent pass that is committed, attended and unattended; let go at 3.9 s, racing D, it passes committed or is refused; never let go, it is refused within D + 1 s, stating the wait it really had. A mutant with the deadline removed (D = Infinity, the 0.3.0 timing) takes longer than D + 1 s on the same run",
    fn() {
      const D = deadlineOf(GUARD);
      const pre = slowStart();
      const rows = [];
      const scene = (label, o) => {
        const s = fresh();
        writeFileSync(lockOf(s), "");                                 // a live holder's lock: fresh the whole run
        const env = { ...(o.env || {}), SLOW_START: "3000", ...(o.release == null ? {} : { SLOW_LOCK: lockOf(s), SLOW_RELEASE: String(o.release) }) };
        const r = s.run(P50, { guard: o.guard, fetch: [{ hang: true }], node: ["--import", pre], env });
        r.spent = (s.state() || {}).spent;
        rows.push(cell(label, [`decision ${r.decision || "none"}`, `${r.ms} ms`, `fetches ${s.fetches().length}`, `committed ${r.spent}`, `reason ${r.message.slice(0, 70)}`]));
        s.cleanup();
        return r;
      };
      const att = scene("held 3 s, lock let go at 3.7 s, read hangs, attended", { release: 3700 });
      const un = scene("the same, unattended", { release: 3700, env: UN });
      const race = scene("the same, let go at 3.9 s (racing D), attended", { release: 3900 });
      const held = scene("the same, the lock never let go, attended", {});
      const d = hooksCopy(null);                                       // the deadline removed: D = Infinity
      const mf = join(d, "credit-guard.mjs");
      const msrc = readFileSync(mf, "utf8");
      const anchored = msrc.split(`const D = ${D};`).length === 2;
      if (anchored) writeFileSync(mf, msrc.replace(`const D = ${D};`, "const D = Infinity;"));
      const mut = anchored ? scene("mutant D = Infinity (0.3.0 timing), as the first row", { release: 3700, guard: mf }) : null;
      rmSync(d, { recursive: true, force: true });
      rmSync(dirname(fileURLToPath(pre)), { recursive: true, force: true });
      console.log(rows.join("\n"));
      const bound = D + 1000;
      assert(Number.isInteger(D) && D > 0 && D <= 7000, `one deadline constant \`const D = <ms>;\` <= 7000 in credit-guard.mjs, read ${D}`);
      assert(att.raw === "" && att.spent === 50 && att.ms <= bound, `attended: a committed silent pass within ${bound} ms of spawn, read ${att.decision} / ${att.spent} after ${att.ms} ms`, att);
      assert(un.raw === "" && un.spent === 50 && un.ms <= bound, `unattended: a committed silent pass within ${bound} ms of spawn, read ${un.decision} / ${un.spent} after ${un.ms} ms`, un);
      assert(((race.raw === "" && race.spent === 50) || (race.decision === "deny" && REFUSAL.test(race.message))) && race.ms <= bound,
        `racing D: a committed pass or the lock refusal, within ${bound} ms, read ${race.decision} after ${race.ms} ms`, race);
      assert(held.decision === "deny" && REFUSAL.test(held.message) && held.ms <= bound &&
        /session lock .* could not be taken in \d+(\.\d)? seconds \(EEXIST\), all the time left before the guard's \d+-second limit/.test(held.message),
        `never let go: the lock refusal, stating the wait it really had, within ${bound} ms, read ${held.decision} after ${held.ms} ms`, held);
      assert(mut && mut.ms > bound, `the fixture binds: the deadline-removed mutant takes longer than ${bound} ms, read ${mut ? mut.ms : "no mutant (no D anchor)"}`);
    },
  },
];
