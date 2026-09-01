# Transcript filtering ... the conversation layer, not the file

Read this when a skill is about to read a session transcript. It names the tool and the
reason for it. **Never dump this file at the user.**

---

## Run the script. Do not hand-type a filter.

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/extract-transcript.py" <session-id or .jsonl path>
```

It accepts a bare session id (it locates the file under `~/.claude/projects/` itself) or
a full path, and prints `USER:` / `ASSISTANT:` lines in order, nothing else.

**The snippet that used to live here is gone on purpose.** It was retyped at every call
site, it drifted, and the version in circulation was wrong. It kept every `text` block
whose role was `user` ... but **task notifications, system reminders, hook output and
local command output also arrive as role `user`**, most of them as a bare content string
rather than a block list. Measured on one real transcript, that leaked 67 lines of
task-notification plumbing straight into a kickoff prompt. Dropping non-text blocks does
not catch a single one of them, because they are all text blocks.

The script also gets right the mistake a blunter filter makes in the other direction: a
`<system-reminder>` is routinely prepended to a genuine user sentence, so the script
**cuts the reminder span out and keeps the surrounding words**, rather than discarding
the whole turn and deleting real speech with it.

## Why filter at all

**Measured on one real session: a 0.90 MB transcript held 29.6 KB of actual conversation
... 3.2% of the file.** The other 97% was tool plumbing: git output, file reads, JSON
payloads. None of it belongs in a kickoff prompt.

## The cp1252 gotcha

On Windows, stdout defaults to cp1252 and dies on the first character outside Latin-1.
The script reconfigures its own stdout to utf-8, so a direct run is safe. If you pipe its
output through another Python process, that process needs `PYTHONIOENCODING=utf-8` or it
hits the same wall.

## Degrade branches

**An empty result is always announced, never silent.** The script prints a plain message
and exits non-zero for a missing file, a zero-byte file, or a file that parsed but holds
no conversation layer. Pass that message along rather than reporting an empty transcript.

**Cowork:** no Bash, so the script cannot run. Say the transcript could not be filtered
and build the prompt from the files alone, with the transcript path still cited in the
read order so tomorrow's session can open it.

**No `**Session log:**` line, or the path is not on disk:** proceed without it. This is a
soft degrade, not a thin flag ... the transcript enriches the prompt, it does not carry a
required field. Say one line that it was unavailable.
