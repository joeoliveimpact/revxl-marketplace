# Next moves — the no-dead-end convention

Every pipeline skill ends every terminal path with a **Next moves** block. A
user with a finished deliverable must never be left staring at it with no
offered road. The blocks live INLINE in each SKILL.md (skills run standalone);
this file is the convention + the edge registry for maintenance.

## Block shape

```
**Next moves**
1. <verb phrase> — <what you get, one clause>. Say: "<exact trigger phrase>"
2. …   (2–4 options total, most-likely-first)
```

## Rules

1. **2–4 options**, one line each, most-likely-next first.
2. Every option names its **exact trigger phrase** — the user can fire it verbatim.
3. **Schedulable items are SUGGESTED, never auto-scheduled.** Max ONE schedule
   suggestion per block, always phrased as an ask, always the onboarding
   Step 4c pattern (Cowork scheduled-task / Code cron-or-`/schedule`, user picks
   the slot, recorded in the `.superengine` marker). A scheduled pulse still
   stops at its credit checkpoint — schedules wake work up, they never spend.
4. **State-gated:** don't offer visuals without `analysis-data.json`; don't
   offer "script the winner" without a winner; detect markers
   (`socialcrawl-superengine`, the RevXL Vault key (Joe's live strategy API, not
   the brand brain), NotebookLM) before offering their
   edges — absent tools get one line, never a block slot.
5. **Offer-once discipline:** never re-offer something declined this session;
   marker says scheduled → don't offer scheduling again.
6. **Teach-mode aware:** in `beginner`, options may carry a one-line "why".
7. The bundled `socialcrawl` skill is an API surface, not a pipeline — no block.

## Edge registry (E1–E16)

| ID | Skill · ending | Routes to |
|----|----------------|-----------|
| E1 | onboarding · Step 8 activation | cross-reference (primary) · reel-scripter (after analysis) · brand-brain (if skipped at 4b) · harvest · pulse-schedule (only if an analysis exists) |
| E2 | onboarding · sub-mode exits | back to work · pulse (if analysis) · "show my setup" |
| E3 | cross-reference · roadmap delivered | visual pack · script top gap · feed themes → brand-brain · weekly pulse [schedule] · (pointer: deeper legs live in competitor-pulse) |
| E4 | cross-reference · stopped at ✋2 (thin set) | more seeds · park+resume · proceed thin (explicit) |
| E5 | cross-reference · stopped at ✋3 (credit decline) | shrink set · top up + resume · park |
| E6 | reel-scripter · script written | next angle (unpicked Step-1 angles) · topic pool · regenerate visuals · pulse [schedule] |
| E7 | reel-scripter · topic pool, idea picked | (existing) → script pipeline Step 1 |
| E8 | reel-scripter · topic pool, no pick | saved-pointer ("script idea N…") · weekly regen via pulse [schedule] · re-spread themes · script top idea |
| E9 | reel-scripter · Step 0a no analysis | route to cross-reference (existing) |
| E10 | brand-brain · mine/refresh complete | script top seed (inline handoff) · refresh schedule [schedule, if unset] · back to caller |
| E11 | brand-brain · refresh declined | proceed on current brain · remind-only nudge [schedule] · top-patterns quick pass |
| E12 | brand-brain · interview floor | wire recording source · first-refresh suggestion [schedule] · script on interim voice |
| E13 | creator-strategy-harvest · manifest written | vault ingest (or "send Joe the HANDOFF") · NotebookLM (detect-first) · harvest another · refresh later |
| E14 | competitor-pulse · weekly brief | script the week's winner · open visuals · roster ops · make-weekly [schedule, if unset] |
| E15 | competitor-pulse · roster op done | backfill + re-analyze · defer to next pulse · run pulse now |
| E16 | competitor-pulse · empty week | quiet-week note (no extra spend) · script from existing pool/gaps · widen to 14 days · roster health |

Adding a new ending? Add the row here first, then write the inline block to
match. A terminal path without a registry row is a bug.
