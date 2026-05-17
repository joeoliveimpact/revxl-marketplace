# Known Issues — Windows & Mac Setup

Durable record of the failure modes hit while making notebooklm-py work cross-platform, and the fix each. `notebooklm-setup` already bakes these in as guardrails; this doc is the remedy map when Phase 7 verification fails.

## Windows

| Symptom | Cause | Fix |
|---|---|---|
| `playwright install chromium` then browser fails: "side-by-side configuration is incorrect" / SxS activation error / `Dependent Assembly <ver> could not be found` | Playwright's bundled Chromium SxS manifest fails to activate on many Windows machines (recurs across Chromium versions; not a missing VC++ redist) | Don't use bundled Chromium on Windows. Use the system Edge via Playwright `channel="msedge"`. Edge ships on all Win10/11. |
| Browser launches then exits immediately, exit code 21, `TargetClosedError: ...browser has been closed` | The `--disable-blink-features=AutomationControlled` launch arg crashes current Edge builds | Never pass that arg. Plain `launch_persistent_context` works. |
| Login script run via background job / `Start-Process -Hidden` exits with no output / exit 21 | PowerShell jobs & windowless processes can't host the GUI browser; output buffers lost | Run the login script **synchronously** in the foreground. It self-detects sign-in and exits on its own. No signal file, no background process. |
| `auth check` fails: missing `__Secure-1PSIDTS`; "extraction was incomplete" | Login script saved the session before Google set the rotating `*PSIDTS` tokens (they appear a few seconds after sign-in) | Poll for the full set `{SID, __Secure-1PSID, __Secure-1PSIDTS, __Secure-3PSIDTS}` then wait 3s before saving. |
| First CLI call traceback in `migrate_to_profiles` / `shutil` `WinError 32` "file in use" | notebooklm-py ≥0.4 migrates auth into `profiles/`; a stale `~/.notebooklm/browser_profile` is locked by a leftover automation browser | Kill only automation browser procs whose command line references `.notebooklm` (never the user's normal browser), delete the stale `browser_profile`, re-run `auth check`. Ensure `storage_state.json` lands at `~/.notebooklm/profiles/default/`. |
| `notebooklm` not found in a new terminal | PATH wrapper added to user PATH but the current shell predates it | Open a new terminal. Setup uses the full venv path for the rest of the run regardless. |

## Mac

| Symptom | Cause | Fix |
|---|---|---|
| `python3` is 3.9 (system default), pip install fails / too old | macOS ships Python < 3.10 | `brew install python@3.12`; build the venv with that interpreter. |
| `playwright` browser missing | Chromium not installed | `~/.notebooklm-venv/bin/python -m playwright install chromium` (Mac has no SxS issue — bundled Chromium is fine here; do **not** use the Edge channel). |
| `~/bin/notebooklm` not found | `~/bin` not on PATH | Append `export PATH="$HOME/bin:$PATH"` to `~/.zshrc` (or `~/.bashrc`), open a new terminal. |

## Both platforms

| Symptom | Cause | Fix |
|---|---|---|
| Was working, now auth errors mid-use | Google session expired (`*PSIDTS` rotate/expire) | `/notebooklm-setup reauth` — re-runs sign-in only, picks up the new session, no reinstall. |
| Generation commands hang or fail | NotebookLM rate limit / long job (audio 10–20m, video 15–45m) | Expected. Kick off → `artifact wait` → notify → `download`. Retry later on rate-limit. |
| Cowork "couldn't reach MCP server" | Out of scope — this plugin is local-only by design | Use NotebookLM in Claude Code (terminal), not Cowork. |
