#!/usr/bin/env node
/*
 * ledger.mjs — the CREDIT LEDGER. Snapshot the account's transaction log before a run, diff it
 * after, and reconcile what the plan QUOTED against what the vendor actually CHARGED.
 *
 *   node ledger.mjs snapshot [--out <file>]
 *   node ledger.mjs diff <before.json> [--after <file>] [--plan <plan.json>]
 *
 * WHY THIS EXISTS. The credit guard adjudicates a command BEFORE it runs, from the command
 * string. It cannot see what the vendor actually billed, it cannot see a refund, and it cannot
 * see a charge that some other process on this machine made while the run was in flight. The
 * quote in a research plan is therefore a PREDICTION until something reads the transaction log
 * back. This is that something. The guard's session cap is not the reconciliation mechanism
 * and was never meant to be — the plan and this file are.
 *
 * THE INVARIANT — the only network path this file may touch is `/v1/credits/`.
 * This script is a shipped network caller and the guard, which hooks the SHELL, cannot see it:
 * an import calls out without ever becoming a Bash command. So the restriction is enforced in
 * code, by ledgerUrl(), which throws BEFORE a transport is ever handed a URL. Every request in
 * this file is built by that one function. `credits/*` is account meta — the guard classifies
 * it as free (credit-guard.mjs, the `p.startsWith("credits/")` branch) — so the reconciliation
 * itself never appears on the bill it is reconciling.
 *
 * EXTERNAL ROWS ARE TAGGED, NEVER FAILED. Other things on this machine spend credits: a cron,
 * another session, a second terminal. Those rows land in the same log and they are NOT this
 * plan's overspend. They are attributed and printed under EXTERNAL, and they do not count
 * against the plan's ceiling. Failing a run over a charge it did not make would train everyone
 * to ignore the exit code.
 *
 * NOT ONE CREDIT FIGURE IS WRITTEN HERE. Quoted numbers come from the plan; actual numbers come
 * from the transaction rows. Unit prices live in hooks/costs.json and this file never reads it.
 *
 * Stdlib only (node:fs, node:path, node:os) plus global fetch, which is reachable only through
 * the injected transport, so the fixture suite exercises every path offline.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HOST = "https://www.socialcrawl.dev";
/* The one permitted path prefix. Referenced by ledgerUrl and by nothing else. */
const CREDITS_PREFIX = "/v1/credits/";
const TRANSACTIONS = "/v1/credits/transactions";
const PAGE_LIMIT = 50; // the documented `limit` for GET /v1/credits/transactions
const MAX_PAGES = 20; // pagination stops here and says so rather than looping forever

const USAGE =
  "usage: node ledger.mjs snapshot [--out <file>]\n" +
  "       node ledger.mjs diff <before.json> [--after <file>] [--plan <plan.json>]";

/* Collected as we go and printed in one block at the end — what this run could NOT establish.
 * Exported so the fixture suite can read a LIMIT back instead of scraping stdout for it. */
export const LIMITS = [];

class LedgerError extends Error {}

/* ------------------------------------------------------------------ THE INVARIANT
 * Every URL this file uses is built here. A path outside /v1/credits/ throws, and it throws
 * before any caller has a URL to hand a transport — so the rejection happens before a socket
 * can be opened, not after. Exported so the fixtures can assert the throw directly.
 */
export function ledgerUrl(path, params = {}) {
  const p = String(path || "");
  if (!p.startsWith(CREDITS_PREFIX)) {
    throw new LedgerError(
      `ledger.mjs may only call ${CREDITS_PREFIX}* — refused ${JSON.stringify(p)} before building a request. ` +
        `This file is a network caller the credit guard cannot see, so anything that could spend is blocked here in code.`
    );
  }
  const u = new URL(HOST + p);
  for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v == null ? "" : String(v));
  return u.toString();
}

/* --------------------------------------------------------------------- key resolution
 * Same order the onboarding skill documents: the env var only when it looks like a key, then
 * the file. The value is never printed, never logged, and never included in an error message.
 */
/* A second line, a CR or a NUL can't ride in a header, and fetch's error quotes the header, key and all. */
const CONTROL = /[\u0000-\u001f\u007f]/;

