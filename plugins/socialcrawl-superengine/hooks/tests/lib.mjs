/*
 * Test harness for hooks/credit-guard.mjs. BUILD-TIME TOOLING ONLY — nothing in this
 * directory is referenced by hooks.json or by any skill, so the plugin never loads it at
 * runtime. Run it with `node hooks/tests/run.mjs`.
 *
 * It invokes the guard exactly the way Claude Code does: a PreToolUse envelope as JSON on
 * stdin, the decision as JSON on stdout, exit 0 always (every path sets exit code 0).
 *
 * Each session gets a throwaway directory, and SC_REVXL_HOME is its `revxl` folder, so the guard's
 * session state file (`<revxl>/sessions/socialcrawl-<sid>.json`), its budget file
 * (`<revxl>/socialcrawl-budget.json`) and the routine day file (`<revxl>/socialcrawl-day.json`) are
 * isolated and seedable, and so running the suite never touches a real session's counter.
 * TEMP/TMP/TMPDIR point at the same directory; the guard keeps no state there.
 *
 * OFFLINE BY DEFAULT (R14b): the guard reads the balance on a paid command with none cached, so
 * every run gets no SOCIALCRAWL_API_KEY, HOME/USERPROFILE at the session directory (no key file)
 * and dead proxies; with no key the guard sends nothing. SC_REVXL_HOME is the session's own
 * `revxl` folder, so the unattended log never reaches a real one. `o.fetch` feeds the balance
 * read through the `--import` preload fake-fetch.mjs, which replaces fetch, with a fake key.
 *
 * URL ASSEMBLY: every fixture URL is built by string CONCATENATION here and in the fixture
 * files, so a transcript-shaped socialcrawl URL never exists as a single literal that a
 * developer's own installed credit guard would match when this suite is edited or grepped.
 * Test hygiene, not evasion — the guard under test still sees the fully assembled string.
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
export const GUARD = resolve(HERE, "..", "credit-guard.mjs");
export const COSTS = resolve(HERE, "..", "costs.json");
/** The `--import` preload that answers the balance read (R14b). */
export const FAKE_FETCH = pathToFileURL(resolve(HERE, "fake-fetch.mjs")).href;
/** Never a real key. Split so no scanner reads it as one; only an `o.fetch` run carries it. */
export const FAKE_KEY = "sc_" + "fixture-not-a-key";
const DEAD = "http://127.0.0.1:9";

// Assembled, never written whole.
export const HOST = "www." + "social" + "crawl" + "." + "dev";
export const V1 = "https://" + HOST + "/v1/";
// The token the transcript gate matches on, never spelled out in one piece.
export const TSCRIPT = "trans" + "cript";

let seq = 0;

