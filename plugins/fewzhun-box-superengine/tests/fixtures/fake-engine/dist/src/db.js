// Fake db.js: openDb logs "<spoke> <pid>" to <root>/starts.log (vault = <root>/spokes/<spoke>), one line per worker start.
import fs from 'node:fs';
import path from 'node:path';

export function openDb() {
  const vault = process.env.OBSIDIAN_VAULT_PATH;
  fs.appendFileSync(path.join(vault, '..', '..', 'starts.log'), `${path.basename(vault)} ${process.pid}\n`);
}
export function applyDbConfigDefaults() {}
export function saveConfigMeta() {}
export function getStoredModel() { return null; }
export function getStoredEmbeddingDim() { return 384; }
export function initVecTable() {}
