# Extraction ... one ingestion pass, two shelves

Split everything you extract by SHELF LIFE, not by source. Evergreen → brain files. Topical → weekly-content-bank (7-day TTL).

## Voice (coach turns + tier-B written)
Catalog per the consumer-standard shape (email engine's voice-anchor parses these):
- **Cadence:** sentence length, rhythm, where they pause.
- **Vocabulary:** words they actually use (including the rough ones if on-brand) + words they'd never use.
- **Signature phrases + analogies:** verbatim, reusable as-is.
- **Stance:** how they position against competitors, how they show empathy, beliefs they repeat.
- **Edge read:** where they sit on vanilla → conversational → spicy → locker-room. Note it; the consumer's edge dial decides how it's applied.

**Register-tag every voice entry:** `spoken-call` | `written-content` | `spoken-video`. Consumers pick their register (IG scripting wants written/spoken-video; email wants whatever fits). Same guide, source-tagged.

## VoC (prospect turns + DM prospect side + testimonials)
- Extract pains, desired outcomes, objections, and VERBATIM phrases ... their exact words, not paraphrase. Verbatim means exact words; mark transcription gaps/elisions with `[...]`, never bridge them silently.
- Dedup, then **rank by frequency** (a pain heard in 9 of 12 calls outranks one heard once). Frequency = evidence. **Minimum-evidence rule:** with fewer than 3 independent sources, mark all ranks `provisional (n=<count>)` ... within-one-call frequency is not a pattern. **Tiebreak within a provisional set** (formalized so two operators rank the same inputs the same way): multi-client attestation on-call > in-call repetition > single mention.
- Tag each entry: bucket (sales/client/group/other) + source. Keep the bank ENGINE-AGNOSTIC ... it powers IG hooks exactly like email subject lines; no email-only assumptions in its shape.
- **Client-of-operator calls** (the operator coaching the brand owner): the brand owner's OWN pains about her business are NOT her avatar's VoC. Store avatar VoC only where she explicitly describes her audience. Her own experience MAY be kept in a clearly labeled **Mirror Language (hypothesis)** subsection ... low-confidence, useful where coach and avatar overlap ... never merged into the ranked bank.

## Content seeds
- **Evergreen seeds** (recurring pains, core beliefs, signature analogies → always-valid content angles) → the Evergreen Content Seeds section of voc-profile.md, each seed pointing at its evidence.
- **Topical seeds** (a hot objection from Tuesday's call, this week's recurring question, a timely joke) → weekly-content-bank.md, dated. A 3-day-old call about a hot objection should surface as a content idea THIS week, then age out.

## Humor
Route candidates to ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/signature-bits.md scoring. Evergreen bits → signature-bits.md (pending canonization). Topical jokes → weekly-content-bank.md.

## Why mining MANY sources beats one
One transcript = one perspective (overfits to that person). Many calls surface the SHARED pains/objections/desires as patterns ... plus real prospect language at frequency. Voice-of-Customer copy (the audience's own words, frequency-backed) converts better; it IS the "avatar shared pains" the broadcast model runs on.
