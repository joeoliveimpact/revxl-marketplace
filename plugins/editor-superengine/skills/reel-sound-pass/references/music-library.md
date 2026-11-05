# Music library: where tracks come from, and the licence row every final needs

Every track on the Sound Board comes from one of three places. The board shows which.

| Origin | Shown as | Where it lives | Its licence row |
|---|---|---|---|
| `pack` | Starter pack | `editor/sound/beds/` (catalogue `beds.json`) | ships with the pack, cleared for the client's own videos |
| `free` | Free library | `editor/music/` (catalogue `library.json`) | the licence exactly as the download page shows it |
| `own` | Your track | `editor/music/` (catalogue `library.json`) | the client ticks "I have the rights to use this track" on the board |

## Adding a free track (guided)

When the board's Send says `music_request: "free"`:

1. Offer a free library and open its page in the Browser pane: Pixabay Music, YouTube Audio Library, Free Music
   Archive, or Kevin MacLeod's incompetech. The client picks and downloads the track themselves.
2. Read the licence off that track's page and record exactly what it says, no more:
   `music_pick.py add-free "<file>" --title "<title>" --author "<author>" --licence "<licence name>" --licence-url "<licence page>" [--attribution "<line>"] [--mood <word>]`.
   It refuses a row without the licence name, the author or the licence page link.
3. CC-BY family (the licence asks for a credit): the attribution line is required. Without one, the standard line
   is built: `"<title>" by <author>, licensed under <licence> (<licence page>)`. It lands in the reel's
   `credits.txt`, ready for the post caption.
4. Non-commercial (NC) or no-derivatives (ND) licences get a plain warning, not a block: a reel that promotes a
   business may not be allowed, and trimming or fading may count as a change. Say so; the client decides.

## The client's own track

`music_pick.py add-own "<file>" --title "<title>"`. It shows on the board with an "I have the rights" box; until
that box is ticked and sent, the final refuses it. The tick is kept in the library, so it is asked once.

## Level and the dip

- **Level** is relative to the voice: the loudness of the stretch of the track that plays is matched to the voice track's, then set this many dB
  under it. -18 dB is suggested, and it is an option, not a rule. Tracks are not level matched and recordings vary,
  so the same setting sounds the same on any track and any recording. No measurable voice: it falls back to the
  track brought to standard loudness (-14 LUFS), and the mix says so.
- **Dip under the voice** (4-12 dB, 6 suggested): a fixed dip wherever the transcript says the voice speaks, easing
  in 80 ms before and out 300 ms after. It is not a compressor; it never reacts to the sound. Less than 4 dB is
  raised to 4. No transcript: no dip, and the mix says so.
- **Where the track starts:** each bed's `suggest_entry_s` is a position in the track (seconds into the song) where
  its strongest section starts. It goes in the bed's track start (`offset_s`), never in the reel time the bed
  comes in.
- **Beat-sync** (off by default, the client's button): each bed row's `grid` is its measured beat (`beat_grid.py`:
  bpm, beat length, first beat and bar start in track seconds; null when no steady beat is found, and the board
  then greys the option out). On, the track start snaps to the nearest beat; if the track would then run out
  before the reel ends, it starts whole bars (4 beats) earlier, never before the first bar, and the mix says so.
  It assumes one steady tempo in 4/4. The grid is cached in `work/beats/`; placement.json's `bed.beat` records it.
- The bed never loops. A track shorter than the reel fades out before it ends.

## The licence check

After the board's Send, `music_pick.py pick <reel>` writes `videos/<reel>/music.json` (the picked track, its
sha256, origin, licence, level and dip) and `credits.txt` when a credit is needed. The mix runs it again before
the final, then the licence check: a picked track with no licence row, a changed file, a free track missing its
author or link, a missing credit line, or an own track without the tick stops the final with one plain line
naming what is missing. No music picked: voice only, nothing to check.

Taste stays the client's: which track, how loud and how deep the dip are options to offer, never rules.
