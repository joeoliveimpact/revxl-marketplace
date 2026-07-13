# Lead Magnet Scoring Rubric

Used by `/lm-revamp` (diagnose mode) and as a pre-output self-check by `/lm-create` and `/lm-inspired-by`.

**Mode note — Section C in self-check:** Self-check mode (pre-output) DOES run Section C. Both modes score all sections; "Flag on Diagnose" in Section C's header means those criteria appear in diagnose output only, not that self-check skips them.

---

## How to Score

Rate each criterion: **PASS**, **FLAG**, or **FAIL**.
- **PASS** — criterion is clearly met.
- **FLAG** — partially met or unclear; note the gap.
- **FAIL** — criterion is missing or violated.

For every FLAG or FAIL, include a one-line fix suggestion.

---

## Section A — Hormozi Criteria

### A1. Narrow Problem
> Does the magnet solve one specific, named problem for one specific type of person?

| Result | What it looks like |
|--------|-------------------|
| PASS | Headline names a single outcome for a defined audience (e.g. "coaches who want X") |
| FLAG | Audience named but problem is vague or multi-part |
| FAIL | Broad promise aimed at "everyone" or no defined audience |

**Fix (FLAG/FAIL):** Rewrite the headline to name the audience + the one specific problem they have right now.

---

### A2. Reveals the Next Problem
> After consuming the magnet, does the reader naturally surface a new, bigger problem they now need help solving?

| Result | What it looks like |
|--------|-------------------|
| PASS | The magnet delivers a result and that result exposes a logical next gap |
| FLAG | Delivers the result but leaves reader with no obvious next step or question |
| FAIL | Magnet is self-contained to the point of solving the whole problem — removes the need for further help |

**Fix (FLAG/FAIL):** End with a section that names what becomes possible now — and what new challenge appears.

---

### A3. Gives the Secrets, Sells the Implementation
> Does the magnet give away the *what* and *why* freely, while making clear the reader needs help with the *how* (execution)?

| Result | What it looks like |
|--------|-------------------|
| PASS | Genuine insight delivered; complexity/time/risk of doing it alone is visible |
| FLAG | Information is shallow — feels withheld — or reader could fully execute without any help |
| FAIL | Either nothing real is shared (pure teaser) OR implementation is handed over completely |

**Fix (FLAG/FAIL):** Share the real strategy or insight. Then make the execution gap obvious: "This is what to do. Here's why doing it alone takes 6 months / gets messy / fails 80% of the time."

---

### A4. Clear Single CTA
> Is there exactly one next-step action, and is it obvious?

| Result | What it looks like |
|--------|-------------------|
| PASS | One CTA, stated clearly, action + outcome described (e.g. "Book a call → we'll build your plan together") |
| FLAG | CTA exists but is vague ("reach out!"), buried, or there are multiple competing CTAs |
| FAIL | No CTA, or CTA asks for something unrelated to the magnet's content |

**Fix (FLAG/FAIL):** Remove all CTAs except one. State what the reader does, what happens next, and what they get.

> *See also C5 for CTA motivational quality — A4 checks structure (single, clear CTA exists); C5 checks motivation (the CTA connects meaningfully to the content).*

---

## Section B — Coach Corpus Criteria

### B1. Results-in-Advance (Cattoni)
> Does the magnet deliver a real, felt result before the reader buys anything?

| Result | What it looks like |
|--------|-------------------|
| PASS | Reader finishes with a tangible win, shift, or "aha" they didn't have before |
| FLAG | Reader gets information but no felt shift or applied result |
| FAIL | Magnet is pure awareness-raising with nothing actionable or experiential |

**Fix (FLAG/FAIL):** Add a quick-win exercise, template, or decision the reader can execute and feel during the magnet itself.

---

### B2. Tease → Taste + Rename (Kennedy)
> Does the magnet tease the bigger outcome, give a taste of the approach, and use a proprietary name that makes the method feel distinct?

| Result | What it looks like |
|--------|-------------------|
| PASS | Framework or method has a unique name; reader gets enough to believe it works but wants the full version |
| FLAG | Has a proprietary/unique name but the tease↔taste ratio is off (too much or too little delivered) |
| FAIL | No proprietary name at all — generic advice with nothing distinctive or memorable |

**Fix (FLAG):** Keep the name; rebalance the ratio — give 1–2 steps in full detail, reference the rest without delivering them.
**Fix (FAIL):** Name the method something specific to you, then apply the ratio fix above.

---

### B3. Avoid Bookmark Graveyard (Klemm)
> Will the reader actually use this, or will it sit in a downloads folder unopened?

| Result | What it looks like |
|--------|-------------------|
| PASS | Short enough to complete in one sitting; format matches the promised time to value |
| FLAG | Longer than the format implies, or requires tools/setup the reader may not have |
| FAIL | Dense PDF, long video, or multi-part series that requires a significant time investment before any value is delivered |

**Fix (FLAG/FAIL):** Cut to the minimum that delivers the core result. If it's long, add a "Start here — 5 minutes" section at the top.

---

### B4. Avoid AI Dust Bunnies (Walther)
> Does the content feel like a real human who has done this work — or like AI-generated filler?

| Result | What it looks like |
|--------|-------------------|
| PASS | Specific examples, personal language, or named client outcomes; reads as real experience |
| FLAG | Generic advice that could apply to any niche; smooth but impersonal |
| FAIL | Buzzword-heavy, listicle-style, no specifics — clearly templated or AI-generated without voice |

**Fix (FLAG/FAIL):** Add one specific story, named example, or real number. Replace any phrase that sounds like it came from a blog aggregator.

---

### B5. ≤5–10 Min to Value (Perry)
> Can the reader reach the promised result within 5–10 minutes of starting?

