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

---

## Step 1 — Detect the runtime

Probe and report a plain READY/MISSING table. Cross-platform (the coach may be on
Windows or Mac).

| Tool | Probe | Needed for |
|------|-------|-----------|
| Python 3.10+ | `python --version` (or `python3`) | runs the analysis engine |
| `ftfy` | `python -c "import ftfy"` | cleans up garbled text in captions |

If Python is missing → stop and point them to python.org (everything downstream
needs it). If `ftfy` is missing → offer `pip install ftfy`.

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

Don't reinvent the key flow — **delegate to the `socialcrawl` skill's resolution**:
env `SOCIALCRAWL_API_KEY` (starts `sc_`) → file `~/.config/socialcrawl/api_key`
→ ask the client + auto-save.

If no key is found, walk them through getting one. Point them at
[`./references/socialcrawl-setup.md`](references/socialcrawl-setup.md) — the
click-path (sign up at socialcrawl.dev, 100 free credits → **API Keys** →
**Create** → copy the `sc_…` key → paste), a Loom slot, and the verify calls.
Save the key to `~/.config/socialcrawl/api_key`. Confirm with the balance/auth
test (also Step 7). **Can't run analysis without it.**

### Optional services (detect-and-note, never block)

| Service | What to do |
|---------|-----------|
| Groq | Already handled in Step 2 if they chose it (cloud transcription). |
| Firecrawl | Open-web research (client website positioning). If the `firecrawl` CLI is installed + authed, note it; else mention it's optional and skip. |
| NotebookLM | Only if they use it for creator harvests. Hand off to its own installer; don't configure here. |

A client with only SocialCrawl can run the full core flow.

---

## Step 4 — Voice (voc handshake)

The reel scripts come out in the **client's brand voice**, which lives at
`~/.claude/revxl/<brand>/voc/` (three files: voice-guide, voc-profile,
business-config). Onboarding only **orchestrates** — it does not mine voice itself.

1. If `~/.claude/revxl/<brand>/voc/` exists → reuse it. Tell the user their voice
   profile is already on file; no re-work.
2. If absent → the dedicated voice skill builds it. **If that skill isn't installed
   yet** (v1 lean path), say so plainly: *"Your brand-voice profile isn't built yet.
   That's fine — reel-scripter will use a sensible interim voice until you build it.
   It's a fast-follow, not a blocker."* Then continue.

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
  "brand": "<brand-slug or null>",
  "voc_present": false,
  "tier": "unknown"
}
```

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
