# Source Ladder — where brand evidence comes from

The brain needs two different things from different best-sources: **voice** (how they sound) and **offer/avatar** (what they sell, who they help). A source can be great for one and useless for the other — rank per need. Walk top→down, take the highest tier present, blend downward.

| Tier | Sources | Voice-confidence |
|------|---------|------------------|
| **A — spoken** | Fathom / Fireflies recordings, podcast, YouTube, webinar/VSL, Loom, voice memos | high |
| **B — written-by-them** | own social captions (SocialCrawl), sent newsletters, Meta DM export, community posts, tweets/threads | med |
| **C — written-FOR-them** | website, sales/landing pages, course copy (firecrawl) | **none — offer/avatar ONLY** |
| **D — floor** | guided interview + record-going-forward | interview |

## Rules
- **Tier C never sets voice.** Website copy is usually written FOR the client — mining it for voice bakes in someone else's voice (the noise-factor trap). Offer, avatar, testimonials only.
- **Own social = the no-recordings primary.** Nearly every creator has it; SocialCrawl is already plumbed in the content engine.
- **Offer/avatar pulls wider than voice:** testimonials + reviews (the avatar's own pain language), intake forms, an existing brand guide all count.
- **DM export (Meta DYI):** Instagram/Messenger history via Accounts Center → Download your information → Messages only, JSON, low media. Prospect side = the richest PRE-sale VoC (feeds the `sales` bucket). Brand-owner side = tier-B written voice. Parser note: repair Meta's Latin-1/UTF-8 mojibake on read; build the parser against a real `message_1.json` (schema varies by export version).
- **Confidence stamp:** `voice_confidence: A|B|C|interview` = the highest tier that actually CONTRIBUTED VOICE (C can't). Consumers lean bold on A, conservative on interview.
- **Recordings connector:** detect Fathom or Fireflies at setup; confirm with the user; propose a how-far-back window before pulling. Every pull is approval-gated.
