---
paths:
  - "**/*.py"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.go"
  - "**/*.rs"
  - "**/*.java"
  - "**/*.rb"
  - "**/*.php"
description: Code quality expectations for source files in this workspace.
---

# Code quality rules

When editing or writing code in this workspace:

1. **Surgical edits.** Change only what the task requires. Do not reformat, rename, or "clean up" unrelated code unless the user asks. Reformatting churn hides real diffs.
2. **No dead code.** If you remove a feature, remove its tests, types, docs, and config entries in the same change. Stale references are a worse bug than the one you fixed.
3. **Match the file you're in.** Use the existing style, framework idioms, import order, and naming conventions of the file you are editing. Do not introduce a new pattern in a single file.
4. **Errors are not return values.** Throw, raise, or return `Result`-style. Do not silently swallow. If you intentionally ignore, leave a one-line `// ignored because X` comment.
5. **Tests next to the change.** If a function changes behavior, its test must change or a new test must appear in the same diff. "I'll add tests later" is a deferred bug.
6. **No new dependencies without asking.** Pulling in a library to save five lines is rarely the right trade.
7. **Read before write.** Before editing a file, read enough of it to understand the surrounding code. Do not patch blind from search results.
8. **Public surface is permanent.** Renames of exported names, public methods, or CLI flags need explicit consent. Internal-only refactors are fine.

When you violate one of these, say so out loud in the response so the user can correct course.
