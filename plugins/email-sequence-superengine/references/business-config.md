# Business Config — email-sequence-superengine

> Persisted via `${CLAUDE_PLUGIN_DATA}` so it survives plugin updates. Do NOT hardcode a path and do NOT store under `${CLAUDE_PLUGIN_ROOT}`. Setup writes these values; every skill reads them.
> Placeholder values below mean "not configured yet" → skills route first-run users to `email-guide`.
>
> **Shared brand-level values (VoC contract):** if `~/.claude/revxl/<brand>/voc/business-config.md` exists, brand-level tokens (avatar, offer, positioning) are READ from there first and any setup updates to those tokens are WRITTEN back there too — so every REVXL engine shares one avatar/offer config. Engine-specific keys (ESP, pitch floor, teach mode, etc.) stay in `${CLAUDE_PLUGIN_DATA}`.

### Brand / program
| Key | Value | Notes |
|-----|-------|-------|
| `{{BRAND_VOICE}}` | _(placeholder)_ | Path/handle to the voice anchor or workspace voice guide |
| `{{PROGRAM_NAME}}` | _(placeholder)_ | The coaching program name (e.g. your flagship program) |
| `{{POSITIONING}}` | _(placeholder)_ | One-line positioning / who it's for |
| `{{COACH_POV}}` | _(placeholder)_ | Coach's contrarian opinions / hot takes vs mainstream advice (feeds POV emails + story-bank) |
| `{{VOICE_EDGE}}` | conversational | The brand's edge dial: `vanilla` / `conversational` (default) / `spicy` / `locker-room`. Controls profanity, polarization/enemy-framing, crude humor, innuendo, shock opens, emoji. Generator MATCHES it — does NOT sanitize a high-edge brand or soften below the set level. See ${CLAUDE_PLUGIN_ROOT}/references/voice-anchor.md (Edge dial). |

### Avatar (deep — the conversion engine)
| Key | Value | Notes |
|-----|-------|-------|
| `{{AUDIENCE}}` | _(placeholder)_ | Target avatar (niche, stage) |
| `{{AVATAR_DREAM}}` | _(placeholder)_ | Desired outcome in STATUS terms — what peers/spouse/industry will think of them differently (Hormozi: status > money) |
| `{{AVATAR_REAL_PAIN}}` | _(placeholder)_ | The visceral/shameful TRUTH, not the polite public version. Plus 3 conflict levels: External (surface) / Internal (feeling) / Philosophical (why it's wrong) |
| `{{AVATAR_PAINS}}` | _(placeholder)_ | Top 3-5 shared pains in the coach's words — specificity engine for broadcast copy |
| `{{AVATAR_ENEMY}}` | _(placeholder)_ | Named villain the avatar already resents (a method, a type of guru, an industry norm) — powers Us-vs-Them |
| `{{AVATAR_TRIED}}` | _(placeholder)_ | What they've already tried + why they tell themselves it failed for THEM (the "won't work for me" belief) |
| `{{AVATAR_OBJECTIONS}}` | _(placeholder)_ | Top objections, mapped to the 4 fears: Self (capacity) / You (trust) / Unknown (status quo) / History (burned before). Include DIY ("why not just YouTube/AI") + Spouse/partner objection. E2/E3 strike the #1 |
| `{{LIST_AWARENESS}}` | problem-aware | problem-aware / solution-aware / product-aware — shapes hooks (Schwartz/Hormozi) |
| `{{AVATAR_NIGHTMARE}}` | _(placeholder)_ | (optional) Who you do NOT want — repulsion criteria for disqualification/anti-pitch |

### Offer (deep)
| Key | Value | Notes |
|-----|-------|-------|
| `{{OFFER_FRAMING}}` | _(placeholder)_ | How the offer is framed (no price stored — coach supplies live) |
| `{{OFFER_MECHANISM}}` | _(placeholder)_ | The vehicle/"how" + how the coach discovered it (Hormozi: sell the vacation, not the plane) |
| `{{OFFER_CONTRARIAN}}` | _(placeholder)_ | "Everything you've been taught about X is wrong because ___" — the point of difference |
| `{{PROOF_ASSETS}}` | _(placeholder)_ | Specific client results WITH numbers (perceived likelihood of achievement) |
| `{{OFFER_MICROWINS}}` | _(placeholder)_ | Quick wins to deliver in E1/E2 (2-min reset, cheat sheet) — instant competence proof |
| `{{COST_OF_INACTION}}` | _(placeholder)_ | What staying stuck 6-12 months costs them ($/exhaustion/missed opportunity) |
| `{{DROPOFF_POINT}}` | _(placeholder)_ | Where clients historically hit the "valley of despair" (e.g. day 10-14) — drives onboarding momentum-save |
| `{{SEGMENTS}}` | _(placeholder)_ | (optional) 2-3 self-select pathways at the gate (B2B/B2C, beginner/advanced) for routing |

### Delivery / system
| Key | Value | Notes |
|-----|-------|-------|
| `{{SENDER_DOMAINS}}` | _(placeholder)_ | Sending domain(s) / subdomain split |
| `{{OUTPUT_DESTINATION}}` | _(placeholder)_ | Where finished sequences go (workspace file / GHL / export) |
| `{{GHL_PUSH}}` | off | on/off — stage copy as GHL templates (opt-in, approval-gated) |
| `{{ESP}}` | ghl | ghl (baseline) / activecampaign / klaviyo / kit / mailchimp / none-export |
| `{{REPLY_ROUTING}}` | ghl-conversations | ghl-conversations (default, keeps automation) / external (WARN: breaks GHL automation) |
| `{{PITCH_FLOOR}}` | soft-floor | soft-floor (default, sell-in-every-marketing-email per Settle) / value-first (allow pure-value nurture) |
| `{{EXPLANATION_LEVEL}}` | beginner | beginner / intermediate / advanced — how much jargon I translate when I talk |
| `{{TEACH_MODE}}` | on | on (default) / off — teach the WHY behind each move in plain 8th-grade language so the coach learns to fish. Distinct from explanation level (see ${CLAUDE_PLUGIN_ROOT}/references/teach-mode.md). Toggle anytime. |
