# Changelog — socialcrawl-superengine

## 0.4.0 - 2026-11-03

### Added
- **A mod: the band above the prompt shows this session's spending.** In the terminal and Desktop,
  once SocialCrawl has been used in a session (a line for it in the call record, or its session
  file), one row above the prompt shows a 10-cell gauge and `<spent> / <limit> cr this session`
  (`<spent> cr this session · automatic cap` while no limit is known). The numbers are the guard's
  own: `spent` from the session file, the limit from the session's newest call-record line, else a
  valid `sessionBudget` in the budget file. With 10% of the limit or less left it adds
  `⚠ <n> cr left`; after a refused call, `⚠ last call refused (<kind>)`. Its buttons, **Budget** (`d`), **Endpoints**
  (`p`) and **Round-up** (`r`), open their panes (below); other plugins' bands draw below it, and it steps aside for a
  survey.
- **The status line shows the account's total balance:** `SC Total Balance: 4,210 cr (2 min ago)`.
  It is read when a person is at the prompt (an interactive start, or the Desktop app or a phone
  attaching) and every 15 minutes after, and the age is kept current each minute. It adds
  `⚠ your <n> budget is above it` when a valid session budget is above the balance, and
  `⚠ not updated for <age>` once the newest good read is over 30
  minutes old. With no key the line is left off; any other failure before a first good read shows
  `SC Total Balance: unavailable · ⚠ last check failed`.
- **The balance is read by a local helper, so the key never enters the mod.** `hooks/mod/helper.mjs`
  runs as its own Node process: it finds the key the way the guard does (`ledger.mjs`), asks for the
  balance (0 credits, a 5-second timeout) and prints only the number. The mod never reads the key
  file or `SOCIALCRAWL_API_KEY` and never fetches, because a mod's file reads and fetches are events
  another plugin can see.
- **A toast after each counted call:** `SocialCrawl: <paths> · up to <worst> cr · <committed> /
  <limit> cr this session`, from this session's new line in the call record. A refused call gets
  none.
- **The heartbeat file.** Each session start writes
  `<revxl>/heartbeat/socialcrawl-superengine/<session>.json`
  (`{v, plugin, version, pane_command: "/socialcrawl-budget", session_id, ts}`), replaced whole each time, and
  deletes this plugin's own heartbeat files older than 7 days. A failure is skipped silently.
- **Nothing draws in `claude -p`, and it makes no balance read there.** A headless run writes the
  heartbeat and nothing else.
- **The Budget pane: one budget per run, set with buttons.** The band's **Budget** button (`d`) and
  `/socialcrawl-budget` open the pane "SocialCrawl Budget". It shows the balance and this session's
  spend, and the budget per run (250, 500, 1,000, 2,000 or Automatic, a quarter of the balance up to
  500): "The most one session, Desktop routine run or claude -p run may spend." A number set by
  hand that isn't a preset shows as `Current: <n>` and is kept until a button changes it. It is buttons only, so it works in the phone app too.
