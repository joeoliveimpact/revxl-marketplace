# Win-Back / Sunset Framework — 3-Touch Reactivation

Source: Email Nurture Architecture Research (Type 8, Chase Dimond sunset). Broadcast: built once, fires
to dormant contacts. Specificity from coach voice + avatar pains, never individual facts.

**Objective:** reactivate 60-90d inactive contacts OR safely remove them to protect deliverability.
**Trigger:** tagged `Inactive` (no open/click 60-90d).
**Cadence:** 3 emails over 14 days. Format: text-only (all three).

| # | Send | Purpose | Lever | Subject angle | CTA |
|---|------|---------|-------|---------------|-----|
| 1 | D1 (60d) | high-value content nudge | Reciprocity/Curiosity | "we miss you" + a genuinely useful resource | download the resource |
| 2 | D7 (90d) | feedback micro-survey | Dialogue Activation | "quick question? (5 seconds)" — one-click options | click best match |
| 3 | D14 (120d) | scarcity sunset | Loss Aversion | "should we remove your email?" — removal in 7d unless they stay | confirm stay |

**Pitch + CTA per email** (see ${CLAUDE_PLUGIN_ROOT}/references/cta-patterns.md): D1 `none/soft` — resource download (4) · D2 `none/soft` — one-click survey (6) · D3 `hard` (value-framed) — binary stay/go (11). **Re-engage soft → hard sunset.**

**Story dose: LIGHT** (see ${CLAUDE_PLUGIN_ROOT}/references/story-engines.md). D1 ("we miss you") can open a curiosity loop or a short "here's what you missed" beat to re-earn attention. D2 survey + D3 sunset stay mechanical. Don't over-narrate a re-engagement play.

**Levers:** Dialogue Activation (one-click re-engagement); Loss Aversion (pending unsubscribe).
**Mistakes to avoid:** keeping non-responders (tanks deliverability); guilt-trips ("why did you leave us?").
**Benchmarks:** sunset open 8-15%; survey click 20-30%; reactivation 8-15%.
**Critical:** D3 must actually suppress non-responders after the window — the deliverability win is the point.
