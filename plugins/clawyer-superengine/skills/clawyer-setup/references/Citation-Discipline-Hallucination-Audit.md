# Citation Discipline — Verify-Against-Source Pass
# (Hallucination Audit Doctrine)

> Companion to CLAUDE.md Rule 5. Mandatory pass before any document leaves the firm.

## Why this exists

In live use of this firm, three hallucinations were caught in a single audit pass — each one a named person, a role, or a holding that the firm asserted based on a filename or a memory of a prior session rather than the document itself. Filed unverified, any one of those would have destroyed credibility in front of the bench. This doctrine is the durable fix.

## The rule

**Cite-by-filename-inference is forbidden.**

A document's filename does NOT establish:

1. The names of people inside the document.
2. The roles those people held.
3. The dates referenced in the document.
4. The legal holding of an opinion.
5. The contents of a transcript page or OFW message ID.

Open the document. Verify the named person, role, and quoted language against the document text — not the filename string, not a memory of a prior session, not a re-state from a downstream summary.

## The verify-against-source pass (mandatory before any artifact ships)

For every document the firm produces that names a person, cites a holding, quotes a record, or asserts a date:

1. **Every named person** — confirm name + role against the document where the firm first encountered them. If the only "source" is a filename, the assertion is hallucinated. Strike or verify.
2. **Every quoted line** — confirm verbatim against the transcript / OFW / record at the cited page. No quote without an open-file check this session.
3. **Every cited holding** — confirm against the primary source the cite tag claims (court record, official slip opinion, statute text). If only paraphrased in a secondary source, tag `[CONFIRM BEFORE CITING]`.
4. **Every exhibit reference** — confirm the exhibit file exists at the path the firm believes, contains what the firm believes, and is the version the firm believes. No assumptions from filename alone.

## What "verify against source" means

| Assertion type | Acceptable source | NOT acceptable |
|---|---|---|
| Name of clerk / court admin / staffer | Court website, official docket | Filename, memory of prior session |
| Role of a staffer (clerk vs admin vs GAL) | Their official title in writing | Inference from where their name appeared |
| Page number of transcript | The transcript file open this session | A prior summary that referenced the page |
| Holding of a case | Slip opinion text or verified-authority memo | A blog, a downstream summary, training memory |
| OFW message contents | The OFW file open this session | A prior cross-exam draft citing the message ID |
| Financial figure | The sworn declaration open this session | A prior memo paraphrasing the declaration |

## Three hallucinations to remember (anonymized pattern, not the matter)

These are the patterns that have actually leaked into firm work; every audit watches for them:

1. **Wrong-role assertion.** The firm referred to a court staffer as the GAL because their name appeared in a filename adjacent to GAL documents. The staffer was the Chancery Clerk. Audit fix: never assert a role unless the role is in the document.
2. **Wrong-person quote.** The firm attributed a transcript line to a witness based on the position of the quote in a summary. The transcript itself attributed it to the judge. Audit fix: every quote cite-checked against the transcript file.
3. **Wrong-holding cite.** The firm cited a case for a proposition that was the dissent's view, not the holding. Audit fix: holdings are read off the majority opinion text, not off a summary.

## Where the audit runs

- Every Tier-2 (court filing) artifact before it ships to `My Case/` or equivalent.
- Every Trial-Packet rebuild.
- Every cross-exam file that names a witness.
- Every chronology / timeline that asserts a date.

## Where the audit is logged

`outputs/working/forensic/Citation-Audit_<Date>.md` — pass / fixes / strikes. Append-only.

## NEXT ACTION pattern

When the audit catches a leak, the next action is ALWAYS: strike the assertion, open the underlying document, requote against source, log the fix.

---

_Added v1.6.0 — case-agnostic. Companion to CLAUDE.md Rule 5 (Citation Discipline) and the Chief-Authority-Doctrine standing authority to update inventory + indexes after a fix._
