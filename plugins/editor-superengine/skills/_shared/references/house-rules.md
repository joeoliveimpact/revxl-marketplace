# House rules

Four rules that govern every editing job in this plugin. They are not style preferences.
Each one is here because breaking it cost a whole build.

---

## 1. Duplicate the source before the first cut

**Duplicate first. Always. No exceptions.** Before the first trim, silence pass or layout
change lands on a recording, duplicate the file or the project and edit the copy. This
applies to any recorder or NLE: a cloud recorder's project, a local master, a timeline in
an editor.

- Name the copy on a version convention, for example `<Reel name> - V1 EDIT (working)`.
  Bump to V2, V3 for later passes.
- The untouched original stays the reference. Reverting is then "open the original", not
  "reconstruct the cut list from memory".

**Why:** an empty cut list only restores a clip whose cut history is still intact and
correct. It does not protect against a bad cut list applied and re-applied across passes,
and it gives you nothing to A/B the edit against. A pristine original costs one copy and
removes the entire class of "can we get the take back" risk.

---

## 2. Build from the source, in the fewest generations

**Every render starts from the highest-quality original available, never from the last
file you made.**

- **Count the generations before you build.** Each lossy encode costs detail permanently.
  A chain with more than two is wrong. Grade, speed, captions and cards fold into **one
  final pass**, not four stacked ones.
- **Downscale once, as late as possible, at high quality.** Never let the resolution drop
  happen inside a fast or cheap encode, and use an explicit scaler (`flags=lanczos`);
  the ffmpeg default is not good enough for a 2:1 drop.
- **Intermediates are near-lossless**: CRF <= 14, `preset slow`. The cheap-and-fast preset
  belongs on throwaway probes, never on anything a later stage reads.
- **Prove it with a number, not a feeling.** Edge energy via a Laplacian convolution plus
  `signalstats` on the same frame both ways.

**Why:** one master shipped four generations deep, with the 4K to 1080 downscale sitting on
the weakest link and the default scaler. The reviewer saw it immediately. Rebuilding from
the raws in two generations measured **+19%** edge energy on a still and **+11%** on the
finished file, and the cut round-trip verified every boundary unchanged.

---

## 3. Never judge picture on a proxy

**A file built small enough to send is not a file anyone can judge picture on.**

- Judge **picture** on the real master, served locally, never on a downscaled or
  low-bitrate copy.
- A proxy is acceptable **only** for a judgment its degradation cannot touch: an audio A/B,
  a pacing pass. It must be **labelled as a proxy in the same message**, naming what was
  reduced.
- If a file is too large to send, **serve it**. Do not shrink it and stay quiet about the
  cost.

**Why:** a music A/B was sent at 608x1080 and 1.2 Mbps... 32% of the width and **8.6% of the
bitrate** of the master. The reviewer judged the picture off it and was right to call it
bad. The proxy was fit for the question that was asked and unfit for the question the
reviewer actually had.

---

## 4. Half-ass setup makes half-ass output

**Load every rule and system that governs the work BEFORE the first file is written, never
after a rejection.** The setup is not overhead in front of the work. It is the work's first
step, and skipping it does not produce a rougher version of the right thing. It produces a
confidently finished version of the wrong thing.

Before anything gets designed, planned or animated, read the design system's own docs, not
just its token files. Tokens give you hex values. The docs give you the house rules.

**Three failure modes this rule exists to stop:**

1. **Compliance is not quality.** Passing lint, passing the safe-zone gate and matching
   every token is a *fit* test. None of it asks whether the frame lands.
2. **Constraints cannot generate a design.** A safe zone tells you where things may not go.
   If the layout falls out of the constraint, there was never an idea in it.
3. **Never invent copy to solve a layout problem.** The approved script is frozen. A
   headline that is not in the voice-over is not a design decision, it is a new claim on
   screen.

**Show cheap, divergent directions before building one finished thing.** Two to four low-fi
options that differ in *approach*, not in polish.

**Why:** a nine-artboard design pass was built from token files alone, with the design
system's own rules unread. It shipped with the wrong typeface, no signature accent, display
type at a fraction of the in-feed floor, hairlines too thin to see, and metadata labels
invented for a reviewer rather than a viewer. The verdict was "thin in quality, colour,
contrast and overall design pop". The second pass fixed the measurable proxies and was still
wrong, because the direction was never the problem the measurements could see. Both passes
were wiped.
