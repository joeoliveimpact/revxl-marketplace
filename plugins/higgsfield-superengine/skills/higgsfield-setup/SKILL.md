---
name: higgsfield-setup
description: Use this skill the first time a coach or client wants to make images or videos with Higgsfield through Claude, or when their Higgsfield connection stops working. Trigger phrases include "set up Higgsfield", "connect my Higgsfield account", "add my Higgsfield key", "Higgsfield setup", "my Higgsfield key is not working", "I topped up Higgsfield", "update my Higgsfield balance". Finds Python, walks the client through the Higgsfield website (sign in, add funds, create the key) while Claude keeps its eyes off the key, saves the key in a masked box, checks it with a free call and records the balance. Windows and Mac.
---

# Higgsfield setup (one time, about 10 minutes)

## Output contract (what the client ends up with)

- Python found, and its location recorded in `higgsfield\.python` in the workspace folder.
- Their Higgsfield API key saved by the key box (Windows user settings, or the Mac Keychain). The key never appears in the chat, in a workspace file, or on Claude's screen.
- A free key check that printed `AUTH OK`.
- Their balance recorded in the spend ledger, so the safety cap is right.
- One closing message in plain English: "You're set up. Your balance is $X. Jobs up to $Y run after a price check; anything bigger asks you first." Then offer a first image.

## Re-invoke guard (read before step 1)

- If the conversation was compacted since this skill loaded, invoke this skill again before going on. Later steps may be missing from memory.
- Never repeat a finished step. First run, in the PowerShell tool: `Test-Path higgsfield\.python`
  - `False`: start at step 1.
  - `True`: first run the no-look status (PowerShell tool), then the step 8 check:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/hooks/hf_guard.py" no-look status`

    - state `on`, `expired` or `leaving`: a key may still be on screen. Resume inside step 7 and do not look at the browser.
    - check says `AUTH OK`: already connected. Do only step 9 (balance), unless the client asks for a new key.
    - anything else: resume at step 4.

## Ground rules

- **The client never types a command.** Claude runs every command below in the tool named. The client only clicks, signs in, pays, and pastes into the key box.
- Plain English, one step at a time, for a busy coach. Gloss each term once, e.g. "API key (a private password that lets Claude use your Higgsfield account)".
- Claude Code may show permission pop-ups along the way. Say what each one is before it appears; the client decides. Never promise there will be none.
- Run every command from the workspace folder, as ONE plain command: no `cd` or `Set-Location` first, and no `;`, `&&` or pipes around a plugin script. The plugin's safety guard blocks anything else.
- Keep every quote exactly as written. `${CLAUDE_PLUGIN_ROOT}` is the plugin's own folder.
- The default tool timeout is 2 minutes. Where a step gives a timeout, set it on the tool call.
- Never ask for the key in chat. If the client pastes it into the chat anyway, do not repeat or store it: have them delete that key on the API keys page (the "..." menu, then Delete) and make a new one in step 7.

## Mac

Same steps as Windows below, with these translations everywhere:
- Use the **Bash tool** wherever a step says PowerShell tool.
- Start every Python command with `"$(cat higgsfield/.python)"` instead of `& (Get-Content -Raw -Encoding UTF8 higgsfield\.python)`. The rest of the command stays the same, for example step 8: `"$(cat higgsfield/.python)" "${CLAUDE_PLUGIN_ROOT}/scripts/hf_rest.py" check`
- Re-invoke guard: `test -f higgsfield/.python && echo yes` instead of `Test-Path`.
- Keyboard: Cmd+V, not Ctrl+V. "Close Claude completely" means Claude menu, then Quit Claude (Cmd+Q), not just the window.

The steps that differ:
- **Step 2:** skip it (Windows only).
- **Step 3, find Python** (Bash tool, timeout 600000 ms). Say the same line first ("no admin password"), then run:

