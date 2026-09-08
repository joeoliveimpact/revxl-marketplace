---
name: onboarding
description: >
  One-time setup for the shortform-superengine plugin. Run this first, right
  after installing. Trigger phrases: "set up shortform superengine", "onboard
  shortform", "install the reel plugin", "configure the reel plugin",
  "shortform setup", "get the shortform superengine ready", "finish setting
  up the content engine", "show my setup". Detects
  what's already on the machine, installs/offers the missing transcription tools,
  wires the required SocialCrawl key (+ optional Groq/Firecrawl/voice), writes a
  setup marker so it only runs once, and verifies everything end-to-end.
---

# shortform-superengine — onboarding

First-run setup. Gets a fresh machine from "just installed" to "can run a
competitor cross-reference and script a reel," with no Joe-specific infrastructure.

## Teach mode

Read the family dial at entry, on every run: `~/.claude/revxl/teach-level`
(one word) if it exists, else the legacy `~/.claude/revxl/teach-mode` mapped
(`beginner` to `new`, `off` to `pro`), else `new`. Convention and the switch:
`../_shared/references/teach-mode.md`.

At **new**, the default, explain in plain words first, THEN name the technical
term with a one-line gloss on first use, and add a "what this means for you" line
wherever the consequence is not obvious. `pro` means teaching off, never less
safe: gates, refusals and cost warnings render at full strength at every level.
On a fresh machine neither file exists, so a first touch runs at **new**; Step 6
writes the default. Mirror the level you read into `state.teach_level`.

## Prereq (E0)

None. onboarding is the door itself: it is where every other skill's E0 refusal
sends a client, so it refuses nobody, and it is safe to re-run (Step 0 routes an
already-onboarded machine into the sub-modes). It is also the first writer on a
fresh install: read `state/<brand>.json` at entry if it is there, Step 6 creates
it when it is not. With no marker, scan
`~/.claude/shortform-superengine/state/*.json` before asking: one file, take its
`brand` and `goal` and say so in a line; several, ask which; none, ask as today.
Schema and rule zero:
`../_shared/references/state-schema.md`. The ledger, and every trigger phrase
quoted below: `../_shared/references/journey-map.md`.

## Terminal paths

Every ending is written out here, so a client is never left with a wired machine
and no idea what to say next. Ids are journey-map rows; the block shape is
`../_shared/references/routing.md`. Render one of these, never an invented menu.

**Next moves** (E1, setup complete)
1. *If `state.goal` is make-a-reel, plan-the-week or read-the-field:* analyze this account against its competitors ... the field read all three of those goals need first. Say: "analyze my Instagram against my competitors"  <- start here
2. *If `state.goal` is set-up, or not set at all:* let the compass read what setup just wrote and rank the moves. Say: "what's next in shortform"
3. *If the brand brain was skipped at Step 4b:* capture the client's real voice first, so the scripts sound like them. Say: "build my brand brain"
4. *If a thought-leader's library is worth capturing:* pull the whole thing into a dated corpus. Say: "harvest <creator>'s library"

**Next moves ... a prior analysis is already on this machine** (E1)
1. *If `state.pulse.scheduled` is false AND the marker's `competitor_pulse.scheduled` is false:* keep that field read alive week to week ... new winners, refreshed charts, one brief. Say: "make the pulse weekly"
2. Script off what already wins in that analysis. Say: "write a reel script from my analysis"
3. Pick the first job and let me route you. Say: "start shortform"

**Next moves ... sub-mode exit** (E2, refresh / reauth / update / show)
1. Back to work ... the compass reads where this brand actually is and ranks what to do next. Say: "what's next in shortform"
2. Print what is wired on this machine, any time. Say: "show my setup"
3. Straight back into the field read. Say: "analyze my Instagram against my competitors"

**Next moves ... a runtime is missing** (E0b)
1. Install Python 3.10+ from python.org, then re-run setup ... the analysis engine and every bundled script run on it. Say: "shortform setup"
2. *If only Node is missing:* install it (Windows `winget install OpenJS.NodeJS.LTS`, Mac `brew install node`) and re-run ... connectors fail to attach silently without it. Say: "shortform setup"
3. Capture the voice while you sort the install out ... brand-brain needs no runtime beyond Claude. Say: "build my brand brain"

**Next moves ... no SocialCrawl key yet** (E0b)
1. Get the key ... the click-path is in [`./references/socialcrawl-setup.md`](references/socialcrawl-setup.md), 100 free credits, about two minutes. Say: "shortform setup"
2. Build the brand brain meanwhile ... voice work needs no social data at all. Say: "build my brand brain"
3. Come back and finish the wiring later. Say: "finish setting up the content engine"

## Layer 2: suggest before invoking

