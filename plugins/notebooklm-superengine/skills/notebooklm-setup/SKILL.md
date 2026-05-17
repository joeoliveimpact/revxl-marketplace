---
name: notebooklm-setup
description: Use to install Google NotebookLM on this computer and sign in, or to fix/refresh/remove that install. Trigger phrases include "set up notebooklm", "install notebooklm", "notebooklm isn't working", "sign in to notebooklm", "reconnect notebooklm", "my notebooklm login expired", "update notebooklm", "uninstall notebooklm", "/notebooklm-setup". Cross-platform (Mac + Windows), non-technical clients. This is the front door — every other notebooklm skill depends on it.
---

# notebooklm-setup — Install, Authenticate, Maintain (v0.1)

One guided pass that takes a client from "nothing" to a working, signed-in `notebooklm` CLI on **Mac or Windows**. Also handles re-auth, update, and clean uninstall. Local-only — no servers, tunnels, or extra accounts.

This skill encodes hard-won fixes. Follow the OS branches exactly. Do not improvise the auth flow.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If `beginner`, emit this 2-3 sentence preamble before any work. If `standard` (or missing), skip silently.

> I'm going to set up Google NotebookLM on your computer. It's about a 5-minute process: I check what's already installed, install the missing pieces, then open a browser once so you can sign in to Google. I'll explain each step and you can pause anytime — nothing here is risky.

## Layer 2: Suggest before invoking

If the prompt is borderline — could want setup or just a quick answer:

> "Sounds like NotebookLM might not be set up on this machine yet — want me to run `/notebooklm-setup` and get it installed and signed in? Or is it already working and you just have a question?"

Only run the full process after confirmation. If the user explicitly invokes `/notebooklm-setup`, skip the suggestion and proceed.

## Runtime environment

Read `.claude/workspace.yml#environment`.

- **`code`** — run the commands below directly.
- **`cowork`** — Bash is unavailable. This skill **cannot install software in Cowork**. Tell the user plainly: "NotebookLM setup has to run in Claude Code (the terminal app), not here — it installs software on your machine. Open this workspace in Claude Code and run `/notebooklm-setup` there." Then stop.

## Sub-modes (read `$ARGUMENTS`)

| Invocation | Mode | What runs |
|---|---|---|
| `/notebooklm-setup` (no args) | **install** | Full Phases 1–8 |
| `/notebooklm-setup reauth` | **reauth** | Phase 5 (login) → Phase 7 (verify) only |
| `/notebooklm-setup update` | **update** | `pip install -U "notebooklm-py[browser]"` in the venv → Phase 7 |
| `/notebooklm-setup uninstall` | **uninstall** | Confirm, then remove venv, PATH wrapper, `~/.notebooklm`, state marker |

If `install` mode detects an already-working install (Phase 1), offer reauth/update/uninstall instead of reinstalling.

---

## Phase 1 — Detect

1. **OS:** run `python -c "import sys; print(sys.platform)"` (Windows) or `python3 -c "import sys; print(sys.platform)"` (Mac/Linux). `win32` → **Windows branch**. `darwin` → **Mac branch**. Linux → Mac branch (same POSIX paths).
2. **Existing install:** check for the state marker `~/.notebooklm/.superengine`. If present, run `notebooklm auth check --test` (via the PATH wrapper). If it prints `Authentication is valid.` → tell the user it's already set up and working, list sub-modes, and stop unless they asked for a sub-mode.
3. Set `PYBIN` for the rest of the run:
   - Windows: `%USERPROFILE%\.notebooklm-venv\Scripts\python.exe`
   - Mac: `~/.notebooklm-venv/bin/python`
4. Set `NB` (the CLI) for the rest of the run:
   - Windows: `%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe`
   - Mac: `~/.notebooklm-venv/bin/notebooklm`

Branch handling for **reauth / update / uninstall** here per the sub-mode table, then jump to the relevant phase.

## Phase 2 — Dependency audit (report before acting)

Check each, then present a plain-English checklist of what's present vs. what will be installed. **Confirm before installing anything.**

