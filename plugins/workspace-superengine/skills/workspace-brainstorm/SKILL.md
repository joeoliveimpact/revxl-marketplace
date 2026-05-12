---
name: workspace-brainstorm
description: Use when the user has a fuzzy idea, asks "what should I do about X", says "I'm thinking about Y", "let's brainstorm", "help me figure out", "I want to launch/write/build/offer something but I'm not sure", or any moment a half-formed concept needs to become a written design before action. Works for content topics, coaching offers, client deliverables, ops changes, code features, and any other creative or strategic work in this workspace. Turns ideas into a saved design document at docs/specs/.
---

# Workspace Brainstorm — Idea to Design

Turn a fuzzy idea into a written, validated design through natural collaborative dialogue. Works for any kind of work in this workspace: content pieces, coaching offers, client deliverables, operational changes, code features, course outlines, sales sequences — anything where someone has the seed of an idea but not yet a plan.

<HARD-GATE>
Do NOT start implementing, drafting the deliverable, writing the content, scaffolding files, or taking any action toward the actual artifact until you have presented a design and the user has approved it. This applies to every project regardless of perceived simplicity — a one-line social post and a multi-week coaching launch both go through this gate. The design can be brief (a few sentences for genuinely small work), but you MUST present it and get approval.
</HARD-GATE>

## Layer 2: Suggest before invoking

When the user's prompt is borderline — the idea might be fuzzy enough to want brainstorming, or might just be a quick request the user wants answered directly — ask before firing the full skill:

> "This sounds like a brainstorm situation — want me to run `/workspace-brainstorm` and turn it into a design doc? Or do you want a quick answer right now?"

Only run the full process below after the user confirms. If the user explicitly invokes `/workspace-brainstorm`, skip the suggestion and proceed.

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A single email, a one-paragraph post, a 30-minute coaching call agenda — all of them. "Simple" work is where unexamined assumptions cause the most wasted effort. The design can be three sentences; what matters is that it exists in writing and the user approves it before you spend tokens building the thing.

## Checklist

Complete in order:

1. **Explore workspace context** — skim `GOALS.md`, `PLANNING.md`, `MEMORY.md`, recent `Checkpoint.md` entries, and any obviously relevant files. Understand what this workspace is for before proposing anything.
2. **Ask clarifying questions** — one at a time. Understand: who the deliverable is for, what success looks like, hard constraints (time, budget, brand voice, format), and any prior attempts.
3. **Propose 2-3 approaches** — with trade-offs and your recommended pick. Lead with the recommendation and why.
4. **Present the design** — in sections scaled to the work's complexity. Pause after each section for approval.
5. **Write design doc** — save to `docs/specs/YYYY-MM-DD-<topic>-design.md` (workspace root, not a subfolder). Create `docs/specs/` if missing.
6. **Self-review the doc** — placeholders, contradictions, ambiguity, scope. Fix inline.
7. **User review gate** — ask the user to read the saved spec and approve before moving on.
8. **Hand off to `workspace-plan`** — invoke that skill to turn the design into a stepwise plan.

## Process

**Understanding the idea:**
- Skim the workspace files listed above first.
- If the request actually contains multiple independent projects (e.g. "launch a new course AND rebuild the website AND hire a VA"), flag it now and propose decomposition — one design doc per project.
- Ask questions one at a time. Multiple-choice when you can; open-ended when you must.
- Focus on: purpose, audience, constraints, success criteria, format/length, deadline.

**Universal examples of clarifying questions (pick what fits the request):**
- Content: "Who's the reader? Existing audience, cold traffic, or a specific client?"
- Coaching offer: "Is this a one-time workshop, a recurring program, or a productized service? How long does a client stay engaged?"
- Client deliverable: "What format does the client expect — slide deck, doc, Loom, dashboard? Any brand template?"
- Ops change: "Is this a one-time cleanup or a recurring process you want to bake into the workspace?"
- Code feature: "Is this a new capability or a fix to existing behavior? What's the smallest thing that proves it works?"

**Exploring approaches:**
- Propose 2-3 different paths. Examples:
  - Content: short post vs. long essay vs. video script with companion post
  - Offer: low-ticket tripwire vs. mid-tier program vs. high-ticket 1:1
  - Ops: manual checklist vs. partial automation vs. full hook/agent
- Always include trade-offs (effort, time, risk, reversibility) and your recommended pick with reasoning.

**Presenting the design:**
- Scale each section to its complexity. A 100-word social post might need 3 sentences. A 6-month coaching launch might need a full page per section.
- Cover whatever sections matter for this kind of work. Common ones:
  - **Purpose & audience** — who, why, what changes when this lands
  - **Definition of Done** — concrete, observable success criteria
  - **Structure / components** — what the deliverable is made of
  - **Constraints** — voice, brand, length, deadline, budget, dependencies
  - **Risks & open questions** — what could go wrong, what's still unknown
- Pause after each section: "Does this section look right?"

**Design for clarity:**
- Break the work into pieces with clear boundaries. For a content piece: hook, body, CTA. For an offer: promise, deliverables, pricing, fulfillment. For a code change: the new behavior, the affected files, the test that proves it.
- Each piece should be describable in one sentence. If you can't, the boundary is fuzzy and needs work.

## After the Design

**Write the doc:**
- Save to `docs/specs/YYYY-MM-DD-<topic>-design.md` in the workspace root. Create the `docs/specs/` directory if it does not exist.
- (User preferences for spec location override this default.)
- Commit if the workspace is a git repo. Skip silently if not.

**Self-review pass:**

1. **Placeholder scan** — any "TBD", "TODO", "decide later", vague phrases? Fix inline.
2. **Internal consistency** — sections don't contradict each other; the structure section matches the Definition of Done.
3. **Scope check** — is this one project or has it grown into several? If several, decompose now.
4. **Ambiguity check** — could any line be read two ways? Pick one reading and make it explicit.

Fix issues inline. No need to re-review.

**User review gate:**

> "Spec written and saved to `docs/specs/<filename>`. Please review it and tell me if you want changes before we turn it into a stepwise plan."

Wait for confirmation. Make any requested changes, then continue.

**Hand off:**
- Invoke `workspace-plan` to turn the approved design into an implementation plan.
- Do NOT invoke any other skill. `workspace-plan` is the only next step.

## Key Principles

- **One question at a time** — don't overwhelm.
- **Multiple choice preferred** — easier to answer than open-ended.
- **YAGNI ruthlessly** — every design starts smaller than the user's first ask. Trim before presenting.
- **2-3 approaches every time** — even when the answer feels obvious. The alternatives sharpen the chosen path.
- **Present, pause, approve** — never write the doc before the user has agreed to the design verbally.
- **Universal, not coding-specific** — this skill runs for marketing emails, sales pages, SOPs, video scripts, and lots more. Choose vocabulary that fits the kind of work being designed.
