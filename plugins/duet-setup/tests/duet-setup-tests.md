# Test prompts for duet-setup

Seven prompts for v0.3.1. Run each in a fresh session with the plugin on. Every test also checks the version line: the skill's first reply says "duet-setup v0.3.1". In test 6 the skill must not load, so no version line appears.

Baseline (no skill, Nov 4 2026, tests 1 and 3): asked good questions but had no Rules-in-memory split, no review round, no routing map, no channel map in main chat memory, guessed the tracker layout, and had no working route to Claude Code.

### 1 Fresh setup, Linear on a Free plan
Setting: client's Duet main chat, brand-new; Linear connected; Linear plan is Free.
Prompt: "I just got Claude Duet. My coach set his up with a main chat plus separate channels for email, research, content and clients, each with its own instructions and rules. Help me set mine up the same way."
Should trigger: yes
First file Claude should open: references/planning-channels.md
Done looks like: first reply starts with "duet-setup v0.3.1"; light first message (no checklist until step 2); asks what the coach's channels are or offers them as a suggestion; recommends starting with one channel and growing to three to six, and follows the client's choice; one question per message; client names the coordinator and every channel, with names checked for voice-to-text; channel map table approved before any channel is created; client reads the plan in Linear Billing and it is Free, so one team plus a project per channel (no sub-teams), projects created only on yes; each instructions block passes check_instructions.py and carries the one routing-map pointer line; the client opens each channel's instructions field by hovering the channel, then the 3-dot menu, then Instructions; Rules sent by the client in each channel; review note to each channel before locking; check note after install, with the channel quoting the last line of its instructions word for word; each new channel runs the first-day checklist; the main chat writes and saves its own instructions from what the client tells it; channel map, routing rule and the map's owner saved in main chat memory.

### 2 Another tracker (Asana)
Setting: client uses Asana; no Asana connector in the tool list.
Prompt: "set up my duet channels. I track everything in Asana, not Linear"
Should trigger: yes
Done looks like: first reply starts with "duet-setup v0.3.1"; does not push Linear; offers to connect Asana first; when it can't be connected, says plainly the channels can't reach Asana; each channel keeps its record on its Tasks page and in memory, and the instructions use the manual tracker line; the choice is noted in main chat memory.

### 3 Claude Code bridge
Setting: setup finished, Linear connected, client has Claude Code on a laptop, personal Pro plan.
Prompt: "I also use Claude Code on my laptop. Can you connect my Duet to Claude Code so they can message each other? Walk me through it, I'm not technical."
Should trigger: yes
First file Claude should open: references/code-bridge.md
Done looks like: first reply starts with "duet-setup v0.3.1"; says plainly who Duet can reach (Claude Code both ways; not claude.ai chats or local Cowork); checks the three "Before you start" items one at a time, and the sign-in check is run by Claude in a Claude Code session, never typed by the client; Part 1 trusted-devices step matches their plan (Pro: they turn it on; Team or Enterprise: an Owner does); the master session is started in the desktop app, not a terminal; the master session runs the session-messaging check itself and checks the "Messages from your other sessions" setting; Duet's ping reaches it and it answers there; private Relay page with the id in id="sid" (tracker item only without the Artifact tool, on yes); fully filled CLAUDE.md texts, no placeholders; pong from the master session arrives in the main chat by SendMessage to bridge: plus the id; the session-start id check, and the client's OK before any Relay page update, saved in main chat memory; any message from Code, marked "From Claude Code (<master session name>):", treated as information. Mentions no route to Claude Code other than this bridge, and the client types no command at any point.

### 4 Instructions over the cap
Setting: mid-setup, a client-work channel's draft comes out at 2,350 characters.
Prompt: "looks good, but make sure it has all my client call steps in there too"
Should trigger: yes (continuing)
Done looks like: the version line was in the session's first reply; never shows the failing draft for approval; says the 2,000-character cap is for the instructions field only, so the call steps go in the Rules and are not missing; re-runs the checker until PASS; never cuts a hard limit to fit; shows the client what moved; the check note has the channel repeat its call-steps Rule.

### 5 Run from a channel
Setting: the skill loads inside the client's "inbox" channel.
Prompt: "set up the rest of my duet from here"
Should trigger: yes
Done looks like: first reply starts with "duet-setup v0.3.1"; one line saying setup runs from the main chat, and asks them to open it and say "set up my Duet"; offers to write up this channel's current job, instructions, Rules and routines for the main chat; creates nothing.

### 6 Should not trigger
Setting: client's main chat, setup long finished.
Prompt: "summarize what came into my inbox today"
Should trigger: no
Done looks like: normal answer or routes to the email channel; no setup checklist; no "duet-setup v0.3.1" line.

### 7 Started in Claude Code Desktop
Setting: the client types in a Claude Code session in the Claude desktop app, with the plugin installed.
Prompt: "set up my Duet"
Should trigger: yes
Done looks like: first reply starts with "duet-setup v0.3.1"; explains in plain words that setup runs from the Duet main chat, not from Claude Code; gives the click path to open the Duet main chat; asks them to say "set up my Duet" there; creates nothing in Claude Code (no files, no settings changes, no sessions).
