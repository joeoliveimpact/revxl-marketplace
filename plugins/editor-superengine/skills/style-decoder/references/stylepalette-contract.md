# stylepalette contract — style-decoder colour extraction

> Companion to `scripts/stylepalette.py`. Dominant colours per zone across ~12
> sampled base frames -> `palette.json` + `palette-swatch.png`. Needs Pillow.

- Zones default to horizontal thirds. Once layout modes are known, the decode phase
  re-runs with `--zones` (a JSON list of `{id, rect_pct:[x,y,w,h]}`) matching the
  discovered panel geometry, so zone colours map 1:1 onto layout-mode zones.
- Method: Pillow median-cut quantize per zone crop, then share-weighted aggregation
  across sampled frames. Pixel counts per palette index come from
  `Image.histogram()` (zero counts skipped), which works on every Pillow version with
  no DeprecationWarning; `getdata()` is deprecated and removed in Pillow 14.
- **Hex values are tokens, not colorimetric truth**: sources are platform-compressed
  512px JPEGs. Claude labels each token's *role* (background skin, accent, pill fill)
  in the decode phase; `color.tokens[]` carries hex + role, the runbook shows the
  swatch strip.
- Whites/creams within about ΔE 5 of each other are one token. Don't mint three
  near-identical whites; pick the modal hex.
