// The fewzhun-box CLI: evidence line on every answer, plain-English errors, the token never printed.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import { promisify } from 'node:util';
import { spawnSync, execFile } from 'node:child_process';
import { makeBox, addToken, tokenOf, note, startServer, cleanup, PLUGIN } from './helpers.mjs';

let box; let srv; let TOKEN; let TFILE;
const CLI = path.join(PLUGIN, 'bin', 'fewzhun-box.mjs');
function cli(args, env = {}) {
  const r = spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8', timeout: 30000,
    env: { PATH: process.env.PATH, SystemRoot: process.env.SystemRoot, HOME: box.tmp, USERPROFILE: box.tmp,
      FEWZHUN_BOX_URL: srv.base, FEWZHUN_BOX_TOKEN_FILE: TFILE, FEWZHUN_BOX_CONFIG: path.join(box.tmp, 'none.json'), ...env },
  });
  const all = `${r.stdout}${r.stderr}`;
  assert.ok(!all.includes(TOKEN), `token printed by: ${args.join(' ')}`);
  return { ...r, last: r.stdout.trimEnd().split('\n').pop() };
}

before(async () => {
  box = makeBox();
  addToken(box, 'workers');
  TOKEN = tokenOf(box, 'workers');
  TFILE = path.join(box.tmp, 'client-token');
  fs.writeFileSync(TFILE, `${TOKEN}\n`, { mode: 0o600 });
  note(box.root, 'guidance', 'Guidance/refunds.md', { status: 'active', title: 'Refunds' }, 'refund within thirty days');
  note(box.root, 'log', 'Calls/x.md', { status: 'active' }, 'refund call');
  fs.mkdirSync(path.join(box.root, 'graphs', 'guidance'), { recursive: true });
  fs.writeFileSync(path.join(box.root, 'graphs', 'guidance', 'graph.json'), '{}');
  fs.writeFileSync(path.join(box.tmp, 'fake-graphify.mjs'), "console.log('graphify ' + JSON.stringify(process.argv.slice(2)));\n");
  srv = await startServer(box);
});
after(async () => { await srv?.stop(); cleanup(box); });

test('search prints results and ends with the evidence line', () => {
  const r = cli(['search', 'refund']);
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /^\[guidance\] Guidance\/refunds\.md \| refunds \| undated \| score 0\.5$/m);
  assert.equal(r.last, 'Brain: 1 notes from guidance');
});

test('nothing found says "not in the brain"', () => {
  const r = cli(['search', 'zzzunknown']);
  assert.equal(r.status, 0);
  assert.match(r.stdout, /^not in the brain$/m);
  assert.equal(r.last, 'Brain: 0 notes from guidance');
});

test('a spoke the token may not read: plain message, skipped evidence line, exit 1', () => {
  const r = cli(['search', 'refund', 'log']);
  assert.equal(r.status, 1);
  assert.equal(r.last, 'Brain: skipped (this token may not read that spoke)');
});

