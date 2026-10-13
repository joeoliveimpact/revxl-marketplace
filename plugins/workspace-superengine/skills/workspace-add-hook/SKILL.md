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

1. Confirm we're in a scaffolded workspace (`CLAUDE.md` at root, plus `.claude/rules/overrides.md` or a legacy root `RULES.md`).
2. Read `.claude/workspace.yml#environment` (`code` or `cowork`; it says nothing about the OS). Always emit a `.sh` script; emit `.ps1` only when the user explicitly asks for PowerShell.

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
4. **Script style** ... always `.sh` (bash). `.ps1` only on the user's explicit request, wired with the `-File` command form in Step 4. `cowork` → defer to a JSON-only declarative hook if possible; otherwise warn the user this hook may not fire in Cowork.

## Step 2 — Name the hook

Default name: `<event>-<short-slug>.{sh|ps1}`. Example: `posttooluse-log-bash.sh`. Confirm with the user; allow override.

Target path: `.claude/hooks/<name>`.

## Step 3 — Generate the script

Translate the user's plain-English action into a script. Keep it small and self-explanatory. Always include:

- A comment header with the user's stated purpose, the date, and the event it binds to.
- Defensive `set -euo pipefail` (bash) or `$ErrorActionPreference = 'Stop'` (PowerShell).
- An explicit exit-code policy. Exit 0 is success. **Exit 2, with the reason on stderr, is the ONLY code that blocks** the action (PreToolUse, UserPromptSubmit, Stop) or feeds the reason back to Claude (PostToolUse). Any other non-zero code, including a `set -e` crash or a PowerShell throw, is logged and the action GOES AHEAD. So a hook meant to block denies with an explicit `exit 2`, and the header comment states whether it fails open (a crash lets the action through, the default) or fails closed (add `trap 'exit 2' ERR` after `set -euo pipefail`).

Show the generated script to the user before writing. Offer "looks good / edit / cancel".

## Step 4 — Wire it into settings.json

Write to workspace `.claude/settings.json` (NOT user global). If the file does not exist, create it with `{ "hooks": { ... } }`. If it exists, merge into the `hooks` block.

Before writing, show the user the `hooks` block as it is now and as it will be after the change, and get a yes. Save the file's exact bytes first (`cp .claude/settings.json .claude/settings.json.before`). After writing, parse it: `perl -MJSON::PP -e 'decode_json(do{local $/;<>})' .claude/settings.json`. If the parse fails, restore the saved bytes (`mv .claude/settings.json.before .claude/settings.json`, or delete a file you just created) and tell the user the hook was not wired. On success, remove the `.before` copy.

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

For a `.ps1` hook a bare path does not run. The command is `powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PROJECT_DIR}/.claude/hooks/<name>.ps1"`, with the inner quotes escaped inside the JSON string.

## Step 5 — Make it executable

On POSIX (`environment: code` and not Windows): `chmod +x` the new script via Bash. On Windows: no-op.

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
