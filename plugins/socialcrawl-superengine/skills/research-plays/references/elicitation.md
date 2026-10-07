# Elicitation reference — the research rubric and how to ask

### The research rubric — five dimensions, asked before any number

Round 1 covers these five. Every why-line carries **both** halves: **COST** (what the answer
changes about the spend) and **COVERAGE** (what the answer changes about what you get to see).
A dimension priced without its coverage consequence teaches nothing, and a dimension covered
without its cost is how a 2cr call becomes a surprise.

1. **Goal** — what decision does this research feed? (pick a competitor to counter, write a
   launch, price an offer, win a pitch.)
   **COST:** a decision-shaped goal usually needs one play, not three — the biggest single lever
   on the bill. **COVERAGE:** it names the artifact, so we can say up front what the output will
   and will not answer.
2. **Subject** — whose accounts? Named handles and URLs, a client, a competitor set, or a whole
   niche with no names yet.
   **COST:** named handles resolve on `profile` (**1cr most platforms, 5cr on LinkedIn**) and
   per-platform `search` calls; "the whole niche" needs discovery calls before any of that.
   **COVERAGE:** with no named subject we can only describe the category, never their actual
   content.
3. **Platforms** — which platforms genuinely matter for this question?
   **COST:** most known platforms land on `/v1/{platform}/search` at **1cr** (5cr on the retail
   ones) — the bottom rung of Ground rule 6. **LinkedIn and X have no 1cr rung: 5cr is their
   floor**, Facebook has no general content search (its `marketplace` and `events` searches are
   1cr but narrow), and Snapchat has none at all. "Everywhere" is the 20cr sweep.
   **COVERAGE:** every platform dropped is a named blind spot; every one added is another rung.
   Say which, out loud.
4. **Depth & freshness** — a quick read or a defensible audit? A snapshot of right now, or a
   trend across time?
   **COST:** depth is the metered dimension — `max=`, `runs=`, `preset=`, page counts. It is
   where a 2cr call becomes 160cr. Freshness across time means repeat runs, so quote per run.
   **COVERAGE:** shallow finds the pattern, deep proves it; one pull cannot show a trend.
5. **End product** — what do they hold at the end? (pain-language doc, ad teardown table,
   offer-ladder map, ICP one-pager, dated radar note.)
   **COST:** the artifact sets the stopping point. Without one, "more data" has no natural end
   and neither does the spend. **COVERAGE:** it fixes which fields the pull must contain, so
   nothing has to be re-bought on a second pass.

**A dimension may be left open, never guessed silently.** State the reading you took in the plan
you re-show, and get a yes on that plan before the run starts. Do not lean on the cost gate to
catch it: Ground rule 4 only asks for an explicit yes from 10cr up, so on a 1cr or 5cr play
nothing downstream will.

### How to ask (popup first, text second)

- **Fire `AskUserQuestion`.** The questions arrive as options they click instead of a wall of
  text to parse. That is the normal path here — not an enhancement, not a bonus.
- **Never hard-require it.** If the tool is not available on this surface, ask the same questions
  as a short numbered list: same wording, same why-lines, same round rules. Only delivery changes.
- **3–5 questions per round.** More than five is an interrogation. The popup itself carries at
  most 4 per call, so a round of five becomes two consecutive batches, not a trimmed round.
- **At most 3 rounds.** Round 1 covers every fuzzy dimension. Rounds 2 and 3 fire only if the
  answers opened new gaps, and ask only about what is still fuzzy.
- **Never re-ask something already answered** — not in a later round, not in a later play, not
  after an escalation from `onboarding`.
- **Re-show the plan and the price between rounds.** They watch the plan sharpen and the number
  move as they answer. That visible before → after is the lesson.
- **One question per real ambiguity.** If the answer would not change what gets built or what it
  costs, do not ask it.
- **Batched, never scattered.** Ask a round together; never drip one question per turn.
- Keep every question simple yet fairly detailed, roughly a 7th-grade reading level, and short.
  Teach while assisting — never lecture.
- In a popup the why-line rides in the **option's description**, not in a separate chat line, and
  it says what choosing that option means for their result. In the text fallback it becomes the
  one-line gloss under the question. Nothing is lost either way.
- Frame the why as what it unlocks — *"here is what this buys you"*, never *"you forgot this."*

**A dispatched subagent cannot ask.** Tool availability follows the agent's role, not the
environment: a subagent has no `AskUserQuestion` even when the parent session does. An agent that
hits a real decision **returns the open question** and the main session asks it, then
re-dispatches. If a dispatch prompt contains the words "ask the user", it is wrong.

**Headless or unattended (`claude -p`, a scheduled run, a loop tick) — STOP AND REPORT on any
paid tier.** Nobody is there: the popup cannot fire and text will not be read. Report exactly
what you needed and what the run would have cost, and exit without spending.
**Proceeding on a default is FORBIDDEN wherever a default would spend.** An unattended run may
continue by itself only while every remaining step is 0cr — a free WebSearch pass or
`GET /v1/credits/balance`. And never block silently on an answer that cannot arrive: a run that
stalls on a question is a run that did nothing, and nobody finds out until they check.

### After the rubric on the no-key path — route, then order the menu

When you price the plan the rubric shaped, lead with the **strongest** option that fits the goal, not
the cheapest one — cheapest is a rung on the ladder, never the recommendation by default.

**Every research ask reaching the pitch is routed first.** Dispatch
`agents/research-router.md`, never on a named call, the express lane, a free-only ask, or a
suggest-hook notice, handing it the absolute paths of what it reads:
`${CLAUDE_PLUGIN_ROOT}/skills/research-plays/curated-workflows.json`,
`${CLAUDE_PLUGIN_ROOT}/skills/research-plays/references/packages.json`,
`${CLAUDE_PLUGIN_ROOT}/hooks/costs.json` and the
`${CLAUDE_PLUGIN_ROOT}/skills/socialcrawl/references/` folder. Unsure: questions with why-lines, one popup call, one round, sized by
`### How to ask` above. Headless, it stops and reports. Otherwise two
or three priced options, the curated play leading when it fits, the strongest present, one
reaching where the curated play does not; the go paragraph in SKILL.md fires the last popup and
its free-path fourth choice.

**A "what are people saying" ask always gets the sweep.** For an ask the `people_saying` row in
`packages.json` fits (what people say, feel or complain about a topic, brand or person, a named
platform or not), the menu always lists `search-everywhere`, the universal search (one 20-credit
call across up to 17 sources), usually as the recommended first option; the deeper platform pulls
(a named platform's own search or comments, Reddit, YouTube) come after it. Reddit is an option,
never the default.

**The menu is a set of options, not a ladder.** Show the tiers that could answer the question
next to each other, each with its own price, so they can compare. Which one leads is the
ordering rule's call, at the top of this section — read it there. One question decides what
order the rows are listed in:

> *"Do you need what real people posted on social platforms, or is a summary of what's published
> on the web enough?"*

Social voice puts tier 1 at the top. Published web puts tier 0 and tier 0.5 at the top.
That answer is how *fits the goal* gets read here — the same ordering rule, not a second one.
**Rows are never removed** — not by that answer, not by a thin balance, not by anything else.
The question sorts the menu; it never shortens it.
