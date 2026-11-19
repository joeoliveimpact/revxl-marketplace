# Changelog - clawyer-superengine

## [0.1.0] - 2026-11-19

### Added
- First release. Clawyer runs a self-represented legal matter in the person's own folder, built on
  pro-se-firm v1.7.0 by Mic H. (MIT).
- `clawyer-setup`: asks state, county, court, a matter name and the kind of case, then writes
  `firm.config.json`, `case-profile.md`, the firm-layer files and the matter folder with `clawyer_init.py`.
  Choosing family law switches the family-law pack on. Installs Python, Git and the scanned-document reader
  after one yes.
- `pro-se-firm`: the managing partner, with the original skill body kept word for word in five reference
  files so the skill stays under the 5,000-token ceiling.
- `matter-intake`, `evidence-intake`, `matter-status`, `matter-close`, `breach-analyzer`, `legal-premortem`,
  `custody-premortem`.
- 19 agents: the 15-reviewer council, `verification-partner`, `legal-researcher`, `contract-reviewer`,
  `cross-examination-builder`.
- Three hooks that load the matter, prompt routing and prompt the fact fan-out. All three print nothing in a
  folder with no `firm.config.json`.
- The failure report in the six skills that run a script or write files.

### Changed from pro-se-firm v1.7.0
- Files carrying Mississippi law open with a jurisdiction note; other states treat them as examples.
- Scripts find the person's folder from the session, not from the script's own location.
- Details of one person's case were removed from agents, templates and scripts.

### Not included
- About 80 case-specific scripts (three of which did not run) and all workflow files. See
  `skills/pro-se-firm/scripts/NOT-SHIPPED.md`.
- The compliance and advisory variant.
