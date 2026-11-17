# Reel scene contract and starting example

Use this with [Build motion](motion-build.md). The checker in
`${CLAUDE_PLUGIN_ROOT}/scripts/scene_check.py` is the contract's authority.

## Contents
- Required files and fields
- Area sizes
- Assets
- Starting example

## Required files and fields

- Write `scene.json` and `scene.html` in the reel scene folder. Build renders `preview.png`; never hand-make it.
  Only those files and `locked` may live in the folder. Assets go in the shared location below.
- JSON requires `id` (folder name), `category` (same id), `kind: "world"`, `licence: "own"`, non-empty
  `source` naming the literal beat id, `area`, `holds`, `caption_band`, `slots`, `dur` and `params`.
- Give at least one slot with integer `maxChars >= 1`, a fitting string `default` and optional boolean
  `required`. A beat fills every slot, using `""` only for an optional empty slot.
- `dur` is `[min_s,max_s]`, with `0 < min_s <= max_s`; authored duration and selected beat must fit it.
  Each param has `type` (`number`, `string`, `boolean` or `color`) and a matching `default`; optional bounds
  must contain the default. Include `accent` and `font` so saved styles can restyle it.
- `holds` is non-empty and lists rest points as non-negative seconds or numeric-param names. Text checks use each rest
  +0.25 seconds (clamped to the last frame) and the last frame. Word timing is owned by
  Build motion's `times` step, including each numeric `t1`, `t2`, etc. param's `word` field.
- `caption_band` is `[y0,y1]`, at least 150 pixels tall in local area coordinates. Captions are centred
  in it; keep the whole band within global y 220-1470. For `full`, use `220 <= y0 < y1 <= 1470`
  (suggested `[1320,1470]`); for `stack`, `0 <= y0 < y1 <= 626` (suggested `[476,626]`);
  for `split`, `220 <= y0 < y1 <= 960` (suggested `[810,960]`).
  Follow [the caption transparency rule](motion-bar.md#6-room-for-the-face-and-the-captions).
- HTML declares every slot and param, each with a `label` and the JSON default, in single-quoted
  `data-composition-variables`, reads
  `window.__hyperframes.getVariables()`, and puts slot text in its matching `data-slot` element.
- The root has `id` and `data-composition-id` equal to the scene id, `data-duration` within `dur`, and `data-width` /
  `data-height` equal to the area size. CSS stays in z-index 400–499, with no background on html, body
  or root. Filled cards and plates use class `plate`.
- Load only `./vendor/gsap.min.js`. Register one paused GSAP timeline in `window.__timelines[id]`.
  No CSS animation, transitions, random values, clocks or timers. Use GSAP xPercent/yPercent for centring.
  Fonts use local `@font-face` declarations from shipped `runtime/fonts`, referenced as `./fonts/<file>`;
  declare every family and weight used. No remote files.

## Area sizes

These are authoring pixels, derived from `compose.world_area()`. Face choices and the full-screen tick
are owned by [Build motion](motion-build.md#scene-areas-and-the-face).

| Area | Width × height | Position in the full frame |
|---|---|---|
| full | 1080 × 1920 | x 0, y 0 |
| stack | 1080 × 1076 | x 0, y 844 |
| split | 1080 × 960 | x 0, y 0 |

## Assets

Product marks require official files in `<reel folder>/motion/assets/`. Record them in
`<reel folder>/motion/assets.json` as `{"files":[{"path":"mark.svg","sha256":"<64 hex characters>","source":"<official origin>"}]}`.
Each `path` is a filename, with no directory components; bytes must match the digest. Reference it as
`./assets/mark.svg`. No file on disk means use the product name as text; never draw a lookalike logo.

## Starting example

This minimal full-area scene is a checker-valid starting point, not a finished look. It keeps all paint
above its caption strip. Adapt the id, source, duration, slots, camera and word timings to the real beat,
then run the checks and Motion review in Build motion. `place` fills slots with the beat's first spoken
words that fit, not the scene defaults; params start empty and use scene defaults. To show other text,
write the matching scene id and every slot under `beat.scene.slots` in both Beat Map files before `place`;
it keeps them. A required slot whose first word cannot fit refuses placement.

`scene.json`:

```json
{
  "id": "reel-b001-example", "category": "reel-b001-example",
  "kind": "world", "licence": "own", "source": "Beat b_001, example look",
  "area": "full", "holds": [0], "caption_band": [1320, 1470],
  "dur": [1, 5],
  "slots": {"text": {"maxChars": 12, "default": "Clear scene", "required": true}},
  "params": {
    "accent": {"type": "color", "default": "#4f8cff"},
    "font": {"type": "string", "default": "Inter"}
  }
}
```

`scene.html`:

```html
<!doctype html>
<html data-composition-variables='[{"id":"text","type":"string","label":"Text","default":"Clear scene"},{"id":"accent","type":"color","label":"Accent","default":"#4f8cff"},{"id":"font","type":"string","label":"Font","default":"Inter"}]'>
<head><script src="./vendor/gsap.min.js"></script><style>
@font-face {font-family:"Inter";src:url("./fonts/Inter-Regular.woff2");font-weight:400;font-style:normal;}
html,body {margin:0;width:1080px;height:1920px;overflow:hidden;}
#reel-b001-example {position:absolute;width:1080px;height:1920px;z-index:400;font-family:"Inter";font-weight:400;}
.plate {position:absolute;left:100px;top:400px;width:880px;height:500px;background:#17233d;}
.slot {position:absolute;left:180px;top:500px;font-size:48px;line-height:1.2;white-space:nowrap;}
</style></head><body>
<div id="reel-b001-example" data-composition-id="reel-b001-example" data-duration="3" data-width="1080" data-height="1920">
  <div class="plate"></div><span class="slot" data-slot="text"></span>
</div>
<script>
const v = window.__hyperframes.getVariables();
const root = document.getElementById("reel-b001-example");
root.querySelector('[data-slot="text"]').textContent = v.text;
root.style.color = v.accent;
root.style.fontFamily = v.font;
const tl = gsap.timeline({paused:true});
tl.to(root, {opacity:1,duration:3}, 0);
window.__timelines = window.__timelines || {};
window.__timelines["reel-b001-example"] = tl;
</script></body></html>
```
