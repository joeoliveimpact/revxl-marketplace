# Fathom → REVXL Pipeline (platform-neutral)

Shared mechanics for all four Fathom→REVXL skills. Cited by each SKILL.md; not loaded unless a skill needs the detail. Read the section you need.

Validated 05.26–05.28.26 across 21 group deep posts + multiple 1:1 history updates.

---

## 0. Platform detection (run first)

Detect OS + arch, then pick the matching `clientclubBinary` and `tokenHelper` from `config.json`.

- **Windows** → PowerShell branch. `clientclubBinary.windows`, `tokenHelper.windows` (.ps1).
- **Linux** → POSIX branch. `clientclubBinary.linux`, `tokenHelper.posix` (.sh). Needs `curl` + `python3` in PATH.
- **macOS** → POSIX branch. `clientclubBinary.darwin-arm64` or `-amd64` by `uname -m` (`arm64` vs `x86_64`).

`~` in config paths expands to the home dir. Resolve `<workspace>` placeholders to the skill's workspace root.

Every command below is given in BOTH branches. Use the one matching the detected OS.

---

## 1. Mint the clientclub token (every invocation)

The token is a 60-min Firebase idToken minted from the refresh token at `config.refreshTokenPath` (`~/.config/clientclub-pp-cli/refresh-token.txt`). Refresh tokens don't expire until revoked.

**Windows (PowerShell):**
```powershell
$env:CLIENTCLUB_COMMUNITY_TOKEN_ID = & '<tokenHelper.windows>'
```
**POSIX (bash):**
```bash
export CLIENTCLUB_COMMUNITY_TOKEN_ID="$(<tokenHelper.posix>)"
```

Both emit the idToken to stdout and the clientclub binary reads `$CLIENTCLUB_COMMUNITY_TOKEN_ID`. Then smoke-test:
```
<clientclubBinary> doctor      # Auth ✓ + API ✓ are load-bearing; "Cache: stale" WARN is cosmetic
```
If Auth ✗ / API ✗ → refresh token revoked → re-run `/har-capture` Phase 2 to get a new one. Do not proceed.

---

## 2. clientclub command reference

Constants: `locationId`, `groupId`, channel IDs from `config.json` / `channel-map.json`.

| Action | Command (positional args) |
|---|---|
| Create post | `groups channels create-post <loc> <grp> <chn> --stdin --agent` (body on stdin) |
| Update/patch post | `groups channels update-post <loc> <grp> <chn> <postId> --stdin --agent` |
| List pinned posts | `groups channels list-pinned-posts <loc> <grp> <chn> --json` |
| List posts (full content) | `groups channels list-posts <loc> <grp> <chn> --json --no-input --no-color` |
| Get one post (full content) | `groups posts get <loc> <grp> <postId> --json` |
| List channels | `groups channels list <loc> <grp> --json` |

**Body JSON shapes:**
- create-post: `{"title":"…","content":"<html>"}`
- update-post: `{"action":"UPDATE_POST","post":{"id":"<postId>","title":"…(optional)","content":"<html>"}}`

**`--agent` strips the `content` field on reads** — for reading post content use `--json` WITHOUT `--agent` (or `groups posts get … --json`). `--agent` is fine for writes.

**Older pinned posts missing from `list-posts`** (channels with >25 posts): use `groups posts get <loc> <grp> <postId> --json` directly (URL has no `/channels/` segment).

---

## 3. Posting via stdin (the BOM trap)

Write the body JSON to a temp file as **UTF-8 no-BOM**, then pipe it in.

**Windows:** native PowerShell pipe adds a BOM the Go JSON parser rejects → must go through `cmd /c` with an absolute exe path:
```powershell
[IO.File]::WriteAllText($tmp, $payload, [Text.UTF8Encoding]::new($false))
cmd /c "`"<clientclubBinary>`" groups channels create-post <loc> <grp> <chn> --stdin --agent < `"$tmp`""
```
**POSIX:** native redirect is fine (no BOM):
```bash
printf '%s' "$payload" > "$tmp"   # or python json.dump
"<clientclubBinary>" groups channels create-post <loc> <grp> <chn> --stdin --agent < "$tmp"
```

Parse the new `_id` from the response with regex `"_id"\s*:\s*"([^"]+)"` (see trap #2 — don't trust ConvertFrom-Json for the response).

---

## 4. Fathom data

### 4a. Summary (MCP — platform-agnostic)
`mcp__2c2a6a6e-d527-497e-88a3-20a3b4670314__get_meeting_summary` with `recording_id` → markdown summary with per-bullet `?tab=summary&timestamp=N` deep-links. Find `recording_id` via `…list_meetings` (filter by date window; match call by URL slug or title).

### 4b. Share URL (curl + regex)
The shareUrl lives in the call-detail Inertia JSON; fetch with the `_fathom_session` cookie from `config.fathomStorageState`.

