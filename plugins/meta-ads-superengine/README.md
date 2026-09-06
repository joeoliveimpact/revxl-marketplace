# Meta Ads Superengine

Your Meta ads coach, built into Claude. It takes you from *"I've never run an
ad"* all the way to a launched campaign you're scaling with confidence — and it
never leaves you staring at a screen wondering what to do next.

## What this is

A complete Meta (Facebook + Instagram) ads engine for online coaches. It walks
the whole journey with you:

- **Start from zero knowledge.** No jargon dumped on you. The engine explains
  every Claude term and every Meta term the first time it comes up — and you can
  dial the hand-holding up or down anytime.
- **Get your numbers right before you spend a dollar.** It runs your breakeven
  math first, so you know what a lead can cost and still be profitable.
- **Learn from your competitors.** It builds a roster of coaches in your niche,
  tracks which of their ads have been running longest (the ones running for
  months are the ones making money), and turns that into creative angles for
  you — never copied, always adapted.
- **Build the right campaign for where you actually are.** A first launch and a
  scaling account need different plans. The engine figures out your stage and
  builds to it.
- **Write ads in your voice.** Hooks, copy, static layouts, and video scripts,
  all matched to how you actually talk.
- **Launch cleanly, then monitor live.** It checks compliance before you launch,
  guides the build step by step, and once you're live it watches your numbers,
  spots fatigue, and — this is the important part — talks you *out* of panic
  edits that would reset your progress.

27 skills, all connected. **You can never hit a dead end:** every step ends by
handing you your best next moves.

## Quick start

Install the plugin, then just say:

> **meta ads**

That's it. The engine reads where you are and routes you to the right next step
— whether that's first-time setup or picking up a campaign you launched last
week.

Two phrases are worth memorizing:

- **"what's next"** — your compass. Say it anytime and the engine shows you
  where you are on the journey and what to do next. You cannot get lost.
- **"teach level"** — turn the explanations up (every term glossed, every
  screen walked) or down (terse, for when you know the ropes).

The first time through, the engine runs a short setup — your offer, your price,
your CRM — and everything after that builds on it.

## The RevXL Brain (optional)

**Requires the workspace-superengine plugin, version 0.14.0 or later.** That is where the `revxl-vault-search` skill lives, and it is the only way this engine reaches the Brain: it finds or asks for the key once, keeps every call inside the daily budget, and explains any failure in plain English.

With a Brain key from Joe, fourteen skills pull the newest Meta-ads strategy patterns at named points and cite them as `[brain] <path>`, and setup runs the Brain connection test ... fifteen skills in all that reach the Brain. Without a key, or without workspace-superengine 0.14.0 or later, the engine runs on its built-in library and says so once.

## Connecting Ads Manager (optional)

You do **not** need to connect anything to use the engine. Typing or pasting
your numbers works forever and is a first-class path — nothing is locked behind
a connection.

If you *want* live data pulled in automatically, you can connect your Meta Ads
Manager as a custom connector in Claude Desktop (it uses Meta's own official
hosted connection, so you sign in through Meta directly). A note on safety: that
connection asks for a broad set of permissions on Meta's side — there is no
"read-only" version Meta offers. The engine's own rule is stricter than that:
in this version it only ever *reads* your account, and it will confirm any
account change with you before touching anything. Whether a connected tool is
even *allowed* to make changes is also controlled account-side by Meta's own
"Actions allowed" setting — you stay in charge of that.

Bottom line: connect it if you like the convenience, skip it if you don't.
Pasting your numbers keeps every feature available either way.

## Install troubleshooting

Most installs just work. If an install or update stalls, here's the fix:

**Stuck update, or a "plugin not found" error after install.** Sometimes the
plugin directory takes a moment to catch up. Two options:

1. Wait a bit and retry the install from the in-app plugin directory.
2. Install straight from the source repo instead:
   ```
   claude plugin marketplace add joeoliveimpact/revxl-marketplace
   claude plugin install meta-ads-superengine@meta-ads-superengine
   ```

**Update won't move / plugin seems frozen.** Install the **plugin-doctor**
plugin and run it — it diagnoses and clears stuck plugin updates.

If you're still stuck after that, reach out and we'll get you sorted.

## Your privacy

Everything the engine remembers about you — your offer, your targets, your
campaign, your numbers — lives in a folder on your own machine
(`~/.claude/meta-ads-superengine/`). It never leaves your computer. There's no
account, no upload, no shared database.

---

*Licensed for active REVXL program members. See LICENSE.*