Borderline prompt (could be a fresh setup, could be a quick question)? Ask before running the full onboarding; wording in [`./references/setup-detail.md`](references/setup-detail.md). If they explicitly invoke `/onboarding` or clearly ask to set up, skip the ask.

---

## Step 0 — Preamble + idempotency check

**Marker:** `~/.claude/shortform-superengine/.superengine` (JSON, written in Step 6).

1. If the marker is **absent** → fresh install. Tell the user, in plain language,
   what the next ~2 minutes will do: "I'll check which tools you already have,
   help install anything missing, connect your data key, and confirm it all works."
2. If the marker is **present** → already set up. Don't re-run blind. Offer the
   sub-modes ... **refresh** (re-detect + re-verify), **reauth** (re-enter a key),
   **update** (re-run one step), **show** (print the current setup). Run only what
   they choose. What each covers, plus the stale-plugin and install-trouble routes:
   [`./references/setup-detail.md`](references/setup-detail.md).

---

## Step 1 — Detect the runtime

Probe and report a plain READY/MISSING table. Cross-platform (the client may be on
Windows or Mac).

| Tool | Probe | Needed for |
|------|-------|-----------|
| Python 3.10+ | `python --version` (or `python3`) | runs the analysis engine |
| `ftfy` | `python -c "import ftfy"` | cleans up garbled text in captions |
| Node.js 18+ | `node --version` | some helper tools + MCP connectors won't run/attach without it |

Python missing is the one hard stop: point them at python.org and render the runtime block from `## Terminal paths`. `ftfy` and Node.js are offers, never blocks. Per-platform install commands, and the install-trouble route: [`./references/setup-detail.md`](references/setup-detail.md).

---

## Step 2 — Transcription options (detect → pick the chain)

This is the heart of setup. Why spoken-word transcription, never captions, is the text
every analysis reads: [`./references/setup-detail.md`](references/setup-detail.md).

The chain in one line: **`yt-dlp`** fetches the media, **Groq**
(`whisper-large-v3-turbo`) transcribes in the cloud, **local Whisper**
(`faster-whisper` + `ffmpeg`) transcribes on the client's own machine, and the two
transcribers run **in parallel, first healthy transcript wins**. Install BOTH. Why,
and the brand-vocabulary prompt Groq needs:
[`./references/setup-detail.md`](references/setup-detail.md).

### Detect

Probe each tier: `yt-dlp --version` (fetch), env `GROQ_API_KEY` (cloud transcribe), `python -c "import faster_whisper"` plus `ffmpeg -version` (offline). What each tier buys: [`./references/setup-detail.md`](references/setup-detail.md).

### The gate rule (what counts as "set up enough")

> **Require at least one real transcriber ... Groq OR local Whisper ... then
>   actively recommend adding the other: the two run in parallel (first wins), so
>   the target setup is BOTH, and no reel falls through the cracks. `yt-dlp` is
>   NOT part of this gate: since 0.4.0 it is harvest-only.**

Why one true transcriber is the floor and two is the target:
[`./references/setup-detail.md`](references/setup-detail.md). This chain is also
the **only** way this plugin ever transcribes: SocialCrawl's `*/transcript` endpoints are banned
(10 credits/reel, no advantage). See the "Never" section of
[`../_shared/references/socialcrawl-endpoints.md`](../_shared/references/socialcrawl-endpoints.md).

Resolve with the user:
- **yt-dlp missing** → offer `pip install yt-dlp`, and say what it is for: since
  0.4.0 it is needed **only by `creator-strategy-harvest`**. The cross-reference,
  reel-scripter and pulse chains do not use it, so a failed or skipped install is
  recorded in `setup.tools.yt_dlp` and onboarding carries on. It never blocks.
- **Neither Groq nor local Whisper** → must add one:
  - Groq: send them to `console.groq.com/keys` (free), then set `GROQ_API_KEY`.
  - Local: offer `pip install faster-whisper` + install `ffmpeg` (Windows: `winget
    install Gyan.FFmpeg` or point to ffmpeg.org; Mac: `brew install ffmpeg`).
- **Has one, not the other** → recommend adding the second now, do not just mention it, and accept a skip gracefully. Wording: [`./references/setup-detail.md`](references/setup-detail.md).

Record the resolved chain (which tiers are live) — it goes in the marker so
`competitor-cross-reference` knows what it can use.

---

## Step 3 — Connections

### SocialCrawl — required (bring-your-own-key)

The social-data source. **Each client uses their own key + credits** — never
yours, never the public's. Why the key is exposed to the paying client:
[`./references/setup-detail.md`](references/setup-detail.md).

