# Routing — the Next-Moves contract

Every skill ends **every terminal path** (success, decline, empty result,
degraded, refused-for-prereqs) with a Next-Moves block. A coach holding a
finished deliverable — or a dead end — must never be left staring at it with
no offered road. Edges come from `journey-map.md`; this file defines the block
shape and the rules. **Blocks live INLINE in each SKILL.md** (skills run
standalone) — this file is the convention; journey-map is the edge ledger.

## Block shape (the choose-your-own-adventure grammar)

```
**Next moves**
1. <verb phrase> — <what you get, one clause>. Say: "<exact trigger phrase>"
2. …   (2–4 options total, most-likely-first)
```

- **Numbered, 2–4 options, most-likely-next first.** Every option ends in
  `Say: "<trigger>"` — the trigger quoted verbatim from the journey-map
  roster. **Exception:** a menu option that ends the conversation or requires
  no routing (e.g. "just ask me anything", "back to the caller") may omit
  `Say:`.
- ***Italic conditionals* for state-gated options:** `*If no analysis exists
  yet:*` — the option renders only when its state condition holds.
- **Labeled variant blocks** for non-happy endings, own header:
  `**Next moves — no-go**`, `**Next moves — compliance failed**`,
  `**Next moves — Brain degraded**`. Declines and refusals get a block too.
- **Router menus** (start first-run, guide exit): same grammar, plus
  `← start here` appended to the primary option's line.
- One or two plain sentences MAY precede the block (what was produced, where
  saved; the outside-Claude step: *"Upload these 3 statics to Ads Manager,
  keep them **paused** — launch happens in the launch runbook."*). The block
  itself stays bare — no emoji scaffold, no position paragraph inside it.
- At `new` teach level an option may carry a one-line "why" clause; at `pro`
  the lines stay bare.

## Rules

1. **Moves come from journey-map edges + current state — never generic.**
   Render the registry row for this ending against `state/<brand>.json`.
   2–4 options, most-likely-next first.
2. **#1 must be immediately actionable now** — its prereqs are already met in
   state. Never rank a gated move #1 while its gate is unmet; offer the
   unblock route instead (edge E0).
3. **Every option quotes its exact trigger phrase** from the journey-map
   roster — the coach can say it verbatim.
4. **Teach-aware rendering** (`teach-mode.md`): at `new`, each move carries a
   one-line "what this means"; at `pro`, bare lines.
5. **State-gated offers:** detect before offering — no Brain key → no
   deeper-dive offer (one line max, never a block slot); no voc/ → the option
   is voice capture, not voice-matched copy; competitor-intel never offered
   before own PDA exists.
6. **Offer-once discipline:** `declined_offers` in state — a declined offer
   never reappears this journey unless the coach asks. Credit-spending moves
   (socialcrawl crawls) are always phrased as an ask with the ✋ cost named.
7. **Refusals route, never scold.** A skip-ahead attempt gets: what's missing,
   why the order exists (one plain-English sentence), and the door — as the
   #1 move.
8. **Degraded endings still route** (F9/F10): the block appears even when the
   Brain was down or voice was cold — with the degrade noted in the preamble
   sentence, and a labeled variant block (`**Next moves — Brain degraded**`)
   when the routes themselves change.

## The compass

`meta-ads-next` is the block-on-demand: reads state + journey-map, renders
"you are here" (done / current / next on the journey graph) + the same ranked
moves, callable anytime. `meta-ads-start` advertises it: *"Lost? Say
**what's next**."* Skills may hand off to it instead of duplicating routing
logic for complex mid-journey states.

## Self-evidencing lines

Two audit lines accompany the block wherever they apply (never silently
skipped):

- **Brain:** `Brain: [brain] <path> woven` or `Brain: skipped (no key /
  cached / degraded / budget)` — required at every Brain trigger point
  (`vault-api.md`).
- **State:** skills that wrote state name it in the preamble ("saved to your journey
  file") at `new` teach level.
