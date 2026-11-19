> 🧭 **METHOD IS UNIVERSAL — the named authorities are the Mississippi example.** The process in this file applies in every state. Where it names **Albright / Armstrong / Ferguson**, a **chancery/chancellor** court, **MRCP / UCCR / the MS Rules of Evidence**, or a Mississippi code section (§93-, §43-19-), that is the **Mississippi worked example** — for a non-MS case, apply the **resolved state-law profile** (its factors, its court, its rules; see `state-law-resolver.md`) instead, and never cite these Mississippi authorities in a non-MS case.

# Companion Skills — auto-fire delegation to other installed skills

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

The overwhelmed pro-se will never remember to invoke a specialist by name — so the firm reaches for the right capability
itself. The managing partner already auto-engages on any family-law prompt and routes to **internal** specialists. This
file extends that to **external companion skills**: when a task maps to a companion that is installed, the firm **invokes it
via the Skill tool, passes the case context, and folds the result back into one answer** — the person never names it.

## The rules of delegation

1. **pro-se-firm leads.** It is the family-law brain and the only thing that reads `case-profile.md` and
   `CASE-CHECKLIST.md`. A companion is a tool the firm picks up, not a replacement front door. The managing partner frames
   the task, dispatches the companion, then assembles the companion's output under the firm's own rules and voice.
2. **Optional + graceful fallback (HARD).** Every companion is **optional**. Before delegating, assume it may not be
   installed. If invoking it fails or it is absent, **fall back to the internal specialist** (or, if there is none, do the
   work directly and note the lighter capability honestly). A stranger who installs only `pro-se-firm` must still get a
   working firm. Never tell the person a task can't be done because a companion is missing.
3. **Pass the context.** When you delegate, hand the companion what it needs: the specific task, the relevant facts from
   `case-profile.md`, and pointers to the documents. The litigation-legal suite keeps its own matter files (one folder per
   matter), so its handoffs already have context; still state the task plainly.
4. **All firm-wide rules still bind the result.** Whatever a companion produces passes back through citation discipline,
   the one-issue guardrail, client-protection, the anti-AI scrubber (if it's a filing), child-by-initials, and the
   coverage-checklist update. The companion's output is raw material; the firm is still responsible for it.
5. **Write it back.** When a companion finishes a piece of work (a drafted demand, a privilege log, a new notebook, a
   parsed PDF), update `CASE-CHECKLIST.md` (`references/case-assurance.md`) so the assurance layer stays true.

## When overlaps exist — who wins (tie-break matrix)

Some companions overlap an internal specialist. Default: **pro-se-firm leads and delegates the mechanical/specialized
piece** to the companion that does it better.

| Capability | Internal (pro-se-firm) | Companion | Rule |
|---|---|---|---|
| Chronology / case history | Records Analyst owns the baseline | litigation-legal `chronology` + matter files | Records Analyst stays **owner/editor**; the litigation-legal `chronology.md` is the canonical **store** it writes to. One truth. |
| Hearing vs deposition | Hearing-Prep Coach (chancery hearing strategy) | litigation-legal `deposition-prep` (deposition mechanics) | Both fire and **hand off** — strategy from the firm, deposition Q-mechanics from the companion. |
| Discovery instruments | Discovery Strategist (non-telegraph strategy) | litigation-legal `subpoena-triage`, `privilege-log-review` | The firm sets strategy and one-issue framing; the companion runs the mechanical instrument. |
| Matter facts | `case-profile.md` | litigation-legal `matter.md` / `_log.yaml` | Both kept; matter files are the source of truth for *facts* (per the workspace), the profile feeds the firm. Records Analyst syncs. |
| Demand letters, claim chart, legal hold, opposing-counsel status | (none) | litigation-legal `demand-*`, `claim-chart`, `legal-hold`, `oc-status` | Companion **wins outright** — no internal equivalent. |

## The companion bench (trigger → companion → handling)

Delegate when the facts show the need; do not wait to be asked.

### litigation-legal suite (if installed)
- **A deposition is coming up / "they want to depose me" / "I have to take her deposition"** → `litigation-legal:deposition-prep` for the deposition question mechanics; the firm's Hearing-Prep Coach owns the strategy and calm-witness coaching. Hand off both.
- **A subpoena was served, or you need to subpoena a bank/employer/records custodian** → `litigation-legal:subpoena-triage`; the firm's Discovery Strategist frames *what to ask for without telegraphing* first.
- **Privileged documents to log / a privilege log to review** → `litigation-legal:privilege-log-review`.
- **Build a claim/element chart** (mapping facts to the elements of a claim or an Albright/Ferguson/Armstrong frame) → `litigation-legal:claim-chart`.
- **A litigation-hold / preserve-evidence question** ("tell her to stop deleting messages," preservation duty) → `litigation-legal:legal-hold`.
- **A demand letter** — received one, or need to send one → `litigation-legal:demand-received` / `demand-intake` / `demand-draft`. Run the firm's Communication Command + one-issue + scrubber over any outgoing demand.
- **Matter bookkeeping** — onboard/update/brief/close the matter file, portfolio status → `litigation-legal:matter-intake` / `matter-update` / `matter-briefing` / `matter-close`. The Records Analyst keeps the chronology and `CASE-CHECKLIST.md` in sync with these.

### Research notebooks (if installed)
- **"Build/update a notebook on X" or a research corpus the firm should stand up** → `notebooklm-superengine:notebooklm-build`.
- **"What does my research say about X" / query the Mississippi Family Law notebook** → `notebooklm-superengine:notebooklm-ask`. Treat notebook answers as **leads to verify** against primary sources (citation discipline still binds).

### Documents (if installed)
- **Read / OCR / extract / split / merge / fill a PDF, or produce a court-ready PDF** → the `pdf` skill (document processing). This is the firm's preferred path over guessing at a scanned document. Pairs with Markdown Maker.
- **Turn a draft into a filed-ready Word document** → a `docx` skill if present.

## pdf-viewer — ON-DEMAND ONLY (HARD carve-out)
The interactive viewer skills — `pdf-viewer:open`, `pdf-viewer:annotate`, `pdf-viewer:fill-form`, `pdf-viewer:sign` —
**never auto-fire.** They open a visual viewer and interrupt the flow, so they run **only** when the person:
- uploads a PDF and asks to see/work in it, or
- explicitly asks to open, annotate, fill, or sign a PDF, or
- a stored PDF must actually be displayed or signed to finish the task the person asked for.
Reading a PDF's *contents* for analysis is the `pdf` skill or Markdown Maker, not the viewer. Do not launch the viewer just
because a PDF is involved.

## Discipline
- Runs under `operating-doctrine.md` and all firm-wide rules. Delegation never bypasses a hard stop (citation discipline,
  one-issue, child-safety, client-protection).
- This routine is **generic** — it names companion plugins but treats each as optional. No case facts live here; the
  case-specific checklist and matter files live in the person's workspace, not in this skill.
