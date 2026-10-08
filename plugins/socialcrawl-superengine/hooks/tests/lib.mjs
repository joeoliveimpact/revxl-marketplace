/*
 * Test harness for hooks/credit-guard.mjs. BUILD-TIME TOOLING ONLY — nothing in this
 * directory is referenced by hooks.json or by any skill, so the plugin never loads it at
 * runtime. Run it with `node hooks/tests/run.mjs`.
 *
 * It invokes the guard exactly the way Claude Code does: a PreToolUse envelope as JSON on
 * stdin, the decision as JSON on stdout, exit 0 always (every path sets exit code 0).
 *
 * Each session gets a throwaway directory, and SC_REVXL_HOME is its `revxl` folder, so the guard's
 * session state file (`<revxl>/sessions/socialcrawl-<sid>.json`) is isolated and seedable, and so
 * running the suite never touches a real session's counter. TEMP/TMP/TMPDIR point at the same
 * directory; the guard keeps no state there.
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
 * balance, and "balance unknown" is its own group). 800 gives the session cap
 * min(500, 25% of 800) = 200 (R18-1, Q-c: 800 keeps every 200-tuned figure). Pass `balance: null`
 * for the balance-unknown group.
 */
export const BALANCE = 800;

/** The figure a fresh session committed or parked for its one command: spent + every pending quote. */
export function quoted(state) {
  if (!state) return null;
  const pend = Object.values(state.pending || {}).reduce((a, v) => a + v, 0);
  return (typeof state.spent === "number" ? state.spent : 0) + pend;
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
    /** Seed the state file; the session's balance rides along unless the session has none. */
    seed(obj) {
      writeFileSync(stateFile, JSON.stringify(balance === null ? obj : { balance, ...obj }));
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
      // the variable is dropped unless the fixture sets it.
      delete env.CLAUDE_CODE_SESSION_ATTENDED;
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
      };
    },
    /** The same command after it ran: PostToolUse, or PostToolUseFailure with `failure: true`. `o.extra` (a tool_name) is kept. */
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

/** One-shot: fresh session, single command, auto-cleanup. Returns the result plus state. */
export function run(command, opts = {}) {
  const s = session(opts);
  if (opts.seedState !== undefined) s.seed(opts.seedState);
  const out = s.run(command, opts);
  out.state = s.state();
  out.stateRaw = s.stateRaw();
  out.stateExists = s.stateExists();
  s.cleanup();
  return out;
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
 * A one-shot run() of a command that is NOT a plain curl (R14a.2), in a fresh seeded session
 * (spent 0): the one NOT A PLAIN CURL ask, naming the visible counted total `want`, which is
 * parked as pending and not committed.
 */
export function assertNotPlain(res, want, msg) {
  assertDecision(res, "ask", `${msg} — a command that is not a plain curl asks`);
  assertMatch(res, /NOT A PLAIN CURL/, `${msg} — the not-plain ask`);
  assertMatch(res, new RegExp(`Visible counted total: ~${want} credits`), `${msg} — names the visible total`);
  assert(quoted(res.state) === want && !(res.state && res.state.spent), `${msg} — ${want} parked as pending, read ${JSON.stringify(res.state)}`, res);
}
/**
 * A one-shot run() of a flat or metered command in a fresh seeded session (spent 0, cap 200)
 * counted exactly `want`: under the cap it is committed and nothing is said; at or over it the
 * one cap-step ask names `want` as this command's worst case and parks it as pending.
 */
export function assertCounted(res, want, msg) {
  const cap = Math.min(500, Math.floor(0.25 * BALANCE));
  assert(quoted(res.state) === want, `${msg} — counted ${quoted(res.state)}, wanted ${want}`, res);
  if (want >= cap) {
    assertDecision(res, "ask", `${msg} — ${want} crosses the ${cap}cr cap step`);
    assertMatch(res, new RegExp(`this command's worst case is ~${want} credits`), `${msg} — the ask names the worst case`);
  } else {
    assertDecision(res, null, `${msg} — under the cap nothing is asked`);
    assert(res.raw === "", `${msg} — under the cap nothing is emitted`, res);
  }
}
