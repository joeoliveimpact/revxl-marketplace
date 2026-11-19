# Case Profile — TEMPLATE

> This is the blank template the skill uses to onboard a new user. The firm reads the user's **own** filled-in copy
> (saved as `case-profile.md` in their working directory) and applies its facts to every task. If no filled profile
> exists, the skill runs intake — asking these questions — and writes the user's `case-profile.md`. **Never put one
> user's facts into the shipped template, and never use another case's facts.**
>
> Fill every field you can. Mark anything uncertain `[CONFIRM AGAINST SOURCE]`. Leave a field blank only if it truly
> doesn't apply. Tag the minor child by **initials only** — that is the only form used in filings.

## Jurisdiction & court
- **State:** [your state] *(REQUIRED — asked first; drives every legal frame via the State-Law Resolver)*
- **County / judicial district:** [your county] *(REQUIRED — asked first; drives the court + local rules)*
- **Court:** [e.g., Chancery Court]
- **Cause / case number:** [ ]
- **Judge / Chancellor:** [ ]
- **Local time zone:** [e.g., America/Chicago]

## Parties
- **You (party designation):** [Plaintiff / Petitioner / Defendant / Respondent] — **representing yourself (pro se):** [yes/no]
- **Your full name / service address / phone / email (for signature blocks):** [ ]
- **Opposing party (full name):** [ ]
- **Opposing counsel (name, firm, service address):** [ ]
- **Guardian ad Litem (if any):** [name; appointment basis — mandatory (abuse/neglect) or discretionary]

## The child(ren)
- **Initials used in filings:** [each child's initials, e.g., A.B.] *(initials ONLY — never a child's full name in any filing; one entry per child)*
- **Age / DOB:** [ ]
- **School / grade:** [ ]
- **Primary residence currently:** [ ]
- **Medical/special needs on record:** [ ]
- **Decision-making / medical-info access issues:** [ ]

## Posture & key orders
- **Marital status / divorce status:** [e.g., divorce granted [date]; issues reserved]
- **Current operative order(s):** [date + the operative terms — custody type, decision-making scope, physical custody, parenting-time schedule]
- **Oral rulings vs. written orders — any discrepancies to watch:** [ ]
- **Next hearing / final-trial date:** [ ]

## Governing legal frames (resolved per state)
- **Custody / spousal support / property:** resolved on load by the State-Law Resolver from your state's law.
  *(Mississippi example: Albright custody, Armstrong support, Ferguson property.)*
- **Local rules to confirm:** [your county's exhibit/discovery/filing specifics] `[CHECK LOCAL RULE]`

## Issues in play (check all that apply)
- [ ] Custody / parenting-time
- [ ] Decision-making authority
- [ ] Child support
- [ ] Alimony / rehabilitative support
- [ ] Property / marital home
- [ ] Retirement division
- [ ] Discovery
- [ ] Enforcement
- [ ] Other: [ ]

## Goals (priority order)
1. [ ]
2. [ ]
3. [ ]

## Strongest evidence on hand
- [ ] [e.g., co-parenting-app (OFW) logs, message history, financial records, contradiction documentation, photos]

## Your own vulnerabilities (for defensive prep — be honest)
- [things opposing counsel will use against you on cross]

## Opposing party / counsel patterns
- **opponent_profile:** [normal / high-conflict] *(set by the High-Conflict Opponent Protocol in `firm-operating-system.md` — when high-conflict, the protocol stays active across sessions and shifts every specialist's posture)*
- [e.g., delay tactics; drafts orders that expand scope; specific documented violations; DARVO; document games; intimidation/rush]

## Deadlines & money
- **Discovery cutoff / response windows:** [`[CHECK LOCAL RULE]`]
- **Filing fees / in forma pauperis status:** [ ]
- **GAL fee owed:** [ ]
