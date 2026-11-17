#!/usr/bin/env node
// tokens.mjs: reader tokens for the box brain. Run as root on the box.
//   node tokens.mjs add <reader>      create the reader's token if missing (re-running keeps it)
//   node tokens.mjs revoke <reader>   delete the token; the server stops accepting it at once
//   node tokens.mjs list              readers, their spokes and the token's last 4 characters
// Files (next to brain.json, so /etc/fewzhun-box by default; FEWZHUN_BOX_CONFIG moves them):
//   tokens/<reader>  the raw token (0600, in a 0700 folder): hand it to that reader, never paste it in chat
//   tokens.json      only each token's sha256; what a reader may read lives in brain.json readers
// Never prints a token value.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { configFile, loadConfig, NAME_RX } from '../lib/config.mjs';

const dir = path.dirname(configFile());
const tdir = path.join(dir, 'tokens');
const jf = path.join(dir, 'tokens.json');
const say = (s) => process.stdout.write(`${s}\n`);
const die = (s, code = 1) => { process.stderr.write(`tokens: ${s}\n`); process.exit(code); };

const readJson = () => { try { return JSON.parse(fs.readFileSync(jf, 'utf8')); } catch (e) { if (e.code === 'ENOENT') return {}; return die(`${jf} is not valid JSON: ${e.message}`); } };
function writeJson(json) {
  const text = `${JSON.stringify(json, null, 2)}\n`;
  let mode = 0o640;
  let own = null;
  try { const st = fs.statSync(jf); mode = st.mode & 0o777; own = st; } catch { /* new file */ }
  fs.writeFileSync(`${jf}.tmp`, text, { mode });
  if (own) { try { fs.chownSync(`${jf}.tmp`, own.uid, own.gid); } catch { /* not root */ } }
  fs.renameSync(`${jf}.tmp`, jf);
}
const readers = () => { try { return loadConfig().readers; } catch { return null; } };
const sha = (t) => crypto.createHash('sha256').update(t).digest('hex');

const [cmd, name] = process.argv.slice(2);
if (cmd === 'add' || cmd === 'revoke') {
  if (!name || !NAME_RX.test(name)) die('reader name may use only letters, digits, - and _', 2);
}

if (cmd === 'add') {
  fs.mkdirSync(tdir, { recursive: true, mode: 0o700 });
  const f = path.join(tdir, name);
  const made = !fs.existsSync(f);
  if (made) fs.writeFileSync(f, `${crypto.randomBytes(32).toString('hex')}\n`, { mode: 0o600, flag: 'wx' });
  const json = readJson();
  const hash = sha(fs.readFileSync(f, 'utf8').trim());
  const changed = json[name]?.sha256 !== hash;
  json[name] = { sha256: hash };
  if (changed) writeJson(json);
  say(`token ${name}: ${f} (${made ? 'created' : 'kept'})${changed ? `; ${jf} updated` : ''}`);
  const r = readers();
  if (r && !r[name]) say(`note: ${name} is not in brain.json readers, so this token can read nothing until you add it there`);
} else if (cmd === 'revoke') {
  const json = readJson();
  const had = name in json;
  delete json[name];
  if (had) writeJson(json);
  try { fs.unlinkSync(path.join(tdir, name)); } catch { /* no raw file */ }
  say(had ? `token ${name}: revoked (the server refuses it from now on)` : `token ${name}: there was no such token`);
} else if (cmd === 'list') {
  const json = readJson();
  const r = readers() || {};
  const names = [...new Set([...Object.keys(json), ...Object.keys(r)])].sort();
  if (!names.length) say('no readers and no tokens yet');
  for (const n of names) {
    let last4 = '????';
    try { last4 = fs.readFileSync(path.join(tdir, n), 'utf8').trim().slice(-4); } catch { /* not readable here */ }
    const tokenPart = json[n] ? `token ...${last4}` : 'NO TOKEN (run: tokens.mjs add)';
    const scope = r[n] ? `spokes: ${r[n].spokes.join(', ') || 'none'}; viewer graphs: ${r[n].view ? 'yes' : 'no'}` : 'not in brain.json readers: can read nothing';
    say(`${n}: ${tokenPart}; ${scope}`);
  }
} else {
  die('usage: node tokens.mjs add <reader> | revoke <reader> | list', 2);
}
