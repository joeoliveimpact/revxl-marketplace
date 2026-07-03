---
name: onboarding
description: >
  One-time setup for the shortform-superengine plugin. Run this first, right
  after installing. Trigger phrases: "set up shortform superengine", "onboard
  shortform", "install/configure the reel plugin", "shortform setup", "get the
  shortform superengine ready", "finish setting up the content engine". Detects
  what's already on the machine, installs/offers the missing transcription tools,
  wires the required SocialCrawl key (+ optional Groq/Firecrawl/voice), writes a
  setup marker so it only runs once, and verifies everything end-to-end.
---

# shortform-superengine — onboarding

First-run setup. Gets a fresh machine from "just installed" to "can run a
competitor cross-reference and script a reel," with no Joe-specific infrastructure.

## Teach mode

Read `~/.claude/revxl/teach-mode` (one word) if it exists, else treat it as
`beginner`. Convention: `_shared/references/teach-mode.md`.
- **beginner** (default): plain-English-first. Explain a thing in plain words,
  *then* name the technical term with a one-line gloss. Add a "what this means
  for you" line whenever the consequence isn't obvious.
- **off**: standard voice, no glosses.

During onboarding you have not written the file yet, so you'll be in **beginner**
by default — which is right for a coach's first touch. (You write the default in
Step 6.)

## Layer 2: suggest before invoking

If the user's prompt is borderline — could be a fresh setup or could be a quick
question — ask first:

> "Looks like you want to set up the shortform superengine — want me to run the
> full onboarding (detect tools, wire your keys, verify)? It's a one-time thing."

If they explicitly invoke `/onboarding` or clearly ask to set up, skip the ask.

---

## Step 0 — Preamble + idempotency check

**Marker:** `~/.claude/shortform-superengine/.superengine` (JSON, written in Step 6).

1. If the marker is **absent** → fresh install. Tell the user, in plain language,
   what the next ~2 minutes will do: "I'll check which tools you already have,
   help install anything missing, connect your data key, and confirm it all works."
