import { test, expect } from 'claude-code/testing'
import {
  normPath, folderKey, homeDir, videosDir, reelNames, isReelName, reelOf, cockpit, openSends, probeOf, act, fill, parseJson,
  ok, missing, unreadable, STAGES, LABELS, TOGGLE, BOARDS, BATON_NONE, BATON_UNREAD, MASTER, type ActionId, type Entry,
} from '../hooks/mod/logic'
import { NOW, DAY, f, json, dir, reel, inputOf, reelIn, list, REEL_018, REEL_020, WALK, walk, CONFIG_FILE, type Tree } from './fixtures/reels'
import { MERGED_REEL, MERGED_STEPS, mergedReel } from './fixtures/merged-reel'

const view = (tree: Tree, o: Parameters<typeof inputOf>[1] = {}, picked?: string) => cockpit(inputOf(tree, o), picked)
const reelView = (tree: Tree, name: string, o: { baseline?: number; acked?: Record<string, number>; probe?: any } = {}) =>
  reelOf(reelIn(tree, name, o.probe), NOW, o.baseline, o.acked ?? {})
const names = (done: boolean[]) => STAGES.filter((_, i) => done[i]).map(s => s.name)

test('Record: RAW.mp4 at the top, one raw video or several raw videos; no take stays at Record', () => {
  for (const files of [{ 'RAW.mp4': f(1) }, { 'raw/x.mp4': f(1) }, { 'raw/x.mp4': f(1), 'raw/y.MOV': f(1) }]) {
    const r = reelView(reel('new', files), 'new')
    expect(r.done[0]).toBe(true)
    expect(STAGES[r.cur]!.name).toBe('Cut')
  }
  expect(reelView({ 'videos/new/': dir }, 'new').done[0]).toBe(false)
  expect(reelView(reel('new', { 'RAW.mp4.prev': f(1), 'raw/x.mp4.tmp': f(1) }), 'new').done[0]).toBe(false)
})

test('paths: normPath, folderKey and homeDir', () => {
  expect(normPath('C:\\Users\\coach\\ws\\')).toBe('C:/Users/coach/ws')
  expect(normPath('/c/Users/coach')).toBe('C:/Users/coach')
  expect(folderKey('D:\\Clients\\Reel Studio')).toBe('d:/clients/reel studio')
  expect(homeDir({ USERPROFILE: 'C:\\Users\\coach' })).toBe('C:/Users/coach')
  expect(homeDir({})).toBeUndefined()
})

test('config: paths.videos, else videos; a missing, broken or unsafe value falls back to videos', () => {
  const cfg = (v: unknown) => ok({ paths: { videos: v } })
  expect(videosDir(missing())).toBe('videos')
  expect(videosDir(unreadable('EBUSY'))).toBe('videos')
  expect(videosDir(parseJson(ok('{not json')))).toBe('videos')
  expect(videosDir(ok(null))).toBe('videos')
  expect(videosDir(ok({ paths: 'x' }))).toBe('videos')
  expect(videosDir(cfg('clips'))).toBe('clips')
  expect(videosDir(cfg('media\\reels'))).toBe('media/reels')
  // read as board_sync.py reads it (PurePosixPath): empty and . segments drop out
  expect(videosDir(cfg('./clips'))).toBe('clips')
  expect(videosDir(cfg('clips/'))).toBe('clips')
  expect(videosDir(cfg('a//b'))).toBe('a/b')
  expect(videosDir(cfg('a/./b'))).toBe('a/b')
  for (const bad of ['', '/abs', '/x', '//x', 'C:/x', 'C:/videos', 'c:videos', '../x', '../videos', 'a/../b', '.', './', 5, null])
    expect(videosDir(cfg(bad))).toBe('videos')
})

test('reels: real folders with a name a board can open; junk, dot folders, links and files are not reels', () => {
  const tree: Tree = {
    'videos/reel-021/raw/a.mp4': f(1), 'videos/My Reel 2/': dir, 'videos/a_b.c/': dir,
    'videos/.hidden/': dir, 'videos/ends./': dir, 'videos/ends /': dir, 'videos/bad*name/': dir, [`videos/${'x'.repeat(121)}/`]: dir,
    'videos/-dash/': dir, 'videos/linked/': { link: true }, 'videos/loose-file.mp4': f(1),
  }
  expect(reelNames(ok(list(tree, 'videos')!))).toEqual(['My Reel 2', 'a_b.c', 'reel-021'])
  expect(isReelName('x'.repeat(120))).toBe(true)
  expect(reelNames(missing())).toEqual([])
  expect(reelNames(unreadable('EBUSY'))).toEqual([])
})

