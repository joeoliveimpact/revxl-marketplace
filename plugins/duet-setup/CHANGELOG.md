# Changelog - duet-setup

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.1] - 2026-11-11

### Fixed
From the live test in Duet:
- Phone path to a channel's Instructions: press and hold the channel's name, then tap Instructions (confirmed by Joe's screenshot).
- Channels are created with a create_project tool that takes the channel template.
- A channel can message the main chat directly (message_project, at most 10 messages an hour), so the first-day hello has no fallback.
- Memory: each chat writes only its own memory. Channels can read the main chat's memory, and the main chat can read every channel's. Nothing is merged.
- The routing map lives only in the main chat's memory, and channels read it there. The tracker copy is gone, because a second copy drifts.
- Quiet hours are a Duet setting with a start and an end hour, changed by telling the main chat or in Settings on the web. Check-ins stop during quiet hours and the brief arrives when they end. Only weekends off are a preference.
- A lapsed sign-in shows as a Reconnect card in the chat, and only the person can sign in again.
- A new connector is account-wide, but each chat gets it at its next fresh session, and a task already running won't have it.

## [0.3.0] - 2026-11-11

### Added
- Ships as a plugin named duet-setup.
- The first reply states the version ("duet-setup v0.3.0").
- Start with one channel and grow to three to six; names that survive voice-to-text; a made-up worked example.
- One routing map with one owner, and one pointer line to it in every channel's instructions.
- A first-day checklist each new channel runs.
- The main chat writes and saves its own instructions; the click path to a channel's instructions field.
- New reference files: day-to-day running (memory, routines and quiet hours, what needs a yes, secrets, connector care, cost traps) and getting started (the band picture, a glossary, what's normal, how to correct Claude).
- Bridge: who Duet can reach, the session-messaging check and the "Messages from your other sessions" setting (both run by Claude), offline delivery, and the person's OK before the Relay page changes after a Duet session swap.
- A plain-text failure report the client copies and sends to Joe.
- Test 7: "set up my Duet" typed in Claude Code.
- The character checker has a built-in self-test (--selftest).

### Changed
- The check note now asks the channel to quote the last line of its instructions word for word.
- The instructions template carries hard rules for paying, deleting, installing and secrets.
- Sign-in checks on the Code side are run by Claude, or given as a click path; the client types no command.
- Undocumented bridge details are marked as tested on Joe's setup.
- The character checker fails any em or en dash by default (--allow-dashes opts out), catches long unfilled template parts, and explains unreadable paths.
- The failure report is emailed by the client to joe@engineforimpact.com.

### Known open items
Each is marked [UNCONFIRMED] in the skill and must be confirmed or cut before release:
- SKILL.md: the click path from Claude Code to the Duet main chat ("at the top of the Duet sidebar").
- task-tracking.md: the full name of the Linear tool that creates projects (Linear:save_project).
- task-tracking.md: the full name of the Linear tool that lists teams (Linear:list_teams).
- code-bridge.md: the Add folder button and folder picker in the desktop app's Code settings.
- code-bridge.md: New session, the folder picker, naming a session, and where the Remote Control switch sits.

## [0.2.0] - 2026-11-05

### Added
- First version, as a skill: channel planning, task tracking, instructions and Rules with a character checker, a review round, and the Claude Code bridge.
