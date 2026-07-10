# Transcript Intake — carousel from a call (source-agnostic, paste-first)

How `carousel-create` resolves "carousel from my last call / from my call with <name>". Source set
by `{{TRANSCRIPT_SOURCE}}` in business-config.md. The universal fallback is manual paste — a build
never blocks on a missing integration.

**Paste-first default:** if the coach already pasted the transcript/notes, USE THAT — don't go
fetch. Auto-pull only when `{{TRANSCRIPT_SOURCE}}` is a connected service AND nothing was pasted.
Never make someone wait on integration hunting when a paste would do.

## The retrieval pattern

1. **Identify the call** — "my last call", a client name, a date, or a pasted recording URL/ID.
2. **Fetch** from `{{TRANSCRIPT_SOURCE}}` — tool names vary by install; discover the exact tools via
   ToolSearch (keyword = the service name, e.g. "fathom transcript") before calling. Never hardcode.
3. **Extract carousel-shaped material** (this is NOT a meeting summary):
   - the ONE teachable idea — a question the client asked, a myth that got busted, a breakthrough
     moment, an objection handled. One call usually holds 2-3 carousel seeds; list them, coach picks.
   - the coach's strongest verbatim lines — how THEY explained it on the call is the voice; quote it
     into slide copy rather than paraphrasing it flat.
   - the client's pain phrasing — avatar language, word for word (hooks live here).
4. **Confirm the pick** in one line ("Slide-worthy moment: <X>. Build on that?") then run the normal
   create flow — the call supplies topic + language; structure still comes from the blueprints.
5. Fetch failed or empty → ask for a paste → "none" → build from the coach's memory of the call and
   FLAG the gap plainly ("built from your recap, not the recording").

## Source map

| `{{TRANSCRIPT_SOURCE}}` | How to retrieve | Notes |
|---|---|---|
| `fathom` | Fathom MCP: search/list meetings by name or date → get the transcript. Pasted URL/ID → resolve directly. | Read-only. |
| `fireflies` | Fireflies MCP (auth once) → list/search → fetch by ID. | |
| `granola` | Granola MCP (auth once) → locate the note → fetch. | |
| `manual` | "Paste the transcript or your notes — or just tell me the moment from the call you want to teach." | Universal fallback — always works. Default. |

## Privacy + VoC

- Pulling a transcript is a read; fine to do for a draft. NEVER quote a CLIENT by name or
  identifiable detail on a slide — client pain phrasing gets anonymized to avatar language
  ("a client told me this week…"). The coach's own lines are theirs to use.
- Strong client phrasing is brand-brain fuel: after the build, offer once — "That pain line is
  gold. Want it saved to your voice bank?" → the `brand-brain` skill captures it (VoC shelf).

## Anti-patterns

- ❌ Hardcoding tool names → discover via ToolSearch every time
- ❌ Blocking the build on a failed fetch → paste → memory-with-flag, in that order
- ❌ Summarizing the call → extract teachable moments + verbatim voice, not minutes
- ❌ Client-identifying details on slides → anonymize to avatar language, always
