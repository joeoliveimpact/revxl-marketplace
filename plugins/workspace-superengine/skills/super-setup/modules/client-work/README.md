# client-work module

Adds the structure needed to run multiple coaching / consulting clients out of one workspace without cross-contamination.

## What it creates

- `clients/_template/` — copy this folder for each new client. Contains:
  - `README.md` — top-of-folder summary fields
  - `intake.md` — discovery questions answered up front
  - `sessions.md` — append-only session log
  - `deliverables.md` — what you owe them and the status of each
- `.claude/rules/client-work.md` — workspace-wide rule enforcing confidentiality and scope boundaries

## Workflow

1. New client lands. Copy `clients/_template/` to `clients/<client-name>/`.
2. Fill `README.md` and `intake.md` during onboarding.
3. Append to `sessions.md` after every call.
4. Track promised work in `deliverables.md`.

## Why a rule file

When Claude is working in this workspace it can see any client's folder. The rule file tells it not to cross-reference clients, not to paste one client's work into another, and to ask before acting on anything ambiguous.
