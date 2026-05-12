---
description: Confidentiality and boundary rules for any workspace that holds multiple clients.
alwaysApply: true
---

# Client-work rules

This workspace contains material from multiple clients. The following rules apply at all times, on every prompt, in every skill invocation.

## Confidentiality

1. **Never read another client's folder unless the current task names it explicitly.** "Look at how I handled the last client" is not explicit — ask which one.
2. **Never quote, paraphrase, or reference Client A's material in a deliverable for Client B.** Patterns, templates, and frameworks are fine; specifics are not.
3. **Do not write a client's name, business details, or session notes into shared files** (RULES.md, GOALS.md, MEMORY.md, the root README, or any file outside `clients/<that-client>/`).
4. **Outputs default to `clients/<client-name>/deliverables/` unless the user says otherwise.** Loose deliverables in workspace root are a leak risk.

## Boundaries

5. **Do not act on a client's behalf in a third-party system** (send email, post to social, log into their platforms) unless the task explicitly authorizes it for that specific client. Coaching workspaces tend to drift into automation; require an explicit "yes, do it on their account" before crossing that line.
6. **Track promises.** Anything you tell the user you will deliver to a client goes into that client's `deliverables.md` in the same response. Spoken promises that don't get written down become broken promises.
7. **Surface conflicts.** If a request would create a conflict of interest between two clients (same niche, overlapping market, conflicting positioning), say so before doing the work.

## Identity hygiene

8. When drafting in a client's voice, read their voice references in `clients/<client-name>/` (intake notes, prior deliverables) before writing. Do not default to the workspace owner's voice.
9. Sign deliverables as the client, not as the workspace owner, unless the owner is the named author.

Violations should be called out in the response, not hidden.
