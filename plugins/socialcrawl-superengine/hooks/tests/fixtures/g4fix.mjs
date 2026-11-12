import { session, V1, HOST, TSCRIPT, T, GUARD, COSTS, FAKE_FETCH, FAKE_KEY, M_NOTPLAIN, mLimit, srcAuto, SRC_FALLBACK, mTranscript, assert, mutationEvidence } from "../lib.mjs";
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync, mkdtempSync, copyFileSync, existsSync, rmSync, utimesSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { uptime } from "node:os";
import { createHash } from "node:crypto";

const G = "credit" + "-guard.mjs", GB = "give-back.mjs", EP = "instagram/profile/posts";
const ROOT = resolve(dirname(GUARD), "../../..");
const KEY = "$SOCIALCRAWL_API_KEY";
const cmd = (ep = EP, header = `-H "x-api-key: ${KEY}"`) => `curl -s ${header} "${V1}${ep}?id=fixture"`;
const quiet = r => assert(r.exit === 0 && r.raw === "" && r.stderr === "", "quiet zero exit", r);
const test = (id, desc, body) => ({ id: id.startsWith("EGF-") ? id : `G4F-${id}`, desc, async fn(guard = GUARD) {
  const s = session().seed({ spent: 0 }); s.guard = guard; s.scratch = [];
  s.budget({ sessionBudget: 20000 });
  try { await body(s); } finally { s.cleanup(); for (const p of s.scratch) rmSync(p, { recursive: true, force: true }); }
} });
function scratch(s) {
  mkdirSync(join(ROOT, ".lane"), { recursive: true });   // a fresh checkout has no .lane yet
  const p = mkdtempSync(join(ROOT, ".lane", "g4-fixture-")); s.scratch.push(p); return p;
}
function preload(s, source) {
  const p = join(scratch(s), "inject.mjs"); writeFileSync(p, source); return pathToFileURL(p).href;
}
function copyHooks(s, find, replacement) {
  const p = scratch(s);
  for (const name of [G, GB, "ledger.mjs", "costs.json"]) copyFileSync(join(dirname(s.guard), name), join(p, name));
  if (find) {
    const f = join(p, G), src = readFileSync(f, "utf8");
    assert(src.split(find).length === 2, "fault anchor occurs exactly once"); writeFileSync(f, src.replace(find, replacement));
  }
  return join(p, G);
}
function run(s, command, o = {}) { return s.run(command, { guard: s.guard, env: { SOCIALCRAWL_API_KEY: FAKE_KEY }, ...o }); }
function pre(s, id = "call1", command = cmd(), o = {}) {
  const r = run(s, command, { ...o, extra: { tool_use_id: id, ...o.extra } }); quiet(r); return r;
}
function post(s, id = "call1", command = cmd(), o = {}) {
  const r = run(s, command, { ...o, event: "PostToolUse", extra: { tool_use_id: id, tool_response: { interrupted: false }, ...o.extra } });
  quiet(r); return r;
}
function edit(s, fn) { const st = s.state(); fn(st); s.seed(st); }
function age(s, ms = 180000) {
  edit(s, st => { for (const h of Object.values(st.holds)) {
    h.t -= ms; h.u -= ms; if (h.post !== undefined) { h.post -= ms; h.pu -= ms; }
  } if (st.led) st.led.at = 0; });
}
function row(amount, request_id = "request1", at = Date.now() - 180000, ep = EP, id = `${request_id}-${amount}`) {
  return { id, type: amount < 0 ? "deduction" : "refund", amount, balance_after: 2345,
    description: "invented charge", endpoint: `/v1/${ep}`, platform: "fixture", credit_tier: "standard", request_id,
    created_at: new Date(at).toISOString() };
}
const page = (items, next_cursor = null, at = Date.now()) => ({ headers: { Date: new Date(at).toUTCString() },
  body: { data: { items: [...items].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)), next_cursor }, credits_remaining: 2345 } });
function batch(s, replies = [page([])], o = {}) {
  const r = run(s, "", { ...o, fetch: { balance: [], transactions: replies }, event: "PostToolBatch",
    extra: { tool_calls: [{ tool_name: "Read", tool_input: {} }], ...o.extra } }); quiet(r); return r;
}
function total(s, n) { assert(s.state().spent === n, `spent ${s.state().spent}; expected ${n}`); }
function ready(s, command = cmd()) { pre(s, "call1", command); post(s, "call1", command); age(s); }
const txCount = s => s.fetches().filter(x => new URL(x.url).pathname.endsWith("/transactions")).length;
const moduleFor = s => import(pathToFileURL(join(dirname(s.guard), GB)).href);
function state(ep = EP, held = 17, post = true) {
  const now = Math.floor(Date.now() / 1000) * 1000, up = uptime() * 1000;
  return { spent: held, fixed: 0, holds: { call1: { t: now - 180000, u: up - 180000,
    ...(post ? { post: now - 180000, pu: up - 180000 } : {}), calls: [[ep, held]] } } };
}
async function calc(s, st, rows, opts = {}) {
  const gb = await moduleFor(s), now = Date.now();
  return gb.recompute(st, rows, opts.vNow ?? now, opts.off ?? 0, opts.uncovered ?? null, now, uptime() * 1000);
}
async function sum(s, st, rows, n, opts) {
  const r = await calc(s, st, rows, opts); assert(r && r.state.spent === n, `recomputed ${r?.state.spent}; expected ${n}`); return r.state;
}
const nap = ms => new Promise(r => setTimeout(r, ms));
async function waitFor(fn) {
  const end = Date.now() + 3500;
  while (!fn() && Date.now() < end) await nap(10);
  assert(fn(), "child reached deterministic barrier");
}
function start(s, event, { id = "call1", command = cmd(), replies = [page([])], node = [], env: additions = {} } = {}) {
  const env = { ...process.env };
  for (const k of Object.keys(env)) if (/^(socialcrawl_api_key|no_proxy|node_options|claude_code_session_attended|claude_code_host_scheduled_run)$/i.test(k)) delete env[k];
  Object.assign(env, { HOME: s.dir, USERPROFILE: s.dir, TEMP: s.dir, TMP: s.dir, TMPDIR: s.dir,
    SC_REVXL_HOME: s.revxl, SOCIALCRAWL_API_KEY: FAKE_KEY, HTTPS_PROXY: "http://127.0.0.1:9",
    HTTP_PROXY: "http://127.0.0.1:9", ALL_PROXY: "http://127.0.0.1:9", NODE_USE_ENV_PROXY: "1",
    FAKE_FETCH: JSON.stringify({ balance: [], transactions: replies }), FAKE_FETCH_LOG: join(s.dir, "fetches.jsonl"), ...additions });
  const child = spawn(process.execPath, ["--import", FAKE_FETCH, ...node, s.guard], { env, stdio: ["pipe", "pipe", "pipe"] });
  let raw = "", stderr = "";
  child.stdout.on("data", b => raw += b); child.stderr.on("data", b => stderr += b);
  const done = new Promise((ok, fail) => { child.on("error", fail); child.on("close", exit => ok({ raw, stderr, exit })); });
  child.stdin.end(JSON.stringify({ session_id: s.sid, hook_event_name: event, tool_name: "Bash", tool_use_id: id,
    tool_input: { command }, tool_response: { interrupted: false } }));
  return { child, done };
}

const M_SETTINGS = "SocialCrawl call not run: your SocialCrawl settings file can't be read, so this session's credit limit can't be checked. Re-save your limit in SocialCrawl → Settings to fix it." + T;
const W6_CHECK = '  if (budgetRead === "bad" && cmdWorst > 0 && transcriptCalls.length === 0) {\n' +
  '    return deny("SocialCrawl call not run: your SocialCrawl settings file can\'t be read, so this session\'s credit limit can\'t be checked. Re-save your limit in SocialCrawl → Settings to fix it." + T, "error");\n' +
  '  }\n';
function badBudget(s, raw) {
  rmSync(s.bf, { recursive: true, force: true });
  if (raw === null) mkdirSync(s.bf); else s.budget(raw);
}
function settingsDenied(s, raw) {
  badBudget(s, raw);
  for (const env of [{ CLAUDE_CODE_SESSION_ATTENDED: "1" }, { CLAUDE_CODE_SESSION_ATTENDED: "0" },
    { CLAUDE_CODE_SESSION_ATTENDED: "1", CLAUDE_CODE_HOST_SCHEDULED_RUN: "1" }]) {
    s.seed({ balance: null, spent: 3, holds: {}, fixed: 3 });
    const before = s.stateRaw(), records = s.callLines().length;
    const r = run(s, cmd("amazon/shop"), { env, fetch: { balance: [{ body: { data: { balance: 800 } } }] }, extra: { tool_use_id: "denied" } });
    assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.message === M_SETTINGS &&
      r.json?.hookSpecificOutput?.permissionDecisionReason === M_SETTINGS, "unreadable settings: exact paid error deny", r);
    assert(s.stateRaw() === before && !s.state().holds.denied, "unreadable settings: spent unchanged and no hold");
    assert(s.fetches().length === 0, "unreadable settings: no balance read before denial");
    const lines = s.callLines();
    assert(lines.length === records + 1 && lines.at(-1).kind === "error" && lines.at(-1).limit === null,
      "unreadable settings: one error record before the limit is picked");
    const free = run(s, cmd("monitors"), { env }); quiet(free);
    assert(s.stateRaw() === before, "unreadable settings: free call passes without counting");
  }
}

