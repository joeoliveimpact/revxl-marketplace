# Changelog

All notable changes to Meta Ads Superengine are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-09-05

### Changed

- **Brain calls go through `revxl-vault-search`.** The wiring reference keeps its
  name and everything meta-ads specific (the `meta-ads-strategy` spoke rule, the
  recipe table, the anchored cache, the evidence line, the compliance boundary)
  and drops its own key ladder, the three curl blocks and the error table. Those
  live in one place for every RevXL plugin now: the `revxl-vault-search` skill in
  workspace-superengine 0.14.0, which also logs every call and tells the three
  429 reasons apart. All fifteen Brain-calling skills name it: the fourteen
  trigger points say so in their headers and each spells out the full
  invocation, and setup's Brain-key row runs the skill's connection test. Behaviour at each trigger is
  unchanged: same recipes, same budget, same `Brain: [brain] <path> woven /
  skipped (...)` line, degrade never blocks the journey.
- Requires workspace-superengine 0.14.0 or later for live Brain pulls; without
  it the engine degrades to its bundled references and says so once.

## [0.3.0] - 2026-07-22

### Added

- **Money math for every kind of offer.** Breakeven math now covers the way you
  actually charge: subscriptions and memberships price off what a client is
  worth over their whole time with you (not just the first month), checkout
  funnels with no sales call get their own math, and free or $0 front ends are
  handled cleanly. Best of all, the engine now spells out in plain English what
  every number means and where it came from, so you can see exactly how a lead
  cost gets decided.
- **A clean restart for a paused account.** If your ad account is fully paused,
  the engine now imports it end to end, tells you straight when there is nothing
  live to bring in (instead of pretending), and gives you a real reactivation
  path to turn it back on ... resetting its monitoring clock so the guidance
  that follows stays accurate.
- **More you can do without connecting anything.** The paste-and-type lane got
  more honest and more capable: you can capture a competitor's ad details by
  hand straight from Meta's Ad Library, keep a manual running count of the
  conversions your CRM tracks, and, where it helps, get set up with a tracking
  bridge that is upfront about the light setup it takes rather than promising
  zero. Every capability is now labeled for exactly what it does.

### Changed

- **A real guardrail on connected accounts.** When you connect Ads Manager, the
  engine now walks you through granting access to one account only (never "all
  accounts and future accounts"), warns you that Meta makes that choice sticky
  once granted, and actively flags any connected account Meta cannot govern ...
  so your most exposed account can no longer slip through unnoticed.
- **Compliance that follows your creative everywhere.** When the live policy
  check turns up a restriction ... say, no before/after photos for a weight-loss
  offer ... the engine now remembers it and enforces it across every place your
  ads get built, so a risky suggestion never lands in your hooks, copy, layouts,
  or scripts.
- **Fair credit for showing up daily.** Logging your numbers every day is now
  fully supported, and the engine counts your streaks fairly: a daily check-in
  and a weekly review both count correctly toward the track record that unlocks
  your next stage.
- **Safer when you run more than one brand.** The engine now double-checks it is
  looking at the right brand before it reports a single number, warns you when
  an offer or price change has left a live campaign untouched (and asks what you
  want to do about it), and flags when your profit math was run against an older
  version of your offer.
- **Explanations you can dial per topic.** You can now set how much the engine
  explains ads separately from how much it explains Claude itself ... new to ads
  but comfortable with tools, or the other way around, and it meets you where
  you actually are on each.

### Fixed

- **Your voice, remembered.** The quick voice sketch you give the engine now
  sticks, so every creative skill writes in your voice without asking you the
  same questions twice.
- **Each piece of creative gets its own slot.** Your hooks, copy, layouts, and
  scripts now each save to their own place, so producing one never overwrites
  another.
- **Steadier under the hood.** The engine's internal guidance is now pinned to
  stable, named references so its advice stays accurate as it grows, plus a
  batch of smaller rough edges smoothed out across setup, routing, and creative.

## [0.2.0] - 2026-07-22

### Added

- **Competitor tracking subsystem.** A new skill builds and maintains a roster
  of coaches in your niche, then tracks how long each of their ads has been
  running — 30 days, 60 days, 6 months and beyond. Ads running for months are
  the ones making money, so the engine flags them and can nominate the strongest
  ones for a deeper teardown. Brings the engine to 27 connected skills.
- **Onramp for coaches already running ads.** If you're already spending, the
  engine now imports your history and gets you straight into the daily
  monitoring loop — without pausing your live campaigns.
- **Two-price offer math.** Breakeven math now handles free or low-cost front
  ends by anchoring the numbers on what your back-end offer is actually worth.
- **Tracking path for pages you don't own.** If you're not sending traffic to a
  page you control, the engine now sets you up with Meta's native lead forms
  plus a no-code tracking bridge, instead of assuming you can install a pixel.
- **Live monitoring on connected accounts.** When you connect Ads Manager, the
  engine now pulls your numbers live and reads fatigue, kill, and scale signals
  straight from the data — with clear evidence behind every recommendation.

### Changed

- **Cleaner launch, safer publishing.** The launch runbook now builds your
  campaign across its three parts, reads your settings back to you before you
  publish, and runs a live error check first so you catch problems before they
  cost you.
- **Honest connection safety.** The engine is now upfront about exactly what a
  connected Ads Manager can and can't do: changes are gated on Meta's own
  account settings, and the engine confirms every account action with you.
- **Smarter offer pricing guidance.** When you run a free or discounted front
  end, the engine now points the profit math at your back-end value where it
  belongs.
- **Compliance that never guesses.** If the engine can't verify a policy live,
  it now routes you to keep building in parallel and re-checks when it's back
  online — your launch stays blocked until there's a real pass, never a guess.
- **Leaner install.** Development and research material no longer ships with the
  plugin, so installs are smaller and faster.

### Fixed

- **No more dead ends.** Closed a gap where one path could leave you without a
  clear next move. Every step now always hands you your ranked next moves.

## [0.1.0] - 2026-07-18

### Added

- Initial release: a 26-skill Meta ads engine for online coaches, taking you
  from zero knowledge through breakeven math, qualified-signal setup, live
  compliance checks, stage-appropriate campaign plans, voice-matched creative,
  disciplined testing, and read-only-first ops that talk you out of panic edits.
- Journey-based routing with a built-in compass ("what's next") so you're never
  lost, and a teach mode that glosses every Claude and Meta term for first-time
  coaches while letting experienced operators run terse.

[0.3.0]: https://github.com/joeoliveimpact/revxl-marketplace
[0.2.0]: https://github.com/joeoliveimpact/revxl-marketplace
[0.1.0]: https://github.com/joeoliveimpact/revxl-marketplace
