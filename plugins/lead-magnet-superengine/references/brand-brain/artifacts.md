# Artifacts — exact output schemas

All five live at `~/.claude/revxl/<brand>/voc/`. Consumers parse these shapes — keep them stable. Every file opens with a stamp block:

    ---
    brand: <brand>
    updated_at: <ISO date+time>
    source_count: <n>
    provisional: <true|false>
    ---

`source_count` = independent sources that contributed (a call, a post corpus, a newsletter batch each count once — NOT items within one source). `provisional: true` whenever `source_count < 3`: rankings and voice reads are hypotheses from thin evidence, and consumers must treat them as such (don't lean bold on a provisional brain regardless of `voice_confidence`). These two keys are ADDITIVE — existing keys and enums are unchanged; older brains gain them lazily on next touch (see refresh).

## voice-guide.md
Stamp block adds: `voice_confidence: A|B|C|interview` (highest tier that contributed VOICE) and `registers_present: [spoken-call, written-content, spoken-video]`.
Sections (the shape email's voice-anchor expects):
- **Cadence** — sentence length, rhythm, pauses. Each entry register-tagged.
- **Vocabulary** — words they use / words they'd never use. Register-tagged.
- **Signature phrases + analogies** — verbatim, with source refs.
- **Stance** — positioning vs competitors, empathy style, repeated beliefs.
- **Edge read** — observed position on vanilla→locker-room (the consumer's dial decides application).

## voc-profile.md
Engine-agnostic. Sections:
- **Pains** / **Desired outcomes** / **Objections** — each entry: verbatim phrase(s) · frequency count · bucket tag · source. Ranked by frequency, highest first.
- **Verbatim language bank** — raw prospect phrasing worth reusing anywhere (subject lines, hooks, captions).
- **Evergreen Content Seeds** — always-valid content angles, each pointing at its evidence (the pain/belief/analogy it derives from).
- **Mirror Language (hypothesis)** — optional, clearly-labeled subsection: the brand owner's OWN client-experience phrasing that plausibly mirrors her market (see extraction). Low-confidence by definition. **Consumer guard: never quote Mirror Language entries as avatar VoC** — they are the coach's words about herself, not the audience's words. Never merged into the ranked sections above.

## business-config.md
Brand-level, shared across engines: avatar definition (who, in their words), offer(s) + promise + price point (if the user supplies it — never store pricing uninvited), enemy/positioning, proof assets. Tokens other engines map in: avatar pains, avatar enemy, offer framing.

## signature-bits.md
Per bit: line (verbatim) · setup/context · reaction evidence (quoted) · **evidence strength (`explicit|riff-along`)** · frequency + where · tag (`personal-signature|topical-to-niche|evergreen`) · status (`candidate|canon`). Candidacy requires the deployability gates (portability + self-contained setup); canon requires recurrence across ≥2 independent sources. Canonization is currently PARKED (no consumer reads this file) — candidates accumulate silently; no review ceremony.

## weekly-content-bank.md
Fast shelf, 7-day TTL, every entry dated. Sections: **This week's themes** · **Hot objections** · **Questions coming up** · **Topical jokes** · **Topical content seeds**. On refresh: expire >7-day entries, write the new week. Consumers treat this as the topical layer for content cross-referencing.

## Workspace-level (NOT at the shared path)
- `voc/transcripts/<bucket>/` — raw source files per bucket (sales/client/group/other).
- `voc/index.md` — per bucket: last-pull timestamp · source (local/Fathom/Fireflies/DM-export/social) · #items mined · decline count · last-offered. The freshness + nudge record.
- "Workspace" = the directory the skill is invoked from. **No workspace context** (standalone/headless run): keep the index at the shared brand path instead (`~/.claude/revxl/<brand>/voc/index.md`) — it's small and non-sensitive; only raw transcripts must stay out of the shared path.