Don't reinvent the key flow. The resolution ladder lives in
[`../_shared/references/socialcrawl-endpoints.md`](../_shared/references/socialcrawl-endpoints.md)
under "The key": env `SOCIALCRAWL_API_KEY` (starts `sc_`) → file
`~/.config/socialcrawl/api_key` → ask the client once, then auto-save to that
file and tell them where it went.

If no key is found, walk them through getting one with [`./references/socialcrawl-setup.md`](references/socialcrawl-setup.md): the click-path, the referral sign-up link (always that link, never a bare socialcrawl.dev), a Loom slot and the verify calls.
Save the key to `~/.config/socialcrawl/api_key` and confirm with the auth
test (also Step 7). **Can't run analysis without it.**

### RevXL Vault (optional, key issued by Joe)

Joe's live strategy library, not the brand brain (that is 4b, built locally). The
plugin reaches it through `workspace-superengine`, never over HTTP, and this
plugin never handles a Vault key
(`../_shared/references/vault-api.md`). Detect whether
`workspace-superengine` is loaded, record it in `setup.keys_present.vault` and
`setup.ws_superengine_version`, and **never block on it**: absent means the engine
runs on its bundled reference library (edge F3). Wiring detail:
[`./references/setup-detail.md`](references/setup-detail.md).

### Optional services (detect-and-note, never block)

Groq is handled in Step 2. Firecrawl and NotebookLM are detect-and-note only: never configure them here, never block on them. A client with only SocialCrawl can run the full core flow. What to say for each: [`./references/setup-detail.md`](references/setup-detail.md).

### Token hygiene (trim connectors you don't need here)

Offer, in plain words, to switch off the MCP connectors this workspace does not
need; let the client pick; never disable anything without confirming; say that
it is reversible. What a loaded connector costs on every message, the full
script and the reasoning:
[`./references/setup-detail.md`](references/setup-detail.md).

---

## Step 4 — Voice + brand brain (source ladder)

The reel scripts come out in the **client's brand voice**, which lives at
`~/.claude/revxl/<brand>/voc/`: a living brand brain built from the client's own
words. Onboarding only **wires the sources and the cadence**; the bundled
`brand-brain` skill does the mining. Voice comes from spoken or written-by-them
material; offer and avatar can come from anywhere, even a form. Why that split
matters: [`./references/setup-detail.md`](references/setup-detail.md).

### 4a — Find a voice source (walk the ladder, top → down)

Walk the ladder top down and stop at the first tier that exists: **A spoken**
(recordings, podcast, YouTube, webinar, Loom, voice memos), **B written-by-them**
(own captions and reels through SocialCrawl, newsletters, DMs, community posts),
**C written-for-them** (website, sales pages ... offer and avatar only, never the
voice), **D none yet** (the guided interview floor). Tag each source with a
voice-confidence letter and stamp the overall confidence on the brain. The table,
the blending rules and the floor:
[`./references/setup-detail.md`](references/setup-detail.md).

Record the found sources + overall confidence in the marker (`voice_sources`,
`voice_confidence`). **Never hard-fail** — worst case is interview-floor, never a dead end.

### 4b — Existing brain?

1. If `~/.claude/revxl/<brand>/voc/` exists → reuse it. Tell the user their brand
   brain is already on file; note its age (see 4c).
2. If absent → offer to build it NOW with the bundled `brand-brain` skill (mines the
   recordings source / own content into the shared brain; ~a few minutes). Decline →
   say plainly: *"That's fine — reel-scripter will use a sensible interim voice until
   you build it. Run brand-brain anytime."* Then continue.

### 4c — Auto-refresh offer (keep it fresh, hands-off)

