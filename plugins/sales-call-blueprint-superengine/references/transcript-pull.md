# Framework: Pulling Prior-Call Transcripts (Source-Agnostic)

<purpose>
Teaches how to retrieve a prior call's transcript (most often the triage call) from whatever recorder a business uses, so its confirmed intel can be folded into a strategy blueprint as "Prior Triage Intel." Source is set by {{TRANSCRIPT_SOURCE}} in references/business-config.md. The universal fallback is always manual paste — the skill never blocks on a missing integration.

**Paste-first default:** if the user already pasted the transcript/notes, USE THAT — don't go fetch. Only auto-pull when {{TRANSCRIPT_SOURCE}} is a connected service AND nothing was pasted. Pasting is the normal, usually-faster path; auto-pull is a convenience for users already wired up. Never make someone wait on integration hunting when a paste would do.
</purpose>

## Core Concepts

### Why pull a transcript
A strategy call is far stronger when the triage call's confirmed data is folded in (revenue, bottleneck, partner status, urgency). A recorded transcript is the highest-fidelity source — better than memory or sparse notes. Treat anything in the transcript as **confirmed intel**: deepen those topics in discovery, don't re-ask them (see references/rfpdp-method.md → Integrating Triage Notes).

### The retrieval pattern (same for every source)
1. **Identify the prior call** — by prospect name, date, or a pasted recording URL/ID.
2. **Fetch the transcript** from {{TRANSCRIPT_SOURCE}} using that source's tools (below). Tool names vary by install — discover exact tools via ToolSearch (keyword = the service name) before calling.
3. **Extract confirmed intel** — revenue, bottleneck, goal, urgency source, partner, coachability, exact phrases to mirror.
4. **Fold into the profile** under "Prior Triage Intel" and mark those discovery topics as confirmed.
5. If retrieval fails or returns nothing → fall back to manual paste; if none → proceed and flag the gap (thin-DM rule).

### Source map
| {{TRANSCRIPT_SOURCE}} | How to retrieve | Notes |
|----------------------|-----------------|-------|
| `fathom` | Fathom MCP: search/list meetings by prospect name or date → get the meeting transcript. If a call URL/ID is pasted, resolve it directly. | Read-only. Live in this workspace. |
| `fireflies` | Fireflies MCP (authenticate first) → list/search transcripts → fetch by ID. | Needs one-time auth. |
| `granola` | Granola MCP (authenticate first) → locate the note/transcript → fetch. | Needs one-time auth. |
| `ghl` | GHL MCP: get the conversation/message recording → message transcription (or download transcription). | Use when calls run through GHL. |
| `otter` / other | No direct integration assumed → manual paste. | — |
| `manual` | Ask the user to paste the transcript or triage notes. | Universal fallback — always works. |

### Discovering the exact tools
Tool names are environment-specific. Before fetching, run ToolSearch with the service keyword (e.g. "fathom transcript", "fireflies", "granola", "ghl transcription") to load the precise tool schemas, then call them. Do not assume tool names.

### Privacy / approval
Pulling a transcript is a read. It is fine to do autonomously to build a draft blueprint. Do NOT send, share, or externally post any transcript content — blueprints stay internal drafts until approved (workspace client-work rule).

## Examples
- **Fathom, by name:** {{TRANSCRIPT_SOURCE}}=fathom, prospect "Jane Prospect" → search meetings for "Jane" → get transcript → extract confirmed intel (revenue, bottleneck, partner status, urgency) → fold into Prior Triage Intel.
- **Pasted URL:** user drops a Fathom share link → resolve the recording directly → transcript → extract.
- **No integration:** {{TRANSCRIPT_SOURCE}}=manual → "Paste the triage call transcript or your notes, or say 'none' and I'll build from the DMs alone."

## Anti-Patterns
- ❌ Hardcoding tool names → they differ per install; discover via ToolSearch
- ❌ Blocking the blueprint because a transcript couldn't be fetched → fall back to paste, then to DMs-only with a flagged gap
- ❌ Treating transcript content as assumptions → it's confirmed intel; deepen, don't re-ask
- ❌ Sharing transcript content externally → internal draft only

