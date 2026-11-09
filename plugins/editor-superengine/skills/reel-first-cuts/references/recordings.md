# New reel and recording intake

For "Start a new reel", use the client's name or propose a short one and confirm it. Names start with a
letter, number or underscore, then use letters, numbers, spaces, `-`, `_` or `.`, with no trailing dot or space.
From the workspace, Claude runs (the client types nothing):

`<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/prepare_reel.py" "<reel>"`

It makes `<paths.videos>/<reel>/raw/` using `editor/editor.config.json` (default videos folder: `videos`).
If `mode` is `record`, tell the client in plain words where to drop the take: "I made your reel folder.
Drop your recording in its raw folder at <drop folder>. I'll check your recording setup first."
This drop location is the one exception to keeping paths out of client lines: they need to find the folder.
Invoke `editor-superengine:recording-preflight`, then wait for their take. Run the command again after it arrives.

- `single`: top-level `RAW.mp4` is ready for Stage 0. If it was missing and `raw/` held one video, the command
  duplicated that video to `RAW.mp4` (house rule 1). The original stays in `raw/`; an existing `RAW.mp4` is never replaced.
- `several`: leave the recordings separate and follow [several-recordings.md](several-recordings.md), using
  the returned sources as the takes, even if an older `RAW.mp4` exists; do not treat several recordings as one take.
- A failure stops intake; say what failed and ask for the missing detail. Never overwrite a source.

For an existing reel, run this intake once before Stage 0 too. All paths in the cutting stages are relative to
the configured reel folder. Keep using that folder, even where an example spells the default `videos/<reel>`.
