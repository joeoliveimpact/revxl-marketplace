/*
 * R6 — hooks/ledger.mjs, the credit ledger: snapshot, diff, reconcile.
 *
 * Every fixture here carries a KILLING MUTATION, the same discipline roster.mjs uses: a copy of
 * the ledger with one substitution applied has to FAIL the assertion the unmutated ledger
 * passes. An assertion no mutant can break is decoration.
 *
 * ZERO CREDITS, ZERO NETWORK. Nothing in this file opens a socket, and that is structural, not
 * a promise:
 *   · every `diff` runs with `--after <fixture>`, which short-circuits the snapshot entirely —
 *     no key is read and no transport is constructed;
 *   · every `snapshot` runs inside a DRIVER script that injects a fake transport, so the real
 *     `fetch` is never reached;
 *   · the one fixture that exercises the real CLI's snapshot path (L10) runs against a mutant
 *     whose transport body is `throw new Error("TRANSPORT REACHED")`, so even a key resolving
 *     unexpectedly cannot produce a request — it produces a failing assertion instead.
 *
 * THE TRANSACTION ROWS are built from the archived schema for GET /v1/credits/transactions —
 * id, type, amount (negative = spend), balance_after, description, endpoint, platform,
 * credit_tier, request_id, created_at, with data.next_cursor for pagination. No captured
 * payload exists, so the schema is the only source and `row()` below is its one construction
 * site: a field that drifts, drifts in one place.
 */
import { assert } from "../lib.mjs";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const LEDGER = resolve(HERE, "..", "..", "ledger.mjs");

/* Never a real key. Split so no scanner ever reads this line as one. */
const FAKE_KEY = "sc_" + "fixture-not-a-key";

const tmp = () => mkdtempSync(join(tmpdir(), "sc-ledger-test-"));

/* One archived transaction row. Every field the schema names, defaults where it allows null. */
const row = (o) => ({
  id: o.id,
  type: o.type || "usage",
  amount: o.amount,
  balance_after: o.balance_after ?? 0,
  description: o.description ?? null,
  endpoint: o.endpoint ?? null,
  platform: o.platform ?? null,
  credit_tier: o.credit_tier ?? "standard",
  request_id: o.request_id ?? null,
  created_at: o.created_at || "2026-09-07T00:00:00.000Z",
});

const snap = (items) => ({ takenAt: "2026-09-07T00:00:00.000Z", items, credits_remaining: 4980 });

/* A picked option in the router's plan shape, plus the per-leg `quoted` the plan supplies. */
const plan = (legs, ceiling) => ({
  id: "fixture-option",
  name: "Fixture option",
  route: "socialcrawl",
  endpoints: legs,
  quote: { low: 0, high: ceiling, driver: "fixture" },
  ceiling,
});
const leg = (call, quoted) => ({ call, countLow: 1, countHigh: 1, role: "fixture leg", ...(quoted === undefined ? {} : { quoted }) });

/** Write JSON into a throwaway dir and return its path. */
function jsonFile(dir, name, value) {
  const p = join(dir, name);
  writeFileSync(p, JSON.stringify(value, null, 2) + "\n");
  return p;
}

/** A copy of the ledger with substitutions applied. Anchors must exist or the fixture fails. */
function mutate(pairs) {
  let src = readFileSync(LEDGER, "utf8");
  for (const [find, replace] of pairs) {
    if (!src.includes(find)) throw new Error(`mutation anchor not found in ledger.mjs: ${JSON.stringify(find)}`);
    src = src.split(find).join(replace);
  }
  const dest = join(tmp(), "ledger.mjs");
  writeFileSync(dest, src);
  return dest;
}

/** A scrubbed environment: no key in it, and home pointed at an empty directory. */
const scrubbed = (dir) => ({ ...process.env, SOCIALCRAWL_API_KEY: "", HOME: dir, USERPROFILE: dir });

