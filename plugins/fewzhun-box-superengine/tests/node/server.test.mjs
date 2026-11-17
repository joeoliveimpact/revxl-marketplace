// brain-server.mjs against the fake engine: auth, scope, active-only, decay, exclusions, viewer, graphs, log.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { makeBox, addToken, tokenOf, note, startServer, get, cleanup, day, PLUGIN } from './helpers.mjs';

let box; let srv; let BOT; let WORKERS; let ADMIN;
const paths = (r) => (r.json?.results || []).map((x) => `${x.spoke}/${x.path}`);
const w = (age) => 0.5 + 0.5 * Math.max(0, 1 - age / 365);
const near = (a, b) => typeof a === 'number' && Math.abs(a - b) < 1e-9;

before(async () => {
  box = makeBox();
  for (const n of ['bot', 'workers', 'admin']) addToken(box, n);
  [BOT, WORKERS, ADMIN] = ['bot', 'workers', 'admin'].map((n) => tokenOf(box, n));
  const r = box.root;
  note(r, 'log', 'fresh.md', { source_date: day(10), status: 'active', fake_score: 0.6 });
  note(r, 'log', 'old.md', { source_date: day(300), status: 'active', fake_score: 0.8 });
  note(r, 'log', 'dated.md', { date: day(300), status: 'active', fake_score: 0.75 });
  note(r, 'log', 'strict.md', { source_date: day(300), status: 'active', sot_policy: 'strict', fake_score: 0.7 });
  note(r, 'log', 'undated.md', { status: 'active', fake_score: 0.3 });
  note(r, 'log', 'draft.md', { source_date: day(1), status: 'draft', fake_score: 0.99 });
  note(r, 'log', 'gone.md', { source_date: day(1), status: 'superseded', fake_score: 0.98 });
  note(r, 'log', 'disputed.md', { source_date: day(1), status: 'conflict', fake_score: 0.97 });
  note(r, 'log', 'nostatus.md', { source_date: day(1), fake_score: 0.96 });
  note(r, 'log', 'replaced.md', { source_date: day(1), status: 'active', superseded_by: 'fresh', fake_score: 0.95 });
  note(r, 'log', 'nullsup.md', { source_date: day(1), status: 'active', superseded_by: 'null', fake_score: 0.2 });
  note(r, 'log', 'spaced.md', { source_date: day(10), status: '" Active "', fake_score: 0.1 });
  note(r, 'guidance', 'rule.md', { source_date: day(600), status: 'active', fake_score: 0.7 });
  note(r, 'guidance', 'fading.md', { source_date: day(365), status: 'active', sot_policy: 'decay', fake_score: 0.6 });
  note(r, 'guidance', 'current.md', { status: 'current', fake_score: 0.5 });
  note(r, 'guidance', 'AGENTS.md', { status: 'active', fake_score: 0.99 });
  note(r, 'guidance', 'README.md', { status: 'active', fake_score: 0.99 });
  note(r, 'guidance', 'sub/AGENTS.md', { status: 'active', fake_score: 0.99 });
  note(r, 'guidance', 'sub/readme.md', { status: 'active', fake_score: 0.99 });
  note(r, 'guidance', 'sub/keep.md', { status: 'active', fake_score: 0.1 });
  note(r, 'ops', 'a1.md', { status: 'active', fake_score: 100 });
  note(r, 'ops', 'a2.md', { status: 'active', fake_score: 90 });
  note(r, 'ops', 'aged.md', { source_date: day(365), status: 'active', sot_policy: 'decay', fake_score: 50 });
  note(r, 'ops', 'plain-old.md', { source_date: day(365), status: 'active', fake_score: 40 });
  fs.mkdirSync(path.join(r, 'vault'), { recursive: true });
  fs.writeFileSync(path.join(r, 'vault', 'README.md'), 'zebra');
  fs.writeFileSync(path.join(box.tmp, 'secret.md'), '---\nstatus: active\n---\nzebra secret outside the brain\n');
  fs.mkdirSync(path.join(r, 'graphs', 'guidance'), { recursive: true });
  fs.mkdirSync(path.join(r, 'graphs', 'ops'), { recursive: true });
  fs.writeFileSync(path.join(r, 'graphs', 'guidance', 'graph.json'), '{"nodes":[],"links":[]}');
  fs.writeFileSync(path.join(r, 'graphs', 'guidance', 'graph.html'), '<html><script>var g=1;</script></html>');
  fs.writeFileSync(path.join(r, 'graphs', 'ops', 'graph.json'), '{"nodes":[{"id":"ops-secret"}]}');
  srv = await startServer(box);
});
after(async () => { await srv?.stop(); cleanup(box); });

