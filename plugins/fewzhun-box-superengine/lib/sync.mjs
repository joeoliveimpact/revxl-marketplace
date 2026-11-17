// sync.mjs: vault -> spokes. Pull the client's notes repo (read-only deploy key, fast-forward only),
// copy each spoke's ACTIVE notes from its folders into <root>/spokes/<spoke>/ (real copies, LF, no
// BOM), delete copies whose source became hidden or vanished, then reindex only the spokes that
// changed (incremental: never --force, never status). A spoke whose reindex failed stays pending
// and is retried next run. Writes /var/lib/fewzhun-box/status/sync.json either way.
import fs from 'node:fs';
import path from 'node:path';
import { syncGitPaths } from './config.mjs';
import { frontmatter, isActive, notANote, normalize } from './notes.mjs';
import { engineRun, run } from './engine.mjs';
import { syncStatusDir } from './status.mjs';

const toPosix = (p) => p.split(path.sep).join('/');

// .md files under dir (posix paths relative to base). Dot entries and symlinks are skipped.
function walk(dir, base) {
  let ents;
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return []; }
  const out = [];
  for (const e of ents) {
    if (e.name.startsWith('.') || e.isSymbolicLink()) continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(full, base));
    else if (e.isFile() && e.name.toLowerCase().endsWith('.md')) out.push(toPosix(path.relative(base, full)));
  }
  return out;
}

function removeEmptyDirs(dir, keep) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!e.isDirectory() || e.name.startsWith('.')) continue;
    const d = path.join(dir, e.name);
    removeEmptyDirs(d, false);
  }
  if (!keep && !fs.readdirSync(dir).length) fs.rmdirSync(dir);
}

export function gitPull(cfg, runner = run) {
  const vault = path.resolve(cfg.root, 'vault');
  const safe = syncGitPaths(cfg).flatMap((p) => ['-c', `safe.directory=${p}`]);
  const env = {
    ...process.env,
    GIT_CONFIG_GLOBAL: cfg.sync.git_config || '/etc/fewzhun-box/sync.gitconfig',
    GIT_TERMINAL_PROMPT: '0',
    GIT_SSH_COMMAND: `ssh -i ${cfg.sync.deploy_key} -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new`,
  };
  const git = (args) => {
    const r = runner('git', [...safe, ...args], { env, timeout: 300000 });
    if (r.error || r.code !== 0) throw new Error(`git ${args.find((a) => !a.startsWith('-') && a !== vault)} failed: ${r.error || `exit ${r.code}`} ${r.stderr.trim().slice(-300)}`);
    return r;
  };
  if (fs.existsSync(path.join(vault, '.git'))) { git(['-C', vault, 'pull', '--ff-only', '--quiet']); return 'pulled'; }
  if (fs.existsSync(vault) && fs.readdirSync(vault).length) throw new Error(`${vault} has files but is not a git clone; move them away or turn sync off`);
  git(['clone', '--quiet', '--', cfg.sync.repo, vault]);
  return 'cloned';
}

// One spoke: returns { files, copied, removed }.
export function copySpoke(cfg, spoke) {
  const vault = path.join(cfg.root, 'vault');
  const dest = path.join(cfg.root, 'spokes', spoke);
  fs.mkdirSync(dest, { recursive: true });
  const want = new Map();
  for (const folder of cfg.spokes[spoke].folders) {
    for (const rel of walk(path.join(vault, folder), vault)) {
      if (notANote(rel)) continue;
      let text;
      try { text = normalize(fs.readFileSync(path.join(vault, rel), 'utf8')); } catch { continue; }
      if (isActive(frontmatter(text).fm)) want.set(rel, text);
    }
  }
  let copied = 0; let removed = 0;
  for (const [rel, text] of want) {
    const dst = path.join(dest, rel);
    let old = null;
    try { old = fs.readFileSync(dst, 'utf8'); } catch { /* new */ }
    if (old === text) continue;
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.writeFileSync(`${dst}.fbx-tmp`, text);
    fs.renameSync(`${dst}.fbx-tmp`, dst);
    copied++;
  }
  for (const rel of walk(dest, dest)) {
    if (want.has(rel)) continue;
    fs.unlinkSync(path.join(dest, rel));
    removed++;
  }
  if (removed) removeEmptyDirs(dest, true);
  return { files: want.size, copied, removed };
}

export function sync(cfg, { log = () => {} } = {}) {
  process.umask(0o007);
  const statusDir = syncStatusDir();
  const statusFile = path.join(statusDir, 'sync.json');
  let prev = {};
  try { prev = JSON.parse(fs.readFileSync(statusFile, 'utf8')); } catch { /* first run */ }
  const pending = new Set((prev.pending || []).filter((s) => cfg.spokes[s]));
  const st = { job: 'sync', started: new Date().toISOString(), ok: false, git: null, spokes: {}, pending: [], errors: [] };
  const save = () => {
    fs.mkdirSync(statusDir, { recursive: true });
    // ok + ts + reason: the same shape the graph/harvest jobs and the failure alert use.
    const data = { ...st, ts: new Date().toISOString(), ...(st.errors.length ? { reason: st.errors.join('; ').slice(0, 500) } : {}), pending: [...pending] };
    fs.writeFileSync(`${statusFile}.tmp`, `${JSON.stringify(data, null, 2)}\n`);
    fs.renameSync(`${statusFile}.tmp`, statusFile);
  };
  try {
    if (cfg.sync.enabled) { st.git = gitPull(cfg); log(`git: ${st.git}`); }
    if (!fs.existsSync(path.join(cfg.root, 'vault'))) throw new Error(`no vault folder at ${path.join(cfg.root, 'vault')} (turn sync on, or put the notes there)`);
    for (const s of Object.keys(cfg.spokes)) {
      st.spokes[s] = copySpoke(cfg, s);
      if (st.spokes[s].copied || st.spokes[s].removed) pending.add(s);
      log(`${s}: ${st.spokes[s].files} active note(s), ${st.spokes[s].copied} copied, ${st.spokes[s].removed} removed`);
    }
    save(); // pending is on disk before any reindex, so a crash mid-reindex retries next run
    for (const s of [...pending]) {
      try {
        engineRun(cfg.engine, path.join(cfg.root, 'spokes', s), ['reindex']);
        pending.delete(s);
        log(`${s}: reindexed`);
      } catch (e) { st.errors.push(`${s}: ${e.message}`); log(`${s}: reindex failed: ${e.message}`); }
    }
    st.ok = !st.errors.length;
  } catch (e) {
    st.errors.push(e.message);
  }
  st.finished = new Date().toISOString();
  save();
  return { ...st, pending: [...pending] };
}
