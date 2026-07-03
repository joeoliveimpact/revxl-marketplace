# Voice Anchor — Framework (extract and apply a coach's voice)

> The METHOD for capturing a coach's real voice and writing in it, not anyone's stored voice profile. Each coach's voice is captured at setup (and, when a standalone voice skill exists, written to a reusable per-workspace voice guide). This framework governs how. No voice profile ships filled in.

## Detect, then prefer
Before extracting, check in this order — first hit wins, PREFER it over the interim process below:
1. **The shared brand brain:** `~/.claude/revxl/<brand>/voc/voice-guide.md` (written by the bundled `brand-brain` skill; cross-engine, per the VoC contract). If present but >7 days stale, the brand-brain skill may offer a quick refresh first.
2. A path in `{{BRAND_VOICE}}`, or a workspace voice guide like `output/data/branding/voice-guide*.md`.

No hit on either → run the interim extraction below, and suggest `brand-brain` for the durable, cross-engine version.

## Extract: the Digital Twin profile (captured ONCE at setup, not per email)
Audit whatever the coach already has. No transcript is required.
1. **Sample emails or posts the coach WROTE.** Fastest, best signal.
2. **Call recordings or transcripts**, if they exist. Mine the coach's own turns.
3. **Voice Q&A fallback.** If no samples: ask 4-5 questions (how they talk, words they use, words they would never use, signature phrases) and build a mini profile.

Catalog and reuse:
- **Cadence:** sentence length, rhythm, where they pause.
- **Vocabulary:** the words they actually use, including the rough ones if on-brand.
- **Signature phrases and analogies:** reuse them verbatim where they fit.
- **Stance:** how they position against competitors, how they show empathy, the beliefs they repeat.

## The edge dial (`{{VOICE_EDGE}}`): MATCH it, never sanitize
A brand's edge is a SETTING, not a risk to flag. Set once, write TO the dial.
- **vanilla:** clean, professional, no profanity or innuendo, gentle on enemies. Corporate-safe.
- **conversational** (default): warm, human, light humor, mild opinions. Most coaches.
- **spicy:** opinionated, polarizing, self-deprecating, occasional mild language, names enemies.
- **locker-room:** unfiltered, crude humor and innuendo OK, hard polarization, shock opens, emoji, profanity-rhythm (clean the literal words only if the coach wants). The differentiation IS the edge.

Rules:
- NEVER soften below the set level or add disclaimers a coach at that dial would not write. Polarization is Ben Settle's core formula. At spicy/locker-room, lean INTO enemy-framing, self-roast, shock, and infotainment devices.
- Do NOT raise a brand-safety or professionalism flag on edge the coach has dialed in. That is the coach's decision, already made. Only flag a genuine factual or legal problem (for example false scarcity), never vibe.
- Edge is independent of `{{EXPLANATION_LEVEL}}` and `{{TEACH_MODE}}` (you can be locker-room AND teach plainly).

## Voice principles (what makes copy sound like a real person, not a template)
- **Conversational connectors.** Rewrite the joints of the text with spoken phrases ("Fact is...", "And guess what?", "Then it hit me..."). This disrupts corporate-speak and builds subconscious trust.
- **Warmth before competence.** Establish relatability, empathy, or shared humor to disarm the reader BEFORE proving authority. People judge "is this person on my side" before "can they actually help me."
- **You, not I/we.** Flip the pronoun ratio toward "you" and "your." Copy about the coach forces the reader to check whether they relate; direct address triggers tribal self-selection.
- **Lowest cognitive load.** Write at a 5th-to-6th grade reading level, active voice. Read it aloud to kill awkward phrasing. If a busy reader spends half a second parsing, they disengage.
- **Name the REAL pain.** The raw, often shameful truth (the exhaustion, the shame of inconsistency), not the polite public symptom. Naming real pain creates immediate emotional safety.
- **Plain-text illusion.** Strip the design until it reads like a left-aligned text letter from a trusted colleague. One sentence per line, paragraphs of 2-3 sentences, contractions, natural fragments. Plain text also lands in the primary inbox better than glossy HTML.

## The rule
Write every email in the COACH's voice, not the framework's. If any coach could have sent it, it failed. These are BROADCAST emails (one set, sent to everyone on the trigger), so specificity comes from naming the avatar's shared pains sharply in the coach's words, NOT from individual-prospect facts. Sound like THIS coach, speak to THIS niche's known wounds, personalize only via merge tokens.

## Privacy
A coach's captured voice and stories are private (one profile per workspace). Never ship a coach's filled-in voice profile. This framework and the coach's own `${CLAUDE_PLUGIN_DATA}` are separate things.
