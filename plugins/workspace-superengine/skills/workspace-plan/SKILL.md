---
name: workspace-plan
description: Use when an approved design or clear spec needs to become a stepwise plan with an explicit Definition of Done. Trigger phrases include "let's plan X", "how should I approach Y", "what's the path to Z", "I need a plan for", "turn this design into steps", "break this down", "what are the steps to launch/write/build/ship". Universal — produces plans for coaching program rollouts, content production schedules, client engagement onboardings, ops migrations, code features, and any other multi-step work. Saves the plan to docs/specs/ alongside the design it implements.
---

# Workspace Plan — Design to Stepwise Plan

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> I'm about to turn your design into a step-by-step plan. Each step gets a clear "you're done when..." line so there's no guessing. The plan becomes a document you can hand to me (or another Claude) to actually build it.

## Overview

Take an approved design (typically the output of `workspace-brainstorm`) and turn it into a stepwise plan that someone could execute even if they had no prior context. Document every step they need: which file or asset to touch, what to do in it, what "done" looks like for each step, how to know it worked.

Assume the executor is capable but knows nothing about this workspace or the project's history.

**Announce at start:** "I'm using the workspace-plan skill to write the implementation plan."

**Save plans to:** `docs/specs/YYYY-MM-DD-<topic>-plan.md` (workspace root). Create `docs/specs/` if missing.

## Layer 2: Suggest before invoking

If the user has a design or a clear concept and is asking how to proceed, but hasn't explicitly invoked this skill, offer:

> "Want me to run `/workspace-plan` and turn this into a stepwise plan with an explicit Definition of Done? Or would you rather we just start working?"

If they want to dive in directly, skip the full process. Otherwise, run it.

## Scope Check

If the design covers multiple independent projects, it should have been decomposed in brainstorming. If it wasn't, stop and suggest decomposition — one plan per project. Each plan should produce something usable on its own.

## Plan Document Header

Every plan MUST start with this header:

```markdown
# [Project Name] Plan

**Goal:** [One sentence describing what this produces]

**Approach:** [2-3 sentences about how]

**Definition of Done:** [Concrete, observable, recipient-facing criteria — what must be true for this to count as finished]

---
```

## Universal Examples

This skill is not coding-specific. Examples of work it plans:

- **Coaching program rollout**: outline modules, build sales page, set up payment, record onboarding video, schedule launch emails, plan first cohort touchpoints.
- **Content production schedule**: research topic, outline, draft, edit, sourced images, publish, repurpose into short-form, schedule promotion.
- **Client engagement onboarding**: kickoff doc, intake form, kickoff call agenda, first deliverable draft, review cycle, sign-off.
- **Ops migration**: document current process, design new process, pilot on one workflow, update SOP, train team, deprecate old process.
- **Code feature**: write failing test, implement, run tests, refactor, commit, document.

## Bite-Sized Task Granularity

Each step is one concrete action (typically 2–15 minutes of work):

For a content production plan:
- "Pull the three reference posts from `output/final/` and skim for tone" — step
- "Draft the hook in `output/drafts/hook-draft.md`" — step
- "Read the hook out loud, cut anything that stumbles" — step
- "Show the hook to user; wait for approval" — step
- "Draft the body" — step
- "Verify against the Definition of Done" — step

For a coaching launch plan:
- "Write the offer one-liner in `output/drafts/offer.md`" — step
- "Get user approval on the one-liner" — step
- "Draft the sales page outline" — step
- "Get user approval on outline" — step
- "Write the sales page draft" — step

Steps should be small enough that a fresh executor can do one without context-switching, and the user can review between steps if they want.

## Task Structure

````markdown
### Task N: [Component Name]

**Files / assets:**
- Create: `exact/path/to/file.md`
- Modify: `exact/path/to/existing.md` (which section)
- Reference: `path/to/source-material.md`

- [ ] **Step 1: [Concrete action]**

Detailed instruction. For text/content work, include the actual prompt, outline, or specification — not "write the section." For code work, include the actual code.

- [ ] **Step 2: [Next action]**

…and so on.

- [ ] **Step N: Verify against Definition of Done**

Re-read the Definition of Done at the top of the plan. Tick each criterion. If anything is missing, list the gap and create remediation steps before claiming this task done.

- [ ] **Step N+1: Commit / save / hand off**

Workspace-appropriate: `git commit -m "..."`, move file from `output/drafts/` to `output/final/`, send to client, etc.
````

## No Placeholders

Every step must contain the actual content the executor needs. Plan failures — never write these:

- "TBD", "TODO", "fill in later", "decide here"
- "Add appropriate copy" / "write the content" / "handle edge cases" without showing what
- "Similar to Task N" — repeat the content, the executor may read tasks out of order
- Steps that describe what to do without showing how (include the prompt, outline, copy, or code)
- References to assets, files, or pieces not defined in any task

## Remember

- Exact file paths and asset names
- Concrete content in every step — if a step produces text, show the outline or draft text inline
- Explicit Definition of Done at both the plan level and verification-step level
- One project per plan; decompose if you find creep

## Self-Review

After writing the complete plan, look at the design with fresh eyes and check the plan against it:

1. **Design coverage** — every section of the design has at least one task that implements it. List gaps.
2. **Placeholder scan** — any of the red flags from the "No Placeholders" section above. Fix them.
3. **Name consistency** — if you called a file `offer-outline.md` in Task 2, you'd better not call it `offer-draft.md` in Task 5. Pick one name and use it.
4. **Definition of Done present** — top-level DoD exists, and at least one verification step references it.

Fix issues inline. If a design requirement has no task, add the task.

## Execution Handoff

After saving the plan, ask the user how they want to execute:

> "Plan saved to `docs/specs/<filename>`. Two options:
>
> 1. **Run it inline** — we work through tasks together in this session.
> 2. **You drive** — you do the work yourself and come back if you get stuck.
>
> Which?"

If the workspace has subagent-capable infrastructure and the project is coding-flavored, you may also offer a subagent-driven path (`superpowers:subagent-driven-development`). For most non-coding work, inline-with-user is the right default.

## Hand-off Rules

- Before claiming any task complete, run `workspace-verify`.
- Before claiming the whole plan complete, run `workspace-verify` against the top-level Definition of Done.