export function resolveKey(env = process.env, home = homedir()) {
  const fromEnv = String(env.SOCIALCRAWL_API_KEY || "").trim();
  const file = join(home, ".config", "socialcrawl", "api_key");
  const key = fromEnv.startsWith("sc_") ? fromEnv : existsSync(file) ? readFileSync(file, "utf8").trim() || null : null;
  if (key && CONTROL.test(key)) {
    throw new LedgerError("the SocialCrawl key (SOCIALCRAWL_API_KEY or ~/.config/socialcrawl/api_key) has a line break or control character inside it; nothing was sent");
  }
  return key;
}

/* The real transport. The ONLY place a request leaves this process; injected everywhere else.
 * A timeout, because a reconciliation that hangs blocks the run it was meant to make safe. */
const TIMEOUT_MS = 30000;
async function httpsTransport(url, key) {
  const res = await fetch(url, { headers: { "x-api-key": key }, signal: AbortSignal.timeout(TIMEOUT_MS) });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new LedgerError(
      `the credits endpoint answered ${res.status}` +
        (res.status === 401 ? " — the key was rejected (no key is printed here)" : "")
    );
  }
  return body;
}

/* One page. ledgerUrl runs FIRST, so a bad path never reaches `transport`. */
async function fetchPage({ path, params, key, transport }) {
  const url = ledgerUrl(path, params);
  try {
    return await transport(url, key);
  } catch (e) {
    // A transport error can quote the x-api-key header; the key never leaves in an error.
    const msg = String((e && e.message) || e);
    throw new LedgerError(key ? msg.split(key).join("<key>") : msg);
  }
}

/* ------------------------------------------------------------------------- snapshot */
export async function snapshot({ key, transport = httpsTransport } = {}) {
  if (!key) throw new LedgerError("no API key found. Set SOCIALCRAWL_API_KEY or save one to ~/.config/socialcrawl/api_key.");
  const items = [];
  let cursor = "";
  let remaining = null;
  let page = 0;
  for (;;) {
    const body = await fetchPage({
      path: TRANSACTIONS,
      params: { limit: PAGE_LIMIT, cursor, request_id: "" },
      key,
      transport,
    });
    page++;
    const data = (body && body.data) || {};
    for (const row of Array.isArray(data.items) ? data.items : []) items.push(row);
    if (remaining === null && body && typeof body.credits_remaining === "number") {
      remaining = body.credits_remaining; // the first page carries the current balance
    }
    cursor = data.next_cursor == null ? "" : String(data.next_cursor);
    if (!cursor) break;
    if (page >= MAX_PAGES) {
      LIMITS.push(
        `PAGINATION CAPPED at ${MAX_PAGES} pages — next_cursor was still set. Rows older than this ` +
          `snapshot's last page are not in it, so a diff against it can only see recent activity.`
      );
      break;
    }
  }
  return { takenAt: new Date().toISOString(), items, credits_remaining: remaining };
}

/* --------------------------------------------------------------- attribution + classification */

/* A plan leg writes an endpoint as "VERB path"; a transaction row writes the same endpoint with
 * a leading version segment and no verb. Same endpoint, two spellings. One normaliser, both
 * sides, so the lane set actually matches. (No spending path is spelled out anywhere in this
 * file — not in code and not in a comment. check_r6_execution.mjs E8 asserts that.) */
