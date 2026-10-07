# Execution contract — running a picked option without surprising anyone

A pitch ends with a pick, and the pick changes what the plan is. Before it, the plan is a
proposal. After it, the plan is an **allowlist**: the exact calls this run may make and the
ceiling it may not pass.

Plain version — **they agreed to a list and a limit. Run the list, watch the limit, show them
the receipt.**

## 1. Only the calls on the allowlist

Run the picked option's `endpoints[]` literally, as written. **Nothing improvised mid-run** — not
a quick extra lookup, not a cheaper substitute, not a deeper variant of a call that IS on the
list. An endpoint absent from `endpoints[]` is not called, however obvious it looks once the
first results land.

A better idea mid-run is a new pitch, not a new call: stop, say what you would add and what its
quote row says, and let them pick again. Parameters may move within what a leg's `role`
describes; the endpoint may not.

**Each paid call is one plain `curl` in its own Bash call**, writing to a literal `-o` path
(`-o /tmp/sc-<leg>.json`, never `-o "$d/x"`), with the header the `socialcrawl` skill's API Key
labels give. Read or process the file (`jq`, python) in a separate Bash call: the typed-out
path keeps the call countable and its output readable. The guard is silent only inside its plain
grammar; set-up (`d=…;`), a variable in the path, a loop, or a pipe into any other program than
`jq` / `head` is outside it and asks every time.

## 2. A ledger snapshot before, a diff after each step

`hooks/ledger.mjs` reads the account's own transaction log, which is the only place the real
charge exists.

- **Before the first call** — `node hooks/ledger.mjs snapshot --out <before.json>`
- **After each step** — `node hooks/ledger.mjs diff <before.json> --plan <picked-option.json>`

Each diff attributes every new transaction row: by `request_id` where the row carries one, by
endpoint where it does not. Rows on the allowlist are LANE. Everything else is EXTERNAL —
another session, a scheduled job, a second terminal spending on this same account. **EXTERNAL
rows are tagged and reported, never failed**, and they never count against this run's ceiling.
Failing a run over a charge it did not make teaches everyone to ignore the exit code.

## 3. Abort at the ceiling

The ceiling is an abort control, not a prediction. When the diff **exits 2**, the netted lane
total has passed the picked option's ceiling: **stop the run. Nothing further is called** — no
one more page, no finishing the step already in flight. Report where it stands and re-pitch
what is left.

The ledger's own calls are free and sit outside the ceiling. It only ever touches `credits/*`,
which is account meta and is not billed, so reconciling never moves the number it is
reconciling.

## 4. Report quoted against actual, including when they are equal

Every lane row prints as quoted, actual, and the delta between them — **even when the delta is
zero**. The debrief's *"what it cost"* beat reads this diff and nothing else.

A run that landed exactly on its quote is the most useful line in the report: it is the one that
shows the quote can be trusted. Suppressing it because "there is nothing to say" is how a quote
quietly stops being checked, and a quote nobody checks is a guess. Where a leg carries no quoted
figure the ledger prints the actual and declares the gap as a LIMIT rather than inventing one —
it prices nothing itself. The numbers behind a quote live in the option's quote row and in
`hooks/costs.json`.

## 5. The guard's session cap is not the mechanism

`credit-guard.mjs` adjudicates a command before it runs, from the command string, and asks only
at a session cap step, on a call it can't count, or on a command that is not a plain `curl`.
That is a **spending gate, not a
reconciliation**: it counts quoted worst cases, it cannot see what was actually billed or a
refund, and a cap ask answered yes reconciles nothing at all. **The plan and this ledger are
the mechanism.** Mistaking the session cap for the check is the failure this contract exists to
prevent.

The ledger is itself a network caller the guard cannot see, because an import never becomes a
shell command. So the restriction is enforced inside `hooks/ledger.mjs` in code: every URL is
built by one function that throws on any path outside `/v1/credits/` before a request is
constructed. **`ledger.mjs` may call `credits/*` and nothing else.**

## If the live reconciliation was waived

**LIMIT — stated, not implied.** Where the live reconciliation step was waived, `hooks/ledger.mjs`
has never been reconciled against a live charge. Everything above is proven on fixtures built
from the vendor's published transactions schema, which is the only archived shape there is.

What that buys: the attribution, the refund netting, the ceiling abort, the pagination and the
credits-only invariant are all exercised, each against a mutation that breaks it. What it does
not buy: proof that a live response matches that schema field for field. Until that
reconciliation happens this file and the CHANGELOG both carry this LIMIT, and where a diff
disagrees with the vendor's own balance, believe the vendor.
