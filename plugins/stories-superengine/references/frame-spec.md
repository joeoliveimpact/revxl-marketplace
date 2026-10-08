# Frame spec — story.json

`scripts/render_frames.py <story_dir>` reads `<story_dir>/story.json` and writes `frame-N.png`
(1080×1920) plus `_contact-sheet.png`. Photos are copied into `<story_dir>` and named there.

```json
{
  "style": "strong",
  "frames": [
    {"bg": "hook.png", "position": "top", "focus": "center 30%",
     "lines": [{"text": "you don't need\nanother meal plan.", "color": "white"},
               {"text": "you need one you'll do.", "color": "black"}]},
    {"bg": "#000000",
     "lines": [{"text": "three 30-minute workouts.", "color": "purple"},
               {"text": "at home.\nno 5am gym runs.", "color": "orange"}]},
    {"bg": "ask.png", "position": "bottom",
     "lines": [{"text": "reply START", "color": "white"},
               {"text": "and I'll send you the plan", "color": "black"}]}
  ]
}
```

## Fields

| Field | Values | Default |
|---|---|---|
| `style` (set) | `modern` `classic` `signature` `editor` `poster` `bubble` `deco` `squeeze` `typewriter` `strong` `meme` `elegant` `directional` `literature` (Instagram's own picker order) | `strong` |
| `bg` (frame) | photo file in the story folder, a swatch hex like `#000000`, or `cm-1`…`cm-7` (Instagram create-mode washes: 1 red-orange, 2 pink-purple, 3 blue-purple, 4 blue-green, 5 lime-purple, 6 light gray, 7 charcoal) | `#000000` |
| `position` | `top` `center` `bottom` (inside the safe area) | `top` |
| `focus` | CSS background-position for the photo, e.g. `center 30%` to keep a face low | `center` |
| `size` | px on the 1080 canvas, frame-wide | 70 |
| `lines[].text` | the words; `\n` breaks a bubble into lines | — |
| `lines[].color` | one of the 27 swatch names: white black blue green yellow orange red magenta purple scarlet salmon light-salmon light-sand sand dark-sand brown dark-brown dark-green gray-1…gray-9 | white |
| `lines[].background` | `solid` (swatch fill, partner letters) · `light` (pale fill, swatch letters) · `off` (no bubble) | `solid` |
| `lines[].style` | override one line's style (avoid: one style per set) | set style |

**Color habits that read well:** white then black solid bubbles on photos; purple / orange / blue in
rotation on plain black. On a light photo, black bubbles stay readable.

## The render checks (a failing frame is not written)

- **LOAD**: story.json read and the frame exists.
- **FONT**: the style's font actually loaded (needs internet for Google Fonts).
- **FIT**: no text past the screen edges or under Instagram's top bar (270px) or reply bar (384px).
  Text inside the 65px side margin prints a note, not a failure.

Then look at `_contact-sheet.png` yourself: faces covered, awkward crops, wording. The checks can't see those.

## Safe area

1080×1920 canvas. Instagram covers the top 270px (progress bar, name) and the bottom 384px (reply
bar). Keep every word between them. Sides: 65px is the comfortable margin.
