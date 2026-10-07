/*
 * REGRESSION SET — the shapes that must not change while the guard is edited.
 *
 * This is the checker's substitute set of nine from
 * "R1 Independent Close - Checker Findings - 08.28.26.md" criterion 5, made permanent so the
 * next builder does not have to reconstruct it, plus the two remaining load-bearing hardcodes.
 * Each fixture asserts the BEHAVIOUR the checker recorded rather than byte-comparing against
 * another build — a committed expectation is what makes it re-runnable at any HEAD.
 */
import { mkdtempSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  run,
  V1,
  HOST,
  TSCRIPT,
  GUARD,
  quoted,
  assert,
  assertDecision,
  assertCounted,
  assertNotPlain,
  assertMatch,
  assertNoMatch,
} from "../lib.mjs";

// No API key is needed: the guard never calls the API. Transcript fixtures strip PATH and
// unset GROQ_API_KEY so the optional local-route sentence cannot vary with the machine.
const NOLOCAL = { unsetEnv: ["GROQ_API_KEY"], env: { PATH: "" } };

/** A copy of the guard in a directory with no costs.json beside it. */
function guardWithoutCosts() {
  const dir = mkdtempSync(join(tmpdir(), "sc-guard-nocosts-"));
  const alt = join(dir, "credit-guard.mjs");
  copyFileSync(GUARD, alt);
  return alt;
}

export default [
  {
    id: "R1-nonsocialcrawl",
    desc: "a command that never touches socialcrawl.dev is untouched (fast path)",
    fn() {
      const r = run(`curl -s "https://example.com/v1/prism/creator-vet?handle=abc"`);
      assert(r.raw === "", "expected zero bytes on stdout for a non-SocialCrawl command", r);
      assert(r.exit === 0, "guard must exit 0 (fail-open by contract)", r);
      assert(!r.stateWritten, "no session state may be written for a non-SocialCrawl command", r);
    },
  },
  {
    id: "R2-credits-free",
    desc: "credits/* is a free account-meta call: silent pass, no state write (hardcode 1)",
    fn() {
      for (const p of ["credits/balance", "credits/transactions"]) {
        const r = run(`curl -s "${V1}${p}"`);
        assert(r.raw === "", `${p} must pass silently`, r);
        assert(!r.stateWritten, `${p} must not write the session counter`, r);
      }
    },
  },
  {
    id: "R3-flat-50",
    desc: "a single flat 50cr endpoint under the session cap is silent and counts ~50 (R14a: the flat >= 5 ask is retired)",
    fn() {
      const r = run(`curl -s "${V1}prism/leads?query=coaches"`);
      assertCounted(r, 50, "a 50cr flat call under the cap");
    },
  },
  {
    id: "R4-flat-1",
    desc: "a single 1cr endpoint emits nothing and counts 1 — no decision, so the normal permission flow applies (R14a: no inform line)",
    fn() {
      const r = run(`curl -s "${V1}amazon/shop?q=widgets"`);
      assertCounted(r, 1, "a 1cr call must not carry a permissionDecision");
    },
  },
  {
    id: "R5-single-transcript",
    desc: "a single transcript call asks, with the per-unit price and the cheaper route, and never denies",
    fn() {
      const r = run(`curl -s "${V1}youtube/video/${TSCRIPT}?id=abc"`, NOLOCAL);
      assertDecision(r, "ask", "transcript policy is ASK-with-redirect, never deny and never silent");
      assertMatch(r, /bills 3 credits PER video — 100 of them = 300 credits/, "mandatory per-unit price");
      assertMatch(r, /Cheaper first: GET youtube\/video\/subtitles/, "mandatory cheaper route");
      assertNoMatch(r, /I see /, "no local-route claim when no key and no binary are detected");
    },
  },
  {
    id: "R6-unpriced-cohorts",
    desc: "an unpriced endpoint asks and refuses to invent a number",
    fn() {
      const r = run(`curl -s "${V1}cohorts?segment=abc"`);
      assertDecision(r, "ask", "unpriced must ask");
      assertMatch(r, /UNPRICED endpoint/, "unpriced wording");
      assertMatch(r, /do not guess a number/, "must not invent a price");
    },
  },
  {
    id: "R7-shellvar-failsafe",
    desc: "host in a variable => not a plain curl => the not-plain ask, nothing visible to count (R14a.2 folds the shell-variable ask into it)",
    fn() {
      const r = run(`H=${HOST}; curl -s "https://$H/v1/prism/creator-vet?handle=abc"`);
      assertNotPlain(r, 0, "no readable /v1/ URL must fail SAFE");
      assert(!r.stateWritten, "the fail-safe path must not write the counter", r);
    },
  },
  {
    id: "R8-deep-scan-floor",
    desc: "deep_scan floor 15 holds where nothing is measured, and a measured 6 beats it (hardcode 3)",
    fn() {
      assertCounted(run(`curl -s "${V1}amazon/shop?q=a"`), 1, "control without deep_scan is the 1cr base");
      const ds = run(`curl -s "${V1}amazon/shop?q=a&deep_scan=true"`);
      assertCounted(ds, 15, "unmeasured deep_scan holds the conservative floor of 15");
      // The pin is named in the ask; balance unknown makes this call ask (R14a).
      const measured = run(`curl -s "${V1}tiktok/comment?url=a&deep_scan=true"`, { balance: null });
      assertMatch(measured, /pins this call at 6 credits/, "a measured 6 beats the guessed 15");
      assert(quoted(measured.state) === 6, `the measured 6 is what is counted, read ${measured.stateRaw}`, measured);
    },
  },
  {
    id: "R9-single-metered",
    desc: "a single metered call counts its command worst case, 75, in the session counter — silently under the cap (R14a: the metered-always ask is retired)",
    fn() {
      const r = run(`curl -s "${V1}prism/creator-vet?handle=abc"`);
      assertCounted(r, 75, "the worst case, not the headline number");
    },
  },
  {
    id: "R10-hardcode-prism-lookup",
    desc: "prism/lookup prices at its own label's worst case, 5 (named label override, Joe 09.24.26: 1 for most lookups, 5 for Amazon and LinkedIn) — never the vendor's 0 or the old hardcoded 1",
    fn() {
      const r = run(`curl -s "${V1}prism/lookup?handle=abc"`);
      // R14a: counted at the label's worst case, 5 — neither the vendor's 0 nor the old 1.
      assertCounted(r, 5, "the label's worst case, 5, is counted");
    },
  },
  {
    id: "R11-hardcode-fallback-big",
    desc: "with costs.json absent the FALLBACK_BIG list still gates the big guns (hardcode 4)",
    fn() {
      const alt = guardWithoutCosts();
      assertCounted(
        run(`curl -s "${V1}prism/creator-vet?handle=abc"`, { guard: alt }),
        50,
        "FALLBACK_BIG must still count 50 with no cost map"
      );
      assertCounted(
        run(`curl -s "${V1}amazon/shop?q=a"`, { guard: alt }),
        1,
        "an endpoint not in FALLBACK_BIG defaults cheap with no cost map"
      );
    },
  },
];
