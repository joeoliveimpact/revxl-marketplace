---
name: meta-ads-superengine:meta-ads-ops-setup
description: Connects Claude to Ads Manager — the client path is Meta's hosted official Ads MCP with OAuth (no developer setup; the connector grants the full tool surface, write-safety is enforced server-side per ad account plus behavioral read-only), the operator path is the official Meta Ads CLI with a System User token. Paused-first doctrine and manual number-pasting stays first-class forever. Trigger phrases include "connect ads manager", "ops setup", "hook up my ad account", "connect meta".
---

# meta-ads-ops-setup — the cockpit hookup

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #22.
Source doctrine: the Cockpit Map (distilled from the developer repo corpus, 07.07.26). A connection is
an ENHANCEMENT — every ops skill works on pasted numbers without one.

## Load
- shared refs
- `.superengine` marker (connections block), platform (Desktop vs Code)

## Prereq (E0)
`setup` done. Missing → setup.

## Steps

**1. Pick the path by who's driving:**

| Path | Who | What | Auth |
|---|---|---|---|
| **A1. Custom connector** (client primary, verified 07.21.26) | clients (consumer-doable) | Claude Desktop → Settings → Connectors → Add custom connector → `https://mcp.facebook.com/ads` | OAuth with the coach's own Meta login — NO developer app |
| **A2. Directory / own-app listing** (live-check, beta) | clients | same hosted MCP if/when it surfaces in the connector directory | OAuth, coach's Meta login |
| **B. Official Meta Ads CLI** | operator (Joe-assisted) | Python CLI built for AI agents, full Claude Code control | System User access token (scope + expiry set at mint) |

**Account scope at sign-in (the highest-leverage guardrail — say this BEFORE
the coach clicks connect):** the OAuth grant asks which ad accounts to
expose. Select ONLY the account the coach actually advertises from. Do NOT
accept **"all accounts and future accounts"** — it enrolls every account
that Meta login can reach AND auto-enrolls any account created later, with
no further prompt. An account never granted cannot be written to by any
means, which makes this stronger than every server-side control below.
**Verified 07.22.26: the grant is sticky** — reconnecting the connector
reuses the existing authorization and does NOT re-show this screen, so a
too-broad grant cannot be narrowed by reconnecting. Getting it right on the
first connect is the whole game; remediation for an existing over-grant is
in step 3.

Known quirk: the hosted MCP's OAuth has a localhost-redirect issue in some
clients → prefer Claude Desktop for path A; path B runs natively in Claude
Code. Live-check the connect surface at run time (beta product — buttons
move). If OAuth dead-ends in `ERR_TOO_MANY_REDIRECTS` on business.facebook.com,
remediation in order: (1) navigate directly to `business.facebook.com/settings`
— the bare domain loops, the full /settings URL clears it; then fallbacks —
(2) log into facebook.com first then retry; (3) try an incognito window;
(4) clear facebook.com cookies.

**2. Write-safety doctrine (the primary guardrail — FULL strength at every
teach level):**
- **(a) The truth:** the connector grants Claude the FULL tool surface at
  sign-in (reads, insights, AND writes) — there is NO read-only *permission*
  scope to pick. But there IS an *account* scope, chosen at sign-in (above),
  and it is the strongest guardrail available: an account never granted is
  unreachable and unwritable by any path. So write-safety IS partly a
  sign-in choice — the account grant — plus the controls below.
- **(b) Server-side gate (per ad account):** walk the coach to Business
  Suite → Settings → Integrations → **"Ads MCP server"** → **Ad accounts**
  tab, and confirm the per-account **"Actions allowed"** column shows
  **"-"** (no actions allowed) — or their intended write tier. Default "-"
  = the account can't be written to no matter what the tool surface
  exposes. Meta's own wording on that panel, worth quoting to the coach:
  *"Connected AI agents can view your ad account and catalog data, even if
  they can't take actions."* — i.e. this gate governs WRITES only; reads are
  never gated by it. (Panel verified live 07.22.26. A **Catalogs** tab sits
  beside Ad accounts and governs the catalog write tools separately — check
  it too if the coach has catalogs.)
- **(c) Allow-once habit:** on any write-approval prompt, always choose
  **"allow once"**, never "always allow".
