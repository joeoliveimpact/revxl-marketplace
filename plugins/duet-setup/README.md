# duet-setup

Set up your Claude Duet the way a coach runs theirs: one main chat that coordinates, and channels that each do one kind of work.

## Demo

_Demo placeholder. A walkthrough of a first setup lands here in a future release._

## What this plugin does

You start it from your Duet main chat by saying "set up my Duet". The main chat becomes your coordinator, and you give it a name. Together you plan your channels (each one is a separate chat with its own job), starting with one and growing to three to six. You name each one, and Claude writes its instructions and Rules in your words, checks each instructions block fits the 2,000-character field, and lets each channel review its own draft before you lock it in. Then it sets up one routing map so every channel knows where other work goes, a home for each channel in your task tracker (Linear or another), and, if you want it, a link so Duet can hand jobs to Claude Code on your computer.

It asks one question at a time, in plain words. Nothing is created, sent or paid for without your yes. You never type a command: Claude runs every check itself, or tells you exactly where to click.

## Skills

### duet-setup
**Say:** "set up my Duet", "add a channel", "redo my research channel", "organize my channels", "connect Duet to Claude Code".

Plans your channels with you, creates them, writes and checks each channel's instructions and Rules, runs a review round and a check after install, gives each new channel a first-day checklist, saves the routing map in your main chat, and offers the Claude Code link at the end. It also covers memory, routines and quiet hours, what needs your yes, keeping passwords out of chats, connector care, cost traps, a short glossary and how to correct Claude.

## Agents

None. Everything ships as one skill.

## Install

**Claude Duet (where setup runs):** on claude.ai, open **Customize**, then **Plugins**, then **Add marketplace**, and add the marketplace you were given. Then install **duet-setup**. Duet loads plugins from your account. Open your Duet main chat and say "set up my Duet".

**Claude desktop app (Code tab):** not needed for setup. If it is installed there, saying "set up my Duet" points you to your Duet main chat. The Claude Code link is set up from Duet, with a few clicks and two short texts you paste on the Code side.

## Dependencies

- A Claude plan with Claude Duet.
- Optional: a task tracker. Linear (Free, Basic, Business or Enterprise) is covered step by step; Asana, Notion, Trello, ClickUp, Monday and similar work when connected, and a manual path works without one.
- Optional, for the Claude Code link: the Claude desktop app on your computer, signed in with the same account as Duet.

No MCP servers to add. No keys to paste.

## Compatibility

| | Claude Duet main chat | A Duet channel | Claude Code (desktop app or terminal) |
|---|---|---|---|
| Skills | Yes, setup runs here | Points you to the main chat, and offers to write up the channel's current setup | Points you to the Duet main chat; creates nothing |
| Agents | None shipped | None shipped | None shipped |
| Commands | None | None | None |
| Hooks | None | None | None |

## Privacy and failure reports

Your channels, instructions, Rules and tracker stay in your own accounts. This plugin does not ship the usual automatic failure report, because that report needs a key a client's Duet doesn't have. Instead, if a step fails, Claude shows a short plain-text report (the skill version, the step and the error line, with no keys and none of your content) that you copy and email to Joe at joe@engineforimpact.com yourself.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).

## Marketplace

Part of [revxl-marketplace](https://github.com/joeoliveimpact/revxl-marketplace).
