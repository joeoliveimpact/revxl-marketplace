# Stories Superengine

Instagram + Facebook Stories for coaches: from a lead magnet or your own words to finished, checked
story frames, scheduled after you say go.

> Demo: coming soon.

## What this plugin does

Stories are shown to people who already follow you, one tap at a time. This engine builds story sets
that keep them tapping and end on one small action, usually "reply KEYWORD" to get your guide. It
reads your guide (or takes your words exactly as you wrote them), splits it into one beat per frame,
places the text where it never covers a face, and renders 1080×1920 frames in Instagram's own text
look. A render check blocks any frame with text running off the screen or under Instagram's top and
reply bars, and you approve a contact sheet before anything goes anywhere.

Then it schedules one story post with every frame, in order, on Instagram and Facebook through
Metricool. It uses whatever you already have connected: Metricool's Claude connector, a composio
Metricool connection, or (when there's no Metricool) Instagram directly, which posts right away. Your
name, handle, photo, time zone and lead magnets are captured once. Claude installs what it needs on
your computer; you never type a command.

## Skills

| Skill | Say | What it does |
|---|---|---|
| `stories-start-here` | "make me a story", "stories for tomorrow" | Front door: routes to the right skill |
| `stories-setup` | "set up stories", "connect Metricool" | Checks/installs Python + the frame renderer, connects posting, records who you are |
| `stories-guide-set` | "story set for my guide", "turn this into a story" | Copy (from your guide or your words) → frames → checked → contact sheet |
| `stories-quote-card` | "quote card", "make this a tweet graphic" | One of your lines as a post-style card, stamped with the real post time |
| `stories-schedule` | "schedule it for 10am", "did my story go out?" | Hosts the frames, schedules or posts after your go, reads back the result |
| `brand-brain` | "capture my voice", "build my brand brain" | Your voice + your audience's words, shared with every REVXL engine |

No agents.

## What it never does

- Posts or schedules anything you haven't seen and approved in the conversation.
- Rewrites your voice for taste. It offers numbered suggestions you can accept or skip.
- Invents numbers, results or client stories, or fills in someone's handle or photo from a web search.
- Shows a blue verified check you don't have, or fake like/view counts.

## Install

**Claude Code (Desktop app, Code tab, or terminal):** add the REVXL marketplace, then install
`stories-superengine` from the plugin picker. Open a folder for your stories and say "set up stories".

**Claude Desktop chat / Cowork:** the skills load, but rendering and scheduling run Python on your
computer, which needs the Code tab. Use Claude Code.

## Requirements

- **Claude Code** with internet (fonts and the renderer's libraries load from public CDNs).
- **Python 3.9+** and the **Playwright** browser library: `stories-setup` finds or installs both for
  your user account, no admin password.
- **To schedule:** a Metricool account (free plan works) connected through Claude's connector or
  composio. Without it: Instagram directly through composio (posts immediately, no Facebook), or
  drafts you post by hand.
- **To host frames** for Metricool/Instagram: Google Drive through composio (or the gws CLI).
- **A DM tool** (ManyChat or similar) that answers your reply keyword on **story replies**.
- Optional: the `workspace-superengine` plugin for session continuity.

## Compatibility

| | Claude Code | Claude Desktop chat / Cowork |
|---|---|---|
| Skills | ✓ | skills load; render + schedule need the Code tab |
| Agents | none | none |
| Windows / Mac | ✓ / ✓ (Linux: manual Python + Playwright install) | — |

## Files you own

- `stories/<SET NAME> <date>/` in your workspace: copy, photos, frames, contact sheet, schedule record
- `~/.claude/revxl/<brand>/stories/`: your avatar and saved looks
- `~/.claude/revxl/<brand>/voc/`: your brand brain (shared with the other REVXL engines)

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).

Part of the [REVXL marketplace](https://github.com/joeoliveimpact/revxl-marketplace).
