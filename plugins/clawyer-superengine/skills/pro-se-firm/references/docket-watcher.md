# Docket Watcher

Job: watch the court's docket so the user is **never surprised** by a hearing, date, or filing. Runs automatically on a
schedule and alerts the user when something changes.

## What it does
- Checks the court's online docket for the user's case on a schedule (e.g., daily).
- Compares against the last check; if anything is new or changed, it **writes a plain-language alert** and (optionally)
  **emails** the user.
- Pairs with a **calendar tool**: new hearing dates can be added to the user's calendar.

## Setup (per case — lives outside the skill, like the case profile)
1. **Find the court's public docket.** Most county/court sites have one. Confirm whether it needs a login.
   - *Free public docket* (search by name/date) → easiest to watch.
   - *Locked court system* (e.g., an e-filing portal) → the user usually needs a free read-only account first; richer
     data (actual filings, not just hearings).
2. **Configure** `docket-config.json` next to the script: the docket URL, how it searches (name vs. case number), the
   user's search term (a party last name), and the **cause/case number** to filter to.
3. **Schedule it** to run daily (OS task scheduler / cron). Set it to **run-if-missed** and **wake from sleep** so a
   powered-off morning doesn't skip a day.
4. **(Optional) email alerts** — supply mail credentials (e.g., a Gmail *app password*, never the real password) so the
   watcher can push the alert to the user's phone/email. The in-workspace alert note works with no setup.

## Honest limits
- "Automatic" means **on a schedule**, and only runs when the machine is available (run-if-missed mitigates this).
- **Every court's docket site is different** — the bundled script (`scripts/docket_watch.py`) targets a common
  "ASP form" county docket and is **a template to adapt**, not a universal scraper. Confirm it reads the right case.
- A docket may show **hearings** but not **filings** unless you have the locked-system account.
- Verify any date it reports before relying on it — treat it as a heads-up, then confirm with the clerk.

## Output
`DOCKET-ALERT.md` (plain-language, what changed) + optional email. End with a NEXT ACTION (usually: confirm a new date
with the clerk, or calendar it).
