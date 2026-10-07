/*
 * The single pricer (Stage B rev4 R10). One place turns a list of calls into a credit range.
 *
 *   import { quote } from "./price.mjs";
 *   quote([{ call: "GET linkedin/search/posts", countLow: 1, countHigh: 3 }], costs)
 *     -> { low: 1, high: 168 }
 *
 * Every price comes from hooks/costs.json, whose entries gen_refs.py builds from the vendor
 * catalogue's own `credits_label`: `range` is what ONE call costs, [lo, hi], or null when the
 * label is a sentence no ceiling can be computed from (the can't-count class). Nothing here
 * reads `credits` — that is the catalogue's price FIELD, recorded beside the label and never
 * trusted on its own (`linkedin/search/posts`: field 5, spec 1, label 1-56).
 *
 *   low  = SUM of countLow  x range[0]
 *   high = SUM of countHigh x range[1]     — null as soon as any leg has no ceiling
 *
 * A leg with range null adds nothing to `low` (its floor is unknown, so 0 is the honest lower
 * bound) and turns `high` into null: "no ceiling" propagates, it is never read as 0.
 * An unknown call THROWS. A phantom endpoint is a call nobody priced, never a free one.
 *
 * Pure: no I/O, no network, no process exit — stdlib only, and nothing is ever mutated.
 */

const isEntry = (e) => e !== null && typeof e === "object" && "range" in e;
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/*
 * The costs.json entry for a "VERB path" call, resolved in the credit guard's own order
 * (credit-guard.mjs lookup()): the exact key, then a templated key on the same verb
 * ("web/jobs/{job_id}"), then the WORST entry on any other verb — no ceiling beats every
 * ceiling, a higher ceiling beats a lower one. Returns null when costs.json knows nothing.
 */
export function entryFor(costs, call) {
  const sp = String(call).indexOf(" ");
  if (sp < 0) throw new Error(`endpoint key must be "VERB path", got ${JSON.stringify(call)}`);
  const verb = call.slice(0, sp).toUpperCase();
  const path = call.slice(sp + 1);
  if (isEntry(costs[`${verb} ${path}`])) return costs[`${verb} ${path}`];
  let other = null;
  const rank = (e) => (e.range === null ? Infinity : e.range[1]);
  const worse = (e) => { if (other === null || rank(e) > rank(other)) other = e; };
  for (const k of Object.keys(costs)) {
    if (k.startsWith("_") || !isEntry(costs[k])) continue;
    const i = k.indexOf(" ");
    const kv = k.slice(0, i);
    const kp = k.slice(i + 1);
    if (!kp.includes("{")) {
      if (kp === path) worse(costs[k]);
      continue;
    }
    const re = new RegExp("^" + esc(kp).replace(/\\\{[a-z_0-9]+\\\}/gi, "[^/]+") + "$");
    if (!re.test(path)) continue;
    if (kv === verb) return costs[k];
    worse(costs[k]);
  }
  return other;
}

/* One call's [lo, hi], or null for "no ceiling". Throws on a call costs.json does not know. */
export function legRange(costs, call) {
  const e = entryFor(costs, call);
  if (!e) throw new Error(`${call}: not in costs.json — a call nobody priced is never free`);
  return e.range === null ? null : [e.range[0], e.range[1]];
}

/* endpoints[] = [{ call, countLow, countHigh }] -> { low, high }; high null = no ceiling. */
export function quote(endpoints, costs) {
  let low = 0;
  let high = 0;
  for (const leg of endpoints || []) {
    const r = legRange(costs, leg.call);
    if (r === null) { high = null; continue; }
    low += r[0] * leg.countLow;
    if (high !== null) high += r[1] * leg.countHigh;
  }
  return { low, high };
}
