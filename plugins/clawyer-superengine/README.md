# Clawyer

Run your own legal matter like a small law firm would, in a folder on your computer.

**Clawyer is not a lawyer and this is not legal advice.** It organizes your case and checks your work. You
make the decisions. For big decisions, check with a licensed attorney.

## Demo

_Demo placeholder. A walkthrough of a first setup lands here in a future release._

## What this plugin does

You open an empty folder, say "set me up", and answer five plain questions: your state, your county, your
court if you know it, a name for the matter, and what kind of case it is. Clawyer writes your case files into
that folder, installs the free tools it needs, and from then on works your matter the way a firm would. It
reads every paper you receive, keeps a dated timeline, and checks every court case it cites against a free
public database to catch made-up cases before they reach your papers. Court orders, filed papers, anything you are asked
to sign and your own filings go through 15 reviewers who each check one thing (the math, the deadlines, the
citations, what was slipped in, what was left out). In a family case every paper from the other side gets
that review too. It verifies before anything is relied on, and red-teams anything before it leaves.

Your case files are saved in your own folder, on your own computer. Clawyer does not upload them to a website
or a REVXL server. To work on them, Claude reads them, and Claude is an online service: the text it reads is
sent to Anthropic, the company that makes Claude, under your Claude account's own privacy terms. Looking up
the law also means searching the web. Nothing is filed, sent or signed without your yes. You never type a
command: Claude runs every step and tells you in plain words what it is doing.

Clawyer is built on **pro-se-firm v1.7.0** by Mic H. (MIT license, see
[skills/pro-se-firm/upstream/LICENSE](skills/pro-se-firm/upstream/LICENSE) and [NOTICE.md](NOTICE.md)), with
guided setup, business-dispute skills and a kind-of-case switch added on top.

## Who it is for

A person representing themselves in a US civil matter: family (custody, divorce, support), a tax problem
with the IRS or a state, or a business, contract or money dispute. Other civil matters work with the same
method and fewer built-in references.

## Skills

### clawyer-setup
**Say:** "set me up", "set up Clawyer", "get me started", "I just installed this", "start my case".

Asks the five questions, writes your case files, switches on the right case-type pack, and installs the free
document tools after one yes from you.

### pro-se-firm
**Say:** "I got served", "I got a letter from the IRS", "they owe me money", "read this order", "what do I
file next", "draft a response", "prepare me for the hearing", "is anything falling through".

The managing partner. Loads your case, puts the right specialist on each part, runs the review council and
the verification gate, and ends every answer with one next step.

### matter-intake
**Say:** "open a matter", "new case", "intake this".

Opens a new matter folder and fills in the basics from what you tell it and what your documents say.

### evidence-intake
**Say:** "add this document", "here's the contract", "ingest this", "convert this PDF".

Turns a document into text Claude can read, files it in your evidence folder and adds it to the timeline.

### matter-status
**Say:** "what's open", "what's due", "where does my case stand".

A read-only snapshot: status, deadlines and the most urgent item. It changes nothing.

### matter-close
**Say:** "close this matter", "this settled", "we're done with this one".

Records how it ended and leaves a complete record. Nothing is deleted.

### breach-analyzer
**Say:** "did they breach", "what clauses did they violate", "build the defense file".

Maps your evidence to the contract, clause by clause, and works out what it does to the money in dispute.

### legal-premortem
**Say:** "premortem this", "poke holes in this", "how would they attack this", "should I send this".

Assumes the move already failed and works backwards to find why. Serious findings block the send.

### custody-premortem
**Say:** "premortem this" in a family case, "should I file this", "should I send this to the other parent".

The family-case version of the premortem, with a best-interests-of-the-child lens. Used when the kind of case
is family.

## Agents

Agents are helpers Claude sends off to check one thing and report back. You do not call them yourself.

- **The review council, 15 reviewers** (`council-a1` through `council-a15`): each reads a document from the
  other side or the court for one kind of problem, such as whether an order matches what the judge ruled,
  whether the math is right, which deadlines it starts, and what it quietly changes or leaves out.
