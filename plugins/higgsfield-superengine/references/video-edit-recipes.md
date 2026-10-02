# Video edits on live footage

Read this before any `video-edit` job on the client's own footage (Seedance 2.5 video-edit; the same order works on Kling O3 edit). Evidence: one client project, 09.30.26, about a dozen edits of phone clips. The two the client approved followed every rule below, and each miss broke one. SINGLE-SOURCE (1 project, several samples); drop a rule when the client's own results say otherwise.

## Before writing

- **Shot type, segment by segment.** Is each segment a selfie (face in frame) or a POV (hands only)? Check several frames across the whole clip, because phone clips flip between the two mid-take. Effects next to a real face got blocked as `nsfw` (2 of 2), so put effects on POV segments or away from the face.
- **Source:** upload the original file (`hf_rest.py upload`; it also records the length for pricing). The output is never sharper than the source, so a 720p source gives a 720p edit. Never edit an edit: every pass loses quality, so regenerate from the original instead.
- **Timing:** ask the client which hand movement each beat happens on, if they haven't said. Don't pick the moment yourself.

## Add an object to live footage: the prompt, in this order

1. "Edit @Video1. It is the sole edit master."
2. **Keep list,** led by the face or the hands: "Keep the hand and its movement, the table, the lighting and the camera exactly as they are."
3. **Region,** named against the body: "Region: the fingertips and the air just above the table."
4. **"Change only this:"** the object, its **size compared with the hand** ("about the size of a shoebox", never just "large"), its **depth** ("in front of his body, never behind his hand"), and its material.
5. **Start state:** what is in frame before anything happens ("Nothing is in the air before the hand opens").
6. **Stage beats tied to hand movements, never to times:** "each time the fingers pinch…", "when the hand tips forward…".
7. **Contact words:**
   - For a held object, say where the fingers touch it ("fingers curl over the front, thumb behind") and that it is "rigidly attached to the grip, following every movement of the hand".
   - For a released object, say it "leaves the fingers … and stays there".
   - Repeating objects get the full cycle: "the hand pulls back empty, then a new one appears between the fingertips".
8. Close with "All other visible content remains unchanged."

Avoid:
- Motion the client didn't ask for (orbiting, floating, drifting): the model performs it exactly.
- Several effects in one pass.
- One prompt reused across different shots.
- Negatives, and hype words like "real film VFX quality".

Worked example (neutral):

> Edit @Video1. It is the sole edit master. Keep the hand and its movement, the table, the lighting and the camera exactly as they are. Region: the palm and the air just above the table. Change only this: a small glowing paper lantern, about the size of a tennis ball. Nothing is in the air before the hand opens. Stage 1: as the fingers open, the lantern appears resting on the palm. Stage 2: the hand lifts and the lantern rises with it, held in the palm in front of the fingers, moving exactly as the hand moves. Stage 3: when the hand tips forward, the lantern leaves the palm, floats up and stays hanging in the air, glowing. All other visible content remains unchanged.

## Effects for compositing (often better than editing the footage)

- Effects that are mostly glow (light, holograms, sparks, sci-fi screens) can be generated on their own, on pure black, for a Screen/Add blend in the editor. Use a green screen only for solid, non-glowing objects.
- Make a reference still of the element first (`image-prompting`): "isolated on a pure black background; no floor, shadow, reflection or vignette". Match the camera angle of the client's shot. Check the corners are true black before compositing.
- Then animate the still. For a structure-locked restyle of a motion sketch: Kling O3 video-edit ignored the sketch's motion and froze (1 sample, 10.01.26). Test the cheapest tier first, and never go straight to 4k.

## Check every edit output

- Compare the downloaded file with the source using ffprobe: frame rate, duration, and width x height. Edits came back at 24 fps and a few frames shorter than 30 fps sources, which breaks a frame-for-frame overlay. Tell the client before they cut it in.
- Trust the file, not the job's metadata: Higgsfield stored vertical edits as "1280x720, 16:9".
- Two `nsfw` blocks on the same shot means change the structure (move the effect off the face, or use a POV segment), not the wording.
