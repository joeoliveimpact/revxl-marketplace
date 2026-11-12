/*
 * 5a-i and 5a-ii — hooks/mod/helper.mjs, the mod's Node helper (the balance read and the N6 heartbeat), and the mod's source
 * rules. The mod's own behaviour is tested by `claude plugin test` (tests/*.test.ts); this file holds what needs a
 * real process and a real file system.
 *
 * Synchronous (P26): each case spawns the helper with spawnSync in a scratch home (HOME, USERPROFILE and
 * SC_REVXL_HOME all inside it), offline (no key unless a case gives the fake one, dead proxies, no NO_PROXY), and
 * every balance request is answered by the fake-fetch.mjs preload. The one dead-proxy case uses the real fetch and
 * reaches nothing. Zero credits, zero network.
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { Worker } from "node:worker_threads";
import { isDeepStrictEqual } from "node:util";
import { BALANCE, COSTS, FAKE_FETCH, GUARD, ROUTINE, V1, assert, session } from "../lib.mjs";
import { ledgerUrl } from "../../ledger.mjs";
import { ask } from "../lib-suggest.mjs";

const HOOKS = dirname(GUARD);
const HELPER = join(HOOKS, "mod", "helper.mjs");
// Every hooks module file (5b: widened from the two named files, so a new module file can't escape S1, S2 or A5).
const MOD = readdirSync(join(HOOKS, "mod")).filter((f) => /\.tsx?$/.test(f)).sort().map((f) => join(HOOKS, "mod", f));
const REG = join(HOOKS, "mod", "register.tsx");
const VERSION = JSON.parse(readFileSync(join(HOOKS, "..", ".claude-plugin", "plugin.json"), "utf8")).version;
const KEY = "sc_" + "TESTsecret123";   // never a real key; split so no scanner reads it as one
const DEAD = "http://127.0.0.1:9";
const TS = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const DAY = 24 * 60 * 60 * 1000;
const PLUGIN = "socialcrawl-superengine";

/**
 * Runs `node helper.mjs <args>` in a scratch home (o.home, else a fresh one). o.fetch: the fake-fetch replies
 * (preloaded); o.keyFile: the text of <home>/.config/socialcrawl/api_key; o.env: variables over the offline env, or a
 * function of the home giving them; o.setup(home): files first.
 */
function run(args, o = {}) {
  const home = o.home || mkdtempSync(join(tmpdir(), "sc-mod-"));
  if (o.keyFile !== undefined) {
    mkdirSync(join(home, ".config", "socialcrawl"), { recursive: true });
    writeFileSync(join(home, ".config", "socialcrawl", "api_key"), o.keyFile);
  }
  if (o.setup) o.setup(home);
  const env = { ...process.env, TEMP: home, TMP: home, TMPDIR: home };
  for (const k of Object.keys(env)) if (/^(socialcrawl_api_key|no_proxy|sc_revxl_home)$/i.test(k)) delete env[k];
  Object.assign(env, { HOME: home, USERPROFILE: home, SC_REVXL_HOME: join(home, "revxl"), HTTPS_PROXY: DEAD, HTTP_PROXY: DEAD, ALL_PROXY: DEAD, NODE_USE_ENV_PROXY: "1" });
  const log = join(home, "fetches.jsonl");
  if (o.fetch) Object.assign(env, { FAKE_FETCH: JSON.stringify(o.fetch), FAKE_FETCH_LOG: log });
  Object.assign(env, (typeof o.env === "function" ? o.env(home) : o.env) || {});
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [...(o.fetch ? ["--import", FAKE_FETCH] : []), ...(o.node || []), HELPER, ...args], { env, cwd: home, encoding: "utf8", timeout: 20000 });
  const res = {
    home, rc: r.status, out: r.stdout || "", err: r.stderr || "", ms: Date.now() - t0,
    fetches: existsSync(log) ? readFileSync(log, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)) : [],
  };
  // A25: the key is in no output and in no file but the key file a case wrote, whatever the branch.
  assert(!res.out.includes(KEY) && !res.err.includes(KEY), `the key printed: ${JSON.stringify(res.out + res.err)}`);
  for (const f of walk(home)) if (!f.endsWith("api_key")) assert(!readFileSync(f, "utf8").includes(KEY), `the key written to ${f}`);
  return res;
}

function walk(d) {
  return readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(join(d, e.name)) : [join(d, e.name)]));
}

/** A balance run's one line, parsed; asserts exit 0, one line and nothing on stderr. */
function oneLine(r, label) {
  assert(r.rc === 0, `${label}: exit 0, read ${r.rc}`, r);
  assert(r.out.endsWith("\n") && r.out.split("\n").length === 2, `${label}: exactly one line, read ${JSON.stringify(r.out)}`, r);
  assert(r.err === "", `${label}: nothing on stderr, read ${JSON.stringify(r.err)}`);
  return JSON.parse(r.out);
}

function failsWith(reason, label, o, fetches) {
  const r = run(["balance"], o);
  const j = oneLine(r, label);
  assert(JSON.stringify(j) === JSON.stringify({ ok: false, reason }), `${label}: {"ok":false,"reason":"${reason}"}, read ${r.out.trim()}`, r);
  if (fetches !== undefined) assert(r.fetches.length === fetches, `${label}: ${fetches} request(s), read ${r.fetches.length}`);
  rmSync(r.home, { recursive: true, force: true });
  return r;
}

const own = (home, root = join(home, "revxl")) => join(root, "heartbeat", PLUGIN);
const age = (f, days) => { const t = new Date(Date.now() - days * DAY); utimesSync(f, t, t); };

// ---- 5a-ii: the Settings tab's Save sends both keys in one `helper.mjs budget-write <revxl> <json>` call.
const BUDGET = "socialcrawl-budget.json";
const LIB = join(HOOKS, "mod", "lib.ts");
const bfOf = (home) => join(home, "revxl", BUDGET);
const inRevxl = (home) => readdirSync(join(home, "revxl")).sort();
/** A scratch home, its budget file seeded with `seed` (a string or bytes) when given. */
function fresh(seed) {
  const home = mkdtempSync(join(tmpdir(), "sc-mod-"));
  if (seed !== undefined) {
    mkdirSync(join(home, "revxl"), { recursive: true });
    writeFileSync(bfOf(home), seed);
  }
  return home;
}
/** `budget-write <root> <json>` (root: <home>/revxl unless given); its one line parsed (exit 0, one line, no stderr). */
function bw(home, json, o = {}) {
  const r = run(["budget-write", o.root ?? join(home, "revxl"), ...(json === undefined ? [] : [json])], { ...o, home });
  return { r, j: oneLine(r, `budget-write ${json}`) };
}
/** What the pane shows for a budget file, from the pane's own rule (lib.ts choiceOf), in a node that strips types. */
function paneShows(file) {
  const code = `import { choiceOf } from ${JSON.stringify(pathToFileURL(LIB).href)};` +
    `process.stdout.write(JSON.stringify(choiceOf(JSON.parse(process.env.PANE_FILE))));`;
  const r = spawnSync(process.execPath, ["--no-warnings", "--input-type=module", "-e", code], { env: { ...process.env, PANE_FILE: file }, encoding: "utf8" });
  assert(r.status === 0, `lib.ts choiceOf ran, read ${r.status} ${r.stderr}`);
  return JSON.parse(r.stdout);
}
/** 5b: `body` run as a module with `lib` (hooks/mod/lib.ts, types stripped), `readFileSync` and `out(value)`, in a node
 *  given `env` over this one's; what it out()s, parsed. */
function libJson(body, env = {}) {
  const code = `import * as lib from ${JSON.stringify(pathToFileURL(LIB).href)}; import { readFileSync } from "node:fs";` +
    `const out = (v) => process.stdout.write(JSON.stringify(v));` + body;
  const r = spawnSync(process.execPath, ["--no-warnings", "--input-type=module", "-e", code], { env: { ...process.env, ...env }, encoding: "utf8", timeout: 20000 });
  assert(r.status === 0, `lib.ts ran, read ${r.status} ${r.stderr}`);
  return JSON.parse(r.stdout);
}
/** 5b: words a launcher's prompt never holds (the guard's own files and its key, R §4). */
const FORBIDDEN = ["budget-write", "revxl", "socialcrawl-budget", "socialcrawl-day", "socialcrawl-calls", "credit-guard-unattended", "sessions/", "x-api-key", "api_key", "SOCIALCRAWL_API_KEY"];
/** A preload that makes every renameSync throw EPERM, the file system left as it was. */
function renameThrows() {
  const d = mkdtempSync(join(tmpdir(), "sc-mod-rn-"));
  const f = join(d, "rename-throws.mjs");
  writeFileSync(f,
    `import { createRequire, syncBuiltinESMExports } from "node:module";\n` +
    `const fs = createRequire(import.meta.url)("node:fs");\n` +
    `fs.renameSync = () => { throw Object.assign(new Error("EPERM, forced"), { code: "EPERM" }); };\n` +
    `syncBuiltinESMExports();\n`);
  return { url: pathToFileURL(f).href, dir: d };
}
const P1 = `curl -s "${V1}amazon/shop?q=a"`;   // plain, flat 1
/** The real guard on a plain paid call in session `s`: its decision and the call record's newest line (the limit it applied). */
function guardOn(s, env) {
  const r = s.run(P1, { env });
  const lines = readFileSync(join(s.revxl, "socialcrawl-calls.jsonl"), "utf8").trim().split("\n");
  return { r, last: JSON.parse(lines[lines.length - 1]) };
}

