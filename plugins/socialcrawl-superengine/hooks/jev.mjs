#!/usr/bin/env node
/*
 * jev.mjs — the Jev decision layer (Stage B rev4 R12). OPTIONAL: the research front door runs it
 * on an unnamed ask unless the suggest hook's note says `jev: off` (no OpenRouter key); with no key it exits 3 and
 * the front door takes the no-key path (R13a, Joe 09.25.26). Jev is TypeSafe's
 * decision model on OpenRouter's Decisions API ("alpha"): typed questions in, probabilities out.
 *
 *   node "${CLAUDE_PLUGIN_ROOT}/hooks/jev.mjs" <intake|cuts|worth> <request.json>   # JSON on stdout
 *
 * The request file is written with the Write tool — never argv, never a heredoc:
 *   intake  {"ask": "..."}                    one call: is_research + missing + package
 *   cuts    {"ask": "..."}                    platform cuts (a platform the ask names always survives),
 *                                             then endpoint cuts (the none_fit path)
 *   worth   {"ask": "...", "row": "<id>"}     a packages.json row: its free path + its options
 *           {"ask": "...", "options": [...]}  the router's options (the none_fit path)
 *
 * EXIT CODES, set on process.exitCode only — on Node 24 / Windows a script that fetched and then
 * calls the exit function directly dies with rc 127 (P2):
 *   0 ok · 3 no key (nothing sent) · 4 key rejected (401/403) · 5 no OpenRouter credit (402)
 *   6 anything else, incl. 404 (a retired model or a moved endpoint) (P20)
 * On 3-6 stdout is empty and stderr has one line. The key is never printed, logged or in an error.
 *
 * JEV NEVER AUTHORIZES SPEND. It routes and it judges value; it never sees a price. Every price
 * here comes from hooks/price.mjs (a curated row keeps its own quote), the ranking is code, and
 * the person's pick in the menu is the go.
 *
 * THE INVARIANT — the only request this file can make is a POST to DECISIONS. decisionsUrl()
 * builds it and throws on anything else before a transport is handed a URL (ledgerUrl's pattern).
 * The credit guard hooks the shell and never sees this file's calls, so the lock lives here.
 *
 * FROZEN TEXT. The intake questions, the worth Score shape, the model pin and both lines are
 * Step 0.5's (09.23.26), which copied T2 (09.22.26) byte for byte. The 16 package options and
 * none_fit's criterion are read from packages.json, whose 14 tested sentences check_packages.mjs
 * pins to T2. The cuts wording and its line ran live once, in R12's lane L (09.25.26).
 *
 * Stdlib + hooks/price.mjs + hooks/platform-tokens.mjs (the suggest hook's platform names, one
 * source). packages.json, costs.json and curated-workflows.json are read relative to this file,
 * so it runs from any cwd.
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { quote } from "./price.mjs";
import { derivePlatforms, hasToken } from "./platform-tokens.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const PACKAGES = join(HERE, "..", "skills", "research-plays", "references", "packages.json");
const CURATED = join(HERE, "..", "skills", "research-plays", "curated-workflows.json");
const COSTS = join(HERE, "costs.json");

export const MODEL = "typesafe/jev-1.13-20260917";
const DECISIONS = "https://openrouter.ai/api/alpha/decisions";
const DECISIONS_PATH = "/api/alpha/decisions";
const TIMEOUT_MS = 10000;
const MODES = ["intake", "cuts", "worth"];
const USAGE = "usage: node jev.mjs <intake|cuts|worth> <request.json>";

class JevError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

/* ------------------------------------------------------------ intake (Step 0.5 part 4, T2 v3) */
export const STATE_DESCRIPTION = "A request typed by a user of a social-media research tool.";
export const IS_RESEARCH = {
  type: "noul",
  instructions: "Is `ask` a research request, where the person wants information gathered and interpreted?",
  criteria: {
    true: "Asks to find out, look into, research, or learn about people, brands, content, markets or facts.",
    false: "Names one exact API endpoint to call, asks to set up or install software, or asks for a task like booking or buying something.",
  },
};
export const MISSING = {
  type: "choice",
  instructions: "What is `ask` still missing before the research can start?",
  criteria: {
    nothing_missing: "The ask names who or what to research and where to look, clearly enough to start.",
    missing_target: "It does not name who to research: an unnamed competitor, client, account or brand.",
    missing_platform: "It names who or what, but not which platform or site to look on, and the research depends on it.",
    missing_topic: "It does not name the topic, niche or subject to research.",
    not_research: "It is not a research request: a single named API call, a setup task, or something like booking or buying.",
  },
};
export const ROUTE_INSTRUCTIONS = "Which route best fits what the person wants in `ask`?";
export const IS_RESEARCH_LINE = 0.5; // research asks scored >= 0.69, the rest <= 0.13
export const NONE_FIT_LINE = 0.2; // p(none_fit) was 0.00 on all 19 asks with a real row

