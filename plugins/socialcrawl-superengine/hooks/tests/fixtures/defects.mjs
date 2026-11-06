/*
 * DEFECT SET — one fixture per defect from the R1 independent close
 * ("R1 Independent Close - Checker Findings - 08.28.26.md", Part 2), each asserting the FIXED
 * behaviour and, where the defect had a control, the control as well.
 *
 * Every fixture reproduces the checker's own command shape. They are written to FAIL on the
 * pre-fix build at 0c7d980 — that is the point of committing them.
 */
import { run, session, visible, V1, HOST, TSCRIPT, quoted, mLimit, srcAuto, BALANCE, LIMIT, assert, assertDecision, assertCounted, assertNotPlain, assertNoMatch } from "../lib.mjs";

const NOLOCAL = { unsetEnv: ["GROQ_API_KEY"], env: { PATH: "" } };
const B = "https://" + HOST + "/v1/";

export default [
  {
    id: "D1-batch-scrape-no-nan",
    desc: "D1: a non-numeric `high` never produces NaN, never writes {\"spent\":null}, and never wipes the counter (D28a: the call is counted at 0, a stated LIMIT, and passes within the limit)",
    fn() {
      // (a) the single call: counted at 0 (no stated maximum), silently, no NaN anywhere.
      const r = run(`curl -X POST "${V1}web/batch-scrape" -d '{}'`);
      assertDecision(r, null, "an un-quotable priced call is counted at 0, not denied for it");
      assertNoMatch(r, /NaN/, "no NaN may reach any output");
      assert(r.raw === "" && r.state && r.state.spent === 0, `counted 0, read ${r.stateRaw}`, r);
      assert(r.stateRaw === null || !/null/.test(r.stateRaw), `state file must never contain null: ${r.stateRaw}`, r);

      // (b) the counter-wipe chain the checker captured: 200 -> 275 -> (batch) -> 350, under a
      // 1,000 session budget (contract §1) so every step is within the limit.
      const s = session().budget({ sessionBudget: 1000 });
      const sov = `curl -s "${V1}prism/share-of-voice?brands=a,b"`;
      assertDecision(s.run(sov), null, "step 1 is within the limit");
      assert(s.state().spent === 200, `step 1 should record 200, got ${s.stateRaw()}`);
      s.run(`curl -s "${V1}prism/creator-vet?handle=abc"`);
      assert(s.state().spent === 275, `step 2 should record 275, got ${s.stateRaw()}`);
      const batch = s.run(`curl -X POST "${V1}web/batch-scrape" -d '{}'`);
      assertNoMatch(batch, /NaN/, "the batch-scrape leg must not emit NaN");
      assert(s.state().spent === 275, `step 3 must PRESERVE 275, got ${s.stateRaw()} (this is the counter wipe)`);
      s.run(`curl -s "${V1}prism/creator-vet?handle=abc"`);
      assert(s.state().spent === 350, `step 4 should record 350, got ${s.stateRaw()} (75 means history was erased)`);
      s.cleanup();

      // (c) the chain it used to poison: the total must be >= the priced leg, never NaN. At the
      // 200 limit the 200 total reaches it exactly, so it passes and counts 200.
      const ch = run(`curl -X POST "${V1}web/batch-scrape" -d '{}' && curl -s "${V1}prism/share-of-voice?brands=a,b"`);
      assertNoMatch(ch, /NaN/, "a chain containing an un-quotable leg must not go NaN");
      assert(ch.raw === "" && ch.state.spent === 200, `the priced leg still carries the total, 200, read ${ch.stateRaw}`, ch);
    },
  },
  {
    id: "D2-batch-transcripts-real-price",
    desc: "D2: a BATCH transcript call counts the row's billable ceiling (300), not the generic 10cr band (D28: past the 200 limit, so M_LIMIT names 300)",
    fn() {
      const r = run(`curl -X POST "${V1}youtube/${TSCRIPT}s" -d '{"ids":["a"]}'`, NOLOCAL);
      assertDecision(r, "deny", "300 is past the 200 limit");
      assert(r.message === mLimit({ spent: 0, worst: 300, limit: LIMIT, src: srcAuto(BALANCE), bf: r.bf }), `exactly M_LIMIT naming the billable 300, read ${r.message}`, r);
      assert(quoted(r.state) === 0, `a deny counts nothing, read ${JSON.stringify(r.state)}`, r);

      // chained with a 1cr call the command total must read 301, not 11.
      const ch = run(`curl -X POST "${V1}youtube/${TSCRIPT}s" -d '{"ids":["a"]}' && curl -s "${V1}amazon/shop?q=a"`, NOLOCAL);
      assert(ch.message === mLimit({ spent: 0, worst: 301, limit: LIMIT, src: srcAuto(BALANCE), bf: ch.bf }), `chain total must be 301, read ${ch.message}`, ch);

      // CONTROL: include=transcript bolted onto another metered endpoint keeps that endpoint's own
      // 75: it is counted at 75, silently, never at a null unit.
      const bolt = run(`curl -s "${V1}prism/creator-vet?handle=a&include=full,${TSCRIPT}"`, NOLOCAL);
      assertCounted(bolt, 75, "a bolt-on transcript param counts the endpoint's 75");
    },
  },
  {
    id: "D3-truncated-url-not-cheap",
    desc: "D3: all four truncation shapes are not plain, so each is denied with M_NOTPLAIN and nothing is counted; its visible total is still the FALLBACK_BIG floor (50), never the 5cr unknown default",
    fn() {
      const shapes = [
        [`curl -s "${B}prism/creator-v""et?h=a"`, "split quoting"],
        [`curl -s "${B}prism/\ncreator-vet?h=a"`, "embedded line break"],
        [`BASE="${B}"; curl -s "\${BASE}prism/creator-vet?h=a"`, "${BASE} variable"],
        [`EP=prism/creator-vet; curl -s "${B}$EP"`, "$EP variable"],
      ];
      // R14a.2: none of the four is a plain curl, so each is denied (D28); the unreadable leg is
      // still seen at the FALLBACK_BIG floor, as the unattended log shows.
      for (const [cmd, label] of shapes) {
        assertNotPlain(run(cmd), `${label}: must fail SAFE`);
        const l = visible(cmd);
        assert(l && l.kind === "not-plain" && l.cmdWorst === 50, `${label}: the visible total is the 50 floor, not the 5cr default, read ${JSON.stringify(l)}`);
      }
      // CONTROL: the same URL written out in full still resolves to its real price.
      const ok = run(`curl -s "${B}prism/creator-vet?h=a"`);
      assertCounted(ok, 75, "a literal URL must still price at 75");
    },
  },
  {
    id: "D4-loops-degrade-to-ask",
    desc: "D4, re-pointed (R14a.2; D28): a loop around a billable URL is not a plain curl, so it is denied with M_NOTPLAIN and nothing is counted, and so is a loop over free credits/* calls",
    fn() {
      const loops = [
        [`for i in $(seq 1 100); do curl -s "${V1}youtube/video/${TSCRIPT}?id=$i"; done`, "for + seq, transcript"],
        [`for i in 1 2 3; do curl -s "${V1}prism/creator-vet?h=$i"; done`, "literal for-list, metered"],
        [`cat ids.txt | xargs -I{} curl -s "${V1}prism/creator-vet?h={}"`, "xargs fan-out"],
        [`while read u; do curl -s "${V1}prism/lookup?handle=$u"; done < h.txt`, "while-read over a file"],
        [`while read u\ndo\n curl -s "${V1}prism/lookup?handle=$u"\ndone < h.txt`, "while/do on separate lines"],
        [`for ((i=0;i<10;i++)); do curl -s "${V1}prism/creator-vet?h=$i"; done`, "C-style for"],
        [`until [ -f stop ]; do curl -s "${V1}prism/creator-vet?h=a"; done`, "until loop"],
        [`for i in 1 2; do curl -s "${V1}instagram/profile?handle=$i"; done`, "cheap call in a loop"],
      ];
      for (const [cmd, label] of loops) {
        const r = run(cmd, NOLOCAL);
        assertNotPlain(r, `${label}: a looped billable call is denied`);
        assertNoMatch(r, /\b(?:100|3|N) iterations\b/, `${label}: the guard must not claim to know the bound`);
      }
      // A benign loop with no SocialCrawl URL passes silently; a loop over free credits/* calls is
      // not a plain curl either, so it is denied (R14a.2: free calls go through the allow-list too).
      const benign = run(`for f in *.txt; do echo $f; done`);
      assert(benign.raw === "", "a loop with no SocialCrawl URL must pass silently", benign);
      assertNotPlain(run(`for i in 1 2 3; do curl -s "${V1}credits/balance"; done`), "a loop over free credits/* calls is denied");
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
    desc: "D5: no quantity param can discount a per-unit quote below the row's published ceiling (see sweep S2); D28: within the 200 limit it is counted, past it M_LIMIT names the full ceiling",
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
    desc: "D6: a percent-encoded transcript path is decoded before the gate; a `%` in the path is not plain (R14a.2), so each is denied with M_NOTPLAIN, and its visible total is the decoded transcript's per-unit price, not an unreadable floor",
    fn() {
      const enc = "transcr" + "%69" + "pt";           // decodes to the gated token
      const enc2 = "%74" + "ranscript";
      const cases = [
        [`curl -s "${V1}youtube/video/${enc}?id=abc"`, 3, "%69 inside the token"],
        [`curl -s "${V1}instagram/media/${enc2}?id=abc"`, 10, "%74 leading the token"],
        [`curl -s "${V1}youtube%2Fvideo%2F${enc}?id=abc"`, 3, "%2F slashes plus %69"],
      ];
      for (const [cmd, price, label] of cases) {
        assertNotPlain(run(cmd, NOLOCAL), `${label}: a % in the path is not plain`);
        const l = visible(cmd, NOLOCAL);
        assert(l && l.cmdWorst === price, `${label}: decoded to the transcript's ${price}, not the 50 floor, read ${JSON.stringify(l)}`);
      }
      // CONTROLS: a malformed escape must not break the decoder or the cost lookup.
      for (const bad of [`curl -s "${V1}prism/creator-vet?h=100%zz"`, `curl -s "${V1}prism/creator-vet?h=100%"`]) {
        assertCounted(run(bad), 75, "a malformed escape must still price at 75");
      }
      // The cheaper subtitles route is not a transcript: its own flat 1, not a transcript band.
      assertCounted(run(`curl -s "${V1}youtube/video/subtitles?id=abc"`, NOLOCAL), 1, "the cheaper subtitles route must not be gated");
    },
  },
];
