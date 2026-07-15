# profile-optimization-superengine

> Audit a coach's Facebook or Instagram personal profile, element by element, and get back specific, copy-paste-ready fixes that actually convert. For online fitness, health, and wellness coaches (B2C).

---

## What this plugin does

Most coaches' profiles quietly leak leads: a vibes-only bio, a suppressed CTA, a link that dumps people into a menu of options, an empty Featured section. This plugin audits every element of a personal profile against proven 2026 frameworks, scores each one, and hands back exact fixes... character counts, dimensions, templates, and copy the coach can paste in.

Name the platform and it routes you:

- **Facebook** scores 8 elements out of 80: bio (101 chars), profile picture + cover photo (320x320 / 820x360), Featured section, About section, pinned post, CTAs, and content pillars, plus a Professional Mode check.
- **Instagram** scores 11 elements out of 110: Name field (64 chars), bio (150), profile photo, single link, Story Highlights, pinned trio, grid/feed, account type, CTA/DM strategy, Instagram SEO, and content pillars.

Both enforce the same rules so they never contradict each other: **one direct link to the lead magnet** (Linktree/Beacons/Stan appear only as a named anti-pattern to remove), amplified CTA language over algorithm-suppressed language, and one DM keyword kept identical everywhere.

**Optional:** benchmark against competitors. `profile-competitor-scan` pulls a few top accounts in your niche via the SocialCrawl API and shows how you stack up ("4 of 5 run a single direct link... you don't"). It's opt-in and credit-gated; the audits never depend on it.

**Recommendations only.** It never posts and never sends... the coach makes the changes.

**Audience:** B2C fitness, health, and wellness coaches. Beginner explanation level is on by default; say "set level to intermediate/advanced" any time.

> **Command naming:** every command is prefixed `profile-` so they group under `/profile-` and never collide with another plugin's commands. Type `/profile-` to see the whole set.

---

## Skills

#### `profile-setup` ... start here
**Triggers:** "set up the profile engine", "profile setup", "configure profile optimization"

One-time setup wizard. Captures your niche, ideal client, offer + lead magnet, account type, which platforms you run, brand voice, and the teach-mode + voice-edge toggles into a persisted config, so the audits skip the basics and open by confirming. Run it once; re-run any time to reconfigure. Skippable... a coach who skips just gets asked inline.

#### `profile-start`
**Triggers:** "/profile-optimization-superengine", "optimize my profile", "audit my profile", "my profile isn't converting"

The orchestrator. Greets, offers setup if you haven't run it, asks Facebook or Instagram (or both), runs the environment detect once, and hands off to the right audit.

#### `profile-fb-audit`
**Triggers:** "fix my facebook", "facebook audit", "optimize my facebook", "facebook for coaches"

Full Facebook personal-profile audit and action plan.

#### `profile-ig-audit`
**Triggers:** "fix my instagram", "instagram audit", "optimize my instagram", "my IG isn't converting"

Full Instagram personal-profile audit and action plan.

#### `profile-competitor-scan` ... optional
**Triggers:** "benchmark my competitors", "competitor scan", "how do I compare to other coaches", "scan my niche"

Optional, credit-gated. Pulls a few competitor / aspirational FB + IG profiles via the SocialCrawl API and benchmarks the coach against their niche ("4 of 5 top accounts run a single direct link... you don't"). Needs Claude Code + a SocialCrawl key; the audits run fine without it and weave the benchmarks in when present. Never a prerequisite.

#### `brand-brain`
**Triggers:** "capture my voice", "build my brand brain", "set up my voice", "refresh my voice guide"

The bundled voice layer. Derives a living, cross-engine brand brain from the coach's real sources so the copy the audits write sounds like the coach. Persistent on Cowork/Code; inline-per-session on Claude.ai Chat.

---

## How it sees your profile

A silent probe classifies the session and confirms it with you:

| Environment | How it pulls your profile |
|-------------|---------------------------|
| Claude Code / Cowork Desktop (with a browser tool) | Opens your live profile in a browser from the URL |
| Claude.ai Chat (or no browser tool) | You send screenshots of your profile top + Featured/pinned (FB) or first 9 grid (IG) |

If a live view is blocked by a login wall, it degrades gracefully to screenshots... it never dead-ends.

---

## Quick install

### Claude Desktop (recommended for coaches)

1. Customize... Skills... **+** next to "Personal plugins"
2. Paste: `joeoliveimpact/revxl-marketplace`
3. Click Sync... click **Install** on `profile-optimization-superengine`

**Start here:** run `profile-setup` once (say _"profile setup"_) so the engine learns your niche, avatar, and offer and never re-asks. Then say _"optimize my profile"_ (or name the platform) and follow along. You can skip setup and go straight to an audit... it'll just ask you inline.

### Claude Code

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install profile-optimization-superengine@revxl-marketplace
```

---

## Compatibility

| Platform | Skills | Notes |
|----------|--------|-------|
| Claude Desktop (Cowork) | 5 of 6 | Browser audit when a browser tool is present, else screenshots. Persistent brand brain + persisted setup config. Competitor scan needs a shell (Claude Code), so it's unavailable here. |
| Claude Code | all 6 | Browser audit only if a browser tool is present, else screenshots. Persistent brand brain + persisted setup config. Competitor scan available (SocialCrawl key + credits). |
| Claude.ai Chat | 5 of 6 | Screenshot intake. Voice captured inline per session (no persistent brain / no persisted config). Competitor scan needs a shell, so it's unavailable here. |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT, see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md): REVXL's curated Claude superengine catalog.
