---
name: login
description: Log into a website that requires authentication so course-crawler can scrape its content. ALWAYS use this skill before /page or /course when the target URL is behind a paywall, members-only login, or any auth gate. Common cases the user might describe with different words ... "I need to log into ..." "this site needs a password", "members area", "paywall", "Substack subscription", "course portal login", "have to sign in first", "behind authentication". Opens a real browser via the chosen backend, watches for the user to finish logging in, then captures the session cookies into ~/.iss/sessions/<domain>.txt. Also supports a manual cookie copy/paste path for users with no working browser backend. Use even if the user hasn't explicitly mentioned login but the URL clearly points at a login-walled platform (Kajabi, Teachable, Thinkific, Skool, MasterClass, Substack premium, Medium members, NYT, FT, paywalled blogs).
---

# Log into a site so we can scrape it

This skill captures the user's authentication so the next time `page` or `course` runs against that domain, it can fetch private content as if logged in. There are two paths: **assisted** (browser backend drives it) and **manual** (copy/paste cookies). Offer manual whenever the assisted path is blocked.

## Step 1: Pick a browser backend

Run the detector and decide:

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/browser_backend.py
```

- If `mcp__plugin_superpowers-chrome_chrome__use_browser` is in your tools → **superpowers-chrome** (preferred).
- Else if `mcp__browser-use__*` is available → **browser-use**.
- Else if a Playwright MCP is available → **playwright**.
- If more than one, ask the user which to use.
- **If none are available**: skip to Step 5 (manual cookie paste). Also offer: "I can run `/setup` to install a browser backend ... want that, or do you want to paste cookies manually for now?"

"The browser" below = the chosen backend's navigate / get-state tools.

## Step 2: Get the login URL

If the user said "log into eastwesthealing.com" without a full URL, ask for the login page (or the page they were trying to scrape ... most sites redirect to their login form automatically).

## Step 3: Open the browser and hand off to the user

Navigate the browser to the URL. A real browser window opens on the user's screen. Confirm with get-state that we're on a login form (look for password input fields).

Tell the user, explicitly:

> "The browser is open. Log in there yourself ... type your email/username and password and submit. I won't touch your credentials. When you're back at the normal logged-in view, tell me 'done' (or I'll detect it automatically)."

Do NOT type credentials yourself. The user owns their login.

## Step 4: Watch for completion, then capture

Poll get-state periodically (every ~10-15s, or when the user says "done"). Completion signals, any of:

- URL is no longer the login/sign-in page (path changed off `/login`, `/sign_in`, `/auth`).
- No password field present in the interactive elements.
- A recognizable logged-in element (account menu, avatar, "Log out").

Don't poll forever ... after ~3 minutes with no progress, ask the user if they're stuck or want the manual path.

Once logged in, capture cookies. The dumper attaches to whatever debuggable Chromium the chosen backend is running (it scans for any `remote-debugging-port`, so it works regardless of which backend launched it):

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/dump_cookies.py \
  ~/.iss/sessions/<domain>.txt --domain <domain>
```

On Windows: `%USERPROFILE%\.iss\venv\Scripts\python.exe` and `%USERPROFILE%\.iss\sessions\<domain>.txt`.

If the dumper reports **no debuggable Chromium found**, the chosen backend isn't exposing a CDP port (some Playwright setups, hardened superpowers-chrome). Don't fail ... fall through to Step 5 (manual paste) and tell the user why.

If it reports **zero cookies**, the user may not have actually completed login, or the domain filter is too narrow. Ask them to open a clearly-private page and re-run.

## Step 5: Manual cookie paste (fallback ... always available)

Use this when there's no working backend, no CDP port, or the user just prefers it.

Tell the user:

> "You can paste your cookies instead. Easiest way: install the 'Get cookies.txt LOCALLY' browser extension, log into the site in your normal browser, click the extension, and copy the exported text. Paste it here and I'll save it."

Accept either:
- A Netscape `cookies.txt` blob (starts with `# Netscape HTTP Cookie File` or tab-separated `domain  TRUE/FALSE  path ...` lines), or
- A raw `Cookie:` header string (`name=value; name2=value2`) ... in that case ask for the domain and convert each pair to a Netscape line for that domain.

Write the result verbatim (or converted) to `~/.iss/sessions/<domain>.txt` (Windows: `%USERPROFILE%\.iss\sessions\<domain>.txt`). Create the `sessions` dir if missing. Confirm the file path and the cookie count back to the user.

Never paste a cookie blob into a script argument or log it ... write it to the file directly. Remind the user these cookies are sensitive and expire (7-90 days typical).

## Step 6: Confirm and offer next step

Show: domain captured, session file path, rough cookie count, and the expiry caveat (re-run `/login` if scrapes start 401/403ing later). Then:

> "Cookies saved. Now run `/page <url>` for a single page, or `/course <url>` to scrape a whole course on this site."

Leave the browser window open ... `course` discovery may reuse the live session for cookie refresh.

## Why this exists

Doing login through the same browser the plugin uses for discovery means the auth and the automation share one session ... no double-login, no manual export. The manual paste path guarantees the plugin still works for users whose environment has no usable agentic browser at all.
