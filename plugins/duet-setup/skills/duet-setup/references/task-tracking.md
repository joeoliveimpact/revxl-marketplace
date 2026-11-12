# Task tracking

Step 3 of the setup. A tracker keeps each channel's record outside the chat, so nothing is lost when a session ends or a long chat gets summarised. Ask what they use; never move them off a tracker that works for them. A tracker only helps if the channels can reach it, so check the connector before writing any channel's tracker paragraph.

## Contents
- Which path
- Linear on a Business or Enterprise plan
- Linear on a Free or Basic plan
- Another tracker
- No tracker
- What every channel's instructions say about it

## Which path

Ask: "Do you use a task tracker?" Then:
- **Linear:** check your tool list for the Linear connector; if it's missing, offer to connect it first. Ask which plan they're on; your tools can't read it, so they look in Linear under Settings, Administration, Billing. Sub-teams exist only on Business and Enterprise; Free allows 2 teams and Basic 5 (Linear docs: linear.app/docs/teams, linear.app/docs/sub-teams). Pick the matching section below.
- **Another tracker** (Asana, Notion, Trello, ClickUp, Monday or similar): see "Another tracker".
- **None:** see "No tracker".

## Linear on a Business or Enterprise plan

The layout: one parent team for coordination across the whole setup, plus one sub-team per channel and one for the main chat.

Linear's connector can't create teams, so the person makes them. Walk them through it, one team at a time:
1. In Linear, open Settings.
2. Under "Your teams", click "+" to create a team.
3. Create the parent team first. Name it for their setup (for example "<coordinator name> system"). Its job: coordination between channels only, not channel work.
4. Create a team for each channel, with the channel's name. In "Team hierarchy", pick the parent team.
5. Create one more for the main chat itself, under the same parent.
6. Tell you when each is done.

Then run your Linear list-teams tool (Linear:list_teams [UNCONFIRMED]) and confirm each team, its key (the short code like ABC in ABC-12) and its parent. Done when every channel has a team and you've recorded the keys.

## Linear on a Free or Basic plan

Sub-teams aren't available and the team count is capped, so use one team for everything and a project per channel.
1. A new Linear workspace already has one team. Ask whether to use it, or have them create one named for their setup (Settings, then "+" under "Your teams"). This team holds all channel work.
2. Propose one project per channel, named after the channel, plus a "Coordination" project for work across channels. On their yes, create the projects with your Linear tool (Linear:save_project [UNCONFIRMED]), then list them back.
3. Tell them once: on the Free plan, a workspace with more than 250 issues can't create new ones (Linear docs, linear.app/docs/billing-and-plans), so channels should log work items, not every message.

Done when every channel has a project and you've recorded the team key and project names.

## Another tracker

Mirror the same idea in its terms: one space for the whole setup, one list, project or board per channel, plus one for coordination.
1. Check your tool list for that tracker's connector. If it isn't there, offer to connect it and show its connect card if you can.
2. **Connected:** if it can create projects or lists, propose the layout and create it on their yes; otherwise walk them through creating each one by hand. Record each channel's home by its exact name.
3. **Can't be connected:** say plainly that the channels can't read or write that tracker. Each channel then keeps its record on its own Tasks page and in its memory, and the person copies anything they want into the tracker by hand. Use the "manual" tracker paragraph below. If they still want a project per channel in that tracker for their own copying, they make it; note the names and the choice in main chat memory.

Done when every channel has a home it can reach, or the person chose the manual path.

## No tracker

Offer Linear once, in one line: it's free for a small setup and keeps each channel's record outside the chat. If they want it, walk them through signing up and connecting Linear in Duet, then use the Free plan layout. If they'd rather not, each channel keeps its record on its own Tasks page and in its memory. Note the choice in main chat memory so later sessions don't ask again.

## What every channel's instructions say about it

**With a connected tracker,** one short paragraph:
- where this channel logs its work (its team, or its project);
- that the coordination team or project is for cross-channel coordination only;
- to read its open items when a session starts, because a new session remembers nothing else;
- to link work another channel made rather than copy or move it, so nothing is logged twice.

**Manual or no tracker,** one line instead: "Keep your record on your Tasks page and in your memory. Check your open tasks when a session starts."
