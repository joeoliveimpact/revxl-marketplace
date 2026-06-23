# email-sequence-superengine

> Set up your voice once, then generate broadcast email sequences for the whole coaching journey... booking to retention. For high-ticket coaches.

---

## What this plugin does

Most coaches' lists go cold because writing sequences is slow and every email ends up sounding like a template. This plugin fixes both. You run one setup that captures your voice, your program, and your ideal client's real pains... then any campaign you name gets built in your voice, as a SET of emails that fires to everyone who hits the trigger. No per-prospect work.

**It is a broadcast engine, not a personalization tool.** Specificity comes from your voice plus the avatar's shared pains plus merge tokens... never invented facts about an individual. That is what keeps it safe to fire to a whole list and still feel personal.

Twelve skills take you from zero to ready-to-load copy:

- A **first-run setup** that captures your brand voice, avatar, and offer, plus a **plain-English guided tour** for non-technical users.
- An **email-add-stories** step that banks your real stories so the story-driven emails pull from truth, never fabrication.
- **Eight campaign generators** covering the full journey: pre-call show-up, pre-sell video script, launch, warm nurture, no-show recovery, post-call follow-up, win-back, and new-client onboarding.

Under the hood: a dosed storytelling engine, a soft-pitch gradient (so you are not hard-selling every email), a goal-indexed length system measured from thousands of real sales emails, a no-false-scarcity guardrail, a `{{VOICE_EDGE}}` dial from vanilla to locker-room, and teach-mode explanations that show you the WHY as it builds. Output is ESP-agnostic with an optional push into GoHighLevel as named templates.

**Drafts only.** It never sends, and it never builds your automation timing... you wire that yourself. Deliverability setup (domains, warm-up, list hygiene) is on you too; this plugin writes the copy.

**Audience:** high-ticket fitness, health, wellness, and online coaches scaling a program. Beginner explanation level is on by default; say "set level to intermediate/advanced" any time.

> **Command naming:** every command is prefixed `email-` so they group under `/email-` and never collide with another plugin's commands. Type `/email-` to see the whole set.

---

## Skills

#### `email-start-here`
**Triggers:** "/email-sequence-superengine", "build an email sequence", "write my nurture emails", "set up my email engine"

The orchestrator. Greets, checks whether you are configured, and routes you to setup, the guided tour, or the campaign you name.

#### `email-setup`
**Triggers:** "set up email sequences", "configure the email engine", "reconfigure my email config"

First-run wizard. Captures brand voice, program, avatar pains + objections, offer, sender domains, reply routing, ESP, pitch floor, and voice edge into one config every generator reads. Re-runnable any time.

#### `email-guide`
**Triggers:** "first time", "walk me through the email engine", "I'm new", "help"

Plain-English first-time tour. Explains what the engine does, runs setup, and builds your first sequence with extra hand-holding, jargon glossed inline.

#### `email-add-stories`
**Triggers:** "add my stories", "story intake", "capture my stories"

Quick Q&A that banks your real stories and analogies. The story-driven generators pull from this well, so the emails are true, never invented.

### Campaign generators

| Skill | Builds | Say |
|-------|--------|-----|
| `email-show-up-sequence` | 4-email strategy-call show-up sequence | "precall sequence", "show-up emails" |
| `email-presell-video` | 5-7 min pre-sell VSL script | "VSL script", "pre-sell video" |
| `email-launch-promo-sequence` | 7-day open-cart launch sequence | "launch sequence", "open cart emails" |
| `email-warm-nurture-sequence` | weekly value-to-invite pattern (1-7/wk) | "warm nurture", "keep my list warm" |
| `email-no-show-sequence` | 4-touch reschedule sequence | "rebook no-shows", "they didn't show" |
| `email-follow-up-sequence` | 4-touch no-close follow-up | "follow up after the call" |
| `email-winback-sequence` | 3-touch win-back / sunset sequence | "winback", "reactivate cold leads" |
| `email-onboarding-sequence` | 5-email 30-day new-client sequence | "onboarding emails", "welcome sequence" |

---

## Quick install

### Claude Desktop (recommended for coaches)

1. Customize → Skills → **+** next to "Personal plugins"
2. Paste: `joeoliveimpact/revxl-marketplace`
3. Click Sync → click **Install** on `email-sequence-superengine`

Then in your first conversation:
1. Say _"first time"_ or _"walk me through it"_ and the `email-guide` tour orients you, runs setup, and builds your first sequence
2. From then on: name a campaign (e.g. _"build my launch sequence"_) and tell me where it goes

### Claude Code

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install email-sequence-superengine@revxl-marketplace
```

Full step-by-step in the [marketplace INSTALL guide](../../README.md#install).

---

## Dependencies

**None are required** to generate copy... configure your voice and avatar, name a campaign, and you get drafts. The integrations below are optional:

| Capability | Optional integration | Always-available fallback |
|------------|----------------------|---------------------------|
| Push finished copy into your CRM as templates | GoHighLevel MCP (`ghl-push`) | Copy the drafts out manually / export |
| Match your written voice automatically | A workspace voice guide or VoC source | Answer the voice questions in `email-setup` |

Sending, domain warm-up, SPF/subdomain setup, and list hygiene are **your** responsibility and gate any real send. This plugin writes the copy; it does not send it.

---

## Compatibility

| Platform | Skills |
|----------|--------|
| Claude Desktop | ✅ all 12 |
| Claude Code | ✅ all 12 |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT, see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md): REVXL's curated Claude superengine catalog.
