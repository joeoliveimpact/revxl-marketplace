/*
 * R12 — hooks/jev.mjs, the Jev decision layer.
 *
 * SYNCHRONOUS (P26). run.mjs does not await, so every fixture runs jev.mjs in a child process —
 * a DRIVER script that imports it and injects a fake transport (fixtures/ledger.mjs's pattern) —
 * or through its CLI with spawnSync, and asserts on what the child printed.
 *
 * ZERO NETWORK, NO REAL KEY. The fake transport records each request and answers from a canned
 * reply. Every child gets a scrubbed env: no OPENROUTER_API_KEY, HOME and USERPROFILE pointed at
 * an empty temp dir (so ~/.config/openrouter/api_key is never read), SC_REVXL_HOME in a temp dir,
 * and every proxy variable at a dead local port. The only key any fixture uses is a fake.
 *
 * Every fixture carries a KILLING MUTATION: a copy of jev.mjs with one substitution must FAIL the
 * assertion the real file passes. A mutant copy lives in a temp dir, so its two relative
 * references (./price.mjs and its own folder) are rewritten to the real hooks/ folder.
 *
 * THE FROZEN TEXT below is copied from Step 0.5 (09.23.26) and T2 (09.22.26), byte for byte, so a
 * drifted question fails here and not in a live call.
 */
import { assert } from "../lib.mjs";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { quote } from "../../price.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const HOOKS = resolve(HERE, "..", "..");
const JEV = join(HOOKS, "jev.mjs");
const RP = resolve(HOOKS, "..", "skills", "research-plays");
const readJson = (p) => JSON.parse(readFileSync(p, "utf8"));
const COSTS = readJson(join(HOOKS, "costs.json"));
const PKG = readJson(join(RP, "references", "packages.json"));
const CURATED = new Map(readJson(join(RP, "curated-workflows.json")).workflows.map((w) => [w.id, w]));

/* Never a real key. Split so no scanner reads this line as one. */
const FAKE_KEY = "sk-or-" + "FAKE-0000";
const DEAD = "http://127.0.0.1:9";
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const tmp = () => mkdtempSync(join(tmpdir(), "sc-jev-test-"));

/* ------------------------------------------------------------------ frozen text (the oracle) */
const MODEL_PIN = "typesafe/jev-1.13-20260917";
const T2_STATE = "A request typed by a user of a social-media research tool.";
const T2_IS_RESEARCH = {
  instructions: "Is `ask` a research request, where the person wants information gathered and interpreted?",
  criteria: {
    true: "Asks to find out, look into, research, or learn about people, brands, content, markets or facts.",
    false: "Names one exact API endpoint to call, asks to set up or install software, or asks for a task like booking or buying something.",
  },
};
const T2_MISSING = {
  instructions: "What is `ask` still missing before the research can start?",
  criteria: {
    nothing_missing: "The ask names who or what to research and where to look, clearly enough to start.",
    missing_target: "It does not name who to research: an unnamed competitor, client, account or brand.",
    missing_platform: "It names who or what, but not which platform or site to look on, and the research depends on it.",
    missing_topic: "It does not name the topic, niche or subject to research.",
    not_research: "It is not a research request: a single named API call, a setup task, or something like booking or buying.",
  },
};
const T2_ROUTE_INSTRUCTIONS = "Which route best fits what the person wants in `ask`?";
const T2_ROUTE = {
  website: "The person wants information pulled from a specific website or web page they name or link.",
  answer_with_sources: "The person wants a factual answer or a news summary backed by cited web sources, not social posts.",
  people_saying: "The person wants to know what people are saying, feeling or complaining about a topic, brand or person across social platforms or forums.",
  who_is: "The person wants a profile of a specific creator, brand or account: who they are, their size, their audience and followers.",
  buyers_leads: "The person wants to find potential buyers or leads: people publicly showing they want to buy something.",
  reviews_reputation: "The person wants product or company reviews and ratings, or what customers say about their experience with a product.",
  trending: "The person wants to know what is trending or popular right now on a platform or in a niche.",
  competitor_ads: "The person wants to see the ads a competitor or brand is running.",
  person_background: "The person wants a person's job history, employer or professional background.",
  own_account_health: "The person wants an audit or health check of their own social account.",
  audience_questions: "The person wants to know what questions their audience or market is asking.",
  carousel_text: "The person wants the actual words written on a competitor's Instagram carousel slides.",
  find_creators: "The person wants to find or build a list of creators or accounts that match a niche or size, not one account they already know.",
  free_web: "None of the above: a plain web search answers this, and no social data is needed.",
};
const NEW_ROWS = {
  competitor_offer: "The person wants to know what a competitor sells, what it costs, and how their offers are laid out.",
  ai_visibility: "The person wants to know whether ChatGPT or other AI search tools mention them, their brand or their competitors.",
};
const NONE_FIT = "The person wants a specific kind of data from a platform, marketplace or app that none of the options above is built to pull, and a plain web search would give only a rough answer.";
const ORDER_17 = [
  "website", "competitor_offer", "answer_with_sources", "people_saying", "who_is", "person_background",
  "find_creators", "buyers_leads", "reviews_reputation", "trending", "competitor_ads", "own_account_health",
  "audience_questions", "carousel_text", "ai_visibility", "free_web", "none_fit",
];
const WORTH_STATE = "A request typed by a user of a social-media research tool, and the research options that could answer it.";
const WORTH_LEVELS = ["It would not answer it", "It would answer a small part of it", "It would answer most of it", "It would answer it fully"];
const worthInstructions = (id) => "How well would the option `" + id + "` in `options` answer what the person wants in `ask`?";

/* What no Jev request may carry: a price field, or a price word outside the person's own ask. */
const PRICE_FIELDS = ["credits", "range", "quote", "ceiling", "perPage", "metered", "dryRun", "price", "cost", "low", "high"];
const PRICE_TEXT = /\d[\s\-–—:]*(?:cr|credits?)\b|\bcredits?\b|\$\s?\d|\bfree\b|\bpaid\b|\bcheap|\bexpensive\b|\bsession cap\b|\bcapped\b|\bown prices?\b|\brefund/i;
const TEST_NOTES = /unmeasured|tested \d|archived call|jev labels/i;

/* Every (where, text) pair in a request except state.ask, keys included. */
function texts(body) {
  const out = [];
  const walk = (v, where) => {
    if (typeof v === "string") return void out.push([where, v]);
    if (!v || typeof v !== "object") return;
    for (const [k, x] of Object.entries(v)) {
      if (where === "state" && k === "ask") continue;
      const at = where ? `${where}.${k}` : k;
      out.push([`${at} (key)`, k]);
      walk(x, at);
    }
  };
  walk(body, "");
  return out;
}
const priceFieldHits = (body) => texts(body).filter(([w, k]) => w.endsWith("(key)") && PRICE_FIELDS.includes(k));
/* "_" joins words in an id (free_topic_scout), where \b sees no word: read it as a space. The one
 * exemption is intake's route id free_web, Step 0.5's frozen text byte for byte (J7). */
const FROZEN_IDS = ["questions.package.criteria.free_web (key)"];
const priceTextHits = (body) => texts(body).filter(([w, t]) => !FROZEN_IDS.includes(w) && PRICE_TEXT.test(t.replace(/_/g, " ")));

/* ------------------------------------------------------------------------- the harness */
const scrubbed = (d) => ({
  ...process.env,
  OPENROUTER_API_KEY: "",
  HOME: d,
  USERPROFILE: d,
  SC_REVXL_HOME: join(d, "revxl"),
  HTTPS_PROXY: DEAD,
  HTTP_PROXY: DEAD,
  ALL_PROXY: DEAD,
  NODE_USE_ENV_PROXY: "1",
});

/* A copy of jev.mjs with substitutions applied. Anchors must exist or the fixture fails. */
const RELOCATE = [
  ['from "./price.mjs";', `from ${JSON.stringify(pathToFileURL(join(HOOKS, "price.mjs")).href)};`],
  ['from "./platform-tokens.mjs";', `from ${JSON.stringify(pathToFileURL(join(HOOKS, "platform-tokens.mjs")).href)};`],
  ["const HERE = dirname(fileURLToPath(import.meta.url));", `const HERE = ${JSON.stringify(HOOKS)};`],
];
function mutate(pairs) {
  let src = readFileSync(JEV, "utf8");
  for (const [find, replace] of [...RELOCATE, ...pairs]) {
    if (!src.includes(find)) throw new Error(`mutation anchor not found in jev.mjs: ${JSON.stringify(find)}`);
    src = src.split(find).join(replace);
  }
  const dest = join(tmp(), "jev.mjs");
  writeFileSync(dest, src);
  return dest;
}

/* A request file in its own temp dir; returns its path. */
function reqFile(obj) {
  const p = join(tmp(), "jev-ask.json");
  writeFileSync(p, JSON.stringify(obj));
  return p;
}

/* The fake decisions endpoint. Serialised into the driver, so it must stay self-contained.
 * CFG.seq[i], when given, is the reply config for the i-th request. */
function respond(body, i, CFG) {
  const C = CFG.seq ? CFG.seq[i] || {} : CFG;
  if (C.throws) return { throws: C.throws === "key" ? "key" : "ECONNRESET (fixture)" };
  if (C.status && C.status !== 200 && !C.withAnswers) return { status: C.status, json: { error: { code: C.status, message: "fixture" } } };
  if (C.noAnswers) return { status: 200, json: { model: "fixture" } };
  if (C.body) return { status: 200, json: C.body };
  const answers = {};
  for (const [id, q] of Object.entries(body.questions || {})) {
    if (q.type === "noul") {
      answers[id] = { type: "noul", noul: (C.noul || {})[id] ?? C.noulDefault ?? 0.1 };
    } else if (q.type === "choice") {
      const keys = Object.keys(q.criteria);
      const pick = (C.choice || {})[id] ?? keys[0];
      const probs = (C.probs || {})[id] || Object.fromEntries(keys.map((k) => [k, k === pick ? 1 : 0]));
      answers[id] = { type: "choice", choice: pick, probabilities: probs, confidence: (C.confidence || {})[id] ?? 0.9 };
    } else if (q.type === "score") {
      const probs = (C.score || {})[id] || { 0: 0, 1: 0, 2: 1, 3: 0 };
      answers[id] = { type: "score", score: (C.scoreValue || {})[id] ?? 2, probabilities: probs, legend: {}, confidence: 0.9 };
    }
  }
  return { status: C.status || 200, json: { model: "typesafe/jev-1.13-20260917", answers, usage: { cost: 0 } } };
}

/*
 * Run `body` in a driver that imported jev.mjs as `J`. In scope: T (the fake transport; T.calls
 * holds every {url, keyOk, body} it was handed), DIR (a temp dir, the default home), ENV (a fake
 * key + SC_REVXL_HOME under DIR), run(argv, {env, home}) -> {code, result, error, calls}, out(o).
 * CFG.request makes T build a Request with the key's header first: undici's own header check, the
 * one fetch runs before sending; building a Request opens no socket. CFG.throws "key" makes T throw
 * an error that quotes the key.
 */
