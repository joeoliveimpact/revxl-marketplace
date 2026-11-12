import { session, V1, assert, GUARD, COSTS, FAKE_FETCH, FAKE_KEY, mutationEvidence } from "../lib.mjs";
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, copyFileSync, mkdirSync, existsSync, rmSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

const EP = "instagram/profile/posts";
const GFILE = "credit" + "-guard.mjs";
const command = (ep = EP) => `curl -s -H "x-api-key: $SOCIALCRAWL_API_KEY" "${V1}${ep}?id=example"`;
const silent = (r) => assert(r.raw === "" && r.stderr === "" && r.exit === 0, "after event is silent and exits zero", r);
const run = (s, cmd, o = {}) => s.run(cmd, { guard: s.gbGuard, ...o, env: { SOCIALCRAWL_API_KEY: FAKE_KEY, ...o.env } });
function pre(s, id = "gb1", cmd = command(), o = {}) {
  const r = run(s, cmd, { ...o, extra: { tool_use_id: id, ...o.extra } });
  assert(r.raw === "" && r.exit === 0, "Pre committed", r);
  return cmd;
}
function marker(s, id = "gb1", cmd = command(), extra = {}) {
  silent(run(s, cmd, { event: "PostToolUse", extra: { tool_use_id: id,
    tool_response: { interrupted: false }, ...extra } }));
}
function row(amount = -1, request_id = "invented-request-1", at = Date.now(), endpoint = EP) {
  return { id: `invented-row-${request_id}-${amount}`, type: amount < 0 ? "deduction" : "refund",
    amount, balance_after: 2345, description: "invented charge", endpoint: endpoint === null ? null : `/v1/${endpoint}`,
    platform: "invented", credit_tier: "invented", request_id, created_at: new Date(at).toISOString() };
}
const page = (items, at = Date.now(), next_cursor = null, unordered = false) => ({ headers: { Date: new Date(at).toUTCString() },
  body: { data: { items: unordered ? items : [...items].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)), next_cursor }, credits_remaining: 2345 } });
function batch(s, replies, extra = {}, o = {}) {
  silent(run(s, "", { ...o, fetch: { balance: [], transactions: replies }, event: "PostToolBatch",
    extra: { tool_calls: [{ tool_name: "Read", tool_input: {}, tool_response: "invented" }], ...extra } }));
}
function edit(s, fn) { const st = s.state(); fn(st); s.seed(st); }
function backdate(h, ms) {
  h.t -= ms; if (h.u !== undefined) h.u -= ms;
  if (h.post !== undefined) { h.post -= ms; if (h.pu !== undefined) h.pu -= ms; }
}
function backdateEntry(entry, ms) {
  entry.t -= ms;
  for (const a of Object.values(entry.rows)) if (a[1] !== null) a[1] -= ms;
}
function age(s, ms = 180000) {
  edit(s, st => { for (const h of Object.values(st.holds)) backdate(h, ms);
    if (st.led) st.led.at = 0; });
}
function spent(s, n) { assert(s.state().spent === n, `spent exactly ${n}, got ${s.stateRaw()}`); }
const test = (id, desc, fn) => ({ id: `GB-${id}`, desc, async fn(guard) {
  const s = session().seed({ spent: 0 });
  s.gbGuard = guard;
  try { s.budget({ sessionBudget: 20000 }); await fn(s); } finally { s.cleanup(); }
} });

const oldRow = (amount = -1, id = "invented-request-1", ep = EP) => row(amount, id, Date.now() - 180000, ep);
function ready(s) { pre(s); marker(s); age(s); }
function txCount(s) { return s.fetches().filter(r => new URL(r.url).pathname.endsWith("/transactions")).length; }
const nap = ms => new Promise(r => setTimeout(r, ms));
function start(s, event, { replies = [page([])], id = "gb1", cmd = command(), extra = {}, node = [], guard = s.gbGuard || GUARD } = {}) {
  const env = { ...process.env };
  for (const k of Object.keys(env)) if (/^(socialcrawl_api_key|no_proxy|node_options|claude_code_session_attended|claude_code_host_scheduled_run)$/i.test(k)) delete env[k];
  Object.assign(env, { HOME: s.dir, USERPROFILE: s.dir, TEMP: s.dir, TMP: s.dir, TMPDIR: s.dir,
    SC_REVXL_HOME: s.revxl, SOCIALCRAWL_API_KEY: FAKE_KEY, FAKE_FETCH_LOG: join(s.dir, "fetches.jsonl"),
    FAKE_FETCH: JSON.stringify({ balance: [], transactions: replies }) });
  const child = spawn(process.execPath, ["--import", FAKE_FETCH, ...node, guard], { env, stdio: ["pipe", "pipe", "pipe"] });
  let raw = "", stderr = "";
  child.stdout.on("data", b => raw += b); child.stderr.on("data", b => stderr += b);
  const done = new Promise((resolve, reject) => {
    child.on("error", reject); child.on("close", exit => resolve({ raw, stderr, exit }));
  });
  child.stdin.end(JSON.stringify({ session_id: s.sid, hook_event_name: event, tool_name: "Bash", tool_use_id: id,
    tool_input: { command: cmd }, tool_response: { interrupted: false }, ...extra }));
  return { done, child };
}
async function waitFor(fn) {
  const end = Date.now() + 3000;
  while (!fn() && Date.now() < end) await nap(10);
  assert(fn(), "concurrent process reached its observation point");
}
function preload(s, name, source) { const p = join(s.dir, name + ".mjs"); writeFileSync(p, source); return pathToFileURL(p).href; }
function unread(s) {
  ready(s); batch(s, [page([oldRow()])]); spent(s, 1);
  pre(s, "gbX"); marker(s, "gbX"); edit(s, st => st.led.at = 0);
  batch(s, [page([])]); spent(s, 18);
  age(s, 780000);
  edit(s, st => { st.led.seen -= 780000; backdateEntry(st.led.eps[EP]["invented-request-1"], 780000); });
}
const newerRows = () => Array.from({ length: 50 }, (_, i) => row(-1, `invented-fresh-${i}`, Date.now() - i, "web/scrape"));