`sh "${CLAUDE_PLUGIN_ROOT}/scripts/find-python.sh"`

  It prints one JSON line. `ok`: Python is recorded in `higgsfield/.python`; go on. `not_found` or `no_curl`: the automatic install didn't work. Ask the client to install Python 3.12 from python.org (the macOS installer), quit and reopen Claude, and ask for Higgsfield setup again. Offer a failure report. Never run `python3` bare on a Mac: if Apple's developer tools are missing, it opens an install pop-up.
- **Step 4:** the same `echo api.higgsfield.ai` check in the Bash tool, the same habits. Not blocked: quit Claude completely (Cmd+Q), open it again in this folder, and say "continue Higgsfield setup".
- **Step 7c, the key box** (Bash tool, timeout 360000 ms). Say: "A small box will pop up. Click inside it, press Cmd+V, then OK. It hides what you paste."

`"$(cat higgsfield/.python)" "${CLAUDE_PLUGIN_ROOT}/scripts/hf-key-box.py"`

  It prints one word, read as in step 7c: `saved`, `invalid`, `cancelled`, or `error` (the Mac Keychain did not keep the key: try once more, then offer a failure report). The key is kept in the client's Mac Keychain, not in a file. If macOS asks whether to allow access to the Keychain, the client decides; say it is the plugin reading its own saved key.

## Windows steps

### 1. Say what's coming

"This takes about 10 minutes. I'll check your computer has Python (a free tool the plugin runs on), then walk you through the Higgsfield website to add funds and make your key. Have a card ready: the minimum top-up is $5."

### 2. Folder location check (PowerShell tool)

`(Get-Location).Path.Length`

`(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem').LongPathsEnabled`

If the length is over 170 and the second value is not `1`, the folder sits too deep for Windows' 260-character path limit, and the price check's files would fail. Say: "Your workspace folder is buried a bit too deep for Windows. Please open a folder with a shorter location in Claude (for example Documents\Higgsfield) and ask me to set up Higgsfield again there." Stop here.

### 3. Find Python (PowerShell tool, timeout 600000 ms)

Say first: "Checking for Python. If it's missing I'll install it for you, just for your user account, no admin password. That can take a few minutes."

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/find-python.ps1"`

It prints one JSON line. Read `status`:
- `ok`: Python is recorded in `higgsfield\.python`. Go on.
- `no_winget`: Windows' "App Installer" is missing. Explain its `fix` hint in plain words (the client installs App Installer from the Microsoft Store), then run this step again.
- `not_found`: the automatic install didn't work. Ask the client to install Python 3.12 from python.org (tick "Add python.exe to PATH"), close and reopen Claude, and ask for Higgsfield setup again. Offer a failure report.

### 4. Safety guard check (PowerShell tool)

`echo api.higgsfield.ai`

This must be **blocked** with a message starting "Blocked by the higgsfield-superengine spend guard". Tell the client: "That block is good news. The plugin's safety guard is on." Then name the two habits that keep it working: "Keep this plugin turned on for all your folders (install it for your user, not one project), because the guard only protects sessions where it's on. And don't run Higgsfield jobs in the mode that skips permission pop-ups (bypass): there the guard can't ask you, so it refuses anything over your cap."

If it is NOT blocked (it just prints `api.higgsfield.ai`), the guards are not running. Usually Python was just installed and Claude started before it. Say: "Please close Claude completely, open it again in this same folder, and say 'continue Higgsfield setup'." Do not go on to the key while the guards are off: the guard that hides the key from Claude would not work.

### 5. Open the Higgsfield website

Open https://open.higgsfield.ai with the browser's navigate tool (in Claude Desktop this is the Browser pane). No browser tools here? Ask the client to open that address in their own browser, and guide them by words only.

- **Sign in:** the client clicks Sign in and picks Google, email, GitHub, Apple, Microsoft or company login. Claude never types their password. Google is known to work inside the pane; if another method fails there, the client uses their own browser.
- New accounts may see an offer for finishing onboarding tasks. Optional.