function drive(body, { jev = JEV, cfg = {} } = {}) {
  const d = tmp();
  const f = join(d, "driver.mjs");
  writeFileSync(
    f,
    [
      `import * as J from ${JSON.stringify(pathToFileURL(jev).href)};`,
      `const CFG = ${JSON.stringify(cfg)};`,
      `const RESPOND = ${respond.toString()};`,
      `const FAKE = ${JSON.stringify(FAKE_KEY)};`,
      `const T = { calls: [], fn: async (url, key, body) => { T.calls.push({ url, keyOk: key === FAKE, body }); if (CFG.request) new Request(url, { method: "POST", headers: { Authorization: "Bearer " + key } }); const r = RESPOND(body, T.calls.length - 1, CFG); if (r.throws) throw new Error(r.throws === "key" ? "fixture error quoting Bearer " + key : r.throws); return r; } };`,
      `const DIR = ${JSON.stringify(d)};`,
      `const ENV = { OPENROUTER_API_KEY: FAKE, SC_REVXL_HOME: DIR + "/revxl" };`,
      `const run = async (argv, o = {}) => { const OUT = [], ERR = []; const before = T.calls.length; const code = await J.main(argv, { transport: T.fn, env: o.env || ENV, home: o.home || DIR, out: (s) => OUT.push(s), err: (s) => ERR.push(s) }); return { code, result: OUT.length ? JSON.parse(OUT.join("")) : null, error: ERR.join(""), calls: T.calls.length - before }; };`,
      `const out = (o) => process.stdout.write(JSON.stringify(o) + "\\n");`,
      `try {`,
      body,
      `} catch (e) { out({ threw: String((e && e.stack) || e) }); }`,
    ].join("\n")
  );
  const r = spawnSync(process.execPath, [f], { encoding: "utf8", input: "", env: scrubbed(d), maxBuffer: 1 << 26 });
  const text = String(r.stdout || "").trim();
  let json = null;
  try {
    json = JSON.parse(text.split("\n").pop());
  } catch { /* left null — the assertion prints the raw text */ }
  return { exit: r.status, stdout: text.slice(0, 1500), stderr: String(r.stderr || "").slice(0, 1500), json };
}

/* One CLI invocation with the scrubbed env (no key anywhere). */
function cli(args, { jev = JEV } = {}) {
  const r = spawnSync(process.execPath, [jev, ...args], { encoding: "utf8", input: "", env: scrubbed(tmp()) });
  return { exit: r.status, stdout: String(r.stdout || ""), stderr: String(r.stderr || "") };
}

const ASK = "research what customers are saying about Peloton on Reddit and TikTok";
const J = (x) => JSON.stringify(x);