const fixtures = [
  test("1-tail", "hold plus row during tail, ledger sum after tail, settlement records", s => {
    pre(s); spent(s, 17); marker(s);
    batch(s, [page([row()])]); spent(s, 18);
    age(s); batch(s, [page([row(-1, "invented-request-1", Date.now() - 180000)])]); spent(s, 1);
    assert(s.callLines().filter(x => x.decision === "settle").map(x => `${x.was}:${x.committed}`).join() === "17:18,18:1", "both changes recorded");
  }),
  test("1a-repeat-tail", "three returned repeats keep all holds while rows are delayed", s => {
    ready(s); batch(s, [page([oldRow()])]); spent(s, 1);
    for (let i = 2; i <= 4; i++) { pre(s, `gb${i}`); marker(s, `gb${i}`); }
    edit(s, st => st.led.at = 0);
    batch(s, [page([])]); spent(s, 52);
    age(s); batch(s, [page([2, 3, 4].map(i => oldRow(-i, `invented-repeat-${i}`)))]); spent(s, 10);
  }),
  test("1b-later-any-tool", "later Read batch finds delayed row, throttle and aging suppress requests", s => {
    pre(s); marker(s); batch(s, [page([])]); spent(s, 17);
    const n = txCount(s); batch(s, [page([row()])]); assert(txCount(s) === n, "30 second throttle");
    age(s); batch(s, [page([oldRow()])]); spent(s, 1); assert(txCount(s) === n + 1, "Read-only batch reads ledger");
    age(s, 780000); batch(s, [page([])]); assert(txCount(s) === n + 1, "13 minute old return makes no request");
  }),
  test("1c-open-aging", "unreturned calls read only while young and never release the hold", s => {
    pre(s); batch(s, [page([row()])]); spent(s, 18);
    edit(s, st => st.led.at -= 31000); batch(s, [page([])]); spent(s, 18);
    assert(txCount(s) === 2, "young open call reads 30 seconds apart");
    age(s, 780000); batch(s, [page([])]); spent(s, 18); assert(txCount(s) === 2, "old open call stops reads");
  }),
  test("2-pre-only", "three commands without after events preserve decisions and totals", s => {
    for (let i = 1; i <= 3; i++) { pre(s, `gb${i}`); spent(s, 17 * i); }
    assert(s.callLines().map(x => `${x.decision}:${x.committed}`).join() === "pass:17,pass:34,pass:51", "unchanged decision records");
    marker(s, "gb3"); spent(s, 51); assert(txCount(s) === 0, "marker never reads ledger");
  }),
  ...[false, true].map(reverse => test(`3-decoys-${reverse}`, "sum both charges plus the background hold in either order", s => {
    pre(s, "gb1"); pre(s, "gb2");
    marker(s, reverse ? "gb1" : "gb2");
    marker(s, reverse ? "gb2" : "gb1", command(), { tool_response: { interrupted: false, backgroundTaskId: null } });
    age(s); const rows = [oldRow(-1, "invented-small"), oldRow(-30, "invented-large")];
    batch(s, [page(reverse ? rows.reverse() : rows)]); spent(s, 48);
    assert(s.state().full === 1 && s.state().usage === 31, "one open hold plus sum, no pairing");
    const line = s.callLines().find(x => x.decision === "settle");
    assert(JSON.stringify(line.over) === JSON.stringify([EP]) && !JSON.stringify(line).includes("invented-small") &&
      !JSON.stringify(line).includes("curl"), "overage records only endpoint sums, never request ids or commands");
  })),
  test("4-refund", "later null-endpoint refund floors one id at zero", s => {
    ready(s); batch(s, [page([oldRow(-5)])]); spent(s, 5);
    edit(s, st => st.led.at = 0); batch(s, [page([row(8, "invented-request-1", Date.now(), null)])]); spent(s, 0);
    edit(s, st => st.led.at = 0); batch(s, [page([oldRow(-5)])]); spent(s, 0);
  }),
  test("4-freeze", "a frozen deduction ignores a later refund while another young call reads", s => {
    ready(s); batch(s, [page([oldRow(-5)])]); spent(s, 5);
    age(s, 780000);
    edit(s, st => { backdateEntry(st.led.eps[EP]["invented-request-1"], 780000); });
    pre(s, "gb2", command("amazon/shop")); marker(s, "gb2", command("amazon/shop"));
    batch(s, [page([row(5, "invented-request-1", Date.now(), null)])]); spent(s, 6);
    assert(txCount(s) === 2, "freeze asserted during an actual later read");
  }),
  test("5-no-row", "no row keeps every hold; first billed row replaces all closed holds", s => {
    ready(s); batch(s, [page([])]); spent(s, 17);
    pre(s, "gb2"); marker(s, "gb2"); age(s);
    batch(s, [page([oldRow()])]); spent(s, 1);
    pre(s, "gb3"); marker(s, "gb3"); age(s);
    batch(s, [page([])]); spent(s, 1);
  }),
  test("6-windows", "other session rows inside the window count; outside and unrelated endpoints do not", s => {
    ready(s); const h = s.state().holds.gb1;
    batch(s, [page([oldRow(-2, "invented-other-session"), row(-40, "invented-before", h.t - 40000),
      row(-50, "invented-after", h.post + 132000), oldRow(-60, "invented-unrelated", "amazon/shop")])]); spent(s, 2);
  }),
  ...[
    ["throw", { throw: true }], ["hang", { hang: true }], ["500", { status: 500 }],
    ["non-json", { body: "invalid" }], ["shape", { body: { items: [] } }],
    ["no-date", { body: { data: { items: [] } } }], ["no-key", page([])],
  ].map(([name, reply]) => test(`7-${name}`, "failed ledger read preserves spend and stops after three failures", s => {
    ready(s);
    if (name === "no-key") {
      const before = s.stateRaw();
      for (let i = 0; i < 4; i++) batch(s, [reply], {}, { unsetEnv: ["SOCIALCRAWL_API_KEY"] });
      spent(s, 17); assert(s.stateRaw() === before && txCount(s) === 0, "no key writes nothing and consumes no failure try"); return;
    }
    if (["500", "non-json", "shape"].includes(name)) reply.headers = { Date: new Date().toUTCString() };
    for (let i = 1; i <= 3; i++) {
      batch(s, [reply], {}, name === "no-key" ? { unsetEnv: ["SOCIALCRAWL_API_KEY"] } : {});
      spent(s, 17); assert(s.state().led.fails === i, "failure counted"); edit(s, st => st.led.at = 0);
    }
    const n = txCount(s); batch(s, [page([oldRow()])]); spent(s, 17); assert(txCount(s) === n, "no fourth request");
    assert(n === (name === "no-key" ? 0 : 3), "exact attempted request count");
  })),
  ...[1, 17].map(charge => test(`8-over-limit-${charge}`, "Pre reads only when over limit and rechecks the current total", s => {
    s.budget({ sessionBudget: 20 }); ready(s);
    assert(txCount(s) === 0, "fitting command never reads ledger");
    const r = run(s, command(), { extra: { tool_use_id: "gb2" }, fetch: { transactions: [page([oldRow(-charge)])] } });
    assert(txCount(s) === 1, "one Pre ledger request");
    if (charge === 1) {
      assert(r.raw === "", "recomputed total passes", r); spent(s, 18);
      const lines = s.callLines().filter(x => x.decision === "settle");
      assert(lines.length === 1 && lines[0].kind === "give-back" && lines[0].was === 17 &&
        lines[0].committed === 1 && lines[0].usage === 1 && lines[0].full === 0, "Pre settlement recorded once");
    }
    else { assert(r.decision === "deny" && r.message.includes("Committed so far: ~17"), "refusal quotes recomputed 17", r); spent(s, 17); }
  })),
  test("8-fit-stale", "a fitting command never requests reconciliation even with holds", s => {
    ready(s); pre(s, "gb2", command(), { fetch: { transactions: [page([oldRow()])] } }); spent(s, 34);
    assert(txCount(s) === 0, "no read for fitting command");
  }),
  test("9-clock-offset", "vendor Date shifts windows ten minutes, excluding PC-stamped row", s => {
    pre(s); marker(s); const now = Date.now();
    batch(s, [page([row(-1, "invented-vendor", now + 600000), row(-9, "invented-pc", now)], now + 600000)]); spent(s, 18);
    age(s); batch(s, [page([row(-1, "invented-vendor", Date.now() + 420000)], Date.now() + 600000)]); spent(s, 1);
  }),
  ...["failed", "interrupted", "background-key", "background-input", "sha", "unknown", "non-bash", "no-response"].map(mode =>
    test(`10-${mode}`, "unclean or mismatched marker leaves the call open", s => {
      pre(s);
      const extra = { tool_use_id: mode === "unknown" ? "absent" : "gb1", tool_response: { interrupted: false } };
      if (mode === "interrupted") extra.tool_response.interrupted = true;
      if (mode === "background-key") extra.tool_response.backgroundTaskId = "";
      if (mode === "background-input") extra.tool_input = { command: command(), run_in_background: true };
      if (mode === "non-bash") extra.tool_name = "PowerShell";
      if (mode === "no-response") extra.tool_response = "invented string";
      silent(run(s, mode === "sha" ? command() + " " : command(), { event: mode === "failed" ? "PostToolUseFailure" : "PostToolUse", extra }));
      assert(s.state().holds.gb1.post === undefined, "marker did not close entry");
      age(s); batch(s, [page([oldRow()])]); spent(s, 18);
    })),
  test("11-command-shapes", "two commands, two endpoints, fixed missing ids and replay ids", s => {
    const multi = command() + " && " + command("amazon/shop");
    pre(s, "gb1", multi); pre(s, "gb2");
    marker(s, "gb1", multi); marker(s, "gb2");
    pre(s, null); pre(s, "gb2"); spent(s, 69);
    assert(s.state().fixed === 34 && s.state().holds.gb1.calls.length === 2, "invalid and replay ids go to fixed");
    age(s); batch(s, [page([oldRow(-2), oldRow(-3, "invented-shop", "amazon/shop")])]); spent(s, 39);
    assert(s.state().full === 0 && s.state().usage === 5, "both endpoint sums counted");
  }),
  test("11-migration", "old spend and holds without fixed migrate without losing credits", s => {
    s.seed({ spent: 10 }); pre(s); marker(s); spent(s, 27);
    assert(s.state().fixed === 10, "old spent becomes fixed");
    edit(s, st => { delete st.fixed; }); age(s);
    batch(s, [page([oldRow()])]); spent(s, 11); assert(s.state().fixed === 10, "missing fixed subtracts held totals once");
  }),
  ...["null", "undefined", "NaN", "Infinity", '"unquotable"'].map(value =>
    test(`11-finite-hold-${value.replace(/"/g, "")}`, "an unquotable leg stores zero and permits later settlement", s => {
      const dir = join(s.dir, "unquotable"); mkdirSync(dir);
      for (const name of [GFILE, "give-back.mjs", "ledger.mjs", "costs.json"]) copyFileSync(join(dirname(s.gbGuard || GUARD), name), join(dir, name));
      const target = join(dir, GFILE), src = readFileSync(target, "utf8"), anchor = "const gatedCalls = calls.filter";
      assert(src.includes(anchor), "classification injection anchor exists");
      writeFileSync(target, src.replace(anchor, `calls[0].worst = ${value};\n  ${anchor}`));
      s.gbGuard = target;
      const cmd = command() + " && " + command("amazon/shop");
      pre(s, "gb1", cmd); spent(s, 1);
      assert(s.state().holds.gb1.calls[0][1] === 0 && s.state().holds.gb1.calls[1][1] === 1, "finite zero and ordinary hold stored");
      marker(s, "gb1", cmd); age(s); batch(s, [page([oldRow(-2)])]); spent(s, 3);
    })),
  test("12-long-session", "old rowless and settled windows never force history reads or restore holds", s => {
    const x = command("amazon/shop");
    pre(s, "gbA", x); marker(s, "gbA", x);
    for (const id of ["gbB", "gbC"]) { pre(s, id); marker(s, id); }
    age(s); batch(s, [page([oldRow(-2, "invented-long-b"), oldRow(-3, "invented-long-c")])]); spent(s, 6);
    age(s, 10800000);
    edit(s, st => {
      st.led.seen -= 10800000;
      for (const a of Object.values(st.led.eps[EP])) backdateEntry(a, 10800000);
    });
    pre(s, "gbD"); marker(s, "gbD");
    edit(s, st => { backdate(st.holds.gbD, 180000); st.led.at = 0; });
    const h = s.state().holds.gbD;
    const newer = Array.from({ length: 50 }, (_, i) => row(-1, `invented-long-new-${i}`, Date.now() - i, "web/scrape"));
    batch(s, [page([]), page(newer, Date.now(), "invented-long-next-1"), page([
      row(-4, "invented-long-d", h.t), row(-1, "invented-long-coverage", h.t - 40000, "web/scrape"),
      row(-1, "invented-long-coverage-2", h.t - 41000, "web/scrape"),
      row(-1, "invented-long-coverage-3", h.t - 42000, "web/scrape"),
    ], Date.now(), "invented-long-next-2")]);
    spent(s, 10); assert(txCount(s) === 3, "new read uses two pages");
    const st = s.state();
    assert(Object.values(st.holds).every(h => !h.stuck) && st.full === 1 && st.usage === 9,
      "only A retains its hold; B and C stay settled; D counts its row");
    assert(st.led.seen > Date.now() - 10000, "recent pages cover every needed span");
  }),
  test("12-frozen-only", "an unverified frozen window still needs coverage", s => {
    ready(s); age(s, 10800000); s.budget({ sessionBudget: 20 });
    const r = run(s, command(), { extra: { tool_use_id: "gb2" }, fetch: { transactions: [
      page([row(-1, "invented-frozen-new", Date.now(), "amazon/shop")], Date.now(), "invented-frozen-next"),
    ] } });
    assert(r.decision === "deny", "rowless frozen hold still enforces budget", r); spent(s, 17);
    assert(txCount(s) === 2 && s.state().holds.gb1.stuck && !s.state().holds.gb1.ok && !s.state().led.seen,
      "unverified frozen history retains the hold and never claims coverage");
  }),
  test("12-covered-tail", "coverage starts at the prior read tail and ignores an empty older span", s => {
    ready(s); age(s, 300000);
    edit(s, st => { st.led = { fails: 0, at: 0, seen: Date.now() - 1000, eps: {} }; });
    pre(s, "gb2"); marker(s, "gb2");
    const now = Date.now();
    batch(s, [page([row(-1, "invented-tail-coverage", now - 150000, "amazon/shop")], now, "invented-tail-next")]);
    spent(s, 34);
    assert(txCount(s) === 1 && Object.values(s.state().holds).every(h => !h.stuck), "prior coverage excludes older history");
  }),
  ...["duplicate", "distinct", "no-id"].map(mode => test(`12-row-id-${mode}`, "page overlap deduplicates ids while distinct and absent ids count normally", s => {
    ready(s); const h = s.state().holds.gb1, deduction = row(-2, "invented-overlap", h.t);
    const other = { ...deduction };
    if (mode === "distinct") other.id += "-other";
    if (mode === "no-id") { delete deduction.id; delete other.id; }
    const newer = Array.from({ length: 49 }, (_, i) => row(-1, `invented-overlap-new-${i}`, Date.now() - i, "amazon/shop"));
    batch(s, [page([...newer, deduction], Date.now(), "invented-overlap-next"),
      page([other, row(-1, "invented-overlap-coverage", h.t - 40000, "amazon/shop")])]);
    spent(s, mode === "no-id" ? 17 : mode === "duplicate" ? 2 : 4); assert(txCount(s) === 2, "overlapping pages both read");
  })),
  ...[false, true].map(stillCursor => test(`12-page2-${stillCursor}`, "second page and uncovered span keep the conservative floor", s => {
    ready(s);
    const newer = Array.from({ length: 50 }, (_, i) => row(-1, `invented-newer-${i}`, Date.now() - i, "amazon/shop"));
    const h = s.state().holds.gb1;
    const second = stillCursor ? [oldRow()] : [oldRow(), row(-1, "invented-coverage", h.t - 40000, "amazon/shop")];
    batch(s, [page(newer, Date.now(), "invented-cursor-1"), page(second, Date.now(), stillCursor ? "invented-cursor-2" : null)]);
    assert(txCount(s) === 2, "exactly two pages requested");
    spent(s, stillCursor ? 18 : 1); assert(!!s.state().holds.gb1.stuck === stillCursor, "coverage controls permanent open status");
  })),
  test("12-uncovered-span", "uncovered recent history never reopens an older frozen window", s => {
    ready(s); batch(s, [page([oldRow()])]); age(s, 780000);
    edit(s, st => backdateEntry(st.led.eps[EP]["invented-request-1"], 780000));
    pre(s, "gb2"); marker(s, "gb2");
    const rows = Array.from({ length: 50 }, (_, i) => row(-1, `invented-recent-${i}`, Date.now() - i, "amazon/shop"));
    batch(s, [page(rows, Date.now(), "invented-next-1"), page([row(-1, "invented-last", Date.now() - 1000, "amazon/shop")], Date.now(), "invented-next-2")]);
    spent(s, 18); assert(!s.state().holds.gb1.stuck && s.state().holds.gb2.stuck, "only a window overlapping the uncovered interval sticks");
  }),
  ...["missing", "damaged", "lost", "empty-holds"].map(mode => test(`13-${mode}`, "unusable state produces no requests, writes, locks or output", s => {
    if (mode === "missing") rmSync(dirname(s.stateFile), { recursive: true });
    else if (mode === "damaged") writeFileSync(s.stateFile, "{");
    else if (mode === "lost") { ready(s); edit(s, st => st.lost = true); }
    const before = s.stateRaw();
    for (const event of ["PostToolUse", "PostToolBatch", "PostToolUseFailure"]) {
      silent(run(s, command(), { event, extra: { tool_use_id: "gb1", tool_response: { interrupted: false } }, fetch: { transactions: [page([])] } }));
      assert(s.stateRaw() === before && !existsSync(s.stateFile + ".lock"), "unchanged state and no lock");
    }
    assert(txCount(s) === 0, "no network");
  })),
  test("13-early-dispatch", "after events bypass oversize and own-file refusal paths even unattended", s => {
    ready(s); const before = s.stateRaw();
    const texts = [command() + "x".repeat(70000), `rm ${s.stateFile}`];
    for (const event of ["PostToolUse", "PostToolUseFailure"]) for (const cmd of texts) {
      silent(run(s, cmd, { event, extra: { tool_use_id: "gb1", tool_response: { interrupted: false } },
        env: { CLAUDE_CODE_SESSION_ATTENDED: "0" } }));
      assert(s.stateRaw() === before && s.logLines().length === 0, "no save or unattended log");
    }
  }),
  test("17-unread-window", "an unread frozen window retains its hold when newer pages miss its row", s => {
    unread(s);
    pre(s, "gbY", command("amazon/shop")); marker(s, "gbY", command("amazon/shop"));
    batch(s, [page([]), page([]), page(newerRows(), Date.now(), "invented-unread-next"),
      page([row(-17, "invented-unread-x", s.state().holds.gbX.t)], Date.now(), "invented-unread-more")]);
    spent(s, 36);
    assert(txCount(s) === 4 && s.state().holds.gbX.stuck && !s.state().holds.gbX.ok && !s.state().holds.gb1.stuck,
      "unverified X counts its full hold and row; settled A stays settled");
  }),
  test("17-unread-window-pre", "the before-refusal read cannot release an unread frozen window", s => {
    unread(s); s.budget({ sessionBudget: 30 });
    const r = run(s, command(), { extra: { tool_use_id: "gbY" }, fetch: { transactions: [
      page([]), page([]),
      page(newerRows(), Date.now(), "invented-unread-next"),
      page([row(-17, "invented-unread-x", s.state().holds.gbX.t)], Date.now(), "invented-unread-more"),
    ] } });
    assert(r.decision === "deny" && r.message.includes("Committed so far: ~35"), "second 17 refused", r);
    spent(s, 35); assert(txCount(s) === 4 && s.state().holds.gbX.stuck && !s.state().holds.gbX.ok, "uncovered X counts its full hold and row");
  }),
  test("17-cached", "a covered read after the tail verifies a cached call and releases its hold", s => {
    ready(s); batch(s, [page([oldRow()])]);
    pre(s, "gbX"); marker(s, "gbX"); age(s);
    batch(s, [page([])]); spent(s, 1);
    assert(s.state().holds.gbX.ok && !s.state().holds.gbX.stuck, "verified empty window settled");
  }),
  test("17-early-read", "coverage during the tail never verifies the full window", s => {
    pre(s); marker(s); batch(s, [page([row()])]); spent(s, 18);
    assert(!s.state().holds.gb1.ok, "tail still needs a later covered read");
    age(s, 780000); edit(s, st => { st.led.seen -= 780000; backdateEntry(st.led.eps[EP]["invented-request-1"], 780000); });
    pre(s, "gbY", command("amazon/shop")); marker(s, "gbY", command("amazon/shop"));
    batch(s, [page([]), page(newerRows(), Date.now(), "invented-early-next"),
      page(newerRows(), Date.now(), "invented-early-more")]); spent(s, 19);
    assert(s.state().holds.gb1.stuck, "unread tail keeps its hold");
  }),
  ...["t-step", "post-step", "restart", "missing-u", "missing-pu", "consistent"].map(mode =>
    test(`18-clock-${mode}`, "PC steps, missing uptime and restarts keep holds; consistent elapsed time settles", s => {
      ready(s);
      edit(s, st => {
        const h = st.holds.gb1;
        if (mode === "t-step") h.t -= 60000;
        if (mode === "post-step") h.post += 180000;
        if (mode === "restart") { h.u += 86400000; h.pu += 86400000; }
        if (mode === "missing-u") delete h.u;
        if (mode === "missing-pu") delete h.pu;
      });
      batch(s, [page([oldRow()])]); spent(s, mode === "consistent" ? 1 : 18);
      assert(!!s.state().holds.gb1.stuck === (mode !== "consistent"), "uptime comparison controls stuck");
    })),
  ...[false, true].map(restart => test(`18-settled-step${restart ? "-restart" : ""}`, "settled calls keep their ledger sum after a PC step or restart", s => {
    for (const id of ["gb1", "gb2", "gb3"]) { pre(s, id); marker(s, id); }
    age(s);
    batch(s, [page([1, 2, 3].map(i => oldRow(-1, `invented-settled-${i}`)))]); spent(s, 3);
    assert(Object.values(s.state().holds).every(h => h.ok && !h.stuck), "three calls verified before clock change");
    edit(s, st => {
      for (const h of Object.values(st.holds)) {
        h.t += 6000; h.post += 6000;
        if (restart) { h.u += 86400000; h.pu += 86400000; }
      }
      st.led.at = 0;
    });
    batch(s, [page([])]); spent(s, 3);
    assert(txCount(s) === 2 && Object.values(s.state().holds).every(h => h.ok && !h.stuck),
      "later read never restores settled holds");
  })),
  ...[false, true].map(first => test(`19-offset-${first ? "first" : "later"}`, "offset jumps fail once per transition and require two agreeing reads", s => {
    ready(s);
    if (!first) { batch(s, [page([oldRow()])]); spent(s, 1); }
    const before = s.state().spent;
    edit(s, st => st.led && (st.led.at = 0));
    batch(s, [page([], Date.now() + 86400000)]); spent(s, before);
    assert(s.state().led.fails === (first ? 0 : 1) && s.state().led.off > 86300000, "jump offset saved, later jump fails");
    edit(s, st => st.led.at = 0);
    batch(s, [page([oldRow()])]); spent(s, before);
    assert(s.state().led.fails === (first ? 1 : 2) && Math.abs(s.state().led.off) < 10000, "first good reply fails and replaces bad offset");
    edit(s, st => st.led.at = 0);
    batch(s, [page([oldRow()])]); spent(s, 1);
    assert(s.state().led.fails === 0, "next agreeing good read succeeds");
  })),
  test("19-page-clock", "a page two Date mismatch fails the whole read", s => {
    ready(s);
    batch(s, [page(newerRows(), Date.now(), "invented-clock-next"), page([oldRow()], Date.now() + 20000)]);
    spent(s, 17); assert(s.state().led.fails === 1 && !s.state().holds.gb1.ok, "mismatched pages never settle");
  }),
  test("19-future-seen", "a future covered-through time cannot suppress real history coverage", s => {
    pre(s); marker(s); batch(s, [page([], Date.now() + 86400000)]); spent(s, 17);
    age(s);
    batch(s, [page([])]); spent(s, 17);
    assert(s.state().led.fails === 1, "clock recovery first records the good offset");
    edit(s, st => st.led.at = 0);
    batch(s, [page([]), page([]), page(newerRows(), Date.now(), "invented-future-seen-next"),
      page([oldRow(), row(-1, "invented-future-seen-coverage", s.state().holds.gb1.t - 40000, "web/scrape")])]);
    spent(s, 1); assert(txCount(s) === 4 && s.state().led.fails === 0, "real history read despite future seen");
  }),
  test("19-future-row", "rows ahead of the Date header fail; nearby rows remain accepted", s => {
    ready(s); batch(s, [page([row(-1, "invented-future", Date.now() + 20000)])]);
    spent(s, 17); assert(s.state().led.fails === 1, "future row fails read");
    edit(s, st => st.led.at = 0); batch(s, [page([oldRow(), row(-1, "invented-near-future", Date.now() + 5000, "web/scrape")])]); spent(s, 1);
    assert(s.state().led.fails === 0, "ordinary row succeeds");
  }),
  ...[false, true].map(absent => test(`20-odd-row-${absent}`, "one old outlier cannot substitute for reading the next page", s => {
    ready(s); const h = s.state().holds.gb1;
    const rows = newerRows(); rows[5] = row(-1, "invented-ancient", h.t - 864000000, "web/scrape");
    batch(s, [page(rows, Date.now(), "invented-odd-next", true), absent ?
      page(newerRows(), Date.now(), "invented-odd-more") : page([row(-3, "invented-odd-x", h.t)])]);
    spent(s, absent ? 17 : 20);
    assert(txCount(s) === 2 && s.state().holds.gb1.stuck && !s.state().holds.gb1.ok,
      "unordered read reaches no history; full hold and observed row both count");
  })),
  ...[false, true].map(exhausted => test(`20-odd-last-row${exhausted ? "-exhausted" : ""}`, "an ancient last row requires page two and preserves uncovered holds", s => {
    ready(s); const h = s.state().holds.gb1;
    const rows = newerRows(); rows[49] = row(-1, "invented-ancient-last", h.t - 864000000, "web/scrape");
    batch(s, [page(rows, Date.now(), "invented-last-next", true), exhausted ?
      page(newerRows(), Date.now(), "invented-last-more") : page([row(-3, "invented-last-x", h.t)])]);
    spent(s, exhausted ? 17 : 20);
    assert(txCount(s) === 2 && s.state().holds.gb1.stuck && !s.state().holds.gb1.ok,
      "two-page cap or existing ordering check retains hold");
    assert(s.state().usage === (exhausted ? 0 : 3), "X row counts once when page two contains it");
  })),
  ...[1, 2, 3].map(count => test(`20-covered-tail-${count}`, "all available tail rows reaching need stop pagination", s => {
    ready(s); const h = s.state().holds.gb1;
    const rows = Array.from({ length: count }, (_, i) => row(-1, `invented-covered-${i}`, h.t - 40000 - i, "web/scrape"));
    batch(s, [page(rows, Date.now(), "invented-covered-next")]); spent(s, 17);
    assert(txCount(s) === 1 && s.state().holds.gb1.ok && !s.state().holds.gb1.stuck,
      "one, two or three old rows establish coverage without page two");
  })),
  test("20-staircase", "small ordering reversals cannot accumulate past an earlier row by over a minute", s => {
    ready(s); const h = s.state().holds.gb1;
    batch(s, [page([0, 40000, 80000].map((ms, i) => row(-1, `invented-stair-${i}`, h.t + ms, "web/scrape")),
      Date.now(), "invented-stair-next", true), page([row(-1, "invented-stair-x", h.t),
      row(-1, "invented-stair-coverage", h.t - 40000, "web/scrape")])]);
    spent(s, 18); assert(txCount(s) === 2 && s.state().holds.gb1.stuck && !s.state().holds.gb1.ok,
      "more than a minute newer than any preceding row means no history coverage");
  }),
  test("21-pre-only-limit", "without after-call markers the old limit decisions and spend are exact", s => {
    s.budget({ sessionBudget: 35 });
    pre(s, "gb1"); pre(s, "gb2"); spent(s, 34);
    const r = run(s, command(), { extra: { tool_use_id: "gb3" }, fetch: { transactions: [page([row(-1)])] } });
    assert(r.decision === "deny" && r.message.includes("Committed so far: ~34"), "third command denied at 34", r);
    pre(s, "gb4", command("amazon/shop")); spent(s, 35);
    assert(txCount(s) === 0 && s.callLines().map(x => `${x.decision}:${x.committed}`).join() ===
      "pass:17,pass:34,deny:34,pass:35", "no ledger request and original record figures");
  }),
  test("22-slack", "both edges include two seconds of slack and hold lasts through the extra tail", s => {
    ready(s); const h = s.state().holds.gb1;
    // Pin only this fixture's read clock, so the reply offset is exactly zero at both edges.
    const now = Math.floor(Date.now() / 1000) * 1000;
    const clock = preload(s, "slack-clock", "Date.now = () => Number(process.env.GB_NOW);");
    const read = items => batch(s, [page(items, now)], {}, { node: ["--import", clock], env: { GB_NOW: String(now) } });
    read([row(-2, "invented-slack-start", h.t - 31000), row(-3, "invented-slack-end", h.post + 121000)]); spent(s, 5);
    pre(s, "gb2"); marker(s, "gb2");
    edit(s, st => { const h = st.holds.gb2; const ms = h.post - now + 121000;
      backdate(h, ms); st.led.at = 0; });
    read([]); spent(s, 22);
    assert(!s.state().holds.gb2.ok, "extra tail still held");
    age(s, 10000); read([]); spent(s, 5);
  }),
  ...[
    ["max", () => command().replace("curl -s", "curl -s --max-time 1"), true, 18],
    ["pipe-jq", () => command() + " | jq .", true, 18],
    ["pipe-head", () => command() + " | head -n 1", true, 18],
    ["pipe-python", () => command() + " | python -m json.tool", true, 18],
    ["semicolon", () => command() + "; sleep 0", true, 18],
    ["newline", () => command() + "\nsleep 0", true, 18],
    ["curl-semicolon", () => command() + "; " + command(), true, 35],
    ["plain", () => command(), false, 1],
    ["and", () => command() + " && " + command(), false, 1],
    ["and-newline", () => command() + " &&\n" + command(), false, 1],
    ["comment", () => "# ordinary comment\n" + command(), false, 1],
  ].map(([name, cmdFn, nc, total]) => test(`23-never-close-${name}`, "masked curl status stays open; ordinary commands still close", s => {
    const cmd = cmdFn(); pre(s, "gb1", cmd); marker(s, "gb1", cmd);
    const h = s.state().holds.gb1;
    assert(!!h.nc === nc && (h.post === undefined) === nc, "command shape controls marker");
    age(s); batch(s, [page([oldRow()])]); spent(s, total);
  })),
  test("24-pre-fails-gate", "three failed reads also stop the before-refusal read", s => {
    ready(s); s.budget({ sessionBudget: 20 });
    edit(s, st => st.led = { fails: 3, at: 0, seen: 0, eps: {} });
    const r = run(s, command(), { extra: { tool_use_id: "gb2" }, fetch: { transactions: [page([oldRow()])] } });
    assert(r.decision === "deny" && txCount(s) === 0, "no read after failure cap", r); spent(s, 17);
  }),
  test("24-partial-refund", "a later partial refund and distinct smaller deduction add by row id", s => {
    ready(s); batch(s, [page([oldRow(-5)])]); spent(s, 5);
    edit(s, st => st.led.at = 0); batch(s, [page([row(2, "invented-request-1", Date.now())])]); spent(s, 3);
    edit(s, st => st.led.at = 0); batch(s, [page([oldRow(-1)])]); spent(s, 4);
  }),
  test("24-pre-failed", "failed before-refusal read preserves exact spend and refusal", s => {
    ready(s); s.budget({ sessionBudget: 20 });
    const r = run(s, command(), { extra: { tool_use_id: "gb2" }, fetch: { transactions: [{ throw: true }] } });
    assert(r.decision === "deny" && r.message.includes("Committed so far: ~17") && s.state().led.fails === 1,
      "failed read cannot turn denial into pass", r); spent(s, 17);
  }),
  test("24-uncovered-seen", "uncovered reads never advance the covered-through time", s => {
    pre(s); marker(s); batch(s, [page([])]);
    edit(s, st => { st.led.at = 0; st.led.seen -= 30000; }); const seen = s.state().led.seen;
    batch(s, [page([]), page(newerRows(), Date.now(), "invented-seen-next"), page(newerRows(), Date.now(), "invented-seen-more")]);
    spent(s, 17); assert(s.state().led.seen === seen && s.state().holds.gb1.stuck, "coverage timestamp unchanged");
  }),
  test("24-marker-no-interrupted", "a response object without interrupted is unclean", s => {
    pre(s); marker(s, "gb1", command(), { tool_response: {} });
    assert(s.state().holds.gb1.post === undefined, "missing interrupted never closes");
    age(s); batch(s, [page([oldRow()])]); spent(s, 18);
  }),
  test("24-marker-replay", "a repeated clean marker never moves post or its uptime", s => {
    ready(s); const h = s.state().holds.gb1; marker(s);
    assert(s.state().holds.gb1.post === h.post && s.state().holds.gb1.pu === h.pu, "first return preserved");
    batch(s, [page([oldRow()])]); spent(s, 1);
  }),
  test("14-atomic", "rename failure preserves exact old bytes and refuses a Pre commit", s => {
    const fault = preload(s, "rename-fault", `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const oldWrite = fs.writeFileSync, oldRename = fs.renameSync;
fs.writeFileSync = (p, ...args) => { if (p === process.env.GB_STATE) { oldWrite(p, ""); throw Object.assign(new Error("forced"), { code: "ENOSPC" }); } return oldWrite(p, ...args); };
fs.renameSync = (a, b) => { if (b === process.env.GB_STATE) { if (!a.startsWith(b + ".")) throw new Error("temp prefix"); if (fs.readFileSync(b, "utf8") !== process.env.GB_OLD) throw new Error("old bytes changed"); throw Object.assign(new Error("forced"), { code: "EPERM" }); } return oldRename(a, b); };
syncBuiltinESMExports();`);
    const before = s.stateRaw();
    const r = run(s, command(), { extra: { tool_use_id: "gb1" }, node: ["--import", fault], env: { GB_STATE: s.stateFile, GB_OLD: before } });
    assert(r.decision === "deny" && r.message.includes("couldn't record"), "failed rename refuses commit", r);
    assert(s.stateRaw() === before && readdirSync(dirname(s.stateFile)).length === 1, "old file byte-identical, temp cleaned");
  }),
  test("14-atomic-after", "failed marker rename preserves the previous complete session", s => {
    pre(s); const before = s.stateRaw();
    const fault = preload(s, "after-rename-fault", `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const rename = fs.renameSync;
fs.renameSync = (a, b) => { if (b === process.env.GB_STATE) throw new Error("forced rename failure"); return rename(a, b); };
syncBuiltinESMExports();`);
    silent(run(s, command(), { event: "PostToolUse", node: ["--import", fault], env: { GB_STATE: s.stateFile },
      extra: { tool_use_id: "gb1", tool_response: { interrupted: false } } }));
    assert(s.stateRaw() === before && readdirSync(dirname(s.stateFile)).length === 1, "failed marker save leaves bytes intact and removes temp");
  }),
  ...["PostToolBatch", "PreToolUse"].map(event => test(`15-unlink-failure-${event}`, "no ledger request leaves while lock deletion fails", s => {
    ready(s); s.budget({ sessionBudget: 20 });
    const fault = preload(s, "unlink-fault", `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const unlink = fs.unlinkSync; let tries = 0;
fs.unlinkSync = (p, ...a) => { if (p === process.env.GB_STATE + ".lock" && tries++ < 10) throw Object.assign(new Error("forced"), { code: "EBUSY" }); return unlink(p, ...a); };
syncBuiltinESMExports();`);
    const r = run(s, command(), { event, node: ["--import", fault], env: { GB_STATE: s.stateFile },
      extra: { tool_use_id: "gb2" }, fetch: { transactions: [page([oldRow()])] } });
    if (event === "PostToolBatch") silent(r); else assert(r.decision === "deny", "Pre refusal stands");
    spent(s, 17); assert(txCount(s) === 0 && !existsSync(s.stateFile + ".lock"), "no request while locked, final cleanup retried");
  })),
  test("15-concurrent", "two batch processes throttle under the lock and preserve every hold", async s => {
    ready(s); pre(s, "gb2");
    const options = { replies: [page([oldRow()])] };
    const a = start(s, "PostToolBatch", options), b = start(s, "PostToolBatch", options);
    for (const r of await Promise.all([a.done, b.done])) silent(r);
    spent(s, 18); assert(Object.keys(s.state().holds).length === 2 && txCount(s) === 1, "valid recompute, no lost hold, one request");
  }),
  test("15-unlocked-read", "a second real process commits during a hanging ledger request", async s => {
    ready(s);
    const a = start(s, "PostToolBatch", { replies: [{ hang: true }] });
    await waitFor(() => txCount(s) === 1);
    assert(!existsSync(s.stateFile + ".lock"), "ledger request holds no session lock");
    const b = start(s, "PreToolUse", { id: "gb2" });
    silent(await b.done); spent(s, 34);
    assert(a.child.exitCode === null, "second process committed while request still hangs");
    silent(await a.done); spent(s, 34);
  }),
  test("14-marker-lock", "marker waits for a live lock then reads the current state", async s => {
    pre(s); writeFileSync(s.stateFile + ".lock", "");
    const a = start(s, "PostToolUse");
    await nap(200); assert(s.state().holds.gb1.post === undefined, "marker cannot write through held lock");
    rmSync(s.stateFile + ".lock"); silent(await a.done); assert(Number.isFinite(s.state().holds.gb1.post), "marker writes after lock released");
  }),
  test("16-module-absent", "isolated guard keeps holds and all after paths are silent no-ops", s => {
    const dir = join(s.dir, "copy"); mkdirSync(dir);
    const guard = join(dir, "credit" + "-guard.mjs"); copyFileSync(GUARD, guard); copyFileSync(COSTS, join(dir, "costs.json"));
    pre(s, "gb1", command(), { guard }); spent(s, 17); const before = s.stateRaw();
    for (const event of ["PostToolUse", "PostToolBatch", "PostToolUseFailure"]) {
      silent(run(s, command(), { guard, event, extra: { tool_use_id: "gb1", tool_response: { interrupted: false } } }));
      assert(s.stateRaw() === before, "missing module does not settle or mark");
    }
  }),
];

