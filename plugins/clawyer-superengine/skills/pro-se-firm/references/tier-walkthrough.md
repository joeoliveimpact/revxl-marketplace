# Tier 2 / 3 / 4 Walkthrough Scripts

> Crawl-mode prompts used by `firm-setup`. One step at a time, plain English, verify each step landed before moving on. Never paste a wall of instructions. Anti-AI-tells scrubbed (no em-dashes, no semicolons, no "delve" or "moreover").
>
> All Tier 2/3/4 items below have the same shape, so the firm can pick any one and walk it without thinking about the others.

## Posture (every walkthrough)
1. Tell them what this tool does, in one short line.
2. Tell them why they may or may not need it for their case (read `case-profile.md` first).
3. One micro-step at a time. After each step, wait for them to say "done" or describe what they see.
4. Verify-step at the end. If anything looks wrong, walk back to the last good step, do not skip.
5. After the tool is live, write the row into `FIRM-TOOLING-INVENTORY.md` and refresh `FIRM-PATHWAYS-MAP.md`.

---

## TIER 2 -- one-time browser approve

### 2a. Claude Code plugin installs (litigation-legal, superpowers, law-student, legal-builder-hub)

These four plugins are not auto-installable from outside Claude Code. Walk through each.

**Open script (say to the user):**
"I want to add four more tools that the firm uses. They live inside this same app. I will walk you through each one, one at a time. You will click the same way every time, so once you do the first, the rest are quick. Ready?"

**For each plugin, in this order: litigation-legal, superpowers, law-student, legal-builder-hub.**

Step 1: "In this Code area, type a forward slash. A small menu should open. Tell me when you see it."
Step 2: "Type `plugin marketplace install` after the slash, then a space."
Step 3: "Paste this exact name: `[PLUGIN-NAME]`. Press Enter."
Step 4: "It may ask whether to trust. Click Yes."
Step 5 (verify): "Type `/plugin` and press Enter. Find the new one in the list and tell me what status it shows next to it."
Step 6: "Type `/reload-plugins` and press Enter."

**If the menu does not open:** the app may need to restart. Say: "Close the Claude app fully and open it again. Then come back here and tell me what you see."

**Inventory write after each:** append a row to the user's `FIRM-TOOLING-INVENTORY.md` under "Claude Code Plugins Installed" with name, today's date, and "active."

---

### 2b. OAuth -- the five sign-ins (NotebookLM, Google Calendar, Google Drive, Gmail, Linear)

**Open script:** "I want to connect the firm to your accounts so it can read your calendar, save research notebooks, look at your emails, and track your tasks. Each one is the same kind of one-time sign-in. We will do them one at a time. You can stop after any of them. Ready?"

#### NotebookLM browser login (Google)
1. "Open your normal web browser (not in this app)."
2. "Go to notebooklm.google.com"
3. "Sign in with your Google account. If you have two-factor, do that too."
4. "When you see your notebooks list, tell me."
5. Verify-step: back in the firm, run `notebooklm list` (the firm runs it, not the user). If it returns notebooks, OK. If it says "not signed in," the cookie has not been picked up. Walk them through the `notebooklm-setup` skill's session-capture step.

#### Google Calendar MCP
1. "In the Code chat box, type `/mcp` and press Enter."
2. "Find the row for Google Calendar. Click `Connect` next to it."
3. "A browser window will open and ask you to sign in with Google."
4. "Pick the same Google account you used for NotebookLM."
5. "Click `Allow` on the permissions screen."
6. "Come back to the app. Tell me what `/mcp` shows next to Google Calendar now."
7. Verify-step: firm runs `list_calendars`. If at least one calendar comes back, OK.

#### Google Drive MCP
Same as Calendar, just pick the Google Drive row.

#### Gmail MCP
Same. Pick the Gmail row.

#### Linear MCP
1. "In the Code chat box, type `/mcp` and press Enter."
2. "Find the row for Linear. Click `Connect`."
3. "Sign in to Linear in the browser window. If you do not have an account, make a free one first."
4. "Click Authorize."
5. Verify-step: firm runs `list_teams`. If a team comes back, OK.

**Inventory write after each:** append a row to "MCP Connectors" with name, today's date, "Active."

---

### 2c. iCloud for Windows (Windows users only)

**Skip on Mac.** iCloud is already built into macOS.

1. "Open the Microsoft Store on your computer."
2. "Search for `iCloud`."
3. "Click the one published by Apple. Click Get / Install."
4. "Open it after it installs."
5. "Sign in with your Apple ID."
6. "Tick the boxes for Photos, iCloud Drive, and anything else you want."
7. "Click Apply."
8. Verify-step: open File Explorer; you should see an `iCloud Drive` folder. Tell me when you see it.

