# Goldmine gotchas

What goes wrong, what the client hears, and what Claude does next. Every runner failure
prints one plain sentence starting `ERROR:` and exits with a code other than 0, never a
traceback. Say the sentence in your own plain words; never paste a code or a path the
client does not need.

## Dashboard step failures

| Exit | What happened | Tell the client | Then |
|---|---|---|---|
| 4 | curl is not installed | The dashboard download needs a small tool called curl, and it is missing on this computer. | Offer to install it (macOS and recent Windows include it, so this is rare), then run the dashboard step again. |
| 5 | Offline, or GitHub did not answer | I could not download the dashboard just now. Everything else is saved. | Stop on the **stopped before the dashboard** block. The next "run the goldmine" lands straight on the dashboard step; nothing is redone or re-paid. |
| 6 | The download's commit stamp is not the pinned one | The dashboard download did not match the version this plugin trusts, so I did not use it. | Do not retry around it and never unpack it by hand. Stop on the same block and say the plugin's maintainer needs to know. |
| 7 | The download is not laid out as expected (not one top folder, or an unsafe file path) | Same as 6. | Same as 6. |
| 8 | The page could not be built | The dashboard could not be built from this run's files. | Read `reel-build/dashboard-build.log` yourself. A `required shared block missing` line means a runner file is gone: re-run compute, then check-reads, then the dashboard step. Anything else: stop on the same block and name the cause plainly. |
| 2 | check-reads has not passed | (Nothing; this is yours to fix.) | Finish the reads and run check-reads until PASS, then the dashboard step. |

The pinned version is downloaded once and kept in
`~/.cache/shortform-superengine/goldmine-dashboard/<tag>/`. Later runs reuse it with no
network. A half-finished unpack is cleaned up and redone on the next run.

## Earlier steps

- **Transcribe stops (exit 3)**: ffmpeg or faster-whisper is missing. Say the reels
  without transcripts will be read from their captions, offer setup ("set up shortform
  superengine" installs the transcription tools), and carry on to compute.
- **No SocialCrawl key, or a balance below the price**: the plan's NEXT line says so.
  Carry on without comments; the comment parts of the page stay empty.
- **The first-run window did not take**: `period_breakouts.window_source` is not `flag`
  after the analyze re-run. Stop. Running on without it would read a shorter window than the month a first run needs.

## The first-run window

A first run is "no `reel-build/goldmine-run.json`", never "no `history/` folder": any
second analyze run creates `history/`. On a first run, analyze re-runs with
`--window-from` set 30 days back, so the first Goldmine covers a month, not a week.

## The priced ask

The comments are the only paid part: 5 credits per breakout reel. The plan step prints
the exact ask with the price; say it word for word and wait for a yes. That holds at
any price, even a few credits. If the client hesitates at the price, offer the smaller
set (the top 3 breakouts per creator) and ask again with its own price. A no is fine:
the dashboard builds without comments.

## Bait or a real lead magnet

Coaches often post engagement bait: "comment AMEN", "type YES if you agree". The
runner flags these as comment asks because the wording matches; a name ending `_weak`
means no payoff was found. In the reads, a comment ask with nothing offered behind it
is an engagement ask: `lm_type` `lm_none`, magnet "engagement ask", and a PAPS row with
no promise. A real lead magnet names something the viewer gets: a guide, a template, a
link, a training. **Never invent a lead magnet** to fill the gap.

## Zero breakouts

No reel beat its creator's usual views by enough in this window. That is a result, not
an error: say the runner's plain message. If an earlier Goldmine exists, it stays in
use (its passed reads stay recorded, so reel scripting keeps checking against them);
say so, with the date from `goldmine.last_run`.