export function normPath(s) {
  return String(s || "")
    .trim()
    .replace(/^[a-z]+\s+/i, "") // a plan leg's leading VERB
    .replace(/^https?:\/\/[^/]+/i, "")
    .replace(/^\//, "")
    .replace(/^v1\//i, "")
    .replace(/\?.*$/, "")
    .replace(/\/+$/, "")
    .toLowerCase();
}

/* The picked option out of whatever was handed to --plan: an option object, or a router plan
 * with exactly one option, or a router plan naming its pick. A menu with no pick is an error —
 * guessing which option ran would silently reconcile against the wrong ceiling. */
export function pickOption(plan) {
  if (!plan || typeof plan !== "object") throw new LedgerError("--plan is not a JSON object");
  if (Array.isArray(plan.endpoints)) return plan;
  const options = Array.isArray(plan.options) ? plan.options : [];
  if (!options.length) throw new LedgerError("--plan has no endpoints[] and no options[] — nothing to reconcile against");
  const pickedId = plan.picked || plan.pickedId || "";
  if (pickedId) {
    const hit = options.find((o) => o && o.id === pickedId);
    if (!hit) throw new LedgerError(`--plan names picked ${JSON.stringify(pickedId)} but no option carries that id`);
    return hit;
  }
  if (options.length === 1) return options[0];
  throw new LedgerError(
    `--plan carries ${options.length} options and names no pick — pass the picked option, or add "picked": "<option id>"`
  );
}

/* New rows are the ones the before-snapshot had never seen, by id. */
export function newRows(before, after) {
  const seen = new Set((before.items || []).map((r) => r && r.id));
  return (after.items || []).filter((r) => r && !seen.has(r.id));
}

/*
 * Group the new rows, then net each group. A refund carries the same request_id as the spend it
 * reverses, so netting HAS to happen inside the attribution group or a refunded call reads as
 * full price. amount is negative for a spend, positive for a refund: actual = -(sum).
 */
export function attribute(rows, laneSet) {
  const groups = new Map();
  for (const r of rows) {
    const rid = r.request_id == null || r.request_id === "" ? null : String(r.request_id);
    const ep = normPath(r.endpoint);
    const key = rid ? `rid:${rid}` : `ep:${ep || "(none)"}`;
    if (!groups.has(key)) {
      groups.set(key, { key, by: rid ? "request_id" : "endpoint", ref: rid || ep || "(none)", endpoint: "", rows: [], refunds: 0, actual: 0 });
    }
    const g = groups.get(key);
    g.rows.push(r);
    if (!g.endpoint && ep) g.endpoint = ep; // a refund row can carry a null endpoint
    const amt = Number(r.amount);
    if (Number.isFinite(amt)) {
      g.actual += -amt;
      if (amt > 0) g.refunds++;
    }
  }
  for (const g of groups.values()) {
    g.lane = !!g.endpoint && laneSet.has(g.endpoint);
    if (!g.endpoint) {
      LIMITS.push(
        `A row group attributed by ${g.by} ${JSON.stringify(g.ref)} carries no endpoint, so it cannot be matched ` +
          `to the allowlist. It is reported EXTERNAL and left out of the lane total.`
      );
    }
  }
  return [...groups.values()];
}

/* The plan's quoted figure for one endpoint, if the plan carried one. Never derived here: this
 * file prices nothing, so an unquoted leg prints as unquoted and says so. */
function quotedFor(option, endpoint) {
  const leg = (option.endpoints || []).find((l) => l && normPath(l.call) === endpoint);
  if (!leg) return null;
  if (typeof leg.quoted === "number") return { low: leg.quoted, high: leg.quoted };
  if (Array.isArray(leg.quoted) && leg.quoted.length === 2) return { low: Number(leg.quoted[0]), high: Number(leg.quoted[1]) };
  return null;
}

const fmtQuote = (q) => (q === null ? "—" : q.low === q.high ? String(q.low) : `${q.low}..${q.high}`);
const fmtDelta = (q, a) => {
  if (q === null) return "—";
  if (a < q.low) return String(a - q.low);
  if (a > q.high) return `+${a - q.high}`;
  return "0";
};

/* --------------------------------------------------------------------------- the diff report */
export function report(groups, option, out = (s) => process.stdout.write(s + "\n")) {
  const lane = groups.filter((g) => g.lane);
  const external = groups.filter((g) => !g.lane);
  const laneTotal = lane.reduce((n, g) => n + g.actual, 0);
  const externalTotal = external.reduce((n, g) => n + g.actual, 0);
  const ceiling = option && typeof option.ceiling === "number" ? option.ceiling : null;

  out("");
  out(`LANE — charges on the picked option's allowlist${ceiling === null ? "" : `, ceiling ${ceiling}`}`);
  if (!lane.length) out("  (no lane rows)");
  for (const g of lane) {
    const q = option ? quotedFor(option, g.endpoint) : null;
    out(
      `  ${g.endpoint}  quoted ${fmtQuote(q)} / actual ${g.actual} / delta ${fmtDelta(q, g.actual)}` +
        `  [by ${g.by} ${g.ref}${g.refunds ? `, ${g.refunds} refund row(s) netted` : ""}]`
    );
  }
  out(`  lane total: actual ${laneTotal}${ceiling === null ? "" : ` against ceiling ${ceiling}`}`);

  out("");
  out("EXTERNAL — charges outside this plan's allowlist. Attributed, not failed; outside the ceiling.");
  if (!external.length) out("  (none)");
  for (const g of external) {
    out(`  ${g.endpoint || "(no endpoint on the row)"}  actual ${g.actual}  [by ${g.by} ${g.ref}]`);
  }
  out(`  external total: ${externalTotal}`);

  const over = ceiling !== null && laneTotal > ceiling;
  out("");
  out(over ? `OVER CEILING — lane actual ${laneTotal} exceeds ceiling ${ceiling}. Stop the run; call nothing further.` : "within ceiling");
  return { laneTotal, externalTotal, over, ceiling };
}

/* ---------------------------------------------------------------------------------- the CLI */
function readJson(path, what) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (e) {
    throw new LedgerError(`could not read ${what} ${JSON.stringify(path)}: ${(e && e.message) || e}`);
  }
}

function parseFlags(argv, allowed) {
  const out = {};
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const name = a.slice(2);
      if (!allowed.includes(name)) throw new LedgerError(`unknown argument ${JSON.stringify(a)}.\n${USAGE}`);
      out[name] = argv[++i];
      if (out[name] == null) throw new LedgerError(`${a} needs a value.\n${USAGE}`);
    } else rest.push(a);
  }
  return { flags: out, rest };
}

