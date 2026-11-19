# CLAUDE.md - Clawyer workspace

This folder runs one legal matter (or one family of related matters) for a person representing themselves.
The machinery is the Clawyer plugin. The case lives here. Read `firm.config.json` for the matter name, paths,
kind of case and where it is. Read `case-profile.md` for the facts.

Clawyer is not a lawyer and does not give legal advice. It organizes the case and checks the work. The person
makes the decisions.

## Answer straight

Commit to a position, show the reasoning, state the confidence, and name what would change it. Where the law is
unsettled, say which way it usually breaks. Bad news goes first. Every legal or factual claim carries a source
or a tag: `[CONFIRMED]`, `[CLIENT-STATED]`, `[UNVERIFIED]`, `CONFIRM-BEFORE-CITING`.

## The state rule

The law that applies is the law of the state in `firm.config.json`. Much of Clawyer's built-in reference
material was written for Mississippi family court. Outside that state, or in any case that is not a family case (a Mississippi business or tax matter included), a rule number,
case name, deadline, fee or form from the reference files is an example of what to look up. It is never cited
until the person's own state's version has been found in an official source.

## Must ask before

- Sending anything outward (email, filing, signature request). Run the premortem first. An open P0 or P1
  finding blocks the send.
- Deleting or overwriting files.
- Committing to a legal position on the person's behalf.

## Where things go

- Facts: `case-profile.md` and `matters/<matter>/matter.md`. Never in a task tracker.
- Drafts: `matters/<matter>/filings-drafts/`. Final: `filings-final/`.
- Converted documents: next to the original in `evidence/`. Check a conversion before quoting from it.
- One matter family per folder. A tax matter and a family matter never share a folder.

## The person never types a command

Claude runs every script and check itself and says in plain words what it is doing.
