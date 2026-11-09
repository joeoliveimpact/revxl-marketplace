# editor-superengine

Your raw talking-head recording, edited into a finished reel. You pick on boards; Claude does the editing.

## Demo

_Demo placeholder. A walkthrough from a raw recording to the finished reel lands here in a future release._

## What this plugin does

You record yourself talking. The editor sets up its own tools, checks your camera and mic before you film, and turns the recording into a tight spoken cut. You choose your lines and takes on the Cut Board, then fix anything you don't like on the Tweak Board. Once you sign the cut off, it adds what goes on screen (titles, lists, quotes, stat cards, end cards), captions, B-roll, colour, music and sound, and a cover. You watch a 720p preview first, and the final video is made only after you say it's good.

Every choice is made on a board, where you can see and hear it, never from a description. Nothing that costs money runs without your yes. You never type a command: Claude runs everything and tells you in plain words what is happening. Your look can be saved as a style, so the next reel starts where the last one ended, and you can copy the editing style of a reel you like.

## Skills

Start with **editor-start-here** ("edit my reel", "what's next"). It names the next step and hands over to the right skill, in this order.

### `editor-start-here`
**Say:** "edit my reel", "where do I start with editing", "what's next", "where am I with this reel", "start a new reel".

The guide. It works out where your reel is, says the next step in one line and starts it.

### `editor-doctor`
**Say:** "is the editor ready", "check the editor's setup", "open my editor hub", "restart my editor boards".

Sets up the editor's own tools the first time (it downloads and checks them itself) and keeps them working. It also opens the editor hub, the page that links all your boards and reels.

### `recording-preflight`
**Say:** "I'm about to record", "check my setup before I film", "does my mic sound ok", "test my camera".

Checks your camera and sound from a 10-second test clip before you record, so a bad setting doesn't waste a take.

### `reel-first-cuts`
**Say:** "cut this reel", "open the Cut Board", "fix it on the Tweak Board", "tighten the gaps", "two recordings", "sync camera and mic", "make Shorts from this long recording".

Turns the raw recording into a finished spoken cut. You pick the lines and takes on the Cut Board; pauses are tightened without clipping a word; you fix the cut on the Tweak Board until it sounds right. It also handles several clips, a separate mic, and cutting Shorts from one long recording.

### `reel-grade`
**Say:** "grade this reel", "fix the colour", "make it warmer", "the skin looks off", "match the colour between my recordings".

Sets the colour. The editor measures your footage, shows every colour option side by side on the Grade Board, and applies the one you pick only after you say yes. Optional.

### `reel-canvas-build`
**Say:** "plan what goes on screen", "add a scene", "lower third", "end card", "design the hook", "add a transition", "render it", "make the final video".

Plans, designs and renders what plays on screen over your cut. On the Beat Map you plan what shows on each line; on Sketches you pick one direction; then a few looks for the hook are tweaked until one lands. It renders a 720p preview for you to watch, then the final video once you OK it. Your styles live here too ("save this as my style", "make Style 2 my default", "auto edit").

### `reel-broll`
**Say:** "add B-roll", "use my clip over this line", "generate B-roll".

Places your own clips, or AI B-roll, as cutaways over chosen moments on the Beat Map.

### `reel-captions`
**Say:** "add captions", "pick a caption look", "highlight these words", "change the caption colour", "turn captions off".

The words on the video. It suggests which words to highlight, only words you actually said, and you pick the look on the Look Picker.

### `reel-sound-pass`
**Say:** "sound pass", "add music", "pick a track", "add sound effects", "clean up my voice", "mix the sound".

Finishes the sound after the cut is locked. You pick the music and every sound effect on the Sound Board. The editor cleans your voice (free by default), mixes and masters. A starter sound pack is downloaded the first time it's needed.

### `reel-cover`
**Say:** "pick a cover", "thumbnail", "cover photo", "pick the frame people see first".

Lets you choose a cover frame from the reel on the Cover Picker, with an optional short title in your own words. The cover can also be the reel's first frame. Optional.

### `reel-trials`
**Say:** "trial reels", "test a few hooks on this video", "try different openings".

