## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. Resolve `~/fewzhun-box/reports/report-body.md` to an absolute path for this user. With the Write tool, put the details in that absolute path: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Use the same resolved absolute path for `--body-file` below. Replace `<name>` with the invoking skill's name. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin fewzhun-box-superengine --plugin-version 0.1.0 --skill <name> --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file "<absolute path to ~/fewzhun-box/reports/report-body.md>"`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
