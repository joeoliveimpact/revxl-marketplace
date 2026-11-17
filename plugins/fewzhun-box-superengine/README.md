# Fewzhun Box Superengine

A private notes brain for your own Linux server. Claude installs it with nobody at the screen, and
your bot and your Claude workers can then ask it questions.

## What it does

- **Search by meaning** over your notes. It finds a note even when the question uses other words.
  Only active notes count: a note marked replaced (superseded), a draft, or an `AGENTS.md` /
  `README.md` instruction file never comes back.
- **Older notes rank lower only where you say so.** Call logs and meeting notes can fade with age;
  guidance and rules never lose rank.
- **Spokes** (groups of notes, like "guidance" or "calls"), each with its own fast search.
- **Readers** with their own token (a long random password). Each reader sees only its own spokes.
  A spoke it may not read and a spoke that doesn't exist get the same answer, so a private spoke's
  existence never leaks.
- **A nightly link graph** per spoke, built with graphify, so agents can ask how ideas connect.
- **A read-only web page** for search, reading and the graphs, on the server's private Docker
  address and optionally your Tailscale address for your phone.
- **Nightly draft notes** (optional, off by default): the brain reads what your bot did, drafts new
  notes, checks each one, and stages it for a person to approve. Approved drafts can be promoted
  into your notes repo as a commit in your agent's own clone. Nothing is pushed for you.
- **Sync** (optional): pulls your notes repo from GitHub every 15 minutes with a read-only key.

## Install

On the client server, Claude installs it headless:

```
/plugin install fewzhun-box-superengine --marketplace joeoliveimpact/revxl-marketplace
```

Then the `fewzhun-box-setup` skill does the rest. The client never types a command.

## Skills

| Skill | Say | What it does |
|---|---|---|
| `fewzhun-box-setup` | "set up the brain on this server", "add a reader" | Detects the server, asks only what it can't detect, shows a dry run, installs on your yes, and turns each owner-only step into a plain task |
| `fewzhun-box-check` | "is the brain working", "did the nightly graph run" | Runs the done-test and reads the job files, then a plain verdict and the next fix |
| `fewzhun-box-use` | "search the brain for", "review the brain drafts" | Search, read and graph answers that end with which notes were used; draft review and promotion on the owner's explicit yes |

For a bot calling over the web: `references/agent-wiring.md`. For promotion with the agent's own
GitHub identity: `references/promotion.md`. Every setting: `config/CONFIG.md`.

## Requirements

- **A headless Linux server** (a VPS), Ubuntu 22.04 or newer. It does not install on Windows
  or macOS, and it does not need the Desktop app.
- **Claude Code on that server**, signed in, with admin rights (passwordless sudo) for the install.
- **Memory**: about 400 MB per spoke when every spoke stays loaded. On a small server the installer
  loads each spoke on its first search instead.
- **Python 3.11+** for the graph (Ubuntu 24.04 ships 3.12). Node.js 20+ is used if present;
  otherwise the installer adds its own pinned, checksum-checked Node.
- **Docker** if your bot runs in a container (the brain listens on the Docker host address).
- **Optional:** a GitHub notes repo (for sync), Tailscale (for your phone), and a Claude login on
  the server for the nightly graph and drafts.

## Steps only the owner can do (pause points)

The installer never does these. The setup skill turns each into a plain task and does the ones
it can on your yes:

1. **Deploy key**: add the server's key to your notes repo on GitHub, with write access OFF.
2. **Firewall**: one rule that lets only your bot's Docker network reach the brain.
3. **Kernel setting**: only if Claude workers run on the server and its sandbox is blocked.
4. **Tailscale**: sign in once, for phone access.
5. **A reader's token**: your bot's builder puts the bot's token into its container as a secret file.

## Privacy and safety

- The brain only reads your notes. The server never pushes to your notes repo or writes to GitHub.
- It is kept off the internet: it listens on the Docker host address by default, refuses a wildcard
  address, and the done-test checks that the outside address refuses the connection.
- Tokens are stored only as fingerprints (sha256). The raw token files in `/etc/fewzhun-box/tokens` (or `tokens_dir`) are root-only, and a token is
  never logged, printed or put on a command line. Revoking one works at once.
- The query log records who asked what, never a token.
- Public code lives in `code_root` (`/opt/fewzhun-box-app`, `root:root`, `0755`): the app,
  search engine, graphify and any bootstrapped Node. `/usr/local/bin/fewzhun-box` is a `0755`
  wrapper. Workers use it with their own token and URL files, without joining `fbx`. CLI graph
  commands fetch the graph over HTTP into a private temporary file and run graphify from `code_root`.
- The data root (`root`, default `/opt/fewzhun-box`) is `root:fbx` mode `0750`. Spokes and vault directories are `fbx:fbx`
  mode `2770`; sync creates files with mode `0660` (umask `007`). Other local users need
  a reader token and use the server, including its `view` permission for CLI graph queries.
- Published graphs and root-job status directories are `root:fbx` mode `0750`, with files
  mode `0640`. The server only reads them. Graph work and caches live in
  `/var/lib/fewzhun-box-graph/<spoke>` (`root:root`, `0700`); the Claude shim ships in
  the root-owned app. Sync writes its own status to `/var/lib/fewzhun-box/status/sync.json`.
- Every nightly model run goes through a login guard first: it can wait while your agent is busy, never
  runs within 60 minutes of the Claude login expiring, has no tools, and is capped at 15 minutes. If
  any check fails the job stops cleanly, keeps the last good result, and writes a status file.
- Nothing about your notes is sent to Joe. A failure report, if you choose to send one, holds only
  what failed and how, and you see it first.

## Version

0.1.0. See `CHANGELOG.md`.
