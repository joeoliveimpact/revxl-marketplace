# MEMORY.md — {{WORKSPACE_NAME}}

Index into durable memory for this workspace. Each bucket is a category of long-lived facts that future sessions should be able to retrieve without re-asking the user.

## The 6 buckets

1. **user-identity** — who the workspace owner is (name, email, brand, GitHub, preferred tools). Pulled from `~/.claude/CLAUDE.md` + `~/.claude/projects/*/memory/` at scaffold time, refined over time.
2. **clients** — clients or accounts this workspace touches, with the level of detail relevant here (NOT credentials).
3. **decisions** — locked architectural / strategic decisions and the reasoning. New sessions should not relitigate these.
4. **preferences** — how the user likes Claude to behave in this workspace (tone, verbosity, what to skip, what to double-check).
5. **feedback** — corrections the user gave Claude in this workspace. Don't repeat the mistake.
6. **tools-and-access** — MCP servers, plugins, integrations available. What's wired up, what isn't, what credentials are stored where (path references only, never secrets).

## How to use

- When you learn a fact that future sessions need: write it under the appropriate bucket, dated.
- When picking up a session: skim this file for any bucket relevant to the current task.
- Keep entries short and indexable. Long write-ups go in their own files; link them from here.

---

## user-identity

- _e.g. Owner: name, email, brand_

## clients

- _none yet_

## decisions

- {{DATE}} — Workspace scaffolded with `workspace-superengine` v0.2 (templates-on-disk model).

## preferences

- _none yet_

## feedback

- _none yet_

## tools-and-access

- _none yet_

_Last touched: {{DATE}}_
