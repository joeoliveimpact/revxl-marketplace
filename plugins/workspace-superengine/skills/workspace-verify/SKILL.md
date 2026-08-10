---
name: workspace-verify
description: Use before claiming any work is complete, done, ready to ship, ready to send, or ready to hand to a client. Trigger phrases include "I'm done with X", "task complete", "ready to ship", "ready to send", "before I close this out", "is this finished", "looks good to go", "wrapping up Y", "let's call it done". Forces a pre-completion checklist — deliverable exists at the expected location, success criteria from the design are met, would the recipient (client / reader / customer / future-you) actually accept this as finished. Works for content drafts, client deliverables, coaching artifacts, ops changes, code shipments, and any other work product.
---

# Workspace Verify — Evidence Before Done

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> Before we call this done, let's double-check. I'll walk through a short list — does the thing actually exist, does it meet the goals you set, would the person you're handing it to accept it as-is. Two minutes, saves headaches later.

## Overview

Claiming work is finished without checking it is dishonesty, not efficiency. This applies whether the work is a blog post, a client deck, a sales email, a coaching curriculum, an ops runbook, or a code change.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit.**

## Layer 2: Suggest before invoking

If the user signals completion without invoking this skill explicitly (e.g. "okay I think we're done"), and the work is non-trivial, offer the check first:

> "Want me to run the `/workspace-verify` checklist before we call this done? Takes about 30 seconds and catches the common gotchas."

If the user declines or the work is genuinely tiny (one-line tweak), skip the full process and proceed.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you have not actually looked at the deliverable in this message, you cannot claim it is done.

## The Gate Function

Before claiming any status or expressing satisfaction:

1. **IDENTIFY** — what would prove this work is done?
   - For a written piece: the file exists at the expected path, it reads end-to-end without gaps.
   - For a client deliverable: the file is in `output/final/` (or the agreed destination), formatted per the client's spec.
   - For an offer/program: the landing page is live, the payment link works, the fulfillment doc exists.
   - For a code change: the relevant command runs, the expected output appears, exit code 0.
   - For an ops change: the new process is documented in the right place AND tested at least once.
2. **CHECK** — actually do the check, fresh, in this turn. Read the file. Open the link. Run the command. Look at the deliverable with your own tools.
3. **READ** — full output / full document. Don't skim the first paragraph and assume the rest is fine.
4. **VERIFY against the Definition of Done** — pull the success criteria from the design doc or the original ask. Tick each one off explicitly.
   - If any criterion fails: state the actual state with evidence. Do not soften.
   - If all pass: state the claim WITH the evidence (path, output, screenshot reference).
5. **ONLY THEN** make the completion claim.

Skip any step = lying, not verifying.

## The "Would the recipient accept this?" Test

Before saying done, picture the recipient — the client, the reader, the customer, the future Joe who'll open this file in three weeks. Would they look at this and say "yes, that's what I wanted"? Or would they ask "where's the X?" / "this isn't formatted right" / "I can't find the link"?

If you can name something the recipient would push back on, you are not done. Fix it.

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| "Draft is ready" | You re-read it end-to-end in this turn | "I just wrote it, it must be ready" |
| "Deck is done" | You opened the file and clicked through every slide | "I saved the file" |
| "Email sequence is finished" | You read all N emails in order and checked the links | "I wrote the last one" |
| "Client deliverable is ready" | File is in the agreed location, named per spec, opens cleanly | "I exported it somewhere" |
| "Offer is live" | You opened the public URL and walked the checkout | "I pushed publish" |
| "Tests pass" | Test command output: 0 failures, run fresh | "Should pass now" |
| "Bug fixed" | Reproduced the original symptom and confirmed it no longer occurs | "Code changed, looks right" |
| "Subagent finished" | You read what they actually produced | The subagent said "done" |

## Red Flags — STOP

- Using "should", "probably", "seems to", "I think so"
- Expressing satisfaction before the check ("Great!", "Perfect!", "All set!")
- About to send / publish / commit / hand off without looking at the artifact
- Trusting a subagent's success report without reading their output
- Doing a partial check and extrapolating to the rest
- Thinking "just this once"
- Tired and wanting the task over
- Any wording that implies done-ness without fresh evidence

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | Check it |
| "I'm confident" | Confidence is not evidence |
| "Just this once" | No exceptions |
| "I read it five minutes ago" | Five minutes is enough for it to have changed; re-read |
| "Agent said success" | Verify independently |
| "Recipient won't notice" | They will, and you will have to redo it |
| "I'm tired" | Exhaustion is not an excuse |

## When To Apply

**ALWAYS before:**
- Any variation of a done/ship/send/complete claim
- Any expression of satisfaction about work state
- Marking a task done in `tasks/STATUS.md`
- Closing a session via `session-closeout`
- Handing a deliverable to a client
- Committing, pushing, publishing
- Moving on to the next task

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of completion
- Any communication that suggests the work is done

## The Bottom Line

**No shortcuts.**

Look at the artifact. Compare it to the Definition of Done. THEN say it's ready.

This is non-negotiable.