/* ------------------------------------------------------------ worth (Step 0.5 part 5, Score) */
export const WORTH_DESCRIPTION =
  "A request typed by a user of a social-media research tool, and the research options that could answer it.";
export const LEVELS = [
  "It would not answer it",
  "It would answer a small part of it",
  "It would answer most of it",
  "It would answer it fully",
];
const worthQuestion = (id) => ({
  type: "score",
  instructions: `How well would the option \`${id}\` in \`options\` answer what the person wants in \`ask\`?`,
  criteria: LEVELS,
});

/* ------------------------------------------ cuts (plan R12 + P19; wording NOT measured live) */
export const AGGREGATORS = ["prism", "search", "web", "tavily", "perplexity", "content_analysis"];
export const CUT_LINE = 0.5;
export const TOP_PLATFORMS = 3;
/* Joe 09.25.26 (R12 lane L): a level-3 option beats the level-2 pick within this many credits. */
export const MARGIN = 5;
const PLATFORMS_DESCRIPTION =
  "A request typed by a user of a social-media research tool, and the platforms that could answer it.";
const ENDPOINTS_DESCRIPTION =
  "A request typed by a user of a social-media research tool, and the endpoints that could answer it.";
const platformQuestion = (name) => ({
  type: "noul",
  instructions: `Would data from the platform \`${name}\` in \`platforms\` help answer what the person wants in \`ask\`?`,
  criteria: {
    true: "The platform holds data that would help answer what the person wants.",
    false: "Nothing on the platform would help answer what the person wants.",
  },
});
const endpointQuestion = (id) => ({
  type: "noul",
  instructions: `Would what the endpoint \`${id}\` in \`endpoints\` returns help answer what the person wants in \`ask\`?`,
  criteria: {
    true: "What the endpoint returns would help answer what the person wants.",
    false: "What the endpoint returns would not help answer what the person wants.",
  },
});

/*
 * A price word: a credit figure or the vendor's currency word, a dollar amount, a tier word,
 * P17's two examples ("Free:", "capped by the session cap"), or the call's own billing ("at each
 * platform's own price", "failed items refunded"). Subject words such as "price history" or
 * "what it costs" describe the data, not the call, and pass.
 */
export const PRICE_WORDS =
  /\d[\s\-–—:]*(?:cr|credits?)\b|\bcredits?\b|\$\s?\d|\b(?:free|paid|cheap(?:er|est)?|expensive)\b|\bsession cap\b|\bcapped\b|\bown prices?\b|\brefund(?:s|ed)?\b/i;

/* A price word in a string VALUE. "_" is a word character, so \b sees free_tier or 5_credits as one
 * word: read it as a space (R13b, R12.1 X1). Keys stay on the raw regex, so intake's frozen route
 * key free_web still goes out; plainDesc uses this same test, so a kept sentence can't abort cuts. */
const hasPriceWord = (s) => PRICE_WORDS.test(s.replace(/_/g, " "));

/* ------------------------------------------------------------------------- THE INVARIANT */
export function decisionsUrl(path = DECISIONS_PATH) {
  const url = new URL(String(path), "https://openrouter.ai").href;
  if (url !== DECISIONS) {
    throw new JevError(6, `jev.mjs may only call ${DECISIONS} — refused ${JSON.stringify(String(path))} before building a request`);
  }
  return url;
}

/* ------------------------------------------------------------------- key and transport */
/* A second line, a CR or a NUL can't ride in a header, and fetch's error quotes the header, key and all. */
const CONTROL = /[\u0000-\u001f\u007f]/;

