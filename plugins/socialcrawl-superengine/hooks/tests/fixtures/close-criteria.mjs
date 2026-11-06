/*
 * R1 CLOSE CRITERIA — U1 and U2, the two defects the 08.27.26 build fixed.
 *
 * These are here so a later edit cannot silently undo them: U1 (a chain quoted at its first
 * leg instead of its total) and U2 (expensive calls never reaching the session counter) are
 * both under-quote classes, and both were invisible until a fixture named the number.
 */
import { run, session, V1, BALANCE, LIMIT, quoted, mLimit, srcAuto, assert, assertDecision, assertNoMatch } from "../lib.mjs";

export default [
  {
    id: "U1-three-call-chain-280",
    desc: "U1, D28: a 3-call chain is counted at its ~280 TOTAL (pre-fix it quoted the first leg, ~5): past the 200 limit it is denied with exactly M_LIMIT naming 280, and nothing is counted",
    fn() {
      const cmd =
        `curl -s "${V1}web/scrape?url=https://x.test" && ` +
        `curl -s "${V1}prism/creator-vet?handle=abc" && ` +
        `curl -s "${V1}prism/share-of-voice?brands=a,b"`;
      const r = run(cmd);
      assertDecision(r, "deny", "a 280cr chain is past the 200 limit");
      assert(r.message === mLimit({ spent: 0, worst: 280, limit: LIMIT, src: srcAuto(BALANCE), bf: r.bf }),
        `exactly M_LIMIT with the command total 280 (5 + 75 + 200), read ${r.message}`, r);
      // The pre-fix contradiction: the chain quoted at its first leg.
      assertNoMatch(r, /worst case: ~5 credits/, "the chain must never be quoted at its first leg");
      assert(quoted(r.state) === 0, `a deny counts nothing, read ${JSON.stringify(r.state)}`, r);
    },
  },
  {
    id: "U2-session-accumulation",
    desc: "U2: the session counter accumulates across calls, including the expensive ones",
    fn() {
      // The checker's headline: seeded 75 + a 1cr call reads 76.
      const s = session().seed({ spent: 75 });
      const r = s.run(`curl -s "${V1}amazon/shop?q=abc"`);
      assertDecision(r, null, "a 1cr call under the limit is silent (R14a: no inform line)");
      assert(s.state().spent === 76, `counter should read 76 = 75 seeded + 1, got ${s.stateRaw()}`);
      s.cleanup();

      // The U2 shape itself: three metered calls then a cheap one, all in one session. At the 200
      // limit (D28) the third would take the total to 225: it is denied and counts nothing, and the
      // cheap one after it is counted on the 150.
      const t = session();
      const want = [75, 150, 150, 151];
      const cmds = [
        `curl -s "${V1}prism/creator-vet?handle=a"`,
        `curl -s "${V1}prism/creator-vet?handle=b"`,
        `curl -s "${V1}prism/creator-vet?handle=c"`,
        `curl -s "${V1}amazon/shop?q=d"`,
      ];
      cmds.forEach((c, i) => {
        const d = t.run(c);
        assertDecision(d, i === 2 ? "deny" : null, `call ${i + 1}`);
        if (i === 2) assert(d.message === mLimit({ spent: 150, worst: 75, limit: LIMIT, src: srcAuto(BALANCE), bf: d.bf }), `call 3: exactly M_LIMIT, read ${d.message}`, d);
        assert(
          t.state() && t.state().spent === want[i],
          `after call ${i + 1} the counter should read ${want[i]}, got ${t.stateRaw()} ` +
            `(pre-fix the metered calls wrote no state file at all and this read back as 1)`
        );
      });
      t.cleanup();

      // A fresh session starts near 1, not carrying another session's total.
      const fresh = run(`curl -s "${V1}amazon/shop?q=abc"`);
      assert(fresh.state && fresh.state.spent === 1, `a fresh session_id starts its own counter, read ${fresh.stateRaw}`, fresh);
    },
  },
  {
    id: "U2b-free-call-does-not-rewrite",
    desc: "U2 boundary: a 0cr credits/* call leaves an existing counter untouched (metered-only by design)",
    fn() {
      const s = session().seed({ spent: 75, marker: "UNTOUCHED" });
      s.run(`curl -s "${V1}credits/balance"`);
      assert(/UNTOUCHED/.test(s.stateRaw() || ""), `a free call must not rewrite the state file, got ${s.stateRaw()}`);
      s.run(`curl -s "${V1}amazon/shop?q=abc"`);
      assert(s.state().spent === 76, `the 1cr control must rewrite it to 76, got ${s.stateRaw()}`);
      s.cleanup();
    },
  },
  {
    id: "C3-web-crawl-limit",
    desc: "R1 done-test: web/crawl computes its 10,000 ceiling rather than the 1cr unit price (D28: past the limit, so denied with M_LIMIT naming 10000)",
    fn() {
      const r = run(`curl -X POST "${V1}web/crawl?limit=10000" -d '{}'`);
      assertDecision(r, "deny", "web/crawl is past the 200 limit");
      assert(r.message === mLimit({ spent: 0, worst: 10000, limit: LIMIT, src: srcAuto(BALANCE), bf: r.bf }), `exactly M_LIMIT naming 10000, not 1, read ${r.message}`, r);
      assert(quoted(r.state) === 0, `a deny counts nothing, read ${JSON.stringify(r.state)}`, r);
    },
  },
  {
    id: "C4-cap-step",
    desc: "D28, the hard limit (the cap is no longer a step): reaching the 200 limit exactly passes and is committed; one credit past it is denied with exactly M_LIMIT, naming the committed total, the worst case, the limit and the balance it came from",
    fn() {
      // Balance 800 -> the automatic cap min(500, 200) = 200. 198 + 1 stays under it: silent.
      const under = session().seed({ spent: 198 });
      assertDecision(under.run(`curl -s "${V1}amazon/shop?q=a"`), null, "199 is under the 200 limit");
      assert(under.state().spent === 199, `the silent call is committed, got ${under.stateRaw()}`);
      under.cleanup();
      // 199 + 1 reaches it exactly: a silent pass. 200 + 1 is past it: the deny, nothing committed.
      const s = session().seed({ spent: 199 });
      const r = s.run(`curl -s "${V1}amazon/shop?q=a"`);
      assertDecision(r, null, "reaching the limit exactly passes");
      assert(r.raw === "" && s.state().spent === 200, `reaching it is committed, got ${s.stateRaw()}`, r);
      const over = s.run(`curl -s "${V1}amazon/shop?q=b"`);
      assertDecision(over, "deny", "one credit past the limit is denied");
      assert(over.message === mLimit({ spent: 200, worst: 1, limit: 200, src: srcAuto(800), bf: over.bf }), `exactly M_LIMIT, read ${over.message}`, over);
      assert(s.state().spent === 200, `a deny commits nothing, got ${s.stateRaw()}`);
      s.cleanup();
    },
  },
];
