---
paths:
  - "content/**/*.md"
  - "content/**/*.txt"
description: Rules for drafting, sourcing, and shipping content in this workspace.
---

# Content creation rules

When drafting, editing, or reviewing content in `content/`:

## Voice

1. **Match the workspace owner's documented voice.** If a `brand-voice.md` or similar exists in the workspace, read it before writing. If none exists, ask once and persist the answer in `MEMORY.md`.
2. **No filler.** Do not pad with "in today's fast-paced world", "in conclusion", or other LLM-style scaffolding. Cut hedge words ("just", "really", "very") unless the author uses them deliberately.
3. **Active voice, short sentences, plain verbs.** Long sentences are fine when they earn it.

## Sourcing

4. **No invented facts, stats, quotes, or studies.** If a claim needs a citation and you don't have one, mark it `[CITE NEEDED]` and surface the gap. Do not paper over with confident-sounding text.
5. **Names and proper nouns:** verify spelling against an authoritative source if the author hasn't supplied one.
6. **Distinguish opinion from fact.** Frame opinions as the author's view, not as universal truth.

## Drafting discipline

7. **One draft per file.** Don't paste multiple variants into the same draft — fork the file (`<slug>_v2.md`).
8. **Headlines last.** Headlines tend to lock in framing before the piece is fully shaped. Write a working title, draft the body, then iterate the headline.
9. **Read before publishing.** A draft that has not been read aloud (or by a second pair of eyes) is not ready to publish.

## Publish discipline

10. **Move, don't copy.** When a draft ships, rename it `YYYY-MM-DD_<slug>.md` and move to `content/published/`. Keeping the same content in two places creates a "which is canonical" problem the next time someone edits.
11. **Record where it lives.** If the published piece lives outside this workspace (a CMS, a newsletter platform), put the canonical URL at the top of the published file as a comment.

Violations should be called out in the draft, not hidden.
