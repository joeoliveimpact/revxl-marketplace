# Glossary — the gloss bank (both vocabulary axes, two tiers)

Canonical glosses skills pull from per teach level (`teach-mode.md`).
**Skills never improvise a gloss for a term listed here** — consistent,
corrected once.

Two tiers:
- **One-liner tier** (Sections 1–2) — used at `learning`, and at `new` for
  terms with no deep entry.
- **Deep tier** (Section 3, `new` ONLY) — the ~25 highest-stakes Meta terms:
  plain-English explanation + analogy + worked numeric example + "what this
  means for you." At `new`, a Section-3 term's FIRST use in a session gets
  its deep entry (swap in the coach's own numbers from state when present);
  later uses that session, the one-liner. Deep tier never renders at
  `learning`/`pro`.

## Section 1 — Claude & plugin terms

| Term | Gloss |
|---|---|
| skill | One packaged ability of this plugin — you fire it by saying its trigger phrase |
| plugin | The whole toolkit installed into Claude — this one is your Meta-ads engine |
| trigger phrase | The exact words that start a skill (listed in every Next-Moves block) |
| slash command | Typing `/` + a skill name — same as saying the trigger phrase |
| Next Moves | The numbered "here's where to go now" block ending every skill — your road, never a dead end |
| the compass | The `what's next` skill — reads your journey file and points you at the best next move, anytime |
| journey / state file | Your per-brand progress record on this computer — every skill reads it so nothing gets asked twice |
| marker file | A small install receipt other RevXL plugins detect — how the engines find each other |
| config | Your saved answers from setup — persists across plugin updates |
| brand slug | Your brand name normalized for file paths (lowercase, hyphens) — shared with your other RevXL engines |
| brand brain / voc | Your captured voice + customer-language files (`~/.claude/revxl/<brand>/voc/`) — what makes copy sound like YOU |
| voice confidence | How well-fed the brand brain is — "low" means copy is honest-but-generic until capture runs |
| teach level | The explanation dial (new / learning / pro) — change it anytime by saying "teach level" |
| the Brain | Joe's living Meta-ads knowledge vault, queried live over the internet — fresher than anything bundled |
| Brain key | Your `vk_` subscription key that opens the Brain — no key, the plugin runs on built-in references |
| MCP / connector | A live hookup between Claude and an outside tool (like Ads Manager) — optional; paste-your-numbers always works |
| OAuth | Signing in with your own account (Meta, Google…) so Claude connects without you ever sharing a password |
| scope | What a connection is allowed to do — read-only "look but don't touch" vs write "can make changes"; this engine stays read-only in v1 |
| CRM | Your customer database (GoHighLevel, Kajabi, ClickFunnels…) — where leads and clients live; the source of truth Meta can't see |
| credit checkpoint ✋ | A hard stop before anything that spends your API credits — you approve the cost first |
| degrade / fallback | What the plugin does when a live service is down: proceed on bundled knowledge + tell you plainly |
| artifact | A saved deliverable file (campaign plan, script, question set) — yours, on disk, reusable |

## Section 2 — Meta-ads terms

### Machine + targeting
| Term | Gloss |
|---|---|
| Andromeda | Meta's ad-delivery AI (2025+) — it reads your CREATIVE to decide who sees it; the ad is the targeting |
| Advantage+ | Meta's automation suite (audience, placements, campaigns) — the defaults you stop fighting |
| broad targeting | Location + age floor + language only — you hand WHO to the machine and steer with creative + signals |
| interest targeting | Picking hobby/topic audiences by hand — legacy; constrains the machine now |
| lookalike (LAL) | "Find people like my list" audiences — legacy as a ladder; Meta expands past them anyway |
| retargeting | Re-showing ads to people who engaged — now handled INSIDE one campaign, not a separate one |
| placement | Where the ad appears (Feed, Reels, Stories…) — leave automatic |
| frequency | Average times one person saw your ad — above ~2.5 on cold traffic means fatigue is coming |

### Structure + money
| Term | Gloss |
|---|---|
| campaign → ad set → ad | Meta's three-layer container: goal → budget/audience → the creative itself |
| objective | What you tell Meta to get you (Leads / Sales) — never traffic or awareness for coaches |
| CBO | Campaign Budget Optimization — one budget at the top, Meta spreads it (analogy: one tank, Meta drives) |
| ABO | Ad-set Budget Optimization — you set each ad set's budget by hand |
| CPL / CPQL | Cost per lead / per QUALIFIED lead — the second number is the one your business feels |
| CPA / cost per result | Cost per conversion event — whatever "result" your objective chases |
| CPM | Cost per 1,000 impressions — a weather report, not a decision metric |
| CTR | Click-through rate — % who clicked; explains WHY, never decides |
| ROAS | Return on ad spend (revenue ÷ spend) — Meta's version is incomplete for coaches; trust the CRM |
| MER | Marketing efficiency ratio — TOTAL revenue ÷ TOTAL ad spend; the honest big-picture number |
| nCAC | New-customer acquisition cost — prospecting spend ÷ NEW clients; catches "great ROAS, no new clients" |
| breakeven ROAS | The ROAS where you stop losing money — computed from YOUR price and close rates |
| hard deck | Your preset budget floor — bad-day cuts never go below it (analogy: minimum safe altitude) |
| raise-in-place | Scaling by nudging the SAME campaign's budget ≤20% every 2–3 days — never duplicating it |
| duplicate-to-scale | Copying a winning campaign to "scale" it — the anti-pattern: it resets learning and makes your copies bid against each other |
| wobble | The 1–2 days of worse numbers right after a budget raise — normal re-learning; judge the 7-day average after, never raise-day |
| ceiling | The spend level where a proven campaign starts decaying toward breakeven — the unlock is fresh creative, not more budget |
| cost cap | A bid ceiling telling Meta "never pay more than X" — an advanced brake, $300+/day territory |
| value rules | Bid adjustments (+/-%) on segments YOU know are worth more — injecting CRM knowledge Meta can't see |
| storytelling metric | A metric that explains WHY a result moved (CTR, CPM, frequency, hook rate) — diagnostic only, never decides an action on its own |

### Signals + tracking
| Term | Gloss |
|---|---|
| Pixel | Meta's browser tracker on your pages — sees what visitors do (until browsers block it) |
| CAPI | Conversions API — your server tells Meta directly what happened; the reliable half of tracking |
| event_id dedup | The matching ID that stops Pixel + CAPI double-counting the same conversion |
| one-click CAPI | Meta-hosted CAPI setup (2026) — no developer needed; check for double-counting after enabling |
| AI-assisted Pixel | Meta's auto-scraping of your page data (2026, auto-ON) — review the setting on every account |
| conversion event | The action you're optimizing toward (lead, booked call, purchase) |
| qualified event | A conversion fired ONLY when a lead passes YOUR bar — teaches Meta to find buyers, not tire-kickers |
| EMQ | Event Match Quality (1–10) — how well your events identify real people; direction matters, decimals don't |
| Events Manager | Meta's tracking dashboard — where Pixel/CAPI health lives |
| attribution window | How long after a click Meta claims credit (7-day click standard) — Meta can't see past it; your CRM can |
| learning phase | Meta's calibration period after launch/big edits — touching the campaign restarts it |
| learning limited | Meta's label when conversions are too few to exit learning — a NORMAL state coaches profit in |

### Creative + testing
| Term | Gloss |
|---|---|
| distinct concept | A creative changing pain point, avatar, format, OR awareness level — not a word swap (the machine bundles near-twins) |
| PDA matrix | Persona × Desire × Awareness grid — how you generate genuinely distinct concepts |
| awareness level | How aware the viewer is of their problem/your solution — decides what the ad must say first |
| hook | The first 1–3 seconds/lines that stop the scroll |
| hook rate | 3-second views ÷ impressions (~30% healthy) — a storytelling metric |
| hold rate | 15-second views ÷ impressions (~7–8%) — did they stay past the hook |
| creative fatigue | A winner wearing out (rising CPM/frequency, decaying CPL) — replaced, not edited |
| Creative-Testing Tool | Meta's native ad-level A/B ("Set Up Test", up to 5 variants, clean splits) — the home for micro-variants |
| dimensional swing | Testing across a big axis (15s UGC vs 90s VSL vs static) — what real tests look like at coach spend |
| UGC | User-generated-content style — phone-shot, native-feeling footage |
| VSL | Video sales letter — the 90–120s+ educational sell, CTA arrives late |
| talking head | You, on camera, to camera — the coach default that outperforms polish |
| primary text / headline | The copy above the creative (125 chars visible) / the bold line under it (40 chars) |
| 5-slot copy variants | Up to 5 primary-text/headline variations INSIDE one ad — never 5 separate ads |
| safe zones | The 9:16 areas UI covers: top 14% / bottom 35% / sides 6% — keep text out of them |
| 4:5 | The feed default ratio (1440×1800) — landscape is dead for this use |
| Instant Form | Meta's native in-app lead form — low friction, needs your qualifying questions to filter |
| Ad Library | Meta's public archive of every running ad — free competitor intel |
| Post-ID (Post ID) | Running an existing organic post AS an ad — keeps its likes/comments (social proof) instead of starting from zero |

### Compliance + ops
| Term | Gloss |
|---|---|
| Special Ad Categories | Restricted ad classes (credit, employment, housing, social issues, + Financial Products since 2024) — some coaching offers trigger the financial one; always live-checked |
| C2PA / AI labeling | Meta's auto-labeling of AI-generated creative (Jun 2026+) — synthetic ads get marked; plan for the trust cost |
| rejection triage | The diagnose-appeal-fix path when an ad is rejected or an account restricted — before touching anything |
| Ads Manager | Meta's campaign dashboard — where launch and daily numbers live |
| bad-day protocol | Do nothing for 3 days (most dips self-correct); day 3 → review, cut ≤20%, never below the hard deck |
| 72h lockout | The post-launch do-not-touch window — every edit restarts learning |
| stop-loss | The preset "kill it" line for a creative (~1× target CPL spent, zero signs of life) |
| exit criteria | The measured bar for moving up a spend stage — stages advance on evidence, never impatience |
| ROI | Return on investment — what you got back vs what you put in, across everything (ROAS is the ads-only version) |
| static ad | A still-image ad (no video) — a picture with words on it |

## Section 3 — Deep tier (`new` teach level ONLY)

Format per entry: plain-English → analogy → worked example (swap in the
coach's real numbers from `targets`/`setup` when state has them) → "what this
means for you." Assume zero ads vocabulary.

### Money & metrics

**ROI (return on investment)**
Plain: did the money you spent come back with friends? Everything counts —
ad spend, your time, software.
Analogy: you buy a $100 espresso machine for your café and it sells $500 of
lattes — the machine "returned" 5× its cost.
Example: you spend $1,000 total and land one $3,000 client → you put in
$1,000 and got $3,000 back.
What this means for you: ROI is the business answer; the ads dashboard can't
see all of it — your CRM can.

**ROAS (return on ad spend)**
Plain: for every $1 you give Meta, how many dollars of sales come back. Only
counts ad spend — nothing else.
Analogy: a vending machine — put $1 in, how much comes out?
Example: $500 of ads → one $2,000 client = 4× ROAS ($4 back per $1 in).
What this means for you: Meta's reported ROAS misses late closes and
referrals — treat your CRM's number as the truth, Meta's as the claim.

**Breakeven ROAS**
Plain: the return where you stop LOSING money — the floor, not the goal.
Analogy: a lemonade stand where lemons cost 50¢ a cup — selling at 50¢ is
breakeven; anything above is profit.
Example: if $1 of ads must bring $2 to cover costs, breakeven ROAS is 2×.
What this means for you: any campaign above YOUR breakeven is profitable —
even if the number looks "low" next to guru screenshots.

**CPL (cost per lead)**
Plain: what one interested person costs you.
Example: spend $100, get 4 people raising their hand → $25 per lead.
What this means for you: cheap leads aren't the goal — leads that BUY are.
That's why we track the next term too.

**CPQL (cost per QUALIFIED lead)**
Plain: what one GOOD lead costs — someone who passed your bar (can afford
you, ready to start).
Analogy: casting a wide net catches lots of fish; you only count the ones
big enough to keep.
Example: $100 → 4 leads, but only 2 pass your questions → CPL $25, CPQL $50.
What this means for you: expect CPQL to be higher than CPL — and expect it
to FALL as Meta learns who your buyers are. This number runs your business.

**CPM (cost per 1,000 impressions)**
Plain: the rent for eyeballs — what Meta charges to show your ad 1,000 times.
Analogy: a billboard's monthly rate — it prices views, not sales.
Example: $20 CPM = 1,000 views cost $20, whether anyone clicks or not.
What this means for you: CPM is weather, not a decision — rising CPM can
hint at ad fatigue, but you never act on CPM alone.

**CTR / clickthrough (click-through rate)**
Plain: of everyone who SAW the ad, what share clicked it.
Example: 1,000 people see it, 15 click → 1.5% CTR.
What this means for you: CTR tells you the ad caught attention — it does
NOT tell you those clicks buy. It explains WHY results moved; it never
decides anything by itself.

**MER (marketing efficiency ratio)**
Plain: ALL your revenue divided by ALL your ad spend — the whole-business
scoreboard.
Example: $10,000 revenue this month, $2,000 total ads → MER 5.
What this means for you: at higher spend this replaces Meta's dashboard as
your north star, because it can't be fooled by attribution games.

### The machine

**Broad targeting**
Plain: you stop picking the audience — location, an age floor, language,
done. The ad itself finds its people.
Analogy: instead of handing flyers to people YOU guess are interested, you
put up a sign so clear that the right people stop on their own.
What this means for you: it feels wrong ("shouldn't I target moms 35–50?")
— but the machine watching 1,000 signals beats your 3 guesses. Your ad IS
the targeting.

**Pixel**
Plain: a tiny tracker on your website that tells Meta what visitors did.
Analogy: a doorbell camera for your website — it sees who came in and what
they did.
What this means for you: without it, Meta is advertising blindfolded —
it can't learn who becomes a client.

**CAPI (Conversions API)**
Plain: your systems telling Meta directly what happened ("this lead booked a
call") — server to server, no browser in the way.
Analogy: the Pixel is a postcard that can get lost in the mail; CAPI is a
phone call that always connects.
What this means for you: browsers block trackers more every year — CAPI is
the reliable half. You want both, deduplicated (so one sale isn't counted
twice).

**Qualified event**
Plain: a signal you fire ONLY when a lead passes YOUR bar — not on every
form-fill.
Analogy: teaching a puppy — reward it for the exact behavior you want, and
that's what it repeats. Reward form-fills, you get form-fillers.
Example: 20 leads, 8 pass your questions → Meta only "hears" about those 8
→ it goes hunting for more people like the 8.
What this means for you: this is THE edge for coaches. Cost per lead goes
UP; cost per client goes DOWN. That trade is the whole point.

**Learning phase**
Plain: Meta's calibration period after a launch or a big edit — it's
experimenting to find your people.
Analogy: a new barista's first week — wobbly while they learn the machine;
changing the recipe daily means they never learn it.
What this means for you: every meaningful edit RESTARTS the clock. This is
why we don't touch anything for 72 hours — patience here is a strategy, not
laziness.

**Frequency**
Plain: how many times the average person has seen your ad.
Example: 10,000 impressions on 4,000 people → frequency 2.5.
What this means for you: past ~2.5 on cold audiences, people start scrolling
past — a sign the ad is wearing out, not a dial to turn.

**CBO (campaign budget optimization)**
Plain: one budget at the top; Meta moves it to whatever is working.
Analogy: one water tank feeding several plants, and the system waters the
one that's growing.
What this means for you: you set ONE daily number and stop micromanaging —
the machine allocates better than daily fiddling does.

**Attribution window**
Plain: how long after a click Meta takes credit for a sale (7 days standard).
Example: someone clicks Tuesday, buys the following month → Meta shows
nothing; your CRM shows the truth.
What this means for you: coaching sales close slowly — Meta will
UNDER-report you. Judge on your CRM, or you'll kill ads that are working.

### Creative

**Static ad**
Plain: a still-image ad — a picture with words, no video.
What this means for you: don't assume video always wins — a plain
text-heavy image explaining your offer often beats polished video for cold
coaching audiences, and it costs nothing to make.

**Hook**
Plain: the first 1–3 seconds (or the first line) — the part that stops the
scroll.
Analogy: a shop window — nobody comes in for the stockroom; they stop for
the window.
What this means for you: ~80% of an ad's success is decided before your
main content plays. It's why we write many hooks per ad concept.

**UGC (user-generated content) style**
Plain: ads that look like a normal person filmed them on a phone — because
that's what people actually watch.
What this means for you: your iPhone selfie video routinely beats a $2,000
production — "authentic" outperforms "polished" for coaches.

**VSL (video sales letter)**
Plain: a longer teaching video (90 seconds+) that earns trust before it
asks for anything — the ask comes late.
Analogy: a mini webinar in an ad.
What this means for you: it filters — fewer clicks, but the people who
watch 90 seconds and THEN book are far more sold before the call.

**Distinct concept**
Plain: an ad that's actually DIFFERENT — different pain, different person,
different format — not the same ad with new words.
Analogy: lottery tickets — ten different numbers = ten chances; ten copies
of the same number = one chance.
What this means for you: Meta bundles near-twins and treats them as one ad.
Five genuinely different ideas beat fifty tweaks of one idea.

**Safe zones**
Plain: the edges of a vertical (9:16) ad that buttons and captions cover —
top 14%, bottom 35%, sides 6%.
What this means for you: text placed there literally can't be read — put
your words in the middle band or they were never seen.

### Running it

**Raise-in-place**
Plain: scaling by nudging the SAME campaign's budget up a little (≤20%)
every 2–3 days — never copying the campaign.
Analogy: turning the oven up 10 degrees vs yanking the dish into a second
oven — one keeps cooking, the other starts over.
What this means for you: duplicating "to scale" restarts learning and makes
your own copies bid against each other. Patience compounds; copies compete.

**Hard deck**
Plain: your pre-agreed budget floor — bad-day cuts never go below it.
Analogy: a pilot's minimum safe altitude — decided on the ground, obeyed in
the air.
What this means for you: you decide the floor when calm (in the math step),
so a scary Tuesday can't talk you into strangling delivery.

**72h lockout**
Plain: the do-not-touch window after launch — show up, look, touch nothing.
What this means for you: the single most expensive beginner habit is
"fixing" a 2-day-old campaign. Most dips self-correct; every touch restarts
the learning clock.
