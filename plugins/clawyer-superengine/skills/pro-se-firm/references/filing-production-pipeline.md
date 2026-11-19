> 🧭 **METHOD IS UNIVERSAL — the named authorities are the Mississippi example.** The process in this file applies in every state. Where it names **Albright / Armstrong / Ferguson**, a **chancery/chancellor** court, **MRCP / UCCR / the MS Rules of Evidence**, or a Mississippi code section (§93-, §43-19-), that is the **Mississippi worked example** — for a non-MS case, apply the **resolved state-law profile** (its factors, its court, its rules; see `state-law-resolver.md`) instead, and never cite these Mississippi authorities in a non-MS case.

# Filing Production Pipeline — from "we need to file X" to filed, on its own

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

This is the firm's assembly line for turning any needed filing into a court-ready document and getting it filed. It
has two halves and one branch. **Phase 1 (Background Production)** the firm runs on its own initiative, end to end,
without asking the person to drive it. **Phase 2 (Delivery Walkthrough)** the firm holds the person's hand through the
physical steps, one at a time. The **Branch** handles the case where an order has already been signed.

It involves the **whole firm** (Managing Partner routing, Research, Records Analyst, Order Integrity, Drafting Counsel,
Local-Procedure Clerk, Communication Command, Action-Plan Navigator) and runs under `operating-doctrine.md` and all
firm-wide rules. It is triggered by the Firm Operating System loop (`firm-operating-system.md`) whenever the work
product is a filing.

> **The standard this encodes is the one proven in practice** building the Supplemental Objection to Form: verify the
> rule from the primary source, verify every quote against the record, scrub, spell-check, match the court's accepted
> format from opposing counsel's own filings, build the PDF, and integrity-check the PDF before anyone prints it.

---

## Phase 1 — Background Production (the firm does this autonomously)

Run every step in order. Each names the owning specialist and the gate it must pass. Do not surface a draft to the
person until it has cleared the whole line. Do not ask permission between steps.

1. **Scope and one-issue check** (Managing Partner / Intake). Identify exactly what is being filed and confirm it is a
   single issue. If it blends custody, support, and property, STOP and split it (one-issue guardrail). Pull the canonical
   caption, cause number, child initials, addresses, and signature boilerplate from `case-profile.md`. **Determine the
   correct filing vehicle before drafting:** a Motion; a **verified Petition under Rule 81(d)** for temporary or
   pendente-lite relief (served with a Form 1D summons, hearing date set first); an **Objection to Form** before an
   order is signed; or a **Motion for Clarification** after one is signed. The wrong vehicle gets a filing bounced.

2. **Authority and rule verification** (Research Counsel + Local-Procedure Clerk). Read the actual rule, statute, or
   local rule text **this session** before citing it. Use web search, then `scripts/fetch_law.py` if a host returns
   403/500 (courts.ms.gov is often down, retry, then use the workaround). Tag every legal citation with its certainty
   token. Never put a rule number, deadline, or fee in a filing you did not read this session. Flag unknowns
   `[CHECK LOCAL RULE]`.

3. **Source-of-Truth verification** (Records Analyst + Order Integrity Reviewer). Establish the controlling record (the
   transcript, the GAL recommendation as adopted, the prior order, the agreement) and verify **every quote and fact**
   against the primary document, not memory. Quote exactly. **Pin-cite only a locator you can confirm.** If the
   pagination is uncertain (for example, a "GAL testimony removed" transcript whose pages will not match the full
   transcript the judge holds), drop the page locator and keep the verbatim quote. A wrong locator is worse than none.

4. **Draft** (Drafting Counsel). Chancery format, Tier 2, one issue, numbered paragraphs, child by initials, relief with
   a specific schedule or figure, proposed order attached when required. Start from `filing-templates.md`. Fill every
   field from the profile. Acknowledge anything the other side already fixed (credibility), press only what is still
   wrong.

5. **Punctuation scrub** (gate). Run `scripts/scrub_check.py <file>`. It must exit 0 (no dashes, no semicolons, no
   colons unless required). Auto-fix with `scripts/scrub_fix.py` then re-read for grammar.

6. **Spell check** (gate). Run `scripts/spell_check.py <file> case-profile.md`. It must exit 0. It ignores legal terms
   and the case's proper nouns, so any hit is a real error to fix. (Note for the person: a PDF viewer's red underlines
   under proper nouns like party, counsel, or judge names, or Latin legal terms like "nunc pro tunc," are not errors, they
   are correct words the viewer does not know.)

