# Transitions

Nothing is added automatically. On the Beat Map, choose Transition on the beat,
then choose the duration and any direction or colour. None keeps the hard cut.
Two or three per reel is a suggestion, never a limit; use more when they fit.

| Choice | When it fits | Settings |
| --- | --- | --- |
| flash | A bright accent on a change of thought | White, black, or a six-digit hex `color` |
| whip | A fast directional change | `dir`: l/r/u/d |
| zoom | A quick push through a cut, settling out after | No extra setting |
| glitch | A brief digital interruption | Deterministic block and RGB colour streaks |
| fade | A quiet entrance or exit for an overlay | `edge`: in/out/both |
| push | An overlay sliding on or off | `edge`, `dir`: l/r/u/d |
| wipe | An overlay revealed or hidden by a moving edge | `edge`, `dir`: l/r/u/d |
| shader | A scene entering or leaving through a shader | `edge`, `shader` |

Flash, whip, zoom and glitch sit on one cut from `work/cuts.json`:
`segments[1:].out_in_f`. Set `at_cut_frame` to that integer. `dur_frames` is
frames **each side** of the cut, from 1 to ceil(fps/3). The span is
`[at_cut_frame - dur_frames, at_cut_frame + dur_frames)`, end exclusive.
At cut 150 with duration 6, only frames 144 through 155 carry the transition.
Exactly one cut must lie strictly inside that span. Two declarations on the
same cut are refused. Ordinary a-roll moves still cannot run across a cut.
These effects use only the existing master: no removed frames, true crossfades
or media handles are needed.

In a pro hand-off, whip, zoom and glitch travel as finished-picture Master clips; flash, fade, push, wipe and shader stay in the overlay layer.

Fade, push and wipe use an overlay beat's own media or plate; the beat needs
layout `overlay`, a `scene`, or `broll`. Shader requires a scene. Set
`at_cut_frame: null`, `edge: in`, `out`, or `both`, and whole-frame duration
from 1 through floor(min(fps, beat length / 2)). In uses
`[start_f, start_f + dur_frames)`; out uses `[end_f - dur_frames, end_f)`.
The effect stays inside the beat and resets exactly on its window's end.

Shader choices: `light-leak`, `sdf-iris`, `chromatic-split`,
`cross-warp-morph`, `flash-through-white`, `glitch`. The installed browser is
checked before rendering. Without WebGL, the scene uses a fade and the plan
says: "shader not available on this machine, used a fade". A missing or wrong
package version needs setup repair. The pinned renderer uses one ordered
scene chain: overlapping shader beats are refused; choose fade on one beat.

The saved style's `transitions.allowed` narrows this menu when nonempty;
`[]` means the whole menu. Reel choices take precedence over saved choices.
`transitions.sfx_pair: true` writes `work/transition_cues.json` for a later sound-pass step; the sound pass doesn't offer them yet. There is one cue per cut or overlay edge. Turning it off
removes that generated cue file. This never mixes a sound or changes voice
audio; compose continues to stream-copy the selected audio.

The board uses a JSON copy of the menu, checked by `transitions.py --selftest`.
`transitions.py --menu-json` prints the authoritative menu for tooling.

The shader bundle is `@hyperframes/shader-transitions@0.8.184`, Apache-2.0,
copied at render time from the pinned installation into the render's vendor
folder. It is never fetched from a CDN or committed here. Its bundled
third-party notices must accompany redistribution. The integrator appends
the licence record at merge.
