# Framework: Delivering the Finished Blueprint (Destination-Agnostic)

<purpose>
Teaches how to send a completed blueprint to wherever the user wants it. Destination is set by {{OUTPUT_DESTINATION}} in ${CLAUDE_PLUGIN_ROOT}/references/business-config.md (or asked at runtime if unset). Mirrors the transcript-pull pattern: one retrieval/write pattern, many backends, never blocks.
</purpose>

## Core Concepts

### File naming (all destinations)
`[Prospect Full Name] - [TRIAGE|STRATEGY] - [MM.DD.YY]` for the deep Pre-Call Prep; `[Prospect Full Name] - LIVE - [MM.DD.YY]` for the Call-Time Blueprint (one consistent pattern — LIVE in the middle, no call-type token). Thread/title = the prospect's name.

### Destination map
| {{OUTPUT_DESTINATION}} | How to deliver |
|------------------------|----------------|
| `local` | Write the `.md` to `output/reports/` in the workspace. Default, no network. |
| `google-drive` | Mirror the user's dated structure: under {{DRIVE_PARENT_FOLDER}} (e.g. "Pre-Call Blueprints"), ensure/create `{YYYY}/{Month}/{MM.DD.YY}/`, then create a Google Doc named per the prospect and write the blueprint into it. Use the Google Drive tools — discover exact tools via ToolSearch (keyword "drive"); create missing folders top-down; convert markdown to a Doc. |
| `ghl-note` | Attach the blueprint as a note on the prospect's GHL contact (search the contact by name/email/phone, then create a contact note). Keeps it next to the lead. Discover GHL tools via ToolSearch. |
| `chat` | Don't write a file — render the blueprint inline in the response for copy/paste. |
| `custom` | Follow {{CUSTOM_DESTINATION}} — any other location/connector the user described in setup (e.g. Notion, a specific folder, Front). Discover the connector's tools via ToolSearch. |

### Multiple destinations
{{OUTPUT_DESTINATION}} may be a list (e.g. `local, google-drive`). Deliver to each. Always also confirm the path/link back to the user.

### Discovering the exact tools
Tool names are environment-specific. Before writing to Drive/GHL/a connector, run ToolSearch with the service keyword to load the precise tools, then call them. Don't assume tool names.

## Always confirm back
After delivering, tell the user exactly where it went: the local path, the Drive doc link, or the GHL contact. If a destination fails (not connected, permission), fall back to `local` and say so — never silently drop the blueprint.

## Approval / privacy
Blueprints are internal drafts. Writing to the user's own Drive/GHL/workspace is fine autonomously. Do NOT send to a prospect or any external party. If a chosen destination would expose it externally, stop and confirm first.

## Examples
- **Drive, dated:** dest=`google-drive`, {{DRIVE_PARENT_FOLDER}}="Pre-Call Blueprints", today MM.DD.YY → ensure `Pre-Call Blueprints/{year}/{Month}/{MM.DD.YY}/`, create Doc "Jane Prospect — STRATEGY CALL BLUEPRINT", return the link.
- **GHL note:** dest=`ghl-note` → find the contact by email (e.g. prospect@example.com) → create a contact note with the blueprint body.
- **Both:** dest=`local, google-drive` → write the file AND the Drive Doc; report both locations.

## Anti-Patterns
- ❌ Hardcoding Drive/GHL tool names → discover via ToolSearch
- ❌ Failing silently when a destination errors → fall back to local + tell the user
- ❌ Guessing the Drive folder structure → follow {{DRIVE_PARENT_FOLDER}} + the dated pattern, create missing folders
- ❌ Sending a blueprint anywhere a prospect could see it

