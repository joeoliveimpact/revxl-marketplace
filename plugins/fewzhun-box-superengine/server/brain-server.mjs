#!/usr/bin/env node
// brain-server.mjs: the box's one search service (bots over HTTP, Claude workers via the CLI,
// the read-only viewer). Ported from the frozen brain-search server (11.17):
// - asks obsidian-hybrid-search 0.12.7 per spoke through one long-lived worker per spoke
//   (the model stays loaded), at most max_procs engine requests at once;
// - hides notes that are not active (lib/notes.mjs) and AGENTS.md / README.md;
// - decays notes in spokes with decay: true, and notes marked sot_policy: decay unless the spoke is
//   "never" (sot_policy: strict never decays);
// - merges spokes by reciprocal rank (k=60), never by raw score;
// - each reader token may read only its own spokes; tokens are stored as sha256 only.
// GET only. Settings: /etc/fewzhun-box/brain.json (FEWZHUN_BOX_CONFIG). Node 20, stdlib only.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import readline from 'node:readline';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { loadConfig, resolveBind } from '../lib/config.mjs';
import { frontmatter, isActive, notANote, noteDate, weight } from '../lib/notes.mjs';
import { readJobs } from '../lib/status.mjs';

const CFG = loadConfig();
const ROOT = path.resolve(CFG.root);
const SPOKE_DIR = path.join(ROOT, 'spokes');
const GRAPH_DIR = path.join(ROOT, 'graphs');
const LOG = path.join(CFG.log_dir, 'queries.jsonl');
const ENGINE = CFG.engine;
const MODE = 'hybrid';
const TIMEOUT_MS = CFG.timeout_ms;
const MAX_PROCS = CFG.max_procs;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const WORKER = path.join(HERE, 'engine-worker.mjs');
const VIEW_HTML = fs.readFileSync(path.join(HERE, 'view', 'index.html'));
const VIEW_JS = fs.readFileSync(path.join(HERE, 'view', 'view.js'));
const SPOKES = Object.keys(CFG.spokes);
const RRF_K = 60;
const MAX_LIMIT = 20;
const DAY = 86400000;
const TICKET_MS = 60000;

// The viewer runs only its own script file; notes are shown as text, never as page code.
const VIEW_CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'";
// graphify's graph.html: inline scripts + vis-network from unpkg (pinned by graphify with SRI).
// Sandboxed (opaque origin: it can never see the viewer's token), no network calls, framable by /view only.
const GRAPH_CSP = "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js; "
  + "style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; "
  + "base-uri 'none'; form-action 'none'; frame-ancestors 'self'";
const API_CSP = "default-src 'none'; frame-ancestors 'none'";

// ---- auth: tokens.json maps reader name -> { sha256 }; scope comes from brain.json readers ----
// Re-read when the file changes, so a revoked token stops working without a restart.
const sha256 = (s) => crypto.createHash('sha256').update(s).digest();
let tok = { key: '', list: [] };
function tokenList() {
  let st;
  try { st = fs.statSync(CFG.tokensFile); } catch { return []; } // no file: nobody is let in
  const key = `${st.mtimeMs}:${st.ino}:${st.size}`;
  if (key === tok.key) return tok.list;
  let list = [];
  try {
    list = Object.entries(JSON.parse(fs.readFileSync(CFG.tokensFile, 'utf8'))).flatMap(([name, e]) => {
      if (/^[0-9a-f]{64}$/.test(e?.sha256 || '')) return [{ name, hash: Buffer.from(e.sha256, 'hex') }];
      console.error(`tokens.json: entry "${name}" has no valid sha256; ignored`);
      return [];
    });
  } catch (e) { console.error(`tokens.json unreadable (${e.message}); every token is refused`); }
  tok = { key, list };
  return list;
}
const reader = (name) => {
  const r = CFG.readers[name];
  return { name, spokes: r ? r.spokes.map(String) : [], view: r?.view === true };
};
// No header, a malformed one, or a token that matches no reader: 401 (403 is only for spokes).
function auth(req) {
  const m = /^Bearer (\S+)$/.exec(req.headers.authorization || '');
  if (!m) return { code: 401 };
  const d = sha256(m[1]);
  let hit = null;
  for (const c of tokenList()) if (crypto.timingSafeEqual(d, c.hash)) hit = c; // constant time, no early exit
  return hit ? { who: reader(hit.name) } : { code: 401 };
}