test('REEL-018 and REEL-020 shapes (old per-board folders): discovered without a throw; only Record, and Master for REEL-018 by its ruled name', () => {
  const tree = { ...REEL_018, ...REEL_020 }
  const input = inputOf(tree)
  expect(input.reels.map(r => r.name)).toEqual(['reel-018', 'reel-020'])
  const r18 = reelOf(input.reels[0]!, NOW, undefined, {}), r20 = reelOf(input.reels[1]!, NOW, undefined, {})
  expect(names(r18.done)).toEqual(['Record', 'Master'])
  expect(names(r20.done)).toEqual(['Record'])
  expect([r18.cur, r20.cur]).toEqual([1, 1])   // Cut: no 0.2.0 cut artifact in either
  expect([r18.idle, r20.idle]).toEqual([true, true])
  expect(names(reelView(REEL_018, 'reel-018', { probe: { 'REEL-018 Master - 10.07.26.mp4': 'video' } }).done)).toEqual(['Record', 'Master'])
  expect(names(reelView(REEL_018, 'reel-018', { probe: { 'REEL-018 Master - 10.07.26.mp4': 'novideo' } }).done)).toEqual(['Record'])
  // Old Send files never open a Send, whatever the baseline.
  expect(reelView(tree, 'reel-018', { baseline: 0 }).sends).toEqual([])
  expect(reelView(tree, 'reel-020', { baseline: 0 }).sends).toEqual([])
  const v = cockpit(input)
  expect(v.state).toBe('nothing')   // both idle, none picked
  expect(v.latest).toEqual(['reel-020', 'reel-018'])
  expect(cockpit(input, 'reel-018').baton).toBe('Your move: Cut Board (reel-018)')
})

test('stages: 0.2.0-named reels walk every stage; the current one is the first not done, Grade skipped', () => {
  for (const [name, , cur] of WALK) {
    const r = reelView(walk(WALK.findIndex(w => w[0] === name)), name)
    expect([name, r.cur]).toEqual([name, cur])
    expect(r.done.slice(0, cur).filter((d, i) => !d && !STAGES[i]!.optional)).toEqual([])
    expect(r.done[6]).toBe(false)   // no Grade Send in the walk
  }
  // an empty reel folder is a reel at Record, with no activity
  const empty = reelView({ 'videos/new/': dir }, 'new')
  expect([empty.cur, empty.activity, empty.idle]).toEqual([0, undefined, true])
})

test('Grade is optional: never current, never blocks Master; its Send marks it done', () => {
  const files = WALK[6]![1]
  expect(reelView(reel('g', files), 'g').cur).toBe(7)
  const graded = reelView(reel('g', { ...files, 'grade-selection.json': f(1) }), 'g')
  expect([graded.done[6], graded.cur]).toEqual([true, 7])
  expect(reelView(reel('g', { ...WALK[7]![1] }), 'g').cur).toBe(8)
})

test('Master: the ruled name directly in renders/, .mp4, more than 0 bytes, not "no video"; nothing else lights it', () => {
  const base = WALK[6]![1]
  const master = (files: Record<string, any>, probe: any = {}) => reelView(reel('m', { ...base, ...files }), 'm', { probe }).done[7]
  expect(master({ 'renders/m Master - 11.03.26.mp4': f(1) })).toBe(true)
  expect(master({ 'renders/M MASTER - 11.03.26.MP4': f(1) })).toBe(true)
  expect(master({ 'renders/Any Name Master - 01.02.26.mp4': f(1) }, { 'Any Name Master - 01.02.26.mp4': 'video' })).toBe(true)
  expect(master({ 'renders/m Master - 11.03.26.mp4': f(1) }, { 'm Master - 11.03.26.mp4': 'unknown' })).toBe(true)
  expect(master({ 'renders/m Master - 11.03.26.mp4': f(1) }, { 'm Master - 11.03.26.mp4': 'novideo' })).toBe(false)
  expect(master({ 'renders/m Master - 11.03.26.mp4': f(1, { size: 0 }) })).toBe(false)
  expect(master({ 'renders/m Master - 11.03.26.mov': f(1) })).toBe(false)
  expect(master({ 'renders/m Master mastered - 11.03.26.mp4': f(1) })).toBe(false)
  expect(master({ 'renders/master-x.mp4': f(1) })).toBe(false)
  expect(master({ 'work/renders/master-x.mp4': f(1), 'work/renders/m Master - 11.03.26.mp4': f(1) })).toBe(false)
  expect(master({ 'raw/m Master - 11.03.26.mp4': f(1) })).toBe(false)
  expect(master({ 'renders/review/m Master - 11.03.26.mp4': f(1) })).toBe(false)
  expect(master({ 'renders/m Master - 11.03.26.mp4.tmp': f(1) })).toBe(false)
  expect(MASTER.test('REEL-018 Master - 10.07.26.mp4')).toBe(true)
})

