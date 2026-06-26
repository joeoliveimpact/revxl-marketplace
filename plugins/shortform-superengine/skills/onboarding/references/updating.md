# Updating the plugin (and the Mac "won't sync" fix)

When a new version of `shortform-superengine` ships to the marketplace, your install
should pick it up automatically. Sometimes — **especially on Mac desktop** — it
doesn't: you click *check for updates*, nothing changes, and you stay on the old
version. This is a Claude Desktop sync glitch, not a problem with the plugin itself.

## Normal update (try this first)

1. Open **Settings → Plugins** (or the plugins panel).
2. Find the plugin → **⋯ (three dots)** → **Sync automatically** + **Check for updates**.
3. If it updates, you're done.

## If it won't sync (the Mac workaround)

If *check for updates* does nothing after a minute:

1. **Quit Claude fully** — not just the window. Top-left **Claude → Quit** (or
   ⌘Q). Reopen. Try the update again.
2. Still stuck? **Uninstall and reinstall the marketplace plugin:**
   - Remove `shortform-superengine` from your plugins.
   - Re-add it from the marketplace (browse plugins → select it → install).
   - Quit Claude fully and reopen.
3. Re-enable the plugin's tools/skills if they came back switched off.

Your setup is safe — onboarding is idempotent. After reinstalling, just say
*"refresh my shortform setup"* and it re-detects everything without redoing work.

## Why this happens

Claude Desktop on Mac occasionally caches the old plugin bundle and skips the new
one. The full quit clears the cache; the uninstall/reinstall forces a clean pull.
Windows is usually fine. Nothing you did wrong — and nothing the plugin can fix from
its side.
