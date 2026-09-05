# The visual text hook is on screen at frame 0

A client-facing delivery standard for every reel this plugin builds.

## The standard

**The complete visual text hook is readable at 0.000s. Not animating in. Present.**

Open the first frame of the render and read it. If the hook is mid-fade, mid-slide, still
assembling, or partially masked, the reel does not meet the standard.

## Two attention grabbers, not a line count

The hook carries **two attention grabbers**: the thing that stops the scroll, and the thing
that makes the stop worth it.

- **This is not a line count.** Two, three or four lines are all fine. A four-line hook and
  a two-line hook can both carry exactly two grabbers.
- **This is not a fixed position.** The grabbers may stack together above a cutout, sit at
  the top and bottom of the frame, or share one band. Splitting them across the frame is an
  option, never a standard.
- **Secondary pieces may animate in shortly after.** Badges, chips, underlines, rails and
  supporting labels are all fair game for a short entrance.
- **The grabbers may not.** They are complete at frame 0 or the standard is not met.

## How to check it

Snapshot at exactly `t=0.000` and read the frame cold. Do not check the storyboard, and do
not trust a timeline position of 0 in an animation tool: a value set at position 0 can be
inert at exactly t=0, so the frame renders without it. Read the rendered frame.

## Why

The scroll decision happens before anything can animate. A hook that arrives at 0.4s has
already lost the viewers it was written for.
