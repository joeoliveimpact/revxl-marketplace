# plugin-doctor

Fixes stalled Claude plugin updates so you're never stuck on an old version.

## When to use
- A plugin updated in the marketplace but your install still shows the old commands/behavior.
- "Check for updates" does nothing.
- Installing from the in-app directory fails with `404 Not Found: plugin_...`.

## Use
Say **"my plugin won't update"** or run `/plugin-doctor`. It diagnoses which of the two stall types you have, then fixes it — for a stuck version it runs the staged, reversible [marketplace-updater script](https://github.com/joeoliveimpact/Claude-marketplace-updater) for you (Claude Desktop quits and reopens mid-fix; your chat survives). Manual CLI/UI walkthroughs remain as fallbacks.

## Your data is safe
Plugin config, story banks, and brand settings live outside the plugin install (in `${CLAUDE_PLUGIN_DATA}` and `~/.claude/revxl/`). Reinstalling a plugin never touches them, and the doctor takes a temp backup anyway before fixing.

## License
MIT — see [LICENSE](LICENSE).
