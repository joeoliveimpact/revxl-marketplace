# Routing ... the Next-Moves contract

Every skill ends **every terminal path** (success, decline, empty result,
degraded, refused-for-prereqs) with a Next-Moves block. A client holding a
finished deliverable, or a dead end, must never be left staring at it with no
offered road. Edges come from `journey-map.md`; this file defines the block
shape and the rules. **Blocks live INLINE in each SKILL.md** (skills run
standalone). This file is the convention; journey-map is the edge ledger.

## Block shape (the choose-your-own-adventure grammar)

```
**Next moves**
1. <verb phrase> ... <what you get, one clause>. Say: "<exact trigger phrase>"
2. ...   (2 to 4 options total, most-likely-first)
```

- **Numbered, 2 to 4 options, most-likely-next first.** Every option ends in
  `Say: "<trigger>"`, the trigger quoted verbatim from the journey-map roster.
  **Exception:** a menu option that ends the conversation or requires no routing
  ("just ask me anything", "back to the caller") may omit `Say:`.
- ***Italic conditionals* for state-gated options:** `*If no analysis exists
  yet:*` ... the option renders only when its state condition holds. An option
  that depends on a plugin or skill that is not installed carries
  "(if installed)".
- **Labeled variant blocks** for non-happy endings, own header:
  `**Next moves ... no analysis**`, `**Next moves ... credits short**`,
  `**Next moves ... Vault degraded**`. Declines and refusals get a block too.
- **Router menus** (shortform-start first-run, the compass): same grammar, plus
  `<- start here` appended to the primary option's line.
- One or two plain sentences MAY precede the block (what was produced, where it
  was saved; the outside-Claude step: *"Film these three, keep them in drafts,
  post the first one tomorrow."*). The block itself stays bare: no emoji
  scaffold, no position paragraph inside it.
- At `new` teach level an option may carry a one-line "why"; at `pro` the lines
  stay bare.

## Rules

1. **Moves come from journey-map edges plus current state, never generic.**
   Render the registry row for this ending against `state/<brand>.json`.
   2 to 4 options, most-likely-next first.
2. **#1 must be immediately actionable now**, its prereqs already met in state.
   Never rank a gated move #1 while its gate is unmet; offer the unblock route
   instead (edge E0).
3. **Every option quotes its exact trigger phrase** from the journey-map roster,
   so the client can say it verbatim.
4. **Teach-aware rendering** (`teach-mode.md`): at `new`, each move carries a
   one-line "what this means"; at `pro`, bare lines.
5. **State-gated offers: detect before offering.** No analysis on disk, no
   "script from the field" offer. No `voc/`, the option is voice capture, not
   voice-matched copy. No socialcrawl-superengine marker, no deep-play offer
   (F9's refusal block instead).
6. **Offer-once discipline:** `declined_offers` in state. A declined offer never
   reappears this journey unless the client asks. Credit-spending moves are
   always phrased as an ask with the cost named
   (`socialcrawl-endpoints.md` holds the prices).
7. **Refusals route, never scold.** A skip-ahead attempt gets: what is missing,
   why the order exists (one plain-English sentence), and the door, as move #1.
8. **Degraded endings still route** (F3, F5): the block appears even when the
   Vault was down or the pulse lost accounts, with the degrade noted in the
   preamble sentence, and a labeled variant block
   (`**Next moves ... Vault degraded**`) when the routes themselves change.

## Where the block lives in the file

Every block sits under a `## Terminal paths` section, and that section starts
**before byte 20,000 of its SKILL.md**. For any SKILL.md over 12,000 bytes it
starts in the **top third** of the file (`min(size/3, 20000)`).

Why: after a context compaction the tail of a long SKILL.md is gone, and the
skill that produces the primary exit is left with no routing at all. This is
the one deliberate deviation from the meta-ads file shape.
`scripts/check_routing.py` enforces it as a build error.

Place the section immediately after `## Teach mode` / `## Overview` and before
the first `## Step`. `## Prereq (E0)` sits beside it, naming the door.

## Grammar the scanner accepts

**Block header.** A line that starts with `**Next moves` and closes with `**`,
optionally carrying a label after ` ... `:

```
**Next moves**
**Next moves ... empty week**
**Next moves ... credits short**
```

**Phrase.** `Say: "<phrase>"` on one line, straight double quotes, the phrase
copied verbatim from the journey-map roster. Placeholders go in angle brackets
(`Say: "add <handle> to my roster"`). A trailing `(if installed)` marks a phrase
whose target is not installed yet and exempts it from the phrase warning.

## The compass

`shortform-next` is the block on demand: it reads state plus `journey-map.md`,
renders "you are here" (done / current / next on the journey graph) and the same
ranked moves, callable any time. `shortform-start` advertises it: *"Lost? Say
**what's next in shortform**."* Skills may hand off to it instead of duplicating
routing logic for a complex mid-journey state.

The compass phrase is `what's next in shortform` (secondary: `shortform next`).
**Never the bare two-word form without `in shortform`**: that phrase belongs to
`meta-ads-next`, and skill selection is catalog-wide.

## Self-evidencing lines

Two audit lines accompany the block wherever they apply, never silently skipped:

- **Vault:** `Vault: <n> searches, <m> reads | <ok|degraded|skipped: reason>`,
  required at every Vault trigger point (`vault-api.md`).
- **State:** skills that wrote state name it in the preamble ("saved to your
  journey file") at `new` teach level.