test('health answers without a token and returns no data', async () => {
  const r = await get(srv.base, '/health');
  assert.equal(r.status, 200);
  assert.equal(r.text, '{"ok":true}');
});

test('no token, a wrong token or a malformed one -> 401', async () => {
  for (const p of ['/search?q=zebra', '/read?spoke=guidance&path=rule.md', '/me', '/graph/guidance/graph.json']) {
    assert.equal((await get(srv.base, p)).status, 401, p);
  }
  assert.equal((await get(srv.base, '/search?q=zebra', 'f'.repeat(64))).status, 401);
  assert.equal((await get(srv.base, '/search?q=zebra', 'short')).status, 401);
  assert.equal((await get(srv.base, '/graph/guidance/graph.json', 'f'.repeat(64))).status, 401);
  const r = await fetch(`${srv.base}/search?q=zebra`, { headers: { authorization: `Basic ${BOT}` } });
  assert.equal(r.status, 401);
});

test('a spoke this token may not read and one that does not exist get the same 403', async () => {
  const forbidden = await get(srv.base, '/search?q=zebra&spokes=ops', BOT);
  const missing = await get(srv.base, '/search?q=zebra&spokes=nope', BOT);
  assert.equal(forbidden.status, 403);
  assert.equal(missing.status, 403);
  assert.equal(forbidden.text.replace('ops', 'X'), missing.text.replace('nope', 'X'));
  assert.equal((await get(srv.base, '/read?spoke=ops&path=a1.md', BOT)).status, 403);
  assert.equal((await get(srv.base, '/read?spoke=vault&path=README.md', ADMIN)).status, 403);
  const r = await get(srv.base, '/search?q=zebra&limit=20', WORKERS);
  assert.deepEqual(r.json.spokes, ['guidance']);
  assert.ok(paths(r).every((p) => p.startsWith('guidance/')));
});

test('/me reports the reader, its spokes and view', async () => {
  assert.deepEqual((await get(srv.base, '/me', BOT)).json, { reader: 'bot', spokes: ['guidance', 'log'], view: true, jobs: {} });
  assert.deepEqual((await get(srv.base, '/me', WORKERS)).json, { reader: 'workers', spokes: ['guidance'], view: false, jobs: {} });
});

test('/me reads root and sync status without disclosing job details', async () => {
  fs.mkdirSync(path.join(box.root, 'status'), { recursive: true });
  fs.mkdirSync(path.join(box.state, 'status'), { recursive: true });
  fs.writeFileSync(path.join(box.root, 'status', 'graph.json'), JSON.stringify({ ok: false, ts: 'night', reason: 'private-spoke error' }));
  fs.writeFileSync(path.join(box.state, 'status', 'sync.json'), JSON.stringify({ ok: true, ts: 'today' }));
  assert.deepEqual((await get(srv.base, '/me', BOT)).json.jobs, { graph: { ok: false, ts: 'night' }, sync: { ok: true, ts: 'today' } });
  fs.writeFileSync(path.join(box.root, 'status', 'sync.json'), JSON.stringify({ ok: false, ts: '2026-11-17T12:00:00Z' }));
  fs.writeFileSync(path.join(box.state, 'status', 'sync.json'), JSON.stringify({ ok: true, ts: '2026-11-17T11:00:00Z' }));
  assert.equal((await get(srv.base, '/me', BOT)).json.jobs.sync.ok, false, 'a newer root failure alert wins');
});