2. If the marker is **present** → already set up. Don't re-run blind. Offer sub-modes:
   - **refresh** — re-detect tools + re-verify (nothing destructive),
   - **reauth** — re-enter a key (SocialCrawl/Groq),
   - **update** — re-run a specific step,
   - **show** — print current setup from the marker.
   Pick one with the user; only run what they choose.
   - **stale plugin?** If the user reports the plugin won't pick up the latest
     version (common on **Mac desktop** — marketplace updates silently don't sync),
     point them to [`./references/updating.md`](references/updating.md) for the
     uninstall/reinstall workaround. Not your bug to fix here — just unblock them.
   - **install / connection trouble?** A tool won't install, a connector won't
     attach, or antivirus is blocking the setup → [`./references/troubleshooting.md`](references/troubleshooting.md).

---

## Step 1 — Detect the runtime

Probe and report a plain READY/MISSING table. Cross-platform (the coach may be on
Windows or Mac).

| Tool | Probe | Needed for |
|------|-------|-----------|
| Python 3.10+ | `python --version` (or `python3`) | runs the analysis engine |
| `ftfy` | `python -c "import ftfy"` | cleans up garbled text in captions |
| Node.js 18+ | `node --version` | some helper tools + MCP connectors won't run/attach without it |

- **Python missing** → stop and point them to python.org (everything downstream needs it).
- **`ftfy` missing** → offer `pip install ftfy`.
- **Node.js missing** → offer to install it (Windows: `winget install OpenJS.NodeJS.LTS`,
  or nodejs.org → LTS installer; Mac: `brew install node`). Don't skip this — a missing
  Node is a common cause of connectors silently failing to attach later.

> Install or connection hiccup (a tool won't install, a connector won't attach, antivirus
> blocking it)? See [`./references/troubleshooting.md`](references/troubleshooting.md).

---

## Step 2 — Transcription options (detect → pick the chain)

This is the heart of setup. Reels get turned into text three possible ways, cheapest
to best. The plugin uses whatever the user has, in this order:

1. **Captions-first** — pulls the reel's own captions with `yt-dlp`. Free, instant,
   no transcribing. **Required floor.**
2. **Groq** — fast cloud transcription when a reel has no captions. Near-free, needs
   a free API key.
3. **Local Whisper** — `faster-whisper` transcribes on the user's own computer.
   Offline, $0, slower. Needs `ffmpeg` + the `faster-whisper` Python package.

### Detect

| Tier | Probe | Plain meaning |
|------|-------|--------------|
| Captions | `yt-dlp --version` | can read a reel's built-in captions |
| Groq | env `GROQ_API_KEY` set? | has a cloud-transcribe key |
| Local Whisper | `python -c "import faster_whisper"` **and** `ffmpeg -version` | can transcribe offline |

### The gate rule (what counts as "set up enough")

> **Require `yt-dlp` (the captions floor), AND require at least one real transcriber
> — Groq OR local Whisper. Offer to add the other.**

Why: captions alone can't handle a reel that *has no captions*, so one true
transcriber is the real floor.

Resolve with the user:
- **yt-dlp missing** → offer `pip install yt-dlp` (required — can't continue without it).
- **Neither Groq nor local Whisper** → must add one:
  - Groq: send them to `console.groq.com/keys` (free), then set `GROQ_API_KEY`.
  - Local: offer `pip install faster-whisper` + install `ffmpeg` (Windows: `winget
    install Gyan.FFmpeg` or point to ffmpeg.org; Mac: `brew install ffmpeg`).
- **Has one, not the other** → mention the other as optional and move on. Example,
  in beginner voice: *"You've got captions + offline Whisper, so you're covered. You
  don't have a Groq key — that's optional; it makes no-caption reels transcribe faster
  in the cloud. Add one anytime, or skip it."*

Record the resolved chain (which tiers are live) — it goes in the marker so
`competitor-cross-reference` knows what it can use.

---

## Step 3 — Connections

### SocialCrawl — required (bring-your-own-key)

The social-data source. **Each client uses their own key + credits** — never
yours, never the public's (this is why the key is exposed to the paying client:
it's the only way they don't draw down someone else's credits).

Don't reinvent the key flow — **delegate to the bundled `socialcrawl` skill's
resolution** (it ships inside this plugin at `skills/socialcrawl/`, so it's always
present — no separate install): env `SOCIALCRAWL_API_KEY` (starts `sc_`) → file
`~/.config/socialcrawl/api_key` → ask the client + auto-save.

If no key is found, walk them through getting one. Point them at
[`./references/socialcrawl-setup.md`](references/socialcrawl-setup.md) — the
click-path (sign up via the **referral link** `https://www.socialcrawl.dev/?ref=AQNU384G`,
100 free credits → **API Keys** → **Create** → copy the `sc_…` key → paste), a Loom
slot, and the verify calls. (Always hand clients the referral sign-up link, not a bare
socialcrawl.dev.)
Save the key to `~/.config/socialcrawl/api_key`. Confirm with the balance/auth
test (also Step 7). **Can't run analysis without it.**

### Optional services (detect-and-note, never block)

| Service | What to do |
|---------|-----------|
| Groq | Already handled in Step 2 if they chose it (cloud transcription). |
| Firecrawl | Open-web research (client website positioning). If the `firecrawl` CLI is installed + authed, note it; else mention it's optional and skip. |
| NotebookLM | Only if they use it for creator harvests. Hand off to its own installer; don't configure here. |

A client with only SocialCrawl can run the full core flow.

### Token hygiene — trim connectors you don't need here

Every MCP connector loaded in a workspace spends tokens on **every** message, just
by being available — whether or not you use it. This plugin ships **no** MCP servers
of its own, so it adds nothing here; the cost comes from other connectors the client
has switched on globally (Drive, Telegram, calendars, CRMs, etc.).

In **this** shortform workspace, the core flow only needs: SocialCrawl (data), the
transcription chain, and the recordings source from Step 4. Offer, in plain words:
*"You've got a bunch of connectors switched on. For reel work you only need a few —
want to switch the rest off in this workspace so Claude stays fast and doesn't burn
tokens carrying tools it won't use? You can flip them back on anytime."* Let the user
decide which to keep; never disable anything without confirming. This is advisory —
**purely the user's call**, and reversible.

---

## Step 4 — Voice + brand brain (source ladder)

The reel scripts come out in the **client's brand voice**, which lives at
`~/.claude/revxl/<brand>/voc/`. The voice isn't a one-time form — it's a **living
brand brain** built from the client's **own words, wherever they live**: their tone,
*who they help* and *the pains they help with*, the **topics** they're on right now,
and the **jokes that actually land**. Onboarding only **wires the sources and the
cadence** — the dedicated voice skill does the mining.

Two different needs, different best-sources:
- **Voice** (how they sound) → best from *spoken* or *written-by-them*.
- **Offer + avatar** (what they sell, who they help, the pains) → can come from
  anywhere, even a form.

### 4a — Find a voice source (walk the ladder, top → down)

Walk down until something exists. Tag each found source with a **voice-confidence**
(A/B/C); stamp the brain with the overall confidence so consumers (reel-scripter)
know how hard to lean on the voice.

| Tier | Sources | Detect / pull | Voice-confidence |
|------|---------|---------------|------------------|
| **A — spoken** | Fathom / Fireflies recordings, podcast, YouTube, webinar/VSL, Loom, voice memos | Fathom or Fireflies MCP available? ask for a podcast/YT handle | **A (high)** — real cadence + objections + jokes |
| **B — written-by-them** | their own social captions/reels, sent newsletters, DMs, community posts (Skool/GHL/Telegram), their tweets/threads | **own posts via SocialCrawl (already wired)**; ask for a newsletter export | **B (med)** — their writing voice + current topics |
| **C — written-FOR-them** | website, sales/landing pages, course copy | firecrawl the site | **C (low for voice)** — usually copywriter-written; use for **offer/avatar only** |
| **D — none yet** | guided interview | see the floor below | floor — works for everyone |

Rules:
- **Prefer the highest tier present; blend downward.** A spoken source *sets* the
  voice; B/C add offer + topics. **Never let a Tier-C site set the voice** — that's
  the noise-factor trap; keep them sounding like *them*.
- **Their own social is the no-recordings primary.** SocialCrawl is already wired, so
  with no recordings, pulling their own captions is the lowest-friction *real* voice
  source. Almost everyone has it.
- **Offer/avatar pulls wider than voice** — also testimonials/reviews (the *avatar's*
  own pain language — gold), intake forms, an existing brand guide. Tag these as
  offer/avatar inputs, **not** voice.

**The floor (Tier D) — brand-new owner / nothing to pull.** If A–C come up empty (new
business, no audience, no site), don't dead-end:
1. **Guided interview now** — the voice skill interviews them (same move as the email
   engine's story intake): voice from their raw answers + offer + avatar from
   structured Q&A. In Cowork/voice it even captures *spoken* voice.
2. **Record going forward** — turn on call recording (Fathom) from call #1, save voice
   memos. The brain compounds: day-1 thin-but-real → week-4 rich. Ties into the
   freshness heartbeat (4c).
Stamp `voice_confidence: "interview"` so reel-scripter leans conservative until real
sources accumulate.

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

A brand brain goes stale: tone drifts, and — more importantly — the **topics** your
clients raise change week to week. A reel built off a 3-day-old hot objection lands;
one built off month-old topics doesn't. So offer to keep it fresh automatically:

- **Cowork client** → offer a **scheduled task** that re-mines recent recordings on a
  cadence. Ask their slot: *"Friday night, Monday morning, or a time you pick?"*
- **Code client** → offer a **routine / cron** (Windows Scheduled Task or `/schedule`)
  on the same cadence.
- Target: **never more than 6–7 days stale.**

Capture the choice in the marker (`brand_brain.refresh`). **Lean-v1 note:** if the
voice skill isn't installed yet, record the source + cadence preference now and tell
the user the auto-refresh **activates when the brand-brain build lands** (the
fast-follow). Don't create a schedule that points at a command that doesn't exist
yet — capture intent, wire on arrival.

Do not hard-fail on missing voice. v1 ships with interim-voice degrade.

---

## Step 5 — (placeholder) tier-aware hooks for v2

v2 adds a content-loop (calendar + Metricool scheduling/measurement, tier-gated).
Nothing to configure now. Just leave the marker shape forward-compatible (Step 6
includes a `tier` field set to `unknown`) so the v2 Metricool step drops in clean.

---

## Step 6 — Write state

1. Ensure `~/.claude/shortform-superengine/` exists.
2. Write the marker `~/.claude/shortform-superengine/.superengine`:

```json
{
  "version": "0.1.0",
  "onboarded_at": "<ISO date>",
  "transcription_chain": ["captions", "groq|local|both"],
  "connections": { "socialcrawl": true, "groq": false, "firecrawl": false },
  "voice_sources": ["fathom|fireflies|own-social|newsletter|podcast|website|interview"],
  "voice_confidence": "A|B|C|interview|none",
  "brand": "<brand-slug or null>",
  "voc_present": false,
  "brand_brain": {
    "present": false,
    "updated_at": null,
    "refresh": { "scheduled": false, "cadence": null, "runtime": "cowork|code|null" }
  },
  "tier": "unknown"
}
```

`voice_sources` = which source-ladder tiers were found (Step 4a); `voice_confidence`
= the overall tier the brain rests on (`A` spoken → `C` written-for-them → `interview`
floor → `none`). Consumers lean bolder on A, conservative on interview. `brand_brain`
= the living voice/ICP/topics/humor artifact: `present` once the voice skill has built
it, `updated_at` its last-build stamp (the freshness clock reads this), and `refresh`
the auto-refresh choice from Step 4c (`scheduled` stays false in lean v1 until the
brand-brain build ships, but `cadence`/`runtime` capture the user's intent now).

3. **teach_mode default.** Ensure `~/.claude/revxl/` exists. If
   `~/.claude/revxl/teach-mode` does **not** exist, create it with the single word
   `beginner`. If it already exists, leave it (the user may have set it). Tell the
   user, plainly: *"I've set the assistant to beginner mode — it'll explain things
   in plain English first. Say 'turn off teach mode' or run `/teach-mode off` anytime
   to switch to the standard voice."*

---

## Step 7 — Verify

Run real checks, report a pass/fail table — never claim done without proof:

- **Files:** marker exists + parses; `~/.config/socialcrawl/api_key` non-empty.
- **No placeholders:** grep the marker for `{{` → must be zero.
- **SocialCrawl auth:** one cheap live call (a credit-balance or a 1-result search)
  → confirms the key works. If it 401s, send them back to Step 3.
- **Transcription chain:** the recorded chain satisfies the gate rule (yt-dlp + ≥1
  transcriber). If not, back to Step 2.
- **Brand brain (non-blocking):** marker has `voice_sources` + a `voice_confidence`
  tier (even `interview`/`none` is a pass — the floor always applies) and a
  `brand_brain.refresh` choice. Confirm it reflects what they picked in Step 4; never
  fail onboarding over voice.
- **teach_mode:** `~/.claude/revxl/teach-mode` exists and reads `beginner` or `off`.

---

## Step 8 — Activation

Tell the user, in plain language, what they can do now:

> "You're set up. Two things you can run:
> - **Competitor cross-reference** — 'analyze my Instagram against my competitors'
>   → a strategy roadmap grounded in real reel data.
> - **Reel-scripter** — after an analysis, 'write a reel script from my analysis'
>   → a reel in your brand voice off what already works in your niche.
> Start with the competitor cross-reference — reel-scripter reads its output."

---

## Notes

- Idempotent: safe to re-run; Step 0 routes to sub-modes if already set up.
- No private infrastructure anywhere — the transcription chain is fully portable
  (captions-first → Groq → local Whisper).
- House pattern: detect → offer-install → wire → write marker → verify → activate.
