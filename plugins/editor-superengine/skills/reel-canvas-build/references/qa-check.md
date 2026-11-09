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

Blocks stop the final: do not make it when the pre check blocks, and do not
deliver it when the full check blocks. Tell the client, in plain words, what
is wrong, where it happens and what to fix. Fix it and run the check again.
Warnings are suggestions: explain the suggested improvement and let the client
choose. Pacing and dead zones never block.

If a caption sits on the speaker's face because the hook title leaves no room, shorten the hook to one line with `--hook-text` or drop `--hook-text` so the opening words become the hook; make a new preview.

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
