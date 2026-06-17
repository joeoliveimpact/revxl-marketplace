---
name: super-setup
description: Use to scaffold a brand-new workspace from scratch — creates RULES.md, CLAUDE.md, ARCHITECTURE.md, GOALS.md, PLANNING.md, MEMORY.md, Checkpoint.md, handoff.md, tasks/, troubleshooting/, outputs/, and .claude/workspace.yml. Trigger phrases include "set up this workspace", "scaffold a new workspace", "I just opened an empty folder", "initialize a project here", "make this folder into a workspace", "/super-setup". Detects Cowork vs Code environment, pre-fills owner identity from global config, and offers a beginner-verbosity mode for first-time clients.
---

# super-setup — Workspace Scaffolding (v0.2)

One skill, one pass. Reads the templates that ship inside this plugin and writes a complete scaffold to the target workspace. No model invention.

## Beginner-mode preamble

Read `.claude/workspace.yml#verbosity` at skill entry. If the value is `beginner`, emit the following 2-3 sentence preamble to the user before doing any work. If `standard` (or missing), skip this block entirely and proceed silently.

> I'm about to set up your workspace files. This creates about 15 starter files — things like a rules file (so Claude follows the same ground rules every session), a memory file, and a checkpoint log. Once done, you'll have everything you need to start working.

## Layer 2: Suggest before invoking

If the user's prompt is borderline — could fit this skill or could just want a quick direct answer — ask before firing:

> "Looks like this might be a fresh workspace — want me to run `/super-setup` and scaffold the core files? Or are you set up already and just want to talk?"

Only run the full process below after the user confirms. If the user explicitly invokes `/super-setup`, skip the suggestion and proceed.

The templates live at: `${PLUGIN_DIR}/skills/super-setup/templates/`

The substitutions performed on every copy:
- `{{WORKSPACE_NAME}}` → user-supplied workspace name
- `{{PURPOSE}}` → user-supplied primary purpose sentence
- `{{DATE}}` → today's date in `YYYY-MM-DD` format

---

## Step 0 — Detect existing scaffold

List the target workspace root. If ANY of these files exist, stop and ask the user before overwriting:

```
RULES.md  CLAUDE.md  ARCHITECTURE.md  GOALS.md  PLANNING.md  MEMORY.md  Checkpoint.md  handoff.md
```

If all 8 root files exist AND `tasks/`, `troubleshooting/`, `outputs/`, `.claude/` are present → the workspace is already scaffolded. Offer `/session-start` instead and exit.

If some files exist and some don't, ask: "Existing scaffold partially present. Overwrite-and-replace, fill-gaps-only, or abort?"

## Step 0.3 — Detect runtime environment

Before asking any setup questions, determine whether this is a Claude Code or Claude Desktop / Cowork session.

**Detection procedure:**

1. Attempt a no-op Bash call: `echo workspace-env-probe`.
   - If the tool call **succeeds** (returns stdout, exit 0) → tentatively `code`.
   - If the tool call **errors** (tool unavailable, sandbox denial, no response) → tentatively `cowork`.

2. Confirm with the user, framed simply:
   > Detected: **Claude Code** (Bash works). Is that right? (Y/n)
   or
   > Detected: **Cowork / Claude Desktop** (Bash unavailable). Is that right? (Y/n)

3. If the user overrides, take their answer.

4. Persist to `.claude/workspace.yml`:

   ```yaml
   environment: code     # or 'cowork'
   ```

   Use the Write tool to update the file (works in both environments).

**Why this matters:** session-start, session-closeout, and any future skill that touches the shell branches on this field. Wrong value here means broken sessions later. Worth the 10-second confirmation.

## Step 0.5 — Detect global identity

Before asking the user for owner name, email, brand, and GitHub handle — scan their machine for values already on record. Surface findings as DEFAULTS in the questions, not silent fills.

### Sources to scan (in priority order)

