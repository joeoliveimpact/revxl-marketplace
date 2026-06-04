# onboarding-config.json — schema + setup interview

Two layers. **Layer 1 (community)** is auto-discovered then coach-confirmed. **Layer 2 (tierMap / tierRecipes / welcomeCopy)** is built by the setup interview — the "ask the coach" flow. Nothing here is hardcoded by the builder; every value comes from discovery or the coach.

## Layer 1 — `community` (discovered + confirmed)
| Field | Meaning | Source |
|---|---|---|
| `locationId`, `groupId` | The coach's community ids | discovered at login (`users <loc>` / config) |
| `publicChannels[]` | `{id,name,visibility}` for every PUBLIC channel | `groups channels list <loc> <grp>` |
| `privateChannelNamePattern` | Template for per-member 1:1 channels, e.g. `{firstName} {lastName} - 1:1` | confirmed by coach |
| `purposes.intro_welcome` | Channel id where new-member intro posts go | **coach picks** from publicChannels |
| `purposes.group_call_featured` | Channel id holding the featured group-call post | discovered / coach confirms |

> Per-member PRIVATE channels are NOT stored — they're discovered fresh each onboard run (idempotency).

## Layer 2 — `tierMap` (GHL tag → tier key)
Maps a GoHighLevel tag to a tier key. The coach states which tag identifies each tier. `onboard` reads the member's tags via the GHL MCP and looks them up here.

## Layer 2 — `tierRecipes[tierKey]`
| Field | Meaning |
|---|---|
| `label` | Human description |
| `createPrivateChannel` | Does this tier get their own `- 1:1` channel? |
| `privateChannelIcon` | Emoji for the created channel |
| `gatedPrivateChannels[]` | Extra PRIVATE channels (by id/name) this tier joins |
| `seedCallRecordingPost` | Create + pin the initial call-recording post in their private channel? |
| `welcomePrivate` | Post a welcome in their private channel? |
| `welcomeCommunity` | Post an intro in the community intro channel? |

## Layer 2 — `welcomeCopy`
`mode: "rotating_scripts"` → `rotating_scripts.pool[]` of ready scripts + `rotationIndex` (advances each onboard so consecutive members differ).
`mode: "framework"` → `framework.{tone, mustInclude[], mustAvoid[]}` Claude writes within per member.

---

## The setup interview (what the setup skill ASKS the coach)
Run after login, in order. Each answer writes the field above.

1. **Confirm the community map.** Auto-discover channels → show the list → "Is this your community? Anything mislabeled?" → writes `community.publicChannels`.
2. **Intro channel.** "When a new member joins, which channel should the 'welcome + say hello' post go in?" (pick from public channels) → `purposes.intro_welcome`.
3. **Group-call channel.** "Which channel holds your featured group-call recap post?" → `purposes.group_call_featured`.
4. **Tiers.** "What membership tiers do you have?" → list of tier keys.
5. **Per tier — tag.** "Which GoHighLevel tag marks a {tier} member?" → `tierMap`.
6. **Per tier — recipe.** "Does {tier} get their own private 1:1 channel?" → `createPrivateChannel`. "Any other private channels they should be added to?" → `gatedPrivateChannels`. "Seed + pin a call-recording post in their private channel?" → `seedCallRecordingPost`. "Welcome post in their private channel?" → `welcomePrivate`. "Intro them in the community?" → `welcomeCommunity`.
7. **Welcome copy.** "For welcomes: a few rotating premade scripts, or a framework I write within each time?" → `welcomeCopy.mode`. If scripts → collect/draft a handful → `pool`. If framework → ask tone + must-include/avoid → `framework`.

Output: a filled `onboarding-config.json`. Re-runnable to edit any layer (e.g., add a tier = repeat steps 4–6 for the new tier only).
