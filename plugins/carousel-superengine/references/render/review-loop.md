# Review Loop — browser markup on a rendered deck (Claude Code)

The coach looks at every slide at real size in a browser, draws on them, and their notes become
edits. Replaces "open 2-3 PNGs and check nothing is clipped," which does not work: on the run this
method came from, the first export passed a spot check and still carried a bleeding headline, a
colliding ghost word, and an unusable proof image.

## 1. Contact sheet

One HTML file. Requirements, all load-bearing:

- **Lives OUTSIDE the render directory.** `render_slides.py` globs `*.html` in the target dir and
  fails on any file without a `#slide` element. Put the sheet in the parent and reference the PNGs
  by relative path (`<render-dir>/png/slide_NN.png`). This bites once per project otherwise.
- **Every slide numbered**, with its filename shown. The coach says "slide 4" and you must land on
  the same slide with no ambiguity.
- **Two modes:** a grid (catches spine breaks, palette drift, and repetition across the set) and
  one-at-a-time at ~540px (catches what a phone catches). Both matter — the grid found a duplicated
  artifact across two slides that neither slide showed on its own.
- **Changed-since-last-round tag per slide** on rounds 2+. The coach should not have to hunt for
  what moved.
- Self-contained: no CDN, no build step, inline CSS.

## 2. Serve

```
python -m http.server <port> --bind 127.0.0.1     # run from the sheet's directory
```

Loopback only. Open in the in-app browser pane and also paste the URL as text — some coaches
annotate in their own browser.

## 3. Reading markup

Notes arrive as numbered lists against annotated screenshots. Before editing:

- **Echo a note → slide-number table.** Cheap, and it catches the misread that would otherwise
  cost a full rebuild.
- **Watch for one note that implies several slides.** "Show the real prompt, not a spec sheet"
  applied to three slides; treating it as one slide's problem would have shipped an inconsistency.
- **Watch for a fix that moves a problem instead of solving it.** Making slide 8 match slide 9
  removed one duplication and created another. Check the neighbours before rebuilding.

## 4. Questions vs instructions

Markup is written fast and often phrased as a question. Answer, recommend, then execute their call.
Push back — once, with the reason — when a note would break something the deck is load-bearing on:

| Note pattern | What to check before doing it |
|---|---|
| "put text on the redacted/teased item" | It is the deck's open loop. Text closes it. And the text must match what the payoff slide actually delivers, or the tease lies. |
| "cut the CTA keyword" | The keyword is what fires the DM automation. Confirm explicitly before removing. |
| "make this headline bigger" | Authored `nowrap` lines bleed past the margin. Bump the size, then Read the PNG. |
| "reuse this treatment elsewhere" | Good instinct — but check the mark does not already mean something else on another slide. One mark, one meaning. |
| a claim in copy ("ten seconds") | If it appears twice on one slide or contradicts a neighbour, fix both. Flag that it is a claim someone can call out. |

## 5. Fix and re-verify

- Edit the **generator**, never the exported HTML. Exports are disposable.
- Re-run build + export.
- **Read every changed PNG at full size.** Thumbnails hide edge bleed, overlap, and small type.
- Re-check the design-rules floor on changed slides: margin frame, text budget, contrast, nothing
  critical below y=1120 (Instagram covers the bottom band).

## 6. What to say when handing back

State what changed, what you deviated on and why, and what is still open. Do not re-narrate slides
the coach can see. If a change created a new inconsistency elsewhere, say so before they find it.
