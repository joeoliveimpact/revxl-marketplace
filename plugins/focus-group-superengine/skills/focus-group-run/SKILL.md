---
name: focus-group-run
description: Run a synthetic focus group on a marketing artifact (name line, bio, hook, thumbnail/title, email, landing copy, offer, ad — or custom). Loads a persona pack built by focus-group-setup, picks a depth × temperature, estimates tokens and confirms, then runs a persona SWARM in Workflow subagents → a COUNCIL verdict (dual-axis attention/convert scores, behavioral funnel, objections, polarizing + mood-adjusted + sycophancy reads, verbatim quotes), and writes a results doc. Trigger when the user wants to "run a focus group", "test this name/bio/hook/thumbnail/offer", "A/B this with the panel", "what would my audience think of X", or runs /focus-group-run. Multi-agent — needs the user's go before any deep/hyperreal run.
---

# Focus Group — Run (test an artifact)

Consumes a persona pack (the portable IP from `focus-group-setup`) and returns a council verdict. The swarm runs in **Workflow subagents** so the main chat only ever sees the verdict, not 50–180 individual reactions.

> **What it IS:** relative comparison (A vs B vs C), objection-surfacing, dud detection, fast directional read.
> **What it ISN'T:** a metrics predictor. Verdicts are directional until calibrated against one real signal (Story poll, real comments). Always say so in the doc.

---

## Step 0 — Locate the pack
- Default: newest `${CLAUDE_PLUGIN_DATA}/persona-pack-*.json`. If several, list them and ask which brand.
- None exists → offer two paths: run `/focus-group-setup` to build a pack grounded in THEIR brand (recommended), or start with the bundled example pack (`${CLAUDE_PLUGIN_ROOT}/references/persona-pack-example-coach-v0.json` — a generic coach/SMB audience; copy it to `${CLAUDE_PLUGIN_DATA}/` before using so their edits persist). Do not invent personas.
- Read the pack. Note `personas.length` (N_available) — the real panel size is capped by the pack until it's scaled (P1).
- **Teach Mode:** read `meta.teach_mode` (default ON if absent). If the user says "teach mode on/off" this session, that overrides the pack for the rest of the session. When ON, follow `${CLAUDE_PLUGIN_ROOT}/references/teach-mode.md` to add plain-English "why" notes in the MAIN thread only (never inside the swarm).

## Step 1 — Artifact intake + type → profile
Get the artifact(s) from the user. **One artifact = its options.** A/B/C = 2–3 options; single = 1 option (still useful for objections/axes).

Auto-detect the type, confirm in one line, load its **profile** (drives the rubric, the `first_action` enum, and the default temperature):

| type | ATTENTION means | CONVERT means | first_action enum | default temp |
|---|---|---|---|---|
| `name`/`profile` | scroll-stop on the name | clarity ("get what they do?") + trust | `scroll_past, tap_profile, follow, share, dm, nothing` | cold |
| `hook`/`reel` | 3-sec stop | keep-watching pull | `keep_watching, swipe_away, like, share, comment, nothing` | hybrid |
| `thumbnail`/`title` | click pull | promise clarity + trust | `click, skip, save, share, nothing` | cold |
| `email` | open-worthiness (subject) | body clarity + trust | `open, reply, delete, unsubscribe, nothing` | warm |
| `funnel`/`landing` | above-fold hook | CTA clarity + trust | `click_cta, read_on, bounce, nothing` | hybrid |
| `offer`/`pricing` | value pop | value-vs-price (CONVERT = worth it?) | `buy_curious, hesitate, reject, nothing` | warm |
| `ad` | stop + intrigue | claim clarity + trust | `click, scroll_past, hide, nothing` | cold |
| `custom` | *(you generate the profile from a 1-line description)* | — | *(you define)* | ask |

If type is ambiguous → ask. If `custom` → write a one-line profile and confirm it.

## Step 2 — Depth × temperature
Two independent axes. **Auto-suggest temperature from the profile's default; user overrides.**

**DEPTH** (rigor/cost — model + nominal panel size; actual = min(nominal, N_available)):
| depth | swarm | council | when |
|---|---|---|---|
| `fast` | Haiku, ~50 | Sonnet | default; directional A/B, quick read |
| `deep` | Sonnet, ~100 | Sonnet | finalists, richer reasoning — **confirm gate** |
| `hyperreal` | mixed (~120 Haiku / 60 Sonnet / few Opus) | Opus | rebrands, launches, flagship offers only — **confirm gate** |

