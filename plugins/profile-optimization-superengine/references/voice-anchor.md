# Voice Anchor... write the coach's profile copy in the coach's voice

> The audit skills write copy the coach will paste as their own... bio options, cover CTA, About mini-sales letter, Highlight names, pinned-post captions. That copy has to sound like THIS coach, not a template. This file governs how to capture and prefer their real voice. No voice profile ships filled in.

## Environment gate FIRST (chat has no persistent filesystem)
Reuse the tier established by `profile-start` or the audit skill's Step 1.5:
- **Cowork / Code tier:** a filesystem persists... the shared brand brain and workspace guides below are available.
- **Claude.ai Chat tier:** NO persistent user filesystem. Do not read or build a brain. Capture voice inline for THIS session only (ask for 2-3 writing samples... a caption, a DM, a voice-note transcript... and mirror them). Tell the coach the persistent voice brain needs the Claude desktop app or Claude Code.

## Detect, then prefer (Cowork / Code)
Before extracting, check in this order... first hit wins, PREFER it over the interim process below:
1. **The shared brand brain:** `~/.claude/revxl/<brand>/voc/voice-guide.md` (written by the bundled `brand-brain` skill; cross-engine, per the VoC contract). On read, compute `days_since_update` from the stamp; if >7 days, surface the age and offer a quick brand-brain refresh ONCE... never gate the audit on it.
2. A path in `{{BRAND_VOICE}}`, or a workspace voice guide like `output/data/branding/voice-guide*.md`.

No hit on either... offer to build the durable, cross-engine brain with `brand-brain`, or capture a couple of voice cues inline and proceed. Never dead-end the audit on a missing brain.

## Interim extraction (fast, when no brain exists)
Audit whatever the coach already has. No transcript is required.
1. **Sample captions, posts, or DMs the coach WROTE.** Fastest, best signal.
2. **Call recordings or transcripts**, if they exist. Mine the coach's own turns only.
3. **Voice Q&A fallback.** If no samples: ask 3-4 questions (how they talk, words they use, words they would never use, signature phrases) and build a mini profile for the session.

Catalog and reuse: cadence (sentence length, rhythm), vocabulary (the words they actually use), signature phrases, and stance (how they position, how they show empathy).

## The rule
Write every bit of coach-facing copy in the COACH's voice, not the framework's. If any coach could have posted it, it failed. The profile audit still enforces the frameworks (character caps, single link, amplified CTAs, keyword consistency)... voice is the layer on top, not a licence to break a spec.

## Privacy
A coach's captured voice is private (one brain per brand, and only where a filesystem persists). Never ship a coach's filled-in voice profile inside any plugin.
