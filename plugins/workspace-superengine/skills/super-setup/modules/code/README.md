# code module

Adds the bare minimum scaffolding to make this workspace useful for code work.

## What it creates

- `.claude/specs/in-progress/` — draft design specs, planning docs, RFCs
- `.claude/specs/completed/` — archive once shipped (workspace-cleanup will move stale in-progress entries here)
- `.claude/rules/code-quality.md` — short rule file that auto-loads on common source-file extensions

## What it does NOT do

- Does not configure a language toolchain
- Does not install linters, formatters, or git hooks
- Does not assume a project type (Python/JS/Go all welcome)

## Install

```
/workspace-add-module code
```

## Uninstall

Delete the three paths above. Remove the `code` entry from `.claude/workspace.yml#modules`.
