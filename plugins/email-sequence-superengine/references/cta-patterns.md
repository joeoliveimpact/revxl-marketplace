# CTA Pattern Library + Skill-Bucket Map

Source: Email Nurture Architecture Research (per-type CTAs + One-Action rule + subject/preview hooks)
+ Vault/Notebook synthesis (reply-as-content, throwaway CTA, one-click, 80/20). The prime CTA patterns,
each tagged with PITCH intensity + which generator(s) it belongs in. Generators pull the CTA that matches
the email's lever + pitch level.

## CTA mechanics (govern every CTA, all campaigns) — vault-hardened (Settle + Hormozi)
- **One-Action rule** — ONE destination per email; repeat the same CTA up to 3x. Never two competing asks. (Settle: "get them to click and BUY, not read your next email"; Hormozi: lock 1-2 CTAs, hold steady.)
- **Primary CTA at the body close, NOT the P.S.** — in email the P.S. is skimmed as a pitch slot (Settle, "poo-pooing the PS"). BUT the P.S. is high-attention real estate (REVUP) — use it strategically and often for subplot / social proof / curiosity-loop / personality / a soft nudge toward the body CTA. Strategic non-CTA device, not the ask itself.
- **No "no" questions** — never phrase so the reader can mentally answer "no."
- **Direct > loopy for the actual ask** — open-loop/curiosity is fine for value emails; the invite/pitch uses a direct, unambiguous CTA (Settle: aggressive direct CTA out-sells teasing).
- **Soft = throwaway CTA** — even a bare link at the close with no hard ask outperforms a no-sell email (Settle/Wilkerson case: $5,112 from a lazy bottom link). "If it's a fit, the door's here."
- **Takeaway / disqualify framing** (soft) — filter out bad-fit readers first ("if you're thinking of buying, don't... this is for people already X"), THEN drop the link. Lowers reactance; reader doesn't feel hunted.
- **Cold / text-only sends** — prefer a reply-ask over a link (deliverability + engagement); use at most one link.
- **"Sell in every marketing email" is about the SEQUENCE, not every email** (Settle, gated by `{{PITCH_FLOOR}}`) — soft-floor = the sequence always sells (~1 invite per 4); a soft/throwaway CTA on a value send is OPTIONAL, not mandatory. value-first = pure-value emails freely allowed. Reading soft-floor as "a CTA on every email" is the plugin's #1 drift — don't.
- **HARD NO-PITCH CONTEXTS (override the floor — NO `soft` or `hard` ask; breadcrumb/anticipation pointers fine):** (1) the FIRST email back to a cold/dormant/reactivation list — pitching an offer burns deliverability, BUT a breadcrumb ("more on YouTube") or anticipation teaser ("community's coming") is fine and encouraged; (2) precall (booked); (3) onboarding (bought); (4) permission-to-exit sends (no-show E3, winback sunset). On these, no soft-offer/hard CTA — the throwaway link is what's barred, not a no-ask pointer.
- **Scarcity/deadline patterns (#10 Deadline-Scarcity, #11 Binary stay/go) require a REAL, coach-confirmed limit** — NEVER fabricate "X spots left," a fake countdown, or an unapproved promo. Fake scarcity is an FTC dark pattern + a 2026 trust-killer (see copy-format-rules honesty floor). No real deadline → drive with cost-of-inaction instead. Always SUGGEST the scarcity + ask the coach to confirm the true number; never invent it.

## The Soft-Pitch Gradient (pitch levels — the dimension the CTA expresses)
Five tiers by how much commitment the CTA asks for. Source: Ben Settle vault (Soft Sell / Throwaway CTA, Takeaway Selling, Content Repurposing Across Channels) + REVUP Skool launch notebook (anticipation/teaser + YouTube goodwill bridge). The middle two are the tier the plugin used to skip.
- **none** — pure value/relationship; non-sales (read, reply, log in). Asks nothing.
- **breadcrumb** (pointer) — zero-commitment direction to where else you are: "more on YouTube," "I'm on IG," "deeper how-to on the channel." Points, does NOT ask for a conversion. [vault: Content Repurposing / goodwill bridge]
- **anticipation** (teaser) — builds future demand, asks nothing now: "keep an eye out, the community's opening soon," "watch your inbox Thursday." [notebook: "third place" anticipation]
- **soft** (throwaway offer) — a real but low-stakes conversion ask: free signup, resource download, a bare/lazy bottom link, takeaway/disqualify framing. Zero pressure, but it IS an ask. [vault: Soft Sell / Throwaway CTA, Takeaway Selling]
- **hard** — direct urgent ask to buy/apply/book-now; scarcity/deadline; the close.

**The line that matters:** breadcrumb + anticipation ask for NO conversion → allowed anywhere, including the hard-no-pitch contexts (a dormant re-intro can absolutely end with "more on YouTube" or "the community's coming"). soft + hard ARE asks → barred from the first dormant send (see below).

## Prime CTA patterns

| # | Pattern | What it is | Pitch | Primary skill buckets |
|---|---------|-----------|-------|----------------------|
| 1 | **Reply-Trigger Word** | "reply CONFIRMED / MYTH / AGREED" — micro-commitment + engagement + deliverability signal | none/soft | precall E1, warm (lesson), onboarding (ROE), no-show E1 |
| 2 | **Calendar-Sync + Confirm** | add to calendar + active confirm | none | precall E1 |
| 3 | **Curiosity / Open-Loop Read** | click to a breakdown/video; value, no ask toward offer | none | warm (lesson), launch (curriculum/case/origin), post-call (case study), video |
| 4 | **Resource Download** | grab a checklist/protocol — reciprocity lead-in | none | winback E1, warm, no-show (resource) |
| 5 | **Portal / Access Login** | log in, access the thing they bought | none (transactional) | onboarding E1 |
| 6 | **One-Click Micro-Survey** | pick the option that fits — dialogue activation | none/soft | winback (survey) |
| 7 | **Book-the-Call** | button/link to book a call/audit/kickoff — core conversion | soft → hard | warm (invite), post-call, no-show, video, onboarding E1 |
| 8 | **Self-Service Rebook Link** | low-pressure "here's the link, grab a time" | soft | no-show (breakup), post-call (breakup) |
| 9 | **Apply / Submit (gated)** | application as friction-filter (qualification) | hard | launch, post-call (timeline check) |
| 10 | **Deadline / Scarcity Secure-Spot** | "secure your spot before [deadline]" — urgency close | hard | launch D6/D7 |
| 11 | **Binary Stay/Go** | "confirm you want to stay or we remove you" — loss aversion | hard (value-framed) | winback (sunset) |

## Per-bucket CTA + pitch profile (how it sequences inside each generator)

| Generator | CTA arc (by email) | Net pitch profile |
|-----------|--------------------|-------------------|
| **precall-nurture** | E1 reply-trigger + cal-sync · E2 open-loop read · E3 resource (pre-work) · E4 access link | **none** (show-up, not sell) |
| **precall-video** | single soft book-frame ("show on time, ready to decide if it's a fit") | **soft** |
| **warm-nurture** | lesson = reply-trigger/open-loop (+ soft throwaway CTA under soft-floor) · story = open-loop + soft · invite = book-the-call | soft-floor: every email ≥ soft, ~1 hard-ish invite per 4 · value-first: lesson may be pure `none` |
| **launch** | D1 soft apply · D2-D4 open-loop read · D5 apply · D6 deadline secure · D7 deadline secure | **escalates** soft → hard |
| **no-show-recovery** | E1 reply-trigger + rebook · E2 resource + rebook · E3 permission · E4 self-service rebook | **soft** (empathy; never hard) |
| **post-call-followup** | E1 reply (confirm alignment) · E2 open-loop case · E3 gated adjust/quick-call · E4 self-service rebook | **soft** → E4 **soft-hard** breakup |
| **winback** | D1 resource download · D7 one-click survey · D14 binary stay/go | **none/soft** → **hard** sunset |
| **onboarding** | E1 portal login + book kickoff · E2 apply (intake) · E3 reply AGREED · E4 resource · E5 reply | **none** (retention) |

## Use
Each framework's email table cites the CTA pattern # + pitch for its row. The generator writes the CTA in the
coach's voice using the matched pattern, obeys the One-Action rule, and the checklist verifies pitch matches
the framework + 80/20 holds across the sequence.
