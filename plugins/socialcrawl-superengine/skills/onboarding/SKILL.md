---
name: onboarding
description: >
  One-time setup for the socialcrawl-superengine plugin. Trigger phrases:
  "set up socialcrawl", "onboard socialcrawl superengine", "connect my
  socialcrawl key", "socialcrawl setup", "install the social research engine".
  Wires the bring-your-own SocialCrawl API key (with referral signup if the
  user has no account), verifies it with a test call, explains the credit
  gates in plain language, and writes the setup marker other RevXL engines
  detect. Run once per machine; safe to re-run (offers refresh/re-verify).
---

# SocialCrawl Superengine — Onboarding

One-time guided setup. Takes about 3 minutes with an existing SocialCrawl account,
~5 with a fresh signup.

**Teach mode:** read `~/.claude/revxl/teach-mode` if it exists; absent = `beginner`.
Beginner voice = plain English, no jargon unglossed, one step at a time.

**Suggest before invoking:** if the user's message is borderline (they might just want a
quick API call, not setup), ask first: *"Want me to run the full superengine setup, or
just make that call?"* Explicit invocation skips the question.

## Step 0 — Already set up?

Check the marker: `~/.claude/socialcrawl-superengine/.superengine`.

- **Present** → say so, show its contents (version, onboarded date), and offer:
  (a) re-verify the key, (b) refresh the marker, (c) nothing — exit. Don't redo setup.
- **Absent** → continue.

## Step 1 — API key

**Never ask the user to type or paste the key into the conversation.** A pasted key is
written into the transcript, the session log, and any screenshot of either. Everything
below exists to avoid that. You never need the key's *value* — only confirmation that a
working key is on disk, which the free balance call gives you.

**1a. Already resolvable?** Check the `socialcrawl` skill's first two sources — env var
`SOCIALCRAWL_API_KEY`, then `~/.config/socialcrawl/api_key`. If either has a key starting
with `sc_`, setup is done; skip to Step 2. Do not re-run setup on a working key.

**1b. No account yet?** Walk them through
[references/socialcrawl-setup.md](references/socialcrawl-setup.md) — referral signup link,
where the key lives in the dashboard, and the free-credits note. Then continue to 1c.

**1c. Point them at the setup helper.** It takes the key in *their own terminal* with the
input hidden, verifies it, and writes the file with owner-only permissions. Give them the
one line for their OS and wait — do not proceed until they say it's done:

- **Windows** — double-click `setup/setup-key.bat`
- **macOS / Linux** — double-click `setup/setup-key.command`
  (first time only: `chmod +x setup/setup-key.command`)

Then verify with Step 2. The helper already tested the key, so Step 2 is confirming that
*this* session can read it.

**1d. Helper can't run?** Some surfaces have no real home directory — Claude Cowork's two
sandboxes report `HOME` as `/root` or `/sessions/…`, and browser chat has no user
filesystem at all. A file written there is invisible to every Claude Code session. Say so
plainly and use the env var instead, set outside this session:

- **Windows** — `setx SOCIALCRAWL_API_KEY "sc_…"` in their own terminal, then restart
- **macOS / Linux** — add `export SOCIALCRAWL_API_KEY="sc_…"` to their shell profile

**1e. If a key lands in the chat anyway** — because they pasted it before you could ask
them not to — **do not refuse it.** The exposure already happened; wasting it helps nobody.
Save it to `~/.config/socialcrawl/api_key`, then tell them plainly:

> "That key is now in this conversation's transcript. Rotate it when you get a chance —
> create a new key in the dashboard and delete this one — then run the setup helper so the
> replacement never touches a chat."

Treat a pasted key as compromised, not as a successful setup.

## Step 2 — Verify

1. `GET /v1/credits/balance` (0 credits) — confirms auth, shows their balance.
2. Tell the user the next call costs 1 credit, then:
   `GET /v1/tiktok/profile?handle=tiktok` — confirms live data flows.
3. Report both results plainly: *"Key works. You have N credits."*

If either fails, troubleshoot via the `socialcrawl` skill's Error Handling table before
proceeding — do not write the marker on a failed verify.

## Step 3 — Credit policy briefing (plain language)

Tell the user, in beginner voice:

> "Every SocialCrawl call costs credits — most cost 1, some cost 5, and a handful of
> heavy research reports cost 15–50 **per call**. My rules with your credits: cheap calls
> just run; anything 5+ I tell you the cost first; anything 10+ I ask before every single
> call; and the big reports always get an explicit price-tag confirmation — never run in
> batches. Two more things: repeat calls within a few minutes are usually free (cached),
> and I will **never** buy transcripts from this API — transcription happens free on your
> machine."

## Step 4 — Write the marker

```bash
mkdir -p ~/.claude/socialcrawl-superengine
```

Write `~/.claude/socialcrawl-superengine/.superengine` as JSON:

```json
{
  "version": "0.1.0",
  "onboarded_at": "<ISO date>",
  "key_saved": true,
  "via": "onboarding"
}
```

This marker is how other RevXL engines (e.g. shortform-superengine) detect that the
deep-research layer is installed and offer its plays.

If `~/.claude/revxl/teach-mode` does not exist, leave it absent (absent = beginner
default) — don't create files the user didn't ask for.

## Step 5 — What now

Two-line menu:

- **Ad-hoc API calls** — "ask me for any profile, post, comments, or search; the
  `socialcrawl` skill covers all 48 platforms."
- **Guided research** — "say things like *'what are people saying about X'*, *'what ads
  is <competitor> running'*, or *'does AI recommend me'* — the `research-plays` skill
  runs the full workflow with costs stated up front."
