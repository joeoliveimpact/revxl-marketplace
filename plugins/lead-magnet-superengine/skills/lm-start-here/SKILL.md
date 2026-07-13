---
name: lm-start-here
description: Router for the lead-magnet engine. Use when a coach wants a lead magnet built, improved, or modeled on someone else's, or wants to set up the engine. Trigger phrases include "/lead-magnet-superengine", "I need a lead magnet", "build me a lead magnet", "make me an opt-in", "create a freebie", "improve my lead magnet", "revamp my opt-in", "make one like this", "set up the lead magnet engine", "/lm-start-here".
---

# /lm-start-here — Lead-Magnet Engine Router

One job: figure out which door the user needs and route there. No building happens
in this skill — each door owns its own workflow.

## Routing — run this decision every invocation

1. **No active profile?** Check `${CLAUDE_PLUGIN_DATA}/profiles/` for a client profile.
   If none exists, or the user says "set up / connect sources / first time":
   → route to the `lm-setup` skill (it seeds the profile from the shipped template
   and walks the optional upgrades). A missing profile does NOT block building —
   offer setup once, then proceed through the right door at zero-upgrade baseline
   if the user prefers.

2. **Intent routing:**

| User says (or means) | Route to |
|---|---|
| "new magnet from scratch", "build/create a lead magnet", "I need an opt-in", names a topic with nothing pre-existing | the `lm-create` skill |
| "improve / refresh / revamp / diagnose my existing magnet", hands over their own PDF/docx/URL | the `lm-revamp` skill |
| "make one like this", "inspired by this [competitor / example]", pastes someone ELSE's magnet, video, or page | the `lm-inspired-by` skill |
| "capture my voice", "build my brand brain", "mine my calls" | the `brand-brain` skill |
| "set up / reconfigure / connect research sources" | the `lm-setup` skill |

3. **Ambiguous?** Ask one question: "Are we starting from scratch, improving something
   you already have, or modeling something you've seen?" Then route.

## Notes

- Ownership matters for the revamp-vs-inspired split: THEIR OWN material → `lm-revamp`;
  someone else's material → `lm-inspired-by` (originality guardrail applies there).
- Every door hands off to the shared pipeline in `${CLAUDE_PLUGIN_ROOT}/core/build-core.md`;
  do not duplicate any of its stages here.
- Drafts only — the user publishes. Never use em dashes in output copy; use "..." for pauses.
