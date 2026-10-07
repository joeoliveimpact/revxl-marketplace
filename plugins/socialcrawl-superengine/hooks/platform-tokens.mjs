/*
 * Platform tokens — the ONE source of platform-name matching. research-suggest.mjs (the trigger
 * hook) and jev.mjs (named platforms always survive the cut, R13a) both import it, so the
 * derivation, the aliases and the stop-list exist once. Moved verbatim out of research-suggest.mjs;
 * the only addition is `platformOf`, which maps every matchable token back to its platform.
 *
 * A pure module: no stdin, no exit, no network. costs.json is read only when derivePlatforms()
 * runs, relative to this file.
 */
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));

/*
 * HAND-MAINTAINED — the only hand-maintained list in this file. Left side: what a human types.
 * Right side: a canonical platform name that MUST exist in costs.json. Verified mechanically by
 * --self-check; any alias whose target is not canonical is dropped at load time (fail-open) and
 * reported as `unknownAliases` by --self-check, which then exits 1. An alias whose target is
 * STOP-LISTED is dropped the same way and reported as `stopListedAliases`, also exit 1.
 *
 * Aliases that are merely the underscore form written with a space ("google news" ->
 * google_news, "app store" -> app_store) are NOT listed here — those are derived automatically
 * from costs.json below. Only genuinely human shorthand lives here.
 */
export const HUMAN_ALIASES = {
  ig: "instagram",
  insta: "instagram",
  yt: "youtube",
  fb: "facebook",
  tt: "tiktok",
  hn: "hackernews",
  "hacker news": "hackernews",
  snap: "snapchat",
  "truth social": "truthsocial",
  "tiktok shop": "tiktokshop",
  "trip advisor": "tripadvisor",
  "link tree": "linktree",
};

/*
 * HAND-MAINTAINED — the second and last hand-maintained list in this file (Joe's call, R3
 * round 2: silence beats noise). These names are still DERIVED and still appear in
 * `canonical`; they are only withheld from the TRIGGER set. A filter applied after
 * derivation, never an edit to what gets derived.
 *
 * Eleven are ordinary English words a research prompt uses in a non-platform sense ("look
 * into target market fit", "research web performance issues", "look into threads in this
 * discussion" — all three measured firing before this list existed; `finance`, `jobs` and
 * `on_page` arrived with the 09-23 catalogue, P28; `economy` with the 10-06 one, Q-g). Three
 * are API function groups rather than
 * platforms at all. `tavily` and `perplexity` deliberately STAY in the trigger set: real
 * research sources, and neither is a common English word.
 *
 * A stop-list is itself a hand-maintained enumeration — the defect class that has blocked
 * this workstream four times — so it does not ship unverified. Every entry must EXIST in the
 * derived canonical set; if a vendor rename ever retires one, --self-check reports it under
 * `staleStopList` and exits 1. Stale loudly, never quietly.
 *
 * BACK DOOR — CLOSED: a HUMAN_ALIASES entry whose target is stop-listed used to route around
 * this filter, silently. The alias loop now drops it (the `!STOP_TOKENS.has(target)` half of
 * its gate) and --self-check reports it under `stopListedAliases` and exits 1. No such alias
 * exists today, so this closes a LATENT hole, not a live defect.
 *
 * RECONCILED: this used to derive 50 canonical names while the plugin's prose claimed 48, and
 * which two the vendor's 48 excluded was not determinable from the plugin or the vendor's site.
 * The prose now states what costs.json can PROVE — "645 endpoints across 68 platform
 * namespaces" — and tools/socialcrawl/check_canon_counts.mjs derives both from that same file
 * and fails if any sentence disagrees. This stop-list is still NOT part of that reconciliation:
 * it withholds fourteen names from the TRIGGER set and changes no count. 68 minus fourteen is
 * not a count.
 */
export const STOP_TOKENS = new Set([
  // ordinary English words
  "target", "threads", "web", "search", "kick", "pillar", "komi",
  // ordinary English words the 09-23 catalogue added as platform names (R10, P28)
  "finance", "jobs", "on_page",
  // an ordinary English word the 10-06 catalogue added as a platform name (R18-6, Q-g)
  "economy",
  // API function groups, not platforms
  "prism", "utility", "content_analysis",
]);

// ---------------------------------------------------------------------------------------
// Derivation
// ---------------------------------------------------------------------------------------

