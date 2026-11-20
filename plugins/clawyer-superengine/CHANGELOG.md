# Changelog - clawyer-superengine

## [0.1.2] - 2026-11-20

### Fixed
- Setup now installs the document libraries on a Mac whose Python comes from Homebrew. Before, that Python
  refused the install and setup never tried the second way, so nothing was installed.
- On Windows and Mac, setup no longer reports freshly installed libraries as missing. They were installed
  into the person's own folder, which the running check could not see until it looked there.

Found by running setup on a real Mac and a real Windows machine for the first time.

## [0.1.1] - 2026-11-19

### Added
- A citation check. Every court case in a draft is looked up in a free public case-law database
  (CourtListener's public citation pages, no account). A made-up citation, or a real citation attached to the
  wrong case name, fails the check. So does a citation with no case name beside it, and a Westlaw or Lexis citation, until a person confirms it. It is a required step in the main skill, the citation reviewer and the
  verification helper. It confirms a case exists and is the one named; it does not cover statutes or whether
  the case says what the draft claims.
- Setup finds Python and installs it if missing (per-user, no admin password), saves which interpreter works,
  then checks for the document libraries, the scanned-page reader and Git and installs what is missing after
  one yes. Each item reports done, needs one click from the person, or failed with what it costs them.
- A connect-a-source step: the court's own self-help page, calendar for deadlines, a cloud documents folder
  and email, offered one at a time and recorded so nobody is asked twice.
- Setup can repair a damaged setup and correct a wrong state or kind of case.

### Fixed
- Reviewer and helper agents now read the matter's own state and kind of case first. Mississippi and
  family-court rules in their text are examples, and three of them can now look rules up.
- The state warning now also covers a Mississippi case that is not a family case.
- The README no longer says case facts stay in the folder. It says what stays on the computer and what is
  sent to Anthropic, to the web and to the citation site.
- The README says a failure report is sent only with a REVXL key and is otherwise saved as a file.
- The 15-reviewer promise is stated per kind of case.
- State can no longer be left blank in setup, and an unsure kind of case becomes "other".

### Removed
- The original environment detector, replaced by `scripts/deps.py`.

### Known limits
- The Mac setup path and the Windows installs of the scanned-page reader and Git have not been run on a
  real machine.
- The connect-a-source step has not been tested with a real connector.

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
