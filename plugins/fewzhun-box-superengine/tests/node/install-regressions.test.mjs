import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { checkConfig, loadConfig, prepareInstallConfig, resolveBind } from '../../lib/config.mjs';
import { gitPull } from '../../lib/sync.mjs';
import { makeBox, cleanup, PLUGIN } from './helpers.mjs';

test('raw token directory is independent of the source config location, including installer output', () => {
  const b = makeBox({ graph: { enabled: false } });
  try {
    const { tokens_dir, ...raw } = b.cfg;
    const source = path.join(b.tmp, 'caller-home', 'brain.json');
    fs.mkdirSync(path.dirname(source));
    for (const [input, expected] of [[raw, '/etc/fewzhun-box/tokens'], [b.cfg, tokens_dir]]) {
      fs.writeFileSync(source, JSON.stringify(input));
      assert.equal(loadConfig(source).tokensDir, expected);
      const r = spawnSync(process.execPath, [path.join(PLUGIN, 'lib/config.mjs'), source, '--install-sh', '--dry-run'], { encoding: 'utf8' });
      assert.equal(r.status, 0, r.stderr);
      assert.ok(r.stdout.includes(`TOKENS_DIR='${expected}'`), r.stdout);
    }
  } finally { cleanup(b); }
});

test('engine uses public code_root and code cannot overlap private data or raw tokens', () => {
  const b = makeBox();
  try {
    const { engine, ...raw } = b.cfg;
    const defaults = checkConfig(raw);
    assert.equal(defaults.code_root, '/opt/fewzhun-box-app');
    assert.equal(defaults.engine, path.join(defaults.code_root, 'node_modules', '.bin', 'obsidian-hybrid-search'));
    const code_root = path.join(b.tmp, 'public-code');
    assert.equal(checkConfig({ ...raw, code_root }).engine, path.join(code_root, 'node_modules', '.bin', 'obsidian-hybrid-search'));
    for (const bad of [b.root, path.join(b.root, 'app'), b.tmp]) {
      assert.throws(() => checkConfig({ ...raw, code_root: bad }), /root and code_root must be separate/);
    }
    assert.throws(() => checkConfig({ ...raw, code_root, tokens_dir: path.join(code_root, 'tokens') }), /tokens_dir must be outside/);
  } finally { cleanup(b); }
});

