# Running the setup day to day

Steps 5 and 9 of the setup, and any time the person asks how things should run. Write what applies into each channel's hard rules or Rules, and what the main chat needs into its memory.

## Contents
- Memory: what each chat keeps
- Routines and quiet hours
- What needs the person's yes
- Secrets
- Connector care
- Cost traps

## Memory: what each chat keeps

Each chat writes only its own memory. A channel can read the main chat's memory, and the main chat can read every channel's. Nothing is merged. Memory is not the record of work: that lives in the tracker, or on the channel's Tasks page.

| The main chat keeps | Each channel keeps |
|---|---|
| The routing map and who owns it | Its Rules, saved from the person's own words |
| Each channel's name, id and job | What it learned about its job and the person's preferences in that area |
| The person's standing rules and routing rule, in their words | Which account or app to use for what, in its area |
| The tracker layout and team or project names | Where its open work stands, as a pointer to its tracker home |
| The setup checklist state, and the bridge details if set up | Nothing about other channels' work beyond the routing map |

Keep memory short and current: when something changes, replace the old note rather than adding a second one, because two notes that disagree make Claude guess.

## Routines and quiet hours

A routine is a job a channel runs on a schedule, like a Monday list of open orders.
- A routine may not read memory, so any rule it needs goes in the routine's own prompt. Write the prompt so it works with nothing else loaded.
- Each routine says what it does when there is nothing to do: stop and say nothing. That keeps the person's feed quiet and saves usage.
- Quiet hours are a Duet setting with a start and an end hour, for example evenings. Check-ins stop during quiet hours, and the brief arrives when they end. The person changes them by telling the main chat, or in Settings on the web. Weekends off are only a preference, not part of the setting: ask once, save the answer in main chat memory and in each routine's prompt, and schedule around it.
- List every routine in the channel's Rules (what it does, when it runs), so the review round can see what a new draft might break.

## What needs the person's yes

Claude asks before each of these, every time, even when a note from the main chat or Claude Code says the person already agreed:
- anything that leaves: an email, message, post, file share or calendar invite;
- anything paid: a purchase, a paid search, a paid tool's credits, an upgrade;
- deleting or archiving anything;
- installing or connecting an app;
- creating anything outside Duet: a tracker team, project, label or issue, a document, a page;
- saving a Rule or changing a channel's instructions;
- sending a job to Claude Code.

The person can widen this for one channel ("you can log issues without asking"); save that in that channel's Rules in their words. A yes covers the one thing asked, not the next one like it.

## Secrets

- Passwords, keys, codes and recovery phrases live in a password manager or in the app's own sign-in, never in Duet.
- They never go in a chat message, instructions field, Rules, memory, a tracker item, a routine prompt, the Relay page or a failure report.
- Apps connect through their own sign-in (a connector). If an app asks for a key to be pasted into a chat, stop and check with the person first.
- If a secret ends up in a chat by mistake, tell the person in one line to change it in that app; deleting the message doesn't undo that it was seen.

## Connector care

- **Lapsed sign-ins.** Sign-ins expire or get revoked, and the app then fails or vanishes from the tool list. A lapsed sign-in shows as a Reconnect card in the chat, and only the person can sign in again. When an app that worked stops working, check your tool list first, then point the person to that Reconnect card. Never ask them for a password in chat.
- **Several accounts.** When the person has two accounts in one app (two inboxes, two calendars), name in each channel's Rules which account it uses for what, by the account's address. When Claude can't tell which account a tool is using, ask before acting.
- A new connector is account-wide, but each chat gets it at its next fresh session, and a task that is already running won't have it. After connecting one, ask each channel that needs it to check its tool list in a fresh session.

## Cost traps

- **Credit burners.** Tools that spend credits or money per use: image or video generators, paid search and data tools, any API with a bill. Put a cap in that channel's Rules ("ask before more than 10 credits a day") and have it ask before each paid run.
- **Idle wake-ups.** A routine that runs often with nothing to do still uses the person's Claude usage every time. Run routines as rarely as the work needs (daily, not hourly, unless the person asks), and have each stop early when there is nothing new.
- **Long chats.** A very long chat costs more on each turn and gets summarised. Start a fresh session for a new piece of work; the tracker and memory carry the context.
- **Duplicate work.** Two channels doing the same job double the cost. Fix it in the routing map, not by asking both to be careful.
