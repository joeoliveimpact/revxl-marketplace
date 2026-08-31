# Background process ledger

Reference for maintainers. The user-facing behavior lives in `/session-closeout` Phase 4.2 and `/session-start` Phase 3.5.

## The problem it solves

Sessions leave background processes running. A dev server behind a `&`, a watcher, a script that never got stopped. They survive the session, survive a crash, and on a non-technical user's machine nobody notices.

The obvious fix is to look at what is running and stop what looks abandoned. **That does not work, and trying it is actively dangerous.**

- **Parent-PID lies.** MCP servers launch through `npx`, which routes through a `cmd.exe` wrapper, so their parent is `cmd.exe` and not `claude`. A "no live Claude parent" filter flagged around thirty actively-in-use MCP servers as orphans.
- **Name lies, catastrophically.** Claude Code IS node. `Stop-Process -Name node` kills the harness running the command plus every other open Claude window.
- **Age lies.** A three-day-old server can be in legitimate daily use. A ten-minute-old one can belong to another live session.
- **Counts drift on their own.** Node process count moved from 41 to 55 inside a single conversation purely from new sessions opening.

Selecting kill targets from the process table was attempted twice in one session and was wrong both times.

## The one rule

**Record on start, close from the ledger. The process table may VERIFY an entry. It may never SELECT a target.** Anything not in the ledger is reported and never stopped.

## How a PID is actually captured

This is the part that is easy to get wrong, because a `PostToolUse` hook sees the tool call only after it has already returned, and the harness reports a background Bash call with its own shell id (`bnup5l780`), not an OS pid.

The mechanism is a **bounded-window snapshot with command correlation**:

1. **`PreToolUse` on `Bash`** writes a single timestamp to `pending/<session>.t0`. No process enumeration, no JSON parse beyond one regex for the session id. It exists only to bound the window, so a survivor can never be attributed to a command that did not start it. Measured cost of the hook round trip on Windows: about 115 ms.
2. **`PostToolUse` on `Bash`** parses the payload and applies a gate (below). Ungated calls exit immediately and enumerate nothing. A full process enumeration costs roughly 2 seconds on Windows, so paying it on every Bash call is not acceptable.
3. For a gated call it takes one process snapshot and keeps processes that are **still alive** and **started at or after `t0 - 2s`**.
4. It removes machinery. See "the exclusion set" below. Refusals are written down as `vetoed` records rather than filtered away, so "excluded on purpose" stays distinguishable from "never seen".
5. It keeps only processes it can **correlate to the command that just ran**: the process's **executable** matches a token from the Bash command, or an **in-window, non-vetoed** ancestor's executable does. Ancestry is restricted to processes that also started inside the window and survived the veto, so neither a long-lived ancestor such as the harness nor a vetoed tool shell can launder an unrelated process into the ledger.
6. Everything else that appeared in the window is written down as an `unattributed` record and **never becomes stoppable**. The no-op is recorded rather than swallowed.

### Attribution matches the executable, not the command line

The first version asked whether the process's command line *contained* a token (`index($cmd, $token) >= 0`). That is far too loose in two ways that both proved real:

- the token `sleep` from `sleep 700 &` matched an unrelated `perl -e "sleep 900"`;
- **every Claude tool shell matched**, because the tool shell embeds the command verbatim inside one of its own arguments (`bash -c "source .../snapshot-bash-... && eval '<your command>' ..."`).

Now a token must equal the process's executable basename, with or without its extension. `"...\sleep.exe" 700` matches the token `sleep`; `bash.exe -c "...sleep 700..."` does not.

**Cost of the tightening, stated plainly:** an interpreter-wrapped launch whose child runs under a different executable (`npm run dev` spawning `node`) is no longer attributed. It is reported as `unattributed` instead. Unrecorded means unstoppable, so the failure is in the safe direction and it is visible.

### The gate

`run_in_background: true` in `tool_input`, or the command matches: trailing `&`, `nohup`, `setsid`, `disown`, `start /b`, `Start-Process`, `Start-Job`, `docker ... -d`, `docker compose up -d`, `pm2 start`, `screen`/`tmux` detached.

### Coverage boundary, stated exactly

**Caught:** processes still alive at the end of a gated Bash tool call whose command line, or whose in-window ancestor's command line, carries a token from that Bash command.

**Provably not caught:**

