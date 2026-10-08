---
name: stories-superengine:stories-quote-card
description: "Render one of the coach's own lines as an X/Twitter-style post card (their photo, name, handle, the words, the real post time) for an Instagram/Facebook story, a 3:4 carousel slide or a square post. Trigger phrases include \"quote card\", \"make this a tweet graphic\", \"post card look\", \"tweet look story\", \"put this line on a card\"."
---

> **Compaction guard:** if this conversation was compacted since this skill loaded, invoke it again.

**Output contract** — `stories/<SET NAME> <MM.DD.YY>/NN - <short name> - story.png` (or `- carousel` /
`- square`), plus `copy.md` with the final words. Nothing posts from here; approved cards go to
`stories-schedule`.

## Load
- `${CLAUDE_PLUGIN_DATA}/business-config.md` (placeholders → `stories-setup` first)
- `${CLAUDE_PLUGIN_ROOT}/references/quote-card.md` (every setting, theme picking, line-break rules)

Scripts run with the recorded Python (see `stories-setup`, "Run a script").

## Steps

1. **Words.** The coach's own line (from them, a call, a post). Pick the size: `story` for stories.
   One card per line; a week of cards is a set, one per day.
2. **Suggestions, not rewrites.** Offer numbered suggestions they can accept or skip (spelling, a line
   past the 220-character soft cap → split into two cards). Wording options only when they ask: three
   per card (light polish, sharper, keep as is) with the full wording in each option's `description`.
3. **Line breaks.** Apply quote-card.md's rules. Only add breaks; never change, cut or reorder words.
   Show their original next to the broken version.
4. **Stamp = the real post time.** No time set yet → ask the coach when it goes out. `meta=8:00 AM · Oct 9, 2026`. Render only once the time is fixed;
   re-render if it moves.
5. **Render** into the set folder. Copy the avatar from `~/.claude/revxl/<brand>/stories/avatar.jpg`
   into the folder first (when it exists).
   `render_card.py "<set folder>" "size=story&layout=card&storybg=cm-3&name=<{{DISPLAY_NAME}}>&handle=<{{IG_HANDLE}}>&check=<{{VERIFIED_BADGE}}>&text=<words>&meta=<time>" "<set folder>/01 - <name> - story.png"`
   - Add `&avatar=avatar.jpg` ONLY when that file is in the folder. No photo → leave `avatar` out and the card shows initials.
   - Type line breaks as a literal `\n`. An `&` inside the words is fine.
   - Vary the `cm-1`…`cm-7` wash across a week; never a generated scene photo behind a card.
   - FONT / FIT / SETUP failure = no PNG. Fix the cause and render again.
6. **Show it.** Open the PNG, check it by eye, show the coach, ask for go → `stories-schedule`.

## Never
- Render another person's name or handle as the author, or a blue check the coach doesn't have.
- Add fake like, repost or view counts.
