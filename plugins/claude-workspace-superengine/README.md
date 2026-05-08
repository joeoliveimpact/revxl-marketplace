# claude-workspace-superengine

> Workspace lifecycle for Claude. Scaffolds, picks up, and closes out — disciplined session continuity.

![demo placeholder](../../docs/demos/claude-workspace-superengine.gif)

---

## What this plugin does

If you've ever come back to a Claude conversation and asked _"wait, what was I doing?"_ — that's the problem this solves. By writing structured notes after every session and reading them at the start of every new one, Claude picks up exactly where you left off. No re-explaining. No lost context.

Built on top of the four `agent-optimizer` override constraints (Intent Clarification, Least Complexity, Surgical Execution, Declarative Focus). Every skill enforces these — so you get continuity AND consistent quality across sessions.

---

## Skills

### `super-setup`
**Triggers:** "set up my workspace", "scaffold this folder", "initialize a new project"

Creates eight canonical scaffold files in any folder so Claude knows where things live:
- `RULES.md` — non-negotiable override constraints
- `CLAUDE.md` — system instructions, references RULES.md
- `ARCHITECTURE.md` — workspace map
- `GOALS.md` — primary objectives
- `PLANNING.md` — active initiatives
- `MEMORY.md` — index pointing to durable memories
- `Checkpoint.md` — accumulating session log
- `handoff.md` — next-session priorities

Optionally chains into `anthropic-skills:setup-cowork` for plugin/connector setup.

### `session-pickup`
**Triggers:** "pick up where we left off", "what's the status?", "where are we?", session start

Reads RULES.md → handoff.md → ARCHITECTURE.md → PLANNING.md → recent Checkpoint.md, runs any verifications flagged in handoff.md, and presents a status brief. Conditional infrastructure-health phase for workspaces with live services.

### `session-closeout`
**Triggers:** "checkpoint", "wrap up", "close out", "handoff", context > 50%

Appends a Checkpoint.md entry, rewrites handoff.md, walks every other root file with explicit UPDATE/NO-CHANGE — no silent skips. Includes a quick-mode for trivial sessions.

---

## Agents

### `session-curator` (Claude Code only)
**Triggers:** same closeout keywords + proactive when context > 50%, also manually delegatable

Token-efficient session compression. Runs the full file walk in its own context window, returns a ~300-token verification table to the parent. Saves an estimated **~5K parent tokens per closeout** by keeping eight scaffold-file reads out of the parent context.

Two modes:
- **Mid-session checkpoint** — parent stays working, agent saves a recovery point
- **Full closeout** — agent walks all eight files and updates everything

Built-in RULES.md compliance self-check before returning.

---

## Quick install

### Claude Desktop
1. Customize → Skills → **+** next to "Personal plugins"
2. Paste: `joeoliveimpact/revxl-marketplace`
3. Click Sync → click **Install** on `claude-workspace-superengine`

### Claude Code
```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install claude-workspace-superengine@revxl-marketplace
```

Full step-by-step in the [marketplace INSTALL guide](../../README.md#install).

---

## How to use it

Just talk to Claude naturally:

| Say this | What happens |
|----------|--------------|
| "set up my workspace" | super-setup scaffolds the 8 files |
| "what's the status?" | session-pickup reads handoff + briefs you |
| "close out the session" | session-closeout writes checkpoint + handoff |
| "checkpoint mid-session" | session-curator saves progress without ending |

You don't need command names. The triggers match how people actually talk.

---

## Design principles

- **One source of truth per concern.** RULES.md owns rules. ARCHITECTURE.md owns the map. handoff.md owns next-session priorities. No file blurs roles.
- **Append-only logs, rewriteable briefs.** Checkpoint.md grows. handoff.md is replaced each session.
- **Never edit RULES.md** unless explicitly asked. Constraints are deliberate, not curatorial.
- **Verifiable scaffolding.** Either all eight files exist, or none — no partial state.

---

## Dependencies

- **Recommended:** `agent-optimizer` skill (provides canonical RULES.md content). If absent, super-setup writes an inline backup version.

---

## Compatibility

| Platform | Skills | Agents |
|----------|--------|--------|
| Claude Desktop | ✅ | n/a (Desktop doesn't run agents) |
| Claude Code (CLI / desktop / IDE) | ✅ | ✅ |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md) — REVXL's curated Claude superengine catalog.
