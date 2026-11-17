#!/usr/bin/env node
// fewzhun-box: the box brain from the command line (Claude workers, the owner, the sync timer).
//   node fewzhun-box.mjs search "<question>" [spoke1,spoke2]
//   node fewzhun-box.mjs read <spoke> <path>
//   node fewzhun-box.mjs graph query "<question>" <spoke>
//   node fewzhun-box.mjs graph explain "<thing>" <spoke>
//   node fewzhun-box.mjs graph path "<from>" "<to>" <spoke>
//   node fewzhun-box.mjs sync        (owner/timer: pull notes, copy active ones, reindex changed spokes)
//   node fewzhun-box.mjs status
//   node fewzhun-box.mjs harvest <args...>      (root: py/harvest.py, e.g. run | drain | post <date> | decide ...)
//   node fewzhun-box.mjs graph-build [args...]  (root: py/graph_job.py, the nightly graph job)
//   node fewzhun-box.mjs promote [args...]      (root: py/promote.py)
// The token is read from FEWZHUN_BOX_TOKEN_FILE or ~/.config/revxl/fewzhun-box/token: never from
// the command line, never printed. The address: FEWZHUN_BOX_URL, ~/.config/revxl/fewzhun-box/url,
// or brain.json when this user can read it. Answers end with an evidence line starting "Brain:".
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { configFile, loadConfig, resolveBind } from '../lib/config.mjs';
import { sync } from '../lib/sync.mjs';
import { readJobs } from '../lib/status.mjs';

const CLIENT_DIR = path.join(os.homedir(), '.config', 'revxl', 'fewzhun-box');
const out = (s) => process.stdout.write(`${s}\n`);
const err = (s) => process.stderr.write(`${s}\n`);
const USAGE = `usage:
  fewzhun-box search "<question>" [spoke1,spoke2]
  fewzhun-box read <spoke> <path>
  fewzhun-box graph query|explain "<text>" <spoke>
  fewzhun-box graph path "<from>" "<to>" <spoke>
  fewzhun-box sync
  fewzhun-box status
  fewzhun-box harvest <args...>     (py/harvest.py)
  fewzhun-box graph-build [args...] (py/graph_job.py)
  fewzhun-box promote [args...]     (py/promote.py)`;

const HTTP_MSG = {
  400: 'the brain did not accept the request',
  401: 'the token is missing or not recognised: check the reader token in the token file',
  403: 'this token may not read that spoke',
  404: 'no such note in that spoke, or the note is not active',
  405: 'the brain only answers reads',
  500: 'the brain service hit an internal error; the owner can check its log',
  502: 'the search engine failed for every spoke; try again in a minute',
};

class Skip extends Error {}
const skip = (msg) => new Skip(msg);
const tryConfig = () => { try { return loadConfig(); } catch { return null; } };

function baseUrl() {
  const trim = (u) => u.trim().replace(/\/+$/, '');
  if (process.env.FEWZHUN_BOX_URL) return trim(process.env.FEWZHUN_BOX_URL);
  try { const u = trim(fs.readFileSync(path.join(CLIENT_DIR, 'url'), 'utf8')); if (u) return u; } catch { /* none */ }
  const c = tryConfig();
  const h = c && resolveBind(c.bind);
  return h ? `http://${h.includes(':') ? `[${h}]` : h}:${c.port}` : null;
}

const tokenFile = () => process.env.FEWZHUN_BOX_TOKEN_FILE || path.join(CLIENT_DIR, 'token');
function readToken() {
  try { return fs.readFileSync(tokenFile(), 'utf8').trim() || null; } catch { return null; }
}

