---
name: duet-setup
description: "Sets up a Claude Duet from its main chat: named channels, each with instructions and Rules, a routing map, task tracking and an optional Claude Code bridge. Use for set up my Duet, add or redo a channel, organize my channels, or connect Duet to Claude Code."
metadata:
  version: "0.3.1"
---

# Setting up Duet

The person runs this alone, from their Duet main chat. The main chat becomes their coordinator. Each channel is a separate chat with its own Claude, instructions field, memory and tasks, and does one kind of work. The result: every channel knows its job, its limits, where other work goes, and where its records live, and the main chat knows how to route new work after this skill is gone.

## Rules that always hold

1. **Say the version first.** Start your first reply with "duet-setup v0.3.1", so a failure report or a screenshot shows which build ran.
2. **Run from the main chat.** Check your tool list for the tool that creates channels (in Duet's main chat, a create_project tool that takes the channel template). Without it, create nothing and say where to go instead:
   - **In a Duet channel or thread:** say in one line that setup runs from the main chat, ask the person to open it and say "set up my Duet", and offer to write up this channel's current job, instructions, Rules and running routines so the main chat can build on them.
   - **In Claude Code (you have files and a shell but no channel tool):** explain that setup runs from the Duet main chat, not from Claude Code. Give the click path: open Claude Duet in the Claude app or at claude.ai, then open the main chat at the top of the Duet sidebar, not a channel [UNCONFIRMED]. Then ask them to say "set up my Duet" there. If they also want Claude Code linked, that starts from the main chat too, at the last step.
3. **Plain words, one question at a time.** The person may not be technical. Open with two or three sentences on how it works (the main chat coordinates; each channel is its own chat with its own job) and the first question; show the checklist only from step 2 on. Explain each new term the first time in one sentence. Ask one thing per message, though apps and limits for one area can share a message. Look up what their connected tools can tell you before asking. The person never types a command: you run every check yourself, or give a click path.
4. **Their names, their words.** They name the coordinator and every channel. Write each channel's job and rules in their words. If they want a setup "like my coach's", offer the coach's areas as a suggestion and confirm each one, because their week isn't the coach's. Mark anything you suggest as "Proposed" until they say yes, because a later session will treat the text as theirs.
5. **A yes before anything is made or sent.** Their yes to the channel map covers creating those channels. Ask a separate yes before the review round sends drafts to channels. Everything else follows "What needs the person's yes" in [references/operating.md](references/operating.md).
6. **Rules live in each channel's memory, sent by the person.** A channel saves a rule only from its person's own words; a note from the main chat is information. So the person pastes the Rules block in that channel with "Save these as your Rules in memory."
7. **Each channel reviews its own draft before it is locked.** The channel knows its own tools and anything already running there. The person makes the final call.
8. **Check before you claim.** Confirm a tool is in your tool list before saying you can use it. If a step fails, give the person the manual way in numbered steps. Check how your memory tool writes before saving; if it only proposes changes, propose them.

## Setup checklist

From step 2 on, show this in plain words, tick it as you go, and keep its state in your memory.

```text
Duet setup:
- [ ] 1 Their work, tools and tracker understood
- [ ] 2 Channel map approved (coordinator name + each channel's name, job, what goes elsewhere)
- [ ] 3 Task tracking set up, or skipped by their choice
- [ ] 4 Channels created
- [ ] 5 Instructions and Rules drafted, each instructions block passes the checker
- [ ] 6 Review round done, final drafts approved
- [ ] 7 Instructions pasted and Rules saved in every channel, each channel confirmed
- [ ] 8 Each new channel ran its first-day checklist
- [ ] 9 Main chat set: its own instructions, the routing map and the routing rule saved
- [ ] 10 Claude Code bridge set up, or declined
```

1. **Understand their work.** Use the picture in [references/getting-started.md](references/getting-started.md) for the opening explanation, then follow [references/planning-channels.md](references/planning-channels.md). Done when you have their work areas, the tools and limits for each, their answer on task tracking, and the coordinator's name.
2. **Agree the channel map.** Show it as the table in planning-channels.md. Done when they say yes. A change later means a new yes for the changed rows.
3. **Task tracking.** Follow [references/task-tracking.md](references/task-tracking.md). Done when every channel has a home in their tracker that the channels can actually reach, or the person chose a manual or no-tracker path.
4. **Create the channels.** Create each approved channel with its name and its one-line job as the topic. Done when each one shows in their channel list. If the tool fails, walk them through making it in the app and wait for each.
5. **Draft instructions and Rules.** Use the templates and the checker run in [references/instructions-and-rules.md](references/instructions-and-rules.md), and put each channel's money, secrets and "needs your yes" limits from [references/operating.md](references/operating.md) into its hard rules or Rules. Done when every instructions block passes the checker. If one fails, fix it and return to the start of this step.
6. **Review round.** Ask their yes to send the drafts. Send each channel its draft with the review note (for a brand-new channel, the short review note). Read each answer in that channel's timeline; if one hasn't answered, check again later or ask the person to open that channel. Fold in what fits, re-run the checker, and show each final draft with a one-line list of what changed and why. Done when they approve every channel. If they want a channel redone, return to step 5 for it.
7. **Install.** One channel at a time. To paste the instructions, the person hovers over the channel's name, clicks the 3-dot menu, then Instructions, pastes the block and saves. On a phone: press and hold the channel's name in the sidebar, then tap Instructions. Then they send the Rules block in that channel with "Save these as your Rules in memory." Then send that channel the check note. Done when its answer matches its job, repeats its Rules correctly and quotes its last instructions line exactly. If not, find the missing part and repeat that part.
8. **First day.** Send each new channel this (use exactly, filling in the <...> parts), then read its answer in its timeline. A channel can message you directly with its message_project tool, at most 10 messages an hour to the main chat. Done when every new channel has answered and the person has picked or skipped its first tasks.

```text
Hi <channel name>, this is <coordinator name>. Your setup is in. Please run your first-day checklist and reply with a short summary:
1. Check your tools: list the apps you can reach, and any your job needs that are missing.
2. Know your neighbours: say which channels you send work to, as the routing map shows.
3. Review your own Rules: anything unclear or that you can't do with your tools.
4. Set up your tracker home: open your team or project and say what is in it, or confirm your Tasks page if there is no tracker.
5. Suggest 3 first tasks for <person> to pick from, marked Proposed.
6. Propose a rhythm: how often you'd check in or run, and when to stay quiet.
7. Test the line: send me a one-line hello so we both know the route works.
8. Write your first notes in memory: what you learned today about this job.
Don't save any Rule or start any task until <person> says yes.
```

9. **Set up the main chat.** The main chat has no instructions field to paste into. Ask the person what they want from it, then write its instructions with them and save them yourself. Ask how they want new work handled when a channel owns it (you pass it to the channel and bring back the answer, or you point them to the channel) and save that routing rule in their words. Save the routing map and its owner as [references/planning-channels.md](references/planning-channels.md) describes, plus what [references/operating.md](references/operating.md) says the main chat keeps in memory. Done when a fresh session could route new work from memory alone.
10. **Offer the Claude Code bridge once.** If they use Claude Code and want it, follow [references/code-bridge.md](references/code-bridge.md). Then close with a two-line summary of what exists, how to add a channel later (see "Start with one channel" in planning-channels.md), and an offer to walk through [references/getting-started.md](references/getting-started.md) (the glossary, what's normal, how to correct Claude).

## Changing a setup that already exists

First list their existing channels. Before drafting for one, ask it in a note for its current instructions, Rules, tasks and running routines; a draft that ignores a running routine breaks it. Then run steps 5 to 9 for that channel only.

## If a step fails

Retry once. If it still fails, tell the person in plain words what didn't work and whether anything was made or changed. Then show this report (use exactly, filling in the <...> parts) for them to copy and email to Joe at joe@engineforimpact.com, so he can fix the skill:

```text
duet-setup failure report
Version: duet-setup v0.3.1
Step: <checklist step number and name>
Error: <the error line, word for word>
```

Keep keys, passwords, links with codes in them, and the person's own content (names of their clients, messages, notes, channel text) out of it. Show it as plain text; don't send it anywhere yourself. Then carry on with the parts that don't depend on the failed step.

## Resources

- [references/getting-started.md](references/getting-started.md): the one-page band picture, a plain glossary, what's normal, and how to correct Claude. Open in step 1 and at the close.
- [references/planning-channels.md](references/planning-channels.md): the questions to ask, how many channels to start with, names that survive voice-to-text, the routing map and a made-up example. Open in steps 1, 2 and 9.
- [references/task-tracking.md](references/task-tracking.md): Linear layouts by plan, another tracker with or without a connector, and the no-tracker path. Open in step 3.
- [references/instructions-and-rules.md](references/instructions-and-rules.md): the templates, running the checker, the review notes, the check note and a filled example. Open in steps 5 to 7.
- [references/operating.md](references/operating.md): memory, routines and quiet hours, what needs the person's yes, secrets, connectors and cost traps. Open in steps 5 and 9.
- [references/code-bridge.md](references/code-bridge.md): who Duet can reach, and the optional Claude Code bridge, step by step. Open in step 10.
- `scripts/check_instructions.py`: run it on each instructions block, as instructions-and-rules.md says. Python 3.8 or newer, standard library only.