1. **Python ≥ 3.10:** `python --version` (Win) / `python3 --version` (Mac). Below 3.10 or absent → will install.
2. **Package manager:** Windows → `winget --version`. Mac → `brew --version`. Absent → flag (Mac: direct user to install Homebrew from brew.sh first and stop; Windows: winget ships with Windows 10/11 — if absent, direct to Microsoft Store "App Installer").
3. **Browser channel:**
   - Windows: confirm Edge exists at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` or `C:\Program Files\Microsoft\Edge\Application\msedge.exe`. (Always present on Win10/11.)
   - Mac: Playwright Chromium will be installed in Phase 3 (no system browser needed).

Present like:
> Here's what I found:
> - Python 3.12 ✓ (already good)
> - winget ✓
> - Microsoft Edge ✓
> I'll create an isolated environment and install the NotebookLM tool into it. Nothing touches your system Python or your normal browser. Ready?

## Phase 3 — Install (OS-branched, narrate each step)

**Windows:**
1. If Python < 3.10/absent: `winget install -e --id Python.Python.3.12` (narrate; tell user a new terminal may be needed afterward).
2. `python -m venv "%USERPROFILE%\.notebooklm-venv"`
3. `& "%USERPROFILE%\.notebooklm-venv\Scripts\python.exe" -m pip install --upgrade pip "notebooklm-py[browser]"`
4. **Do NOT run `playwright install chromium`** — Playwright's bundled Chromium fails with a side-by-side (SxS) activation error on many Windows machines. We use the system Edge channel instead (Phase 5).

**Mac:**
1. If Python < 3.10/absent: `brew install python@3.12`
2. `python3 -m venv ~/.notebooklm-venv`
3. `~/.notebooklm-venv/bin/python -m pip install --upgrade pip "notebooklm-py[browser]"`
4. `~/.notebooklm-venv/bin/python -m playwright install chromium`

## Phase 4 — PATH wrapper

So `notebooklm` works in any terminal.

**Windows:**
1. Create `%USERPROFILE%\bin` if absent.
2. Write `%USERPROFILE%\bin\notebooklm.cmd` containing exactly:
   ```
   @echo off
   "%USERPROFILE%\.notebooklm-venv\Scripts\notebooklm.exe" %*
   ```
   (ASCII encoding.)
3. Add `%USERPROFILE%\bin` to the **user** PATH (only if not already present):
   ```powershell
   $u=[Environment]::GetEnvironmentVariable("Path","User"); if($u -notlike "*$env:USERPROFILE\bin*"){[Environment]::SetEnvironmentVariable("Path","$u;$env:USERPROFILE\bin","User")}
   ```
4. Tell the user: "I added `notebooklm` to your PATH. Open a **new** terminal window to use it directly. I'll keep using the full path for the rest of this setup."

**Mac:**
1. `mkdir -p ~/bin`
2. `ln -sf ~/.notebooklm-venv/bin/notebooklm ~/bin/notebooklm`
3. If `~/bin` not on PATH, append `export PATH="$HOME/bin:$PATH"` to `~/.zshrc` (or `~/.bashrc` if that's the shell). Tell the user to open a new terminal.

## Phase 5 — Authenticate (self-detecting login, synchronous)

The built-in `notebooklm login` needs interactive terminal input that Claude Code's tools can't provide. Use this custom script instead. It opens a real browser, the user signs in, and it **detects success on its own** and exits — no signal files, no background process.

Write this to a temp file (`%TEMP%\nlm_login.py` on Windows, `/tmp/nlm_login.py` on Mac):

```python
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

STORAGE_PATH = Path.home() / ".notebooklm" / "storage_state.json"
PROFILE_PATH = Path.home() / ".notebooklm" / "auth_profile"
TIMEOUT_SECONDS = 280
CHANNEL = "__CHANNEL__"  # "msedge" on Windows; "" on Mac (omit channel)

STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
print("Opening a browser for Google sign-in...", flush=True)

with sync_playwright() as p:
    kwargs = dict(user_data_dir=str(PROFILE_PATH), headless=False)
    if CHANNEL:
        kwargs["channel"] = CHANNEL
    browser = p.chromium.launch_persistent_context(**kwargs)
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.goto("https://notebooklm.google.com/")

    required = {"SID", "__Secure-1PSID", "__Secure-1PSIDTS", "__Secure-3PSIDTS"}
    deadline = time.time() + TIMEOUT_SECONDS
    authed = False
    while time.time() < deadline:
        names = {c["name"] for c in browser.cookies()}
        if required.issubset(names):
            time.sleep(3)  # let rotating tokens settle
            authed = True
            break
        time.sleep(2)

    if not authed:
        browser.close()
        raise SystemExit("TIMEOUT: sign-in not completed.")

    with open(STORAGE_PATH, "w") as f:
        json.dump(browser.storage_state(), f)
    print(f"AUTH OK. Saved {len(browser.storage_state().get('cookies', []))} cookies.", flush=True)
    browser.close()
