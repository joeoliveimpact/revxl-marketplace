// Shared test helpers: a throwaway box (root, etc, config, tokens) and a running server on 127.0.0.1.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const PLUGIN = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const FAKE_ENGINE = path.join(PLUGIN, 'tests', 'fixtures', 'fake-engine', 'dist', 'src', 'cli.js');
export const day = (n) => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);

export function makeBox(extra = {}) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'fbx-test-'));
  const root = path.join(tmp, 'root');
  const etc = path.join(tmp, 'etc');
  fs.mkdirSync(etc, { recursive: true });
  fs.mkdirSync(path.join(tmp, 'log'), { recursive: true });
  const cfg = {
    tokens_dir: path.join(etc, 'tokens'),
    root, bind: '127.0.0.1', port: 0, timezone: 'UTC', log_dir: path.join(tmp, 'log'), engine: FAKE_ENGINE,
    timeout_ms: 4000, max_procs: 2, warm: 'all',
    spokes: { guidance: { folders: ['Guidance'], decay: 'never' }, log: { folders: ['Calls'], decay: true }, ops: { folders: ['Ops'], decay: false } },
    readers: { bot: { spokes: ['guidance', 'log'], view: true }, workers: { spokes: ['guidance'], view: false }, admin: { spokes: ['guidance', 'log', 'ops'], view: true } },
    ...extra,
  };
  const file = path.join(etc, 'brain.json');
  fs.writeFileSync(file, `${JSON.stringify(cfg, null, 2)}\n`);
  const state = path.join(tmp, 'state');
  const env = { ...process.env, FEWZHUN_BOX_CONFIG: file, FEWZHUN_BOX_STATE_DIR: state };
  return { tmp, root, etc, file, cfg, env, state, log: path.join(tmp, 'log', 'queries.jsonl') };
}

export function addToken(box, name) {
  return execFileSync(process.execPath, [path.join(PLUGIN, 'bin', 'tokens.mjs'), 'add', name], { env: box.env, encoding: 'utf8' });
}
export const tokenOf = (box, name) => fs.readFileSync(path.join(box.etc, 'tokens', name), 'utf8').trim();

export function note(root, spoke, rel, fm, body = 'zebra crossing notes') {
  const f = path.join(root, 'spokes', spoke, rel);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, `---\n${Object.entries(fm).map(([k, v]) => `${k}: ${v}`).join('\n')}\n---\n${body}\n`);
}

export async function startServer(box) {
  const srv = spawn(process.execPath, [path.join(PLUGIN, 'server', 'brain-server.mjs')], {
    env: { PATH: process.env.PATH, SystemRoot: process.env.SystemRoot, FEWZHUN_BOX_CONFIG: box.file, FEWZHUN_BOX_STATE_DIR: box.state },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let errOut = '';
  srv.stderr.on('data', (d) => { errOut += d; });
  const base = await new Promise((resolve, reject) => {
    let out = '';
    srv.stdout.on('data', (d) => { out += d; const m = /listening on ([\d.]+):(\d+)/.exec(out); if (m) resolve(`http://${m[1]}:${m[2]}`); });
    srv.on('exit', (c) => reject(new Error(`server exited ${c}: ${errOut}`)));
    setTimeout(() => reject(new Error(`server did not start: ${errOut}`)), 10000);
  });
  const stop = async () => {
    const pids = [];
    try {
      for (const l of fs.readFileSync(path.join(box.root, 'starts.log'), 'utf8').trim().split('\n')) {
        const pid = Number(l.split(' ')[1]);
        if (!Number.isInteger(pid) || pid <= 0) continue;
        try { process.kill(pid, 'SIGKILL'); pids.push(pid); } catch { /* gone */ }
      }
    } catch { /* no workers */ }
    if (srv.exitCode === null && srv.signalCode === null) {
      const exited = new Promise((res) => srv.once('exit', res));
      srv.kill();
      await exited;
    }
    // Windows can retain file handles briefly after TerminateProcess returns.
    for (let i = 0; i < 100 && pids.some((pid) => { try { process.kill(pid, 0); return true; } catch { return false; } }); i++) {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
  };
  return { base, stop, stderr: () => errOut };
}

export async function get(base, p, token) {
  const r = await fetch(base + p, { headers: token ? { authorization: `Bearer ${token}` } : {} });
  const text = await r.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* not JSON */ }
  return { status: r.status, json, text, headers: r.headers };
}

export const cleanup = (box) => fs.rmSync(box.tmp, { recursive: true, force: true, maxRetries: 20, retryDelay: 200 });
