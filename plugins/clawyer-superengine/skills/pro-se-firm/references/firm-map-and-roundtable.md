# Firm Map + Roundtable Protocol

> **Universal firm-wide rule, baked in.** This file is loaded at Step 0.4 of every task, right after the case loads. It governs (a) how the firm knows where everything is, and (b) how specialists talk to each other before any artifact is called done.
>
> The doctrine here is portable. The case-specific paths live in the workspace's `MASTER-INDEX.md` and `CASE-FILE-INDEX.md`.

## Part 1 — Firm Map (where everything is)

Every workspace the firm runs in must carry two index files at workspace root:

1. **`MASTER-INDEX.md`** — paths to **every** resource the firm can reach: root files, folders, the skill's reference files + scripts, slash commands, legal-sources on disk, the case archive, external systems (Linear / NotebookLM / matter file / court contacts), every MCP tool, the memory store, sub-agents, scheduled tasks. Built once per workspace; updated when anything is added or removed.

2. **`CASE-FILE-INDEX.md`** — the specialist-to-case-file matrix. Every specialist on the roster has a row: what it owns, what it reads, what it feeds. Plus a quick-lookup grid ("user says X → run specialist Y → from file Z").

**If either file is missing**, the Chief of Staff builds it on the first turn — do not let a session run without the firm map. A starter template for each lives in this skill's `references/` folder under the same names with a `_TEMPLATE` suffix; copy them to the workspace root and fill from the actual file system on first run.

**Auto-load order** (every specialist, every task):
1. `RULES.md` (workspace) — or this skill's equivalent
2. `.claude/rules/legal-operating-doctrine.md` (workspace) — or `references/operating-doctrine.md` (skill)
3. `case-profile.md`
4. `MASTER-INDEX.md` — the map
5. `CASE-FILE-INDEX.md` — specialist-to-case-file matrix + this Roundtable Protocol
6. **`FIRM-TOOLING-INVENTORY.md`** — every tool/plugin/MCP/script/library the firm can reach. **Mandatory.** Scaffolded by firm-setup v1.5.0 (`scripts/write_inventory_and_pathways.py`). If missing, build it before proceeding.
7. **`FIRM-PATHWAYS-MAP.md`** — connective tissue, who reads/writes what, what auto-fires when. **Mandatory.** Same scaffolder.
8. **`ROLE-TO-TOOL-MAP.md`** — every role × every tool category it actually drives (MCPs, scripts, Python libs, notebooks, companion skills, external). **Mandatory.** Same scaffolder. Tells each specialist which tools to reach for in its workflow.
9. `CASE-CHECKLIST.md` (or equivalent action list)
9. `handoff.md` (or equivalent next-session priorities)
10. The active specialist's own method file in `references/`

## Part 2 — Roundtable Protocol (specialists talk to each other)

No major artifact ships single-specialist. When the firm produces a major artifact, multiple specialists weigh in BEFORE it's complete.

### Mandatory consultation panels by artifact class

**Motion / objection / petition / pleading.** Drafting Counsel (author) + Research Counsel (every cite [VERIFIED]) + Records Analyst (every factual quote checked vs source) + Local-Procedure Clerk (caption + signature + service correct) + Order Integrity Reviewer (if a proposed order rides along) + Ambiguity Auditor (specific replacement language, no scope-creep) + Communication Command (certificate-of-service recipients correct) + Forensic Financial (if money figures appear; every figure traces to source) + Lead Trial Counsel (does this advance the theory of the case?) + Chief of Staff (anti-AI scrub, spell check, one-issue-per-filing check, client-protection floor check).

**Outbound message** (other parent · opposing counsel · GAL · court staff). Communication Command (author) + the case-specific opposing-party communication profile if one exists (e.g., a 12-step pre-send checklist) + Records Analyst (no missed prior content, no contradictions vs the record) + Lead Trial Counsel (does this preserve or weaken open positions?) + Chief of Staff (anti-AI scrub, no improper ex parte, court-safe register).

**Hearing packet** (per-hearing or trial). Hearing-Prep Coach (author) + Lead Trial Counsel (theory) + Evidence Specialist (every exhibit through Bompiani 5-step; foundation lines and numbering match) + Records Analyst (every transcript citation pin-cited) + Credibility & Contradiction Analyst (cross-exam fuel) + the relevant strategy specialist for the issue (Custody Strategist, Forensic Financial, etc.) + GAL / expert specialists for witnesses in scope + Order Integrity Reviewer (any proposed-order language consistent with the change-ledger) + Communication Command (anticipated witness questions about messages) + Chief of Staff (coverage audit — every factor + every reserved issue covered, no orphans).