// Every mutant is confined to an isolated hooks copy; each invokes a named real-process fixture.
const mutations = [
  ["M0", "1a-repeat-tail", "give-back.mjs", "vNow < w.end || !w.h.ok", "w.h.post === undefined"],
  ["M1", "3-decoys-false", "give-back.mjs", "sum + Math.ceil(Math.max(0, -Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0)))", "Math.max(sum, Math.ceil(Math.max(0, -Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0))))"],
  ["M2", "5-no-row", "give-back.mjs", "ids.length ? open : finiteCalls", "open"],
  ["M3", "4-refund", "give-back.mjs", "Math.max(0, -Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0))", "(-Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0))"],
  ["M4", "9-clock-offset", "give-back.mjs", "off = vNow - arrived;", "off = 0;"],
  ["M5", "15-unlocked-read", GFILE, "if (!await unlock(stateFile)) return; locked = false;", "/* keep lock during request */"],
  ["M6", "1c-open-aging", "give-back.mjs", "endedOpen.reduce((sum, w) => sum + w.held, 0)", "0"],
  ["M7", "10-background-key", GFILE, 'Object.hasOwn(response, "backgroundTaskId")', "false"],
  ["M8", "7-throw", GFILE, "(state.led?.fails || 0) < 3", "true"],
  ["M9", "10-sha", GFILE, "h.sha !== sha(rawCmd)", "false"],
  ["M10", "14-atomic", GFILE, 'writeFileSync(temp, JSON.stringify(st), { flag: "wx" });', "writeFileSync(stateFile, JSON.stringify(st));"],
  ["M11", "1-tail", GFILE, "try { await sessionMain(input, true); } catch {}", 'try { await sessionMain(input, true); process.stdout.write("mutant"); } catch {}'],
  ["M12", "1b-later-any-tool", GFILE, 'const event = input.hook_event_name;', 'const event = input.hook_event_name; if (event === "PostToolBatch" && !input.tool_calls?.some(c => c.tool_name === "Bash")) return;'],
  ["M13", "1b-later-any-tool", GFILE, "Date.now() - (state.led?.at || 0) >= 30000", "true"],
  ["M14", "14-marker-lock", GFILE, 'locked = await lock(stateFile, "session lock", 2000);', "locked = true;"],
  ["release-error", "15-unlink-failure-PostToolBatch", GFILE, "if (!await unlock(stateFile)) return; locked = false;", "await unlock(stateFile); locked = false;"],
  ["coverage-span", "12-uncovered-span", "give-back.mjs", "span && span.start < uncovered.end && span.end >= uncovered.start", "w.start < uncovered.end"],
  ["old-coverage", "12-long-session", "give-back.mjs", "if (w.h.ok) return null;", "/* require settled history again */"],
  ["row-id", "12-row-id-duplicate", "give-back.mjs", "if (seenRows.has(row.id)) continue;", 'if (seenRows.has(row.id)) row.id += "-duplicate";'],
  ["finite-hold", "11-finite-hold-null", GFILE, '[normalPath(c.p).replace(/sc_[^/?#]*/gi, "sc_…"), num(c.worst) === null ? 0 : c.worst]', '[normalPath(c.p).replace(/sc_[^/?#]*/gi, "sc_…"), c.worst]'],
  ["pre-settle", "8-over-limit-1", GFILE, "const settled = saveRecompute(st, gb, read, true);", "const settled = saveRecompute(st, gb, read);"],
  ["unread-frozen", "17-unread-window-pre", "give-back.mjs", "if (w.h.ok) return null;", "if (w.h.ok || vNow > w.end + FREEZE_MS) return null;"],
  ["uncovered-ok", "17-unread-window", "give-back.mjs", "w.h.stuck = true;", "w.h.ok = true;"],
  ["early-ok", "17-early-read", "give-back.mjs", "vNow >= w.end", "true"],
  ["pc-drift", "18-clock-t-step", "give-back.mjs", "if (drift(h.t, h.u) || (h.post !== undefined && drift(h.post, h.pu)))", "if (false)"],
  ["offset-jump", "19-offset-later", "give-back.mjs", "finite(st.led?.off) && Math.abs(off - st.led.off) > 30000", "false"],
  ["page-date", "19-page-clock", "give-back.mjs", "Math.abs(date - vNow) > 10000", "false"],
  ["future-row", "19-future-row", "give-back.mjs", "t > vNow + 10000", "false"],
  ["future-seen", "19-future-seen", "give-back.mjs", "st.led.seen <= vNow", "true"],
  ["oldest-row", "20-odd-row-false", "give-back.mjs", "oldest = unordered || !body.data.items.length ? Infinity : Math.max(...rows.slice(-3).map(r => Date.parse(r.created_at)));", "oldest = rows.length ? Math.min(...rows.map(r => Date.parse(r.created_at))) : Infinity;"],
  ["settled-step", "18-settled-step", "give-back.mjs", "if (h.ok === true) continue;", "/* check settled clocks again */"],
  ["last-row-only", "20-odd-last-row", "give-back.mjs", "oldest = unordered || !body.data.items.length ? Infinity : Math.max(...rows.slice(-3).map(r => Date.parse(r.created_at)));", "oldest = unordered || !body.data.items.length ? Infinity : previous;"],
  ["adjacent-order", "20-staircase", "give-back.mjs", "t > lowest + 60000", "t > previous + 60000"],
  ["no-after-pre", "21-pre-only-limit", GFILE, "Object.values(st.holds || {}).some(h => h.post !== undefined)", "Object.keys(st.holds || {}).length"],
  ["no-slack", "22-slack", "give-back.mjs", "export const SLACK_MS = 2000;", "export const SLACK_MS = 0;"],
  ["never-close", "23-never-close-max", GFILE, "!h || h.nc || Object.hasOwn", "!h || Object.hasOwn"],
  ["and-newline", "23-never-close-and-newline", GFILE, 'sep === "\\n" && !andPending', 'sep === "\\n"'],
  ["pre-failure-gate", "24-pre-fails-gate", GFILE, "(st.led?.fails || 0) < 3", "true"],
  ["partial-deduction", "24-partial-refund", "give-back.mjs", "const stored = { ...old?.rows, ...g.rows };", "const stored = { ...g.rows };"],
  ["failed-pre-zero", "24-pre-failed", GFILE, "else if (left() > 0) readFailure(st, read);", "else if (left() > 0) { st.spent = 0; readFailure(st, read); }"],
  ["uncovered-seen", "24-uncovered-seen", "give-back.mjs", "if (uncovered === null) st.led.seen = vNow;", "st.led.seen = vNow;"],
  ["missing-interrupted", "24-marker-no-interrupted", GFILE, "response.interrupted !== false", "response.interrupted === true"],
  ["marker-replay", "24-marker-replay", GFILE, 'Object.hasOwn(h, "post")', "false"],
];
const mutants = mutations.map(([id, victim, file, find, replacement]) => test(`mutant-${id}`, `${id} is killed by GB-${victim}`, async s => {
  await mutationEvidence(file, find, replacement, guard => fixtures.find(f => f.id === `GB-${victim}`).fn(guard));
}));
export default [...fixtures, ...mutants];