/** One CLI invocation. `ledger` swaps in a mutant copy. */
function cli(args, { ledger, env } = {}) {
  const d = tmp();
  const r = spawnSync(process.execPath, [ledger || LEDGER, ...args], {
    encoding: "utf8",
    input: "",
    env: env || scrubbed(d),
  });
  return { exit: r.status, stdout: String(r.stdout || ""), stderr: String(r.stderr || ""), all: String(r.stdout || "") + String(r.stderr || "") };
}

/**
 * Run `body` in a script that has imported the ledger as `L`, with a fake transport in scope.
 * This is how the snapshot path is exercised without a socket: `T.calls` records every URL the
 * transport was handed, and `T.fn` is what gets injected.
 */
function drive(body, { ledger, pages } = {}) {
  const d = tmp();
  const f = join(d, "driver.mjs");
  writeFileSync(
    f,
    `import * as L from ${JSON.stringify(pathToFileURL(ledger || LEDGER).href)};\n` +
      `const PAGES = ${JSON.stringify(pages || [])};\n` +
      `const T = { calls: [], fn: async (url) => { T.calls.push(url); return PAGES[Math.min(T.calls.length - 1, PAGES.length - 1)]; } };\n` +
      `const KEY = ${JSON.stringify(FAKE_KEY)};\n` +
      `const out = (o) => process.stdout.write(JSON.stringify(o) + "\\n");\n` +
      `try {\n${body}\n} catch (e) { out({ threw: String((e && e.message) || e), calls: T.calls.length }); }\n`
  );
  const r = spawnSync(process.execPath, [f], { encoding: "utf8", input: "", env: scrubbed(d) });
  const text = String(r.stdout || "").trim();
  let json = null;
  try {
    json = JSON.parse(text.split("\n").pop());
  } catch { /* left null — the assertion reports the raw text */ }
  return { exit: r.status, stdout: text, stderr: String(r.stderr || ""), json };
}

/** A transactions page in the archived response shape. */
const page = (items, next_cursor = null) => ({
  success: true,
  platform: "meta",
  endpoint: "/v1/credits/transactions",
  data: { items, next_cursor },
  credits_used: 0,
  credits_remaining: 4980,
  request_id: "fixture",
  cached: false,
});

const AD = "/v1/facebook/adlibrary/ad";
const SEARCH = "/v1/reddit/omni-search";

