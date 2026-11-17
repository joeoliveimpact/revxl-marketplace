---
name: fewzhun-box-check
description: >
  Checks the Fewzhun Box brain on a Linux server and says in plain English what works and what to
  fix next: the search service, tokens, meaning search, hidden superseded notes, the nightly sync,
  graph and draft jobs, and the owner's open setup steps. Use for "is the brain working", "check the
  brain", "brain health", "why can't my bot reach the brain", "the brain search is broken", "did the
  nightly graph run", "did the sync work", "run the done-test". NOT for installing (fewzhun-box-setup)
  or searching (fewzhun-box-use).
---

# fewzhun-box-check: is the brain healthy?

## Output contract (every run, in this order)

1. A one-line verdict: "The brain is working", "The brain works, with N things to fix", or "The brain is down".
2. One plain line per area (service, sign-in and access, search by meaning, hidden notes, privacy, the bot's container, sync, graph, nightly drafts, the Claude login): ✓ ok, ⚠ needs attention, ✗ broken, or "not set up". Never paste PASS/FAIL lines, paths or JSON to the owner.
3. Under every ⚠ or ✗: the next fix, either what Claude will do on a yes or the one thing the owner does (a click path, never a command).
4. Open owner steps still waiting (deploy key, firewall, kernel setting, Tailscale, a reader's token).
5. On any failure you can't fix in two tries: what went wrong in plain words, then the failure report offer below.

## Re-invoke guard (read before step 1)

- If the conversation was compacted since this skill loaded, invoke this skill again before going on.
- This check only reads. It changes nothing unless the owner says yes to a named fix.
- **Never run the search engine's own `status` command** (`obsidian-hybrid-search status`): it rewrites the index. `fewzhun-box status` below is a different, safe command. Never run a forced reindex.
- Never print, echo or `cat` a token or a token file. Never put a token on a command line.

## Ground rules

- **The client never types a command.** Claude runs each command in the Bash tool.
- `<node>`: `command -v node && node --version`; if missing or under 20, `ls <code_root>/node/node-v*/bin/node 2>/dev/null | tail -1`. Reuse the printed path literally.
- `<root>`: `/opt/fewzhun-box` unless brain.json says otherwise.
- `<code_root>`: `/opt/fewzhun-box-app` unless brain.json says otherwise. Public code lives here; private data stays in `<root>`. Workers need no membership in `fbx`.
- Admin commands run as `sudo -n ...`. If `sudo -n true` fails, run only step 2 and say the full check needs an admin session.
- Plain English. Gloss a term once, e.g. "token (the long password a reader uses)".

## 1. Is it installed?

`sudo -n test -f /etc/fewzhun-box/brain.json && test -d <code_root>/app && echo INSTALLED`

Not installed: say "The brain isn't installed on this server yet" and offer the fewzhun-box-setup skill. Stop.

## 2. The service, as this user sees it

`fewzhun-box status`

It prints the config, the address, whether the service answers, this user's token file, the reader name and spokes, and one line per nightly job. It never prints a token.

Also: `systemctl is-active fewzhun-box-server; systemctl list-timers 'fewzhun-box-*' --no-pager`

## 3. The done-test (admin)

Run with `run_in_background` if it is slow (it sends real searches), then read every line:

`sudo -n env FBX_NODE=<node> sh <code_root>/app/bin/done-test.sh`

Each line is PASS, FAIL or SKIP; the last line counts failures. It only reads, apart from the searches it sends.

## 4. The nightly job files (admin)

`sudo -n fewzhun-box status`

This merges `<root>/status/` with `/var/lib/fewzhun-box/status/sync.json`. Each job line says `ok` or `FAILED` with its reason. No line for a job means it has not run yet. For graph details, read `<root>/status/graph.json` as admin: `llm_calls` per spoke is 0 on a night with no changed notes.

Only when the graph or harvest reason mentions the login guard, run its check (reads only): `sudo -n python3 <code_root>/app/py/claude_guard.py check`

## 5. What each failure means and the next fix

| What the line says | Plain meaning | Next fix |
|---|---|---|
| `service: not answering`, health FAIL | The brain service is down. | Claude reads `sudo -n journalctl -u fewzhun-box-server -n 50 --no-pager`, explains it, and on a yes runs `sudo -n systemctl restart fewzhun-box-server`. |
| `bind ... resolves to no address` | The Docker network the bot uses isn't there. | Check Docker is running (`systemctl is-active docker`). The service retries by itself once it exists. |
| no token / 401 | The token is missing or not recognised. | Worker: re-save the token (fewzhun-box-setup, section 5). Bot: its token file is wrong; the bot's builder re-copies it. |
| wrong spoke / 403 | That token may not read that spoke (or it doesn't exist). | Working as designed. To widen access, change `readers` with the fewzhun-box-setup skill. |
| meaning search FAIL "did not find" | Search by meaning did not find the test note. | Re-run once (the first search after a restart is slower). Still failing: the test question may be too far from the note; pick a closer rewording. If every search fails, the embedding model did not load: report it. |
| meaning search FAIL "shares words" | The test question proves nothing. | Claude rewords `done_test.semantic` so it shares no words with the note. |
| superseded FAIL | A replaced note still shows up. | Run the sync once (`sudo -n systemctl start fewzhun-box-sync`), then check again. Still there: report it. |
| ageing FAIL | Older notes aren't ranked as set up. | Check the spoke's `decay` setting (`true`, `false` or `"never"`) and that both test notes are old and dated. |
| `... is not set in brain.json` | The done-test has no test notes yet. | Claude picks them (fewzhun-box-setup, section 6). |
| outside address answered | **The brain can be reached from the internet.** | Urgent. Say so first. Claude checks `bind` in brain.json is not a public address and that no proxy forwards port 8791. |
| listeners FAIL | The service listens somewhere it shouldn't. | Same as above. |
| container FAIL `not found` | The bot's container name changed or the bot is stopped. | Ask the owner if the bot runs; update `done_test.container`. |
| container `/health` FAIL | The bot can't reach the brain. | Usually the firewall rule (owner step "firewall"). |
| container search not 200 | The bot reaches the brain but its key is wrong. | The bot's builder re-copies its token (references/agent-wiring.md). |
| query log FAIL | The query log is missing, or holds a token. | Missing after a fresh install is normal until the first search. Holds a token: urgent, report it at once. |
| sync `ok: false` | The notes couldn't be pulled. | Most often the deploy key isn't on GitHub yet (owner step "deploy key"). |
| graph `ok: false` | Last night's graph didn't build. The old graph stays. | Read the reason. A login-guard refusal (agent busy, login near expiry) clears by itself on a later night. Anything else after two nights: report it. |
| harvest `ok: false` | Last night's drafts weren't made. Nothing was half-written. | Same as graph. |

## 6. Open owner steps

Mention each one that still applies, in plain words, with what Claude can do on a yes:
- **deploy key**: sync is on and its status file is missing or says the pull failed.
- **firewall**: `sudo -n ufw status` is active and the container check could not reach `/health`.
- **kernel setting**: `sysctl -n kernel.apparmor_restrict_unprivileged_userns` prints 1 and Claude workers run here.
- **Tailscale**: `tailnet_bind` is set and `tailscale ip -4` prints nothing.
- **a reader's token**: a reader is in brain.json but its key isn't where it is used (the container check fails with 401, or this user's token file is missing).

## 7. Tell the owner

Follow the output contract. Example: "The brain works, with 1 thing to fix. ✓ Service answering. ✓ Search by meaning found the test note. ✓ Replaced notes stay hidden. ✓ Not reachable from the internet. ⚠ Your bot can't reach the brain yet: your firewall blocks it. I can add one rule that lets only your bot's network in. Add it?"

After a failure you can't fix in two tries, follow `${CLAUDE_PLUGIN_ROOT}/references/failure-report.md` with `--skill fewzhun-box-check`.
