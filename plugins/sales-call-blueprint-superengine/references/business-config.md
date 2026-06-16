# Business Config

> This is the ONLY file you edit to deploy the skill for your business. Every `{{VARIABLE}}` below is substituted wherever it appears in skills and templates. The values below are placeholders — run `setup` (or `guide` for a walkthrough) and the skill will auto-discover and fill them for you. Until they're filled, the skill will route you to the first-run tour.

## Skill Mode
- **{{EXPLAINER_MODE}}** = on `(on | off — when on, the skill explains each step in plain English with a "what this means for you" line, and routes first-time users through the guided tour. Turn off once you're comfortable, or say "explainer off". Same thing as "quick mode" = off.)`
- **{{USES_TRIAGE}}** = [yes | no — run setup] `(do you run a short triage/qualification call before the full sales call? If yes, the skill asks "triage or full call?" each time. If no, it never asks — every blueprint is for the full call.)`

## Brand & People
- **{{BRAND_NAME}}** = [Your brand / business name]
- **{{CLOSER_NAME}}** = [Who takes the closing / strategy calls]

## Program
- **{{PROGRAM_NAME}}** = [Your program / offer name]
- **{{STRATEGY_CALL_NAME}}** = [What you call your sales call] `(also referred to as discovery call, sales call, strategy call)`
- **{{PROGRAM_DESC}}** = [One line: what your program does + the outcome it delivers]
- **{{PROGRAM_LENGTH}}** = [e.g. 6 months] `(used in goal-horizon questions and pricing framing)`

## Pricing
> Intentionally NOT stored. You know your own pricing — supply the real figure live when the blueprint reaches the price drop. The skill structures HOW to drop the number (see ${CLAUDE_PLUGIN_ROOT}/references/rfpdp-method.md), never WHAT the number is.

## Free Resource (for disqualify/redirect + follow-up)
- **{{FREE_RESOURCE}}** = [Your free resource — link/handle you point not-yet-ready prospects to]

## Call Recording / Transcript Source
- **{{TRANSCRIPT_SOURCE}}** = [fathom | fireflies | granola | ghl | otter | manual | local-audio]
  - Used to auto-pull a prior call's transcript (e.g. the triage call) and fold confirmed intel into a strategy blueprint. See ${CLAUDE_PLUGIN_ROOT}/references/transcript-pull.md.
  - `manual` = paste the transcript. `local-audio` = transcribe an audio file yourself (needs ffmpeg + local whisper). A service (fathom/etc.) means NO local whisper needed.

## Output Destination
- **{{OUTPUT_DESTINATION}}** = [google-drive | local | ghl-note | chat | custom] `(where finished blueprints go — one or more)`. See ${CLAUDE_PLUGIN_ROOT}/references/deliver-blueprint.md.
- **{{DRIVE_PARENT_FOLDER}}** = Pre-Call Blueprints `(used if destination includes google-drive; auto-creates {year}/{month}/{MM.DD.YY}/[Prospect] underneath)`
- **{{CUSTOM_DESTINATION}}** = [Not set] `(used if destination=custom; describe the connector/location, e.g. a Notion DB or Front)`

## Ideal-Fit Definition (drives the triage in/out decision)
- **{{CORE_PROBLEM_SOLVED}}** = [The ONE problem your program solves] `({{PROGRAM_NAME}} solves THIS, not adjacent problems)`
- **{{DISQUALIFIER_FLOOR}}** = [Your minimum-fit floor — e.g. under $X/month revenue with no path forward]

---

## Config Notes
- Pricing is deliberately absent — you supply it live at the price drop.
- Update `{{PROGRAM_LENGTH}}` to match your program — the goal-horizon questions and delivery timeline reference it.
- `[NEEDS INPUT]` any field you don't have a value for; the skill will flag it rather than invent one.
