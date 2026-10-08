# Business Config — stories-superengine

The one file every Stories skill reads first. The filled copy lives at
`${CLAUDE_PLUGIN_DATA}/business-config.md` so plugin updates never wipe it; this shipped copy is only
the template. Placeholder values mean setup has not run: route to the `stories-setup` skill.

**Shared-brain rule:** brand-level facts (voice, avatar, offer, proof) come from
`~/.claude/revxl/<brand>/voc/` (written by the `brand-brain` skill, shared with every REVXL engine).
Story-specific settings live here. Saved looks and lead-magnet notes live in
`~/.claude/revxl/<brand>/stories/`.

## A. Who and how
| Token | Value | Notes |
|---|---|---|
| `{{BRAND_SLUG}}` | (placeholder — run setup) | lowercase letters + digits only; the `~/.claude/revxl/<brand>/` folder |
| `{{EXPLANATION_LEVEL}}` | beginner | beginner / intermediate / advanced |
| `{{TEACH_MODE}}` | on | explain the WHY behind each frame as it's built |
| `{{DISPLAY_NAME}}` | (placeholder — run setup) | name on quote cards, exactly as on their profile |
| `{{IG_HANDLE}}` | (placeholder — run setup) | @handle, from the coach or their connected account, never a web search |
| `{{AVATAR_FILE}}` | none | profile photo saved in `~/.claude/revxl/<brand>/stories/avatar.jpg`, or none (initials) |
| `{{VERIFIED_BADGE}}` | off | on only if the coach's account really shows a blue check |

## B. Story defaults
| Token | Value | Notes |
|---|---|---|
| `{{STORY_STYLE}}` | strong | one native text style for a whole set (see frame-spec.md) |
| `{{STORY_COLORS}}` | purple, orange, blue | bubble colors on plain black frames, in rotation |
| `{{TIMEZONE}}` | (placeholder — run setup) | IANA name, e.g. America/New_York (from Metricool when connected) |
| `{{DEFAULT_POST_TIME}}` | 10:00 | when a set goes out unless the coach names a time |
| `{{AI_LABEL}}` | auto | auto (on when any frame uses a generated image) / on / off |

## C. Lead magnets (what a story set can sell)
| Token | Value | Notes |
|---|---|---|
| `{{LEAD_MAGNETS}}` | (placeholder — run setup) | one line each: name · reply keyword · where the file lives |
| `{{DM_AUTOMATION}}` | unknown | manychat / other / none: who sends the guide when someone replies |

## D. Publishing
| Token | Value | Notes |
|---|---|---|
| `{{PUBLISH_ROUTE}}` | unknown | metricool-connector / metricool-composio / instagram-direct / drafts-only (set by setup) |
| `{{METRICOOL_TOOLKIT}}` | — | composio toolkit name when the route is metricool-composio |
| `{{METRICOOL_BRAND_ID}}` | — | the brand id Metricool lists for the coach's account |
| `{{MEDIA_HOST}}` | unknown | composio-googledrive / gws (where frames get a public link Metricool can fetch) |
| `{{PYTHON}}` | unknown | path recorded in the workspace's `stories/.python` by setup |
