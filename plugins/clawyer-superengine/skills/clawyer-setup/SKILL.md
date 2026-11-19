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
every technical step yourself, including finding and installing what the computer is missing. They answer
five questions and say yes once.

## Output contract (re-read this after any context compaction)

Setup is done only when all of these are true:

1. `firm.config.json` exists in the folder the person opened, with their state, county, matter name and kind
   of case. You wrote it by running `clawyer_init.py`, never by hand and never by asking them to.
2. `case-profile.md`, `CLAUDE.md`, the firm-layer files and `matters/<matter>/` exist. Nothing they already
   had was overwritten.
3. Python was found or installed by you (`.clawyer/.python` exists), the tools check has been run, and every
   missing tool is either installed or named to the person with what it costs them.
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

Before anything is created, confirm the folder in one line: "Your case files will live in this folder:
<folder name>. It should be a folder just for this case. Good to go?" If they already keep another kind of
case here, stop and ask them to open a separate, empty folder. A tax matter and a family matter never share
a folder, because a tax agency can hand what you send it to the other party.

## Step 2 - find Python (you do this, they watch)

Python is the free program that runs Clawyer's tools. Say first: "Checking for a free program called Python.
If it's missing I'll install it for you, just for your own account, with no admin password. That can take a
few minutes."

**Windows** (PowerShell tool, timeout 600000 ms):

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/find-python.ps1"`

It prints one line of JSON. Read `status`:
- `ok`: Python is found and its location is saved in `.clawyer\.python`. Go on.
- `no_winget`: Windows' "App Installer" is missing. Ask them to install "App Installer" from the Microsoft
  Store (a search and one click), then run this step again.
- `not_found`: the automatic install did not work. Ask them to install Python 3.12 from python.org and tick
  "Add python.exe to PATH" on the first screen, then close Claude completely, open it again in this folder
  and say "continue Clawyer setup". Offer a failure report.

**Mac** (Bash tool, timeout 600000 ms). Say also: "A box from Apple may ask to install developer tools.
That's fine, click Install."

`sh "${CLAUDE_PLUGIN_ROOT}/scripts/find-python.sh"`

- `ok`: saved in `.clawyer/.python`. Go on.
- `no_python`: if Apple's box appeared, they click Install, wait for it to finish, and you run this step
  again. If no box appeared, ask them to install Python 3.12 from python.org (double-click the installer and
  follow it), quit Claude completely (Cmd+Q), reopen it in this folder and say "continue Clawyer setup".
  With `"brew": true` Homebrew was already tried; offer a failure report.

Never repeat this step once `.clawyer/.python` exists.

### How every Python command is run from here on

A bare `python` is not reliable: on many computers it is missing or opens the Microsoft Store. **Wherever a
command in this skill, or in any Clawyer skill, agent or reference file, starts with `python`, start it with
the saved interpreter instead.** The rest of the command stays exactly as written.

- Bash tool (Mac, and Windows with Git Bash): `"$(cat .clawyer/.python)" "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" status`
- PowerShell tool (Windows): `& (Get-Content -Raw -Encoding UTF8 .clawyer\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" status`

## Step 3 - is it already set up?

Run the status check (read-only), using the saved interpreter:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" status`

- `set_up: true` and no `error`: say so, skip to Step 6 to check the tools, then Step 8.
- `set_up: true` with an `error`, or `matter_folder_exists: false`: the setup is damaged. Tell them in one
  line, then run Step 5 again with the same answers (read them from `firm.config.json` if it opens, ask again
  if it does not). It only fills in what is missing.
- `set_up: false`: go on to Step 4.

## Step 4 - five questions

Ask them one at a time.

1. **State.** "Which state is this case in?" This one cannot be left blank: the state decides which law
   applies. If they are unsure, ask which state the court or agency on their paperwork is in, or where the
   other side filed. If there is truly no paper yet, use the state they live in and tell them it can be
   changed.
2. **County.** "Which county?" (For a federal tax matter, the county where they live.) If unknown, record
   `[CONFIRM]`.
3. **Court or agency.** "Do you know which court or agency has it? It is usually printed at the top of the
   first page of any paper you received. If you don't know, say so." Unknown is fine: leave it empty.
4. **A name for the matter.** "What should we call this? A short label only you will see, like
   'Lease dispute' or 'IRS 2023 notice'."
5. **Kind of case.** Offer these, in these words. If they are unsure, pick "Something else":
   - Family (custody, divorce, child support) → `family-law`
   - A tax problem with the IRS or a state → `tax`
   - A business, contract or money dispute → `business`
   - Something else → `other`

Then two optional ones, only if they have a paper in hand: the case number, and any hearing or trial date.

