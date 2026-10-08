# Quote card — one of the coach's lines as a post-style card

`scripts/render_card.py <job_dir> "<settings>" <out.png>` renders an X-style post card (avatar, name,
handle, text, timestamp). `<job_dir>` holds the avatar and any background photo.

## Settings (URL keys, joined with `&`)

| Key | Values | Default |
|---|---|---|
| `size` | `story` 1080×1920 · `carousel` 1080×1440 · `square` 1080×1080 | `carousel` |
| `layout` | `full` (post fills the frame) · `card` (rounded card on a background) | `full` |
| `theme` | `auto` (picked from what's behind) · `dark` · `light` · `dim` (navy, never auto) | `auto` |
| `font` | `native` (Inter, reads like a real post) · `brand` (Poppins) | `native` |
| `text` | the post; type a line break as a literal `\n` (never `%0A`) | — |
| `meta` | timestamp line: the REAL post time, e.g. `8:00 AM · Oct 9, 2026`; `off` hides it | today 8:00 AM |
| `bg` / `storybg` | `#hex`, `cm-1`…`cm-7` wash, or a photo in the job folder | `#000000` |
| `storytext` | story size only: a native text bubble above the card | none |
| `name` `handle` | **required**, from the coach's config (never a web search) | — |
| `avatar` | photo file in the job folder; empty = initials circle | — |
| `check` | `on` only if the coach's account really has the blue check | `off` |
| `ring` | Instagram story ring around the avatar: `on` · `off` | `on` |

**Story quote cards:** `size=story&layout=card&storybg=#000000` or `storybg=cm-1`…`cm-7`. Vary the
wash across a week. Never put a card on a generated scene photo: the card covers the faces.

## Theme=auto

Card color comes from what's behind it, white or black only: very dark behind → white card;
colorful behind (every wash, bright colors) → black card; otherwise darker → white, lighter → black.
Navy (`dim`) is a manual switch-up for variety, suggested, never applied silently.

## Length

Text steps down 64 → 56 → 48px as the post gets longer and never goes smaller. Soft cap 220
characters; past it, split into two cards.

## Line breaks (only add breaks, never change words)

1. One sentence under ~90 characters: no breaks.
2. Setup + payoff ("They need...", "But...", "That's why..."): a blank line (`\n\n`) before the payoff.
   Several beats get a blank line between each.
3. Two or three short sentences, each its own beat: one per line (`\n`).
4. Lists: one item per line, no bullets unless the coach wrote them.
5. Never break inside a sentence to make a shape. If the coach typed breaks, keep theirs.

Show the broken version next to their original before rendering.

## Checks (a failure = no PNG)

FONT (every weight loaded), FIT (inside the story safe area or the frame), SETUP (name + handle given).
Fix the cause: shorten, split, or check the network. Don't work around a check.

## Rules

- The coach's words, the coach's account. Never render someone else's name or handle as the author.
- No fake like, repost or view counts.
