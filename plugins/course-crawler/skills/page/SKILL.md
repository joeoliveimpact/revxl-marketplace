---
name: page
description: Save a single web page as a clean local archive (Markdown + raw HTML + metadata). Use this skill whenever a user wants to capture, save, scrape, archive, ingest, mirror, or "grab" a single URL ... a blog post, news article, course lesson, Substack post, Notion page, paywalled article, Medium piece, documentation page, or any other one-off page. Works on both public pages (no auth) and private/logged-in pages (uses cookies captured by /login). Outputs clean Markdown stripped of navigation/sidebars/ads via trafilatura, the original HTML for re-parsing later, and a metadata JSON with title/date/author/links. No LLM tokens are spent on the fetch itself ... it's just an HTTP request + a parser. Use this even if the user phrases the request informally ("save this", "grab this article", "I want to read this offline", "pull this into my notes").
---

# Save a single web page

This is the simplest skill in the plugin. One URL in, one set of files out. Use it for any "I want to capture this one page" request.

## Prerequisites

`/setup` must have run successfully. If `~/.iss/venv/bin/python` doesn't exist, tell the user to run `/setup` first.

If the page is behind a login (paywall, members-only), `/login` should have been run for that domain first ... cookies live at `~/.iss/sessions/<domain>.txt`.

## Step 1: Get the URL and the output destination

The user provides the URL. If they didn't, ask: "Which page do you want to save?"

Default output destination is `./scraped/<slug>/` relative to the current working directory. The slug is derived from the page title once we have it, or from the URL path if we can't. If the user explicitly said "save into <some-folder>", use that.

## Step 2: Detect whether cookies are needed

Look at the URL's domain. Check if `~/.iss/sessions/<domain>.txt` exists:

- **Exists** → use it. The page likely needs auth.
- **Missing** → try the public path first. If we get redirected to a login page (HTTP 302 to `/login` or similar), stop and tell the user: "This page needs authentication ... run `/login <domain>` first, then come back and run `/page` again."

## Step 3: Fetch and parse

Run the pull script from the plugin's bundled `scripts/`:

```bash
~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/pull_lesson.py "<url>" \
  --out "./scraped/<slug>/" \
  --cookies "~/.iss/sessions/<domain>.txt"   # only if cookies exist
```

The script writes a clean set of files into the output directory:

- `<slug>.md` ... clean Markdown via trafilatura (no nav/footer/ads)
- `<slug>.links.md` ... categorized reference links (only if any found)
- `<slug>_assets/` ... downloaded attachments (only if any found)
- `<slug>.json` ... small metadata (title, author, date, source URL)

Raw HTML is **not** saved unless the user explicitly wants it ... pass `--keep-html` to also write `<slug>.html`.

## Step 4: Verify and report

After the script returns:

1. Open the `.md` file and skim the first ~10 lines. If it looks empty or like JavaScript/CSS, the page was probably rendered client-side and trafilatura can't see content. Flag this:
   > "The page extracted as mostly empty. It's likely a JS-rendered SPA. Want me to render it through the browser backend (see /login Step 1 for detection) and re-capture? Or re-run with `--keep-html` so we have the raw HTML to work from."

2. If the markdown looks good, show the user:
   - The title we extracted
   - File paths
   - Character count of the Markdown (so they have a sense of how much content)

## Edge cases

- **Page is a redirect to login**: handled in Step 2. Tell the user to log in first.
- **403 Forbidden**: cookies may have expired. Suggest re-running `/login`.
- **404 Not Found**: URL is wrong. Ask the user to check it.
- **5xx**: the site is having problems. Suggest retrying in a minute.
- **JS-rendered SPA**: described above. Offer the browser-backend render fallback.

## Why this exists

For a single page, an agentic browser is overkill ... it costs LLM tokens for every page load. A plain HTTP fetch + content extractor is free and instant. This skill keeps the workflow lean and obvious.