Build the cookie header once: join all `fathom.video` cookies from storage-state.json as `name=value; …`. Then:
```
curl -s -o <tmp> -w "%{http_code}" --max-redirs 0 -H "x-inertia: true" -H "Cookie: <cookieHeader>" "https://fathom.video/calls/<slug>"
```
(`curl.exe` on Windows, `curl` on POSIX.) On 200, regex the raw body: `"universalShareable":\s*\{[^}]*"shareUrl"\s*:\s*"([^"]+)"` (fallback `"shareUrl"\s*:\s*"([^"]+)"`).

**Cookie expiry (≈7-day TTL):** 30x redirect or 401 → session expired. Skip the call, queue for re-auth, don't abort. Re-auth: `npx playwright open --save-storage="<fathomStorageState>" https://fathom.video` (log in, close).

---

## 5. Drive transcript resolution

Match a call to its transcript file via `gws drive files list` (cross-platform via Node). PowerShell arg-quoting mangles the JSON `--params` — pass it through `cmd /c` on Windows (POSIX shells are fine).

```
gws drive files list --params '{"q":"<query>","fields":"files(id,name)","pageSize":50}'
```
View URL from a file id: `https://drive.google.com/file/d/<id>/view?usp=sharing`.

**Filename schemes:**
- Backfill (historical): `[{Series}] - Fathom Transcript - {MM.DD.YY}.md` — **sanitized chars**: `/`→`-`, `:`→`-` (e.g. `REVUP Wednesday: Content` → `[REVUP Wednesday- Content]`, `Setting/Sales` → `[… Setting-Sales]`).
- Live n8n (≈May 27+): `{YYYY-MM-DD}_{Series-Hyphenated}_{recording_id}` — `recording_id` is the reliable match key.

**Resolution order:** (1) exact backfill filename; (2) `name contains '{keyword}' and name contains '{date}'` for sanitized variants; (3) drive-wide search by `recording_id`; (4) **fallback** — extract the Drive id from the relevant weekly-index post (group) or existing history entries (1:1), which already pair shareUrl→driveUrl. (5) **graceful-missing** — omit the 📜 link and flag it.

---

## 6. Channel + post resolution

From `config.channelMap` (`channel-map.json`): array of `{name, id, visibility, isAnnouncement}`.

- **Client 1:1 channel:** match `"{Client} - 1:1"`, then bare `"{Client}"` (e.g. Dana Whitfield has no ` - 1:1` suffix), then case-insensitive contains. Apply name aliases (`Dana Scanlon Whitfield` → `Dana Whitfield`).
- **Group Calls channel:** `config.groupCallsChannelId` (`6a149a52d27da139efdbab4d`).
- **Featured Call-History post:** in the client's channel, `list-pinned-posts` → pick the post whose title contains "Call History" (or "1:1"). If none → don't auto-create; queue + ask.

---

## 7. PowerShell 5.1 traps (Windows branch only)

Full reference: memory `feedback_powershell_5_1_api_traps.md`. The five that bite this pipeline:

1. **Cookie-auth GETs:** use `curl.exe`, NOT `Invoke-WebRequest`/`Invoke-RestMethod` (PS re-processes multi-cookie headers → corrupts them).
2. **Nested JSON fields:** regex the raw body, NOT `ConvertFrom-Json` (PS 5.1 silently flattens nested objects on key collision — `universalShareable` disappears).
3. **Reading UTF-8 files:** `[IO.File]::ReadAllText($p,[Text.UTF8Encoding]::new($false))`, NOT `Get-Content -Raw` (defaults to Windows-1252 → corrupts ⚡/📜 emojis on round-trip).
4. **Emojis:** `[Char]::ConvertFromUtf32(0x1F4DD)` for supra-BMP (📝/📜/📞), NOT `[char]`. For multi-codepoint sequences (▶️ = U+25B6+U+FE0F) force the string overload on `.Replace([string]$a,[string]$b)`.
5. **stdin to the Go CLI:** write UTF-8 no-BOM via `[IO.File]::WriteAllText`, pipe via `cmd /c "exe … < file"` with an **absolute** exe path (cmd /c doesn't inherit cwd).

**POSIX equivalents:** native `curl`; `jq` or `python3 -c` for JSON; UTF-8 is the default encoding; native `< file` stdin redirect; emojis are literal in source. None of traps 1–5 apply on Linux/macOS, but the *patterns* (regex-extract the response `_id`, write a temp payload file) stay the same for consistency.

---

## 8. Round-trip discipline (mandatory before bulk)

Before bulk-writing a new format or overwriting any live post: validate ONE end-to-end (API readback + visual UI check), and **back up** any post you overwrite (`groups posts get … --json` → file). Memory: `feedback_round_trip_test_one_first.md`. This is what caught a prior destructive-overwrite incident.