print(f"Saved to {STORAGE_PATH}", flush=True)
```

Substitute `__CHANNEL__`: `msedge` on Windows, empty string on Mac.

**Critical guardrails — do not deviate:**
- **Never** add `args=["--disable-blink-features=AutomationControlled"]`. It crashes Edge instantly (exit code 21) on current builds.
- **Never** use a bash signal-file / background-process pattern. The script is synchronous and self-detecting.
- Wait for the **full** cookie set including `__Secure-1PSIDTS` and `__Secure-3PSIDTS`, not just `SID` — those rotate in a few seconds *after* sign-in; saving early produces an invalid session.
- Before running, delete a stale `~/.notebooklm/auth_profile` only if no browser process is locking it; if locked, kill only the automation browser processes whose command line references `.notebooklm` (never the user's normal browser).

Run it synchronously and narrate first:
> A browser window will open. Sign in to your Google account and let it land on notebooklm.google.com. It closes itself automatically once you're in — just leave it. (Up to ~4 minutes.)

Run: `<PYBIN> -u <login script path>` with a 300s timeout.

## Phase 6 — Reconcile the profiles migration

notebooklm-py ≥ 0.4 migrates auth into a `profiles/` layout on first CLI call.

1. Run `<NB> auth check` once (it triggers/repairs the migration).
2. If it errors copying/removing `~/.notebooklm/browser_profile` because files are locked: kill only automation browser processes referencing `.notebooklm`, delete the stale `~/.notebooklm/browser_profile`, retry.
3. Ensure the freshly saved `storage_state.json` is also at `~/.notebooklm/profiles/default/storage_state.json` (copy it there if the migration created that path). The CLI reads the profiles path.

## Phase 7 — Verify (REQUIRED before claiming done)

Both must pass:

1. `<NB> auth check --test` → must contain `Authentication is valid.`
2. `<NB> list` → must return notebooks (or an empty-but-valid list, not an auth error).

If either fails → STOP, do not claim success. Route to the matching remedy in `docs/known-issues-windows-mac.md` and tell the user the specific next step (usually `/notebooklm-setup reauth`).

## Phase 8 — Mark + finish

1. Write `~/.notebooklm/.superengine` containing `version=0.1.0` and the date (so the SessionStart hook and future `notebooklm-doctor` can detect a healthy install).
2. Success report + **forward-looking next-moves offer** (beginner tone, ≤3 items). This is the activation moment — end with concrete doors, not just "done":
   > NotebookLM is set up and signed in ✓
   > - Tool installed and on your PATH (open a new terminal to use `notebooklm` directly)
   > - Signed in to Google — verified live
   >
   > What next? You can:
   > 1. **See what you've got** — "list my NotebookLM notebooks"
   > 2. **Build your first one** — "build a notebook about &lt;topic&gt;" (uses `notebooklm-build`)
   > 3. **Let me suggest what to build** — "look at my material and suggest notebooks worth building" (uses `notebooklm-suggest`)

   **Graceful degradation by version:** offer only the doors whose skills exist. v0.1.0 ships setup alone — offer #1 (the `notebooklm list` nudge) only. As `notebooklm-build` / `notebooklm-suggest` ship, light up #2 / #3. Never offer a door that routes to a skill that isn't installed. The offer *points at* those skills via natural language (soft coordination) — it never embeds their work in setup.

## Uninstall mode

Confirm explicitly ("This removes the NotebookLM tool and its saved sign-in from this computer. Your notebooks in Google are untouched. Proceed?"), then:
- Remove `~/.notebooklm-venv`
- Remove the PATH wrapper (Windows `%USERPROFILE%\bin\notebooklm.cmd`; Mac `~/bin/notebooklm` symlink) — leave the PATH entry, it's harmless
- Remove `~/.notebooklm` (auth + profiles + marker)
- Confirm done with a clean summary.

---

## Ground rules (inherited from RULES.md)

- **Intent Clarification:** if OS detection is ambiguous or a package manager is missing, ask once — don't guess.
- **Least Complexity:** the venv + PATH wrapper + auth is the floor. No background services, no MCP server, no tunnels (local-only by design).
- **Surgical Execution:** never kill the user's normal browser; only automation processes referencing `.notebooklm`. Never overwrite an existing working install without offering sub-modes first.
- **Declarative Focus:** DoD = `auth check --test` valid AND `list` works AND the state marker is written. Anything past that belongs to other notebooklm-superengine skills.
