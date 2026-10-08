# Changelog — higgsfield-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.1.5 — 2026-10-08

### Added

- Spend mod (`hooks/mod/register.ts` + `logic.ts`, registered under `modules` in hooks.json; Claude Code 2.1.287+). The first paid submit in a chat asks the client for that chat's cap ($5 / $10 / $20 / Not now; only Not now refuses the job). A band above the prompt shows the chat's spend against its cap with +$5, ×2, Back to $5 and Details; the Details pane lists the chat's jobs (Open shows a media file inside the folder), spend by model, last 24 h / 7 days, and the balance (Update balance). A reopened chat that already used Higgsfield shows its band again (`bandOnStart`). A cap change is noted to Claude in the chat (`$.session.append`, else `$.ui.log`).
- Ledger: each reservation records its chat (`reserve --session`); `session-cap set|get`; `check`/`status --session` report the chat's spend, cap and headroom. A picked cap is checked against that chat's spend only and ignores the 25%-of-balance rule; with no pick, the rolling 24 h rule decides as before. v0.1.4 ledgers (entries without a session) load and keep counting in 24 h.

### Changed

- Guard: passes the hook event's `session_id` to `reserve --session`; the estimate's price quote uses the same rule, so the band, the quote and the guard show the same figures ("this chat's cap" after a pick, "the 24 h limit" before).
- Guard: refuses any command, or script Claude wrote (`.py`, `.ps1`, `.sh`, at write time and at run time), that sets a session cap. Only the client's band buttons set one.
- The mod never blocks on its own trouble: a closed box, no window to ask in, or an unreadable spend record falls back to the guard's 24 h rule (the band then shows a grey "spend record unavailable" line).
- hf-generate: the "Say first" line mentions the cap box; failure reports send `--plugin-version 0.1.5`.

## 0.1.4 — 2026-10-05

### Changed

- Spend guard trimmed to the money checks (Mac report 10.05.26). It keeps: pricing + the spend cap (allow under, ask over), and the denies for raw api.higgsfield.ai calls, the higgsfield CLI/SDK, other ways into hf_rest (including scripts that mention it), and the guard's own files.
- Over the cap in bypassPermissions now asks instead of denying: a PreToolUse hook's ask is honored in bypass (proven 10.05.26 with a headless bypass run). Only dontAsk, where nobody can be asked, still denies.
- Showing the full prompt and reading the model notes are hf-generate instructions now, no longer guard checks.

### Removed

- The transcript checks `real_call()` and `reviewed()`. On Mac Claude Desktop (Code tab) the tool_use row is written after PreToolUse fires, so every submit was refused (no charge). Selftests R1–R6 and V1–V12 removed; new M1 (no transcript row, or no transcript_path, still allows under the cap).
- The no-look screen guard (hooks.json browser/screen matcher, the no-look flag, selftests N0–N8). `hf_guard.py no-look ...` is a no-op for older setup text. higgsfield-setup step 7 tells Claude in words to keep off the screen while the key is showing.

## 0.1.3 — 2026-10-02

### Added

- Mac support. The spend guard and the no-look guard now run on a Mac: hooks.json adds `sh hooks/hf-guard.sh` beside the Windows `py -3` entry, and `hf_guard.py hook --only-on win32|posix` makes exactly one of them decide per OS (Windows machines with Git can run `sh` too). The launcher finds Python in fixed places, never via PATH, and never runs Apple's `/usr/bin/python3` without the developer tools (no install pop-up). No Python: the plugin's money paths are blocked, setup is not.
- `scripts/find-python.sh`: the Mac twin of find-python.ps1, same approach as the other REVXL plugins: a version check, then `brew install python@3.12` if Homebrew is there, else the client installs from python.org (or from Apple's developer-tools box). Records the interpreter in `higgsfield/.python`.
- higgsfield-setup and hf-generate: a full Mac path (Bash tool, `"$(cat higgsfield/.python)"`, Cmd+V, Keychain key box), replacing the "beta, stop after the quote" note.

### Fixed

- hf_rest selftest G14 passes on Linux/macOS: a real collision must show up across the 10 rounds, not in every round (still exactly 1 POST per round). All selftests pass on Windows and Linux.

## 0.1.2 — 2026-10-02

### Fixed

- Estimate output: `price.ask` now includes the spend cap (the ledger's check, which reserves nothing), so a job over the cap shows `ask: true` / `over_cap` and hf-generate warns the client about the pop-up. Previously it showed `ask: false`. The hook still decides at submit. The hf_rest selftest now uses a temp ledger; new G16.
- Pricing: Seedance 2.5 video-edit uses the x0.6 video-input token rate. Confirmed by billing for three 720p REST edits on 09.30.26 (x0.6 list, x0.7 sale). A 5.5 s edit is now quoted $3.66 (was $6.10); the list price stays the upper bound.

## 0.1.1 — 2026-10-01

### Fixed

- Spend guard: stamps a paid submit only for a real pending tool call (transcript tool_use_id + command, no result yet); a hand-built hook event or runner script is refused. Selftest R1–R6.
- Spend guard: refuses a paid submit unless the model's notes file was read, a prompting or use-case skill was loaded, and every prompt in the request was shown word for word with a client reply after it. Selftest V1–V7.
- Pricing: `hf_rest.py upload` records an MP4's length (stdlib mvhd reader); estimates carry `input_video_s`; Seedance input/edit seconds and Genjutsu are priced on it (rounded up, capped at the table max).
- Pricing: Seedance 2.5 audio_unproven ask dropped (audio on = off, measured 09.30.26); Flare/Sunburst 1k $0.06 and 2k $0.15 ceilings (xhigh/max 2x).
- References: Seedance 2.5 and Genjutsu reach 1080p; Seedance 2.0 uses `<<<image_N>>>`; Kling O3 video-edit marked untested for restyles; Qwen thinking stays on; Hailuo optimizer off for built prompts; LTX aspect ratio must match the start image.
- Codex adversarial review fixes:
  - guarded paths are normalized and resolved (`.config/./…` no longer slips past);
  - `python <script>` is refused when the script mentions the submit script, the guard or the ledger;
  - the whole transcript is read, not the last 8 MB;
  - only successful Read/Skill calls count, for this plugin's own model file;
  - promptless requests still need a description and a reply;
  - `refund not_sent` is refused once a submit used the stamp (new reason `rejected`);
  - clip lengths are no longer rounded down before pricing.
- Known limit: the guard cannot see inside a script Claude writes; a deliberately obfuscated script could still forge approval. Approval held outside the agent's reach is planned for v0.2.

### Added

- `references/video-edit-recipes.md`: shot-type check, add-an-object prompt order, effects on black for compositing, output checks.
- Reference manifest rule (image-prompting, video-prompting, thumbnails, Flare, Kling O3).
- Setup names the two guard habits: plugin on for every folder, no bypass mode.

## 0.1.0 — 2026-09-30

First release (catalog 0.1.70).

### Added

- Plugin scaffold: manifest, README, changelog, MIT license, and the folders later work fills in (`scripts/`, `hooks/`, `skills/`, `references/`, `references/models/`).
