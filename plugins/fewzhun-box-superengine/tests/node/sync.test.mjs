// sync: active-only copies, superseded/vanished copies removed, LF + no BOM, reindex only changed spokes
// with a scrubbed env, pending retry after a failed reindex, git clone + fast-forward pull.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { makeBox, cleanup } from './helpers.mjs';
import { loadConfig } from '../../lib/config.mjs';
import { sync } from '../../lib/sync.mjs';
import { engineRun, engineEnv } from '../../lib/engine.mjs';

let box; let cfg; let ELOG;
const vnote = (rel, fm, body = 'body text', { crlf = false, bom = false } = {}) => {
  const f = path.join(box.root, 'vault', rel);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  let t = `---\n${Object.entries(fm).map(([k, v]) => `${k}: ${v}`).join('\n')}\n---\n${body}\n`;
  if (crlf) t = t.replace(/\n/g, '\r\n');
  fs.writeFileSync(f, (bom ? '﻿' : '') + t);
};
const copy = (spoke, rel) => path.join(box.root, 'spokes', spoke, rel);
const calls = () => { try { return fs.readFileSync(ELOG, 'utf8').trim().split('\n').filter(Boolean).map((l) => JSON.parse(l)); } catch { return []; } };

before(() => {
  box = makeBox();
  process.env.FEWZHUN_BOX_STATE_DIR = box.state;
  cfg = loadConfig(box.file);
  ELOG = path.join(box.tmp, 'engine.log');
  process.env.FAKE_ENGINE_LOG = ELOG;
  process.env.OPENAI_API_KEY = 'sk-should-never-reach-the-engine';
  process.env.OPENAI_BASE_URL = 'http://example.invalid';
  vnote('Guidance/refunds.md', { status: 'active', source_date: '2026-01-02' });
  vnote('Guidance/sub/deep.md', { status: 'active' });
  vnote('Guidance/windows.md', { status: 'active' }, 'line one\nline two', { crlf: true, bom: true });
  vnote('Guidance/wip.md', { status: 'draft' });
  vnote('Guidance/old.md', { status: 'superseded' });
  vnote('Guidance/moved.md', { status: 'active', superseded_by: 'refunds' });
  vnote('Guidance/nostatus.md', { title: 'x' });
  vnote('Guidance/current.md', { status: 'current' });
  vnote('Guidance/AGENTS.md', { status: 'active' });
  vnote('Guidance/README.md', { status: 'active' });
  vnote('Calls/2026-01-01.md', { status: 'active', source_date: '2026-01-01' });
  vnote('Elsewhere/stray.md', { status: 'active' });
});
after(() => { delete process.env.FEWZHUN_BOX_STATE_DIR; delete process.env.FAKE_ENGINE_LOG; delete process.env.OPENAI_API_KEY; delete process.env.OPENAI_BASE_URL; cleanup(box); });

test('first sync copies only active notes, as LF without BOM, then reindexes changed spokes', () => {
  const r = sync(cfg);
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.ok(fs.existsSync(copy('guidance', 'Guidance/refunds.md')));
  assert.ok(fs.existsSync(copy('guidance', 'Guidance/sub/deep.md')));
  assert.ok(fs.existsSync(copy('log', 'Calls/2026-01-01.md')));
  for (const hidden of ['wip', 'old', 'moved', 'nostatus', 'current', 'AGENTS', 'README']) assert.ok(!fs.existsSync(copy('guidance', `Guidance/${hidden}.md`)), hidden);
  assert.ok(!fs.existsSync(copy('guidance', 'Elsewhere/stray.md')), 'only the spoke folders');
  const win = fs.readFileSync(copy('guidance', 'Guidance/windows.md'));
  assert.ok(!win.includes(13), 'no CR');
  assert.notEqual(win[0], 0xEF, 'no BOM');
  assert.ok(!fs.lstatSync(copy('guidance', 'Guidance/refunds.md')).isSymbolicLink(), 'a copy, not a link');
  const c = calls();
  assert.deepEqual(c.map((x) => path.basename(x.vault)).sort(), ['guidance', 'log'], 'ops has no notes, so no reindex');
  for (const x of c) {
    assert.deepEqual(x.args, ['reindex']);
    assert.ok(!x.envKeys.some((k) => k.startsWith('OPENAI_')), 'OPENAI_* scrubbed');
    assert.equal(x.ignore, '.obsidian/**');
  }
  const st = JSON.parse(fs.readFileSync(path.join(box.state, 'status', 'sync.json'), 'utf8'));
  assert.ok(!fs.existsSync(path.join(box.root, 'status', 'sync.json')));
  if (process.platform !== 'win32') assert.equal(fs.statSync(copy('guidance', 'Guidance/refunds.md')).mode & 0o777, 0o660);
  assert.equal(st.ok, true);
  assert.ok(st.ts);
  assert.deepEqual(st.pending, []);
});

