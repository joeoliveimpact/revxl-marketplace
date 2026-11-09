# Emphasis: mark the smallest truthful run of words

**Hard rule.** When a caption bolds, capitalises or punches words, the marked words must say something true on their own. A viewer's eye lands on the marked words first, and sometimes only on them. If the marked part flips or overstates what the full sentence says, the caption is telling a lie in big letters.

So mark the **smallest run of words that is still true by itself**. Small, so the emphasis stays sharp. True, so it never says half a thing.

## What a marked run must keep

### Negations
A "not" word changes the meaning, so it goes inside the mark.

- "This doesn't **work**" says *work* to the skimming eye. Mark **doesn't work**.
- "You **never** need to post daily" is fine: *never* is the whole point.
- Counts as a negation: not, no, never, none, nothing, without, hardly, and any *n't* word (don't, can't, isn't, won't). It joins the mark when it sits within two words before it.

### Conditions
A promise with a condition is a different promise without it.

- "It grows only if you **post daily**" marks a habit as if it were the result. Mark **only if you post daily**.
- Condition words: if, unless, only, until, except, when. The mark reaches back to the condition word in the same clause.

### Numbers and their units
A number without its unit, or a unit without its number, means nothing or something bigger.

- "**30** days" becomes **30 days**. "ten **clients**" becomes **ten clients**.
- **3x**, **50%** and **$5k** already carry their unit, so they stand alone.
- A qualifier or currency sign attached to the number comes too: "up to **$5k**" becomes **up to $5k**; "over **100** leads" becomes **over 100 leads**. Dropping "up to" turns a ceiling into a promise.

### Contrasts
A contrast is two halves. Marking one half alone states only half the claim.

- "Not more posts but **better hooks**": mark the whole clause, **not more posts but better hooks**.
- Contrast words: but, than, instead, vs, versus, rather, and a "not" followed by "but". When the mark contains one, sits right before one, or has one up to two words in front of it, the mark widens to the whole clause, up to the nearest comma or full stop on each side.

## What is fine

- Marking a whole claim that is already true alone: "**Hooks beat volume.**"
- Marking a name, a keyword or a deliverable: "Comment **GUIDE**".
- Marking more than the minimum. The rule only forbids marking too little.

## How it is checked

`${CLAUDE_PLUGIN_ROOT}/skills/caption-writer/scripts/emphasis.py` holds the one copy of this rule. The caption checker uses it on every bolded span and suggests the truthful run when a mark is too small. The word-mark picker for burned-in captions (`editor-superengine:reel-captions`) imports the same function, so a bolded caption word and a punched on-screen word follow one rule.

The check reads words, not meaning, so it can miss a half-truth it has no word list for. When a mark looks fine to the script but reads wrong to you, widen it.
