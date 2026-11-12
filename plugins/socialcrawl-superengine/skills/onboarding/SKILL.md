---
name: onboarding
description: >
  One-time setup for the socialcrawl-superengine plugin. Use when the user
  says: "set up socialcrawl", "onboard socialcrawl superengine", "connect my
  socialcrawl key", "socialcrawl setup", "install the social research engine",
  "set up my SocialCrawl key", "set up Jev", "set up my OpenRouter key".
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
env var wins over the file: say the env var holds a dead key, then take the route for their OS,
with nothing typed by them. **Windows:** the 1d window, pressing **Edit…** on
`SOCIALCRAWL_API_KEY` in place of **New…** to paste a new key (or **Delete** to remove it), then
restart. **macOS / Linux:** with the Bash tool, find the file that sets it
(`grep -l SOCIALCRAWL_API_KEY ~/.zprofile ~/.zshrc ~/.bash_profile ~/.bashrc ~/.profile 2>/dev/null`,
which prints file names only) and open that file in their text editor (`open -t <file>`; Linux:
`xdg-open <file>`); they delete that line, save, close the editor and restart. Never read the
file. Removed → 1c. A file on disk
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
- **Linux** — no box: go to 1d.

The box checks only the length and the `sc_` start, so a wrong key can be saved; Step 2's
balance call is the real test. By exit code:

- **0** (`RESULT=OK`) → Step 2.
- **2** (cancelled, timed out or left empty; nothing saved) → stop here. Say it can be done
  any time with "set up my SocialCrawl key".
- **3** (the box couldn't open or couldn't save), or no desktop at all → 1d.

**1d. Box can't run?** Some surfaces have no real home directory — Claude Cowork's two
sandboxes report `HOME` as `/root` or `/sessions/…`, and browser chat has no user
filesystem at all. A file written there is invisible to every Claude Code session. Say so
plainly, then take the path for where they are. The user never types a command, and the key
never passes through this chat:

- **No real home directory** (the surfaces above) — ask them to open Claude Code Desktop on
  their own computer and say "set up my SocialCrawl key" there, where the key box works.
- **Windows** — the key goes in a user environment variable, set in a Windows settings window:
  Start menu → search **Edit environment variables for your account** → under *User variables*
  press **New…** → name `SOCIALCRAWL_API_KEY`, value: paste the key → **OK**, then **OK**. Then
  they restart Claude Code and say "set up my SocialCrawl key", and 1a checks it.
- **macOS / Linux** — with the Bash tool, make an empty, owner-only key file and open it in their
  text editor: `mkdir -p ~/.config/socialcrawl && touch ~/.config/socialcrawl/api_key && chmod 600 ~/.config/socialcrawl/api_key && open -t ~/.config/socialcrawl/api_key`
  (Linux: `xdg-open` in place of `open -t`). Ask them to paste only the key on the first line,
  save and close the editor, then make Step 2's balance call. Never read the file.

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

> "Every SocialCrawl call costs credits — most cost 1, some cost 5, heavy research reports
> cost up to 243 **per call**, and a full AI-visibility audit can reach 1,605. My rules with your credits: I tell you
> the price before a run, and the option you pick is the go-ahead. After that a built-in
> guard keeps a running count and never stops to ask you: it lets calls through quietly up
> to a limit for each session or scheduled run — your own limit if you set one (press **Open
> SocialCrawl** on the SocialCrawl band above the prompt, then **Settings**; the band shows once
> setup is done), otherwise the smaller of 500
> credits or a quarter of your balance (500 if the balance can't be read) — and refuses any
> call that would go past it, as it counts it. While a call runs, the guard counts its highest
> price. Usually a couple of minutes after it finishes, once SocialCrawl's free record of charges
> shows what that kind of call cost, it gives back the difference; until then, and for some calls,
> the count stays higher than what you spent. A few calls it can't price up front (cohort lookups,
> batch jobs, batch scrapes, website monitors, and transcripts that bill many items) it counts low
> or at 0, and the limit doesn't stop the ones it counts at 0, even once it's used up; I'll name the
> real price before running one. It also refuses any command that carries a SocialCrawl link but
> isn't a plain API call, like a
> loop or a note. The big reports never run in batches. Two more things: repeat calls
> within a few minutes are usually free (cached), and transcripts from this API are
> **priced per item** — 3 credits a video on YouTube, about 10 credits an item elsewhere —
> so I'll always show you that price and the cheaper route (YouTube captions for 1 credit,
> or transcribing free on your machine) and only buy one if you say yes. If you'd like the guard
> to enforce that too, block them in Settings — I'll show you how in a moment."

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
  - **3**, no desktop, or Linux → as in 1d, with `OPENROUTER_API_KEY` as the Windows variable
    name and `~/.config/openrouter/api_key` as the file on macOS and Linux.
  - A key pasted into chat → as in 1e: advise rotation, then open the key box above with
    `openrouter`; never write the key yourself.

## Step 3c — Transcripts: what this computer already has

With the Bash tool, run the helper's label-only check:
`node "${CLAUDE_PLUGIN_ROOT}/hooks/mod/helper.mjs" routes`. It prints `{"ok":true,"routes":[…]}`
with labels only, never a value: `yt-dlp` and `whisper` are free transcript tools found on this
computer, and `groq` means a Groq key is set.

Then look at this session's own connections, **by name only**: if a 1Password, Composio or
Aperture connection is available, you may look at the names of its stored items or connected
apps for Groq or a transcription tool. Never read, show, copy or move a value or a secret, and
never move the plugin's own SocialCrawl key: it stays where Step 1 put it.

Tell the user in a sentence or two what was found, then:

- **The check found something** → *"Paid transcripts cost far more than what you already have.
  Press **Open SocialCrawl** on the band above the prompt and go to **Settings**: **Blocked** is
  picked for you (unless you saved a choice there before), so just press **Save**."*
- **It found nothing** → *"Paid transcripts run unless you block them. To block them, press
  **Open SocialCrawl**, go to **Settings**, press **Blocked**, then **Save**."*
- **A name only in a key store** → Settings can't see it and picks by the check above alone, so
  say: *"Settings can't see that, so press **Blocked** yourself if you want them blocked."*

If they don't see the band yet, say it appears once setup finishes (after Step 4), and to do this
then.

Onboarding writes nothing in this step: the choice is saved only when the user presses Save,
and until Blocked is saved, paid transcripts still run.

## Step 4 — Write the marker

```bash
mkdir -p ~/.claude/socialcrawl-superengine
```

Write `~/.claude/socialcrawl-superengine/.superengine` as JSON:

```json
{
  "version": "<copy the version field from ${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json here>",
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

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `socialcrawl-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names, web addresses or file paths (those go in the body
   file; a command carrying the SocialCrawl address that isn't a plain `curl` is refused):

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin socialcrawl-superengine --plugin-version 0.4.1 --skill onboarding --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file socialcrawl-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

No `python`? Use `python3`. If neither runs, nothing was sent: tell the client the details are in
`socialcrawl-superengine/reports/report-body.md`, to email to Joe.