### 6. Add funds (at least $5)

Guide: **Billing** in the left menu, then **Add funds**, then $5 or more (the minimum is $5), then pay. The client types the card details and clicks pay; Claude never enters card details or clicks a pay button. If checkout won't finish inside the pane, the client pays in their own browser. Leave Auto top-up off unless they ask for it.

### 7. Create the key, with Claude's eyes off the screen

**Before** the client clicks Create API key, turn the screen guard ON (PowerShell tool):

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/hooks/hf_guard.py" no-look on`

Expect `"state": "on"`. From now until 7d is done, do not screenshot, read, or click in the browser (the guard blocks it anyway). Guide by words only:

a. "Click **API keys** in the left menu, then **Create API key**. Name it something like Claude."
b. "A box called **Save your API key** appears. Higgsfield shows this key only **once**. Click the copy button next to the key. Don't click Done yet. Tell me when it's copied."
c. Open the key box (PowerShell tool, timeout 360000 ms). Say: "A small box will pop up. Click inside it, press Ctrl+V, then OK. It hides what you paste."

`powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "${CLAUDE_PLUGIN_ROOT}/scripts/hf-key-box.ps1"`

It prints one word:
- `saved`: "Saved. Now click Done on the Higgsfield box."
- `invalid`: "That didn't look like the whole key. It's still copied, so let's try once more." Open the key box again.
- `cancelled`: the box was closed, or it timed out after 5 minutes. If the Higgsfield box is still open, open the key box again. If they already clicked Done, the key can't be shown again: they create a new key (and delete the unsaved one), then repeat from b.

d. Only after `saved` AND the client says the Higgsfield box is closed, clear the guard (PowerShell tool):

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/hooks/hf_guard.py" no-look off`

A pop-up asks whether the key is off the screen. Say first: "This pop-up is you confirming the key is hidden. Click Allow only if the Higgsfield key box is closed." Then navigate the browser to https://open.higgsfield.ai/dashboard with the navigate tool on its own (not inside a batch). That finishes clearing the guard. If a pop-up later asks "Is the API key off the screen?", the client answers it, never Claude.

### 8. Check the key (free, PowerShell tool)

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/hf_rest.py" check`

This costs nothing: it only asks Higgsfield for a price quote. Read the JSON `class`:
- `ok` and the line `AUTH OK`: "Connected."
- `invalid_credentials`: the saved key is wrong or was deleted. Repeat step 7 with a new key.
- `no_key` or `key_malformed`: the key box didn't save it. Repeat step 7.
- anything else: explain its `message` in plain words and try once more. Still failing: offer a failure report.

### 9. Record the balance (PowerShell tool)

Read the balance (in US dollars) at the top of the dashboard, or ask the client to read it out. Then record it, as a plain number with no $ sign:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" balance set 12.50`

The reply's `cap_usd` is the silent cap: the smaller of $5 and 25% of the balance. Say: "Jobs up to $<cap_usd> run after a price check. Anything bigger asks you first." Run this step again whenever the client says they topped up.

### 10. Done

Send the closing message from the output contract. Offer: "Want to make your first image? Just describe it." That runs the `higgsfield-superengine:hf-generate` skill.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, then offer: "Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `higgsfield/reports/report-body.md`: what the client was doing, which step failed, the output's `class` and `message`. Never the key.
2. Draft it (PowerShell tool). Keep the summary short, in single quotes, with no apostrophes and no script names:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin higgsfield-superengine --plugin-version 0.1.3 --summary 'Setup failed at the key check' --body-file higgsfield/reports/report-body.md --error-code invalid_credentials`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is so they can email it to Joe. Skip instead:

`& (Get-Content -Raw -Encoding UTF8 higgsfield\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

Before step 3 (no Python yet), there is no report script to run: tell the client to screenshot the message and send it to Joe.
