---
name: fewzhun-box-setup
description: >
  Installs the Fewzhun Box brain on a Linux server (a VPS) with nobody at the screen: note search,
  a nightly link graph, a private read-only web page, and reader tokens for a bot and Claude workers.
  Use for "set up the brain on this server", "install fewzhun box", "install the box brain",
  "update the brain install", "add a reader", "give my bot access to the brain", "new token for",
  "revoke a token", "change which notes the bot can read". NOT for checking a running install
  (fewzhun-box-check) or searching the brain (fewzhun-box-use).
---

# fewzhun-box-setup: install the brain on a Linux server

## Output contract (every run, in this order)

1. What Claude found on the server, one plain line each (Linux, admin rights, Docker, memory, Tailscale, Claude login, an earlier install).
2. Each question Claude still needs answered, one at a time, only for what it could not detect.
3. The dry run as a short plain list ("will create the service user", "will install the search engine"). Never paste the raw output. Then ask: "Install now?"
4. After the install: every PAUSE POINT as an owner task in plain English (table below), and which ones Claude can do itself on a yes.
5. The done-test result: how many checks passed, and each failure in plain words with its next fix.
6. A last line: "The brain is ready", or what still stops it.
7. On any failure you can't fix in two tries: what went wrong in plain words, then the failure report offer below.

## Re-invoke guard (read before step 1)

- If the conversation was compacted since this skill loaded, invoke this skill again before going on.
- Re-running is safe. `install.sh --apply` skips what is already in place and keeps existing tokens. Never delete `/etc/fewzhun-box`, the install folder or a token to start fresh.
- Never run the search engine's own `status` command and never a forced reindex: both rewrite the index. Never print, echo or `cat` a token. Never put a token on a command line.
- Never install where another brain search service runs (`install.sh` refuses; do not work around it).

## Ground rules

- **The client never types a command.** Claude runs everything in the Bash tool. When a step needs the owner (a GitHub click, a Tailscale sign-in), give a click path, never a command to paste.
- Plain English. Gloss a term once, e.g. "spoke (one group of notes, like your rules or your call logs)".
- `<node>`: find it once and reuse the printed path literally: `command -v node && node --version`. If there is none, or the version is under 20, use `ls <code_root>/node/node-v*/bin/node 2>/dev/null | tail -1` (the installer puts its own Node there).
- `<root>`: the install folder, `/opt/fewzhun-box` unless brain.json says otherwise.
- `<code_root>`: `/opt/fewzhun-box-app` unless brain.json says otherwise. Public code lives here; private data stays in `<root>`. Workers need no membership in `fbx`.
- `<work>`: `~/fewzhun-box-setup/`, where Claude keeps the draft config before install.
- Admin commands run as `sudo -n ...` (no password prompt). `sudo` resets PATH, so always give the full `<node>` path.

## 1. Look before asking (Claude detects, the owner answers nothing yet)

Run these, one at a time, and keep the answers:

- `uname -s; . /etc/os-release; echo "$PRETTY_NAME"; id -un; id -u` (must be Linux)
- `sudo -n true && echo ADMIN_OK` (admin rights without a password)
- `sudo -n test -f /etc/fewzhun-box/brain.json && echo INSTALLED` (an update, not a first install)
- `free -m; nproc`
- `command -v docker && docker ps --format '{{.Names}}'` and `ip -4 -o addr show | awk '$2=="docker0" || $2 ~ /^br-/ {print $2, $4}'`
- `command -v tailscale && tailscale ip -4`
- `timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone`
- `python3 --version` (3.11 or newer for the graph)
- `test -f ~/.claude/.credentials.json && echo CLAUDE_LOGIN` (the login the nightly graph uses)

Stop and say so plainly when:
- Not Linux: "This plugin installs on Linux servers only."
- No `ADMIN_OK` and the user is not root: owner task "admin rights": "The install needs admin rights on this server, once. Ask whoever manages the server to give this user admin rights without a password prompt, or start Claude as an admin user, then tell me to go on." Wait.
- `INSTALLED`: skip section 2. Copy the live file for review with `sudo -n cat /etc/fewzhun-box/brain.json` (it holds no secrets), ask only about what the owner wants changed, then go to section 3.

