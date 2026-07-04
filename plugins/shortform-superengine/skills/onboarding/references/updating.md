# Updating the plugin (and the "won't sync" fix)

When a new version of `shortform-superengine` ships to the marketplace, your install
should pick it up automatically. Sometimes Claude Desktop doesn't: you click
*check for updates*, nothing changes, and you stay on the old version — sometimes a
marketplace you *removed* even comes back after a restart. **This is a known Claude
Desktop bug, not a problem with the plugin**, and it happens on **both Mac and
Windows** (Windows also has a separate glitch where *Check for updates* silently does
nothing).

## Tier 1 — the quick fix (try this first)

1. Open **Settings → Plugins**.
2. Find `shortform-superengine` → **⋯ (three dots)** → make sure **Sync automatically**
   is on, then **Check for updates**.
3. If nothing changes, **fully quit Claude** — not just closing the window:
   - **Mac:** menu bar **Claude → Quit** (⌘Q).
   - **Windows:** right-click the Claude **tray icon → Quit**, or open **Task Manager →
     End task** on Claude.
   Reopen Claude and check for updates again.
4. Still on the old version? **Remove the plugin, re-add it** from the marketplace,
   fully quit again, reopen.

Your setup is safe — onboarding is idempotent. After reinstalling, just say
*"refresh my shortform setup"* and it re-detects everything without redoing work.

## Tier 2 — the app-state reset (if Tier 1 fails)

Claude Desktop keeps its own cached copy of your marketplaces. When that cache gets
stuck on an old version, Tier 1 can't fix it — the app rebuilds from the stuck cache
on every launch (this is also why a removed marketplace reappears). Resetting the
cache forces a clean pull from the marketplace, and you land on the latest version.

> **Read first:** this signs you out of Claude Desktop (you'll sign back in) and
> resets desktop-app preferences. It does **not** touch your files, your work, or your
> plugin setup. You **rename** the folder (not delete), so you can put it back if
> anything looks off.

1. **Fully quit Claude Desktop** (Tier 1, step 3 — this is required; the cache is
   locked while the app runs).
2. **Rename the Claude app-state folder** to `Claude.bak`:
   - **Windows:** paste `%APPDATA%` into the File Explorer address bar → rename the
     **`Claude`** folder to **`Claude.bak`**.
   - **Mac:** Finder → **Go → Go to Folder** → paste `~/Library/Application Support` →
     rename the **`Claude`** folder to **`Claude.bak`**.
3. **Reopen Claude Desktop and sign back in.** It re-downloads marketplaces fresh —
   you'll be on the latest version.
4. Re-enable the plugin's tools/skills if they came back switched off.
5. Once you've confirmed the new version loads, delete `Claude.bak`.

If you'd rather not do this solo, reply and we'll walk you through it in ~2 minutes.

## Why this happens

Claude Desktop's marketplace sync (its "remote plugin manager") caches marketplace
state and, in current versions, doesn't reliably advance it to new releases — it can
even re-add a marketplace you removed. Anthropic has fixed related versions of this
bug; this variant is still around. Nothing you did wrong, and nothing the plugin can
fix from its side — the fix is clearing Claude Desktop's own cache.
