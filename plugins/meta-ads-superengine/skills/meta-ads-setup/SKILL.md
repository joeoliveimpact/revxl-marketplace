---
name: meta-ads-superengine:meta-ads-setup
description: Chunked, resumable onboarding for the Meta ads engine. Runs the connections audit, the ads-history interview, business config, and teach-level calibration; writes the install marker and the per-brand state file. Minimal viable setup is just offer + price + spend level — everything else can wait. Trigger phrases include "set up my ads", "ads setup", "configure meta ads", "resume setup", "switch brand".
---

# meta-ads-setup — onboarding (chunked + resumable)

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #2.
State shapes: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/state-schema.md` (the
marker + `state/<brand>.json` templates live there — create from them, never invent keys).

## Load
1. `state-schema.md` (shapes + ownership) · `journey-map.md` (edges) · `teach-mode.md` · `glossary.md` — all under `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/`
2. Existing `~/.claude/meta-ads-superengine/.superengine` + state — **resuming?** Say "we're N% through — picking up at <section>" and jump there.

## Section 0 — Brand + teach calibration (2 minutes)

**"switch brand" fast path (no interview):** if invoked as "switch brand",
ask which brand → normalize to the slug. Slug already has state → flip the
marker's `active_brand` to it + one-line confirm ("switched to <brand>") and
STOP — no interview. Slug unknown → offer to set it up ("no engine for
<brand> yet — want to set it up?") → falls into the normal flow below.

1. **Brand name** → normalize to the slug (state-schema rules; same convention
   as brand-brain). **Write the marker's `active_brand` now** — create the
   marker from the state-schema template if absent, otherwise UPDATE
   `active_brand` on the existing marker (never a second creation). Existing
   state for that slug → this is a resume/edit, load it.
2. **Teach calibration** — **already calibrated? skip it.** If
   `~/.claude/revxl/teach-level` already exists (a prior brand/engine set it ...
   it's family-shared), don't re-ask: one-line confirm ("teach level: <level>
   ... say 'teach mode' to change"), and if the marker's `tooling_level` is set,
   confirm both axes (per `teach-mode.md`'s split-axis rule). **Absent** → two
   questions: "How familiar are you with Meta ads?" (→ `teach-level`) / "How
   familiar with Claude and plugins?" (→ `tooling_level` when it diverges) →
   pick `new`/`learning`/`pro`, write `~/.claude/revxl/teach-level` + legacy
   dual-write per `teach-mode.md`. Tell them how to change it anytime.

## Section A — The three that matter (minimal viable setup)
Ask conversationally, in the coach's words:
1. **Offer** — what do you sell, to whom (one sentence).
2. **Price** — what does it cost. **If the answer is 0 / "free" / "$0"** (free
   or low-ticket front end), ask ONE follow-up: *"what does a client eventually
   pay you? (the backend program price — that's the number your ad math runs
   on)"* → `setup.backend_price`. **If the price is monthly/recurring**
   (subscription, membership), ask *"how many months does an average client
   stay?"* → `setup.avg_retention_months` (breakeven-math turns it into
   lifetime value).
3. **Spend level** — spending now, or planning to spend, per day.

→ Write `setup.offer/price/spend_level` (+ `setup.backend_price` when the
front end is free/low-ticket), and **stamp `offer_version: 0` explicitly on
this first capture** (never leave it to a default; 0 is the initial value, not
"unset" ... consumers null-check it). **The moment these three exist,
say so:** *"That's enough to start — everything else below can wait."* and
include the E3 move (breakeven-math) in every pause-point's Next-Moves from
here on.

## Section B — Ads history (seeds journey position)
4. Run ads before? What happened? (yes/no → `setup.ran_ads_before`; free text
   → `history_note`)
5. **Currently spending?** → `currently_spending`. **If yes → edge F5, the
   onramp:** flag it now — *"We won't touch anything that's live. First we
   import what's running, diagnose the stage, and backfill — no pausing."*
   Attach or paste your export right here — I'll file it for you (into
   `state/<brand>/history/`). To pull it: Ads Manager → Reports (or the
   Export button) → Export table data → CSV. (When the Meta MCP is connected,
   Section C cross-checks this against a live ACTIVE read; an "I think so /
   not sure" answer runs that cross-check as soon as the connection is
   confirmed, before leaning on the onramp promise.)
6. **Funnel type** — does a sales call sit between a lead and the purchase, or
   do people buy directly? → `setup.funnel_type` (`"call"` | `"checkout"`).
7. **Call funnels only** (checkout funnels skip this ... breakeven-math asks
   the right ones): close/show/lead→call rates if known (skip freely —
   breakeven-math asks again and sanity-checks; don't double-interrogate).
8. **CRM** — GHL / Kajabi / ClickFunnels / other / none → `setup.crm`.

## Section C — Connections audit (each: ✅/⚠️ + what it unlocks + the fix)
Detect, never demand — absent is NEVER a blocker (family law):
| Connection | Detect | Unlocks | Fix |
|---|---|---|---|
| Brain key | ladder per `vault-api.md` (env → `~/.config/revxl/vault_api_key`) | freshest strategy patterns woven into deliverables | paste your access key here when you have it — I'll store it for you (degrades cleanly without it — F9) |
| Brand brain (voc/) | `~/.claude/revxl/<brand>/voc/voice-guide.md` | copy in YOUR voice; absent → offer capture at first creative skill, not now | build the brand brain (voc/) — offered at the first creative skill |
| Meta MCP | connected tools | live numbers instead of pasting; manual-paste always works | Say: "connect ads manager" |
| GHL MCP | connected tools | qualified-event fast-path wiring | Say: "connect ads manager" |
| socialcrawl key | env → `~/.config/socialcrawl/api_key` | competitor/own-content mining (✋ credit-gated) | paste your `sc_` key here when you have it — I'll store it for you |
| carousel-superengine | its `.superengine` marker | slide production handoff | install carousel-superengine |

→ Write results into the marker's `connections` block.

**Cross-check `currently_spending` (connected-only enhancement, family law):**
if `currently_spending` was answered TRUE in Section B AND the Meta MCP is
connected, run a live campaign-level read (`ads_get_ad_entities`, campaign
level, `effective_status`) to confirm what the account is actually doing:
- **Any ACTIVE campaign found** → the onramp stands as answered; keep
  `currently_spending: true` and continue.
- **Zero ACTIVE campaigns** → reset the expectation plainly: *"Your account
  shows everything paused, so nothing is currently spending."* Correct
  `currently_spending` to false, keep `ran_ads_before: true` and the imported
  history, and route as a RELAUNCH (import the history for diagnosis, then a
  fresh plan and launch) rather than a live onramp.
- **Meta MCP not connected** → the coach's word stands (family law); no live
  read, no nagging.

## Section D — Wrap
- Update the marker (`installed_at`, `connections`; `active_brand` was already
  written in Section 0 — this is an UPDATE, not a fresh creation) + write the
  state file; stamp `setup.complete_pct` honestly.
- Seed `stage` from Section B when confident (spend level + history);
  otherwise leave null (stage-check owns it).
- Any offer/price EDIT on a resume bumps `offer_version` (cascade warning:
  targets + compliance go stale — say so plainly). **If `launched_at` is set (a
  live launch exists),** the warning goes past the in-plugin cascade: say
  plainly that the ads Meta is still serving carry the OLD offer/price ... this
  edit changes the plugin's records, not the live campaign. Real-world confirm:
  ask whether the live campaign should keep running as-is, be updated in Ads
  Manager (walk the coach through it), or be relaunched under the new offer
  (compliance + targets re-run first, per the cascade).

## Terminal paths — inline blocks (routing.md grammar)

**Minimal-viable met (E3):**

**Next moves**
1. Run your numbers — what a lead is allowed to cost YOU, before $1 is spent. Say: "run my numbers"  ← start here
2. Finish the rest of setup — connections + history, ~5 more minutes, resumable anytime. Say: "resume setup"
3. See the whole road first. Say: "ads tour"

**Paused mid-interview (E4):**

**Next moves**
1. Pick setup back up — we're N% through, I saved everything. Say: "resume setup"
2. *If offer + price + spend are already in:* skip ahead to the math gate. Say: "run my numbers"

**Next moves — already running ads (F5 onramp)**
1. Import what's running — I'll read your exports and backfill state, nothing live gets touched. Say: "review my ads" (import mode)
2. Diagnose your spend stage from the imports. Say: "what stage am I in"
3. Finish the rest of setup. Say: "resume setup"

Triggers quoted from the journey-map roster.

## Teach mode
In `new`: plain-English-first — gloss every term on first use (deep-tier
glossary entries for any glossary Section-3 term, e.g. CPL/ROAS, with worked
numbers once `price` is captured), explain WHY offer + price + spend are the only three
hard requirements, add "what this means for you" lines. In `learning`: gloss
Meta terms first use. In `pro`: terse — ask the questions, record, move.