- **MCP servers.** The harness starts them, not a tool call, so no Bash hook ever observes them. **This gap is the feature.** It lines up exactly with the safety boundary: what we cannot prove we started, we must never stop. Do not try to close it.
- **Daemons started by commands the gate does not match.** A wrapper script that forks internally with no backgrounding syntax in the command line is invisible here.
- **Double-forking daemons that share no token with the command** and whose in-window parent chain is gone by the time the snapshot runs.
- **Anything started outside a Bash tool call**, including processes the user starts in their own terminal.
- **A pure-shell background job with no child executable.** `{ while true; do :; done; } &` forks a subshell that inherits the tool shell's own command line, so the machinery veto refuses it and nothing is recorded. Measured: `OPEN records = 0`, the subshell vetoed as `Claude tool-shell signature (shell-snapshots)`. The **leaf** of a normal `{ ...; } &` is still caught whenever it runs a real program, which is the ordinary case. The prose elsewhere says "a script left running behind a `&`"; the pure-shell subset of that is not trackable, and is refused rather than misattributed.
- **Wrapper scripts whose child runs under a different executable.** Measured: `bash wrapper.sh &` where the wrapper starts node produced `OPEN = 0`, with the node process landing in `unattributed`. Same shape as the `npm run dev` case above. Reported, never stopped.

Everything in that list stays running and is never reported as stoppable. The cost of the gap is a missed cleanup. The cost of closing it wrongly is killing the user's editor, their build, or Claude itself.

## The exclusion set: four independent vetoes

Getting this wrong once already offered Claude Code's own Bash tool shell and `conhost.exe` as kill candidates, through the normal consent flow, with no tampering. So the machinery guard is deliberately redundant. **Each of the four below is independently sufficient for that case.** If one silently no-ops, the others still hold.

**V1 ... pids known for certain, plus descendants.** This perl (`/proc/self/winpid` on Windows, `$$` elsewhere) and the launcher shell (`WSE_SHIM_PID`). Their ancestors are excluded too, and the walk now **hops over gaps**: the earlier version bailed at the first ancestor missing from the snapshot, which under msys is the immediate parent, because the launcher `exec`s away. Measured before the fix: **zero ancestors excluded**. Ancestors are excluded as individual pids only, never with their descendants ... the harness is an ancestor, and expanding it downwards would exclude every candidate on the machine and silently disable the whole feature.

**V2 ... msys ancestry read from `/proc`, not from the Windows process table.** msys keeps its own parent links, and they stay intact when the Windows parent-pid chain is broken. Walking `/proc/<pid>/stat` and mapping each hop through `/proc/<pid>/winpid` reaches the Claude tool shell directly. Chain pids are excluded; their descendants are not, because the process we are trying to record is itself a descendant of the tool shell. Returns nothing off msys, which is correct: V1's table walk does not break there.

**V3 ... a direct child of the harness is harness machinery.** Claude spawns tool shells and hook processes as its own children. Anything a command actually starts sits at least one level below that shell.

**V4 ... a structural signature veto** (`is_machinery()`): the tool-shell markers (`shell-snapshots`, `snapshot-bash`, the `claude-<hex>-cwd` handoff), `conhost.exe`, this plugin's own hook processes, and `claude.exe` itself.

A denylist by name is the **wrong** tool for selecting a kill target and the **right** tool for refusing one. It can only ever prevent a stop, never cause one, so its worst case is a missed cleanup rather than a killed shell. That asymmetry is why it is safe here and unsafe everywhere else in this file.

The plugin-machinery patterns are plain substring matches, so they over-refuse: a user script whose own name merely contains `run-hook.cmd`, `process-ledger` or `process-probe.ps1` (say, `test-process-ledger.sh`) is refused too. Deliberately left loose, because the failure is a missed cleanup on an oddly-named script rather than a wrong kill.

**V4 is coupled to current Claude Code internals.** `shell-snapshots`, `snapshot-bash` and the `claude-<hex>-cwd` handoff are strings the harness happens to use today. If a future release changes them this veto goes quiet, which is the whole reason the other four exist and do not depend on it.

There is effectively a fifth: the tightened attribution rule above rejects the tool shell on its own, since the command appears only inside one of the shell's arguments and never as its executable.

### Checking the vetoes one at a time

`explain` exists so the last two can be verified without editing the file:

```bash
printf '%s\n' '<a candidate command line>' | process-ledger explain --tool-command "sleep 700 &"
```

It prints, per candidate, the parsed executable, whether the machinery veto fires, whether attribution matches, and the resulting verdict.

## On-disk layout

Persistent and per-workspace, deliberately not in a temp directory and not inside the workspace. A crashed session never reaches closeout, so the record has to outlive both the session and a reboot.