export async function main(argv, { transport = httpsTransport, env = process.env, home = homedir() } = {}) {
  const cmd = argv[0];
  if (!cmd || cmd === "--help" || cmd === "-h") {
    process.stdout.write(USAGE + "\n");
    return 0;
  }

  if (cmd === "snapshot") {
    const { flags, rest } = parseFlags(argv.slice(1), ["out"]);
    if (rest.length) throw new LedgerError(`snapshot takes no positional argument, got ${JSON.stringify(rest[0])}.\n${USAGE}`);
    const key = resolveKey(env, home);
    if (!key) throw new LedgerError("no API key found. Set SOCIALCRAWL_API_KEY or save one to ~/.config/socialcrawl/api_key.");
    const snap = await snapshot({ key, transport });
    const text = JSON.stringify(snap, null, 2) + "\n";
    if (flags.out) {
      writeFileSync(flags.out, text);
      process.stdout.write(`ledger: snapshot ${snap.items.length} row(s) -> ${flags.out}\n`);
    } else process.stdout.write(text);
    LIMITS.forEach((l) => process.stdout.write(`LIMIT: ${l}\n`));
    return 0;
  }

  if (cmd === "diff") {
    const { flags, rest } = parseFlags(argv.slice(1), ["after", "plan"]);
    if (rest.length !== 1) throw new LedgerError(`diff needs exactly one <before.json>.\n${USAGE}`);
    const before = readJson(rest[0], "the before snapshot");
    let after;
    if (flags.after) after = readJson(flags.after, "the after snapshot");
    else {
      const key = resolveKey(env, home);
      if (!key) throw new LedgerError("no API key found. Set SOCIALCRAWL_API_KEY or save one to ~/.config/socialcrawl/api_key.");
      after = await snapshot({ key, transport });
    }

    let option = null;
    if (flags.plan) option = pickOption(readJson(flags.plan, "the plan"));
    else LIMITS.push("NO --plan GIVEN — there is no allowlist and no ceiling, so every row reads EXTERNAL and only actuals are printed.");

    const laneSet = new Set(option ? (option.endpoints || []).map((l) => normPath(l && l.call)).filter(Boolean) : []);
    const rows = newRows(before, after);
    const groups = attribute(rows, laneSet);

    process.stdout.write(`ledger diff — ${rows.length} new row(s) since ${before.takenAt || "the before snapshot"}\n`);
    if (option && !(option.endpoints || []).some((l) => l && typeof l.quoted !== "undefined")) {
      LIMITS.push("The plan carries no per-leg `quoted` figure, so every lane row prints its quote as `—`. Quoted numbers are the plan's to supply; this file prices nothing.");
    }
    const res = report(groups, option);
    LIMITS.forEach((l) => process.stdout.write(`LIMIT: ${l}\n`));
    return res.over ? 2 : 0;
  }

  throw new LedgerError(`unknown subcommand ${JSON.stringify(cmd)}.\n${USAGE}`);
}

const isEntry = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isEntry) {
  // process.exitCode, never an explicit exit: after a fetch on Node 24/Windows that aborts with rc
  // 127 (P2). 2 = over the ceiling, 1 = an error, 0 = done.
  main(process.argv.slice(2))
    .then((code) => { process.exitCode = code; })
    .catch((e) => {
      process.stderr.write(`ledger: ${(e && e.message) || e}\n`);
      process.exitCode = 1;
    });
}
