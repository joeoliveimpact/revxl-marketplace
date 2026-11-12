// Ledger-only settlement. No tool output is an input to this module.
import { homedir } from "node:os";
import { ledgerUrl, resolveKey, normPath } from "./ledger.mjs";

export const TAIL_MS = 120000;
export const LEAD_MS = 30000;
export const FREEZE_MS = 600000;
export const YOUNG_MS = 750000;
export const SLACK_MS = 2000;
const finite = n => typeof n === "number" && Number.isFinite(n);
const windows = (st, off) => Object.values(st.holds || {}).flatMap(h => h.calls.map(([ep, held]) => ({
  ep, held, h, start: h.t + off - LEAD_MS - SLACK_MS,
  end: h.nc || h.post === undefined || h.stuck ? Infinity : h.post + off + TAIL_MS + SLACK_MS,
})));
const inside = (w, t) => w.start <= t && t <= w.end;
const neededSpan = (w, st, vNow) => {
  if (w.h.ok) return null;
  const start = st.led?.seen && st.led.seen <= vNow ? Math.max(w.start, st.led.seen - TAIL_MS) : w.start;
  const end = Math.min(w.end, vNow);
  return start <= end ? { start, end } : null;
};

// A fresh object or null: invalid arithmetic never changes the caller's state.
export function recompute(state, rows, vNow, off, uncovered = null, now, up) {
  try {
    const st = structuredClone(state);
    st.holds ||= {};
    st.led ||= { fails: 0, at: 0, seen: 0, eps: {} };
    st.led.eps ||= {};
    const validEntry = entry => entry && !Array.isArray(entry) && finite(entry.t) &&
      (entry.c === undefined || typeof entry.c === "boolean") &&
      (entry.f === undefined || typeof entry.f === "boolean") &&
      entry.rows && typeof entry.rows === "object" && !Array.isArray(entry.rows) &&
      Object.entries(entry.rows).every(([id, a]) => id !== "" && Array.isArray(a) && a.length === 2 &&
        finite(a[0]) && (a[1] === null || finite(a[1])) && (a[0] >= 0 || finite(a[1])));
    if (Object.values(st.led.eps).some(ids => !ids || typeof ids !== "object" || Array.isArray(ids) ||
      Object.values(ids).some(entry => !validEntry(entry)))) return null;
    if (!finite(vNow) || !finite(off) || !finite(now) || !finite(up)) return null;
    for (const h of Object.values(st.holds)) {
      if (h.ok === true) continue;
      const drift = (t, u) => !finite(u) || up < u || Math.abs((now - t) - (up - u)) > 5000;
      if (drift(h.t, h.u) || (h.post !== undefined && drift(h.post, h.pu))) h.stuck = true;
    }
    let ws = windows(st, off);
    if (st.fixed === undefined) st.fixed = st.spent - ws.reduce((sum, w) => sum + w.held, 0);
    if (!finite(st.fixed) || ws.some(w => !finite(w.held) || !finite(w.start) ||
      (w.end !== Infinity && !finite(w.end)))) return null;
    if (uncovered !== null) {
      for (const w of ws) {
        const span = neededSpan(w, st, vNow);
        if (span && span.start < uncovered.end && span.end >= uncovered.start) w.h.stuck = true;
      }
      ws = windows(st, off);
    }
    for (const w of ws) {
      const span = neededSpan(w, st, vNow);
      if (w.h.post !== undefined && !w.h.stuck && vNow >= w.end &&
        !(uncovered && span && span.start < uncovered.end && span.end >= uncovered.start)) w.h.ok = true;
    }
    for (const [ep, ids] of Object.entries(st.led.eps)) {
      for (const entry of Object.values(ids)) {
        if (entry.f === true) continue;
        const containing = ws.filter(w => w.ep === ep && inside(w, entry.t));
        if (containing.length && containing.every(w => w.end !== Infinity && vNow > w.end + FREEZE_MS)) entry.f = true;
      }
    }
    const groups = new Map();
    const seenRows = new Set();
    for (const row of rows) {
      if (row?.id === undefined || row?.id === null || row.id === "") return null;
      if (seenRows.has(row.id)) continue;
      seenRows.add(row.id);
      const id = typeof row.request_id === "string" && row.request_id ? row.request_id : "row:" + row.id;
      if (!finite(row.amount)) return null;
      let g = groups.get(id);
      if (!g) groups.set(id, g = { rows: {}, deductions: [] });
      let stamp = null;
      if (row.amount < 0) {
        const t = Date.parse(row.created_at);
        if (!finite(t)) return null;
        stamp = t;
        g.deductions.push({ ep: normPath(row.endpoint), t });
      }
      Object.defineProperty(g.rows, row.id, { value: [row.amount, stamp], enumerable: true, configurable: true, writable: true });
    }
    for (const [id, g] of groups) {
      const eps = new Set(g.deductions.filter(d => ws.some(w => w.ep === d.ep && inside(w, d.t))).map(d => d.ep));
      for (const [ep, ids] of Object.entries(st.led.eps)) if (Object.hasOwn(ids, id)) eps.add(ep);
      for (const ep of eps) {
        const ids = st.led.eps[ep] ||= {};
        const old = Object.hasOwn(ids, id) ? ids[id] : null;
        const frozen = old?.f === true;
        const stored = { ...old?.rows, ...g.rows };
        if (frozen) {
          for (const [rowId, [amount]] of Object.entries(g.rows)) {
            if (Object.hasOwn(old.rows, rowId)) stored[rowId] = old.rows[rowId];
            else if (amount >= 0) delete stored[rowId];
          }
        }
        const t = Math.min(...Object.values(stored).filter(([amount]) => amount < 0).map(([, stamp]) => stamp));
        if (!finite(t)) return null;
        Object.defineProperty(ids, id, { value: { t, rows: stored, ...(old?.c === true ? { c: true } : {}), ...(frozen ? { f: true } : {}) },
          enumerable: true, configurable: true, writable: true });
      }
    }
    let spent = st.fixed, usage = 0, full = 0;
    const over = [];
    for (const ep of new Set(ws.map(w => w.ep))) {
      const calls = ws.filter(w => w.ep === ep);
      const allIds = Object.values(st.led.eps[ep] || {});
      const ids = allIds.filter(entry => entry.c === true || Object.values(entry.rows).some(([amount, stamp]) =>
        amount < 0 && calls.some(w => w.end !== Infinity && inside(w, stamp))));
      for (const entry of ids) entry.c = true;
      const net = ids.reduce((sum, entry) => sum + Math.ceil(Math.max(0, -Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0))), 0);
      const counted = new Set(ids);
      const endedOpen = calls.filter(w => w.end === Infinity);
      const openIds = allIds.filter(entry => !counted.has(entry) && Object.values(entry.rows).some(([amount, stamp]) =>
        amount < 0 && endedOpen.some(w => inside(w, stamp))));
      const openRows = openIds.reduce((sum, entry) => sum + Math.ceil(Math.max(0, -Object.values(entry.rows).reduce((n, [amount]) => n + amount, 0))), 0);
      const openHolds = endedOpen.reduce((sum, w) => sum + w.held, 0);
      const finiteCalls = calls.filter(w => w.end !== Infinity);
      const open = finiteCalls.filter(w => vNow < w.end || !w.h.ok);
      const finiteHolds = ids.length ? open : finiteCalls;
      usage += net + openRows;
      full += finiteHolds.length + endedOpen.length;
      spent += finiteHolds.reduce((sum, w) => sum + w.held, 0) + net + (openHolds + openRows);
      if (net + openRows > finiteCalls.filter(w => !finiteHolds.includes(w)).reduce((sum, w) => sum + w.held, 0)) over.push(ep);
    }
    if (![spent, usage, full].every(Number.isInteger)) return null;
    st.spent = spent;
    st.usage = usage;
    st.full = full;
    st.led.fails = 0;
    st.led.off = off;
    if (uncovered === null) st.led.seen = vNow;
    return { state: st, over };
  } catch { return null; }
}

