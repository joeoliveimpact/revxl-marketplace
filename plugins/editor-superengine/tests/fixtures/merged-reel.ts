import { CONFIG_FILE, f, json, reel, type Tree } from './reels'

// H-UI-11: cumulative outputs of the merged skills, at a single reel root.
// Sources: reel-first-cuts/references/{boards,no-board-path}.md,
// reel-canvas-build/references/{beat-map,build}.md, reel-sound-pass/references/sound-board.md.
export const MERGED_REEL = 'Reel 3'
export const MERGED_STEPS: [string, Tree][] = [
  ['Record', { 'raw/Reel 3 take1 - Raw - 11.03.26.mp4': f(6) }],
  ['Cut', { 'cut-selection.json': json(5, { v: 1, reel: MERGED_REEL, lines: [] }),
    'work/edl.json': json(4, [{ src_in: 0, src_out: 12, take: 1 }]) }],
  ['Ear pass', { 'tweak-selection.json': json(3, { reel: MERGED_REEL, cuts: [], speed: 1.1 }) }],
  ['Beat map', { 'beat-map.state.json': json(2, { schema: 1, reel: MERGED_REEL, fps: 30,
    words: 'work/edit_map.cut.json', beats: [], word_marks: [], proposed: {}, notes: {}, needs: [], sent_at: '2026-11-02T10:00:00Z' }),
    'beat-map-selection.json': json(2, { schema: 1, reel: MERGED_REEL, beats: [], sent_at: '2026-11-02T10:00:00Z' }) }],
  ['Motion', { 'sketches.state.json': json(1.5, { schema: 1, reel: MERGED_REEL, rough: null,
    directions: [], pick: 'opening-a', sketches: [], note: '', sent_at: null, locked_at: '2026-11-03T00:00:00Z' }) }],
  ['Sound', { 'sound-selection.json': json(1, { project: MERGED_REEL, cues: [], undecided: [] }) }],
  ['Grade', { 'grade-selection.json': json(0.75, { reel: MERGED_REEL, clips: [] }) }],
  ['Master', { 'renders/Reel 3 Master - 11.03.26.mp4': f(0.5) }],
]
export const mergedReel = (count = MERGED_STEPS.length): Tree => ({
  ...CONFIG_FILE, ...reel(MERGED_REEL, { 'raw/': {}, ...Object.assign({}, ...MERGED_STEPS.slice(0, count).map(([, files]) => files)) }),
})