test('read prints the note and its evidence line; a missing note is a plain 404 message', () => {
  let r = cli(['read', 'guidance', 'Guidance/refunds.md']);
  assert.equal(r.status, 0);
  assert.match(r.stdout, /refund within thirty days/);
  assert.equal(r.last, 'Brain: 1 notes from guidance (Guidance/refunds.md)');
  r = cli(['read', 'guidance', '../log/Calls/x.md']);
  assert.equal(r.status, 1);
  assert.match(r.last, /^Brain: skipped \(no such note in that spoke/);
});

test('wrong token, no token, service down: plain messages, never the token', () => {
  const bad = path.join(box.tmp, 'bad-token');
  fs.writeFileSync(bad, 'f'.repeat(64));
  assert.match(cli(['search', 'refund'], { FEWZHUN_BOX_TOKEN_FILE: bad }).last, /^Brain: skipped \(the token is missing or not recognised/);
  assert.match(cli(['search', 'refund'], { FEWZHUN_BOX_TOKEN_FILE: path.join(box.tmp, 'missing') }).last, /^Brain: skipped \(no token/);
  assert.match(cli(['search', 'refund'], { FEWZHUN_BOX_URL: 'http://127.0.0.1:9' }).last, /^Brain: skipped \(the brain service is not answering/);
});

test('graph respects view:false even when a graph exists on disk', () => {
  const env = { FEWZHUN_BOX_ROOT: box.root, FEWZHUN_BOX_GRAPHIFY: path.join(box.tmp, 'fake-graphify.mjs') };
  let r = cli(['graph', 'query', 'how do refunds work', 'guidance'], env);
  assert.equal(r.status, 1, r.stderr);
  assert.equal(r.last, 'Brain: skipped (this token may not read that spoke)');
  r = cli(['graph', 'explain', 'refunds', 'log'], env);
  assert.equal(r.status, 1);
  assert.equal(r.last, 'Brain: skipped (this token may not read that spoke)');
  r = cli(['graph', 'query', '--help', 'guidance'], env);
  assert.equal(r.status, 1, 'flag-like text refused');
  assert.equal(cli(['graph', 'path', 'a', 'guidance'], env).status, 2, 'usage');
});

test('graph query/path/explain fetch Bearer-authenticated HTTP into a private temp file and remove it', async () => {
  const requests = [];
  const graph = { nodes: [{ id: 'http-only' }], links: [] };
  const fake = http.createServer((req, res) => {
    requests.push({ url: req.url, auth: req.headers.authorization });
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify(graph));
  });
  await new Promise((resolve) => fake.listen(0, '127.0.0.1', resolve));
  const bin = path.join(box.tmp, 'inspect-graph.mjs');
  fs.writeFileSync(bin, `import fs from 'node:fs';
const args = process.argv.slice(2); const file = args.at(-1);
fs.writeFileSync(new URL('./graph-used', import.meta.url), file);
console.log(JSON.stringify({args, graph: JSON.parse(fs.readFileSync(file)), mode: fs.statSync(file).mode & 0o777}));
if (args.includes('fail')) process.exit(1);
`);
  try {
    for (const args of [['query', 'question'], ['path', 'from', 'to'], ['explain', 'thing'], ['query', 'fail']]) {
      const r = await promisify(execFile)(process.execPath, [CLI, 'graph', ...args, 'guidance'], {
        env: { ...box.env, FEWZHUN_BOX_URL: `http://127.0.0.1:${fake.address().port}`,
          FEWZHUN_BOX_TOKEN_FILE: TFILE, FEWZHUN_BOX_ROOT: path.join(box.tmp, 'no-local-graphs'), FEWZHUN_BOX_GRAPHIFY: bin },
      }).catch((e) => e);
      const used = fs.readFileSync(path.join(box.tmp, 'graph-used'), 'utf8');
      assert.ok(!fs.existsSync(path.dirname(used)), 'temp directory deleted on success and failure');
      if (args.includes('fail')) {
        assert.equal(r.code, 1);
        continue;
      }
      const result = JSON.parse(r.stdout.split('\n')[0]);
      const file = result.args.at(-1);
      assert.deepEqual(result.args.slice(0, -1), [...args, '--graph']);
      assert.deepEqual(result.graph, graph);
      if (process.platform !== 'win32') assert.equal(result.mode, 0o600);
      assert.ok(file.startsWith(os.tmpdir() + path.sep));
      assert.ok(!fs.existsSync(path.dirname(file)), 'temp directory deleted');
    }
    assert.deepEqual(requests, Array(4).fill({ url: '/graph/guidance/graph.json', auth: `Bearer ${TOKEN}` }));
    const src = fs.readFileSync(CLI, 'utf8');
    assert.ok(!/path\.join\([^\n]*['"]graphs['"]/.test(src), 'CLI never opens graphs directly');
  } finally { await new Promise((resolve) => fake.close(resolve)); }
});

test('installed CLI uses its public graphify and own token without reading private config', { skip: process.platform === 'win32' }, () => {
  const code = path.join(box.tmp, 'public-code');
  const app = path.join(code, 'app');
  for (const dir of ['bin', 'lib']) fs.cpSync(path.join(PLUGIN, dir), path.join(app, dir), { recursive: true });
  const graphify = path.join(code, 'venv', 'bin', 'graphify');
  fs.mkdirSync(path.dirname(graphify), { recursive: true });
  fs.writeFileSync(graphify, `#!/bin/sh\nexec "${process.execPath}" -e 'const fs = require("node:fs"); const f = process.argv.at(-1); console.log("public graphify: " + fs.readFileSync(f, "utf8").trim());' -- "$@"\n`, { mode: 0o755 });
  const wrapper = path.join(box.tmp, 'fewzhun-box');
  fs.writeFileSync(wrapper, `#!/bin/sh\nexec "${process.execPath}" "${app}/bin/fewzhun-box.mjs" "$@"\n`, { mode: 0o755 });
  addToken(box, 'bot');
  const token = path.join(box.tmp, 'graph-reader-token');
  fs.writeFileSync(token, tokenOf(box, 'bot'), { mode: 0o600 });
  fs.chmodSync(box.tmp, 0o755);
  fs.chmodSync(box.root, 0o700);
  fs.chmodSync(box.etc, 0o700);
  const identity = process.getuid() === 0 ? { uid: 65534, gid: 65534 } : {};
  if (identity.uid) fs.chownSync(token, identity.uid, identity.gid);
  for (const args of [['search', 'refund'], ['read', 'guidance', 'Guidance/refunds.md'], ['graph', 'explain', 'refunds', 'guidance']]) {
    const r = spawnSync(wrapper, args, { ...identity, encoding: 'utf8', timeout: 30000,
      env: { PATH: process.env.PATH, HOME: box.tmp, FEWZHUN_BOX_CONFIG: identity.uid ? box.file : path.join(box.tmp, 'missing.json'),
        FEWZHUN_BOX_URL: srv.base, FEWZHUN_BOX_TOKEN_FILE: token } });
    assert.equal(r.status, 0, r.stderr || String(r.error));
    assert.ok(!r.stdout.includes(tokenOf(box, 'bot')), 'token stays private');
    if (args[0] === 'graph') assert.match(r.stdout, /public graphify: \{\}/);
    assert.match(r.stdout, /Brain: /);
  }
});

test('the token never goes on a command line: the CLI talks HTTP itself', () => {
  const src = fs.readFileSync(CLI, 'utf8');
  assert.ok(!/curl|wget/.test(src));
  assert.ok(!/argv[^\n]*token|token[^\n]*argv/i.test(src.replace(/never from\s+\/\/ the command line/, '')));
});

test('status reports the token file as present without printing it', () => {
  fs.mkdirSync(path.join(box.root, 'status'), { recursive: true });
  fs.mkdirSync(path.join(box.state, 'status'), { recursive: true });
  fs.writeFileSync(path.join(box.root, 'status', 'graph.json'), '{"ok":true,"ts":"night"}');
  fs.writeFileSync(path.join(box.state, 'status', 'sync.json'), '{"ok":true,"ts":"today"}');
  const r = cli(['status'], { FEWZHUN_BOX_ROOT: box.root, FEWZHUN_BOX_STATE_DIR: box.state });
  assert.equal(r.status, 0);
  assert.match(r.stdout, /token file: .* \(present\)/);
  assert.match(r.stdout, /reader: workers; spokes: guidance/);
  assert.match(r.stdout, /job graph: ok at night/);
  assert.match(r.stdout, /job sync: ok at today/);
});

test('harvest, graph-build and promote run python3 <app>/py/<module>.py with args as an argv array', () => {
  const fake = path.join(box.tmp, 'fake-python.mjs');
  fs.writeFileSync(fake, "console.log(JSON.stringify(process.argv.slice(2))); process.exit(/promote\\.py$/.test(process.argv[4]) ? 2 : 0);\n");
  const py = (m) => path.join(PLUGIN, 'py', `${m}.py`);
  const tricky = 'x; rm -rf / $(whoami) `id` | cat';
  let r = cli(['harvest', 'decide', '2026-11-17', '1', 'approve', '--by', tricky], { FEWZHUN_BOX_PYTHON: fake });
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(JSON.parse(r.stdout), ['-E', '-s', py('harvest'), 'decide', '2026-11-17', '1', 'approve', '--by', tricky]);
  r = cli(['graph-build', '--spoke', 'guidance'], { FEWZHUN_BOX_PYTHON: fake });
  assert.deepEqual(JSON.parse(r.stdout), ['-E', '-s', py('graph_job'), '--spoke', 'guidance']);
  r = cli(['promote', '--apply', '--ids', 'a,b', '--by', 'owner'], { FEWZHUN_BOX_PYTHON: fake });
  assert.deepEqual(JSON.parse(r.stdout), ['-E', '-s', py('promote'), '--apply', '--ids', 'a,b', '--by', 'owner']);
  assert.equal(r.status, 2, 'the job\'s exit code comes through');
  r = cli(['harvest', 'run'], { FEWZHUN_BOX_PYTHON: path.join(box.tmp, 'no-such-python3') });
  assert.equal(r.status, 127);
  assert.match(r.stderr, /python3 is not installed, and harvest needs it/);
});