function coverageNeed(st, off, vNow) {
  return Math.min(...windows(st, off).map(w => neededSpan(w, st, vNow)).filter(Boolean).map(span => span.start));
}

// left() is the guard's monotonic deadline, including process startup and lock waits.
export async function readLedger(st, { left, transport = globalThis.fetch, env = process.env, home = homedir() } = {}) {
  try {
    const key = resolveKey(env, home);
    if (!key || left() <= 700) return null;
    let cursor = "", rows = [], vNow, off, oldest = Infinity, need, previous = Infinity, lowest = Infinity, unordered = false;
    for (let page = 0; page < 2; page++) {
      const ms = Math.floor(Math.min(3000, left() - 700));
      if (ms <= 0) return null;
      const response = await transport(ledgerUrl("/v1/credits/transactions", { limit: 50, cursor }), {
        method: "GET", headers: { "x-api-key": key }, signal: AbortSignal.timeout(ms),
      });
      const arrived = Date.now();
      const date = Date.parse(response.headers.get("Date"));
      if (!response.ok || !finite(date)) return null;
      if (page === 0) {
        vNow = date;
        off = vNow - arrived;
        if (finite(st.led?.off) && Math.abs(off - st.led.off) > 30000) return { failed: true, off };
      } else if (Math.abs(date - vNow) > 10000) return null;
      const body = await response.json();
      if (!Array.isArray(body?.data?.items) || left() <= 0) return null;
      rows.push(...body.data.items);
      for (const row of body.data.items) {
        const t = Date.parse(row?.created_at);
        if (!finite(t) || t > vNow + 10000) return null;
        if (t > lowest + 60000) unordered = true;
        lowest = Math.min(lowest, t);
        previous = t;
      }
      oldest = unordered || !body.data.items.length ? Infinity : Math.max(...rows.slice(-3).map(r => Date.parse(r.created_at)));
      cursor = body.data.next_cursor;
      need = coverageNeed(st, off, vNow);
      if (!cursor || need === Infinity || oldest <= need || page === 1 || left() < 2000) break;
    }
    if (left() <= 0) return null;
    return { rows, vNow, off, uncovered: need !== Infinity && (unordered || (cursor && oldest > need)) ? { start: need, end: oldest } : null };
  } catch { return null; }
}