export function resolveKey(env = process.env, home = homedir()) {
  const fromEnv = String(env.OPENROUTER_API_KEY || "").trim();
  const file = join(home, ".config", "openrouter", "api_key");
  const key = fromEnv.startsWith("sk-or-") ? fromEnv : existsSync(file) ? readFileSync(file, "utf8").trim() || null : null;
  if (key && CONTROL.test(key)) {
    throw new JevError(6, "the OpenRouter key (OPENROUTER_API_KEY or ~/.config/openrouter/api_key) has a line break or control character inside it; nothing was sent");
  }
  return key;
}

/* The real transport: the ONLY place a request leaves this process. Injected everywhere else. */
async function httpsTransport(url, key, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return { status: res.status, json: await res.json().catch(() => null) };
}

/* Every key and string of a request except the person's own ask. One hit refuses the request. */
export function assertNoPriceWords(body) {
  const walk = (v, where) => {
    if (typeof v === "string") {
      if (hasPriceWord(v)) throw new JevError(6, `a price word reached a Jev request at ${where}; refused before sending`);
      return;
    }
    if (!v || typeof v !== "object") return;
    for (const [k, x] of Object.entries(v)) {
      if (where === "state" && k === "ask") continue;
      const at = where ? `${where}.${k}` : k;
      if (PRICE_WORDS.test(k)) throw new JevError(6, `a price word reached a Jev request at ${at}; refused before sending`);
      walk(x, at);
    }
  };
  walk(body, "");
}

async function decide(body, key, transport) {
  const url = decisionsUrl(); // before any transport sees a URL
  assertNoPriceWords(body);
  let res;
  try {
    res = await transport(url, key, body);
  } catch (e) {
    // A transport error can quote the Authorization header; the key never leaves in an error.
    throw new JevError(6, `Jev unreachable: ${String((e && e.message) || e).split(key).join("<key>")}`);
  }
  const status = res && res.status;
  if (status === 401 || status === 403) throw new JevError(4, `OpenRouter rejected the key (HTTP ${status})`);
  if (status === 402) throw new JevError(5, "OpenRouter has no credit left for this key (HTTP 402)");
  const answers = res && res.json && res.json.answers;
  if (!(status >= 200 && status < 300) || !answers || typeof answers !== "object") {
    throw new JevError(6, `Jev unavailable (HTTP ${status})`);
  }
  return answers;
}

function num(v) {
  if (typeof v !== "number" || Number.isNaN(v)) throw new JevError(6, "a Jev answer is missing its number");
  return v;
}

/* ---------------------------------------------------------------------------------- intake */
export function intakeRequest(ask, pkg) {
  const criteria = {};
  for (const r of pkg.rows) if (r.jev === true) criteria[r.id] = r.use_when;
  criteria.none_fit = pkg.none_fit.criterion;
  return {
    model: MODEL,
    state: { description: STATE_DESCRIPTION, ask },
    questions: {
      is_research: IS_RESEARCH,
      missing: MISSING,
      package: { type: "choice", instructions: ROUTE_INSTRUCTIONS, criteria },
    },
  };
}

/* Step 0.5's order: not research -> something missing -> the package or the none_fit trigger. */
export function intakeVerdict(answers, rowIds) {
  const isr = num(answers.is_research && answers.is_research.noul);
  const miss = answers.missing && answers.missing.choice;
  const pick = answers.package && answers.package.choice;
  const pNone = num(answers.package && answers.package.probabilities && answers.package.probabilities.none_fit);
  if (!Object.hasOwn(MISSING.criteria, miss) || !rowIds.includes(pick)) {
    throw new JevError(6, "Jev answered outside the options it was given");
  }
  const v = { next: "package", row: null, missing: null, is_research: isr, p_none_fit: pNone };
  if (isr < IS_RESEARCH_LINE || miss === "not_research") return { ...v, next: "not_research" };
  if (miss !== "nothing_missing") return { ...v, next: "missing", missing: miss };
  if (pick === "none_fit" || pNone >= NONE_FIT_LINE) return { ...v, next: "none_fit" };
  return { ...v, row: pick };
}

/* ------------------------------------------------------------------------------------ cuts */
const endpointId = (key) => key.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");

/* The catalogue line minus every sentence that names a price; the path when nothing is left. */
function plainDesc(key, entry) {
  const kept = String(entry.desc || "")
    .split(/(?<=[.!?])\s+/)
    .filter((s) => s.trim() && !hasPriceWord(s))
    .join(" ");
  return kept || key.slice(key.indexOf(" ") + 1);
}

