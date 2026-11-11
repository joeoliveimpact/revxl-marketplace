// Pure data layer for the Editor Cockpit: no engine calls, no I/O. register.ts lists the reel folders, reads the few
// JSON files the stage rules need, runs ffprobe on a master candidate, and passes it all in with $.clock.now();
// everything below turns that into the view the pane, the band and the status line draw.

// ---------------------------------------------------------------- reads ------

/** One file or folder read: what it held, that it is not there, or that it could not be read (and why). */
export type Read<T> = { status: 'ok'; value: T } | { status: 'missing' } | { status: 'unreadable'; reason: string }
export const ok = <T>(value: T): Read<T> => ({ status: 'ok', value })
export const missing = <T>(): Read<T> => ({ status: 'missing' })
export const unreadable = <T>(reason: string): Read<T> => ({ status: 'unreadable', reason })

/** A text read parsed as JSON; text that does not parse is unreadable, never an empty object. */
export function parseJson<T>(r: Read<string>): Read<T> {
  if (r.status !== 'ok') return r
  try { return ok(JSON.parse(r.value) as T) } catch { return unreadable('not valid JSON') }
}

/** A directory entry as $.fs.list gives it (FsEntry fits): size and mtimeMs are a file's own, 0 for a folder. */
export type Entry = { name: string; kind: string; size: number; mtimeMs: number; isLink?: boolean }

export const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)

// ---------------------------------------------------------------- paths ------

/** Backslashes to `/`, a Git Bash `/c/...` to `C:/...`, no trailing slash. */
export function normPath(p: string): string {
  // ponytail: a one-letter top folder (`/c/...`) is read as a drive; a real Linux `/c/` path would be misread.
  return p.replace(/\\/g, '/').replace(/^\/([a-zA-Z])(?=\/|$)/, (_, d: string) => `${d.toUpperCase()}:`)
    .replace(/(?<!^)\/+$/, '')
}

/** A folder as the store keys it: normalised and lower case (Windows paths ignore case). */
export const folderKey = (p: string) => normPath(p).toLowerCase()

/** The home folder: HOME, else USERPROFILE (stock Windows sets only the second). */
export function homeDir(env: { HOME?: string; USERPROFILE?: string }): string | undefined {
  const h = env.HOME || env.USERPROFILE
  return h ? normPath(h) : undefined
}

/** Fixed paths under the workspace root (the editor's scripts hardcode the `editor` folder for both). */
export const CONFIG = 'editor/editor.config.json'
export const PLATFORM = 'editor/.platform.json'

/** The videos folder, relative to the workspace: `paths.videos`, else `videos`. An absolute path, one with `:`, or one
 *  with an empty, `.` or `..` segment falls back to `videos` (board_sync.py's workspace_paths refuses the same). */
export function videosDir(config: Read<unknown>): string {
  const v = config.status === 'ok' && isRecord(config.value) && isRecord(config.value.paths) ? config.value.paths.videos : undefined
  if (typeof v !== 'string' || !v) return 'videos'
  // Read as board_sync.py reads it (PurePosixPath): empty and `.` segments drop out.
  const p = v.replace(/\\/g, '/'), segs = p.split('/').filter(s => s !== '' && s !== '.')
  return p.startsWith('/') || p.includes(':') || segs.includes('..') || !segs.length ? 'videos' : segs.join('/')
}

// ---------------------------------------------------------------- reels ------

// board_server.py's REEL: its first character already rules out a leading dot.
const REEL = /^[A-Za-z0-9_][A-Za-z0-9_. -]{0,119}$/
export const isReelName = (n: string) => REEL.test(n) && !/[. ]$/.test(n)

/** The reels: real folders (not links) directly in the videos folder whose names a board can open. */
export function reelNames(videos: Read<Entry[]>): string[] {
  return videos.status !== 'ok' ? []
    : videos.value.filter(x => x.kind === 'dir' && !x.isLink && isReelName(x.name)).map(x => x.name).sort()
}

/** The folders of a reel the stage rules and its activity look in; `root` is the reel folder itself. */
export type Folder = 'root' | 'raw' | 'work' | 'renders' | 'sound'
export const FOLDERS: readonly Folder[] = ['root', 'raw', 'work', 'renders', 'sound']
export type Probe = 'video' | 'novideo' | 'unknown'
/** One reel as register.ts gathered it: its folder listings, the reel-root JSON files the rules read (missing when not
 *  listed), and ffprobe's answer per master candidate in renders/ (by file name). */
