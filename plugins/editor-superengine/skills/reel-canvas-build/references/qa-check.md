# Check the reel before posting

Use `<editor python>` and `<reel folder>` exactly as defined in this skill's
SKILL.md. Claude runs both commands from the client's workspace.

Before making the 1080p final:

```bash
<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/checks/check.py" <reel folder> --phase pre
```

After making the final, replace `<master>` with the finished video's path:

```bash
<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/_shared/checks/check.py" <reel folder> --phase all --render <master>
```

The check reads the cut, spoken words, Beat Map and captions before rendering.
Afterward it also checks the finished picture and sound, including frame count,
gaps, likely freezes, text placement and pacing. The discovered check modules
write their findings to `work/qa.json`; the hub's Quality check shows them.

- `card-on-face`: measured overlay cards cover your eyes or mouth; missing or stale card boxes share `placement-not-judged` with captions until you make a preview.

Without positions for every enabled caption, pre QA blocks with "placement not judged yet (make the preview)";
it cannot report clear until a preview has placed them, including when captions were planned again.

Blocks stop the final: do not make it when the pre check blocks, and do not
deliver it when the full check blocks. Preview runs this same pre check after saving its file and positions;
blocks stop it before "Preview ready" or an OK invitation. OK and master rerun the same gate.
Show every grouped block line, help you make the named change, then make the preview again and OK it.
Warnings are suggestions: explain the suggested improvement and let the client
choose. Pacing and dead zones never block.

If a caption covers your face under an overlay card or hook-title scene, on the Look Picker open Advanced controls
and untick "Captions under small overlays", then Send and make a new preview. For a plain hook, follow the check's
advice: it only says to shorten the hook to one line when re-placing every blocked caption with that height clears it.
Otherwise, or without an overlay, choose "No captions" on the Look Picker, then Send and make a new preview.

If the client says a flagged freeze is intentional, Claude records that specific
moment in `work/qa-ok.json` as `{"allow":[{"check":"frozen","at":<s>}]}`,
using the finding's time in seconds. Preserve existing approvals when adding it.
Never approve a freeze on the client's behalf; rerun the full check afterward.

Review aids live in `work/qa/`: `contact.jpg` shows one frame per second,
`cut-NN.png` shows consecutive frames around each cut with the sound waveform
and the spoken words when available, and `phone-720p.mp4` is a phone-size copy.
`index.json` lists the available files; the hub links them under Quality check.
A failed optional aid warns and leaves the other pieces available. Watch the
phone copy with sound as well as inspecting the still images.

## Eye test

Claude opens `work/qa/contact.jpg` and the cut strips and answers these questions
YES or NO for each relevant moment. These are our own viewing questions; code
cannot decide whether a visual communicates well. Record a NO with its time and
a concrete fix, then inspect the revised pictures. Do not infer motion or sound
quality from a contact sheet alone; replay the video where needed.

1. Can I read the main message at phone size without stopping to enlarge it?
2. Do the frames on either side of each cut make the spoken thought easy to follow?
3. Do the visible caption words agree with the words beneath that cut strip?
4. Is the speaker's expression clear wherever their face carries the message?
5. Does each shown number or example explain the point being made at that moment?
6. Do the opening and closing pictures give the viewer a clear beginning and ending?

Tell the client the useful findings in ordinary language, with suggested fixes.
Keep paths, JSON and checker names out of the client-facing explanation.
