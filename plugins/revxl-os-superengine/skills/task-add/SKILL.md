---
name: task-add
description: Use this skill when the user wants to add a task, capture a commitment, or remind themselves of something. Triggers include "add task", "remind me to", "I need to", "todo", "don't let me forget", or any inbound message in the Telegram `#tasks` topic (delivered as a `<channel source="telegram" topic="tasks">` event). Stores the task in the canonical REVXL OS task store at `~/.claude/revxl-os/tasks.json` and confirms back to the user. Foundation skill for the task-agent pipeline.
---

# task-add

Adds a single task to the canonical REVXL OS task store. The simplest write path — no extraction, no prioritization, just capture.

---

## When this fires

1. **Direct command in any session:** "add task: call Maya about her funnel"
2. **Telegram inbound** in `#tasks` topic: `<channel source="telegram" topic="tasks" chat_id="...">remind me to ship the proposal by Friday</channel>`
3. **Voice note via Telegram** transcribed → text in `#tasks` topic (handled identically once transcribed)
4. **Other agents calling it programmatically** (e.g., task-extract finds a promise in a transcript and adds it)

---

## What it does (the actual flow)

1. **Resolve the task store path:** `~/.claude/revxl-os/tasks.json`
   - If the file doesn't exist, create it with an empty `{"tasks": []}` structure.
   - If the parent directory doesn't exist, create it. Never assume the user ran `os-setup` yet.

2. **Parse the input** — clean up the user's text:
   - Strip leading "remind me to", "add task", "todo:", etc.
   - Detect a due date if mentioned ("by Friday", "tomorrow", "in 2 hours", "Tuesday at 3pm") — store as ISO 8601, otherwise `null`.
   - Detect a person mention if a name appears (`@maya` or "Maya") — store in `context.people[]`.
   - Detect a project/tag mention if `#project-x` style appears — store in `context.tags[]`.

3. **Build the task object:**
   ```json
   {
     "id": "<short ulid or uuid v7 — sortable by creation>",
     "text": "<cleaned text>",
     "created_at": "<ISO 8601 UTC>",
     "source": "<one of: direct, telegram-tasks, telegram-voice, agent-extract, manual-import>",
     "source_meta": { "chat_id": "...", "transcript_id": "..." },
     "due_at": null,
     "completed": false,
     "context": { "people": [], "tags": [] }
   }
   ```

4. **Append to the store:** Read the JSON, push the new task into `tasks[]`, write atomically (write to `tasks.json.tmp` then rename — never leave the user with a corrupted file).

5. **Confirm to the user:**
   - **If invoked from Telegram:** Use the `reply` tool from the telegram channel plugin. Pass back the `chat_id` from the inbound `<channel>` tag.
     - Format: `✓ Got it. Added: "{text}"` (one line, no fluff)
     - If a due date was detected: `✓ Got it. Added: "{text}" — due {human_date}`
   - **If invoked directly in a Claude Code session:** Print a one-line confirmation in the terminal.

---

## Tone rules

- Confirm in **one short line**. No "I have successfully added the task..." dross.
- Use ✓ as the success marker. Plain text otherwise.
- Don't echo the full task object. Just the cleaned text + due date if any.
- If something fails (e.g., write error), surface it plainly: "Couldn't save task: {reason}". Don't pretend.

---

## What this skill does NOT do (intentionally)

- **No prioritization.** That's `task-morning-brief`'s job.
- **No sync to GHL/ClickUp/Airtable.** That's `task-sync-out`'s job, runs nightly.
- **No de-duplication.** If the user adds the same task twice, both stick. `task-extract` handles dedup for promises pulled from transcripts.
- **No NLP for due dates beyond the obvious.** Use a simple ISO-or-null approach. If parsing is uncertain, leave `due_at: null` and don't ask for clarification — the user can add a follow-up "due tomorrow" task or edit later.
- **No editing existing tasks.** That's a different skill (`task-edit`, future).

Surgical scope. Add one task, confirm. Done.

---

## Store location and shape

**Path:** `~/.claude/revxl-os/tasks.json` (cross-platform; resolves to `C:\Users\{user}\.claude\revxl-os\tasks.json` on Windows)

**Shape (v0.1):**
```json
{
  "version": 1,
  "tasks": [ /* see task object above */ ],
  "last_modified": "<ISO 8601 UTC>"
}
```

**Migration plan:** When v0.2 moves to SQLite, a migration helper reads `tasks.json` and writes to `tasks.db`. JSON is preserved as a backup until the user confirms migration.

---

## Example invocations

### Direct in Claude Code:
```
User: add task: call Maya about her funnel review by tomorrow 3pm
You: ✓ Got it. Added: "call Maya about her funnel review" — due Fri May 9, 3:00 PM
```

### Telegram inbound:
```
<channel source="telegram" topic="tasks" chat_id="123456">
remind me to follow up with the Adams family about the December retreat
</channel>
```
You silently invoke task-add, then call the telegram channel's `reply` tool with `chat_id=123456` and `text="✓ Got it. Added: \"follow up with the Adams family about the December retreat\""`.

### Programmatic (from another skill):
Another skill (e.g., `task-extract`) calls task-add with `source: "agent-extract"` and provides the cleaned text. Same flow, no Telegram reply.

---

## Failure modes to handle

- **Store file is corrupted JSON:** rename the bad file to `tasks.json.corrupted-{timestamp}`, create a fresh one, log to user. Never silently lose tasks.
- **Disk full:** surface the error, don't pretend it saved.
- **Telegram reply tool not available** (channel not enabled): still save the task; print confirmation to terminal instead.
- **Empty/unclear input:** if the user just sent "task" with no content, ask one short clarifying question: "What's the task?"

---

## Integration with other skills

- `task-collect` (nightly) can call task-add for each commitment it extracts
- `task-morning-brief` reads from the same JSON store (read-only)
- `task-sync-out` reads the store and pushes to external systems

This skill is the canonical write path. All other writes go through it.
