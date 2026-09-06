# Carousel Superengine

Voice-matched Instagram + LinkedIn carousel engine for coaches — from topic to finished slide
images. Run setup once, then generate complete carousels... hook slide, value slides, CTA slide,
per-slide copy and design, a caption built for 2026 search, hashtags, AND the actual images:
AI-generated in your look (optionally with your trained face), a paste-ready Claude Design prompt,
or local PNG / LinkedIn-PDF rendering on Claude Code. Save any finished look as a template and the
next build takes minutes. Plus a paste-a-link teardown, a niche-wide competitor synthesis, and
carousels straight from your client calls.

Drafts only. Nothing posts automatically. Your config, voice, and templates persist across plugin
updates.

## Commands

| Command | What it does |
|---|---|
| `/carousel-start-here` | Entry point... routes you to the right place |
| `/carousel-setup` | First-run wizard: voice, avatar pains, platform, CTA destination, data sources, render prefs |
| `/carousel-guide` | Hand-held tour for first-timers: setup + your first carousel |
| `/carousel-create` | The generator: topic / reel script / your calls / teardown → full package |
| `/carousel-render` | Package → finished slide images (image-gen in your look, Claude Design prompt, or local PNG/PDF) |
| `/carousel-templates` | "Save this look" after a build → "use my template" forever after |
| `/carousel-teardown` | Paste a public carousel link → why-it-works breakdown → your version (reviews your own posts too) |
| `/carousel-inspire` | "What's working in my niche" → evidence-cited patterns + ready-to-build ideas |
| `/brand-brain` | Capture or refresh your voice + customer language (shared across REVXL engines) |

## Quickstart

1. Install the plugin, run `/carousel-start-here`.
2. Say "walk me through it" (first time) or run `/carousel-setup`.
3. "Carousel about [the thing your clients keep complaining about]" ... you get the full package
   as a draft: slide map, per-slide copy + design, caption, hashtags, alt text.
4. "Make the images" ... finished slides, in your look. "Save this look" ... and next time it's
   "use my template" and done.

## The images

Three ways to finished slides, picked per build:

- **Image generation** — the engine briefs an image model slide by slide (anchor first, then one at
  a time for consistency). Optional: train it on YOUR face once and every image is actually you.
- **Claude Design** — you get ONE paste-ready prompt; claude.ai/design builds the cards on the plan
  you already have. No extra tools.
- **Workspace render (Claude Code)** — slides built as local files: exact-pixel PNGs for Instagram
  or a single PDF for LinkedIn document posts. No design tool at all.

If a path isn't available on your setup, the engine says so and hands you the next one — you always
walk away with something postable.

## The teardown feature

See a carousel that's clearly working? Paste the link.

- **Everywhere (Cowork, Desktop, Code):** the engine pulls the post through YOUR OWN SocialCrawl
  key (2-minute free signup, ~1 low-cost credit per pull)... caption, slides, engagement... and
  breaks down the hook, structure, and CTA mechanics.
- **On Claude Code with Python:** a bundled fetch script can pull EVERY slide of a public post for
  a true slide-by-slide teardown (public posts only, rate-limited, personal research use).

Then: "build my version" rebuilds the STRUCTURE with your content, your voice, your CTA — and the
downloaded slides guide the LOOK of your images. Nothing is ever copied.

Want the whole niche instead of one post? `/carousel-inspire` studies many winning accounts and
hashtags and hands you patterns + ranked ideas, every claim cited.

## Autopilot (optional)

"Schedule my carousels" sets up recurring DRAFT builds — weekly or daily, from your topics or your
newest calls, in your saved look. The engine only ever suggests it; you approve the schedule, you
approve every draft, and "stop the weekly carousel" kills it anytime. Posting is never automated.

## What it never does

- Post or send anything (scheduled builds draft; only YOU post)
- Invent client results, testimonials, or fake scarcity
- Copy a competitor's wording, examples, or images
- Spend credits without telling you first (scheduled runs spend none unless you explicitly cap some in)
- Ship your voice/config data anywhere... the brand brain lives on your machine

## The RevXL Brain (optional)

With a Brain key from Joe, carousel-create pulls the newest content-strategy patterns at two named points and cites them as `[brain] <path>`. The connection comes from the workspace-superengine plugin (`revxl-vault-search`): it finds or asks for the key once, keeps every call inside the daily budget, and explains any failure in plain English. Without a key, or without workspace-superengine, the engine runs on its built-in library and says so once.

## Requirements

- None for generation.
- RevXL Brain (optional): a Brain key from Joe plus the workspace-superengine plugin (0.14.0 or
  later), which provides the connection. Adds live pulls of Joe's newest content-strategy patterns
  at carousel-create's two named points, cited `[brain] <path>`; without either, the engine runs on
  its bundled library and says so once.
- Teardown/inspire link pulls: a free [SocialCrawl](https://www.socialcrawl.dev/?ref=AQNU384G) API key
  (bring-your-own-key; the engine walks you through it).
- Full-slide teardown (optional): Claude Code + Python 3.10+ and your own Instagram cookies, exported
  once with the free Cookie-Editor browser extension (setup walks you through it)... no install, no
  password stored, just your session cookies, on your machine.
- Image generation (optional): the Higgsfield MCP connector + your own account is the preferred
  route (no plugin install, no CLI — auth rides your account session; paid plan for the
  trained-face option). The Higgsfield plugin/CLI works as a fallback. Claude Design path needs
  nothing extra. Workspace render needs Claude Code + Python (Playwright installs itself on first
  use, with your ok).
