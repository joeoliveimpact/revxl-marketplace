# Connect a source

Outside tools that make Clawyer more useful. Every one is optional. Clawyer works without any of them, and a
missing connection is never a reason to tell the person a task cannot be done.

## Contents

- How to offer one
- Case law (CourtListener)
- The court's own self-help site
- Calendar
- Documents (Drive)
- Email
- Sources to leave alone in this version

## How to offer one

1. Read what is already decided:
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" sources`
   Offer only the ones marked `not-asked`. Never re-ask a `declined` one unless the person brings it up.
2. Offer one at a time, in one sentence that says what it gets them, then stop and let them answer.
3. **Connecting is always the person's own click.** Look at the tools this session already has. If a
   connector for the source is there, it is connected: say so and use it. If it is not, tell them it is added
   in the Claude desktop app's connector settings, wait for them to do it, and check your tool list again.
   Never ask for a password, a token or a code, and never type one for them.
4. Record the answer so it is not asked again:
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" sources --set calendar=connected`
   (states: `connected`, `declined`, `not-asked`; names: `case_law`, `calendar`, `documents`, `email`,
   `court_site`).
5. Read-only by default. Anything that writes to their account (a calendar entry, an email draft) is shown
   to them first and needs a yes each time.

## Case law (CourtListener)

Free database of US court opinions, run by a non-profit.

- **Nothing to connect for the citation check, so there is nothing to record for it.** `cite_lookup.py` in the pro-se-firm skill confirms that a
  cited case exists using CourtListener's public pages. No account.
- **Optional, for searching case law by topic:** a CourtListener connector, if the person has added one. With
  it, the `legal-researcher` agent can search opinions and dockets directly. Without it, research uses
  official court and legislature sites on the web.
- Say: "I check every case I cite against a free public database, to catch made-up cases before they reach your papers.
  That part is already on."

## The court's own self-help site

No connection. This is a lookup you do once.

1. Search for the official self-help page and forms page for the court in `firm.config.json`. Official means
   the court system's or the state judiciary's own site, not a law firm and not a forms seller.
2. Open it and confirm it is the right court and county.
3. Save it: `python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" sources --set court_site=connected --court-site-url "<address>"`
4. Note in `case-profile.md` what the page offers: forms, filing fees, e-filing, a self-help desk and its
   hours, free legal help. Tag anything you did not read on the page itself `CONFIRM-BEFORE-CITING`.

If the court is unknown, do this as soon as it is known. If no official page can be found, say so and
record `declined`.

## Calendar

- **What it gets them:** every confirmed deadline and hearing lands on their own calendar with a reminder.
- **Rule:** only dates tagged `[CONFIRMED]` (read from a court paper or an official source) go on the
  calendar. A date that is `CONFIRM-BEFORE-CITING` goes on as "CONFIRM: ..." or not at all.
- **Each entry is shown first** (title, date, reminder) and needs a yes. The title carries the matter's short
  name and what is due. No facts about the case, no other party's name.
- Without a calendar connector: keep the dates table in `case-profile.md` current and read the next deadline
  out at the start of each session. The session-start hook already shows the hearing date.

## Documents (Drive)

- **What it gets them:** Clawyer can find and read case papers they keep in their cloud folder, without them
  downloading each one.
- Read only. Copy what is needed into the matter's `evidence/` folder and convert it there, so the case
  record stays on their computer. Never move, rename or delete anything in their Drive.
- Without it: they drop files into the chat or the `evidence/` folder.

## Email

- **What it gets them:** messages with the other side or the court can be pulled in as dated evidence.
- Read only, and only threads the person points to. Save each as a file in `evidence/` with its date.
- **Never send.** A reply to the other side is drafted in the matter's drafts folder, goes through the
  premortem, and is sent by the person themselves.
- Without it: they forward or paste the messages.

## Sources to leave alone in this version

Named in older reference files, not set up by Clawyer 0.1.1: paid research services, practice-management
systems, co-parenting apps, speaker separation for audio, and a task tracker. If the person already has one
connected and asks to use it, use it read-only under the rules above. Do not offer to set one up.
