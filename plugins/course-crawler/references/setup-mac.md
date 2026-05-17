# Setup on macOS (and Linux/WSL)

This reference walks through every step of `setup` on macOS. Linux and WSL users follow the same steps with `apt` (or `dnf`) instead of `brew` where noted.

## Variables this doc refers to

- `$ISS_HOME` ... user-specific data dir. Resolves to `$HOME/.iss` on Mac/Linux.
- `$VENV` ... the per-user Python virtualenv at `$ISS_HOME/venv`.

## Step 1: Install Homebrew (if missing)

Check first: `which brew`. If it prints a path, skip ahead.

If missing, Homebrew's installer needs the user's sudo password and can't accept piped input from Claude Code's Bash tool. So instruct the user to paste this **into their own Terminal app** (not in Claude Code) and wait for it to finish:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Tell them: "When this finishes (a few minutes), come back here and tell me 'done'."

Then wait. When they confirm, verify `which brew` succeeds.

**Linux/WSL users**: skip Homebrew. Use `sudo apt update && sudo apt install -y python3.13 ffmpeg yt-dlp` (Ubuntu) or your distro's equivalent.

## Step 2: Install the CLI tools

```bash
brew install python@3.13 ffmpeg yt-dlp uv
```

`uv` is required because `browser-use install` shells out to `uvx`.

## Step 3: Create the per-user virtualenv

```bash
mkdir -p ~/.iss
/opt/homebrew/bin/python3.13 -m venv ~/.iss/venv
~/.iss/venv/bin/pip install --upgrade pip
```

On Intel Macs, Python may be at `/usr/local/bin/python3.13` instead. Use `which python3.13` to find it.

## Step 4: Install the Python deps

```bash
~/.iss/venv/bin/pip install \
  browser-use \
  faster-whisper \
  trafilatura \
  httpx \
  websockets
```

This pulls in ~80 transitive packages. Takes about 30 seconds on a good connection.

Important: **Python 3.13** specifically. Python 3.14 has an `asyncio.get_event_loop()` regression that breaks browser-use's CLI.

## Step 5: Download Chromium for browser-use

```bash
~/.iss/venv/bin/browser-use install
```

This pulls a copy of Chromium (~200MB) into `~/Library/Caches/ms-playwright/`. Required for any login flow or browser-use-driven discovery.

## Step 6: Verify the install

```bash
~/.iss/venv/bin/browser-use doctor
```

Expect 3-of-5 or 5-of-5 checks passed. The `cloudflared` and `profile_use` checks are optional features (tunneling, profile sync). The three required checks are `package`, `browser`, `network`.

## Step 7: Wire the MCP into Claude Code

Edit `~/.claude.json` (it likely already exists ... read it first, don't overwrite).

Use Python to do this safely:

```bash
~/.iss/venv/bin/python <<'PY'
import json, os
p = os.path.expanduser("~/.claude.json")
try:
    cfg = json.load(open(p))
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
cfg.setdefault("mcpServers", {})
cfg["mcpServers"]["browser-use"] = {
    "command": os.path.expanduser("~/.iss/venv/bin/browser-use"),
    "args": ["--mcp", "--headed"]
}
json.dump(cfg, open(p, "w"), indent=2)
print(f"Wrote MCP entry to {p}")
PY
```

Tell the user to **restart Claude Code** (close + reopen the workspace) so the MCP loads.

## Step 8: Capture a Groq API key (optional)

Already covered in the main SKILL.md. Save to `~/.iss/.env` with mode 600.

## Common failures

- **"command not found: brew" after install** ... the installer prints final instructions about adding brew to PATH. Run them, or restart the terminal.
- **"No module named 'uvx'"** ... `uv` wasn't installed via brew. Do step 2 again.
- **`browser-use install` fails** ... usually a network issue. Try again.
- **`browser-use doctor` fails on `network`** ... corporate VPN or firewall. The user has to figure out their network situation.
