---
name: editor-superengine:style-decoder
description: Decodes the editing style of a reel saved on the client's computer into a reusable style later edits follow. Use on "copy this creator's style", "decode this reel's style", "make this editing style repeatable", "add this reel to my style X" or "build a template from this style". NOT for a content or hook teardown of a posted reel (that's reel-teardown).
---

# Style Decoder: a reel file → a reusable editing style

## Output contract (every finished run, in this order)

1. **`style-spec.json`** — the style as rules, each tied to the frames that prove it.
   It lives at `editor/style-decoder/styles/<slug>/style-spec.json` in the client's folder.
2. **Contact sheets** — `evidence/<group> - Contact Sheet - MM.DD.YY.jpg`, the proof
   frames for each rule group, shown to the client at the review gate.
3. **The held-out file** — `heldout.json`: frames the rules never cited, with a
   pass / fail / n/a verdict for every rule on every frame.

Also written: the runbook (`<Name> - Style Runbook - MM.DD.YY.md`), which the blind
check reads. Tell the client in plain words what each file is for. Never paste JSON,
paths or command output to them.

## Re-invoke guard (read before stage 1)

- If the conversation was compacted since this skill loaded, invoke it again first.
- If the skill is invoked again mid-run, **pick up where the files say you are; never
  start over.** Check `editor/style-decoder/styles/<slug>/` before running anything:
  - `style-spec.json` exists → never run `init` again (it refuses anyway).
  - the video is in `spec.sources` → never add it again (`add-source` refuses a repeat).
  - `frames/`, `captions/`, `palette.json`, `audio.json` exist → skip those passes.
  - `heldout.json` holds verdicts → never regenerate it (the script refuses); continue scoring.
  - `status` is `approved` → the run is done; only refine with a new reel.

## How it works

Scripts measure (frames, cuts, colours, loudness). **You judge** (layouts, type,
motion, structure) by reading frames, and every judgment goes into the spec with
`evidence[]`, `confidence` and `observed_in`. `UNKNOWN` is a legal value: never guess.
The client never types a command; you run everything.

- `<editor python>` is the editor's own Python. Windows: `"$(H="$LOCALAPPDATA/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/Scripts/python.exe"`. macOS: `"$(H="$HOME/Library/Application Support/revxl/editor-superengine"; P="$(cat "$H/home-pointer.txt" 2>/dev/null | tr -d '\r\n')"; [ -n "$P" ] && [ -f "$P/state.json" ] && H="$P"; printf '%s' "$H")/venv/bin/python"`. Keep the quotes.
  Run every script from the client's workspace folder.
- Every command below is a script in `${CLAUDE_PLUGIN_ROOT}/skills/style-decoder/scripts/`.
  Run it as `<editor python> "<that folder>/<script>.py" <arguments>`, quoting the path.
- The full rules (schema, merge, the confirmation ladder):
  `${CLAUDE_PLUGIN_ROOT}/skills/style-decoder/references/stylespec-contract.md`.
  Frame passes: `references/styleframes-contract.md` in the same skill.