export default [
  {
    id: "J1-jev-no-key-exits-3-with-zero-requests",
    desc: "no OPENROUTER_API_KEY (or one without the sk-or- prefix) and no key file: exit 3 and the transport is never called; a key file alone is enough to run",
    fn() {
      const q = reqFile({ ask: ASK });
      const r = drive(
        `const empty = DIR + "/empty"; const withFile = DIR + "/withfile";\n` +
          `const fs = await import("node:fs"); fs.mkdirSync(empty); fs.mkdirSync(withFile + "/.config/openrouter", { recursive: true });\n` +
          `fs.writeFileSync(withFile + "/.config/openrouter/api_key", FAKE + "\\n");\n` +
          `const none = await run(["intake", ${J(q)}], { env: {}, home: empty });\n` +
          `const noPrefix = await run(["intake", ${J(q)}], { env: { OPENROUTER_API_KEY: "not-a-key" }, home: empty });\n` +
          `const file = await run(["intake", ${J(q)}], { env: {}, home: withFile });\n` +
          `out({ none, noPrefix, file, keyOk: T.calls.every((c) => c.keyOk) });`
      );
      const j = r.json;
      assert(j && j.none && j.none.code === 3 && j.none.calls === 0, `no key must exit 3 with zero requests\n${r.stdout}${r.stderr}`);
      assert(j.noPrefix.code === 3 && j.noPrefix.calls === 0, `an env value without sk-or- is not a key\n${r.stdout}`);
      assert(j.file.code === 0 && j.file.calls === 1 && j.keyOk, `the key file alone must be read\n${r.stdout}`);
      assert(!/sk-or-/.test(r.stdout), `no key material may appear in the output\n${r.stdout}`);

      const c = cli(["intake", q]);
      assert(c.exit === 3, `CLI without a key must exit 3, got ${c.exit}\n${c.stderr}`);
      assert(c.stdout === "" && /no OpenRouter key/.test(c.stderr), `stdout empty, one plain line on stderr\n${J(c)}`);

      // KILL: drop the key check. The run walks straight into the transport.
      const m = mutate([["if (!key) throw new JevError(3,", "if (false) throw new JevError(3,"]]);
      const k = drive(`out(await run(["intake", ${J(q)}], { env: {}, home: DIR }));`, { jev: m });
      assert(k.json && k.json.calls === 1, `the mutant must reach the transport, or J1 proves nothing\n${k.stdout}`);
    },
  },
  {
    id: "J2-jev-http-status-maps-to-exit-code",
    desc: "401/403 -> 4 (key rejected), 402 -> 5 (no OpenRouter credit), 404 and every other failure (500, 429, a 500 whose body still carries answers, a thrown transport, a 200 with no answers, answers that are not an object, an unanswered question, a choice outside the options, a missing packages.json) -> 6",
    fn() {
      const q = reqFile({ ask: ASK });
      const want = [[401, 4], [403, 4], [402, 5], [404, 6], [500, 6], [429, 6], ["throws", 6], ["noAnswers", 6],
        ["500 with answers", 6], ["answers not an object", 6], ["a question unanswered", 6], ["a choice outside the options", 6]];
      const OTHER = {
        throws: { throws: true },
        noAnswers: { noAnswers: true },
        "500 with answers": { status: 500, withAnswers: true },
        "answers not an object": { body: { answers: "is_research: yes" } },
        "a question unanswered": { body: { answers: {} } },
        "a choice outside the options": { choice: { package: "not_a_row" } },
      };
      const seq = want.map(([s]) => OTHER[s] || { status: s });
      const runs = (jev) => {
        const r = drive(`const res = []; for (let n = 0; n < ${want.length}; n++) res.push(await run(["intake", ${J(q)}])); out(res);`, { jev, cfg: { seq } });
        assert(Array.isArray(r.json), `driver failed\n${r.stdout}${r.stderr}`);
        return want.map(([status, code], n) => ({ status, code, got: r.json[n].code, calls: r.json[n].calls }));
      };
      for (const x of runs(JEV)) {
        assert(x.got === x.code && x.calls === 1, `HTTP ${x.status} must exit ${x.code} after one request, got ${x.got}`);
      }

      // KILL: fold 402 into "other" (a dead OpenRouter balance would hide as exit 6), and 403 out of auth.
      const m402 = runs(mutate([["if (status === 402) throw new JevError(5,", "if (false) throw new JevError(5,"]])).find((x) => x.status === 402);
      assert(m402.got === 6, "the 402 mutant must exit 6, or J2 proves nothing about 402");
      const m403 = runs(mutate([["if (status === 401 || status === 403) throw", "if (status === 401) throw"]])).find((x) => x.status === 403);
      assert(m403.got === 6, "the 403 mutant must exit 6, or J2 proves nothing about 403");
      // KILLS: a 500 read as success when its body carries answers; a choice Jev was never offered accepted.
      const mOk = runs(mutate([["if (!(status >= 200 && status < 300) || !answers ||", "if (!answers ||"]])).find((x) => x.status === "500 with answers");
      assert(mOk.got === 0, `the no-status-check mutant must accept the 500, or J2 proves nothing (got ${mOk.got})`);
      const mOut = runs(mutate([["if (!Object.hasOwn(MISSING.criteria, miss) || !rowIds.includes(pick)) {", "if (false) {"]])).find((x) => x.status === "a choice outside the options");
      assert(mOut.got === 0, `the no-options-check mutant must accept the stray choice, or J2 proves nothing (got ${mOut.got})`);

      // A failure that is not one of jev.mjs's own errors (packages.json missing beside it) still exits 6.
      const empty = tmp();
      const moved = [[`const HERE = ${JSON.stringify(HOOKS)};`, `const HERE = ${JSON.stringify(empty)};`]];
      const lost = (jev) => drive(`out(await run(["intake", ${J(q)}]));`, { jev }).json;
      const l = lost(mutate(moved));
      assert(l && l.code === 6 && l.calls === 0 && l.result === null, `a missing packages.json must exit 6 before the transport\n${J(l)}`);
      // KILL: the catch-all code for such a failure.
      const lk = lost(mutate([...moved, ["return e instanceof JevError ? e.code : 6;", "return e instanceof JevError ? e.code : 1;"]]));
      assert(lk && lk.code === 1, `the catch-all mutant must exit 1, or J2 proves nothing (got ${lk && lk.code})`);
    },
  },
  {
    id: "J3-jev-host-lock-throws-before-the-transport",
    desc: "THE INVARIANT: decisionsUrl() refuses any URL but https://openrouter.ai/api/alpha/decisions (another path, host, scheme, port, userinfo, trailing-dot host, query or fragment), and a refused URL never reaches the transport",
    fn() {
      const BAD = {
        chat: "/api/v1/chat/completions",
        evil: "//evil.example/api/alpha/decisions",
        lookalike: "https://openrouter.ai.evil.example/api/alpha/decisions",
        http: "http://openrouter.ai/api/alpha/decisions",
        userinfo: "https://u:p@openrouter.ai/api/alpha/decisions",
        trailingDot: "https://openrouter.ai./api/alpha/decisions",
        port: "https://openrouter.ai:8443/api/alpha/decisions",
        query: "https://openrouter.ai/api/alpha/decisions?x=1",
        fragment: "https://openrouter.ai/api/alpha/decisions#x",
      };
      // The BAD names a copy of jev.mjs lets through without the lock's error (want: none).
      const passed = (jev) => {
        const t = drive(
          `const tryUrl = (p) => { try { return J.decisionsUrl(p); } catch (e) { return "THREW " + e.message; } };\n` +
            `const res = { ok: tryUrl() }; for (const [k, u] of Object.entries(${J(BAD)})) res[k] = tryUrl(u); out(res);`,
          { jev }
        );
        assert(t.json && t.json.ok === "https://openrouter.ai/api/alpha/decisions", `the default must be the decisions URL\n${t.stdout}${t.stderr}`);
        return Object.keys(BAD).filter((k) => !/^THREW .*may only call/.test(t.json[k]));
      };
      const open = passed(JEV);
      assert(!open.length, `${J(open)} must throw naming the only URL`);

      const q = reqFile({ ask: ASK });
      const moved = mutate([['const DECISIONS_PATH = "/api/alpha/decisions";', 'const DECISIONS_PATH = "/api/v1/chat/completions";']]);
      const s = drive(`out(await run(["intake", ${J(q)}]));`, { jev: moved });
      assert(s.json && s.json.code === 6 && s.json.calls === 0, `a moved path must stop before the transport (exit 6, 0 requests)\n${s.stdout}`);

      // KILL: the same moved path with the lock off reaches the transport with the wrong URL.
      const off = mutate([
        ['const DECISIONS_PATH = "/api/alpha/decisions";', 'const DECISIONS_PATH = "/api/v1/chat/completions";'],
        ["if (url !== DECISIONS) {", "if (false) {"],
      ]);
      const k = drive(`await run(["intake", ${J(q)}]); out({ urls: T.calls.map((c) => c.url) });`, { jev: off });
      assert(k.json && k.json.urls.length === 1 && /chat\/completions/.test(k.json.urls[0]), `the mutant must reach the transport, or J3 proves nothing\n${k.stdout}`);

      // KILLS: four looser locks, each let through by the case it loosens.
      for (const [name, check, want] of [
        ["also http", 'if (url !== DECISIONS && url !== DECISIONS.replace("https:", "http:")) {', "http"],
        ["origin + path only", "if (new URL(url).origin + new URL(url).pathname !== DECISIONS) {", "userinfo"],
        ["trailing dot ignored", 'if (url.replace("openrouter.ai./", "openrouter.ai/") !== DECISIONS) {', "trailingDot"],
        ["any port", 'if (((u) => ((u.port = ""), u.href))(new URL(url)) !== DECISIONS) {', "port"],
      ]) {
        const got = passed(mutate([["if (url !== DECISIONS) {", check]]));
        assert(got.includes(want), `the ${name} mutant must let ${want} through, or J3 proves nothing (${J(got)})`);
      }
    },
  },
  {
    id: "J4-jev-no-price-field-or-word-in-any-request",
    desc: "no request carries a price field or a price word (P14/P17): intake, worth on all 17 rows and on router options, cuts, and every catalogue line cuts can send; no test note reaches worth; a priced option name, a paid label starting \"Free\" and a price word in a key are refused before sending",
    fn() {
      const q = reqFile({ ask: ASK });
      const rows = PKG.rows.map((r) => [r.id, reqFile({ ask: ASK, row: r.id })]);
      const router = reqFile({
        ask: ASK,
        options: [
          { id: "trustpilot-reviews", name: "A business's Trustpilot reviews, each labelled with its sentiment and the issue it raises", route: "socialcrawl", endpoints: [{ call: "GET trustpilot/reviews", countLow: 1, countHigh: 1, role: "reviews" }], quote: { low: 25, high: 25 }, ceiling: 25 },
          { id: "free-topic-scout", name: "Free topic scout", route: "websearch" },
        ],
      });
      const priced = reqFile({ ask: ASK, options: [{ id: "scrape", name: "Scrape the page for 20 credits", route: "socialcrawl", endpoints: [{ call: "GET web/scrape", countLow: 1, countHigh: 1, role: "page" }] }] });
      // Only the free path's own name may lose a leading "Free"; a paid option's label never does.
      const freePaid = reqFile({ ask: ASK, options: [{ id: "tiktok-trending", name: "Free TikTok's trending videos feed", route: "socialcrawl", endpoints: [{ call: "GET tiktok/trending", countLow: 1, countHigh: 1, role: "feed" }] }] });
      // Every builder echoes its keys into an instruction, so the key check is read directly.
      const keyOnly = { model: "m", state: { description: "d", ask: "a", options: { paid: "An option" } }, questions: {} };
      const askOnly = { model: "m", state: { description: "d", ask: "is it free or paid, 5 credits?" }, questions: {} };
      const body =
        `const codes = {};\n` +
        `codes.intake = (await run(["intake", ${J(q)}])).code;\n` +
        `for (const [id, p] of ${J(rows)}) codes["worth " + id] = (await run(["worth", p])).code;\n` +
        `codes.router = (await run(["worth", ${J(router)}])).code;\n` +
        `codes.cuts = (await run(["cuts", ${J(q)}])).code;\n` +
        `const sent = T.calls.length;\n` +
        `const refused = await run(["worth", ${J(priced)}]);\n` +
        `const freeLabel = await run(["worth", ${J(freePaid)}]);\n` +
        `const check = (b) => { try { J.assertNoPriceWords(b); return "passed"; } catch (e) { return e.message; } };\n` +
        `const keyCheck = { keyOnly: check(${J(keyOnly)}), askOnly: check(${J(askOnly)}) };\n` +
        `const fs = await import("node:fs");\n` +
        `const costs = JSON.parse(fs.readFileSync(${J(join(HOOKS, "costs.json"))}, "utf8"));\n` +
        `const all = J.endpointsRequest(${J(ASK)}, costs, Object.keys(costs._platforms)).body;\n` +
        `out({ codes, sent, refused, freeLabel, keyCheck, bodies: T.calls.slice(0, sent).map((c) => c.body), all });`;
      const cfg = { noul: { platform_youtube: 0.9, platform_linkedin: 0.8, platform_tiktok: 0.7 } };
      const check = (jev) => {
        const r = drive(body, { jev, cfg });
        assert(r.json && r.json.codes, `driver failed\n${r.stdout}${r.stderr}`);
        return r.json;
      };
      const j = check(JEV);
      const bad = Object.entries(j.codes).filter(([, c]) => c !== 0);
      assert(!bad.length, `every request must succeed: ${J(bad)}`);
      // cuts = round 3 + youtube, linkedin, tiktok + reddit (named in ASK, outside the top 3; R13a) + aggregators
      assert(j.sent === 1 + PKG.rows.length + 1 + 6, `expected ${1 + PKG.rows.length + 1 + 6} requests, got ${j.sent}`);
      for (const b of [...j.bodies, j.all]) {
        const f = priceFieldHits(b);
        const t = priceTextHits(b);
        assert(!f.length && !t.length, `a price reached Jev: fields ${J(f)} text ${J(t.slice(0, 3))}`);
      }
      assert(Object.keys(j.all.state.endpoints).length === Object.keys(COSTS).filter((k) => !k.startsWith("_")).length, "the all-catalogue body must carry every endpoint");
      for (const b of j.bodies.filter((b) => b.state.options)) {
        const notes = texts(b).filter(([, t]) => TEST_NOTES.test(t));
        assert(!notes.length, `a test note reached a worth request: ${J(notes)}`);
      }
      // XR2-1: the router's free path "free-topic-scout" goes out as topic_scout in the key, the
      // question id and the instruction.
      const rb = j.bodies[1 + PKG.rows.length];
      assert(same(Object.keys(rb.state.options), ["trustpilot_reviews", "topic_scout"]) && same(Object.keys(rb.questions), ["worth_trustpilot_reviews", "worth_topic_scout"]) && rb.questions.worth_topic_scout.instructions === worthInstructions("topic_scout"), `the router's free id must lose its tier word\n${J(rb)}`);
      assert(j.refused.code === 6 && j.refused.calls === 0 && /price word/.test(j.refused.error), `a priced option name must be refused before sending\n${J(j.refused)}`);
      assert(j.freeLabel.code === 6 && j.freeLabel.calls === 0 && /price word/.test(j.freeLabel.error), `a paid label starting "Free" must be refused before sending\n${J(j.freeLabel)}`);
      assert(/state\.options\.paid/.test(j.keyCheck.keyOnly) && j.keyCheck.askOnly === "passed", `a price word in a key is refused; the ask is the person's own words\n${J(j.keyCheck)}`);

      // KILL 1: no text check. The priced name goes out.
      const k1 = check(mutate([["  assertNoPriceWords(body);\n", ""]]));
      assert(k1.refused.calls === 1, `the mutant must send the priced name, or J4 proves nothing\n${J(k1.refused)}`);
      // KILL 2: keep "Free" on the free path. Four rows' free paths are named "Free ...".
      const k2 = check(mutate([['text: legs.length ? label : label.replace(/^free\\s+/i, ""),', "text: label,"]]));
      assert(Object.values(k2.codes).some((c) => c !== 0), `the mutant must trip on "Free", or J4 proves nothing\n${J(k2.codes)}`);
      // KILL 3: keep every catalogue sentence. tiktok/hashtags/popular names its credits per hashtag.
      const k3 = check(mutate([[".filter((s) => s.trim() && !hasPriceWord(s))", ".filter((s) => s.trim())"]]));
      assert(priceTextHits(k3.all).length > 0, "the mutant must leak a catalogue price sentence, or J4 proves nothing");
      // KILL 4: drop a leading "Free" from every label. The paid "Free ..." label goes out.
      const k4 = check(mutate([['text: legs.length ? label : label.replace(/^free\\s+/i, ""),', 'text: label.replace(/^free\\s+/i, ""),']]));
      assert(k4.freeLabel.calls === 1, `the mutant must send the paid "Free" label, or J4 proves nothing\n${J(k4.freeLabel)}`);
      // KILL 5: no check on keys.
      const k5 = check(mutate([["if (PRICE_WORDS.test(k)) throw", "if (false) throw"]]));
      assert(k5.keyCheck.keyOnly === "passed", `the mutant must pass a price word in a key, or J4 proves nothing\n${J(k5.keyCheck)}`);
      // KILL 6, on this fixture's own oracle: round 2's shape (no id check, no free-path id drop)
      // sends free_topic_scout, and the oracle must see it; \b alone reads it as one word. Round 2
      // had no R13b value rule either, which now also catches the id inside the instruction.
      const k6 = check(mutate([
        ['if (PRICE_WORDS.test(id.replace(/_/g, " "))) throw', "if (false) throw"],
        ['jid: jevId(legs.length ? o.id : o.id.replace(/^free[^A-Za-z0-9]+/i, "") || o.id),', "jid: jevId(o.id),"],
        ['const hasPriceWord = (s) => PRICE_WORDS.test(s.replace(/_/g, " "));', "const hasPriceWord = (s) => PRICE_WORDS.test(s);"],
      ]));
      assert(priceTextHits(k6.bodies[1 + PKG.rows.length]).length > 0, `the oracle must flag free_topic_scout, or J4 proves nothing\n${J(k6.bodies[1 + PKG.rows.length].state.options)}`);
      // KILL 7: no billing words. search/multi's "at each platform's own price" goes out in the
      // merged aggregator request of every cuts run, and prism's "failed ... refunded" with it.
      const k7 = check(mutate([["|\\bown prices?\\b|\\brefund(?:s|ed)?\\b/i;", "/i;"]]));
      const bill = k7.bodies.slice(-5).flatMap((b) => priceTextHits(b).map(([w]) => w));
      assert(bill.includes("state.endpoints.get_search_multi") && bill.includes("state.endpoints.post_prism_post_stats"), `the mutant must send the aggregators' billing sentences in cuts, or J4 proves nothing\n${J(bill)}`);
    },
  },
  {
    id: "J5-jev-argv-is-mode-plus-path",
    desc: "argv is exactly <intake|cuts|worth> <request.json>; the ask is read from the file, never from argv; anything else exits 6 before a request",
    fn() {
      const q = reqFile({ ask: ASK });
      const ok = cli(["intake", q]);
      assert(ok.exit === 3, `a well-formed argv reaches the key check (no key here -> 3), got ${ok.exit}\n${ok.stderr}`);
      for (const argv of [["intake"], ["intake", q, "extra"], ["route", q], []]) {
        const r = cli(argv);
        assert(r.exit === 6 && /usage/.test(r.stderr), `argv ${J(argv)} must exit 6 with the usage line, got ${r.exit}\n${r.stderr}`);
      }
      const d = drive(
        `const onArgv = await run(["intake", ${J(ASK)}]);\n` +
          `const fromFile = await run(["intake", ${J(q)}]);\n` +
          `out({ onArgv, fromFile, ask: T.calls.map((c) => c.body.state.ask) });`
      );
      assert(d.json && d.json.onArgv.code === 6 && d.json.onArgv.calls === 0, `an ask on argv is not a file: exit 6, no request\n${d.stdout}`);
      assert(d.json.fromFile.code === 0 && same(d.json.ask, [ASK]), `the ask must come from the file\n${d.stdout}`);

      // KILL: accept extra arguments.
      const m = mutate([["if (!MODES.includes(mode) || !file || extra.length) throw", "if (!MODES.includes(mode) || !file) throw"]]);
      const k = cli(["intake", q, "extra"], { jev: m });
      assert(k.exit === 3, `the mutant must accept the extra argument, or J5 proves nothing (got ${k.exit})`);
    },
  },
  {
    id: "J6-jev-never-calls-process-exit",
    desc: "no `process.exit(` anywhere in jev.mjs (P2: fetch then a direct exit is rc 127 on Node 24 / Windows); it sets process.exitCode",
    fn() {
      const calls = (src) => (src.match(/process\.exit\(/g) || []).length;
      const src = readFileSync(JEV, "utf8");
      assert(calls(src) === 0, `jev.mjs calls process.exit( ${calls(src)} time(s)`);
      assert(/process\.exitCode = code;/.test(src), "jev.mjs must set process.exitCode");

      // KILL: the check must see a direct exit when one is there.
      assert(calls(src.replace("process.exitCode = code;", "process.exit(code);")) === 1, "the mutant must be caught, or J6 proves nothing");
    },
  },
  {
    id: "J7-jev-intake-request-is-step05-verbatim",
    desc: "one intake request: is_research + T2 v3's 5-way missing + the package Choice of the 16 jev rows + none_fit in Step 0.5's order, every sentence byte for byte; dev_radar is not offered",
    fn() {
      const q = reqFile({ ask: ASK });
      const r = drive(`const x = await run(["intake", ${J(q)}]); out({ x, bodies: T.calls.map((c) => c.body) });`);
      const j = r.json;
      assert(j && j.x.code === 0 && j.bodies.length === 1, `intake must make exactly one request\n${r.stdout}`);
      const b = j.bodies[0];
      assert(same(Object.keys(b.questions), ["is_research", "missing", "package"]), `questions ${J(Object.keys(b.questions))}`);
      assert(same(b.questions.is_research, { type: "noul", ...T2_IS_RESEARCH }), `is_research drifted\n${J(b.questions.is_research)}`);
      assert(same(b.questions.missing, { type: "choice", ...T2_MISSING }), `missing drifted\n${J(b.questions.missing)}`);
      const crit = b.questions.package.criteria;
      assert(same(Object.keys(crit), ORDER_17), `package options/order drifted: ${J(Object.keys(crit))}`);
      for (const [id, text] of Object.entries({ ...T2_ROUTE, ...NEW_ROWS, none_fit: NONE_FIT })) {
        assert(crit[id] === text, `${id} is not byte-identical\n  got:  ${J(crit[id])}\n  want: ${J(text)}`);
      }
      assert(!("dev_radar" in crit), "dev_radar is name-only (jev: false)");

      // KILL: offer every row, jev: false included.
      const m = mutate([["for (const r of pkg.rows) if (r.jev === true) criteria[r.id] = r.use_when;", "for (const r of pkg.rows) criteria[r.id] = r.use_when;"]]);
      const k = drive(`await run(["intake", ${J(q)}]); out({ keys: Object.keys(T.calls[0].body.questions.package.criteria) });`, { jev: m });
      assert(k.json && k.json.keys.includes("dev_radar"), `the mutant must offer dev_radar, or J7 proves nothing\n${k.stdout}`);
    },
  },
  {
    id: "J8-jev-state-description-instructions-and-model-verbatim",
    desc: "Step 0.5's state_description, route instructions, worth description, worth instruction template and four levels, byte for byte; the model is pinned to typesafe/jev-1.13-20260917",
    fn() {
      const q = reqFile({ ask: ASK });
      const w = reqFile({ ask: ASK, row: "trending" });
      const body = `await run(["intake", ${J(q)}]); await run(["worth", ${J(w)}]); out({ bodies: T.calls.map((c) => c.body) });`;
      const check = (jev) => {
        const r = drive(body, { jev });
        const [i, s] = (r.json && r.json.bodies) || [];
        const fails = [];
        if (!i || !s) return [`driver failed ${r.stdout}`];
        if (i.model !== MODEL_PIN || s.model !== MODEL_PIN) fails.push(`model ${i.model} / ${s.model}`);
        if (i.state.description !== T2_STATE) fails.push(`intake description ${J(i.state.description)}`);
        if (i.questions.package.instructions !== T2_ROUTE_INSTRUCTIONS) fails.push("route instructions");
        if (s.state.description !== WORTH_STATE) fails.push(`worth description ${J(s.state.description)}`);
        const ids = Object.keys(s.state.options);
        if (!same(Object.keys(s.questions), ids.map((id) => `worth_${id}`))) fails.push("one worth_<id> question per option");
        for (const id of ids) {
          const qq = s.questions[`worth_${id}`];
          if (!same(qq, { type: "score", instructions: worthInstructions(id), criteria: WORTH_LEVELS })) fails.push(`worth_${id} ${J(qq)}`);
        }
        return fails;
      };
      const f = check(JEV);
      assert(!f.length, `frozen text drifted: ${f.join(" | ")}`);

      // KILL: the moving alias instead of the dated pin; a description that lost its full stop; a reworded level.
      assert(check(mutate([['export const MODEL = "typesafe/jev-1.13-20260917";', 'export const MODEL = "typesafe/jev-1.13";']])).length, "the alias mutant must fail, or J8 proves nothing");
      assert(check(mutate([["social-media research tool.\";", "social-media research tool\";"]])).length, "the description mutant must fail, or J8 proves nothing");
      assert(check(mutate([['"It would answer most of it",', '"It would answer most of the ask",']])).length, "the level mutant must fail, or J8 proves nothing");
    },
  },
  {
    id: "J9-jev-ranking-six-cases",
    desc: "the ranking (Joe, P25): a free option within one level wins; level 1 never wins; nothing below level 2 is recommended; cheapest top price wins; ties go to fewer calls; no ceiling is never the cheap one — plus Step 0.5's two Score replies replayed",
    fn() {
      const o = (id, level, high, calls, score = level) => ({ id, level, score, quote: { low: 0, high }, calls });
      const CASES = [
        ["free-within-one-wins", [o("websearch", 2, 0, 0), o("a", 3, 20, 1)], "websearch", "a"],
        ["free-two-below-loses", [o("websearch", 1, 0, 0), o("a", 3, 20, 1), o("b", 2, 50, 2)], "a", "a"],
        ["level-1-never-wins", [o("websearch", 1, 0, 0), o("a", 2, 50, 1)], "a", "a"],
        ["nothing-at-level-2", [o("websearch", 1, 0, 0, 0.9), o("a", 1, 5, 1, 1.2), o("b", 0, 100, 1)], null, "a"],
        ["tie-goes-to-fewer-calls", [o("a", 3, 20, 4), o("b", 3, 20, 1)], "b", "a"],
        ["no-ceiling-never-cheapest", [o("a", 3, null, 1), o("b", 2, 500, 1)], "b", "a"],
      ].map(([name, items, rec, strong]) => ({ name, items: items.map((x, idx) => ({ ...x, idx })), rec, strong }));
      const trending = reqFile({ ask: "what's trending on TikTok in the fitness niche this week", row: "trending" });
      const people = reqFile({ ask: ASK, row: "people_saying" });
      // Step 0.5's live Score probabilities (step05-score-*-response.json), keyed to each row's ids.
      // campaign-tracker and crisis-radar were not in that smoke; they are given level 0 here.
      const tCfg = {
        score: {
          worth_websearch: { 0: 0.04, 1: 0.24, 2: 0.55, 3: 0.17 },
          worth_tiktok_trending: { 0: 0.01, 1: 0.42, 2: 0.48, 3: 0.09 },
          worth_tiktok_hashtags_popular: { 0: 0, 1: 0.03, 2: 0.42, 3: 0.55 },
          worth_instagram_reels_trending: { 0: 0.91, 1: 0.09, 2: 0, 3: 0 },
          worth_youtube_shorts_trending: { 0: 0.87, 1: 0.13, 2: 0, 3: 0 },
          worth_google_trends_trending_rising: { 0: 0.27, 1: 0.66, 2: 0.06, 3: 0.01 },
        },
      };
      const pCfg = {
        score: {
          worth_websearch: { 0: 0.06, 1: 0.78, 2: 0.13, 3: 0.03 },
          worth_search_forums: { 0: 0.01, 1: 0.95, 2: 0.04, 3: 0 },
          worth_search_everywhere: { 0: 0, 1: 0.01, 2: 0.22, 3: 0.77 },
          worth_voice_of_customer: { 0: 0.02, 1: 0.23, 2: 0.51, 3: 0.24 },
          worth_share_of_voice: { 0: 0.68, 1: 0.32, 2: 0, 3: 0 },
          worth_campaign_tracker: { 0: 1, 1: 0, 2: 0, 3: 0 },
          worth_crisis_radar: { 0: 1, 1: 0, 2: 0, 3: 0 },
        },
      };
      const body =
        `const ranked = ${J(CASES)}.map((c) => { const r = J.rank(c.items); return { name: c.name, rec: r.recommended, strong: r.strongest, order: r.order.map((x) => x.id) }; });\n` +
        `out({ ranked, t: (await run(["worth", ${J(trending)}])).result });`;
      const check = (jev) => {
        const r = drive(body, { jev, cfg: tCfg });
        assert(r.json && r.json.ranked, `driver failed\n${r.stdout}${r.stderr}`);
        return r.json;
      };
      const j = check(JEV);
      CASES.forEach((c, n) => {
        const got = j.ranked[n];
        assert(got.rec === c.rec && got.strong === c.strong, `${c.name}: recommended ${got.rec} (want ${c.rec}), strongest ${got.strong} (want ${c.strong})`);
        assert(got.order[0] === (c.rec ?? c.strong), `${c.name}: the menu leads with the recommendation, else the strongest: ${J(got.order)}`);
      });
      assert(j.t && j.t.recommended === "websearch" && j.t.strongest === "tiktok-hashtags-popular", `Step 0.5 trending replay: web search (level 2) over the hashtag board (level 3)\n${J(j.t)}`);
      const p = drive(`out((await run(["worth", ${J(people)}])).result);`, { cfg: pCfg }).json;
      assert(p && p.recommended === "search-everywhere" && p.strongest === "search-everywhere", `Step 0.5 people_saying replay\n${J(p)}`);

      // KILLS, one per clause. The ">= max - 1" clause has no killing mutant on a 0-3 scale: with
      // ">= 2" beside it, it can never bind (max 3 gives 2; max 2 gives 1). Stated, not tested.
      const kill = (name, pairs, caseName) => {
        const k = check(mutate(pairs));
        const n = CASES.findIndex((c) => c.name === caseName);
        assert(k.ranked[n].rec !== CASES[n].rec, `${name}: the mutant must change ${caseName}, or J9 proves nothing`);
      };
      kill(">= 2", [["f.level >= top - 1 && f.level >= 2", "f.level >= top - 1"]], "level-1-never-wins");
      kill("cheapest", [["const cheaper = (a, b) => cost(a) - cost(b) ||", "const cheaper = (a, b) => cost(b) - cost(a) ||"]], "free-within-one-wins");
      kill("fewer calls", [["cost(a) - cost(b) || a.calls - b.calls || a.idx - b.idx", "cost(a) - cost(b) || a.idx - b.idx"]], "tie-goes-to-fewer-calls");
      kill("null is dearest", [["(f.quote.high === null ? Infinity : f.quote.high)", "(f.quote.high === null ? 0 : f.quote.high)"]], "no-ceiling-never-cheapest");
    },
  },
  {
    id: "J10-jev-between-level-score-ranks-by-argmax",
    desc: "a Score of 1.99 is level 2 (argmax, P17), not level 1; a bimodal 1.45 is level 2, not a rounded 1; a two-way tie keeps the lower level",
    fn() {
      const w = reqFile({
        ask: ASK,
        options: [
          { id: "opt-a", name: "TikTok's trending videos feed", route: "socialcrawl", endpoints: [{ call: "GET tiktok/trending", countLow: 1, countHigh: 1, role: "feed" }] },
          { id: "opt-b", name: "Web search", route: "websearch" },
          { id: "opt-c", name: "YouTube's trending shorts", route: "socialcrawl", endpoints: [{ call: "GET youtube/shorts/trending", countLow: 1, countHigh: 1, role: "shorts" }] },
        ],
      });
      const cfg = {
        score: { worth_opt_a: { 0: 0, 1: 0.01, 2: 0.99, 3: 0 }, worth_opt_b: { 0: 0.3, 1: 0.1, 2: 0.45, 3: 0.15 }, worth_opt_c: { 0: 0.05, 1: 0.45, 2: 0.45, 3: 0.05 } },
        scoreValue: { worth_opt_a: 1.99, worth_opt_b: 1.45, worth_opt_c: 1.5 },
      };
      const check = (jev) => {
        const r = drive(`out((await run(["worth", ${J(w)}])).result);`, { jev, cfg });
        const res = r.json || {};
        const lv = Object.fromEntries((res.options || []).map((x) => [x.id, x.level]));
        return { lv, rec: res.recommended, strong: res.strongest, raw: r.stdout };
      };
      const j = check(JEV);
      assert(j.lv["opt-a"] === 2 && j.lv["opt-b"] === 2 && j.lv["opt-c"] === 1, `levels ${J(j.lv)}\n${j.raw}`);
      assert(j.rec === "opt-b" && j.strong === "opt-a", `recommended ${j.rec} (want opt-b), strongest ${j.strong} (want opt-a)\n${j.raw}`);

      // KILLS: floor the score, round the score, let a tie take the higher level.
      const floor = check(mutate([["  return best;\n}", "  return Math.floor(answer.score);\n}"]]));
      assert(floor.lv["opt-a"] === 1, `the floor mutant must read 1.99 as 1, or J10 proves nothing ${J(floor.lv)}`);
      const round = check(mutate([["  return best;\n}", "  return Math.round(answer.score);\n}"]]));
      assert(round.lv["opt-b"] === 1, `the round mutant must read 1.45 as 1, or J10 proves nothing ${J(round.lv)}`);
      const tie = check(mutate([["if (p[String(l)] > p[String(best)]) best = l;", "if (p[String(l)] >= p[String(best)]) best = l;"]]));
      assert(tie.lv["opt-c"] === 2, `the tie mutant must lift opt-c to 2, or J10 proves nothing ${J(tie.lv)}`);
    },
  },
  {
    id: "J11-jev-worth-prices-equal-price-mjs",
    desc: "every worth price is code's: an uncurated option = price.mjs quote(endpoints), a curated one = its own row's reviewed quote, the free path 0; a router option's stated quote is ignored; worth is one request",
    fn() {
      const rows = PKG.rows.map((r) => [r.id, reqFile({ ask: ASK, row: r.id })]);
      const routerOpts = [
        { id: "trustpilot-reviews", name: "A business's Trustpilot reviews, each labelled with its sentiment and the issue it raises", route: "socialcrawl", endpoints: [{ call: "GET trustpilot/reviews", countLow: 1, countHigh: 2, role: "reviews" }], quote: { low: 1, high: 2 }, ceiling: 2 },
        { id: "share-of-voice", name: "Share of voice (2-5 brands)", route: "socialcrawl", endpoints: [{ call: "GET prism/share-of-voice", countLow: 1, countHigh: 1, role: "sov" }] },
        { id: "free-topic-scout", name: "Free topic scout", route: "websearch" },
      ];
      const router = reqFile({ ask: ASK, options: routerOpts });
      const body =
        `const res = {};\n` +
        `for (const [id, p] of ${J(rows)}) { const x = await run(["worth", p]); res[id] = { code: x.code, calls: x.calls, options: x.result && x.result.options }; }\n` +
        `const x = await run(["worth", ${J(router)}]); res.router = { code: x.code, calls: x.calls, options: x.result && x.result.options };\n` +
        `out(res);`;
      const expected = (o) => {
        const cur = CURATED.get(o.curated ?? o.id);
        if (cur) return { low: cur.quote.low, high: cur.quote.high };
        return quote(o.endpoints || [], COSTS);
      };
      const check = (jev) => {
        const r = drive(body, { jev });
        assert(r.json && r.json.router, `driver failed\n${r.stdout}${r.stderr}`);
        const fails = [];
        let n = 0;
        for (const row of PKG.rows) {
          const got = r.json[row.id];
          if (got.code !== 0 || got.calls !== 1) { fails.push(`${row.id}: exit ${got.code}, ${got.calls} request(s)`); continue; }
          const want = [...(row.free ? [{ id: "websearch", curated: row.free.curated, endpoints: [] }] : []), ...row.options];
          for (const o of want) {
            const g = got.options.find((x) => x.id === o.id);
            n++;
            if (!g || !same(g.quote, expected(o))) fails.push(`${row.id}/${o.id}: ${J(g && g.quote)} vs ${J(expected(o))}`);
          }
        }
        const ro = r.json.router.options || [];
        const byId = Object.fromEntries(ro.map((x) => [x.id, x.quote]));
        if (!same(byId["trustpilot-reviews"], quote(routerOpts[0].endpoints, COSTS))) fails.push(`router trustpilot-reviews ${J(byId["trustpilot-reviews"])}`);
        if (!same(byId["share-of-voice"], { low: 80, high: 200 })) fails.push(`router share-of-voice ${J(byId["share-of-voice"])}`);
        if (!same(byId["free-topic-scout"], { low: 0, high: 0 })) fails.push(`router free-topic-scout ${J(byId["free-topic-scout"])}`);
        return { fails, n };
      };
      const j = check(JEV);
      assert(!j.fails.length, `worth prices differ from price.mjs:\n  ${j.fails.join("\n  ")}`);
      assert(j.n === PKG.rows.reduce((s, r) => s + r.options.length + (r.free ? 1 : 0), 0), `every option on every row priced (${j.n})`);

      // KILL 1: price curated rows from their legs (share-of-voice / voice-of-customer are hand-reviewed).
      assert(check(mutate([["const q = cur ? { low: cur.quote.low, high: cur.quote.high } : quote(legs, costs);", "const q = quote(legs, costs);"]])).fails.length, "the legs-for-curated mutant must fail, or J11 proves nothing");
      // KILL 2: trust a router option's own quote.
      assert(check(mutate([[": quote(legs, costs);", ": o.quote || quote(legs, costs);"]])).fails.length, "the trust-the-router mutant must fail, or J11 proves nothing");
    },
  },
  {
    id: "J12-jev-candidate-log-holds-no-ask-text",
    desc: "cuts appends one line to <revxl>/jev-candidates.jsonl (folder created if missing): {ts, ask_sha256, survivors} — the ask's hash, never its text (P25)",
    fn() {
      const ask = "zqxmarker what's trending on TikTok in the fitness niche this week";
      const q = reqFile({ ask });
      const cfg = { noul: { platform_tiktok: 0.9, endpoint_get_tiktok_trending: 0.9 } };
      const body =
        `const revxl = DIR + "/not-yet/revxl";\n` +
        `const x = await run(["cuts", ${J(q)}], { env: { OPENROUTER_API_KEY: FAKE, SC_REVXL_HOME: revxl } });\n` +
        `const fs = await import("node:fs");\n` +
        `out({ x, log: fs.readFileSync(revxl + "/jev-candidates.jsonl", "utf8") });`;
      const check = (jev) => drive(body, { jev, cfg }).json;
      const j = check(JEV);
      assert(j && j.x && j.x.code === 0, `cuts must succeed\n${J(j)}`);
      const lines = j.log.split("\n").filter(Boolean);
      assert(lines.length === 1, `one line per cuts run, got ${lines.length}`);
      const line = JSON.parse(lines[0]);
      assert(same(Object.keys(line), ["ts", "ask_sha256", "survivors"]), `line keys ${J(Object.keys(line))}`);
      assert(line.ask_sha256 === createHash("sha256").update(ask, "utf8").digest("hex"), "the hash must be sha256 of the ask");
      assert(same(line.survivors, j.x.result.survivors) && line.survivors.includes("GET tiktok/trending"), `survivors ${J(line.survivors)}`);
      assert(!lines[0].includes("zqxmarker") && !lines[0].includes("fitness"), `the ask text leaked: ${lines[0]}`);

      // KILL: log the ask itself.
      const k = check(mutate([["JSON.stringify({ ts: new Date().toISOString(), ask_sha256, survivors })", "JSON.stringify({ ts: new Date().toISOString(), ask_sha256, ask, survivors })"]]));
      assert(k && /zqxmarker/.test(k.log), `the mutant must leak the ask, or J12 proves nothing\n${J(k)}`);
    },
  },
  {
    id: "J13-jev-intake-evaluation-order-and-lines",
    desc: "Step 0.5's order and lines on its own observed answers: is_research < 0.5 or not_research leaves, first; any missing_* asks, before the package, with no confidence line; none_fit when chosen (at any p) or p >= 0.20; else the package row, with no confidence line",
    fn() {
      const q = reqFile({ ask: ASK });
      const pick = (isr, miss, pkg, pNone, x = {}) => ({
        noul: { is_research: isr },
        choice: { missing: miss, package: pkg },
        probs: { package: Object.fromEntries(ORDER_17.map((k) => [k, k === "none_fit" ? pNone : k === pkg ? 1 - pNone : 0])), ...x.probs },
        confidence: x.confidence,
      });
      const pkgProbs = (p) => ({ ...Object.fromEntries(ORDER_17.map((k) => [k, 0])), ...p });
      // Step 0.5's N1 answer on missing, verbatim: missing_platform picked at confidence 0.44.
      const N1_MISSING = { not_research: 0, missing_topic: 0, nothing_missing: 0.44, missing_target: 0, missing_platform: 0.56 };
      const CASES = [
        ["#15 book a flight (p none_fit 0.42)", pick(0.02, "not_research", "free_web", 0.42), { next: "not_research" }],
        ["C express-lane call", pick(0.13, "not_research", "who_is", 0.02), { next: "not_research" }],
        ["is_research 0.49, nothing missing", pick(0.49, "nothing_missing", "trending", 0), { next: "not_research" }],
        ["#6 unnamed competitor", pick(0.98, "missing_target", "who_is", 0.1), { next: "missing", missing: "missing_target" }],
        ["missing beats none_fit", pick(0.95, "missing_platform", "none_fit", 0.6), { next: "missing", missing: "missing_platform" }],
        ["F5 who_is at p none_fit 0.25", pick(0.97, "nothing_missing", "who_is", 0.25), { next: "none_fit" }],
        ["F3 none_fit chosen", pick(0.78, "nothing_missing", "none_fit", 0.67), { next: "none_fit" }],
        ["p none_fit exactly 0.20", pick(0.9, "nothing_missing", "website", 0.2), { next: "none_fit" }],
        ["p none_fit 0.19", pick(0.9, "nothing_missing", "free_web", 0.19), { next: "package", row: "free_web" }],
        ["#1 Peloton", pick(0.98, "nothing_missing", "people_saying", 0), { next: "package", row: "people_saying" }],
        ["is_research exactly 0.50", pick(0.5, "nothing_missing", "trending", 0), { next: "package", row: "trending" }],
        ["is_research 0.30 with missing_target", pick(0.3, "missing_target", "who_is", 0), { next: "not_research" }],
        ["N1 missing_platform at confidence 0.44", pick(0.98, "missing_platform", "competitor_offer", 0, { probs: { missing: N1_MISSING }, confidence: { missing: 0.44 } }), { next: "missing", missing: "missing_platform" }],
        ["none_fit chosen at p 0.15", pick(0.9, "nothing_missing", "none_fit", 0.15, { probs: { package: Object.fromEntries(ORDER_17.map((k) => [k, k === "none_fit" ? 0.15 : 0.053125])) } }), { next: "none_fit" }],
        ["website at confidence 0.38, p none_fit 0.10", pick(0.94, "nothing_missing", "website", 0.1, { probs: { package: pkgProbs({ website: 0.38, reviews_reputation: 0.3, answer_with_sources: 0.22, none_fit: 0.1 }) }, confidence: { package: 0.38 } }), { next: "package", row: "website" }],
        ["is_research 0.90 with not_research", pick(0.9, "not_research", "trending", 0), { next: "not_research" }],
      ];
      const run = (jev) => {
        const r = drive(`const res = []; for (let n = 0; n < ${CASES.length}; n++) res.push((await run(["intake", ${J(q)}])).result); out(res);`, { jev, cfg: { seq: CASES.map((c) => c[1]) } });
        assert(Array.isArray(r.json), `driver failed\n${r.stdout}${r.stderr}`);
        return CASES.map(([name], n) => ({ name, got: r.json[n] }));
      };
      const res = run(JEV);
      CASES.forEach(([name, , want], n) => {
        const g = res[n].got || {};
        const ok = g.next === want.next && (g.row ?? null) === (want.row ?? null) && (g.missing ?? null) === (want.missing ?? null);
        assert(ok, `${name}: got ${J(g)}, want ${J(want)}`);
      });
      const at = (r, name) => r.find((x) => x.name === name).got || {};

      // KILLS: package before missing; ">" for ">="; no is_research line.
      const order = run(mutate([
        ['  if (miss !== "nothing_missing") return { ...v, next: "missing", missing: miss };\n  if (pick === "none_fit" || pNone >= NONE_FIT_LINE) return { ...v, next: "none_fit" };',
          '  if (pick === "none_fit" || pNone >= NONE_FIT_LINE) return { ...v, next: "none_fit" };\n  if (miss !== "nothing_missing") return { ...v, next: "missing", missing: miss };'],
      ]));
      assert(at(order, "missing beats none_fit").next === "none_fit", "the order mutant must change a case, or J13 proves nothing");
      const gt = run(mutate([["pNone >= NONE_FIT_LINE", "pNone > NONE_FIT_LINE"]]));
      assert(at(gt, "p none_fit exactly 0.20").next === "package", "the > mutant must change the 0.20 case, or J13 proves nothing");
      const noLine = run(mutate([['if (isr < IS_RESEARCH_LINE || miss === "not_research")', 'if (miss === "not_research")']]));
      assert(at(noLine, "is_research 0.49, nothing missing").next !== "not_research", "the no-line mutant must change the 0.49 case, or J13 proves nothing");

      // KILLS: "<=" at 0.5; missing_* before not-research; a confidence line on missing or on the
      // package; a none_fit pick ignored below 0.20. Each must move the case that names it.
      const moved = (name, pairs, caseName) => {
        const g = at(run(mutate(pairs)), caseName);
        const w = CASES.find((c) => c[0] === caseName)[2];
        assert(g.next !== w.next || (g.row ?? null) !== (w.row ?? null), `the ${name} mutant must change "${caseName}", or J13 proves nothing`);
      };
      moved("<= 0.5", [["isr < IS_RESEARCH_LINE", "isr <= IS_RESEARCH_LINE"]], "is_research exactly 0.50");
      moved("missing-first", [['  if (isr < IS_RESEARCH_LINE || miss === "not_research")', '  if (miss.startsWith("missing_")) return { ...v, next: "missing", missing: miss };\n  if (isr < IS_RESEARCH_LINE || miss === "not_research")']], "is_research 0.30 with missing_target");
      moved("missing-confidence", [['if (miss !== "nothing_missing") return', 'if (miss !== "nothing_missing" && answers.missing.confidence >= 0.5) return']], "N1 missing_platform at confidence 0.44");
      moved("package-confidence", [["  return { ...v, row: pick };", '  if (answers.package.confidence < 0.5) return { ...v, next: "none_fit" };\n  return { ...v, row: pick };']], "website at confidence 0.38, p none_fit 0.10");
      moved("none_fit-pick-ignored", [['if (pick === "none_fit" || pNone >= NONE_FIT_LINE)', "if (pNone >= NONE_FIT_LINE)"]], "none_fit chosen at p 0.15");
      moved("not_research-ignored", [['if (isr < IS_RESEARCH_LINE || miss === "not_research")', "if (isr < IS_RESEARCH_LINE)"]], "is_research 0.90 with not_research");
    },
  },
  {
    id: "J14-jev-cuts-shape-and-request-counts",
    desc: "cuts: round 3 = one request of Nouls over the single-platform namespaces only; round 4 = the top 3 platforms one request each + ONE merged request of every aggregator endpoint; catalogue price sentences dropped; 5 requests when the ask names no platform outside the top 3 (a named one always advances, R13a: J18)",
    fn() {
      const q = reqFile({ ask: "what's trending on TikTok in the fitness niche this week" });
      const AGG = ["prism", "search", "web", "tavily", "perplexity", "content_analysis"];
      const P = COSTS._platforms;
      const ns = (k) => k.slice(k.indexOf(" ") + 1).split("/")[0];
      const eps = (names) => Object.keys(COSTS).filter((k) => !k.startsWith("_") && names.includes(ns(k)));
      const eid = (k) => k.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
      const cfg = {
        noul: {
          platform_tiktok: 0.9, platform_instagram: 0.8, platform_youtube: 0.7, platform_google_trends: 0.6,
          endpoint_get_tiktok_hashtags_popular: 0.95, endpoint_get_search_everywhere: 0.7,
        },
      };
      const body = `const x = await run(["cuts", ${J(q)}]); out({ x, bodies: T.calls.map((c) => c.body) });`;
      const check = (jev, c = cfg) => {
        const r = drive(body, { jev, cfg: c });
        assert(r.json && r.json.x, `driver failed\n${r.stdout}${r.stderr}`);
        return r.json;
      };
      const j = check(JEV);
      const [r3, ...r4] = j.bodies;
      const singles = Object.keys(P).filter((p) => !AGG.includes(p));
      assert(j.x.code === 0 && j.bodies.length === 5 && j.x.result.calls === 5, `3 platforms + aggregators = 5 requests, got ${j.bodies.length}`);
      assert(same(Object.keys(r3.questions), singles.map((p) => `platform_${p}`)), "round 3 asks about every single platform and no aggregator");
      assert(same(r3.state.platforms, Object.fromEntries(singles.map((p) => [p, P[p].category]))), "round 3 state = name + category");
      assert(same(j.x.result.platforms, ["tiktok", "instagram", "youtube"]), `top 3 by p above the line: ${J(j.x.result.platforms)}`);
      const want4 = [["tiktok"], ["instagram"], ["youtube"], AGG];
      want4.forEach((names, n) => {
        assert(same(Object.keys(r4[n].questions), eps(names).map((k) => `endpoint_${eid(k)}`)), `round 4 request ${n + 1} must be ${names.join("+")}'s endpoints`);
      });
      const hashtags = r4[0].state.endpoints.get_tiktok_hashtags_popular;
      assert(hashtags === "Read TikTok's own trending-hashtag board for a market and time window: the overall board plus 15 industry boards.", `the credits sentence must be dropped: ${J(hashtags)}`);
      assert(same(j.x.result.survivors, ["GET tiktok/hashtags/popular", "GET search/everywhere"]), `survivors ${J(j.x.result.survivors)}`);
      // No platform above the line: round 3 + TikTok (the ask names it, R13a) + the aggregator request.
      const none = check(JEV, { noulDefault: 0.1 });
      assert(none.bodies.length === 3 && same(none.x.result.platforms, ["tiktok"]), `no platform above the line: round 3 + the named tiktok + the aggregator request, got ${none.bodies.length} ${J(none.x.result.platforms)}`);

      // KILLS: aggregators judged in round 3; a fourth platform; the aggregators split apart.
      const k1 = check(mutate([["const singles = Object.keys(P).filter((p) => !AGGREGATORS.includes(p));", "const singles = Object.keys(P);"]]));
      assert(Object.keys(k1.bodies[0].questions).includes("platform_prism"), "the round-3 mutant must ask about prism, or J14 proves nothing");
      const k2 = check(mutate([["export const TOP_PLATFORMS = 3;", "export const TOP_PLATFORMS = 4;"]]));
      assert(k2.bodies.length === 6, `the top-4 mutant must send 6 requests, or J14 proves nothing (${k2.bodies.length})`);
      const k3 = check(mutate([["[...kept.map((p) => [p]), AGGREGATORS]", "[...kept.map((p) => [p]), ...AGGREGATORS.map((a) => [a])]"]]));
      assert(k3.bodies.length === 10, `the split-aggregator mutant must send 10 requests, or J14 proves nothing (${k3.bodies.length})`);
    },
  },
  {
    id: "J15-jev-key-never-reaches-an-error",
    desc: "a key with a line break, CR or NUL inside it (a note under the key, two keys, a stray byte; file or env) exits 6 before the transport, and its message holds no key; a transport error that quotes the key prints with the key cut out",
    fn() {
      const q = reqFile({ ask: ASK });
      const leaks = (s) => /FAKE-000/.test(String(s));
      const mask = (s) => String(s).replace(/FAKE-000\d/g, "<FAKE>");
      const NAMES = ["note", "twoKeys", "nul", "envLF"];
      const body =
        `const fs = await import("node:fs");\n` +
        `const files = { note: FAKE + "\\n# my openrouter key", twoKeys: FAKE + "\\r\\n" + FAKE.replace("0000", "0001"), nul: FAKE + "\\u0000tail" };\n` +
        `const res = {};\n` +
        `for (const [name, text] of Object.entries(files)) {\n` +
        `  const h = DIR + "/" + name;\n` +
        `  fs.mkdirSync(h + "/.config/openrouter", { recursive: true });\n` +
        `  fs.writeFileSync(h + "/.config/openrouter/api_key", text + "\\n");\n` +
        `  res[name] = await run(["intake", ${J(q)}], { env: {}, home: h });\n` +
        `}\n` +
        `res.envLF = await run(["intake", ${J(q)}], { env: { OPENROUTER_API_KEY: FAKE + "\\nsecond-line" }, home: DIR });\n` +
        `out(res);`;
      const r = drive(body);
      assert(r.json && r.json.envLF, `driver failed\n${mask(r.stdout)}${mask(r.stderr)}`);
      for (const k of NAMES) {
        const x = r.json[k];
        assert(x.code === 6 && x.calls === 0 && x.result === null, `${k}: a malformed key must exit 6 before the transport, got exit ${x.code} after ${x.calls} request(s)`);
        assert(/line break or control character/.test(x.error) && !leaks(x.error), `${k}: one plain line, no key: ${mask(x.error)}`);
      }

      // The CLI itself: its stderr is what the front door's Bash tool_result shows.
      const home = tmp();
      mkdirSync(join(home, ".config", "openrouter"), { recursive: true });
      writeFileSync(join(home, ".config", "openrouter", "api_key"), FAKE_KEY + "\n# my openrouter key\n");
      const c = spawnSync(process.execPath, [JEV, "intake", q], { encoding: "utf8", input: "", env: scrubbed(home) });
      assert(c.status === 6 && c.stdout === "" && /line break/.test(c.stderr) && !leaks(c.stderr), `CLI with a two-line key file: exit 6, stdout empty, no key on stderr (exit ${c.status}: ${mask(c.stderr)})`);

      // A transport error that quotes the key (fetch's header error does): the key is cut out.
      const t = drive(`out(await run(["intake", ${J(q)}]));`, { cfg: { throws: "key" } });
      assert(t.json && t.json.code === 6 && t.json.calls === 1 && /<key>/.test(t.json.error) && !leaks(t.json.error), `a transport error quoting the key must print without it: ${mask(t.stdout)}`);

      // KILL 1: no control-character check. Each malformed key reaches the transport, where undici's
      // own header check throws and quotes it; the message still prints with the key cut out.
      const a = drive(body, { jev: mutate([["if (key && CONTROL.test(key)) {", "if (false) {"]]), cfg: { request: true } });
      for (const k of NAMES) {
        const x = a.json && a.json[k];
        assert(x && x.calls === 1, `${k}: the mutant must reach the transport, or J15 proves nothing`);
        assert(x.code === 6 && /invalid header value/.test(x.error) && /<key>/.test(x.error) && !leaks(x.error), `${k}: undici's header error must print with the key cut out: ${mask(x.error)}`);
      }
      // KILL 2: no redaction. The quoted key reaches stderr.
      const b = drive(`out(await run(["intake", ${J(q)}]));`, { jev: mutate([['.split(key).join("<key>")', ""]]), cfg: { throws: "key" } });
      assert(b.json && leaks(b.json.error), "the mutant must print the key, or J15 proves nothing");
    },
  },
  {
    id: "J16-jev-price-words-in-option-ids-and-the-session-cap",
    desc: "XR2-1: an option id is checked with \"_\" read as a space, so a price word joined into an id (free_tiktok_trending, trending_paid_feed) is refused before sending; only the free path's id loses a leading \"free\" (free-topic-scout goes as topic_scout in the key, the question id and the instruction, and its answer is read back under that id); P17: \"capped by the session cap\", \"session cap\" and \"capped\" are price words",
    fn() {
      const leg = (call) => [{ call, countLow: 1, countHigh: 1, role: "fixture leg" }];
      const one = (o) => reqFile({ ask: ASK, options: [o] });
      const REQ = {
        freeId: one({ id: "free-tiktok-trending", name: "TikTok's trending videos feed", route: "socialcrawl", endpoints: leg("GET tiktok/trending") }),
        midId: one({ id: "trending_paid_feed", name: "TikTok's trending videos feed", route: "socialcrawl", endpoints: leg("GET tiktok/trending") }),
        capLabel: one({ id: "web-scrape", name: "One web page, capped by the session cap", route: "socialcrawl", endpoints: leg("GET web/scrape") }),
        freePath: one({ id: "free-topic-scout", name: "Free topic scout", route: "websearch" }),
      };
      const LONE = { sessionCap: "Every page, up to the session cap", capped: "Pages are capped at ten" };
      const body =
        `const res = {};\n` +
        `for (const [k, p] of Object.entries(${J(REQ)})) { const n = T.calls.length; res[k] = await run(["worth", p]); res[k].bodies = T.calls.slice(n).map((c) => c.body); }\n` +
        `const check = (b) => { try { J.assertNoPriceWords(b); return "passed"; } catch (e) { return e.message; } };\n` +
        `res.lone = Object.fromEntries(Object.entries(${J(LONE)}).map(([k, t]) => [k, check({ state: { ask: "a", options: { a: t } } })]));\n` +
        `out(res);`;
      const check = (jev) => {
        const r = drive(body, { jev });
        assert(r.json && r.json.lone, `driver failed\n${r.stdout}${r.stderr}`);
        return r.json;
      };
      const j = check(JEV);
      for (const [k, id] of [["freeId", "free_tiktok_trending"], ["midId", "trending_paid_feed"]]) {
        const x = j[k];
        assert(x.code === 6 && x.calls === 0 && x.error.includes(`price word reached a Jev request in the option id ${id}`), `${k}: a price word joined into an id must be refused before sending\n${J(x)}`);
      }
      assert(j.capLabel.code === 6 && j.capLabel.calls === 0 && /price word/.test(j.capLabel.error), `"capped by the session cap" must be refused before sending\n${J(j.capLabel)}`);
      for (const k of Object.keys(LONE)) assert(/price word/.test(j.lone[k]), `${k}: ${J(LONE[k])} is a price word\n${J(j.lone)}`);
      const fp = j.freePath;
      const sent = fp.bodies[0];
      assert(fp.code === 0 && fp.calls === 1 && fp.result.options[0].id === "free-topic-scout", `the free path runs and the menu keeps the caller's id\n${J(fp)}`);
      assert(same(sent.state.options, { topic_scout: "topic scout" }) && same(Object.keys(sent.questions), ["worth_topic_scout"]) && sent.questions.worth_topic_scout.instructions === worthInstructions("topic_scout"), `free-topic-scout must go as topic_scout\n${J(sent)}`);
      assert(!priceTextHits(sent).length, `a price word reached the free path's request: ${J(priceTextHits(sent))}`);

      // KILLS: no id check; the id check blind to "_" (round 2's shape); no free-path id drop; the
      // drop on every id; the answer read under the raw id; "session cap" / "capped" / both unlisted.
      const ID_CHECK = 'PRICE_WORDS.test(id.replace(/_/g, " "))';
      const ID_DROP = 'jid: jevId(legs.length ? o.id : o.id.replace(/^free[^A-Za-z0-9]+/i, "") || o.id),';
      const CAP = "|\\bsession cap\\b|\\bcapped\\b|";
      // R13b's value rule reads "_" as a space in the instruction too, which carries the id, so
      // the two id mutants also put the values back on the raw regex (round 2 had neither).
      const RAW = ['const hasPriceWord = (s) => PRICE_WORDS.test(s.replace(/_/g, " "));', "const hasPriceWord = (s) => PRICE_WORDS.test(s);"];
      assert(check(mutate([[ID_CHECK, "false"], RAW])).freeId.calls === 1, "the no-id-check mutant must send free_tiktok_trending, or J16 proves nothing");
      const blind = check(mutate([[ID_CHECK, "PRICE_WORDS.test(id)"], RAW]));
      assert(blind.freeId.calls === 1 && blind.midId.calls === 1, "the \\b-only mutant must send both joined ids, or J16 proves nothing");
      assert(check(mutate([[ID_DROP, "jid: jevId(o.id),"]])).freePath.code === 6, "the no-drop mutant must refuse the free path, or J16 proves nothing");
      assert(check(mutate([[ID_DROP, 'jid: jevId(o.id.replace(/^free[^A-Za-z0-9]+/i, "") || o.id),']])).freeId.calls === 1, "the drop-on-every-id mutant must send the paid option, or J16 proves nothing");
      assert(check(mutate([["answers[`worth_${f.jid}`]", "answers[`worth_${jevId(f.id)}`]"]])).freePath.code === 6, "the raw-id-lookup mutant must lose the free path's answer, or J16 proves nothing");
      assert(check(mutate([[CAP, "|\\bcapped\\b|"]])).lone.sessionCap === "passed", "the no-session-cap mutant must pass \"up to the session cap\", or J16 proves nothing");
      assert(check(mutate([[CAP, "|\\bsession cap\\b|"]])).lone.capped === "passed", "the no-capped mutant must pass \"capped at ten\", or J16 proves nothing");
      assert(check(mutate([[CAP, "|"]])).capLabel.calls === 1, "the mutant with neither must send the session-cap label, or J16 proves nothing");
    },
  },
  {
    id: "J17-jev-ranking-margin-level-3-within-5",
    desc: "the lane L margin (Joe 09.25.26): a level-2 pick gives way to the cheapest level-3 option whose quote.high is at most 5 credits above it — competitor_offer's site-teardown (L2, high 5) flips to link-in-bio-recon (L3, high 7), replayed end to end; 20 vs 1050 does not; a free level-2 pick flips to a level-3 at exactly 5 and not at 6; a level-3 with no ceiling never does; the J9 tie case is unchanged",
    fn() {
      const o = (id, level, high, calls, score = level) => ({ id, level, score, quote: { low: 0, high }, calls });
      const CASES = [
        ["lane-competitor-offer", [o("site-teardown", 2, 5, 5), o("link-in-bio-recon", 3, 7, 3), o("websearch", 1, 0, 0)], "link-in-bio-recon"],
        ["20-vs-1050-holds", [o("search-forums", 2, 20, 2), o("voice-of-customer", 3, 1050, 7)], "search-forums"],
        ["free-l2-vs-l3-at-5-flips", [o("websearch", 2, 0, 0), o("a", 3, 5, 1)], "a"],
        ["free-l2-vs-l3-at-6-holds", [o("websearch", 2, 0, 0), o("a", 3, 6, 1)], "websearch"],
        ["cheapest-l3-within", [o("p", 2, 5, 1), o("x", 3, 10, 1), o("y", 3, 7, 1)], "y"],
        ["no-ceiling-l3-never-within", [o("b", 2, 500, 1), o("a", 3, null, 1)], "b"],
        ["tie-unchanged", [o("a", 3, 20, 4), o("b", 3, 20, 1)], "b"],
      ].map(([name, items, rec]) => ({ name, items: items.map((x, idx) => ({ ...x, idx })), rec }));
      // Lane L's competitor_offer ask and row (output/data/jev-lane-l-09.25.26/worth-competitor_offer.json),
      // replayed with the levels the lane measured: site-teardown 2, link-in-bio-recon 3, the free sketch 1.
      const lane = reqFile({ ask: "what does my competitor sell through the link in their Instagram bio, and how are their offers laid out", row: "competitor_offer" });
      const cfg = { score: { worth_site_teardown: { 0: 0, 1: 0, 2: 1, 3: 0 }, worth_link_in_bio_recon: { 0: 0, 1: 0, 2: 0, 3: 1 }, worth_websearch: { 0: 0, 1: 1, 2: 0, 3: 0 } } };
      const body =
        `const ranked = ${J(CASES)}.map((c) => J.rank(c.items).recommended);\n` +
        `out({ ranked, lane: (await run(["worth", ${J(lane)}])).result });`;
      const check = (jev) => {
        const r = drive(body, { jev, cfg });
        assert(r.json && r.json.ranked, `driver failed\n${r.stdout}${r.stderr}`);
        return r.json;
      };
      const j = check(JEV);
      CASES.forEach((c, n) => assert(j.ranked[n] === c.rec, `${c.name}: recommended ${j.ranked[n]} (want ${c.rec})`));
      const L = j.lane;
      const q = Object.fromEntries(((L && L.options) || []).map((x) => [x.id, x.quote.high]));
      assert(L && L.recommended === "link-in-bio-recon" && L.strongest === "link-in-bio-recon" && L.options[0].id === "link-in-bio-recon" && q["site-teardown"] === 5 && q["link-in-bio-recon"] === 7, `the lane replay must recommend link-in-bio-recon (7 within 5 of site-teardown's 5)\n${J(L)}`);

      // KILLS, one per clause: no margin; a margin of 4; "<" for "<="; the null guard dropped; the
      // first level-3 by position instead of the cheapest.
      const MARGIN_LINE = "if (recommended && recommended.level === 2 && full && full.quote.high <= cost(recommended) + MARGIN) recommended = full;";
      const kill = (name, pairs, caseName) => {
        const k = check(mutate(pairs));
        const n = CASES.findIndex((c) => c.name === caseName);
        assert(k.ranked[n] !== CASES[n].rec, `${name}: the mutant must change ${caseName}, or J17 proves nothing`);
      };
      kill("no margin", [[MARGIN_LINE, ""]], "lane-competitor-offer");
      kill("margin 4", [["export const MARGIN = 5;", "export const MARGIN = 4;"]], "free-l2-vs-l3-at-5-flips");
      kill("strict", [["full.quote.high <= cost(recommended) + MARGIN", "full.quote.high < cost(recommended) + MARGIN"]], "free-l2-vs-l3-at-5-flips");
      kill("null guard", [["f.level === 3 && f.quote.high !== null", "f.level === 3"]], "no-ceiling-l3-never-within");
      kill("first level-3", [["const full = items.filter((f) => f.level === 3 && f.quote.high !== null).sort(cheaper)[0];", "const full = items.filter((f) => f.level === 3 && f.quote.high !== null)[0];"]], "cheapest-l3-within");
    },
  },
  {
    id: "J18-jev-named-platforms-survive-the-cut",
    desc: "a single platform the ask names always advances past round 3, beyond the top 3, one request each (Joe 09.25.26, no cap): lane L's F4 ask keeps amazon (round 3 + ebay, walmart, google_shopping, amazon + aggregators = 6 requests); names come from platform-tokens.mjs, the suggest hook's own derivation (an alias counts; a stop-listed word or an aggregator adds nothing); a named platform already in the top 3 adds nothing",
    fn() {
      // Lane L's F4 ask, verbatim (output/data/jev-lane-l-09.25.26/cuts-F4.json); round 3 put amazon below the line.
      const F4 = reqFile({ ask: "compare the price of Bowflex SelectTech 552 dumbbells on Amazon, Walmart and eBay" });
      const alias = reqFile({ ask: "look into what gym owners post on ig" });
      const quiet = reqFile({ ask: "research target market fit for gyms on the web, with tavily and perplexity answers" });
      const P = COSTS._platforms;
      const eid = (k) => k.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
      const eps = (p) => Object.keys(COSTS).filter((k) => !k.startsWith("_") && k.slice(k.indexOf(" ") + 1).split("/")[0] === p);
      // One driver per ask, each with its own round-3 answers (endpoint Nouls default to 0.1).
      const ASKS = {
        F4: [F4, { noul: { platform_ebay: 0.9, platform_walmart: 0.8, platform_google_shopping: 0.7, platform_amazon: 0.2 } }],
        alias: [alias, { noul: { platform_tiktok: 0.9, platform_youtube: 0.8, platform_reddit: 0.7 } }],
        quiet: [quiet, {}],
      };
      const check = (jev) =>
        Object.fromEntries(Object.entries(ASKS).map(([k, [file, cfg]]) => {
          const r = drive(`const x = await run(["cuts", ${J(file)}]); out({ code: x.code, result: x.result, bodies: T.calls.map((c) => c.body) });`, { jev, cfg });
          assert(r.json && r.json.result, `driver failed (${k})\n${r.stdout}${r.stderr}`);
          return [k, r.json];
        }));
      const j = check(JEV);
      const f = j.F4;
      assert(f.code === 0 && f.bodies.length === 6 && f.result.calls === 6, `F4: round 3 + 3 top + amazon + aggregators = 6 requests, got ${f.bodies.length}`);
      assert(same(f.result.platforms, ["ebay", "walmart", "google_shopping", "amazon"]), `F4 must keep amazon after the top 3: ${J(f.result.platforms)}`);
      assert(same(Object.keys(f.bodies[4].questions), eps("amazon").map((k) => `endpoint_${eid(k)}`)), "F4's fifth request must be amazon's endpoints");
      assert(same(j.alias.result.platforms, ["tiktok", "youtube", "reddit", "instagram"]) && j.alias.bodies.length === 6, `"ig" names instagram: ${J(j.alias.result.platforms)}`);
      assert(same(j.quiet.result.platforms, []) && j.quiet.bodies.length === 2, `a stop-listed word or an aggregator names no platform: ${J(j.quiet.result.platforms)}`);
      assert(Object.keys(P).includes("target") && Object.keys(P).includes("tavily"), "the quiet case must name real namespaces, or it proves nothing");
      // One source: jev.mjs reads the names from platform-tokens.mjs and keeps no list of its own.
      const src = readFileSync(JEV, "utf8");
      assert(src.includes('import { derivePlatforms, hasToken } from "./platform-tokens.mjs";') && !/HUMAN_ALIASES|STOP_TOKENS/.test(src), "jev.mjs must take platform names from platform-tokens.mjs and hold no alias or stop list");

      // KILLS: no named survival; canonical names only (a second, alias-blind and stop-list-blind
      // list); aggregators not filtered out; a named top-3 platform requested twice.
      const kept = "const kept = [...top, ...namedPlatforms(ask, singles).filter((p) => !top.includes(p))];";
      assert(!check(mutate([[kept, "const kept = top;"]])).F4.result.platforms.includes("amazon"), "the no-named mutant must drop amazon, or J18 proves nothing");
      const own = check(mutate([["for (const [token, p] of derivePlatforms().platformOf)", "for (const [token, p] of singles.map((s) => [s, s]))"]]));
      assert(!own.alias.result.platforms.includes("instagram") && own.quiet.result.platforms.includes("target"), `the own-list mutant must miss "ig" and name "target", or J18 proves nothing ${J([own.alias.result.platforms, own.quiet.result.platforms])}`);
      assert(check(mutate([["  return singles.filter((p) => named.has(p));", "  return [...named];"]])).quiet.bodies.length > 2, "the unfiltered mutant must add an aggregator request, or J18 proves nothing");
      assert(check(mutate([[kept, "const kept = [...top, ...namedPlatforms(ask, singles)];"]])).F4.bodies.length === 8, "the no-dedupe mutant must request ebay and walmart twice, or J18 proves nothing");
    },
  },
  {
    id: "J19-jev-a-leading-tilde-is-the-home-directory",
    desc: "SKILL.md's no-note ask file, ~/.claude/revxl/jev-ask.json, reaches jev.mjs inside double quotes, where no shell expands it: a leading ~ is read as the home jev.mjs was given, so the literal path reads the file and one request goes out",
    fn() {
      const body =
        `const fs = await import("node:fs");\n` +
        `fs.mkdirSync(DIR + "/.claude/revxl", { recursive: true });\n` +
        `fs.writeFileSync(DIR + "/.claude/revxl/jev-ask.json", JSON.stringify({ ask: ${J(ASK)} }));\n` +
        `out(await run(["intake", "~/.claude/revxl/jev-ask.json"]));`;
      const r = drive(body);
      assert(r.json && r.json.code === 0 && r.json.calls === 1, `the literal ~ path must read the ask file under the home and send one request\n${r.stdout}${r.stderr}`);

      // KILL: ~ left as ~. The literal is a cwd-relative path again: exit 6, nothing sent.
      const k = drive(body, { jev: mutate([["() => home)", '() => "~")']]) });
      assert(k.json && k.json.code === 6 && k.json.calls === 0, `the no-expansion mutant must exit 6 with no request, or J19 proves nothing\n${k.stdout}`);
    },
  },
  {
    id: "J20-jev-worth-marks-the-free-path",
    desc: "R13a.1 (Joe 09.26.26, ruling 4): every worth option carries a code-set boolean `free`, true only on the free path (the finalist with no legs): a row's websearch, the router's free-topic-scout (an id that is not \"websearch\"), and free_web's lone option; a row with no free path has none; the free path stays a finalist and can still be recommended",
    fn() {
      const routerOpts = [
        { id: "trustpilot-reviews", name: "A business's Trustpilot reviews", route: "socialcrawl", endpoints: [{ call: "GET trustpilot/reviews", countLow: 1, countHigh: 2, role: "reviews" }] },
        { id: "free-topic-scout", name: "Free topic scout", route: "websearch" },
      ];
      const files = {
        trending: reqFile({ ask: "what's trending on TikTok in the fitness niche this week", row: "trending" }),
        free_web: reqFile({ ask: "what year was the Eiffel Tower finished", row: "free_web" }),
        competitor_ads: reqFile({ ask: "what ads is Gymshark running", row: "competitor_ads" }),
        router: reqFile({ ask: ASK, options: routerOpts }),
      };
      const body =
        `const res = {};\n` +
        `for (const [k, p] of Object.entries(${J(files)})) { const x = await run(["worth", p]); res[k] = { code: x.code, recommended: x.result && x.result.recommended, free: x.result && Object.fromEntries(x.result.options.map((o) => [o.id, o.free])) }; }\n` +
        `out(res);`;
      // trending's live Step 0.5 levels (J9): web search is level 2 and is recommended.
      const cfg = { score: { worth_websearch: { 0: 0.04, 1: 0.24, 2: 0.55, 3: 0.17 }, worth_tiktok_hashtags_popular: { 0: 0, 1: 0.03, 2: 0.42, 3: 0.55 } } };
      const check = (jev) => {
        const r = drive(body, { jev, cfg });
        assert(r.json && r.json.router, `driver failed\n${r.stdout}${r.stderr}`);
        const j = r.json;
        const fails = [];
        for (const [k, v] of Object.entries(j)) if (v.code !== 0) fails.push(`${k}: exit ${v.code}`);
        const want = {
          trending: Object.fromEntries([["websearch", true], ...PKG.rows.find((x) => x.id === "trending").options.map((o) => [o.id, false])]),
          free_web: { websearch: true },
          competitor_ads: Object.fromEntries(PKG.rows.find((x) => x.id === "competitor_ads").options.map((o) => [o.id, false])),
          router: { "trustpilot-reviews": false, "free-topic-scout": true },
        };
        for (const [k, w] of Object.entries(want)) {
          const got = j[k].free || {};
          const bad = Object.keys(w).filter((id) => got[id] !== w[id]);
          if (bad.length || Object.keys(got).length !== Object.keys(w).length) fails.push(`${k}: free ${J(got)} (want ${J(w)})`);
        }
        if (j.trending.recommended !== "websearch") fails.push(`trending: the free path must still be recommendable, got ${j.trending.recommended}`);
        return fails;
      };
      const f = check(JEV);
      assert(!f.length, `the free field is wrong:\n  ${f.join("\n  ")}`);

      // KILLS: no free field in the output; keyed on the id "websearch" (misses the router's
      // free-topic-scout); every option marked free.
      assert(check(mutate([["    free: f.free,\n", ""]])).length, "the no-field mutant must fail, or J20 proves nothing");
      assert(check(mutate([["free: !legs.length,", 'free: o.id === "websearch",']])).some((x) => x.startsWith("router:")), "the id-keyed mutant must miss free-topic-scout, or J20 proves nothing");
      assert(check(mutate([["free: !legs.length,", "free: true,"]])).length, "the all-free mutant must fail, or J20 proves nothing");
    },
  },
  {
    id: "J21-jev-price-words-joined-by-underscore-in-values",
    desc: "R13b (R12.1 X1): in a string VALUE \"_\" separates words like \"-\" does, so free_tier, 5_credits, paid_api, credits_left, cheap_scrape, refund_policy and capped_run in an option's label or name are refused before the transport (exit 6, zero requests), as cheap-scrape already was; keys stay on the raw regex, so intake still sends the frozen route key free_web; plainDesc drops a catalogue sentence on the same test",
    fn() {
      const WORDS = ["free_tier", "5_credits", "paid_api", "credits_left", "cheap_scrape", "refund_policy", "capped_run"];
      const opt = (field, w) => ({ id: "web-scrape", [field]: `One web page, ${w}`, route: "socialcrawl", endpoints: [{ call: "GET web/scrape", countLow: 1, countHigh: 1, role: "page" }] });
      const REQ = {};
      for (const w of WORDS) for (const field of ["label", "name"]) REQ[`${field} ${w}`] = reqFile({ ask: ASK, options: [opt(field, w)] });
      REQ["name cheap-scrape"] = reqFile({ ask: ASK, options: [opt("name", "cheap-scrape")] });
      const q = reqFile({ ask: ASK });
      const DESC = { "GET fixture/page": { range: [1, 1], desc: "Returns the page text. Works on the free_tier only." } };
      const body =
        `const res = {};\n` +
        `for (const [k, p] of Object.entries(${J(REQ)})) { const x = await run(["worth", p]); res[k] = { code: x.code, calls: x.calls, error: x.error }; }\n` +
        `const n = T.calls.length; const intake = await run(["intake", ${J(q)}]);\n` +
        `res.intake = { code: intake.code, calls: intake.calls, keys: intake.calls ? Object.keys(T.calls[n].body.questions.package.criteria) : [] };\n` +
        `res.desc = J.endpointsRequest(${J(ASK)}, ${J(DESC)}, ["fixture"]).body.state.endpoints;\n` +
        `out(res);`;
      const check = (jev) => {
        const r = drive(body, { jev });
        assert(r.json && r.json.intake, `driver failed\n${r.stdout}${r.stderr}`);
        return r.json;
      };
      const j = check(JEV);
      for (const k of Object.keys(REQ)) {
        assert(j[k].code === 6 && j[k].calls === 0 && /price word/.test(j[k].error), `${k}: a price word joined by "_" or "-" must be refused before sending\n${J(j[k])}`);
      }
      assert(j.intake.code === 0 && j.intake.calls === 1 && j.intake.keys.includes("free_web"), `intake must still send the frozen key free_web\n${J(j.intake)}`);
      assert(j.desc.get_fixture_page === "Returns the page text.", `plainDesc must drop the free_tier sentence\n${J(j.desc)}`);

      // KILLS: the raw regex back on values (every joined word goes out); the new test on keys too
      // (intake refuses free_web); plainDesc on the raw regex (the free_tier sentence is kept).
      const RULE = 'const hasPriceWord = (s) => PRICE_WORDS.test(s.replace(/_/g, " "));';
      const raw = check(mutate([[RULE, "const hasPriceWord = (s) => PRICE_WORDS.test(s);"]]));
      const leaked = Object.keys(REQ).filter((k) => k !== "name cheap-scrape" && raw[k].calls === 1);
      assert(leaked.length === WORDS.length * 2, `the raw-regex mutant must send every "_" label and name, or J21 proves nothing (${J(leaked)})`);
      assert(check(mutate([["if (PRICE_WORDS.test(k)) throw", "if (hasPriceWord(k)) throw"]])).intake.code === 6, "the keys-too mutant must refuse free_web, or J21 proves nothing");
      assert(/free_tier/.test(check(mutate([[".filter((s) => s.trim() && !hasPriceWord(s))", ".filter((s) => s.trim() && !PRICE_WORDS.test(s))"]])).desc.get_fixture_page), "the raw plainDesc mutant must keep the free_tier sentence, or J21 proves nothing");
    },
  },
];