Makes a few trial versions of one approved reel, each changing exactly one thing (the opening, the hook, the framing or the colour look), so you can compare them side by side. Optional.

### `pro-editor-handoff`
**Say:** "open this reel in Resolve", "send it to my editor", "files for Premiere or Final Cut".

Exports the finished reel as an editable timeline for DaVinci Resolve Studio or another editor. Only offered when you have Resolve Studio or chose another editor.

### `caption-writer`
**Say:** "write the caption", "is my caption optimized", "hook lines for the caption", "alt text", "which hashtags".

Writes or checks the text under your post (not the words on the video).

### `reel-teardown`
**Say:** "tear down this reel", "what would we fix", "why did this flop", "make a page I can send them".

Takes a reel that's already posted and shows what to fix, as one page to read or send to the creator. With shortform-superengine installed, the page also shows the same footage rebuilt; without it, the teardown is a diagnosis only.

### `style-decoder`
**Say:** "decode this reel's style", "make this editing style repeatable", "build a template from this style".

Measures how a reel you saved is edited and turns it into a style your next reels can follow.

## Agents

None. Everything ships as skills.

## Install

The plugin is built for Claude Code: the **Code** tab of the Claude desktop app, or Claude Code in a terminal.

**Claude desktop app (Code tab):** in a local session, click **+** next to the prompt box and choose **Add plugins** (or **Plugins**, then **Browse plugins**). Add the REVXL marketplace by its GitHub path, `joeoliveimpact/revxl-marketplace`, then install **editor-superengine**. All clicks, no typing in a terminal.

**Claude Code in a terminal:**

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install editor-superengine@revxl-marketplace
```

Then say "edit my reel". The first time, the editor sets itself up: it downloads its own copies of Python, Node.js, ffmpeg, a rendering browser, HyperFrames and the speech and cutout models, checks each one against its pinned fingerprint, and runs a short offline self-test. This needs the internet once and a few GB of disk. After that, editing runs on your computer.

## Dependencies

You don't install anything by hand: `editor-doctor` sets up everything the editor needs. On Windows it uses Git for Windows, which Claude Code on Windows already needs.

**Optional add-ons.** The editor works without every one of these.

| Add-on | What it adds | What you need |
|---|---|---|
| An NVIDIA graphics card (Windows) | faster transcription | nothing: the editor finds it and picks the faster engine |
| DaVinci Resolve Studio | the editable Resolve timeline (`pro-editor-handoff`) | Resolve Studio 21.1 or newer with a Studio licence on your computer, and external scripting set to Local in Resolve's preferences (the editor tells you how) |
| Auphonic | a paid voice clean-up instead of the free one | your own Auphonic key; every paid job shows its cost and waits for your yes |
| higgsfield-superengine | AI-generated B-roll (`reel-broll`) | that plugin set up with your own Higgsfield plan; you approve the prompt, then a second yes to the cost estimate before any credits are spent |
| shortform-superengine | scripting and hook writing; the full `reel-teardown` (the rebuilt footage needs it) | that plugin |

No MCP servers. No accounts are needed for the core editing path.

## Compatibility

| | Claude Code (desktop app Code tab, or terminal) | Claude desktop chat / Cowork |
|---|---|---|
| Skills | Yes | Not supported: the editor runs its own tools and local boards |
| Agents | None shipped | None shipped |
| Commands | None shipped as plugin commands; the Cockpit adds `/editor`, which opens its pane (optional, never needed) | n/a |
| Hooks | The Editor Cockpit (a quick-menu pane, a progress band and a status line). It's a helper only; every skill works without it | n/a |

## Privacy

Your recordings, styles and boards stay on your computer. If something fails, the editor can offer a short failure report: you see exactly what would be sent and choose Send or Skip, and it never includes your keys or your content.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE). Third-party notices are in [LICENSES/NOTICE](LICENSES/NOTICE); GSAP is under its own licence ([runtime/gsap/GSAP-NOTICE](runtime/gsap/GSAP-NOTICE)).

## Marketplace

Part of [revxl-marketplace](https://github.com/joeoliveimpact/revxl-marketplace).
