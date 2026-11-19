# pro-se-firm — Upgrade notes (v1.0 → v1.4.0)

The shareable, generic, **50-state** pro-se family-law firm. All case facts live in the user's own `case-profile.md`, never inside the skill.

---

## v1.4.0 (this release) — the common-person upgrade

The strategic frame for this release: the shareable user is the **common person**. They have no idea what AI can do. They use AI like Google for chicken recipes. Everything below is judged against that floor.

### Hard naive-phrase routing
- **New table at SKILL.md Step 0.45** — a mandatory routing table that fires the right specialist on the actual words a scared non-lawyer types ("I got served," "she's hiding money," "the order isn't being followed," "I'm scared I'll lose my kids," "I want to fight this," any abuse keyword). Multiple specialists fire in parallel. Empathy first when fear shows up. Never a menu — the firm reads what they wrote and fires.

### Common-person language rules
- **New "Conversational vocabulary" rule** in `references/operating-doctrine.md` — never speak file names, paths, or technical jargon to the person. Internally use them; conversationally say "your case file," "the trial packet I built you," "your print-ready folder." If the firm reads a document, it says "I just read your order" — not "I parsed the .md at outputs/..."
- **README.md rewritten** to lead 50-state, with Mississippi as the worked example. New "What to do right now" 3-step kickoff.
- **First-contact "drop your papers right here" cue** added to `references/cold-start.md` — before any deep intake questions, the firm invites the person to upload, paste, or photograph any court paper they have. Naive users describe documents when they could just hand them over; this fixes that.

### Roundtable Protocol polish (v1.3.0 feature, hardened)
- **Panel Review block format pinned** in SKILL.md Step 0.4. Every Drafting Counsel artifact now ends with a uniform `## Panel Review` block — one line per reviewer, verdict in CAPS (PASS / REVISE / FAIL), one-sentence basis. A FAIL blocks ship; a REVISE must resolve before delivery.

---

## v1.3.0 — firm map + Roundtable Protocol + 50-state resolver

- **Firm map (`MASTER-INDEX.md` + `CASE-FILE-INDEX.md`)** loaded on every task, right after the case loads. Tells every specialist where everything is and how specialists talk to each other.
- **Roundtable Protocol** — non-overridable. No major artifact ships single-specialist. Each artifact class (filing · message · hearing packet · discovery · financial work product · order audit) names the mandatory consultation panel.
- **State-Law Resolver** (`references/state-law-resolver.md`) — the firm is **50-state**, no state defaulted. As soon as intake captures state + county, the resolver establishes that forum's controlling law (custody standard, spousal support, property regime, court, procedure). Mississippi ships as the complete worked example; for any other state, the resolved profile governs.
- **Controlling-law gate (HARD RULE — 50-state)** added to `operating-doctrine.md`. Mississippi authorities (Albright / Armstrong / Ferguson) may **only** be cited when forum state is Mississippi.
- **Reference files fenced** — every Mississippi-specific example now carries a `📍 MISSISSIPPI WORKED EXAMPLE — controlling only if forum state is MS` header.
- **Standing Autonomy** baked in — the firm runs the Firm Operating System loop without per-step permission.

---

## v1.2.x — full firm bench + companion-skill auto-fire

- **The full firm bench (44 roles total)** loaded across five department files (Strategy & Governance · Operations & Discovery · Financial & Property · Custody/Parenting/MH · Resolution & Investigation).
- **High-Conflict Opponent Protocol** auto-activates when a narcissistic/combative party or aggressive attorney is detected.
- **Companion skills auto-fire** — the firm invokes installed companion skills (deposition-prep, subpoena-triage, demand-letter, pdf, docx, notebooklm, etc.) via the Skill tool, passes case context, folds results back. Falls back to the internal specialist if a companion is absent.
- **Anti-AI scrubber** mechanical gate (`scripts/scrub_check.py` + `scripts/scrub_fix.py`) — every filing scrubbed of dashes, semicolons, and AI-tell phrases before delivery. Spell-check gate (`scripts/spell_check.py`) added.
- **`firm-setup` companion skill** — one-shot guided installer for non-technical users.

---

## v1.1.x — Legal Educator + Intake + Action Plan + Docket Watcher

- **Legal Educator** specialist — teaches the *why* in plain English; simple answer first, in-depth on request. Always on.
- **Intake Counsel** — gathers basics from the person, writes `case-profile.md`.
- **Action-Plan Navigator** — priority checklist of exactly what to DO/FILE, PROVIDE/BRING, and ASK FOR, with literal courthouse walk-throughs.
- **Docket Watcher** — scheduled, automatic docket checks with plain-language and optional email alerts.
- **Communication Command** specialist — co-parenting + opposing counsel + GAL + clerk messages, one-issue, exhibit-safe, DARVO/manipulation detection.
- **Responsive-Filing** mode — 5-step method to answer the other side's motions.

---

## v1.0 — the original pro-se firm

Managing partner that routes by legal issue. Core specialists (Research · Drafting · Evidence · Hearing-Prep · Local-Procedure · Records Analyst · Order Integrity Reviewer). Mississippi-first; chancery format; one-issue guardrail; verify-before-cite; child by initials.

---

## Portability check (run before every release)

No case-specific facts (party names, judge, cause number) belong in the skill. They live in `case-profile.md` on the user's machine. Grep-verify before sharing.

## To ship this as an installable plugin

This folder is the **source**. Package with `package_skill` (or zip it forward-slash with `.claude-plugin` at root). Confirm front-matter `description` stays ≤ 1024 characters. Validate before sharing.
