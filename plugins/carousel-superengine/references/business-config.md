# Business Config — carousel-superengine

Single source the engine reads at the start of every build. Values persist via `${CLAUDE_PLUGIN_DATA}`
so plugin updates never wipe them. Placeholder values below mean setup has not run — route to the
`carousel-setup` skill.

**Shared-brain rule:** brand-level tokens (positioning, avatar, proof) read/write the shared
`~/.claude/revxl/<brand>/voc/business-config.md` when that file exists, so every REVXL engine sees one
truth. Engine-specific tokens (platform, pillars, CTA destination, data sources, rendering, schedule)
live only here.

## A. Tone + brand
| Token | Value | Notes |
|---|---|---|
| `{{EXPLANATION_LEVEL}}` | beginner | beginner / intermediate / advanced |
| `{{TEACH_MODE}}` | on | teach the WHY as we build |
| `{{PROGRAM_POSITIONING}}` | (placeholder — run setup) | who they serve + one-line positioning |
| `{{VOICE_SOURCE}}` | (placeholder — run setup) | shared brain path, or interim anchor sources |
| `{{VOICE_EDGE}}` | conversational | vanilla / conversational / locker-room |

## B. Avatar
| Token | Value | Notes |
|---|---|---|
| `{{AVATAR_PAINS}}` | (placeholder — run setup) | 3-5 shared pains, avatar's own words |
| `{{DREAM_OUTCOME_STATUS}}` | (placeholder — run setup) | outcome in status terms |
| `{{THE_ENEMY}}` | (placeholder — run setup) | named villain the avatar resents |
| `{{AWARENESS_LEVEL}}` | (placeholder — run setup) | problem / solution / product aware |
| `{{PROOF_ASSETS}}` | (placeholder — run setup) | real client results with numbers; never invented |

## C. Platform + content
| Token | Value | Notes |
|---|---|---|
| `{{PRIMARY_PLATFORM}}` | instagram | instagram / linkedin / both |
| `{{CONTENT_PILLARS}}` | (placeholder — run setup) | 3-5 recurring themes |
| `{{CTA_DESTINATION}}` | (placeholder — run setup) | DM keyword / lead magnet / follow / community |

## D. Data sources
| Token | Value | Notes |
|---|---|---|
| `{{SOCIALCRAWL_KEY_STATUS}}` | unset | unset / saved (key itself lives in `~/.config/socialcrawl/api_key`, never in this file) |
| `{{FULL_SLIDE_FETCH}}` | unknown | available (Bash + Python 3.10+) / unavailable — set by setup |
| `{{TRANSCRIPT_SOURCE}}` | manual | manual (paste) / fathom / fireflies / granola / other named service — powers "carousel from my last call" |

## E. Output + rendering
| Token | Value | Notes |
|---|---|---|
| `{{OUTPUT_DESTINATION}}` | chat | chat / workspace file / both |
| `{{RENDER_PREF}}` | ask | image-gen / claude-design / ask (each build) |
| `{{HIGGSFIELD_STATUS}}` | unknown | detected / absent — probed by setup via ToolSearch, refreshed at render time |
| `{{WORKSPACE_RENDER}}` | unknown | available (Bash + Python — local PNG/PDF render) / unavailable — set by setup env detect |

## F. Scheduled builds (suggest-only — the schedule itself lives in the platform scheduler)
| Token | Value | Notes |
|---|---|---|
| `{{SCHEDULE_STATUS}}` | unset | unset / active / paused / declined:<n> (n = times declined; stop offering at 2) |
| `{{SCHEDULE_CADENCE}}` | — | human-readable, e.g. weekly-monday-9am / daily-7am (cron lives platform-side) |
| `{{SCHEDULE_TOPIC_SOURCE}}` | auto | auto (new transcripts → weekly bank → idea engine) / bank-only / transcripts-only / pillar:<name> |
| `{{SCHEDULE_TEMPLATE}}` | none | template name from `~/.claude/revxl/<brand>/carousel/templates/` or none |
| `{{SCHEDULE_RENDER}}` | free-only | free-only (workspace render on Code, Claude Design prompt otherwise) / higgsfield-capped:<n> (explicit opt-in, max n paid images per run) |
| `{{SCHEDULE_HANDLE}}` | — | platform-side task name/id — dedup, change, cancel |

Run log: `${CLAUDE_PLUGIN_DATA}/schedule-log.md` — one line per scheduled run (date · topic · source ·
draft path). Read it to avoid repeating topics; append after every scheduled build.

## Security
- The SocialCrawl key NEVER gets written into this file, any output, or any log — only its status.
- `{{PROOF_ASSETS}}` ship in carousels only as the coach provided them; no rounding up, no invention.
- Scheduled runs never post and never spend third-party credits beyond an explicit `higgsfield-capped` opt-in.
