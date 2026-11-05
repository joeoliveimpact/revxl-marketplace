# Reel teardown: commands, fallback rubric and common mistakes

Detail for `editor-superengine:reel-teardown`. Claude runs every command with the Bash tool,
from the teardown folder (`teardowns/<creator> <MM.DD.YY>/`, named that way from the start),
except the transcription, which runs from the client's workspace folder (SKILL.md stage 0); go
back to the teardown folder after it.

## Contents

- The editor's ffmpeg and ffprobe
- Stage 0: pull a reel link
- Stage 0: length
- Stage 1: frames and strips
- Pace for the 90 s gate
- Fallback craft rubric
- Check the page: the launch entry
- Common mistakes

## The editor's ffmpeg and ffprobe

Get the paths once per session. If either command fails, the editor setup isn't finished:
invoke `editor-superengine:editor-doctor`.

```bash
FF=$(<editor python> -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/skills/_shared'); import runtime; print(runtime.tool('ffmpeg'))")
FP=$(<editor python> -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/skills/_shared'); import runtime; print(runtime.tool('ffprobe'))")
mkdir -p work site/img
```

## Stage 0: pull a reel link (only after the client said yes to the cost)

1 SocialCrawl credit, which covers the details and the video download. The key comes from
`SOCIALCRAWL_API_KEY` or `~/.config/socialcrawl/api_key`; never echo it.

```bash
KEY="${SOCIALCRAWL_API_KEY:-$(cat ~/.config/socialcrawl/api_key)}"
curl -s -H "x-api-key: $KEY" "https://www.socialcrawl.dev/v1/instagram/post?url=<URL-ENCODED LINK>&download_media=true" -o work/post.json
```

Fields: `data.post.content.author.username` and `.display_name`,
`data.post.content.engagement.views`, `.likes`, `.comments`, `data.post.content.published_at`,
and `data.post.ext.download_media_urls[0].cdn_url`. Use that last one: it lasts, while the plain
`media_urls` links expire.

```bash
curl -sL "<cdn_url>" -o work/reel.mp4
```

A failed pull (an error in the reply, no `download_media_urls`) is a failure at step `pull`.
Say whether the credit was spent.

## Stage 0: length

```bash
"$FP" -v error -show_entries format=duration -of default=nw=1:nk=1 work/reel.mp4
```

Then transcribe with the command in SKILL.md stage 0, run from the client's workspace folder so
the workspace language is read. It takes no `--probe` and no `--edit-map`: a teardown has neither.
Pace and sentence onsets come from the word list in `work/tx.json`.

## Stage 1: frames and strips

The opening strip is the first six times: 0, 0.5, 1.5, 3, 8 and 15 s (on a reel under 16 s,
use the end minus 1 s for any time past it). The body strip is six frames spread evenly from
25% of the length to the end minus 1 s, so the two strips never repeat on a short reel.
`<length>` is the duration from stage 0.

```bash
for t in 0 0.5 1.5 3 8 15; do "$FF" -v error -y -ss $t -i work/reel.mp4 -frames:v 1 -vf scale=360:-1 work/o_$t.png; done
BODY=$(<editor python> -c "L=<length>; print(' '.join(f'{0.25*L + i*(0.75*L-1)/5:.2f}' for i in range(6)))")
i=0; for t in $BODY; do "$FF" -v error -y -ss $t -i work/reel.mp4 -frames:v 1 -vf scale=360:-1 work/b_$i.png; i=$((i+1)); done
"$FF" -v error -y -i work/reel.mp4 -frames:v 1 -vf scale=540:-1 -q:v 3 site/img/frame0.jpg
"$FF" -v error -y -i work/o_0.png -i work/o_0.5.png -i work/o_1.5.png -i work/o_3.png -i work/o_8.png -i work/o_15.png -filter_complex hstack=inputs=6 -q:v 3 site/img/frames-open.jpg
"$FF" -v error -y -i work/b_0.png -i work/b_1.png -i work/b_2.png -i work/b_3.png -i work/b_4.png -i work/b_5.png -filter_complex hstack=inputs=6 -q:v 3 site/img/frames-body.jpg
```

The strip captions and the method line name the real times used.

## Pace for the 90 s gate

Measured pace = spoken words / (last word end minus first word start), in words per second,
so silences don't flatter it.
A rebuilt script's length = its spoken word count / that pace. Under 90 s passes.

## Fallback craft rubric (when reel-scripter's references aren't available)

Score each part 0 to 100 on the writing alone. The anchors below are rough points; score
between them.

| Part | About 20 | About 50 | About 80 |
|---|---|---|---|
| Hook | The opening states the conclusion or warms up; nothing names the viewer; nothing on screen at frame 0, or text that just repeats the speech | One clear subject and some reason to stay, but it arrives late or hedges | Viewer named in the first seconds, one open question or contrast, spoken line and frame-0 text working together |
| Body | One idea told once in a straight line; no seams; the strongest lines buried | Clear order and a good example, but long stretches with no new question | Every stretch earns the next one: typed re-hooks at the drop-off points, best line early, every loop it opens gets closed |
| CTA | No ask at all | An ask that is vague, stacked with other asks, or doesn't fit the metric | One ask, matched to the metric, easy to act on, set up by the content before it |
| Overall | The parts fight each other or one is missing | Works, but the weakest part holds it back | The parts serve one goal; nothing to cut |

Overall is a judgment of the whole, not an average. A missing CTA keeps it low.

## Check the page: the launch entry

The Browser pane can't run the checks on a page opened from a file, so serve it locally.
Find a free port:

```bash
<editor python> -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])"
```

Add this entry to `.claude/launch.json` in the client's workspace, using Python's `json` module
so existing entries stay. If the file is missing, create it as
`{"version": "0.0.1", "configurations": []}` first. If an entry with the same name exists,
replace that entry only.

```json
{
  "name": "teardown-<folder>",
  "runtimeExecutable": "<editor python, written out as its full path>",
  "runtimeArgs": ["-m", "http.server", "<port>", "--bind", "127.0.0.1", "--directory", "<absolute path of teardowns/<folder>/site in the client's workspace>"],
  "port": <port>
}
```

Then `preview_start` with the name `teardown-<folder>`, set the width to 375 px and run the
four checks in SKILL.md stage 5.

## Common mistakes

| Mistake | What it costs | Fix |
|---|---|---|
| One hook, hand-written | The client has nothing to pick from | hook returns 3 to 5 options; the client picks one |
| Re-hooks placed by feel at round times | The first lands before the clock allows, none are typed, loops aren't tracked | rehooks places and types them; its pay-off check shows every loop closing |
| An unsupported line sold as "the share line" | A skeptic hears it, and the creator repeats it as fact | viral's skeptic check catches it; mark it as a question for the creator |
| Running rehooks on the original | It refuses anything over 90 s and names no next step | Run it third, on viral's result |
| Rebuilding by hand when shortform-superengine is missing | A fake rebuild that looks like the real one | Diagnosis-only page, with the install offer |
| A screenshot as the only proof | The pane can time out and nothing gets checked | The JavaScript checks first, the screenshot second |
