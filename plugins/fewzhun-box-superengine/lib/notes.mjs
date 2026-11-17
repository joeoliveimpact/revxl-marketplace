// notes.mjs: the note rules shared by the server and sync, so both hide the same notes.
// Ported from the frozen brain-search server (frontmatter, dates, decay) and Fewzhun v1.1
// search.mjs (hidden statuses). Node 20, stdlib only.

// Frontmatter: simple `key: value` lines between --- fences. BOM tolerated.
export function frontmatter(text) {
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  const m = /^---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/.exec(text);
  const fm = {};
  if (m) {
    for (const line of m[1].split(/\r?\n/)) {
      const kv = /^([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$/.exec(line);
      if (kv) fm[kv[1]] = kv[2].replace(/^(['"])(.*)\1$/, '$2');
    }
  }
  return { fm, body: m ? text.slice(m[0].length) : text };
}

// Active rule (the frozen brain-search server's): only status: active (trimmed, any case) is shown.
// Anything else, a missing status included, is hidden. A note with superseded_by set is hidden too.
const unset = (v) => ['', 'null', '~', '""', "''"].includes(String(v ?? '').trim().toLowerCase());
export function isActive(fm) {
  return String(fm.status ?? '').trim().toLowerCase() === 'active' && unset(fm.superseded_by);
}

// Instruction files are not notes: AGENTS.md and README.md at any depth.
export const notANote = (rel) => /(^|\/)(agents|readme)\.md$/i.test(rel);

export function isoDate(v) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v || ''));
  if (!m) return null;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3] ? d.toISOString().slice(0, 10) : null;
}
// source_date ranks; date is the fallback. File times are never used.
export const noteDate = (fm) => isoDate(fm.source_date) || isoDate(fm.date);

// Decay (the hub_rerank formula, as in the frozen brain-search server): x (0.5 + 0.5 x max(0, 1 - age/365)).
// spokeDecay is the spoke's `decay`: true | false | "never". A note decays when its spoke has
// decay: true, or when it is marked sot_policy: decay and its spoke is not "never".
// sot_policy: strict never decays. An undated note has no known age, so no decay.
export function weight(spokeDecay, fm, ageDays) {
  const policy = String(fm.sot_policy || '').trim().toLowerCase();
  if (ageDays === null || policy === 'strict') return 1;
  if (spokeDecay !== true && !(policy === 'decay' && spokeDecay !== 'never')) return 1;
  const rw = Math.max(0, Math.min(1, 1 - ageDays / 365));
  return 0.5 + 0.5 * rw;
}

// Line endings and BOM normalized the way sync stores copies.
export const normalize = (text) => (text.charCodeAt(0) === 0xFEFF ? text.slice(1) : text).replace(/\r\n/g, '\n');
