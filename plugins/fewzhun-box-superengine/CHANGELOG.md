# Changelog - fewzhun-box-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.1.0 - 2026-11-17

First release. A private notes brain for a client's own headless Linux server, built from a search
service proven live on a client server and generalized: every client-specific value now lives in one
config file, `/etc/fewzhun-box/brain.json` (see `config/CONFIG.md`).

### Added
- **Search service** (Node 20+, no packages of its own): one warm search engine per spoke
  (obsidian-hybrid-search 0.12.7, pinned with its lockfile), results from several spokes merged by
  rank, read-only `GET` endpoints for search, read, the reader's own access and health. Active notes
  only (`status: active`, no `superseded_by`); `AGENTS.md` and `README.md` are never returned. Age
  lowers rank only in spokes set to decay, or for notes marked `sot_policy: decay` outside a
  `"never"` spoke.
- **Per-reader tokens** stored as sha256 fingerprints, compared in constant time, revocable at once.
  A spoke a token may not read and one that doesn't exist get the same answer. Tokens are never logged.
- **Sync** (off by default): fast-forward pulls with a read-only deploy key, active copies per spoke,
  reindex only for spokes that changed, engine environment scrubbed.
- **Nightly link graph** with graphify 0.9.112 in its own venv, one graph per spoke, cached so
  unchanged notes cost no model calls, published only when complete; a failed night keeps the old graph.
- **Read-only web page** with a strict security header; each spoke's graph only for a token allowed it.
- **Nightly draft notes** (off by default): masked sources, one no-tools model run, a threat scan and
  a secret-path gate that block bad drafts, staging for approval through the client's own bot
  (`fewzhun-box harvest decide`), and `fewzhun-box promote` into the client's own clone, never pushed.
- **Login guard** for every model call: idle and busy checks, at least 60 minutes left on the Claude
  login, no tools, a hard time cap, and a status file on any refusal.
- **Installer** (`bin/install.sh`): dry run by default, safe to re-run, refuses to take over another
  brain search service, checks memory, locked-down systemd services, named pause points for the
  owner-only steps, and a done-test (`bin/done-test.sh`) that checks both directions.
- **Skills**: `fewzhun-box-setup`, `fewzhun-box-check`, `fewzhun-box-use`, each with the standard
  failure report (`scripts/report_to_joe.py`).
- **References**: `references/agent-wiring.md` (a bot over HTTP) and `references/promotion.md`.
