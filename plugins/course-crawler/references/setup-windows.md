# Setup on Windows

This reference walks through `setup` on Windows. Two paths exist:

- **Native Windows** (PowerShell + winget). The path described here.
- **WSL2 + Ubuntu**: follow `setup-mac.md` instead, but inside the WSL shell.

If the user mentions WSL, route them to the Mac/Linux reference. If they say "just Windows" or aren't sure, walk them through native Windows here.

## Variables

- `$ISS_HOME` ... `$env:USERPROFILE\.iss`
- `$VENV` ... `$ISS_HOME\venv`

## Step 1: Install winget (almost always already present)

Check: in PowerShell, run `winget --version`. On Windows 10 21H2+ and all Windows 11 it's pre-installed. If missing, the user installs the **App Installer** from the Microsoft Store.

## Step 2: Install Python 3.13, ffmpeg, yt-dlp, uv

```powershell
winget install -e --id Python.Python.3.13
winget install -e --id Gyan.FFmpeg
winget install -e --id yt-dlp.yt-dlp
winget install -e --id astral-sh.uv
```

After each install, the user may need to **open a new PowerShell window** for PATH changes to take effect.

Verify:

```powershell
python --version    # should print 3.13.x
ffmpeg -version
yt-dlp --version
uv --version
```

## Step 3: Create the per-user virtualenv

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.iss"
python -m venv "$env:USERPROFILE\.iss\venv"
& "$env:USERPROFILE\.iss\venv\Scripts\python.exe" -m pip install --upgrade pip
```

## Step 4: Install Python deps

```powershell
& "$env:USERPROFILE\.iss\venv\Scripts\pip.exe" install `
  browser-use `
  faster-whisper `
  trafilatura `
  httpx `
  websockets
```

Backtick (`` ` ``) is the line continuation character in PowerShell.

## Step 5: Download Chromium for browser-use

```powershell
& "$env:USERPROFILE\.iss\venv\Scripts\browser-use.exe" install
```

Pulls Chromium into `%USERPROFILE%\AppData\Local\ms-playwright\`.

## Step 6: Verify

```powershell
& "$env:USERPROFILE\.iss\venv\Scripts\browser-use.exe" doctor
```

## Step 7: Wire the MCP into Claude Code

Claude Code's user config on Windows is `%USERPROFILE%\.claude.json`. Edit it with Python (same approach as Mac):

```powershell
& "$env:USERPROFILE\.iss\venv\Scripts\python.exe" -c @"
import json, os
p = os.path.expanduser('~/.claude.json')
try:
    cfg = json.load(open(p))
except (FileNotFoundError, json.JSONDecodeError):
    cfg = {}
cfg.setdefault('mcpServers', {})
cfg['mcpServers']['browser-use'] = {
    'command': os.path.expanduser('~/.iss/venv/Scripts/browser-use.exe'),
    'args': ['--mcp', '--headed']
}
json.dump(cfg, open(p, 'w'), indent=2)
print(f'Wrote MCP entry to {p}')
"@
```

Tell the user to **restart Claude Code**.

## Step 8: Groq API key (optional)

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.iss"
Set-Content -Path "$env:USERPROFILE\.iss\.env" -Value "GROQ_API_KEY=<their-key>"
```

(Windows doesn't have Unix mode bits ... no chmod equivalent. Users on shared machines should be aware the file is readable by other admin accounts.)

## Common failures

- **"python is not recognized"** ... PowerShell window opened before the winget install completed. Close + reopen PowerShell.
- **ffmpeg silently doesn't work after winget install** ... the binary lands in a versioned subfolder. The `Gyan.FFmpeg` package adds it to PATH automatically but only for new shells.
- **"This script can't be loaded because running scripts is disabled"** ... PowerShell execution policy issue. Run as user: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
- **browser-use crashes on Windows with "Permission denied"** ... antivirus is sandboxing Chromium. User needs to exclude `%USERPROFILE%\.iss\` from AV scanning.
- **Path separators**: yt-dlp can be picky on Windows with paths containing spaces. Always quote paths.
