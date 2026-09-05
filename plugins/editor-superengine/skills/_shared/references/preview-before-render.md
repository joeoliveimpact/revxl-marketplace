# Preview before any render

**The reviewer sees previews and approves BEFORE a render starts. Every time.**

Applies to any render, export or master: a composition render, a PDF or browser render, an
ffmpeg export, an audio master, an image export.

## Before the render

- Produce the cheap visual first... a frame snapshot at each changed timestamp, a page PNG,
  a contact sheet... and **show it to the reviewer in the response**.
- **Cover every beat that changed, not just frame 0.** If four moments moved, show four
  frames.
- Then stop and wait. Approval is the reviewer saying so, not the absence of an objection.
- **A passing lint or check run is not approval.** Lint measures fit, not judgment. A check
  can exit green having run zero layout samples, on a hook whose text overflows its band and
  whose rail dots collide with the headline.

## After the render

**Frames are the gate BEFORE the render. After it, the video is the review surface.** Do not
hand back stills off a finished file. Once the video exists, serve it and let the reviewer
watch it. Judge pacing only at ship speed, never in a slowed preview.

## Why

Renders are slow and expensive, and a wrong one wastes the wall-clock plus every pass queued
behind it. Snapshots cost seconds and catch the same defects. The eyes-on gate belongs to the
reviewer, not to the builder.
