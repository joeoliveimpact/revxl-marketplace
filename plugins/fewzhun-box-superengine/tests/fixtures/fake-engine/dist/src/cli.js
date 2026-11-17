// A stand-in for obsidian-hybrid-search 0.12.7's CLI, for tests (pattern: Fewzhun v1.1
// tests/fixtures/fake-engine.mjs). Only `reindex` is supported: it writes the spoke's index file
// in place (same inode, like an incremental reindex). Logs argv + env keys to FAKE_ENGINE_LOG.
// FAKE_ENGINE_FAIL=1 exits 1. The server's worker never runs this file; it loads the siblings.
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
if (process.env.FAKE_ENGINE_LOG) {
  fs.appendFileSync(process.env.FAKE_ENGINE_LOG, `${JSON.stringify({ args, cwd: process.cwd(), envKeys: Object.keys(process.env),
    vault: process.env.OBSIDIAN_VAULT_PATH, ignore: process.env.OBSIDIAN_IGNORE_PATTERNS })}\n`);
}
if (process.env.FAKE_ENGINE_FAIL === '1') { process.stderr.write('boom'); process.exit(1); }
if (args[0] !== 'reindex') { process.stderr.write('unsupported'); process.exit(2); }
const vault = process.env.OBSIDIAN_VAULT_PATH || process.cwd();
const walk = (rel = '') => fs.readdirSync(path.join(vault, rel), { withFileTypes: true }).flatMap((e) => {
  if (e.name.startsWith('.')) return [];
  const r = rel ? `${rel}/${e.name}` : e.name;
  return e.isDirectory() ? walk(r) : e.name.endsWith('.md') ? [r] : [];
});
fs.writeFileSync(path.join(vault, '.obsidian-hybrid-search.db'), `${JSON.stringify(walk())}\n`);
process.stdout.write('ok\n');
