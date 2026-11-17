// engine.mjs: run the pinned search engine (obsidian-hybrid-search 0.12.7) over one spoke.
// Copied from Fewzhun v1.1 scripts/lib/engine.mjs (env scrub + runner), cut down to one spoke folder:
// - an OPENAI_* key silently switches embeddings and the next reindex wipes the index, so the
//   engine never sees one;
// - never `status` (it rewrites the index and phones the npm registry), never `--force`,
//   never `--rerank` (the large re-ranking model).
import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

export const ENGINE_VERSION = '0.12.7';
export const SCRUB_KEYS = ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_EMBEDDING_MODEL', 'LOCAL_EMBEDDING_MODEL'];
export const DB_FILE = '.obsidian-hybrid-search.db';

export function engineEnv(dir, base = process.env) {
  const env = { ...base };
  for (const k of Object.keys(env)) if (SCRUB_KEYS.includes(k) || k.startsWith('OPENAI_')) delete env[k];
  env.OBSIDIAN_VAULT_PATH = dir;
  env.OBSIDIAN_IGNORE_PATTERNS = '.obsidian/**';
  return env;
}

export function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { encoding: 'utf8', windowsHide: true, maxBuffer: 64 * 1024 * 1024, ...opts });
  return {
    code: r.status, stdout: r.stdout || '', stderr: r.stderr || '',
    error: r.error ? (r.error.code || r.error.message) : null, signal: r.signal || null,
  };
}

// enginePath: the engine's bin (a symlink to dist/src/cli.js); it runs under this Node.
export function engineRun(enginePath, dir, args, timeoutMs = 600000) {
  if (args[0] === 'status' || args.includes('--force') || args.includes('--rerank')) throw new Error('refused engine argument');
  let cli;
  try { cli = fs.realpathSync(enginePath); } catch {
    const e = new Error(`search engine not found at ${enginePath} (run the installer)`);
    e.code = 'ENGINE_MISSING';
    throw e;
  }
  const r = run(process.execPath, [cli, ...args], { cwd: dir, env: engineEnv(dir), timeout: timeoutMs });
  if (r.error || r.code !== 0) {
    const e = new Error(`engine ${args[0]} failed: ${r.error || r.signal || `exit ${r.code}`} ${r.stderr.trim().slice(-300)}`);
    e.code = 'ENGINE_FAILED';
    throw e;
  }
  return r;
}
