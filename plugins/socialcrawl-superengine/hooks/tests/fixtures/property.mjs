/*
 * PROPERTY SET — the round-2 checker's self-disclosed blind spot, made executable.
 *
 * Its own words: "my 342-chain C2 scan checks within-message consistency (quote vs roster vs
 * total), not quote-vs-row-ceiling. It returned 0 mismatches on a build that under-quotes
 * web/crawl?page=1 by 10,000x ... A future scan should assert quoted >= the row's published
 * ceiling whenever no quantity evidence exists."
 *
 * These are not per-command fixtures. They walk EVERY metered or no-ceiling entry of costs.json
 * (R10: `metered: true` or `range: null` — the rows the retired _perUnit block used to hold,
 * now read from each entry's own label range) — the whole set, not just the rows some other
 * fixture happens to touch — and assert the invariant
 * directly, so a discount reintroduced on ANY row fails here even if nobody wrote a fixture
 * for that endpoint. The figure compared is the one the guard actually commits to: the worst
 * case it writes into the session counter (R14a: committed at once under the cap, or held as
 * pending behind a cap-step ask until the Post run commits it — countOf reads both).
 *
 * Direction, restated from the plan's R1 rule: over-quoting is safe and under-quoting is the
 * defect class, so the assertion is >=, never ==.
 *
 * MEASURED PER-BUILD EXPECTATIONS (same 51bdd7f extraction as the sweep set):
 *   P1-per-unit-row-never-below-ceiling  PASS on BOTH — with no quantity evidence at all the
 *                                        pre-fix driver discount had nothing to fire on, so
 *                                        P1 is a regression bar for the future, not a bite.
 *   P2-quantity-params-never-discount    FAIL at 51bdd7f (prism/ai-visibility quoted 2 against
 *                                        a 1605 ceiling)   PASS at the fix HEAD.
 */
import { readFileSync } from "node:fs";
import { run, V1, COSTS, quoted as countOf, assert, assertDecision, assertMatch } from "../lib.mjs";

const NOLOCAL = { unsetEnv: ["GROQ_API_KEY"], env: { PATH: "" } };
const ENTRIES = JSON.parse(readFileSync(COSTS, "utf8"));
const PER_UNIT = Object.fromEntries(
  Object.entries(ENTRIES)
    .filter(([k, e]) => !k.startsWith("_") && e && (e.metered || e.range === null))
    .map(([k, e]) => [k, { high: e.range ? e.range[1] : null }])
);

// Every quantity-shaped param name that has ever been read as a multiplier by this guard, plus
// the five distinct bare-word `driver` values carried by the six rows the checker audited
// (probe, leg, url x2, page, ttl_seconds). None of them is a proven billing driver on any
// shipped row per the in-tree vendor openapi, so none of them may lower a quote.
const QUANTITY_BLOB =
  "limit=1&max=1&page=1&count=1&per_page=1&page_size=1&num_results=1&max_results=1" +
  "&url=1&probe=1&leg=1&ttl_seconds=0";

function rows() {
  return Object.entries(PER_UNIT).map(([key, m]) => {
    const sp = key.indexOf(" ");
    return { key, verb: key.slice(0, sp), path: key.slice(sp + 1), m };
  });
}

function invoke(r, query) {
  const verbFlag = r.verb === "GET" ? "-s" : `-X ${r.verb} -d '{}'`;
  return run(`curl ${verbFlag} "${V1}${r.path}${query}"`, NOLOCAL);
}

export default [
  {
    id: "P1-per-unit-row-never-below-ceiling",
    desc: "PROPERTY: with no quantity evidence in the command, every metered row quotes at least its label ceiling, and every no-ceiling row asks",
    fn() {
      const checked = [];
      for (const r of rows()) {
        const high = r.m.high;
        const res = invoke(r, "");
        if (typeof high !== "number" || !Number.isFinite(high)) {
          // A row the vendor's label gives no ceiling for (range null). It must not invent a
          // number — it takes the dedicated no-ceiling ask instead.
          assertDecision(res, "ask", `${r.key}: a per-unit row with no published ceiling must ask`);
          assertMatch(res, /NO computable ceiling/, `${r.key}: must say plainly that no ceiling exists`);
          continue;
        }
        const quoted = countOf(res.state);
        assert(
          quoted !== null,
          `${r.key}: a priced per-unit call must record a numeric worst case, read ${res.stateRaw}`,
          res
        );
        assert(
          quoted >= high,
          `${r.key}: quoted ${quoted} is BELOW the published ceiling ${high} with no quantity ` +
            `evidence in the command — that is the under-quote class this property exists to catch`,
          res
        );
        checked.push(r.key);
      }
      assert(checked.length >= 30, `expected every metered entry to be walked, checked ${checked.length}`);
    },
  },
  {
    id: "P2-quantity-params-never-discount",
    desc: "PROPERTY: no quantity-shaped query param can pull a metered quote below the row's label ceiling (the S2/D5 class)",
    fn() {
      for (const r of rows()) {
        const high = r.m.high;
        if (typeof high !== "number" || !Number.isFinite(high)) continue;
        const res = invoke(r, `?${QUANTITY_BLOB}`);
        const quoted = countOf(res.state);
        assert(
          quoted !== null && quoted >= high,
          `${r.key}: quoted ${quoted} against a ${high} ceiling once quantity params were ` +
            `present — a param that is not a proven billing driver must never discount`,
          res
        );
      }
      // The exact regression the property was written for, stated as a number.
      const crawl = run(`curl -X POST "${V1}web/crawl?page=1&limit=10000" -d '{}'`);
      assert(
        countOf(crawl.state) === 10000,
        `web/crawl?page=1 must record 10000, read ${crawl.stateRaw}`,
        crawl
      );
    },
  },
  {
    id: "P3-verb-twin-names-whose-price",
    desc: "PROPERTY: a free GET whose path has a no-ceiling entry on another verb still asks (path-only fallback), but names whose price it quotes and never pins that price on the GET",
    fn() {
      const twins = Object.entries(ENTRIES)
        .filter(([k, e]) => !k.startsWith("_") && !k.startsWith("GET ") && e && e.range === null)
        .map(([k]) => [k, `GET ${k.slice(k.indexOf(" ") + 1)}`])
        .filter(([, g]) => ENTRIES[g] && Array.isArray(ENTRIES[g].range) && ENTRIES[g].range[1] === 0);
      assert(twins.length > 0, "expected at least one no-ceiling entry with a free GET twin");
      for (const [key, get] of twins) {
        const res = run(`curl -s "${V1}${get.slice(4)}"`, NOLOCAL);
        assertDecision(res, "ask", `${get}: the path-only fallback still asks`);
        assert(res.message.includes(`prices ${key} by a sentence`), `${get}: must name ${key} as the price's owner`, res);
        assertMatch(res, /reads as a GET/, `${get}: must say the command reads as the free verb`);
        assert(!res.message.includes(`prices ${get} by`), `${get}: a free read never gets another verb's price as its own`, res);
      }
    },
  },
];
