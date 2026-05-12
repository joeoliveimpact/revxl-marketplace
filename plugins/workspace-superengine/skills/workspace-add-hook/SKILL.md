---
name: workspace-add-hook
description: Use to build a workspace-local hook in .claude/hooks/ that fires on a Claude Code lifecycle event (SessionStart, UserPromptSubmit, Stop, etc.). Trigger phrases include "I want a hook for X", "automate Z at session start", "make something happen when Y", "run this every time I open the workspace", "build a hook", "/workspace-add-hook".
---

# workspace-add-hook

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> I'm about to build you an automation. A hook is a small script that runs by itself when something happens — like every time you start a new Claude session. I'll ask what you want it to do, then save it into your workspace.

Builds a hook that lives entirely inside this workspace (`.claude/hooks/`) and runs only when this workspace is open.

## Layer 2: Suggest before invoking

If the user's prompt is borderline — could fit this skill or could just want a quick direct answer — ask before firing:

> "Sounds like you might want a hook — want me to run `/workspace-add-hook` and scaffold one? Or is this something a skill would handle better?"

Only run the full process below after the user confirms. If the user explicitly invokes `/workspace-add-hook`, skip the suggestion and proceed.

## When to use

Trigger phrases:

- "I want a hook that runs when..."
- "automate X at session start" / "trigger Y when a tool fires"
- "make something happen before every prompt"
- "add a PreToolUse / PostToolUse / SessionStart / UserPromptSubmit / Stop hook"
- "set up an automation that..."

Do NOT use for:

- User-global hooks → that lives in `~/.claude/settings.json`. Defer to `update-config` skill.
- Plugin-level hooks → those belong to the plugin author.
- One-off scripts the user just wants to run manually.

## Step 0 — Preconditions

1. Confirm we're in a scaffolded workspace (`RULES.md` + `CLAUDE.md` exist at root).
2. Read `.claude/workspace.yml#environment` to know whether to emit a `.sh` or `.ps1` script.

## Step 1 — Gather the four pieces of info

Ask the user (one batched question if your tools allow, otherwise sequential):

1. **Hook event** — which lifecycle event fires the hook? Show this menu:
   ```
   1. SessionStart      — fires at the start of every session
   2. UserPromptSubmit  — fires every time the user sends a message
   3. PreToolUse        — fires before a tool runs
   4. PostToolUse       — fires after a tool finishes
   5. Stop              — fires when Claude finishes a response
   6. Notification      — fires on system notifications
   ```
2. **Matcher** — for PreToolUse / PostToolUse only. Which tool(s)? Default `*` (all). Examples: `Bash`, `Write|Edit`, `mcp__.*`.
3. **What should happen?** — one sentence in plain English. The skill turns this into a script.
4. **Script style** — auto-pick based on `environment`. `code` → `.sh` (POSIX) or `.ps1` (Windows). `cowork` → defer to a JSON-only declarative hook if possible; otherwise warn the user this hook may not fire in Cowork.

## Step 2 — Name the hook

Default name: `<event>-<short-slug>.{sh|ps1}`. Example: `posttooluse-log-bash.sh`. Confirm with the user; allow override.

Target path: `.claude/hooks/<name>`.

## Step 3 — Generate the script

Translate the user's plain-English action into a script. Keep it small and self-explanatory. Always include:

- A comment header with the user's stated purpose, the date, and the event it binds to.
- Defensive `set -euo pipefail` (bash) or `$ErrorActionPreference = 'Stop'` (PowerShell).
- An explicit exit code policy: exit 0 on success; exit non-zero only if the hook should block the action (PreToolUse blocking is the only case where non-zero is load-bearing).

Show the generated script to the user before writing. Offer "looks good / edit / cancel".

## Step 4 — Wire it into settings.json

Write to workspace `.claude/settings.json` (NOT user global). If the file does not exist, create it with `{ "hooks": { ... } }`. If it exists, merge into the `hooks` block.

Example settings.json entry for a `PostToolUse` hook matching `Bash`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/posttooluse-log-bash.sh"
          }
        ]
      }
    ]
  }
}
```

Use `${CLAUDE_PROJECT_DIR}` for the path so the hook is portable.

## Step 5 — Make it executable

On POSIX (`environment: code` and not Windows): `chmod +x` the new script via Bash. On Windows: no-op (PowerShell scripts run by interpreter).

In Cowork: skip the chmod and warn that the hook may need to be made executable manually if the workspace is later opened in Code.

## Step 6 — Test prompt

Tell the user how to verify:

```
Hook installed:
  Event:   PostToolUse (matcher: Bash)
  Script:  .claude/hooks/posttooluse-log-bash.sh
  Wired:   .claude/settings.json -> hooks.PostToolUse

To test:
  Run any Bash command in this workspace. Check that <expected side effect> happened.

To remove:
  Delete the script file and the matching entry in .claude/settings.json.
```

## Ground rules

- **Intent Clarification:** if the user's "what should happen" is vague (e.g. "make Claude smarter"), ask for a concrete observable action. Do not invent.
- **Least Complexity:** one hook per invocation. Multi-hook setups happen one at a time with separate confirmations.
- **Surgical Execution:** never overwrite an existing hook file or a settings.json entry without the user explicitly saying "replace". Default is to surface the conflict and let them rename.
- **Declarative Focus:** Definition of Done is "the script exists, is executable (where applicable), and settings.json wires it correctly". Verifying the hook actually does its job is the user's call after install.

## Environment notes

Cowork users: not every hook event fires in Cowork. If `environment == cowork`, warn that PreToolUse / PostToolUse may be best-effort and recommend testing.
