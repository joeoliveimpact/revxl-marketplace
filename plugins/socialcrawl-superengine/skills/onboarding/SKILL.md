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

Check the marker: `~/.claude/socialcrawl-superengine/.superengine`. The marker is not
proof the key works; the key decides.

- **Present** → run 1a. Key works → say so, show the marker's contents (version, onboarded
  date), and offer: (a) re-verify the key, (b) refresh the marker, (c) nothing — exit. Don't
  redo setup. Then run Step 3b, which skips itself if Jev is set up or was declined. No key,
  or a **401** → say the key isn't working and follow 1a's routing.
- **Absent** → continue.

## Step 1 — API key

**Never ask the user to type or paste the key into the conversation.** A pasted key is
written into the transcript, the session log, and any screenshot of either. Everything
below exists to avoid that. You never need the key's *value* — only confirmation that a
working key is on disk, which the free balance call gives you.

**1a. Already working?** Run the `socialcrawl` skill's API Key steps 1–2 (they print a
label, never the key) and note which one answered.
No key starting with `sc_` → 1b if they have no account, else 1c. A key → make Step 2's free
balance call now. **200** → the key works: if Step 0 sent you here, back to its menu;
otherwise go to Step 2 and use this answer for its first check. **401** from the file → the
key is dead; go to 1c. **401** from `SOCIALCRAWL_API_KEY` → the box can't fix it, because the
env var wins over the file: say the env var holds a dead key, and have them set a new key in
it or remove it, outside this session, then restart (as in 1d); removed → 1c. A file on disk
proves nothing; the balance call does. Do not re-run setup on a working key.

**1b. No account yet?** Walk them through
[references/socialcrawl-setup.md](references/socialcrawl-setup.md) — referral signup link,
where the key lives in the dashboard, and the free-credits note. Then continue to 1c.

**1c. Open the key box.** A small window with a hidden field takes the key, so it never
passes through this chat, and saves it with owner-only permissions. First the key: it's
under **API Keys** at https://www.socialcrawl.dev/dashboard (a revoked key → create a new
one there; no account → 1b). Ask *"Got your key copied?"* and only after a yes tell them a
box is opening, then run the line for their OS with the Bash tool, timeout 240000. It waits for
them, closes itself after 3 minutes, and prints one `RESULT=` line, never the key:

- **Windows** — `powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "${CLAUDE_PLUGIN_ROOT}/setup/key-box.ps1" -Kind socialcrawl`
- **macOS** — `bash "${CLAUDE_PLUGIN_ROOT}/setup/key-box.command" socialcrawl`
- **Linux** — no box: they run `setup/setup-key.command` from the plugin folder in their own
  terminal (first time only: `chmod +x`), or use 1d.

The box checks only the length and the `sc_` start, so a wrong key can be saved; Step 2's
balance call is the real test. By exit code:

- **0** (`RESULT=OK`) → Step 2.
- **2** (cancelled, timed out or left empty; nothing saved) → stop here. Say it can be done
  any time with "set up my SocialCrawl key", or with the setup helper: double-click
  `setup/setup-key.bat` (Windows) or `setup/setup-key.command` (macOS / Linux) in the plugin
  folder.
- **3** (the box couldn't open or couldn't save), or no desktop at all → 1d.

**1d. Box can't run?** Some surfaces have no real home directory — Claude Cowork's two
sandboxes report `HOME` as `/root` or `/sessions/…`, and browser chat has no user
filesystem at all. A file written there is invisible to every Claude Code session. Say so
plainly and use the env var instead, set outside this session. They run one line in their own
terminal, paste the key at the prompt (nothing shows) and press Enter, then restart; the key
never sits in a command line or shell history:

- **Windows** (PowerShell) — `$s = Read-Host 'SocialCrawl key' -AsSecureString; [Environment]::SetEnvironmentVariable('SOCIALCRAWL_API_KEY', [Net.NetworkCredential]::new('', $s).Password, 'User')`
- **macOS / Linux** — `read -rs k && printf "export SOCIALCRAWL_API_KEY='%s'\n" "$k" >> ~/.zprofile; unset k` (Linux with bash: `~/.bashrc` in place of `~/.zprofile`)

**1e. If a key lands in the chat anyway** — because they pasted it before you could ask
them not to — **do not refuse it.** The exposure already happened; wasting it helps nobody.
Never write the key to a file or a command yourself: that puts a second copy in the
transcript. Tell them plainly:

> "That key is now in this conversation's transcript. Rotate it when you get a chance —
> create a new key in the dashboard and delete this one. For now I'll open the key box:
> paste your key there and the box saves it."

Then open the key box (1c) for that kind of key. Treat a pasted key as compromised, not as a
successful setup.

## Step 2 — Verify