- **(d) Behavioral read-only:** in v1 Claude invokes read/insights tools
  ONLY. Write graduation ships at **NTB-10** — not on coach request, ever;
  until then the write tools exist in the surface but are never called.
- **Billing/financial:** never enabled — behavioral (Claude never invokes a
  financial tool) and server-side (financial toggles stay off). Not a scope
  tier to withhold; a line that stays uncrossed.

**3. Verify the connection:** pull account list + one campaign read; record
result honestly in the marker (`connections.meta_mcp` / `meta_cli`:
state + scope + date). Failed/declined → recorded as absent, no nagging.
**Enumerate every visible ad account** via `ads_get_ad_accounts` — the
connector exposes ALL accounts granted at sign-in — and read `business_id`,
`is_ads_mcp_enabled`, and `has_payment_method` on each. Flag any account
where `business_id` is empty AND `is_ads_mcp_enabled` is true: it is
reachable by the connector but **does not appear in the Business Suite
"Ads MCP server" table at all** (verified live 07.22.26 — absent even on a
direct ID search), so it can NEVER be given an "Actions allowed" setting.
Reachable, but ungovernable. If `has_payment_method` is also true, say
plainly that it can spend real money with no server-side gate. Give it an
explicit warning + a no-touch line ("Claude will not act on this account").
Remediation, in order: (1) attach it to a business so it becomes governable,
(2) remove its access from the Meta login, or (3) revoke the integration's
authorization entirely and reconnect with a narrower account grant — note
that a plain reconnect does NOT re-prompt the account screen (step 1), so
only a full revoke-then-reconnect can narrow an existing grant.
Record `accounts_visible` (the id list) and a per-account `guardrail_note`
in the marker connections block — mirror the live shape (`accounts_visible:
[ids]`, `guardrail_note: "<acct> has no owning business — ungovernable, not
listed in the Ads MCP server table"`).

**4. Token hygiene (path B):** System User token minted with expiry and
narrowest scope; stored per Meta's guidance, never pasted into chat logs.

## Terminal paths — inline blocks (routing.md grammar)

**Connected (E20):** preamble names path + write-safety posture + what just
got unlocked, then (ranked by whether a campaign is live — #1 must be
actionable NOW):

**Next moves**
*If launched (`launched_at` set):*
1. See it work — pull today's live numbers into your 60-second brief. Say: "daily brief"  ← start here
2. Run a full read-only health check of the account. Say: "review my ads"

*If not launched yet, but you have past/current campaign data to import:*
1. See what your past/current numbers say — performance-review in import mode. Say: "review my ads"  ← start here
2. Back to what you were doing. Say: "what's next"

*If not launched and nothing importable (never ran ads through the plugin, no history):*
1. Pick up the journey where you left off. Say: "what's next"  ← start here

**Next moves — declined / can't connect now**
Nothing is lost — pasting numbers works forever:
*If launched (`launched_at` set):*
1. Keep running on manual paste — every ops skill takes a copy-paste or CSV export. Say: "daily brief"  ← start here
2. Retry the hookup whenever. Say: "connect ads manager"

*If not launched yet:*
1. Pick up the journey where you left off — manual paste stays first-class the whole way. Say: "what's next"  ← start here
2. Retry the hookup whenever. Say: "connect ads manager"

## Teach mode
In `new`: plain-English-first — MCP deep-glossed ("a live hookup between
Claude and Ads Manager — behavioral read-only means Claude only looks, never
touches"); OAuth explained as "signing in with your own Meta account, no
passwords shared"; the write-safety doctrine gets "what this means for you"
per plank (especially the "Actions allowed = -" check). In `learning`: gloss
MCP/write-gate first use. In `pro`: path table + write-safety doctrine, terse.

## Guardrails
- v1 invokes NO write tools (behavioral read-only); the connector still
  grants the full surface, so server-side "Actions allowed" stays "-" per
  account. Write graduation ships at NTB-10, not on coach request;
  paused-first + confirm-every-write doctrine inherited NOW (premortem #12).
- Manual-paste is first-class, never framed as a fallback.
- Beta surface → live-check instructions; never assert from memory.
