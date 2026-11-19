# Notice

Clawyer is built on **pro-se-firm v1.7.0** by **Mic H.**, released under the MIT license. The original
license text, with its copyright line, is kept unchanged at `skills/pro-se-firm/upstream/LICENSE`, and the
original README, disclaimer, changelog and verification ledger sit beside it.

## What came from pro-se-firm

- `skills/pro-se-firm/references/` (the doctrine and role playbooks) and the five files under
  `references/managing-partner/`, which are the original skill body split into parts.
- `skills/pro-se-firm/scripts/` (eleven of the original scripts).
- `agents/council-a1` through `council-a15`, `verification-partner` and `cross-examination-builder`.
- `templates/firm-layer/` and `skills/clawyer-setup/references/` and three of its `scripts/`.
- The text of the three hooks.

## What was changed

- A "Jurisdiction note (Clawyer)" line was added at the top of each file that carries Mississippi law.
- Details of one person's case (dates, a case number, names, a folder layout) were removed.
- Scripts that find the workspace now look in the person's folder, not beside the script.
- The skill body was split so the skill file stays under the size Claude keeps after compaction.
- About 80 scripts and all workflow files were left out (`skills/pro-se-firm/scripts/NOT-SHIPPED.md`).

## What is new in Clawyer

The setup skill and `scripts/clawyer_init.py`, the matter, evidence, breach and premortem skills, the
`contract-reviewer` and `legal-researcher` agents, the case-type switch, the workspace templates and the
leak check.

`hooks/run-py.sh` and `scripts/report_to_joe.py` come from the REVXL marketplace (MIT).
