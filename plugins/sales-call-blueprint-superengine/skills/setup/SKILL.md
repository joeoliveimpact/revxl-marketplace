---
name: sales-call-blueprint-superengine:setup
description: First-run configuration wizard for the sales-call blueprint superengine. Use to set up or reconfigure the skill for a business — auto-discovers brand/program/closer details from where they already live, sets the transcript source and output destination, and checks dependencies. Trigger phrases include "/sales-call-blueprint-superengine setup", "set up the blueprint skill", "configure blueprints", "reconfigure for a different business", "change my transcript source", "change where blueprints save".
---

<purpose>
First-run setup: populate references/business-config.md by AUTO-DISCOVERING the user's brand/closer/program data from places it already lives (rather than a blank form), confirm it, set the transcript source and output destination, and run a dependency check scoped to those choices. Re-runnable any time to reconfigure.
</purpose>

<user-story>
As a new user of this skill, I want it to find my brand and program details automatically and check that my integrations work, so that I'm ready to generate blueprints without manually filling a config or hitting missing-dependency surprises mid-call.
</user-story>

<when-to-use>
- First time using the skill (auto-offer this if business-config.md still has placeholder/example values)
- Redeploying for a different business
- Entry point routes here via /sales-call-blueprint-superengine setup
</when-to-use>

<steps>

<step name="locate_brand_data" priority="first">
Ask the user WHERE their brand/user/program info might live, then pull from those sources instead of asking them to type everything. Prompt:
"To set this up, point me at anywhere your brand, offer, and pricing info lives — I'll read it and draft your config. Any of: a website URL, this or another workspace's CLAUDE.md, a Google Drive folder, a Notion/doc, or just tell me and I'll ask. What've you got?"

**Wait for response.**
</step>

<step name="auto_discover">
Pull from the sources named (and the obvious defaults) to draft the config values. Read what you can, don't fabricate:
- **Global CLAUDE.md** (`~/.claude/CLAUDE.md`) and the **workspace CLAUDE.md** / `RULES.md` — brand, closer, program, naming conventions.
- **Other workspace folders** the user named — read their CLAUDE.md / config / docs.
- **Website** — if a URL was given, fetch it for brand name, offer description, program positioning.
- **Google Drive / connectors** — if pointed there, search for an offer/brand doc and read it (discover tools via ToolSearch).
- **Prior blueprints** in `output/reports/` or the Drive blueprint folder — infer format/positioning from real examples.
Draft each {{VARIABLE}}: BRAND_NAME, CLOSER_NAME, PROGRAM_NAME, STRATEGY_CALL_NAME, PROGRAM_DESC, PROGRAM_LENGTH, FREE_RESOURCE, CORE_PROBLEM_SOLVED, DISQUALIFIER_FLOOR. Mark anything you couldn't find `[NEEDS INPUT]`. **Do not invent pricing — it's intentionally not stored.**
</step>

<step name="confirm_config">
Present the drafted config as a table (value + where you found it). Ask the user to confirm or correct each, and to fill any `[NEEDS INPUT]`. Apply edits.

**Wait for confirmation.**
</step>

<step name="set_source_and_destination">
Capture the operational choices:
1. **Triage calls?** ({{USES_TRIAGE}}) — "Do you run a short triage/qualification call before the full sales call?" yes | no. If **no**, the skill will never ask "triage or full?" — every blueprint is for the full call. If **yes**, it asks each time.
2. **Transcript source** ({{TRANSCRIPT_SOURCE}}) — fathom | fireflies | granola | ghl | otter | manual | local-audio. "Where do your prior call recordings/transcripts come from?"
3. **Output destination(s)** ({{OUTPUT_DESTINATION}}, may be a list) — google-drive | local | ghl-note | chat | custom. "Where should finished blueprints go?" If google-drive: capture {{DRIVE_PARENT_FOLDER}} (default "Pre-Call Blueprints", dated subfolders). If custom: capture {{CUSTOM_DESTINATION}}.

**Wait for responses.**
</step>

<step name="dependency_check">
Verify ONLY the integrations the user's choices actually require (don't check what isn't used):
- **Transcript source:** if a service (fathom/fireflies/granola/ghl) → ToolSearch for that service's tools and confirm they load. If `manual` → nothing to check. If `local-audio` → check ffmpeg and a local whisper option (faster-whisper / whisper.cpp server / GPU) exist; otherwise warn that local transcription won't work and suggest a service or manual paste. **Skip the whisper check entirely if the transcript comes from a service** (most common — it won't be needed).
- **Output destination:** google-drive → confirm Drive tools load + access; ghl-note → confirm GHL tools load; custom → confirm the named connector's tools load; local/chat → nothing to check.
- **DM source (optional):** if pulling DM threads from GHL, confirm GHL tools load.
Report a READY / MISSING table. Missing items are warnings, not blockers — note the workaround (e.g. "Fathom not connected → paste transcripts manually").
</step>

<step name="write_config">
Write the confirmed values into references/business-config.md (preserve the file's structure and notes; only replace the values). Report: "Setup complete — config saved. {N} ready, {M} missing (with workarounds)." Then: "Run /sales-call-blueprint-superengine triage|strategy to build a blueprint."

Ask: "Look right?"
**Wait for approval.**
</step>

</steps>

<output>
A populated references/business-config.md plus a dependency-check report (ready/missing with workarounds), scoped to the user's actual transcript source and output destination.
</output>

<acceptance-criteria>
- [ ] Asked where brand/user data lives; pulled from named sources + global/workspace CLAUDE.md
- [ ] Drafted config from discovered data, marked gaps [NEEDS INPUT], invented nothing (no pricing)
- [ ] User confirmed/corrected the config
- [ ] Transcript source + output destination(s) captured
- [ ] Dependency check scoped to choices (whisper skipped when source is a service)
- [ ] business-config.md written; ready/missing reported
- [ ] User approved
</acceptance-criteria>
