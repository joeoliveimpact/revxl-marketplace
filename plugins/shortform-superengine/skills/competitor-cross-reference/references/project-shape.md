# Project shape and the visual pack

Relocated verbatim from `SKILL.md` at 0.4.0. The two primary artefacts,
`analysis-data.json` and `strategy-roadmap.md`, stay named in the skill itself.

## The project directory

```
projects/<YYYY-MM-DD>-<client-slug>-baseline/
├── foundation.md        # client positioning (from website or IG-signal fallback)
├── baseline.md          # client reel metrics summary
├── tiers.json           # competitor set (input to analyze.py)
├── analysis-data.md     # cross-reference metrics (output of analyze.py)
├── strategy-roadmap.md  # 10-section client-facing deliverable
└── source/
    ├── profile.json                     # client profile
    ├── reels-full.json                  # client reels
    └── competitors/
        ├── profiles/<handle>.json       # one per competitor (follower counts)
        └── reels/<handle>.json          # one per competitor (~36 reels)
```

Generated on top of this as the project lives: `visuals/` (the HTML pack),
`history/` + `refresh-log.md` (written by `competitor-pulse`), `brain-pulls/`
(the RevXL Vault cache written by `reel-scripter` ... the Vault is Joe's live strategy API,
not your brand brain; the directory keeps its historical name).

## The visual pack

→ `<project>/visuals/`: **overview.html** (stat cards, reach ladder, tier
scoreboard, hooks + themes field-vs-client, followers×views map, cadence,
opportunity map, gap cards, outlier wall), **competitors.html** (per-competitor
profiles with a picker; `--split` also writes one standalone file per
competitor for client delivery), **client.html** (client profile + hook mix +
the written analysis inlined). Self-contained offline HTML — open anywhere,
send anywhere. Brand the pack by dropping
`<project>/visual-theme.json` `{"brand":"#hex","accent":"#hex","logo_text":"..."}`.
