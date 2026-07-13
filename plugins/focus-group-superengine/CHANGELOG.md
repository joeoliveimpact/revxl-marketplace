# Changelog

## 0.1.1 — honest depth tiers
- Clarified that DEPTH sets two separate things: the reasoning tier (which model judges — always applies) and a target panel size (capped by your pack: `panel = min(target, personas_in_pack)`).
- The bundled example pack is 16 personas, so all tiers currently run 16 panelists — the tier changes reasoning depth, not crowd size. The skill now states this honestly instead of implying a 50/100/180-body panel. Build a larger pack via `/focus-group-setup` to widen the crowd (a real multi-size pack generator lands in 0.2.0).

## 0.1.0 — initial release
- v4 engine: word-ladder ratings (personas pick anchored words, never numbers) + JS-computed math (the council can't fudge stats) + monadic isolation (each persona × option judged in its own call).
- Two skills: `focus-group-setup` (persona-pack builder, any niche) + `focus-group-run` (swarm → council verdict).
- Teach Mode: opt-in plain-English "why" notes wrapped around the verdict; OFF path unchanged.
- Dual-axis verdict (attention vs convert, never blended), behavioral funnel, confidence-weighted pick, polarizing / mood-adjusted / sycophancy reads, clustered objections, verbatim quotes.
- Bundled generic coach/SMB example pack (16 personas) for out-of-box first runs.
- Token estimate + confirm gate before every run; deep/hyperreal require explicit go.
