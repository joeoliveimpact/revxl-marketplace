#!/usr/bin/env python3
"""extract-transcript.py ... print the conversation layer of a session transcript.

Usage:
    python extract-transcript.py <session-id>
    python extract-transcript.py <path/to/session.jsonl>

Prints one "USER: ..." / "ASSISTANT: ..." line-group per text block, in order.
Everything else in the .jsonl is plumbing and is dropped: tool_use, tool_result,
thinking, and ... the part a hand-typed filter always misses ... the machine
traffic that arrives wearing role "user".

WHY THIS IS A SCRIPT AND NOT A SNIPPET
The old prose snippet kept every `text` block from role `user`. But task
notifications, system reminders, hook output, slash-command envelopes and local
command output are ALSO delivered as role "user", most of them as a bare content
STRING rather than a block list. Measured across 590 transcripts on one machine:
1,561 such blocks, up to 30 in a single file. A filter that only drops non-text
blocks does not catch any of them.

WHAT IS DROPPED, AND WHY EACH ONE
  * blocks whose whole payload is a machine wrapper tag (see WRAPPERS below)
  * an embedded <system-reminder>...</system-reminder> span is CUT OUT of the
    text and the surrounding words are KEPT. Reminders are routinely prepended
    to a genuine user sentence, so dropping the whole block deletes real speech.
  * records flagged isMeta, which is Claude Code's own marker for injected
    bodies (skill text, slash-command definitions) rather than anything anyone
    said.
Sidechain (subagent) turns are NOT dropped ... they are real conversation, just
a nested one.

Windows note: stdout defaults to cp1252 and dies on the first non-Latin-1
character, so stdout is reconfigured to utf-8 below. The input is read as utf-8
with errors="replace" for the same reason.
"""

import json
import os
import re
import sys
from pathlib import Path

# Wrappers that mark a user-role payload as machine traffic, not conversation.
# The tag AND its contents are cut; whatever surrounds it is kept, because these
# are routinely prepended to a real sentence.
WRAPPERS = (
    "task-notification",
    "system-reminder",
    "local-command-stdout",
    "local-command-stderr",
    "user-prompt-submit-hook",
    "session-start-hook",
    "post-tool-use-hook",
    # A slash command arrives as <command-message>/<command-name> plus a
    # <command-args> payload. The first two are envelope; the args are what the
    # user actually typed, so they are unwrapped below rather than dropped.
    "command-message",
    "command-name",
    "preview-annotation-context",
    "cross-session-message",
    "scheduled-task",
)

# Tags whose CONTENTS are real user text. Only the tag itself is removed.
# Dropping these wholesale would delete genuinely typed input ... the same
# mistake that dropping a whole <system-reminder> block would make.
UNWRAP = ("command-args",)

SPANS = [re.compile(r"<%s\b[^>]*>.*?</%s>" % (w, w), re.S) for w in WRAPPERS]
UNWRAP_TAGS = [re.compile(r"</?%s\b[^>]*>" % w) for w in UNWRAP]
OPENERS = tuple("<%s" % w for w in WRAPPERS)
OPENER_TAG = re.compile(r"<(?:%s)\b[^>]*>" % "|".join(WRAPPERS))


def strip_machine(text):
    """Remove machine wrappers. Returns the surviving human text, or ''."""
    for rx in SPANS:
        text = rx.sub("", text)
    for rx in UNWRAP_TAGS:
        text = rx.sub("", text)
    # An unclosed wrapper (truncated write, streamed notification) leaves a bare
    # opener behind. Drop the TAG only and keep the words ... never the whole
    # block. A user who types "<system-reminder> keeps showing up, why?" is
    # talking, and deleting that is worse than leaking a stray tag. Measured
    # across 590 transcripts this path fires zero times, so the safe direction
    # costs nothing and the unsafe one silently eats speech.
    if text.lstrip().startswith(OPENERS):
        text = OPENER_TAG.sub("", text, count=1)
    return text.strip()


def resolve(arg):
    """Accept a full path or a bare session id."""
    p = Path(arg)
    if p.is_file():
        return p
    if not p.suffix:
        p = p.with_suffix(".jsonl")
        if p.is_file():
            return p
    root = Path(os.path.expanduser("~")) / ".claude" / "projects"
    hits = sorted(root.glob("*/%s" % p.name)) if root.is_dir() else []
    return hits[0] if hits else None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2

    path = resolve(sys.argv[1])
    if path is None:
        print("No transcript found for %r. Give a full .jsonl path, or a session "
              "id that exists under ~/.claude/projects/." % sys.argv[1],
              file=sys.stderr)
        return 1
    if path.stat().st_size == 0:
        print("Transcript %s is empty (0 bytes). Nothing to filter ... this is "
              "an empty file, not an empty conversation." % path, file=sys.stderr)
        return 1

    kept = dropped = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("isMeta"):
                continue
            msg = rec.get("message") or {}
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content")
            if isinstance(content, str):
                blocks = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                blocks = content
            else:
                continue
            for b in blocks:
                if not (isinstance(b, dict) and b.get("type") == "text"):
                    continue
                raw = b.get("text", "")
                if role == "user":
                    text = strip_machine(raw)
                    if not text:
                        dropped += 1
                        continue
                else:
                    text = raw.strip()
                    if not text:
                        continue
                kept += 1
                print("%s: %s" % (role.upper(), text))

    if kept == 0:
        print("Read %s but found no user/assistant text blocks. The file parsed; "
              "it just holds no conversation layer." % path, file=sys.stderr)
        return 1
    print("[%d conversation blocks from %s; %d machine user-role blocks dropped]"
          % (kept, path.name, dropped), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
