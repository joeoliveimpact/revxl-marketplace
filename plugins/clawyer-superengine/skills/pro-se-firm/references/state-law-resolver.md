# State-Law Resolver — establish the forum's controlling law on case load

The firm is **50-state**. No state is the default. On every case load, after the firm has the
**state and county**, it resolves that forum's controlling law and writes a **state-law profile**
into the case. That profile is what governs (see the controlling-law gate in `operating-doctrine.md`).

## When it runs
Immediately after intake captures **state + county**, before any substantive case work.

## What to resolve (write each into the case's state-law profile)
1. **Custody** — the state's standard, its factors, and its vocabulary (e.g., Texas uses
   "conservatorship: managing / possessory," not "custody"). Capture the parenting-time default.
2. **Spousal support / alimony** — eligibility, types, factors, statutory caps and duration limits.
3. **Property** — the regime (community vs. equitable) and the division standard + factors.
4. **Forum / court** — which court hears family law in that state/county, and how a self-represented
   party files there. Treat this as FIRST-CLASS: court structure and local rules vary more than
   substantive law. Flag county specifics `[CHECK LOCAL RULE]`.
5. **Procedure** — filing format, service, the temporary/pendente-lite relief vehicle, discovery
   cutoff.

## How to resolve (research discipline — HARD)
- Research from **primary sources** (the state legislature site, official court site).
- If generic search/WebFetch returns a directory page, 403, or 500, use `scripts/fetch_law.py`
  as the fallback to reach the official source.
- **Tag every item** with a certainty token:
  - `[VERIFIED — source]` — read against an official source THIS session.
  - `[CONFIRM BEFORE CITING]` — corroborated across reputable secondary sources, not yet against
    the official source. Good enough to ORIENT the client; NOT court-ready.
  - `[UNVERIFIED — DO NOT FILE]` — not confirmed this session.
- **Never fabricate** a statute number, factor list, or cap. A gap beats a wrong cite.

## Mississippi shortcut
If the forum state is **Mississippi**, the bundled MS worked example IS the resolved profile
(`albright-factors.md`, `armstrong-ferguson.md`, the chancery procedure files). Still verify any
specific cite before filing.

## Output
Write a "Resolved State-Law Profile" block into the user's `case-profile.md` (or a sibling
`state-law-profile.md`), each line carrying its certainty token. Everything downstream reads from
this block, not from any state's hardcoded law.
