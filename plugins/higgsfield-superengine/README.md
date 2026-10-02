# higgsfield-superengine

> Higgsfield image and video generation, driven by Claude. Your own Higgsfield key, prompting best practices built in, and a price check before anything spends. Windows-first.

---

## Status: released (v0.1.1)

Install it from the REVXL catalog. See CHANGELOG.md for what changed in each version.

---

## What this plugin does

Higgsfield can make great images and videos, but getting good results means knowing which model to pick, how to write the prompt, and what each run will cost. This plugin handles that for you.

- **Your own account.** It talks to the Higgsfield REST API (Higgsfield's official web interface for programs) directly, with your own Higgsfield API key. Each client uses and pays for their own account.
- **Prompting built in.** Image and video prompting best practices are part of the plugin, so you describe what you want in plain English and Claude writes the prompt.
- **Estimate first.** Every paid generation is priced before it runs. Small jobs under a safety cap run after the price check; anything bigger waits for your yes.

---

## Planned skills

- `higgsfield-setup` — connect your Higgsfield key, one time.
- `hf-generate` — the only skill that spends credits. Prices the job first, then runs it.
- `image-prompting`, `video-prompting` — the prompting craft.
- `static-ads`, `ugc-video-ads`, `product-shots`, `thumbnails` — guided flows for common jobs.

---

## Compatibility

| Platform | Status |
|----------|--------|
| Windows | Primary target |
| Mac | Key box is beta and untested |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md) — REVXL's curated Claude superengine catalog.
