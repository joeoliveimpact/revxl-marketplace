// config.mjs: load and check /etc/fewzhun-box/brain.json (FEWZHUN_BOX_CONFIG overrides the path).
// Every client-specific value lives in that one file; see config/CONFIG.md.
// CLI (used by install.sh and done-test.sh):
//   node lib/config.mjs <file> --sh          print checked values as KEY='value' lines for sh eval
//   node lib/config.mjs <file> --warm-lazy   set "warm": "lazy" in the file (install, low memory)
import fs from 'node:fs';
import os from 'node:os';
import net from 'node:net';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const configFile = () => process.env.FEWZHUN_BOX_CONFIG || '/etc/fewzhun-box/brain.json';
export const NAME_RX = /^[a-z0-9][a-z0-9_-]{0,63}$/i;
const safePath = (p) => typeof p === 'string' && path.isAbsolute(p) && !/[\n\r'"`$\\|&]/.test(p.replace(/^[A-Za-z]:\\/, '').replace(/\\/g, '/'));

const DEFAULTS = {
  code_root: '/opt/fewzhun-box-app', tokens_dir: '/etc/fewzhun-box/tokens',
  root: '/opt/fewzhun-box', bind: 'auto-docker', docker_network: null, port: 8791, tailnet_bind: null, timezone: 'UTC',
  max_procs: 2, warm: 'all', memory_max: '3500M', log_dir: '/var/log/fewzhun-box', timeout_ms: 20000,
};
const SECTION_DEFAULTS = {
  sync: { enabled: false, repo: null, deploy_key: '/etc/fewzhun-box/deploy_key', git_config: '/etc/fewzhun-box/sync.gitconfig', interval_min: 15 },
  graph: { enabled: true, graphify_version: '0.9.112', backend: 'claude-cli', time: '03:30' },
  harvest: { enabled: false, time: '02:30' },
  done_test: {},
};

export function checkConfig(raw, file = configFile(), { checkClaudeBin = true } = {}) {
  const errs = [];
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error(`${file}: not a JSON object`);
  const c = { ...DEFAULTS, ...raw };
  for (const [k, d] of Object.entries(SECTION_DEFAULTS)) c[k] = { ...d, ...(raw[k] || {}) };
  if (!safePath(c.root)) errs.push('root must be an absolute path without quotes');
  if (!safePath(c.code_root)) errs.push('code_root must be an absolute path without quotes');
  if (!safePath(c.tokens_dir)) errs.push('tokens_dir must be an absolute path without quotes');
  const contains = (a, b) => { const rel = path.relative(a, b); return rel === '' || (rel !== '..' && !rel.startsWith('..' + path.sep) && !path.isAbsolute(rel)); };
  if (safePath(c.root) && safePath(c.code_root) && (contains(c.root, c.code_root) || contains(c.code_root, c.root))) errs.push('root and code_root must be separate directories, neither inside the other');
  if (safePath(c.code_root) && safePath(c.tokens_dir) && contains(c.code_root, c.tokens_dir)) errs.push('tokens_dir must be outside code_root');
  if (c.bind !== 'auto-docker' && !net.isIP(String(c.bind))) errs.push('bind must be "auto-docker" or an IP address');
  if (c.docker_network !== null && (typeof c.docker_network !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(c.docker_network))) errs.push('docker_network must be null or a Docker network name');
  if (['0.0.0.0', '::'].includes(String(c.bind))) errs.push('bind may not be a wildcard address (it would expose the brain publicly)');
  if (c.tailnet_bind !== null && c.tailnet_bind !== 'auto' && !net.isIP(String(c.tailnet_bind))) errs.push('tailnet_bind must be null, "auto" or an IP address');
  if (['0.0.0.0', '::'].includes(String(c.tailnet_bind))) errs.push('tailnet_bind may not be a wildcard address');
  if (!Number.isInteger(c.port) || c.port < 0 || c.port > 65535) errs.push('port must be a whole number 0-65535');
  if (!Number.isInteger(c.max_procs) || c.max_procs < 1) errs.push('max_procs must be 1 or more');
  if (!['all', 'lazy'].includes(c.warm)) errs.push('warm must be "all" or "lazy"');
  if (!/^\d+[KMG]?$/.test(String(c.memory_max))) errs.push('memory_max must look like 3500M');
  if (!safePath(c.log_dir)) errs.push('log_dir must be an absolute path');
  if (!/^[A-Za-z][A-Za-z0-9_+-]*(\/[A-Za-z0-9_+-]+)*$/.test(String(c.timezone))) errs.push('timezone must be a name like UTC or Europe/London');
  if (!/^\d+\.\d+\.\d+$/.test(String(c.graph.graphify_version))) errs.push('graph.graphify_version must be an exact version like 0.9.112');
  if (c.claude?.run_as && !/^[a-z_][a-z0-9_-]*$/.test(String(c.claude.run_as))) errs.push('claude.run_as must be a Linux user name');
  if (c.claude && (c.graph.enabled || c.harvest.enabled)) {
    if (!safePath(c.claude.bin)) errs.push('claude.bin must be an absolute path');
    else if (checkClaudeBin && !fs.existsSync(c.claude.bin)) errs.push(`claude.bin does not exist: ${c.claude.bin}`);
    if (c.claude.token_file != null && !safePath(c.claude.token_file)) errs.push('claude.token_file must be null or an absolute path');
  }
  if (!c.spokes || typeof c.spokes !== 'object' || !Object.keys(c.spokes).length) errs.push('spokes needs at least one spoke');
  for (const [s, v] of Object.entries(c.spokes || {})) {
    if (!NAME_RX.test(s)) errs.push(`spoke name "${s}" may use only letters, digits, - and _`);
    if (!v || !Array.isArray(v.folders) || !v.folders.length) errs.push(`spoke ${s}: folders must be a non-empty list`);
    for (const f of v?.folders || []) {
      if (typeof f !== 'string' || !f || path.isAbsolute(f) || /^[A-Za-z]:/.test(f) || f.split(/[\\/]/).includes('..')) errs.push(`spoke ${s}: folder "${f}" must be a path inside the vault`);
    }
    if (v && v.decay !== undefined && ![true, false, 'never'].includes(v.decay)) errs.push(`spoke ${s}: decay must be true, false or "never"`);
  }
  if (!c.readers || typeof c.readers !== 'object' || !Object.keys(c.readers).length) errs.push('readers needs at least one reader');
  for (const [r, v] of Object.entries(c.readers || {})) {
    if (!NAME_RX.test(r)) errs.push(`reader name "${r}" may use only letters, digits, - and _`);
    if (!v || !Array.isArray(v.spokes)) errs.push(`reader ${r}: spokes must be a list`);
    for (const s of v?.spokes || []) if (!c.spokes?.[s]) errs.push(`reader ${r}: spoke "${s}" is not in spokes`);
    if (v && v.view !== undefined && typeof v.view !== 'boolean') errs.push(`reader ${r}: view must be true or false`);
  }
  if (c.sync.enabled) {
    if (typeof c.sync.repo !== 'string' || !c.sync.repo || c.sync.repo.startsWith('-')) errs.push('sync.repo must be set when sync is enabled');
    if (!safePath(c.sync.deploy_key) || /\s/.test(c.sync.deploy_key)) errs.push('sync.deploy_key must be an absolute path without spaces');
  }
  if (!Number.isInteger(c.sync.interval_min) || c.sync.interval_min < 1) errs.push('sync.interval_min must be 1 or more');
  if (!safePath(c.sync.git_config)) errs.push('sync.git_config must be an absolute path without quotes');
  if (errs.length) throw new Error(`${file}: ${errs.join('; ')}`);
  const dir = path.dirname(file);
  return {
    ...c, file,
    tokensFile: path.join(dir, 'tokens.json'),
    tokensDir: c.tokens_dir,
    engine: c.engine || path.join(c.code_root, 'node_modules', '.bin', 'obsidian-hybrid-search'),
  };
}

// The fbx service has ProtectHome=yes and cannot stat a worker's private executable.
// The root installer validates its existence; the guard checks it before every model run.
export const loadConfig = (file = configFile(), options = { checkClaudeBin: false }) => checkConfig(JSON.parse(fs.readFileSync(file, 'utf8')), file, options);

export function syncGitPaths(c) {
  const paths = [path.resolve(c.root, 'vault')];
  const repo = c.sync.repo || '';
  if (repo.startsWith('file://')) paths.push(fileURLToPath(repo));
  else if (repo && (path.isAbsolute(repo) || (!/^[a-z][a-z0-9+.-]*:/i.test(repo) && !/^[^/]+@[^/]+:/.test(repo)))) paths.push(path.resolve(repo));
  return paths;
}

// "auto-docker": docker0's IPv4 (every bridge network's containers reach it), else the first
// compose bridge (br-*). "auto" (tailnet): tailscale0, else any 100.64.0.0/10 address. null = not up.
export function resolveBind(spec, ifaces, run = spawnSync) {
  if (!ifaces) {
    ifaces = os.networkInterfaces();
    if (spec === 'auto-docker') {
      // getifaddrs (used by Node) can omit NO-CARRIER bridges. ip lists their assigned IPs.
      const r = run('ip', ['-j', '-4', 'addr', 'show'], { encoding: 'utf8' });
      if (r.status === 0) {
        for (const e of JSON.parse(r.stdout)) {
          ifaces[e.ifname] = (e.addr_info || []).filter((a) => a.family === 'inet')
            .map((a) => ({ family: 'IPv4', address: a.local }));
        }
      }
    }
  }
  const v4 = (name) => (ifaces[name] || []).find((a) => a.family === 'IPv4' || a.family === 4)?.address || null;
  if (spec === 'auto-docker') return v4('docker0') || Object.keys(ifaces).filter((n) => n.startsWith('br-')).sort().map(v4).find(Boolean) || null;
  if (spec === 'auto') {
    if (v4('tailscale0')) return v4('tailscale0');
    for (const list of Object.values(ifaces)) {
      for (const a of list || []) {
        const m = /^100\.(\d+)\./.exec(a.address);
        if (m && +m[1] >= 64 && +m[1] <= 127) return a.address;
      }
    }
    return null;
  }
  return spec || null;
}

// Only the installer invokes discovery; services use the stored IP and absolute binary.
export function prepareInstallConfig(raw, run = spawnSync) {
  const c = structuredClone(raw);
  if (c.docker_network || (c.bind || 'auto-docker') === 'auto-docker') {
    if (c.docker_network) {
      if (!/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(c.docker_network)) throw new Error('docker_network must be a Docker network name');
      const r = run('docker', ['network', 'inspect', c.docker_network], { encoding: 'utf8' });
      if (r.status !== 0) throw new Error(`docker_network cannot be inspected: ${c.docker_network}`);
      const n = JSON.parse(r.stdout)[0];
      if (n?.Driver !== 'bridge') throw new Error('docker_network must use the bridge driver');
      const bridge = n.Options?.['com.docker.network.bridge.name'] || (n.Name === 'bridge' ? 'docker0' : `br-${n.Id.slice(0, 12)}`);
      const a = run('ip', ['-j', '-4', 'addr', 'show', 'dev', bridge], { encoding: 'utf8' });
      const ip = a.status === 0 && JSON.parse(a.stdout).flatMap((e) => e.addr_info || []).find((e) => e.family === 'inet')?.local;
      if (!ip) throw new Error(`docker_network bridge ${bridge} has no IPv4 address`);
      c.bind = ip;
    } else c.bind = resolveBind('auto-docker', undefined, run) || 'auto-docker';
  }
  if (c.graph?.enabled !== false || c.harvest?.enabled) {
    c.claude ||= {};
    if (!path.isAbsolute(c.claude.bin || '')) {
      const user = c.claude.run_as;
      if (typeof user !== 'string' || !/^[a-z_][a-z0-9_-]*$/.test(user)) throw new Error('claude.run_as must name the Linux user for binary discovery');
      const r = run('sudo', ['-u', user, '-i', 'sh', '-c', 'command -v claude'], { encoding: 'utf8' });
      const bin = (r.stdout || '').trim();
      if (r.status !== 0 || !path.isAbsolute(bin) || !fs.existsSync(bin)) throw new Error(`PAUSE POINT (claude binary): Claude was not found for ${user}; install it for that user and set claude.bin to its absolute path`);
      c.claude.bin = bin;
    }
  }
  return c;
}

const q = (v) => `'${String(v ?? '').replace(/'/g, `'\\''`)}'`;
function shLines(c) {
  const dt = c.done_test || {};
  const reader = dt.reader && c.readers[dt.reader] ? dt.reader : Object.keys(c.readers)[0];
  const r = c.readers[reader];
  const other = Object.keys(c.spokes).find((s) => !r.spokes.includes(s)) || '';
  const hhmm = (t, d) => (/^([01]\d|2[0-3]):[0-5]\d$/.test(String(t)) ? t : d);
  const out = {
    ROOT: c.root, CODE_ROOT: c.code_root, PORT: c.port, BIND_SPEC: c.bind, BIND: resolveBind(c.bind) || '', TAILNET_SPEC: c.tailnet_bind || '',
    TAILNET: c.tailnet_bind ? resolveBind(c.tailnet_bind) || '' : '', WARM: c.warm, MEMORY_MAX: c.memory_max,
    SPOKES: Object.keys(c.spokes).join(' '), NSPOKES: Object.keys(c.spokes).length, READERS: Object.keys(c.readers).join(' '),
    TIMEZONE: c.timezone, LOG_DIR: c.log_dir, ENGINE: c.engine, TOKENS_DIR: c.tokensDir, TOKENS_FILE: c.tokensFile,
    SYNC_ENABLED: c.sync.enabled ? 1 : 0, SYNC_INTERVAL: c.sync.interval_min, DEPLOY_KEY: c.sync.deploy_key,
    SYNC_GITCONFIG: c.sync.git_config,
    SYNC_SSH: /^(git@|ssh:\/\/)/.test(c.sync.repo || '') ? 1 : 0,
    GRAPH_ENABLED: c.graph.enabled ? 1 : 0, GRAPHIFY_VERSION: c.graph.graphify_version, GRAPH_TIME: hhmm(c.graph.time, '03:30'),
    HARVEST_ENABLED: c.harvest.enabled ? 1 : 0, HARVEST_TIME: hhmm(c.harvest.time, '02:30'),
    CLAUDE_RUN_AS: c.claude?.run_as || '',
    DT_READER: reader, DT_SPOKES: r.spokes.join(','), DT_VIEW: r.view ? 1 : 0, DT_OTHER_SPOKE: other,
    DT_QUERY: dt.query || '', DT_SEM_Q: dt.semantic?.q || '', DT_SEM_EXPECT: dt.semantic?.expect_path || '',
    DT_SUP_Q: dt.superseded?.q || '', DT_SUP_PATH: dt.superseded?.path || '',
    DT_DECAY_Q: dt.decay?.q || '', DT_DECAYS: dt.decay?.decays || '', DT_KEEPS: dt.decay?.keeps || '',
    DT_CONTAINER: dt.container || '',
  };
  return Object.entries(out).map(([k, v]) => `${k}=${q(v)}`).join('\n');
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [file, mode] = process.argv.slice(2);
  try {
    if (mode === '--install-sh') {
      const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
      const prepared = prepareInstallConfig(raw);
      const c = checkConfig(prepared, file);
      if (process.argv.includes('--apply') && JSON.stringify(raw) !== JSON.stringify(prepared)) {
        fs.writeFileSync(file, `${JSON.stringify(prepared, null, 2)}\n`);
      }
      console.log(shLines(c));
    } else if (mode === '--sync-gitconfig') {
      const c = loadConfig(file);
      console.log('[safe]\n' + syncGitPaths(c).map((p) => `\tdirectory = ${JSON.stringify(p)}`).join('\n'));
    } else if (mode === '--sh') console.log(shLines(loadConfig(file, { checkClaudeBin: true })));
    else if (mode === '--warm-lazy') {
      const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
      raw.warm = 'lazy';
      checkConfig(raw, file);
      const st = fs.statSync(file);
      fs.writeFileSync(`${file}.tmp`, `${JSON.stringify(raw, null, 2)}\n`, { mode: st.mode & 0o777 });
      try { fs.chownSync(`${file}.tmp`, st.uid, st.gid); } catch { /* not root: keep ours */ }
      fs.renameSync(`${file}.tmp`, file);
      console.log(`set warm=lazy in ${file}`);
    } else { console.error('usage: node config.mjs <brain.json> --sh|--warm-lazy'); process.exit(2); }
  } catch (e) { console.error(`config: ${e.message}`); process.exit(1); }
}
