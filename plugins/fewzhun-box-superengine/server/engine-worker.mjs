// engine-worker.mjs: one long-lived obsidian-hybrid-search 0.12.7 process for ONE spoke, so the
// embedding model loads once instead of on every query.
// Spawned by brain-server.mjs: node engine-worker.mjs <engine dist/src dir>
// with cwd and OBSIDIAN_VAULT_PATH = the spoke.
//
// It imports the engine's own modules and runs the same init as `obsidian-hybrid-search search`
// (cli.js init({ allowWipe: false }), never the wipe path), then answers newline-delimited JSON on
// stdin, one request at a time:
//   {"id":1,"q":"...","limit":24,"mode":"hybrid"} -> {"id":1,"results":[...]} | {"id":1,"error":"..."}
// Not the engine's `serve --stdio` or MCP mode: both also start background indexing and a file
// watcher (cli.js:517-521, server.js:455-458), and indexing stays with `fewzhun-box sync`.
// One spoke per process: the engine keeps its database, config and search cache in module globals
// (db.js:7, config.js:3, searcher.js:735), so spokes must never share a process.
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const dir = process.argv[2];
const out = process.stdout.write.bind(process.stdout);
console.log = (...a) => console.error(...a); // stdout is the protocol channel
console.info = console.log;
const load = (f) => import(pathToFileURL(path.join(dir, f)).href);
const [{ config }, db, emb, { search }] = await Promise.all(['config.js', 'db.js', 'embedder.js', 'searcher.js'].map(load));

// ---- cli.js init({ allowWipe: false }), 0.12.7 ----
db.openDb();
db.applyDbConfigDefaults();
db.saveConfigMeta({ vaultPath: config.vaultPath, apiBaseUrl: config.apiBaseUrl, apiModel: config.apiModel });
const modelName = config.apiKey || process.env.OPENAI_BASE_URL ? config.apiModel : `local:${config.localModel}`;
const stored = db.getStoredModel();
if (stored && stored !== modelName) {
  process.stderr.write(`[warn] Embedding model mismatch: DB has "${stored}", current env has "${modelName}".\n`);
}
const storedDim = db.getStoredEmbeddingDim();
const [, apiDim] = await Promise.all([
  emb.getContextLength(),
  storedDim === null
    ? emb.getEmbeddingDim().catch((e) => { process.stderr.write(`[worker] embedding unavailable: ${e.message}\n`); return null; })
    : null,
]);
const dim = storedDim ?? apiDim;
if (dim !== null) { emb.primeEmbeddingDim(dim); db.initVecTable(dim); }
out(`${JSON.stringify({ ready: true })}\n`);

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  let id = null;
  try {
    const r = JSON.parse(line);
    id = r.id;
    // the options `search <q> --mode m --json --limit n` passes in cli.js 0.12.7
    const results = await search(String(r.q), { mode: r.mode, limit: r.limit, threshold: 0, related: false, depth: 1, rerank: false, anchors: false });
    out(`${JSON.stringify({ id, results })}\n`);
  } catch (e) {
    out(`${JSON.stringify({ id, error: e instanceof Error ? e.message : String(e) })}\n`);
  }
}
process.exit(0); // stdin closed: the server is gone
