# Business Config — carousel-superengine

Single source the engine reads at the start of every build. Values persist via `${CLAUDE_PLUGIN_DATA}`
so plugin updates never wipe them. Placeholder values below mean setup has not run — route to the
`carousel-setup` skill.

**Shared-brain rule:** brand-level tokens (positioning, avatar, proof) read/write the shared
`~/.claude/revxl/<brand>/voc/business-config.md` when that file exists, so every REVXL engine sees one
truth. Engine-specific tokens (platform, pillars, CTA destination, teardown) live only here.

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

## D. Teardown
| Token | Value | Notes |
|---|---|---|
| `{{SOCIALCRAWL_KEY_STATUS}}` | unset | unset / saved (key itself lives in `~/.config/socialcrawl/api_key`, never in this file) |
| `{{FULL_SLIDE_FETCH}}` | unknown | available (Bash + Python 3.10+) / unavailable — set by setup |

## E. Output
| Token | Value | Notes |
|---|---|---|
| `{{OUTPUT_DESTINATION}}` | chat | chat / workspace file / both |

## Security
- The SocialCrawl key NEVER gets written into this file, any output, or any log — only its status.
- `{{PROOF_ASSETS}}` ship in carousels only as the coach provided them; no rounding up, no invention.