export type ReelIn = { name: string; lists: Record<Folder, Read<Entry[]>>; json: Record<string, Read<unknown>>; probe: Record<string, Probe> }

// Atomic writes leave `*.tmp`, state backups `*.prev`: never an artifact, never activity.
const IGNORED = /\.(tmp|prev)$/i
/** A reel folder's files as the rules see them: files only, *.tmp and *.prev left out. */
export const filesIn = (r: ReelIn, f: Folder): Entry[] => {
  const l = r.lists[f]
  return l.status === 'ok' ? l.value.filter(x => x.kind === 'file' && !IGNORED.test(x.name)) : []
}

// ---------------------------------------------------------------- stages -----

export type BoardId = 'cut' | 'tweak' | 'beatmap' | 'sketches' | 'sound' | 'grade'
/** The six fixed board buttons, in order (Cockpit spec, H-R29): never read from boards.json. */
export const BOARDS: readonly BoardId[] = ['cut', 'tweak', 'beatmap', 'sketches', 'sound', 'grade']
export const BOARD_NAME: Readonly<Record<BoardId, string>> = {
  cut: 'Cut Board', tweak: 'Tweak Board', beatmap: 'Beat Map', sketches: 'Sketches', sound: 'Sound Board', grade: 'Grade Board',
}

/** A stage's done rule. `in` or its optional `or`: a file in that reel folder whose name matches (`video`: also size > 0 and ffprobe did
 *  not say "no video"). `applied`: at least one reel-relative output is as new as the matched file.
 *  `json`: that reel-root JSON parses to an object that passes `when`, or its JSON `or` does.
 *  An unreadable primary JSON or an unknown absence blocks the alternative. `never`: no artifact. */
export type Rule =
  | { in: Folder; match: RegExp; video?: true; applied?: readonly string[]; or?: { in: Folder; match: RegExp } }
  | { json: string; when: (v: Record<string, unknown>) => boolean;
      or?: { json: string; when: (v: Record<string, unknown>) => boolean } }
  | { never: true }

export type ActionId = 'start' | 'next' | 'hub' | 'switch' | 'record' | BoardId | 'master' | 'post' | 'send' | 'cockpit'

export type Stage = {
  name: string; short: string; rule: Rule; action: ActionId; board?: BoardId
  optional?: true      // Grade: never the main move, never blocks Master, drawn dashed
  head: string; sub: string   // the hero card in your move at this stage (the head's last word is drawn in coral)
  baton?: string       // the status line's words when the stage has no board
}

/** The ruled final master: `renders/<Reel> Master - MM.DD.YY.mp4` (H-S15a-4). Only files directly in renders/ count. */
export const MASTER = /^.+ master - \d{2}\.\d{2}\.\d{2}\.mp4$/i

const sentWithoutScenes = (s: Record<string, unknown>): boolean => s.sent_at != null && Array.isArray(s.beats)
  && s.beats.every(b => isRecord(b) && b.scene == null)