test('beat map and motion: the state JSON must parse to an object and carry sent_at / locked_at; an unreadable one is not done', () => {
  const at = (files: Record<string, any>) => reelView(reel('b', { ...WALK[3]![1], ...files }), 'b')
  expect(at({ 'beat-map.state.json': json(1, { sent_at: null }) }).done[3]).toBe(false)
  expect(at({ 'beat-map.state.json': json(1, { sent: true }) }).done[3]).toBe(false)
  expect(at({ 'beat-map.state.json': json(1, [1]) }).done[3]).toBe(false)
  expect(at({ 'beat-map.state.json': f(1, { text: '{"sent_at": "x"' }) }).done[3]).toBe(false)
  const busy = at({ 'beat-map.state.json': f(1, { busy: true }) })
  expect([busy.done[3], busy.unread]).toEqual([false, true])
  expect(at({ 'beat-map.state.json': json(1, { sent_at: 0 }) }).done[3]).toBe(true)
  expect(at({ 'beat-map.state.json': json(1, { sent_at: 'x' }), 'sketches.state.json': json(1, { locked_at: '' }) }).done[4]).toBe(false)
  expect(at({ 'beatmap.state.json': json(1, { sent_at: 'x' }) }).done[3]).toBe(false)   // the old name
})

test('*.tmp and *.prev are never artifacts and never activity', () => {
  const r = reelView(reel('t', { 'raw/take.mp4': f(20), 'sound-selection.json.tmp': f(0), 'beat-map.state.json.prev': f(0), 'work/edl.json.tmp': f(0) }), 't')
  expect(r.cur).toBe(1)
  expect(r.done[5]).toBe(false)
  expect(r.activity).toBe(NOW - 20 * DAY)
  expect(r.idle).toBe(true)
})

test('idle: newest file in the reel, raw/, work/, renders/ older than 7 days; the current reel is the newest active one or the picked one', () => {
  const tree: Tree = {
    ...reel('old', { 'raw/a.mp4': f(8) }), ...reel('recent', { 'raw/a.mp4': f(6) }), ...reel('newest', { 'raw/a.mp4': f(10), 'renders/x.txt': f(2) }),
    ...reel('deep', { 'raw/a.mp4': f(30), 'sketches/new.html': f(0) }),   // a subfolder the rules don't list: not activity
  }
  expect(reelView(tree, 'old').idle).toBe(true)
  expect(reelView(tree, 'recent').idle).toBe(false)
  expect(reelView(tree, 'newest').activity).toBe(NOW - 2 * DAY)
  expect(reelView(tree, 'deep').idle).toBe(true)
  expect(view(tree).reel).toBe('newest')
  expect(view(tree, {}, 'old').reel).toBe('old')   // picked, though idle
  expect(view(tree, {}, 'gone').reel).toBe('newest')   // a pick that no longer exists is ignored
  expect(view(tree).latest).toEqual(['newest', 'recent', 'old'])
  expect(view(reel('old', { 'raw/a.mp4': f(8) })).state).toBe('nothing')
})