test('/read refuses a spoke symlink into the vault', async (t) => {
  const vault = path.join(box.root, 'vault');
  fs.writeFileSync(path.join(vault, 'private.md'), '---\nstatus: active\n---\nprivate vault note\n');
  const link = path.join(box.root, 'spokes', 'guidance', 'vault-link');
  try { fs.symlinkSync(vault, link, process.platform === 'win32' ? 'junction' : 'dir'); }
  catch (e) { if (e.code === 'EPERM') return t.skip('symlinks unavailable'); throw e; }
  try {
    assert.equal((await get(srv.base, '/read?spoke=guidance&path=vault-link/private.md', BOT)).status, 404);
  } finally { fs.unlinkSync(link); }
});

test('read refuses paths that climb out of the spoke (404, same as missing)', async () => {
  for (const p of ['../log/fresh.md', '..%2Flog%2Ffresh.md', 'sub/../../log/fresh.md', encodeURIComponent(path.join(box.tmp, 'secret.md')),
    '/etc/passwd', '../../../etc/passwd', '%2e%2e/%2e%2e/etc/passwd', 'nothere.md', 'rule.txt']) {
    assert.equal((await get(srv.base, `/read?spoke=guidance&path=${p}`, ADMIN)).status, 404, p);
  }
  const ok = await get(srv.base, '/read?spoke=guidance&path=rule.md', ADMIN);
  assert.equal(ok.status, 200);
  assert.match(ok.json.text, /zebra/);
});

test('only status: active is shown; any other status, none, or superseded_by is hidden', async () => {
  const r = await get(srv.base, '/search?q=zebra&spokes=log&limit=20', BOT);
  const got = paths(r);
  for (const hidden of ['draft', 'gone', 'disputed', 'nostatus', 'replaced']) assert.ok(!got.includes(`log/${hidden}.md`), hidden);
  assert.ok(got.includes('log/spaced.md'), 'status " Active " trimmed, any case');
  assert.ok(got.includes('log/nullsup.md'), 'superseded_by: null counts as unset');
  for (const p of ['draft.md', 'gone.md', 'disputed.md', 'nostatus.md', 'replaced.md']) {
    assert.equal((await get(srv.base, `/read?spoke=log&path=${p}`, BOT)).status, 404, p);
  }
  const g = paths(await get(srv.base, '/search?q=zebra&spokes=guidance&limit=20', BOT));
  assert.ok(!g.includes('guidance/current.md'), 'status current is hidden');
  assert.equal((await get(srv.base, '/read?spoke=guidance&path=current.md', BOT)).status, 404);
});

test('decay: decay spoke ages by source_date then date; strict and undated never age', async () => {
  const r = await get(srv.base, '/search?q=zebra&spokes=log&limit=20', BOT);
  const f = (p) => r.json.results.find((x) => x.path === p);
  assert.ok(paths(r).indexOf('log/fresh.md') < paths(r).indexOf('log/old.md'), 'fresh (raw 0.6) above 300-day-old (raw 0.8)');
  assert.ok(near(f('old.md').score, 0.8 * w(300)), String(f('old.md').score));
  assert.ok(near(f('dated.md').score, 0.75 * w(300)), 'date is the fallback');
  assert.equal(f('strict.md').weight, 1);
  assert.equal(f('strict.md').score, 0.7);
  assert.equal(f('undated.md').weight, 1);
  assert.equal(f('undated.md').date, null);
});

test('decay: a never spoke keeps old scores even with sot_policy: decay; a false spoke ages only sot_policy: decay', async () => {
  const r = await get(srv.base, '/search?q=zebra&spokes=guidance&limit=20', BOT);
  const f = (p) => r.json.results.find((x) => x.path === p);
  assert.equal(f('rule.md').score, 0.7, '600-day-old guidance note keeps its score');
  assert.equal(f('rule.md').weight, 1);
  assert.equal(f('fading.md').weight, 1, 'a guidance note with sot_policy: decay in a never spoke keeps its score');
  assert.equal(f('fading.md').score, 0.6);
  const o = await get(srv.base, '/search?q=zebra&spokes=ops&limit=20', ADMIN);
  const g = (p) => o.json.results.find((x) => x.path === p);
  assert.equal(g('aged.md').weight, 0.5, 'sot_policy: decay in a decay: false spoke, 365 days -> x0.5');
  assert.equal(g('aged.md').score, 25);
  assert.equal(g('plain-old.md').weight, 1, 'decay: false spoke, no sot_policy -> keeps score');
});

