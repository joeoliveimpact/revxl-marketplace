# Changelog — stories-superengine

## 0.1.0 ... 2026-10-08

First release. Built from story sets that ran on a live coach account (four guide sets and a week of
quote cards, Sep–Oct 2026), with the owner's data stripped out.

**Skills:** `stories-start-here`, `stories-setup`, `stories-guide-set`, `stories-quote-card`,
`stories-schedule`, `brand-brain` (shared REVXL brand-brain, synced via `scripts/sync-brand-brain.py`).

**Rendering:** frames are rendered from a `story.json` with Instagram's native text styles (bundled
design system). Three checks block a bad frame: LOAD, FONT (the style's font really loaded), FIT (no
text off the screen or under Instagram's top/reply bars; text in the side margin is a note only).
Quote cards keep FONT + FIT and add SETUP (name and handle required; no default identity). The
verified badge is off unless the coach has one. CDN scripts are pinned with integrity hashes.

**Publishing:** one script (`publish.py`) detects the route, hosts frames on Google Drive (composio or
gws) and refuses to schedule unless every link serves an image or video, builds the Metricool payload
with the UTC offset computed for the post's own date (daylight saving), schedules one story post with
every frame on Instagram + Facebook, and reads back by date. Instagram-direct converts frames to JPEG
and posts them in order, only with `--confirm-live`.

**Verified on the author's machine:** both render selftests (planted defects caught), the publish
selftest (DST offsets, payload shape, WSL path conversion), a regression rebuild of a published
6-frame set (identical layout; the one line that had clipped in production is blocked by FIT), and
live read-only runs of detect / brands / host / payload / readback against a real Metricool brand.
**Not yet verified:** the Instagram-direct route posting live, and a clean-machine install.