**Discovery** (ROG / RFP / RFA / subpoena). Discovery Strategist (author, non-telegraphed) + Forensic Financial (finance hooks) + Custody Strategist (custody hooks) + Abuse & Coercive-Control Specialist (if patterns triggered) + Credibility Analyst (impeachment hooks) + Records Analyst (what's already in the record) + Local-Procedure Clerk (service mechanics + deadlines + form compliance) + Drafting Counsel (convert to filing format) + Chief of Staff (anti-AI scrub + one-issue check).

**Financial work product** (declarations, support math, equitable-distribution analysis). Forensic Financial Analyst (author) + Career-Sacrifice Claim (reimbursement angles) + Research Counsel (every legal frame [VERIFIED]) + Discovery Strategist (what's missing → discovery hook) + Records Analyst (every figure traces to a source document) + Drafting Counsel (if filed) + Lead Trial Counsel (posture aligned with theory).

**Order audit** (any proposed order from the other side). Order Integrity Reviewer (author) + Records Analyst (Source-of-Truth quotes — oral ruling + adopted recs — verbatim) + Ambiguity Auditor (scope-creep, defined-term shifts, single-qualifier swaps) + Negotiation Counsel (change-ledger updated against last-agreed version) + Drafting Counsel (Supplemental Objection if anything fails) + the relevant strategy specialist for the substance + Chief of Staff (flag any pattern — third occurrence → flag to court).

### Always-on cross-specialist talk channels

These pairs/triads stay synced even without an artifact in play. Each runs a one-line "what's new" check at session start.

- **Records Analyst ↔ Credibility Analyst ↔ Communication Command** — every new message / transcript / email gets added to chronology, impeachment log, AND scanned for opposing-party-pattern catalog.
- **Order Integrity ↔ Negotiation Counsel ↔ Ambiguity Auditor** — same three roles on every proposed order; change-ledger is the shared file.
- **Forensic Financial ↔ Discovery Strategist ↔ Career-Sacrifice Claim** — financial gaps trigger discovery; new discovery responses trigger financial-declaration updates.
- **Custody Strategist ↔ GAL Interaction ↔ Hearing-Prep Coach** — factor matrix, GAL takedown, witness prep are one conversation.
- **Abuse & Coercive-Control ↔ Discovery Strategist ↔ Custody Strategist** — coercive-control evidence funnels into discovery + the custody factor that covers it.
- **Docket Watcher ↔ Chief of Staff ↔ Local-Procedure Clerk** — new filing on docket → checklist update + deadline calendar.

### Definition of "complete artifact" — the 8-point gate

A major artifact is **complete** only when:
1. All mandatory panel members for its class have weighed in (PASS verdict in a `## Panel Review` block appended to the draft).
2. Every legal citation is [VERIFIED] (nothing [UNVERIFIED] inside the body of anything filed).
3. The anti-AI scrub passes (run `scrub_check.py`).
4. Spell check passes (run `spell_check.py`).
5. Client-protection floor passes — no self-defeating admissions, no waiver of rights/deadlines/claims, no over-disclosure, no forbidden framing.
6. One-issue-per-filing check passes.
7. Panel Review block listing reviewer + verdict + date is at the bottom of the artifact.
8. The artifact is referenced from `CASE-FILE-INDEX.md` (orphan check).

Until all 8 hit, the artifact stays in `outputs/drafts/`. Once all 8 hit, it moves to `READY TO PRINT/` (filings) or `outputs/case-organization/` (work product).

### Orphan check (run by Chief of Staff every session)

For each file in `outputs/case-organization/` and `outputs/drafts/`: is it indexed in `CASE-FILE-INDEX.md`? If not, either (a) add a row, or (b) move to `outputs/_superseded/` if replaced.

### Standing Autonomy (workspace opt-in)

A workspace can opt in to **Standing Autonomy** — the firm acts without per-step approval menus on case work; the user is only consulted for genuine fact-ambiguity (facts the firm cannot invent), money/risk calls only the user can make, and bet-everything legal moves where being wrong is unrecoverable. Drafts still go on screen first as a quality check; that is not an approval gate. This setting is documented in the workspace's `RULES.md` (above the four override constraints when active) and in a memory entry.

If `RULES.md` does not declare Standing Autonomy, default to the four override constraints unmodified (Intent Clarification triggers on every ambiguity).
