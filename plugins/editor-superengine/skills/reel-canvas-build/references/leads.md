# Optional render leads and board fine-tuning

On the glass card, glow (soft or bloom, default bloom) and dust (points or quarks, default quarks) are set on the Beat Map. Motion easing isn't offered yet: use the not-built line.

## Motion 14.6.0

Use Motion for a short DOM movement or fade that benefits from its keyframes.
Load `./vendor/motion.js` as the second src script, immediately after GSAP.
Keep the scene's single paused GSAP timeline registered as usual.
Create animations with:

```js
Motion.animate(element, {
  transform: ["translateX(0px)", "translateX(120px)"], opacity: [0, 1]
}, {duration: 4, ease: "linear", autoplay: false});
```

Use only native WAAPI properties: transform, opacity, filter and clip-path.
Never use springs or JS-driven values. A spring is driven by JS and a seek
cannot reproduce it. HyperFrames' WAAPI adapter pauses every animation from
`document.getAnimations()` and sets its currentTime on every seek. Scene
code must not add another clock or manually advance a Motion animation.
The Motion proof fixture is temporary; no Motion scene is shipped.

## postprocessing 6.39.5

Use bloom to accent the glass card's bright edge and dust when emphasis is
useful. `glass-card-3d` accepts `glow: "soft" | "bloom"`, default `"bloom"`.
WebGL uses EffectComposer, RenderPass and EffectPass with DepthOfFieldEffect,
plus BloomEffect for bloom. The card is in focus; far dust becomes bokeh and
front dust is slightly defocused. The underlying footage is a separate layer
and cannot be blurred by this scene; depth blur acts only on the scene's dust.
A diagonal specular sweep crosses during 0.5–1.4 s and again, fainter, near
the end. Glyphs render in a final sharp pass. All optical effects are clipped
to regions[place]. There is no temporal accumulation; composer delta is zero.
The CSS path ignores glow/dust and keeps its existing soft glow and Canvas dust.
Import postprocessing through the exact local scene import map only.

## three.quarks / quarks.core 0.17.1

Use `dust: "points" | "quarks"`, default `"quarks"`, for depth-spanning dust.
The ParticleSystem emits mostly far dust and some larger foreground dust;
BatchedRenderer supplies sprites with depth for postprocessing. Every seek
restarts the system and re-simulates from zero in 1/fps steps, plus any final
fractional step, using a restarted mulberry32(seed) stream. The library's
random source is temporarily replaced and restored in finally. No scene
clock or timer drives it. Both ESM packages use exact local import-map names;
a missing runtime file stops composition plainly. Keep the seed fixed when
comparing renders. The CSS path ignores dust and retains its original output.

## Fine-tune boards

Tweakpane belongs only to the Sketches and Tweak boards, never a composition.
Sketches selects a beat, binds numeric bounds and colours from its catalog,
and keeps the existing numeric controls and Send state in sync. A counter's
spoken value stays locked. Tweak selects a mark and edits its start/end time
or pause milliseconds through the board's existing save and undo paths.
Both panels collapse. A selection without editable values explains that
in plain words. Board sync copies all nonhidden template files, including
the local module, manifest and licence; the board server serves local JS.