| Result | What it looks like |
|--------|-------------------|
| PASS | Core value is front-loaded; reader hits the win within the first screen or first 5 minutes |
| FLAG | Value is there but buried after 10+ minutes of setup, context, or background |
| FAIL | Reader must complete the entire magnet — including setup or prerequisites — before getting anything |

**Fix (FLAG/FAIL):** Move the quick win to the top. Provide context after the win, not before.

---

### B6. Avoid Deciphering Fatigue (Conner)
> Is the language plain enough that the reader doesn't have to work to understand it?

| Result | What it looks like |
|--------|-------------------|
| PASS | Short sentences, common words, no unexplained jargon; a smart 8th grader could follow it |
| FLAG | Some jargon or passive voice; reader occasionally has to re-read a sentence |
| FAIL | Dense, clinical, or theoretical language throughout; reader fatigues before reaching the value |

**Fix (FLAG/FAIL):** Run every sentence through "could a busy person skim this and get it?" Replace any word over 3 syllables that has a plain equivalent.

---

## Section C — Anti-Patterns (Flag on Diagnose)

These are red flags to actively check for in `/lm-revamp` diagnose mode.

### C1. Clinical / Dry
> Does the magnet feel cold, academic, or corporate in tone?

| Result | What it looks like |
|--------|-------------------|
| PASS | Warm, direct, conversational — sounds like a person talking to a person |
| FLAG | Neutral/professional tone; not off-putting but not engaging |
| FAIL | Formal, jargon-heavy, reads like a report or textbook |

**Fix (FLAG/FAIL):** Rewrite the opening paragraph as if you're talking to one specific client you actually helped.

---

### C2. Catalog / Feature-Led
> Is the magnet a list of features or topics instead of a path to a result?

| Result | What it looks like |
|--------|-------------------|
| PASS | Structured around a single outcome; each section advances toward that outcome |
| FLAG | Mixed — some outcome focus, some feature listing |
| FAIL | Table of contents reads like a product brochure: "Module 1: X, Module 2: Y, Module 3: Z" with no throughline |

**Fix (FLAG/FAIL):** Reframe every section heading as a step toward the end result, not a topic.

---

### C3. Too Broad
> Does the magnet try to help everyone with everything?

| Result | What it looks like |
|--------|-------------------|
| PASS | Clearly scoped — one audience, one problem, one result |
| FLAG | Audience is named but problem is wide (e.g. "grow your business") |
| FAIL | Could be handed to any service business owner with no edits |

**Fix (FLAG/FAIL):** Pick the single most painful problem your best clients face and cut everything else.

---

### C4. Withholds the Win
> Does the magnet promise a result but deliver only awareness or a list of things to consider?

| Result | What it looks like |
|--------|-------------------|
| PASS | Reader ends with something they can use or have already used |
| FLAG | Reader ends knowing more but not doing anything differently |
| FAIL | Magnet is entirely "here's why this matters" with no actionable output |

**Fix (FLAG/FAIL):** Add a decision, template, or exercise that produces a concrete output the reader can keep.

---

### C5. Weak CTA
> Does the CTA fail to motivate action or make the next step unclear?

| Result | What it looks like |
|--------|-------------------|
| PASS | CTA is specific, low-friction, and connected to the value the magnet just delivered |
| FLAG | CTA exists but doesn't connect to the magnet's content, or the benefit of taking action is unstated |
| FAIL | No CTA, a generic "follow me for more," or multiple competing asks |

**Fix (FLAG/FAIL):** Write one CTA that completes this sentence: "Because you just learned X, the logical next step is Y — here's how to do that right now."

---

## Scoring Summary Template

Copy this block into the output of any diagnose run:

```
## Rubric Score — [Magnet Title]

| # | Criterion | Result | Fix (if needed) |
|---|-----------|--------|-----------------|
| A1 | Narrow Problem | PASS / FLAG / FAIL | |
| A2 | Reveals Next Problem | PASS / FLAG / FAIL | |
| A3 | Gives Secrets, Sells Implementation | PASS / FLAG / FAIL | |
| A4 | Clear Single CTA | PASS / FLAG / FAIL | |
| B1 | Results-in-Advance (Cattoni) | PASS / FLAG / FAIL | |
| B2 | Tease→Taste + Rename (Kennedy) | PASS / FLAG / FAIL | |
| B3 | Avoid Bookmark Graveyard (Klemm) | PASS / FLAG / FAIL | |
| B4 | Avoid AI Dust Bunnies (Walther) | PASS / FLAG / FAIL | |
| B5 | ≤5–10 Min to Value (Perry) | PASS / FLAG / FAIL | |
| B6 | Avoid Deciphering Fatigue (Conner) | PASS / FLAG / FAIL | |
| C1 | Clinical/Dry (Anti-pattern) | PASS / FLAG / FAIL | |
| C2 | Catalog/Feature-Led (Anti-pattern) | PASS / FLAG / FAIL | |
| C3 | Too Broad (Anti-pattern) | PASS / FLAG / FAIL | |
| C4 | Withholds the Win (Anti-pattern) | PASS / FLAG / FAIL | |
| C5 | Weak CTA (Anti-pattern) | PASS / FLAG / FAIL | |

**Overall:** X PASS · Y FLAG · Z FAIL
**Verdict:** [READY / REVAMP NEEDED / REBUILD]
```

### Verdict guide
- **READY** — 0 FAIL, 0–2 FLAG
- **REVAMP NEEDED** — 1–3 FAIL or 3+ FLAG
- **REBUILD** — 4+ FAIL or core criteria (A1, A3, B1) all fail. Core failures mean the magnet's foundation (audience, value exchange, results) is wrong — patching surface content won't fix it; 4+ scattered FAILs mean the fix list is longer and riskier than starting fresh.