export function platformsRequest(ask, names, platforms) {
  const state = { description: PLATFORMS_DESCRIPTION, ask, platforms: {} };
  const questions = {};
  for (const p of names) {
    state.platforms[p] = platforms[p].category;
    questions[`platform_${p}`] = platformQuestion(p);
  }
  return { model: MODEL, state, questions };
}

/* One request over every endpoint of the given namespaces: { keys, body }. */
export function endpointsRequest(ask, costs, names) {
  const keys = Object.keys(costs).filter((k) => {
    const e = costs[k];
    return !k.startsWith("_") && e && typeof e === "object" && "range" in e && names.includes(k.slice(k.indexOf(" ") + 1).split("/")[0]);
  });
  const state = { description: ENDPOINTS_DESCRIPTION, ask, endpoints: {} };
  const questions = {};
  for (const k of keys) {
    const id = endpointId(k);
    if (Object.hasOwn(state.endpoints, id)) throw new JevError(6, `two endpoints share the question id ${id}`);
    state.endpoints[id] = plainDesc(k, costs[k]);
    questions[`endpoint_${id}`] = endpointQuestion(id);
  }
  return { keys, body: { model: MODEL, state, questions } };
}

/* The single platforms the ask names, by the suggest hook's own tokens (aliases and stop-list included). */
export function namedPlatforms(ask, singles) {
  const lower = String(ask).toLowerCase();
  const named = new Set();
  for (const [token, p] of derivePlatforms().platformOf) if (hasToken(lower, token)) named.add(p);
  return singles.filter((p) => named.has(p));
}

async function cuts(ask, costs, call, io) {
  const P = costs._platforms || {};
  const singles = Object.keys(P).filter((p) => !AGGREGATORS.includes(p));
  const a3 = await call(platformsRequest(ask, singles, P));
  const top = singles
    .map((p, i) => ({ p, i, v: num(a3[`platform_${p}`] && a3[`platform_${p}`].noul) }))
    .filter((s) => s.v >= CUT_LINE)
    .sort((a, b) => b.v - a.v || a.i - b.i)
    .slice(0, TOP_PLATFORMS)
    .map((s) => s.p);
  // Named platforms always survive the cut (Joe 09.25.26, R12 lane L): one request each beyond the
  // top 3, uncapped, so the none_fit budget is 7 + the named platforms outside the top 3.
  const kept = [...top, ...namedPlatforms(ask, singles).filter((p) => !top.includes(p))];
  // Round 4: the kept single platforms one request each, plus ONE merged request for the
  // aggregators, which always advance (P19).
  const reqs = [...kept.map((p) => [p]), AGGREGATORS].map((g) => endpointsRequest(ask, costs, g)).filter((r) => r.keys.length);
  const a4 = await Promise.all(reqs.map((r) => call(r.body)));
  const survivors = [];
  reqs.forEach((r, n) => {
    r.keys
      .map((k, i) => ({ k, i, v: num(a4[n][`endpoint_${endpointId(k)}`] && a4[n][`endpoint_${endpointId(k)}`].noul) }))
      .filter((s) => s.v >= CUT_LINE)
      .sort((a, b) => b.v - a.v || a.i - b.i)
      .forEach((s) => survivors.push(s.k));
  });
  logCandidates(ask, survivors, io);
  return { mode: "cuts", platforms: kept, aggregators: AGGREGATORS, survivors, calls: 1 + reqs.length };
}

/* The survivors and the ask's HASH, never its text, for a human to promote into a row (P25). */
function logCandidates(ask, survivors, { env, home, err }) {
  const override = String(env.SC_REVXL_HOME || "").trim();
  const dir = override || join(home, ".claude", "revxl");
  try {
    mkdirSync(dir, { recursive: true });
    const ask_sha256 = createHash("sha256").update(ask, "utf8").digest("hex");
    appendFileSync(join(dir, "jev-candidates.jsonl"), JSON.stringify({ ts: new Date().toISOString(), ask_sha256, survivors }) + "\n");
  } catch (e) {
    err(`jev: the candidate log was not written (${(e && e.code) || "error"})\n`);
  }
}

