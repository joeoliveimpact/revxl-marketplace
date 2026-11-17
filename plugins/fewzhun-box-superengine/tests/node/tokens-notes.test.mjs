// tokens.mjs (add / revoke / list, never a token value) and the shared note rules.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { makeBox, cleanup, PLUGIN } from './helpers.mjs';
import { isActive, weight, frontmatter, normalize } from '../../lib/notes.mjs';
import { checkConfig, resolveBind } from '../../lib/config.mjs';

test('tokens: add stores sha256 only, keeps on re-run, list shows the last 4, revoke removes', () => {
  const box = makeBox();
  try {
    const run = (...a) => execFileSync(process.execPath, [path.join(PLUGIN, 'bin', 'tokens.mjs'), ...a], { env: box.env, encoding: 'utf8' });
    const out1 = run('add', 'bot');
    const tok = fs.readFileSync(path.join(box.etc, 'tokens', 'bot'), 'utf8').trim();
    assert.match(tok, /^[0-9a-f]{64}$/);
    const json = JSON.parse(fs.readFileSync(path.join(box.etc, 'tokens.json'), 'utf8'));
    assert.deepEqual(json, { bot: { sha256: crypto.createHash('sha256').update(tok).digest('hex') } });
    assert.match(out1, /created/);
    const out2 = run('add', 'bot');
    assert.match(out2, /kept/);
    assert.equal(fs.readFileSync(path.join(box.etc, 'tokens', 'bot'), 'utf8').trim(), tok);
    const list = run('list');
    assert.match(list, new RegExp(`bot: token \\.\\.\\.${tok.slice(-4)}; spokes: guidance, log; viewer graphs: yes`));
    assert.match(list, /workers: NO TOKEN/);
    for (const o of [out1, out2, list]) assert.ok(!o.includes(tok) && !o.includes(tok.slice(0, 8)));
    assert.match(run('add', 'stranger'), /not in brain\.json readers/);
    assert.match(run('revoke', 'bot'), /revoked/);
    assert.ok(!fs.existsSync(path.join(box.etc, 'tokens', 'bot')));
    assert.ok(!('bot' in JSON.parse(fs.readFileSync(path.join(box.etc, 'tokens.json'), 'utf8'))));
    assert.throws(() => run('add', '../evil'), /letters, digits/);
  } finally { cleanup(box); }
});

test('active rule: only status active (trimmed, any case); superseded_by also hides', () => {
  assert.equal(isActive({ status: 'active' }), true);
  assert.equal(isActive({ status: ' Active ' }), true);
  for (const fm of [{}, { status: '' }, { status: 'reviewed' }, { status: 'current' }, { status: 'superseded' }, { status: 'Draft' }, { status: 'conflict' }, { status: 'active', superseded_by: 'x' }]) {
    assert.equal(isActive(fm), false, JSON.stringify(fm));
  }
  assert.equal(isActive({ status: 'active', superseded_by: '' }), true);
  assert.equal(isActive(frontmatter('﻿---\r\nstatus: active\r\n---\r\nbody').fm), true);
  assert.equal(normalize('﻿a\r\nb\r\n'), 'a\nb\n');
});

test('weight: decay true ages; sot_policy decay ages unless the spoke is never; strict and undated never do', () => {
  assert.equal(weight(true, {}, 365), 0.5);
  assert.equal(weight(true, {}, 0), 1);
  assert.equal(weight(true, {}, 730), 0.5);
  assert.equal(weight(false, {}, 900), 1);
  assert.equal(weight(false, { sot_policy: 'decay' }, 365), 0.5);
  assert.equal(weight(true, { sot_policy: 'strict' }, 900), 1);
  assert.equal(weight(true, {}, null), 1);
  assert.equal(weight('never', {}, 900), 1);
  assert.equal(weight('never', { sot_policy: 'decay' }, 365), 1, 'guidance note marked decay in a never spoke keeps its score');
});

test('config: refuses wildcard binds, unknown reader spokes and unsafe names; auto-docker prefers docker0', () => {
  const base = { spokes: { a: { folders: ['A'] } }, readers: { r: { spokes: ['a'] } } };
  assert.equal(checkConfig(base, '/etc/x/brain.json').bind, 'auto-docker');
  assert.throws(() => checkConfig({ ...base, bind: '0.0.0.0' }), /wildcard/);
  assert.equal(checkConfig({ ...base, spokes: { a: { folders: ['A'], decay: 'never' } } }).spokes.a.decay, 'never');
  assert.throws(() => checkConfig({ ...base, spokes: { a: { folders: ['A'], decay: 'sometimes' } } }), /true, false or "never"/);
  assert.throws(() => checkConfig({ ...base, readers: { r: { spokes: ['b'] } } }), /not in spokes/);
  assert.throws(() => checkConfig({ ...base, spokes: { '../x': { folders: ['A'] } }, readers: {} }), /spoke name/);
  assert.throws(() => checkConfig({ ...base, spokes: { a: { folders: ['../A'] } } }), /inside the vault/);
  const ifs = { lo: [{ family: 'IPv4', address: '127.0.0.1' }], 'br-abc': [{ family: 'IPv4', address: '10.9.8.7' }],
    docker0: [{ family: 'IPv4', address: '172.17.0.1' }], tailscale0: [{ family: 'IPv4', address: '100.101.1.2' }] };
  assert.equal(resolveBind('auto-docker', ifs), '172.17.0.1');
  assert.equal(resolveBind('auto-docker', { 'br-abc': ifs['br-abc'] }), '10.9.8.7');
  assert.equal(resolveBind('auto-docker', { lo: ifs.lo }), null);
  assert.equal(resolveBind('auto', ifs), '100.101.1.2');
  assert.equal(resolveBind('auto', { lo: ifs.lo }), null);
});
