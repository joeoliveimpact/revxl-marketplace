# Changelog — higgsfield-superengine

All notable changes to this plugin. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.1.1 — 2026-10-01

### Fixed

- Spend guard: stamps a paid submit only for a real pending tool call (transcript tool_use_id + command, no result yet); a hand-built hook event or runner script is refused. Selftest R1–R6.
- Spend guard: refuses a paid submit unless the model's notes file was read, a prompting or use-case skill was loaded, and every prompt in the request was shown word for word with a client reply after it. Selftest V1–V7.
- Pricing: `hf_rest.py upload` records an MP4's length (stdlib mvhd reader); estimates carry `input_video_s`; Seedance input/edit seconds and Genjutsu are priced on it (rounded up, capped at the table max).
- Pricing: Seedance 2.5 audio_unproven ask dropped (audio on = off, measured 09.30.26); Flare/Sunburst 1k $0.06 and 2k $0.15 ceilings (xhigh/max 2x).
- References: Seedance 2.5 and Genjutsu reach 1080p; Seedance 2.0 uses `<<<image_N>>>`; Kling O3 video-edit marked untested for restyles; Qwen thinking stays on; Hailuo optimizer off for built prompts; LTX aspect ratio must match the start image.
- Codex adversarial review fixes:
  - guarded paths are normalized and resolved (`.config/./…` no longer slips past);
  - `python <script>` is refused when the script mentions the submit script, the guard or the ledger;
  - the whole transcript is read, not the last 8 MB;
  - only successful Read/Skill calls count, for this plugin's own model file;
  - promptless requests still need a description and a reply;
  - `refund not_sent` is refused once a submit used the stamp (new reason `rejected`);
  - clip lengths are no longer rounded down before pricing.
- Known limit: the guard cannot see inside a script Claude writes; a deliberately obfuscated script could still forge approval. Approval held outside the agent's reach is planned for v0.2.

### Added

- `references/video-edit-recipes.md`: shot-type check, add-an-object prompt order, effects on black for compositing, output checks.
- Reference manifest rule (image-prompting, video-prompting, thumbnails, Flare, Kling O3).
- Setup names the two guard habits: plugin on for every folder, no bypass mode.

## 0.1.0 — 2026-09-30

First release (catalog 0.1.70).

### Added

- Plugin scaffold: manifest, README, changelog, MIT license, and the folders later work fills in (`scripts/`, `hooks/`, `skills/`, `references/`, `references/models/`).