async function get(pathAndQuery) {
  const url = baseUrl();
  if (!url) throw skip('no brain address: set FEWZHUN_BOX_URL or write it to ~/.config/revxl/fewzhun-box/url');
  const token = readToken();
  if (!token) throw skip('no token: set FEWZHUN_BOX_TOKEN_FILE or put the reader token in ~/.config/revxl/fewzhun-box/token');
  let r;
  try {
    r = await fetch(url + pathAndQuery, { headers: { authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(60000) });
  } catch {
    throw skip(`the brain service is not answering at ${url}`);
  }
  const text = await r.text();
  let body = null;
  try { body = JSON.parse(text); } catch { /* not JSON */ }
  if (r.status !== 200) {
    const detail = r.status === 400 && typeof body?.error === 'string' ? `: ${body.error}` : '';
    throw skip(`${HTTP_MSG[r.status] || `the brain answered HTTP ${r.status}`}${detail}`);
  }
  if (!body) throw skip('the brain answered something that is not JSON');
  return body;
}

async function cmdSearch([q, spokes]) {
  if (!q || !q.trim()) { err(USAGE); return 2; }
  const qs = new URLSearchParams({ q });
  if (spokes) qs.set('spokes', spokes);
  const r = await get(`/search?${qs}`);
  for (const h of r.results) out(`[${h.spoke}] ${h.path} | ${h.title} | ${h.date || 'undated'} | score ${Number(Number(h.score).toPrecision(3))}\n  ${h.snippet}`);
  if (!r.results.length) out(r.failed ? 'nothing found in the spokes that answered' : 'not in the brain');
  if (r.failed) out(`(not searched, spoke failed: ${Object.keys(r.failed).join(', ')})`);
  out(`Brain: ${r.results.length} notes from ${r.spokes.join(', ')}`);
  return 0;
}

async function cmdRead([spoke, rel]) {
  if (!spoke || !rel) { err(USAGE); return 2; }
  const r = await get(`/read?${new URLSearchParams({ spoke, path: rel })}`);
  out(r.text.trimEnd());
  out(`Brain: 1 notes from ${spoke} (${rel})`);
  return 0;
}

// The server enforces both the spoke scope and view flag before returning graph.json.
async function cmdGraph([sub, ...rest]) {
  const need = { query: 2, explain: 2, path: 3 }[sub];
  if (!need || rest.length !== need) { err(USAGE); return 2; }
  const spoke = rest[rest.length - 1];
  const args = rest.slice(0, -1);
  if (args.some((a) => !a.trim() || a.startsWith('-'))) throw skip('graph text may not be empty or start with "-"');
  const graph = await get(`/graph/${encodeURIComponent(spoke)}/graph.json`);
  const codeRoot = tryConfig()?.code_root || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'fbx-graph-'));
  const gj = path.join(tmp, 'graph.json');
  try {
    fs.writeFileSync(gj, `${JSON.stringify(graph)}\n`, { mode: 0o600, flag: 'wx' });
    let bin = process.env.FEWZHUN_BOX_GRAPHIFY || path.join(codeRoot, 'venv', 'bin', 'graphify');
    let argv = [sub, ...args, '--graph', gj];
    if (/\.(mjs|js)$/i.test(bin)) { argv = [bin, ...argv]; bin = process.execPath; } // test seam
    const env = { PATH: process.env.PATH || '/usr/bin:/bin', HOME: os.homedir(), LANG: 'C.UTF-8', PYTHONIOENCODING: 'utf-8' };
    const r = spawnSync(bin, argv, { encoding: 'utf8', timeout: 120000, env, windowsHide: true });
    if (r.error || r.status !== 0) throw skip(`graphify ${sub} failed: ${r.error?.code || r.signal || `exit ${r.status}`} ${(r.stderr || '').trim().slice(-200)}`);
    out(r.stdout.trimEnd());
    out(`Brain: graph of ${spoke} (graphify ${sub})`);
    return 0;
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

function cmdSync() {
  const res = sync(loadConfig(), { log: out });
  if (!res.ok) { err(`sync failed: ${res.errors.join('; ')}`); return 1; }
  out(`sync ok${res.pending.length ? ` (still pending: ${res.pending.join(', ')})` : ''}`);
  return 0;
}

async function cmdStatus() {
  const c = tryConfig();
  out(`config: ${configFile()} ${c ? '(readable)' : '(not readable by this user, or invalid)'}`);
  const url = baseUrl();
  out(`address: ${url || 'unknown (set FEWZHUN_BOX_URL)'}`);
  if (url) {
    try {
      const r = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
      out(`service: ${r.status === 200 ? 'answering' : `HTTP ${r.status}`}`);
    } catch { out('service: not answering'); }
  }
  out(`token file: ${tokenFile()} (${readToken() ? 'present' : 'missing'})`);
  if (url && readToken()) {
    try { const me = await get('/me'); out(`reader: ${me.reader}; spokes: ${me.spokes.join(', ') || 'none'}; viewer graphs: ${me.view ? 'yes' : 'no'}`); } catch (e) { out(`reader: ${e.message}`); }
  }
  const jobs = readJobs(process.env.FEWZHUN_BOX_ROOT || c?.root || '/opt/fewzhun-box');
  for (const [job, s] of Object.entries(jobs)) {
    out(`job ${job}: ${s.ok ? 'ok' : 'FAILED'} at ${s.ts || s.finished || 'unknown time'}${s.ok ? '' : ` (${String(s.reason || 'no detail').slice(0, 200)})`}`);
  }
  if (!Object.keys(jobs).length) out('jobs: no status files yet');
  return 0;
}

// The Python jobs (harvest, graph, promote): python3 <app>/py/<module>.py with the arguments passed
// through as an argv array, never through a shell. stdio is shared so their own output and exit code show.
// FEWZHUN_BOX_PYTHON overrides python3 (tests); a .mjs/.js value runs under this Node.
const PY_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'py');
function pyJob(module) {
  return (args) => {
    let bin = process.env.FEWZHUN_BOX_PYTHON || 'python3';
    let argv = ['-E', '-s', path.join(PY_DIR, `${module}.py`), ...args];
    if (/\.(mjs|js)$/i.test(bin)) { argv = [bin, ...argv]; bin = process.execPath; }
    const env = { PATH: process.env.PATH || '/usr/bin:/bin', HOME: os.homedir(), LANG: 'C.UTF-8', PYTHONIOENCODING: 'utf-8' };
    for (const k of ['FEWZHUN_BOX_CONFIG', 'SYSTEMROOT', 'SystemRoot', 'USERPROFILE']) if (process.env[k]) env[k] = process.env[k];
    const r = spawnSync(bin, argv, { stdio: 'inherit', env, windowsHide: true });
    if (r.error?.code === 'ENOENT') {
      err(`fewzhun-box: python3 is not installed, and ${module} needs it. Install it (apt-get install -y python3) and run again.`);
      return 127;
    }
    if (r.error) { err(`fewzhun-box: could not start python3 for ${module}: ${r.error.code || r.error.message}`); return 1; }
    return r.status ?? 1;
  };
}

async function main() {
  const [cmd, ...args] = process.argv.slice(2);
  const run = { search: cmdSearch, read: cmdRead, graph: cmdGraph, sync: cmdSync, status: cmdStatus,
    harvest: pyJob('harvest'), 'graph-build': pyJob('graph_job'), promote: pyJob('promote') }[cmd];
  if (!run) { err(USAGE); return 2; }
  try {
    return await run(args);
  } catch (e) {
    if (!(e instanceof Skip)) throw e;
    err(`fewzhun-box: ${e.message}`);
    out(`Brain: skipped (${e.message})`);
    return 1;
  }
}

process.exitCode = await main();
