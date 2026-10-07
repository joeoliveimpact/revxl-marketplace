#!/usr/bin/env node
/*
 * SocialCrawl research suggester — UserPromptSubmit hook.
 *
 * Purpose: when a prompt looks like social research, point the session at the FRONT DOOR
 * (the `research-plays` skill) instead of letting it hand-roll API calls. It SUGGESTS ONLY:
 * it runs no query, calls no API, and cannot spend a credit. Its output surface is
 * `hookSpecificOutput.additionalContext` — a string appended to the user's prompt — plus, only
 * when it carries the unattended notice (below), the same notice as a `systemMessage` the user
 * sees. It never emits a decision, never blocks, never rewrites the prompt.
 *
 * FAIL-OPEN by contract: this fires on EVERY user prompt, not just Bash ones. Any error,
 * unexpected shape, missing file, or unreadable roster -> exit 0 with no suggestion (at most the
 * unattended notice), and the prompt proceeds untouched. Same I/O shape as
 * hooks/credit-guard.mjs (JSON on stdin, JSON-or-nothing on stdout, exit 0 always).
 *
 * THREE TRIGGER CLASSES, ALL CLOSED SETS (Joe's design, settled 08.26.26):
 *   1. Wake-word. The word "socialcrawl" used as a verb ("socialcrawl this handle on ig").
 *      Always fires. Zero false positives by construction — nobody says it by accident.
 *   2. Intent phrase x co-occurrence. "research" / "look into" / "find out about" fires ONLY
 *      when the SAME prompt also carries a URL, an @handle, a roster entry, or a platform name.
 *   3. Shape triggers. URL shape, @handle shape, and a roster-entry hit.
 *
 * A BARE INTENT PHRASE WITH NO CO-OCCURRENCE STAYS SILENT. "research flights to Tokyo" must
 * produce nothing. This is inverted from an earlier draft, and silence is the more important
 * half of the behaviour — a hook that fires on every "research" is a hook the user turns off.
 *
 * PLATFORM NAMES ARE DERIVED, NEVER INVENTED. The canonical platform set is read out of
 * costs.json (gen_refs.py output — read, never hand-edited) as the first path segment of every
 * endpoint key. Only the HUMAN aliases are hand-maintained, and every one of them must
 * resolve to a canonical name that actually exists in costs.json AND is not stop-listed. The
 * derivation, the aliases and the stop-list live in platform-tokens.mjs, shared with jev.mjs. It
 * is imported statically and ships beside this file: a missing module is a broken install (the
 * hook then exits non-zero before any catch), not one of the runtime states above.
 * `node research-suggest.mjs --self-check` proves that mechanically and exits 1 if any alias
 * dangles or targets a stop-listed name — a hand-maintained
 * enumeration that nothing verifies is the defect class that has blocked this workstream four
 * times.
 *
 * ROSTER. `~/.claude/revxl/entities.jsonl` (the plugin's own convention — precedent is the
 * teach-mode switch file at `~/.claude/revxl/teach-mode`). R4 writes it; this hook only READS
 * it. A missing or empty roster is a NORMAL state, not an error. `SC_REVXL_HOME` overrides the
 * directory so the fixture suite can seed a roster without touching a real one.
 *
 * JEV LINE (R13a). Every note ends `jev: on` with the absolute ask-file path `<revxl>/jev-ask.json`
 * (the hook creates `<revxl>`), or `jev: off`. On means an OpenRouter key is PRESENT: the
 * OPENROUTER_API_KEY env var is set, or ~/.config/openrouter/api_key has a non-zero size. The
 * value is never read (P15); jev.mjs does its own key check and exits 3 on a bad one.
 */
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { HUMAN_ALIASES, STOP_TOKENS, derivePlatforms, firstToken } from "./platform-tokens.mjs";

/** The front door. Named once so a fixture can assert the suggestion actually points at it. */
const FRONT_DOOR = "research-plays";

// ---------------------------------------------------------------------------------------
// Trigger vocabulary
// ---------------------------------------------------------------------------------------

// Class 1. Wake-word. "social crawl" / "social-crawl" spelled apart is just as deliberate.
const WAKE_RE = /\bsocial[\s-]?crawl\b/i;

// Class 2. Intent phrases — the closed set from the plan, plus their ordinary inflections.
const INTENT_RE =
  /\bresearch(?:ing|ed|es)?\b|\blook(?:ing|ed|s)?\s+into\b|\bfind(?:ing|s)?\s+out\s+about\b/i;

