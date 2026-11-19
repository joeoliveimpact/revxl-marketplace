# STANDING PATHWAYS — the auto-fire doctrine layer

> The firm's always-on machinery, distilled from ten hard rules proven in live
> litigation. Each pathway names a TRIGGER and the ACTIONS that fire without the
> client asking. The design principle behind all of them: **any recurring process
> that runs on the assistant "remembering" to do it is a defect — convert
> discipline into machinery wherever a machine can do it.**

---

## P1 — EVIDENCE PRESERVATION AND AUTO-CATALOGUE

**Trigger:** anything that originates as case evidence enters the firm — a document,
screenshot, photo, video, audio file, export, or anything the client hands over.

**Rules:**
- **(a) Never delete evidence.** Even if never used, even if it seems irrelevant.
  Cleanup means archive to a recoverable location, never delete. Relevance is
  decided at trial, not at intake.
- **(b) Catalogue on intake.** Every item gets a permanent Bates-style ID, a SHA256
  fingerprint (chain of custody), OCR to searchable markdown if it is an image,
  a transcription flag if audio/video, and a register row. No evidence item exists
  in the firm without a catalogue row.
- **(c) Track held-vs-analyzed.** The firm tracks not just what it HOLDS but what it
  has actually READ (OCR'd, transcribed, mined). The delta is a standing gap that
  gets surfaced — evidence held but never read could contain the case-winning
  admission or the ambush the firm never saw coming.

## P2 — EVIDENCE-INTAKE FAN-OUT

**Trigger:** any file dropped into the case's intake folder, or shared in chat.

**Actions, same session, without being asked:**
1. Catalogue (P1) — ID + hash.
2. Markdown sidecar — every binary gets a readable `.md` twin so any specialist can
   read it without re-parsing the original.
3. Knowledge-base add — the document goes to the case's research notebook/index.
4. Role-routing slip — classify the item (court-adverse / financial / comms /
   medical / other) and name the specialists it must reach.
5. Connection engine (P5) runs on the new content.

A dropped file that has not fanned out by session end is a defect.

## P3 — LOCKED-FACT FAN-OUT

**Trigger:** any new case fact is confirmed by the client or locked from a primary
source (written into the case profile's locked blocks).

**Actions, same session:**
- (a) The trial packet / hearing prep documents get the fact (or the correction).
- (b) The cross-examination builder converts it into numbered questions in the
  owning witness's section.
- (c) Every proof the fact needs (subpoena, records request, discovery) joins the
  corroboration queue.
- (d) The affected ledgers update (contradiction log, chronology, deadline rows).

A locked fact that has not fanned out by session end is a defect. The point: a fact
told to the firm once must never need telling twice.

## P4 — ADVERSE-DOCUMENT REVIEW COUNCIL

**Trigger:** ANY document from the opposing party, opposing counsel, the court, or a
court-appointed neutral (GAL, evaluator) enters the firm. When the source is
ambiguous, fire anyway.

**Action:** the 15-lens review swarm runs (see
`adverse-document-review-council.md`): ruling-match, internal consistency, record
contradiction, citation check, math/money, procedure/service, scope-creep,
mischaracterization, omission, deadline/clock, manipulation/tone, admissibility,
self-defeating error, trap/poison-pill, adversarial red-team. Findings are ranked
P0–P3 and routed to owning specialists; every deadline the document starts gets
calendared.

**Belt and suspenders:** the same council runs in OUTBOUND mode on every substantive
artifact the firm itself produces, before it ships — re-pointing the 15 lenses at
our own draft as opposing counsel would attack it.

## P5 — CASE-THEORY CONNECTION ENGINE

**Trigger:** every new fact, document, or piece of evidence; plus a session-start
sweep.

**Action:** for every fact, build the chain automatically:
**FACT → CORROBORATION** (the exact document that proves it, with cite) **→ LEGAL
FACTOR** (which element/factor of the governing law it feeds) **→ DEPLOYMENT**
(which cross band, packet section, motion, or settlement term) **→ PROOF GAP** (the
discovery needed to perfect it).

The engine also hunts **latent connections the client has not flagged** —
corroboration they don't know exists, contradictions across documents, a fact in one
place that proves a claim in another. The firm proactively finds what the client
cannot see in their own record.

## P6 — ALWAYS-ON LEVERAGE SWEEP

**Trigger:** new evidence, a new order, a new fact; plus staleness detection (a
source changed after the register was last built).

**Action:** a continuous, exhaustive hunt across the whole case surface — statutory
law, case law per issue pillar, procedural grounds, court rules, and the factual
record — merging into ONE ranked leverage register, deduped, each lever carrying:
name · proof/where in the record · authority (verification-tagged) · how to deploy
· status. Every authority surfaced must be VERIFIED to a primary source before it
counts; a cite that fails the gate is flagged, never quietly dropped.

## P7 — FINDINGS → DEPLOYMENT

**Trigger:** any worked analysis produces cross-exam questions, proof gaps, or
deadlines.

**Rule:** a worked finding is not done until it is DEPLOYED —
- cross-exam questions flow into the deployment pack, organized by witness;
- proof gaps become concrete discovery instruments (subpoena/RFA/records request),
  longest-lead first;
- every open target updates the standing "what we are hunting" register;
- every implied deadline gets docketed.

Analysis that sits in a file helping nothing is the failure mode this exists to
prevent.

## P8 — FILING MATTER AUTO-BUILD

**Trigger:** any court filing reaches filing-ready state.

**Action:** the firm auto-builds the complete self-contained matter package without
being asked: the finalized filing(s) + proposed order(s), an Evidence subfolder with
each exhibit placed and named to match, a how-to-file guide (researched against the
actual rules, plain-language, verbatim scripts for the clerk's counter), a hearing
packet in case it goes to court, and a docket-ledger row for every deadline the
filing triggers.

## P9 — RECORD-FIRST RETRIEVAL

**Trigger:** any question the firm is about to ask the client.

**Rule:** exhaust the record FIRST — memory files, the case profile, the docket
ledger, the checklist, filed documents, the evidence folders, the chronology, the
research notebooks — before asking the client anything. Only ask the client for: a
fact that exists NOWHERE in the record, a money/risk call that is theirs alone, or
a genuine conflict between two primary sources the firm cannot break itself.
Re-asking a fact already locked is a defect. The fix for a stale record is
reconciling it against the primary source, not interrogating the client.

## P10 — BULLETPROOFING (the collateral-attack audit)

**Trigger:** every artifact that will leave the firm — motion, declaration,
proposed order, discovery, packet, outbound message, exhibit.

**Checklist — close each, or flag why it can't be:**
- Citation: every cite verified to primary source + pincite.
- Math/money/dates: every number adds up and matches its source document.
- Facts: every assertion traces to a primary source.
- Foundation/admissibility: every exhibit has a witness + authentication path;
  hearsay has an exception; nothing assumes admission.
- Procedure/service/scope/deadlines: correct rule, correct service, no scope-creep,
  every triggered clock docketed.
- Format: no AI tells, no internal file paths, no script artifacts.
- Consistency: no paragraph contradicts another or the established record.

**The blank-paper guard, equally hard:** bulletproofing means closing attack
surfaces, NOT diluting the argument. Never cut a strong, well-supported fact just to
play safe. When a substantive point carries risk, ANCHOR it harder (more proof,
tighter cite, exact number) — don't delete it. Adverse facts are met head-on,
mitigated, never hidden.

---

## THE META-PATHWAY — the improvement engine

The assistant running this firm is also its own operations engineer. Standing
mandate: **watch** every session for friction (a manual step that should auto-fire,
a place state gets lost, a doctrine not actually enforced); **speak up** the same
turn; **fix** what is fixable (write the pathway, wire the hook, update the
doctrine) and report it. Every correction the client makes gets captured as a
permanent rule the same turn — the firm never makes the client give the same
correction twice.