// Graph pages load in an iframe, which can't send a header: the viewer trades its token for a
// one-use ticket that names one reader and one spoke and lives 60 s. Tickets are never logged.
const tickets = new Map();
function issueTicket(name, spoke) {
  const now = Date.now();
  for (const [k, v] of tickets) if (v.exp < now) tickets.delete(k);
  const t = crypto.randomBytes(24).toString('base64url');
  tickets.set(t, { name, spoke, exp: now + TICKET_MS });
  return t;
}
function useTicket(t, spoke) {
  const v = tickets.get(t);
  if (!v) return null;
  tickets.delete(t);
  return v.exp >= Date.now() && v.spoke === spoke ? reader(v.name) : null;
}

const spokes = () => SPOKES.filter((s) => { try { return fs.lstatSync(path.join(SPOKE_DIR, s)).isDirectory(); } catch { return false; } });

function snippetOf(h, body) {
  const s = (typeof h.snippet === 'string' && h.snippet.trim()) ? h.snippet : body;
  const flat = s.replace(/\s+/g, ' ').trim();
  return flat.length <= 300 ? flat : `${flat.slice(0, 300).replace(/\s+\S*$/, '')}...`;
}

// A note's real path (symlinks resolved) must be a .md file inside its spoke;
// anything resolving elsewhere, another spoke included, is refused.
function allowedReal(spoke, file) {
  try {
    const real = fs.realpathSync(file);
    const roots = [path.join(SPOKE_DIR, spoke)]
      .map((r) => { try { return fs.realpathSync(r); } catch { return null; } }).filter(Boolean);
    return real.endsWith('.md') && roots.some((r) => real.startsWith(r + path.sep)) && fs.statSync(real).isFile() ? real : null;
  } catch { return null; }
}

// /read: no absolute paths or `..`, must name a .md note, then the realpath rule above.
function notePath(spoke, rel) {
  if (!rel || rel.includes('\0') || path.isAbsolute(rel) || /^[A-Za-z]:/.test(rel)) return null;
  if (rel.split(/[\\/]/).includes('..') || !rel.endsWith('.md') || notANote(rel.replace(/\\/g, '/'))) return null;
  return allowedReal(spoke, path.join(SPOKE_DIR, spoke, rel));
}

// ---- engine: at most MAX_PROCS requests in flight across all workers ----
// ponytail: unbounded wait queue; each call is still capped by TIMEOUT_MS once it runs.
let running = 0;
const waiting = [];
async function limited(fn) {
  if (running < MAX_PROCS) running++; else await new Promise((r) => waiting.push(r)); // a slot is handed over
  try { return await fn(); } finally { const next = waiting.shift(); if (next) next(); else running--; }
}

// One long-lived engine-worker.mjs per spoke (spawned, never a shell), started on first use and
// again after a crash, a timeout, or the spoke's index file being replaced.
const workers = new Map();
let seq = 0;
const dbIno = (dir) => { try { return fs.statSync(path.join(dir, '.obsidian-hybrid-search.db')).ino; } catch { return null; } };
function worker(spoke) {
  const dir = path.join(SPOKE_DIR, spoke);
  let w = workers.get(spoke);
  if (w && (w.child.killed || w.child.exitCode !== null || w.child.signalCode !== null || w.ino !== dbIno(dir))) {
    w.child.kill('SIGKILL');
    w = null;
  }
  if (w) return w;
  const cli = fs.realpathSync(ENGINE); // .../obsidian-hybrid-search/dist/src/cli.js; the worker loads its siblings
  // Explicit env: no OPENAI_* ever reaches the engine.
  const env = { PATH: process.env.PATH || '/usr/bin:/bin', OBSIDIAN_VAULT_PATH: dir };
  if (process.env.HOME) env.HOME = process.env.HOME; // the engine caches its model under HOME
  const child = spawn(process.execPath, [WORKER, path.dirname(cli)], { cwd: dir, env, stdio: ['pipe', 'pipe', 'pipe'] });
  w = { child, pending: new Map(), ino: dbIno(dir) };
  const me = w;
  readline.createInterface({ input: child.stdout }).on('line', (line) => {
    let m = null;
    try { m = JSON.parse(line); } catch { /* not JSON */ }
    if (!m || typeof m !== 'object' || Array.isArray(m)) {
      process.stderr.write(`[${spoke}] ignored non-protocol output: ${line.slice(0, 200)}\n`);
      return;
    }
    if (m.ready) return;
    const p = me.pending.get(m.id);
    if (!p) return;
    me.pending.delete(m.id);
    if (m.error) p.reject(new Error(m.error)); else p.resolve(m.results);
  });
  child.stderr.on('data', (d) => process.stderr.write(`[${spoke}] ${d}`));
  child.stdin.on('error', () => { /* it died; the exit handler reports it */ });
  const gone = (why) => {
    if (workers.get(spoke) === me) workers.delete(spoke);
    for (const p of me.pending.values()) p.reject(new Error(`engine worker stopped (${why})`));
    me.pending.clear();
  };
  child.on('exit', (code, sig) => gone(sig || `exit ${code}`));
  child.on('error', (e) => gone(e.message));
  workers.set(spoke, w);
  return w;
}