1. **`~/.claude/CLAUDE.md`** — the user's global Claude instructions file.
   - Look for explicit `# userEmail` or `# currentDate` style sections (the user's auto-memory format).
   - Look for plain-text patterns: lines matching `email[:\s]*<value>`, `name[:\s]*<value>`, or `The user's email address is <value>`.
   - Use Read tool, then Grep tool with patterns:
     - `(?i)^The user's email address is\s+(\S+)`
     - `(?i)^#\s*userEmail\s*$` (then read the line that follows)
     - `(?i)^(?:Full name|Name)[:\s]+(.+)$`

2. **`~/.claude/projects/*/memory/*.md`** — per-workspace user memory files.
   - Use Glob: `~/.claude/projects/*/memory/*.md`
   - For each file, Read the first ~10 lines and check frontmatter for `type: user`.
   - If `type: user` is present, scan the body with Grep for these fields:
     - `Full name:\s*(.+)`
     - `Email:\s*(\S+@\S+)`
     - `Company\s*/?\s*brand:\s*(.+)` or `Brand:\s*(.+)`
     - `GitHub(?:\s+username)?:\s*[`']?([\w-]+)`
   - Track first occurrence wins (highest-priority source = most recent file by mtime).

3. **`~/.gitconfig`** — fallback only if (1) and (2) yielded no name or email.
   - Read with Read tool.
   - Grep for `\s*name\s*=\s*(.+)` and `\s*email\s*=\s*(\S+)`.

### Privacy boundary — what NOT to pull

This is a hard rule. From the sources above, EXTRACT ONLY these fields:

| Allowed | Notes |
|---|---|
| Full name | personal identifier |
| Email | primary contact |
| Brand / company | for attribution and copyright |
| GitHub username | for repo author fields |
| Preferred tools | only if explicitly listed as "preferred tools: X, Y" |

**Never extract:**
- Client lists, customer names, contact details from CRM-style memory
- Project secrets, API keys, credentials (even partial)
- Feedback memories (`feedback_*.md`, anything in body marked as a complaint or preference about Claude's behavior in a specific workspace)
- Brand voice details, marketing positioning, internal strategy
- Anything from memory files where frontmatter `type:` is anything other than `user`
- Anything from `~/.claude/CLAUDE.md` that looks like a workspace-specific instruction (path-bound, tool-bound)

If a memory file has no `type` frontmatter at all, **skip it**. Don't infer.

### Surfacing detected values as defaults

In the user-question phase, format each prompt like this:

```
Workspace owner name: [Joe Olive] — press Enter to accept, or type a new value:
Workspace owner email: [joe@engineforimpact.com] — press Enter to accept, or type a new value:
Brand affiliation: [REVXL / Engine For Impact] — press Enter to accept, or type a new value:
GitHub username: [joeoliveimpact] — press Enter to accept, or type a new value:
```

If a field was not detected from any source, show the prompt without a default:

```
Workspace owner name: (no value detected — please enter)
```

Record which fields came from detection vs. were entered fresh — useful for the Checkpoint.md first entry note ("Identity pre-filled from global config: name, email, brand. GitHub entered manually.").

### Detection-source ranking (when sources conflict)

If `~/.claude/CLAUDE.md` says `joe@bizzfixx.com` but `~/.claude/projects/*/memory/user_identity.md` (type: user) says `joe@engineforimpact.com`, **prefer the memory file** — it's typically more recent and explicit. Surface BOTH to the user as a disambiguation prompt:

```
Two emails detected:
  - joe@engineforimpact.com (from user_identity memory, dated 2026-05-07)
  - joe@bizzfixx.com (from ~/.claude/CLAUDE.md)
Which is correct? [1/2/type new]:
```

## Step 1 — Gather context

Ask the user (single AskUserQuestion batch):
1. **Workspace name** — short, used in document headers.
2. **Primary purpose** — one sentence; populates `GOALS.md` and `CLAUDE.md`.

Skip questions whose answers are obvious from prior context (directory name, prior messages).

## Step 2 — Compute substitutions

Set:
- `WORKSPACE_NAME` = user answer to Q1
- `PURPOSE` = user answer to Q2
- `DATE` = today (`YYYY-MM-DD`)

## Steps 3–10 — Copy and substitute the 12 template files

For each template under `templates/`, read it from the plugin directory, perform string substitution on all three placeholders, and Write the result to the target path:

| Source (in plugin) | Destination (in workspace) |
|---|---|
| `templates/RULES.md` | `RULES.md` |
| `templates/CLAUDE.md` | `CLAUDE.md` |
| `templates/ARCHITECTURE.md` | `ARCHITECTURE.md` |
| `templates/GOALS.md` | `GOALS.md` |
| `templates/PLANNING.md` | `PLANNING.md` |
| `templates/MEMORY.md` | `MEMORY.md` |
| `templates/Checkpoint.md` | `Checkpoint.md` |
| `templates/handoff.md` | `handoff.md` |
| `templates/tasks/STATUS.md` | `tasks/STATUS.md` |
| `templates/tasks/findings.md` | `tasks/findings.md` |
| `templates/troubleshooting/known-issues.md` | `troubleshooting/known-issues.md` |
| `templates/workspace.yml` | `.claude/workspace.yml` |

Create the destination directories (`tasks/`, `troubleshooting/`, `.claude/`) as needed before writing.

## Step 11 — Create the 3 placeholder folders

Create these as empty (zero-byte) `.gitkeep` files:
- `outputs/drafts/.gitkeep`
- `outputs/final/.gitkeep`
- `.claude/rules/.gitkeep`

## Step 12 — Report

Tell the user which files were created. Don't dump contents — list paths only.

## Step 13 — Verify (REQUIRED before claiming done)

Perform all three checks below. Surface any failure to the user and DO NOT report success.

### 13a — File existence

Confirm all 15 artifacts exist at the expected paths in the target workspace:

```
RULES.md
CLAUDE.md
ARCHITECTURE.md
GOALS.md
PLANNING.md
MEMORY.md
Checkpoint.md
handoff.md
tasks/STATUS.md
tasks/findings.md
troubleshooting/known-issues.md
.claude/workspace.yml
outputs/drafts/.gitkeep
outputs/final/.gitkeep
.claude/rules/.gitkeep
```

Missing files → STOP, report which are missing, do not proceed.

### 13b — CLAUDE.md line count

Read `CLAUDE.md`. Count lines. Must be **≤ 150**. If over, STOP and report the line count — a template regression has occurred.

### 13c — Placeholder substitution

For each of the 12 non-`.gitkeep` files, search for the literal strings `{{WORKSPACE_NAME}}`, `{{PURPOSE}}`, `{{DATE}}`, and any pattern matching `{{` `}}`. If ANY remains, STOP, report which file and which placeholder, do not claim success.

### 13d — Success report

Only if 13a, 13b, 13c all pass, report:

```
Workspace scaffolded: {{WORKSPACE_NAME}}
  ✓ 15 artifacts created
  ✓ CLAUDE.md within 150-line budget
  ✓ no template placeholders remaining

Next: open handoff.md for P0, or run /session-start.
```

## Step 14 — Linear tracking (conditional)

Now that the workspace purpose is known, optionally wire up Linear tracking. This step is a **no-op unless both conditions hold** — so workspaces (and clients) without Linear are unaffected:

1. The Linear MCP is connected (a `list_teams` probe succeeds), **and**
2. The `linear-kickoff` skill is available in this session.

If both hold, offer it:

> "Want me to set up Linear tracking for this workspace? I'll attach a team + project so work stays tracked. (Run `linear-kickoff` in tracking mode.)"

If the user says yes, invoke `linear-kickoff` in **tracking-only mode** — it assigns/creates the project under an existing team (it cannot create teams via MCP; it hands that off), records the result in `.claude/workspace.yml` under `linear:`, and flips the `## Linear Tracking` section in this workspace's `CLAUDE.md` to its post-setup form. It only touches GitHub if the workspace is coding-related and the user confirms.

If either condition fails (no Linear, or no `linear-kickoff` skill), **skip silently** — leave the pre-setup `## Linear Tracking` section as-is so a future session can offer it once Linear is connected.

---

## Ground rules (inherited from RULES.md)

- **Intent Clarification:** if workspace name or purpose is ambiguous, ask once.
- **Least Complexity:** 15 artifacts is the floor. Modules add more — they are separate skills.
- **Surgical Execution:** never overwrite without confirmation in Step 0.
- **Declarative Focus:** DoD is "15 artifacts exist; CLAUDE.md ≤ 150 lines; no `{{...}}` left." Anything beyond that is a separate task.
