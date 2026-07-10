# chart.umd.min.js — vendored Chart.js

- **Version:** 4.4.7 (UMD, minified)
- **Source:** https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js
- **SHA-256:** `206b6e8bb00fc7bba2c7ee80ca41db3e9e05ba7be0aa35abeba9cfd5357f5d0e`
- **License:** MIT (banner preserved in the file)
- **Vendored:** 07.10.26

Used by `competitor-cross-reference/render_visuals.py`, which **inlines this file
into every generated HTML deliverable** so the output opens fully offline from
`file://` on Mac + Windows. There is deliberately NO CDN fallback — if this file
is missing the renderer exits loudly with the expected path.

Re-vendor: download the pinned URL above (bump the version deliberately), replace
this file, update version + SHA-256 here (`sha256sum chart.umd.min.js`), re-run
the renderer's offline + determinism checks.