function engine(spoke, q, n) {
  return limited(() => new Promise((resolve, reject) => {
    let w;
    try { w = worker(spoke); } catch { return reject(new Error(`engine not found at ${ENGINE}`)); }
    const id = ++seq;
    const timer = setTimeout(() => {
      w.pending.delete(id);
      w.child.kill('SIGKILL'); // its state is unknown now; the next request starts a fresh one
      reject(new Error(`timed out after ${TIMEOUT_MS} ms`));
    }, TIMEOUT_MS);
    w.pending.set(id, {
      resolve: (hits) => { clearTimeout(timer); return Array.isArray(hits) ? resolve(hits) : reject(new Error('engine returned something that is not a hit list')); },
      reject: (e) => { clearTimeout(timer); reject(e); },
    });
    w.child.stdin.write(`${JSON.stringify({ id, q, limit: n, mode: MODE })}\n`);
  }));
}

// One spoke: engine hits -> drop hidden and out-of-bounds -> decay -> ranked list.
// ponytail: one engine call with a 4x window (min 24); widen it if filters start eating the window.
async function searchSpoke(spoke, q, limit) {
  const dir = path.join(SPOKE_DIR, spoke);
  const decays = CFG.spokes[spoke].decay ?? false;
  const raw = await engine(spoke, q, Math.max(limit * 4, 24));
  const today = Date.parse(`${new Date().toISOString().slice(0, 10)}T00:00:00Z`);
  const out = [];
  for (const h of raw) {
    if (!h || typeof h.path !== 'string') continue;
    const rel = h.path.replace(/\\/g, '/');
    if (notANote(rel)) continue;
    const file = path.resolve(dir, rel);
    if (!file.startsWith(dir + path.sep)) continue;
    const real = allowedReal(spoke, file);
    if (!real) continue;
    let text;
    try { text = fs.readFileSync(real, 'utf8'); } catch { continue; }
    const { fm, body } = frontmatter(text);
    if (!isActive(fm)) continue;
    const date = noteDate(fm);
    const age = date ? Math.round((today - Date.parse(`${date}T00:00:00Z`)) / DAY) : null;
    const base = typeof h.score === 'number' ? h.score : 0;
    const wgt = weight(decays, fm, age);
    out.push({
      spoke, path: rel,
      title: (typeof h.title === 'string' && h.title) || fm.title || path.basename(rel, '.md'),
      date,
      status: fm.status || null,
      score: base * wgt,
      weight: wgt,
      snippet: snippetOf(h, body),
    });
  }
  return out.sort((a, b) => b.score - a.score);
}

// Reciprocal rank fusion: each result scores 1/(k + rank in its own spoke). Ties go to request order.
function merge(lists, limit) {
  const all = [];
  lists.forEach((list, si) => list.forEach((r, i) => all.push({ ...r, rrf: 1 / (RRF_K + i + 1), si })));
  all.sort((a, b) => b.rrf - a.rrf || a.si - b.si);
  return all.slice(0, limit).map(({ si, ...r }) => r);
}

function asText(r) {
  const lines = r.results.map((h) => `[${h.spoke}] ${h.path} | ${h.title} | ${h.date || 'undated'} | score ${Number(h.score.toPrecision(3))}\n  ${h.snippet}`);
  if (!lines.length) lines.push(r.failed ? 'nothing found in the spokes that answered' : 'not in the brain');
  if (r.failed) lines.push(`(not searched, spoke failed: ${Object.keys(r.failed).join(', ')})`);
  return `${lines.join('\n')}\n`;
}