const w3cmd = path => `curl -s -H "x-api-key: ${KEY}" "${V1}${path}"`;
function w3case(s, path, worst, shape) {
  for (const transcripts of ["block", "allow", undefined]) {
    s.seed({ spent: 0 }); s.budget({ sessionBudget: 5000, ...(transcripts ? { transcripts } : {}) });
    const command = w3cmd(path), before = s.stateRaw();
    const r = run(s, command, { env: { CLAUDE_CODE_SESSION_ATTENDED: "1" }, extra: { tool_use_id: "w3" } });
    if (transcripts === "block") {
      assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.message === mTranscript("blocked", shape),
        `${path}: Blocked gives the exact transcript-locked denial`, r);
      assert(s.stateRaw() === before && !s.state().holds?.w3 && s.callLines().at(-1).kind === "transcript-locked",
        "blocked encoded transcript creates no hold or spend");
    } else {
      quiet(r); total(s, worst);
      assert(s.state().holds?.w3?.calls[0][1] === worst,
        `${path}: ${transcripts || "no setting"} holds the transcript price ${worst}`);
    }
  }
}

const fixtures = [
  test("EGF-W3-1", "double-encoded facebook transcript parameter is locked and priced at ten", s => {
    for (const name of ["get_transcrip%2574", "get_%2574ranscript"])
      w3case(s, `facebook/post?url=X&${name}=true`, 10, "param:get_transcript");
  }),
  test("EGF-W3-2", "no transcript setting holds ten credits for the double-encoded facebook parameter", s => {
    s.budget({ sessionBudget: 5000 });
    pre(s, "w3", w3cmd("facebook/post?url=X&get_transcrip%2574=true"));
    assert(s.state().holds.w3.calls[0][1] === 10 && s.state().spent === 10,
      "double-encoded facebook parameter holds ten credits, never one");
  }),
  test("EGF-W3-3", "triple-encoded transcript parameter is locked and priced at ten", s =>
    w3case(s, "facebook/post?url=X&get_transcrip%252574=true", 10, "param:get_transcript")),
  test("EGF-W3-4", "single-encoded ordinary query stays at one beside an encoded transcript-price control", s => {
    for (const transcripts of ["block", "allow", undefined]) {
      s.seed({ spent: 0 }); s.budget({ sessionBudget: 5000, ...(transcripts ? { transcripts } : {}) });
      pre(s, "ordinary", w3cmd("amazon/shop?q=a%20b")); total(s, 1);
      assert(s.state().holds.ordinary.calls[0][1] === 1, "single-encoded ordinary query keeps its one-credit hold");
    }
    w3case(s, "facebook/post?url=X&note.transcript=true", 10, "param:note.transcript");
    w3case(s, "facebook/post?url=X&get_transcrip%2574=true", 10, "param:get_transcript");
  }),
  test("EGF-W3-5", "double-encoded video-intel include value is transcript locked", s =>
    w3case(s, "prism/video-intel?url=X&include=%2574ranscript", 15, "bolt")),
  ...["include+", "include%20", "include.0"].map((name, i) =>
    test(`EGF-W3-${i + 6}`, `${name} normalises to a transcript include`, s =>
      w3case(s, `prism/video-intel?url=X&${name}=${TSCRIPT}`, 15, "bolt"))),
  test("EGF-W3-9", "double-encoded search transcript parameter is locked", s =>
    w3case(s, "search/everywhere?q=a&include_transcrip%2574s=true", 20, "param:include_transcripts")),
  test("EGF-W3-10", "double-encoded facebook include value carries the transcript price", s =>
    w3case(s, "facebook/post?url=X&include=%2574ranscript", 10, "bolt")),
  test("EGF-W3-bounds", "literal percent, malformed escapes and over-five encodings fail closed", s => {
    for (const path of ["amazon/shop?q=100%25", "amazon/shop?q=%zz",
      "prism/brief%2dcheck?url=X&y=%zz", `youtube/video/transcrip%2574?id=a`,
      "facebook/post?url=X&get_transcrip%252525252574=true"]) {
      const before = s.stateRaw(), r = run(s, w3cmd(path), { extra: { tool_use_id: "bad" } });
      assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.message === M_NOTPLAIN && s.stateRaw() === before,
        `${path}: exact not-plain denial without counting`, r);
    }
    w3case(s, "facebook/post?url=X&get_transcrip%2525252574=true", 10, "param:get_transcript");
  }),
  test("EGF-B2-1", "a paid routine pass logs exactly once; an ordinary attended pass logs nothing", s => {
    pre(s, "routine", cmd(), { env: { CLAUDE_CODE_SESSION_ATTENDED: "1", CLAUDE_CODE_HOST_SCHEDULED_RUN: "1" } });
    const lines = s.logLines();
    assert(lines.length === 1 && lines[0].decision === "pass" && lines[0].kind === "under-cap" &&
      lines[0].cmdWorst === 17 && lines[0].committed === 17, "routine paid pass writes exactly one pass line with cmdWorst 17");
    rmSync(join(s.revxl, "credit-guard-unattended.jsonl"));
    pre(s, "attended", cmd(), { env: { CLAUDE_CODE_SESSION_ATTENDED: "1" } });
    assert(s.logLines().length === 0, "ordinary attended paid pass writes no unattended-log line");
  }),
  test("EGF-C1-1", "balance 40.5 gives cap 10 naming balance 40: eleven denied, ten passes", s => {
    rmSync(s.bf); s.seed({ balance: 40.5, spent: 0 });
    const investigate = n => cmd("prism/investigate").replace("?id=fixture", `?goal=x&budget=${n}`);
    const r = run(s, investigate(11), { extra: { tool_use_id: "eleven" } });
    assert(r.decision === "deny" && r.message === mLimit({ spent: 0, worst: 11, limit: 10, src: srcAuto(40) }),
      "balance 40.5: eleven denied at cap 10 naming floored balance 40", r);
    total(s, 0); assert(!s.state().holds?.eleven, "eleven-credit denial creates no hold");
    pre(s, "ten", investigate(10)); total(s, 10);
  }),
  test("EGF-C1-2", "balance 2001.9 gives ceiling 500 naming 2001; null keeps fallback 500", s => {
    rmSync(s.bf);
    for (const [balance, src] of [[2001.9, srcAuto(2001)], [null, SRC_FALLBACK]]) {
      s.seed({ balance, balanceFails: 3, spent: 500 });
      const r = run(s, cmd("amazon/shop"));
      assert(r.decision === "deny" && r.message === mLimit({ spent: 500, worst: 1, limit: 500, src }),
        `balance ${balance}: cap 500 with the correct source`, r);
      s.seed({ balance, balanceFails: 3, spent: 499 });
      pre(s, "ceiling", cmd("amazon/shop")); total(s, 500);
    }
  }),
  test("EGF-W6-1", "bad JSON denies paid calls before balance reads; free calls pass", s => settingsDenied(s, "{bad")),
  test("EGF-W6-2", "a JSON array denies paid calls before balance reads; free calls pass", s => settingsDenied(s, "[]")),
  test("EGF-W6-3", "a folder denies paid calls before balance reads; free calls pass", s => settingsDenied(s, null)),
  test("EGF-W6-4", "a JSON string denies paid calls; bad JSON retains the transcript-specific denial", s => {
    settingsDenied(s, '"block"');
    badBudget(s, "{bad"); s.seed({ spent: 3 });
    const before = s.stateRaw(), r = run(s, cmd(`youtube/video/${TSCRIPT}`), { extra: { tool_use_id: "transcript" } });
    assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.message === mTranscript("unreadable", "youtube"),
      "bad JSON keeps the exact transcript unreadable denial", r);
    assert(s.stateRaw() === before && !s.state().holds?.transcript && s.callLines().at(-1).kind === "transcript-locked",
      "transcript remains locked without a commit or hold");
  }),
  ...[
    ["Authorization", "Bearer $OTHER_KEY"], ["authorization", "Bearer $OTHER_KEY"],
    ["AUTHORIZATION", ""], ["aUtHoRiZaTiOn", "ordinary"],
  ].map(([name, value], i) => test(`G3-H2-${i + 1}`, "an Authorization header preserves the full open hold regardless of case or value", s => {
    const command = cmd(EP, `-H "x-api-key: ${KEY}" -H "${name}: ${value}"`);
    pre(s, "call1", command); post(s, "call1", command); age(s);
    batch(s, [page([row(-1)])]);
    const h = s.state().holds.call1;
    assert(h.nc === true && h.post === undefined, "Authorization never gets a finite window");
    assert(h.calls[0][1] === 17 && s.state().full === 1, "the full 17-credit hold is retained beside the row");
  })),
  ...[
    "api_key=other", "apikey=other", "key=other", "x_api_key=other", "access_token=other", "token=other", "auth=other",
    "API-KEY=other", "X-API-KEY=other", "id=x&key=other", "%61pi_key=other",
    `id=${FAKE_KEY}`, "id=SOCIALCRAWL_API_KEY", "id=api_key)", "id=sc%5Ffixture",
  ].map((query, i) => test(`G3-H2-query-${i + 1}`, "a key-named query parameter or key-shaped value preserves the full open hold", s => {
    const command = cmd().replace("?id=fixture", `?${query}`);
    pre(s, "call1", command); post(s, "call1", command); age(s);
    batch(s, [page([row(-1)])]);
    const h = s.state().holds.call1;
    assert(h.nc === true && h.post === undefined, "query key never gets a finite window");
    assert(h.calls[0][1] === 17 && s.state().full === 1, "the full 17-credit hold is retained beside the row");
  })),
  test("G3-H2-keyword", "an ordinary keyword parameter still closes and settles to the one-credit row", s => {
    ready(s, cmd().replace("?id=fixture", "?keyword=test"));
    batch(s, [page([row(-1)])]);
    const h = s.state().holds.call1;
    assert(!h.nc && h.post !== undefined, "keyword gets a finite window"); total(s, 1);
  }),
  test("G3-H2-sc-inside", "a value that only contains sc_ inside a word (a handle like disc_golf) still closes", s => {
    ready(s, cmd().replace("?id=fixture", "?handle=disc_golf"));
    batch(s, [page([row(-1)])]);
    const h = s.state().holds.call1;
    assert(!h.nc && h.post !== undefined, "disc_golf gets a finite window"); total(s, 1);
  }),
  test("G3-H2-query-variable","a variable in the query is refused as not plain and never receives a window", s => {
    const command = cmd().replace("?id=fixture", "?api_key=$OTHER");
    const r = run(s, command, { extra: { tool_use_id: "call1" } });
    assert(r.exit === 0 && r.decision === "deny" && r.message === M_NOTPLAIN, "variable URL is refused as not plain", r);
    post(s, "call1", command);
    assert(!s.state().holds?.call1, "refused call has no hold or finite window"); total(s, 0);
  }),
  test("G3-H3-1", "repeated endpoint slashes are collapsed in the hold and match a ledger row", s => {
    const command = cmd("instagram//profile/posts");
    pre(s, "call1", command); post(s, "call1", command);
    const h = s.state().holds.call1;
    assert(h.calls[0][0] === EP, "stored endpoint is instagram/profile/posts");
    assert(!h.nc && h.post !== undefined, "plain env-key call has a finite window");
    age(s); batch(s, [page([row(-1)])]); total(s, 1);
  }),
  test("F3-one-open-window", "a row inside A only counts beside both piped calls' full holds", s => {
    const command = cmd() + " | jq .";
    for (const id of ["A", "B"]) { pre(s, id, command); post(s, id, command); }
    age(s);
    edit(s, st => { st.holds.A.t = st.holds.B.t - 120000; st.holds.A.u = st.holds.B.u - 120000; });
    const { A, B } = s.state().holds, stamp = A.t + 1000;
    assert(A.nc && B.nc && A.post === undefined && B.post === undefined && stamp < B.t - 32000,
      "A's row is inside its open window and earlier than B's window");
    batch(s, [page([row(-30, "reqA", stamp, EP, "only-A")])]);
    total(s, 64);
    assert(s.state().usage === 30 && s.state().full === 2, "34 full holds plus one 30-credit row");
  }),
  test("F2-freeze", "late frozen read adds deductions and conservatively ignores the new refund", async s => {
    const gb = await moduleFor(s), T0 = 1.8e12, up0 = 5e8;
    const items = [row(-4, "req1", T0 + 7000, "a/x", "A"), row(-15, "req1", T0 + 98000, "a/x", "B"),
      row(-5, "req1", T0 + 95000, "a/x", "C"), row(5, "req1", T0 + 137000, "a/x", "D")];
    let st = { spent: 17, fixed: 0, holds: { call1: { t: T0, u: up0, calls: [["a/x", 17]] } } };
    const first = gb.recompute(st, [items[0]], T0 + 80000, 0, null, T0 + 80000, up0 + 80000);
    assert(first?.state.spent === 21, "initial open hold and row both count"); st = first.state;
    st.holds.call1.post = T0 + 150000; st.holds.call1.pu = up0 + 150000;
    const late = T0 + 150000 + 122000 + 2000 + 600000 + 5000;
    const split = gb.recompute(st, items, late, 0, null, late, up0 + late - T0);
    const fresh = gb.recompute({ spent: 17, fixed: 0, holds: structuredClone(st.holds) }, items, late, 0, null, late, up0 + late - T0);
    assert(fresh?.state.spent === 19, "same rows first seen together net nineteen");
    assert(split?.state.spent === 24, `frozen split read should count twenty-four; got ${split?.state.spent}`);
    assert(split.state.spent >= 19, "accepted frozen over-count covers the real nineteen");
  }),
  test("F2-frozen-new-deductions", "an established frozen entry adds unseen deductions and ignores refunds or replacements", async s => {
    const gb = await moduleFor(s), st = state(), t = st.holds.call1.t;
    const first = await sum(s, st, [row(-4, "r", t, EP, "A")], 4);
    const now = Date.now(), late = now + 780000;
    const result = gb.recompute(first, [row(-40, "r", t, EP, "A"), row(-15, "r", t + 1000, EP, "B"),
      row(-5, "r", t + 2000, EP, "C"), row(5, "r", t + 3000, EP, "D")], late, 0, null, late, uptime() * 1000 + 780000);
    assert(result?.state.spent === 24, `frozen net adds twenty credits; got ${result?.state.spent}`);
    assert(result.state.led.eps[EP].r.rows.A[0] === -4 && !Object.hasOwn(result.state.led.eps[EP].r.rows, "D"), "stored deduction is immutable and late refund is ignored");
  }),
  ...[false, true].map(empty => test(`F2-frozen-${empty ? "empty-read" : "shift"}`, "an already frozen figure cannot decrease after its window offset moves", async s => {
    const gb = await moduleFor(s), st = state(), t = st.holds.call1.t;
    const first = await sum(s, st, [row(-4, "r", t)], 4), now = Date.now(), up = uptime() * 1000;
    const frozen = gb.recompute(first, empty ? [] : [row(-4, "r", t)], now + 780000, 0, null, now + 780000, up + 780000);
    assert(frozen?.state.spent === 4, "figure reaches the elapsed freeze boundary");
    const shifted = gb.recompute(frozen.state, [row(3, "r", t + 1000)], now + 920000, 40000, null, now + 880000, up + 880000);
    assert(shifted?.state.spent === 4, "a later offset move cannot unfreeze a late refund");
  })),
  ...[false, true].map(frozen => test(`F2-refund-${frozen ? "frozen" : "young"}`, "a refund nets before freeze and cannot lower a frozen figure", async s => {
    const gb = await moduleFor(s), st = state(), t = st.holds.call1.t;
    const first = await sum(s, st, [row(-4, "r", t)], 4), delay = frozen ? 780000 : 1000, now = Date.now() + delay;
    const result = gb.recompute(first, [row(3, "r", t + 1000)], now, 0, null, now, uptime() * 1000 + delay);
    assert(result?.state.spent === (frozen ? 4 : 1), "refund follows the freeze boundary");
  })),
  ...["shift", "vendor-offset"].map(mode => test(`F1-${mode}`, "settled rows stay counted across PC or vendor offset moves through readLedger", async s => {
    const gb = await moduleFor(s), T0 = 1.8e12, up0 = 5e8, realNow = Date.now; let pc = 0, vendor = 0;
    let st = { spent: 34, fixed: 0, holds: {
      call1: { t: T0, u: up0, post: T0 + 5000, pu: up0 + 5000, calls: [["a/x", 17]] },
      call2: { t: T0 + 100000, u: up0 + 100000, post: T0 + 130000, pu: up0 + 130000, calls: [["a/x", 17]] },
    } };
    const rows = [row(-4, "req2", T0 + 129000, "a/x", "r2"), row(-5, "req1", T0 + 1000, "a/x", "r1")];
    const transport = async () => new Response(JSON.stringify({ data: { items: rows, next_cursor: null } }), { headers: { Date: new Date(vendor).toUTCString() } });
    const read = async (v, clock, up, failed) => {
      vendor = v; pc = clock;
      const result = await gb.readLedger(st, { left: () => 4000, transport, env: { SOCIALCRAWL_API_KEY: FAKE_KEY }, home: s.dir });
      assert(result && !!result.failed === failed, "offset jump fails once, then the agreeing read succeeds");
      if (result.failed) { st.led.fails++; st.led.off = result.off; }
      else {
        const computed = gb.recompute(st, result.rows, result.vNow, result.off, result.uncovered, pc, up);
        assert(computed, "recompute succeeds"); st = computed.state;
      }
      assert(st.spent === 9 && st.usage === 9, `settled total stays 9, got ${st.spent}`);
    };
    try {
      Date.now = () => pc;
      await read(T0 + 300000, T0 + 300000, up0 + 300000, false);
      if (mode === "shift") {
        await read(T0 + 400000, T0 + 360000, up0 + 400000, true);
        await read(T0 + 440000, T0 + 400000, up0 + 440000, false);
      } else {
        await read(T0 + 440000, T0 + 400000, up0 + 400000, true);
        await read(T0 + 480000, T0 + 440000, up0 + 440000, false);
      }
    } finally { Date.now = realNow; }
  })),
  test("F1-mark", "a finite-counted id remains counted after its closed window moves", async s => {
    let st = state(); const t = st.holds.call1.t;
    st = await sum(s, st, [row(-5, "r", t)], 5);
    assert(st.led.eps[EP].r.c === true, "finite membership is persisted");
    for (const key of ["t", "post", "u", "pu"]) st.holds.call1[key] += 40000;
    await sum(s, st, [], 5);
  }),
  test("F1-open-unmarked", "open-only rows never gain a finite-counted mark", async s => {
    const st = state(EP, 0, false); st.holds.call1.nc = true;
    const result = await sum(s, st, [row(-5, "r", st.holds.call1.t)], 5);
    assert(result.led.eps[EP].r.c !== true && result.full === 1, "open hold and row count without a finite mark");
  }),
  ...[["dotdot", "~/x/../.config/socialcrawl/api_key"], ["dot", "~/.config/./socialcrawl/api_key"]].map(([name, path]) =>
    test(`C2-${name}`, "dot segments in a file-key path always keep its hold", s => {
      const keyFile = join(s.dir, ".config", "socialcrawl", "api_key"); mkdirSync(dirname(keyFile), { recursive: true }); writeFileSync(keyFile, FAKE_KEY);
      const command = cmd(EP, `-H "x-api-key: $(cat ${path})"`), o = { env: { SOCIALCRAWL_API_KEY: "" } };
      pre(s, "call1", command, o); post(s, "call1", command, o);
      assert(s.state().holds.call1.nc && s.state().holds.call1.post === undefined, "a lexical dot alias is never closable");
    })),
  ...[["zero", 0, 5], ["hold", 17, 1], ["row", 17, 30]].map(([name, held, charge]) =>
    test(`R2-open-${name === "hold" ? "hold-row" : name}`, "an actual piped call counts its full hold plus open rows", async s => {
      let command = cmd() + " | jq .";
      if (held === 0) {
        const src = readFileSync(s.guard, "utf8"), anchor = "const gatedCalls = calls.filter";
        assert(src.includes(anchor), "uncomputable-price injection anchor exists");
        s.guard = copyHooks(s, anchor, 'calls[0].kind = "uncomputable"; calls[0].worst = null;\n  ' + anchor);
      }
      pre(s, "call1", command); post(s, "call1", command); age(s);
      const h = s.state().holds.call1;
      assert(h.nc && h.post === undefined && h.calls[0][1] === held, "piped uncomputable/ordinary call retains its quoted hold");
      batch(s, [page([row(-charge, "r", h.t)])]);
      const expected = held + charge, st = s.state(); total(s, expected);
      assert(st.usage === charge && st.full === 1, "usage counts rows while the full hold stays counted");
      assert(Number.isInteger(st.spent) && Number.isInteger(st.usage), "public counts stay integral");
      const line = s.callLines().find(x => x.decision === "settle");
      assert(line?.over.includes(EP), "counted rows above released holds flag the endpoint");
    })),
  test("R2-open-AB", "two piped calls retain both full holds beside one visible billed row", s => {
    const command = cmd() + " | jq .";
    for (const id of ["A", "B"]) { pre(s, id, command); post(s, id, command); }
    age(s); batch(s, [page([row(-30, "reqA", s.state().holds.A.t)])]);
    const st = s.state(); total(s, 64);
    assert(st.spent >= 47 && st.usage === 30 && st.full === 2, "34 holds plus 30 rows cover at least 47 owed");
  }),
  test("R2-open-overlap", "one request inside two open windows counts once for the endpoint", async s => {
    const st = state(EP, 17, false); st.holds.call1.nc = true;
    st.holds.call2 = structuredClone(st.holds.call1); st.spent = 34;
    const r = await calc(s, st, [row(-40, "r", st.holds.call1.t)]);
    assert(r?.state.spent === 74 && r.state.usage === 40 && r.state.full === 2 && r.over.includes(EP), "both holds plus one forty-credit row");
  }),
  test("R2-open-fractional", "open ids are floored and rounded up individually before summing", async s => {
    const st = state(EP, 0, false); st.holds.call1.nc = true; const t = st.holds.call1.t;
    const r = await calc(s, st, [row(-1.2, "a", t), row(-1.2, "b", t), row(-1, "refund", t), row(3, "refund", t + 1000)]);
    assert(r?.state.spent === 4 && r.state.usage === 4 && r.state.full === 1, "open sum is ceil(1.2) + ceil(1.2) + floor(-2)");
  }),
  test("R2-open-finite", "a finite counted id is excluded from overlapping open rows", async s => {
    const st = state(); st.holds.nc = { ...st.holds.call1, nc: true }; delete st.holds.nc.post; delete st.holds.nc.pu; st.spent = 34;
    const r = await calc(s, st, [row(-30, "finite", st.holds.call1.t)]);
    assert(r?.state.spent === 47 && r.state.usage === 30 && r.state.full === 1, "finite rows count once beside the open full hold");
  }),
  test("R2-open-over-fallback", "over excludes finite holds retained by the no-row fallback", async s => {
    const st = state(); st.holds.nc = { ...st.holds.call1, nc: true }; delete st.holds.nc.post; delete st.holds.nc.pu;
    st.holds.nc.t += 180000; st.holds.nc.u += 180000; st.spent = 34;
    const r = await calc(s, st, [row(-5, "open-only", st.holds.nc.t)]);
    assert(r?.state.spent === 39 && r.state.usage === 5 && r.state.full === 2, "both unreleased holds plus five counted credits");
    assert(r.over.includes(EP), "five rows exceed zero released holds");
  }),
  test("C2-skill-table", "the shipped API Key table selects closable headers only for its own key source", s => {
    const text = readFileSync(join(dirname(GUARD), "..", "skills", "socialcrawl", "SKILL.md"), "utf8");
    const section = text.split("## API Key")[1]?.split(/\n## /)[0];
    assert(section, "API Key section exists");
    for (const source of ["env", "file"]) {
      const rows = section.split("\n").filter(line => line.startsWith(`| \`${source}=ok\``));
      assert(rows.length === 1, `exactly one ${source}=ok row exists`);
      const headers = [...rows[0].matchAll(/-H "[^"\n]*"/g)].map(m => m[0]);
      assert(headers.length === 1, "one literal header extracted byte for byte");
      const keyFile = join(s.dir, ".config", "socialcrawl", "api_key"); mkdirSync(dirname(keyFile), { recursive: true }); writeFileSync(keyFile, FAKE_KEY);
      for (const setup of ["env", "file"]) {
        const id = `${source}_${setup}`, command = cmd(EP, headers[0]), env = { SOCIALCRAWL_API_KEY: setup === "env" ? FAKE_KEY : "" };
        pre(s, id, command, { env }); post(s, id, command, { env });
        const h = s.state().holds[id], closable = setup === source;
        assert(!!h.nc === !closable && (h.post !== undefined) === closable, "table header is bound to its selected source");
      }
    }
  }),
  test("C1-fractional", "H-76 rounds each request net up and keeps public totals integral", async s => {
    const st = state(), r = await calc(s, st, [row(-1.2, "fractional", st.holds.call1.t)]);
    assert(r?.state.spent === 2 && r.state.usage === 2 && Number.isInteger(r.state.spent) && Number.isInteger(r.state.usage), "fractional request nets two whole credits");
  }),
  test("C1-fractional-fixed", "H-76 refuses a fractional inherited remainder without altering it", async s => {
    const st = state(EP, 1); st.fixed = 1.2; st.spent = 2.2; const before = JSON.stringify(st);
    assert(await calc(s, st, [row(-1.2, "fractional", st.holds.call1.t)]) === null && JSON.stringify(st) === before,
      "nonintegral legacy arithmetic must keep its holds, never round an inherited count down");
  }),
  test("C1-1", "three distinct rows across reads sum to four, replacing the wrong GB pin of three", async s => {
    let st = state(); const t = st.holds.call1.t;
    st = await sum(s, st, [row(-5, "r", t)], 5);
    st = await sum(s, st, [row(2, "r", t + 2000)], 3);
    await sum(s, st, [row(-1, "r", t + 1000)], 4);
  }),
  test("C1-2", "the same three rows in one read sum to four", async s => {
    const st = state(), t = st.holds.call1.t;
    await sum(s, st, [row(-5, "r", t), row(2, "r", t + 2000), row(-1, "r", t + 1000)], 4);
  }),
  test("C1-3", "two pages with the same request id sum all three rows", s => {
    ready(s); const t = s.state().holds.call1.t;
    batch(s, [page([row(2, "r", t + 2000), row(-1, "r", t + 1000)], "next"), page([row(-5, "r", t)])]);
    total(s, 4); assert(txCount(s) === 2, "read page two");
  }),
  test("C1-4", "upfront forty, later thirty and refund forty leave thirty", async s => {
    let st = state("prism/investigate", 40); const t = st.holds.call1.t;
    st = await sum(s, st, [row(-40, "r", t, "prism/investigate")], 40);
    await sum(s, st, [row(-30, "r", t + 1000, "prism/investigate"), row(40, "r", t + 2000, "prism/investigate")], 30);
  }),
  test("C1-5", "a repeated row id is stored once and a replacement replaces its amount", async s => {
    let st = state(); const t = st.holds.call1.t, r = row(-5, "r", t);
    st = await sum(s, st, [r], 5); st = await sum(s, st, [r], 5);
    await sum(s, st, [{ ...r, amount: -6 }], 6);
  }),
  test("C1-6", "old three-array ledger entries are rejected strictly", async s => {
    const st = state(); st.led = { eps: { [EP]: { r: [5, 0, st.holds.call1.t] } } };
    assert(await calc(s, st, []) === null, "old ledger shape must keep holds");
  }),
  ...[undefined, null, ""].map((id, i) => test(`C1-${7 + i}`, "a deduction without a usable row id rejects recompute", async s => {
    const st = state(), r = row(-5, "r", st.holds.call1.t); r.id = id;
    assert(await calc(s, st, [r]) === null, "missing row id is uncertain");
  })),
  test("C1-10", "same row id replaces a larger prior amount rather than retaining its maximum", async s => {
    let st = state(); const t = st.holds.call1.t, r = row(-5, "r", t);
    st = await sum(s, st, [r], 5); await sum(s, st, [{ ...r, amount: -4 }], 4);
  }),
  test("C1-11", "stored ledger shape retains every row id and the earliest deduction stamp", async s => {
    const st = state(), t = st.holds.call1.t, rows = [row(-5, "r", t), row(2, "r", t + 2000)];
    const result = await calc(s, st, rows), entry = result?.state.led.eps[EP].r;
    assert(entry && !Array.isArray(entry) && entry.t === t && Object.keys(entry.rows).length === 2, "per-request object stores t and rows");
    assert(JSON.stringify(entry.rows[rows[0].id]) === JSON.stringify([-5, t]), "deduction amount and stamp stored");
    assert(entry.rows[rows[1].id]?.[0] === 2, "refund amount stored under its row id");
  }),
  ...[
    ["env", KEY, true, false], ["braced", "${SOCIALCRAWL_API_KEY}", true, false],
    ["env-file", "$(cat ~/.config/socialcrawl/api_key)", true, true],
    ["file", "$(cat ~/.config/socialcrawl/api_key)", false, false], ["file-env", KEY, false, true],
    ["other-var", "$OTHER_KEY", true, true], ["other-file", "$(cat /tmp/other)", true, true],
    ["literal", FAKE_KEY, true, true], ["duplicate", KEY, true, true], ["single", KEY, true, true],
    ["subdomain", KEY, true, true], ["missing", KEY, true, true], ["chained", KEY, true, true],
    ["case", KEY, true, false], ["absolute", null, false, false],
  ].map(([name, value, hasEnv, nc], i) => test(`C2-${i + 1}`, `${name}: account provenance controls closing after a clean return and rows`, s => {
    const keyFile = join(s.dir, ".config", "socialcrawl", "api_key"); mkdirSync(dirname(keyFile), { recursive: true }); writeFileSync(keyFile, FAKE_KEY);
    if (name === "absolute") value = `$(cat ${keyFile.replaceAll("\\", "/")})`;
    let header = `-H "x-api-key: ${value}"`;
    if (name === "duplicate") header += ` -H "X-API-KEY: ${value}"`;
    if (name === "single") header = `-H 'x-api-key: ${value}'`;
    if (name === "missing") header = "";
    if (name === "case") header = `-H "X-Api-Key:  ${value}  "`;
    let command = cmd(EP, header);
    if (name === "subdomain") command = command.replace(HOST, HOST.replace("www.", "api."));
    if (name === "case") command = command.replace(HOST, HOST.toUpperCase());
    if (name === "chained") command += " && " + cmd(EP, '-H "x-api-key: $OTHER_KEY"');
    const o = { env: { SOCIALCRAWL_API_KEY: hasEnv ? FAKE_KEY : "" } };
    pre(s, "call1", command, o); post(s, "call1", command, o); age(s);
    batch(s, [page([row(-1)])], o);
    const h = s.state().holds.call1;
    assert(!!h.nc === nc, `nc must be ${nc}`);
    assert((h.post === undefined) === nc, "only a proven account gets a finite window");
    total(s, nc ? (name === "chained" ? 35 : 18) : 1);
  })),
  test("C2-16", "ten calls on another account cannot settle to one unrelated row", s => {
    const c = cmd("prism/creator-vet", '-H "x-api-key: $OTHER_KEY"');
    for (let i = 0; i < 10; i++) { pre(s, `c${i}`, c); post(s, `c${i}`, c); }
    age(s); batch(s, [page([row(-75, "unrelated", Date.now() - 180000, "prism/creator-vet")])]);
    assert(s.state().spent >= 750, "other account's 750-credit debt stays held");
  }),
  ...["PreToolUse", "PostToolUse"].map((event, i) => test(`C3-${i + 1}`, "losing lock ownership before rename refuses the write and preserves bytes", s => {
    if (event === "PostToolUse") pre(s);
    const before = s.stateRaw(), p = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const write = fs.writeFileSync;
fs.writeFileSync = (p, ...a) => { if (String(p).startsWith(process.env.G4_STATE + ".") && String(p).endsWith(".tmp")) write(process.env.G4_STATE + ".lock", "foreign-owner"); return write(p, ...a); };
syncBuiltinESMExports();`);
    const r = run(s, cmd(), { event, node: ["--import", p], env: { SOCIALCRAWL_API_KEY: FAKE_KEY, G4_STATE: s.stateFile },
      extra: { tool_use_id: "call1", tool_response: { interrupted: false } } });
    if (event === "PreToolUse") assert(r.decision === "deny", "lost ownership refuses call", r); else quiet(r);
    assert(s.stateRaw() === before, "lost write leaves state byte-identical and holds retained");
  })),
  test("C3-3", "an eleven-second stale lock can be broken", s => {
    writeFileSync(s.stateFile + ".lock", "dead-owner"); const old = new Date(Date.now() - 11000); utimesSync(s.stateFile + ".lock", old, old);
    pre(s); total(s, 17); assert(!existsSync(s.stateFile + ".lock"), "own lock removed");
  }),
  test("C3-4", "unlock leaves another owner's token intact", s => {
    const p = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const rename = fs.renameSync;
fs.renameSync = (a, b, ...rest) => { const r = rename(a, b, ...rest); if (b === process.env.G4_STATE) fs.writeFileSync(b + ".lock", "foreign-owner"); return r; }; syncBuiltinESMExports();`);
    pre(s, "call1", cmd(), { node: ["--import", p], env: { SOCIALCRAWL_API_KEY: FAKE_KEY, G4_STATE: s.stateFile } });
    assert(existsSync(s.stateFile + ".lock") && readFileSync(s.stateFile + ".lock", "utf8") === "foreign-owner", "foreign lock survives unlock");
  }),
  test("C3-5", "a stale stat followed by a fresh owner's replacement must preserve the fresh lock", s => {
    writeFileSync(s.stateFile + ".lock", "dead-owner"); const old = new Date(Date.now() - 11000); utimesSync(s.stateFile + ".lock", old, old);
    const before = s.stateRaw(), p = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const stat = fs.statSync; let swapped = false;
fs.statSync = (p, ...a) => { const st = stat(p, ...a); if (p === process.env.G4_STATE + ".lock" && !swapped) { swapped = true; fs.writeFileSync(p, "fresh-B"); } return st; }; syncBuiltinESMExports();`);
    const r = run(s, cmd(), { node: ["--import", p], env: { SOCIALCRAWL_API_KEY: FAKE_KEY, G4_STATE: s.stateFile }, extra: { tool_use_id: "call1" } });
    assert(r.decision === "deny" && s.stateRaw() === before, "P cannot write through B's fresh lock", r);
    assert(existsSync(s.stateFile + ".lock") && readFileSync(s.stateFile + ".lock", "utf8") === "fresh-B", "B lock survives stale break");
  }),
  test("C3-6", "new lock content is a pid and unique UUID owner token", s => {
    const trace = join(scratch(s), "owner"), p = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const write = fs.writeFileSync;
fs.writeFileSync = (p, ...a) => { const r = write(p, ...a); if (p === process.env.G4_STATE + ".lock") write(process.env.G4_TRACE, fs.readFileSync(p)); return r; }; syncBuiltinESMExports();`);
    pre(s, "call1", cmd(), { node: ["--import", p], env: { SOCIALCRAWL_API_KEY: FAKE_KEY, G4_STATE: s.stateFile, G4_TRACE: trace } });
    assert(/^\d+\.[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(readFileSync(trace, "utf8")), "pid.randomUUID token");
  }),
  ...["read", "stat"].map(mode => test(`C3-private-error-${mode}`, "an inconclusive private-lock check restores a fresh owner", s => {
    const lock = s.stateFile + ".lock", before = s.stateRaw(), trace = join(scratch(s), "fault-seen");
    writeFileSync(lock, "dead-owner"); const old = new Date(Date.now() - 11000); utimesSync(lock, old, old);
    const p = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const stat = fs.statSync, read = fs.readFileSync; let swapped = false, failed = false;
const fault = (p, mode) => { if (!failed && String(p).startsWith(process.env.G4_STATE + ".lock.") && String(p).endsWith(".stale") && process.env.G4_MODE === mode) { failed = true; fs.writeFileSync(process.env.G4_TRACE, mode); throw Object.assign(new Error("private check unavailable"), { code: "EACCES" }); } };
fs.statSync = (p, ...a) => { fault(p, "stat"); const st = stat(p, ...a); if (p === process.env.G4_STATE + ".lock" && !swapped) { swapped = true; fs.writeFileSync(p, "fresh-B"); } return st; };
fs.readFileSync = (p, ...a) => { fault(p, "read"); return read(p, ...a); }; syncBuiltinESMExports();`);
    const r = run(s, cmd(), { node: ["--import", p], env: { SOCIALCRAWL_API_KEY: FAKE_KEY, G4_STATE: s.stateFile, G4_MODE: mode, G4_TRACE: trace }, extra: { tool_use_id: "call1" } });
    assert(existsSync(trace), "private-file error was exercised");
    assert(r.decision === "deny" && s.stateRaw() === before && existsSync(lock) && readFileSync(lock, "utf8") === "fresh-B", "inconclusive read/stat cannot delete B's fresh lock", r);
  })),
  test("C3-7", "deterministic P stale-stat and B fresh-lock race preserves B's write", async s => {
    pre(s); const before = s.stateRaw(), dir = scratch(s), lock = s.stateFile + ".lock";
    writeFileSync(lock, "stale-owner"); const old = new Date(Date.now() - 11000); utimesSync(lock, old, old);
    const paused = join(dir, "p-paused"), pGo = join(dir, "p-go"), bReady = join(dir, "b-ready"), bGo = join(dir, "b-go");
    const pHook = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const stat = fs.statSync; let once = false;
fs.statSync = (p, ...a) => { const st = stat(p, ...a); if (p === process.env.G4_STATE + ".lock" && !once) { once = true; fs.writeFileSync(process.env.G4_PAUSED, "ready"); const end = Date.now() + 6500; while (!fs.existsSync(process.env.G4_GO) && Date.now() < end) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10); } return st; }; syncBuiltinESMExports();`);
    const bHook = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const write = fs.writeFileSync; let once = false;
fs.writeFileSync = (p, ...a) => { if (!once && String(p).startsWith(process.env.G4_STATE + ".") && String(p).endsWith(".tmp")) { once = true; write(process.env.G4_PAUSED, "ready"); const end = Date.now() + 6500; while (!fs.existsSync(process.env.G4_GO) && Date.now() < end) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10); } return write(p, ...a); }; syncBuiltinESMExports();`);
    const p = start(s, "PreToolUse", { id: "p", node: ["--import", pHook], env: { G4_STATE: s.stateFile, G4_PAUSED: paused, G4_GO: pGo } });
    let b;
    try {
      await waitFor(() => existsSync(paused)); rmSync(lock);
      b = start(s, "PreToolUse", { id: "b", node: ["--import", bHook], env: { G4_STATE: s.stateFile, G4_PAUSED: bReady, G4_GO: bGo } });
      await waitFor(() => existsSync(bReady)); const owner = readFileSync(lock, "utf8"); writeFileSync(pGo, "go");
      const pr = await p.done;
      const survived = existsSync(lock) && readFileSync(lock, "utf8") === owner && s.stateRaw() === before;
      writeFileSync(bGo, "go"); const br = await b.done; quiet(br);
      assert(survived && pr.exit === 0 && JSON.parse(pr.raw).hookSpecificOutput.permissionDecision === "deny", "B fresh lock survives P's break attempt");
      total(s, 34); assert(s.state().holds.call1 && s.state().holds.b && !s.state().holds.p, "B saves its own committed hold");
    } finally {
      writeFileSync(pGo, "go"); writeFileSync(bGo, "go");
      for (const child of [p, b].filter(Boolean)) { if (child.child.exitCode === null) child.child.kill(); await child.done; }
    }
  }),
  ...[
    ["web/crawl/", "web/crawl", " -X POST -d '{\"url\":\"x\",\"limit\":10000}'", 10000],
    ["prism/investigate/?goal=x&budget=200", "prism/investigate?goal=x&budget=200", "", 200],
    ["instagram//profile", "instagram/profile", "", 50],
    ["credits//balance", "credits/balance", "", 0],
  ].map(([variant, ordinary, flags, expected], i) => test(`C4-${i + 1}`, "slash spelling counts at least the typed baseline and normal price", s => {
    const c = ep => `curl -s${flags} -H "x-api-key: ${KEY}" "${V1}${ep}"`;
    pre(s, "normal", c(ordinary)); const normal = s.state().spent;
    pre(s, "variant", c(variant)); const counted = s.state().spent - normal;
    assert(counted === Math.max(expected, normal), `slash variant ${counted}; normal ${normal}; baseline floor ${expected}`);
  })),
  test("R1-1", "session path storage scrubs a key run", s => {
    pre(s, "call1", cmd("sc_" + "inventedCanary123/x"));
    assert(!/sc_[a-z0-9_-]{3,}/i.test(s.stateRaw()), "no key-shaped run in session JSON");
  }),
  test("R1-2", "ordinary endpoint storage stays exact", s => {
    pre(s); assert(s.state().holds.call1.calls[0][0] === EP, "ordinary path unchanged");
  }),
  test("R1-3", "key-print lint includes a session JSON clause", () => {
    const src = readFileSync(join(ROOT, "tools", "socialcrawl", "check_r15_2_keyprint.mjs"), "utf8");
    assert(/sessions/.test(src) && /\.json/.test(src), "session JSONs must be in lint scope (implementation deferred to Phase B)");
  }),
  test("R1-session-scope", "session lint scans clean JSON and rejects a planted key without printing it", s => {
    const src = readFileSync(join(ROOT, "tools", "socialcrawl", "check_r15_2_keyprint.mjs"), "utf8");
    const clause = src.slice(src.indexOf("/* C11:"), src.indexOf("/* ------------------------------------------------------------------------- report */"));
    assert(clause.startsWith("/* C11:"), "session clause exists");
    const evaluate = code => {
      let result;
      Function("process", "homedir", "join", "existsSync", "readdirSync", "statSync", "readFileSync", "clause", code)(
        { env: { SC_REVXL_HOME: s.revxl } }, () => s.dir, join, existsSync, readdirSync, statSync, readFileSync,
        (id, cover, bad) => { result = { id, cover, bad }; });
      return result;
    };
    assert(evaluate(clause).bad.length === 0, "ordinary session is clean");
    const canary = "sc_" + "SessionFixture123"; s.seed({ spent: 0, path: canary });
    const result = evaluate(clause);
    assert(result.bad.length === 1 && !JSON.stringify(result).includes(canary), "one planted key detected, with no key in lint output");
    const find = '/sc_[a-z0-9_-]{3,}/i.test(readFileSync(file, "utf8"))';
    assert(clause.includes(find), "session scanner mutation anchor exists");
    const mutant = clause.replace(find, "false");
    const target = join(scratch(s), "session-clause.mjs"); writeFileSync(target, mutant);
    assert(evaluate(readFileSync(target, "utf8")).bad.length === 0, "named C11-blind mutant misses the planted key and makes the session assertion RED");
  }),
  test("G3-C11-1", "session lint skips unset or blank homes without consulting the real home", s => {
    const src = readFileSync(join(ROOT, "tools", "socialcrawl", "check_r15_2_keyprint.mjs"), "utf8");
    const code = src.slice(src.indexOf("/* C11:"), src.indexOf("/* ------------------------------------------------------------------------- report */"));
    const skip = "SC_REVXL_HOME is not set, so C11 was skipped (it never reads the real settings folder)";
    for (const override of [undefined, "", "  ", scratch(s), s.revxl]) {
      const lines = []; let result, reads = 0, homes = 0;
      if (override === s.revxl) writeFileSync(s.stateFile, JSON.stringify({ path: FAKE_KEY }));
      const scoped = fn => (...args) => { reads++; return fn(...args); };
      Function("process", "homedir", "join", "existsSync", "readdirSync", "statSync", "readFileSync", "clause", "console", code)(
        { env: override === undefined ? {} : { SC_REVXL_HOME: override } }, () => { homes++; return s.dir; },
        scoped(join), scoped(existsSync), scoped(readdirSync), scoped(statSync), scoped(readFileSync),
        (id, cover, bad) => { result = { id, cover, bad }; }, { log: line => lines.push(line) });
      if (!override?.trim()) {
        assert(homes === 0 && reads === 0, "unset or blank override never resolves or reads a home path");
        assert(lines.includes(skip) && result?.bad.length === 0, "C11 explicitly skips without a failure");
      } else {
        assert(homes === 0 && lines.length === 0 && result?.id === "C11", "explicit home keeps the C11 scan");
        assert(result.cover === `${override === s.revxl ? 1 : 0} session JSON files scanned`, "explicit home reports scanned count");
        assert(result.bad.length === (override === s.revxl ? 1 : 0), "only the planted fake key fails C11");
        assert(!JSON.stringify(result).includes(FAKE_KEY), "C11 does not print the fake key");
      }
    }
  }),
  test("R2-1", "forty never-closing five-credit holds plus forty five-credit rows count four hundred", async s => {
    const st = state(EP, 5, false), h = st.holds.call1; h.nc = true;
    st.holds = Object.fromEntries(Array.from({ length: 40 }, (_, i) => [`c${i}`, structuredClone(h)])); st.spent = 200;
    await sum(s, st, Array.from({ length: 40 }, (_, i) => row(-5, `r${i}`, h.t)), 400);
  }),
  test("R2-2", "a row first seen during a long call remains counted when its finite window closes", async s => {
    let st = state(EP, 17, false); const t = st.holds.call1.t;
    st = await sum(s, st, [row(-4, "r", t)], 21);
    st.holds.call1.post = t; st.holds.call1.pu = st.holds.call1.u;
    await sum(s, st, [], 4);
  }),
  test("R2-3", "nc hold stays full beside a returned call's counted row", async s => {
    const st = state(); st.holds.nc = { ...st.holds.call1, nc: true }; delete st.holds.nc.post; delete st.holds.nc.pu; st.spent = 34;
    st.holds.nc.t += 180000; st.holds.nc.u += 180000;
    const result = await sum(s, st, [row(-4, "r", st.holds.call1.t)], 21);
    assert(result.usage === 4 && result.full === 1, "finite-only row counts beside the later open hold");
  }),
  test("R2-4", "a stuck window counts its full hold plus its rows", async s => {
    const st = state(); st.holds.call1.stuck = true;
    await sum(s, st, [row(-4, "r", st.holds.call1.t)], 21);
  }),
  test("R3-1", "the single async-start constant matches positive-price catalogue descriptions", () => {
    const costs = JSON.parse(readFileSync(COSTS, "utf8"));
    const expected = [...new Set(Object.entries(costs).filter(([, v]) => /async|background job/i.test(v.desc || "") &&
      (typeof v.credits !== "number" || v.credits > 0)).map(([k]) => k.replace(/^\S+ /, "")))].sort();
    const src = readFileSync(GUARD, "utf8"), sets = [...src.matchAll(/const\s+\w+\s*=\s*(?:new Set\()?\[([^\]]*)\]/g)];
    const candidates = sets.map(m => [...m[1].matchAll(/["']([^"']+)["']/g)].map(x => x[1]).sort());
    assert(candidates.some(x => JSON.stringify(x) === JSON.stringify(expected)), `single async constant must equal ${expected.join(", ")}`);
  }),
  ...["web/agent", "web/batch-scrape", "web/crawl", "prism/jobs"].map((ep, i) => test(`R3-${i + 2}`, "async start never acquires a clean-return window", s => {
    const c = `curl -s -X POST -H "x-api-key: ${KEY}" "${V1}${ep}" -d '{"urls":["x"],"limit":10}'`;
    pre(s, "call1", c); post(s, "call1", c);
    const h = s.state().holds.call1; assert(h.nc === true && h.post === undefined, `${ep} stays open`);
  })),
  test("R3-6", "async path detection also covers GET with repeated and trailing slashes", s => {
    const c = cmd("web//agent/"); pre(s, "call1", c); post(s, "call1", c);
    assert(s.state().holds.call1.nc && s.state().holds.call1.post === undefined, "normalised async path never closes with another verb");
  }),
  test("R4-1", "after path takes the lock before its first readState", () => {
    const src = readFileSync(GUARD, "utf8"), after = src.slice(src.indexOf("if (after) {"), src.indexOf("// Heredoc bodies"));
    assert(after.indexOf("lock(stateFile") >= 0 && after.indexOf("lock(stateFile") < after.indexOf("readState()"), "after path reads only under lock");
  }),
  ...["EPERM", "EACCES", "EBUSY"].map((code, i) => test(`R4-${i + 2}`, "state rename retries two transient failures then saves", s => {
    const trace = join(scratch(s), "rename-times.jsonl"), p = preload(s, `import fs from "node:fs"; import { syncBuiltinESMExports } from "node:module";
const rename = fs.renameSync; let n = 0;
fs.renameSync = (a, b, ...rest) => { if (b === process.env.G4_STATE) { fs.appendFileSync(process.env.G4_TRACE, Date.now() + "\\n"); if (n++ < 2) throw Object.assign(new Error("transient"), { code: process.env.G4_CODE }); } return rename(a, b, ...rest); }; syncBuiltinESMExports();`);
    const r = run(s, cmd(), { node: ["--import", p], env: { SOCIALCRAWL_API_KEY: FAKE_KEY, G4_STATE: s.stateFile, G4_TRACE: trace, G4_CODE: code }, extra: { tool_use_id: "call1" } });
    quiet(r); total(s, 17);
    const ts = readFileSync(trace, "utf8").trim().split("\n").map(Number);
    assert(ts.length === 3 && ts[1] - ts[0] >= 18 && ts[2] - ts[1] >= 18, "20 ms pauses between rename retries");
  })),
  ...["empty", "Read", "PostToolUse", "refusal"].map((shape, i) => test(`W-MINOR-1-${i + 1}`, "no key writes no session bytes for an after event or refusal", s => {
    ready(s); s.budget({ sessionBudget: 20 }); const before = s.stateRaw(), o = { env: { SOCIALCRAWL_API_KEY: "" } };
    if (shape === "refusal") {
      const r = run(s, cmd(), { ...o, extra: { tool_use_id: "call2" } }); assert(r.decision === "deny", "over limit still denied");
    } else if (shape === "PostToolUse") {
      // Use a new unmarked hold, so no-key early exit is observable.
      edit(s, st => { delete st.holds.call1.post; delete st.holds.call1.pu; });
      const raw = s.stateRaw(); post(s, "call1", cmd(), o); assert(s.stateRaw() === raw, "no-key marker writes nothing"); return;
    } else batch(s, [page([])], { ...o, extra: { tool_calls: shape === "empty" ? [] : [{ tool_name: "Read", tool_input: {} }] } });
    assert(s.stateRaw() === before && txCount(s) === 0, "no-key state byte-identical; no failed read counted");
  })),
  test("W-MINOR-1-5", "two refusals within thirty seconds make only one failed read", s => {
    ready(s); s.budget({ sessionBudget: 20 });
    for (const id of ["call2", "call3"]) {
      const r = run(s, cmd(), { extra: { tool_use_id: id }, fetch: { transactions: [{ throw: true }] } });
      assert(r.decision === "deny", "transport failure preserves refusal");
    }
    total(s, 17); assert(txCount(s) === 1 && s.state().led.fails === 1, "before-refusal spacing is thirty seconds");
  }),
  ...["PostToolUse", "PostToolBatch"].map((event, i) => test(`W-MINOR-2-${i + 1}`, "after-call lock wait stays below 2600 ms", s => {
    pre(s); const before = s.stateRaw(); writeFileSync(s.stateFile + ".lock", "foreign-fresh-owner");
    const r = run(s, cmd(), { event, extra: { tool_use_id: "call1", tool_response: { interrupted: false } } });
    quiet(r); assert(s.stateRaw() === before, "held lock keeps bytes"); assert(r.ms < 2600, `after lock wait ${r.ms} ms must be under 2600`);
  })),
  test("W-MINOR-2-3", "Pre retains its four-second fresh-lock wait", s => {
    const before = s.stateRaw(); writeFileSync(s.stateFile + ".lock", "foreign-fresh-owner");
    const r = run(s, cmd(), { extra: { tool_use_id: "call1" } });
    assert(r.decision === "deny" && r.exit === 0 && r.stderr === "" && r.ms >= 3500 && r.ms < 5000, `Pre waits four seconds: ${r.ms}`, r);
    assert(s.stateRaw() === before, "refused Pre leaves state unchanged");
  }),
  test("R5-1", "hook description contains exactly the four frozen wording replacements", () => {
    let original = readFileSync(join(dirname(GUARD), "hooks.json"), "utf8");
    const desc = JSON.parse(original).description;
    const pairs = [
      ["and pass within the limit.", "and pass within the limit, " + TSCRIPT + " calls unless the person's " + TSCRIPT + " setting blocks them."],
      ["and reaching it exactly passes.", "and reaching it exactly passes. Before such a refusal, when one of its counted calls has returned, it reads the free ledger once (at most once per 30 seconds) and settles returned holds first."],
      ["and whether the run is a Desktop routine, never a key or a command", "whether the run is a Desktop routine and the call's tool_use_id; a change the give-back makes to the total adds a settle line (decision settle, the total before and after); never a key or a command"],
      ["is denied before anything else and is not logged;", "is denied before anything else and is not logged (a command over 65,536 characters naming " + HOST.slice(4) + " is denied as not plain first, and logged when unattended);"],
    ];
    for (const [old, fresh] of pairs) {
      assert(desc.includes(fresh), `new phrase required: ${fresh}`);
      // The second insertion deliberately retains its old sentence as a prefix.
      if (!fresh.includes(old)) assert(!desc.includes(old), "replaced phrase is gone");
      original = original.replace(fresh, old);
    }
    assert(createHash("sha256").update(original).digest("hex") === "b0fa468401c80421fbfcc886d99a2911838a43a025d3c5e13745bfa1767ced33", "all other hooks.json bytes stay identical to baseline (re-pinned by G3: the wording sweep and the give-back limits; re-pinned by EGfix-G: B1, B2, C1, W1, W6 wording)");
  }),
  ...["early", "late"].map((which, i) => test(`R6-${i + 1}`, "guard-error deny gives the retry instruction with the usual tail", s => {
    const source = readFileSync(s.guard, "utf8"), anchor = which === "early" ? "async function sessionMain(input, after) {" : "      let lead = null;";
    s.guard = copyHooks(s, anchor, anchor + '\n throw new Error("forced guard error");');
    const before = s.stateRaw(), r = run(s, cmd("youtube/" + TSCRIPT), { extra: { tool_use_id: "call1" } });
    assert(source.includes(anchor), "error injection path exists");
    const message = "SocialCrawl call not run: the credit guard hit an error while checking this " + TSCRIPT + " call. Run the command again." + T;
    assert(r.decision === "deny" && r.message === message && !r.message.includes("Settings"), "exact retry error wording", r);
    assert(s.stateRaw() === before, "error denies without counting");
  })),
  ...[null, undefined, ""].map((request, i) => test(`R8-${i + 1}`, "a missing request id groups its deduction by row id and includes seventeen", async s => {
    const st = state(), t = st.holds.call1.t;
    const missing = row(-17, "unused", t, EP, "unattributed-row"); missing.request_id = request;
    await sum(s, st, [row(-1, "matched", t), missing], 18);
  })),
  test("R7-1", "the identical refund row read twice is counted once", async s => {
    let st = state(); const t = st.holds.call1.t, refund = row(2, "r", t + 2000);
    st = await sum(s, st, [row(-5, "r", t)], 5);
    st = await sum(s, st, [refund], 3); await sum(s, st, [refund], 3);
  }),
  test("R9-1", "covered read during tail followed by short pages keeps the hold stuck", async s => {
    const gb = await moduleFor(s), now = Math.floor(Date.now() / 1000) * 1000, up = uptime() * 1000;
    let st = state(); Object.assign(st.holds.call1, { t: now - 200000, u: up - 200000, post: now - 140000, pu: up - 140000 });
    st = await sum(s, st, [row(-1, "r", now - 190000)], 18, { vNow: now - 60000 });
    const replies = [page([row(-1, "other1", now - 80000, "web/scrape")], "next", now),
      page([row(-1, "other2", now - 90000, "web/scrape")], "more", now)];
    let calls = 0;
    const read = await gb.readLedger(st, { left: () => 8000, env: { SOCIALCRAWL_API_KEY: FAKE_KEY }, home: s.dir,
      transport: async () => { const r = replies[calls++]; return new Response(JSON.stringify(r.body), { headers: r.headers }); } });
    assert(read && calls === 2 && read.uncovered, "back-reach needs both pages and still finds an uncovered span");
    const result = await calc(s, st, read.rows, read);
    assert(result && result.state.holds.call1.stuck && result.state.spent >= 17, "uncovered tail stays held and stuck");
  }),
  test("R10-1", "over-refunded id cannot cancel a second id's four credits", async s => {
    const st = state(), t = st.holds.call1.t;
    await sum(s, st, [row(-5, "a", t), row(8, "a", t + 2000), row(-4, "b", t)], 4);
  }),
  test("R11-1", "Pre re-reads under lock after a hanging read and preserves a concurrent commit", async s => {
    ready(s); s.budget({ sessionBudget: 20 });
    const a = start(s, "PreToolUse", { id: "denied", replies: [{ hang: true }] });
    try {
      await waitFor(() => txCount(s) === 1);
      assert(!existsSync(s.stateFile + ".lock"), "ledger wait is unlocked");
      pre(s, "concurrent", cmd("amazon/shop")); total(s, 18);
      assert(a.child.exitCode === null, "concurrent commit happened during hanging read");
      const r = await a.done; assert(r.exit === 0 && r.stderr === "" && JSON.parse(r.raw).hookSpecificOutput.permissionDecision === "deny", "first Pre refuses");
      total(s, 18); assert(s.state().holds.call1 && s.state().holds.concurrent, "both committed holds survive");
    } finally { if (a.child.exitCode === null) { a.child.kill(); await a.done; } }
  }),
  ...["500", "non-json", "shape", "iterable-shape", "no-date"].map((name, i) => test(`R12-${i + 1}`, "failed read has a valid Date except the explicit missing-Date control", async s => {
    const gb = await moduleFor(s), st = state(), good = page([]);
    const body = name === "non-json" ? "not-json" : JSON.stringify(name === "shape" ? { items: [] } : name === "iterable-shape" ? { data: { items: "" } } : good.body);
    let calls = 0;
    const result = await gb.readLedger(st, { left: () => 8000, env: { SOCIALCRAWL_API_KEY: FAKE_KEY }, home: s.dir,
      transport: async () => { calls++; return new Response(body, { status: name === "500" ? 500 : 200, headers: name === "no-date" ? {} : good.headers }); } });
    assert(calls === 1 && result === null, `${name} fails for its own reason`);
  })),
  test("R12-6", "dated OK empty ledger is covered, not a failed read", async s => {
    const gb = await moduleFor(s), good = page([]);
    const result = await gb.readLedger(state(), { left: () => 8000, env: { SOCIALCRAWL_API_KEY: FAKE_KEY }, home: s.dir,
      transport: async () => new Response(JSON.stringify(good.body), { headers: good.headers }) });
    assert(result && result.rows.length === 0 && result.uncovered === null, "ordinary dated empty response succeeds");
  }),
  test("R13-1", "hanging before-refusal read denies within nine seconds and never changes spent", s => {
    ready(s); s.budget({ sessionBudget: 20 });
    const r = run(s, cmd(), { extra: { tool_use_id: "denied" }, fetch: { transactions: [{ hang: true }] } });
    assert(r.exit === 0 && r.stderr === "" && r.decision === "deny" && r.ms < 9000, `hanging Pre: ${r.ms} ms`, r);
    total(s, 17); assert(!s.state().holds.denied, "refused call never committed");
  }),
  test("Fake-ledger-1", "refund carries endpoint on its deduction page with a three-second Date skew", async s => {
    const st = state(), t = st.holds.call1.t, now = Math.floor(Date.now() / 1000) * 1000;
    const items = [row(-5, "a", t), row(2, "a", t + 2600)], reply = page(items, null, now + 3000), gb = await moduleFor(s);
    assert(items.every(x => x.endpoint === `/v1/${EP}`), "real-shaped refund endpoint");
    const result = await gb.readLedger(st, { left: () => 8000, env: { SOCIALCRAWL_API_KEY: FAKE_KEY }, home: s.dir,
      transport: async () => new Response(JSON.stringify(reply.body), { headers: reply.headers }) });
    assert(result && result.off > 1000 && result.off <= 3000, "Date is ahead of row clock");
    await sum(s, st, result.rows, 3, result);
  }),
  test("No-exit-1", "no-process-exit lint includes give-back and all covered modules are clean", () => {
    const lint = readFileSync(join(dirname(GUARD), "tests", "fixtures", "balance.mjs"), "utf8");
    assert(lint.includes('"give-back.mjs"'), "lint scope includes settlement module");
    for (const file of [G, GB, "ledger.mjs", "jev.mjs", "price.mjs"])
      assert(!readFileSync(join(dirname(GUARD), file), "utf8").includes("process.exit("), `no process.exit in ${file}`);
  }),
  test("Harness-1", "a throwing fixture after actual module execution is rejected as a mutant kill", async () => {
    let error;
    try { await mutationEvidence(GB, "const finite =", "const finite =", async guard => {
      await fixtures.find(f => f.id === "G4F-R7-1").fn(guard);
      if (guard !== GUARD) throw new Error("infrastructure fault");
    }); } catch (e) { error = e; }
    assert(error?.message === "mutant must fail a fixture assertion, not merely throw", "arbitrary throw cannot produce a passing kill");
  }),
  test("Harness-2", "identity assertion failure is never accepted as a kill", async () => {
    let error;
    try { await mutationEvidence(GB, "const finite =", "const finite =", () => assert(false, "identity failed")); } catch (e) { error = e; }
    assert(error?.message === "identity failed", "failed identity propagates before mutating");
  }),
  test("Harness-3", "a mutant that only throws while loading is rejected", async () => {
    let error;
    try { await mutationEvidence(GB, "export const TAIL_MS", 'throw new Error("load fault");\nexport const TAIL_MS',
      guard => fixtures.find(f => f.id === "G4F-R7-1").fn(guard)); } catch (e) { error = e; }
    assert(error?.message.startsWith("a module-load error is not a mutant kill"), "throw-only module is not a kill");
  }),
  test("H-64-1", "encoded false and zero disable the price flag at its base cost", s => {
    for (const [i, value] of ["%66alse", "%30"].entries()) {
      pre(s, `c${i}`, cmd(`google/company/ads?get_ad_details=${value}&id=x`)); total(s, 5 * (i + 1));
    }
  }),
];

const mutationCases = [
  ["EGF-W3", "EGF-W3-2", G, "pass < 5", "pass < 1"],
  ["EGF-B2", "EGF-B2-1", G, 'if (UNATTENDED || ROUTINE) logUnattended(sid, "pass",', 'if (UNATTENDED) logUnattended(sid, "pass",'],
  ["EGF-C1", "EGF-C1-1", G, 'if (Number.isFinite(balance) && balance >= 0)', 'if (Number.isInteger(balance) && balance >= 0)'],
  ["EGF-W6", "EGF-W6-1", G, W6_CHECK, ""],
  ["G3-H2-authorization", "G3-H2-1", G, 'if (headers.some(h => h.v.slice(0, h.v.indexOf(":")).trim().toLowerCase() === "authorization")) neverClose = true;', ""],
  ["G3-H2-query", "G3-H2-query-1", G, 'if ([...new URL(url.q.v).searchParams].some(([name, value]) =>', 'if (false && [...new URL(url.q.v).searchParams].some(([name, value]) =>'],
  ["G3-H3-collapse", "G3-H3-1", G, '.replace(/\\?.*$/, "").replace(/\\/+/g, "/")', '.replace(/\\?.*$/, "")'],
  ["R2-open-every", "F3-one-open-window", GB, "endedOpen.some(w => inside(w, stamp))", "endedOpen.every(w => inside(w, stamp))"],
  ["F2-skip-frozen", "F2-freeze", GB, "if (frozen) {", "if (frozen) continue; if (frozen) {"],
  ["F2-ignore-freeze-mark", "F2-frozen-empty-read", GB, "const frozen = old?.f === true;", "const frozen = false;"],
  ["R2-unreleased-over", "R2-open-over-fallback", GB, "!finiteHolds.includes(w)", "!open.includes(w)"],
  ["F1-ignore-mark", "F1-shift", GB, "entry.c === true || ", ""],
  ["F4-dot-segments", "C2-dotdot", G, 'if (!expanded.split(/[\\\\/]/).some(part => part === "." || part === ".."))', "if (true)"],
  ["R2-max", "R2-open-row", GB, "(openHolds + openRows)", "Math.max(openHolds, openRows)"],
  ["R2-hold-only", "R2-open-hold-row", GB, "(openHolds + openRows)", "openHolds"],
  ["R2-row-counted-twice", "R2-open-finite", GB, "!counted.has(entry) && ", ""],
  ["C1-rounding", "C1-fractional", GB, "Math.ceil(Math.max(0, -Object.values(entry.rows)", "Math.floor(Math.max(0, -Object.values(entry.rows)"],
  ["C1-integral-state", "C1-fractional-fixed", GB, "[spent, usage, full].every(Number.isInteger)", "[spent, usage, full].every(finite)"],
  ["C1-storage", "C1-1", GB, "const stored = { ...old?.rows, ...g.rows };", "const stored = { ...g.rows };"],
  ["C2-source", "C2-skill-table", G, "|| !sameSource) neverClose = true;", "|| false) neverClose = true;"],
  ["C3-owner", "C3-1", G, "if (owner !== lockToken)", "if (false)"],
  ["C3-stale-mtime", "C3-5", G, " && Date.now() - statSync(stale).mtimeMs > 10000", ""],
  ["C3-private-error", "C3-private-error-read", G, "let verifiedStale = false;", "let verifiedStale = true;"],
  ["C4-price", "C4-1", G, "if (normalized === u) return typed;", "if (true) return typed;"],
  ["R1-storage", "R1-1", G, 'normalPath(c.p).replace(/sc_[^/?#]*/gi, "sc_…")', "normalPath(c.p)"],
  ["R2-open-window", "F1-open-unmarked", GB, "w.end !== Infinity && inside(w, stamp)", "inside(w, stamp)"],
  ["R3-async", "R3-2", G, "if (ASYNC_START.has(path))", "if (false)"],
  ["R4-retry", "R4-2", G, 'if (!["EPERM", "EACCES", "EBUSY"].includes(e?.code) || left() < 20) throw e;', "throw e;"],
  ["W-MINOR-1-key", "W-MINOR-1-3", G, "!gb.hasKey() ||", "false ||"],
  ["W-MINOR-1-spacing", "W-MINOR-1-5", G, " && Date.now() - (st.led?.at || 0) >= 30000", ""],
  ["W-MINOR-2-cap", "W-MINOR-2-1", G, 'lock(stateFile, "session lock", 2000)', 'lock(stateFile, "session lock", 4000)'],
  ["R6-error", "R6-1", G, 'systemMessage: "SocialCrawl call not run: the credit guard hit an error while checking this ' + TSCRIPT + ' call. Run the command again." + T,', 'systemMessage: "Settings",'],
  ["R8-request-id", "R8-1", GB, "const id = typeof row.request_id", 'if (!row.request_id) continue; const id = typeof row.request_id'],
  ["R7", "R7-1", GB, "const stored = { ...old?.rows, ...g.rows };", "const stored = { ...old?.rows, ...g.rows }; for (const [rid, a] of Object.entries(g.rows)) if (a[0] > 0 && old?.rows?.[rid]) stored[rid] = [old.rows[rid][0] + a[0], a[1]];"],
  ["R9", "R9-1", GB, "st.led.seen - TAIL_MS", "st.led.seen"],
  ["R10", "R10-1", GB, "ids.reduce((sum, entry) => sum + Math.ceil(Math.max(0, -Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0))), 0)", "Math.ceil(Math.max(0, -ids.reduce((sum, entry) => sum + Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0), 0)))"],
  ["R11", "R11-1", G, 'st = await readState();\n        if (!st) return deny', '/* missing Pre re-read */\n        if (!st) return deny'],
  ["R12-status", "R12-1", GB, "!response.ok || !finite(date)", "!finite(date)"],
  ["R12-shape", "R12-4", GB, "!Array.isArray(body?.data?.items)", "false"],
  ["R13", "R13-1", GB, "Math.min(3000, left() - 700)", "9200"],
];
const mutants = mutationCases.map(([name, victim, file, find, replacement]) => {
  const victimId = victim.startsWith("EGF-") ? victim : `G4F-${victim}`;
  return test(`Mutant-${name}-1`, `named ${name} mutant is killed by ${victimId} after identity passes`, async () => {
    const proof = await mutationEvidence(file, find, replacement, guard => fixtures.find(f => f.id === victimId).fn(guard));
    console.log(`    MUTANT ${name}: ${victimId} RED; loaded=${proof.loaded}; ran=${proof.ran}; assertion=${proof.assertion.split("\n")[0]}`);
  });
});
export default [...fixtures, ...mutants];
