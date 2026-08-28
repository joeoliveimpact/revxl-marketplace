# Kickoff prompt — recorded rationale

Reference for maintainers. Nothing here is loaded at runtime; it exists so settled questions are not re-opened by the next person to read `session-continue`.

---


A headless `claude -p "<prompt>"` through Bash is the only way to remove the click. **It is the wrong trade.** It runs the next session non-interactively, which means the user cannot steer it, cannot answer its questions, and cannot pick local vs worktree vs cloud. The click is not friction to be optimized away ... it is the human gate on starting a session, and it is where a real decision gets made.
