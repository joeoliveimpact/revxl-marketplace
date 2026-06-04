---
name: fathom-revxl-setup
description: Use when provisioning or health-checking a host to run the Fathom→REVXL skill suite — e.g. "set up the Fathom skills on Orion", "audit dependencies for the deep-post skills", "can this machine run the clientclub skills", "check clientclub/Fathom auth", "what's missing to deploy these to Hermes", or the daily cron's pre-run auth smoke test. Covers OS/arch detection, CLI/binary/MCP/token checks, and per-platform install + auth remediation.
---

# fathom-revxl-setup

Audit a host for everything the Fathom→REVXL suite needs, report present/missing, and give exact per-platform remediation. Run this FIRST when standing the suite up on a new machine (especially Orion/Hermes, whose OS may differ from Joe's Windows box).

## Modes
- **`audit`** (default) — full dependency + auth report with remediation. Run when provisioning a host.
- **`verify`** — fast auth/connectivity smoke test only (token mints, `doctor` OK, Fathom cookie 200, Fathom MCP responds). Used by the daily cron pass before it does work.

## Procedure
1. **Detect OS + arch** (`windows` / `linux` / `darwin-arm64` / `darwin-amd64`). This selects the binary + token-helper rows below. See `../_fathom-revxl-shared/pipeline.md` §0.
2. **Load `config.json`** — confirm it exists and every path resolves on THIS host. Missing → copy `config.example.json` and fill the OS-matching values.
3. **Run each check** in the table. Mark ✅/❌.
4. **For each ❌**, emit the remediation line.
5. **Auth smoke test** — mint token (§1), `<clientclubBinary> doctor`, Fathom cookie test call, Fathom MCP `list_meetings`.
6. **Report** a checklist + a remediation section. In `verify` mode, only step 5 + a pass/fail line.

## Dependency checklist

| Check | How (per detected OS) | Why | If ❌ — remediation |
|---|---|---|---|
| clientclub binary | `config.clientclubBinary[os]` exists + runs `version` | posts to REVXL | Copy the matching `build/clientclub-{linux-amd64,darwin-arm64,darwin-amd64}` (or `.exe`) to the configured path. POSIX: `chmod +x`. Static Go, no runtime deps. |
| `doctor` passes | `<binary> doctor` → Auth ✓ API ✓ | auth+connectivity | If Auth ✗ → token/refresh issue (see refresh token row). "Cache stale" WARN is cosmetic. |
| python3 | `python3 --version` | POSIX token helper + JSON parsing | Linux: `apt install python3` / Mac: preinstalled or `brew install python`. (Windows path uses the .ps1 helper — python not required there.) |
| curl | `curl --version` (`curl.exe` on Win) | Fathom share-URL fetch | Win10+/Mac/most Linux ship it. Linux minimal: `apt install curl`. |
| node / npx | `node --version`, `npx --version` | gws CLI + Playwright re-auth | Install Node LTS (nodejs.org / nvm / `brew install node`). |
| gws CLI | `gws drive --help` | Drive transcript lookup | `npm i -g @googleworkspace/cli` (then authenticate via its keyring). |
| refresh token | `config.refreshTokenPath` exists + token helper mints an idToken | Firebase auth | Run `/har-capture` Phase 2 against clientclub.net to obtain; save to `~/.config/clientclub-pp-cli/refresh-token.txt`. |
| `~/.config/clientclub-pp-cli/` writable | write test | token rotation persists here | `mkdir -p` + ensure writable. |
| Fathom storage-state | `config.fathomStorageState` exists; test call returns 200 | share-URL auth (~7d cookie) | `npx playwright open --save-storage="<path>" https://fathom.video` → log in → close. |
| Fathom MCP | `list_meetings` returns | summaries + recording lookup | Configure the Fathom MCP server in the host agent's MCP settings (server id `2c2a6a6e-…`). Can't be installed by a skill. |
| channel-map | `config.channelMap` exists + parses | channel/post resolution | Copy `channel-map.json` from the source workspace, or regenerate via `groups channels list`. |

## Orion / Hermes wiring (deployment reference)

The suite is scheduler-agnostic. Two triggers:
- **Webhook (real-time):** n8n (or Fathom) POSTs on a new recording → host agent invokes `create-fathom-deep-post <recording_id>` (group) or `add-1on1-call-to-history <client> <recording_id>` (1:1), or `update-client-1on1-history webhook <recording_id>` to classify+dispatch.
- **Daily cron audit:** scheduled → `fathom-revxl-setup verify` → if green, `update-client-1on1-history daily` (reconcile last window, dispatch anything missing) → notify (Telegram/Obsidian — channel per host).

**Deploying to a new host:** copy `.claude/skills/{fathom-revxl-setup, create-fathom-deep-post, add-1on1-call-to-history, update-client-1on1-history, _fathom-revxl-shared}/` as a set → copy `config.example.json` to `config.json` and fill OS values → run this skill in `audit` mode → remediate ❌s → run a single round-trip (one deep post or one 1:1 entry) before enabling the cron.

**Known unknowns for Orion** (confirm at audit time, were undocumented as of 05.28): exact OS/arch, Tailscale/network reachability to clientclub + Fathom + Google, scheduler choice (cron/systemd/Hermes-native), and how failures surface back to Joe.

## Common mistakes
- Treating "Cache stale" as a failure — it's cosmetic; only Auth/API matter in `doctor`.
- Assuming the Windows clientclub.exe runs on Linux — pick the arch-matched binary from `build/`.
- Forgetting the Fathom MCP must be configured on the host (not installable by the skill).

## References
- `../_fathom-revxl-shared/pipeline.md` — platform detection, token mint, auth
- `../_fathom-revxl-shared/config.json` / `config.example.json` — paths + IDs