/* ----------------------------------------------------------------------------------- worth */
/* The finalists: a package row's free path + options, or the router's options, priced in code. */
function finalists(req, data) {
  let list;
  if (typeof req.row === "string" && req.options === undefined) {
    const row = data.pkg.rows.find((r) => r.id === req.row);
    if (!row) throw new JevError(6, `packages.json has no row ${JSON.stringify(req.row)}`);
    const free = row.free ? [{ id: "websearch", label: row.free.how, route: "websearch", curated: row.free.curated }] : [];
    list = [...free, ...row.options];
  } else if (Array.isArray(req.options) && req.row === undefined) {
    list = req.options;
  } else {
    throw new JevError(6, 'a worth request names a "row" or carries "options", one of the two');
  }
  if (!list.length) throw new JevError(6, "a worth request with nothing to judge");
  return list.map((o, idx) => priced(o, idx, data));
}

function priced(o, idx, { costs, curatedById }) {
  const label = String((o && (o.label ?? o.name)) ?? "").trim();
  if (!o || typeof o.id !== "string" || !o.id || !label) throw new JevError(6, "every option needs an id and a label");
  if (o.curated !== undefined && !curatedById.has(o.curated)) throw new JevError(6, `no curated row ${JSON.stringify(o.curated)}`);
  // A curated row keeps its own reviewed quote (P14); anything else is priced from its legs.
  const cur = curatedById.get(o.curated ?? o.id);
  const legs = cur ? cur.endpoints || [] : o.endpoints || [];
  if (!cur && !legs.length && o.route !== "websearch") throw new JevError(6, `option ${o.id} has no legs and is not the free path`);
  const q = cur ? { low: cur.quote.low, high: cur.quote.high } : quote(legs, costs);
  return {
    id: o.id,
    // Jev's id: the free path's id loses its leading tier word like its label does
    // ("free-topic-scout" goes as topic_scout); a price word left in any id is refused.
    jid: jevId(legs.length ? o.id : o.id.replace(/^free[^A-Za-z0-9]+/i, "") || o.id),
    label,
    // Only the free path's own name ("Free topic scout") loses its tier word; any other label
    // carrying a price word is refused before sending.
    text: legs.length ? label : label.replace(/^free\s+/i, ""),
    ...(cur ? { curated: cur.id } : {}),
    quote: q,
    ceiling: cur ? cur.ceiling : o.ceiling ?? q.high,
    calls: legs.reduce((n, l) => n + (l.countHigh || 0), 0),
    // The free path is the finalist with no legs; SKILL.md keeps it off the priced menu (R13a.1).
    free: !legs.length,
    idx,
  };
}

const jevId = (id) => String(id).replace(/[^A-Za-z0-9_]/g, "_");

export function worthRequest(ask, list) {
  const options = {};
  const questions = {};
  for (const f of list) {
    const id = f.jid;
    // The id goes out three times (options key, worth_<id>, the instruction). "_" is a word
    // character, so \b can't see "free" in free_tiktok: read it as a space for this check.
    if (PRICE_WORDS.test(id.replace(/_/g, " "))) throw new JevError(6, `a price word reached a Jev request in the option id ${id}; refused before sending`);
    if (Object.hasOwn(options, id)) throw new JevError(6, `two options share the id ${id}`);
    options[id] = f.text;
    questions[`worth_${id}`] = worthQuestion(id);
  }
  return { model: MODEL, state: { description: WORTH_DESCRIPTION, ask, options }, questions };
}

/* The most likely level (argmax of the Score probabilities, P17). A tie keeps the LOWER level. */
export function levelOf(answer) {
  const p = answer && answer.probabilities;
  let best = 0;
  for (let l = 0; l < LEVELS.length; l++) {
    num(p && p[String(l)]);
    if (p[String(l)] > p[String(best)]) best = l;
  }
  return best;
}

/*
 * The ranking (Joe, P25): recommend the cheapest quote.high whose level is >= max - 1 AND >= 2;
 * ties go to fewer calls. No ceiling (null high) is never the cheap one. Then the margin (Joe
 * 09.25.26, R12 lane L): a level-2 pick gives way to the cheapest level-3 option whose quote.high
 * is at most MARGIN credits above it; a level-3 option with no ceiling is never within a margin.
 * The strongest is the highest level (then the higher score) and is always shown. Order:
 * recommendation, strongest, then the rest by level, price and calls. Nothing recommended when no
 * option reaches level 2.
 */
