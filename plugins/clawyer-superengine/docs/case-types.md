# Kinds of case

The core method is the same for every case. Setup asks which kind this is and writes the answer to
`firm.config.json` as `case_type`. That one setting decides what below is switched on. Nothing is copied or
installed by the person.

| Kind of case | `case_type` | Pack switched on | Gate before anything goes out | What is different |
|---|---|---|---|---|
| **Family** (custody, divorce, support) | `family-law` | `family-law` | the custody-premortem skill | Adds 17 family-law reference files, the custody premortem (best-interests lens) and an OCR helper for scanned filings. |
| **Tax** (IRS or a state) | `tax` | none | the legal-premortem skill | A second body of law (`federal`) is recorded and looked up too. Keep it in a **separate folder** from any family case: a tax agency may hand what you send it to the other party. |
| **Business, contract or money dispute** | `business` | none | the legal-premortem skill | Uses the breach-analyzer skill and the contract-reviewer agent. The 15-reviewer council runs on court orders, filed papers, anything to sign and our own filings, not on every letter. |
| **Something else** | `other` | none | the legal-premortem skill | The method works. Topics with no built-in reference are named as gaps, not guessed at. |

A **compliance and advisory** variant (a business checking its own obligations) exists but is not packaged in
this version.

## Rules that hold for every kind

- One matter family per folder. Do not mix unrelated cases.
- A task tracker holds tasks only. No case facts, names or dollar amounts tied to a party.
- Every fact carries a tag: `[CONFIRMED]`, `[CLIENT-STATED]`, `[UNVERIFIED]` or `CONFIRM-BEFORE-CITING`.
- Nothing goes outward while the premortem shows an open P0 or P1.
- The law that applies is the law of the state in `firm.config.json`. Built-in Mississippi material is an
  example of what to look up everywhere else.

## How a pack works

A pack is a folder of reference files inside the plugin, at `packs/<name>/references/`. It is "on" when its
name is in the `packs` list in `firm.config.json`. Setup sets that list from the kind of case. To change it
later, the person says "switch on the family-law pack" and Claude edits the one line.
