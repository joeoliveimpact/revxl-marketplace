# content module

Adds the lightest possible structure for running a content operation out of this workspace.

## What it creates

- `content/drafts/` — anything that isn't live yet
- `content/published/` — anything that is. Naming convention: `YYYY-MM-DD_slug.{md,txt,...}`
- `.claude/rules/content-creation.md` — voice, sourcing, and publish-discipline rules

## What it does NOT do

- Does not assume a CMS, distribution channel, or schedule
- Does not include voice guidelines (those belong in a brand voice file or the workspace owner's identity layer)
- Does not auto-publish anything

## Workflow

1. Draft lives in `content/drafts/<slug>.md`.
2. When it ships, rename to `YYYY-MM-DD_<slug>.md` and move to `content/published/`.
3. `workspace-cleanup` lists every draft and never moves one on "all"; a draft marked published or shipped is offered a move, and a draft moves only when you pick it by hand (to `content/published/` if it shipped, else `content/drafts/_stale/`).
