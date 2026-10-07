/*
 * R10 — hooks/price.mjs, the single pricer.
 *
 * SYNCHRONOUS BY CONSTRUCTION. price.mjs is a pure module — no I/O, no network, no promise —
 * so it is imported and called directly and every assertion runs inside f.fn(). run.mjs does
 * not await (P26); nothing in this file returns a promise for it to drop.
 *
 * Every price is read from the committed costs.json, whose `range` comes from the vendor
 * catalogue's own label. The fixtures name real entries and state the premise they rest on, so
 * a regenerated pricebook that moves a premise fails loudly here rather than quietly.
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { quote, legRange } from "../../price.mjs";
import { COSTS, assert } from "../lib.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const CURATED = resolve(HERE, "..", "..", "..", "skills", "research-plays", "curated-workflows.json");
const costs = JSON.parse(readFileSync(COSTS, "utf8"));
const leg = (call, countLow, countHigh) => ({ call, countLow, countHigh });
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export default [
  {
    id: "PR1-null-range-is-no-ceiling",
    desc: "a leg whose range is null makes the quote's high null (no ceiling) — never 0, never skipped, in either order",
    fn() {
      assert(costs["POST web/batch-scrape"].range === null, "premise: web/batch-scrape is range null (G7)");
      const q = quote([leg("GET prism/leads", 1, 1), leg("POST web/batch-scrape", 1, 3)], costs);
      assert(q.high === null, `high must be null (no ceiling), got ${JSON.stringify(q)}`);
      assert(q.low === 50, `the priced leg still carries the low, got ${JSON.stringify(q)}`);
      const r = quote([leg("POST web/batch-scrape", 1, 1), leg("GET prism/leads", 1, 1)], costs);
      assert(r.high === null, `a later finite leg must not overwrite the null, got ${JSON.stringify(r)}`);
      assert(legRange(costs, "GET prism/investigate") === null, "a G7 sentence label is a null range");
      assert(same(legRange(costs, "GET prism/lookup"), [1, 5]), "the named override (Joe 09.24.26): prism/lookup reads 1-5 from its label");
      let threw = false;
      try { quote([leg("GET nosuch/endpoint", 1, 1)], costs); } catch { threw = true; }
      assert(threw, "an unknown call must throw — a call nobody priced is never free");
    },
  },
  {
    id: "PR2-count-times-label-range",
    desc: "low = sum countLow x range[0], high = sum countHigh x range[1], read from the LABEL range (linkedin/search/posts 1-56, not its credits field 5)",
    fn() {
      assert(same(costs["GET linkedin/search/posts"].range, [1, 56]), "premise: linkedin/search/posts is 1-56");
      const one = quote([leg("GET linkedin/search/posts", 2, 3)], costs);
      assert(same(one, { low: 2, high: 168 }), `2 x 1 .. 3 x 56 = 2..168, got ${JSON.stringify(one)}`);
      const three = quote(
        [leg("GET linkedin/search/posts", 2, 3), leg("GET search/news", 0, 1), leg("GET instagram/profile", 1, 4)],
        costs
      );
      assert(same(three, { low: 3, high: 234 }), `2+0+1 .. 168+62+4 = 3..234, got ${JSON.stringify(three)}`);
      assert(same(quote([], costs), { low: 0, high: 0 }), "no legs is a derived 0, not an error");
    },
  },
  {
    id: "PR3-hand-reviewed-quote-untouched",
    desc: "the handReviewed curated rows keep their reviewed quote; for the three reviewed before R10 the pricer's arithmetic over the same legs differs, so a re-derivation would have moved it; ad-library-recon (R18, Q-f) was reviewed as that arithmetic on the 10-06 costs, 15-65",
    fn() {
      const spec = JSON.parse(readFileSync(CURATED, "utf8"));
      // The reviewed figures as they stood at a8625f6. R10 re-derives every derivable row and
      // none of these.
      const reviewed = {
        "voice-of-customer": [25, 1050, 120],
        "ai-visibility-audit": [20, 1605, 40],
        "share-of-voice": [80, 200, 200],
        // R18 (Q-f): company/ads turned metered on 10-06, so the row became response-determined;
        // its review IS the 10-06 arithmetic, so the overwrite probe below does not apply to it.
        "ad-library-recon": [15, 65, 65],
      };
      const reviewedAsArithmetic = new Set(["ad-library-recon"]);
      const rows = spec.workflows.filter((w) => w.handReviewed === true);
      assert(
        same(rows.map((w) => w.id).sort(), Object.keys(reviewed).sort()),
        `the handReviewed set moved: ${JSON.stringify(rows.map((w) => w.id))}`
      );
      for (const w of rows) {
        const [lo, hi, ceil] = reviewed[w.id];
        assert(
          w.quote.low === lo && w.quote.high === hi && w.ceiling === ceil,
          `${w.id}: the reviewed quote ${lo}-${hi} / ceiling ${ceil} changed to ` +
            `${w.quote.low}-${w.quote.high} / ${w.ceiling}`
        );
        const q = quote(w.endpoints, costs);
        assert(q.high !== null, `${w.id}: its legs must still price, got ${JSON.stringify(q)}`);
        if (reviewedAsArithmetic.has(w.id)) {
          assert(q.low === lo && q.high === hi, `${w.id}: reviewed as the 10-06 arithmetic ${lo}-${hi}, the pricer now says ${q.low}-${q.high}`);
          continue;
        }
        assert(
          !(q.low === lo && q.high === hi),
          `${w.id}: the arithmetic equals the stored quote, so this fixture cannot tell a review from an overwrite`
        );
      }
    },
  },
];