**TEMPERATURE** (who's judging — relationship to the creator; injected as context per persona, NOT separate packs):
- `cold` = strangers scrolling, never heard of you → acquisition assets (name, hook, thumbnail, bio, ad).
- `warm` = already follow/trust you → retention assets (content, offers, email).
- `hybrid` = realistic blend (a Reel hits followers + cold reach at once). New acct ≈ 90/10 cold; established ≈ 70/30.

State the picked combo back: e.g. "Running **fast × cold** (Haiku, 16 panelists, strangers)."

## Step 3 — Token estimate + confirm gate
Estimate before running: `panel × options × per-persona` — **monadic**, so each persona reacts to every option separately (2 options = 2× the calls, 4 options = 4×). Per-persona ≈ Haiku 3–8K · Sonnet 12–25K. Translate to a plain scale:
- **small** (< ~150K) · **notable** (~150–600K) · **heavy** (> ~600K).

Then:
- `fast` → show the estimate, proceed.
- `deep` / `hyperreal` → **require explicit confirm.** Show the estimate and prompt the user to glance at usage first (**Desktop = the app's usage view; terminal = `/status`**) — we can't auto-read quota. Wait for "go".
- This is a multi-agent Workflow → always get the user's go before launching.

## Step 4 — Build + run the Workflow
Take the **engine template below**, replace the four injection markers, and call the `Workflow` tool with the filled script.

**Injection rules (Workflow sandbox has NO filesystem, NO `Math.random`, NO `Date` — everything is baked in):**
1. `__PERSONAS__` → the pack's `personas` array as a JSON literal.
2. `__ARTIFACT__` → `{ type, temperature, options: [{label, text}, ...] }`.
3. `__PROFILE__` → `{ attention_means, convert_means, first_action: [enum...] }` from Step 1.
4. `__CONFIG__` → `{ swarm_model, council_model, temp_context, recognition_suppress }` where `temp_context` is the cold/warm/hybrid sentence, `recognition_suppress` is `true` when options include real/known names or brands (cold name/bio/competitor tests) so fame can't leak in (else `false`), and the models match the depth tier (`haiku`/`sonnet`/`opus`).

Mood is **stratified deterministically** (no RNG) and is the **same within a persona across all options** (controlled A/B). Do not change `MOOD_PATTERN`.

The Workflow returns `{ n, stats, verdict }` — `stats` are the code-computed per-option numbers (means, value10, confidence-weighted, distributions) and `verdict` is the council's qualitative synthesis. You don't parse the raw reactions in the main thread.

## Step 5 — Write the results doc
Write `${CLAUDE_PLUGIN_DATA}/runs/run-NN-<artifact-slug>-MM.DD.YY.md` (next NN in sequence). Include, from the council `verdict`:
- Header: engine v4, depth × temperature, panel size, token actuals if known.
- **Result**: raw pick + distribution AND confidence-weighted pick + distribution (call out if weighting FLIPS the winner = loud minority vs meh majority).
- **Lead with RELATIVE**: rank order + paired deltas first. Label every absolute /10 "uncalibrated — within-run only" — absolutes compress hard under cold+skeptic panels.
- **Dual axis**: attention per option · convert (clarity + trust) per option — never averaged together.
- **Behavioral funnel**: first_action breakdown per option.
- **Emotion mix** (call out % `indifferent`).
- **Polarizing read** (low-convert + high-attention = polarizing winner?).
- **Mood-adjusted read** (is negativity content-driven or clustered in low-mood panelists?).
- **Sycophancy check** (council's flag if sentiment is suspiciously uniform/positive).
- **Top objections** (clustered) + **by-role** read.
- **Recommendation** + **standout verbatim quotes**.
- **Calibration caveat**: directional until checked against a real audience signal.

Then give the user a tight verdict summary in chat (don't dump the whole doc).

- **If Teach Mode is ON** (`meta.teach_mode` or toggled on this session): after the verdict summary, add a short **🎓 Why** block — 1–3 plain-English notes per `${CLAUDE_PLUGIN_ROOT}/references/teach-mode.md`, each tied to what THIS verdict just showed (e.g. why the winner won on attention but the panel split on convert; what the top objection means for the next test). 8th-grade, a line or two each, pick only the concepts that fit this result. **If Teach Mode is OFF, skip this block entirely — output the verdict exactly as today.**

---

## Engine template (v4) — fill the 4 markers, pass as the Workflow `script`

```javascript
export const meta = {
  name: 'focus-group-run',
  description: 'Synthetic focus group (engine v4): each persona reacts to each option in isolation via word-ladders; JS computes the math; council synthesizes a dual-axis verdict',
  phases: [
    { title: 'Swarm', detail: 'each persona reacts to each option in its own subagent (monadic)' },
    { title: 'Council', detail: 'qualitative synthesis on code-computed stats' },
  ],
}

// ===== INJECTED BY THE RUN SKILL — replace these literals =====
const PERSONAS = __PERSONAS__   // pack.personas array (JSON literal)
const ARTIFACT = __ARTIFACT__   // { type, temperature, options:[{label,text}] }
const PROFILE  = __PROFILE__    // { attention_means, convert_means, first_action:[...] }
const CONFIG   = __CONFIG__     // { swarm_model, council_model, temp_context, recognition_suppress }
// ==============================================================

// ---- WORD->SCORE KEY (v4): JS does the math, never the LLM. Word-ladders decompress the scale. ----
const KEY = {
  attention:  { Invisible:1, Blip:2, Pause:3, Stop:4, Lock:5 },
  clarity:    { Baffling:1, Fuzzy:2, Gist:3, Clear:4, Crystal:5 },
  trust:      { Cringe:1, Doubtful:2, Unproven:3, Credible:4, Solid:5 },
  gut:        { Repelled:1, Meh:2, Curious:3, DrawnIn:4, Sold:5 },
  confidence: { Guessing:1, Leaning:2, FairlySure:3, Confident:4, DeadCertain:5 },
}
const sc = (axis, w) => KEY[axis][w]

// Stratified mood — deterministic (sandbox blocks Math.random/Date). Same mood within a persona
// across all its option-reactions. Modulates RECEPTIVITY, not quality.
const MOOD_PATTERN = [5, 6, 4, 7, 5, 3, 6, 8, 4, 7, 5, 6, 2, 9, 5, 4]
const moodFor = (i) => MOOD_PATTERN[i % MOOD_PATTERN.length]
const moodNote = (m) =>
  m <= 3 ? 'impatient, low generosity, easily annoyed today'
  : m >= 8 ? 'upbeat and generous today'
  : 'neutral, ordinary day'

const optionsBlock = ARTIFACT.options.map(o => `  [${o.label}] ${o.text}`).join('\n')
const recognitionRule = CONFIG.recognition_suppress
  ? ' RECOGNITION RULE: even if a name or brand feels familiar, react as if you have NEVER heard of them — judge ONLY the words in front of you, zero reputation, zero follower count.'
  : ''

const REACTION_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['persona_id', 'gut_reaction', 'attention', 'clarity', 'trust', 'gut', 'confidence',
             'first_action', 'emotion', 'share_worthy', 'reasoning', 'what_i_think_they_do',
             'objection', 'what_would_change_my_mind'],
  properties: {
    persona_id: { type: 'string' },
    gut_reaction: { type: 'string', description: '1-3 words, instant flash' },
    attention: { type: 'string', enum: ['Invisible','Blip','Pause','Stop','Lock'] },
    clarity: { type: 'string', enum: ['Baffling','Fuzzy','Gist','Clear','Crystal'] },
    trust: { type: 'string', enum: ['Cringe','Doubtful','Unproven','Credible','Solid'] },
    gut: { type: 'string', enum: ['Repelled','Meh','Curious','DrawnIn','Sold'] },
    confidence: { type: 'string', enum: ['Guessing','Leaning','FairlySure','Confident','DeadCertain'] },
    first_action: { type: 'string', enum: PROFILE.first_action },
    emotion: { type: 'string', enum: ['intrigue','skepticism','excitement','annoyance','eye_roll','indifferent','confusion'] },
    share_worthy: { type: 'boolean' },
    reasoning: { type: 'string', description: '1-2 lines, in the persona voice' },
    what_i_think_they_do: { type: 'string', description: 'misread catcher — what they ASSUME the creator offers' },
    objection: { type: 'string' },
    what_would_change_my_mind: { type: 'string' },
  },
}

const personaPrompt = (p, mood, opt) => `You are a REAL person scrolling — NOT a focus-group judge. React as yourself.

WHO YOU ARE:
- ${p.name}, ${p.age}, ${p.segment}, ${p.stage}${p.ai ? `, AI level: ${p.ai}` : ''}
- skepticism: ${p.skepticism} · main pain: ${p.pain} · lives on: ${p.platform}
- your voice: ${p.voice}
- your assigned lens: "${p.role}" — a LENS, not a script (a skeptic can still like something; a fan can still bounce)

YOUR MOOD RIGHT NOW: ${mood}/10 — ${moodNote(mood)}. Mood changes how RECEPTIVE you are (patience/generosity), NOT the quality of what you see.

CONTEXT: ${CONFIG.temp_context}${recognitionRule}

YOU'RE REACTING TO a ${ARTIFACT.type}. ATTENTION here = ${PROFILE.attention_means}. CONVERT here = ${PROFILE.convert_means}. You see ONLY this ONE — judge it on its own:
"""
${opt.text}
"""

RATE YOUR GUT IN WORDS — pick the ONE word per axis that matches what you ACTUALLY felt. No numbers:
ATTENTION (does it stop you?): Invisible · Blip · Pause · Stop · Lock
  Invisible=never saw it · Blip=registered, moved on · Pause=slowed a beat · Stop=stopped to take it in · Lock=stopped everything, "this is for me"
CLARITY (do you get what they do/offer?): Baffling · Fuzzy · Gist · Clear · Crystal
  Baffling=no idea · Fuzzy=vague guess · Gist=roughly get it · Clear=I get it · Crystal=instant, exact
TRUST (do you believe it?): Cringe · Doubtful · Unproven · Credible · Solid
  Cringe=scam/ick · Doubtful=skeptical · Unproven=neutral, no signal · Credible=I buy it · Solid=I'd pay them
GUT (overall pull): Repelled · Meh · Curious · DrawnIn · Sold
  Repelled=push away · Meh=nothing · Curious=mild interest · DrawnIn=want more · Sold=yes, in
CONFIDENCE (how sure is THIS read?): Guessing · Leaning · FairlySure · Confident · DeadCertain

Be honest: most weak/generic content lands Blip / Meh / Unproven. But if it genuinely Locks or Repels YOU, say so — use the ends of the ladder when you truly feel them, grounded in WHO YOU ARE.

Then: first_action (what you'd ACTUALLY do next: ${PROFILE.first_action.join(', ')}), emotion, share_worthy, what_i_think_they_do, objection, what_would_change_my_mind.

Return ONLY the structured object; persona_id = "${p.id}".`

const COUNCIL_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['raw_pick','raw_distribution','weighted_pick','weighted_distribution',
             'attention_axis','convert_axis','behavioral_funnel','emotion_mix',
             'polarizing_read','mood_adjusted_read','sycophancy_check',
             'top_objections','by_role','recommendation','standout_quotes'],
  properties: {
    raw_pick: { type: 'string', description: 'option with the highest computed value10' },
    raw_distribution: { type: 'string', description: 'value10 per option (verbatim from stats)' },
    weighted_pick: { type: 'string', description: 'option with the highest confidence_weighted_gut' },
    weighted_distribution: { type: 'string', description: 'confidence_weighted_gut per option; note if it FLIPS the raw winner' },
    attention_axis: { type: 'string', description: 'mean_attention per option (verbatim)' },
    convert_axis: { type: 'string', description: 'mean_clarity AND mean_trust per option, SEPARATE (verbatim)' },
    behavioral_funnel: { type: 'string', description: 'first_action distribution per option (verbatim)' },
    emotion_mix: { type: 'string', description: 'emotion counts; explicitly call out % indifferent' },
    polarizing_read: { type: 'string', description: 'any option high-attention + low-convert = polarizing? if not, say so' },
    mood_adjusted_read: { type: 'string', description: 'is negativity content-driven, or clustered in low-mood (<=3) panelists?' },
    sycophancy_check: { type: 'string', description: 'flag + down-weight if sentiment is suspiciously uniform/positive; name the likely cause' },
    top_objections: { type: 'array', items: { type: 'string' }, description: 'clustered, most common first' },
    by_role: { type: 'string', description: 'how enthusiasts vs fence-sitters vs skeptics vs haters split' },
    recommendation: { type: 'string' },
    standout_quotes: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['persona_id', 'quote'],
        properties: { persona_id: { type: 'string' }, quote: { type: 'string' } },
      },
    },
  },
}

const councilPrompt = (stats, reactions) => `You are the focus-group council. Engine v4: ${reactions.length} grounded reactions to a ${ARTIFACT.type}; every (persona × option) was an ISOLATED monadic reaction. Personas picked WORDS on anchored 5-rung ladders (never numbers); the means are ALREADY COMPUTED in code from a fixed word->score key — USE THEM VERBATIM, never recompute an average.

THE OPTIONS:
${optionsBlock}

COMPUTED STATS (objective — value10 is the 1-10 headline):
${JSON.stringify(stats, null, 1)}

RAW REACTIONS (words + text, tagged by option/mood/role):
${JSON.stringify(reactions, null, 1)}

Produce the verdict (math done). Hard rules:
- LEAD with relative ranking + paired deltas using the provided value10 numbers. Report absolutes as SECONDARY, labeled "uncalibrated — valid only WITHIN this run" (cold+skeptic panels compress absolutes).
- Report BOTH the raw (value10) pick and the confidence-weighted (confidence_weighted_gut) pick. If weighting flips the winner, that's loud-minority-vs-meh-majority — say so.
- Keep ATTENTION and CONVERT (clarity, trust) on SEPARATE axes. Never blend them.
- Polarizing read: an option can lose on convert but win on attention — surface that combo.
- Mood-adjusted read: check whether negativity clusters in low-mood (<=3) panelists vs content-driven.
- Sycophancy guard: if sentiment is suspiciously uniform/positive, FLAG it, down-weight it, name the likely cause.${CONFIG.recognition_suppress ? '\n- Recognition check: flag any option whose trust looks like leaked fame despite the suppression rule.' : ''}
- Cluster objections; give the by-role split; pull standout VERBATIM quotes.`

phase('Swarm')
const tasks = []
for (const opt of ARTIFACT.options) {
  PERSONAS.forEach((p, i) => tasks.push(() =>
    agent(personaPrompt(p, moodFor(i), opt), {
      label: `${opt.label}:${p.id}`,
      phase: 'Swarm',
      model: CONFIG.swarm_model,
      schema: REACTION_SCHEMA,
    }).then(r => r && ({ ...r, option: opt.label, mood: moodFor(i), role: p.role, segment: p.segment }))
  ))
}
const reactions = (await parallel(tasks)).filter(Boolean)

// ---- JS does ALL the math (objective; no LLM arithmetic) ----
const round2 = (x) => Math.round(x * 100) / 100
function statsFor(rs) {
  const n = rs.length || 1
  const mean = (axis) => rs.reduce((s, r) => s + sc(axis, r[axis]), 0) / n
  const att = mean('attention'), cla = mean('clarity'), tru = mean('trust'), gut = mean('gut')
  const value10 = (att + cla + tru + gut) / 4 * 2
  const cwNum = rs.reduce((s, r) => s + sc('gut', r.gut) * sc('confidence', r.confidence), 0)
  const cwDen = rs.reduce((s, r) => s + sc('confidence', r.confidence), 0) || 1
  const dist = (key) => rs.reduce((o, r) => { o[r[key]] = (o[r[key]] || 0) + 1; return o }, {})
  return {
    n: rs.length, value10: round2(value10), confidence_weighted_gut: round2(cwNum / cwDen),
    mean_attention: round2(att), mean_clarity: round2(cla), mean_trust: round2(tru), mean_gut: round2(gut),
    first_action: dist('first_action'), emotion: dist('emotion'),
    dist_attention: dist('attention'), dist_clarity: dist('clarity'), dist_trust: dist('trust'), dist_gut: dist('gut'),
  }
}
const byOption = {}
for (const opt of ARTIFACT.options) byOption[opt.label] = statsFor(reactions.filter(r => r.option === opt.label))
const vals = Object.values(byOption).map(s => s.value10)
const stats = {
  per_option: byOption,
  value_rank: Object.entries(byOption).sort((a, b) => b[1].value10 - a[1].value10).map(([k, v]) => `${k}: ${v.value10}`),
  weighted_rank: Object.entries(byOption).sort((a, b) => b[1].confidence_weighted_gut - a[1].confidence_weighted_gut).map(([k, v]) => `${k}: ${v.confidence_weighted_gut}`),
  value_band: round2(Math.max(...vals) - Math.min(...vals)),
}

phase('Council')
const verdict = await agent(councilPrompt(stats, reactions), {
  label: 'council',
  phase: 'Council',
  model: CONFIG.council_model,
  schema: COUNCIL_SCHEMA,
})

return { n: reactions.length, stats, verdict }
```

---

## Notes / guardrails
- **Pack is injected, never read at runtime** — Workflow has no filesystem. Same for mood/temperature (baked as literals).
- **Panel size = min(tier nominal, N_available).** The bundled example pack is 16; if the user asks for `deep`/`hyperreal` on a 16-persona pack, warn that the panel is capped at 16 until the pack is scaled (build a bigger pack via `/focus-group-setup`).
- **Monadic cost:** each persona reacts to every option in its OWN call, so calls = panel × options. Factor options into the Step 3 estimate.
- **Models are per-run, set in `CONFIG`** — never change the user's session model.
- **Cold-test caveat:** a name/bio judged without face/content under-scores personality. Note it when temperature = `cold`.
- After a high-stakes verdict, recommend a real-signal calibration check (Story poll / comments) before fully trusting it.
