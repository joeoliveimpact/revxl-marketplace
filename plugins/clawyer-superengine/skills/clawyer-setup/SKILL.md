---
name: clawyer-setup
description: >-
  First-time setup for Clawyer. Use when someone says "set me up", "set up Clawyer", "get me started",
  "I just installed this", "start my case", "install everything", "nothing is set up", or when any Clawyer skill
  finds no firm.config.json in the folder. Asks five plain questions (state, county, court, a name for the
  matter, and what kind of case it is), writes the case files into the person's own folder, switches on the
  matching case-type pack, and installs the free tools the firm needs. The person never types a command and
  never edits a file. Also use to repair a setup whose tools are missing. Not for ordinary case work once
  setup is done.
---

# Clawyer setup

Take a person who has never used a terminal from "I installed the plugin" to a working case folder. You do
every technical step yourself. They answer five questions and say yes once.

## Output contract (re-read this after any context compaction)

Setup is done only when all of these are true:

1. `firm.config.json` exists in the folder the person opened, with their state, county, matter name and kind
   of case. You wrote it by running `clawyer_init.py`, never by hand and never by asking them to.
2. `case-profile.md`, `CLAUDE.md`, the firm-layer files and `matters/<matter>/` exist. Nothing they already
   had was overwritten.
3. The environment check has been run and every gap is either closed or named to the person in plain words.
4. You told them, in one short message, what was created, what is still optional, and the one next thing to say.

**Re-invoke guard:** if this skill's text looks cut off, load it again before continuing.

## Posture

- Plain words, short messages, one question at a time. Use the clickable question tool when it is available.
- Never show a raw command and never ask them to run one. Narrate instead: "I'm setting up the part that
  reads scanned documents now."
- Say once, early and without drama: Clawyer is a tool, not a lawyer, and gives legal information, not legal
  advice. For big decisions they should check with a licensed attorney.
- Never claim something installed that did not. Never invent a step.
- A friend on a screen-share is a fine way to do this. Offer it if they freeze.

## Step 1 - is this the right folder?

Run the status check (read-only):

`python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" status`

- `set_up: true` → say so, skip to Step 4 to check tools, then Step 6.
- `set_up: false` → confirm the folder with them in one line: "Your case files will live in this folder:
  <folder name>. It should be a folder just for this case. Good to go?" If they already keep another kind of
  case here, stop and ask them to open a separate, empty folder. A tax matter and a family matter never share
  a folder, because a tax agency can hand what you send it to the other party.

If `python` itself is not found, that is the first gap. Do Step 4's Python install first, then come back.

## Step 2 - five questions

Ask them one at a time. If they do not know one, record `[CONFIRM]` and move on. Do not guess for them.

1. **State.** "Which state is this case in?"
2. **County.** "Which county?" (For a federal tax matter, the county where they live.)
3. **Court or agency.** "Do you know which court or agency has it? It is usually printed at the top of the
   first page of any paper you received. If you don't know, say so." Unknown is fine.
4. **A name for the matter.** "What should we call this? A short label only you will see, like
   'Lease dispute' or 'IRS 2023 notice'."
5. **Kind of case.** Offer these, in these words:
   - Family (custody, divorce, child support) → `family-law`
   - A tax problem with the IRS or a state → `tax`
   - A business, contract or money dispute → `business`
   - Something else → `other`

Then two optional ones, only if they have a paper in hand: the case number, and any hearing or trial date.

`${CLAUDE_PLUGIN_ROOT}/docs/case-types.md` says what each kind of case switches on. For `tax`, pass
`--secondary federal` when the IRS is involved. For "something else", say plainly which topics have no
built-in reference yet; the method still works.

## Step 3 - write the case files

Run this yourself, from the folder they opened, with their answers (leave out the optional flags they did not
answer; dates are `YYYY-MM-DD`):

`python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" init --state "<state>" --county "<county>" --court "<court or empty>" --matter "<matter name>" --case-type <family-law|tax|business|other>`

Optional flags: `--cause-no "<number>"`, `--trial-date <YYYY-MM-DD>`, `--secondary federal`.

It prints what it created and what it kept. It never overwrites. Choosing family law switches the family-law
pack on (`"packs": ["family-law"]`); there is nothing to copy and nothing for the person to install. Tell
them in one line what now exists: "Your case folder is ready. Your facts stay on this computer."

## Step 4 - the free tools (one yes)

Run the read-only detector and read its GAPS list:

`python "${CLAUDE_PLUGIN_ROOT}/skills/clawyer-setup/scripts/check_environment.py"`

If there are gaps, ask once: "I'm going to set up a few free tools on your computer so I can read your
documents and build court-ready PDFs. I'll tell you what each one is as I go. Okay to start?" After that one
yes, install only what is missing, and re-run the detector to confirm.

**Windows (winget):**
- Python: `winget install -e --id Python.Python.3.12`
- Reader for scanned documents: `winget install -e --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements`
- Git (it is what runs Clawyer's start-of-session reminders): `winget install -e --id Git.Git`

**macOS (Homebrew; install it first if missing):** `brew install python@3.12 tesseract git`

**Then, any system, only the missing ones:**
`python -m pip install reportlab pdfminer.six pyspellchecker pdfplumber markitdown pymupdf pytesseract pypdf pillow`

Reading the detector: ignore every line that ends in "venv" and the browser line (optional extras from the
original tool). The gap named `spellchecker` is closed by the `pyspellchecker` package above. Because of the
"venv" lines the detector's own `ready` flag stays false. Setup is ready when no other gap is left. If an install fails, say so plainly, carry on with
the rest, and tell them what will not work until it is fixed (for example: "I can't read scanned pages yet;
typed PDFs are fine").

## Step 5 - optional extras (ask, never front-load)

Offer only what fits their case, one at a time, and skip the rest:

- **A research notebook** (NotebookLM) for asking questions of their state's law: only if they want it. If the
  NotebookLM plugin is installed, use its setup; put the notebook id in `firm.config.json` under
  `notebooks.authority_library` yourself.
- **Heavier document tools** (stronger OCR, name redaction): run
  `python "${CLAUDE_PLUGIN_ROOT}/skills/clawyer-setup/scripts/install_tier1.py"` only when a real document
  needs it. It reports what landed as JSON; relay failures plainly.
- **Their court's online docket:**
  `python "${CLAUDE_PLUGIN_ROOT}/skills/clawyer-setup/scripts/lookup_docket_portal.py" --state "<state>" --county "<county>"`.
  Most states are not in the built-in list. When theirs is missing, say so and ask them to paste the court's
  website address. Never invent a portal address.

The bundled references under `references/` in this skill (court PDF specs, the drafting constitution, the
citation audit) are for you, when a filing is being formatted. The person does not need to read them.

## Step 6 - hand off

One short, warm message: what is ready, that their facts stay on their computer, and the next thing to say.
For example: "You're set up. Nothing technical left. Tell me what's going on, or drop in the first paper you
received." From here the `pro-se-firm` skill takes over, and the `matter-intake` skill opens any further
matter in this folder.

## What this skill cannot do

It runs only after the plugin is installed. Installing the plugin and signing in are the person's own clicks.
Signing in to any account of theirs is always theirs to do, in their own browser.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `.clawyer/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text). This is a legal matter, so also never a party's name, a case
   number, a date from the case, an amount, or a single word from any document.
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin clawyer-superengine --plugin-version 0.1.0 --skill clawyer-setup --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file .clawyer/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
