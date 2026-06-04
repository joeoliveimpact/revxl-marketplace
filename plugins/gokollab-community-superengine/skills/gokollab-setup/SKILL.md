---
name: gokollab-setup
description: First-run installer + setup interview for the GoKollab Community Superengine plugin. Use to provision a NEW coach/client to run the clientclub community automations — turns on bypass permissions, detects OS (Windows/Mac), checks AND installs dependencies (Node, Python, gws, a browser MCP) plus the bundled clientclub binary, drives a guided one-click login to capture their clientclub token with no terminal use, discovers + confirms their community channel map, runs the "ask the coach" interview to build onboarding-config.json, then self-tests. Triggers — "set up the community superengine", "install the plugin", "get me set up", "/gokollab-setup". Recurring daily health checks use fathom-revxl-setup verify, not this.
---

# gokollab-setup

First-run provisioning for a new community operator. Claude runs everything; the client only (1) flips one toggle and (2) logs in once. No terminal commands typed by the client. Writes their own credentials + a filled `onboarding-config.json`, then proves it works.

> **Portability rule (non-negotiable):** every community-specific value — `locationId`, `origin`, Firebase `apiKey`, channel ids — comes from THIS operator's login/discovery. Never carry over another community's location id, subdomain, or channel ids (including any shipped in `*.example` files). Reusing them is the #1 way to silently automate the wrong community.

## Phase 0 — Bypass permissions (FIRST)
So Claude can run setup without prompting a non-technical user on every step:
- **Claude Code desktop → Settings:** enable bypass-permissions mode.
- **Chat textbox:** flip the bypass-permissions toggle (the yellow chip, bottom-left).
Confirm both are on before continuing. If the client won't enable it, fall back to approving each step manually (slower, but works).

## Phase 1 — Detect OS
Windows vs Mac. Set per-OS binary path (`config.json#clientclubBinary`) + install commands. Record to a setup-state scratch note.

## Phase 2 — Dependencies: check + INSTALL (not just check)
For each: detect → if missing, install (OS-branched) → re-verify. Report a table.

| Dep | Windows | Mac |
|---|---|---|
| Node LTS | `winget install OpenJS.NodeJS.LTS` | `brew install node` |
| Python 3 | `winget install Python.Python.3.12` | `brew install python` |
| gws CLI | `npm i -g @googleworkspace/cli` | same |
| clientclub binary | **bundled** at `cli/bin/clientclub-windows-amd64.exe` | `cli/bin/clientclub-darwin-{arm64,amd64}` → `chmod +x` + clear Gatekeeper quarantine |
| Browser MCP | superpowers-chrome `use_browser` — install the MCP **and** connect its Chrome extension; verify with one `use_browser` navigate | same |

The browser MCP is the only interactive install (the client connects the Chrome extension once) — walk them through it and confirm with a test navigation before Phase 3.

## Phase 3 — Guided login → capture token (no terminal)
1. Ask the client for their community URL (e.g. `https://<their>.app.clientclub.net`) — or detect from their GHL.
2. `use_browser` `navigate` → that login URL. Tell the client: **"Log in in the window that opened, then tell me you're in."** (One click for them.)
3. After they confirm, `use_browser` `eval` to read the Firebase auth from localStorage:
   ```js
   (()=>{const k=Object.keys(localStorage).find(x=>x.startsWith('firebase:authUser:'));
   if(!k)return JSON.stringify({error:'not logged in'});
   const v=JSON.parse(localStorage.getItem(k));
   const rt=(v.stsTokenManager&&v.stsTokenManager.refreshToken)||v.refreshToken;
   return JSON.stringify({apiKey:k.split(':')[2],uid:v.uid,refreshToken:rt});})()
   ```
4. **Persist** `refreshToken` → `~/.config/clientclub-pp-cli/refresh-token.txt` (UTF-8, **no BOM, no trailing newline**). Note the `apiKey` (use it in the token helper if it differs from the default).
5. **Write `config.toml`** with the mandatory headers but THIS client's values: `channel=APP`, `source=PORTAL_USER`, `version=2023-02-21`, `x-location-id=<their locationId>`, `origin=<their community URL>`, `x-app-version=web`, `x-platform-details=web`. (Get `locationId` from the portal/`users` discovery in Phase 4 — write config.toml after you have it, or backfill.)
6. **Mint + verify:** run the token helper → set `CLIENTCLUB_COMMUNITY_TOKEN_ID` (NOTE: the helper's header comment says `CLIENTCLUB_TOKEN_ID` — that's a doc bug; the binary reads `CLIENTCLUB_COMMUNITY_TOKEN_ID`) → `doctor` → confirm **Auth ✓ / API ✓**.

## Phase 4 — Discover + confirm community map
1. `users <loc>` → their group(s) → `groups channels list <loc> <grp> --json`.
2. Present the discovered map (public channels; the `{Name} - 1:1` private pattern) and ask: **"Is this your community? Anything mislabeled?"**
3. Write the `community` layer of `onboarding-config.json` (locationId, groupId, publicChannels[], privateChannelNamePattern).

## Phase 5 — Setup interview ("ask the coach")
Run the interview in `../onboard-member/CONFIG-SCHEMA.md` (steps 2–7): intro channel → group-call channel → tiers → per-tier GHL tag + recipe (1:1 channel? gated channels? seed call post? welcomes?) → welcome-copy mode (rotating scripts vs framework). Write `purposes`, `tierMap`, `tierRecipes`, `welcomeCopy`. Result: a fully-filled `onboarding-config.json`.

## Phase 6 — Self-test
1. `fathom-revxl-setup verify` (or a single read) → green.
2. Offer a **`--dry-run` `onboard`** on a test member — shows the exact request sequence, makes **no** writes — so the client sees it work safely.
3. Final readiness table: deps ✓ · auth ✓ · map confirmed ✓ · config filled ✓ · dry-run ✓.

## Outputs
- `~/.config/clientclub-pp-cli/refresh-token.txt` + `config.toml` (client-specific)
- `onboarding-config.json` (filled, both layers)

## Common pitfalls
- **Another community's values leaking in** — config.toml + the community map must be THIS operator's. The portability rule above.
- **Firebase apiKey assumed** — read it from the localStorage key, don't hardcode a fixed one.
- **BOM / newline in refresh-token.txt** — write UTF-8 no-BOM, trimmed (`[IO.File]::WriteAllText(... ,[Text.UTF8Encoding]::new($false))`).
- **Env var name** — `CLIENTCLUB_COMMUNITY_TOKEN_ID` (helper comment is wrong).
- **Browser MCP not connected to the client's real Chrome** — the login + localStorage read must happen in the browser where they actually log in.

## References
- `../_fathom-revxl-shared/pipeline.md` — token mint (§1), commands (§2), PS/BOM traps (§3,§7)
- `../onboard-member/onboarding-config.example.json` + `CONFIG-SCHEMA.md` — config shape + the interview
- `../fathom-revxl-setup/SKILL.md` — the recurring `verify` smoke test (reused in Phase 6)
- `use_browser` MCP (`action:"eval"`) — login + localStorage token extraction
