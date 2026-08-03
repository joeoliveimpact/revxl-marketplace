# Changelog: promptception

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-08-02

### Added
- **Orchestrator Mode** (`/orchestrator-mode`): runs big cross-system work (audits, migrations, multi-session plans) through a tiered subagent crew instead of solo reading. Qualification gate (Opus-class/Fable lead required), Step-0 batched questions, tiered audit, both-directions verification on anything live, plan-mode premortem, execution-mode recommendation, artifact persistence to `output/orchestrator-mode/MM.DD.YY/`.
- **Premortem** (`/premortem`): standalone red-team pass on any completed draft plan, prompt, or spec ... assumes it failed six weeks out and works backwards. KILLER/MAJOR/MINOR findings with evidence and fixes; single source of truth for the protocol referenced by orchestrator-mode.
- **5 agents**: `orch-scout` (Sonnet retrieval), `orch-reader` (Opus code reads + PORT/WIRE verdicts), `orch-builder` (Opus plan execution), `orch-checker` (Opus independent done-tests, read-only), `orch-premortem` (Opus max-effort adversarial review). All carry the clarity contract: never fill a gap with a guess, always report a COULD-NOT-DETERMINE section.
- **Trigger hook**: UserPromptSubmit hook that spots orchestrator/premortem trigger phrases in a prompt and reminds Claude to invoke the matching skill.

## [0.1.0] - 2026-07-06

### Added
- Initial release. One skill (`/promptception`) that turns a messy, spoken-style brain-dump into a clear, complete prompt, shows the prompt it built, closes real gaps with 3 to 5 targeted questions (up to 3 rounds, never assume), runs it, and ends with a one-line lesson. Beginner teach-mode is the default (every question carries its "why"); "standard mode" drops the explanations for speed. Detects when an ask is bigger than one prompt and offers to build a step-by-step plan instead. Any outward action (send, post, publish, schedule) gets an explicit ask with the real routes available in the session.