// The hub may change entries: each rule is one small data entry.
export const STAGES: readonly Stage[] = [
  { name: 'Record', short: 'Record', rule: { in: 'raw', match: /\.(mp4|mov|m4v|mkv)$/i, or: { in: 'root', match: /^RAW\.mp4$/ } }, action: 'record',
    head: 'Record your take', sub: "Put the recording in this reel's raw folder.", baton: 'record' },
  { name: 'Cut', short: 'Cut', rule: { in: 'work', match: /^(cuts|edl)\.json$/ }, action: 'cut', board: 'cut',
    head: 'Review the cut', sub: 'Pick the takes on the Cut Board, then press Send.' },
  { name: 'Ear pass', short: 'Ear', rule: { in: 'root', match: /^tweak-selection\.json$/, applied: ['work/cuts.json', 'work/edl.json'] }, action: 'tweak', board: 'tweak',
    head: 'Do the ear pass', sub: 'Play the cut at ship speed, then press Send.' },
  { name: 'Beat map', short: 'Beats', rule: { json: 'beat-map.state.json', when: s => s.sent_at != null }, action: 'beatmap', board: 'beatmap',
    head: 'Rule the beat map', sub: 'Set the beat plan on the Beat Map, then press Send.' },
  { name: 'Motion', short: 'Motion', rule: { json: 'sketches.state.json', when: s => !!s.locked_at, or: { json: 'beat-map.state.json', when: sentWithoutScenes } }, action: 'sketches', board: 'sketches',
    head: 'Lock the motion', sub: "Lock each beat's motion on the Sketches board." },
  { name: 'Sound', short: 'Sound', rule: { in: 'root', match: /^sound-selection\.json$/, or: { in: 'sound', match: /^final\.mp4$/ } }, action: 'sound', board: 'sound',
    head: 'Review the sound', sub: 'Audition the cues on the Sound Board, then press Send.' },
  { name: 'Grade', short: 'Grade', optional: true, rule: { in: 'root', match: /^grade-selection\.json$/ }, action: 'grade', board: 'grade',
    head: 'Grade the picture', sub: 'Optional: grade on the Grade Board, then press Send.' },
  { name: 'Master', short: 'Master', rule: { in: 'renders', match: MASTER, video: true }, action: 'master',
    head: 'Render the master', sub: 'Every board is done. Render the final master.', baton: 'render the master' },
  { name: 'Post', short: 'Post', rule: { never: true }, action: 'post',
    head: 'Post the reel', sub: 'The master is ready. Write the caption and post.', baton: 'post' },
]

/** The reel-root JSON files the rules read: register.ts reads these, and only when the reel folder lists them. */
export const JSON_FILES: readonly string[] = [...new Set(STAGES.flatMap(s =>
  'json' in s.rule ? [s.rule.json, ...(s.rule.or ? [s.rule.or.json] : [])] : []))]

/** The files in renders/ ffprobe is asked about: a master by name, more than 0 bytes. */
export const masterCandidates = (r: ReelIn): Entry[] => filesIn(r, 'renders').filter(x => MASTER.test(x.name) && x.size > 0)

/** ffprobe's answer: output naming a video stream = video; ran fine with none = novideo; failed = unknown. */
export const probeOf = (r: { exitCode: number; stdout: string }): Probe =>
  /video/.test(r.stdout) ? 'video' : r.exitCode === 0 ? 'novideo' : 'unknown'

export function isDone(rule: Rule, r: ReelIn): boolean {
  if ('never' in rule) return false
  if ('json' in rule) {
    const j = r.json[rule.json]
    if (!j || j.status === 'unreadable') return false
    if (j.status === 'missing' && (r.lists.root.status !== 'ok'
      || r.lists.root.value.some(x => x.name === rule.json))) return false
    return (j.status === 'ok' && isRecord(j.value) && rule.when(j.value)) || !!rule.or && isDone(rule.or, r)
  }
  return filesIn(r, rule.in).some(x => rule.match.test(x.name)
    && (!rule.applied || rule.applied.some(p => (mtimeAt(r, p) ?? -Infinity) >= x.mtimeMs))
    && (!rule.video || (x.size > 0 && r.probe[x.name] !== 'novideo')))
    || !!rule.or && filesIn(r, rule.or.in).some(x => rule.or!.match.test(x.name))
}

// ---------------------------------------------------------------- sends ------

/** The Send files (H-UI-2; Beat Map and Sketches added by H-S15a-7), flat at the reel root, each its board's;
 *  `downstream` (relative to the reel) is what Claude makes from it: a Send older than its newest downstream file has
 *  been acted on. A Send with no downstream file stays open until its ack. */
export const SENDS: readonly { file: string; board: BoardId; downstream: readonly string[] }[] = [
  { file: 'cut-selection.json', board: 'cut', downstream: ['work/cuts.json', 'work/edl.json'] },
  { file: 'tweak-selection.json', board: 'tweak', downstream: ['work/cuts.json', 'work/edl.json'] },   // a re-cut
  { file: 'beat-map-selection.json', board: 'beatmap', downstream: ['sketches.state.json'] },   // reel-canvas-build beat-map.md
  { file: 'sketches-selection.json', board: 'sketches', downstream: [] },
  { file: 'sound-selection.json', board: 'sound', downstream: [] },
  { file: 'grade-selection.json', board: 'grade', downstream: [] },
]
export type OpenSend = { file: string; board: BoardId; mtimeMs: number }

