# Story Bank — Framework (source, bank, match, and safely use REAL stories)

> This is the METHOD, not a fill-in template and not anyone's stored stories. Each coach's actual stories are captured at runtime by `email-add-stories` and persisted to `${CLAUDE_PLUGIN_DATA}` (one private bank per workspace/brand). They never live in this file and never ship. Story-driven generators read the coach's bank; this framework governs how that bank gets built and used.

## Why a bank, not invention
Real beats invented, every time. Audiences are allergic to polished marketing speak and respond to raw, authentic human connection. AI cannot fabricate that, so the generators pull from the coach's REAL material instead of making things up. If there is nothing real to pull, the honest move is to say the output will be generic and ask for one real moment, never to invent one.

## Sourcing: fill from BOTH wells, always (not either/or)
A sequence is many emails, so it needs many real stories. Draw from both wells every run, then combine.

**1. story-intake Q&A** (the coach's everyday/business stories). The elicitation method:
- **Pick people, not projects.** Do not audit deliverables, specs, or timelines. Center the human and the turning point.
- **Conversational flow, not a rigid questionnaire.** Let the coach wander and speak freely. Raw doubts, emotional turning points, and the moment they almost quit surface when they are not boxed into a form.
- **Extract the emotional center.** Find the exact crisis or decision that changed everything. Prompts that work: "a time you took a real risk or almost gave up," "an unexpected failure or challenge recently," "the biggest personal or business lesson lately."
- **Keep a rolling story log.** Mundane daily moments that surprise, delight, or challenge the coach become assets later.

**2. Transcripts** (coach turns). Mine the COACH's side of recent calls for stories, analogies, signature bits, and hot takes they already say out loud. Same mechanism as VoC, but VoC mines PROSPECT turns for pains while this mines COACH turns for stories.

**3. (optional) The coach's own content, DMs, texts.** Texts to friends are especially rich: real voice plus real story.

## Story engines (match a real story to a structure)
The full engine taxonomy and per-campaign dosing live in `${CLAUDE_PLUGIN_ROOT}/references/story-engines.md`. Quick map: Loss & Redemption, Us-vs-Them, Analogy/Seinfeld, Vulnerability / Attractive Character, Third-Person Proof, Secret-Telling/POV, Before & After, Amazing Discovery. Vulnerability and Controversy/POV are the highest-trust and highest-risk engines: they only work on REAL material, never manufactured edge.

## The Bridge (story to point to offer, never forced)
Any real story connects to the offer in three moves:
- **Tell it.** First person, start in the middle of the action, descriptive. Do not telegraph the product yet.
- **Make the lesson.** State the broader, inarguable point of the story.
- **Connect the dots.** One or two transition lines that bridge the moral to the coach's mechanism or offer.

## How a generator uses the bank
1. READ the coach's bank before writing any story-driven email.
2. Match a `fresh` entry to the email's engine/storyline.
3. Write the proven framework AROUND the real story. Keep the coach's real details, in their voice.
4. Mark the entry `used` (and where) so it is not reused stale.
5. Empty, thin, or stale bank: run `email-add-stories` (or a quick top-up) FIRST. If the coach gives nothing and no transcripts exist, tell them the emails will be generic without real input and ask for at least one real moment. Do NOT fabricate.

## Safety and privacy (non-negotiable)
- Real names (family, clients) and private specifics (legal, financial, health, relationship, custody) are PRIVATE. Archetype them in any broadcast output ("my family," "my kid," "a coach I work with") unless the coach explicitly approves naming, in their own framing.
- A coach's one-off approval to use a story inside a specific email is NOT approval to publish that story anywhere else. Honor the principal's framing. Never escalate the edge or expose more than they themselves wrote.
- Broadcast-safe means no individual-prospect facts. Specificity comes from the avatar's shared pains plus the coach's voice, not from private data.

## Freshness
Rotate so the list does not see the same story twice quickly. A used story can be reworked for another campaign later. Keep a few fresh entries per engine on hand.

## What the bank records (captured by story-intake into the coach's private bank)
Per story, the bank holds: a short label, the engine/storyline, the raw story in the coach's own words, a status (`fresh` or `used` and where), and an output-safety note flagging anything that must be archetyped. This record lives in the coach's `${CLAUDE_PLUGIN_DATA}` bank, not in this framework.
