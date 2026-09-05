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
- `.claude/rules/overrides.md` — non-negotiable override constraints, loaded by the harness every session
- `CLAUDE.md` — system instructions
- `ARCHITECTURE.md` — workspace map
- `GOALS.md` — primary objectives
- `PLANNING.md` — active initiatives
- `MEMORY.md` — index pointing to durable memories
- `Checkpoint.md` — accumulating session log
- `handoff.md` — next-session priorities

Optionally chains into `anthropic-skills:setup-cowork` for plugin/connector setup.

### `session-start`
**Triggers:** "pick up where we left off", "what's the status?", "where are we?", session start

Verifies the override constraints (migrating a legacy RULES.md into .claude/rules/overrides.md when found), then reads handoff.md → ARCHITECTURE.md → PLANNING.md → recent Checkpoint.md, runs any verifications flagged in handoff.md, and presents a status brief. Conditional infrastructure-health phase for workspaces with live services.

### `session-closeout`
**Triggers:** "let's wrap up", "closing out for the day", "session closeout", "save state", "I'm done for now"

Appends a Checkpoint.md entry, rewrites handoff.md, walks every other root file with explicit UPDATE/NO-CHANGE — no silent skips. Includes a quick-mode for trivial sessions.

### `session-continue`
**Triggers:** "close out and queue tomorrow", "wrap up and start the next session", "continue this tomorrow"

Runs the full `session-closeout`, then reads back what closeout just wrote and builds the next session's kickoff prompt out of it. Spawns that prompt as a task chip you click when you're ready to start ... so the next session opens already knowing where the last one stopped.

### `revxl-vault-search`
**Triggers:** "check the vault for", "search the vault", "what does the vault say about", "test the vault connection", and any RevXL plugin that needs Joe's newest strategy material before it writes

The one way a RevXL plugin talks to the RevXL Vault (Joe's live content-strategy knowledge base at brain.engineforimpact.com) with the client's own key. Search, read, related, and a connection test that doubles as the doctor. Read-only, capped at 10 searches and 6 reads per run, every call logged to `~/.config/revxl/brain-calls.jsonl` (the ledger keeps its historical filename), and every failure degrades to the calling plugin's bundled references in plain English. Not brand-brain (your local voice profile) ... different names on purpose.

---

## Agents

### `session-curator` (Claude Code only)
**Triggers:** "checkpoint", "save progress", "save where we are but keep going", proactive when context > 50%, also manually delegatable. **Mid-session only** — end-of-session phrases route to `session-closeout` or `session-continue`.

Token-efficient session compression. Runs the full file walk in its own context window, returns a ~300-token verification table to the parent. Saves an estimated **~5K parent tokens per closeout** by keeping eight scaffold-file reads out of the parent context.

Two modes:
- **Mid-session checkpoint** — parent stays working, agent saves a recovery point
- **Full closeout** — agent walks all eight files and updates everything

Built-in override-constraint compliance self-check before returning.

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
| "what's the status?" | session-start reads handoff + briefs you |
| "close out the session" | session-closeout writes checkpoint + handoff |
| "checkpoint mid-session" | session-curator saves progress without ending |

You don't need command names. The triggers match how people actually talk.

---

## Design principles

- **One source of truth per concern.** `.claude/rules/overrides.md` owns rules. ARCHITECTURE.md owns the map. handoff.md owns next-session priorities. No file blurs roles.
- **Append-only logs, rewriteable briefs.** Checkpoint.md grows. handoff.md is replaced each session.
- **Never edit `.claude/rules/overrides.md`** unless explicitly asked. Constraints are deliberate, not curatorial.
- **Verifiable scaffolding.** Either all eight files exist, or none — no partial state.

---

## Dependencies

- **Recommended:** `agent-optimizer` skill (provides the canonical override-constraint content). If absent, super-setup writes an inline backup version.

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