- **Only Save writes.** Pressing a preset changes the pane's pending choice and shows `Unsaved
  changes`; nothing is written until **Save**. Automatic deletes `sessionBudget`, and every save
  deletes an old `routines` block, which nothing reads. Before saving, the pane warns `⚠ This is above
  your <n> balance. Allowed; SocialCrawl stops at zero.` for a budget above the last balance, and
  `⚠ This session has already spent <s> cr; a budget this low stops further paid calls in this
  session.` for a budget at or below this session's spend.
- **A save is atomic and read back.** Save runs `helper.mjs budget-write`, which checks every number
  again by the guard's rule (a whole number from 1 to 20,000; anything else saves nothing), keeps
  every key in the file the pane doesn't own, stamps `updatedAt` and `updatedBy`, writes a temporary
  file beside the budget file and renames it over it, then reads it back. A half-written budget file
  would read as no budget (the looser automatic cap), so none is ever left; a failed save leaves the
  old file as it was. The pane says `Saved. Every open session uses it from its next paid call.` only
  when the file reads back as chosen, else `Not saved: <reason>.`, keeping the choice. A UTF-16 file,
  or one with a byte order mark, is saved as UTF-8; one that isn't a JSON object is replaced by a fresh file
  of the pane's own keys.
- **Claude can't change the budget.** The guard refuses Claude's own commands that name the budget
  file or the pane's save step (`budget-write`), and the save step runs only from the pane's Save
  button: the mod registers no tool Claude can call, sends a prompt only when a person presses in the Endpoints, Combos or Suggested tab (their pick, as their own prompt) or presses Round-up's Summarize (built from the pane's own facts), makes no model call but the Suggested tab's Haiku call (only once that tab is opened), and
  `/socialcrawl-budget` only opens the pane.
- **The band and the Budget pane use the REVXL Lantern look (paper cards)**, with plain-text versions in the terminal and on the phone.
- **The Endpoints and Combos tabs.** `/socialcrawl-endpoints` or the band's **Endpoints** button (`p`) opens them: 29 one-click calls with one target box, and every research-plays package option, each priced; a press sends that priced pick as your own prompt, one at a time.
- **The Suggested tab.** The Endpoints pane's **Suggested** button opens it: up to six of the Endpoints and Combos buttons, each with a one-line reason. Haiku picks them from the brand's `business-config.md`, the person's last five prompts and this session's call paths. It is asked only after the tab is opened in a session, and then only when one of those changes; a dim line shows the tokens used. A suggestion is a button the other tabs already draw, pressed the same way, so Haiku's words never reach a prompt.
- **The Round-up tab.** The band's **Round-up** button (`r`) or `/socialcrawl-roundup` opens it. It shows:
  - this session's total (the Budget pane's own);
  - its paid calls (time, paths, the guard's worst-case quote);
  - its refused calls, apart and never counted;
  - the files its counted calls saved;
  - the last routine (when it ran, what it spent, what it refused);
  - **Summarize**, which sends a request built only from those facts as the person's own prompt.

  It writes nothing.
- **What 0.4.0 needs.** The band and its tabs are a mod: Claude Code 2.1.286 or later with mods on. Without them the guard still runs, at the automatic limit or a budget file already set. It counts calls made in the Bash tool, which on Windows needs Git for Windows; a SocialCrawl call through PowerShell is denied.
- **Failure report.** onboarding, research-plays and socialcrawl offer the standard failure report (`scripts/report_to_joe.py`; drafts kept in `socialcrawl-superengine/reports/` in the project folder). The client sees the exact report before it is sent. It scrubs keys, `~/.config/socialcrawl/api_key` included. It needs `python` or `python3`; without either, the details stay in that folder's `report-body.md` for the client to email. The mod (the band and its tabs) has no report of its own: its helper's failures already show as "unavailable" and never block a call.

### Changed
- **The credit guard never raises a permission prompt (D28).** Every decision is a silent pass or a
  deny whose message names the fix. A SocialCrawl command that isn't a plain `curl` in the Bash tool (a loop, a pipe into a program, a wrapper, a
  variable, a heredoc, a mention such as `echo` or `grep`, or anything through PowerShell) is
  denied before any session, budget or balance is read, and the message says to write one plain
  `curl` per call in the Bash tool, or to use the Read or Grep tool for a mere mention. Transcript,
  unreadable, uncomputable and unpriced calls are no longer stopped: each is counted at its known
  worst case and passes within the limit. In a session whose committed total was lost, every paid
  call is denied, with "start a new session". An error of the guard's own still passes attended
  and denies unattended or in a routine. A deny reads the same attended and unattended, and
  nothing it denies is counted.
- **The limit is hard, not a step.** A command that would take the session's committed total past
  its limit is denied; reaching the limit exactly passes. The limit is the session budget when one
  is set, else the automatic cap, the smaller of 500 and a quarter of the balance, else 500 when the
  balance can't be read, for every session, Desktop routine and `claude -p` run alike. A balance of
  0 to 3 gives a limit of 0.
- **A budget file: `<revxl>/socialcrawl-budget.json`** (`<revxl>` is `SC_REVXL_HOME`, else
  `~/.claude/revxl`), set by the person, never by Claude. `sessionBudget`, the one field the guard
  reads, sets the limit; an old `routines` block is ignored. A number counts only as a whole number
  from 1 to 20,000; anything else is unset, and an unset `sessionBudget` falls back to the automatic cap. A file that is missing, a folder, not JSON or
  not a JSON object reads as no file. A file that is there but can't be read is tried again, and
  if it still can't be read, a paid call is denied rather than held to a looser limit; it is read
  however long the guard has already run. With a valid `sessionBudget` the balance is not read.
- **A passing read error no longer costs the session.** A session file that is there but can't be
  read (EBUSY, EPERM or EACCES while another program holds it) is tried again, up to 5 times within
  the guard's time limit; if it still can't be read, the call is denied and the file is never saved
  over, where before it was saved as a lost total. A damaged file (empty, not JSON) is still a lost
  total.
- **A call whose worst case is 0 is never denied for the limit.** A free GET twin or an unpriced call
  passes even when the committed total is already above a lowered limit.
- **New denies**, the same attended and unattended and logged `error` unattended: the session file
  can't be read right now; the budget file exists but can't be read right now.
- **The guard runs before a command only.** Its PostToolUse and PostToolUseFailure entries are
  removed from `hooks.json`, and with them the pending quote: a call's worst case is committed when
  it passes. A Post input from an older registration passes untouched, and a session file that
  still holds an older build's pending quote reads as a whole session, the quote ignored.
- **Claude can't change the guard's own files.** The credit guard now also runs on Write, Edit,
  MultiEdit and NotebookEdit. A write-type call to the budget file, the old routine day file, the
  unattended log `credit-guard-unattended.jsonl` or the call record `socialcrawl-calls.jsonl` (a
  lock, temporary or rotated copy of one included: the name, a `.` and more) in a revxl location (a
  folder of its path named `revxl`, or `<revxl>` itself), or to a session file
  (`socialcrawl-<session id>.json` or `.json.lock`) in `revxl/sessions` or `<revxl>/sessions`, and a
  Bash or PowerShell command that names one of them with a revxl location, is denied before
  anything else, a SocialCrawl URL in the
  same command included. The message says the person sets the budget in the SocialCrawl Budget tab,
  and that Claude can look with the Read tool, which is not matched. The deny reads the same attended
  and unattended, is not logged, and reads and writes nothing. Every other write-type call passes
  untouched.
- **A byte order mark no longer voids a file.** One leading byte order mark (PowerShell 5.1's
  `Set-Content -Encoding UTF8` writes one) is dropped before the budget file or a session file is
  read, so a budget saved that way is the limit, and a session file saved that way is not a lost total. Anything else that isn't
  JSON reads as before.
- **A per-call record: `<revxl>/socialcrawl-calls.jsonl`.** Each decision the guard makes once it
  holds the session lock (a pass at the commit, and every deny from the lock on) adds one
  JSON line, attended and unattended, with exactly `ts`, `sid`, `paths`, `worst`, `committed`,
  `decision`, `kind`, `limit`, `balance`, `balanceAt` and `routine` (true in a Desktop routine
  run), in that order. `paths` are the unattended
  log's own (each call's `/v1/` path, no query string, any `sc_` run masked), so a line never holds a
  key, a command, a header or a query value; `worst` and `committed` are the guard's worst-case
  figures, not the vendor's billing. The session file now keeps `balanceAt`, the time its cached
  balance was read; an older session file without it still reads. At 1 MiB the record is moved to
  `socialcrawl-calls.jsonl.1` (an older `.1` is replaced) and started again. Writing it is best
  effort: a line that can't be written, moved or measured is dropped, with no wait, and changes no
  decision. Nothing is recorded for a run that never holds the session lock (a command that isn't a
  SocialCrawl call, a guard-file deny, a write-type call, a command that isn't plain, a free plain
  call, or a session lock it can't take) or on an error of the guard's own. The unattended log is
  unchanged.
- **Claude can't delete or move the revxl folder.** A Bash or PowerShell command with a delete, move or
  rename verb (`rm`, `rmdir`, `rd`, `del`, `erase`, `mv`, `move`, `ren`, `rename`, `Remove-Item`,
  `Move-Item`, `Rename-Item`, `ri`, `mi`, `rni`, after any character that isn't a letter, a digit, `_`
  or `-`, with or without `.exe`, so `"rm"`, `\rm`, `/bin/rm`, `rm.exe`, a verb inside
  `bash -c "..."` or backticks and a module-qualified `...\Remove-Item` count) and the revxl folder
  itself is denied the same way, naming the revxl folder: a deleted folder would restart the session's
  count and lose its cached balance. The folder itself is any of: `revxl` or `revxl/sessions` with no
  real file or folder after it (a `.` or `..` segment, a glob, a trailing slash, or punctuation such as
  `>`, `,` or `{` counts as none); a path under revxl with a `..` segment in it; the `.claude` folder
  itself; or `<revxl>` itself, resolved, with either slash and with or without `sessions`, so an
  `SC_REVXL_HOME` not named revxl is covered too. A file in a brand folder below revxl is left to the
  command, and a command that names one of the guard's files still gets that file's name. For those
  files, a revxl location in a command is now `revxl` not run on into a longer name (so
  `revxl-marketplace` is not one) or `<revxl>` itself with either slash.
- **A stream or a short name no longer hides a guard file from a write-type call.** Its name is read
  without a stream (`socialcrawl-budget.json::$DATA`), and a name holding `~`
  (an 8.3 short name such as `SOCIAL~1.JSO`) is read as its long name, the one file lookup a write-type
  call makes.
- **A UTF-16 budget or session file is read.** A file that starts with the UTF-16LE byte order
  mark (PowerShell 5.1's `>` and `Out-File` write one) is read as UTF-16LE, so a budget saved that way
  is the limit instead of reading as no file. UTF-16BE is still unreadable, and the guard still writes
  UTF-8 with no mark.
- **The skills and references describe the never-ask guard.** `skills/_shared/references/credit-guard.md`
  is the one full statement of the guard (the limit, how each kind of call is counted, the denies,
  the guard's own files, the call record) and of what a run with nobody there may spend, a Desktop
  routine and `claude -p` alike. The socialcrawl,
  research-plays and onboarding skills, the research-router agent, the README and the generated
  platform references point to it, and no longer describe an ask, a pause or a cap step.
- **research-plays: the Jev route's steps moved to `references/jev-route.md`**, word for word, to make room for the failure report; the skill points to it.

### Known limits
- An unpriced call (the cohorts surface), and a call with a null price range and no stated maximum
  (POST `prism/jobs`, POST `web/batch-scrape`, POST `web/monitors`), is counted at 0, so its spend
  is not held to the limit.
- A per-unit price is counted as a floor: a transcript call counts one unit's price, so a call that
  bills many units is counted low.
- shortform-superengine's SocialCrawl spend is unseen by this guard until shortform 0.7.0: its
  Goldmine fetch carries no SocialCrawl address in the command.
- A Desktop routine whose permission picker is set to Manual stalls on every Bash step, its
  SocialCrawl calls included: the guard passes a call silently and never returns `allow`, so the
  picker decides.
- There is no daily total: each run is held to the one budget, so several runs in a day can spend
  that many times it.
- A routine run's count lives in its own session file: a deleted session file restarts that run's
  count.
- One number caps every kind of run at once: a budget set for a routine also caps attended sessions
  and `claude -p` runs while it is set.
- The guard's own files are kept from Claude's Bash, PowerShell and write-type tools only. It can't
  stop an MCP tool's shell or file writes, a glob (`socialcrawl-b*`), a path built at runtime, a `cd`
  into revxl followed by a bare file name in a later command, a script on disk, or another mod's own
  file writes (`$.fs`).
- Every Write, Edit, MultiEdit and NotebookEdit call now starts the guard: a Node start of about 50
  to 100 ms each.
- Two sessions moving the call record to `.1` at the same moment can lose a line or a `.1`.
- A short name for a guard file that doesn't exist yet can't be read as its long name, so a
  write-type call that creates the file by its short name isn't stopped.
- A `cd` into revxl followed by a bare `rm -rf sessions` in a later command isn't seen as the revxl
  folder's delete.
- A delete or move run by a program rather than named in the command, such as
  `python -c "shutil.rmtree(...)"` or `find ... -delete`, isn't seen.
- A Bash or PowerShell command whose text only mentions a revxl location and a guard file's name,
  such as a `git commit -m` message or a `grep`, is denied as if it changed the file.
- A Bash or PowerShell command that only mentions `budget-write`, such as a `grep`, an `echo`, a `cat` of a file of that name or a `git commit -m` message, is refused as if it ran the Budget pane's save step.
- A symlink or junction that points into revxl isn't followed: a write through it under another
  path isn't seen.
- The folder rule sees an `SC_REVXL_HOME` not named revxl only where a command spells its resolved
  path; another spelling (`$SC_REVXL_HOME`, a `~`-relative path) isn't seen.
- The folder rule sees a glob that stops at the folder (`~/.claude/*`, `~/.claude/revxl/*`), but not
  one that only matches its name (`~/.claude/rev*`).
- A delete or move of a folder above `.claude`, such as `rm -rf ~`, isn't seen as the revxl
  folder's.
- A Bash or PowerShell command that names a guard file or the `.claude` folder by its 8.3 short name
  (`SOCIAL~1.JSO`, `CLAUDE~1`) isn't seen.
- If `socialcrawl-calls.jsonl.1` is a folder, a record at 1 MiB can't be moved, and every later line
  is dropped; no decision changes.
- Over-blocks, the safe direction: the folder rule has no left boundary and reads the whole command,
  so these are denied too: `rm -rf /tmp/foorevxl`, `cd ~/.claude/revxl && rm old.md`,
  `git rm -r --cached revxl`, `echo rm ~/.claude/revxl`, a commit message that says "move the revxl
  folder", a verb and the folder in unrelated parts of one command
  (`ls ~/.claude/revxl && rm -rf build`), and a project's own `.claude` folder (`rm -rf .claude`,
  `git rm -r --cached .claude`; `rm -rf .claude/commands` passes).
- Another plugin can rewrite what any mod draws: this one's band, status line and toast included.
- The toast can name the wrong call when Bash calls run side by side: the call record carries no
  tool-use id, so the toast shows this session's newest line, can show it twice, and Round-up can keep the other call's saved file.
- A free call, and a tamper, not-plain or not-Bash deny, writes no call-record line, so it moves
  neither the band's refused warning nor a toast.
- A script Claude writes itself, a name built at runtime, a name split up with shell quoting (`budget"-"write`), or another plugin's mod (`$.fs`) can still
  write the budget file; the guard can't see those.
- The Budget pane's save runs as a `$.process.run` that another plugin hooking `process.run` can see.
  It carries the revxl folder and the budget numbers only, never the key.
- Two Budget panes saving at the same moment: the later save wins whole.
- A target typed into the Endpoints tab that holds `budget-write`, or a guard file's name together with `revxl`, gets the guard's 'guard file left alone' refusal when Claude runs the call: nothing is spent, but the message is about the budget, not the target.
- A target holding `&deep_scan=true` or `&include=transcript` is counted at the higher price those flags carry (15 or 10 credits), not the button's label. It errs high, as the guard always has.
- A target holding a lone UTF-16 surrogate makes the press do nothing: no prompt is sent and no note is shown.
- Whether the mod's pane state (Round-up's saved files, the Suggested tab's recent prompts and whether it was opened) is kept per session when one app runs several sessions is unconfirmed. If it is shared, one session's saved files can show in another's Round-up, and one session's prompts can feed another's suggestions.
- Round-up keeps every file this session's counted calls saved, with no cap; past roughly 700 the Summarize button can be pushed out of the pane (Summarize itself lists at most 20).
- Round-up finds saved files from a command's `-o`, `>` and `>>` targets only: `tee`, `--output`, `>|`, `&>`, a numbered redirect and some heredoc or backtick shapes are missed, and a command such as `-d '-o' …` can list a file that isn't one. It is display only; Summarize leaves out anything unsafe.
- On Desktop, the band's pill shows a thin sliver of colour at 0 credits spent once a limit is known.
- After the call record moves to `socialcrawl-calls.jsonl.1` at 1 MiB, the band shows the session budget or the automatic cap, and no refused warning, until this session's next line in the new record.
- A line of this session's in the call record that lacks a field shows `undefined` in its toast, its Round-up row or the band's refused warning. The guard writes every field.
- When the budget file is there but can't be read just now, the Budget pane still highlights Automatic, and its top line can say "automatic cap", beside the line saying the file couldn't be read.
- In the terminal the band writes its numbers without commas (`1200 / 2000 cr`), while the panes and the Desktop pill write `1,200 / 2,000`.
- For developers: the Summarize text's mirror of the research suggester's patterns is pinned for the four it has today; a synonym added inside one, an inline pattern or a normalisation step there isn't caught. Two Round-up behaviours are right but untested: a saved path holding `"` is left out of Summarize, and a call record whose size didn't change gives no toast. Guard fixture P2-A16 can time out under machine load. The mod's 15-minute balance refresh test can time out under load too. `tsc_mod.mjs` type-checks against the Claude Code type file with the newest file time, not the highest version. The 3e lint that checks the guard's wording is untuned: it reads words, not meaning.
- A failure report whose summary names the budget, day or calls file can't be sent or skipped when the project's own path holds a folder named `revxl`: the guard reads it as one of its files. The draft stays in `socialcrawl-superengine/reports/` for the client to email.
- On Windows with only the `py` launcher (the python.org default), `python` and `python3` can be the Microsoft Store stand-ins, so the failure report falls back to the body file in `socialcrawl-superengine/reports/` for the client to email.
- The failure report's body file and drafts stay in the project folder's `socialcrawl-superengine/reports/` after a send; in a git project, add that folder to `.gitignore`.
- The research ledger is tested against fixtures and has never been reconciled against a live charge: where its figures and the account's own balance disagree, believe the balance.
- Names and reasons drawn by the band and its tabs show zero-width joiners and direction marks as a space, so an emoji built from several parts, or Persian or Indic text, can show a gap. Display only.

## 0.3.1 - 2026-10-08

### Changed
- **The credit guard watches the PowerShell tool too.** Its three hooks (PreToolUse,
  PostToolUse, PostToolUseFailure) match `Bash|PowerShell`. A SocialCrawl call through any tool
  but Bash is never read as a plain `curl`, whatever its shape: attended it asks every time,
  naming the URLs it can see, and once it runs that visible total is counted; unattended it is
  denied and nothing is counted. Every such ask or deny says to use the Bash tool, where a plain
  `curl` is still counted silently under the cap. A hook input with no tool name is read as Bash,
  as before.
- **The session's count has its own file: `<revxl>/sessions/socialcrawl-<session id>.json`**
  (`<revxl>` is `SC_REVXL_HOME`, else `~/.claude/revxl`), with its lock beside it. The guard
  makes the `sessions` folder on the first SocialCrawl call that isn't a free plain `curl`; if it can't, that call is refused at once,
  naming the folder. TEMP is no longer used, and the old `%TEMP%/sc-credit-guard-<session id>.json`
  is ignored: never read, never written. The reason: shortform-superengine 0.6.0's guard writes
  that same name, unlocked, so it could overwrite this guard's count. A plugin update in the
  middle of a session therefore starts that session's count from 0, and the balance is read again.
- **Every wait ends within one time limit: 7 seconds from the guard's start.** The lock wait (4
  seconds at most), the balance read (3 seconds at most), the run after a command retrying its
  save, the lock delete retries and the PATH scan for a local transcription route are all cut to
  the time left, and a slow Node start uses part of it. A run out of time takes a path it already
  had: no lock is a refusal, and a balance read cut short is an unreadable balance, so the paid
  call asks. The lock refusal states the wait it really had.

### Known limits
- Claude Code kills a hook still running at its 10-second timeout and lets the tool call run,
  with nothing asked or counted. The 7-second limit exists to finish every run before that; it
  can't help a run whose process doesn't start in time.
- `<revxl>/sessions/` is never pruned: about 100 bytes a session.
- shortform-superengine 0.6.0 writes the old TEMP file (0.6.1 moved to its own name); this guard
  reads neither. Shortform's own guard still watches only Bash, so with both plugins on, a paid
  Bash call can be asked about twice.
- With the Bash tool unavailable, every SocialCrawl call through PowerShell asks.
- A PowerShell call's own verb flag (`Invoke-RestMethod -Method Post`) isn't read, so a POST
  through it is priced as a GET: it still asks, but the visible total can be low (up to 20
  credits for `web/sessions`). Use the Bash tool, where `curl -X POST` is priced.
- A SocialCrawl address hidden from a plain text match (split strings, an escape character
  inside the host) is not seen by the guard in either shell.

## 0.3.0 - 2026-10-07

### Added
- **An optional Jev decision layer, `hooks/jev.mjs`.** With an OpenRouter key it asks Jev
  (TypeSafe's decision model, pinned to `typesafe/jev-1.13-20260917`) three things: what an ask
  is still missing and which package fits it (`intake`), which endpoints could answer an ask no
  package fits (`cuts`), and how well each option would answer it (`worth`). Jev never sees a
  price and never approves spend: every price comes from `hooks/price.mjs`, the ranking is code,
  and the person's pick is the go. Without a key it exits 3 and sends nothing. It can only call
  OpenRouter's decisions endpoint.
- **The research front door runs the Jev path.** On an unnamed ask, unless the suggest hook's note
  says `jev: off`, `research-plays` writes the ask to a file and runs `jev.mjs intake`: a package fit goes to
  `worth`, a `none_fit` to `cuts`, the router, then `worth`. The menu is Jev's first three priced
  options plus "None of these — just the free path", and the pick is the go. With no key
  `jev.mjs` exits 3 and the front door takes the no-key path without a word.
- **The suggest hook's note ends `jev: on` (with the ask file's path) or `jev: off`.** It only
  checks that an OpenRouter key is present, the env var set or the key file non-empty, and never
  reads the key.
- **A key box, `setup/key-box.ps1` (Windows) and `setup/key-box.command` (macOS).** One small
  window with a hidden field takes a SocialCrawl or OpenRouter key (`-Kind socialcrawl|openrouter`),
  so the key never passes through the chat. It closes itself after 3 minutes, saves the trimmed
  key to `~/.config/<kind>/api_key` with owner-only permissions, and prints one line that never
  holds the key: `RESULT=OK len=<n> prefix=<True|False>`, `RESULT=CANCEL`, `RESULT=TIMEOUT` or
  `RESULT=FAIL step=<show|folder|write|acl|kind>`. Exit 0 saved, 2 cancelled, timed out or left
  empty (nothing written), 3 a bad kind or a step that failed. On Windows a failed step leaves
  an existing key in place. `setup-key.*` stay as the fallback.
- **Onboarding offers Jev once (Step 3b).** After the SocialCrawl key is proven it asks, in
  plain words, whether to add Jev with an OpenRouter key, opens the keys page or prints its
  link, asks "Got your key copied?" and then opens the key box. A "no" is kept in
  `<revxl>/jev-declined` (`SC_REVXL_HOME`, else `~/.claude/revxl`) so it isn't asked again;
  "set up Jev" still opens the step, and a saved key removes the "no".

### Changed
- **Prices now come from the vendor's own catalogue.** `hooks/costs.json` and the platform
  references regenerate from a same-day snapshot of `GET /v1/utility/endpoints`, `openapi.json`
  and `llms.json` (2026-10-06): 645 endpoints across 68 platform namespaces, the new `economy`
  platform included. Each entry carries
  the catalogue's `credits_label` and the range read from it: flat, a metered low-high range,
  or no ceiling at all for six of the seven labels that are sentences, which always ask. The
  seventh, `prism/lookup`, states its own bounds (1 credit for most lookups, 5 for Amazon and
  LinkedIn), so it is priced from them and quoted at 5; its hardcoded 1 is gone. The
  hand-maintained per-unit lists and the regex that guessed at metering are gone, and a
  per-unit tripwire fails the build if a batch call over a list of items is ever labelled flat.
  The vendor removed `google_finance`, so its reference is deleted.
- **Package options now say what they pull.** The option labels in `packages.json` carried
  test notes; each is now a plain description of what the option pulls.
- **Jev's recommendation takes a full answer when it costs little more.** A recommendation that
  would answer most of the ask gives way to the cheapest option that would answer it fully, when
  that option's top price is at most 5 credits higher.
- **A platform the ask names always survives `cuts`.** Amazon in "compare it on Amazon, Walmart
  and eBay" is searched even when Jev ranks other platforms first: one more Jev request per named
  platform outside the top three, so a `none_fit` ask makes at most 7 Jev calls plus one per such
  platform (8 plus one per such platform with the re-intake). The names come from the suggest hook's own list, now in `hooks/platform-tokens.mjs`.
- **`research-plays/SKILL.md` is smaller.** The rubric, the router paragraph, the strongest-first
  rule and the menu-ordering question moved to `references/elicitation.md`, the no-key path's
  reference. `prism/lookup` is quoted at 1-5 credits and `prism/post-stats` at 2 per Instagram
  URL (100 Instagram URLs hold 200 credits).
- **The research router reads the files it is handed.** It reads `curated-workflows.json`,
  `packages.json` (new to it), `costs.json` and the per-platform references at the absolute
  `${CLAUDE_PLUGIN_ROOT}/…` paths its dispatch hands it, never relative to the working
  directory, and the no-key dispatch in `references/elicitation.md` now hands them. On Jev's
  `none_fit` path it takes the `cuts` survivors, returns options only, and never a free
  (`websearch`) option: the menu's "None of these — just the free path" already covers it.
- **Jev refuses a price word joined by `_`.** `free_tier`, `5_credits` or `paid_api` in any text
  value it would send is refused before sending, as `free-tier` already was, and the catalogue
  sentences `cuts` sends are filtered the same way. Keys are read as before, so intake's
  `free_web` route still goes out.
- **The build's plan validator rejects a free (`websearch`) option that has legs.**
- **A silent session cap replaces the per-call credit ladder.** The credit guard counts each
  paid call's quoted worst case against min(500, 25% of the balance) and says nothing under it.
  It asks once when a command takes the session's committed total across the next cap step,
  naming that total, the cap, the command's worst case and the balance; a balance it can't read
  counts as a crossing. It still asks before every call it can't count: a transcript, `cohorts`,
  an unreadable URL and a per-unit call with no ceiling. The asks on every metered call, every
  call of 5 credits or more and every 15 credits of session spend are gone, and so is the "no
  flat price" wording.
- **Only a call that runs is counted.** An asked call waits until the same script, now also
  registered on PostToolUse and PostToolUseFailure, sees it run, so a declined ask is never
  counted and the next paid call asks again. Unattended (`CLAUDE_CODE_SESSION_ATTENDED=0`), an
  ask becomes a deny that is never counted.
- **The guard reads the balance, and logs what it decides unattended.** On the first command of
  a session that shows a paid SocialCrawl URL it reads `GET /v1/credits/balance` (0 credits) with
  the key the plugin already uses, and keeps the figure for the session: that is the balance the
  cap is a quarter of. An unattended command that isn't a plain `curl` is denied without a read.
  Unattended, every deny and every paid pass is one line in
  `~/.claude/revxl/credit-guard-unattended.jsonl` (the visible `/v1/` paths, never the command
  or the key), and the next attended prompt says once: "N unattended denials (~Q credits
  blocked), M credits spent unattended since <date> → <log path>". An error inside the guard
  now denies unattended; attended it still lets the command through to the CLI's own prompt.
- **The guard's surcharge overlay is gone.** The 2026-09-23 labels already include every
  conditional charge, so its five rows were counted twice: `creator-vet` 100 instead of 75,
  `crisis-radar` 75 instead of 45, `video-intel` 25 instead of 15, `youtube/search/advanced` 16
  instead of 11 and the TikTok transcript 20 instead of 10.
- **A call the guard can't count commits its stated maximum when it runs:** `prism/investigate`
  the `budget` its URL sends, or 200 when it can't read one, `web/sessions` 20 and
  `economy/imports` 20.
- **The guard is silent only for a plain `curl`.** A plain command is the plugin's own call
  templates plus tidy output: `curl` calls chained only with `&&`, `;` or new lines (with `sleep N`
  and full-line `#` comments between them), each with only `-s`, `-S`, `-sS`, `-N`, `-f`,
  `--max-time`, `-X`, `-H`, `-d '…'`, `-o` and `-w`, one whole quoted `https://…/v1/` URL, a
  key header of `$NAME`, `${NAME}` or `$(cat <file>)`, and output only into `jq`, `head`,
  `python -m json.tool` or a file. Any other command carrying `socialcrawl.dev` (a loop, a pipe
  into a program, a wrapper, a variable, a heredoc, a note, `grep`, `echo`, a commit message, a
  docs URL, a free `credits/*` call in any of those) gets one ask, "NOT A PLAIN CURL", naming the
  total of the SocialCrawl URLs visible in it, counted once it runs; unattended it is denied.
  This replaces the loop and shell-variable asks and the repeat detection, which kept missing
  shapes (brace lists, a loop piped into `bash`, Python shelling out to curl, curl config files).
- **`dry_run=1` is counted at its full label price**, declared or not: a hidden `~/.curlrc`,
  `-K`, `--expand-data` or `--request-target` can change what curl sends, so a free dry run can't
  be proven from the command. Every SocialCrawl URL visible anywhere in a command, a heredoc
  body's included, counts toward that command's total.
- **The skills, the README and the plugin description describe the cap**, and the prose prices
  match the catalogue: `prism/lookup` 1-5 credits (5 on Amazon and LinkedIn), `prism/post-stats`
  2 per Instagram URL (100 Instagram URLs hold 200) and `prism/comment-lookup` at most 100 a
  batch.
- **The `socialcrawl` skill asks once too.** An ask that doesn't name SocialCrawl gets "Are you
  trying to search with SocialCrawl?" once per session, one answer for both skills.
- **Onboarding goes by whether the key works, not by the marker.** A returning user whose key
  is missing or answers 401 on the free balance call goes to the key box (a dead key in
  `SOCIALCRAWL_API_KEY` is named instead, since the env var wins over the box's file); a key
  file alone no longer counts as set up. Onboarding's key step opens the key box instead of sending the user
  to `setup-key.bat` and waiting.
- **A missing key gives one message and one route.** The `socialcrawl` skill's key step now
  says "This needs a SocialCrawl key and I don't see one in this session" and opens
  `onboarding`, as `research-plays` does; the setup reference no longer says to ask for the key.
- **The catalogue is the 2026-10-06 snapshot** (`research/socialcrawl-docs-2026-10-06/`, with
  its `PROVENANCE.md`; 0 credits): 645 endpoints across 68 platform namespaces. Sixteen endpoints
  are new: the `economy` platform (five; `economy/imports` is priced by a sentence, "20 credits per
  call, whatever the limit", so it always asks and counts 20 once it runs), `finance/fundamentals`, `google/keyword-volume`, `tiktok/similar`, `tiktokshop/sales`
  and seven free `utility` calls. Four prices widened: `linkedin/profile/posts` is now metered
  5-200 (2 a post past 50), `facebook/adlibrary/company/ads` 5-35 (`include=audience` holds 1 a
  ad), `instagram/search/reels` 1-69 and `search/multi` 0-28. `tiktokshop/sales` and
  `search/multi` join the rows whose vendor label decides the price. `economy` is an ordinary
  word, so it is not a platform trigger. `search/everywhere` is described as the vendor does:
  14 platforms, up to 17 sources (it said 12). The tier tables carry the 10-06 counts.
- **`ad-library-recon` is quoted 15-65 credits** (was 15-35): the ads pull is now metered up to
  35. The row is hand-reviewed, and `facebook/adlibrary/company/ads` joins the
  response-determined endpoints.
- **The silent session cap is min(500, 25% of the balance)** (was min(200, …)). The guard still
  counts the worst case.
- **A missing TEMP folder refuses at once.** A paid call is refused with no 4-second lock wait:
  attended the reason names the missing folder, unattended it is denied with the cap-step reason;
  the run after a command stops at once too.
- **A save that doesn't throw counts as recorded.** The read-back after each save is gone; a save
  that errors still refuses the call.
- **Monitors calls are free per call and pass silently.** Every `/v1/monitors` call (list, get,
  create, pause, delete, runs, timeseries, export) is priced 0. The `socialcrawl` skill states a
  monitor's monthly cost (its recipe's price plus 1 credit of orchestration, × its runs a month;
  the create response's `estimated_monthly_cost`) and that it bills until paused or deleted
  before one is created. Cohorts still ask.
- **An unattended deny ends with its own line** ("Nothing was counted. If it is needed, run it in
  an attended session…"), not the attended "run it only on a yes" or "every paid call asks". A
  lost session's ask says the committed total was lost, instead of "~0 committed" and "couldn't
  read your balance", and a not-plain ask with nothing visible to count no longer says it will be
  counted.
- **Each paid call is one plain `curl` in its own Bash call, saving to a literal `-o` file**, with
  any processing in a separate call (the `socialcrawl` and `research-plays` skills). The API Key
  section maps each label to its exact header, and the balance flow works for a key kept only in
  the file. `credits_remaining` is described as null on a cached answer.
- **The no-Jev menu always lists `search-everywhere` for a "what are people saying" ask**,
  usually first, with the deeper platform pulls after it.

### Known limits
- 21 platforms have a generated reference with no curated notes yet.
- A monitor's runs bill outside the guard: it prices the monitors calls at 0 and never sees a
  scheduled run, which bills the recipe's price plus 1 credit for orchestration. The skill's
  warning before creating one is the only control.
- The shortform-superengine mirrors are not re-synced (`sync_lean.py` was not run).
- `prism/lookup` is priced from its 2026-10-06 label (unchanged since 2026-09-23), at most 5. A pricier resolved item type
  added later is under-counted until the next snapshot.
- OpenRouter's decisions endpoint is in alpha. Jev's `cuts` questions and their 0.5 line have
  been run live once (2026-09-25).
- The suggest hook stays silent on most asks and on a direct `/research-plays`, so on an
  unnamed ask the front door usually has no note: it then tries Jev with the ask file at `~/.claude/revxl/jev-ask.json`.
- Named platforms are matched with the suggest hook's words: a stop-listed name (Target, Threads,
  Kick) or a two-letter one (`hm`, `g2`) never counts, and an ordinary word that is also a
  platform ("google it") adds a Jev request. A compound name counts twice: "Google Shopping"
  names `google` and `google_shopping`, "TikTok Shop" names `tiktok` and `tiktokshop`.
- Whether `${CLAUDE_PLUGIN_ROOT}` reaches the model substituted inside the router agent file and
  `references/elicitation.md` is not measured yet.
- `prism/jobs`, `web/batch-scrape` and `web/monitors` state no maximum, so the guard counts them
  at 0 and asks before every one. `economy/imports` states its price in a sentence (20 a call),
  so it asks before every one and counts 20 once it runs.
- A mention (a note, `grep`, `echo`, a commit message) or a docs URL asks, and is denied
  unattended. Once it runs, the URLs visible in it are counted as if they were called: an
  over-count.
- A script written with `cat > x.sh <<'EOF'` is counted once, when it is written: the guard reads
  each command on its own, so running it again later is not counted.
- `prism/post-stats` is counted at its label worst case, 500, whatever the batch holds: an
  over-count (100 Instagram URLs hold 200), so a 100-URL Instagram batch asks at every cap
  step, the 500 cap included.
- The committed total is the quoted worst case, not the bill. One test session counted 111
  credits for about 4 really spent: every `1-17` page counts 17 and every `1-25` search 25, so a
  cap step arrives after far less real spend (why the cap is now min(500, …), not min(200, …)).
  An asked call that the user then rejects leaves its quote pending; nothing counts it.
- The cap runs high on purpose: it counts quoted worst cases, a call the CLI's own permission
  prompt then declined, a failed command that may never have billed, and a `budget` it can't be
  sure is sent (a command that is not a plain `curl`, or a URL that is not a plain quoted `curl`
  argument, or any data flag in the command). Every over-count is in the safe direction; the
  ledger reconciles the real spend.
- `dry_run=1` counts at its full label price: an over-count, since the vendor charges 0 on the
  49 endpoints that declare it.
- A hidden `~/.curlrc`, or a `CURL_HOME` set outside the command, that adds URLs or query
  parameters to a plain curl isn't seen.
- The not-plain ask names, and commits once it runs, only the total of the SocialCrawl URLs it
  can see: a loop or a script that sends more is under-counted, and a URL assembled from pieces
  adds nothing.
- The balance read waits at most 3 seconds, and a session makes at most 3 tries: a failed read
  (no key, a timeout, an error, an answer with no number in it) is tried again on the next paid
  command, and until a read succeeds every paid call counts as a crossing. A balance read as
  0-3, a negative or a fraction is kept for the session and gives no cap, so every paid call
  asks. If the session's state file can't be saved (TEMP missing or read-only, a full disk), the
  balance is not read and no paid call runs: each is refused (below). A save that fails
  part-way can leave the file empty or cut off, which the next call reads as a lost total (below).
- A damaged or unreadable session file turns the silent cap off for that session, whether the
  guard meets it before a command or after one: every paid call asks, or is denied unattended, and
  the balance is not read again. Damaged means empty, cut off, not a JSON object, or a `spent` that
  isn't a finite number; unreadable is any read error except a missing file, which is a new
  session. A read error that lasts only a moment (a scanner holding the file), or a read cut off
  by a save in progress, counts too: an over-ask, not an under-count. A file that stays unreadable
  still takes saves, so its paid calls ask; an asked call's quote can't then be read by its Post
  run, so it is not counted, but the cap is already off and nothing passes silently.
- A call the guard can't record is refused, attended and unattended. Before a command runs, the
  guard has to save either its count (a silent pass) or its quote (an ask, counted once the
  command has run). When it can't, the call is denied with a message that gives the reason and
  the session file's path and says to run it again, so no ask goes out for a call that would then
  run uncounted. "Can't" is any of: the guard didn't get the session lock within 4 seconds, the
  session folder is missing, or the save threw an error. A save that doesn't throw counts as
  recorded; there is no read-back. A session file that can never be written (TEMP missing or
  read-only, a folder in its place) therefore refuses every paid call until that is fixed; with
  TEMP missing each refusal comes at once; attended it names the missing folder, while unattended
  the call is denied at once with the cap-step reason (no balance can be read there). Unattended, an ask is
  denied before anything is recorded, so its deny keeps its own kind (`cap-step`, `not-plain`,
  `transcript` and so on); only a silent pass the guard can't record is logged as a deny of kind
  `error`. A free call, and an ask that counts nothing, are not affected.
- A save that is lost without an error is not detected. The guard trusts a save that doesn't
  throw, so a pass or an ask whose save silently vanished is counted nowhere, and later calls can
  pass silently by that much.
- Guard runs of one session take turns: each holds a lock file beside the session file from its
  read to its last save, and has 4 seconds to get it, trying again every 20 ms whatever error the
  attempt gives. A run still waiting when the 4 seconds end (slow balance reads ahead of it, or a
  lock left by a killed run) refuses its paid call, as above. A lock left by a killed run is
  cleared once it is 10 seconds old, so for up to 10 seconds that session's paid calls can each
  wait 4 seconds and be refused; two runs clearing it at the same moment can both go ahead. The
  slowest run (a full wait for the lock, then a balance read that times out) takes about 7 of
  the hook's 10 seconds.
- A call that has already run can't be refused. The run after a command tries its save again
  until its 4-second wait ends (at once when the session folder is missing); if it still can't save (the file busy or read-only all that
  time), that asked call is never counted, and later calls can pass silently by that much. If
  that run never got the lock, it saves anyway, and can collide with a run that still holds it:
  one of the two counts can be lost.
- Once the balance is read, an unattended session (`claude -p`, a scheduled run) spends
  silently on plain `curl` calls up to the next cap step. Nobody sees those calls until the
  next attended prompt's notice.
- The unattended log only grows; nothing rotates or trims it. It holds paths, figures and the
  session id, never the command or the key. `SC_REVXL_HOME` moves it.
- The notice appears on the next prompt of an attended session only (the suggest hook doesn't
  run under `claude -p`). Q and M add up quoted worst cases, the cap's own count, not what the
  vendor billed; the ledger reconciles the real spend.
- A hook call with no session id shares one state (`nosession`) with every other such call: one
  committed total, one read balance and one count of failed reads.
- The macOS key box (`key-box.command`, `osascript`) has not been run on a Mac.
- The clipboard keeps a key that was copied to paste into the box (Windows clipboard history
  included); the box can't clear it.
- On Windows the box's field is hidden only on screen: any program running as the same user can
  read its text through .NET UI Automation while the box is open. Such a program can already
  read the saved key file, so this adds no new reader. Standing rule: no agent or test harness
  ever lists or reads the box's controls while a real key is in it; tests, live ones included,
  use dummy values only.
- The box checks only the length and the start of the key, so a wrong key is saved; for
  SocialCrawl, onboarding's balance call catches it straight after. A wrong OpenRouter key
  is not caught until Jev's first call.
- With no desktop (Cowork, browser chat, a remote shell) or on Linux there is no box: the key
  goes in the env var, set outside the session.
- That env-var line takes the key at a hidden prompt, so the value is in no command line and no
  shell history, but on macOS / Linux it is still saved as plain text in the shell profile.
- The macOS / Linux env-var line (`read -rs` into the shell profile) has not been run on a real
  Mac or Linux terminal; it was tested only with a dummy key and a scratch home folder.

## 0.2.1 - 2026-08-25

### Fixed
- **The credit guard has never once fired since 0.1.1 - it now does (in terminal sessions).**
  The hook emitted a decision missing the required `hookEventName`, and put its reason in
  `systemMessage` rather than `permissionDecisionReason`. Claude Code cannot route such a
  decision, so it discarded the output and ran the command - exit 0, no error, nothing
  logged. Invoked by hand the script printed a perfect-looking `deny`, which is why three
  earlier investigations cleared it. Every banned transcript call and every un-confirmed
  paid call since 0.1.1 went through unguarded.

  **Coverage - please read, and note what is NOT claimed:**
  - **Terminal `claude` sessions: enforcement confirmed.** Measured.
  - **Claude Desktop: unverified, and not previously testable.** Earlier notes said the hook
    "is not invoked" in Desktop. That was never established. Desktop materialises plugins from
    the *published* marketplace version, and every published build until this one carried the
    inert guard above - so what was measured was a dead hook failing to fire, which says
    nothing about whether Desktop invokes hooks at all. **0.2.1 is the first build on which
    that question can actually be answered.** Until it is, assume Desktop is unguarded.
  - **Cowork: not enforced.** Plugin hooks are never loaded there. Independently confirmed.

  If you rely on the guard, run SocialCrawl work from a terminal session.
- **Six metered endpoints were priced as flat calls.** Worst is `prism/ai-visibility`,
  stored at 2 credits but billed **2 per probe** - its defaults (8 runs x 2 engines) make
  the cheapest real call **32 credits**, and at 2 it sat below the guard's 5-credit ask
  threshold, so it spent silently. Also `prism/share-of-voice` (40/brand, 2-5 brands),
  `prism/org-radar` (5/repo), `prism/comments` (1 per page scanned), `reddit/omni-search`
  (per page + per expanded thread) and `search/news` (per leg). `_perUnit` now carries 14
  entries; the guard quotes the unit and the realistic worst case, never the unit price
  alone.
- **`prism/lookup` was hardcoded as free but bills 1 credit.** Measured live and uncached:
  the catalog, the vendor's pricing page and the utility endpoint all store 0; two successful
  calls each billed 1. The guard returned 0 *before* consulting the cost map, so the spend was
  not merely mispriced - it was never recorded at all, and could never contribute to the
  15-credit "still going?" prompt. A loop of lookups reported nothing and gated nothing. The
  override lives in the hook rather than in `costs.json`, because that file is generated from
  the vendor spec and a regeneration would silently restore the 0.
- **The cost figures the skills quote were wrong wherever an endpoint is metered.** The
  guidance told the model that a client with a *low balance* should be offered "the free/1cr
  cheat codes" - a list on which `prism/post-stats` really bills per URL (100 Instagram links
  = 500 credits), `prism/comments` 2-5+, and `reddit/omni-search` 5-8+. That pointed the
  broke client at the most expensive endpoint available. Every metered endpoint now quotes a
  `low-high` range with the parameter that drives it, and the cheat-code list is replaced by a
  real-cost table. `share-of-voice` 40 -> 80-200, `org-radar` 26 -> 6-26, `ai-visibility`
  "~10cr" -> 20-1,600.
- **The API key is no longer written into commands or requested in chat.** The skill
  previously inlined the key value into every curl - putting it in the transcript - and
  onboarding asked you to paste it into the conversation. Calls now read it at run time
  from the key file. Both instructions were inherited verbatim from upstream. **If you set
  up on 0.1.x or 0.2.0, rotate your key.**

### Added
- **`setup/` - a double-clickable key helper** (`setup-key.bat`/`.ps1` on Windows,
  `setup-key.command` on macOS/Linux). Opens its own window, hides the key as you type,
  verifies it against the free balance endpoint before saving, writes it with owner-only
  permissions, and writes nothing at all if verification fails. The key never touches the
  chat. The Windows path is verified; the macOS/Linux script ships untested.

### Known stale
- The plugin describes itself as covering **48 platforms / 381 endpoints**. A full live sweep
  on 2026-08-23 measured **400**. The reference files also disagree with each other (one tier
  table sums to 417 directly above a "Total: 381"). These counts are descriptive only - no
  cost or gating decision reads them - and correcting them requires regenerating the reference
  set, which is deliberately not bundled into a guard-safety release.

## 0.2.0 — 2026-08-16

### Fixed
- **Batch endpoints bill per row, not per call — the previous release understated some
  costs by up to 500×.** 0.1.0 advertised `prism/post-stats` as "refresh a whole watchlist
  for 1 credit". It is metered per successful URL at that URL's platform rate, so 100
  Instagram links is **500 credits**, not 1. Eight endpoints bill per row / item / 50-id
  chunk / page; every one now renders its unit in the refs, and the credit guard always
  asks before a metered call. The error was inherited from SocialCrawl's own docs and was
  caught by a live test. **If you ran a large batch on 0.1.x, check your balance.**
- **Pagination guidance was teaching retired parameters.** SocialCrawl shipped a universal
  `cursor` parameter; the refs still directed you at each platform's native param
  (`max_id`, `next_max_id`, `page`). Send `pagination.next_cursor` back verbatim and the
  API maps it for you. 24 of 48 refs were affected.
- **The credit guard mis-priced two endpoints.** `costs.json` was keyed by bare path, so
  `POST /web/sessions` (5cr) passed as free against `GET /web/sessions` (0cr); costs are
  now verb-qualified. `POST /web/agent` (25cr) was missing entirely.
- `POST /youtube/transcripts` is now correctly denied — it is a transcript endpoint, and a
  live test confirmed 3 credits **per video**, so there is no batch discount to justify it.

### Added
- **Full catalogue coverage: 48 platforms / 381 endpoints** (was 43 / 333). New platform
  refs: ebay, home_depot, target, walmart, web. Every endpoint now carries the API's own
  description, its parameters and a ready-to-run curl.
- **"Which endpoint should I use?"** — seven decision tables plus a five-rung search ladder,
  so the cheapest correct endpoint is reachable. Previously every cross-platform search
  routed to `search/everywhere` at 20 credits while `search/forums` at 10 appeared nowhere.
- Endpoint-selection guidance for all 48 platforms, and stories/highlights routing.
- A Pagination section in `api-overview.md`, including the warning that **each page is a
  separately billed call**.

### Changed
- Refs are now generated from SocialCrawl's OpenAPI spec rather than its prose docs, and
  verified against the **live** catalogue. The old source documented GET operations only
  and could never see the 17 non-GET endpoints on web / youtube / prism.

## 0.1.1 — 2026-07-05

- Enforced credit-guard hook + prompt-injection defense (published directly to the
  marketplace; backfilled here for an accurate history).

## 0.1.0 — 2026-07-04

Initial release.

- **`socialcrawl` skill (canon):** full 43-platform / 333-endpoint reference set,
  generated from SocialCrawl's own docs + pricing registry — every endpoint row carries
  its **exact** credit cost (the public 1/5/10 tier model hides ~30 flat-override
  endpoints priced up to 50 credits; the refs don't). Cheat-codes section (free
  `prism/lookup` URL dispatcher, 1-credit `prism/post-stats` for 100 URLs, 1-credit
  `prism/comments`, 1-credit `reddit/omni-search` VoC sweep, 5-credit
  `prism/handle-audit` pre-pull gate). Hardened ⛔ transcription ban on all 9
  `*/transcript` endpoints.
- **`research-plays` skill:** 6 guided plays (VoC mining, ad-library recon,
  AI-visibility audit, link-in-bio offer recon, TikTok audience demographics, dev
  radar) + 10 big-gun one-shot runbooks (15–50cr) behind a strict gate ritual
  (balance + named cost + explicit confirm, never batched).
- **`onboarding` skill:** BYO-key setup with guided signup, 1-credit verify,
  plain-English credit briefing, and the `~/.claude/socialcrawl-superengine/.superengine`
  marker that RevXL format engines detect to offer deep plays.
