/*
 * SWEEP SET — the defects the round-2 hostile sweep found at 51bdd7f
 * ("R1 Re-Check at 51bdd7f - Checker Findings - 08.29.26.md", Sweep section).
 *
 *   S2  driver-as-param quantity discount under-quoted by up to 10,000x   (regression of 3cd79c4)
 *   S3  repeat shapes the REPEAT patterns did not match                   (residue of b64f007)
 *   S4  dot-segment paths bypassed the credits/* and prism/lookup hardcodes (pre-existing)
 *   S5  vendor-documented conditional surcharges missing from the quote     (pre-existing)
 *   S6  REPEAT fired on prose and in-URL occurrences of xargs/seq          (residue of 51bdd7f)
 *
 * Every fixture reproduces the checker's own command shape. S4 and S5 split into a defect
 * fixture and a control fixture on purpose, so the per-build expectation is readable per
 * fixture rather than averaged inside one.
 *
 * MEASURED PER-BUILD EXPECTATIONS (suite copied onto a `git archive 51bdd7f` extraction,
 * guard blob re-verified 3f56ff07 after the copy; 25/31, exit 1):
 *   S2-driver-param-no-discount        FAIL at 51bdd7f   PASS at the fix HEAD
 *   S4-dot-segments-normalised         FAIL at 51bdd7f   PASS at the fix HEAD
 *   S4-controls-unchanged              PASS on BOTH  (pre-existing behaviour, unchanged)
 *   S5-conditional-surcharges          FAIL at 51bdd7f   PASS at the fix HEAD
 *   S5-controls-unchanged              PASS on BOTH  (pre-existing behaviour, unchanged)
 *   (R14a, Joe 09.28.26: the manual surcharge overlay is deleted — the 09-23 labels already
 *   include every surcharge — so S5 now asserts each row counts its label's max, nothing on top.)
 *   S6-repeat-command-position-only    FAIL at 51bdd7f   PASS at the fix HEAD
 *   S3-repeat-literal-bash-shapes      FAIL at 51bdd7f   PASS at the fix HEAD
 *
 * ROUND 4 adds the two defects the round-3 sweep found at b1783c9
 * ("R1 Re-Check at b1783c9 - Checker Findings - 08.29.26.md", Sweep section).
 *
 *   SW1  a BACKSLASH dot segment slipped the credits/* hardcode and the transcript gate
 *   SW2  `bash -c '<loop>'` hid the loop from every REPEAT arm (regression of 6922c13)
 *
 * MEASURED PER-BUILD EXPECTATIONS for those (suite copied onto a `git archive b1783c9`
 * extraction, guard blob re-verified after the copy):
 *   SW1-backslash-dot-segments         FAIL at b1783c9   PASS at the fix HEAD
 *   SW1-backslash-controls             PASS on BOTH  (pre-existing behaviour, unchanged)
 *   SW2-shell-invoker-argument-is-code FAIL at b1783c9   PASS at the fix HEAD
 *   SW2-repeat-negatives-still-silent  PASS on BOTH  (the S6 negatives must not come back)
 *
 * ROUND 4 also closes the three COVERAGE GAPS the round-3 checker's mutation testing exposed
 * (its C5 note: "no SINGLE mutation kills the S6 fixture ... and M8 passes 31/31, i.e. the
 * `do` requirement has no covering fixture"). The G-fixtures below are NOT defect fixtures —
 * every build in this workstream is silent on all of them, so they PASS at b1783c9 as well.
 * Their falsifiability is proved by MUTATION, not by an older build, exactly as accepted for
 * P1 in round 3: each one is the sole fixture killed by deleting the mechanism it pins.
 *   G1-loop-needs-do                   dies under "HAS_DO = true"                 (M8)
 *   G2-mask-alone-is-load-bearing      dies under "CODE = cmd" (no masking)       (M3)
 *   G3-command-position-is-load-bearing  dies under CMD_POS = "\b"                (M7)
 *
 * R14a.2 (Joe 09.28.26): the repeat readers (LOOPY, CURL_GLOB, BRACE_RANGE, WRAPPER, RECURSIVE,
 * the CODE mask, CMD_POS) are deleted; the allow-list replaces them. Every shape below that is not
 * a plain curl now takes the one NOT A PLAIN CURL ask at its visible figure, and the plain ones
 * are counted silently. The G-fixtures keep their shapes, re-pointed to that decision; the
 * mechanisms their mutations pinned no longer exist.
 */
import { run, V1, TSCRIPT, quoted, assert, assertDecision, assertCounted, assertNotPlain, assertMatch, assertNoMatch } from "../lib.mjs";

const NOLOCAL = { unsetEnv: ["GROQ_API_KEY"], env: { PATH: "" } };
// A literal backslash, never spelled inline in a URL so the shapes below stay readable.
const BS = String.fromCharCode(92);

