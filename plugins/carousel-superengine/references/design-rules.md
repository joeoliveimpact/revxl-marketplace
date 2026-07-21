# Design Rules — directions a non-designer can execute

The engine outputs DESIGN DIRECTIONS per slide, not finished art. Every direction below is
executable in Canva by a coach with zero design background. Carousels out-engage single images
(~114%) and Reels (~12%) when they respect mobile readability... 80%+ of viewers are on a phone.

## Text + readability (hard rules)

- **Text budget (single source of truth — other refs defer here):** default text ≤ ~20% of canvas
  area. Spec-sheet/educational formats legitimately run 25-40% — the deck's FORMAT sets the budget;
  declare it once and hold it every slide. Past ~40% it's a blog post, not a slide.
- **One idea per slide**, 25-50 words body max (2026 target: under 40... the average per-slide
  glance is ~1.5 seconds).
- **Sizes (IG 1080×1350):** headlines ≥ 36px bold (readable at grid-thumbnail size), body ≥ 22-24px.
- Line height 1.4-1.6×; 35-45 characters per line; bold the skim path.
- **UI safe zone (IG 1080×1350, 2026):** Instagram's caption text, like/save icons, and swipe
  indicator obscure roughly the bottom 150-250px, and the top ~120px can be truncated on some
  devices. Keep headlines, body text, and the focal cutout inside the center-upper ~75% of the
  canvas; nothing critical in the bottom band.

## Composition (line logic + layout) — T1, every rule from a live defect

**Line breaks are authored, never auto-wrapped.** The break lands where the THOUGHT breaks:
- **Phrase = line.** A sentence or complete phrase owns its line. Never let a wrap split a
  parenthetical, a couplet's correction, or a claim mid-phrase ("(Swipe and you / won't have to.)"
  is a defect; sentence on line 1, parenthetical on line 2 is the fix).
- **No orphans.** A lone word ("calls.") on its own line fails the slide. Rebreak by phrase.
- **Balance the block.** Adjacent authored lines should read as a deliberate shape (equal-ish, or
  clearly stepped) — never almost-equal-but-off.
- **Size change → re-verify the widest line.** Authored `nowrap` lines bleed past the margin when
  the size bumps. Any type-size change re-checks every authored line against the margin frame.

**Layout:**
- **Boxed text spans the content column.** Character caps (35-45/line) size BARE text; once copy
  sits in a framing device (box, card), the device spans the column — a narrow box in a wide
  column reads jumbled and wastes the canvas.
- **One frame per idea.** Never two framing devices on one thought (a boxed payoff inside a body
  box, a bordered quote under a rule). Merge or drop one.
- **Size = narrative weight.** The recurring motif (progress rail, tease, mark) is scaled to its
  role in the deck, not left at default. If it's the through-line, it reads like one.
- **Value marks ≠ cost marks.** A filled bar always reads "more = better" — never use it for
  cost/price. Cost gets $ symbols (or equivalent) so more visibly = worse.
- **Artifacts are composed at slide scale.** Never blow up a cropped strip and ship it; rebuild
  the artifact in the design system so it is legible at phone size.
- **Reposition → collision re-check.** Moving or resizing any element re-checks its neighbors
  (ghost words, mascots, badges) for overlap and edge bleed. Neighbors do not stay safe by default.

## Color + contrast

<!-- T1 (universal craft): -->
- High contrast text-on-background, always. Structure rule: **one base + one deep anchor + ONE
  accent reserved for data points and CTA elements.** The structure is universal; the actual hues
  are NOT (see palette note below).
- **2-3 colors per slide max**, even if the brand kit holds five.
- **Export sRGB only.** CMYK uploads render washed-out/neon on IG + LinkedIn. (Canva default is
  fine; flag it only if the coach works in Photoshop/print tools.)
- Sterile clinical minimalism and cheap clip art read as 2021 and break trust — texture and warmth
  in SOME form, whatever the palette.

<!-- T3 (pulled from the coach, never shipped as "the" answer): -->
- **The specific palette comes from the coach's brand** — brand kit / brand brain first, else pick
  a starter direction at setup: **wellness-warm** (cream base, forest green, coral) ·
  **dark-tech/spec-sheet** (warm near-black, cream ink, gold or single hot accent) ·
  **editorial** (off-white, ink, one saturated accent) · **bold-color** (saturated field, white
  display). No single family is "proven" for every coach — a wellness palette on an AI-coach brand
  (or vice versa) mis-serves the brand. Hex values welcome; a brand system defined in hex ships
  in hex.

## Typography + brand system

- **Two fonts, locked:** one bold display for headlines (Montserrat Bold / Space Grotesk class),
  one clean quiet body font (Inter / DM Sans class). Same pair on every carousel.
- **Watermark every slide:** small handle/profile element, same corner every time. Critical on
  LinkedIn... PDFs get downloaded and travel offline; the brand rides along.
- Lock margins (~60px) and element positions into a reusable template; change only the focal
  element per slide. Run the system ≥90 days before judging it... recognition compounds.

## Image use

- Real people over stock, the coach's own face over everything. This demographic buys people.
- **Cutout treatment:** background-removed portrait + subtle white/colored outline shadow =
  polished "sticker" pop (one-click in Canva Pro).
- Real receipts (progress data, app screenshots, client charts) beat illustrations for authority...
  only ever REAL ones from `{{PROOF_ASSETS}}`.
- **Mixed media (IG only):** ONE 5-second silent looping video mid-carousel lifts engagement ~29%
  over static-only. Direction it like: "slide 5: 5s loop of [specific real moment]."

## Per-slide design direction format (what the engine outputs)

For each slide: `visual:` one executable sentence (layout, focal element, color note) +
`retention device:` if one applies (panorama seam, micro-arrow, loop teaser). Example shape:
"visual: cream base, left-aligned headline in forest green, coach cutout right with sticker
outline; tiny arrow bottom-right." Nothing vaguer than a coach can act on alone.
