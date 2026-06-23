---
name: email-sequence-superengine:warm-nurture
description: Build an ongoing weekly value-to-invite nurture pattern (1-7 emails per week, default 3) that entertains, gives value, and softly invites to keep a list warm. Trigger phrases include "warm nurture", "weekly nurture emails", "keep my list warm", "value emails", "reactivation sequence".
---

# Task: warm-nurture

Build the weekly 3-email value→invite pattern (broadcast: an evergreen repeating week, fires to the ongoing-nurture segment).

## Campaign framework
${CLAUDE_PLUGIN_ROOT}/references/warm-nurture-framework.md
${CLAUDE_PLUGIN_ROOT}/references/story-engines.md (REQUIRED — warm runs on story, not tips)
${CLAUDE_PLUGIN_ROOT}/references/story-bank.md (REQUIRED — pull REAL stories; never invent)

## Before writing: get real material — from BOTH wells
Fill the story-bank from BOTH sources every run (not either/or): (1) run the `story-intake` skill for fresh
personal stories AND (2) pull coach-turn stories/analogies from recent transcripts (via the voice/VoC skill,
or ask the coach to point at recent calls). Combine, then build each email around a REAL banked story matched
to its engine. If the coach gives nothing and no transcripts exist → tell them the emails will be generic
without real input, ask for at least one real moment. Do NOT fabricate.

## Flow
Follow ${CLAUDE_PLUGIN_ROOT}/references/generator-flow.md exactly, loading the warm-nurture framework above. Before generating:
**ask the coach how many emails per week (1-7), default 3.** Suggest scaling to list size + niche appetite +
content capacity (small/cold list → fewer; engaged list → more). Then build ONE week's pattern at the chosen
frequency using the framework's role tiers, as the reusable template the coach repeats and varies weekly.
Text-only. Keep ~1 invite per 4 emails (80/20 value-to-pitch).

**Storytelling is mandatory here** (per ${CLAUDE_PLUGIN_ROOT}/references/story-engines.md): each email runs a story engine and
ROTATES (Story Selling / Analogy-Seinfeld / HSO·HIPS·PAS); rotate the Attractive-Character storyline week to
week; chain a weekly open loop (end teasing a named next send); run a P.S. subplot thread; blunt seam to one
CTA. Source stories from the coach's real life + VoC, in the coach's voice. If an email reads like a generic
tips newsletter → it failed, rewrite it as a story.
