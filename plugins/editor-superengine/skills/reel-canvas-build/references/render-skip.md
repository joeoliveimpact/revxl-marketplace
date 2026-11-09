# Reuse an unchanged successful render

`scripts/render_skip.py` wraps the existing compositor without changing its
render path or approval flow:

```text
render_skip.py preview --reel-dir videos/REEL_018
render_skip.py master --reel-dir videos/REEL_018 --force
```

It accepts `--hook-text`, `--layers all|aroll|overlay|captions`, and
`--keep-project`. Separate layers use the compositor's master tier. An unchanged
fingerprint skips rendering only while its recorded output file still exists.
`--force` always calls the compositor.

The fingerprint covers reel JSON inputs (including cut words, captions, style
choices and approval), local media size and modification time, grade cubes,
plugin sources, scenes, layouts, templates, bundled runtime files, saved styles,
runtime installation facts, tier, layer selection, hook text, dimensions and
quality settings. Generated scale tracks, QA reports, render scratch, and
finished output folders are excluded. The cut master under `work/renders`
remains an input. Media are checked by size and timestamp, so an external tool
that rewrites bytes while preserving both can defeat this optimization; use
`--force` after such a replacement.

Only a successful render with an existing output writes `work/.render-fp.json`.
It stores `{fp, out}`, including the compositor's dated output path. Compose can
write caption plans and remembered choices, so the saved fingerprint reflects
their settled values after success. Failed renders do not update it. The cache
holds one result: switching tier or layers can replace that result. Delete the
state file, or use `--force`, to start fresh.

Skipping is a speed option. Watch the resulting video and run the ordinary
post-render QA before delivery.