## 2. Ask only what Claude could not detect

One question at a time, offering the detected answer as the default.

1. **Where the notes live.** "Are your notes in a GitHub repo? If yes, what is its address?" Use the SSH form `git@github.com:<owner>/<repo>.git` and turn sync on. If the notes are only a folder on this server, sync stays off and Claude copies the folder in after the install.
2. **Spokes.** "Which folders hold which kind of notes?" Propose names from the folder names. For each spoke set `decay`: `"never"` for rules, guidance and regulations (age never matters), `true` for call logs and meeting notes (older ones rank lower), `false` for the rest.
3. **Readers** (who may read which spokes). Propose `bot` (every spoke, `view: true` so its token also opens the graph pages) and `workers` (Claude workers on this server, `view: true` when they should use the graph). Ask only if the owner wants a reader kept out of a spoke.
4. **The bot's container.** If Docker lists containers, ask which one is the bot, or none. Its name goes in `done_test.container`. No Docker: `bind` must be an IP; ask which address the bot uses.
5. **Phone access.** "Do you want to open the brain's web page from your phone over Tailscale (your private device network)?" Yes sets `tailnet_bind: "auto"`.
6. **The nightly graph.** On by default. It uses this user's Claude login (`claude.run_as` = `id -un`). Confirm `claude.bin` is the absolute executable path (`sudo -u <run_as> -i sh -c 'command -v claude'`). Choose `claude.token_file` (root-readable `0600` file holding a `claude setup-token` token) or `claude.credentials` (the login's credentials file). No Claude login on the server: ask whether to sign Claude in first or turn the graph off.
7. **Nightly draft notes** (harvest). Off by default. Ask once: "Do you want the brain to draft new notes each night from your bot's logs, for you to approve? You can add it later." On a yes, ask which folders or files to read and who may approve, then follow the harvest section of `${CLAUDE_PLUGIN_ROOT}/config/CONFIG.md`.

Then write `<work>/brain.json` with the Write tool, starting from `${CLAUDE_PLUGIN_ROOT}/config/brain.example.json`. Every setting is explained in `${CLAUDE_PLUGIN_ROOT}/config/CONFIG.md`. Rules:
- No `<...>` placeholder may remain. Set unused ones to `null` (or `[]` for lists). With harvest off, `harvest.sources` is `[]`.
- `timezone` = the detected zone. `bind` stays `"auto-docker"` when Docker is present.
- `done_test`: fill it now only if Claude can read the notes on this server (a clone or folder); pick the values with the rules in section 6. Otherwise leave `done_test` with only `reader` and `container` and fill the rest in section 6.

## 3. Dry run, then the owner's yes

`sudo -n sh "${CLAUDE_PLUGIN_ROOT}/bin/install.sh" --config ~/fewzhun-box-setup/brain.json`

It changes nothing. `would:` lines are the plan; `STOP:` is a refusal (fix the named setting, run again). A stop because Node is missing is normal: the install adds Node first. Summarize the plan in 4 to 8 plain lines, ask "Install now?" and wait for a clear yes.

## 4. Install

On the yes, run with `run_in_background` (the first install downloads the search engine and its model, often 5 to 15 minutes) and wait for it:

`sudo -n sh "${CLAUDE_PLUGIN_ROOT}/bin/install.sh" --config ~/fewzhun-box-setup/brain.json --apply`

`--config` is only used when `/etc/fewzhun-box/brain.json` does not exist yet. For an update with changed settings, first show the owner what changes, then on a yes: `sudo -n install -o root -g fbx -m 0640 ~/fewzhun-box-setup/brain.json /etc/fewzhun-box/brain.json`, then run the same `--apply` line.

If the notes are only a folder on this server (sync off), after the install copy them in and index them: `sudo -n cp -R <notes folder>/. <root>/vault/ && sudo -n systemctl start fewzhun-box-sync`.

## 5. Pause points (the installer prints `PAUSE POINT (<name>): ...`)

Turn each one into an owner task. Never paste the line itself.

