---
name: ghl-mcp-installer
description: Use this skill when a coaching client says "install the GoHighLevel MCP", "connect my GHL account to Claude", "set up GHL", "wire up GoHighLevel", or any phrase indicating they want Claude Desktop to talk to their GoHighLevel account. Walks the client through installing the GoHighLevel-MCP (mastanley13) into Claude Desktop step-by-step, getting their Private Integrations API key, and verifying the connection. Designed for non-technical users — narrate every step, confirm before each action, reassure liberally.
---

# GHL MCP Installer

Walk the client through installing the **mastanley13/GoHighLevel-MCP** into Claude Desktop. The client is non-technical. Your job is to be patient, narrate every step, confirm before doing anything, and never dump the whole list at once.

**Source:** https://github.com/mastanley13/GoHighLevel-MCP

---

## Tone (CRITICAL — read every time)

- One step at a time. Never give more than one action item per turn.
- Plain English. No jargon without an explainer ("a Node version is the engine that runs the GHL MCP — like making sure your car has the right fuel before you drive it").
- Reassure: "totally normal," "this is fixable," "we can pause anytime."
- Celebrate small wins.
- Always confirm before they do anything destructive (paste API keys, edit config files, restart apps).

---

## Pre-flight Check (Step 0)

Before starting, ask:
1. **"Are you on Mac or Windows?"** — config file paths differ.
2. **"Do you already have a GoHighLevel account with Settings → Integrations access?"** — they need to be on a plan that allows Private Integrations.
3. **"Are you comfortable opening a Terminal (Mac) or PowerShell (Windows) for a few commands?"** — if no, flag this. The install requires terminal use; we'll walk them through it slowly. If they're a hard "no" on terminals, recommend they ask a tech-savvy friend or pause and do this together over a screen-share.

---

## Phase 1 — Install Node.js (5 min)

> "First, we need to install something called Node.js. Think of it as the engine that runs the GHL connector. We do this once and forget about it."

1. Open browser → https://nodejs.org → download the **LTS** version (the green button on the left).
2. Run the installer with all default settings.
3. Verify by opening a terminal and typing:
   ```
   node --version
   ```
   They should see something like `v20.x.x`. Anything 18 or higher is fine.

**If something fails:** ask them to paste the error message. Common issues: PATH not set (need terminal restart), or Windows Defender blocking.

---

## Phase 2 — Get the GHL Private Integrations API Key (5 min)

> "Next we need to give Claude permission to talk to your GHL account. This is like giving someone a guest key to your house — you can revoke it any time."

1. Have them log into GoHighLevel.
2. **Settings → Integrations → Private Integrations**
3. Click **Create new private integration**.
4. Name it: `Claude MCP Server`
5. **Scopes to enable** (read these one at a time, get confirmation on each):
   - `contacts.readonly` and `contacts.write`
   - `conversations.readonly` and `conversations.write`
   - `opportunities.readonly` and `opportunities.write`
   - `calendars.readonly` and `calendars.write`
   - `locations.readonly` and `locations.write`
   - `workflows.readonly`
6. Click **Save**.
7. **Copy the API key** that GHL generates. It starts with `pit-` typically.

   > ⚠️ "This key is like a password. Don't post it anywhere. We're going to put it in one config file and that's it."

8. Then go to **Settings → Company → Locations** and copy your **Location ID** (looks like a string of letters and numbers).

**Save these two values somewhere safe** — they'll need them in Phase 4.

---

## Phase 3 — Download and Build the MCP Server (10 min)

> "Now we install the actual connector. We're going to copy a folder of code, install some helpers, and build it. I'll talk you through every command."

Open a terminal. Have them run **one command at a time**, waiting for each to finish before pasting the next.

1. **Clone the repo:**
   ```
   git clone https://github.com/mastanley13/GoHighLevel-MCP.git
   ```
   > "This downloads the MCP folder to your computer."

   *If `git` isn't installed:* download from https://git-scm.com/downloads → install with defaults → restart terminal → retry.

2. **Move into the folder:**
   ```
   cd GoHighLevel-MCP
   ```