7. **Format and service verification** (Local-Procedure Clerk + Records Analyst). Confirm the court's accepted format
   **empirically** by reading opposing counsel's own filed PDFs in this matter (`pdfminer.six`): page size, font, font
   size, margins, line spacing. Match them. Verify each served party's address from a **primary source** (the
   attorney's own filing signature block, the official GAL roster, the bar directory), never an unverified web listing.
   Where the local-rules server is reachable, confirm any local format/backer rule, otherwise rely on the accepted-filing
   standard and say so.

8. **Run the content gates BEFORE the person sees anything (fail closed).** On the drafted text: scrub
   (`scripts/scrub_check.py`, no dashes/semicolons), spelling (`scripts/spell_check.py`), and a no-placeholder check (no
   `[CONFIRM]` or blanks left, every required quote/figure/address present, minor child by initials only). Then the
   **client-protection review** (`operating-doctrine.md` client-protection floor): no self-defeating admission, no
   accidental waiver of a right/claim/deadline, no over-disclosure (only what is legally required; withhold the person's
   home address, financials, medical where lawful; child by initials), nothing that invites sanctions or a fee award;
   every custody output protects the child and preserves or expands the parent's time. Fix everything here before the
   person sees it.

9. **Go over the document WITH the person in plain text, BEFORE building any PDF (crawl mode — HARD RULE).** Never build
   the PDF first. They approve the wording while it is still easy to change. One small step at a time, wait after each:
   - [ ] Say: "Here is your [document name], in plain words on screen. Let's read it together. I'll go one part at a time,
         no rush."
   - [ ] Walk it **section by section** (caption → each numbered paragraph → the relief you're asking for →
         signature + Certificate of Service). After each part, stop and ask: "Is this part right, or do you want to change
         anything?" Wait for the answer before the next part.
   - [ ] In plain words, say what each part means and why it's there (Legal Educator), so they approve something they
         understand, not just nod along.
   - [ ] Make any edits on screen, then quietly re-run the gates (scrub, spell, no-placeholder, client-protection) on the
         changed text.
   - [ ] Last: "That's the final wording. Want me to turn it into the court-ready PDF now?" Only a clear yes moves on.
   Save the approved plain-text (markdown) copy as the backup.

10. **Only after the person says yes, build the PDF** (engine: `scripts/build_filing_pdf.py`). Letter 8.5x11, matched
   font/margins/spacing, centered bold caption, numbered paragraphs, page numbers "Page X of N" (two-pass total),
   Certificate of Service forced onto its own page. **Save it where the person cannot miss it:** a `READY TO PRINT` folder
   inside their work folder, with a plain, obvious name like `Motion-to-Compel_PRINT-AND-SIGN.pdf` (not buried in a deep
   folder, not a formal-only name). Keep the approved markdown copy beside it.

11. **Integrity-check the built PDF, then open the folder for them (crawl mode).**
   - [ ] Extract the PDF's own text and confirm **formatting only** (the wording is already approved): page numbers read
         "X of N", the Certificate of Service is alone on its page with no body text bleeding in, no placeholder survived
         the build. If a formatting fix changes any wording, show that part again before continuing.
   - [ ] **Open the folder with the PDF itself highlighted, so they never have to hunt for it** — reveal the exact file
         selected, not just the folder (Windows: `explorer /select,"<full path to the .pdf>"`; Mac: `open -R "<full path
         to the .pdf>"`). Then say, plainly: "I just opened the folder and highlighted your file. The one lit up, named
         ___, is the one you print. You can double-click it to see it."

**End of Phase 1:** the person has read and approved the wording, the court-ready PDF is sitting in their **READY TO PRINT**
folder, and that folder is already open on their screen. Now move to Phase 2 (print, sign, file, serve).

---

## Phase 2 — Delivery Walkthrough (the firm holds the person's hand)

Plain language, ≤ 7th grade, **one step at a time**. The person should never have to figure out the courthouse alone.
Give the single next action, wait, then the next. Cover whichever route the person needs.

**A. Find the file (it should already be open).** In step 11 the firm opened the folder for them, so start there: "See the
window I opened? Your file is the one named ___." As a backup, give the exact folder path and a one-line "open File
Explorer (Mac: Finder) and go to ...". If the person's work folder lives in a cloud drive (OneDrive, iCloud, Google
Drive), the file also reaches their phone. Confirm they can see the file before moving on.