| Pause point | Tell the owner | Who does it |
|---|---|---|
| deploy key | "On GitHub, open your notes repo, then Settings, Deploy keys, Add deploy key. Paste the key I show you, name it fewzhun-box, and leave Allow write access OFF." Show the public key from the line (a public key is safe to show). | Owner. Then Claude runs `sudo -n systemctl start fewzhun-box-sync` and checks it with the fewzhun-box-check skill. |
| firewall | "Your firewall blocks your bot from reaching the brain. I can add one rule that lets only your bot's Docker network in. Add it?" | Claude, on a yes: run the `ufw allow ...` from the line with `sudo -n`. |
| kernel setting | "Claude workers on this server need one kernel setting so their safety sandbox can start. Change it?" | Claude, on a yes: run the line's command with `sudo -n sh -c '...'`. |
| tailscale | "Phone access needs Tailscale on this server. I can install it; you then sign in once from a link." | Claude on a yes (below), then the owner opens the sign-in link and signs in. |
| token for `<reader>` | For a Claude worker reader: "I'll save this reader's key where Claude workers on this server look for it. It is never shown." For the bot: "Your bot needs its key as a secret file. Whoever set up your bot adds it; the how-to is in references/agent-wiring.md." | Worker: Claude (below). Bot: owner or the bot's builder. |

Tailscale, on the owner's yes: `curl -fsSL https://tailscale.com/install.sh -o /tmp/tailscale-install.sh && sudo -n sh /tmp/tailscale-install.sh`, then `sudo -n tailscale up --timeout 10s` and give the owner the sign-in link it prints. The brain opens on the Tailscale address within a minute, with no restart.

Save a worker reader's token and address for this user, without printing either the token or its contents:

`mkdir -p ~/.config/revxl/fewzhun-box && sudo -n install -o "$(id -un)" -m 600 /etc/fewzhun-box/tokens/<reader> ~/.config/revxl/fewzhun-box/token && echo saved`

Then write the address from the PAUSE POINT line (`http://<bind>:8791`) to `~/.config/revxl/fewzhun-box/url` and confirm with `fewzhun-box status`.

## 6. The done-test and its settings

The installer ends with the done-test (one PASS, FAIL or SKIP line per check). A FAIL that says a `done_test` setting is not set means Claude has not picked the test notes yet. Pick them now by reading the active notes in `<root>/vault` (or the notes clone):

- `query`: one word that appears in an active note.
- `semantic`: a question that shares no word longer than 3 letters with one active note, plus that note as `expect_path` (`<spoke>/<path in the spoke>`). This proves search by meaning. Write a real rewording, the way a person would ask.
- `superseded`: a note marked `status: superseded` (or with `superseded_by`) and a query that would match it.
- `decay`: one old dated note in a `decay: true` spoke and one old dated note in a `"never"` spoke, plus a query that returns both.

A vault with no superseded note or no old dated notes cannot pass that check: say so plainly; it is not an install fault. Write the values into the live file (show the change, then `sudo -n install -o root -g fbx -m 0640 ...` as in section 4), then run the fewzhun-box-check skill. No restart is needed for `done_test`.

Report the result by the output contract. For each FAIL use the fewzhun-box-check skill's table of meanings.

## 7. Readers later: add, change spokes, revoke, list

- Add: put the reader in `readers` in the live brain.json (on a yes), then `sudo -n <node> "${CLAUDE_PLUGIN_ROOT}/bin/tokens.mjs" add <reader>` and `sudo -n systemctl restart fewzhun-box-server`. It prints where the token file is, never the token. Hand it over as in section 5.
- Change spokes: prepare the edit to `readers.<reader>.spokes` in the live `/etc/fewzhun-box/brain.json`, show the exact change and get the owner's yes before saving it. Then reinstall with `sudo -n sh "${CLAUDE_PLUGIN_ROOT}/bin/install.sh" --apply` and run `sudo -n systemctl restart fewzhun-box-server`.
- Revoke (owner's yes first; anything using it stops working at once): `sudo -n <node> "${CLAUDE_PLUGIN_ROOT}/bin/tokens.mjs" revoke <reader>`.
- List: `sudo -n <node> "${CLAUDE_PLUGIN_ROOT}/bin/tokens.mjs" list` (shows only the last 4 characters).

After a failure you can't fix in two tries, follow `${CLAUDE_PLUGIN_ROOT}/references/failure-report.md` with `--skill fewzhun-box-setup`.
