---
name: notebooklm-studio
description: Use to generate NotebookLM Studio outputs from a notebook — "make a podcast from my X notebook", "turn this into a study guide", "generate a mind map", "create a slide deck from my research", "make a video overview", "quiz me on this notebook", "/notebooklm-studio". Cross-platform; requires notebooklm-setup done first. Generations are long and rate-limited — this skill runs them async.

---

# notebooklm-studio — Generate & Download Outputs (v0.1)

Turns a notebook into a podcast, video, mind map, slide deck, report, quiz, or flashcards, then downloads it. Generations are **long-running and rate-limited** (audio 10–20 min, video 15–45 min) — this skill kicks off, tracks, notifies, and downloads; it never blocks the session waiting.

See `docs/command-surface.md` for exact `generate` formats/options and the autonomy rules (`generate *` and `download *` are **ask-before**).

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity`. If `beginner`, emit; else skip:

> I'll have NotebookLM turn your notebook into the thing you want — a podcast, video, slide deck, study guide, mind map, or quiz. The bigger ones (audio/video) take a while; I'll start it, let you keep working, and tell you when it's ready to download.

## Layer 2: Suggest before invoking

If borderline ("can you make a podcast of this", "I need a study guide from my notes"):

> "Want me to generate that from your NotebookLM notebook with `/notebooklm-studio`? Heads-up: audio/video take 10–45 min — I'll run it in the background."

If explicitly invoked, skip the suggestion.

## Preconditions

1. `.claude/workspace.yml#environment` `cowork` → "Needs Claude Code (the terminal app)." Stop.
2. `~/.notebooklm/.superengine` missing **and** `<NB> auth check --test` invalid → "Run `/notebooklm-setup` first." Stop. (Marker missing but auth valid → proceed.)
3. Set `NB`: Win `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe` / Mac `~/.notebooklm-venv/bin/notebooklm`.

## Phase 1 — Resolve notebook + output (Intent Clarification)

- Target notebook: named → match `<NB> list`; ambiguous/none → list, ask; else `<NB> status` active. Confirm which notebook on the first generate of a session.
- Output type + options (from `docs/command-surface.md`): audio (`--format deep-dive|brief|critique|debate`, `--length`), video (`--format`, `--style`), report (`--format briefing-doc|study-guide|blog-post|custom`), slide-deck (`--format`, → pdf/pptx), mind-map (sync/instant), quiz/flashcards (`--difficulty`, `--quantity`). Confirm type + key options before spending the (rate-limited) generation.

## Phase 2 — Kick off (ASK BEFORE — autonomy rule)

`generate *` is ask-before. Confirm explicitly ("This starts a ~15–45 min video generation and can hit rate limits. Proceed?"). Then run `<NB> generate <type> [options] [--retry 2]`. Capture the artifact id from output.

## Phase 3 — Track async (never block)

- **Mind map:** sync/instant — skip waiting, go to Phase 4.
- **Everything else:** tell the user it's running with a realistic ETA, and that they can keep working / leave — you'll check back. Track via `<NB> artifact wait <id>` (or poll `<NB> artifact list`). On rate-limit/failure: report plainly, suggest retry later (`generate ... --retry N`), don't silently loop forever.

## Phase 4 — Download (ASK BEFORE — autonomy rule)

`download *` writes files. Ask path + format. Default destination: the workspace `output/` (e.g. `output/research/` for reports, `output/` for media) — confirm. Run `<NB> download <type> "<path>" [--format pptx]`. Slide decks: ask pdf vs pptx. Quiz/flashcards: json vs md vs html.

## Phase 5 — Report

≤3 items: what was generated, the saved path, one next move (e.g. "open it" / "generate another format" / "ask the notebook a follow-up").

## Ground rules (inherited from RULES.md)

- **Surgical Execution:** generation only on the chosen notebook; never alter sources/notebook content. Write only to the confirmed download path.
- **Intent Clarification:** confirm notebook + output type + options before spending a rate-limited generation.
- **Least Complexity:** one artifact per request unless asked. Kick-off → track → download; no elaborate polling UIs.
- **Declarative Focus:** DoD = requested artifact generated and downloaded to the confirmed path (or an honest "rate-limited, here's how to retry").
