# CHANGELOG — pro-se-firm v1.7.0 (2026-08-07)

Two months of live-litigation refinement folded into the shareable engine
(v1.6.0 was built 2026-06-05). Everything below was proven in actual use before
it was generalized. No case data, no client data, no state-specific law is
included — method only.

## NEW — the firm layer

- **`references/firm-charter.md`** — Chief (the managing-partner persona), the
  Three Hard Laws (anti-hallucination · anti-yes-man · verify-don't-guess), the
  one hard stop (nothing files without the client's explicit approval), the
  never-counsel-waiving-a-right rule, session choreography, and the voice
  standard. This is the top of the instruction hierarchy.

- **`references/standing-pathways.md`** — the auto-fire doctrine layer: ten
  standing pathways with named triggers (evidence preservation + catalogue,
  intake fan-out, locked-fact fan-out, adverse-document council, connection
  engine, leverage sweep, findings→deployment, filing auto-build, record-first
  retrieval, bulletproofing + the blank-paper guard), plus the meta-pathway
  (the improvement engine). Design principle: any recurring process that runs
  on the assistant "remembering" is a defect — convert discipline to machinery.

## NEW — specialists

- **`references/adverse-document-review-council.md`** — the 15-lens review
  swarm that fires on every document from the other side, the court, or a
  court-appointed neutral; also runs in OUTBOUND mode on the firm's own drafts.
- **`references/cross-examination-builder.md`** — the continuous cross-exam
  specialist: every ingested document is mined for contradictions and
  admissions and converted to numbered leading questions, topic-banded,
  exhibit-anchored, with volume targets per witness class.
- **`references/hallucination-auditor.md`** — the citation/named-person
  verification gate with retraction protocol.
- **`references/format-compliance-officer.md`** — drafting-standards
  enforcement.
- **`references/pdf-builder-specialist.md`** — the two-genre PDF doctrine
  (court filings vs. personal trial packets).
- **`references/client-education-route.md`** — the firm never out-runs the
  client: teach-with-the-work blocks, the client curriculum, quiz-me reps,
  walkthrough-before-use.

## NEW — trial craft

- **`references/trial-craft-doctrine.md`** — bench-trial method for the
  self-represented, distilled from the classical schools (Younger, Pozner &
  Dodd, MacCarthy, Mauet) and converted for family-law bench trials: the
  bench-trial adjustment, one-fact-per-question cross, treat-everyone-as-
  hostile witness prep, the three self-testimony formats, the minute map,
  make-and-meet objections, the scenario matrix, recording/business-record/
  screenshot foundations, and conduct doctrine under fire (route through the
  court · document don't confront · show don't say · the precise claim beats
  the broad one).

- **`references/custody-premortem.md`** — red-team a custody MOVE (not just a
  document) before it happens: assume the day-after-the-hearing loss and work
  backwards through eight lenses (threshold/vehicle, status quo, the fostering
  factor, allegation proportionality, the GAL/neutral read, our own record read
  hostile, blowback economics, the judge's two-sentence read). P0/P1 findings
  block the send. Adapted from a contributed New York Family Court skill,
  converted to the plugin's fenced-example convention.

## SCRIPTS

- **`scripts/update_role_to_tool_map.py`** — auto-propagates new tools/roles
  into the role-to-tool coverage grid with human-curated classifications
  preserved across runs.

## DESIGN NOTES (for the technically curious)

The live system this generalizes runs on: session-start hooks that audit
staleness (a register whose sources changed after it was built gets flagged),
post-edit hooks that fire fan-out checklists when the case profile changes, a
deterministic claims ledger, per-corpus mining agents, and a PII gate
(`check_no_pii.py`-style) that blocks any share/publish while case identifiers
are present. The doctrine files here are the portable layer; the hooks are
described in `standing-pathways.md` so any host environment can wire its own
equivalents.
