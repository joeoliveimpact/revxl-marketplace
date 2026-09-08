# Setup detail ... the reference half of onboarding

Everything onboarding has to explain but does not need in line. `SKILL.md`
keeps the steps; this file keeps the tables, the walkthroughs and the why.
Moved here at 0.4.0 so `SKILL.md` fits the routing size rule
(`../../_shared/references/routing.md`). The text is the 0.3.4 text, unchanged
apart from house punctuation.

## Sub-modes (Step 0, a machine that is already set up)

2. If the marker is **present** → already set up. Don't re-run blind. Offer sub-modes:
   - **refresh** ... re-detect tools + re-verify (nothing destructive),
   - **reauth** ... re-enter a key (SocialCrawl/Groq),
   - **update** ... re-run a specific step,
   - **show** ... print current setup from the marker.
   Pick one with the user; only run what they choose.
   - **stale plugin?** If the user reports the plugin won't pick up the latest
     version (common on **Mac desktop** ... marketplace updates silently don't sync),
     point them to [`updating.md`](updating.md) for the
     uninstall/reinstall workaround. Not your bug to fix here ... just unblock them.
   - **install / connection trouble?** A tool won't install, a connector won't
     attach, or antivirus is blocking the setup → [`troubleshooting.md`](troubleshooting.md).

## The transcription chain (Step 2)

1. **`yt-dlp`** ... fetches the reel's video/audio (and any subtitle track) so the
   transcribers have something to eat. **Required floor** ... it feeds everything below.
2. **Groq** ... fast cloud transcription (`whisper-large-v3-turbo`). Near-free, needs
   a free API key. **Pass a vocabulary prompt built from brand-brain** ... without one,
   Whisper mangles brand and product names it has never seen (measured: the correct
   brand name appeared 3 times against 18 mangled ones in the same body of audio).
   See `brand-brain/references/transcription-vocabulary.md` ... it also covers the two
   ways a prompt can backfire.
3. **Local Whisper** ... `faster-whisper` transcribes on the user's own computer.
   Offline, $0, slower. Needs `ffmpeg` + the `faster-whisper` Python package.

Groq and local Whisper run **in parallel ... first healthy transcript wins**. Install
BOTH so transcription never stalls on one engine having a bad day.

**Why one is the floor and two is the target.** Captions alone cannot handle a reel
that *has no captions*, so one true transcriber is the real floor; and two mean a
Groq outage or an offline session still cannot stall a run.

**Why real transcription and never captions (relocated from `SKILL.md` Step 2 at
0.4.0).** Real spoken-word transcription is not optional garnish, it is the primary
text every analysis reads. Without it the engine falls back to post captions, which
are *not* what the creator says on camera, and the analysis is degraded.

## RevXL Vault wiring (Step 3)

Joe's live strategy library, not the brand brain (that is 4b, built locally):
current, curated content-strategy intelligence that updates continuously, unlike
the bundled reference files.

**This plugin never handles a Vault key and never calls the Vault over HTTP.**
Since 0.4.0 the only path is the `workspace-superengine:revxl-vault-search`
skill, and the callee owns the key
([`../../_shared/references/vault-api.md`](../../_shared/references/vault-api.md)).
Onboarding's whole job here is a probe:

1. Does the `revxl-vault-search` skill resolve? Record the answer in
   `setup.keys_present.vault` (presence only, never a key) and the loaded
   workspace-superengine version in `setup.ws_superengine_version`, or null.
2. Absent, or the client has no Vault access yet? Say it once in plain words:
   the engine runs on its built-in reference library, which works fine but does
   not get the newest patterns. **Never block on it** (edge F3).

The 0.3.4 ladder (env `VAULT_API_KEY`, `~/.config/revxl/vault_api_key`, ask the
client to paste a key) is **deleted at 0.4.0**: no shortform skill reads,
resolves, stores or prints a Vault key. If an old file is still on the machine,
leave it alone and say nothing about it.

## Token hygiene (Step 3)

### Token hygiene ... trim connectors you don't need here

Every MCP connector loaded in a workspace spends tokens on **every** message, just
by being available ... whether or not you use it. This plugin ships **no** MCP servers
of its own, so it adds nothing here; the cost comes from other connectors the client
has switched on globally (Drive, Telegram, calendars, CRMs, etc.).

In **this** shortform workspace, the core flow only needs: SocialCrawl (data), the
transcription chain, and the recordings source from Step 4. Offer, in plain words:
*"You've got a bunch of connectors switched on. For reel work you only need a few ... 
want to switch the rest off in this workspace so Claude stays fast and doesn't burn
tokens carrying tools it won't use? You can flip them back on anytime."* Let the user
decide which to keep; never disable anything without confirming. This is advisory ... 
**purely the user's call**, and reversible.

## Voice source ladder (Step 4a)

Walk down until something exists. Tag each found source with a **voice-confidence**
(A/B/C); stamp the brain with the overall confidence so consumers (reel-scripter)
know how hard to lean on the voice.

| Tier | Sources | Detect / pull | Voice-confidence |
|------|---------|---------------|------------------|
| **A ... spoken** | Fathom / Fireflies recordings, podcast, YouTube, webinar/VSL, Loom, voice memos | Fathom or Fireflies MCP available? ask for a podcast/YT handle | **A (high)** ... real cadence + objections + jokes |
| **B ... written-by-them** | their own social captions/reels, sent newsletters, DMs, community posts (Skool/GHL/Telegram), their tweets/threads | **own posts via SocialCrawl (already wired)**; ask for a newsletter export | **B (med)** ... their writing voice + current topics |
| **C ... written-FOR-them** | website, sales/landing pages, course copy | firecrawl the site | **C (low for voice)** ... usually copywriter-written; use for **offer/avatar only** |
| **D ... none yet** | guided interview | see the floor below | floor ... works for everyone |

Rules:
- **Prefer the highest tier present; blend downward.** A spoken source *sets* the
  voice; B/C add offer + topics. **Never let a Tier-C site set the voice** ... that's
  the noise-factor trap; keep them sounding like *them*.
- **Their own social is the no-recordings primary.** SocialCrawl is already wired, so
  with no recordings, pulling their own captions is the lowest-friction *real* voice
  source. Almost everyone has it.
- **Offer/avatar pulls wider than voice** ... also testimonials/reviews (the *avatar's*
  own pain language ... gold), intake forms, an existing brand guide. Tag these as
  offer/avatar inputs, **not** voice.

**The floor (Tier D) ... brand-new owner / nothing to pull.** If A to C come up empty (new
business, no audience, no site), don't dead-end:
1. **Guided interview now** ... the voice skill interviews them (same move as the email
   engine's story intake): voice from their raw answers + offer + avatar from
   structured Q&A. In Cowork/voice it even captures *spoken* voice.
2. **Record going forward** ... turn on call recording (Fathom) from call #1, save voice
   memos. The brain compounds: day-1 thin-but-real → week-4 rich. Ties into the
   freshness heartbeat (4c).
Stamp `voice_confidence: "interview"` so reel-scripter leans conservative until real
sources accumulate.

## Marker fields (Step 6)

`voice_sources` = which source-ladder tiers were found (Step 4a); `voice_confidence`
= the overall tier the brain rests on (`A` spoken → `C` written-for-them → `interview`
floor → `none`). Consumers lean bolder on A, conservative on interview. `brand_brain`
= the living voice/ICP/topics/humor artifact: `present` once the bundled `brand-brain`
skill has built it, `updated_at` its last-build stamp (the freshness clock reads this),
and `refresh` the auto-refresh choice from Step 4c (`scheduled: true` once the user
picks a cadence ... brand-brain is bundled, so the schedule can point at it now).

## Layer 2, suggest before invoking (before Step 0)

If the user's prompt is borderline ... could be a fresh setup or could be a quick
question ... ask first:

> "Looks like you want to set up the shortform superengine ... want me to run the
> full onboarding (detect tools, wire your keys, verify)? It's a one-time thing."

If they explicitly invoke `/onboarding` or clearly ask to set up, skip the ask.

## Runtime install commands (Step 1)

- **Python missing** → stop and point them to python.org (everything downstream needs it).
- **`ftfy` missing** → offer `pip install ftfy`.
- **Node.js missing** → offer to install it (Windows: `winget install OpenJS.NodeJS.LTS`,
  or nodejs.org → LTS installer; Mac: `brew install node`). Don't skip this ... a missing
  Node is a common cause of connectors silently failing to attach later.

> Install or connection hiccup (a tool won't install, a connector won't attach, antivirus
> blocking it)? See [`troubleshooting.md`](troubleshooting.md).

## Transcription detect table (Step 2)

### Detect

| Tier | Probe | Plain meaning |
|------|-------|--------------|
| Fetch (yt-dlp) | `yt-dlp --version` | can download a reel's video/audio + subtitle track |
| Groq | env `GROQ_API_KEY` set? | has a cloud-transcribe key |
| Local Whisper | `python -c "import faster_whisper"` **and** `ffmpeg -version` | can transcribe offline |

## Recommending the second transcriber (Step 2)

- **Has one, not the other** → recommend adding the second now (don't just mention
  it). Example, in beginner voice: *"You've got captions + offline Whisper, so you're
  covered ... but I'd add Groq too. It's a free API key (console.groq.com/keys), super
  fast, and it means you have multiple ways to transcribe, so nothing gets through
  the cracks. Want to grab it now? Takes about a minute."* Accept a "skip" gracefully
  and move on ... recommend, never block.

## The SocialCrawl sign-up walkthrough (Step 3)

**Why the key is exposed to the paying client.** It is the only way they do not
draw down someone else's credits: each client's own key bills each client's own
balance. Never your key, never a shared one.

If no key is found, walk them through getting one. Point them at
[`socialcrawl-setup.md`](socialcrawl-setup.md) ... the
click-path (sign up via the **referral link** `https://www.socialcrawl.dev/?ref=AQNU384G`,
100 free credits → **API Keys** → **Create** → copy the `sc_…` key → paste), a Loom
slot, and the verify calls. (Always hand clients the referral sign-up link, not a bare
socialcrawl.dev.)

## Optional services (Step 3)

| Service | What to do |
|---------|-----------|
| Groq | Already handled in Step 2 if they chose it (cloud transcription). |
| Firecrawl | Open-web research (client website positioning). If the `firecrawl` CLI is installed + authed, note it; else mention it's optional and skip. |
| NotebookLM | Only if they use it for creator harvests. Hand off to its own installer; don't configure here. |

## Why the brand voice matters (Step 4)

The reel scripts come out in the **client's brand voice**, which lives at
`~/.claude/revxl/<brand>/voc/`. The voice isn't a one-time form ... it's a **living
brand brain** built from the client's **own words, wherever they live**: their tone,
*who they help* and *the pains they help with*, the **topics** they're on right now,
and the **jokes that actually land**. Onboarding only **wires the sources and the
cadence** ... the dedicated voice skill does the mining.

Two different needs, different best-sources:
- **Voice** (how they sound) → best from *spoken* or *written-by-them*.
- **Offer + avatar** (what they sell, who they help, the pains) → can come from
  anywhere, even a form.

## Why the brain needs a refresh cadence (Step 4c)

A brand brain goes stale: tone drifts, and ... more importantly ... the **topics** your
clients raise change week to week. A reel built off a 3-day-old hot objection lands;
one built off month-old topics doesn't. So offer to keep it fresh automatically:

- **Cowork client** → offer a **scheduled task** that re-mines recent recordings on a
  cadence. Ask their slot: *"Friday night, Monday morning, or a time you pick?"*
- **Code client** → offer a **routine / cron** (Windows Scheduled Task or `/schedule`)
  on the same cadence.
- Target: **never more than 6 to 7 days stale.**

## Detecting socialcrawl-superengine (Step 8)

Detect the install by EITHER that marker OR a directory matching
`~/.claude/plugins/cache/*/socialcrawl-superengine/` (an installed-but-never-run copy has no
marker). To install it, the client asks Claude to add the RevXL marketplace
(`joeoliveimpact/revxl-marketplace`) and install `socialcrawl-superengine` from it; Claude
adds the marketplace and installs the plugin, and the client types nothing.
When it is installed, the plays are run by invoking its `research-plays` skill by
name (`socialcrawl-superengine:research-plays`): a cross-plugin play is run by
invoking the other plugin's skill by its qualified name, never by re-implementing
it here.

## House notes

- Idempotent: safe to re-run; Step 0 routes to sub-modes if already set up.
- No private infrastructure anywhere ... the transcription chain is fully portable
  (Groq + local Whisper in parallel; `yt-dlp` for the harvest fetch).
- House pattern: detect → offer-install → wire → write marker → verify → activate.

## The v2 placeholder (Step 5)

v2 adds a content-loop (calendar + Metricool scheduling/measurement, tier-gated).
Nothing to configure now. Just leave the marker shape forward-compatible (Step 6
includes a `tier` field set to `unknown`) so the v2 Metricool step drops in clean.

## What to say about socialcrawl-superengine (Step 8)

Then check `~/.claude/socialcrawl-superengine/.superengine`: if present, add ... *"You also
have the SocialCrawl Superengine installed: deep research plays (audience voice mining,
competitor ad recon, AI-visibility audits) are available on top."* If absent, add one
line ... *"Optional: the `socialcrawl-superengine` plugin from the same marketplace adds
deep research plays (VoC mining, ad recon, audits)."* ... and move on.