3. **Install dependencies:**
   ```
   npm install
   ```
   > "This downloads all the helper pieces the MCP needs. Takes a minute or two. You'll see a lot of text scrolling — that's normal."

4. **Create the env file:**
   ```
   cp .env.example .env
   ```
   On Windows PowerShell, use:
   ```
   copy .env.example .env
   ```

5. **Edit the .env file.** Open it in any text editor (Notepad on Windows, TextEdit on Mac). Replace the placeholder values:
   ```
   GHL_API_KEY=<paste your Private Integrations API key from Phase 2>
   GHL_BASE_URL=https://services.leadconnectorhq.com
   GHL_LOCATION_ID=<paste your Location ID from Phase 2>
   NODE_ENV=production
   ```
   Save and close.

6. **Build it:**
   ```
   npm run build
   ```
   > "This compiles the code so Claude can use it. Should take ~30 seconds. Last step before we wire it up."

7. **Note the absolute path** to `dist/server.js`. From inside the `GoHighLevel-MCP` folder, run:
   - **Mac:** `pwd` then add `/dist/server.js`
   - **Windows:** `cd` then add `\dist\server.js`

   Save this full path. They'll need it in Phase 4.

---

## Phase 4 — Wire It Into Claude Desktop (5 min)

> "Last step — we tell Claude where to find the connector."

1. **Locate the Claude Desktop config file:**
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

   On Windows: copy `%APPDATA%\Claude\` into File Explorer's address bar.
   On Mac: in Finder, hit `Cmd+Shift+G` and paste the path.

2. **Open the file** in any text editor.

   - If the file doesn't exist yet, create it with:
     ```json
     {
       "mcpServers": {}
     }
     ```

3. **Add the GHL server entry** under `mcpServers`:
   ```json
   {
     "mcpServers": {
       "ghl-mcp-server": {
         "command": "node",
         "args": ["FULL_PATH_TO_DIST_SERVER_JS_FROM_PHASE_3"],
         "env": {
           "GHL_API_KEY": "your_private_api_key_from_phase_2",
           "GHL_BASE_URL": "https://services.leadconnectorhq.com",
           "GHL_LOCATION_ID": "your_location_id_from_phase_2"
         }
       }
     }
   }
   ```

   > ⚠️ Replace the three placeholder values. Use the **absolute path** for `args` (the one from Phase 3 step 7). On Windows, double the backslashes: `C:\\Users\\...\\dist\\server.js`.

4. **Save the file.**

5. **Quit Claude Desktop completely** (not just close the window — fully quit from the menu bar / system tray).

6. **Reopen Claude Desktop.**

---

## Phase 5 — Verify (2 min)

> "Let's make sure it's connected."

1. Start a new conversation in Claude Desktop.
2. Type:
   > "Search my GHL contacts for anyone with 'test' in their name."

3. If Claude responds with a list of contacts (or "no contacts found matching test"), the MCP is working. ✅

4. If Claude says it doesn't have access to GHL or asks how to do it manually, the MCP isn't connected. Walk through troubleshooting.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Claude doesn't recognize GHL after restart | Re-check `claude_desktop_config.json` — common: missing comma, unescaped backslashes on Windows, wrong path |
| "command not found: node" in terminal | Node not installed properly. Re-run Phase 1, restart terminal |
| `npm install` fails | Often a permissions issue. On Mac, try `sudo npm install`. On Windows, run terminal as Administrator |
| API key invalid error | Re-check Private Integrations scopes in GHL — they may have missed enabling one |
| Wrong Location ID | Settings → Company → Locations — copy the ID, not the name |

---

## After Install

1. **Confirm to client:** "You just connected Claude to your entire GoHighLevel account. From now on, I can read and update contacts, manage tags, work with your pipeline, and more — just by talking to you."

2. **Recommend next:** Run the `ghl-session-startup` skill in a fresh conversation to take stock of their account state.

3. **Save reminder:** "If you ever need to revoke this access, go to Settings → Integrations → Private Integrations in GHL and delete the integration. Done in 10 seconds."
