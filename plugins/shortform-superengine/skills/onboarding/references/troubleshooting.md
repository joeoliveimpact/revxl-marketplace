# Install & connection troubleshooting

Plain-English fixes for the rough spots that show up during first-run setup. Most
"it won't work" moments here are one of three things: Claude needs a full restart,
antivirus is in the way, or a background tool (Node/Python) wasn't there yet. Walk
these in order before assuming anything is broken.

---

## 1. Restart Claude *properly* (the #1 fix)

Newly-installed tools — Node, Python, MCP connectors — often aren't detected until
Claude fully restarts. **Closing the window with the `X` does NOT shut Claude down** —
it keeps running in the background, so the restart "doesn't take."

Do a real restart:

1. Right-click the Windows taskbar (or press `Ctrl+Shift+Esc`) → **Task Manager**.
2. Find **Claude** in the list → click it → **End task** (top-right).
3. Wait ~10 seconds (let it fully close).
4. Reopen Claude.

> **What this means for you:** if Claude just installed something and then says it
> "can't find" it or a connector "isn't detected," this restart fixes it ~80% of the
> time. Try it before anything else.

(Mac: `Cmd+Q` to quit fully — not just the red close button — then reopen. If it
hangs, Force Quit from the Apple menu.)

---

## 2. Antivirus is blocking the install (Norton, McAfee, etc.)

Third-party antivirus — **Norton** especially — sometimes blocks Claude from
installing a tool or running a background command, often **silently** (the install
just fails or hangs with no clear reason).

**Symptoms:** an install that should take seconds never finishes; a command "runs"
but nothing happens; repeated "couldn't install / not detected" after a clean restart.

**The workaround — run the command yourself in a terminal:**

When Claude gives you a command to run (or you ask it for the exact command), run it
in a real terminal, which the antivirus is less likely to interfere with:

1. Right-click the Windows Start button → **Terminal** (or **Terminal (Admin)** if
   the command needs elevated rights — Claude will say if it does).
2. Paste the command Claude gave you → press **Enter**.
3. If it asks for permission or your antivirus pops a prompt, **allow it**.
4. Copy any output back to Claude (select it → `Ctrl+C`) so it can continue.

> **What this means for you:** you're not bypassing security — you're running the
> exact same install step in a window the antivirus trusts more. If it still blocks,
> temporarily allow/whitelist the action in your antivirus, install, then re-enable.

(Mac rarely hits this. If Gatekeeper blocks something, System Settings → Privacy &
Security → "Allow anyway.")

---

## 3. A connector (MCP) won't attach

A connector — Claude calls these **MCP servers** (the integrations under Customize →
Connectors) — can fail to attach right after it's added or after an update.

Fix it in order:

1. **Full restart** (Section 1) — this alone usually fixes it.
2. **Check Node is installed** — `node --version` in a terminal. Many connectors need
   Node; if it's missing, install it (Windows: `winget install OpenJS.NodeJS.LTS`;
   Mac: `brew install node`) and restart again.
3. **Antivirus?** — see Section 2; some connectors spawn a background process AV blocks.
4. **Verify it's actually on** — Claude → **Customize → Connectors** → confirm the
   connector shows as connected. Toggle it off/on if it's stuck.

> Connectors cost tokens just by being switched on (see onboarding Step 3 — token
> hygiene). Only keep the ones this workspace needs attached.

---

## When to stop and ask Joe

If you've done a proper restart, confirmed Node + Python are installed, and ruled out
antivirus, and it *still* won't work — stop. Note the exact error text and flag it.
First-run plugins have rough edges; a real bug is worth reporting, not grinding on.
