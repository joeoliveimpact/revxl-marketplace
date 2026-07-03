# Artifacts — exact output schemas

All five live at `~/.claude/revxl/<brand>/voc/`. Consumers parse these shapes — keep them stable. Every file opens with a stamp block:

    ---
    brand: <brand>
    updated_at: <ISO date+time>
    ---

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

## business-config.md
Brand-level, shared across engines: avatar definition (who, in their words), offer(s) + promise + price point (if the user supplies it — never store pricing uninvited), enemy/positioning, proof assets. Tokens other engines map in: avatar pains, avatar enemy, offer framing.

## signature-bits.md
Per bit: line (verbatim) · setup/context · reaction evidence (quoted) · frequency + where · tag (`personal-signature|topical-to-niche|evergreen`) · status (`candidate|canon`). Candidates sit at the top awaiting thumbs-up.

## weekly-content-bank.md
Fast shelf, 7-day TTL, every entry dated. Sections: **This week's themes** · **Hot objections** · **Questions coming up** · **Topical jokes** · **Topical content seeds**. On refresh: expire >7-day entries, write the new week. Consumers treat this as the topical layer for content cross-referencing.

## Workspace-level (NOT at the shared path)
- `voc/transcripts/<bucket>/` — raw source files per bucket (sales/client/group/other).
- `voc/index.md` — per bucket: last-pull timestamp · source (local/Fathom/Fireflies/DM-export/social) · #items mined · decline count · last-offered. The freshness + nudge record.
- "Workspace" = the directory the skill is invoked from. **No workspace context** (standalone/headless run): keep the index at the shared brand path instead (`~/.claude/revxl/<brand>/voc/index.md`) — it's small and non-sensitive; only raw transcripts must stay out of the shared path.
