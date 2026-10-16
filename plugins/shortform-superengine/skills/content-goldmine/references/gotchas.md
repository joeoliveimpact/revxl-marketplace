# Goldmine gotchas

What goes wrong, what the client hears, and what Claude does next. Every runner failure
prints one plain sentence starting `ERROR:` and exits with a code other than 0, never a
traceback. Say the sentence in your own plain words; never paste a code or a path the
client does not need.

## Dashboard step failures

| Exit | What happened | Tell the client | Then |
|---|---|---|---|
| 4 | curl is not installed | The dashboard download needs a small tool called curl, and it is missing on this computer. | Offer to install it (macOS and recent Windows include it, so this is rare), then run the dashboard step again. |
| 5 | Offline, GitHub did not answer, or the download saved no file | I could not download the dashboard just now. Everything else is saved. | Stop on the **stopped before the dashboard** block. The next "run the goldmine" lands straight on the dashboard step; nothing is redone or re-paid. |
| 6 | The download's commit stamp is not the pinned one | The dashboard download did not match the version this plugin trusts, so I did not use it. | Do not retry around it and never unpack it by hand. Stop on the same block and say the plugin's maintainer needs to know. |
| 7 | The download is not laid out as expected (not one top folder, or an unsafe file path) | Same as 6. | Same as 6. |
| 8 | The page could not be built | The dashboard could not be built from this run's files. | Read `reel-build/dashboard-build.log` yourself. A `required shared block missing` line means a runner file is gone: re-run compute, then check-reads, then the dashboard step. Anything else: stop on the same block and name the cause plainly. |
| 9 | The download landed in a folder path of 260 characters or more that the runner could not reach. Rare: the runner handles long paths itself, so this is a network home folder | I could not open the dashboard download: the folder it saves into has a longer path than Windows allows. Everything else is saved. | Do not retry, and change nothing on the computer. Stop on the **stopped before the dashboard** block and say the plugin's maintainer needs to know. |
| 2 | check-reads has not passed | (Nothing; this is yours to fix.) | Finish the reads and run check-reads until PASS, then the dashboard step. |

The pinned version is downloaded once and kept in
`~/.cache/shortform-superengine/goldmine-dashboard/<tag>/`. Later runs reuse it with no
network. A half-finished unpack is cleaned up and redone on the next run.

## Earlier steps

- **Transcribe stops (exit 3)**: ffmpeg or faster-whisper is missing. Say the reels
  without transcripts will be read from their captions, offer setup ("set up shortform
  superengine" installs the transcription tools), and carry on to compute.
- **No SocialCrawl key, or a balance below the cheapest level**: the plan's NEXT line says so.
  Carry on without comments; the comment parts of the page stay empty.
- **The first-run window did not take**: `period_breakouts.window_source` is not `flag`
  after the analyze re-run. Stop. Running on without it would read a shorter window than the month a first run needs.
- **A long project folder on a network drive (exit 10)**: the runner reaches long project
  folders on this computer itself, but not on a network drive. Tell the client plainly that
  this project's folder is on a network drive with a longer path than Windows allows there,
  and nothing was changed. Do not retry, and change nothing on the computer. Stop and say the
  plugin's maintainer needs to know.

## Comment read and reply drafts

These run after the page is published, so none of them takes this week's page away. Every
other stop is in the "When something stops" table of `./comment-read.md` or `./reply-drafts.md`.

| Message | What happened | Tell the client | Then |
|---|---|---|---|
| `comment read: N comments with no category list (null) treated as no category.` (dashboard step) | A batch file held `null` where a list of categories belongs. The step read it as no category, so the page still builds | Nothing. | Carry on. |
| `ERROR:` ... `no owner label is set`, or ... `is spoken by` (reply-candidates, exit 2) | Call transcripts exist, but the runner does not know which speaker is the client, or no line carries the name it was given. The line lists the most frequent speaker names (names only) | Which of these is you? (with the names the line lists) | Run it again with `--owner "<the name they pick>"`. Never guess one. The yes to drafts is kept, so never ask that again. |
| `ERROR: Finish the <date> reply drafts first` (exit 2) | An earlier set of drafts has not passed check-replies | Nothing. | Run `check-replies`, fix what it names in the pending file until PASS, then run reply-candidates again. |
| `ERROR: no call transcripts in` ... `so nothing was saved` (reply-candidates, exit 2) | No transcripts in the folder it looked in and no written answers: usually the wrong folder. Nothing was kept | Do you have call transcripts? (once) | Yes: run it again from their workspace folder (the one holding `voc/`) or with `--workspace`. None: run it again with `--no-sources-ok`. |
| `No call transcripts or written answers yet, ...` (reply-candidates with `--no-sources-ok`, exit 0) | No transcripts and no written answers to draft from | That line, once, in plain words. | Fill every real question as `no_match` with a content idea. If they paste answers, save them for them (`./reply-drafts.md`). |
| `ERROR: the verdicts file ... is missing or not valid JSON` (check-comments, exit 2) | The saved verdicts are not one JSON list (text around the code fence, or a cut-off reply) | Nothing. | Save just the list (one code fence around it is fine), then run `--verdicts` again. |
| `ERROR: this pull has no saved page yet` (record-publish, exit 2) | record-publish ran before the dashboard step saved this pull's page | Nothing. | Run the dashboard step, publish, then `record-publish`. |

## The first-run window

A first run is "no `reel-build/goldmine-run.json`", never "no `history/` folder": any
second analyze run creates `history/`. On a first run, analyze re-runs with
`--window-from` set 30 days back, so the first Goldmine covers a month, not a week.

## The priced ask

The comments are the only paid part: 5 credits per breakout reel. The plan step prints
one ask with three levels, each with its real price: Light (the best breakout per
competitor), Standard (the top 3) and Deep (every breakout in the window), plus the
window dates and the balance. Say it in plain words and wait for the client to pick a
level. That holds at any price, even a few credits. A bare yes is not a pick: ask which
level, never default to Deep. Then run only that level's command. A level priced over
the balance is marked; a level with nothing new says so. A no is fine: the dashboard
builds without comments.

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
