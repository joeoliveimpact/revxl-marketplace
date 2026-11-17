// view.js: the read-only brain viewer. Every note value is shown with textContent, never as HTML.
// The token lives in sessionStorage (this tab only) and goes out only as a Bearer header.
'use strict';
const $ = (id) => document.getElementById(id);
const KEY = 'fewzhun-box-token';
const MSG = {
  400: 'The search was not accepted',
  401: 'Not signed in, or the token is not recognised: paste a reader token.',
  403: 'This token may not read that spoke.',
  404: 'Not in the brain (or not active).',
  502: 'The search engine failed for every spoke. Try again in a minute.',
};

async function api(path) {
  const token = sessionStorage.getItem(KEY) || '';
  let r;
  try {
    r = await fetch(path, { headers: { authorization: `Bearer ${token}` }, cache: 'no-store', credentials: 'omit' });
  } catch {
    return { status: 0, body: null };
  }
  let body = null;
  try { body = await r.json(); } catch { /* not JSON */ }
  return { status: r.status, body };
}

const say = (text) => { $('status').textContent = text; };
const explain = (r) => (r.status === 0 ? 'The brain service is not answering.'
  : `${MSG[r.status] || `Error ${r.status}`}${r.status === 400 && r.body?.error ? `: ${r.body.error}` : ''}`);

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

async function start() {
  const r = await api('/me');
  if (r.status !== 200) {
    $('signin').hidden = false;
    $('app').hidden = true;
    if (sessionStorage.getItem(KEY)) say(explain(r));
    return;
  }
  $('signin').hidden = true;
  $('app').hidden = false;
  const sel = $('spoke');
  sel.replaceChildren(el('option', 'all my spokes'));
  sel.firstChild.value = '';
  for (const s of r.body.spokes) { const o = el('option', s); o.value = s; sel.append(o); }
  const g = $('graphs');
  g.replaceChildren();
  $('graph-section').hidden = !r.body.view || !r.body.spokes.length;
  for (const s of r.body.view ? r.body.spokes : []) {
    const b = el('button', `Graph: ${s}`);
    b.type = 'button';
    b.addEventListener('click', () => openGraph(s));
    g.append(b);
  }
  say(`Signed in. You can read: ${r.body.spokes.join(', ') || 'no spokes'}.`);
}

async function search(ev) {
  ev.preventDefault();
  const q = $('q').value.trim();
  if (!q) return;
  const params = new URLSearchParams({ q, limit: '20' });
  if ($('spoke').value) params.set('spokes', $('spoke').value);
  say('Searching...');
  const r = await api(`/search?${params}`);
  const list = $('results');
  list.replaceChildren();
  if (r.status !== 200) { say(explain(r)); return; }
  for (const h of r.body.results) {
    const li = el('li');
    const b = el('button', h.title);
    b.type = 'button';
    b.addEventListener('click', () => read(h.spoke, h.path));
    li.append(b, el('div', `${h.spoke} / ${h.path} | ${h.date || 'undated'}`, 'meta'), el('div', h.snippet));
    list.append(li);
  }
  const failed = r.body.failed ? ` (spoke failed: ${Object.keys(r.body.failed).join(', ')})` : '';
  say(r.body.results.length ? `${r.body.results.length} note(s) from ${r.body.spokes.join(', ')}${failed}` : `Not in the brain${failed}.`);
}

async function read(spoke, path) {
  const r = await api(`/read?${new URLSearchParams({ spoke, path })}`);
  if (r.status !== 200) { say(explain(r)); return; }
  $('note-title').textContent = r.body.title;
  $('note-meta').textContent = `${r.body.spoke} / ${r.body.path} | ${r.body.date || 'undated'} | ${r.body.status}`;
  $('note-text').textContent = r.body.text;
  $('note').hidden = false;
  $('note').scrollIntoView();
}

// The graph page can't carry a header, so trade the token for a one-use 60 s ticket.
async function openGraph(spoke) {
  const r = await api(`/graph/${encodeURIComponent(spoke)}/ticket`);
  if (r.status !== 200 || typeof r.body?.url !== 'string' || !r.body.url.startsWith('/graph/')) { say(explain(r)); return; }
  const f = $('graph');
  f.src = r.body.url;
  f.hidden = false;
  say(`Graph of ${spoke}.`);
}

$('signin-form').addEventListener('submit', (ev) => {
  ev.preventDefault();
  sessionStorage.setItem(KEY, $('token').value.trim());
  $('token').value = '';
  start();
});
$('search-form').addEventListener('submit', search);
$('signout').addEventListener('click', () => {
  sessionStorage.removeItem(KEY);
  $('results').replaceChildren();
  $('note').hidden = true;
  $('graph').hidden = true;
  $('graph').removeAttribute('src');
  say('');
  start();
});
start();