- **verification-partner**: checks that a fact or a citation is true before it is used. It can block.
- **legal-researcher**: looks up the law for your state and returns an answer with its sources.
- **contract-reviewer**: reads an agreement clause by clause and flags the risky parts.
- **cross-examination-builder**: builds question lists for a hearing from sworn statements already on record.

## Where your case lives

| Yours, in your folder | The machinery, in the plugin |
|---|---|
| `firm.config.json` (state, county, matter name, kind of case) | skills, agents and hooks |
| `case-profile.md` (your facts) | reference files and case-type packs |
| `matters/<your-matter>/` (timeline, evidence, drafts, finals) | scripts and templates |
| `ROUTING.md`, `COUNCIL.md` and the other firm-layer files | |

Setup also writes a `.gitignore` that keeps your case files out of any online copy of the folder.

## Install

**Claude desktop app (Code tab):** open **Customize**, then **Plugins**, then **Add marketplace**, and add
the REVXL marketplace you were given. Install **clawyer-superengine**. Then open an empty folder for your case and say
"set me up".

**Claude Code in a terminal:** add the REVXL marketplace and install `clawyer-superengine` from the plugin screen, open
your case folder, and say "set me up".

## Dependencies

- Claude Code Desktop (the Code tab of the Claude desktop app). Not for Cowork or plain Chat.
- Python 3.9 or newer, a handful of free document libraries, Git, and a free reader for scanned pages
  (Tesseract). **Setup checks for each one and installs what is missing for you**, with no admin password.
  Your computer may show one or two of its own "allow this?" boxes along the way; setup tells you when to
  expect one. If something cannot be installed, setup says exactly what will not work and carries on.
- Optional: a NotebookLM research notebook of your own. Clawyer works without it.

No keys to paste and no accounts to create.

## Compatibility

| | Claude desktop app, Code tab | Claude Code in a terminal | Cowork or Chat |
|---|---|---|---|
| Skills | Yes | Yes | Not supported |
| Agents | Yes | Yes | Not supported |
| Hooks | Yes, and silent in any folder that is not a Clawyer case | Same | Not supported |
| Commands | None | None | None |

## Known limits

- **The built-in doctrine was written for Mississippi family court.** The method (intake, timeline, council,
  verification, premortem) is general. Many reference files still cite Mississippi rules, and each one says so
  at the top. In any other state, and in a Mississippi case that is not a family case, Clawyer treats those
  rules as examples of what to look up and cites nothing until it has found the rule for your state and your
  kind of case in an official source.
- **Fewer built-in references outside family law.** Tax and business matters run on the general method plus
  the breach, contract and premortem tools.
- **Some original tooling is left out of this version**: about 80 scripts and all the multi-agent workflow
  files from pro-se-firm were tied to one case. They are listed in
  [skills/pro-se-firm/scripts/NOT-SHIPPED.md](skills/pro-se-firm/scripts/NOT-SHIPPED.md).
- **Audio and video are not transcribed** in this version.
- **A compliance and advisory variant** (a business checking its own obligations) is not packaged yet.

## Privacy and failure reports

Clawyer keeps your case files in your folder and does not upload them anywhere. What does leave your
computer: the text Claude reads while it works (to Anthropic, as with any use of Claude), web searches for
the law, citation lookups (only a citation such as "384 U.S. 436" goes to a public case-law site), and
anything you choose to connect, such as a calendar or a cloud documents folder, which goes to that service.

If a step fails and Claude cannot fix it, Claude offers to write a short report for Joe at REVXL. You see the
exact text first and choose Send or Skip. Claude is told to put only the skill, the step and the error
message in it, and never a name, a case number, a date, an amount or text from your documents. An error
message can include the name of your case folder, so read the preview before you say Send. Sending needs a
REVXL key on your computer, which most people will not have, and goes through a REVXL relay server. Without a key, the report is saved as a file in your case folder and Claude tells
you where it is, so you can pass it on yourself.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE). Built on pro-se-firm v1.7.0, copyright (c) 2026 Mic H., MIT.

## Marketplace

Part of the [REVXL marketplace](../../README.md).