// Never a token, a ticket or a header: only who asked (reader name), what and the outcome.
function log(entry) {
  fs.appendFile(LOG, `${JSON.stringify({ time: new Date().toISOString(), ...entry })}\n`,
    (e) => { if (e) console.error(`query log: ${e.message}`); });
}

const BASE_HEADERS = { 'cache-control': 'no-store', 'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer' };

async function handle(req, res) {
  const t0 = Date.now();
  const ip = req.socket.remoteAddress;
  const send = (code, body, type = 'application/json', csp = API_CSP, extra = {}) => {
    res.writeHead(code, { ...BASE_HEADERS, 'content-type': `${type}; charset=utf-8`, 'content-security-policy': csp, ...extra });
    res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
  };
  try {
    const url = new URL(req.url, 'http://localhost');
    const ep = url.pathname;
    const p = url.searchParams;
    if (req.method !== 'GET') return send(405, { error: 'GET only' });
    if (ep === '/health') return send(200, { ok: true });
    if (ep === '/view' || ep === '/view/') return send(200, VIEW_HTML, 'text/html', VIEW_CSP);
    if (ep === '/view/view.js') return send(200, VIEW_JS, 'text/javascript', VIEW_CSP);
    const gm = /^\/graph\/([^/]+)\/(graph\.html|graph\.json|ticket)$/.exec(ep);
    if (ep !== '/search' && ep !== '/read' && ep !== '/me' && !gm) return send(404, { error: 'not found' });

    // ---- graph: a reader with that spoke AND view: true ----
    if (gm) {
      const [, spoke, file] = gm;
      let who;
      if (file === 'graph.html' && p.has('t')) {
        who = useTicket(p.get('t'), spoke);
        if (!who) {
          log({ ip, ep: '/graph', spoke, file, status: 401 });
          return send(401, { error: 'this graph link has expired; open it again from the viewer' });
        }
      } else {
        const a = auth(req);
        if (!a.who) {
          log({ ip, ep: '/graph', spoke, file, status: a.code });
          return send(401, { error: 'token missing or not recognised' }, undefined, undefined, { 'www-authenticate': 'Bearer' });
        }
        who = a.who;
      }
      if (!who.view || !spokes().includes(spoke) || !who.spokes.includes(spoke)) {
        log({ ip, who: who.name, ep: '/graph', spoke, file, status: 403 });
        return send(403, { error: `graph not allowed for this token: ${spoke}` });
      }
      if (file === 'ticket') {
        log({ ip, who: who.name, ep: '/graph', spoke, file, status: 200 });
        return send(200, { url: `/graph/${spoke}/graph.html?t=${issueTicket(who.name, spoke)}`, expires_in: TICKET_MS / 1000 });
      }
      const f = path.join(GRAPH_DIR, spoke, file);
      let ok = false;
      try { ok = fs.lstatSync(f).isFile(); } catch { /* no graph yet */ }
      log({ ip, who: who.name, ep: '/graph', spoke, file, status: ok ? 200 : 404, ms: Date.now() - t0 });
      if (!ok) return send(404, { error: `no graph yet for ${spoke}` });
      return file === 'graph.json' ? send(200, fs.readFileSync(f)) : send(200, fs.readFileSync(f), 'text/html', GRAPH_CSP);
    }

    const a = auth(req);
    if (!a.who) {
      log({ ip, ep, status: a.code });
      return send(401, { error: 'token missing or not recognised' }, undefined, undefined, { 'www-authenticate': 'Bearer' });
    }
    const who = a.who;
    // A spoke that doesn't exist and one this token may not read get the same 403.
    const allowed = spokes().filter((s) => who.spokes.includes(s));

    if (ep === '/me') {
      // No per-spoke details or failure reasons, which could expose another reader's notes.
      const jobs = Object.fromEntries(Object.entries(readJobs(ROOT)).map(([job, s]) => [job, { ok: !!s.ok, ts: s.ts || s.finished || null }]));
      return send(200, { reader: who.name, spokes: allowed, view: who.view, jobs });
    }

    if (ep === '/read') {
      const spoke = p.get('spoke') || '';
      const rel = p.get('path') || '';
      if (!allowed.includes(spoke)) {
        log({ ip, who: who.name, ep, spoke, path: rel, status: 403 });
        return send(403, { error: `spoke not allowed for this token: ${spoke}`, spokes: allowed });
      }
      const file = notePath(spoke, rel);
      let note = null;
      if (file) {
        const text = fs.readFileSync(file, 'utf8');
        const { fm } = frontmatter(text);
        if (isActive(fm)) {
          note = { spoke, path: rel, title: fm.title || path.basename(rel, '.md'), date: noteDate(fm), status: fm.status || null, text };
        }
      }
      // Same answer for "bad path" and "missing", so probing can't map the disk.
      log({ ip, who: who.name, ep, spoke, path: rel, status: note ? 200 : 404, ms: Date.now() - t0 });
      return note ? send(200, note) : send(404, { error: 'no such note in that spoke' });
    }

    const q = (p.get('q') || '').trim();
    const want = (p.get('spokes') || '').split(',').map((s) => s.trim()).filter(Boolean);
    const limit = Math.min(Math.max(1, Math.floor(Number(p.get('limit'))) || 6), MAX_LIMIT);
    const bad = !q ? 'q is required' : q.length > 500 ? 'q is longer than 500 characters'
      : q.startsWith('-') ? 'q may not start with "-"' : null;
    if (bad) {
      log({ ip, who: who.name, ep, q, spokes: want, status: 400 });
      return send(400, { error: bad });
    }
    const denied = want.find((s) => !allowed.includes(s));
    const use = want.length ? want : allowed;
    if (denied || !use.length) {
      log({ ip, who: who.name, ep, q, spokes: want, status: 403 });
      return send(403, { error: `spoke not allowed for this token: ${denied || '(none allowed)'}`, spokes: allowed });
    }
    const settled = await Promise.allSettled(use.map((s) => searchSpoke(s, q, limit)));
    const failed = {};
    settled.forEach((r, i) => { if (r.status === 'rejected') failed[use[i]] = r.reason.message; });
    const results = merge(settled.map((r) => (r.status === 'fulfilled' ? r.value : [])), limit);
    const all = Object.keys(failed).length === use.length;
    const ms = Date.now() - t0;
    const body = { q, spokes: use, results, ...(Object.keys(failed).length ? { failed } : {}), ms };
    log({ ip, who: who.name, ep, q, spokes: use, n: results.length, ms, status: all ? 502 : 200, ...(body.failed ? { failed: Object.keys(failed) } : {}) });
    if (body.failed) console.error(`search failed on spoke(s): ${JSON.stringify(failed)}`);
    return p.get('format') === 'text' ? send(all ? 502 : 200, asText(body), 'text/plain') : send(all ? 502 : 200, body);
  } catch (e) {
    console.error(e);
    return send(500, { error: 'internal error' });
  }
}