`${CLAUDE_PLUGIN_ROOT}/docs/case-types.md` says what each kind of case switches on. For `tax`, pass
`--secondary federal` when the IRS is involved. For "something else", say plainly which topics have no
built-in reference yet; the method still works.

## Step 5 - write the case files

Run this yourself, from the folder they opened, with their answers (leave out the optional flags they did not
answer; dates are `YYYY-MM-DD`):

`python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" init --state "<state>" --county "<county>" --matter "<matter name>" --case-type <family-law|tax|business|other>`

Optional flags, each added only when there is a value: `--court "<court>"`, `--cause-no "<number>"`,
`--trial-date <YYYY-MM-DD>`, `--secondary federal`. Never pass an empty value such as `--court ""`: the
PowerShell tool drops it and the command fails.

It prints what it created and what it kept. It never overwrites. Choosing family law switches the family-law
pack on (`"packs": ["family-law"]`); there is nothing to copy and nothing for the person to install. Tell
them in one line what now exists: "Your case folder is ready. Your files are saved on this computer. To work on them I read them, and what I read goes to Anthropic, the company that makes Claude."

**To change a wrong answer later, or fill in one that was unknown** (state, county, court, kind of case): the script never overwrites, so edit
that one value in `firm.config.json` yourself with the Edit tool, show them the before and after, and when
the kind of case changes also set `packs` to `["family-law"]` for a family case or `[]` for any other.

## Step 6 - the free tools (one yes, then you install)

Check what is on the computer (read-only):

`python "${CLAUDE_PLUGIN_ROOT}/scripts/deps.py" check`

It prints JSON. `ready: true` means nothing is missing: say so and go on. Otherwise each missing item has a
plain `what` line. Ask once, naming what is missing in their words: "I need to add a few free tools so I can
read your documents and build print-ready PDFs: <the `what` of each missing item>. I'll do the installing.
Okay to start?" After that one yes (timeout 900000 ms):

`python "${CLAUDE_PLUGIN_ROOT}/scripts/deps.py" install`

Read each item's `status` and tell them the result in one short message:

- `ok` or `installed`: nothing to say beyond "done".
- `needs_person`: read its `person_step` and walk them through that one click (for example Windows asking
  "Do you want to allow this app to make changes?", Apple's developer-tools box, or quitting and reopening
  Claude so a new tool is picked up). Then run `check` again.
- `failed`: say so plainly, read them the item's `means` line (what will not work until it is fixed), carry
  on with the rest, and offer a failure report. Never say something installed when its status is `failed`.

Setup is ready when `ready` is true, or when every item that is not ready has been named to the person with
what it costs them. A missing scanned-page reader does not block typed documents.

## Step 7 - connect a source, then optional extras (ask, never front-load)

**Connect a source.** Read `${CLAUDE_PLUGIN_ROOT}/skills/clawyer-setup/references/connect-a-source.md` and
follow it. In short, and one at a time:

1. Tell them the citation check is already on: every court case Clawyer cites is checked against a free
   public database to catch made-up cases, with nothing to sign up for.
2. Find their court's official self-help page (a lookup, no connection) once the court is known.
3. Offer the calendar for deadlines, then their cloud documents folder, then email, only if it fits the case.
   Connecting is the person's own click. Record each answer so it is never asked twice:
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" sources --set calendar=declined`

**Other extras.** Offer only what fits their case, one at a time, and skip the rest:

- **A research notebook** (NotebookLM) for asking questions of their state's law: only if they want it. If the
  NotebookLM plugin is installed, use its setup; put the notebook id in `firm.config.json` under
  `notebooks.authority_library` yourself.
- **Heavier document tools**: only when a real document needs it (handwriting or a poor scan the normal
  reader cannot handle, or names that must be blacked out), and only after telling them what it adds: a
  stronger page reader, a name-redaction tool with its language model, a research-notebook helper, and a
  program that runs AI models on their own computer. Together these are several gigabytes. On a yes run
  `python "${CLAUDE_PLUGIN_ROOT}/skills/clawyer-setup/scripts/install_tier1.py"`. It reports what landed
  as JSON; relay failures plainly.
- **Their court's online docket:**
  `python "${CLAUDE_PLUGIN_ROOT}/skills/clawyer-setup/scripts/lookup_docket_portal.py" --state "<state>" --county "<county>"`.
  Most states are not in the built-in list. When theirs is missing, say so and ask them to paste the court's
  website address. Never invent a portal address.

The bundled references under `references/` in this skill (court PDF specs, the drafting constitution, the
citation audit) are for you, when a filing is being formatted. The person does not need to read them.

## Step 8 - hand off

One short, warm message: what is ready, that their case files are saved on their own computer, and the next thing to say.
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

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin clawyer-superengine --plugin-version 0.1.1 --skill clawyer-setup --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file .clawyer/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