**B. Print it.** Offer the routes and let the person pick:
- **Office Depot online:** officedepot.com, Print and Copy Services, upload the PDF, settings **8.5 x 11, black and
  white, single-sided, no binding**, pick a store, pay, pick up.
- **Email or USB:** email the PDF to the store, or copy it to a USB stick for the print desk.
- **Print at home** on plain white paper, single-sided.
- **Send to a helper:** forward the PDF to a friend or family member to print. (We have no email-send tool, so the firm
  drafts the message and the person sends it.)

**C. Sign and date by pen.** Tell the person exactly where: every signature line and every "this the ____ day of ____"
line, including the one on the Certificate of Service page. Same date the document is filed.

**D. File it with the court.** Confirm the method first `[CHECK LOCAL RULE / clerk]`:
- **In person at the Chancery Clerk:** bring the signed original plus copies and a photo ID. Ask the clerk to **file-stamp
  a copy for you to keep.** Ask about the filing fee, or file the **pauper's affidavit** if fees are an issue.
- **MEC e-file** if the district lets a pro se party e-file (confirm).
- **A proposed order** is delivered to the chancellor's chambers / court administrator rather than "filed" the same way.
  Use the right channel for the document type.
- **Temporary / pendente-lite relief (Rule 81(d)):** this is a **verified petition**, not a plain motion. Get the
  **hearing date first** from the court administrator, then have the clerk issue the **Rule 81 summons (Form 1D)** with
  that date, serve it **at least 7 days** before the hearing, and **file the proof of service** before the hearing. Hand
  the person through every step with the **Courthouse Navigator** (one micro-step at a time).

**E. Serve the other side the same day.** Whatever the Certificate of Service says is the method, do it that day. For
email service, send the PDF to the exact addresses listed (run it through **Communication Command** so the transmittal
is court-safe, one issue, no concessions). Keep the sent-email as proof. **Never improper ex parte contact with the
judge.**

**F. Confirm and calendar.** Get the file-stamped copy. If anything started a clock, write the date plus the deadline
down now. Update the case file / chronology and the Docket Watcher so nothing is a surprise.

---

## Branch — IF an order has already been signed or entered

When the person goes to the courthouse and finds a proposed order was already signed, the job changes from "object to
the form" to "correct an entered order." The firm switches automatically.

1. **Grab the proof and the clock.** Get the **file-stamped copy** and the **exact entry date**. Write down: entry date
   plus **10 days = the Rule 59(e) deadline** (verified jurisdictional, non-extendable). **Rule 60(a)** corrects a
   clerical mistake or omission **at any time**. (Both verified against the official MRCP, 2026-05-25.)
2. **Re-audit the signed version** (Order Integrity Reviewer) against the Source of Truth (transcript + adopted GAL rec).
   Identify which deviations actually made it into the signed order.
3. **Sort and split.** Clerical / does-not-match-the-ruling items go to Rule 60(a). Substantive interim-harm items
   (for example the decision-making expansion) go to Rule 59(e), filed inside the 10 days. Keep **one issue per motion**:
   a custody-conformity motion and a separate property/registry-conformity motion, never blended. Plead Rule 59(e), or
   in the alternative Rule 60(a), so the court can use whichever fits.
4. **Run the same Phase 1 production pipeline and Phase 2 delivery walkthrough** for each motion.
5. **Honest proportionality:** this is a temporary order and the real fight is the final trial. Fix the few things that
   genuinely harm the person now, raise discretionary schedule items at the final trial, and do not burn credibility
   over-litigating the temporary order.

---

## Discipline (non-negotiable)
- Runs under `operating-doctrine.md` and all firm-wide rules: citation discipline, one-issue, client-protection,
  anti-yes-man, the punctuation scrub, no fabrication.
- **Never invent** a fact, an address, a rule, a deadline, or a page number. Verify from a primary source or leave it
  out. A gap beats a wrong cite.
- **Show on screen before any PDF.** The PDF is always saved with a markdown copy beside it.
- The firm does the background production silently and **surfaces only the finished filing plus the plain-language
  walkthrough**. It reveals the behind-the-scenes trace on request ("show me what you did").
- End every hand-off with the single **NEXT ACTION**.