/** A JSON-lines file as an array of objects; [] when it is absent. */
function jsonl(p) {
  try {
    return readFileSync(p, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
  } catch {
    return [];
  }
}

/**
 * The balance every guard session is seeded with (P21: every guard fixture runs with a seeded
 * balance, and "balance unknown" is its own group). 800 gives the automatic cap
 * min(500, 25% of 800) = 200 (R18-1, Q-c: 800 keeps every 200-tuned figure), the hard limit
 * (D28) of every session with no budget file. Pass `balance: null` for the balance-unknown group.
 */
export const BALANCE = 800;
export const LIMIT = Math.min(500, Math.floor(0.25 * BALANCE));

/** The figure a session has committed (D28: there is no pending quote any more): its spent. */
export function quoted(state) {
  if (!state) return null;
  return typeof state.spent === "number" ? state.spent : 0;
}

// The guard's messages (Phase 3a §c), whole. Every deny is checked by equality, never by a regex.
export const T = " Nothing was sent and nothing was counted.";
export const USE_BASH = " For SocialCrawl calls, use the Bash tool.";
export const M_NOTPLAIN =
  "SocialCrawl call not run: this command carries a SocialCrawl URL but is not a plain `curl` the credit guard can count " +
  "(a loop, a pipe into a program, a wrapper, a variable, a heredoc, a note or other mention, or a flag outside the plain set), " +
  "so what it sends, and how many times, can't be read. Rewrite it as one plain `curl` per SocialCrawl call in the Bash tool; " +
  "if it only mentions socialcrawl.dev, use the Read or Grep tool instead." + T;
export const M_NOTBASH =
  "SocialCrawl call not run: it came through a tool other than Bash, and the credit guard counts plain `curl` calls in the " +
  "Bash tool only." + USE_BASH + T;
export const M_LOST =
  "SocialCrawl call not run: this session's committed total was lost (its session file was damaged or unreadable), so its " +
  "credit limit can't be enforced. Start a new session to continue." + T;
export const mError = (notBash = false) =>
  "SocialCrawl call not run: the credit guard hit an error reading this command, so it could not count what it would cost." +
  (notBash ? USE_BASH : "") + T;
export const SRC_SESSION = "your session budget";
export const SRC_FALLBACK = "the fallback cap of 500, because your balance couldn't be read";
export const srcAuto = (balance) => `the automatic cap: the smaller of 500 and a quarter of your ${balance}-credit balance`;
/** M_LIMIT, the same for every run (D55): it names no file and no kind of budget. */
export const mLimit = ({ spent, worst, limit, src }) =>
  `SocialCrawl call not run: it would take this session past its credit limit. Committed so far: ~${spent} credits; ` +
  `this command's worst case: ~${worst} credits; the limit is ${limit} credits (${src}). To go further, the person ` +
  `raises it in the SocialCrawl Budget pane.` + T;
// Phase 3b's two read denies, whole.
export const mStateRead = (sf) =>
  `SocialCrawl call not run: the session file ${sf} can't be read right now, so this session's committed total can't be checked. Run the command again.` + T;
export const mBudgetRead = (bf) =>
  `SocialCrawl call not run: the budget file ${bf} exists but can't be read right now, so this session's credit limit can't be checked. Run the command again.` + T;
/** A Desktop routine's env (D26), and an old routines block, which the guard ignores (D55). */
export const ROUTINE = { CLAUDE_CODE_HOST_SCHEDULED_RUN: "1" };
export const ROUTINES_ON = { routines: { enabled: true, perRun: 2000, perDay: 4000 } };
/** Today as the day file dates it: the local YYYY-MM-DD. */
export function today() {
  const n = new Date();
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}-${String(n.getDate()).padStart(2, "0")}`;
}

/** A guard session: one session_id and one isolated directory (its TEMP and its revxl), reusable across calls. */
export function session(opts = {}) {
  const dir = mkdtempSync(join(tmpdir(), "sc-guard-test-"));
  const sid = opts.sessionId || `scgt${process.pid}x${++seq}`;
  const stateFile = join(dir, "revxl", "sessions", `socialcrawl-${sid}.json`);
  mkdirSync(dirname(stateFile), { recursive: true });   // as TEMP always was; a fixture removes it to test its making
  const balance = opts.balance === undefined ? BALANCE : opts.balance;
  const s = {
    dir,
    sid,
    stateFile,
    /** The budget file and the routine day file the guard reads (contract §1, §6). */
    bf: join(dir, "revxl", "socialcrawl-budget.json"),
    df: join(dir, "revxl", "socialcrawl-day.json"),
    /** Seed the state file; the session's balance rides along unless the session has none. */
    seed(obj) {
      writeFileSync(stateFile, JSON.stringify(balance === null ? obj : { balance, ...obj }));
      return this;
    },
    /** Write the budget file: an object as JSON, a string as-is. */
    budget(v) {
      writeFileSync(this.bf, typeof v === "string" ? v : JSON.stringify(v));
      return this;
    },
    /** Write the routine day file: an object as JSON, a string as-is. */
    day(v) {
      writeFileSync(this.df, typeof v === "string" ? v : JSON.stringify(v));
      return this;
    },
    stateExists() {
      return existsSync(stateFile);
    },
    stateRaw() {
      try {
        return readFileSync(stateFile, "utf8");
      } catch {
        return null;
      }
    },
    state() {
      try {
        return JSON.parse(readFileSync(stateFile, "utf8"));
      } catch {
        return null;
      }
    },
    /** The unattended log's folder (SC_REVXL_HOME) and its parsed lines. */
    revxl: join(dir, "revxl"),
    logLines() {
      return jsonl(join(dir, "revxl", "credit-guard-unattended.jsonl"));
    },
    /** Every balance request fake-fetch.mjs answered in this session: {url, key, signal}. */
    fetches() {
      return jsonl(join(dir, "fetches.jsonl"));
    },
    run(command, o = {}) {
      const env = { ...process.env, TEMP: dir, TMP: dir, TMPDIR: dir };
      // Absent = attended. The runner's own session may be unattended (`claude -p` sets 0), so
      // the variable is dropped unless the fixture sets it; so is a routine runner's
      // CLAUDE_CODE_HOST_SCHEDULED_RUN (D26), which only a routine fixture sets.
      delete env.CLAUDE_CODE_SESSION_ATTENDED;
      delete env.CLAUDE_CODE_HOST_SCHEDULED_RUN;
      // Offline by default (R14b): no key in the env or under HOME, dead proxies, and the log in
      // this session's own folder.
      for (const k of Object.keys(env)) if (/^(socialcrawl_api_key|no_proxy)$/i.test(k)) delete env[k];
      Object.assign(env, {
        HOME: dir, USERPROFILE: dir, SC_REVXL_HOME: join(dir, "revxl"),
        HTTPS_PROXY: DEAD, HTTP_PROXY: DEAD, ALL_PROXY: DEAD, NODE_USE_ENV_PROXY: "1",
      });
      // o.fetch: the replies the balance read gets, in order, the last one repeating (see
      // fake-fetch.mjs). The fake key rides along; `unsetEnv: ["SOCIALCRAWL_API_KEY"]` drops it.
      if (o.fetch) Object.assign(env, { FAKE_FETCH: JSON.stringify(o.fetch), FAKE_FETCH_LOG: join(dir, "fetches.jsonl"), SOCIALCRAWL_API_KEY: FAKE_KEY });
      Object.assign(env, o.env || {});
      for (const k of o.unsetEnv || []) delete env[k];
      const before = this.stateRaw();
      const t0 = Date.now();
      const r = spawnSync(process.execPath, [...(o.fetch ? ["--import", FAKE_FETCH] : []), ...(o.node || []), o.guard || GUARD], {
        input: JSON.stringify({
          session_id: sid,
          hook_event_name: o.event || "PreToolUse",
          tool_name: "Bash",
          tool_input: { command },
          ...(o.extra || {}),
        }),
        encoding: "utf8",
        env,
        timeout: 30000,
      });
      const ms = Date.now() - t0;
      const stateWritten = this.stateRaw() !== before;
      const raw = String(r.stdout || "");
      let parsed = null;
      if (raw.trim()) {
        try {
          parsed = JSON.parse(raw);
        } catch {
          parsed = null;
        }
      }
      const hso = (parsed && parsed.hookSpecificOutput) || null;
      return {
        raw,
        stderr: String(r.stderr || ""),
        exit: r.status,
        json: parsed,
        decision: (hso && hso.permissionDecision) || null,
        // The guard mirrors systemMessage into permissionDecisionReason on a decision path.
        message:
          (parsed && parsed.systemMessage) || (hso && hso.permissionDecisionReason) || "",
        stateWritten,
        ms,
        bf: this.bf,
        df: this.df,
      };
    },
    /**
     * The same command as a stray PostToolUse input, or PostToolUseFailure with `failure: true`
     * (D28a: the guard no longer runs after a command, so it must print and write nothing). `o.extra`
     * (a tool_name) is kept.
     */
    post(command, o = {}) {
      return this.run(command, {
        ...o,
        event: o.failure ? "PostToolUseFailure" : "PostToolUse",
        extra: {
          ...(o.extra || {}),
          ...(o.failure ? { error: "Exit code 1" } : { tool_response: { stdout: "", stderr: "", interrupted: false } }),
        },
      });
    },
    cleanup() {
      try {
        rmSync(dir, { recursive: true, force: true });
      } catch {}
    },
  };
  if (balance !== null) s.seed({});                 // P21: every session starts with its balance
  return s;
}

/** One-shot: fresh session, single command, auto-cleanup. Returns the result plus state and log. */
export function run(command, opts = {}) {
  const s = session(opts);
  if (opts.seedState !== undefined) s.seed(opts.seedState);
  if (opts.budget !== undefined) s.budget(opts.budget);
  const out = s.run(command, opts);
  out.state = s.state();
  out.stateRaw = s.stateRaw();
  out.stateExists = s.stateExists();
  out.log = s.logLines();
  s.cleanup();
  return out;
}

/**
 * The unattended log line of `command` run once unattended in a fresh seeded session (spent 0):
 * for a command that is not plain, its deny's visible worst case and paths (D28: nothing is
 * counted, but the visible total is logged for the next notice). Null when nothing is logged.
 */
export function visible(command, opts = {}) {
  const r = run(command, { ...opts, env: { ...(opts.env || {}), CLAUDE_CODE_SESSION_ATTENDED: "0" } });
  return r.log.length === 1 ? r.log[0] : null;
}

/** Assertion helpers. Every failure throws with the guard's own output attached. */
export function assert(cond, msg, ctx) {
  if (!cond) {
    const extra = ctx ? `\n      guard said: ${JSON.stringify(ctx).slice(0, 900)}` : "";
    throw new Error(msg + extra);
  }
}
export function assertMatch(res, re, msg) {
  assert(re.test(res.message), `${msg} — expected /${re.source}/ in the message`, {
    decision: res.decision,
    message: res.message,
    state: res.state,
  });
}
export function assertNoMatch(res, re, msg) {
  assert(!re.test(res.message), `${msg} — did NOT expect /${re.source}/ in the message`, {
    decision: res.decision,
    message: res.message,
    state: res.state,
  });
}
export function assertDecision(res, want, msg) {
  assert(res.decision === want, `${msg} — decision was ${JSON.stringify(res.decision)}, wanted ${JSON.stringify(want)}`, {
    message: res.message,
    state: res.state,
  });
}
/**
 * A run() of a command that is NOT a plain curl (R14a.2), through the Bash tool: denied with
 * exactly M_NOTPLAIN (D28), before any state is read or written, so nothing is counted.
 */
export function assertNotPlain(res, msg) {
  assertDecision(res, "deny", `${msg} — a command that is not a plain curl is denied`);
  assert(res.message === M_NOTPLAIN, `${msg} — the message is exactly M_NOTPLAIN, read ${JSON.stringify(res.message).slice(0, 300)}`, res);
  assert(!res.stateWritten, `${msg} — nothing is counted or written, read ${res.stateRaw}`, res);
}
/**
 * A one-shot run() of a plain command in a fresh seeded session (spent 0, no budget file, so the
 * automatic cap of 200) whose worst case is `want`: within the limit (reaching it exactly
 * included) it is committed and nothing is emitted; past it, it is denied with exactly M_LIMIT
 * naming `want`, and nothing is counted (D28).
 */
export function assertCounted(res, want, msg) {
  if (want <= LIMIT) {
    assert(quoted(res.state) === want, `${msg} — counted ${quoted(res.state)}, wanted ${want}`, res);
    assertDecision(res, null, `${msg} — within the limit no decision is made`);
    assert(res.raw === "", `${msg} — within the limit nothing is emitted`, res);
  } else {
    assertDecision(res, "deny", `${msg} — ${want} is past the ${LIMIT}cr limit`);
    const m = mLimit({ spent: 0, worst: want, limit: LIMIT, src: srcAuto(BALANCE), bf: res.bf });
    assert(res.message === m, `${msg} — exactly M_LIMIT naming ~${want}, read ${JSON.stringify(res.message).slice(0, 400)}`, res);
    assert(quoted(res.state) === 0, `${msg} — a deny counts nothing, read ${JSON.stringify(res.state)}`, res);
  }
}