test('open Sends: newer than the baseline, the ack and the downstream file; no baseline, nothing open; newest first', () => {
  const B = NOW - 10 * DAY
  const base = { 'raw/a.mp4': f(12), 'work/edl.json': f(5) }
  const sends = (files: Record<string, any>, acked: Record<string, number> = {}, baseline: number | null = B) =>
    openSends(reelIn(reel('s', { ...base, ...files }), 's'), baseline ?? undefined, acked).map(s => s.file)
  expect(sends({ 'cut-selection.json': f(3) })).toEqual(['cut-selection.json'])
  expect(sends({ 'cut-selection.json': f(6) })).toEqual([])   // the EDL is newer: acted on
  expect(sends({ 'tweak-selection.json': f(3) })).toEqual(['tweak-selection.json'])
  expect(sends({ 'tweak-selection.json': f(3), 'work/cuts.json': f(2) })).toEqual([])   // re-cut since
  expect(sends({ 'sound-selection.json': f(11) })).toEqual([])   // older than the baseline
  expect(sends({ 'sound-selection.json': f(3) }, {}, null)).toEqual([])   // no baseline yet
  expect(sends({ 'sound-selection.json': f(3) }, { 's/sound-selection.json': NOW - 3 * DAY })).toEqual([])   // acked
  expect(sends({ 'sound-selection.json': f(1) }, { 's/sound-selection.json': NOW - 3 * DAY })).toEqual(['sound-selection.json'])   // sent again
  expect(sends({ 'sound-selection.json': f(3), 'grade-selection.json': f(1) })).toEqual(['grade-selection.json', 'sound-selection.json'])
  expect(sends({ 'sound-selection.json.tmp': f(1) })).toEqual([])
})

const B = NOW - 10 * DAY
const newSends = (files: Record<string, any>, acked: Record<string, number> = {}) =>
  openSends(reelIn(reel('s', { 'raw/a.mp4': f(12), ...files }), 's'), B, acked).map(s => [s.file, s.board])

test('Beat Map Send (H-S15a-7): open after the baseline; closed by its ack, or by a newer sketches.state.json', () => {
  const open = [['beat-map-selection.json', 'beatmap']]
  expect(newSends({ 'beat-map-selection.json': f(3) })).toEqual(open)
  expect(newSends({ 'beat-map-selection.json': f(11) })).toEqual([])   // older than the baseline
  expect(newSends({ 'beat-map-selection.json': f(3) }, { 's/beat-map-selection.json': NOW - 3 * DAY })).toEqual([])   // acked
  expect(newSends({ 'beat-map-selection.json': f(3), 'sketches.state.json': json(2, {}) })).toEqual([])   // acted on
  expect(newSends({ 'beat-map-selection.json': f(3), 'sketches.state.json': json(4, {}) })).toEqual(open)   // sketches older
})

test('Sketches Send (H-S15a-7): open after the baseline; no downstream file, so it stays open until its ack', () => {
  const open = [['sketches-selection.json', 'sketches']]
  expect(newSends({ 'sketches-selection.json': f(3) })).toEqual(open)
  expect(newSends({ 'sketches-selection.json': f(11) })).toEqual([])   // older than the baseline
  expect(newSends({ 'sketches-selection.json': f(3), 'sketches.state.json': json(1, {}), 'work/edl.json': f(1), 'sound-selection.json.tmp': f(1) }))
    .toEqual(open)   // newer files elsewhere never close it
  expect(newSends({ 'sketches-selection.json': f(3) }, { 's/sketches-selection.json': NOW - 3 * DAY })).toEqual([])   // acked
})

test("three states, their hero, main move and baton", () => {
  const none = view(CONFIG_FILE)
  expect([none.state, none.main, none.baton, none.head, none.cur]).toEqual(['nothing', 'start', BATON_NONE, 'Nothing in the edit', -1])
  expect(cockpit({ ...inputOf({}), videos: unreadable('EBUSY') }).baton).toBe(BATON_UNREAD)
  expect(cockpit({ ...inputOf({}), videos: unreadable('EBUSY') }).sub[0]).toBe("I couldn't read your videos folder.")
  const expected: [number, ActionId, string][] = [
    [0, 'record', 'Your move: record (r0)'], [1, 'cut', 'Your move: Cut Board (r1)'], [2, 'tweak', 'Your move: Tweak Board (r2)'],
    [3, 'beatmap', 'Your move: Beat Map (r3)'], [4, 'sketches', 'Your move: Sketches (r4)'], [5, 'sound', 'Your move: Sound Board (r5)'],
    [6, 'master', 'Your move: render the master (r6)'], [7, 'post', 'Your move: post (r7)'],
  ]
  for (const [i, main, baton] of expected) {
    const v = view(walk(i))
    expect([v.state, v.main, v.baton]).toEqual(['yours', main, baton])
    expect(v.eyebrow).toBe(`${WALK[i]![0]} · YOUR MOVE`)
  }
  const sent = view({ ...walk(5), ...reel('r5', { 'sound-selection.json': f(0.5) }) }, { baseline: NOW - 3 * DAY })
  expect([sent.state, sent.main, sent.baton, sent.head, sent.cur]).toEqual(['claude', 'send', "Claude's move: Sound Board Send (r5)", 'Sound Board sent', 7])
  expect(act('send', sent)).toEqual({ label: 'Use my Send', phrase: 'Go ahead with my Sound Board Send for r5' })
  expect(view(walk(3)).board).toBe('beatmap')
  expect(view(walk(0)).board).toBeUndefined()
})

