# editor-superengine

Raw talking-head recording to a finished spoken cut, with every boundary verified against the waveform... then the design loop for the reel's visuals.

## Demo

_Demo placeholder. A walkthrough of a full first-cut pass (probe, ruling, waveform gate, silence budget, ear pass) lands here in a future release._

## What this plugin does

You point it at a raw camera file and an approved script. It measures the file instead of believing its container, transcribes with word timestamps, ranks trim candidates for you to rule on, and then audits every cut boundary against the measured RMS envelope, because ASR word ends run early by up to 0.54s and that is enough to amputate a punchline. Gaps are tightened in source coordinates so nothing depends on a render existing. The whole cut is then gated against a silence budget, the one check that is aggregate rather than local: a reel can pass every per-gap cap and still drag, because the defect is the sum.

The second half of the plugin is the design-iteration loop for the reel's visuals. Directions before polish, one parameter factory per element under iteration, tweaks shipped as ladders rather than single attempts, and every ruling taken from a rendered frame. It exists because the same hook took roughly 590k tokens to land the conversational way and 12 parametric rungs to land the right way.

## Tone

**This plugin is written for operators doing editing work, not for beginners.** It is the documented tone exemption in `docs/plugin-conventions.md` ("If your plugin is for a different audience... explicitly state the tone shift in the plugin's README"). Expect an expert register: ffmpeg filter graphs, dB floors, GOP sizes and CRF values are used without translation, and instructions are stated once rather than narrated step by step. There is no hand-holding and no celebration of small wins here. If you want the plain-English register, the other REVXL superengines carry it.

## Skills

### `editor-start-here`
**Triggers:** "edit my reel", "cut this talking head", "first cut", "tighten the gaps", "design the hook", "motion comps", "where do I start with editing", "editor superengine".

The router. Names the pipeline order, sends you to the right skill for the ask, points at the four shared references, and runs the dependency check before anything touches a file.

### `reel-first-cuts`
**Triggers:** "cut this reel", "build the A-roll", "tighten the gaps", "the pause after X is too long", "make it 1.15x", "why does this cut sound clipped", "there's an orphan word", "the gap drags".

Raw recording to finished spoken cut in one build pass: probe and calibrate, transcribe with word timestamps, line-selection ruling, waveform-verified EDL, gap tightening, speed ruling, one render from the raw, round-trip verification, silence budget, ear pass, and the ear-driven correction loop. Three stages stop for a human. Ships four analysis scripts plus a bundled word-timestamp transcriber.

### `reel-motion-comps`
**Triggers:** "design the hook", "motion comps", "direction comps for the reel", "hook treatment options", "ladder the blur", "iterate this visual", "reel design pass", "comp the intro".

The design-iteration loop for reel visuals: divergent directions over the real plates, a parameter factory per element, ladders instead of single attempts, a measurement kit that has caught real defects, and safe-zone pre-checks against Instagram's UI reserves.

## Agents

**No agents in 0.1.0.** Everything ships as skills, which keeps the plugin usable in Claude Desktop as well as Claude Code.

## Install

**Claude Code**

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install editor-superengine@revxl-marketplace
```

**Claude Desktop**

Settings > Extensions > Browse, add the `joeoliveimpact/revxl-marketplace` marketplace, then install **editor-superengine**. Skills load automatically; agents and slash-commands are Claude Code only, and this plugin ships neither.

## Dependencies

| Dependency | Why | How to get it |
|---|---|---|
| `ffmpeg` and `ffprobe` on PATH | every measurement, gate and render | ffmpeg.org, or your package manager |
| Python 3.10+ | the five bundled scripts | python.org |
| `faster-whisper` | the bundled word-timestamp transcriber | `pip install faster-whisper` |
| A browser | motion-comps previews and review pages | any modern one |

`faster-whisper` is optional if you bring your own transcript. Any backend works as long as its output satisfies the contract in `${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/references/transcription-contract.md`: word-level timestamps, VAD on, and a hard failure when `words` is empty. No MCP servers, no external accounts, no other plugins required.

## Compatibility

| | Claude Desktop | Claude Code |
|---|---|---|
| Skills | Yes | Yes |
| Agents | None shipped | None shipped |
| Commands | None shipped | None shipped |
| Hooks | None shipped | None shipped |

## What ships in 0.1.0 and what does not

**Ships:** `editor-start-here`, `reel-first-cuts`, `reel-motion-comps`, plus four shared references (house rules, the frame-zero hook standard, preview-before-render, and the art-director design prompt).

**Deferred to 0.2:**
- `reel-sound-pass` ... music, SFX spotting and mastering levels.
- `design-canvas-review` ... the single review surface the motion loop refers to.
- The Design / Higgsfield / HyperFrames router.
- Zoom and punch-in suggestions on the spoken cut.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT... see [LICENSE](LICENSE).

## Marketplace

Part of [revxl-marketplace](https://github.com/joeoliveimpact/revxl-marketplace).
