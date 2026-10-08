---
name: stories-superengine:stories-setup
description: "First-run setup for the Stories engine: checks and installs what the computer needs (Python, the frame renderer), connects a way to post (Metricool through Claude's connector or composio, or Instagram directly), and records the coach's name, handle, time zone and lead magnets. Trigger phrases include \"set up stories\", \"stories setup\", \"connect Metricool\", \"it can't post\", \"reconfigure stories\"."
---

> **Compaction guard:** if this conversation was compacted since this skill loaded, invoke it again
> and resume at the first step whose result isn't in the config yet.

**Output contract:**
- `${CLAUDE_PLUGIN_DATA}/business-config.md`, filled (from the template in
  `${CLAUDE_PLUGIN_ROOT}/references/business-config.md`; never write into the template).
- `stories/.python` in the workspace: the Python every script runs with.
- `~/.claude/revxl/<brand>/stories/` created (avatar + saved looks live there).
The coach never types a command. Claude runs every step and says in one plain line what it's doing.

## Run a script

Every script runs with the recorded Python, never a bare `python`:
- PowerShell: `& (Get-Content -Raw -Encoding UTF8 stories\.python) "${CLAUDE_PLUGIN_ROOT}/scripts/check_deps.py"`
- Bash: `"$(cat stories/.python)" "${CLAUDE_PLUGIN_ROOT}/scripts/check_deps.py"`
Same pattern for `render_frames.py`, `render_card.py` and `publish.py` in the same folder.

## Steps

**1. Say what's coming.** "About 5 minutes. I'll check your computer can make the frames, then connect
the way your stories get posted."

**2. Find Python** (timeout 600000 ms). Say first: "Checking for Python, a free tool this runs on. If
it's missing I'll install it just for your user account, no admin password."
- Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/find-python.ps1"`
- Mac: `sh "${CLAUDE_PLUGIN_ROOT}/scripts/find-python.sh"`
One JSON line: `ok` → recorded in `stories/.python`, go on. `no_winget` → explain its `fix` hint in
plain words, run again. `not_found` / `no_python` → ask the coach to install Python 3.12 from
python.org (Windows: tick "Add python.exe to PATH"), reopen Claude in this folder, say "continue
stories setup".

**3. Renderer.** Run `check_deps.py`. Exit 3 → say "Setting up the frame renderer, about 2 minutes,
one time" and run `check_deps.py --install`, then check again. Still missing → show the `fix` line in
plain words and offer to retry.

**4. Brand.** Look in `~/.claude/revxl/` for an existing brand folder (lowercase letters + digits).
One found → confirm it's theirs. None → ask for their business name (a personal name or handle is fine), make the slug ("Maria G Fit" →
`mariagfit`), confirm, create `~/.claude/revxl/<brand>/stories/`. Voice: if
`~/.claude/revxl/<brand>/voc/voice-guide.md` exists, use it; otherwise offer the `brand-brain` skill
later (never block setup on it).

**5. How stories get posted.** Check in this order, stop at the first that works
(`${CLAUDE_PLUGIN_ROOT}/references/publish-paths.md`):
- a. **Metricool connector:** ToolSearch for `metricool brand settings` / `scheduled post`. Tools found
  → call its brand-settings tool (a free read). Works → route `metricool-connector`.
- b. **composio:** run `publish.py detect`. `metricool_toolkit` set → run `publish.py brands --toolkit <it>`.
  A list comes back → route `metricool-composio`.
- c. `instagram: true` in detect → route `instagram-direct`. Say plainly: "This can post to Instagram
  right away but can't schedule or post to Facebook. Metricool can do both, free plan included."
- d. Nothing → offer to connect Metricool through Claude's connector: Customize (left sidebar) →
  Connectors → Discover → Metricool → Connect → Continue connecting → Grant access. Their free plan
  works and allows one connector at a time. They decline → route `drafts-only` (frames are saved;
  they post by hand).
Metricool brands come back as a list: pick the one whose Instagram matches the coach's handle; ask
when several could fit. Record `{{METRICOOL_BRAND_ID}}` and take `{{TIMEZONE}}` from it. No brand matches → show the list and
ask which is theirs; none is → their Instagram isn't in Metricool yet: walk them through adding it in
Metricool's app, then check again.

**6. Hosting** (Metricool and Instagram fetch frames from a link). `publish.py detect` shows
`googledrive: true` → `composio-googledrive`. Else `gws: true` → `gws`. Neither → ask the coach to
connect Google Drive in composio (the coach clicks through `composio link googledrive`'s browser page;
Claude starts it). Skipping → route becomes `drafts-only`.

**7. Who they are on screen.**
- `{{DISPLAY_NAME}}` and `{{IG_HANDLE}}`: from the coach, or the connected Instagram/Metricool account.
  **Never from a web search** (a name search finds the wrong person).
- Profile photo: the coach shares one, or it's read from the connected account; save it as
  `~/.claude/revxl/<brand>/stories/avatar.jpg`. None → initials.
- Blue check: ask "Does your Instagram show a blue check next to your name?" Only yes → `on`.

**8. Lead magnets.** "What do you give away when someone replies to a story? Name, the reply word, and
where the file lives." Record each. Ask which tool sends it on a reply (ManyChat or similar), and
remind them: that tool needs a **story reply** trigger for each word, not only a comment trigger.

**9. Finish.** Write the config, read it back in plain English, then offer (never block):
- "Make your first story set?" → `stories-guide-set`
- "Capture your real voice from your calls and posts?" → `brand-brain` (when no voice guide exists)
