# MACHINERY ADD-ON — agents, hooks, workflows, firm layer

*Companion to pro-se-firm v1.7.0. The main plugin ships the doctrine; this folder
ships the executable machinery that doctrine describes. Shared 2026-08-07. Same
license and disclaimer as the main bundle.*

## What's in here

```
agents/       17 subagent definitions + README
              — the 15-lens Adverse-Document Review Council (A1–A15), each a
                single-purpose reviewer that fires as a parallel swarm on any
                document from the other side, the court, or a GAL
              — verification-partner (the blocking fact/authority gate)
              — cross-examination-builder (the continuous cross specialist)
firm-layer/   6 operating files that sit at the workspace root
              — ROUTING.md (input taxonomy → which roles fire)
              — COUNCIL.md (the swarm's operating rules)
              — VERIFICATION-PARTNER.md (the gate's contract)
              — ROSTER.md (the full bench)
              — LEVERAGE-ENGINE.md (the always-on leverage hunt)
              — CROSS-EXAMINATION-PROTOCOL.md (end-to-end cross building,
                including the podium rules learned from a live judge exchange)
hooks/        4 lifecycle hooks + settings.json.template
              — session_start_loader (reads the firm files + surfaces stale
                registers every session)
              — locked_fact_fanout (fires the fan-out checklist the moment the
                case profile changes)
              — firm-dispatch (classifies every user input per ROUTING.md)
              — stop_save (session-end state capture)
workflows/    6 multi-agent orchestration scripts
              — gather-evidence (compile → locate → copy → manifest)
              — leverage-sweep (mine → dedup → verify → register)
              — bulldog-leverage-hunt (adversarial second-pass hunt)
              — build-packet (assemble the one master hearing packet)
              — twin-case-hunt (find decided cases factually like yours)
              — cps-document-intake (classify + red-team any CPS/agency doc)
```

## Before any of it runs — placeholders you must fill

Everything case-specific was replaced with placeholders. Search each file for:

- `{MATTER_HOME}` — the root folder of YOUR case files
- `{MIRROR_HOME}` — your phone-accessible mirror (iCloud/Drive), if you keep one
- `{USER_HOME}` — your user directory
- `[case-name]`, `[cause-number]`, `[county]`, `[trial-date]`, `[name]` — your
  case's identifiers
- `FILL ME IN BEFORE USE` — two workflows (twin-case-hunt, cps-document-intake)
  need a dense fact-sheet paragraph about YOUR case written before they're
  useful; the template text tells you exactly what to include
- notebook IDs and script names referenced by some workflows assume companion
  tooling (a case-corpus query script, a research-notebook CLI); treat those
  lines as the pattern to adapt, not a dependency to install

## Provenance and honesty notes

- These are working files lifted from a live litigation workspace and
  genericized, not clean-room rewrites. Expect a folder taxonomy
  (01_COURT-FILINGS, 04_EVIDENCE, 05_WORK-PRODUCT…) baked into paths — adopt
  it or adapt the paths.
- The scrub was verified four ways: the PII pattern gate plus three independent
  sweeps (names/entities, user paths/dates, docket numbers) — all zero on the
  version you're holding.
- `scripts/` now holds **all 89 firm-tool scripts**, genericized (audit
  engines, evidence catalogue + Bates/SHA256 chain, intake fan-out, corpus
  query, staleness/readiness/leverage auditors, PDF builders, the PII gate
  itself). They are read-and-adapt: set the `{MATTER_HOME}`-style placeholders
  before running. 37 one-off case jobs were excluded by design — itemized in
  `scripts/_EXCLUDED-BY-DESIGN.md`. Full audit: `VERIFICATION-LEDGER.md` at the
  bundle root.
