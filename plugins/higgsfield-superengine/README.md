# higgsfield-superengine

> Higgsfield image and video generation, driven by Claude. Your own Higgsfield key, prompting best practices built in, and a price check before anything spends. Windows and Mac.

---

## Status: released (v0.1.5)

Install it from the REVXL catalog. See CHANGELOG.md for what changed in each version.

---

## What this plugin does

Higgsfield can make great images and videos, but getting good results means knowing which model to pick, how to write the prompt, and what each run will cost. This plugin handles that for you.

- **Your own account.** It talks to the Higgsfield REST API (Higgsfield's official web interface for programs) directly, with your own Higgsfield API key. Each client uses and pays for their own account.
- **Prompting built in.** Image and video prompting best practices are part of the plugin, so you describe what you want in plain English and Claude writes the prompt.
- **Estimate first.** Every paid generation is priced before it runs. Small jobs under a safety cap run after the price check; anything bigger waits for your yes.

---

## Spend band

New in v0.1.5: you decide how much each chat may spend, and you can see it.

- **The cap box.** The first paid job in a chat asks you how much this chat may spend: $5, $10, $20, or Not now. Jobs that fit under the amount you pick just run. Not now sends nothing, and the box comes back with the next paid job.
- **The band.** A strip above the prompt shows what this chat has spent against its cap, with buttons: **+$5** and **×2** raise the cap, **Back to $5** lowers it, and **Details** opens the Details pane. It turns amber at 70% of the cap and red at 90%. Only your clicks change the cap; Claude can't set it for you.
- **The Details pane.** This chat's jobs (time, model, price, status), with **Open** to view a finished picture or video; spend by model; what you spent in the last 24 hours and 7 days; and your Higgsfield balance (**Update balance** records the figure from your Higgsfield billing page).
- **A reopened chat** that already used Higgsfield shows its band again.
- **A cap you pick is the cap for that chat.** It is not lowered to a quarter of your balance, the way the 24-hour limit is, so pick an amount your balance can cover.
- **Prices are Higgsfield's list prices**, before any sale. While Higgsfield runs a sale, a quote can be higher than what you are actually charged, so a job may ask for your OK sooner than it needs to.

**Where the band does not appear:** Cowork, VS Code, WSL sessions, Claude Code older than 2.1.287, or with mods turned off. Your spending is still protected there: until a cap is picked for a chat, the limit of at most $5 per 24 hours applies, and any job over it shows a pop-up with the price (Allow runs that one job, Deny spends nothing).

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
| Windows | Supported |
| Mac | Supported since v0.1.3: Python 3.9+ (found by setup; Homebrew installs it if missing); the key is kept in the Keychain |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md) — REVXL's curated Claude superengine catalog.
