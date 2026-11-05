// Synthetic workspace trees for the Cockpit tests: paths, sizes and mtimes only. No media; the only file contents are
// the tiny JSON the stage rules read. Keys are relative to the workspace root; a key ending in `/` is a folder with
// nothing in it (or a link, with `link`); every other folder is implied by the files under it.
import { ok, missing, parseJson, reelNames, filesIn, JSON_FILES, FOLDERS, type Entry, type Input, type ReelIn, type Probe, type Read } from '../../hooks/mod/logic'

export const NOW = Date.UTC(2026, 10, 4, 12)
export const DAY = 86_400_000
export const ROOT = 'D:/Clients/Reel Studio'
export type F = { at?: number; size?: number; text?: string; link?: true; busy?: true }
export type Tree = Record<string, F>

/** A file changed `days` ago (`text`: its JSON content; `size` 0 for an empty file). */
export const f = (days = 1, o: Omit<F, 'at'> = {}): F => ({ at: NOW - days * DAY, size: o.text?.length ?? 1000, ...o })
export const json = (days: number, value: unknown): F => f(days, { text: JSON.stringify(value) })
export const dir: F = {}
/** The reel's own files, under `videos/<name>/` (or another videos folder). */
export const reel = (name: string, files: Record<string, F>, videos = 'videos'): Tree =>
  Object.fromEntries(Object.entries(files).map(([k, v]) => [`${videos}/${name}/${k}`, v]))
export const CONFIG_FILE: Tree = { 'editor/editor.config.json': { at: NOW - 30 * DAY, text: '{"schema":1,"paths":{"editor":"editor","videos":"videos"}}' } }

/** The direct children of a folder as $.fs.list gives them, or undefined when the tree has no such folder. */
export function list(tree: Tree, folder: string): Entry[] | undefined {
  const pre = `${folder}/`, out = new Map<string, Entry>()
  for (const [k, v] of Object.entries(tree)) {
    if (!k.startsWith(pre)) continue
    const rest = k.slice(pre.length), i = rest.indexOf('/'), name = i < 0 ? rest : rest.slice(0, i)
    if (!name) continue
    const isDir = i >= 0, isLeaf = !isDir || i === rest.length - 1
    if (isLeaf && v.link) out.set(name, { name, kind: 'other', size: 0, mtimeMs: 0, isLink: true })
    else if (!out.has(name)) out.set(name, isDir ? { name, kind: 'dir', size: 0, mtimeMs: 0, isLink: false }
      : { name, kind: 'file', size: v.size ?? 1000, mtimeMs: v.at ?? NOW, isLink: false })
  }
  return out.size || Object.keys(tree).some(k => k === pre) ? [...out.values()] : undefined
}

const listed = (tree: Tree, folder: string): Read<Entry[]> => {
  const l = list(tree, folder)
  return l ? ok(l) : missing()
}

/** One reel gathered as register.ts gathers it (its listings, the listed JSON files parsed, ffprobe's answers). */
export function reelIn(tree: Tree, name: string, probe: Record<string, Probe> = {}, videos = 'videos'): ReelIn {
  const base = `${videos}/${name}`
  const lists = Object.fromEntries(FOLDERS.map(x => [x, listed(tree, x === 'root' ? base : `${base}/${x}`)])) as ReelIn['lists']
  const r: ReelIn = { name, lists, json: {}, probe }
  for (const n of JSON_FILES) {
    const at = tree[`${base}/${n}`], here = filesIn(r, 'root').some(x => x.name === n)
    r.json[n] = !here || !at ? missing() : at.busy ? { status: 'unreadable', reason: 'EBUSY' } : parseJson(ok(at.text ?? ''))
  }
  return r
}

/** The whole Input for the pure tests. */
export function inputOf(tree: Tree, o: { baseline?: number; acked?: Record<string, number>; probe?: Record<string, Probe>; videos?: string } = {}): Input {
  const videos = listed(tree, o.videos ?? 'videos')
  return { now: NOW, videos, reels: reelNames(videos).map(n => reelIn(tree, n, o.probe, o.videos)), baseline: o.baseline,
    acked: o.acked ?? {}, configFound: !!tree['editor/editor.config.json'] }
}