const mtimeAt = (r: ReelIn, rel: string): number | undefined => {
  const i = rel.indexOf('/'), f = (i < 0 ? 'root' : rel.slice(0, i)) as Folder, n = i < 0 ? rel : rel.slice(i + 1)
  return filesIn(r, f).find(x => x.name === n)?.mtimeMs
}

/** A Send is open when it is newer than the workspace's baseline, than its ack (`acked['<reel>/<file>']`, S15b writes
 *  it) and than its newest downstream file. No baseline yet: nothing is open. Newest first. */
export function openSends(r: ReelIn, baseline: number | undefined, acked: Record<string, unknown>): OpenSend[] {
  if (baseline === undefined) return []
  return SENDS.flatMap(s => {
    const at = mtimeAt(r, s.file)
    if (at === undefined || at <= baseline) return []
    const ack = acked[`${r.name}/${s.file}`]
    if (typeof ack === 'number' && at <= ack) return []
    const down = Math.max(-Infinity, ...s.downstream.map(d => mtimeAt(r, d) ?? -Infinity))
    return at > down ? [{ file: s.file, board: s.board, mtimeMs: at }] : []
  }).sort((a, b) => b.mtimeMs - a.mtimeMs)
}

// ---------------------------------------------------------------- reel -------

export const IDLE_MS = 7 * 86_400_000

export type Reel = {
  name: string
  activity?: number    // the newest file mtime in the reel, raw/, work/ and renders/ (none = no activity)
  idle: boolean        // no activity in the last 7 days
  done: boolean[]      // per STAGES
  cur: number          // the first stage not done, Grade skipped
  sends: OpenSend[]
  unread: boolean      // a listing or a JSON the rules read could not be read
}

export function reelOf(r: ReelIn, now: number, baseline: number | undefined, acked: Record<string, unknown>): Reel {
  const times = FOLDERS.flatMap(f => filesIn(r, f).map(x => x.mtimeMs))
  const activity = times.length ? Math.max(...times) : undefined
  const done = STAGES.map(s => isDone(s.rule, r))
  return {
    name: r.name, activity, idle: activity === undefined || now - activity > IDLE_MS, done,
    cur: STAGES.findIndex((s, i) => !s.optional && !done[i]),   // Post is never done, so always found
    sends: openSends(r, baseline, acked),
    unread: [...Object.values(r.lists), ...Object.values(r.json)].some(x => x.status === 'unreadable'),
  }
}

// ---------------------------------------------------------------- labels -----

/** Action id -> button label and the phrase it sends as the person's own message (`<reel>`, `<board>` filled in).
 *  Frozen wording. No phrase: the pane acts itself
 *  (Switch reel asks, Cockpit opens the pane). Labels 22 characters at most, "Create" never "Make", no long dashes. */
export const LABELS: Readonly<Record<ActionId, { label: string; phrase?: string }>> = {
  start: { label: 'Start a reel', phrase: 'Start a new reel in the editor' },
  next: { label: "What's next?", phrase: "What's next in editing <reel>?" },
  hub: { label: 'Editor hub', phrase: 'Open my editor hub' },
  switch: { label: 'Switch reel' },
  record: { label: 'Check my setup', phrase: "I'm about to record <reel>" },
  cut: { label: 'Open Cut Board', phrase: 'Open my Cut Board for <reel>' },
  tweak: { label: 'Open Tweak Board', phrase: 'Open my Tweak Board for <reel>' },
  beatmap: { label: 'Open Beat Map', phrase: 'Open my Beat Map for <reel>' },
  sketches: { label: 'Open Sketches', phrase: 'Open my Sketches for <reel>' },
  sound: { label: 'Open Sound Board', phrase: 'Open my Sound Board for <reel>' },
  grade: { label: 'Open Grade Board', phrase: 'Open my Grade Board for <reel>' },
  master: { label: 'Render the master', phrase: 'Render the master for <reel>' },
  post: { label: 'Write my caption', phrase: 'Write the post caption for <reel>' },
  send: { label: 'Use my Send', phrase: 'Go ahead with my <board> Send for <reel>' },
  cockpit: { label: 'Cockpit' },
}
/** The pane footer's autostart toggle (store only, no phrase). */
export const TOGGLE = { off: "Don't auto-open here", on: 'Auto-open here' } as const