// Class 3a. URL shape: a scheme URL, a www. host, or a host-with-path. A bare "example.com"
// with no path and no www is deliberately NOT a URL here — "joe@example.com" must not fire.
const URL_RE =
  /(?:\bhttps?:\/\/[^\s<>"')]+)|(?:\bwww\.[a-z0-9][a-z0-9-]*\.[a-z]{2,})|(?:\b[a-z0-9][a-z0-9-]*\.[a-z]{2,}\/[^\s<>"')]*)/i;

// Class 3b. @handle shape. The leading boundary is load-bearing: without it every email
// address in every prompt reads as a handle ("joe@example.com" -> "@example").
const HANDLE_RE = /(?:^|[\s(\[{"'“‘,;:>])@([a-z0-9][a-z0-9._-]{1,29})/i;

/** Fields a roster line may carry a matchable name in. `platform` is deliberately excluded:
 *  matching on it would make every roster entry drag its whole platform in as a trigger. */
const ROSTER_FIELDS = ["handle", "username", "name", "entity", "alias", "brand"];

// ---------------------------------------------------------------------------------------
// Roster
// ---------------------------------------------------------------------------------------

function revxlDir() {
  const override = process.env.SC_REVXL_HOME;
  return override && String(override).trim() ? String(override) : join(homedir(), ".claude", "revxl");
}

function rosterPath() {
  return join(revxlDir(), "entities.jsonl");
}

/**
 * Roster tokens, or []. Absent file, empty file, unparsable line, wrong shape — all normal,
 * all silently skipped. One bad line never costs the good ones. Capped at 2000 lines so a
 * runaway roster cannot slow down every prompt in the session.
 */
function loadRoster() {
  const out = [];
  try {
    const p = rosterPath();
    if (!existsSync(p)) return out;
    const lines = readFileSync(p, "utf8").split(/\r?\n/).slice(0, 2000);
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let obj;
      try {
        obj = JSON.parse(trimmed);
      } catch {
        continue; // a half-written line from R4 is not an error here
      }
      const values = [];
      if (typeof obj === "string") values.push(obj);
      else if (obj && typeof obj === "object" && !Array.isArray(obj)) {
        for (const f of ROSTER_FIELDS) if (typeof obj[f] === "string") values.push(obj[f]);
      }
      for (const v of values) {
        const tok = v.trim().replace(/^@+/, "").toLowerCase();
        if (tok.length >= 3 && tok.length <= 80) out.push(tok);
      }
    }
  } catch {
    return out;
  }
  return out;
}

// ---------------------------------------------------------------------------------------
// Unattended notice (R14b, J3)
// ---------------------------------------------------------------------------------------

/**
 * The credit guard appends one line to `<revxl>/credit-guard-unattended.jsonl` for each unattended
 * decision it makes: every deny, and every paid pass. Once per new batch of lines, the next prompt
 * carries one line, to the user (`systemMessage`) and to the model (`additionalContext`): "N
 * unattended denials (~Q credits blocked), M credits spent unattended since <date> → <log>", where
 * Q and M add up the lines' `cmdWorst` and <date> is the batch's first line. The marker
 * `<revxl>/credit-guard-unattended.seen` holds how many bytes of the log were already reported.
 * Files only; any error = no notice. Returns null, or {note (null when the batch has no readable
 * line), mark()}; mark() is called after the output, so a failed write shows the batch again.
 */
function unattendedNote() {
  try {
    const log = join(revxlDir(), "credit-guard-unattended.jsonl");
    const seen = join(revxlDir(), "credit-guard-unattended.seen");
    const size = statSync(log).size;
    let from = 0;
    try {
      const v = Number(readFileSync(seen, "utf8"));
      if (Number.isInteger(v) && v >= 0 && v <= size) from = v;   // else: the log was cut or replaced
    } catch {}
    if (from === size) return null;                               // nothing new: no read at all
    const buf = readFileSync(log);
    const end = buf.lastIndexOf(10) + 1;                          // whole lines; a partial one waits
    if (end <= from) return null;
    let n = 0, q = 0, m = 0, lines = 0, since = null;
    for (const line of buf.subarray(from, end).toString("utf8").split("\n")) {
      let o;
      try { o = JSON.parse(line); } catch { continue; }
      if (!o || (o.decision !== "deny" && o.decision !== "pass")) continue;
      const w = typeof o.cmdWorst === "number" && Number.isFinite(o.cmdWorst) ? o.cmdWorst : 0;
      if (o.decision === "deny") { n++; q += w; } else m += w;
      lines++;
      if (!since && /^\d{4}-\d\d-\d\dT\d\d:\d\d/.test(String(o.ts))) since = `${String(o.ts).slice(0, 16).replace("T", " ")} UTC`;
    }
    return {
      note: lines
        ? `${n} unattended denials (~${q} credits blocked), ${m} credits spent unattended since ${since || "the last notice"} → ${log}`
        : null,
      mark() {
        try { writeFileSync(seen, String(end)); } catch {}
      },
    };
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------------------

function silent() {
  const u = unattendedNote();
  if (u && u.note) emit(u.note, u.note);
  if (u) u.mark();
  process.exit(0); // no suggestion -> the prompt proceeds untouched (a new unattended notice aside)
}

/**
 * The note's last line (R13a): `jev: on` + the absolute ask-file path, or `jev: off`. On = an
 * OpenRouter key is PRESENT — the env var is set, or the key file's size is above zero. Presence
 * only: the value is never read (P15). On creates `<revxl>` so the Write tool can put the ask there.
 */
function jevLine() {
  let on = Boolean(process.env.OPENROUTER_API_KEY);
  try {
    on = on || statSync(join(homedir(), ".config", "openrouter", "api_key")).size > 0;
  } catch {}
  if (!on) return "jev: off";
  try {
    mkdirSync(revxlDir(), { recursive: true });
  } catch {}
  return `jev: on — ask file: ${join(revxlDir(), "jev-ask.json")}`;
}

/**
 * The ONLY thing this hook can emit. `additionalContext` is advisory text appended to the
 * prompt, and `systemMessage` carries the unattended notice, when there is one, to the user;
 * there is deliberately no permissionDecision, no `decision`, and no `continue:false`
 * anywhere in this file. hookEventName is set explicitly — the credit guard sat inert for six
 * weeks because a hook output missing it is silently discarded.
 */
function emit(context, note) {
  try {
    process.stdout.write(
      JSON.stringify({
        ...(note ? { systemMessage: note } : {}),
        hookSpecificOutput: {
          hookEventName: "UserPromptSubmit",
          additionalContext: context,
        },
      })
    );
  } catch {}
}

function suggest(trigger, detail) {
  const u = unattendedNote();
  const context =
    `[socialcrawl-superengine] Research signal in this prompt (trigger: ${trigger} — ${detail}).\n` +
    `Before hand-rolling API calls or picking endpoints, offer the FRONT DOOR: the ` +
    `\`${FRONT_DOOR}\` skill. It scopes the goal, prices the options, and never spends ` +
    `without an explicit go.\n` +
    `This is a SUGGESTION ONLY — this hook ran no query, called no API, and spent no credits. ` +
    `If the prompt is not about social research, ignore it.\n` +
    (u && u.note ? `${u.note}\n` : "") +               // before the jev line, which stays last
    jevLine();
  emit(context, u && u.note);
  if (u) u.mark();
  process.exit(0);
}

// ---------------------------------------------------------------------------------------
// Build-time self-check (never runs under Claude Code — it passes no argv)
// ---------------------------------------------------------------------------------------

if (process.argv.includes("--self-check")) {
  const { canonical, tokens, unknownAliases, staleStopList, stopListedAliases } = derivePlatforms();
  const report = {
    canonicalCount: canonical.size,
    canonical: [...canonical].sort(),
    aliasCount: Object.keys(HUMAN_ALIASES).length,
    aliases: HUMAN_ALIASES,
    stopList: [...STOP_TOKENS],
    tokenCount: tokens.size,
    // The trigger set in full, so a checker can see exactly what fires and can assert
    // mechanically that no stop-listed name (or spelling variant of one) survived into it.
    triggerTokens: [...tokens].sort(),
    unknownAliases,
    staleStopList,
    // Aliases whose target is stop-listed. Empty is the only acceptable value: a non-empty one
    // means a hand-maintained alias is re-admitting a name the stop-list withheld.
    stopListedAliases,
  };
  process.stdout.write(JSON.stringify(report, null, 2));
  process.exit(unknownAliases.length || staleStopList.length || stopListedAliases.length ? 1 : 0);
}

// ---------------------------------------------------------------------------------------
// Hook entry
// ---------------------------------------------------------------------------------------

let input;
try {
  input = JSON.parse(readFileSync(0, "utf8"));
} catch {
  silent();
}

const prompt = input && typeof input.prompt === "string" ? input.prompt : "";
if (!prompt.trim()) silent();

try {
  const lower = prompt.toLowerCase();

  // 1. Wake-word. Always fires, and costs no file I/O.
  if (WAKE_RE.test(lower)) suggest("wake-word", 'the word "socialcrawl"');

  // 3a/3b. Shape triggers. Also no file I/O.
  if (URL_RE.test(prompt)) suggest("url", "a link in the prompt");
  const handle = prompt.match(HANDLE_RE);
  if (handle) suggest("handle", `@${handle[1]}`);

  // 2. Intent phrase x co-occurrence. URL and @handle already returned above, so the
  //    co-occurrence signals still in play are the ROSTER and the PLATFORM name. Both file
  //    reads live behind this gate, so a prompt with no research phrase does no file I/O.
  const hasIntent = INTENT_RE.test(lower);

  // 2a. Roster entry. GATED behind the intent phrase (R3 round 2, Joe's call) — the plan
  //     lists a roster entry as a class-2 CO-OCCURRENCE signal, not a class-3 standalone
  //     shape. Class 3 is URL-shape and @handle-shape only. Standalone, a rostered common
  //     first name would turn "I met Sarah at Starbucks" into a trigger the moment R4 writes
  //     real data, breaking one of the plan's own SILENT done-tests. Missing roster = no
  //     tokens = falls through; that is a normal state, not an error.
  if (hasIntent) {
    const rosterHit = firstToken(lower, loadRoster());
    if (rosterHit) suggest("intent+roster", `a research phrase alongside "${rosterHit}", which is in your entities roster`);
  }

  // 2b. Platform name. costs.json is read only here — most prompts never touch it.
  if (hasIntent) {
    const platform = firstToken(lower, derivePlatforms().tokens);
    if (platform) suggest("intent+platform", `a research phrase alongside "${platform}"`);
  }

  // Bare intent phrase, or nothing at all. SILENT — this is the correct output.
  silent();
} catch {
  silent(); // any unexpected error -> the prompt proceeds untouched
}
