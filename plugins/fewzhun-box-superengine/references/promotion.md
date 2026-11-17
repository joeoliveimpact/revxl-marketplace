# Promotion: approved drafts into the notes repo, under the agent's own GitHub identity

The nightly harvest only stages drafts. A person approves them (`harvest decide`). Promote then turns each approved draft into an active note in the client's own git clone of the notes repo and commits it. **It never pushes and never touches a remote.** Pushing is the client's agent's own step, with its own GitHub access, after the owner's yes. The box itself has only a read-only deploy key and never writes to GitHub.

Every value in `<angle brackets>` is a placeholder.

## Who runs it

The client's own agent on the server: a Claude worker using the fewzhun-box-use skill, or the owner's agent. Promote reads the root-only staging folder, so it runs with admin rights (`sudo -n`).

## One-time setup of the agent's clone

1. The agent keeps its own clone of the notes repo on the server, for example `<agent home>/notes`. It is a different clone from the box's read-only copy in `<root>/vault`; never point promote at `<root>/vault`.
2. Give the clone the agent's own commit identity (set in the clone only, not globally):

   ```sh
   git -C <clone> config user.name "<agent name>"
   git -C <clone> config user.email "<agent email or GitHub noreply address>"
   ```

   Promote refuses a clone with no identity: `the repo has no git identity`.
3. The agent's push access is its own: an SSH key or a fine-grained GitHub token with write access to that one repo, stored where only the agent's user can read it. It is never the box's deploy key and never a reader token.
4. Optional: put the clone's path in brain.json `harvest.promote.repo` so `--repo` can be left out.

## Each time

Run from the plugin with the full Node path (see the fewzhun-box-use skill for `<node>`):

```sh
# 1. bring the clone up to date first, so the new notes land on the latest main
git -C <clone> pull --ff-only

# 2. preview: lists what it would do, changes nothing
sudo -n <node> "<plugin>/bin/fewzhun-box.mjs" promote --repo <clone>

# 3. on the owner's yes: write the notes and commit them
sudo -n <node> "<plugin>/bin/fewzhun-box.mjs" promote --repo <clone> --apply

# 4. on the owner's separate yes: the agent pushes with its own access
git -C <clone> push
```

What promote does for each approved draft that is not yet promoted:
- Sets the fields from `harvest.promote.on_promote` (by default `status: active` and `last_verified: <today>`).
- Puts it in the folder its type maps to in `harvest.schema.folders` (a type with no folder is refused).
- Runs the note check, the threat scan and the secret-path gate. A hit blocks that note, with the line numbers. It is never redacted or forced in.
- Writes `<clone>/<folder>/<id>.md`. An existing file there is never overwritten; that note is reported as blocked.
- `--apply` commits exactly those files, with the clone's own identity and with git hooks off.
- Records each promoted note in `<root>/status/promoted.jsonl`, so a second run changes nothing.

Exit codes: 0 nothing blocked, 1 something blocked or failed, 2 the input was refused.

## Drafts approved some other way

If a draft was approved outside `harvest decide` (for example in a chat thread the owner confirms), name it:

```sh
sudo -n <node> "<plugin>/bin/fewzhun-box.mjs" promote --repo <clone> --ids <id>,<YYYY-MM-DD>/<id> --by <approver> --apply
```

`<approver>` must be listed in `harvest.approvers`; it is recorded with each note. Only with the owner's explicit yes for those ids.

## What never happens

- Promote never pushes, never adds or changes a remote, and never runs git hooks.
- It never edits the staging folder or the approvals list.
- The agent never pushes without the owner's yes, and never force-pushes.