```
~/.claude/workspace-superengine/process-ledger/
  cli-path.txt                        absolute path to the CLI, so a skill can
                                      find it without depending on an env var
  <workspace-name>-<md5[0:8]>/
    ledger.jsonl                      append-only, folded on read
    pending/<session>.t0              the PreToolUse timestamp
    sessions/<session>.json           heartbeat + owning harness identity
    DEGRADED.txt                      plain-text record of anything that broke
```

Override the root with `WORKSPACE_SUPERENGINE_LEDGER_HOME` (used by the tests so they never touch the real ledger).

`ledger.jsonl` is append-only and folded on read: an `open` record is live until a matching `close` record appears. It is never rewritten in place, because two sessions can be appending at once and a lost update means a forgotten process.

### Record shape

```json
{"type":"open","uid":"1786720640-47128-1","pid":47128,
 "started_at":"2026-08-14T15:17:18Z","started_epoch":1786720638,
 "cmd":"\"C:\\Program Files\\Git\\usr\\bin\\sleep.exe\" 400",
 "workspace":"<workspace-root>","session":"sess-alpha-0001","started_by":"bash-tool",
 "ppid":88044,"rss_kb_at_record":5372,"recorded_at":"2026-08-14T15:17:20Z",
 "tool_command":"sleep 400 &","gate":"trailing &",
 "matched_on":"command token 'sleep'","window_fallback":false,
 "harness_pid":116776,"harness_started_at":"2026-08-14T14:50:39Z"}
```

Other types: `close` (`outcome` is `stopped` or `gone`), `unattributed`, `vetoed`, `degraded`.

### The five states `list` reports

| State | Meaning | Offerable |
|---|---|---|
| `STOPPABLE` | identity verified, and this Claude instance owns it or the owning session is provably gone | yes, with consent |
| `OTHER-WINDOW` | identity verified, another live Claude harness owns it | no |
| `MISMATCH` | the pid is running something other than what was recorded, or the recorded pid is absent while its command and start time run elsewhere | no |
| `MACHINERY` | identity verified, and the target is Claude's own plumbing | no |
| `GONE` | the pid is absent and nothing matches the recorded identity; the entry is auto-closed | nothing to do |

Only `STOPPABLE` enters the consent token and the `STOPPABLE:` count. **`MACHINERY` is deliberately not a failure.** It means the entry passed every truth check and was refused anyway, because a true entry pointing at the shell every command runs in is still a shell you must not kill. The state exists so that refusal is visible and named rather than looking like a process that quietly vanished from the list. `skills/session-closeout/SKILL.md` Phase 4.2 Step 2 carries the same table for the agent, and is the single description the two skills share.

### Output blocks a reader will actually see

- **`Resolved by:`** ... printed under `Workspace:` on every `list`. Says whether the workspace came from `CLAUDE_PROJECT_DIR` or from walking up to a marker file, and names the marker. **This is the line that diagnoses a wrong-workspace read**, which is exactly the D3 failure shape: a plausible-looking "nothing is running" that is really an answer about a different directory. When the `Workspace:` line looks wrong, this line says why.
- **`Refused as machinery ... N process(es)`** ... a count of things vetoed at recording time, so they never became entries at all. Backed by the `vetoed` records in the JSONL. Informational; it is what makes "refused" distinguishable from "never seen" at the place a human is actually looking.
- **`Also seen, never recorded and never stoppable ... N`** ... the `unattributed` count, for processes that appeared in the window but could not be tied to the command.

### Finding the workspace

The hook side gets `CLAUDE_PROJECT_DIR`. The CLI side, run from a skill's Bash call, **does not** ... verified unset there. So the CLI walks up from the current directory for a real marker (`.claude/workspace.yml`, `.claude/rules/overrides.md`, `CLAUDE.md`, `.git`, plus legacy `RULES.md`) instead of trusting cwd. Trusting cwd meant running from a subdirectory hashed to a different slug, so `list` read an empty folder and reported a clean machine while the populated ledger sat one slug over.

If no marker is found anywhere above, the tool **refuses** and says so, rather than answering "nothing is running" about a workspace it could not identify. `list` prints the resolved path and how it was resolved on every run, and names any sibling ledgers that do exist under the same root.

## Verification before stopping

The identity triple is **pid + started_at + cmd**, and all three must match the live process before anything is stopped. Windows and Linux both reuse pid numbers; by closeout, pid 39916 may be something else entirely.

**Mismatch means SKIP. Never a force, never a retry, never a lookup by another route.** The entry stays open and gets reported again next time. It closes on its own when that pid finally dies.

