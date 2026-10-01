# rehooks Step-3 mode: the lines for each slot

Read this file only when reel-scripter calls rehooks with `step: 3-lines`. At Step 2,
rehooks placed the slots: where each one sits, its type and its visual. Now write the
words for them.

## How to write them

The method is `./legit-rehooks.md`: the nine types, "Split the surfaces", the "Does a
line count as a re-hook?" test, the failure modes and the guardrails. Start from the type
and the visual named at Step 2. Write in the voice anchor. When a phrase from the creator
or their audience is gold, keep it word for word.

## What to return

For each slot in `slots:`, give 3 options. Each option has:

1. The spoken line.
2. The on-screen text, short enough to read in about a second.
3. The visual change.

Work in this order, one call each:

1. **The secondary hook first,** right after the user picks the hook. Build it on the
   picked hook and the approved skeleton.
2. **The mid-reel re-hooks after the body and proof picks exist.** Each one sits on
   something real the viewer just got, so write them only once those lines are picked.

If `slots:` is empty (a short reel with no secondary hook and no mid-reel slot), say so
in one line.

To regenerate, reel-scripter makes one more rehooks call with `step: 3-lines`, the same
slot, and what cut the first options. reel-scripter never writes these lines itself.
When `redo:` is present, return a fresh set that avoids what it names.

Your stamp is recorded automatically when this skill is called; do not write a from: line.
