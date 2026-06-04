---
name: onboard-member
description: Use when onboarding a new member into the GoKollab / clientclub community by tier — e.g. "onboard Sarah Lee", "onboard [name]", or a webhook on a new approved member. Approves their pending join request, reads their tier from GoHighLevel (tag/custom field via the GHL MCP), then runs that tier's recipe from onboarding-config.json — adds them to tier private channels, creates their own private 1:1 channel (if the tier gets one), seeds + features their call-recording post, and posts welcomes in their private channel + a community channel. NOT for posting group/1:1 call recordings → use create-fathom-deep-post / add-1on1-call-to-history. Config is built by the setup interview (see CONFIG-SCHEMA.md).
---

# onboard-member

Onboard ONE member end-to-end, driven by their **tier**. The tier comes from GoHighLevel (a tag/custom field, read via the GHL MCP); the per-tier **recipe** lives in `onboarding-config.json` and is filled by the setup interview. This skill only **orchestrates existing clientclub CLI commands** — it adds no new endpoints.

## When to use
- "Onboard {member}" — they're sitting in the member-request queue and need to be let in + set up by tier.
- Webhook carrying `{contactId}` (or name) for a new join request.
- **Not** for call-recording posts → `add-1on1-call-to-history` (1:1) / `create-fathom-deep-post` (group). This skill *creates + pins the initial* call-recording post; that skill keeps it updated.

## Inputs
- `member` — name (resolved via GHL MCP) or `contactId` directly. Optional `tier` to skip tag lookup.
- Reads `onboarding-config.json` (community map + tier recipes) and shared `_fathom-revxl-shared/config.json` (binary paths, ids).

## Preconditions
- `onboarding-config.json` exists + confirmed (run the setup interview first — CONFIG-SCHEMA.md).
- GHL MCP available (tier read). clientclub CLI authed (token minted; `doctor` Auth ✓).

## Procedure
1. **Platform + token + config.** Detect OS, load both configs, mint token, `doctor`. `../_fathom-revxl-shared/pipeline.md` §0–1.
2. **Resolve member → contactId + tier (GHL MCP).** `mcp__ghl__search_contacts` by name → `{contactId, tags, customFields}`. >1 match → STOP, ask which. No match → STOP, ask. Map tag → tier via `config.tierMap`. None/ambiguous → STOP, ask the coach which tier. Load `config.tierRecipes[tier]`.
3. **Approve the join request (recipe step 1).** `groups users list-members <loc> <grp> --member-status Requested --json` → find the entry whose `contactId` matches → read its **`userId`** (NOT the contactId). Then `groups users approve-member-request <loc> <grp> <userId> --status Active`. Already Active / not in queue → skip (idempotent), note it.
4. **PREVIEW the full plan, then confirm.** Before any write, print: tier, channels to join, private channel to create (name), posts to make (titles). Wait for go unless `--yes`. (Surgical/destructive guardrail — same discipline as `feedback_confirm_before_destructive_overwrite.md`.)
5. **Private channel (if `recipe.createPrivateChannel`).** Idempotency: scan the community map for an existing `"{First Last} - 1:1"` → reuse its id; else create:
   `groups channels create <loc> <grp> --name "{First Last} - 1:1" --visibility PRIVATE --icon "{recipe.privateChannelIcon}"`. Parse new `_id` via regex `"_id"\s*:\s*"([^"]+)"` (pipeline §3 — don't trust ConvertFrom-Json).
6. **Add member to channels.** Public channels are skipped (visible to all — adding is unnecessary). Only PRIVATE access:
   - Their private channel: `groups channels add-users-to <loc> <grp> <privChn> --stdin` ← `[{"contactId":"<cid>","role":"MEMBER","notify":true}]`.
   - Each `recipe.gatedPrivateChannels` (resolve purpose/name → id from the map), same shape.
7. **Seed + feature the call-recording post (if `recipe.seedCallRecordingPost`).** In the private channel: `create-post` the initial "Call History" post (seed body per `add-1on1-call-to-history` / `1on1-format.md`; empty-history header is fine) → parse `postId` → `update-post … --stdin` ← `{"action":"PIN_TO_CHANNEL"}` to feature it. Ongoing updates are `add-1on1-call-to-history`'s job, not this skill's.
8. **Welcome posts.**
   - Private (if `recipe.welcomePrivate`): `create-post` in the private channel with welcome copy resolved from `config.welcomeCopy` — mode `rotating_scripts` → take the next script from the pool and advance the rotation index; mode `framework` → write within `config.welcomeCopy.framework` guidelines.
   - Community intro (if `recipe.welcomeCommunity`): `create-post` in `config.community.purposes.intro_welcome` introducing the member + prompting them to say hello.
9. **Report.** Approved ✓ · channels joined · private channel id · post ids/links. Note any skipped (idempotent) steps.

## Quick reference (all verified syntax)
```
groups users list-members <loc> <grp> --member-status Requested --json     # find userId
groups users approve-member-request <loc> <grp> <userId> --status Active
groups channels create <loc> <grp> --name "<Name> - 1:1" --visibility PRIVATE --icon "<emoji>"
groups channels add-users-to <loc> <grp> <chn> --stdin   # [{"contactId","role":"MEMBER","notify":true}]
groups channels create-post <loc> <grp> <chn> --stdin    # {"title","content"}
groups channels update-post <loc> <grp> <chn> <postId> --stdin   # {"action":"PIN_TO_CHANNEL"}
```
Posting bodies go via stdin as UTF-8 **no-BOM**; on Windows pipe through `cmd /c` (pipeline §3 BOM trap).

## Common mistakes
- **Confusing `userId` (approve) with `contactId` (add-to-channel).** approve-member needs the membership `userId` from `list-members`; add-users-to needs the GHL `contactId`. They differ.
- **Adding to public channels** — unnecessary (public = everyone sees). Only add PRIVATE access.
- **Skipping the preview** before writes, or **duplicating** a private channel / posts on re-run — always idempotency-check the map + existing posts first.
- **BOM on stdin** (Windows) → Go JSON parser rejects it. Use `cmd /c` + `[IO.File]::WriteAllText($tmp,$payload,[Text.UTF8Encoding]::new($false))`. pipeline §3 / §7.
- **Parsing `_id` with ConvertFrom-Json** — use the regex (pipeline §3 trap #2).
- **Inventing channel ids** — every id comes from the discovered, coach-confirmed community map. Never hardcode.

## References
- `../_fathom-revxl-shared/pipeline.md` — auth (§0–1), command reference + stdin/BOM (§2–3), PS traps (§7)
- `./onboarding-config.example.json` — two-layer config shape (community map + tier recipes)
- `./CONFIG-SCHEMA.md` — field-by-field + the setup-interview question set that builds the config
- `../add-1on1-call-to-history/SKILL.md` + `../_fathom-revxl-shared/1on1-format.md` — call-recording post format + ongoing updates
- GHL MCP (`mcp__ghl__search_contacts` / `get_contact`) — tier (tag/custom field) read