export default [
  /* ------------------------------------------------------------------ the diff, on fixtures */
  {
    id: "L1-ledger-quoted-equals-actual-is-still-printed",
    desc: "an on-quote row prints `quoted / actual / delta 0` — the debrief's cost beat reads this line, so a run that matched its quote must still produce one",
    fn() {
      const d = tmp();
      const before = jsonFile(d, "before.json", snap([]));
      const after = jsonFile(d, "after.json", snap([row({ id: "t1", amount: -15, endpoint: AD, request_id: "req_1" })]));
      const p = jsonFile(d, "plan.json", plan([leg("GET facebook/adlibrary/ad", 15)], 15));

      const r = cli(["diff", before, "--after", after, "--plan", p]);
      assert(r.exit === 0, `on-quote diff must exit 0, got ${r.exit}\n${r.all}`);
      assert(
        /facebook\/adlibrary\/ad\s+quoted 15 \/ actual 15 \/ delta 0/.test(r.stdout),
        `the equal row must still print quoted/actual/delta\n${r.all}`
      );

      // KILL: report only the rows that disagree with their quote — the "nothing to see" bug.
      const m = mutate([["  for (const g of lane) {", "  for (const g of lane) {\n    { const q = quotedFor(option, g.endpoint); if (q && q.low === g.actual && q.high === g.actual) continue; }"]]);
      const k = cli(["diff", before, "--after", after, "--plan", p], { ledger: m });
      assert(!/actual 15 \/ delta 0/.test(k.stdout), `the mutant must drop the equal row, or L1 proves nothing\n${k.all}`);
    },
  },
  {
    id: "L2-ledger-refund-nets-against-its-spend",
    desc: "a held-ceiling endpoint that refunds down: the refund row shares the spend's request_id, so actual is the NET, not the gross",
    fn() {
      const d = tmp();
      const before = jsonFile(d, "before.json", snap([]));
      const after = jsonFile(
        d,
        "after.json",
        snap([
          row({ id: "t1", amount: -8, endpoint: SEARCH, request_id: "req_2" }),
          row({ id: "t2", type: "refund", amount: 5, endpoint: null, request_id: "req_2" }),
        ])
      );
      const p = jsonFile(d, "plan.json", plan([leg("GET reddit/omni-search", 8)], 8));

      const r = cli(["diff", before, "--after", after, "--plan", p]);
      assert(r.exit === 0, `a refunded run is under quote, not a failure — got ${r.exit}\n${r.all}`);
      assert(/quoted 8 \/ actual 3 \/ delta -5/.test(r.stdout), `the refund must net against the spend\n${r.all}`);
      assert(/refund row\(s\) netted/.test(r.stdout), `the netting must be visible in the line, not silent\n${r.all}`);

      // KILL: count spends only. Gross 8 reads as on-quote and the refund vanishes.
      const m = mutate([["      g.actual += -amt;", "      if (amt < 0) g.actual += -amt;"]]);
      const k = cli(["diff", before, "--after", after, "--plan", p], { ledger: m });
      assert(/actual 8/.test(k.stdout), `the mutant must report the gross, or L2 proves nothing\n${k.all}`);
    },
  },
  {
    id: "L3-ledger-over-ceiling-exits-2",
    desc: "the ceiling is an abort control: lane actual above it exits 2, which is what stops the run",
    fn() {
      const d = tmp();
      const before = jsonFile(d, "before.json", snap([]));
      const after = jsonFile(d, "after.json", snap([row({ id: "t1", amount: -40, endpoint: AD, request_id: "req_3" })]));
      const p = jsonFile(d, "plan.json", plan([leg("GET facebook/adlibrary/ad", 15)], 35));

      const r = cli(["diff", before, "--after", after, "--plan", p]);
      assert(r.exit === 2, `over the ceiling must exit 2, got ${r.exit}\n${r.all}`);
      assert(/OVER CEILING/.test(r.stdout), `exit 2 must be explained in words too\n${r.all}`);

      // KILL: raise the comparison out of reach. Same overspend, silent exit 0.
      const m = mutate([["  const over = ceiling !== null && laneTotal > ceiling;", "  const over = false;"]]);
      const k = cli(["diff", before, "--after", after, "--plan", p], { ledger: m });
      assert(k.exit === 0, `the mutant must stop failing, or L3 proves nothing\n${k.all}`);
    },
  },
  {
    id: "L4-ledger-external-row-is-tagged-not-failed",
    desc: "a charge from outside this plan's allowlist (another session, a cron) is attributed under EXTERNAL and left outside the ceiling — it is not this run's overspend",
    fn() {
      const d = tmp();
      const before = jsonFile(d, "before.json", snap([]));
      const after = jsonFile(
        d,
        "after.json",
        snap([
          row({ id: "t1", amount: -10, endpoint: AD, request_id: "req_4" }),
          row({ id: "t2", amount: -25, endpoint: "/v1/instagram/profile/posts", request_id: "cron_9" }),
        ])
      );
      const p = jsonFile(d, "plan.json", plan([leg("GET facebook/adlibrary/ad", 10)], 15));

      const r = cli(["diff", before, "--after", after, "--plan", p]);
      assert(r.exit === 0, `an external charge must not fail the run, got ${r.exit}\n${r.all}`);
      assert(/EXTERNAL[\s\S]*instagram\/profile\/posts\s+actual 25/.test(r.stdout), `the external row must be attributed and printed\n${r.all}`);
      assert(/lane total: actual 10/.test(r.stdout), `the external 25 must stay out of the lane total\n${r.all}`);

      // KILL: treat every endpoint as in-lane. The cron's 25 now busts a ceiling it never touched.
      const m = mutate([["    g.lane = !!g.endpoint && laneSet.has(g.endpoint);", "    g.lane = !!g.endpoint;"]]);
      const k = cli(["diff", before, "--after", after, "--plan", p], { ledger: m });
      assert(k.exit === 2, `the mutant must fail on the external charge, or L4 proves nothing\n${k.all}`);
    },
  },
  {
    id: "L5-ledger-null-request-id-attributes-by-endpoint",
    desc: "the schema allows a null request_id; those rows are attributed by endpoint instead, and two of them are ONE charge, not two",
    fn() {
      const d = tmp();
      const before = jsonFile(d, "before.json", snap([]));
      const after = jsonFile(
        d,
        "after.json",
        snap([
          row({ id: "t1", amount: -2, endpoint: SEARCH, request_id: null }),
          row({ id: "t2", amount: -3, endpoint: SEARCH, request_id: null }),
        ])
      );
      const p = jsonFile(d, "plan.json", plan([leg("GET reddit/omni-search", 5)], 5));

      const r = cli(["diff", before, "--after", after, "--plan", p]);
      assert(r.exit === 0, `expected exit 0, got ${r.exit}\n${r.all}`);
      assert(/omni-search\s+quoted 5 \/ actual 5 \/ delta 0\s+\[by endpoint/.test(r.stdout), `both null-id rows must land in one endpoint-attributed group\n${r.all}`);
      const laneLines = r.stdout.split("\n").filter((l) => /omni-search\s+quoted/.test(l));
      assert(laneLines.length === 1, `expected one lane line, got ${laneLines.length}\n${r.all}`);

      // KILL: fall back to the row id instead of the endpoint — two groups, neither one the charge.
      const m = mutate([['`ep:${ep || "(none)"}`', "`ep:${r.id}`"]]);
      const k = cli(["diff", before, "--after", after, "--plan", p], { ledger: m });
      assert(!/actual 5 \/ delta 0/.test(k.stdout), `the mutant must split the group, or L5 proves nothing\n${k.all}`);
    },
  },
  {
    id: "L6-ledger-empty-diff-reports-nothing-charged",
    desc: "no new rows means nothing was charged — it must say so and exit 0, never fall through to an empty report that reads like a failure",
    fn() {
      const d = tmp();
      const rows = [row({ id: "t1", amount: -15, endpoint: AD, request_id: "req_old" })];
      const before = jsonFile(d, "before.json", snap(rows));
      const after = jsonFile(d, "after.json", snap(rows));
      const p = jsonFile(d, "plan.json", plan([leg("GET facebook/adlibrary/ad", 15)], 15));

      const r = cli(["diff", before, "--after", after, "--plan", p]);
      assert(r.exit === 0, `an empty diff must exit 0, got ${r.exit}\n${r.all}`);
      assert(/0 new row\(s\)/.test(r.stdout), `the row count must be stated\n${r.all}`);
      assert(/\(no lane rows\)/.test(r.stdout) && /lane total: actual 0/.test(r.stdout), `an empty lane must be named, not blank\n${r.all}`);

      // KILL: forget what the before snapshot already held — the old row reads as a new charge.
      const m = mutate([["  const seen = new Set((before.items || []).map((r) => r && r.id));", "  const seen = new Set();"]]);
      const k = cli(["diff", before, "--after", after, "--plan", p], { ledger: m });
      assert(/1 new row\(s\)/.test(k.stdout), `the mutant must invent a new row, or L6 proves nothing\n${k.all}`);
    },
  },
  {
    id: "L11-ledger-reconciles-a-package-option",
    desc: "R11/P13: a packages.json row with its pick reconciles against that option's own legs and ceiling — at the ceiling exits 0, one credit over exits 2",
    fn() {
      const PKG = resolve(HERE, "..", "..", "..", "skills", "research-plays", "references", "packages.json");
      const pkgRow = JSON.parse(readFileSync(PKG, "utf8")).rows.find((r) => r.id === "find_creators");
      const opt = pkgRow && pkgRow.options.find((o) => o.id === "search-then-size");
      assert(opt && opt.endpoints.length === 2 && typeof opt.ceiling === "number", `find_creators/search-then-size must carry two legs and a numeric ceiling\n${JSON.stringify(opt)}`);
      const [ep1, ep2] = opt.endpoints.map((l) => "/v1/" + l.call.replace(/^[A-Z]+\s+/, ""));
      const C = opt.ceiling;

      const d = tmp();
      const before = jsonFile(d, "before.json", snap([]));
      const at = jsonFile(d, "at.json", snap([row({ id: "t1", amount: -1, endpoint: ep1, request_id: "req_1" }), row({ id: "t2", amount: -(C - 1), endpoint: ep2, request_id: "req_2" })]));
      const over = jsonFile(d, "over.json", snap([row({ id: "t1", amount: -1, endpoint: ep1, request_id: "req_1" }), row({ id: "t2", amount: -C, endpoint: ep2, request_id: "req_2" })]));
      const p = jsonFile(d, "plan.json", { ...pkgRow, picked: opt.id });

      const r = cli(["diff", before, "--after", at, "--plan", p]);
      assert(r.exit === 0, `a lane total equal to the package ceiling must exit 0, got ${r.exit}\n${r.all}`);
      assert(new RegExp(`ceiling ${C}\\b`).test(r.stdout) && new RegExp(`lane total: actual ${C} against ceiling ${C}`).test(r.stdout), `both legs must land in the lane against the option's ceiling ${C}\n${r.all}`);
      const o = cli(["diff", before, "--after", over, "--plan", p]);
      assert(o.exit === 2 && /OVER CEILING/.test(o.stdout), `one credit over the package ceiling must exit 2, got ${o.exit}\n${o.all}`);

      // KILL: ignore the pick and reconcile against the row's first option — a different lane and ceiling.
      const m = mutate([["    const hit = options.find((o) => o && o.id === pickedId);", "    const hit = options[0];"]]);
      const k = cli(["diff", before, "--after", at, "--plan", p], { ledger: m });
      assert(!new RegExp(`lane total: actual ${C} against ceiling ${C}`).test(k.stdout), `the mutant must reconcile against the wrong option, or L11 proves nothing\n${k.all}`);
    },
  },

  /* ------------------------------------------------- the snapshot path, on injected transports */
  {
    id: "L7-ledger-pagination-consumes-the-next-cursor",
    desc: "next_cursor non-null means there is another page of charges; a snapshot that stops at page one under-reports the run, and a snapshot that loops forever says so instead",
    fn() {
      const two = [
        page([row({ id: "t1", amount: -15, endpoint: AD, request_id: "req_1" })], "cursor_2"),
        page([row({ id: "t2", amount: -5, endpoint: SEARCH, request_id: "req_2" })], null),
      ];
      const r = drive(`const s = await L.snapshot({ key: KEY, transport: T.fn }); out({ items: s.items.length, calls: T.calls.length, remaining: s.credits_remaining });`, { pages: two });
      assert(r.json && r.json.items === 2, `both pages must be consumed, got ${r.stdout}`);
      assert(r.json.calls === 2, `the transport must be called twice, got ${r.stdout}`);
      assert(r.json.remaining === 4980, `credits_remaining must come off the first page, got ${r.stdout}`);

      // The cap: a cursor that never goes null must stop AND declare that it stopped early.
      const endless = [page([row({ id: "t9", amount: -1, endpoint: AD, request_id: "req_9" })], "cursor_forever")];
      const c = drive(`const s = await L.snapshot({ key: KEY, transport: T.fn }); out({ calls: T.calls.length, limits: L.LIMITS.filter((l) => /PAGINATION CAPPED/.test(l)).length });`, { pages: endless });
      assert(c.json && c.json.calls === 20, `pagination must stop at the documented cap, got ${c.stdout}`);
      assert(c.json.limits === 1, `a capped snapshot must print a LIMIT, got ${c.stdout}`);

      // KILL: stop after the first page. The second page's charges never enter the reconciliation.
      const m = mutate([["    if (!cursor) break;", "    break;"]]);
      const k = drive(`const s = await L.snapshot({ key: KEY, transport: T.fn }); out({ items: s.items.length, calls: T.calls.length });`, { pages: two, ledger: m });
      assert(k.json && k.json.items === 1, `the mutant must see one page, or L7 proves nothing\n${k.stdout}`);
    },
  },
  {
    id: "L8-ledger-snapshot-round-trips-through-diff",
    desc: "the file `snapshot` writes is the file `diff` reads: a snapshot diffed against itself has zero new rows, or the two halves do not agree on their own format",
    fn() {
      const d = tmp();
      const out = join(d, "snap.json");
      const pages = [
        page([
          row({ id: "t1", amount: -15, endpoint: AD, request_id: "req_1" }),
          row({ id: "t2", amount: -5, endpoint: SEARCH, request_id: "req_2" }),
        ], null),
      ];
      const w = drive(
        `const s = await L.snapshot({ key: KEY, transport: T.fn });\n` +
          `const { writeFileSync } = await import("node:fs");\n` +
          `writeFileSync(${JSON.stringify(out)}, JSON.stringify(s, null, 2) + "\\n");\n` +
          `out({ items: s.items.length });`,
        { pages }
      );
      assert(w.json && w.json.items === 2, `the snapshot must hold both rows, got ${w.stdout}`);

      const r = cli(["diff", out, "--after", out]);
      assert(r.exit === 0, `a self-diff must exit 0, got ${r.exit}\n${r.all}`);
      assert(/0 new row\(s\)/.test(r.stdout), `a snapshot against itself must find no new rows\n${r.all}`);
      assert(/LIMIT: NO --plan GIVEN/.test(r.stdout), `without a plan there is no allowlist and no ceiling — that must be declared, not assumed\n${r.all}`);

      // KILL: write the rows under a different key. The file still looks like a snapshot, but
      // diff reads items[], so the same two rows now read as two brand-new charges.
      const m = mutate([["  return { takenAt: new Date().toISOString(), items, credits_remaining: remaining };", "  return { takenAt: new Date().toISOString(), rows: items, items: [], credits_remaining: remaining };"]]);
      const bad = join(d, "bad.json");
      drive(
        `const s = await L.snapshot({ key: KEY, transport: T.fn });\n` +
          `const { writeFileSync } = await import("node:fs");\n` +
          `writeFileSync(${JSON.stringify(bad)}, JSON.stringify(s, null, 2) + "\\n");\n` +
          `out({ ok: 1 });`,
        { pages, ledger: m }
      );
      const k = cli(["diff", bad, "--after", out]);
      assert(/2 new row\(s\)/.test(k.stdout), `the mutant snapshot must fail to round-trip, or L8 proves nothing\n${k.all}`);
    },
  },

  /* --------------------------------------------------------------------------- the invariant */
  {
    id: "L9-ledger-refuses-any-path-outside-credits-before-a-request",
    desc: "THE INVARIANT: this file is a shipped network caller the credit guard cannot see, so a path outside /v1/credits/ throws in the URL builder — before a transport is ever handed anything",
    fn() {
      const t = drive(`try { L.ledgerUrl("/v1/instagram/profile"); out({ threw: null }); } catch (e) { out({ threw: String(e.message) }); }`);
      assert(t.json && typeof t.json.threw === "string", `ledgerUrl must throw on a spending path, got ${t.stdout}`);
      assert(/\/v1\/credits\//.test(t.json.threw), `the refusal must name the only permitted prefix, got ${t.json.threw}`);

      // The throw has to beat the socket: point the snapshot at a spending path and the
      // transport must record ZERO calls.
      const spend = mutate([['const TRANSACTIONS = "/v1/credits/transactions";', 'const TRANSACTIONS = "/v1/instagram/profile";']]);
      const s = drive(`await L.snapshot({ key: KEY, transport: T.fn }); out({ threw: null, calls: T.calls.length });`, { ledger: spend, pages: [page([], null)] });
      assert(s.json && typeof s.json.threw === "string", `a spending path must abort the snapshot, got ${s.stdout}`);
      assert(s.json.calls === 0, `the transport must never have been called, got ${s.stdout}`);

      // KILL: disable the guard. The same spending path now builds a URL and reaches the transport.
      const off = mutate([
        ['const TRANSACTIONS = "/v1/credits/transactions";', 'const TRANSACTIONS = "/v1/instagram/profile";'],
        ["  if (!p.startsWith(CREDITS_PREFIX)) {", "  if (false) {"],
      ]);
      const k = drive(`await L.snapshot({ key: KEY, transport: T.fn }); out({ threw: null, calls: T.calls.length });`, { ledger: off, pages: [page([], null)] });
      assert(k.json && k.json.threw === null && k.json.calls === 1, `the mutant must reach the transport, or L9 proves nothing\n${k.stdout}`);
    },
  },
  {
    id: "L10-ledger-no-key-exits-1-without-a-request",
    desc: "no key means a plain refusal and no request at all — not a 401 round trip, and never the key itself in the message",
    fn() {
      // Run against a mutant whose transport body throws a marker instead of calling fetch. That
      // makes the "no request" assertion checkable AND makes this fixture unable to hit the
      // network even if a key resolved unexpectedly.
      const TRIP = ['  const res = await fetch(url, { headers: { "x-api-key": key }, signal: AbortSignal.timeout(TIMEOUT_MS) });', '  throw new Error("TRANSPORT REACHED");'];
      const guarded = mutate([TRIP]);
      const r = cli(["snapshot"], { ledger: guarded });
      assert(r.exit === 1, `a missing key must exit 1, got ${r.exit}\n${r.all}`);
      assert(/no API key found/.test(r.stderr), `the refusal must be plain English, got ${JSON.stringify(r.stderr)}`);
      assert(!/TRANSPORT REACHED/.test(r.all), `nothing may be requested without a key\n${r.all}`);
      assert(!/sc_/.test(r.all), `no key material may appear in the output\n${r.all}`);

      // KILL: drop the key check. The run now walks straight into the transport.
      const k = cli(["snapshot"], {
        ledger: mutate([
          TRIP,
          [
            '    const key = resolveKey(env, home);\n    if (!key) throw new LedgerError("no API key found. Set SOCIALCRAWL_API_KEY or save one to ~/.config/socialcrawl/api_key.");\n    const snap = await snapshot({ key, transport });',
            '    const snap = await snapshot({ key: "unchecked", transport });',
          ],
        ]),
      });
      assert(/TRANSPORT REACHED/.test(k.all), `the mutant must reach the transport, or L10 proves nothing\n${k.all}`);
    },
  },
  {
    id: "L12-ledger-a-key-with-a-control-character-never-reaches-output",
    desc: "R15.2 S11: a key with a line feed, a CR or a NUL inside it, in the key file or in SOCIALCRAWL_API_KEY, is refused before any request in one plain line that never holds the key; a transport error that quotes the key prints it as <key>",
    fn() {
      const CANARY = "sc_" + "CANARY0000"; // a dummy, split so no scanner reads it as one
      const leaks = (s) => /CANARY/.test(String(s));
      const mask = (s) => String(s).replace(/CANARY\d*/g, "<CANARY>");
      const DEAD = "http://127.0.0.1:9";
      const offline = (d, extra) => ({ ...scrubbed(d), HTTPS_PROXY: DEAD, HTTP_PROXY: DEAD, ALL_PROXY: DEAD, NODE_USE_ENV_PROXY: "1", ...extra });
      const keyHome = (text) => {
        const d = tmp();
        mkdirSync(join(d, ".config", "socialcrawl"), { recursive: true });
        writeFileSync(join(d, ".config", "socialcrawl", "api_key"), text + "\n");
        return d;
      };

      // The real CLI and its real transport: its stdout and stderr are what the Bash tool_result
      // shows. An OS environment can't hold a NUL, so the env cases here are LF and CR.
      const cli6 = [
        ["file LF", offline(keyHome(CANARY + "\nX"))],
        ["file CR", offline(keyHome(CANARY + "\rX"))],
        ["file NUL", offline(keyHome(CANARY + "\u0000X"))],
        ["env LF", offline(tmp(), { SOCIALCRAWL_API_KEY: CANARY + "\nX" })],
        ["env CR", offline(tmp(), { SOCIALCRAWL_API_KEY: CANARY + "\rX" })],
      ];
      for (const [label, env] of cli6) {
        const r = cli(["snapshot"], { env });
        assert(r.exit === 1 && /line break or control character/.test(r.stderr) && !leaks(r.all), `CLI ${label}: exit 1, one plain line, no key (exit ${r.exit}: ${mask(r.all)})`);
      }

      // In process, all six cases (env NUL included). H runs undici's own header check, the one
      // fetch runs before sending; building Headers opens no socket.
      const body =
        `const C = ${JSON.stringify(CANARY)};\n` +
        `const fs = await import("node:fs"); const os = await import("node:os"); const path = await import("node:path");\n` +
        `const base = fs.mkdtempSync(path.join(os.tmpdir(), "sc-ledger-l11-"));\n` +
        `const H = { calls: 0, fn: async (url, key) => { H.calls++; new Headers({ "x-api-key": key }); return ${JSON.stringify(page([], null))}; } };\n` +
        `const res = {};\n` +
        `const go = async (name, env, home) => { const n = H.calls; try { await L.main(["snapshot"], { transport: H.fn, env, home }); res[name] = { threw: null, calls: H.calls - n }; } catch (e) { res[name] = { threw: String((e && e.message) || e), calls: H.calls - n }; } };\n` +
        `for (const [n, c] of Object.entries({ LF: "\\n", CR: "\\r", NUL: "\\u0000" })) {\n` +
        `  const h = path.join(base, n); fs.mkdirSync(path.join(h, ".config", "socialcrawl"), { recursive: true });\n` +
        `  fs.writeFileSync(path.join(h, ".config", "socialcrawl", "api_key"), C + c + "X\\n");\n` +
        `  await go("file " + n, {}, h);\n` +
        `  await go("env " + n, { SOCIALCRAWL_API_KEY: C + c + "X" }, base);\n` +
        `}\n` +
        `try { await L.snapshot({ key: C, transport: async (u, k) => { throw new Error("fixture error quoting x-api-key: " + k); } }); res.quote = { threw: null }; } catch (e) { res.quote = { threw: String((e && e.message) || e) }; }\n` +
        `out(res);`;
      const NAMES = ["file LF", "env LF", "file CR", "env CR", "file NUL", "env NUL"];
      const r = drive(body);
      assert(r.json && r.json.quote, `driver failed\n${mask(r.stdout)}${mask(r.stderr)}`);
      for (const k of NAMES) {
        const x = r.json[k];
        assert(x && x.calls === 0 && /line break or control character/.test(x.threw) && !leaks(x.threw), `${k}: refused before the transport, no key (${x && x.calls} request(s): ${mask(x && x.threw)})`);
      }
      assert(/<key>/.test(r.json.quote.threw) && !leaks(r.json.quote.threw), `a transport error quoting the key must print without it: ${mask(r.json.quote.threw)}`);

      // KILL 1: no control-character check. Each key reaches the transport, where undici's header
      // check throws and quotes it; the message still comes out with the key cut out.
      const GUARD = ["if (key && CONTROL.test(key)) {", "if (false) {"];
      const a = drive(body, { ledger: mutate([GUARD]) });
      for (const k of NAMES) {
        const x = a.json && a.json[k];
        assert(x && x.calls === 1 && /invalid header value/.test(x.threw) && /<key>/.test(x.threw) && !leaks(x.threw), `${k}: the guard-off mutant must reach the transport and still print no key, or L12 proves nothing: ${mask(x && x.threw)}`);
      }
      // KILL 2: no check and no redaction. The canary reaches the error, so the canary detects a leak.
      const b = drive(body, { ledger: mutate([GUARD, ['key ? msg.split(key).join("<key>") : msg', "msg"]]) });
      for (const k of [...NAMES, "quote"]) {
        assert(b.json && b.json[k] && leaks(b.json[k].threw), `${k}: the mutant must print the canary, or L12 proves nothing`);
      }
    },
  },
];
