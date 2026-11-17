# The motion bar: what a built graphic must look like

Every graphic Claude builds for a reel (the opening look and one scene per beat sketch) is held to this bar.
The Motion review board shows short labels under each card; use the questions here to judge the result.
The visual advice guides taste; the scene-area and caption-band rules are machine-checked.
Say scene, camera move and rest point to the user; never world, hold, loop or sha256. Follow
[What the user hears](../../editor-start-here/references/what-the-user-hears.md).

## 1. The frame is a window into a world

- Lay out a world larger than the frame first, then move a camera across it. Apps, inboxes, panels and
  cards sit at fixed places in that world. The camera pans, pushes in and pulls back; elements slide into
  frame from outside it.
- Never a couple of small cards popping onto an empty background. If the frame looks mostly empty, the
  world is too small or the camera is too far out.
- The world fills the frame AROUND the transparent caption strip. A pull-back still fills that surrounding frame. Pack the world tighter, or end the pull-back
  closer, rather than shrinking everything to thumbnails.

  Check on the board: does the frame feel full the whole time, and does the camera travel?

## 2. Real interfaces, not boxes

- When the words name a product, show something that looks like it: a mail app has a toolbar, a search
  bar, labelled rows, sender names and subjects; a settings window has a sidebar with the item selected.
- Product marks come only from official files listed in the reel's `motion/assets.json`. They are never
  redrawn, recoloured or imitated. With no official file on disk, write the product name as text.
- Use believable sample content (senders, subjects, amounts) that fits the user's topic. Never real
  private data.

  Check on the board: would a viewer recognise the app at a glance?

## 3. Lift and depth on every element

- Give each window or card layered shadows (a tight one plus a wide soft one), a faint top highlight and,
  where it sits on a surface, a floor shadow.
- Move the background slower than the foreground (parallax).
- Use scale, fade and blur with distance for anything arranged in depth (a ring, a stack, a row going back).
  Reel scenes use GSAP and CSS only; the optional 3D glass card follows [3d.md](3d.md).
- A small lift with a deeper shadow marks the element the voice is talking about.

  Check on the board: does anything look flat or pasted on?

## 4. Moves land on the words

- Time arrivals, stamps, highlights and camera stops with the `times` command in [Build motion](motion-build.md).
  A short lead-in can help a move settle on its word; judge it in the scene video.
- Name each rest point (field `holds`) so checks inspect settled text. After a recut, follow Build motion's
  rebuild steps; timing does not update itself.
- Ease in and out on camera moves; a slight overshoot on things that land; no linear slides except slow
  drifts.

  Check on the board: does each move hit its word?

## 5. Contrast and backdrop

- Dark elements on a light backdrop, or light on dark; never a dark object on a dark background with
  nothing separating them.
- Vary the backdrop across the reel (for example a dark desk with a dot grid and soft glows, then a warm
  cream grid) so neighbouring beats don't blur together.
- Keep the user's accent colour for the one thing that matters in each beat (a ring, a connector, a
  highlight), not for everything.

  Check on the board: does the important thing pop?

## 6. Room for the face and the captions

- Follow [Build motion: Scene areas and the face](motion-build.md#scene-areas-and-the-face) for area sizes
  and the user's full-screen choice.
- Nothing, backdrop included, may paint inside `caption_band` on any frame of the beat being checked,
  including pauses; the strip stays transparent. This is machine-checked, alongside text checks at rest points.
  Build the backdrop and camera layer as two clipped panes above and below the band, so no move crosses it.
  Keep those clips fixed in area coordinates while moving the content inside them. Caption-band placement
  and suggested bounds for each area are in [the scene contract](motion-scene.md#required-files-and-fields).

  Check on the board: is the speaker visible where they should be, and can the captions be read?
