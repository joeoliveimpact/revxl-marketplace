# VERIFICATION LEDGER — personal firm vs. shareable bundle

*Produced 2026-08-07 at the owner's direction: "absolutely verify that everything
I have built... every tool every role every script every hook." Method: mechanical
diff per component class, then a PII pattern gate plus five independent content
sweeps on everything ported. This ledger states exactly what is in, what is out,
and why.*

## COMPONENT-BY-COMPONENT

| Class | Personal firm | In this bundle | Status |
|---|---|---|---|
| Skill reference files | ~50 | ~53 (all + 3 new doctrine files) | ✅ COMPLETE (diff = zero missing) |
| Skill scripts | all | all | ✅ COMPLETE (diff = zero missing) |
| Subagent definitions (roles) | 17 (15-lens council + verification partner + cross-exam builder) | 17 | ✅ COMPLETE — `plugins/pro-se-firm/agents/` |
| Firm-layer operating files | 6 (ROUTING · COUNCIL · VERIFICATION-PARTNER · ROSTER · LEVERAGE-ENGINE · CROSS-EXAM-PROTOCOL) + FIRM.md | 6 + FIRM.md's substance as `firm-charter.md` | ✅ COMPLETE — `.../firm-setup/references/firm-layer-templates/` |
| Lifecycle hooks | 4 + settings.json wiring | 4 + settings.json.template | ✅ COMPLETE — `plugins/pro-se-firm/hooks/` |
| Orchestration workflows | 6 | 6 | ✅ COMPLETE — `plugins/pro-se-firm/workflows/` |
| Workspace scripts (firm tools) | 89 | 89 ported, genericized | ✅ COMPLETE — `plugins/pro-se-firm/skills/pro-se-firm/scripts/` |
| One-off case scripts | 37 (`_`-prefixed scrapes, single-motion builders, one day's transcriptions, a prior-counsel corpus builder) | 0 | ⛔ EXCLUDED BY DESIGN — they ARE the case, not the engine. Itemized in `scripts/_EXCLUDED-BY-DESIGN.md` |
| Doctrine (drafting standards, PDF specs, operating doctrine) | CLAUDE.md + 2 PDF specs + RULES.md doctrines | all (skill references + firm-setup scaffold + `standing-pathways.md`) | ✅ COMPLETE |
| Case corpus, verified law library, research notebooks | 8,500+ docs | 0 | ⛔ EXCLUDED BY DESIGN — case data. Each user grows their own; the engine that builds it is included |
| PII pattern file (`pii_patterns.txt`) | 1 | 0 | ⛔ EXCLUDED — it is literally a list of the owner's identifiers |

## WHAT "GENERICIZED" MEANS HERE

Every ported file had case identifiers replaced with labeled placeholders:
`{MATTER_HOME}` `{MIRROR_HOME}` `{USER}` `[case-name]` `[cause-number]`
`[opposing-party]` `[child-name]` `[county]` `[trial-date]` `[name]` — plus
fill-in templates where a whole case fact-sheet had been embedded
(twin-case-hunt, cps-document-intake). Scripts will not run until the
placeholders are set; the README explains each.

## THE VERIFICATION ITSELF

1. **PII pattern gate** (`check_no_pii.py`, the owner's identifier list): **CLEAN**
   on the full bundle including the add-on.
2. **Sweep 2 — names/entities** (parties, relatives, witnesses, banks, schools,
   employers, account numbers, sworn dollar figures): **0 hits** (the only
   remaining matches are the deliberately fenced "Mississippi worked example"
   doctrine lines, which name no person).
3. **Sweep 3 — user paths and dates** (real user directories, the trial date):
   **0 hits.**
4. **Sweep 4 — docket artifacts** (document numbers, cause-number fragments):
   **0 hits.**
5. **Sweep 5 — biography shapes** (marriage/separation dates, employers, wage
   figures, the mortgage payment): **0 hits.**

Leaks the multi-sweep process caught that the pattern gate alone had passed: the
owner's full fact sheet embedded in a workflow constant, a real user path in
three workflows, the child's first name in mining keyword lists, a prior
counsel's email domain in a corpus script (script pulled entirely), phone
numbers, a ZIP code, and a real mortgage figure in two PDF sample builders. An
identifier gate cannot catch a biography; the sweeps exist because of that.

## HONEST LIMITS

- Ported scripts are **read-and-adapt**, not run-out-of-the-box: paths are
  placeholders, some reference companion tooling (a corpus-query script, a
  notebook CLI) the user must supply or stub.
- The excluded one-off scripts mean a reviewer sees the engine, not every
  artifact the engine ever produced. That is the point.
- Mississippi authorities appear only as fenced worked examples per the
  50-state design; the state-law resolver supplies the user's own forum law.
