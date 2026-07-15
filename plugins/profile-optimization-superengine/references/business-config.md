# Business Config... profile-optimization-superengine

> This file is the shipped TEMPLATE / schema (placeholders). The `profile-setup` wizard writes the FILLED copy to `${CLAUDE_PLUGIN_DATA}/business-config.md`, which persists across plugin updates. Every skill reads the persisted copy FIRST; if none exists, values are placeholders and the coach hasn't run setup yet.
> Do NOT hardcode a path and do NOT write into this `${CLAUDE_PLUGIN_ROOT}` copy... it is the template only.
>
> **Shared brand-level values (VoC contract):** if `~/.claude/revxl/<brand>/voc/business-config.md` exists (written by the bundled `brand-brain` skill), brand-level tokens (brand name, voice, niche, avatar, offer) are READ from there first and setup updates to those tokens are WRITTEN back there too... so every REVXL engine shares one config. This only applies on Cowork/Code, where a filesystem persists. On Claude.ai Chat there is no persistent user filesystem, so voice is captured inline for the session only.
>
> **Session-live, NEVER persisted:** the environment tier (Claude Code / Cowork / Claude.ai Chat) is detected fresh every session and is NOT stored here. A coach can run setup in Cowork and later audit in Chat. Only the durable business config + toggles + the brand-brain marker below persist.

### Setup markers
| Key | Value | Notes |
|-----|-------|-------|
| `{{SETUP_COMPLETE}}` | false | Set to `true` when `profile-setup` finishes. The router checks this to decide whether to offer setup. |
| `{{BRAND_BRAIN_BUILT}}` | none | `persistent` (shared brain built/reused on Cowork/Code) / `inline-session` (captured in-conversation on Chat, not persisted) / `none` (not captured). |
| `{{COMPETITORS_SCANNED}}` | none | Date stamp when `profile-competitor-scan` last built `${CLAUDE_PLUGIN_DATA}/competitors/benchmarks.md`, or `none`. Optional... the audits detect the benchmarks file directly and never depend on it. |

### Brand / voice
| Key | Value | Notes |
|-----|-------|-------|
| `{{BRAND_NAME}}` | _(placeholder)_ | The coach's brand or business name |
| `{{BRAND_SLUG}}` | _(placeholder)_ | Normalized slug (lowercase, alphanumeric, no separators) used to resolve the shared brain folder |
| `{{BRAND_VOICE}}` | _(placeholder)_ | Path/handle to a voice guide, or "inline" when captured per-session (Chat tier) |
| `{{VOICE_EDGE}}` | conversational | The brand's edge dial: `vanilla` / `conversational` (default) / `spicy` / `locker-room`. Controls how bold the copy the audits write can be (bio, CTA, About letter). MATCH the coach's actual register... edge is a setting to match, not a risk to sand down. |

### Business intake (captured ONCE by profile-setup; the audits read these instead of re-asking Round 1)
| Key | Value | Notes |
|-----|-------|-------|
| `{{NICHE}}` | _(placeholder)_ | Coaching niche in the coach's words (e.g. "fat loss for women over 40") |
| `{{IDEAL_CLIENT}}` | _(placeholder)_ | Avatar: age range, lifestyle, biggest struggle, in concrete language |
| `{{OFFER}}` | _(placeholder)_ | Current offer / program (no price stored... coach supplies live) |
| `{{LEAD_MAGNET}}` | _(placeholder)_ | The free asset the single bio link points to (e.g. "Metabolism Reset Starter Guide") |
| `{{DM_KEYWORD}}` | _(placeholder)_ | The one shouty-caps DM keyword derived from the offer + confirmed (e.g. RESET), kept identical across every element |
| `{{PLATFORMS}}` | _(placeholder)_ | fb / ig / both... which profile(s) the coach runs |
| `{{IG_ACCOUNT_TYPE}}` | _(placeholder)_ | Creator / Business / Personal (only relevant if they run Instagram) |
| `{{FB_PROFESSIONAL_MODE}}` | _(placeholder)_ | on / off (only relevant if they run Facebook) |

### Behavior toggles
| Key | Value | Notes |
|-----|-------|-------|
| `{{EXPLANATION_LEVEL}}` | beginner | beginner / intermediate / advanced... how much jargon I translate when I talk. Honor "set level to X" any time. |
| `{{TEACH_MODE}}` | on | on (default) / off... teach the WHY behind each fix in plain 8th-grade language so the coach learns to fish. Distinct from explanation level (see ${CLAUDE_PLUGIN_ROOT}/references/teach-mode.md). Toggle anytime. |
