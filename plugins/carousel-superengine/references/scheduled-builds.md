# Scheduled Builds — autopilot drafts, suggest-only

Recurring carousel DRAFT builds on a cadence the coach picks. This engine never schedules anything
by itself: it OFFERS, captures intent after an explicit yes, and hands the actual schedule to the
platform's scheduler. Posting is never scheduled — every run ends in a draft the coach approves.

## When the offer appears (and when it shuts up)

- Natural exits only: after a create, a render, a template save (the strongest moment — voice +
  look + topics are all captured), or an inspire report. Also on direct ask ("schedule my
  carousels", "weekly carousel", "autopilot").
- Only when `{{SCHEDULE_STATUS}}` is `unset`. At most ONCE per session. Declined → set
  `declined:1`; at `declined:2` stop offering entirely (direct ask always still works).

## Permission phrasing (plain-English, the shape to keep)

> "Want me to put this on autopilot? Every <Monday morning> I'd draft a fresh carousel from
> <your weekly topics / your newest call>, in <your saved look>, and drop it in <destination> as a
> draft. Nothing ever posts by itself... you approve every one. Saying 'stop the weekly carousel'
> kills it anytime. Want it?"

## Capture flow (5 quick answers → config section F)

1. **Cadence** — weekly (suggest their audience's best day) or daily → `{{SCHEDULE_CADENCE}}`
2. **Topic source** → `{{SCHEDULE_TOPIC_SOURCE}}`: auto (default: new call transcripts → weekly
   content bank → idea engine) / bank-only / transcripts-only / pillar:<name>
3. **Look** — saved template? → `{{SCHEDULE_TEMPLATE}}` (none = design directions only, render on
   demand later)
4. **Render mode** → `{{SCHEDULE_RENDER}}`: free-only (default — workspace render where available,
   otherwise the Claude Design prompt rides in the draft) / higgsfield-capped:<n> ONLY if the coach
   explicitly opts into paid images per run, with the per-run cap named
5. **Destination** — confirm `{{OUTPUT_DESTINATION}}` is where drafts should land

Write section F. Then hand off — never create silently, and if `{{SCHEDULE_HANDLE}}` is already
set, UPDATE that schedule instead of creating a second one.

## Platform handoff

- **Cowork/Desktop:** create via the scheduled-tasks MCP (discover exact tools via ToolSearch,
  "scheduled task") after the coach's explicit yes. Store the returned task name/id in
  `{{SCHEDULE_HANDLE}}`.
- **Claude Code:** hand the coach the exact `/schedule` invocation with the composed prompt (offer
  to run it for them). Store the routine name in `{{SCHEDULE_HANDLE}}`.
- Neither available → say so plainly and offer the manual ritual: "Say 'carousel about ___' every
  Monday and it's the same thing minus the automation." Never fake a schedule.

## The scheduled prompt (compose with real values, self-contained)

> Run a scheduled carousel build for <brand> using the carousel-superengine plugin.
> 1. Read the engine business-config. If it holds placeholder values, STOP — deliver a short note
>    to <OUTPUT_DESTINATION> asking the coach to run carousel-setup. Never guess a voice.
> 2. Pick ONE topic — first source that yields, honoring {{SCHEDULE_TOPIC_SOURCE}}: (a) a new call
>    transcript since the last line of schedule-log.md (only if {{TRANSCRIPT_SOURCE}} is a connected
>    service; read-only, per references/transcript-intake.md); (b) the freshest entry in
>    ~/.claude/revxl/<brand>/voc/weekly-content-bank.md not already used in schedule-log.md; (c) the
>    idea engine: topic frameworks × {{CONTENT_PILLARS}} × {{AVATAR_PAINS}} — strongest pick, one-line
>    why. Use the brand brain as-is; if stale >7 days, note it in the summary — never run an
>    interactive refresh here.
> 3. Run the carousel-create flow non-interactively: platform {{PRIMARY_PLATFORM}}, blueprint chosen
>    to fit the topic (never blueprint C without a real proof asset), skip confirmation pauses, full
>    carousel-quality gate.
> 4. Render per {{SCHEDULE_RENDER}}: template <name> via carousel-templates use-template when set;
>    free-only = workspace render if this environment has Bash + Python, otherwise include the
>    paste-ready Claude Design prompt in the package. Spend ZERO third-party credits (no SocialCrawl,
>    no Higgsfield) unless {{SCHEDULE_RENDER}} is higgsfield-capped — then at most <n> images,
>    degrading to the Claude Design prompt on any failure.
> 5. Save everything as a DRAFT to {{OUTPUT_DESTINATION}}; append one line to schedule-log.md
>    (date · topic · source · draft path). Never post; never touch posting tools.
> 6. End with a 3-line summary: topic + why · where the draft landed · "say 'make the images' or
>    'stop the weekly carousel' to act."

## Lifecycle

- **Dry-run first (offer it):** "Want me to test it right now?" → run the composed prompt once
  interactively; the coach sees exactly what Monday will produce.
- **Change** ("make it daily", "switch to my new template") → update section F + the platform-side
  schedule via `{{SCHEDULE_HANDLE}}`.
- **Stop** ("stop the weekly carousel") → set `{{SCHEDULE_STATUS}}: paused`, cancel/delete the
  platform task via the handle (or hand the coach the exact cancel step), confirm in one line.
- **Status** ("what's on autopilot?") → read section F + the last 3 lines of schedule-log.md.