That promise has one more leg than it looks. If the `pid` field itself is wrong, the entry classifies `GONE` and would be retired, losing a live process for good. So before retiring anything, the classifier checks whether the recorded command **and** start time are running under some other pid. If they are, the entry is `MISMATCH`, not `GONE`: it stays open, is reported every time, and is never stoppable. That check reads the process table to report, never to select, so no target is ever chosen from it.

Re-verification runs three times: when `list` classifies, when `stop` re-classifies, and once more immediately before each signal.

`started_epoch` is compared **only on Windows**, where it is exact. On unix it is derived from elapsed time and jitters by a second between reads, so comparing it there would mark every entry `MISMATCH` and silently disable the feature. The identity string on unix is `lstart`, which is stable.

## Ownership, the three consent gates

1. **Not owned by a live session.** Each entry records the owning harness pid and its start time. `STOPPABLE` means either this Claude instance owns it, or the owning harness is provably gone (verified by identity, not by pid alone). A different harness that is still alive means `OTHER-WINDOW`: report only. Where no harness identity was captured, it falls back to session heartbeat age with a 4-hour window and says which rule it used.
2. **Provably started by this workspace's sessions.** Only ledger entries under this workspace's slug are ever considered.
3. **Explicit consent for that specific list, re-checked at kill time.** `list` prints a consent token, an md5 over the exact `pid|started_at|cmd` set it offered. `stop` recomputes it and refuses the whole batch if it differs. Per-pid verdicts are printed *before* the token check, so the reason any one process was skipped is always legible even when the batch is refused.

## Platform notes

- Windows uses `process-probe.ps1` (`Get-CimInstance Win32_Process`). Unix uses `ps -eo pid=,ppid=,etime=,rss=,lstart=,command=`. Both normalise to the same TSV, so recording and verifying share one code path. Changing that format silently invalidates every existing entry.
- **`taskkill //F //PID n`, with doubled slashes, is deliberate.** Git Bash rewrites a lone `/F` into the path `F:/` before taskkill sees it, which fails with "Invalid argument/option" and leaves the process running. This was caught in testing after the first implementation reported `FAILED` on a process it should have stopped. There is a `Stop-Process -Force` fallback if the mangled-argument error appears anyway.
- Graceful first, then forced. On Windows a console process typically answers the polite `taskkill` with "can only be terminated forcefully"; that is treated as "still alive, escalate under the same consent," not as a failure.

## Failure behavior

Hook subcommands always exit 0. A ledger problem must never break a session. `list`, `stop` and `paths` exit 2, and the launcher matches those codes when it cannot reach perl at all.

**The report that the ledger is broken must not live inside the ledger.** Writing `DEGRADED.txt` into an unwritable folder fails too, and a swallowing `eval` around it turns a broken install into a machine that looks perfectly clean. So `note_degraded()` also writes to the system temp directory, under a per-workspace filename, and to stderr, every time.

Two separate mechanisms sit on top of that, and it is worth being precise about which one does what, because it is easy to assume the wrong one:

- **The drain relocates, it does not silence.** Once the real ledger is writable again, the out-of-band file is appended into `DEGRADED.txt` and deleted. That keeps one machine-wide temp file from collecting every workspace's history. It does **not** quieten anything: `read_degraded_split()` reads the destination file too, so a drained line still reports from its new home. Measured: after a fault fully healed and the marker drained, `session-start` on an otherwise empty ledger still emitted 579 bytes on every run.
- **The 24-hour window is what ends the banner.** Only degradation timestamped within the trailing 24 hours is reported. Older lines stay in the file and `list` prints a one-line count of them. That is what stops a healed fault from shouting forever, and a banner that fires forever stops being read.

So the "an empty ledger emits zero bytes at session start" property holds **only when no degradation was recorded in the previous 24 hours.** Within that window the banner is correct and wanted: the lines are timestamped historical fact, not a claim that anything is currently broken.

**`ledger_unusable()` is the gate every entry point asks first.** It proves the ledger folder can be created *and written to*, with an actual write, not a stat. `list` may only print "the ledger folder was read and written to successfully, and it holds no open entries" after that returns clean. Anything else prints `PROCESS LEDGER UNAVAILABLE` with the reason, because "I could not check" and "nothing is running" must never be the same output.

`home_dir()` returns undef rather than falling back to the current directory when `HOME` and `USERPROFILE` are both unset. A cwd-derived home drifts with wherever the shell happened to be, which produces a different ledger every time and a permanent, confident, wrong "nothing is running".

If perl or `JSON::PP` is missing, the launcher and the CLI both say `PROCESS LEDGER UNAVAILABLE` in words, and `session-start` emits an in-context notice so the session knows it is running untracked.
