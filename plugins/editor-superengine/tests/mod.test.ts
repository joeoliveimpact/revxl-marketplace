import { test, expect, mock } from 'claude-code/testing'
import { LABELS, BOARD_NAME, STAGES, TOGGLE, BATON_NONE, BATON_UNREAD, fill, folderKey } from '../hooks/mod/logic'
import { NOW, DAY, ROOT, f, json, reel, walk, WALK, list, CONFIG_FILE, REEL_018, REEL_020, type Tree } from './fixtures/reels'

// The mod drawn and run through the engine; the test's hooks beneath it stand for the disk, the store, the clock, the
// dialog, the opener and another plugin's band.
const PLUGIN = 'editor-superengine'
const SURFACES = ['terminal', 'desktop'] as const
const PANE = { title: 'Editor Cockpit', isFocused: true, bodyColumns: 48, placement: 'dock', scroll: { offset: 0, bodyRows: 60 }, view: {} }
const BAND = { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 100, scroll: { offset: 0, bodyRows: 10 }, view: {} }
const KEY = folderKey(ROOT)
const START = { cwd: ROOT, surface: 'terminal', isInteractive: true } as any
const FFPROBE = 'C:/Tools/ffprobe.exe'
const PLATFORM: Tree = { 'editor/.platform.json': { at: NOW - 30 * DAY, text: JSON.stringify({ schema: 1, tools: { ffprobe: FFPROBE } }) } }
const turn = (extra: object = {}) => ({ answer: 'Done.', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer', ...extra }) as any
const typed = (command: string) => ({ command, args: '', origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 80 } }) as any

type Opts = {
  busy?: string[]                  // folders (relative to the root) whose listing is refused, as a syncing folder is
  cwdFails?: boolean               // $.session.cwd() refused: the forced failure
  open?: 'placed' | 'unplaced' | 'refused'
  pick?: (options: string[]) => string | null   // the dialog's answer; null = dismissed
  probe?: (argv: string[]) => { exitCode: number; stdout: string } | 'refuse'
  refuseRegister?: boolean
}

function world(on: any, tree: Tree, o: Opts = {}) {
  const seen = { submits: [] as any[], status: [] as (string | undefined)[], store: new Map<string, unknown>(), sets: [] as string[],
    opens: [] as any[], asks: [] as { question: string; header: string; options: string[] }[], runs: [] as string[][], reads: [] as string[],
    writes: [] as string[], logs: [] as any[], toasts: [] as string[], registers: [] as any[], clock: undefined as any }
  const gone = { deny: 'ENOENT: no such file or directory' }, busy = { deny: 'EBUSY: resource busy or locked' }
  // The engine hands fs hooks the OS's own spelling (backslashes on Windows): looked up relative to the root.
  const rel = (e: any): string | undefined => {
    const p = String(e.path).replace(/\\/g, '/')
    return p.startsWith(`${ROOT}/`) ? p.slice(ROOT.length + 1) : undefined
  }
  seen.clock = mock.clock(on, { now: NOW })
  on('session.cwd', async () => (o.cwdFails ? { deny: 'forced failure' } : { value: ROOT }))
  on('store.get', async ($: any, e: any) => ({ value: seen.store.get(e.key) }))
  on('store.set', async ($: any, e: any) => { seen.sets.push(e.key); seen.store.set(e.key, JSON.parse(JSON.stringify(e.value))); return { value: undefined } })
  on('ui.status', async ($: any, e: any) => { seen.status.push(e.text); return { value: undefined } })
  on('session.start', async ($: any, e: any) => ({ cwd: e.cwd }))
  on('turn.complete', async ($: any, e: any) => ({ text: e.answer }))
  on('command.register', async ($: any, e: any) => { seen.registers.push(e); return o.refuseRegister ? { deny: 'refused' } : { value: { command: e.name } } })
  on('ui.open', async ($: any, e: any) => {
    seen.opens.push(e)
    return o.open === 'refused' ? { deny: 'refused' } : { value: o.open === 'unplaced' ? { isPlaced: false, reason: 'too narrow' } : { isPlaced: true } }
  })
  on('tool.call', { tool: 'AskUserQuestion' }, async ($: any, e: any) => {
    const q = e.questions[0], options = q.options.map((x: any) => x.label)
    seen.asks.push({ question: q.question, header: q.header, options })
    const a = (o.pick ?? (() => null))(options)
    return a === null ? { deny: 'dismissed' } : { result: { questions: e.questions, answers: { [q.question]: a } } }
  })
  on('fs.stat', async ($: any, e: any) => {
    const r = rel(e), v = r === undefined ? undefined : tree[r]
    if (v && !r!.endsWith('/')) return { value: { kind: 'file', size: v.size ?? 1000, mtimeMs: v.at ?? NOW, isLink: false } }
    return r !== undefined && list(tree, r) ? { value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: false } } : gone
  })
  on('fs.read', async ($: any, e: any) => {
    const r = rel(e), v = r === undefined ? undefined : tree[r]
    seen.reads.push(r ?? String(e.path))
    return !v ? gone : v.busy ? busy : { value: v.text ?? '' }
  })
  on('fs.list', async ($: any, e: any) => {
    const r = rel(e)
    if (r !== undefined && o.busy?.includes(r)) return busy
    const l = r === undefined ? undefined : list(tree, r)
    return l ? { value: l } : r !== undefined && tree[r] ? { deny: 'ENOTDIR: not a directory' } : gone
  })
  on('fs.write', async ($: any, e: any) => { seen.writes.push(String(e.path)); return { value: undefined } })
  on('process.run', async ($: any, e: any) => {
    seen.runs.push([...e.argv])
    const a = o.probe ? o.probe(e.argv) : { exitCode: 0, stdout: 'video\n' }
    return a === 'refuse' ? { deny: 'spawn failed' } : { value: { ...a, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('prompt.submit', async ($: any, e: any) => { seen.submits.push(e); return { text: e.text } })
  on('ui.toast', async ($: any, e: any) => { seen.toasts.push(e.text); return { value: undefined } })
  on('ui.log', async ($: any, e: any) => { seen.logs.push(e); return { value: undefined } })
  // Another plugin's band, beneath ours.
  on('ui.render', { component: 'AbovePrompt' }, async ($: any, e: any) => {
    const { Box, Text }: any = $.ui.resolve(e)
    return Box({ key: 'other-band', children: [Text({ children: ['other plugin band'] })] })
  })
  return seen
}

const mount = ($: any, surface: (typeof SURFACES)[number]) =>
  $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'ed-cockpit', props: PANE as any })
const band = ($: any, surface: (typeof SURFACES)[number], props: object = BAND) =>
  $.ui.mount({ plugin: PLUGIN, surface, component: 'AbovePrompt', props: props as any })
const sent = (seen: any) => seen.submits.map((s: any) => ({ text: s.text, asUser: s.origin?.asUser }))
const labelsOf = async (ui: any) => (await ui.findAll({ type: 'Button' })).map((b: any) => b.props.label)
/** Every phrase a button may send: LABELS' phrases filled with each reel (or none) and each board (or none). */
const phrases = (tree: Tree) => {
  const reels = (list(tree, 'videos') ?? []).filter(x => x.kind === 'dir').map(x => x.name)
  return new Set(Object.values(LABELS).flatMap(a => (a.phrase ? [undefined, ...reels].flatMap(r =>
    [undefined, ...Object.values(BOARD_NAME)].map(b => fill(a.phrase!, r, b))) : [])))
}

const SENT: Tree = { ...walk(5), ...reel('r5', { 'sound-selection.json': f(0.5) }) }
const BASELINE = NOW - 3 * DAY
// The Beat Map sent (sent_at set), its sketches.state.json not yet written: Claude's move (H-S15a-7).
const SENT_BEATS: Tree = { ...walk(4), ...reel('r4', { 'beat-map-selection.json': f(0.5) }) }
/** name, disk, world options, a baseline already in the store, whether a reel is in progress. */
const STATES: [string, Tree, Opts, number | undefined, boolean][] = [
  ['nothing in the edit', CONFIG_FILE, {}, undefined, false],
  ['no config, no videos folder', {}, {}, undefined, false],
  ['only idle reels (REEL-018/020 shapes)', { ...CONFIG_FILE, ...REEL_018, ...REEL_020 }, {}, undefined, false],
  ...WALK.map((w, i): [string, Tree, Opts, undefined, boolean] => [`your move at ${STAGES[w[2]]!.name}`, walk(i), {}, undefined, true]),
  ["Claude's move", SENT, {}, BASELINE, true],
  ["Claude's move, Beat Map Send", SENT_BEATS, {}, BASELINE, true],
  ['unreadable videos folder', CONFIG_FILE, { busy: ['videos'] }, undefined, false],
  ['unreadable state file', { ...walk(3), ...reel('r3', { 'beat-map.state.json': f(1, { busy: true }) }) }, {}, undefined, true],
  ['unreadable reel subfolder', walk(2), { busy: ['videos/r2/work'] }, undefined, true],
  ['broken config', { 'editor/editor.config.json': { at: NOW, text: '{oops' }, ...reel('r1', WALK[1]![1]) }, {}, undefined, true],
]

// The draw sweep: one refused element blanks the whole pane, so every state draws on both surfaces.
for (const [name, tree, o, base, busyReel] of STATES)
  for (const surface of SURFACES)
    test(`${surface} sweep, ${name}: pane and band draw, nothing refused`, async ($, on) => {
      const seen = world(on, tree, o)
      if (base !== undefined) seen.store.set('editorBaseline', { [KEY]: base })
      const ui = await mount($, surface)
      await ui.drawn()   // rejects if the surface refused the tree
      expect(await ui.find({ key: 'cockpit-error' })).toBeUndefined()
      expect(String((await ui.find({ key: 'main' }))?.props.label)).toMatch(/\S  →$/)
      expect(await ui.findAll({ type: 'Svg' })).toHaveLength(surface === 'desktop' ? 2 : 0)   // hero card, stepper
      expect((await ui.findAll({ type: 'Button' })).filter((b: any) => /→/.test(b.props.label)).map((b: any) => b.key)).toEqual(['main'])
      const strip = await band($, surface)
      await strip.drawn()
      expect(await strip.find({ key: 'other-band' })).toBeDefined()
      expect(!!(await strip.find({ key: 'ed-band' }))).toBe(busyReel)
      expect(await strip.findAll({ type: 'Svg' })).toHaveLength(busyReel && surface === 'desktop' ? 1 : 0)
      expect((await labelsOf(strip)).some((l: string) => /→/.test(l))).toBe(false)
    })

for (const surface of SURFACES)
  test(`${surface}: a forced failure draws the error card; its What's next? submits as the user; the throw is logged`, async ($, on) => {
    const seen = world(on, walk(5), { cwdFails: true })
    const ui = await mount($, surface)
    await ui.drawn()
    const card = await ui.find({ key: 'cockpit-error' })
    expect(card?.props).toMatchObject({ borderStyle: 'round', borderColor: 'error' })
    await ui.press({ key: 'error-next' })
    expect(sent(seen)).toEqual([{ text: "What's next in editing?", asUser: true }])
    expect(seen.logs.some(l => /cockpit draw: .*forced failure/.test(l.text) && l.to === 'debug')).toBe(true)
    const strip = await band($, surface)
    expect(await strip.find({ key: 'ed-band' })).toBeUndefined()
    expect(await strip.find({ key: 'other-band' })).toBeDefined()
  })

// Every button: one phrase from LABELS as the person's own message, or the pane opened (Cockpit), or one question
// (Switch reel), or a store write only (the autostart toggle).
for (const [name, tree, o, base] of STATES)
  test(`every button, ${name}: each press does exactly one thing`, async ($, on) => {
    const seen = world(on, tree, o)
    if (base !== undefined) seen.store.set('editorBaseline', { [KEY]: base })
    const allowed = phrases(tree)
    for (const [ui, isBand] of [[await mount($, 'desktop'), false], [await band($, 'desktop'), true]] as const) {
      for (const b of await ui.findAll({ type: 'Button' })) {
        const before = [seen.submits.length, seen.opens.length, seen.asks.length, seen.sets.length]
        await ui.press({ key: b.key! })
        const d = [seen.submits.length, seen.opens.length, seen.asks.length, seen.sets.length].map((n, i) => n - before[i]!)
        if (b.key === 'switch') expect(d).toEqual([0, 0, 1, 0])
        else if (b.key === 'autostart') expect(d).toEqual([0, 0, 0, 1])
        else if (b.key === 'band-cockpit') {
          expect(d).toEqual([0, 1, 0, 0])
          expect(seen.opens.at(-1)).toMatchObject({ id: 'ed-cockpit', title: 'Editor Cockpit', focus: true })
        } else {
          expect([b.key, ...d]).toEqual([b.key, 1, 0, 0, 0])
          const s = seen.submits.at(-1)
          expect(allowed.has(s.text)).toBe(true)
          expect(s.origin?.asUser).toBe(true)
        }
        if (!isBand) expect(b.key).not.toBe('band-cockpit')
      }
    }
    expect(seen.writes).toEqual([])
  })

// Colours: Box and Text take theme keys only; Lantern hex lives only inside Svg markup (an Svg is neither).
test('colour rule: no Box or Text color, borderColor or backgroundColor is hex, in every state, pane and band, both surfaces', async ($, on) => {
  const tree: Tree = {}, o: Opts = {}
  const seen = world(on, tree, o)   // one world, its disk and options swapped per state
  const bad: string[] = [], keys = new Set<unknown>()
  const uis = await Promise.all(SURFACES.flatMap(s => [mount($, s), band($, s)]))
  for (const [name, t, so, base] of STATES) {
    for (const k of Object.keys(tree)) delete tree[k]
    for (const k of Object.keys(o)) delete (o as any)[k]
    Object.assign(tree, t), Object.assign(o, so)
    seen.store.clear()
    if (base !== undefined) seen.store.set('editorBaseline', { [KEY]: base })
    for (const ui of uis) {
      await ui.redraw()
      await ui.drawn()
      for (const el of [...await ui.findAll({ type: 'Box' }), ...await ui.findAll({ type: 'Text' })])
        for (const p of ['color', 'borderColor', 'backgroundColor']) {
          keys.add(el.props[p])
          if (/^#/.test(String(el.props[p] ?? ''))) bad.push(`${name}, ${ui.surface}: ${el.type} ${el.key ?? ''} ${p}=${el.props[p]}`)
        }
    }
  }
  expect(bad).toEqual([])
  for (const k of ['subtle', 'claude']) expect(keys.has(k)).toBe(true)   // the walk reached the coloured elements
})

test('pane layout: hero, main button, quick buttons, stepper and boards in subtle boxes, the toggle last', async ($, on) => {
  world(on, walk(5))
  const ui = await mount($, 'terminal')
  const root = await ui.find({ key: 'cockpit' })
  expect(root?.children.map((c: any) => c.key ?? c.props?.key)).toEqual(['hero', 'main-act', 'quick', 'progress', 'boards', 'autostart-act'])
  expect((await ui.find({ key: 'main' }))?.props).toMatchObject({ label: 'Open Sound Board  →', variant: 'primary' })
  expect((await ui.find({ key: 'quick' }))?.children.map((c: any) => c.key ?? c.props?.key)).toEqual(['hub', 'next', 'switch'])
  for (const key of ['progress', 'boards']) expect((await ui.find({ key }))?.props).toMatchObject({ borderStyle: 'round', borderColor: 'subtle' })
  expect((await ui.find({ key: 'progress' }))?.text).toContain('■■■■■◐□□□ Sound')
  const boards = await Promise.all(['cut', 'tweak', 'beatmap', 'sketches', 'sound', 'grade'].map(async b => (await ui.find({ key: `board-${b}` }))?.props.label))
  expect(boards).toEqual(['Cut Board ✓', 'Tweak Board ✓', 'Beat Map ✓', 'Sketches ✓', 'Sound Board ●', 'Grade Board'])
  expect((await ui.find({ key: 'hero' }))?.text).toContain('r5 · YOUR MOVE')
})

test('desktop: the hero card and the stepper are Svg; the stepper dashes Grade, escapes text, and the main button keeps its arrow only on screen', async ($, on) => {
  const seen = world(on, walk(6))
  const ui = await mount($, 'desktop')
  const [heroSvg, step] = await ui.findAll({ type: 'Svg' })
  expect(heroSvg!.props.source).toContain('Render the <tspan font-weight="600" fill="#FF5A3C">master</tspan>')
  expect(heroSvg!.props.source).toContain('url(#lamp)')
  expect(step!.props.alt).toBe('Editing progress: Record, Cut, Ear pass, Beat map, Motion, Sound done; now Master')
  expect(step!.props.source).toContain('stroke-dasharray="3 3"')
  expect(step!.props.isInteractive).toBe(true)
  expect(heroSvg!.props.source).toContain('r6 · YOUR MOVE')
  await ui.press({ key: 'main' })
  expect(sent(seen)).toEqual([{ text: 'Render the master for r6', asUser: true }])
})

test("Claude's move: the main button is Use my Send; the hero says the board's Send is in", async ($, on) => {
  const seen = world(on, SENT)
  seen.store.set('editorBaseline', { [KEY]: BASELINE })
  const ui = await mount($, 'terminal')
  expect((await ui.find({ key: 'main' }))?.props.label).toBe('Use my Send  →')
  expect((await ui.find({ key: 'hero' }))?.text).toContain("r5 · CLAUDE'S MOVE")
  expect((await ui.find({ key: 'hero' }))?.text).toContain('Sound Board sent')
  await ui.press({ key: 'main' })
  expect(sent(seen)).toEqual([{ text: 'Go ahead with my Sound Board Send for r5', asUser: true }])
})

// ---- Switch reel
const FOUR: Tree = { ...CONFIG_FILE, ...reel('a', { 'raw/x.mp4': f(1) }), ...reel('b', { 'raw/x.mp4': f(2) }), ...reel('c', { 'raw/x.mp4': f(3) }),
  ...reel('d', { 'raw/x.mp4': f(4) }), ...reel('z', { 'raw/x.mp4': f(20) }) }

test('Switch reel: asks from the press with the 3 latest reels + Editor hub; a pick refreshes, re-pins the baton and redraws', async ($, on) => {
  const seen = world(on, FOUR, { pick: () => 'b' })
  const ui = await mount($, 'terminal')
  expect((await ui.find({ key: 'hero' }))?.text).toContain('a · YOUR MOVE')
  await ui.press({ key: 'switch' })
  expect(seen.asks).toEqual([{ question: 'Which reel do you want to work on?', header: 'Editor', options: ['a', 'b', 'c', 'Editor hub'] }])
  expect(seen.status.at(-1)).toBe('Your move: Cut Board (b)')
  expect((await ui.find({ key: 'hero' }))?.text).toContain('b · YOUR MOVE')
  expect(seen.submits).toEqual([])
  const strip = await band($, 'terminal')
  expect((await strip.find({ key: 'ed-band' }))?.text).toContain('b · Cut · your move')
})

test('Switch reel: an idle reel can be picked; Editor hub sends the hub phrase; free text and a dismissal do nothing', async ($, on) => {
  let answer: string | null = 'Editor hub'
  const seen = world(on, { ...CONFIG_FILE, ...REEL_018, ...REEL_020 }, { pick: () => answer })
  const ui = await mount($, 'terminal')
  await ui.press({ key: 'switch' })
  expect(seen.asks[0]!.options).toEqual(['reel-020', 'reel-018', 'Editor hub'])
  expect(sent(seen)).toEqual([{ text: 'Open my editor hub', asUser: true }])
  answer = 'make it shorter'
  await ui.press({ key: 'switch' })
  answer = null
  await ui.press({ key: 'switch' })
  expect(seen.submits).toHaveLength(1)
  expect(seen.logs.some(l => /switch reel: .*dismissed/.test(l.text) && l.to === 'debug')).toBe(true)
  expect((await ui.find({ key: 'main' }))?.props.label).toBe('Start a reel  →')
  answer = 'reel-018'
  await ui.press({ key: 'switch' })
  expect((await ui.find({ key: 'main' }))?.props.label).toBe('Open Cut Board  →')
  expect(seen.status.at(-1)).toBe('Your move: Cut Board (reel-018)')
})

test('Switch reel with no reels offers only Editor hub (the engine pads the rest); a padded answer does nothing', async ($, on) => {
  const seen = world(on, CONFIG_FILE, { pick: options => options.find(x => x !== 'Editor hub') ?? null })
  const ui = await mount($, 'terminal')
  await ui.press({ key: 'switch' })
  expect(seen.asks[0]!.options[0]).toBe('Editor hub')
  expect(seen.asks[0]!.options.filter(x => x !== 'Editor hub' && x !== 'Yes' && x !== 'No')).toEqual([])
  expect(seen.submits).toEqual([])
})

// ---- the band
for (const surface of SURFACES) {
  test(`${surface}: band with a reel in progress: our row first, What's next?, Open <board>, Cockpit; another band beneath, untouched`, async ($, on) => {
    const seen = world(on, walk(5))
    const ui = await band($, surface)
    const column = await ui.find({ type: 'Box' })
    expect(column?.props.flexDirection).toBe('column')
    expect(column?.children.map((c: any) => c.props?.key)).toEqual(['ed-band', 'other-band'])
    expect((await ui.find({ key: 'other-band' }))?.text).toBe('other plugin band')
    expect(await labelsOf(ui)).toEqual(["What's next?", 'Open Sound Board', 'Cockpit'])
    expect(await ui.find({ text: 'Editing progress' })).toBeDefined()
    if (surface === 'desktop') expect((await ui.find({ type: 'Svg' }))?.props).toMatchObject({ width: 230, alt: 'Editing progress: Record, Cut, Ear pass, Beat map, Motion done; now Sound' })
    else expect((await ui.find({ key: 'ed-progress' }))?.text).toContain('■■■■■◐□□□ r5 · Sound · your move')
    await ui.press({ key: 'band-next' })
    await ui.press({ key: 'band-board' })
    await ui.press({ key: 'band-cockpit' })
    expect(sent(seen)).toEqual([{ text: "What's next in editing r5?", asUser: true }, { text: 'Open my Sound Board for r5', asUser: true }])
    expect(seen.opens.map(x => [x.id, x.title, x.focus])).toEqual([['ed-cockpit', 'Editor Cockpit', true]])
  })

  test(`${surface}: band at Record has no board button; nothing in the edit leaves only the band beneath; a survey too`, async ($, on) => {
    world(on, walk(0))
    expect(await labelsOf(await band($, surface))).toEqual(["What's next?", 'Cockpit'])
    const survey = await band($, surface, { ...BAND, hasSurvey: true })
    expect(await survey.find({ key: 'ed-band' })).toBeUndefined()
    expect(await survey.find({ key: 'other-band' })).toBeDefined()
  })
}

test('band with nothing in the edit: the other band alone', async ($, on) => {
  world(on, { ...CONFIG_FILE, ...REEL_018 })
  const ui = await band($, 'desktop')
  expect(await ui.find({ key: 'ed-band' })).toBeUndefined()
  const d: any = await ui.drawn()
  expect(d.key ?? d.props?.key).toBe('other-band')
})

test('band: a refused Cockpit open toasts and is logged', async ($, on) => {
  const seen = world(on, walk(5), { open: 'refused' })
  const ui = await band($, 'terminal')
  await ui.press({ key: 'band-cockpit' })
  expect(seen.toasts).toEqual(['Editor Cockpit could not open'])
  expect(seen.logs.some(l => l.text.startsWith('editor-superengine: band open:'))).toBe(true)
})

// ---- /editor
test('/editor: registered at session start; running it opens the pane focused and says so', async ($, on) => {
  const seen = world(on, walk(5))
  await $.session.start(START)
  expect(seen.registers.map(r => [r.name, r.description])).toEqual([['editor', 'Open the Editor Cockpit']])
  seen.opens.length = 0
  const out: any = await $.command.run(typed('editor'))
  expect(seen.opens.map(x => [x.id, x.title, x.focus])).toEqual([['ed-cockpit', 'Editor Cockpit', true]])
  expect(out.text).toBe('Opened the Editor Cockpit.')
  expect(seen.status.at(-1)).toBe('Your move: Sound Board (r5)')
  expect(seen.submits).toEqual([])
})

test("/editor: opened but not placed says it couldn't be shown here, with the baton", async ($, on) => {
  world(on, walk(5), { open: 'unplaced' })
  const out: any = await $.command.run(typed('editor'))
  expect(out.text).toBe("The Editor Cockpit couldn't be shown here. Your move: Sound Board (r5)")
})

test('/editor: a refused open toasts and says it could not open', async ($, on) => {
  const seen = world(on, walk(5), { open: 'refused' })
  const out: any = await $.command.run(typed('editor'))
  expect(out.text).toBe('The Editor Cockpit could not open.')
  expect(seen.toasts).toEqual(['Editor Cockpit could not open'])
})

test('/editor: a refused registration is logged to debug; the session start goes on', async ($, on) => {
  const seen = world(on, walk(5), { refuseRegister: true })
  await $.session.start(START)
  expect(seen.logs.some(l => l.text.startsWith('editor-superengine: /editor not registered:') && l.to === 'debug')).toBe(true)
  expect(seen.status).toEqual(['Your move: Sound Board (r5)'])
})

// ---- the status-line baton
const BATONS: [string, Tree, Opts, number | undefined, string][] = [
  ['nothing in the edit', CONFIG_FILE, {}, undefined, BATON_NONE],
  ['your move at a board', walk(5), {}, undefined, 'Your move: Sound Board (r5)'],
  ['your move at Record', walk(0), {}, undefined, 'Your move: record (r0)'],
  ['your move at Master', walk(6), {}, undefined, 'Your move: render the master (r6)'],
  ['your move at Post', walk(7), {}, undefined, 'Your move: post (r7)'],
  ["Claude's move", SENT, {}, BASELINE, "Claude's move: Sound Board Send (r5)"],
  ["Claude's move, Beat Map Send", SENT_BEATS, {}, BASELINE, "Claude's move: Beat Map Send (r4)"],
  ['an unreadable videos folder', CONFIG_FILE, { busy: ['videos'] }, undefined, BATON_UNREAD],
  ['a failed load', walk(5), { cwdFails: true }, undefined, BATON_UNREAD],
]
for (const [name, tree, o, base, line] of BATONS)
  test(`baton at session start, ${name}: "${line}"`, async ($, on) => {
    const seen = world(on, tree, o)
    if (base !== undefined) seen.store.set('editorBaseline', { [KEY]: base })
    await $.session.start(START)
    expect(seen.status).toEqual([line])
  })

test('baton follows the disk on a main-loop answer only; a Send made after the baseline turns it to Claude', async ($, on) => {
  const tree: Tree = { ...walk(5) }
  const seen = world(on, tree)
  await $.session.start(START)
  expect(seen.store.get('editorBaseline')).toEqual({ [KEY]: NOW })
  await seen.clock.advance(60_000)
  Object.assign(tree, reel('r5', { 'sound-selection.json': { at: NOW + 30_000, size: 10 } }))
  await $.turn.complete(turn({ agentId: 'agent-1' }))
  await $.turn.complete(turn({ reason: 'aborted', isAborted: true }))
  expect(seen.status).toHaveLength(1)
  await $.turn.complete(turn())
  expect(seen.status.at(-1)).toBe("Claude's move: Sound Board Send (r5)")
  seen.store.set('editorAcked', { 'r5/sound-selection.json': NOW + 30_000 })   // S15b's ack
  await $.turn.complete(turn())
  expect(seen.status.at(-1)).toBe('Your move: render the master (r5)')
})

// ---- the store: only editorBaseline and autostartOff are ever written
test('store: only editorBaseline (once, never moved) and autostartOff are written; nothing goes to disk', async ($, on) => {
  const seen = world(on, FOUR, { pick: () => 'c' })
  await $.session.start(START)
  await seen.clock.advance(5 * DAY)
  await $.session.start(START)
  await $.turn.complete(turn())
  expect(seen.store.get('editorBaseline')).toEqual({ [KEY]: NOW })
  const ui = await mount($, 'desktop')
  for (const b of await ui.findAll({ type: 'Button' })) await ui.press({ key: b.key! })
  const strip = await band($, 'desktop')
  for (const b of await strip.findAll({ type: 'Button' })) await strip.press({ key: b.key! })
  await $.command.run(typed('editor'))
  expect([...new Set(seen.sets)].sort()).toEqual(['autostartOff', 'editorBaseline'])
  expect(seen.sets.filter(k => k === 'editorBaseline')).toHaveLength(1)
  expect(seen.writes).toEqual([])
})

test('the baseline keeps other workspaces and is set per workspace', async ($, on) => {
  const seen = world(on, walk(5))
  seen.store.set('editorBaseline', { 'd:/other': 5 })
  await $.session.start(START)
  expect(seen.store.get('editorBaseline')).toEqual({ 'd:/other': 5, [KEY]: NOW })
})

// ---- autostart
const opened = (seen: any) => seen.opens.map((x: any) => [x.id, x.title, x.focus])
test('autostart: an editor workspace opens the pane unfocused at session start, once per module life', async ($, on) => {
  const seen = world(on, walk(5))
  await $.session.start(START)
  await $.session.start(START)
  expect(opened(seen)).toEqual([['ed-cockpit', 'Editor Cockpit', undefined]])
})

test('autostart: Claude Code Desktop (isInteractive false, surface null) still opens', async ($, on) => {
  const seen = world(on, walk(5))
  await $.session.start({ cwd: ROOT, surface: null, isInteractive: false } as any)
  expect(opened(seen)).toEqual([['ed-cockpit', 'Editor Cockpit', undefined]])
})

for (const [name, tree, off] of [['no editor config', reel('r1', WALK[1]![1]), undefined], ['switched off here', walk(5), [KEY]]] as const)
  test(`autostart: stays shut with ${name}`, async ($, on) => {
    const seen = world(on, tree)
    if (off) seen.store.set('autostartOff', off)
    await $.session.start(START)
    expect(seen.opens).toEqual([])
  })

test('autostart: a refused open is only logged', async ($, on) => {
  const seen = world(on, walk(5), { open: 'refused' })
  await $.session.start(START)
  expect(seen.logs.some(l => l.text.startsWith('editor-superengine: autostart:') && l.to === 'debug')).toBe(true)
})

test('the footer toggle saves this folder to autostartOff and takes it out again; a session there then stays shut', async ($, on) => {
  const seen = world(on, walk(5))
  seen.store.set('autostartOff', ['d:/elsewhere'])
  const ui = await mount($, 'terminal')
  expect((await ui.find({ key: 'autostart' }))?.props.label).toBe(TOGGLE.off)
  await ui.press({ key: 'autostart' })
  expect(seen.store.get('autostartOff')).toEqual(['d:/elsewhere', KEY])
  expect((await ui.find({ key: 'autostart' }))?.props.label).toBe(TOGGLE.on)
  await $.session.start(START)
  expect(seen.opens).toEqual([])
  await ui.press({ key: 'autostart' })
  expect(seen.store.get('autostartOff')).toEqual(['d:/elsewhere'])
  expect((await ui.find({ key: 'autostart' }))?.props.label).toBe(TOGGLE.off)
  expect(seen.submits).toEqual([])
})

test('the footer toggle is hidden where autostart never fires (no config), unless already switched off', async ($, on) => {
  const seen = world(on, reel('r1', WALK[1]![1]))
  const ui = await mount($, 'terminal')
  expect(await ui.find({ key: 'autostart' })).toBeUndefined()
  seen.store.set('autostartOff', [KEY])
  await ui.redraw()
  expect((await ui.find({ key: 'autostart' }))?.props.label).toBe(TOGGLE.on)
})

// ---- the master's ffprobe
const R7_MASTER = `${ROOT}/videos/r7/renders/r7 Master - 11.03.26.mp4`
const ARGV = [FFPROBE, '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', R7_MASTER]

test('ffprobe: run on a refresh only, once per path and mtime, with the exact argv; never on a draw', async ($, on) => {
  const tree: Tree = { ...walk(7), ...PLATFORM }
  const seen = world(on, tree)
  const ui = await mount($, 'desktop')   // a draw before any refresh: no run, the master counts by existence
  expect(seen.runs).toEqual([])
  expect((await ui.find({ key: 'main' }))?.props.label).toBe('Write my caption  →')
  await $.session.start(START)
  expect(seen.runs).toEqual([ARGV])
  expect(seen.status.at(-1)).toBe('Your move: post (r7)')
  await $.turn.complete(turn())
  await $.command.run(typed('editor'))
  await ui.redraw()
  await band($, 'desktop')
  expect(seen.runs).toHaveLength(1)
  tree['videos/r7/renders/r7 Master - 11.03.26.mp4'] = f(0.5)   // re-rendered
  await $.turn.complete(turn())
  expect(seen.runs).toHaveLength(2)
})

const PROBES: [string, Opts['probe'], Tree, string][] = [
  ['a video stream', () => ({ exitCode: 0, stdout: 'video\n' }), PLATFORM, 'Your move: post (r7)'],
  ['no video stream', () => ({ exitCode: 0, stdout: '' }), PLATFORM, 'Your move: render the master (r7)'],
  ['an ffprobe error', () => ({ exitCode: 1, stdout: '' }), PLATFORM, 'Your move: post (r7)'],
  ['ffprobe will not start', () => 'refuse', PLATFORM, 'Your move: post (r7)'],
  ['no .platform.json', () => ({ exitCode: 0, stdout: '' }), {}, 'Your move: post (r7)'],
  ['no ffprobe in .platform.json', () => ({ exitCode: 0, stdout: '' }), { 'editor/.platform.json': { text: '{"tools":{"ffprobe":null}}' } }, 'Your move: post (r7)'],
]
for (const [name, probe, extra, line] of PROBES)
  test(`ffprobe, ${name}: "${line}"`, async ($, on) => {
    const seen = world(on, { ...walk(7), ...extra }, { probe })
    await $.session.start(START)
    expect(seen.status).toEqual([line])
    expect(seen.runs).toHaveLength(Object.keys(extra).length && name !== 'no ffprobe in .platform.json' ? 1 : 0)
    const ui = await mount($, 'terminal')
    expect((await ui.find({ key: 'main' }))?.props.label).toBe(line.includes('master') ? 'Render the master  →' : 'Write my caption  →')
  })

test('REEL-018 shape: its ruled-name master is probed; mastered and .mov files are not', async ($, on) => {
  const seen = world(on, { ...CONFIG_FILE, ...REEL_018, ...PLATFORM })
  await $.session.start(START)
  expect(seen.runs.map(r => r.at(-1))).toEqual([`${ROOT}/videos/reel-018/renders/REEL-018 Master - 10.07.26.mp4`])
})

// ---- the mtime cache
test('a state JSON is read once while its mtime holds, and again once it changes; a failed read is not kept', async ($, on) => {
  const path = 'videos/r4/beat-map.state.json'
  const tree: Tree = { ...walk(4) }
  const seen = world(on, tree)
  const ui = await mount($, 'terminal')
  await ui.redraw()
  expect(seen.reads.filter(p => p === path)).toHaveLength(1)
  tree[path] = { ...json(0.5, { sent_at: 'again' }), busy: true }
  await ui.redraw()
  expect((await ui.find({ key: 'main' }))?.props.label).toBe('Open Beat Map  →')   // refused: not done this draw
  delete tree[path]!.busy
  await ui.redraw()
  expect(seen.reads.filter(p => p === path)).toHaveLength(3)
  expect((await ui.find({ key: 'main' }))?.props.label).toBe('Open Sketches  →')
})