/** A phrase with its slots filled; with no reel, " <reel>" and " for <reel>" drop out. */
export function fill(phrase: string, reel?: string, board?: string): string {
  const p = board ? phrase.replace(/<board>/g, () => board) : phrase
  return reel ? p.replace(/<reel>/g, () => reel) : p.replace(/ (for )?<reel>/g, '')
}

/** An action as a button: its label and its filled phrase (the Send's board for `send`). */
export function act(id: ActionId, v: { reel?: string; send?: OpenSend }): { label: string; phrase?: string } {
  const a = LABELS[id]
  return a.phrase ? { label: a.label, phrase: fill(a.phrase, v.reel, v.send && BOARD_NAME[v.send.board]) } : { label: a.label }
}

// ---------------------------------------------------------------- view -------

export type Input = {
  now: number
  videos: Read<Entry[]>   // the videos folder's listing
  reels: ReelIn[]
  baseline?: number       // $.store editorBaseline for this workspace
  acked: Record<string, unknown>   // $.store editorAcked
  configFound: boolean    // editor/editor.config.json is there (autostart)
}

export type View = {
  state: 'nothing' | 'yours' | 'claude'
  reel?: string
  done: boolean[]
  cur: number              // the current stage, -1 with no reel
  board?: BoardId          // the current stage's board
  send?: OpenSend          // the newest open Send (Claude's move)
  main: ActionId
  eyebrow: string; head: string; sub: string[]
  baton: string
  pill: string             // the band's one-line stepper words
  alt: string              // the stepper's words
  latest: string[]         // Switch reel: the 3 reels with the newest activity, idle included
}

export const BATON_NONE = 'Editor: no reel in progress'
export const BATON_UNREAD = "Editor: couldn't read your reels"

/** A name for one line: at most `max` characters, "..." on the end when cut. */
export const clip = (s: string, max = 24) => (s.length <= max ? s : `${s.slice(0, max - 3)}...`)

/** The three states (Cockpit spec): nothing in the edit, Claude's move (an open Send), your move. The current reel is
 *  the one Switch reel picked while it still exists, else the newest reel that is not idle, else none. */
export function cockpit(input: Input, picked?: string): View {
  const reels = input.reels.map(r => reelOf(r, input.now, input.baseline, input.acked))
  const byActivity = [...reels].sort((a, b) => (b.activity ?? -1) - (a.activity ?? -1) || a.name.localeCompare(b.name))
  const latest = byActivity.slice(0, 3).map(r => r.name)
  const cur = reels.find(r => r.name === picked) ?? byActivity.find(r => !r.idle)
  if (!cur) {
    const bad = input.videos.status === 'unreadable'
    return { state: 'nothing', done: STAGES.map(() => false), cur: -1, main: 'start', latest,
      eyebrow: 'EDITOR', head: 'Nothing in the edit',
      sub: bad ? ["I couldn't read your videos folder.", 'It may still be syncing.'] : ['Drop a recording in and Claude starts the cut.'],
      baton: bad ? BATON_UNREAD : BATON_NONE, pill: 'No reel in the edit', alt: 'No reel in progress' }
  }
  const stage = STAGES[cur.cur]!, board = stage.board, send = cur.sends[0], name = clip(cur.name)
  const doneNames = STAGES.filter((_, i) => cur.done[i]).map(s => s.name)
  const alt = `Editing progress: ${doneNames.length ? `${doneNames.join(', ')} done; ` : ''}now ${stage.name}`
  const note = cur.unread ? ["Some files couldn't be read (may be syncing)."] : []
  if (send) {
    const b = BOARD_NAME[send.board]
    return { state: 'claude', reel: cur.name, done: cur.done, cur: cur.cur, board, send, main: 'send', latest, alt,
      eyebrow: `${name} · CLAUDE'S MOVE`, head: `${b} sent`, sub: ['Claude picks it up when you say go.', 'Nothing happens until then.', ...note],
      baton: `Claude's move: ${b} Send (${cur.name})`, pill: `${name} · ${b} sent` }
  }
  return { state: 'yours', reel: cur.name, done: cur.done, cur: cur.cur, board, main: stage.action, latest, alt,
    eyebrow: `${name} · YOUR MOVE`, head: stage.head, sub: [stage.sub, ...note],
    baton: `Your move: ${board ? BOARD_NAME[board] : stage.baton} (${cur.name})`, pill: `${name} · ${stage.short} · your move` }
}