test('AGENTS.md and README.md never come back, at any depth', async () => {
  const got = paths(await get(srv.base, '/search?q=zebra&spokes=guidance&limit=20', ADMIN));
  assert.ok(!got.some((p) => /(agents|readme)\.md$/i.test(p)), JSON.stringify(got));
  assert.ok(got.includes('guidance/sub/keep.md'));
  for (const p of ['AGENTS.md', 'README.md', 'sub/AGENTS.md', 'sub/readme.md']) {
    assert.equal((await get(srv.base, `/read?spoke=guidance&path=${p}`, ADMIN)).status, 404, p);
  }
});

test('spokes merge by rank, not raw score; bad queries refused; text format says "not in the brain"', async () => {
  const m = paths(await get(srv.base, '/search?q=zebra&spokes=ops,guidance&limit=3', ADMIN));
  assert.deepEqual(m, ['ops/a1.md', 'guidance/rule.md', 'ops/a2.md']);
  assert.equal((await get(srv.base, '/search?q=--rerank', ADMIN)).status, 400);
  assert.equal((await get(srv.base, '/search?q=', ADMIN)).status, 400);
  const t = await get(srv.base, '/search?q=nothingmatchesthis&format=text', ADMIN);
  assert.equal(t.status, 200);
  assert.equal(t.text.trim(), 'not in the brain');
  const post = await fetch(`${srv.base}/search?q=zebra`, { method: 'POST', headers: { authorization: `Bearer ${ADMIN}` } });
  assert.equal(post.status, 405);
});

test('a crashed worker fails only its request; stray stdout is ignored', async () => {
  let r = await get(srv.base, '/search?q=crashme&spokes=ops', ADMIN);
  assert.equal(r.status, 502);
  assert.ok(r.json.failed.ops);
  r = await get(srv.base, '/search?q=zebra&spokes=ops', ADMIN);
  assert.equal(r.status, 200);
  assert.ok(r.json.results.length > 0);
  note(box.root, 'ops', 'noisy.md', { status: 'active' }, 'noisy');
  r = await get(srv.base, '/search?q=noisy&spokes=ops', ADMIN);
  assert.equal(r.status, 200);
  assert.ok(paths(r).includes('ops/noisy.md'));
});

test('viewer: strict CSP, JS in its own file, no inline script', async () => {
  const r = await get(srv.base, '/view');
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('content-security-policy'), "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'");
  assert.equal(r.headers.get('x-content-type-options'), 'nosniff');
  assert.ok(!/<script(?![^>]*\bsrc=)[^>]*>/i.test(r.text), 'no inline <script>');
  assert.match(r.text, /<script src="\/view\/view\.js"><\/script>/);
  const js = await get(srv.base, '/view/view.js');
  assert.equal(js.status, 200);
  assert.match(js.headers.get('content-type'), /javascript/);
  assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write/.test(js.text), 'notes are rendered as text only');
});