/**
 * Canonical platform names = the first path segment of every non-underscore key in costs.json.
 * Keys are verb-qualified ("GET instagram/profile"), so the verb is stripped first.
 * Returns { canonical, tokens, platformOf }: `canonical` is the derived truth used to validate
 * aliases; `tokens` is what we actually match prompts against (canonical + spelling variants +
 * aliases); `platformOf` maps each token to the canonical platform it names.
 * costs.json missing or unreadable -> all three empty. Platform co-occurrence then simply never
 * fires; the wake-word and shape triggers still work. Degrade, never throw.
 */
export function derivePlatforms() {
  const canonical = new Set();
  const tokens = new Set();
  const platformOf = new Map();
  const add = (token, platform) => {
    tokens.add(token);
    platformOf.set(token, platform);
  };
  const unknownAliases = [];
  // An alias whose TARGET is stop-listed re-admits that platform through the back door (see the
  // alias loop below). Derived here from the two hand-maintained lists ALONE, so it does not
  // depend on costs.json and is reported identically on the two degraded returns below — a
  // hand-list defect must never hide behind an unreadable catalog.
  const stopListedAliases = Object.entries(HUMAN_ALIASES)
    .filter(([, target]) => STOP_TOKENS.has(target))
    .map(([alias, target]) => `${alias} -> ${target}`);
  let costs = null;
  try {
    costs = JSON.parse(readFileSync(join(HERE, "costs.json"), "utf8"));
  } catch {
    return { canonical, tokens, platformOf, unknownAliases: Object.keys(HUMAN_ALIASES), staleStopList: [...STOP_TOKENS], stopListedAliases };
  }
  if (!costs || typeof costs !== "object") {
    return { canonical, tokens, platformOf, unknownAliases: Object.keys(HUMAN_ALIASES), staleStopList: [...STOP_TOKENS], stopListedAliases };
  }
  for (const key of Object.keys(costs)) {
    if (key.startsWith("_")) continue; // _platforms / _gated / _conditional / _unpriced
    const path = key.includes(" ") ? key.slice(key.indexOf(" ") + 1) : key;
    const seg = String(path).split("/")[0].trim().toLowerCase();
    // 3+ chars keeps a two-letter segment from becoming a trigger; the character class keeps
    // path templates like {job_id} out.
    if (!/^[a-z0-9][a-z0-9_]{2,}$/.test(seg)) continue;
    canonical.add(seg);
    // Derived, canonical, and reported — but withheld from the trigger set, along with every
    // spelling variant it would otherwise have generated.
    if (STOP_TOKENS.has(seg)) continue;
    add(seg, seg);
    if (seg.includes("_")) {
      // "google_news" is how the API spells it; "google news" is how a human does.
      add(seg.replace(/_/g, " "), seg);
      add(seg.replace(/_/g, "-"), seg);
      add(seg.replace(/_/g, ""), seg);
    }
  }
  for (const [alias, target] of Object.entries(HUMAN_ALIASES)) {
    // The gate is two-part on purpose. `canonical.has` drops a DANGLING alias; `!STOP_TOKENS.has`
    // closes the BACK DOOR — a stop-listed segment is skipped above and never reaches `tokens`,
    // so admitting its alias here would put it back in the trigger set and route around the
    // stop-list filter entirely, with no error and no log.
    if (canonical.has(target) && !STOP_TOKENS.has(target)) add(alias, target);
    else if (STOP_TOKENS.has(target)) continue;        // dropped; reported as stopListedAliases
    else unknownAliases.push(`${alias} -> ${target}`); // dangling: dropped, never matched
  }
  // Mechanical check on the hand-maintained stop-list: an entry naming nothing real is stale.
  const staleStopList = [...STOP_TOKENS].filter((t) => !canonical.has(t));
  return { canonical, tokens, platformOf, unknownAliases, staleStopList, stopListedAliases };
}

// ---------------------------------------------------------------------------------------
// Matching
// ---------------------------------------------------------------------------------------

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Whole-token match, optionally @-prefixed in the prompt. "web" must not match "webinar". */
export function hasToken(haystack, token) {
  try {
    return new RegExp(`(?:^|[^a-z0-9_])@?${escapeRe(token)}(?![a-z0-9_])`, "i").test(haystack);
  } catch {
    return false;
  }
}

export function firstToken(haystack, tokens) {
  for (const t of tokens) if (hasToken(haystack, t)) return t;
  return null;
}