export function rank(items) {
  const top = Math.max(...items.map((f) => f.level));
  const cost = (f) => (f.quote.high === null ? Infinity : f.quote.high);
  const cheaper = (a, b) => cost(a) - cost(b) || a.calls - b.calls || a.idx - b.idx;
  let recommended = items.filter((f) => f.level >= top - 1 && f.level >= 2).sort(cheaper)[0] || null;
  const full = items.filter((f) => f.level === 3 && f.quote.high !== null).sort(cheaper)[0];
  if (recommended && recommended.level === 2 && full && full.quote.high <= cost(recommended) + MARGIN) recommended = full;
  const strongest = [...items].sort((a, b) => b.level - a.level || b.score - a.score || a.idx - b.idx)[0];
  const rest = items.filter((f) => f !== recommended && f !== strongest).sort((a, b) => b.level - a.level || cheaper(a, b));
  const order = [recommended, strongest === recommended ? null : strongest, ...rest].filter(Boolean);
  return { recommended: recommended ? recommended.id : null, strongest: strongest.id, order };
}

async function worth(req, data, call) {
  const list = finalists(req, data);
  const answers = await call(worthRequest(req.ask, list));
  const scored = list.map((f) => {
    const a = answers[`worth_${f.jid}`];
    const level = levelOf(a);
    return { ...f, level, score: typeof a.score === "number" ? a.score : level };
  });
  const r = rank(scored);
  const options = r.order.map((f) => ({
    id: f.id,
    label: f.label,
    ...(f.curated ? { curated: f.curated } : {}),
    level: f.level,
    levelText: LEVELS[f.level],
    quote: f.quote,
    ceiling: f.ceiling,
    calls: f.calls,
    mayStop: f.quote.high === null || f.quote.high >= 200,
    free: f.free,
    recommended: f.id === r.recommended,
    strongest: f.id === r.strongest,
  }));
  return { mode: "worth", row: req.row ?? null, recommended: r.recommended, strongest: r.strongest, options, calls: 1 };
}

/* -------------------------------------------------------------------------------------- CLI */
function readRequest(file) {
  let req;
  try {
    req = JSON.parse(readFileSync(file, "utf8"));
  } catch {
    throw new JevError(6, `could not read the request file ${JSON.stringify(file)}. ${USAGE}`);
  }
  if (!req || typeof req.ask !== "string" || !req.ask.trim()) throw new JevError(6, 'the request file needs an "ask" string');
  return req;
}

export async function main(argv, io = {}) {
  const {
    transport = httpsTransport,
    env = process.env,
    home = homedir(),
    out = (s) => process.stdout.write(s),
    err = (s) => process.stderr.write(s),
  } = io;
  try {
    const [mode, file, ...extra] = argv;
    if (!MODES.includes(mode) || !file || extra.length) throw new JevError(6, USAGE);
    const key = resolveKey(env, home);
    if (!key) throw new JevError(3, "no OpenRouter key (OPENROUTER_API_KEY or ~/.config/openrouter/api_key); nothing was sent");
    // A leading ~ is the home directory: SKILL.md's no-note ask file arrives quoted, so no shell expanded it.
    const req = readRequest(file.replace(/^~(?=[\\/])/, () => home));
    const read = (p) => JSON.parse(readFileSync(p, "utf8"));
    const call = (body) => decide(body, key, transport);
    let result;
    if (mode === "intake") {
      const pkg = read(PACKAGES);
      const body = intakeRequest(req.ask, pkg);
      result = { mode, ...intakeVerdict(await call(body), Object.keys(body.questions.package.criteria)), calls: 1 };
    } else if (mode === "cuts") {
      result = await cuts(req.ask, read(COSTS), call, { env, home, err });
    } else {
      const curatedById = new Map(read(CURATED).workflows.map((w) => [w.id, w]));
      result = await worth(req, { pkg: read(PACKAGES), costs: read(COSTS), curatedById }, call);
    }
    out(JSON.stringify(result) + "\n");
    return 0;
  } catch (e) {
    err(`jev: ${(e && e.message) || e}\n`);
    return e instanceof JevError ? e.code : 6;
  }
}

const isEntry = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isEntry) {
  main(process.argv.slice(2)).then(
    (code) => {
      process.exitCode = code;
    },
    () => {
      process.exitCode = 6;
    }
  );
}