export default [
  {
    id: "S2-driver-param-no-discount",
    desc: "S2: no quantity-shaped query param discounts a metered call below its label ceiling (the class the retired `driver` field once opened)",
    fn() {
      // The checker's measured quoted-vs-billable shapes. Each param was once a bare word in a
      // _perUnit row's `driver` field (a field R10 retired with that block), and NONE of them
      // is a real billing query param on that endpoint per the vendor openapi.
      const cases = [
        [`curl -X POST "${V1}web/crawl?page=1&limit=10000" -d '{"url":"https://site.test","limit":10000}'`, 10000, "web/crawl ?page=1 (quoted 1, billable 10000)"],
        [`curl -X POST "${V1}web/crawl?limit=10000&page=2" -d '{}'`, 10000, "web/crawl ?page=2 (quoted 2)"],
        [`curl -s "${V1}prism/ai-visibility?brand=x&probe=1"`, 1605, "ai-visibility ?probe=1 (quoted 2, 802x under)"],
        [`curl -s "${V1}search/news?query=x&leg=1"`, 62, "search/news ?leg=1 (quoted 1; 14 before the 09-23 label)"],
        [`curl -X POST "${V1}prism/post-stats?url=1" -d '{}'`, 500, "post-stats ?url=1 (quoted 5)"],
      ];
      // web/sessions was the sixth shape (?ttl_seconds=0, quoted 5 against 20). Its 09-23 label
      // is a sentence (G7), so it has no ceiling to discount: it must take the no-ceiling ask.
      const sess = run(`curl -X POST "${V1}web/sessions?ttl_seconds=0" -d '{}'`);
      assertDecision(sess, "ask", "web/sessions ?ttl_seconds=0: a can't-count call must ask");
      assertMatch(sess, /NO computable ceiling/, "web/sessions ?ttl_seconds=0: no ceiling, said plainly");
      for (const [cmd, want, label] of cases) {
        assertCounted(run(cmd), want, `${label}: must count the ~${want} ceiling`);
      }
      // The message must not carry the deleted formula, which contradicts a ceiling quote on
      // every limit below the cap (the U1 self-contradiction class).
      assertNoMatch(
        run(`curl -X POST "${V1}web/crawl?limit=10" -d '{}'`),
        /Quote = worst x limit/,
        "the generated note's quoting formula describes a discount this guard no longer applies"
      );
      // D5 stays fixed in the same breath: no discount via `limit` OR `max`.
      for (const [cmd, label] of [
        [`curl -s "${V1}prism/comments?url=X&limit=1"`, "comments ?limit=1"],
        [`curl -s "${V1}prism/comments?url=X&max=1"`, "comments ?max=1"],
      ]) {
        assertCounted(run(cmd), 200, `${label}: still the 200 ceiling (defect D5)`);
      }
    },
  },
  {
    id: "S4-dot-segments-normalised",
    desc: "S4: `..` and `.` are resolved before the credits/* and prism/lookup hardcodes, so a dot-segment path cannot buy a free or 1cr quote",
    fn() {
      // curl 8.18.0 normalises dot segments client-side and sends the resolved path, so the
      // guard has to price what curl will actually request. Measured by the checker.
      const cases = [
        [`curl -s "${V1}credits/../prism/creator-vet?h=a"`, 75, /Quote the ~75 credit worst case/, "credits/.. hid a 75cr call behind the free-call hardcode (guard emitted NOTHING)"],
        [`curl -s "${V1}credits/./../prism/creator-vet?h=a"`, 75, /Quote the ~75 credit worst case/, "credits/./.. variant"],
        [`curl -s "${V1}credits/../prism/share-of-voice?brands=a,b"`, 200, /Quote the ~200 credit worst case/, "credits/.. hid a 200cr call"],
        [`curl -X POST "${V1}credits/../web/crawl?limit=10000" -d '{}'`, 10000, /Quote the ~10000 credit worst case/, "credits/.. hid a 10,000cr call"],
        [`curl -s "${V1}prism/lookup/../../prism/creator-vet?h=a"`, 75, /Quote the ~75 credit worst case/, "prism/lookup/../.. quoted 1cr informational for a 75cr call"],
      ];
      // R14a.2: a dot segment in the path is not a plain curl, so each takes the not-plain ask,
      // and the figure it parks is still the resolved endpoint's price.
      for (const [cmd, want, , label] of cases) {
        assertNotPlain(run(cmd), want, `${label}: must price the resolved endpoint`);
      }
      // A path that walks OUT of /v1/ cannot be priced at all -> the fail-safe ask, never silence.
      const escaped = run(`curl -s "${V1}../credits/balance"`);
      assertNotPlain(escaped, 50, "a path that escapes /v1/ must fail SAFE");
      assertMatch(escaped, /endpoint unreadable/, "an escaped path is unreadable, not free");
    },
  },
  {
    id: "S4-controls-unchanged",
    desc: "S4 controls: plain credits/* stays silent-free and plain prism/lookup quotes its label's worst case, 5 (R10.1: named label override)",
    fn() {
      for (const p of ["credits/balance", "credits/transactions"]) {
        const r = run(`curl -s "${V1}${p}"`);
        assert(r.raw === "", `${p} must still pass silently`, r);
        assert(!r.stateWritten, `${p} must still write no session counter`, r);
      }
      assertCounted(run(`curl -s "${V1}prism/lookup?handle=abc"`), 5, "plain prism/lookup must count its label's worst case, 5");
      // A dot in a path SEGMENT is not a dot segment: nothing here may be rewritten.
      assertCounted(
        run(`curl -s "${V1}prism/creator-vet?h=a.b.c"`),
        75,
        "dots inside a query value must not disturb the path"
      );
    },
  },
  {
    id: "S5-conditional-surcharges",
    desc: "S5, re-pointed (Joe 09.28.26: the manual surcharge overlay is deleted): each of its five former rows counts its 09-23 label's max, which already includes the surcharge, and no message claims a charge on top",
    fn() {
      const cases = [
        [`curl -s "${V1}tiktok/post/${TSCRIPT}?url=X&use_ai_as_fallback=true"`, 10, "tiktok transcript AI fallback: 10 (openapi: included in the endpoint's 10 credits); the overlay said 20"],
        [`curl -s "${V1}prism/crisis-radar?brand=x&confirm=true"`, 45, "crisis-radar confirm: the label's full 45; the overlay said 75"],
        [`curl -s "${V1}prism/creator-vet?handle=a&include=cross_platform"`, 75, "creator-vet cross_platform: the label's 75; the overlay said 100"],
        [`curl -s "${V1}prism/video-intel?url=x&include=${TSCRIPT}"`, 15, "video-intel transcript leg: the label's 15; the overlay said 25"],
        [`curl -s "${V1}youtube/search/advanced?q=x&includeExtras=true"`, 11, "youtube/search/advanced extras: the label's 11; the overlay said 16"],
      ];
      for (const [cmd, want, label] of cases) {
        const r = run(cmd, NOLOCAL);
        assert(quoted(r.state) === want, `${label}: should count ${want}, read ${JSON.stringify(r.state)}`, r);
        assertNoMatch(r, /on top of that endpoint's own price/, `${label}: no surcharge may be claimed on top`);
      }
      // The transcript ask keeps its per-unit price and the cheaper route, and claims no +10.
      const tk = run(`curl -s "${V1}tiktok/post/${TSCRIPT}?url=X&use_ai_as_fallback=true"`, NOLOCAL);
      assertDecision(tk, "ask", "the transcript gate still asks");
      assertMatch(tk, /bills 10 credits PER post/, "the per-unit price is non-negotiable ask content");
      assertMatch(tk, /Cheaper first/, "the redirect is non-negotiable ask content");
      assertNoMatch(tk, /\+10 credits/, "the retired +10 surcharge must not be stated");
    },
  },
  {
    id: "S5-controls-unchanged",
    desc: "S5 controls: the same endpoints WITHOUT the surcharge param keep their round-2 figures (these pass on BOTH builds)",
    fn() {
      const cases = [
        [`curl -s "${V1}tiktok/post/${TSCRIPT}?url=X"`, 10, "tiktok transcript, no fallback param"],
        [`curl -s "${V1}prism/crisis-radar?brand=x"`, 45, "crisis-radar, no confirm"],
        [`curl -s "${V1}prism/creator-vet?handle=a"`, 75, "creator-vet, no include"],
        [`curl -s "${V1}prism/video-intel?url=x"`, 15, "video-intel, no include"],
        [`curl -s "${V1}youtube/search/advanced?q=x"`, 11, "youtube/search/advanced, no extras (the 09-23 label ceiling)"],
      ];
      for (const [cmd, want, label] of cases) {
        const r = run(cmd, NOLOCAL);
        assert(
          quoted(r.state) === want,
          `${label}: counter should record ${want}, read ${JSON.stringify(r.state)}`,
          r
        );
        assertNoMatch(r, /on top of that endpoint's own price/, `${label}: no surcharge may be claimed`);
      }
      // A different value on the same param must not trigger the surcharge.
      const other = run(`curl -s "${V1}prism/creator-vet?handle=a&include=basic"`, NOLOCAL);
      assert(quoted(other.state) === 75, `include=basic must stay 75, read ${JSON.stringify(other.state)}`, other);
      // D2's bolt-on control keeps its round-2 figure: include=full,transcript on creator-vet
      // is a gated bolt-on, not the cross_platform leg.
      const bolt = run(`curl -s "${V1}prism/creator-vet?handle=a&include=full,${TSCRIPT}"`, NOLOCAL);
      assert(quoted(bolt.state) === 75, `the D2 bolt-on control must stay 75, read ${JSON.stringify(bolt.state)}`, bolt);
    },
  },
  {
    id: "S6-repeat-command-position-only",
    desc: "S6, re-pointed (R14a.2): the words xargs/seq inside a URL or a body of a plain curl are counted silently; a trailing comment is not plain and asks; every real fan-out takes the not-plain ask",
    fn() {
      // The checker's five former false positives. Each is a single call that does not repeat.
      const benign = [
        [`curl -s "${V1}web/search?q=xargs"`, "the word inside the URL's own query string"],
        [`curl -s "${V1}search/news?query=xargs+tutorial"`, "in-URL, with a + separator"],
        [`curl -s -d '{"q":"how do I use xargs"}' "${V1}prism/creator-vet?h=a"`, "inside a single-quoted request body"],
        [`curl -s -d '{"q":"analyze the seq 2 protein"}' "${V1}prism/creator-vet?h=a"`, "seq as prose in a body"],
      ];
      for (const [cmd, label] of benign) {
        const r = run(cmd, NOLOCAL);
        assertDecision(r, null, `${label}: a plain curl under the cap is silent`);
        assert(r.raw === "" && quoted(r.state) > 0, `${label}: counted, read ${JSON.stringify(r.state)}`, r);
      }
      // A trailing comment is not a full-line comment, so the command is not plain (R14a.2).
      assertNotPlain(run(`curl -s "${V1}prism/creator-vet?h=a"  # later: pipe to xargs`, NOLOCAL), 75, "a trailing comment");
      const cheap = run(`curl -s "${V1}amazon/shop?q=xargs"`, NOLOCAL);
      assertDecision(cheap, null, "an in-URL 'xargs' must not promote a 1cr call to an ask");
      // TRUE POSITIVES: every fan-out is not a plain curl, so it asks. The last entry is the 9th
      // loop shape the round-2 findings list ("until/do newline"), which the D4 fixture's
      // eight shapes do not cover — committed here so all nine are re-runnable.
      const loops = [
        [`cat ids.txt | xargs -I{} curl -s "${V1}prism/creator-vet?h={}"`, "xargs after a pipe"],
        [`yes | head -100 | xargs -n1 curl -s "${V1}prism/creator-vet?h=a"`, "xargs at the end of a pipeline"],
        [`xargs -I{} curl -s "${V1}prism/creator-vet?h={}" < ids.txt`, "xargs at the start of the command"],
        [`seq 1 100 | xargs -n1 -I{} curl -s "${V1}prism/creator-vet?h={}"`, "seq at the start of a pipeline"],
        [`for i in $(seq 1 100); do curl -s "${V1}youtube/video/${TSCRIPT}?id=$i"; done`, "seq inside a command substitution"],
        [`until [ -f stop ]
do
 curl -s "${V1}prism/creator-vet?h=a"
done`, "until/do on separate lines"],
      ];
      for (const [cmd, label] of loops) {
        const r = run(cmd, NOLOCAL);
        assertDecision(r, "ask", `${label}: a real fan-out must ask`);
        assertMatch(r, /NOT A PLAIN CURL/, `${label}: a real fan-out is not a plain curl`);
      }
    },
  },
  {
    id: "S3-repeat-literal-bash-shapes",
    desc: "S3, re-pointed (R14a.2): curl URL globbing, bash brace expansion, watch, parallel and a recursive function are not plain curls, so each takes the not-plain ask; so do -g and a repeat around a free call",
    fn() {
      const shapes = [
        [`curl -s "${V1}youtube/video/${TSCRIPT}?id=[1-3]"`, 3, "curl URL globbing, numeric range (3 HTTP requests, measured)"],
        [`curl -s "${V1}prism/creator-vet?h=[a-c]"`, 75, "curl URL globbing, alpha range"],
        [`curl -s "${V1}prism/creator-vet?h={alpha,beta}"`, 75, "curl URL globbing, brace list"],
        [`curl -s "${V1}prism/creator-vet?h="{1..3}`, 75, "bash brace expansion adjacent to the URL (3 requests, measured)"],
        [`watch -n1 curl -s "${V1}prism/creator-vet?h=a"`, 75, "watch, unbounded"],
        [`parallel curl -s "${V1}prism/creator-vet?h={}" ::: a b c`, 75, "parallel fan-out"],
        [`f() { curl -s "${V1}prism/creator-vet?h=a"; f; }; f`, 75, "recursive function, unbounded"],
        // -g/--globoff is not a plain flag (Joe 09.28.26), and a bash brace list outside the
        // quotes expands before curl sees -g at all (checker X8(b)).
        [`curl -g -s "${V1}prism/creator-vet?h=[a-c]"`, 75, "-g globoff"],
        [`curl --globoff -s "${V1}prism/creator-vet?h=[a-c]"`, 75, "--globoff"],
        [`curl -sg "${V1}prism/creator-vet?h=[a-c]"`, 75, "-g bundled into a short-flag group"],
        [`mkdir -p out{1..3}; curl -s "${V1}prism/creator-vet?h=a"`, 75, "a brace range on another command"],
        [`f() { curl -s "${V1}prism/creator-vet?h=a"; }; f`, 75, "define-then-call-once"],
        // A repeat around a FREE call asks too: free calls go through the allow-list (R14a.2).
        [`watch -n1 curl -s "${V1}credits/balance"`, 0, "a repeat around free credits/* calls"],
      ];
      for (const [cmd, want, label] of shapes) {
        const r = run(cmd, NOLOCAL);
        assertNotPlain(r, want, `${label}: must ask`);
        assertNoMatch(r, /\b(?:3|100) iterations\b/, `${label}: bounds are deliberately not parsed`);
      }
      // The words in prose or in a URL of a plain curl are not commands: counted silently.
      for (const [cmd, label] of [
        [`curl -s "${V1}web/search?q=watch+later"`, "'watch' inside the URL"],
        [`curl -s -d '{"q":"run these in parallel"}' "${V1}prism/creator-vet?h=a"`, "'parallel' inside a body"],
      ]) {
        assertDecision(run(cmd, NOLOCAL), null, `${label}: prose is not a command`);
      }
    },
  },
  {
    id: "SW1-backslash-dot-segments",
    desc: "SW1: a backslash is a path separator to curl, so `credits/..\\prism/...` must price the resolved endpoint instead of taking the free credits/* hardcode",
    fn() {
      // The checker WIRE-MEASURED curl 8.18.0 sending GET /v1/prism/creator-vet for the first
      // shape. At b1783c9 the guard emitted 0 bytes for every one of these — no decision, no
      // session counter — while 50-10,000 credits billed.
      const cases = [
        [`curl -s "${V1}credits/..${BS}prism/creator-vet"`, 75, /Quote the ~75 credit worst case/, "hid a 75cr call behind the free-call hardcode"],
        [`curl -s "${V1}credits/..${BS}prism/leads"`, 50, /up to ~50 credits in one call/, "hid a 50cr call"],
        [`curl -s "${V1}credits/..${BS}prism/share-of-voice"`, 200, /Quote the ~200 credit worst case/, "hid a 200cr call"],
        [`curl -X POST "${V1}credits/..${BS}web/crawl" -d '{}'`, 10000, /Quote the ~10000 credit worst case/, "hid a 10,000cr ceiling"],
        [`curl -s "${V1}credits/..${BS}prism/crisis-radar"`, 45, /Quote the ~45 credit worst case/, "hid a 45cr call"],
        [`curl -s "${V1}prism/lookup/..${BS}..${BS}prism/creator-vet"`, 75, /Quote the ~75 credit worst case/, "quoted 1cr informational for a 75cr call"],
        // DELIBERATE OVER-QUOTE, not a mirror of the client. The checker measured that curl
        // only rewrites the backslash when the URL carries NO query string, so this one goes
        // on the wire literally and probably 404s. It is normalised anyway: reading the
        // truncated `credits/..` is the silent free pass this defect is made of, and silence
        // on an unknown path is never the safe direction.
        [`curl -s "${V1}credits/..${BS}prism/share-of-voice?brands=a,b"`, 200, /Quote the ~200 credit worst case/, "backslash WITH a query string must not fall silent either"],
      ];
      // R14a.2: a backslash in the URL is not a plain curl, so each takes the not-plain ask; the
      // figure it parks is the resolved endpoint's price, never the free credits/* hardcode.
      for (const [cmd, want, , label] of cases) {
        assertNotPlain(run(cmd, NOLOCAL), want, `${label}: must price the resolved endpoint`);
      }
      // The worst shape of all: the transcript gate is the per-unit-price control that
      // replaced the hard deny on 08.27.26 (findings 08.27.26b), and a backslash walked
      // straight past it in silence.
      const t = run(`curl -s "${V1}credits/..${BS}youtube/video/${TSCRIPT}"`, NOLOCAL);
      assertDecision(t, "ask", "a backslash must not bypass the transcript gate");
      assertMatch(t, /NOT A PLAIN CURL/, "a backslash in the URL is not a plain curl (R14a.2)");
      assertMatch(t, /bills 3 credits PER video/, "the per-unit price is non-negotiable ask content");
      assertMatch(t, /Cheaper first/, "the cheaper route is non-negotiable ask content");
      assert(quoted(t.state) === 3, `transcript backslash shape should count 3, read ${JSON.stringify(t.state)}`, t);
      // MECHANISM, not just the numbers: curl turns `\` into `/`, so every one of these must
      // behave EXACTLY as its forward-slash twin already does (S4, verified round 3). Pinning
      // the equivalence keeps the two paths from ever drifting apart again.
      const twins = [
        `curl -s "${V1}credits/..@prism/creator-vet"`,
        `curl -s "${V1}credits/..@prism/share-of-voice"`,
        `curl -X POST "${V1}credits/..@web/crawl" -d '{}'`,
        `curl -s "${V1}credits/..@youtube/video/${TSCRIPT}"`,
        `curl -s "${V1}prism/lookup/..@..@prism/creator-vet"`,
        `curl -s "${V1}credits/..@prism/share-of-voice?brands=a,b"`,
        `curl -s "${V1}prism/creator-vet/..@..@credits/balance"`,
      ];
      for (const tpl of twins) {
        const bs = run(tpl.split("@").join(BS), NOLOCAL);
        const fwd = run(tpl.split("@").join("/"), NOLOCAL);
        assert(
          bs.raw === fwd.raw,
          `backslash and forward-slash forms of ${tpl} must decide identically — ` +
            `backslash said ${JSON.stringify(bs.raw).slice(0, 300)}, forward slash said ${JSON.stringify(fwd.raw).slice(0, 300)}`
        );
      }
    },
  },
  {
    id: "SW1-backslash-controls",
    desc: "SW1 controls: a backslash that is NOT a path separator is left alone — the `\\?` shell escape and a backslash inside a query value still price at 75, now behind the not-plain ask (R14a.2: a backslash or an unquoted URL is not a plain curl)",
    fn() {
      // `curl .../prism/creator-vet\?h=a` is the ordinary shell escape of `?` on an unquoted
      // URL: bash removes the backslash and curl never sees it. Rewriting it to `/` would
      // turn a correct 75cr quote into a trailing-slash miss, so a path-FINAL backslash must
      // stay untouched.
      for (const [cmd, label] of [
        [`curl -s ${V1}prism/creator-vet${BS}?h=a`, "escaped ? on an unquoted URL"],
        [`curl -s "${V1}prism/creator-vet${BS}?h=a"`, "escaped ? inside double quotes"],
        [`curl -s ${V1}prism/creator-vet?h=a${BS}&x=b`, "escaped & on an unquoted URL"],
        [`curl -s "${V1}prism/creator-vet?h=a${BS}b"`, "a backslash inside a query VALUE, not the path"],
      ]) {
        assertNotPlain(run(cmd, NOLOCAL), 75, `${label}: must still price at 75`);
      }
      // The S4 hardcode controls are untouched by the backslash work.
      for (const p of ["credits/balance", "credits/transactions"]) {
        const r = run(`curl -s "${V1}${p}"`, NOLOCAL);
        assert(r.raw === "", `${p} must still pass silently`, r);
        assert(!r.stateWritten, `${p} must still write no session counter`, r);
      }
      assertCounted(run(`curl -s "${V1}prism/lookup?handle=abc"`, NOLOCAL), 5, "plain prism/lookup must count its label's worst case, 5 (R10.1)");
    },
  },
  {
    id: "SW2-shell-invoker-argument-is-code",
    desc: "SW2, re-pointed (R14a.2): a loop wrapped in bash/sh/zsh/dash -c or eval is not a plain curl, so it takes the not-plain ask, bare or wrapped, and keeps the transcript price",
    fn() {
      const CV = `${V1}prism/creator-vet?h=a`;
      // FLAGSHIP: the D4 defect command with nothing changed but a wrapper. At b1783c9 this
      // quoted 3 credits against 300 credits of billing and never said the call repeats.
      const flag = run(
        `bash -c 'for i in $(seq 1 100); do curl -s "${V1}youtube/video/${TSCRIPT}?id=$i"; done'`,
        NOLOCAL
      );
      assertNotPlain(flag, 3, "the wrapped D4 command must ask");
      assertMatch(flag, /how many times, can't be read/, "the count must be declared unreadable");
      assertMatch(flag, /bills 3 credits PER video/, "the wrapper must not cost the gate its per-unit price");
      // The checker's 9-shape matrix: 9/9 detected bare and 0/9 wrapped at b1783c9.
      const nine = [
        [`for i in $(seq 1 100); do curl -s "${V1}youtube/video/${TSCRIPT}?id=$i"; done`, "for + seq"],
        [`for i in 1 2 3; do curl -s "${V1}prism/creator-vet?h=$i"; done`, "literal for-list"],
        [`cat ids.txt | xargs -I{} curl -s "${V1}prism/creator-vet?h={}"`, "xargs"],
        [`while read h; do curl -s "${V1}prism/creator-vet?h=$h"; done < ids.txt`, "while-read"],
        [`while true\ndo\n curl -s "${CV}"\ndone`, "while/do on separate lines"],
        [`for ((i=0;i<100;i++)); do curl -s "${CV}"; done`, "C-style for"],
        [`until [ -f stop ]; do curl -s "${CV}"; done`, "until"],
        [`until [ -f stop ]\ndo\n curl -s "${CV}"\ndone`, "until/do newline"],
        [`for i in 1 2 3; do curl -s "${V1}instagram/profile?handle=$i"; done`, "a cheap 1cr call in a loop"],
      ];
      for (const [inner, label] of nine) {
        const bare = run(inner, NOLOCAL);
        assertDecision(bare, "ask", `${label}: must ask unwrapped (control)`);
        assertMatch(bare, /NOT A PLAIN CURL/, `${label}: must be not plain unwrapped (control)`);
        const wrapped = run(`bash -c '${inner}'`, NOLOCAL);
        assertDecision(wrapped, "ask", `${label} wrapped in bash -c: must ask`);
        assertMatch(wrapped, /NOT A PLAIN CURL/, `${label} wrapped in bash -c: the wrapper must not hide it`);
        assert(quoted(bare.state) === quoted(wrapped.state), `${label}: bare and wrapped park the same figure, read ${JSON.stringify(bare.state)} vs ${JSON.stringify(wrapped.state)}`);
      }
      // The other repeat shapes and the recursion shape, all through the wrapper.
      const LOOP = `for i in 1 2 3; do curl -s "${CV}"; done`;
      const others = [
        [`bash -c 'curl -s "${V1}prism/creator-vet?h=[a-c]"'`, "curl URL globbing"],
        [`bash -c 'curl -s "${V1}prism/creator-vet?h="{1..3}'`, "bash brace expansion"],
        [`bash -c 'watch -n1 curl -s "${CV}"'`, "watch"],
        [`bash -c 'parallel curl -s "${V1}prism/creator-vet?h={}" ::: a b c'`, "parallel"],
        [`bash -c 'f() { curl -s "${CV}"; f; }; f'`, "recursive function"],
        [`bash -c 'curl -g -s "${V1}prism/creator-vet?h=[a-c]"'`, "a -g inside the -c argument"],
      ];
      for (const [cmd, label] of others) {
        assertNotPlain(run(cmd, NOLOCAL), 75, `${label} wrapped in bash -c: must still ask`);
      }
      // Every shell-invoker spelling, and nested or malformed quoting: all not plain.
      const invokers = [
        [`sh -c '${LOOP}'`, "sh -c"],
        [`zsh -c '${LOOP}'`, "zsh -c"],
        [`dash -c '${LOOP}'`, "dash -c"],
        [`bash -lc '${LOOP}'`, "bash -lc (login flag bundle)"],
        [`bash -ic '${LOOP}'`, "bash -ic (interactive flag bundle)"],
        [`bash --norc -c '${LOOP}'`, "a long flag before -c"],
        [`/bin/bash -c '${LOOP}'`, "a path-qualified shell"],
        [`env FOO=1 bash -c '${LOOP}'`, "env prefix"],
        [`sudo bash -c '${LOOP}'`, "sudo prefix"],
        [`eval 'for i in 1 2 3; do curl -s ${CV}; done'`, "eval"],
        [`bash -c "for i in 1 2 3; do curl -s '${CV}'; done"`, "a double-quoted -c argument"],
        [`bash -c 'sh -c "for i in 1 2 3; do curl -s ${CV}; done"'`, "a nested shell invoker"],
        [`bash -c "for i in 1 2 3; do curl -s \\"${CV}\\"; done"`, "escaped double quotes inside double"],
        [`bash -c 'for i in 1 2 3; do curl -s "${CV}; done'`, "an unterminated quote INSIDE the argument"],
        [`bash -c 'for i in 1 2 3; do curl -s "${CV}"; done`, "an unterminated wrapper quote"],
      ];
      for (const [cmd, label] of invokers) {
        assertNotPlain(run(cmd, NOLOCAL), 75, `${label}: must ask`);
      }
    },
  },
  {
    id: "SW2-repeat-negatives-still-silent",
    desc: "SW2 negatives, re-pointed (R14a.2): the former false positives that are plain curls are counted silently; the ones with a trailing comment or a wrapper take the not-plain ask; a wrapper never changes the figure",
    fn() {
      const CV = `${V1}prism/creator-vet?h=a`;
      for (const [cmd, label] of [
        [`curl -s "${V1}web/search?q=xargs"`, "the word inside the URL's own query string"],
        [`curl -s "${V1}search/news?query=xargs+tutorial"`, "in-URL, with a + separator"],
        [`curl -s -d '{"q":"how do I use xargs"}' "${CV}"`, "inside a single-quoted request body"],
        [`curl -s -d '{"q":"analyze the seq 2 protein"}' "${CV}"`, "seq as prose in a body"],
        [`curl -s -d '{"q":"how do I use bash -c for i in 1 2 3; do x; done"}' "${CV}"`, "a loop described inside a JSON body"],
      ]) {
        assertDecision(run(cmd, NOLOCAL), null, `${label}: a plain curl under the cap is silent`);
      }
      for (const [cmd, label] of [
        [`curl -s "${CV}"  # later: pipe to xargs`, "a trailing comment"],
        [`curl -s "${CV}"  # try bash -c 'for i in 1 2; do x; done'`, "a loop described inside a trailing comment"],
        [`bash -c 'curl -s "${CV}"'`, "bash -c around a single call"],
        [`bash -c 'curl -s "${CV}" # for i in 1 2; do x; done'`, "a comment inside a bash -c argument"],
        [`mesh -c 'for i in 1 2 3; do echo $i; done'; curl -s "${CV}"`, "a -c flag on something that is not a shell"],
      ]) {
        assertNotPlain(run(cmd, NOLOCAL), 75, `${label}: not a plain curl`);
      }
      // The wrapper must not cost the coster anything either: same figure, wrapped or bare.
      const bare = run(`curl -s "${CV}"`, NOLOCAL);
      const wrapped = run(`bash -c 'curl -s "${CV}"'`, NOLOCAL);
      assert(
        bare.state && wrapped.state && bare.state.spent === quoted(wrapped.state),
        `a bash -c wrapper must not change the quoted figure — bare ${JSON.stringify(bare.state)}, wrapped ${JSON.stringify(wrapped.state)}`
      );
    },
  },
  {
    id: "G1-loop-needs-do",
    desc: "COVERAGE, re-pointed (R14a.2): loop keywords as prose after an unquoted-URL curl, and real loops, are all not plain, so each asks at the one-call figure",
    fn() {
      const CV = `${V1}prism/creator-vet?h=a`;
      for (const [cmd, label] of [
        [`curl -s ${CV}; echo rerun for each in the roster`, "'for each in' as prose, no do"],
        [`curl -s ${CV}; echo check back while the crawl finishes`, "'while' as prose, no do"],
        [`curl -s ${CV}; echo retry until it returns 200`, "'until' as prose, no do"],
        [`curl -s ${CV}; echo for ((i=0;i<3;i++))`, "a C-style for header with no body"],
        [`for i in 1 2 3; do curl -s "${CV}"; done`, "for/in with do"],
        [`while true; do curl -s "${CV}"; done`, "while with do"],
        [`until [ -f stop ]; do curl -s "${CV}"; done`, "until with do"],
      ]) {
        assertNotPlain(run(cmd, NOLOCAL), 75, `${label}: not a plain curl`);
      }
    },
  },
  {
    id: "G2-mask-alone-is-load-bearing",
    desc: "COVERAGE, re-pointed (R14a.2): a pipeline quoted inside a -d body is data, so the curl stays plain and silent; the same pipeline for real, or a trailing comment, is not plain and asks",
    fn() {
      const CVQ = `"${V1}prism/creator-vet?h=a"`;
      for (const [cmd, label] of [
        [`curl -s -d '{"q":"is cat ids.txt | xargs -n1 curl faster?"}' ${CVQ}`, "a pipeline quoted inside a JSON body"],
        [`curl -s -d '{"q":"try: seq 1 100 | xargs -n1 echo"}' ${CVQ}`, "seq and xargs quoted inside a JSON body"],
        [`curl -s -d '{"q":"compare: parallel curl vs watch curl"}' ${CVQ}`, "wrapper names quoted inside a body"],
      ]) {
        assertDecision(run(cmd, NOLOCAL), null, `${label}: quoted text is data, not syntax`);
      }
      assertNotPlain(run(`curl -s ${CVQ} # next step: ids.txt | xargs -n1 curl`, NOLOCAL), 75, "a pipeline written in a trailing comment");
      assertNotPlain(run(`cat ids.txt | xargs -n1 curl -s ${CVQ}`, NOLOCAL), 75, "the same pipeline unquoted is a real fan-out");
    },
  },
  {
    id: "G3-command-position-is-load-bearing",
    desc: "COVERAGE, re-pointed (R14a.2): an unquoted URL is not a plain curl, whatever word its query holds, so each asks; so do xargs and watch in command position",
    fn() {
      for (const [cmd, want, label] of [
        [`curl -s ${V1}web/search?q=xargs`, null, "an unquoted URL whose query IS the word xargs"],
        [`curl -s ${V1}web/search?q=seq`, null, "an unquoted URL querying seq"],
        [`curl -s ${V1}web/search?q=watch`, null, "an unquoted URL querying watch"],
        [`curl -s ${V1}web/search?q=parallel`, null, "an unquoted URL querying parallel"],
        [`curl -s ${V1}prism/creator-vet?h=a -o xargs.json`, 75, "an output FILENAME called xargs.json"],
        [`xargs -I{} curl -s "${V1}prism/creator-vet?h={}" < ids.txt`, 75, "xargs at the start"],
        [`watch -n1 curl -s "${V1}prism/creator-vet?h=a"`, 75, "watch at the start"],
      ]) {
        const r = run(cmd, NOLOCAL);
        assertDecision(r, "ask", `${label}: not a plain curl, so it asks`);
        assertMatch(r, /NOT A PLAIN CURL/, `${label}: the not-plain ask`);
        if (want !== null) assert(quoted(r.state) === want, `${label}: parks ${want}, read ${JSON.stringify(r.state)}`, r);
      }
    },
  },
];
