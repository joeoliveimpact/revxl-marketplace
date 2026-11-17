// Fake searcher.js (from the frozen brain-search selftest): a note matches when its text contains the
// query; its score is the note's `fake_score:` value (0.5 if none). The "model" loads once per process.
// Magic queries: crashme exits the worker, noisy writes stray stdout the server must ignore.
import fs from 'node:fs';
import path from 'node:path';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let loaded = false;
export async function search(q, { limit = 10 } = {}) {
  if (!loaded) { await sleep(100); loaded = true; }
  if (q === 'crashme') process.exit(3);
  if (q === 'noisy') process.stdout.write('null\n[1]\n"x"\n42\nnot json\n');
  const vault = process.env.OBSIDIAN_VAULT_PATH;
  const walk = (rel = '') => fs.readdirSync(path.join(vault, rel), { withFileTypes: true }).flatMap((e) => {
    if (e.name.startsWith('.')) return [];
    const r = rel ? `${rel}/${e.name}` : e.name;
    return e.isDirectory() ? walk(r) : e.name.endsWith('.md') ? [r] : [];
  });
  const hits = [];
  for (const rel of walk()) {
    let t;
    try { t = fs.readFileSync(path.join(vault, rel), 'utf8'); } catch { continue; }
    if (!t.toLowerCase().includes(String(q).toLowerCase())) continue;
    const s = /fake_score: ([0-9.]+)/.exec(t);
    hits.push({ path: rel, title: path.basename(rel, '.md'), score: s ? Number(s[1]) : 0.5, snippet: '' });
  }
  hits.sort((x, y) => y.score - x.score);
  return hits.slice(0, limit);
}