test('graphs: only a reader with the spoke AND view; tickets are one-use and spoke-bound', async () => {
  let r = await get(srv.base, '/graph/guidance/graph.json', BOT);
  assert.equal(r.status, 200);
  assert.equal(r.text, '{"nodes":[],"links":[]}');
  const other = await get(srv.base, '/graph/ops/graph.json', BOT);
  const missing = await get(srv.base, '/graph/nope/graph.json', BOT);
  assert.equal(other.status, 403);
  assert.equal(other.text.replace('ops', 'X'), missing.text.replace('nope', 'X'));
  assert.equal((await get(srv.base, '/graph/guidance/graph.json', WORKERS)).status, 403, 'view: false');
  assert.equal((await get(srv.base, '/graph/log/graph.json', BOT)).status, 404, 'allowed, no graph yet');
  r = await get(srv.base, '/graph/guidance/graph.html', BOT);
  assert.equal(r.status, 200);
  assert.match(r.headers.get('content-security-policy'), /^sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' https:\/\/unpkg\.com\/vis-network@9\.1\.6\/standalone\/umd\/vis-network\.min\.js;/);
  assert.match(r.headers.get('content-security-policy'), /connect-src 'none'/);
  const t = await get(srv.base, '/graph/guidance/ticket', BOT);
  assert.equal(t.status, 200);
  assert.match(t.json.url, /^\/graph\/guidance\/graph\.html\?t=[\w-]{20,}$/);
  r = await get(srv.base, t.json.url);
  assert.equal(r.status, 200, 'ticket opens the graph without a header');
  assert.match(r.text, /var g=1/);
  assert.equal((await get(srv.base, t.json.url)).status, 401, 'a ticket works once');
  const t2 = await get(srv.base, '/graph/guidance/ticket', BOT);
  assert.equal((await get(srv.base, t2.json.url.replace('/guidance/', '/ops/'))).status, 401, 'a ticket opens only its own spoke');
  assert.equal((await get(srv.base, '/graph/guidance/ticket', WORKERS)).status, 403);
  assert.equal((await get(srv.base, '/graph/guidance/graph.html?t=forged')).status, 401);
  srv.ticket = t2.json.url.split('t=')[1];
});

test('revoking a token takes effect without a restart', async () => {
  const box2tok = execFileSync(process.execPath, [path.join(PLUGIN, 'bin', 'tokens.mjs'), 'add', 'temp'], { env: box.env, encoding: 'utf8' });
  assert.match(box2tok, /created/);
  const T = tokenOf(box, 'temp');
  assert.equal((await get(srv.base, '/me', T)).status, 200, 'not in readers: recognised, no spokes');
  assert.deepEqual((await get(srv.base, '/me', T)).json.spokes, []);
  execFileSync(process.execPath, [path.join(PLUGIN, 'bin', 'tokens.mjs'), 'revoke', 'temp'], { env: box.env, encoding: 'utf8' });
  assert.equal((await get(srv.base, '/me', T)).status, 401);
  srv.temp = T;
});

test('every query is logged with who and what, never a token or ticket', async () => {
  await new Promise((r) => setTimeout(r, 300));
  const raw = fs.readFileSync(box.log, 'utf8');
  const lines = raw.trim().split('\n').map((l) => JSON.parse(l));
  const s = lines.find((l) => l.ep === '/search' && l.status === 200);
  assert.ok(['time', 'ip', 'who', 'q', 'spokes', 'n', 'ms'].every((k) => k in s), JSON.stringify(s));
  for (const t of [BOT, WORKERS, ADMIN, srv.temp, srv.ticket, crypto.createHash('sha256').update(BOT).digest('hex')]) {
    assert.ok(t && !raw.includes(t), 'secret in the log');
  }
  assert.ok(!srv.stderr().includes(BOT));
});

test('warm: lazy starts no engine worker until a spoke is first searched', async () => {
  const b = makeBox({ warm: 'lazy' });
  addToken(b, 'admin');
  note(b.root, 'ops', 'a.md', { status: 'active' });
  note(b.root, 'guidance', 'g.md', { status: 'active' });
  const s = await startServer(b);
  try {
    await new Promise((r) => setTimeout(r, 400));
    const starts = () => { try { return fs.readFileSync(path.join(b.root, 'starts.log'), 'utf8').trim().split('\n').filter(Boolean).map((l) => l.split(' ')[0]); } catch { return []; } };
    assert.deepEqual(starts(), []);
    assert.equal((await get(s.base, '/search?q=zebra&spokes=ops', tokenOf(b, 'admin'))).status, 200);
    assert.deepEqual(starts(), ['ops']);
  } finally { await s.stop(); cleanup(b); }
});