const host = resolveBind(CFG.bind);
if (!host) {
  console.error(`bind ${CFG.bind}: no Docker network address yet (docker0 or br-*); exiting so systemd retries`);
  process.exit(1);
}
const server = http.createServer(handle);
server.listen(CFG.port, host, () => {
  const a = server.address();
  console.log(`fewzhun-box listening on ${a.address}:${a.port} (root ${ROOT}, spokes ${spokes().join(',')}, warm ${CFG.warm}, max ${MAX_PROCS} engine requests at once)`);
  // warm: all = load every spoke's model now; lazy = on its first search (small servers).
  if (CFG.warm === 'all') for (const s of spokes()) engine(s, 'warmup', 1).catch((e) => console.error(`warm-up ${s}: ${e.message}`));
});

// Optional second listener on the tailnet (phone reading). Opened only once Tailscale is up.
if (CFG.tailnet_bind) {
  const tryTailnet = () => {
    const ip = resolveBind(CFG.tailnet_bind);
    if (!ip || ip === host) return false;
    const t = http.createServer(handle);
    t.on('error', (e) => console.error(`tailnet listener ${ip}: ${e.message}`));
    t.listen(CFG.port, ip, () => console.log(`fewzhun-box also listening on tailnet ${ip}:${t.address().port}`));
    return true;
  };
  if (!tryTailnet()) {
    console.log('tailnet: not up yet; checking every 60 s');
    const iv = setInterval(() => { if (tryTailnet()) clearInterval(iv); }, 60000);
    iv.unref();
  }
}
