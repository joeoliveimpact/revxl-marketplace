# Signature Bits ... making humor objective

Don't ask an AI "is this funny." Score lines on OBSERVABLE signals from the source material:

## The two signals
- **Reaction signal** ... the OTHER party reacts: "haha", "lol", "that's hilarious", "stop it", `[laughs]`, audible laughter in the transcript. **Riff-alongs count too** (the other party extends/plays along with the joke) ... weaker than an explicit laugh; note the evidence strength (`explicit` vs `riff-along`). Funny by evidence, not opinion.
- **Repetition signal** ... the same bit reused across multiple calls/posts = a rehearsed signature, not a one-off.

| Signals hit | Status |
|-------------|--------|
| Both | **Canon candidate** ... top of the queue |
| Reaction only | candidate (landed once ... may be situational) |
| Repetition only | candidate (they lean on it ... audience reaction unproven) |
| Neither | not a bit; leave it in the transcript |

## Deployability gates (candidacy ... check BEFORE filing)
A line only becomes a candidate if it survives both gates. These are mechanical, not taste:
- **Portability:** the line + its setup must not reference call participants, the operator, or session context ("you can't helicopter for Joe" names the other party ... not a candidate; it stays in the transcript).
- **Self-contained setup:** the stored setup must be reproducible in content. You-had-to-be-there context = not a candidate.

## Canon floor
Canon requires the repetition signal across **≥2 independent sources**. A single-source brain therefore holds zero canon ... that honesty is the feature, not a shortfall to paper over.

## Store per bit
- The line (verbatim) + the setup/context it needs
- Reaction evidence (quoted) + **evidence strength (`explicit` | `riff-along`)** + frequency count (which calls/posts)
- Tag: `personal-signature` | `topical-to-niche` | `evergreen`
- Status: `candidate` | `canon`

## Canonization: parked (and human-in-loop when it returns)
No consumer engine currently reads canon bits, so do NOT run a canonization review ... file candidates silently and note "parked for a future bits engine" in the run report. When a consumer exists and canonization resumes, the hard rule stands: the system PROPOSES candidates with their evidence, the human thumbs-up to canonize. No approval, no canon, no deployment. Consumers deploy the client's ACTUAL jokes ... never invent new ones, never punch up old ones.

## Attribution guard
A bit belongs to the person who SAID it (per speaker-separation). Cross-contamination is the one unforgivable failure: the operator's recurring analogy showing up in a client's brain means the brain is lying about who the client is.

## Topical vs evergreen routing
An evergreen bit (works any week) → signature-bits.md. A topical joke (this week's news, a moment from Tuesday's call) → weekly-content-bank.md with a date, where it ages out on the 7-day TTL.
