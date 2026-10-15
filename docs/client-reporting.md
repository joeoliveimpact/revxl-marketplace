# Client Failure Reporting (standard)

Every REVXL client plugin and skill offers a failure report that goes to Joe through the shared n8n relay
(`revxl-client-report-relay`, `POST https://n8n.engineforimpact.com/webhook/revxl-client-report`).
The relay files one `.md` per report in Google Drive under `REVXL Client Reports/<plugin>/<client_id>/`.
With no client id the folder is `key-<first 8 hex of the Vault key's SHA-256>`. If a subfolder cannot be
found or made, the report lands in `REVXL Client Reports/` itself. Reports never go to AgentMail.

Proven first in `higgsfield-superengine` (09.26.26). This is that pattern, made reusable.

## What each report carries

| Field | Flag | Required | Limit |
|---|---|---|---|
| plugin | `--plugin` | yes | 64 |
| version | `--plugin-version` | yes | 32 |
| one-line headline | `--summary` | yes | 200 |
| details (markdown) | `--body-file` / `--body-stdin` | yes | 51,200 bytes |
| skill | `--skill` | standard | 64 |
| step that failed | `--step` | standard | 100 |
| the error line, verbatim | `--error-line` | standard | 300 |
| error code / class | `--error-code` | optional | 64 |
| client or workspace id | `--client-id` (auto, see below) | auto | 64, slugged |

**Client id** is read automatically: `--client-id`, else env `REVXL_CLIENT_ID`, else `~/.config/revxl/client_id`.
It is cut to a folder-safe slug (`acme-coaching`). Use a business slug, never a person's name or email.
With none set, the relay still routes per client by the Vault key fingerprint.

## What a report never carries

- **Credentials.** The helper scrubs every value of a secret-named environment variable, the key files it
  knows (`~/.config/revxl/vault_api_key`, `~/.config/openrouter/api_key`; add your plugin's key file to
  `KEY_FILES`), and token shapes (`vk_`, `sk-`, `ghp_`, JWTs, `Bearer`, `Authorization:`, long hex runs).
  It scrubs before cutting, on draft and again on send. The Vault key only ever goes in the `x-api-key` header.
- **Client data.** The body holds what failed and how: the skill, the step, the command shape, the error
  output. Not the client's contacts, messages, call notes, vault notes, customer names or file contents.
  Name a file by its role ("the note being written"), not its text.
- **Anything the client has not seen.** The client sees the exact preview and says Send or Skip.

## Install in a plugin

1. Copy `scripts/templates/report_to_joe.py` to `plugins/<plugin>/scripts/report_to_joe.py`.
2. Change the one plugin-specific line, `DEFAULT_LOCAL_DIR` (where drafts and unsent reports are kept,
   for example `"vault-notes/reports"`). Add your plugin's key file to `KEY_FILES` if it has one.
3. Run `python scripts/report_to_joe.py --selftest` (all checks must pass; it never touches the real relay).
4. Paste the block below into every client-facing SKILL.md that can fail: anything that calls an API,
   writes files, runs a script, or installs something. Fill in the four `<...>` values.

## The block (paste into SKILL.md)

```markdown
## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `<local dir>/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin <plugin> --plugin-version <version> --skill <skill> --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file <local dir>/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
```

If the plugin pins its own Python (Higgsfield reads `higgsfield\.python`), call that interpreter instead of
`python`. The client never types any of these; Claude runs them.

## Exit codes

`0` sent or skipped, `2` usage error (fix the call), `3` saved locally (relay down, no Vault key, rate cap).