**Saved styles** (list, show, rename, default, delete, restore, Standing notes, and saving a decoded style as a new style): ${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/saved-styles.md.

## The stages

| # | Stage | You run | Gate |
|---|---|---|---|
| 1 | Intake | `init`, `add-source` | client confirms the style name |
| 2 | Measure | `styleframes --pass all`, `stylepalette`, `styleaudio` | — |
| 3 | Decode | you read frames, write rules + runbook | — |
| 4 | Check | `validate`, then `coverage` | both pass, or fix |
| 5 | Review | `contact-sheet` | **client reviews** |
| 6 | Confirm | `heldout`, then blind reconstruction | fix every fail |
| 7 | Publish | set `approved`, `index` | **client approves** |
| 8 | Template (optional) | `styletemplate` plan → build | needs a look |

### 1. Intake: a local file only

Ask for the reel as a video file on this computer. If the client gives a link, say
plainly: "I can only read a video that's saved on your computer. Save the reel to a
file and tell me where it is." Never download, never fetch, never accept a link.
Agree a short slug with the client (e.g. `bold-explainer`), then:

`stylespec.py init <slug> --name "<Display Name>"`
`stylespec.py add-source <slug> "<path to the video file>"`

`add-source` copies the file in as `sources/src-01/source.mp4` (byte for byte) and
records its length, size and frame rate. It refuses a link or a missing file with a
plain message; pass that message on in plain words.

**Transcript.** If the client has already run reel-first-cuts on this same video, copy
its `.words.json` to `sources/src-01/transcript.json`; styleaudio and the blind check
use it. Otherwise go on without one: speech and music then read `UNKNOWN`, which is
honest, and nothing claims to have heard the audio. Never transcribe as part of this
skill.

### 2. Measure

`styleframes.py <slug> src-01 --pass all`
`stylepalette.py <slug> src-01`
`styleaudio.py <slug> src-01`

`--pass all` = base frames, scene cuts, hook and cut bursts, caption-band strips. If
the captions sit outside 33–72 % of the frame height, re-run
`--pass captions --band-top <n> --band-bottom <n>`.

### 3. Decode (your judgment)

Budget: about 120 frames *read* (config `style.frame_budget`). Before writing audio
rules, read `references/styleaudio-contract.md`; before minting colour tokens, read
`references/stylepalette-contract.md`.

1. Read the **base frames fully**. Classify each into layout modes and write
   `sources/src-01/layout_timeline.json` (contiguous `{t_start, t_end, mode_id}`
   segments). `cuts.json` is a candidate list: scene-detect misses panel swaps and
   fires on caption pops, so cross-check it.
2. Read the **hook burst** (0–3 s) fully; read cut bursts only at layout changes plus
   a few caption events.
3. Write `measure-request.json` (one keyframe per mode, crops of text zones,
   micro-bursts for the animations you must time), run `--pass measure`, read the
   results. Overshoot then settle = `back/elastic`, smooth = `power-out`, even steps
   = `linear`, else `UNKNOWN`.
4. Re-run `stylepalette.py --zones <file>` with the real panel geometry.
5. Read the **caption strips** to recover the grouping rule (thresholds and
   algorithm, not a word count).

**Determinism is the bar.** Two editors following the spec must make the same
frame. Capture: layout modes, grammar and an inlined timeline · transitions ·
overlay treatments · typography roles (`font_guess` and `closest_available`,
`size_metric`, `mode_scope`; mark the one default caption role `caption_default:
true` with `baseline_y_pct_of_height`) · caption mechanics and content rules
(lexicon, role precedence, transcript normalization: verbatim means the spoken word,
not the ASR token) · colour tokens and skins · motion rules (duration + easing
class, anchors) · pacing · beats, patterns, screens · assets · audio · and
**`ingredients[]`**, the shopping list a new video must supply. Never restate a rule
in two places; reference its id.

Write the runbook beside the spec: identity, the style in one paragraph, required
ingredients, layouts with sheets, transitions, typography, caption rules, colour,
motion (UNKNOWNs flagged), pacing, beat template, audio, assets, a "how to edit in
this style" checklist, open questions.

### 4. Check

`stylespec.py validate <slug>` → must print `VALIDATE PASS`.
`stylespec.py coverage <slug>` → fix each `GAP` it lists, or record it as an
open question. Run both again after every fix.

### 5. Review gate

`stylespec.py contact-sheet <slug>`, then show the client the sheets and the
runbook summary. Ask for the one-line music and sound-effect feel
(`audio.music.character`, `audio.sfx.character`) or `n/a`. You can't hear the
audio; don't pretend to. Wait for the client before going on.

### 6. Confirm: held-out screen, then blind reconstruction

`stylespec.py heldout <slug> --n 10` picks up to 10 base frames that no rule
cites and writes `heldout.json` with an empty slot per rule per frame. Read each
frame and fill every slot `pass`, `fail` or `n/a`; the scoring is your judgment. A
rule that only holds on its own evidence is a description of one frame: fix it or
set it `provisional`.

Then dispatch a **subagent** that reads ONLY `style-spec.json`, the runbook and the
transcript (if there is one), never the video or frames, and predicts what named
frames show. Every "I had to guess" is a missing field; every mismatch is an
ambiguity. Fix them, then re-run stage 4.

### 7. Publish

Before `index`: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/saved-styles.md` §5 (adapters and approved copy).

Only after the client approves: set `style.status` to `approved`, then
`stylespec.py index`. Tell the client that "approved" means the spec faithfully
describes this reel; it is proven to *reproduce* the style only after the first
real rebuild.

**Refine with a second reel:** stages 1–3 for `src-02` (a new `add-source`), write the
new rules to a candidate file, then `stylespec.py merge <slug> --source src-02
--candidate <file> --dry-run`, then without `--dry-run`. Exit 2 = conflicts: show the
client only the conflicts and new rules, and record each ruling in
`merge_log[].resolutions`.

### 8. Template build (optional)

Needs a design-system entry (the look; the registry starts empty, see
`references/designsystem-contract.md`). GSAP ships with the plugin; never download it.

`styletemplate.py plan <slug> --inputs <inputs.json> --stamp MM.DD.YY`
`styletemplate.py build <plan dir> --inputs <inputs.json> --gsap "${CLAUDE_PLUGIN_ROOT}/runtime/gsap/gsap.min.js"`

Exit 2 = a human ruling is needed; show it to the client. The build stops with an
error naming the field when the default caption role or its size or position is
missing; fix the spec, never the number. Details:
`references/styletemplate-contract.md`.

## When something fails

- "isn't set up on this computer yet" → run the editor-doctor skill, then retry.
- "Pillow … isn't installed" → the colour and contact-sheet steps need an image
  library the editor's setup hasn't added on this computer. Tell the client, finish
  what you can, and offer the failure report below.
- `DRIFT` → the copied video changed since it was added. Add it again as a new source.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `editor-superengine/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin editor-superengine --plugin-version 0.2.2 --skill style-decoder --step '<intake, measure, check, confirm, publish or template>' --error-line '<the error line>' --summary '<headline>' --body-file editor-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`<editor python> "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