export default [
  {
    id: "EGM B3b: 5-real-charge-starting-kinds",
    desc: "real costs.json independently classifies all More rows, including 584 priced, 25 free and 7 request-priced; Search has 13 free calls",
    fn() {
      const costs = JSON.parse(readFileSync(COSTS, "utf8"));
      const r = libJson(`const c = JSON.parse(readFileSync(process.env.COSTS_FILE, "utf8"));` +
        `out({ rows: lib.moreOf(c, Object.keys(c._platforms)), shortlist: lib.ENDPOINTS.map(e => e.call), search: lib.moreOf(c, lib.GROUP_PLATFORMS.Search) });`, { COSTS_FILE: COSTS });
      const expected = Object.keys(costs).filter(call => !call.startsWith("_") && !r.shortlist.includes(call));
      assert(isDeepStrictEqual(r.rows.map(row => row.call), expected), "all real non-shortlist calls remain in file order");
      const counts = ["priced", "free", "unpriced"].map(kind => r.rows.filter(row => row.kind === kind).length);
      assert(isDeepStrictEqual(counts, [584, 25, 7]), `kinds 584/25/7, read ${counts.join("/")}`);
      assert(r.search.filter(row => row.kind === "free").length === 13, "Search has 13 free calls");
      for (const row of r.rows) {
        const range = costs[row.call].range;
        const kind = row.call === "PATCH web/monitors/{monitor_id}" || range === null ? "unpriced" : range[0] === 0 && range[1] === 0 ? "free" : "priced";
        assert(row.kind === kind, `${row.call}: ${kind}, read ${row.kind}`);
        if (kind === "unpriced") assert(row.price === null, `${row.call}: no price`);
        if (kind === "free") assert(row.price === "free", `${row.call}: free price`);
      }
    },
  },
  {
    id: "EGM W: 5-neutral-brand-comment",
    desc: "brandSlug's comment uses the exact neutral My Brand/mybrand example",
    fn() {
      const source = readFileSync(LIB, "utf8");
      assert(source.includes("/** A brand's folder name: lowercase letters and digits only (`My Brand` is `mybrand`). */"), "brandSlug comment uses (`My Brand` is `mybrand`)");
    },
  },
  {
    id: "5-costs-mirror",
    desc: "the engine tests' evaluated costs-real.ts default export deep-equals the real hooks/costs.json",
    fn() {
      const mirror = pathToFileURL(join(HOOKS, "..", "tests", "costs-real.ts")).href;
      const r = spawnSync(process.execPath, ["--no-warnings", "--input-type=module", "-e",
        `import costs from ${JSON.stringify(mirror)}; process.stdout.write(JSON.stringify(costs));`], { encoding: "utf8" });
      assert(r.status === 0, `costs-real.ts evaluated: ${r.status} ${r.stderr}`);
      assert(isDeepStrictEqual(JSON.parse(r.stdout), JSON.parse(readFileSync(COSTS, "utf8"))), "costs-real.ts matches costs.json; regenerate the mirror when prices/platforms change");
    },
  },
  {
    id: "M6 C1: 5-runtime-more-inventory",
    desc: "real costs through libJson: groups plus 56 other platforms partition all 616 non-shortlist calls, with pinned kinds, metering, transcript flags and unique verb-bearing keys",
    fn() {
      const groups = { Instagram: ["instagram"], TikTok: ["tiktok", "tiktokshop"], YouTube: ["youtube"], LinkedIn: ["linkedin"], "Facebook ads": ["facebook"], Reddit: ["reddit"], Search: ["prism", "search", "tavily", "perplexity", "web"] };
      const r = libJson(`const c = JSON.parse(readFileSync(process.env.COSTS_FILE, "utf8")); const groups = JSON.parse(process.env.GROUPS);` +
        `const others = lib.otherPlatforms?.(c); out({ groups: lib.GROUP_PLATFORMS, others, shortlist: lib.ENDPOINTS.map(e => e.call),` +
        `sets: [...Object.values(groups), ...(others ?? []).map(p => [p])].map(ps => ({ ps, rows: lib.moreOf?.(c, ps) ?? null })),` +
        `platformOptions: lib.platformOptions?.(c) });`, { COSTS_FILE: COSTS, GROUPS: JSON.stringify(groups) });
      assert(JSON.stringify(r.groups) === JSON.stringify(groups), "M6 C1: GROUP_PLATFORMS is the exact seven-group map");
      const costs = JSON.parse(readFileSync(COSTS, "utf8"));
      const routes = Object.keys(costs).filter(c => !c.startsWith("_"));
      const others = Object.keys(costs._platforms).filter(p => !Object.values(groups).flat().includes(p));
      assert(routes.length === 645 && r.others?.length === 56 && new Set(r.others).size === 56 && others.every(p => r.others.includes(p)), "645 routes and exactly the other 56 platforms");
      const rows = r.sets.flatMap(s => s.rows ?? []);
      for (const { ps, rows: got } of r.sets) {
        const want = routes.filter(c => ps.includes(c.split(" ")[1].split("/")[0]) && !r.shortlist.includes(c));
        assert(JSON.stringify(got?.map(r => r.call)) === JSON.stringify(want), `${ps}: runtime file order/count ${want.length}, read ${got?.length}`);
        for (const row of got) {
          const [verb, path] = row.call.split(" ");
          assert(row.platform === path.split("/")[0] && typeof row.name === "string" && row.name.length > 0, `${row.call}: platform and display name`);
          assert(row.key === `more-${verb.toLowerCase()}-${path.replace(/\//g, "-")}`, `${row.call}: key holds the verb`);
          assert(row.metered === (costs[row.call].metered === true), `${row.call}: metered flag from file`);
          assert(row.transcript === (path.includes("transcript") || path === "prism/brief-check"), `${row.call}: guard's transcript rows`);
        }
      }
      const remaining = routes.filter(c => !r.shortlist.includes(c));
      assert(rows.length === 616 && new Set(rows.map(r => r.call)).size === 616 && remaining.every(c => rows.some(r => r.call === c)), "all and only the 616, each once");
      assert(["priced", "free", "unpriced"].map(k => rows.filter(r => r.kind === k).length).join("/") === "584/25/7", "kinds 584/25/7");
      assert(rows.filter(r => r.metered).length === 115 && rows.filter(r => r.transcript).length === 11, "115 metered and 11 transcript rows");
      assert(new Set(rows.map(r => r.key)).size === 616, "unique More keys");
      const shortKeys = r.shortlist.map(c => c.split(" ")[1].replace(/\//g, "-"));
      assert(rows.every(row => !shortKeys.includes(row.key)), "no shortlist key reused");
      const names = libJson(`out(Object.fromEntries(Object.keys(JSON.parse(readFileSync(process.env.COSTS_FILE, "utf8"))._platforms).map(p => [p, lib.siteName?.(p)])));`, { COSTS_FILE: COSTS });
      const sorted = [...others].sort((a, b) => names[a].localeCompare(names[b]));
      assert(JSON.stringify(r.others) === JSON.stringify(sorted), "other platforms sorted by display name");
      const options = [{ value: "", label: "Choose a platform…" }, ...sorted.map(p => ({ value: p, label: `${names[p]} · ${rows.filter(r => r.platform === p).length}` }))];
      assert(JSON.stringify(r.platformOptions) === JSON.stringify(options), "platform options display their live counts");
    },
  },
  {
    id: "M6 G1: 5-real-glossary-coverage",
    desc: "SITES covers exactly the real 68 platform ids; one short sentence, digits only inside its own name, without superlatives or coach",
    fn() {
      const sites = libJson("out(lib.SITES ?? null);");
      const costs = JSON.parse(readFileSync(COSTS, "utf8"));
      assert(JSON.stringify(Object.keys(sites ?? {}).sort()) === JSON.stringify(Object.keys(costs._platforms).sort()), "M6 G1: SITES exactly covers the real _platforms ids");
      for (const [id, { name, line }] of Object.entries(sites)) {
        assert(typeof name === "string" && name.trim().length > 0, `${id}: non-empty name`);
        assert(typeof line === "string" && line.length <= 160 && /^[^.?!]+[.]$/.test(line), `${id}: one sentence, at most 160 chars`);
        assert(!/\d/.test(line.split(name).join("")), `${id}: digits only inside its own name: ${line}`);
        assert(!/\b(?:most|best|largest|leading|popular|top|biggest|world's|coach)\b/i.test(line), `${id}: no superlative or coach: ${line}`);
      }
    },
  },
  {
    id: "M6 P: 5-real-guard-ceiling-sweep",
    desc: "H-79: every numeric-range route, plain and with each raising conditional, runs through the real offline guard; displayed ceiling covers every counted worst (eight isolated worker batches)",
    async fn() {
      const start = Date.now();
      const costs = JSON.parse(readFileSync(COSTS, "utf8"));
      const routes = Object.keys(costs).filter(c => !c.startsWith("_"));
      const numeric = routes.filter(c => Array.isArray(costs[c].range) && costs[c].range.length === 2 && costs[c].range.every(n => typeof n === "number" && Number.isFinite(n)));
      const prices = libJson(`const c = JSON.parse(readFileSync(process.env.COSTS_FILE, "utf8")); out(Object.fromEntries(Object.keys(c).filter(k => !k.startsWith("_")).map(k => [k, lib.rowPrice?.(c, k) ?? null])));`, { COSTS_FILE: COSTS });
      const cases = numeric.flatMap(call => [{ call }, ...(costs._conditional?.[call] ?? []).map(c => ({ call, param: c.param, value: c.value ?? "true" }))]);
      const driver = `const { parentPort, workerData } = require('node:worker_threads');
        (async () => {
          const { session, V1 } = await import(workerData.helpers);
          const out = [];
          for (const c of workerData.cases) {
            const s = session({ balance: 1000000000 });
            try {
              s.seed({ spent: 0 }); s.budget({ sessionBudget: 20000, transcripts: 'allow' });
              const [verb, template] = c.call.split(' ');
              const path = template.replace(/\\{[^}]+\\}/g, 'plain-id');
              const url = V1 + path + (c.param ? '?' + c.param + '=' + encodeURIComponent(c.value) : '');
              const body = ['POST', 'PATCH', 'DELETE'].includes(verb) ? ' -X ' + verb + " -d '{}'" : '';
              const cmd = 'curl -sS' + body + ' -H "x-api-key: $SOCIALCRAWL_API_KEY" "' + url + '"';
              const r = s.run(cmd, { fetch: [{ body: { data: { balance: 1000000000 } } }] });
              out.push({ ...c, exit: r.exit, raw: r.raw, decision: r.decision, spent: s.state()?.spent, worst: s.callLines().at(-1)?.worst });
            } catch (e) { out.push({ ...c, error: String(e) }); }
            finally { s.cleanup(); }
          }
          parentPort.postMessage(out);
        })().catch(e => { throw e; });`;
      const batches = Array.from({ length: 8 }, (_, i) => cases.filter((_, n) => n % 8 === i));
      const results = (await Promise.all(batches.map(cases => new Promise((resolve, reject) => {
        const w = new Worker(driver, { eval: true, workerData: { cases, helpers: pathToFileURL(join(HOOKS, "tests", "lib.mjs")).href } });
        w.once("message", resolve); w.once("error", reject); w.once("exit", code => { if (code !== 0) reject(new Error(`guard worker exit ${code}`)); });
      })))).flat();
      const elapsed = Date.now() - start;
      console.log(`    M6 P: ${results.length} real guard runs, ${numeric.length} numeric routes; skipped ${routes.length - numeric.length} unpriced; ${elapsed} ms`);
      const errors = [];
      // Re-read the inventory independently of the cases generator so omitted param runs cannot lower the expectation.
      const inventory = JSON.parse(readFileSync(COSTS, "utf8"));
      const expectedRoutes = Object.keys(inventory).filter(call => !call.startsWith("_") &&
        Array.isArray(inventory[call].range) && inventory[call].range.length === 2 &&
        inventory[call].range.every(n => typeof n === "number" && Number.isFinite(n)));
      const expectedParams = Object.entries(inventory._conditional ?? {}).flatMap(([call, entries]) =>
        expectedRoutes.includes(call) ? entries.map(({ param, value }) => ({ call, param, value: value ?? "true" })) : []);
      const expectedRuns = expectedRoutes.length + expectedParams.length;
      if (results.length !== expectedRuns) errors.push(`guard run count: expected ${expectedRuns} from fresh costs.json, read ${results.length}`);
      for (const { call, param, value } of expectedParams) {
        const matches = results.filter(r => r.call === call && r.param === param && r.value === value);
        if (matches.length !== 1) errors.push(`${call} ${param}=${value}: expected exactly one conditional guard run, read ${matches.length}`);
      }
      for (const r of results) {
        const m = /^(\d+)(?:–(\d+))? cr(?: · varies)?$/.exec(prices[r.call] ?? "");
        const top = m ? Number(m[2] ?? m[1]) : NaN;
        const counted = r.worst ?? r.spent;
        if (r.error || r.exit !== 0 || r.raw !== "" || r.decision !== null || !Number.isFinite(counted) || !(counted <= top)) errors.push(`${r.call}${r.param ? ` ${r.param}=${r.value}` : ""}: counted=${counted}, displayed=${prices[r.call]}, decision=${r.decision}, error=${r.error ?? r.raw}`);
      }
      assert(results.length === cases.length && numeric.length === 639 && routes.length - numeric.length === 6, "all 639 numeric routes and each conditional tested; six unpriced skipped");
      assert(errors.length === 0, `M6 P: shown ceiling must cover guard's count (${errors.length} failures; first 12):\n${errors.slice(0, 12).join("\n")}`);
      assert(elapsed < 170000, `M6 P: guard sweep under ~170 s, read ${elapsed} ms`);
    },
  },
  {
    id: "M6 FX: 5-shared-toggle-six-buttons",
    desc: "5a-iii-A5 addition: six Button calls remain six; the sixth is a top-level toggle with a string label, shared by help, sites and More options",
    fn() {
      const reg = readFileSync(REG, "utf8");
      assert((reg.match(/\bButton\(/g) ?? []).length === 6, "six Button calls stay six");
      assert(/function toggle\(\$: [^,]+, e: [^,]+, key: string, label: string, onPress:/.test(reg), "M6 FX: top-level toggle($, e, key, label, onPress) declares a string label");
      const at = reg.indexOf("function toggle(");
      const body = reg.slice(at, reg.indexOf("\n}", at) + 2);
      assert(/Button\(\{ key, label, onPress \}\)/.test(body), "toggle owns Button({ key, label, onPress }): shorthand label is its plain string parameter");
      for (const key of ["help-toggle", "sites-toggle"]) assert(new RegExp("toggle\\(\\$, e, ['\"]" + key).test(reg), `${key} uses toggle`);
      assert(/toggle\(\$, e, [`'"]more-/.test(reg), "More options uses the same toggle");
    },
  },
  {
    id: "M6 FX: 5-more-prompts-no-built-url",
    desc: "More options uses moreText as its only prompt builder; register.tsx holds no URL literal or API host, and no requestOf/endpointText builds a More call",
    fn() {
      const reg = readFileSync(REG, "utf8");
      assert(/\bmoreText\(/.test(reg), "M6 FX: register uses moreText for More calls");
      assert(!reg.includes("https://") && !reg.includes("social" + "crawl.dev"), "register holds no literal https:// or API host");
      const src = readFileSync(LIB, "utf8");
      assert((src.match(/export (?:function|const) moreText\b/g) ?? []).length === 1, "one More prompt builder");
      assert((src.match(/My pick from the Endpoints tab, priced \$\{row.price\}/g) ?? []).length === 1 && !/My pick from the Endpoints tab/.test(reg), "only moreText owns the More prompt frame");
      const contexts = reg.split("moreText(").slice(1).map(s => s.slice(0, s.indexOf("\n}")));
      assert(contexts.every(s => !/requestOf\(|endpointText\(|https:\/\//.test(s)), "More launch path builds no URL");
    },
  },
  {
    id: "M6 FX: 5-single-inline-glossary",
    desc: "lib.ts exports SITES exactly once; no other glossary file exists under hooks/mod",
    fn() {
      const src = readFileSync(LIB, "utf8");
      assert((src.match(/export const SITES\b/g) ?? []).length === 1, "M6 FX: exactly one export const SITES");
      const files = readdirSync(join(HOOKS, "mod"));
      assert(!files.some(f => /sites|glossary/i.test(f)), "no separate glossary text file under hooks/mod");
      const line = "Tavily web search: search the web with an optional written answer";
      assert(walk(join(HOOKS, "mod")).filter(f => statSync(f).isFile() && readFileSync(f, "utf8").includes(line)).length === 1, "one inline glossary, not a second text file");
    },
  },
  {
    id: "5a-i-H1-balance-ok",
    desc: "A24/A25: `helper.mjs balance` GETs ledgerUrl('/v1/credits/balance') with the key in x-api-key and an abort signal, and prints exactly {\"ok\":true,\"balance\":<n>,\"at\":\"<ISO, whole seconds, Z>\"} and exit 0",
    fn() {
      const r = run(["balance"], { env: { SOCIALCRAWL_API_KEY: KEY }, fetch: [{ body: { data: { balance: 4210 } } }] });
      const j = oneLine(r, "ok");
      assert(JSON.stringify(Object.keys(j)) === JSON.stringify(["ok", "balance", "at"]) && j.ok === true && j.balance === 4210 && TS.test(j.at), `the line, read ${r.out.trim()}`);
      assert(r.fetches.length === 1 && r.fetches[0].url === ledgerUrl("/v1/credits/balance") && r.fetches[0].key === true && r.fetches[0].signal === true,
        `one GET to the credits/balance URL with the key and a timeout signal, read ${JSON.stringify(r.fetches)}`);
      rmSync(r.home, { recursive: true, force: true });
    },
  },
  {
    id: "5a-i-H2-key-resolution",
    desc: "A23: the key is ledger.mjs resolveKey's (imported): SOCIALCRAWL_API_KEY only when it starts sc_, else <home>/.config/socialcrawl/api_key trimmed; none, an empty file or a control character sends nothing (no-key)",
    fn() {
      const src = readFileSync(HELPER, "utf8");
      assert(/import \{[^}]*\bresolveKey\b[^}]*\} from "\.\.\/ledger\.mjs"/.test(src) && /import \{[^}]*\bledgerUrl\b[^}]*\} from "\.\.\/ledger\.mjs"/.test(src),
        "helper.mjs imports resolveKey and ledgerUrl from ../ledger.mjs");
      const ok = [{ body: { data: { balance: 7 } } }];
      failsWith("no-key", "no key anywhere", { fetch: ok }, 0);
      failsWith("no-key", "an env value not starting sc_, no file", { env: { SOCIALCRAWL_API_KEY: "TESTsecret123" }, fetch: ok }, 0);
      failsWith("no-key", "an empty key file", { keyFile: "  \n", fetch: ok }, 0);
      failsWith("no-key", "a control character in the key file", { keyFile: "sc_TEST\u0007x\n", fetch: ok }, 0);
      for (const [label, o] of [["the key file", { keyFile: KEY + "\n" }], ["the file, an env value not starting sc_ ignored", { keyFile: KEY, env: { SOCIALCRAWL_API_KEY: "nope" } }],
        ["the env, trimmed", { env: { SOCIALCRAWL_API_KEY: ` ${KEY} ` } }]]) {
        const r = run(["balance"], { ...o, fetch: ok });
        assert(oneLine(r, label).balance === 7 && r.fetches.length === 1, `${label}: one request and the balance, read ${r.out.trim()}`, r);
        rmSync(r.home, { recursive: true, force: true });
      }
    },
  },
  {
    id: "5a-i-H3-balance-failures",
    desc: "A24/A25: a non-OK status is http, a body without a finite data.balance is body, a network error is network; each one line, exit 0, the key nowhere",
    fn() {
      const k = { SOCIALCRAWL_API_KEY: KEY };
      failsWith("http", "401", { env: k, fetch: [{ status: 401, body: { error: "x" } }] }, 1);
      failsWith("http", "500", { env: k, fetch: [{ status: 500, body: { data: { balance: 9 } } }] }, 1);
      for (const body of ["not json", { data: { balance: "4210" } }, { data: { balance: null } }, { data: {} }, {}, [], null]) {
        failsWith("body", `body ${JSON.stringify(body)}`, { env: k, fetch: [{ body: body === null ? "null" : body }] }, 1);
      }
      failsWith("network", "a network error", { env: k, fetch: [{ throw: true }] }, 1);
    },
  },
  {
    id: "5a-i-H4-hang-and-dead-proxy",
    desc: "A26: a fake that hangs gives {\"ok\":false,\"reason\":\"timeout\"} and the dead proxy (the real fetch) gives ok:false, each within 6 s",
    fn() {
      const k = { SOCIALCRAWL_API_KEY: KEY };
      const hang = failsWith("timeout", "a hanging fake", { env: k, fetch: [{ hang: true }] }, 1);
      assert(hang.ms < 6000, `the hang ends within 6 s, read ${hang.ms} ms`);
      const r = run(["balance"], { env: k });
      const j = oneLine(r, "dead proxy");
      assert(j.ok === false && (j.reason === "network" || j.reason === "timeout") && r.ms < 6000, `dead proxy: ok false within 6 s, read ${r.out.trim()} after ${r.ms} ms`);
      rmSync(r.home, { recursive: true, force: true });
    },
  },
  {
    id: "5a-i-H5-heartbeat-write",
    desc: "A27-A29: `helper.mjs heartbeat <sid>` writes <revxl>/heartbeat/socialcrawl-superengine/<sid>.json, UTF-8 with no mark, the v1 keys in order and ts in whole seconds, prints nothing, exit 0, leaves no temporary file; a rerun replaces it whole, never appends",
    fn() {
      let first = null;
      const r = run(["heartbeat", "abc-123"], {
        setup(home) { mkdirSync(own(home), { recursive: true }); writeFileSync(join(own(home), "abc-123.json"), "an older line\n"); },
      });
      assert(r.rc === 0 && r.out === "" && r.err === "", `silent, exit 0, read ${r.rc} ${JSON.stringify(r.out + r.err)}`);
      const f = join(own(r.home), "abc-123.json");
      const raw = readFileSync(f);
      assert(raw[0] === 0x7b, `starts "{" with no byte order mark, read ${raw[0]}`);
      first = raw.toString("utf8");
      assert(!first.includes("\n") && !first.includes("older"), `the file is the record alone, read ${JSON.stringify(first)}`);
      const j = JSON.parse(first);
      assert(JSON.stringify(Object.keys(j)) === JSON.stringify(["v", "plugin", "version", "pane_command", "session_id", "ts"]), `key order, read ${Object.keys(j)}`);
      assert(j.v === 1 && j.plugin === PLUGIN && j.version === VERSION && j.pane_command === "/socialcrawl-budget" && j.session_id === "abc-123" && TS.test(j.ts),
        `the values, read ${first}`);
      assert(JSON.stringify(readdirSync(own(r.home))) === JSON.stringify(["abc-123.json"]), `one file, no temporary left, read ${readdirSync(own(r.home))}`);
      const again = run(["heartbeat", "abc-123"], { home: r.home });
      const second = readFileSync(f, "utf8");
      assert(again.rc === 0 && !second.includes("\n") && JSON.parse(second).session_id === "abc-123", `a rerun replaces it, read ${JSON.stringify(second)}`);
      assert(readdirSync(own(r.home)).length === 1, `still one file, read ${readdirSync(own(r.home))}`);
      rmSync(r.home, { recursive: true, force: true });
    },
  },
  {
    id: "5a-i-H6-heartbeat-prune",
    desc: "A30: each write deletes this plugin's own *.json/*.tmp older than 7 days; a 6-day-old file, another file type and anything under heartbeat/<other-plugin>/ stay",
    fn() {
      const r = run(["heartbeat", "s1"], {
        setup(home) {
          const mine = own(home);
          const other = join(home, "revxl", "heartbeat", "other-plugin");
          mkdirSync(mine, { recursive: true });
          mkdirSync(other, { recursive: true });
          for (const [dir, name, days] of [[mine, "old.json", 8], [mine, "old.tmp", 8], [mine, "six.json", 6], [mine, "notes.txt", 8], [other, "old.json", 30]]) {
            writeFileSync(join(dir, name), "{}");
            age(join(dir, name), days);
          }
        },
      });
      const mine = readdirSync(own(r.home)).sort();
      assert(JSON.stringify(mine) === JSON.stringify(["notes.txt", "s1.json", "six.json"]), `own folder after the prune, read ${mine}`);
      assert(existsSync(join(r.home, "revxl", "heartbeat", "other-plugin", "old.json")), "another plugin's file is never touched");
      rmSync(r.home, { recursive: true, force: true });
    },
  },
  {
    id: "5a-i-H7-heartbeat-sid-and-failures",
    desc: "A27/A31: the sid is sanitised again (A8); a sid that sanitises to nothing, or an unwritable folder, writes nothing, prints nothing and exits 0; no sid is nosession",
    fn() {
      const r = run(["heartbeat", "../evil/a.b"]);
      assert(JSON.stringify(readdirSync(own(r.home))) === JSON.stringify(["evilab.json"]) && !existsSync(join(r.home, "revxl", "heartbeat", "evil")),
        `sanitised to evilab, read ${readdirSync(own(r.home))}`);
      rmSync(r.home, { recursive: true, force: true });
      const none = run(["heartbeat", "../.."]);
      assert(none.rc === 0 && none.out === "" && none.err === "" && !existsSync(join(none.home, "revxl")), `nothing for an empty sid, read ${none.rc}`);
      rmSync(none.home, { recursive: true, force: true });
      const bare = run(["heartbeat"]);
      assert(existsSync(join(own(bare.home), "nosession.json")), "no sid writes nosession.json");
      rmSync(bare.home, { recursive: true, force: true });
      const blocked = run(["heartbeat", "s1"], {
        setup(home) { writeFileSync(join(home, "blocker"), "a file, not a folder"); },
        env: (home) => ({ SC_REVXL_HOME: join(home, "blocker", "revxl") }),
      });
      assert(blocked.rc === 0 && blocked.out === "" && blocked.err === "", `an unwritable folder: silent, exit 0, read ${blocked.rc} ${JSON.stringify(blocked.out + blocked.err)}`);
      rmSync(blocked.home, { recursive: true, force: true });
    },
  },
  {
    id: "5a-i-H8-heartbeat-revxl-rule",
    desc: "A27 = A9: SC_REVXL_HOME is used untrimmed when it holds more than spaces (\"  rx\" is a folder named with its spaces, under the working folder); spaces alone fall back to <USERPROFILE>/.claude/revxl",
    fn() {
      const spaced = run(["heartbeat", "s1"], { env: { SC_REVXL_HOME: "  rx" } });
      assert(existsSync(join(spaced.home, "  rx", "heartbeat", PLUGIN, "s1.json")) && !existsSync(join(spaced.home, "rx")), "\"  rx\" used as given");
      rmSync(spaced.home, { recursive: true, force: true });
      const blank = run(["heartbeat", "s1"], { env: { SC_REVXL_HOME: "   " } });
      assert(existsSync(join(own(blank.home, join(blank.home, ".claude", "revxl")), "s1.json")), "spaces alone: <home>/.claude/revxl");
      rmSync(blank.home, { recursive: true, force: true });
    },
  },
  {
    id: "5a-i-S1-mod-source",
    desc: "A2/A5/B6 (5c rewrite): the hooks module (register.tsx, lib.ts) never fetches and checks only key-file existence: no http.fetch, SOCIALCRAWL_API_KEY or x-api-key; its one model.complete is register.tsx's refresh, on haiku; and no Joe-only bit in any mod file (workspace.yml only inside the brand resolver)",
    fn() {
      for (const f of MOD) {
        const src = readFileSync(f, "utf8");
        for (const bad of [/\.http\.fetch\b/, /SOCIALCRAWL_API_KEY/, /x-api-key/i]) assert(!bad.test(src), `${f} holds ${bad}`);
      }
      const keyCheck = "$.fs.exists(`${home}/.config/socialcrawl/api_key`).catch(() => false)";
      const keyReg = readFileSync(REG, "utf8");
      assert(keyReg.includes(keyCheck) && !/api_key/i.test(keyReg.replace(keyCheck, "")) && !/api_key/i.test(readFileSync(LIB, "utf8")), "api_key appears only in its guarded existence check");
      // 5c: exactly one model call in the module, inside register.tsx's refresh, with model 'haiku'.
      const reg = readFileSync(REG, "utf8");
      const inFn = (name, at) => { const s = reg.indexOf(`\nasync function ${name}(`); const e = reg.indexOf("\n}\n", s); return s > 0 && at > s && at < e; };
      const models = MOD.flatMap((f) => [...readFileSync(f, "utf8").matchAll(/\.model\.complete\b/g)].map((m) => [f, m.index]));
      assert(models.length === 1 && models[0][0] === REG && inFn("refresh", models[0][1]) && reg.startsWith(".model.complete({ model: 'haiku',", models[0][1]),
        `one model.complete, in register.tsx's refresh, model 'haiku', read ${JSON.stringify(models)}`);
      for (const f of [...MOD, HELPER]) {
        const src = readFileSync(f, "utf8");
        for (const bad of [/r16-keyvault/i, /tasks\/findings\.md/i, /\bsealed\b/i, /C:[\\/]Users/i]) assert(!bad.test(src), `${f} holds ${bad}`);
      }
      // 5c: workspace.yml is workspace-superengine's shared config, not Joe-only; it is named only inside the brand resolver.
      const ws = [...MOD, HELPER].flatMap((f) => [...readFileSync(f, "utf8").matchAll(/workspace\.yml/gi)].map((m) => [f, m.index]));
      assert(ws.length >= 1 && ws.every(([f, at]) => f === REG && inFn("brandFile", at)), `workspace.yml only inside register.tsx's brandFile, read ${JSON.stringify(ws)}`);
    },
  },
  {
    id: "5a-ii-H9-budget-write",
    desc: "A11: `budget-write` merges the choice into <revxl>/socialcrawl-budget.json, UTF-8 with no mark, updatedAt in whole seconds with Z, updatedBy socialcrawl-budget-pane; prints {\"ok\":true,\"budget\":<the file as written>}, exit 0; leaves no temporary file and touches no other file",
    fn() {
      const home = fresh();
      const others = { "socialcrawl-day.json": '{"date":"x","spent":3}', "socialcrawl-calls.jsonl": '{"sid":"a"}\n', "credit-guard-unattended.jsonl": "{}\n",
        "socialcrawl-budget.json.lock": "1", [join("sessions", "socialcrawl-s1.json")]: '{"spent":4}', [join("sessions", "socialcrawl-s1.json.lock")]: "1" };
      mkdirSync(join(home, "revxl", "sessions"), { recursive: true });
      for (const [f, t] of Object.entries(others)) { writeFileSync(join(home, "revxl", f), t); age(join(home, "revxl", f), 1); }
      const before = Object.keys(others).map((f) => statSync(join(home, "revxl", f)).mtimeMs);
      const { j } = bw(home, '{"sessionBudget":500}');
      const raw = readFileSync(bfOf(home));
      assert(raw[0] === 0x7b, `starts "{" with no byte order mark, read ${raw[0]}`);
      const f = JSON.parse(raw.toString("utf8"));
      assert(JSON.stringify(Object.keys(j)) === '["ok","budget"]' && j.ok === true && JSON.stringify(j.budget) === JSON.stringify(f), `the line is the file as written, read ${JSON.stringify(j)}`);
      assert(JSON.stringify(Object.keys(f)) === '["sessionBudget","updatedAt","updatedBy"]' && f.sessionBudget === 500 && TS.test(f.updatedAt) && f.updatedBy === "socialcrawl-budget-pane",
        `the file, read ${raw.toString("utf8")}`);
      assert(JSON.stringify(inRevxl(home)) === JSON.stringify(["credit-guard-unattended.jsonl", BUDGET, "socialcrawl-budget.json.lock", "socialcrawl-calls.jsonl", "socialcrawl-day.json", "sessions"].sort()),
        `no temporary file and nothing new, read ${inRevxl(home)}`);
      Object.entries(others).forEach(([n, t], i) => assert(readFileSync(join(home, "revxl", n), "utf8") === t && statSync(join(home, "revxl", n)).mtimeMs === before[i], `${n} untouched`));
      assert(bw(home, '{"transcripts":"block"}').j.ok === true, "transcripts-only saved");
      Object.entries(others).forEach(([n, t], i) => assert(readFileSync(join(home, "revxl", n), "utf8") === t && statSync(join(home, "revxl", n)).mtimeMs === before[i], `${n} untouched after transcripts-only save`));
      const none = fresh();
      bw(none, '{"sessionBudget":null}');
      assert(JSON.stringify(inRevxl(none)) === JSON.stringify([BUDGET]), `with no revxl folder yet, it makes the folder and the file alone, read ${inRevxl(none)}`);
      for (const h of [home, none]) rmSync(h, { recursive: true, force: true });
    },
  },
  {
    id: "5a-ii-H10-budget-write-keys",
    desc: "A7/A8 (D55): sessionBudget null deletes the key (Automatic, D32); every key the pane doesn't own survives, equal in value, but an old routines block, which every save deletes (a session save, an Automatic save and a transcripts-only save alike)",
    fn() {
      const seed = { note: "hand-set ü", sessionBudget: 750, extra: { a: [1, 2.5, null], b: "x" }, routines: { enabled: false, perRun: 1000, perDay: 2000, x: 1 } };
      const kept = (f, label) => ["note", "extra"].forEach((k) => assert(JSON.stringify(f[k]) === JSON.stringify(seed[k]), `${label}: ${k} kept, read ${JSON.stringify(f[k])}`));
      for (const [label, json, check] of [
        ["Automatic", '{"sessionBudget":null}', (f) => !("sessionBudget" in f)],
        ["250", '{"sessionBudget":250}', (f) => f.sessionBudget === 250],
        ["transcripts only", '{"transcripts":"block"}', (f) => f.sessionBudget === 750 && f.transcripts === "block"],
      ]) {
        const home = fresh(JSON.stringify(seed));
        bw(home, json);
        const f = JSON.parse(readFileSync(bfOf(home), "utf8"));
        assert(check(f), `${label}: sessionBudget as chosen, read ${JSON.stringify(f)}`);
        assert(!("routines" in f), `${label}: the save deletes routines, read ${JSON.stringify(f)}`);
        kept(f, label);
        rmSync(home, { recursive: true, force: true });
      }
    },
  },
  {
    id: "5a-ii-H11-budget-write-invalid",
    desc: "A9/A11 (D55): G's rule, integer 1-20,000, again in the helper, and only the owned keys, sessionBudget and/or transcripts (\"block\" or \"allow\"), at least one (G2): 0, 20001, 1.5, \"500\", -1, any routines key (a once-valid routines block included, alone or beside sessionBudget) and any other shape give {\"ok\":false,\"reason\":\"invalid\"} and write nothing; 1, 20000 and null pass",
    fn() {
      const seed = '{"sessionBudget":500,"k":1}';
      const bad = ['{"sessionBudget":0}', '{"sessionBudget":20001}', '{"sessionBudget":1.5}', '{"sessionBudget":"500"}', '{"sessionBudget":-1}',
        '{"routines":{"enabled":true,"perRun":2000}}', '{"routines":{"enabled":true,"perRun":2000,"perDay":20001}}', '{"routines":{"enabled":false,"perRun":0,"perDay":4000}}',
        '{"routines":{"enabled":"true","perRun":2000,"perDay":4000}}', '{"routines":{"enabled":true,"perRun":2000,"perDay":4000,"x":1}}', '{"routines":null}',
        '{"routines":{"enabled":false,"perRun":2000,"perDay":4000}}', '{"routines":{"enabled":true,"perRun":2000,"perDay":4000}}',
        '{"sessionBudget":500,"routines":{"enabled":true,"perRun":2000,"perDay":4000}}', '{"sessionBudget":null,"routines":{"enabled":false,"perRun":2000,"perDay":4000}}',
        '{"sessionBudget":500,"other":1}', "{}", "[]", "null", '"x"', "not json", undefined];
      for (const b of bad) {
        const home = fresh(seed);
        const { j } = bw(home, b);
        assert(JSON.stringify(j) === '{"ok":false,"reason":"invalid"}', `${b}: invalid, read ${JSON.stringify(j)}`);
        assert(readFileSync(bfOf(home), "utf8") === seed && JSON.stringify(inRevxl(home)) === JSON.stringify([BUDGET]), `${b}: nothing written`);
        rmSync(home, { recursive: true, force: true });
      }
      const none = fresh();
      for (const [label, args] of [["no revxl", ["budget-write"]], ["an empty revxl", ["budget-write", "", '{"sessionBudget":500}']]]) {
        const r = run(args, { home: none });
        assert(JSON.stringify(oneLine(r, label)) === '{"ok":false,"reason":"invalid"}' && !existsSync(join(none, "revxl")), `${label}: invalid, nothing written`);
      }
      bw(none, '{"sessionBudget":0}');
      assert(!existsSync(join(none, "revxl")), "an invalid choice makes no folder");
      rmSync(none, { recursive: true, force: true });
      for (const v of [1, 20000, null]) {
        const home = fresh();
        const { j } = bw(home, `{"sessionBudget":${v}}`);
        assert(j.ok === true && (v === null ? !("sessionBudget" in j.budget) : j.budget.sessionBudget === v) && !("routines" in j.budget), `${v} passes, read ${JSON.stringify(j)}`);
        rmSync(home, { recursive: true, force: true });
      }
    },
  },
  {
    id: "5a-ii-H12-budget-write-atomic",
    desc: "A11/B2: temp + rename: when the rename fails the old file is byte-identical and no .tmp is left ({\"ok\":false,\"reason\":\"write\"}); a folder where the file goes is left alone",
    fn() {
      const pre = renameThrows();
      const seed = '{"sessionBudget":500,"k":1}';
      const home = fresh(seed);
      const { j } = bw(home, '{"sessionBudget":250}', { node: ["--import", pre.url] });
      assert(JSON.stringify(j) === '{"ok":false,"reason":"write"}', `the rename refused: write, read ${JSON.stringify(j)}`);
      assert(readFileSync(bfOf(home), "utf8") === seed, `the old file byte-identical, read ${readFileSync(bfOf(home), "utf8")}`);
      assert(JSON.stringify(inRevxl(home)) === JSON.stringify([BUDGET]), `no .tmp left, read ${inRevxl(home)}`);
      const tr = bw(home, '{"transcripts":"block"}', { node: ["--import", pre.url] }).j;
      assert(JSON.stringify(tr) === '{"ok":false,"reason":"write"}' && readFileSync(bfOf(home), "utf8") === seed && JSON.stringify(inRevxl(home)) === JSON.stringify([BUDGET]), "transcripts-only rename failure: old file byte-identical, no temporary file");
      rmSync(pre.dir, { recursive: true, force: true });
      rmSync(home, { recursive: true, force: true });
      const dir = fresh();
      mkdirSync(bfOf(dir), { recursive: true });
      writeFileSync(join(bfOf(dir), "inside"), "x");
      const d = bw(dir, '{"sessionBudget":250}').j;
      assert(JSON.stringify(d) === '{"ok":false,"reason":"write"}' && statSync(bfOf(dir)).isDirectory() && readFileSync(join(bfOf(dir), "inside"), "utf8") === "x",
        `a folder at the budget path: write, the folder untouched, read ${JSON.stringify(d)}`);
      assert(JSON.stringify(inRevxl(dir)) === JSON.stringify([BUDGET]), `no .tmp left, read ${inRevxl(dir)}`);
      rmSync(dir, { recursive: true, force: true });
    },
  },
  {
    id: "5a-ii-H13-budget-write-encodings",
    desc: "A11: the file is decoded as G:324 does: a UTF-16LE file (FF FE) or a UTF-8 one with EF BB BF is re-written as UTF-8 with no mark, its keys kept; a garbled or non-object file is replaced by a fresh file of the owned keys, with transcripts \"block\" unless the save names transcripts (0.4.1)",
    fn() {
      const le = Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from('{"keep":"é ü","sessionBudget":300,"transcripts":"block"}', "utf16le")]);
      const bom = Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from('{"keep":2,"sessionBudget":300,"transcripts":"block"}', "utf8")]);
      for (const [label, seed, keep] of [["UTF-16LE", le, "é ü"], ["UTF-8 with a mark", bom, 2]]) {
        const home = fresh(seed);
        const { j } = bw(home, '{"sessionBudget":500}');
        const raw = readFileSync(bfOf(home));
        const f = JSON.parse(raw.toString("utf8"));
        assert(j.ok === true && raw[0] === 0x7b && !raw.includes(0) && f.keep === keep && f.sessionBudget === 500 && f.transcripts === "block", `${label}: UTF-8, no mark, keys kept, read ${raw.toString("utf8")}`);
        rmSync(home, { recursive: true, force: true });
      }
      const home = fresh("not json {");
      const { j } = bw(home, '{"sessionBudget":null}');
      assert(j.ok === true && JSON.stringify(Object.keys(j.budget)) === '["transcripts","updatedAt","updatedBy"]' && j.budget.transcripts === "block", `garbled: a fresh file of the owned keys, transcripts kept blocked (0.4.1), read ${JSON.stringify(j)}`);
      rmSync(home, { recursive: true, force: true });
    },
  },
  {
    id: "5a-ii-H14-pane-guard-round-trip",
    desc: "A12 (D55): the pane writes, the guard reads: for each file budget-write writes (session 500, Automatic, the A8/A11 files), the real credit-guard.mjs on a plain paid call applies the limit the pane shows (lib.ts choiceOf), attended, in a Desktop routine and unattended alike",
    fn() {
      const rows = [];
      const caseOf = (label, prep, json, env, check) => {
        const s = session();
        if (prep) prep(s);
        const { j } = bw(s.dir, json, { root: s.revxl });
        assert(j.ok === true, `${label}: written, read ${JSON.stringify(j)}`);
        const file = readFileSync(s.bf, "utf8");
        const shown = paneShows(file);
        const g = guardOn(s, env);
        check(shown, g, s);
        for (const [who, e] of [["a routine", ROUTINE], ["unattended", { CLAUDE_CODE_SESSION_ATTENDED: "0" }]]) {
          const x = guardOn(s, e);
          assert(x.last.decision === g.last.decision && x.last.limit === g.last.limit, `${label}, ${who}: the same limit, read G ${x.last.decision} at ${x.last.limit} vs ${g.last.limit}`);
        }
        rows.push([label, JSON.stringify(JSON.parse(file)), g.last.decision, g.last.limit]);
        s.cleanup();
      };
      const AUTO = Math.min(500, Math.floor(0.25 * BALANCE));
      caseOf("session 500", null, '{"sessionBudget":500}', undefined, (p, g) =>
        assert(p.session === 500 && g.r.raw === "" && g.last.decision === "pass" && g.last.limit === 500, `500: the pane ${p.session}, G ${g.last.limit}`));
      caseOf("Automatic", (s) => s.budget({ sessionBudget: 500 }), '{"sessionBudget":null}', undefined, (p, g) =>
        assert(p.session === null && g.last.decision === "pass" && g.last.limit === AUTO, `Automatic: the pane ${p.session}, G ${g.last.limit} (automatic cap ${AUTO})`));
      caseOf("A8: unknown keys, 250", (s) => s.budget({ note: "x", extra: { a: 1 }, sessionBudget: 750 }), '{"sessionBudget":250}', undefined, (p, g) =>
        assert(p.session === 250 && g.last.limit === 250, `250: the pane ${p.session}, G ${g.last.limit}`));
      caseOf("A11: UTF-16LE re-written, 500", (s) => writeFileSync(s.bf, Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from('{"sessionBudget":300}', "utf16le")])), '{"sessionBudget":500}', undefined, (p, g) =>
        assert(p.session === 500 && g.last.limit === 500, `UTF-16LE: the pane ${p.session}, G ${g.last.limit}`));
      caseOf("A11: garbled replaced, Automatic", (s) => s.budget("not json {"), '{"sessionBudget":null}', undefined, (p, g) =>
        assert(p.session === null && g.last.limit === AUTO, `garbled: the pane ${p.session}, G ${g.last.limit}`));
      if (process.env.SC_A12_TABLE) for (const r of rows) console.log(`    A12 | ${r.join(" | ")}`);
    },
  },
  {
    id: "5a-ii-G1-guard-refuses-budget-write",
    desc: "R2-1 (H-1): the real G denies Claude's Bash or PowerShell command naming budget-write with the tamper message (k=6) through Bash, PowerShell and with no tool_name, before the fast path, a SocialCrawl URL in the same command included; the seeded 250 is untouched; balance, heartbeat and look-alike names pass",
    fn() {
      const M_BW = "SocialCrawl guard file left alone: this command names the pane's budget save step (budget-write), which holds the person's " +
        "SocialCrawl budget or spend record. Claude is not to change it (the guard refuses the plain ways; a glob, a link to the folder, an MCP tool or a script can still get past it); the person sets the limit in SocialCrawl → Settings. To look at it, use the Read tool.";
      const deny = [
        ["bash", `node "C:/x/plugins/socialcrawl-superengine/hooks/mod/helper.mjs" budget-write "C:/u/.claude/revxl" '{"sessionBudget":20000}'`],
        ["bash", `node "$HOME/.claude/plugins/cache/x/hooks/mod/helper.mjs" budget-write "$HOME/.claude/revxl" '{"sessionBudget":20000}'`],
        ["bash", `node \${CLAUDE_PLUGIN_ROOT}/hooks/mod/helper.mjs budget-write ~/.claude/revxl '{"sessionBudget":20000}'`],
        ["PowerShell", `& node C:\\x\\hooks\\mod\\helper.mjs budget-write C:\\u\\.claude\\revxl '{"sessionBudget":20000}'`],
        ["bash", `NODE helper.mjs BUDGET-WRITE x '{}'`],
        ["bash", `cd hooks/mod && node helper.mjs budget-write r '{}'`],
        ["bash", `node helper.mjs "budget-write" r '{}'`],
        ["bash", `node helper.mjs 'budget-write' r '{}'`],
        ["bash", `node helper.mjs\tbudget-write r '{}'`],
        ["bash", `x=1;node helper.mjs budget-write`],
        ["bash", `node helper.mjs budget-write r '{}' && curl -s "${V1}amazon/shop?q=a"`],   // the tamper deny comes first
      ];
      const pass = ["node helper.mjs balance", "node helper.mjs heartbeat abc", "echo budget-writer", "npm run budget-write-test", "git log --oneline", "cat my_budget-write", "ls"];
      const s = session();
      s.budget('{"sessionBudget":250}');
      for (const [tool, cmd] of deny) {
        const r = s.run(cmd, tool === "PowerShell" ? { extra: { tool_name: "PowerShell" } } : {});
        assert(r.decision === "deny" && r.message === M_BW, `${JSON.stringify(cmd)}: the k=6 tamper deny, read ${r.decision} ${JSON.stringify(r.message).slice(0, 200)}`, r);
        assert(!r.stateWritten && readFileSync(s.bf, "utf8") === '{"sessionBudget":250}', `${JSON.stringify(cmd)}: nothing counted, the budget still 250`);
      }
      // X4: with no tool_name (read as Bash, as plain.mjs:449) k=6 still denies, and a plain helper call still passes.
      const nt = s.run(deny[0][1], { extra: { tool_name: undefined } });
      assert(nt.decision === "deny" && nt.message === M_BW, `no tool_name: the k=6 tamper deny, read ${nt.decision} ${JSON.stringify(nt.message).slice(0, 200)}`, nt);
      assert(!nt.stateWritten && readFileSync(s.bf, "utf8") === '{"sessionBudget":250}', "no tool_name: nothing counted, the budget still 250");
      const np = s.run("node helper.mjs balance", { extra: { tool_name: undefined } });
      assert(np.decision === null && np.raw === "", `no tool_name: "node helper.mjs balance" passes untouched, read ${np.decision} ${JSON.stringify(np.raw).slice(0, 200)}`, np);
      for (const cmd of pass) {
        const r = s.run(cmd);
        assert(r.decision === null && r.raw === "", `${JSON.stringify(cmd)}: no deny, read ${r.decision} ${JSON.stringify(r.raw).slice(0, 200)}`, r);
      }
      assert(readFileSync(s.bf, "utf8") === '{"sessionBudget":250}', "the budget file is still 250");
      s.cleanup();
    },
  },
  {
    id: "5a-ii-S2-budget-write-source",
    desc: "A13/B1/B12 (M5): the Settings tab's Save sends both keys in one budget-write call inside its onPress; the pane is the only shipped writer (G1): no mod file calls $.fs.write, $.state or $.http or registers a tool; its one $.model is the refresh's model.complete (S1), its only command socialcrawl-budget, its one $.prompt.submit inside the launcher onPress; store holds only appearance, help entries live only in L, and routes is asked only on Settings activation, never from a draw",
    fn() {
      const reg = readFileSync(REG, "utf8");
      const askAt = reg.indexOf("function askRoutes($: Api)");
      const openAt = reg.indexOf("function openPane(");
      const switchAt = reg.indexOf("function switchTab(");
      const askEnd = reg.indexOf("\n}", askAt);
      const openEnd = reg.indexOf("\n}", openAt);
      const switchEnd = reg.indexOf("\n}", switchAt);
      const renderAt = reg.indexOf("on('ui.render'");
      const routeNames = [...reg.matchAll(/\baskRoutes\(/g)].map(m => m.index);
      assert(askAt >= 0 && askEnd > askAt && openAt > askEnd && openEnd > openAt && switchAt > openEnd && switchEnd > switchAt && renderAt > switchEnd &&
        routeNames.length === 3 && routeNames[0] === askAt + "function ".length &&
        routeNames[1] > openAt && routeNames[1] < openEnd && routeNames[2] > switchAt && routeNames[2] < switchEnd &&
        !reg.slice(renderAt).includes("askRoutes("), "askRoutes is declared once and called only in openPane and switchTab, never after the first render hook");
      const routeHelpers = [...reg.matchAll(/helper\(\$, (["'`])routes\1\)/g)].map(m => m.index);
      assert(routeHelpers.length === 1 && routeHelpers[0] > askAt && routeHelpers[0] < askEnd, "one routes helper call, inside askRoutes");
      // 5c: the one .model in the module is the refresh's model.complete (S1 pins where it sits).
      const models = MOD.flatMap((f) => [...readFileSync(f, "utf8").matchAll(/\.model\b/g)].map((m) => [f, m.index]));
      assert(models.length === 1 && models[0][0] === REG && reg.startsWith(".model.complete(", models[0][1]), `one .model in the module, the model.complete call, read ${JSON.stringify(models)}`);
      for (const f of MOD) {
        const src = readFileSync(f, "utf8");
        for (const bad of [/\.fs\.write\b/, /\.fs\.append\b/, /\.tool\b/, /\.command\.run\b/, /\.state\b/, /\.http\b/]) assert(!bad.test(src), `${f} holds ${bad}`);
        if (f !== REG) {
          assert(!/budget-write/.test(src), `${f} names no budget-write`);
          assert(!/prompt\.submit/.test(src), `${f} holds no prompt.submit (only register.tsx's launcher submits)`);
        }
      }
      const calls = reg.match(/["'`]budget-write["'`]/g) || [];
      assert(calls.length === 1, `register.tsx has one budget-write call, read ${calls.length}`);
      const commands = [...reg.matchAll(/on\('command\.run', \{ command: '([^']+)' \}/g)].map((m) => m[1]);
      assert(JSON.stringify(commands) === '["socialcrawl-budget"]' && (reg.match(/on\('command\.run'/g) || []).length === 1,
        `the only command hook is socialcrawl-budget, read ${commands}`);
      // 5b A13: one submit, inside the onPress of the launcher's one Button call (never a start, timer or render path).
      // 5c: the only other prompt.submit is the hook that records the person's prompts and passes each on unchanged.
      const HOOK = "on('prompt.submit', async ($, e, next) => {";
      assert(reg.split(HOOK).length === 2 && (reg.match(/prompt\.submit/g) || []).length === 2, `register.tsx names prompt.submit twice: the launcher's call and the one recording hook`);
      const submits = [...reg.matchAll(/\$\.prompt\.submit\b/g)].map((m) => m.index);
      const launcherAt = reg.indexOf("function launcher(");
      const btn = reg.indexOf("const button = Button({", launcherAt);
      const press = reg.indexOf("onPress: async () => {", btn);
      const btnEnd = reg.indexOf("\n  } })", btn);
      assert(submits.length === 1 && launcherAt > 0 && btn > launcherAt && press > btn && submits[0] > press && btnEnd > submits[0] && reg.slice(btn, btnEnd).split("Button(").length === 2,
        `register.tsx's one prompt.submit sits inside the launcher Button's onPress (submits ${submits}, launcher ${launcherAt}, Button ${btn}, onPress ${press}, end ${btnEnd})`);
      const paneAt = reg.indexOf("on('ui.render', { component: 'Pane', requestId: 'sc-pane' }");
      const paneEnd = reg.indexOf("\n  on(", paneAt + 1);
      const save = reg.indexOf("Button({ key: 'save'", paneAt);
      const at = reg.search(/["'`]budget-write["'`]/);
      const nextButton = reg.indexOf("Button(", save + 1);
      assert(paneAt > 0 && save > paneAt && at > save && at < paneEnd && (nextButton < 0 || at < nextButton) && reg.slice(save, at).includes("onPress:"),
        `the budget-write call sits inside the Save Button's onPress, in the Settings tab (pane ${paneAt}, save ${save}, call ${at}, end ${paneEnd})`);
      const lib = readFileSync(LIB, "utf8");
      const stores = MOD.flatMap(f => [...readFileSync(f, "utf8").matchAll(/\.store\b/g)].map(m => [f, m.index]));
      const styleAt = reg.indexOf("function styleNow(");
      const styleEnd = reg.indexOf("\n}", styleAt);
      const getAt = reg.indexOf('.store.get(APPEARANCE_KEY)');
      const styleBody = reg.slice(styleAt, styleEnd);
      assert(stores.length === 2 && stores.every(([f]) => f === REG) && reg.split('.store.get(APPEARANCE_KEY)').length === 2 && reg.split('.store.set(APPEARANCE_KEY,').length === 2 &&
        styleAt >= 0 && getAt > styleAt && getAt < styleEnd &&
        /return\s+styleOf\(\s*look\.style\s*\?\?\s*\(\s*await\s+\$\.store\.get\(APPEARANCE_KEY\)\s*\)\s*\)/.test(styleBody) &&
        lib.includes("export const APPEARANCE_KEY = 'appearance'"), "Mfix FX/P2: exactly one appearance get inside styleNow's styleOf expression (fresh choice first), and one appearance set, in R only");
      const bandAt = reg.indexOf("on('ui.render', { component: 'AbovePrompt' }");
      const bandEnd = reg.indexOf("\n  })", bandAt);
      const bandBody = reg.slice(bandAt, bandEnd);
      assert(/const below = await next\(e\)\s+try\s*\{/.test(bandBody) && /catch\s*\{\s*return below\s*\}\s*$/.test(bandBody),
        "Mfix FX/P1: everything after next(e) in the band handler is guarded by catch { return below }");
      assert(!/\.store\.(delete|keys)\b/.test(reg + lib), "no store delete or keys");
      assert((lib.match(/export const HOW_IT_WORKS\b/g) || []).length === 1 && !/(?:const|let|function) HOW_IT_WORKS\b/.test(reg) && reg.includes('HOW_IT_WORKS.flatMap('), "help declared once in L, drawn from the list in R");
      const entries = libJson('out(lib.HOW_IT_WORKS);');
      assert(entries.length === 11 && entries.every(e => !reg.includes(e.text)), "R holds no help entry text; all eleven entries live in L");
    },
  },
  {
    id: "5a-ii-Mfix-error-refusal",
    desc: "Mfix: the error refusal covers both reading and saving guard files",
    fn() {
      const words = libJson('out([lib.refusalShort("error"), lib.refusalOf("error")]);');
      assert(JSON.stringify(words) === JSON.stringify([
        "guard could not read or save its files",
        "guard could not read or save its files. Try the call again; if it keeps happening, ask Claude to check the guard's session and settings files.",
      ]), `the error refusal words, read ${JSON.stringify(words)}`);
    },
  },
  {
    id: "5a-iii-A5-look-source",
    desc: "A5/B3/B7/B8 (M6: six Button calls, shared toggle's string label, Summarize through launcher()): the Lantern look keeps the mod kit's rules in source: no hex colour in a color, borderColor or backgroundColor prop, none anywhere in register.tsx, and in lib.ts only inside its Lantern Svg section (whose only exports are Drawing, bandDial, chip, detailCards, esc, eyebrow, rowCard and sessionCard); no hover, Image, opacity or zIndex in either file; every Button a plain-text label (a label, no children, no Text, no JSX Button)",
    fn() {
      // 5b: no new module file (the source fixtures cover the hooks module whole; B10).
      assert(JSON.stringify(MOD.map((f) => f.slice(join(HOOKS, "mod").length + 1))) === '["lib.ts","register.tsx"]',
        `hooks/mod holds only lib.ts and register.tsx as .ts(x), read ${MOD.map((f) => f.slice(join(HOOKS, "mod").length + 1))}`);
      const [lib, reg] = MOD.map((f) => readFileSync(f, "utf8"));
      const HEX = /#[0-9a-fA-F]{3,8}\b/g;
      for (const [name, src] of [["register.tsx", reg], ["lib.ts", lib]]) {
        assert(!/\b(color|borderColor|backgroundColor)\s*[:=]\s*\{?\s*["'`]#[0-9a-fA-F]{3,8}/.test(src), `${name}: a hex colour in a color, borderColor or backgroundColor prop`);
        for (const bad of [/\bhover\b/i, /\bImage\b/, /opacity/i, /zIndex/i]) assert(!bad.test(src), `${name} holds ${bad}`);
      }
      const inReg = reg.match(HEX) || [];
      assert(inReg.length === 0, `register.tsx holds no hex colour (the Svg builders live in lib.ts), read ${inReg}`);
      const at = lib.indexOf("// ---- The Lantern look");
      const outside = at < 0 ? [] : lib.slice(0, at).match(HEX) || [];
      const inside = at < 0 ? [] : lib.slice(at).match(HEX) || [];
      assert(at > 0 && outside.length === 0 && inside.length > 0, `lib.ts: hex only in the Lantern Svg section (section at ${at}, outside ${outside}, inside ${inside.length})`);
      const exported = [...lib.slice(at).matchAll(/^export (?:const|function|type) (\w+)/gm)].map((m) => m[1]).sort();
      assert(JSON.stringify(exported) === '["Drawing","bandDial","chip","detailCards","esc","eyebrow","rowCard","sessionCard"]', `the Lantern section exports only Drawing, bandDial, chip, detailCards, esc, eyebrow, rowCard and sessionCard (never the palette), read ${exported}`);
      assert(!/<Button\b/.test(reg), "register.tsx draws no JSX Button: each is a Button({...}) call, read below");
      const calls = [];
      for (let i = reg.indexOf("Button("); i >= 0; i = reg.indexOf("Button(", i + 1)) {
        let depth = 0, j = i + "Button".length;
        for (; j < reg.length; j++) { if (reg[j] === "(") depth++; else if (reg[j] === ")" && --depth === 0) break; }
        calls.push(reg.slice(i, j + 1));
      }
      assert(calls.length === 6, `the six Button calls (the band's Open, a tab, the one pick, Save, the shared help/sites/More toggle, a launcher) are read, read ${calls.length}`);
      assert(calls.filter((c) => c.startsWith("Button({ key: 'sc-open', label: 'Open SocialCrawl', hotkey: 'd',")).length === 1, "the band's Open Button, hotkey d");
      for (const key of ["sc-suggested-open", "sc-roundup-open", "sc-endpoints-open", "sc-budget-open"]) assert(!reg.includes(key), `no old opener ${key}`);
      assert(reg.split("launcher($, Button, pane, 'sc-roundup-summarize', 'Summarize', 'Summarize  →', () => text, e)").length === 2, "Summarize is drawn by launcher(), once");
      // The launcher's label is its string parameter, or "Queued · <name>" while its press is in flight (5b).
      const LAUNCHER_LABEL = "label: tabs.queued === key ? (row || card ? 'Queued' : `Queued · ${name}`) : card ? 'Run  →' : row ? 'Run' : label,";
      const TOGGLE_LABEL = "Button({ key, label, onPress })";
      for (const c of calls) {
        const label = c.match(/\blabel\b(\s*:\s*(.))?/);
        assert(label && (!label[1] || label[2] === "'" || label[2] === '"' || c.includes(LAUNCHER_LABEL) || c.includes(TOGGLE_LABEL)) && !/\bchildren\b/.test(c) && !/\bText\(/.test(c),
          `a Button takes a plain-text label only (a label, no children, no Text), read ${c.slice(0, 120)}`);
      }
      assert(/const pick = \(key: string, label: string,/.test(reg), "the preset Buttons' label is pick's string parameter");
      assert(/function launcher\([^)]*\bname: string, label: string,/.test(reg), "the launcher Buttons' label and name are launcher's string parameters");
    },
  },
  {
    id: "5b-A2-endpoint-prices",
    desc: "A2/B1: lib.ts's rangeIn + rowPrice over the real hooks/costs.json for all 29 calls: each entry there with a numeric range, the label's high end range[1] (G's worst, G:763-764), never `credits`; pins prism/lookup 1–5, reddit/omni-search 5–9, search/news 2–62, tiktok/ads/top 10–100, prism/post-stats 1–500, instagram/profile 1 cr",
    fn() {
      const rows = libJson(`const costs = JSON.parse(readFileSync(process.env.COSTS_FILE, "utf8"));` +
        `out(lib.ENDPOINTS.map((e) => { const r = lib.rangeIn(costs, e.call); return [e.call, r, lib.rowPrice(costs, e.call)]; }));`, { COSTS_FILE: COSTS });
      const costs = JSON.parse(readFileSync(COSTS, "utf8"));
      assert(rows.length === 29, `29 calls, read ${rows.length}`);
      for (const [call, r, label] of rows) {
        const want = costs[call] && costs[call].range;
        assert(Array.isArray(want) && want.length === 2 && want.every(Number.isFinite) && JSON.stringify(r) === JSON.stringify(want), `${call}: the range is costs.json's, read ${JSON.stringify(r)} (costs.json ${JSON.stringify(want)})`);
        assert(label === (want[0] === want[1] ? `${want[1]} cr` : `${want[0]}–${want[1]} cr`) + (want[0] !== want[1] ? " · varies" : ""), `${call}: the label comes from range, high end range[1], read ${label}`);
      }
      const pins = { "GET prism/lookup": "1–5 cr · varies", "GET reddit/omni-search": "5–9 cr · varies", "GET search/news": "2–62 cr · varies", "GET tiktok/ads/top": "10–100 cr · varies", "POST prism/post-stats": "1–500 cr · varies", "GET instagram/profile": "1 cr" };
      for (const [call, want] of Object.entries(pins)) {
        const got = (rows.find((x) => x[0] === call) || [])[2];
        assert(got === want, `pin ${call}: ${want}, read ${got}`);
      }
    },
  },
  {
    id: "5b-A4-guard-prices-the-click",
    desc: "A4/B2/B3/B11: for the targets `mom's café #1 @x/y?z&w`, `@nike`, `nike` and a YouTube URL on every call with a target (and once on each target-less call), the URL (and post-stats' body) taken out of the submitted text, sent as one plain curl with the skill's header through the real credit-guard.mjs in a scratch session: a silent pass counted at that call's range[1]; post-stats refuses the three that aren't URLs; no text names the guard's own words",
    fn() {
      const TARGETS = ["mom's café #1 @x/y?z&w", "@nike", "nike", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"];
      const cases = libJson(`const costs = JSON.parse(readFileSync(process.env.COSTS_FILE, "utf8")); const res = [];` +
        `for (const e of lib.ENDPOINTS) for (const t of e.kind === "none" ? [""] : JSON.parse(process.env.TARGETS)) {` +
        ` const q = lib.requestOf(e, t); const price = lib.rowPrice(costs, e.call);` +
        ` res.push({ call: e.call, kind: e.kind, target: t, note: "note" in q ? q.note : null, text: "note" in q ? null : lib.endpointText(e, price, q) }); }` +
        `out(res);`, { COSTS_FILE: COSTS, TARGETS: JSON.stringify(TARGETS) });
      const costs = JSON.parse(readFileSync(COSTS, "utf8"));
      const HEADER = '-H "x-api-key: $SOCIALCRAWL_API_KEY"';   // the socialcrawl skill's API Key table, env form
      let ran = 0;
      for (const c of cases) {
        const label = `${c.call} target ${JSON.stringify(c.target)}`;
        if (c.kind === "urls" && c.target !== TARGETS[3]) {
          assert(c.note === "Post stats can't take that URL from here. Ask Claude in the chat." && c.text === null, `${label}: refused with the note, read ${JSON.stringify(c)}`);
          continue;
        }
        assert(c.note === null && typeof c.text === "string", `${label}: a text, read ${JSON.stringify(c)}`);
        for (const w of FORBIDDEN) assert(!c.text.includes(w), `${label}: the text names ${w}`);
        const m = /, (GET|POST) (https:\/\/\S+?)( with body (\{\S*\}))?\. Use one plain curl in the Bash tool /.exec(c.text);
        assert(m && m[1] === c.call.split(" ")[0] && (m[1] === "POST") === Boolean(m[4]), `${label}: the text names the call's verb, its URL and (POST) its body, read ${c.text}`);
        const cmd = m[1] === "POST"
          ? `curl -sS -X POST ${HEADER} -H "content-type: application/json" -d '${m[4]}' "${m[2]}" -o /tmp/sc-a4.json`
          : `curl -sS ${HEADER} "${m[2]}" -o /tmp/sc-a4.json`;
        const s = session();
        s.budget({ sessionBudget: 1000 });   // above post-stats' 500, so every call is within the limit
        const r = s.run(cmd);
        const worst = costs[c.call].range[1];
        const st = s.state();
        s.cleanup();
        assert(r.decision === null && r.raw === "" && st && st.spent === worst, `${label}: a silent pass counted at ${worst}, read ${r.decision} spent ${st && st.spent} ${r.message.slice(0, 240)}`, r);
        ran++;
      }
      assert(ran === 26 * 4 + 1 + 2, `107 guard runs (26 target calls x 4, post-stats' URL, 2 target-less), read ${ran}`);
    },
  },
  {
    id: "5b-A7-combos-real-files",
    desc: "A7/A8/B8/B14: lib.ts's combosOf over the real packages.json and curated-workflows.json: 48 options keyed row:id (48 unique keys, 45 distinct ids), free_web with none, each price quote.low–ceiling from the option or its curated workflow, never quote.high (pins voice-of-customer 25–120 cr, ai-visibility-audit 20–40 cr); each Combos text names its row, option, curated id and price, and none of the guard's own words",
    fn() {
      const PK = join(HOOKS, "..", "skills", "research-plays", "references", "packages.json");
      const CW = join(HOOKS, "..", "skills", "research-plays", "curated-workflows.json");
      const rows = libJson(`const rows = lib.combosOf(JSON.parse(readFileSync(process.env.PK, "utf8")), JSON.parse(readFileSync(process.env.CW, "utf8")));` +
        `out(rows.map((r) => ({ ...r, options: r.options.map((o) => ({ ...o, text: o.price === null ? null : lib.comboText(o) })) })));`, { PK, CW });
      const pk = JSON.parse(readFileSync(PK, "utf8"));
      const flows = Object.fromEntries(JSON.parse(readFileSync(CW, "utf8")).workflows.map((w) => [w.id, w]));
      assert(JSON.stringify(rows.map((r) => r.row)) === JSON.stringify(pk.rows.map((r) => r.id)), `every row in file order, read ${rows.map((r) => r.row)}`);
      const opts = rows.flatMap((r) => r.options);
      const keys = opts.map((o) => o.key);
      assert(opts.length === 48 && new Set(keys).size === 48 && new Set(opts.map((o) => o.id)).size === 45, `48 options, 48 unique keys, 45 distinct ids, read ${opts.length}, ${new Set(keys).size}, ${new Set(opts.map((o) => o.id)).size}`);
      assert(keys.every((k, i) => k === `${opts[i].row}:${opts[i].id}`), "every key is row:id");
      assert(rows.find((r) => r.row === "free_web").options.length === 0, "free_web has no options");
      for (const r of pk.rows) for (const o of r.options) {
        const src = o.curated ? flows[o.curated] : o;
        const want = src.quote.low === src.ceiling ? `${src.ceiling} cr` : `${src.quote.low}–${src.ceiling} cr`;
        const got = opts.find((x) => x.key === `${r.id}:${o.id}`);
        assert(got && got.price === want && got.curated === (o.curated || null), `${r.id}:${o.id}: priced ${want} (curated ${o.curated || "none"}), read ${JSON.stringify(got)}`);
        const text = `[SocialCrawl launcher] My pick from the Combos tab, priced ${want}: run the research-plays option "${o.label}" (packages.json row ${r.id}, option ${o.id}` +
          `${o.curated ? `, curated ${o.curated}` : ""}). Ask me only for what it can't run without, show the price gate, then run it.`;
        assert(got.text === text, `${r.id}:${o.id}: the Combos frame, read ${got.text}`);
        for (const w of FORBIDDEN) assert(!got.text.includes(w), `${r.id}:${o.id}: the text names ${w}`);
      }
      for (const [k, want] of [["people_saying:voice-of-customer", "25–120 cr"], ["ai_visibility:ai-visibility-audit", "20–40 cr"]]) {
        assert(opts.find((o) => o.key === k).price === want, `pin ${k}: ${want}, read ${opts.find((o) => o.key === k).price}`);
      }
    },
  },
  {
    id: "5c-A1-allowlist-source",
    desc: "A1/B2: the Suggested allowlist is built from the same arrays the two tabs draw: lib.ts allowOf is ENDPOINTS keyed by slugOf(call) plus the Combos rows' row:id keys; the Endpoints tab keys ENDPOINTS through endpointLauncher (slugOf), the Combos tab and the refresh both take their rows from combosNow, and the refresh's ok is allowOf of them",
    fn() {
      const [lib, reg] = MOD.map((f) => readFileSync(f, "utf8"));
      const pins = [
        [lib, "lib.ts allowOf", "export function allowOf(combos: readonly { options: readonly Combo[] }[]): Set<string> {\n  return new Set([...ENDPOINTS.map(x => slugOf(x.call)), ...combos.flatMap(r => r.options.map(o => o.key))])\n}"],
        [lib, "lib.ts picksOf's exact match", "if (typeof id === 'string' && ok.has(id) && !out.some(p => p.id === id)) out.push({ id, why: whyOf(o?.why) })"],
        [reg, "the Endpoints tab's rows", "ENDPOINTS.filter(x => x.group === g).map(x => endpointLauncher($, Button, pane, costs, x, e, style))"],
        [reg, "endpointLauncher's key", "return launcher($, Button, pane, slugOf(x.call), x.name,"],
        [reg, "the Combos tab's rows", "const rows = await combosNow($)\n"],
        [reg, "comboLauncher's key", "return launcher($, Button, pane, o.key, o.label,"],
        [reg, "the refresh's rows", "const combos = await combosNow($)\n    const ok = allowOf(combos)\n"],
        [reg, "the refresh's filter", "picksOf(r.text, ok)"],
      ];
      for (const [src, name, text] of pins) assert(src.split(text).length === 2, `${name}: exactly one ${JSON.stringify(text.slice(0, 90))}`);
      assert((reg.match(/\ballowOf\(/g) || []).length === 1 && (reg.match(/\bconst ok\b/g) || []).length === 1, "register.tsx builds the allowlist once, from allowOf");
    },
  },
  {
    id: "5c-A1-allowlist-real-files",
    desc: "A1/B1/B3/B4: over the real packages.json and curated-workflows.json, allowOf holds the 29 Endpoints keys and the 48 Combos row:id keys (77); picksOf keeps a real id exactly and drops an invented id, a changed case, a leading space, a /v1/ prefix, a verb added, the costs.json call form, a bare Combo id (site-teardown), a repeat, a non-string id and a line that isn't JSON; the 7th and later are dropped",
    fn() {
      const PK = join(HOOKS, "..", "skills", "research-plays", "references", "packages.json");
      const CW = join(HOOKS, "..", "skills", "research-plays", "curated-workflows.json");
      const reply = ["not json at all", { id: "instagram-everything" }, { id: " tiktok-ads-top" }, { id: "TIKTOK-TRENDING" }, { id: "/v1/youtube-channel" }, { id: "GET search-news" },
        { id: "GET instagram/profile" }, { id: "instagram/profile/posts" }, { id: "site-teardown" }, { id: 7 }, { why: "no id" }, { id: "instagram-profile", why: "one" }, { id: "instagram-profile", why: "again" },
        { id: "people_saying:voice-of-customer" }, { id: "website:site-teardown" }, { id: "tiktok-user-audience" }, { id: "youtube-shorts-trending" }, { id: "reddit-omni-search" },
        { id: "web-scrape" }, { id: "prism-lookup" }].map((x) => (typeof x === "string" ? x : JSON.stringify(x))).join("\n");
      const r = libJson(`const ok = lib.allowOf(lib.combosOf(JSON.parse(readFileSync(process.env.PK, "utf8")), JSON.parse(readFileSync(process.env.CW, "utf8"))));` +
        `out({ size: ok.size, keys: [...ok], picks: lib.picksOf(process.env.REPLY, ok) });`, { PK, CW, REPLY: reply });
      assert(r.size === 77 && r.keys.includes("website:site-teardown") && r.keys.includes("competitor_offer:site-teardown") && !r.keys.includes("site-teardown"),
        `77 ids: 29 Endpoints keys and 48 row:id keys, no bare Combo id, read ${r.size}`);
      assert(JSON.stringify(r.picks.map((p) => p.id)) === JSON.stringify(["instagram-profile", "people_saying:voice-of-customer", "website:site-teardown", "tiktok-user-audience", "youtube-shorts-trending", "reddit-omni-search"]),
        `the exact ids, the first of a repeat, the first 6, read ${JSON.stringify(r.picks)}`);
      assert(r.picks[0].why === "one", `the first of a repeat keeps its own reason, read ${r.picks[0].why}`);
    },
  },
  {
    id: "5d-A7-summarize-silent",
    desc: "A7/B11-B13: the Summarize text lib.ts builds from a session's facts (callRows, outputsOf, mapPath, summaryOf) — the kit's A7 world exactly, a hostile one (perplexity/research, a saved path under a Socialcrawl folder, an @, a dotted host path, a revxl and a sessions/ path, an intent phrase) and an empty one with no limit — holds none of the forbidden words, and the real research-suggest.mjs on each text is silent; R2-3: a Kelvin-sign \"look into\" path that wakes the real hook is left out; R2-4: research-suggest's *_RE set is exactly WAKE, INTENT, URL and HANDLE, and each of their top-level alternatives holds an entry of lib.ts's UNSAFE as written; M3 U7 pins both Usage sentences with known and automatic limits",
    fn() {
      const TEMP = "C:\\Users\\t\\AppData\\Local\\Temp";
      const L = (o) => JSON.stringify({ ts: "2026-10-15T12:00:00.000Z", sid: "sid-1", paths: ["/v1/instagram/profile"], worst: 1, committed: 1, decision: "pass", kind: "under-cap", limit: 500, balance: 800, balanceAt: null, ...o }) + "\n";
      const worlds = [
        { record: L({ ts: "2026-10-15T12:01:00.000Z" }) + L({ ts: "2026-10-15T12:02:00.000Z", paths: ["/v1/tiktok/ads/top"], worst: 100, decision: "deny", kind: "over-limit" }) +
            L({ ts: "2026-10-15T12:03:00.000Z", paths: ["/v1/youtube/channel", "/v1/reddit/omni-search"], worst: 10, committed: 11 }),
          cmds: [`curl -sS -H "x-key: $K" "$U" -o /tmp/sc-a.json 2>/dev/null && curl -s "$U2" > out.json`], spent: 11, limit: 500 },
        { record: L({ paths: ["/v1/perplexity/research"] }) + L({ paths: ["/v1/instagram/profile/@x"] }) + L({ ts: "2026-10-15T12:05:00.000Z" }) + L({ sid: "other", paths: ["/v1/tiktok/trending"] }),
          cmds: [`curl -s "$U" -o "/c/x/Socialcrawl Superengine/o.json" && curl -s "$U" -o ~/my.site/x.json && curl -s "$U" -o /tmp/a@b.json`,
            `curl -s "$U" -o ~/.claude/revxl/x.json && curl -s "$U" -o sessions/x.json && curl -s "$U" -o "/c/look into/x.json" && curl -s "$U" -o /tmp/ok.json`], spent: 3, limit: 500 },
        { record: "", cmds: [], spent: 0, limit: null },
      ];
      const texts = libJson(`out(JSON.parse(process.env.WORLDS).map((w) => { const rows = lib.callRows(w.record, "sid-1");` +
        ` const files = [...new Set(w.cmds.reverse().flatMap((c) => lib.outputsOf(c).map((p) => lib.mapPath(p, process.env.TEMP5, "C:/Users/t"))))];` +
        ` return lib.summaryOf(rows.paid, files, w.spent, w.limit, null); }));`, { WORLDS: JSON.stringify(worlds), TEMP5: TEMP });
      const hm = (ts) => { const d = new Date(ts); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
      const HEAD = "Summarize what this session pulled, using only the facts below and the Read tool for the saved files. Make no new calls and run no commands. ";
      // The kit's 5d A7 press sends this same text (tests/mod.test.ts).
      const want0 = HEAD + `Calls: ${hm("2026-10-15T12:03:00.000Z")} · youtube/channel, reddit/omni-search · counted 10 cr; ${hm("2026-10-15T12:01:00.000Z")} · instagram/profile · counted 1 cr. ` +
        'Saved files: "C:/Users/t/AppData/Local/Temp/sc-a.json"; "out.json". Counted: 11 of 500 credits. No Usage read yet.';
      assert(texts[0] === want0, `the kit's A7 text, read ${texts[0]}`);
      assert(texts[1].includes(`Calls: ${hm("2026-10-15T12:05:00.000Z")} · instagram/profile · counted 1 cr (2 more not listed here.)`) &&
        texts[1].includes('Saved files: "C:/Users/t/AppData/Local/Temp/ok.json" (6 more not listed here.)') && !texts[1].includes("tiktok/trending"),
        `the hostile world: its safe facts kept, the rest counted, read ${texts[1]}`);
      assert(texts[2] === HEAD + "Calls: none. Saved files: none. Counted: 0 of automatic cap credits. No Usage read yet.", `the empty world, read ${texts[2]}`);
      const BAD = [/social[\s-]?crawl/i, /research/i, /https?:\/\//i, /\bwww\./i, /@/, /revxl/i, /budget-write/i, /credit-guard/i, /sessions\//i, /\[SocialCrawl launcher\]/i, /look\s+into/i, /find\s+out\s+about/i, /my\.site\//];
      for (const [i, t] of texts.entries()) {
        for (const bad of BAD) assert(!bad.test(t), `world ${i}: the text holds ${bad}: ${t}`);
        for (const w of FORBIDDEN) assert(!t.includes(w), `world ${i}: the text names ${w}`);
        const r = ask(t);
        assert(r.exit === 0 && !r.fired && r.raw === "", `world ${i}: research-suggest is silent on the text, read ${r.exit} ${JSON.stringify(r.raw).slice(0, 300)}`);
      }
      // R2-3: research-suggest reads the prompt lowercased (RS:290), so a Kelvin sign (U+212A) reads as k. Kept, the path wakes it;
      // Summarize leaves it out.
      const kel = libJson(`const p = "C:/x/loo" + String.fromCharCode(0x212a) + " into/y.json";` +
        ` out({ p, t: lib.summaryOf(["12:00 · instagram/profile · counted 1 cr"], [p, "C:/x/ok.json"], 1, 500, null) });`);
      const would = ask(HEAD + `Calls: 12:00 · instagram/profile · counted 1 cr. Saved files: "${kel.p}". Counted: 1 of 500 credits. No Usage read yet.`);
      assert(would.fired, `the Kelvin-sign path kept would wake research-suggest, read ${would.raw.slice(0, 200)}`);
      const kt = ask(kel.t);
      assert(!kel.t.includes(kel.p) && kel.t.includes('Saved files: "C:/x/ok.json" (1 more not listed here.)') && !kt.fired && kt.raw === "",
        `Summarize leaves the Kelvin-sign path out and stays silent, read ${kel.t}`);
      // R2-4: the mirror is pinned. research-suggest's trigger constants are exactly these four, and each top-level alternative
      // of each (with \b taken off) holds, as written, an alternative of an UNSAFE entry (\b taken off). A new trigger turns this red.
      const rs = readFileSync(join(HOOKS, "research-suggest.mjs"), "utf8");
      const names = [...rs.matchAll(/^const (\w+_RE)\b/gm)].map((m) => m[1]).sort();
      const lits = [...rs.matchAll(/^const (\w+_RE) =\s*\/((?:\\.|\[(?:\\.|[^\]\\])*\]|[^\/\\\n\[])+)\/[a-z]*;/gm)];
      assert(JSON.stringify(names) === '["HANDLE_RE","INTENT_RE","URL_RE","WAKE_RE"]' && lits.length === 4, `research-suggest's *_RE set, read ${names} (${lits.length} literals)`);
      const alts = (src) => {
        const out = [];
        let depth = 0, cls = false, cur = "";
        for (let i = 0; i < src.length; i++) {
          const c = src[i];
          if (c === "\\") { cur += c + src[++i]; continue; }
          if (cls) { if (c === "]") cls = false; }
          else if (c === "[") cls = true;
          else if (c === "(") depth++;
          else if (c === ")") depth--;
          else if (c === "|" && depth === 0) { out.push(cur); cur = ""; continue; }
          cur += c;
        }
        return [...out, cur];
      };
      const nob = (s) => s.split("\\b").join("");
      const unsafe = libJson("out(lib.UNSAFE.map((r) => r.source));").flatMap(alts).map(nob);
      for (const [, name, src] of lits) for (const a of alts(src).map(nob)) {
        assert(unsafe.some((u) => a.includes(u)), `${name}'s alternative ${a} holds no UNSAFE entry: lib.ts's mirror is out of date`);
      }
      // M3: known and unknown Usage with a known limit and an automatic cap.
      const cases = [{ usage: null, limit: 500 }, { usage: 1, limit: 500 }, { usage: null, limit: null }, { usage: 1, limit: null }];
      const usageTexts = libJson(`out(JSON.parse(process.env.M3_CASES).map(({ usage, limit }) => lib.summaryOf(` +
        `["12:00 · instagram/profile · counted 1 cr", "perplexity/research"],` +
        `["C:/x/ok.json", "C:/look into/x.json", "sessions/x.json"], 17, limit, usage)));`, { M3_CASES: JSON.stringify(cases) });
      const head = "Summarize what this session pulled, using only the facts below and the Read tool for the saved files. Make no new calls and run no commands. ";
      const expected = cases.map(({ usage, limit }) => head +
        'Calls: 12:00 · instagram/profile · counted 1 cr (1 more not listed here.) Saved files: "C:/x/ok.json" (2 more not listed here.) ' +
        `Counted: 17 of ${limit === null ? "automatic cap" : "500"} credits. ` +
        (usage === null ? "No Usage read yet." : "Usage read from the ledger: 1 credit."));
      for (const [i, text] of usageTexts.entries()) {
        for (const word of FORBIDDEN) assert(!text.includes(word), `M3 U7: world ${i} names ${word}`);
        const r = ask(text);
        assert(r.exit === 0 && !r.fired && r.raw === "", `M3 U7: world ${i} stays silent, read ${r.exit} ${JSON.stringify(r.raw)}`);
      }
      assert(JSON.stringify(usageTexts) === JSON.stringify(expected), `M3 U7: exact counted/Usage prompts, read ${JSON.stringify(usageTexts)}`);
    },
  },
];