Offer to keep the brain fresh automatically ... a scheduled task for a Cowork
client, a routine or cron for a Code client, and ask which slot (*"Friday night,
Monday morning, or a time you pick?"*). Why it goes stale, and the 6-to-7-day
target: [`./references/setup-detail.md`](references/setup-detail.md).

Capture the choice in the marker (`brand_brain.refresh`). **`brand-brain` is bundled
in this plugin**, so wire the auto-refresh schedule now — it points at the bundled
`brand-brain` refresh (no missing command). Record the source + cadence + runtime,
and set `brand_brain.refresh.scheduled: true` once the user picks a cadence.

Do not hard-fail on missing voice. v1 ships with interim-voice degrade.

---

## Step 5 — (placeholder) tier-aware hooks for v2

Nothing to configure now. The marker's `tier` field keeps the shape forward-compatible for the v2 content loop: [`./references/setup-detail.md`](references/setup-detail.md).

---

## Step 6 — Write state

1. Ensure `~/.claude/shortform-superengine/` exists.
2. Write the marker `~/.claude/shortform-superengine/.superengine`. Read the
   `version` value out of this plugin's `.claude-plugin/plugin.json` at write
   time and copy it in. **Never hardcode a version literal here**: the marker
   went stale that way once already.

```json
{
  "version": "<the version field read from .claude-plugin/plugin.json>",
  "onboarded_at": "<ISO date>",
  "transcription_chain": ["captions", "groq|local|both"],
  "connections": { "socialcrawl": true, "groq": false, "firecrawl": false },
  "voice_sources": ["fathom|fireflies|own-social|newsletter|podcast|website|interview"],
  "voice_confidence": "A|B|C|interview|none",
  "active_brand": "<brand-slug>",
  "brand": "<the same brand-slug>",
  "brand_brain": {
    "present": false,
    "updated_at": null,
    "refresh": { "scheduled": false, "cadence": null, "runtime": "cowork|code|null", "mode": "auto-refresh|remind-only|null" }
  },
  "competitor_pulse": { "scheduled": false, "cadence": null, "runtime": null, "project": null, "last_run": null },
  "tier": "unknown"
}
```

`active_brand` is authoritative; `brand` carries the same slug so 0.3.4 readers
keep working. Ask for the brand rather than writing null: every downstream file
is keyed to that slug. **Never write `voc_present`** (vestigial at 0.4.0, nothing
reads it, `voc.present` is derived from `~/.claude/revxl/<brand>/voc/` on read);
if an old marker holds one, leave it and never trust it. Keep the
`competitor_pulse` block exactly this shape: `shortform-start` migrates it into
`state.pulse`. Field-by-field notes: [`./references/setup-detail.md`](references/setup-detail.md).

3. **Write the journey file.** Create
   `~/.claude/shortform-superengine/state/<brand>.json` from the template in
   `../_shared/references/state-schema.md` when it is absent, then write only the
   keys this skill owns: `setup.complete`, `setup.keys_present.socialcrawl` and
   `.vault` (presence only, never a key itself), `setup.tools.yt_dlp` / `.groq` /
   `.whisper`, `setup.socialcrawl_superengine_installed`,
   `setup.ws_superengine_version`, plus `brand` (this file's own slug) and
   `project_path` if the client already has a project directory. Then the
   every-skill keys: append `onboarding` to `completed_skills`, refresh
   `updated_at`, mirror the teach level into `teach_level`, log declined offers in
   `declined_offers`. Nothing else: rule zero.

4. **Teach level.** Ensure `~/.claude/revxl/` exists, then: neither file present
   -> write `new` to `teach-level` and the legacy word `beginner` to `teach-mode`;
   only the legacy `teach-mode` present -> migrate in place (`beginner` to `new`,
   `off` to `pro`) and write that word to `teach-level`; `teach-level` already
   present -> leave both alone, the client set it. Then one line: *"I've set the
   assistant to new mode ... it explains things in plain English first. Say
   `/teach-mode pro` any time for the standard voice."*

---

## Step 7 — Verify

Run real checks, report a pass/fail table — never claim done without proof:

- **Files:** marker exists + parses; `~/.config/socialcrawl/api_key` non-empty.
- **No placeholders:** grep the marker for `{{` → must be zero.
- **SocialCrawl auth:** one cheap live call (a credit-balance or a 1-result search)
  → confirms the key works. If it 401s, send them back to Step 3.
- **Transcription chain:** the recorded chain satisfies the gate rule (at least
  one real transcriber). If not, back to Step 2. `yt-dlp` is recorded in
  `setup.tools.yt_dlp` and is never a pass/fail item: it is harvest-only.
- **Brand brain (non-blocking):** marker has `voice_sources`, a `voice_confidence`
  tier (`interview` and `none` both pass) and a `brand_brain.refresh` choice that
  matches Step 4. Never fail onboarding over voice.
- **Teach level:** `~/.claude/revxl/teach-level` exists and reads `new`,
  `learning` or `pro`.
- **Journey file:** `state/<brand>.json` exists, parses, and its `brand` matches
  the marker's `active_brand`.

---

## Step 8 — Activation

Hand the client to the front door. Render the E1 block from
`## Terminal paths`, state-gated: if a prior project with `analysis-data.json`
already exists on this machine, render the "a prior analysis is already on this
machine" variant instead. Offer nothing that is not in that section, and nothing
the machine cannot actually run right now.

Then probe `~/.claude/socialcrawl-superengine/.superengine` and say one line either way: installed means the deep research plays are available on top; absent means it is an optional add from the same marketplace. Wording, the second detection path and how the plays are invoked: [`./references/setup-detail.md`](references/setup-detail.md). Record the result in `setup.socialcrawl_superengine_installed`.

Sub-mode exits (refresh / reauth / update / show) end the same way, with the
sub-mode block (E2) from `## Terminal paths`.
