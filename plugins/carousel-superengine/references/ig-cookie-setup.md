# Instagram cookie capture — Cookie-Editor walk-through

Full-slide teardown (Path B) pulls every slide using the client's OWN Instagram session, supplied as a
cookie export. No login script, no password, no terminal — just a 2-minute point-and-click export with
the free **Cookie-Editor** browser extension. Do this once during setup; redo it only if a fetch later
returns `login_required`.

## Steps (walk the client through these)

1. **Install Cookie-Editor** (free) in Chrome or Edge — the "Cookie-Editor" extension from the Chrome Web
   Store (by cgagnier). Pin it for convenience.
2. **Log into Instagram** in that browser at instagram.com — the account whose access you'll use. Their
   OWN account; a secondary / low-value account is fine and keeps per-account volume tiny.
3. On any instagram.com tab, **click the Cookie-Editor icon**.
4. Click **Export** (icons at the bottom-right of the popup) → **Export as JSON**. This copies all
   instagram.com cookies to the clipboard as a JSON array.
5. **Paste that JSON** back here when the engine asks. Done.

## What the engine does with it
- Saves it to `${CLAUDE_PLUGIN_DATA}/ig_session.json` (persists across plugin updates; per-client).
- `carousel_fetch.py` reads `sessionid` (plus the other instagram.com cookies) and calls Instagram's
  mobile API to pull each slide. The export format from Cookie-Editor is consumed as-is.

## Safety
- The export includes `sessionid` = **full access to that Instagram account**. Treat it like a password:
  it lives in `${CLAUDE_PLUGIN_DATA}` on the client's machine and is never shipped, committed, or shared.
- **Revoke** by logging that account out of Instagram (Settings → the "logged-in devices" / security
  area), which kills the session server-side. Re-export afterward if you still want full-slide teardown.
- Use the client's own account, never a shared one — concentrated scraping volume on a single account is
  what gets flagged.
- Don't paste cookies into places that persist them (public chats, shared docs). The setup flow saves
  them locally and doesn't echo them back.

## When to refresh
- **Only when a teardown returns `login_required`.** Instagram sessions typically last months for an
  active account — there's no fixed expiry worth scheduling. The engine detects `login_required` and
  asks for a fresh export; no timer needed.
