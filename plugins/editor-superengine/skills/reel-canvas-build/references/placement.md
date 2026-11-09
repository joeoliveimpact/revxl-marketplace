# Keeping captions off the face

The face step measures a protected head box, from the top of the head down to
75% of the person's height. It needs the cut master first. Before every captioned
preview, follow [build.md, section 2](build.md#2-make-the-preview) to measure any
missing or older anchors, whatever the Follow my face setting. After a new cut,
measure the anchors again. Follow my face only moves the camera.

The placer reads the zoom, its centre and the video layout throughout each
caption's time on screen. It maps the protected box into the final picture,
including the movement between zoom settings, and leaves clearance around it.
The caption band must also fit inside Instagram's safe text area, away from
the interface at the top, bottom and sides.

It tries a low spot first, then a spot below the protected head, then the top
of the safe area. The first spot that fits without covering the head wins.
It does not reduce the requested zoom to force a fit.

If every spot covers the protected head, it uses the spot inside the safe text
area with the smallest overlap with the zoomed head box over the whole chunk.
If two spots cover the same area, the lower spot wins. This does not stop the
caption step. Claude tells the client in plain words: "Captions from X to Y
seconds overlap part of the speaker's head because the shot is tight; the
caption step may shorten or drop them." A caption band taller than the safe
text area still cannot be placed.

Active still hook titles and layout card plates are kept clear of captions whenever a safe spot exists, including a spot just below the still.
A spoken opening hook shows its own words instead of duplicate captions; other captions sit just below it when that clears the eyes-to-mouth band, with the full head protected after it ends.
