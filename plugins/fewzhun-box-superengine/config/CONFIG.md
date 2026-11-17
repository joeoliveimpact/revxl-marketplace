# brain.json: every setting

The box reads one file: `/etc/fewzhun-box/brain.json` (owner root, group fbx, mode 0640). Set `FEWZHUN_BOX_CONFIG` to use another path. Start from `brain.example.json`, replace every `<...>` placeholder, then run `sh bin/install.sh` (a dry run) and `sh bin/install.sh --apply`.

The file must be plain JSON: no comments. If a value is wrong, the installer stops and names the key.

Files made by the installer:
- `tokens.json` next to the live brain.json: each reader's token as a sha256 fingerprint only.
- `/etc/fewzhun-box/tokens/<reader>` (or `tokens_dir`): the raw token, readable by root only. Hand it to that reader as a file or secret, never in chat.

## Where things live

| Key | Default | What it does |
|-----|---------|--------------|
| `root` | `/opt/fewzhun-box` | The private data root: `vault/` (the notes repo clone), `spokes/<spoke>/` (active copies + each spoke's index), `graphs/<spoke>/`, `staging/`, `approved/`, root-job `status/<job>.json`. Never point it at another tool's folder. |
| `code_root` | `/opt/fewzhun-box-app` | Public code only: `app/` (the installed plugin), `node_modules/` (the search engine), `venv/` (graphify) and `node/` when Node is bootstrapped. Keep separate from `root`, with neither inside the other. No notes, tokens or graphs. |
| `tokens_dir` | `/etc/fewzhun-box/tokens` | Raw token files, regardless of where `--config` points. Must stay outside `code_root`. |
| `log_dir` | `/var/log/fewzhun-box` | Where `queries.jsonl` goes: one line per request with time, address, reader name, query, spokes, result count and status. Tokens are never logged. Rotated weekly, 8 weeks kept. |
| `engine` | `<code_root>/node_modules/.bin/obsidian-hybrid-search` | The search engine. Leave unset; tests point it at a stand-in. |
| `timeout_ms` | `20000` | How long one spoke's search may take before that spoke reports failed. |

Permissions set by the installer:
- `<code_root>` is `root:root` mode `0755`; code files are readable and executables runnable by every user, with no write access for other users. `/usr/local/bin/fewzhun-box` is a root-owned `0755` wrapper that execs Node on `<code_root>/app/bin/fewzhun-box.mjs`.
- `<root>` is `root:fbx` mode `0750`. `spokes/`, each spoke and `vault/` are `fbx:fbx` mode `2770`; sync uses umask `007`, so copied notes are `0660`.
- `graphs/`, its spoke directories and `status/` are `root:fbx` mode `0750`; published graphs, root-job JSON status and the default promoted ledger are `root:fbx` mode `0640`. The `fbx` server only reads these directories. Atomic writes refuse symlink targets and create exclusive, no-follow temporary files.
- Graph work and cache directories are `/var/lib/fewzhun-box-graph/<spoke>`, `root:root` mode `0700`. The static `app/py/shim/claude` is installed `root:root` mode `0755`; the job never writes a shim.
- `/var/lib/fewzhun-box` is `root:fbx` mode `0750`; its `status/` and model cache are writable by `fbx`. Sync runs as `fbx` and writes `/var/lib/fewzhun-box/status/sync.json`, separate from root-job status. The CLI reads both locations; authenticated `/me` returns only job `ok` and timestamp summaries. `FEWZHUN_BOX_STATE_DIR` overrides `/var/lib/fewzhun-box` for isolated tests.

Unrelated local users cannot read the install root. Readers use their Bearer token through the server. `/read` accepts files resolving inside the requested spoke only, including when a symlink points into `vault/`.

## Network

| Key | Default | What it does |
|-----|---------|--------------|
| `bind` | `"auto-docker"` | The address the service listens on. The installer saves the Docker bridge's IPv4 here, even with NO-CARRIER or a down link. Without `docker_network`, it prefers `docker0`, else the first `br-*` network. Or give an IP. A wildcard (`0.0.0.0`, `::`) is refused. The done-test prints the resolved address. |
| `docker_network` | `null` | Optional Docker network name. The installer uses `docker network inspect` to resolve its bridge, reads that bridge's assigned IPv4, and stores it in `bind`. Set this to choose a specific container network. |
| `port` | `8791` | The port, on the `bind` address and the tailnet address. |
| `tailnet_bind` | `null` | `null` = no phone access. `"auto"` = also listen on this server's Tailscale address (opened as soon as Tailscale is up, checked every minute). Or give the Tailscale IP. |
| `timezone` | `"UTC"` | The time zone for the nightly `graph.time` and `harvest.time`, like `Europe/London`. |

## Spokes (groups of notes)

`spokes` maps a spoke name to its settings. Names use letters, digits, `-` and `_`.

| Key | What it does |
|-----|--------------|
| `spokes.<name>.folders` | Folders inside the notes repo whose notes belong to this spoke, like `["Guidance"]`. Sub-folders are included. A note's path in the spoke is its path in the repo, so `Guidance/Refunds.md` reads as spoke `guidance`, path `Guidance/Refunds.md`. |
| `spokes.<name>.decay` | `true` = older notes rank lower (call logs, meeting notes). `false` = notes keep their rank unless one is marked `sot_policy: decay`. `"never"` = age never matters, whatever a note says (guidance, rules, regulations). |

How age works: a note's age comes from frontmatter `source_date` (YYYY-MM-DD), else `date`. A note with neither never loses rank. The score is multiplied by `0.5 + 0.5 x max(0, 1 - age_in_days / 365)`, so a year-old note counts half. A note marked `sot_policy: decay` also ages in a `false` spoke, but never in a `"never"` spoke. A note marked `sot_policy: strict` never ages, even in a decay spoke.

Which notes show up (sync copies only these, and the server checks again):
- Only a note whose frontmatter says `status: active` is shown (spaces and capitals don't matter).
- Every other status hides the note: `draft`, `superseded`, `conflict`, `current`, anything else, and no status at all.
- A note with `superseded_by` set is hidden too.
- `AGENTS.md` and `README.md` are instructions, not notes. They are never copied or returned.

## Readers (who may read what)

`readers` maps a reader name to its access. Each reader gets its own token (`node bin/tokens.mjs add <name>`; the installer does this for every reader listed).

| Key | What it does |
|-----|--------------|
| `readers.<name>.spokes` | The spokes this reader may search and read. Asking for any other spoke, or one that does not exist, gets the same "not allowed" answer, so a private spoke's existence never leaks. |
| `readers.<name>.view` | `true` = this reader's token also opens the graph pages in the viewer for its spokes. Search and read in the viewer work for any reader. |

CLI `graph query|path|explain` also requires `view: true`. It fetches `/graph/<spoke>/graph.json` with the reader's Bearer token, runs graphify from `<code_root>/venv/bin/graphify` against a `0600` file in the system temporary directory, then deletes that file. It never reads `graphs/` directly. A worker outside `fbx` uses its own token and URL files; the CLI locates `code_root` from its installed app path when brain.json is unreadable.

Changing a reader's spokes takes effect after `systemctl restart fewzhun-box-server` (the installer does it). Revoking a token (`node bin/tokens.mjs revoke <name>`) takes effect at once.

## Load and memory

| Key | Default | What it does |
|-----|---------|--------------|
| `max_procs` | `2` | At most this many spoke searches run at the same moment; the rest wait their turn. |
| `warm` | `"all"` | `"all"` loads every spoke's search model when the service starts, so the first search is fast. `"lazy"` loads a spoke on its first search (slower first answer, less memory). The installer switches to `"lazy"` when free memory is under about 400 MB per spoke. |
| `memory_max` | `"3500M"` | The service's hard memory cap (systemd `MemoryMax`). Each loaded spoke holds its own model copy, about 400 MB. |

## sync: pull the notes repo

Off by default. When on, a timer pulls the repo every `interval_min` minutes. It copies each spoke's active notes into `<root>/spokes/<spoke>/`, removes copies whose note became hidden or was deleted, and updates the index only for spokes that changed. Line endings become Linux style and a leading BOM is dropped. With sync off, put notes in `<root>/vault/` yourself and run `systemctl start fewzhun-box-sync`.

| Key | Default | What it does |
|-----|---------|--------------|
| `sync.enabled` | `false` | Turn the timer and the git pull on. |
| `sync.repo` | none | The notes repo's SSH, HTTPS, local path or `file://` address. Fast-forward pulls only; the box never writes to it. Every git call trusts the clone path and, for local or `file://` repos, the source path with `safe.directory`. |
| `sync.git_config` | `/etc/fewzhun-box/sync.gitconfig` | Root-owned 0644 Git config, rewritten from config on every install. Sync sets `GIT_CONFIG_GLOBAL` to this path for every Git command so upload-pack also trusts local sources. `GIT_CONFIG_NOSYSTEM` is unchanged. |
| `sync.deploy_key` | `/etc/fewzhun-box/deploy_key` | The SSH key for the repo. Only for `git@` or `ssh://` repos, the installer creates it if missing and prints the public half as a PAUSE POINT: add it on GitHub as a deploy key with write access OFF. |
| `sync.interval_min` | `15` | Minutes between pulls. |

## graph: the nightly link graph (graphify)

| Key | Default | What it does |
|-----|---------|--------------|
| `graph.enabled` | `true` | Install graphify and turn on the nightly graph job. |
| `graph.graphify_version` | `"0.9.112"` | The exact graphify version, installed into `<code_root>/venv`. |
| `graph.backend` | `"claude-cli"` | The AI that reads notes for the graph. `claude-cli` uses `claude` below, always under the login guard. |
| `graph.time` | `"03:30"` | When the nightly graph job runs (HH:MM in `timezone`). |
| `graph.min_nodes` | `1` | A new graph with fewer nodes than this is refused and the old one stays. Never below 1, so an empty graph never replaces a good one. |
| `graph.graphify` | `<code_root>/venv/bin/graphify` | The graphify command. Leave unset; tests point it at a stand-in. |
| `spokes.<name>.graph` | `true` | Set `false` to leave one spoke out of the graph job. |

How the job runs (`py/graph_job.py`, as root, from `fewzhun-box-graph.timer`):
- The login guard runs first (see `claude` below). Permanent refusals (missing or unreadable files, missing binary, bad config) stop immediately with exit 2. Only transient refusals (busy, idle gate, near-expiry) retry up to `claude.retries`. The job writes `<root>/status/graph.json` with the reason. Graph-build prints the last guard or graphify error line and exit code.
- For each spoke it runs `graphify extract <root>/spokes/<spoke> --backend claude-cli --out /var/lib/fewzhun-box-graph/<spoke>`, then `graphify cluster-only /var/lib/fewzhun-box-graph/<spoke> --no-label`. `extract` writes `graph.json`; `cluster-only` writes `graph.html`. `--no-label` keeps the "Community N" names, so there is no second round of model calls.
- graphify's `claude` is the guard's stand-in (`claude_guard.py shim`, first on graphify's PATH). Every model call graphify makes passes the guard again and runs with no tools, no MCP servers, no settings and the configured model. graphify's own flags are ignored.
- The root-only work folder `/var/lib/fewzhun-box-graph/<spoke>/` is kept between nights. graphify's cache lives there, so a rerun over unchanged notes makes no model calls, and a run cut off by the time cap resumes where it stopped. Each spoke's `llm_calls` in `status/graph.json` shows how many model calls that night made.
- The whole run for one spoke is capped at `claude.max_run_minutes` and killed if it runs over.
- The new graph is published only if `graph.json` parses, has at least `graph.min_nodes` nodes, and `graph.html` exists. Both files are copied next to `<root>/graphs/<spoke>/` and moved in with an atomic rename. On any failure the published graph stays as it was, the work folder's graph is put back, and the status file says why. Any failed spoke makes the unit fail, which starts `fewzhun-box-alert@graph`.

The viewer shows graphify's own `graph.html` for each spoke. It runs in a sandbox that cannot see the viewer's token. CSP allows only the exact external script `https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js`, which graphify pins with an integrity hash.

## harvest: nightly draft notes for approval

Off by default. Each night (`py/harvest.py run`, as root, from `fewzhun-box-harvest.timer`) it reads what is new in the sources, masks it, asks the model for draft notes, checks every draft, and stages the good ones for a person to approve. It never writes to the vault or to git.

| Key | Default | What it does |
|-----|---------|--------------|
| `harvest.enabled` | `false` | Turn the nightly harvest on. |
| `harvest.time` | `"02:30"` | When it runs (HH:MM in `timezone`). |
| `harvest.cutoff` | `null` | `"YYYY-MM-DD"`: only items on or after this day (in `timezone`) are read. `null` = no cutoff. |
| `harvest.max_drafts` | `12` | At most this many drafts are staged per night; the rest are dropped and counted on the card. |
| `harvest.budget_chars` | `60000` | At most this much masked text goes to the model per night, oldest items first. What does not fit waits for the next night. |
| `harvest.item_chars` | `6000` | Longest single item; longer ones are cut. A source can set its own `max_chars`. |
| `harvest.sources` | `[]` | What to read (below). |
| `harvest.notify` | `null` | A command (a list of words, or one string split like a shell would, never run through a shell) that gets each night's card and each failure alert as JSON on stdin. `null` = no messages; the card is still in `card.md`. |
| `harvest.approvers` | `[]` | The names that may decide drafts. `decide --by <name>`, a queued tap, and `promote --by` all refuse any other name. |
| `harvest.known_hosts` | `["github.com"]` | A draft that links to any other host is blocked. Add a host only when a real note needs it. |
| `harvest.secret_patterns` | `[]` | Extra regular expressions for the secret-path gate. They add to the built-in list; they never replace it. |
| `harvest.taps_file` | `null` | The queue a bot writes taps to. `null` = `<root>/staging/taps.jsonl`. |
| `harvest.schema.types` | 7 types | The note types a draft may have. |
| `harvest.schema.folders` | | The vault folder for each type, like `{ "rule": "Guidance" }`. `promote` refuses a type with no folder. |
| `harvest.schema.applies_to` | `["all-agents", "humans", "build"]` | The audiences a draft may name in `applies_to` (exactly one). |
| `harvest.schema.sot_policy` | rule, fact, process, decision: `strict`; system: `decay`; lesson, daily: `blended` | Which `sot_policy` the model is told to use per type. A type not listed is `strict`. |
| `harvest.promote.repo` | `null` | Default `--repo` for `promote`: the client's own git clone of the vault. |
| `harvest.promote.on_promote` | `{ "status": "active", "last_verified": "{today}" }` | Frontmatter fields `promote` sets. `{today}` becomes today's date in `timezone`. |

### Sources

Each source needs a unique `name` (lowercase letters, digits, `-`). The name becomes the start of every source reference the drafts cite, like `daily:notes-2026-11-17@2026-11-17`.

| `type` | Keys | What it reads |
|--------|------|---------------|
| `markdown-dir` | `path`, `glob` (`"*.md"`), `date_from_filename` (`null`), `finished_days_only` (`true`) | Each matching file is one item. With `date_from_filename` set (`true` = `YYYY-MM-DD` in the name, or your own regular expression with groups `y`, `m`, `d`), the date comes from the file name and today's file waits until the day is over. Without it, the file's change time is the item time, so an edited file is read again. |
| `jsonl` | `path`, `text_field` (`"text"`, or a list joined with ` \| `), `ts_field` (`"ts"`), `id_field` (`"id"`) | One item per line. The time may be epoch seconds or ISO 8601. Lines that do not parse are skipped. |
| `sqlite` | `path`, `query` | Opened read-only. The `SELECT` must return `(id, ts, text)` rows; filter out bot and system rows in the query. |

Every source may set `max_chars`. One broken source is reported on the card and never hides the others.

The harvest service runs with a read-only file system except its own folders. A sqlite source in WAL mode needs to write its `-shm` file even to read, so add that database's folder with a drop-in: `systemctl edit fewzhun-box-harvest`, then `[Service]` and `ReadWritePaths=<folder>`. Do the same for a notify command that writes files.

### What one night does

1. Collect, with no model: items on or after `cutoff`, newer than what the last night took from that source, and never fed before. Secrets, keys, emails, phone numbers, card and ID numbers, street addresses and long numbers are masked. One masked file goes to the model: `<root>/staging/YYYY-MM-DD/input.md`.
2. The login guard, then one model run with no tools (see `claude`).
3. Code sets `status: draft`, `confidence: 0.7` and the dates. Each draft must pass, in order: the threat scan (hidden characters, injection phrases, commands, requests to send or paste secrets, links to hosts not in `known_hosts`) and the secret-path gate (`.env` files, `.credentials.json`, ssh private keys, key files, `/etc/...key...`, `token/` and `tokens/` files, secret folders, plus `secret_patterns`). A hit **blocks** the draft: it is kept in `blocked/` with the line numbers, never staged, never redacted. Then the note check (fields, one `applies_to` from the schema, dates, `id` equals the file name, no masked text, no copied questions) and the source rules (every claim cites a source from tonight's input). A failure **drops** the draft.
4. Staging: `<root>/staging/YYYY-MM-DD/` (mode 0700) holds `NN-<id>.md` drafts, `blocked/`, `index.json` (every draft with its sha256), `card.md` and `reply.md`.
5. The ledger (`<root>/staging/ledger.json`) records every item fed and what came of it. Any item in it is never fed again. A failed night writes nothing to the ledger and removes its half-made folder, so the next run picks everything up again.
6. If `notify` is set, it gets the card (below). `<root>/status/harvest.json` records the night.

### The card (what `notify` gets on stdin)

```json
{"kind": "card", "date": "2026-11-17", "header": "Brain drafts for 2026-11-17: 2 to review.",
 "decide": "fewzhun-box harvest decide 2026-11-17 <n> approve|reject --by <name>",
 "drafts": [{"n": 1, "id": "backup-schedule", "title": "Backup schedule", "type": "fact", "folder": "Guidance",
             "file": "01-backup-schedule.md", "sha256": "...", "conflict": false, "collides": false,
             "text": "the whole draft as the approver should see it"}]}
```

A failure alert is `{"kind": "alert", "job": "harvest", "reason": "...", "ts": "...", "text": "one line"}`. `python3 harvest.py post YYYY-MM-DD` sends a night's undecided drafts again.

### Deciding

Only the client's own agent or bot decides; the viewer is read-only.

- `python3 <code_root>/app/py/harvest.py decide YYYY-MM-DD N approve|reject --by <name>` (as root). `<name>` must be in `approvers`. The first decision on a draft stands; a later one prints "already decided" and changes nothing.
- Every decision is one line in `<root>/staging/approvals.jsonl` (append-only): date, number, id, decision, who, when.
- An approved draft is copied byte for byte to the outbox, `<root>/approved/YYYY-MM-DD/NN-<id>.md`, after its sha256 is checked against `index.json`. It still says `status: draft`. Whoever commits it to the vault flips it to `active`: the client's agent, or `promote` below.
- A bot that cannot run as root writes taps to `taps_file`, one JSON line each: `{"date": "YYYY-MM-DD", "n": 3, "decision": "approve", "by": "<approver>", "id": "<optional id check>"}`. Root moves them into `approvals.jsonl` with `harvest.py drain`; `run`, `decide` and `post` drain first too. A line whose `by` is not an approver is skipped. Re-draining is harmless.

Example: a chat-bot adapter. Set `notify` to a small script that reads the card JSON, posts each draft's `text` to the team chat with Approve and Reject buttons, and keeps `date` and `n` in each button's data. When someone taps, the bot (the one that posted, so it receives the tap) appends a tap line with the tapper's approver name to `taps_file` and starts `harvest.py drain` as root, or leaves it for the next `run`. Messages that are too long for the chat are the script's job to split.

### promote: approved drafts into the vault repo

```sh
python3 <code_root>/app/py/promote.py --repo <clone of the vault>            # dry run: lists what it would do
python3 <code_root>/app/py/promote.py --repo <clone of the vault> --apply    # writes and commits
python3 <code_root>/app/py/promote.py --repo <clone> --ids <id>[,<date>/<id>] --by <approver> --apply
```

- Reads `approvals.jsonl` and the staged drafts; it never changes the staging folder. `--staging <dir>` reads another staging folder of the same layout.
- For each approved draft not yet promoted: sets the `on_promote` fields, picks the folder from `schema.folders`, runs the note check, the threat scan and the secret-path gate (a hit is reported with its line numbers), and writes `<repo>/<folder>/<id>.md`. An existing file there is never overwritten; that note is reported as blocked.
- `--ids` promotes drafts that were approved some other way; `--by` must be an approver and is recorded in the promoted ledger.
- `--apply` commits exactly those files with the repo's own git identity, with git hooks off. It never pushes and never touches remotes; pushing stays with the client.
- The promoted ledger is `<root>/status/promoted.jsonl` (or `--ledger`). A re-run is a no-op. Exit 0 = nothing blocked, 1 = something blocked or failed, 2 = refused input.

## claude: the login the graph and harvest jobs use

The box may share one Claude login with the client's own agent. Two programs refreshing the same login at once can wipe it, so every model call goes through the login guard (`py/claude_guard.py`) first. If any check fails, the job stops cleanly and writes `<root>/status/<job>.json` with `ok: false` and the reason. It never leaves a half-written result.

| Key | Default | What it does |
|-----|---------|--------------|
| `claude.bin` | detected at install | Absolute path to the Claude Code executable, usually `<run_as home>/.local/bin/claude`. The installer detects it with `sudo -u <run_as> -i sh -c 'command -v claude'` when unset or relative, and saves it. A missing path fails validation; failed discovery prints a PAUSE POINT. The guard always executes this absolute path. |
| `claude.run_as` | none | The Linux user that is signed in to Claude. The jobs run as root and drop to this user for each model call. |
| `claude.credentials` | `<run_as home>/.claude/.credentials.json` | That login's credentials file. The guard reads one field, `expiresAt`. If the file is not in `<run_as home>/.claude/`, model calls get `CLAUDE_CONFIG_DIR` set to its folder. |
| `claude.token_file` | `null` | Alternative to credentials: an absolute path to a root-readable regular file, mode `0600`, containing the long-lived token from `claude setup-token`. The guard reads it before dropping privileges and passes it only to the Claude child through `CLAUDE_CODE_OAUTH_TOKEN`, never argv or logs. Credentials are not read in this mode; status records `long-lived token: expiry not checked`. |
| `claude.idle_cmd` | `null` | A command that must exit 0 (for example, a check that the client's agent is idle), or `null`. |
| `claude.busy_url` | `null` | A local address answering JSON with `agent_busy`; a model call runs only while it reads 0. Or `null`. |
| `claude.min_token_minutes` | `60` | The login must have at least this many minutes left, so a run can never be the one that refreshes it. |
| `claude.max_run_minutes` | `15` | Hard time cap on each model run (and on each spoke's whole graph run). Over it, the run is killed. Keep it well under `min_token_minutes`. |
| `claude.model` | `"haiku"` | The model the jobs ask for. The CLI's own startup report must name it, or the run is killed. |
| `claude.retries` | `12` | Maximum checks for transient refusals; permanent refusals exit 2 immediately. |
| `claude.retry_minutes` | `5` | Minutes between those checks. |

What every model run looks like: `claude -p --model <model> --tools "" --strict-mcp-config --mcp-config '{"mcpServers":{}}' --setting-sources "" --disable-slash-commands --no-session-persistence --output-format stream-json --verbose --system-prompt ...`, input on stdin, in an empty temporary folder, with a clean environment (no API keys). Before the model writes anything, the CLI reports what it loaded; the run is killed unless that report shows no tools, no MCP servers, the configured model and no API key. A tool call at any point kills it too.

`python3 <code_root>/app/py/claude_guard.py check` runs the checks once and prints the result.

## done_test: what the install check proves

`bin/done-test.sh` (the installer runs it last) checks the real service with these. Paths are `<spoke>/<path in the spoke>`. A check whose setting is missing counts as a failure, except `container`.

| Key | What it does |
|-----|--------------|
| `done_test.reader` | The reader whose token the test uses (default: the first reader). It must be able to read every spoke named below. |
| `done_test.query` | A word that appears in at least one active note. It must return results with no failed spoke, in under 5 seconds. |
| `done_test.semantic` | `{ "q": ..., "expect_path": ... }`: a question that shares no words with the note at `expect_path`, which must still come back in the top 10. This proves meaning search works. The test fails if the question shares a word with the note. |
| `done_test.superseded` | `{ "q": ..., "path": ... }`: a note marked superseded in the repo. It must not come back, must not be readable, and must have no copy on disk. |
| `done_test.decay` | `{ "q": ..., "decays": ..., "keeps": ... }`: an old dated note in a decay spoke (must have weight under 1) and an old dated note in a `"never"` spoke (must keep weight 1). The query must return both. |
| `done_test.container` | The bot's Docker container name: the test runs `/health` and one search from inside it. `null` skips this check. |
