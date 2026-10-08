# Changelog — socialcrawl-superengine

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
