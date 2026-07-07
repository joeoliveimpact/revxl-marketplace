# Carousel Superengine

Voice-matched Instagram + LinkedIn carousel engine for coaches. Run setup once, then generate
complete carousel packages... hook slide, value slides, CTA slide, per-slide design directions you
can execute in Canva, a caption built for 2026 search, and hashtags. Plus a paste-a-link teardown
that analyzes any public carousel and rebuilds its winning structure as YOURS.

Drafts only. Nothing posts automatically. Your config and voice persist across plugin updates.

## Commands

| Command | What it does |
|---|---|
| `/carousel-start-here` | Entry point... routes you to the right place |
| `/carousel-setup` | First-run wizard: voice, avatar pains, platform, CTA destination |
| `/carousel-guide` | Hand-held tour for first-timers: setup + your first carousel |
| `/carousel-create` | The generator: topic / reel script / transcript / teardown → full package |
| `/carousel-teardown` | Paste a public carousel link → why-it-works breakdown → your version |
| `/brand-brain` | Capture or refresh your voice + customer language (shared across REVXL engines) |

## Quickstart

1. Install the plugin, run `/carousel-start-here`.
2. Say "walk me through it" (first time) or run `/carousel-setup`.
3. "Carousel about [the thing your clients keep complaining about]" ... done. You get the full
   package as a draft: slide map, per-slide copy + design directions, caption, hashtags, alt text.

## The teardown feature

See a carousel that's clearly working? Paste the link.

- **Everywhere (Cowork, Desktop, Code):** the engine pulls the post through YOUR OWN SocialCrawl
  key (2-minute free signup, ~1 low-cost credit per pull)... caption, cover slide, engagement...
  and breaks down the hook, structure, and CTA mechanics. Honest limit: this path sees the cover
  slide, not slides 2+.
- **On Claude Code with Python:** a bundled fetch script can pull EVERY slide of a public post for
  a true slide-by-slide teardown (public posts only, rate-limited, personal research use).

Then: "build my version" rebuilds the STRUCTURE with your content, your voice, your CTA. Nothing
is ever copied.

## What it never does

- Post, schedule, or send anything
- Invent client results, testimonials, or fake scarcity
- Copy a competitor's wording, examples, or images
- Ship your voice/config data anywhere... the brand brain lives on your machine

## Requirements

- None for generation.
- Teardown link pulls: a free [SocialCrawl](https://www.socialcrawl.dev/?ref=AQNU384G) API key
  (bring-your-own-key; the engine walks you through it).
- Full-slide teardown (optional): Claude Code + Python 3.10+ and your own Instagram cookies, exported
  once with the free Cookie-Editor browser extension (setup walks you through it)... no install, no
  password stored, just your session cookies, on your machine.