1. `GET /v1/credits/balance` (0 credits) — confirms auth, shows their balance.
2. Tell the user the next call costs 1 credit, then:
   `GET /v1/tiktok/profile?handle=tiktok` — confirms live data flows.
3. Report both results plainly: *"Key works. You have N credits."*

If either fails, troubleshoot via the `socialcrawl` skill's Error Handling table before
proceeding — do not write the marker on a failed verify. A **401** means the key is wrong
or revoked: from `SOCIALCRAWL_API_KEY`, handle it as in 1a; otherwise open the key box again
(1c).

## Step 3 — Credit policy briefing (plain language)

Tell the user, in beginner voice:

> "Every SocialCrawl call costs credits — most cost 1, some cost 5, and a handful of
> heavy research reports cost 15–50 **per call**. My rules with your credits: I tell you
> the price before a run, and the option you pick is the go-ahead. After that a built-in
> guard keeps a running count and stays quiet until the session's total reaches a cap —
> the smaller of 500 credits or a quarter of your balance — then checks with you once
> before each further step of that size. Calls it can't price up front always get a check,
> and so does any command that carries a SocialCrawl link but isn't a plain API call, like a
> loop or a note. The big reports never run in batches. Two more things: repeat calls
> within a few minutes are usually free (cached), and transcripts from this API are
> **priced per item** — 3 credits a video on YouTube, about 10 credits an item elsewhere —
> so I'll always show you that price and the cheaper route (YouTube captions for 1 credit,
> or transcribing free on your machine) and only buy one if you say yes."

## Step 3b — Optional: Jev (an OpenRouter key)

`<revxl>` is `$SC_REVXL_HOME` if set, else `~/.claude/revxl`.

**Skip** when an OpenRouter key resolves or `<revxl>/jev-declined` exists. The key check, run
with the Bash tool, prints a label and never the key; `or=env` or `or=file` means it resolves:
`case "${OPENROUTER_API_KEY-}" in sk-or-*) echo or=env;; *) [ -s ~/.config/openrouter/api_key ] && echo or=file || echo or=unset;; esac`. "Set up Jev"
or "set up my OpenRouter key" opens this step anyway, declined or not.

Otherwise ask once, in plain words: *"Want to add Jev? It's a helper that speeds me up,
makes better decisions and uses fewer tokens. It's optional, and it runs on an
OpenRouter key, which needs a few dollars of prepaid credit."*

- **No** → create `<revxl>/jev-declined` (make the folder if needed), say "set up Jev" adds it
  any time, and don't ask again.
- **Yes** → if a browser or preview tool is available in this session, open
  https://openrouter.ai/settings/keys there; otherwise print the link. Ask *"Got your key
  copied?"* and only after a yes open the box, as in 1c with `openrouter` in place of
  `socialcrawl`:
  - **Windows** — `powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "${CLAUDE_PLUGIN_ROOT}/setup/key-box.ps1" -Kind openrouter`
  - **macOS** — `bash "${CLAUDE_PLUGIN_ROOT}/setup/key-box.command" openrouter`

  Check only the `RESULT=` line: a length above 0 and `prefix=True` (starts with `sk-or-`).
  Never read the file, and make no OpenRouter call.
  - **0** → delete `<revxl>/jev-declined` if it exists and say the key is saved. With
    `prefix=False`, say it doesn't start with `sk-or-` and offer the box again.
  - **2** → stop here; say it can be done any time with "set up my OpenRouter key".
  - **3**, no desktop, or Linux → the env var, set outside this session at a hidden prompt, as in 1d:
    - **Windows** (PowerShell) — `$s = Read-Host 'OpenRouter key' -AsSecureString; [Environment]::SetEnvironmentVariable('OPENROUTER_API_KEY', [Net.NetworkCredential]::new('', $s).Password, 'User')`
    - **macOS / Linux** — `read -rs k && printf "export OPENROUTER_API_KEY='%s'\n" "$k" >> ~/.zprofile; unset k` (Linux with bash: `~/.bashrc`).
  - A key pasted into chat → as in 1e: advise rotation, then open the key box above with
    `openrouter`; never write the key yourself.

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
  `socialcrawl` skill covers all 68 platform namespaces."
- **Guided research** — "say things like *'what are people saying about X'*, *'what ads
  is <competitor> running'*, or *'does AI recommend me'* — the `research-plays` skill
  runs the full workflow with costs stated up front."

**Then ask once — skippable:** *"Whose accounts will you be researching most — your own
handles, and a competitor or two?"* Put each answer through the roster writer:
`node "${CLAUDE_PLUGIN_ROOT}/hooks/roster-write.mjs" --handle <h> --source onboarding` — the
only sanctioned writer for `~/.claude/revxl/entities.jsonl`. A rostered handle lets a later
*"research …"* wake the `research-plays` suggestion on its own. If they skip, say so and move
on — the roster fills itself from the first play that names a subject.