// ---- REEL-018 / REEL-020: the stage-relevant shape of two real reels made before 0.2.0 (old per-board subfolders),
// with the gotchas. Names generic past the reel id. Neither uses a 0.2.0 artifact name.
const OLD = 28   // days ago: both are idle now
export const REEL_018: Tree = reel('reel-018', {
  'Clock - 1.1x - 10.07.26.json': f(OLD),
  'REEL-018 Screen Takes - Shot List - 10.07.26.md': f(OLD),
  'beatmap/beatmap.state.json': json(OLD, { saved_at: '2026-10-08', current: {}, sent: null, sent_at: null }),
  'beatmap/beatmap.state.prev.json': f(OLD),
  'beatmap/index.html': f(OLD),
  'cut/board/selection.json': json(OLD, { v: 1, reel: 'reel-018', lines: [], saved_at: '2026-10-07' }),
  'cut/board/selection-board-10.07.26.json': f(OLD),   // a dated Send copy
  'cut/board/cut.state.json': f(OLD),
  'cut/board/cut.state.prev.json': f(OLD),
  'cut/work/edl.json': f(OLD),
  'cut/work/segments.json': f(OLD),
  'raw/REEL-018 take1 - Raw - 10.06.26.mp4': f(OLD + 1),
  'raw/REEL-018 screen S1 step1 - Raw - 10.07.26.mp4': f(OLD),
  'raw/REEL-018 Master Raw (audio gap-padded) - 10.07.26.mov': f(OLD),   // "Master" in raw/: never the master
  'renders/REEL-018 Lock 110 UHD - 10.07.26.mov': f(OLD),
  'renders/REEL-018 Master - 10.07.26.mov': f(OLD),
  'renders/REEL-018 Master - 10.07.26.mp4': f(OLD),   // the ruled final-master name: lights Master
  'renders/REEL-018 Master mastered - 10.08.26.mov': f(OLD),
  'renders/REEL-018 Master mastered - 10.08.26.mp4': f(OLD),
  'renders/review/REEL-018 Master - 10.07.26.mp4': f(OLD),   // a review duplicate, one folder down
  'renders/review/REEL-018 EDIT review - 10.07.26.mp4': f(OLD),
  'resolve/grade/A-match.cube': f(OLD),
  'sketches/batch.py': f(OLD),
  'sketches/rough-reel.mp4': f(OLD),
  'sketches/batch/sketch-open.mp4': f(OLD),
  'sound/selection-sfx-bed-stops-10.07.26.json': f(OLD),   // a dated Send copy
  'sound/board/selection.json': json(OLD, { project: 'reel-018', cues: [] }),
  'sound/board/sound.state.json': f(OLD),
  'sound/board/media/locked.mp4': f(OLD),   // "locked" by name, not a motion lock
})

export const REEL_020: Tree = reel('reel-020', {
  'beatmap/beatmap.state.json': json(OLD - 7, { saved_at: '2026-10-15', current: {}, sent: true, sent_at: '2026-10-15T12:44:09.046Z' }),
  'beatmap/selection.json': json(OLD - 7, { reel: 'reel-020', board: 'beatmap', beats: [] }),
  'cut/segments.json': f(OLD - 7),
  'cut/renders/REEL-020 Lock 1.075x - 4K - 10.15.26.mov': f(OLD - 7),
  'raw/REEL-020 avatar take - 1080 - 10.15.26.mp4': f(OLD - 7),
  'raw/REEL-020 screens - 4K - 10.15.26.mp4': f(OLD - 7),
  'renders/REEL-020 Master - 10.15.26.mov': f(OLD - 7),   // .mov: not the ruled name
  'renders/REEL-020 Master mastered - 10.15.26.mp4': f(OLD - 7),   // "mastered": not the ruled name
  'renders/_master-audio.wav': f(OLD - 7),
  'sketches/batch.LOCKED-10.15.26.py': f(OLD - 7),
  'sketches/hook/canvas.LOCKED-10.15.26.html': f(OLD - 7),
  'sketches/_frames/REEL-020 Rough Reel - LOCKED - 10.15.26.mp4': f(OLD - 7),
  'sound/board/selection.json': json(OLD - 7, { project: 'reel-020', cues: [] }),
  'sound/board/media/locked.mp4': f(OLD - 7),
})

// ---- 0.2.0-named reels walking every stage (each one step further than the last), all active.
const R1 = { 'raw/take1.mp4': f(5) }
const R2 = { ...R1, 'work/edl.json': f(4) }
const R3 = { ...R2, 'tweak-selection.json': f(3) }
const R4 = { ...R3, 'beat-map.state.json': json(2, { sent_at: '2026-11-02T10:00:00Z' }) }
const R5 = { ...R4, 'sketches.state.json': json(2, { locked_at: '2026-11-02T11:00:00Z' }) }
const R6 = { ...R5, 'sound-selection.json': f(1) }
const R7 = { ...R6, 'renders/r7 Master - 11.03.26.mp4': f(1) }
/** name, files, the current stage's index, the stage names done. */
export const WALK: [string, Record<string, F>, number][] = [
  ['r0', { 'notes.md': f(1), 'raw/': dir }, 0],
  ['r1', R1, 1],
  ['r2', R2, 2],
  ['r3', R3, 3],
  ['r4', R4, 4],
  ['r5', R5, 5],
  ['r6', R6, 7],   // Grade skipped: Master is next
  ['r7', R7, 8],
]
export const walk = (i: number): Tree => ({ ...CONFIG_FILE, ...reel(WALK[i]![0], WALK[i]![1]) })