test('missing config: defaults, never a throw; a custom videos folder is followed', () => {
  expect(view(reel('r1', WALK[1]![1])).reel).toBe('r1')
  const clips: Tree = { 'editor/editor.config.json': { text: '{"paths":{"videos":"clips"}}' }, ...reel('c1', { 'raw/a.mp4': f(1) }, 'clips') }
  expect(view(clips, { videos: videosDir(parseJson(ok(clips['editor/editor.config.json']!.text!))) }).reel).toBe('c1')
})

test('ffprobe answers: a video stream, none, or a failure', () => {
  expect(probeOf({ exitCode: 0, stdout: 'video\n' })).toBe('video')
  expect(probeOf({ exitCode: 0, stdout: '' })).toBe('novideo')
  expect(probeOf({ exitCode: 1, stdout: '' })).toBe('unknown')
})

test('phrases: slots filled; with no reel " for <reel>" drops out', () => {
  expect(act('next', { reel: 'reel-021' }).phrase).toBe("What's next in editing reel-021?")
  expect(act('next', {}).phrase).toBe("What's next in editing?")
  expect(act('cut', {}).phrase).toBe('Open my Cut Board')
  expect(act('record', { reel: 'reel-021' }).phrase).toBe("I'm about to record reel-021")
  expect(act('switch', { reel: 'x' })).toEqual({ label: 'Switch reel' })
  expect(fill('a <reel> b', 'r$&')).toBe('a r$& b')
})

test('LABELS guard: every label 22 chars or fewer, never "Make", no long dash; every action the view uses exists', () => {
  const labels = [...Object.values(LABELS).map(a => a.label), TOGGLE.on, TOGGLE.off]
  for (const l of labels) {
    expect(l.length <= 22).toBe(true)
    expect(/\bmake\b/i.test(l)).toBe(false)
    expect(/[–—]/.test(l)).toBe(false)
  }
  for (const a of Object.values(LABELS)) if (a.phrase) expect(/[–—]/.test(a.phrase)).toBe(false)
  const used: ActionId[] = ['start', 'next', 'hub', 'switch', 'send', 'cockpit', ...STAGES.map(s => s.action), ...BOARDS]
  for (const id of used) expect(LABELS[id]?.label).toBeTruthy()
  for (const s of STAGES) if (s.board) expect(s.action).toBe(s.board)
  expect(BOARDS.map(b => STAGES.findIndex(s => s.board === b) >= 0)).toEqual(BOARDS.map(() => true))
})

test('LABELS frozen snapshot: all action ids, labels and phrases', () => {
  expect(LABELS).toEqual({
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
  })
})

test('H-UI-11: merged skill outputs light each stage in turn, then a fresh Send opens until acked', () => {
  for (let i = 0; i <= MERGED_STEPS.length; i++) {
    const r = reelView(mergedReel(i), MERGED_REEL)
    expect(names(r.done)).toEqual(MERGED_STEPS.slice(0, i).map(([stage]) => stage))
    expect(r.cur).toBe(i === 6 ? 7 : i === 7 ? 7 : i === 8 ? 8 : i)
  }
  const tree = { ...mergedReel(), ...reel(MERGED_REEL, { 'sound-selection.json': { at: NOW + 1, size: 10 } }) }
  expect(reelView(tree, MERGED_REEL, { baseline: NOW }).sends).toEqual([{ file: 'sound-selection.json', board: 'sound', mtimeMs: NOW + 1 }])
  expect(reelView(tree, MERGED_REEL, { baseline: NOW, acked: { [`${MERGED_REEL}/sound-selection.json`]: NOW + 1 } }).sends).toEqual([])
})

test('Entry shape: list() gives files their size and mtime, folders 0', () => {
  const l = list({ 'videos/a/raw/x.mp4': f(1, { size: 5 }) }, 'videos/a') as Entry[]
  expect(l).toEqual([{ name: 'raw', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }])
  expect(list({ 'videos/a/raw/x.mp4': f(1, { size: 5 }) }, 'videos/a/raw')).toEqual([{ name: 'x.mp4', kind: 'file', size: 5, mtimeMs: NOW - DAY, isLink: false }])
})
