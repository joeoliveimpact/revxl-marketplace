/*
 * DEFECT SET — one fixture per defect from the R1 independent close
 * ("R1 Independent Close - Checker Findings - 08.28.26.md", Part 2), each asserting the FIXED
 * behaviour and, where the defect had a control, the control as well.
 *
 * Every fixture reproduces the checker's own command shape. They are written to FAIL on the
 * pre-fix build at 0c7d980 — that is the point of committing them.
 */
import { run, session, V1, HOST, TSCRIPT, quoted, assert, assertDecision, assertCounted, assertNotPlain, assertMatch, assertNoMatch } from "../lib.mjs";

const NOLOCAL = { unsetEnv: ["GROQ_API_KEY"], env: { PATH: "" } };
const B = "https://" + HOST + "/v1/";

export default [
  {
    id: "D1-batch-scrape-no-nan",
    desc: "D1: a non-numeric `high` never produces NaN, never writes {\"spent\":null}, and never wipes the counter",
    fn() {
      // (a) the single call: ask, per-unit price present, no NaN anywhere.
      const r = run(`curl -X POST "${V1}web/batch-scrape" -d '{}'`);
      assertDecision(r, "ask", "an un-quotable priced call must fail SAFE");
      assertNoMatch(r, /NaN/, "no NaN may reach the message");
      // R10: the entry is range null (a G7 sentence label), and the per-unit price reaches the
      // ask as the vendor's own label, verbatim.
      assertMatch(r, /1 credit per URL submitted/, "the per-unit price must still be stated");
      assertMatch(r, /NO computable ceiling/, "must say plainly that no ceiling exists");
      assert(r.stateRaw === null || !/null/.test(r.stateRaw), `state file must never contain null: ${r.stateRaw}`, r);

      // (b) the counter-wipe chain the checker captured: 200 -> 275 -> (batch) -> 350. The
      // 200cr step crosses the 200 cap step, so it asks and counts once it has run (R14a).
      const s = session();
      const sov = `curl -s "${V1}prism/share-of-voice?brands=a,b"`;
      assertDecision(s.run(sov), "ask", "step 1 crosses the cap step");
      s.post(sov);
      assert(s.state().spent === 200, `step 1 should record 200, got ${s.stateRaw()}`);
      s.run(`curl -s "${V1}prism/creator-vet?handle=abc"`);
      assert(s.state().spent === 275, `step 2 should record 275, got ${s.stateRaw()}`);
      const batch = s.run(`curl -X POST "${V1}web/batch-scrape" -d '{}'`);
      assertNoMatch(batch, /NaN/, "the batch-scrape leg must not emit NaN");
      assert(s.state().spent === 275, `step 3 must PRESERVE 275, got ${s.stateRaw()} (this is the counter wipe)`);
      s.run(`curl -s "${V1}prism/creator-vet?handle=abc"`);
      assert(s.state().spent === 350, `step 4 should record 350, got ${s.stateRaw()} (75 means history was erased)`);
      s.cleanup();

      // (c) the chain it used to poison: the total must be >= the priced leg, never NaN.
      const ch = run(`curl -X POST "${V1}web/batch-scrape" -d '{}' && curl -s "${V1}prism/share-of-voice?brands=a,b"`);
      assertNoMatch(ch, /NaN/, "a chain containing an un-quotable leg must not go NaN");
      assertMatch(ch, /Worst case for the whole command: ~200 credits/, "the priced leg still carries the total");
      assertMatch(ch, /excludes a call no ceiling can be computed for/, "the total must say what it excludes");
    },
  },
  {
    id: "D2-batch-transcripts-real-price",
    desc: "D2: the transcript gate states the BATCH row's billable ceiling (300), not the generic 10cr band",
    fn() {
      const r = run(`curl -X POST "${V1}youtube/${TSCRIPT}s" -d '{"ids":["a"]}'`, NOLOCAL);
      assertDecision(r, "ask", "a batch transcript call must still be gated");
      assertMatch(r, /TRANSCRIPT call/, "the gate must still fire");
      assertMatch(r, /Cheaper first/, "the redirect is mandatory policy");
      // R10: the per-unit price is the vendor's own label, quoted in the batch-row sentence.
      assertMatch(r, /BATCH transcript endpoint/, "the batch row's own sentence, not the generic band");
      assertMatch(r, /3 credits per successful transcript/, "the per-unit price is mandatory policy");
      assertMatch(r, /ceiling of 300 credits/, "the billable ceiling must be stated");
      assertMatch(r, /Worst case for this call: ~300 credits/, "the number in the ask must be the billable one");
      assert(quoted(r.state) === 300, `300 should be counted (pending the Post commit), read ${JSON.stringify(r.state)}`, r);

      // chained with a 1cr call the command total must read 301, not 11.
      const ch = run(`curl -X POST "${V1}youtube/${TSCRIPT}s" -d '{"ids":["a"]}' && curl -s "${V1}amazon/shop?q=a"`, NOLOCAL);
      assertMatch(ch, /Worst case for the whole command: ~301 credits/, "chain total must be 301");

      // CONTROL: include=transcript bolted onto another metered endpoint keeps the generic band.
      const bolt = run(`curl -s "${V1}prism/creator-vet?handle=a&include=full,${TSCRIPT}"`, NOLOCAL);
      assertDecision(bolt, "ask", "a bolt-on transcript param is still gated");
      assertNoMatch(bolt, /BATCH transcript endpoint/, "a bolt-on is not a batch transcript row");
      assertNoMatch(bolt, /per null/, "no null unit may reach the message");
    },
  },
  {
    id: "D3-truncated-url-not-cheap",
    desc: "D3: all four truncation shapes become a fail-safe ask with a floor, never the 5cr unknown default",
    fn() {
      const shapes = [
        [`curl -s "${B}prism/creator-v""et?h=a"`, "split quoting"],
        [`curl -s "${B}prism/\ncreator-vet?h=a"`, "embedded line break"],
        [`BASE="${B}"; curl -s "\${BASE}prism/creator-vet?h=a"`, "${BASE} variable"],
        [`EP=prism/creator-vet; curl -s "${B}$EP"`, "$EP variable"],
      ];
      // R14a.2: none of the four is a plain curl, so each takes the not-plain ask; the unreadable
      // leg is still counted at the FALLBACK_BIG floor and named as a floor.
      for (const [cmd, label] of shapes) {
        const r = run(cmd);
        assertNotPlain(r, 50, `${label}: must fail SAFE at the FALLBACK_BIG floor, not the 5cr default`);
        assertMatch(r, /endpoint unreadable — that figure is a FLOOR/, `${label}: must be named as unreadable`);
        assertNoMatch(r, /up to ~5 credits in one call/, `${label}: the cheap unknown default must be gone`);
      }
      // CONTROL: the same URL written out in full still resolves to its real price.
      const ok = run(`curl -s "${B}prism/creator-vet?h=a"`);
      assertCounted(ok, 75, "a literal URL must still price at 75");
      assertNoMatch(ok, /UNREADABLE endpoint/, "a resolvable path is not unreadable");
    },
  },
  {
    id: "D4-loops-degrade-to-ask",
    desc: "D4, re-pointed (R14a.2): a loop around a billable URL is not a plain curl, so it takes the not-plain ask at its visible one-call figure, and a loop over free credits/* calls asks too",
    fn() {
      const loops = [
        [`for i in $(seq 1 100); do curl -s "${V1}youtube/video/${TSCRIPT}?id=$i"; done`, 3, "for + seq, transcript"],
        [`for i in 1 2 3; do curl -s "${V1}prism/creator-vet?h=$i"; done`, 75, "literal for-list, metered"],
        [`cat ids.txt | xargs -I{} curl -s "${V1}prism/creator-vet?h={}"`, 75, "xargs fan-out"],
        [`while read u; do curl -s "${V1}prism/lookup?handle=$u"; done < h.txt`, 5, "while-read over a file"],
        [`while read u\ndo\n curl -s "${V1}prism/lookup?handle=$u"\ndone < h.txt`, 5, "while/do on separate lines"],
        [`for ((i=0;i<10;i++)); do curl -s "${V1}prism/creator-vet?h=$i"; done`, 75, "C-style for"],
        [`until [ -f stop ]; do curl -s "${V1}prism/creator-vet?h=a"; done`, 75, "until loop"],
        [`for i in 1 2; do curl -s "${V1}instagram/profile?handle=$i"; done`, 1, "cheap call in a loop"],
      ];
      for (const [cmd, want, label] of loops) {
        const r = run(cmd, NOLOCAL);
        assertNotPlain(r, want, `${label}: a looped billable call must ask`);
        assertMatch(r, /how many times, can't be read/, `${label}: the count must be declared unreadable`);
        assertNoMatch(r, /\b(?:100|3|N) iterations\b/, `${label}: the guard must not claim to know the bound`);
      }
      // A benign loop with no SocialCrawl URL passes silently; a loop over free credits/* calls is
      // not a plain curl either, so it asks (R14a.2: free calls go through the allow-list too).
      const benign = run(`for f in *.txt; do echo $f; done`);
      assert(benign.raw === "", "a loop with no SocialCrawl URL must pass silently", benign);
      assertNotPlain(run(`for i in 1 2 3; do curl -s "${V1}credits/balance"; done`), 0, "a loop over free credits/* calls asks");
      assertCounted(run(`curl -s "${V1}prism/creator-vet?handle=abc"`), 75, "a single plain call is counted silently");
      // Loop keywords inside a body or a path are not a loop: these are plain curls, counted silently.
      const prose = [
        [`curl -s -d '{"q":"what to do while waiting"}' "${V1}prism/creator-vet?h=a"`, "'do'+'while' in a body"],
        [`curl -s -d '{"q":"search for items in the list"}' "${V1}prism/creator-vet?h=a"`, "'for x in' in a body"],
        [`curl -s "${V1}prism/creator-vet?h=a" > /data/seq/out.json`, "'seq' as a path segment"],
      ];
      for (const [cmd, label] of prose) {
        assertCounted(run(cmd), 75, `${label}: prose is not a loop`);
      }
    },
  },
  {
    id: "D5-driver-not-limit",
    desc: "D5: no quantity param can discount a per-unit quote below the row's published ceiling (see sweep S2)",
    fn() {
      const cases = [
        [`curl -s "${V1}prism/comments?url=X&max=5000&limit=10"`, 200, "comments with max and limit"],
        [`curl -s "${V1}prism/comments?url=X&limit=1"`, 200, "comments with limit=1 (was 5, 40x under)"],
        [`curl -s "${V1}prism/comments?url=X&max=5000"`, 200, "CONTROL comments driven by max only"],
        [`curl -s "${V1}search/news?query=x&limit=1"`, 62, "search/news (was 1; 14 before the 09-23 label)"],
        [`curl -s "${V1}prism/ai-visibility?brand=x&limit=2"`, 1605, "ai-visibility (was 4)"],
        [`curl -X POST "${V1}prism/post-stats?per_page=2" -d '{}'`, 500, "post-stats (was 10)"],
        [`curl -X POST "${V1}youtube/videos?count=2" -d '{}'`, 100, "youtube/videos (was 10)"],
      ];
      for (const [cmd, want, label] of cases) {
        assertCounted(run(cmd), want, `${label}: must count ~${want}`);
      }
      // web/crawl's headline done-test still holds.
      assertCounted(
        run(`curl -X POST "${V1}web/crawl?limit=10000" -d '{}'`),
        10000,
        "web/crawl limit=10000 must still compute 10000"
      );
    },
  },
  {
    id: "D6-percent-encoded-transcript",
    desc: "D6: a percent-encoded transcript path is decoded before the gate, so the price and redirect survive",
    fn() {
      const enc = "transcr" + "%69" + "pt";           // decodes to the gated token
      const enc2 = "%74" + "ranscript";
      const cases = [
        [`curl -s "${V1}youtube/video/${enc}?id=abc"`, /bills 3 credits PER video/, "%69 inside the token"],
        [`curl -s "${V1}instagram/media/${enc2}?id=abc"`, /bills 10 credits PER media/, "%74 leading the token"],
        [`curl -s "${V1}youtube%2Fvideo%2F${enc}?id=abc"`, /bills 3 credits PER video/, "%2F slashes plus %69"],
      ];
      for (const [cmd, priceRe, label] of cases) {
        const r = run(cmd, NOLOCAL);
        assertDecision(r, "ask", `${label}: must be gated`);
        // R14a.2: a `%` in the path is not plain, so the not-plain ask carries the transcript sentence.
        assertMatch(r, /NOT A PLAIN CURL/, `${label}: not a plain curl`);
        assertMatch(r, /TRANSCRIPT call/, `${label}: the gate must fire`);
        assertMatch(r, priceRe, `${label}: the per-unit price is mandatory`);
        assertMatch(r, /Cheaper first/, `${label}: the redirect is mandatory`);
        assertNoMatch(r, /^SocialCrawl PAID call/, `${label}: must not fall through to a plain PAID ask`);
      }
      // CONTROLS: a malformed escape must not break the decoder or the cost lookup.
      for (const bad of [`curl -s "${V1}prism/creator-vet?h=100%zz"`, `curl -s "${V1}prism/creator-vet?h=100%"`]) {
        assertCounted(run(bad), 75, "a malformed escape must still price at 75");
      }
      assertNoMatch(
        run(`curl -s "${V1}youtube/video/subtitles?id=abc"`, NOLOCAL),
        /TRANSCRIPT call/,
        "the cheaper subtitles route must not be gated"
      );
    },
  },
];
