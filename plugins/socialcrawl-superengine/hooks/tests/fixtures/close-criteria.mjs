/*
 * R1 CLOSE CRITERIA — U1 and U2, the two defects the 08.27.26 build fixed.
 *
 * These are here so a later edit cannot silently undo them: U1 (a chain quoted at its first
 * leg instead of its total) and U2 (expensive calls never reaching the session counter) are
 * both under-quote classes, and both were invisible until a fixture named the number.
 */
import { run, session, V1, quoted, assert, assertDecision, assertMatch, assertNoMatch } from "../lib.mjs";

export default [
  {
    id: "U1-three-call-chain-280",
    desc: "U1: a 3-call chain quotes ~280 TOTAL and names all three endpoints (pre-fix it quoted the first leg, ~5)",
    fn() {
      const cmd =
        `curl -s "${V1}web/scrape?url=https://x.test" && ` +
        `curl -s "${V1}prism/creator-vet?handle=abc" && ` +
        `curl -s "${V1}prism/share-of-voice?brands=a,b"`;
      const r = run(cmd);
      assertDecision(r, "ask", "a 280cr chain must ask");
      assertMatch(r, /This command makes 3 SocialCrawl calls/, "must count the calls");
      assertMatch(r, /\/v1\/web\/scrape up to ~5cr/, "leg 1 in the roster");
      assertMatch(r, /\/v1\/prism\/creator-vet up to ~75cr/, "leg 2 in the roster");
      assertMatch(r, /\/v1\/prism\/share-of-voice up to ~200cr/, "leg 3 in the roster");
      assertMatch(r, /Worst case for the whole command: ~280 credits/, "the command total");
      // R14a: the number the user approves is the cap-step ask's worst case for the command.
      assertMatch(r, /this command's worst case is ~280 credits/, "the number the user approves");
      // The pre-fix contradiction: a per-leg ceiling presented as the thing to quote.
      assertNoMatch(r, /Quote the 5 ceiling/, "the pre-fix phrasing must stay gone");
      assertNoMatch(r, /worst case is ~5 credits/, "the chain must never be quoted at its first leg");
      // R14a: an ask parks the command's worst case as pending; the Post run commits it.
      assert(quoted(r.state) === 280 && r.state.spent === 0, `280 should be pending, not committed, read ${JSON.stringify(r.state)}`, r);
    },
  },
  {
    id: "U2-session-accumulation",
    desc: "U2: the session counter accumulates across calls, including the expensive ones",
    fn() {
      // The checker's headline: seeded 75 + a 1cr call reads 76.
      const s = session().seed({ spent: 75 });
      const r = s.run(`curl -s "${V1}amazon/shop?q=abc"`);
      assertDecision(r, null, "a 1cr call under the cap is silent (R14a: no inform line)");
      assert(s.state().spent === 76, `counter should read 76 = 75 seeded + 1, got ${s.stateRaw()}`);
      s.cleanup();

      // The U2 shape itself: three metered calls then a cheap one, all in one session. At a
      // 200 cap the third crosses a step: it asks, and it counts once it has run (R14a).
      const t = session();
      const want = [75, 150, 225, 226];
      const cmds = [
        `curl -s "${V1}prism/creator-vet?handle=a"`,
        `curl -s "${V1}prism/creator-vet?handle=b"`,
        `curl -s "${V1}prism/creator-vet?handle=c"`,
        `curl -s "${V1}amazon/shop?q=d"`,
      ];
      cmds.forEach((c, i) => {
        if (t.run(c).decision === "ask") t.post(c);
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
    desc: "R1 done-test: web/crawl computes its 10,000 ceiling rather than the 1cr unit price",
    fn() {
      const r = run(`curl -X POST "${V1}web/crawl?limit=10000" -d '{}'`);
      assertDecision(r, "ask", "web/crawl must ask");
      assertMatch(r, /this command's worst case is ~10000 credits/, "10,000 not 1");
      assert(quoted(r.state) === 10000, `10000 should be pending, read ${JSON.stringify(r.state)}`, r);
    },
  },
  {
    id: "C4-cap-step",
    desc: "the session cap asks once when a command crosses its next step, naming the committed total, the cap, the worst case and the balance",
    fn() {
      // Balance 800 -> cap min(500, 200) = 200. 198 + 1 stays under the step: silent.
      const under = session().seed({ spent: 198 });
      assertDecision(under.run(`curl -s "${V1}amazon/shop?q=a"`), null, "199 is under the 200 step");
      assert(under.state().spent === 199, `the silent call is committed, got ${under.stateRaw()}`);
      under.cleanup();
      // 199 + 1 reaches it: one ask with all four figures, and nothing committed yet.
      const s = session().seed({ spent: 199 });
      const r = s.run(`curl -s "${V1}amazon/shop?q=a"`);
      assertDecision(r, "ask", "crossing the cap step must ask");
      assertMatch(r, /worst case is ~1 credits/, "names this command's worst case");
      assertMatch(r, /~199 credits are committed/, "names the committed total");
      assertMatch(r, /The cap is 200 credits/, "names the cap");
      assertMatch(r, /800-credit balance/, "names the balance");
      assert(s.state().spent === 199, `an ask commits nothing, got ${s.stateRaw()}`);
      s.cleanup();
    },
  },
];