test('a second sync with nothing new reindexes nothing', () => {
  fs.writeFileSync(ELOG, '');
  assert.equal(sync(cfg).ok, true);
  assert.deepEqual(calls(), []);
});

test('a note marked superseded (or deleted) loses its copy; only its spoke is reindexed', () => {
  fs.writeFileSync(ELOG, '');
  vnote('Guidance/refunds.md', { status: 'superseded', source_date: '2026-01-02' });
  fs.rmSync(path.join(box.root, 'vault', 'Guidance', 'sub', 'deep.md'));
  const r = sync(cfg);
  assert.equal(r.ok, true);
  assert.ok(!fs.existsSync(copy('guidance', 'Guidance/refunds.md')), 'superseded copy removed');
  assert.ok(!fs.existsSync(copy('guidance', 'Guidance/sub/deep.md')), 'vanished copy removed');
  assert.ok(!fs.existsSync(copy('guidance', 'Guidance/sub')), 'empty folder removed');
  assert.ok(fs.existsSync(path.join(box.root, 'spokes', 'guidance', '.obsidian-hybrid-search.db')), 'index file kept');
  assert.equal(r.spokes.guidance.removed, 2);
  assert.deepEqual(calls().map((x) => path.basename(x.vault)), ['guidance']);
});

test('a failed reindex stays pending and is retried next run', () => {
  fs.writeFileSync(ELOG, '');
  vnote('Calls/2026-01-05.md', { status: 'active' });
  process.env.FAKE_ENGINE_FAIL = '1';
  let r = sync(cfg);
  delete process.env.FAKE_ENGINE_FAIL;
  assert.equal(r.ok, false);
  assert.deepEqual(r.pending, ['log']);
  const st = JSON.parse(fs.readFileSync(path.join(box.state, 'status', 'sync.json'), 'utf8'));
  assert.equal(st.ok, false);
  assert.match(st.reason, /log: engine reindex failed/);
  fs.writeFileSync(ELOG, '');
  r = sync(cfg);
  assert.equal(r.ok, true);
  assert.deepEqual(calls().map((x) => path.basename(x.vault)), ['log'], 'no content change, but the pending spoke is reindexed');
});

test('the engine runner refuses status, --force and --rerank, and scrubs OPENAI_*', () => {
  for (const a of [['status'], ['reindex', '--force'], ['search', 'x', '--rerank']]) {
    assert.throws(() => engineRun(cfg.engine, box.root, a), /refused/);
  }
  const env = engineEnv('/x', { OPENAI_API_KEY: 'k', OPENAI_ORG: 'o', LOCAL_EMBEDDING_MODEL: 'm', PATH: '/bin' });
  assert.deepEqual(Object.keys(env).sort(), ['OBSIDIAN_IGNORE_PATTERNS', 'OBSIDIAN_VAULT_PATH', 'PATH']);
});

const hasGit = spawnSync('git', ['--version']).status === 0;
test('sync on: clones the repo, then fast-forwards and copies the new note', { skip: !hasGit && 'git not installed' }, () => {
  const b = makeBox();
  process.env.FEWZHUN_BOX_STATE_DIR = b.state;
  try {
    const src = path.join(b.tmp, 'src');
    const git = (...a) => {
      const r = spawnSync('git', ['-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-c', 'commit.gpgsign=false', '-c', 'core.autocrlf=false', ...a], { cwd: src, encoding: 'utf8' });
      assert.equal(r.status, 0, r.stderr);
    };
    fs.mkdirSync(path.join(src, 'Guidance'), { recursive: true });
    fs.writeFileSync(path.join(src, 'Guidance', 'a.md'), '---\nstatus: active\n---\nalpha\n');
    git('init', '-q');
    git('add', '.');
    git('commit', '-q', '-m', 'one');
    const raw = JSON.parse(fs.readFileSync(b.file, 'utf8'));
    raw.sync = { enabled: true, repo: src, deploy_key: path.join(b.etc, 'deploy_key'), interval_min: 15 };
    fs.writeFileSync(b.file, JSON.stringify(raw));
    const c = loadConfig(b.file);
    let r = sync(c);
    assert.equal(r.git, 'cloned', JSON.stringify(r.errors));
    assert.ok(fs.existsSync(path.join(b.root, 'spokes', 'guidance', 'Guidance', 'a.md')));
    fs.writeFileSync(path.join(src, 'Guidance', 'b.md'), '---\nstatus: active\n---\nbeta\n');
    git('add', '.');
    git('commit', '-q', '-m', 'two');
    r = sync(c);
    assert.equal(r.git, 'pulled', JSON.stringify(r.errors));
    assert.equal(r.ok, true, JSON.stringify(r.errors));
    assert.ok(fs.existsSync(path.join(b.root, 'spokes', 'guidance', 'Guidance', 'b.md')));
  } finally { process.env.FEWZHUN_BOX_STATE_DIR = box.state; cleanup(b); }
});