test('installer wrapper uses public app and Node, preserves arguments and installs as 0755', () => {
  const script = fs.readFileSync(path.join(PLUGIN, 'bin/install.sh'), 'utf8');
  const block = script.split('# Public CLI wrapper:')[1]?.split('# Sync git config')[0].split('\n').slice(1).join('\n');
  assert.ok(block);
  const b = makeBox();
  try {
    const posix = (p) => p.replaceAll('\\', '/');
    const shell = `set -eu\nNODE='/public code/node'\nCODE_ROOT='/public code'\nTMPD='${posix(b.tmp)}'\n`
      + 'put() { [ "$2" = /usr/local/bin/fewzhun-box ] && [ "$3" = 0755 ]; };\n' + block;
    const r = spawnSync('bash', ['-c', shell], { encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr || String(r.error));
    const wrapper = fs.readFileSync(path.join(b.tmp, 'fewzhun-box'), 'utf8');
    assert.equal(wrapper, '#!/bin/sh\nexec "/public code/node" "/public code/app/bin/fewzhun-box.mjs" "$@"\n');
  } finally { cleanup(b); }
});

test('bind resolver includes IPv4 on NO-CARRIER and DOWN bridges omitted by Node', () => {
  const entries = [
    { ifname: 'docker0', operstate: 'DOWN', flags: ['NO-CARRIER'], addr_info: [{ family: 'inet', local: '172.17.0.1' }] },
    { ifname: 'br-abc', operstate: 'DOWN', addr_info: [{ family: 'inet', local: '172.19.0.1' }] },
  ];
  const ip = (cmd, args) => {
    assert.equal(cmd, 'ip');
    assert.deepEqual(args, ['-j', '-4', 'addr', 'show']);
    return { status: 0, stdout: JSON.stringify(entries) };
  };
  assert.equal(resolveBind('auto-docker', undefined, ip), '172.17.0.1');
  entries.shift();
  assert.equal(resolveBind('auto-docker', undefined, ip), '172.19.0.1');
});

test('installer resolves the named Docker network bridge and saves its down-link IP', () => {
  for (const custom of [false, true]) {
    const calls = [];
    const raw = { bind: 'auto-docker', docker_network: 'notes', graph: { enabled: false } };
    const c = prepareInstallConfig(raw, (cmd, args) => {
      calls.push([cmd, args]);
      return { status: 0, stdout: JSON.stringify(cmd === 'docker'
        ? [{ Driver: 'bridge', Name: 'notes', Id: 'abc123456789ffffffff', Options: custom ? { 'com.docker.network.bridge.name': 'notes0' } : {} }]
        : [{ operstate: 'DOWN', addr_info: [{ family: 'inet', local: '172.22.0.1' }] }]) };
    });
    assert.equal(c.bind, '172.22.0.1');
    assert.equal(raw.bind, 'auto-docker');
    assert.deepEqual(calls, [['docker', ['network', 'inspect', 'notes']], ['ip', ['-j', '-4', 'addr', 'show', 'dev', custom ? 'notes0' : 'br-abc123456789']]]);
  }
});

test('installer discovers the absolute Claude binary using the login user', () => {
  const c = prepareInstallConfig({ bind: '127.0.0.1', claude: { bin: 'claude', run_as: 'worker' } }, (cmd, args) => {
    assert.equal(cmd, 'sudo');
    assert.deepEqual(args, ['-u', 'worker', '-i', 'sh', '-c', 'command -v claude']);
    return { status: 0, stdout: process.execPath + '\n' };
  });
  assert.equal(c.claude.bin, process.execPath);
  assert.throws(() => prepareInstallConfig({ bind: '127.0.0.1', claude: { run_as: 'worker' } }, () => ({ status: 1 })), /PAUSE POINT \(claude binary\)/);
  const b = makeBox();
  try {
    assert.throws(() => checkConfig({ ...b.cfg, claude: { bin: path.join(b.tmp, 'missing') } }), /claude.bin does not exist/);
    fs.writeFileSync(b.file, JSON.stringify({ ...b.cfg, claude: { bin: path.join(b.tmp, 'private-home/claude') } }));
    assert.equal(loadConfig(b.file).claude.bin, path.join(b.tmp, 'private-home/claude'), 'service config does not stat the private worker home');
  } finally { cleanup(b); }
});

test('all sync clone and pull git calls trust clone and decoded file source paths', () => {
  const b = makeBox();
  try {
    const source = path.join(b.tmp, 'source with spaces');
    const vault = path.join(b.root, 'vault');
    const cfg = { root: b.root, sync: { repo: pathToFileURL(source).href, deploy_key: '/unused' } };
    const calls = [];
    const run = (cmd, args, opts) => { calls.push([cmd, args, opts]); return { code: 0, stdout: '', stderr: '' }; };
    assert.equal(gitPull(cfg, run), 'cloned');
    fs.mkdirSync(path.join(vault, '.git'), { recursive: true });
    assert.equal(gitPull(cfg, run), 'pulled');
    for (const [cmd, args, { env }] of calls) {
      assert.equal(cmd, 'git');
      assert.deepEqual(args.slice(0, 4), ['-c', `safe.directory=${vault}`, '-c', `safe.directory=${source}`]);
      assert.equal(env.GIT_CONFIG_GLOBAL, '/etc/fewzhun-box/sync.gitconfig');
      assert.equal(env.GIT_CONFIG_NOSYSTEM, process.env.GIT_CONFIG_NOSYSTEM);
    }
    calls.length = 0;
    cfg.sync.repo = source;
    cfg.sync.git_config = path.join(b.etc, 'sync.gitconfig');
    gitPull(cfg, run);
    assert.deepEqual(calls[0][1].slice(0, 4), ['-c', `safe.directory=${vault}`, '-c', `safe.directory=${source}`]);
    assert.equal(calls[0][2].env.GIT_CONFIG_GLOBAL, cfg.sync.git_config);
    calls.length = 0;
    cfg.sync.repo = 'https://example.invalid/notes.git';
    gitPull(cfg, run);
    assert.deepEqual(calls[0][1].slice(0, 3), ['-c', `safe.directory=${vault}`, '-C']);
  } finally { cleanup(b); }
});

test('installer rewrites a root-owned 0644 sync gitconfig with clone and file source paths', () => {
  const script = fs.readFileSync(path.join(PLUGIN, 'bin/install.sh'), 'utf8');
  const block = script.split('# Sync git config (rewritten on every install).')[1]?.split('# End sync git config.')[0];
  assert.ok(block, 'installer has a sync gitconfig block');
  const b = makeBox();
  try {
    const dest = path.join(b.etc, 'sync.gitconfig');
    const raw = { ...b.cfg, sync: { enabled: true, repo: pathToFileURL(path.join(b.tmp, 'source with spaces')).href, git_config: dest } };
    const posix = (p) => p.replaceAll('\\', '/');
    for (const source of ['source with spaces', 'replacement']) {
      raw.sync.repo = pathToFileURL(path.join(b.tmp, source)).href;
      fs.writeFileSync(b.file, JSON.stringify(raw));
      const vars = spawnSync(process.execPath, [path.join(PLUGIN, 'lib/config.mjs'), b.file, '--sh'], { encoding: 'utf8' });
      assert.equal(vars.status, 0, vars.stderr);
      const shell = `set -eu\n${vars.stdout}\nAPPLY=1\nNODE='${posix(process.execPath)}'\nHERE='${posix(PLUGIN)}'\nCONF_READ='${posix(b.file)}'\nTMPD='${posix(b.tmp)}'\n`
        + 'act() { eval "$1"; }; die() { echo "$*" >&2; exit 1; };\n'
        + 'install() { [ "$1 $2 $3 $4 $5 $6" = "-o root -g root -m 0644" ]; cp "$7" "$8"; };\n' + block;
      const result = spawnSync('bash', ['-c', shell], { encoding: 'utf8' });
      assert.equal(result.status, 0, result.stderr || String(result.error));
      const git = spawnSync('git', ['config', '--file', dest, '--get-all', 'safe.directory'], { encoding: 'utf8' });
      assert.equal(git.status, 0, git.stderr);
      assert.deepEqual(git.stdout.trim().split('\n'), [path.resolve(b.root, 'vault'), path.join(b.tmp, source)]);
    }
  } finally { cleanup(b); }
});

test('deploy-key pause is emitted only for SSH repos, never file or HTTPS', () => {
  const script = fs.readFileSync(path.join(PLUGIN, 'bin/install.sh'), 'utf8');
  const block = script.split('# ---- 13.')[1].split('# ---- 14.')[0].split('\n').slice(1).join('\n');
  for (const repo of ['file:///notes.git', 'https://example.invalid/notes.git', 'git@example.invalid:notes.git', 'ssh://example.invalid/notes.git']) {
    const b = makeBox({ sync: { enabled: true, repo } });
    try {
      const vars = spawnSync(process.execPath, [path.join(PLUGIN, 'lib/config.mjs'), b.file, '--sh'], { encoding: 'utf8' });
      assert.equal(vars.status, 0, vars.stderr);
      const r = spawnSync('bash', ['-c', vars.stdout + '\nact() { :; }; pause() { echo "PAUSE POINT ($1)"; };\n' + block], { encoding: 'utf8' });
      assert.equal(r.status, 0, r.stderr || String(r.error));
      assert.equal(r.stdout.includes('PAUSE POINT (deploy key)'), /^(git@|ssh:\/\/)/.test(repo), repo);
    } finally { cleanup(b); }
  }
});

test('systemd leaves the root-owned private state directory to the installer', () => {
  const script = fs.readFileSync(path.join(PLUGIN, 'bin/install.sh'), 'utf8');
  assert.ok(script.includes('install -d -o root -g fbx -m 0750 $LIB'));
  assert.doesNotMatch(fs.readFileSync(path.join(PLUGIN, 'systemd/fewzhun-box-server.service'), 'utf8'), /^StateDirectory=/m);
});
