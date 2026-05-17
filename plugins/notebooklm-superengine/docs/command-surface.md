# NotebookLM CLI — Command Surface & Autonomy Rules

Reference for every notebooklm-superengine skill. The CLI is `notebooklm` (on PATH after `notebooklm-setup`). Source: distilled from the upstream notebooklm-py skill, trimmed to the local-only surface this plugin uses.

## Autonomy rules

**Run without asking (read-only / safe):**
`notebooklm status`, `auth check`, `list`, `source list`, `artifact list`, `language list/get`, `artifact wait`, `source wait`, `research status/wait`, `use <id>`, `create`, `ask "..."` (without `--save-as-note`), `history`, `source add`.

**Ask before running:**
`delete` (destructive), `generate *` (long-running, may rate-limit), `download *` (writes files), `ask --save-as-note` (writes a note), `history --save` (writes a note).

## Quick reference

| Task | Command |
|---|---|
| List notebooks | `notebooklm list` |
| Create notebook | `notebooklm create "Title"` |
| Set active notebook | `notebooklm use <notebook_id>` |
| Show context | `notebooklm status` |
| Add URL / YouTube / file source | `notebooklm source add "<url-or-path>"` |
| List sources | `notebooklm source list` |
| Web research (fast) | `notebooklm source add-research "query"` |
| Web research (deep) | `notebooklm source add-research "query" --mode deep --no-wait` |
| Research status / wait | `notebooklm research status` / `research wait --import-all` |
| Ask a question | `notebooklm ask "question"` |
| Ask with citations | `notebooklm ask "question" --json` |
| Ask, save answer as note | `notebooklm ask "question" --save-as-note` |
| Generate podcast | `notebooklm generate audio "instructions"` |
| Generate video | `notebooklm generate video "instructions"` |
| Generate report | `notebooklm generate report --format briefing-doc` |
| Generate quiz / flashcards | `notebooklm generate quiz` / `generate flashcards` |
| Generate mind map | `notebooklm generate mind-map` |
| Generate slide deck | `notebooklm generate slide-deck` |
| Artifact status / wait | `notebooklm artifact list` / `artifact wait <id>` |
| Download artifact | `notebooklm download <audio\|video\|slide-deck\|report\|mind-map\|data-table\|quiz\|flashcards> <path>` |
| Auth check (live) | `notebooklm auth check --test` |

## Generation options

All `generate` commands accept `-s/--source` (specific sources), `--language`, `--json`, `--retry N`.

| Type | Command | Key options |
|---|---|---|
| Podcast | `generate audio` | `--format [deep-dive\|brief\|critique\|debate]`, `--length [short\|default\|long]` |
| Video | `generate video` | `--format [explainer\|brief]`, `--style [...]` |
| Slide deck | `generate slide-deck` | `--format [detailed\|presenter]`; download `.pdf`/`.pptx` |
| Report | `generate report` | `--format [briefing-doc\|study-guide\|blog-post\|custom]` |
| Mind map | `generate mind-map` | sync, instant; `.json` |
| Quiz / Flashcards | `generate quiz` / `flashcards` | `--difficulty`, `--quantity`; `.json/.md/.html` |

## Timing / limits

- Generations rate-limit and run long: audio 10–20 min, video 15–45 min, quiz/flashcards 5–15 min.
- Skills that generate should kick off → `artifact wait` (or poll `artifact list`) → notify → `download`. Never block a session waiting.
- Unofficial API — Google can change behavior; fail gracefully and suggest retry on rate-limit.