**Inventory:** add to "External CLIs / Desktop Apps."

### 2d. Trellis (auth check only -- came in with litigation-legal)

litigation-legal already wires Trellis. Just verify.
1. "In the Code chat, type a question that would use a matter, like `list my matters`."
2. If Trellis prompts for sign-in, walk them through the email/password screen.
3. Verify: a matter list comes back, even if empty.

---

## TIER 3 -- account creation + token

### 3a. CourtListener OAuth (state/court-level aware)

**Pre-check the firm runs silently:** read `case-profile.md` and look for `state`, `court_level` (state vs federal), and `court` (e.g., "your court's district, Harrison County").

**Open script if the case is purely state court (most family-law cases):**
"CourtListener is a free public archive of federal court records. Your case is in state court, so it does not have your docket in it. But it is still useful for looking up federal case law that other lawyers cite. Want to set it up? It is free. Takes about five minutes."

**Open script if the case touches federal court:** "Your case has a federal piece. CourtListener has the federal docket. Want to set it up? It is free."

Steps:
1. "Open your web browser and go to courtlistener.com"
2. "Click Sign up in the top right."
3. "Use your real email. Pick a password. Write the password down."
4. "Check your email for a verification link. Click it."
5. "Sign in. Then click your name in the corner and choose `Profile`."
6. "Scroll down to `API Tokens` or `API Access`. Click `Create a Token`."
7. "Copy the token it shows. Paste it back to me here. I will store it in the firm so we never have to ask again."

Firm-side: write the token into a local secrets file (`.claude/secrets/courtlistener.token`, chmod 600 on Mac), then run a test query to confirm.

Verify-step: firm runs a one-call test against the CourtListener API. If it returns 200, OK.

**Inventory write:** flip the CourtListener row to "Active."

---

### 3b. pyannote HuggingFace token (only if multi-speaker audio detected)

**Gating rule:** only fire this walkthrough if the case-profile lists audio evidence AND that audio has more than one speaker (the firm flags this when audio is ingested). If neither is true, leave dormant.

When triggered, say:
"You have audio recordings with more than one voice in them. pyannote is the tool that separates the voices so the firm can label who said what. It is free but needs you to make a HuggingFace account."

1. "Open your browser and go to huggingface.co"
2. "Click Sign Up. Use your real email."
3. "Verify your email."
4. "Sign in. Go to huggingface.co/pyannote/speaker-diarization-3.1 and click `Agree and access repository`."
5. "Click your profile picture, then Settings, then Access Tokens."
6. "Click `New token`. Name it `pro-se-firm`. Choose Read access. Create."
7. "Copy the token and paste it back to me."

Firm-side: store in `.claude/secrets/huggingface.token`, run a test load of the diarization pipeline.

**Inventory:** flip pyannote row to "Active."

---

## TIER 4 -- state/county-aware docket subscription

### 4a. Docket subscription (state and county detection)

**Pre-step the firm runs silently:**
1. Read `case-profile.md` for `state` and `county`.
2. Open `references/state-docket-portals.yaml` and look up the state. Then the county under that state.
3. Three branches:
   - **Both found.** Walk the user through the system_name + county portal_url using the signup_steps stored in the YAML. Use the cost_note in the script.
   - **State found, county not found.** Use the state-level system_name and ask the user to paste their county clerk URL. Offer to append the new county to the YAML.
   - **State not found.** Ask the user to paste their county's online docket portal URL, or say they do not have one. Append a starter entry for that state if they paste a URL.

**Open script template (filled from YAML):**
"Your state's electronic court-records system is `{system_name}`. Your county's portal is `{portal_url}`. Cost is `{cost_note}`. Setup takes about ten minutes. Want to walk through it?"

**Open script for missing state:** "I do not have your state's court-records portal on file yet. Two options. One, paste the URL of your county's online docket if you have it. Two, tell me you do not have one and I will skip this step. Which one?"

**Walk steps (from YAML signup_steps, one at a time):** for each step, say it, wait for confirmation, then move to the next.

**Verify-step:** ask the user to open their own case (or any case in their county) on the portal and confirm they see docket entries. If yes, OK.

**Inventory write:** append a row to "External CLIs / Desktop Apps" or a new "Docket Subscriptions" section with state, county, system, cost, and today's date.

**Pathways write:** if the docket portal creates an auto-fire pathway (e.g., daily check), add it to `FIRM-PATHWAYS-MAP.md` under a new "Docket Watcher" subsection.

---

## When a walkthrough fails

Never pretend it worked. Say plainly: "That step did not land. What do you see on screen?" If still stuck after two retries, offer the screen-share / friend path the same way the install does. Mark the row in the inventory as `BLOCKED -- <one-line reason>` so the next session knows.
