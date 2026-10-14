import { test, expect, mock } from 'claude-code/testing'

// Engine tests: the mod's hooks run in the real engine; every $ call it makes is answered by a stub beneath it.
const PLUGIN = 'workspace-superengine'
const BAND = { hasSurvey: false, isWorking: false, maxRows: 20, bodyColumns: 100,
  scroll: { offset: 0, bodyRows: 19 }, view: {} }
const PANE = { title: 'Workspace', isFocused: true, bodyColumns: 80, placement: 'dock' }
const SURFACES = ['terminal', 'desktop'] as const
const HANDOFF = '# handoff.md\r\n\r\n## Last session\r\n2026-10-13 \u2014 shipped\r\n\r\n## Blockers\r\n1. Joe\'s review.\r\n' +
  '\r\n## P0 \u2014 Next Actions\r\n1. Build Step 4.\r\n2. Send the note.\r\n'
const HB = 'C:/Users/t/.claude/revxl/heartbeat/workspace-superengine/sid-e1.json'

/** Stubs every $ call the mod makes; returns what it saw. */
function world(on: any, opts: { version?: string; handoff?: string | null; writeFails?: boolean; readError?: string } = {}) {
  const seen = { writes: [] as { path: string; text: string }[], runs: 0, fills: [] as string[], submits: 0,
    opened: [] as string[], commands: [] as string[], logs: [] as string[], toasts: [] as string[] }
  const clock = mock.clock(on, { now: Date.UTC(2026, 9, 14, 12) })
  mock.env(on, { USERPROFILE: 'C:\\Users\\t', HOME: '/c/Users/t' })
  on('session.version', async () => ({ value: { version: opts.version ?? '2.1.295', base: opts.version ?? '2.1.295' } }))
  on('session.root', async () => ({ value: 'C:\\ws' }))
  on('session.id', async () => ({ value: 'sid-e1' }))
  on('command.register', async ($: any, e: any) => { seen.commands.push(e.name); return { value: { command: e.name } } })
  on('process.run', async () => { seen.runs++; return { value: { exitCode: 0, stdout: '', stderr: '' } } })
  on('fs.read', async ($: any, e: any) => {
    const p = e.path.replace(/\\/g, '/')
    if (p.endsWith('/.claude-plugin/plugin.json')) return { value: '{"name":"workspace-superengine","version":"0.15.3"}' }
    if (p === 'C:/ws/handoff.md' && opts.readError) return { deny: opts.readError }   // there, but unreadable: the read rejects
    if (p === 'C:/ws/handoff.md' && opts.handoff !== null) return { value: opts.handoff ?? HANDOFF }
    throw new Error('ENOENT: ' + e.path)
  })
  on('fs.write', async ($: any, e: any) => {
    if (opts.writeFails) throw new Error('EACCES: ' + e.path)
    seen.writes.push({ path: e.path, text: e.text }); return { value: undefined }
  })
  on('fs.exists', async ($: any, e: any) => ({ value: !!opts.readError && e.path.replace(/\\/g, '/') === 'C:/ws/handoff.md' }))
  on('prompt.fill', async ($: any, e: any) => { seen.fills.push(e.text); return { isFilled: true } })   // an engine event
  on('prompt.submit', async () => { seen.submits++; return { value: {} } })
  on('ui.open', async ($: any, e: any) => { seen.opened.push(e.id); return { value: { isPlaced: true } } })
  on('ui.invalidate', async () => ({ value: undefined }))
  on('ui.log', async ($: any, e: any) => { seen.logs.push(e.text); return { value: undefined } })
  on('ui.toast', async ($: any, e: any) => { seen.toasts.push(e.text); return { value: undefined } })
  on('session.start', ($: any, e: any) => ({ cwd: e.cwd }))
  // a stand-in for another REVXL band (Fewzhun's) beneath ours: it must still draw
  on('ui.render', { component: 'AbovePrompt' }, async ($$: any, e: any) => {
    const { Box, Button } = $$.ui.resolve(e)
    return Box({ children: [Button({ key: 'fz-stand-in', label: 'Fewzhun stand-in', plain: true, onPress: () => {} })] })
  })
  return { seen, clock }
}

test('session start: /workspace registered; heartbeat is ONE $.fs.write of the v1 record, no process', async ($, on) => {
  const { seen, clock } = world(on)
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: 'C:\\ws' } as any)
  await clock.settle()
  expect(seen.commands).toEqual(['workspace'])
  expect(seen.writes.length).toBe(1)
  expect(seen.writes[0]!.path.replace(/\\/g, '/')).toBe(HB)   // the engine hands Windows paths over with backslashes
  expect(seen.writes[0]!.text.endsWith('\n')).toBe(true)
  const rec = JSON.parse(seen.writes[0]!.text)
  expect(Object.keys(rec)).toEqual(['v', 'plugin', 'version', 'pane_command', 'session_id', 'ts'])
  expect(rec).toEqual({ v: 1, plugin: 'workspace-superengine', version: '0.15.3', pane_command: '/workspace',
    session_id: 'sid-e1', ts: '2026-10-14T12:00:00Z' })
  expect(seen.runs).toBe(0)
})

test('heartbeat write fails: silent, the start and /workspace unharmed', async ($, on) => {
  const { seen, clock } = world(on, { writeFails: true })
  const r: any = await $.session.start({ surface: 'terminal', isInteractive: true, cwd: 'C:\\ws' } as any)
  await clock.settle()
  expect(r.cwd).toBe('C:\\ws')
  expect(seen.commands).toEqual(['workspace'])
  expect(seen.writes).toEqual([])
  expect(seen.toasts).toEqual([])
})

test('too old a Claude Code: no command, no heartbeat, the band passes through (the floor)', async ($, on) => {
  const { seen, clock } = world(on, { version: '2.1.286' })
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: 'C:\\ws' } as any)
  await clock.settle()
  expect(seen.commands).toEqual([])
  expect(seen.writes).toEqual([])
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'terminal', component: 'AbovePrompt', props: BAND as any })
  expect(await ui.find({ key: 'wse-close' })).toBeUndefined()
  expect(await ui.find({ key: 'fz-stand-in' })).toBeDefined()
  await ui.unmount()
})

test('band (Layout A): a column of our one row (c e k w) then the band beneath; fills never send', async ($, on) => {
  const { seen } = world(on)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'AbovePrompt', props: BAND as any })
    const t: any = await ui.drawn()
    expect(t.type).toBe('Box')
    expect(t.props.flexDirection).toBe('column')
    expect(t.children.length).toBe(2)
    const row = t.children[0]
    expect(row.props.flexDirection).toBe('row')
    expect(row.children.map((b: any) => b.type)).toEqual(['Button', 'Button', 'Button', 'Button'])
    expect(row.children.map((b: any) => b.props.label)).toEqual(['Close out', 'Continue', 'Checkpoint', 'Workspace'])
    expect(row.children.map((b: any) => b.props.hotkey)).toEqual(['c', 'e', 'k', 'w'])
    expect(JSON.stringify(t.children[1])).toContain('fz-stand-in')   // the band beneath ours still draws, below
    expect(await ui.findAll({ type: 'Text', text: /workspace-superengine/i })).toHaveLength(0)   // no name headline
    for (const key of ['wse-close', 'wse-continue', 'wse-checkpoint']) await ui.press({ key })
    await ui.press({ key: 'wse-workspace' })
    await ui.unmount()
  }
  expect(seen.fills).toEqual(['/session-closeout', '/session-continue', 'checkpoint: save progress and keep going',
    '/session-closeout', '/session-continue', 'checkpoint: save progress and keep going'])
  expect(seen.submits).toBe(0)
  expect(seen.opened).toEqual(['wse-workspace', 'wse-workspace'])
})

test('band yields to a survey', async ($, on) => {
  world(on)
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'terminal', component: 'AbovePrompt',
    props: { ...BAND, hasSurvey: true } as any })
  expect(await ui.find({ key: 'wse-close' })).toBeUndefined()
  expect(await ui.find({ key: 'fz-stand-in' })).toBeDefined()
  await ui.unmount()
})

test('/workspace opens the pane', async ($, on) => {
  const { seen } = world(on)
  const r: any = await $.command.run({ command: 'workspace' } as any)
  expect(r.text).toBe('Workspace pane opened.')
  expect(seen.opened).toEqual(['wse-workspace'])
})

test('pane: Last session date, Next (P0) and Blockers from handoff.md', async ($, on) => {
  world(on)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'wse-workspace', props: PANE as any })
    expect(await ui.find({ type: 'Text', text: 'Last session: 2026-10-13' })).toBeDefined()
    expect(await ui.find({ type: 'Markdown', text: '1. Build Step 4.\n2. Send the note.' })).toBeDefined()
    expect(await ui.find({ type: 'Markdown', text: '1. Joe\'s review.' })).toBeDefined()
    await ui.unmount()
  }
})

test('pane fallbacks: missing heading is said, never blank; no handoff offers /super-setup', async ($, on) => {
  const { seen } = world(on, { handoff: '# handoff\n\n## Last session\nundated\n' })
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'desktop', component: 'Pane', requestId: 'wse-workspace', props: PANE as any })
  expect(await ui.find({ type: 'Markdown', text: 'handoff.md has no "## P0" heading.' })).toBeDefined()
  expect(await ui.find({ type: 'Markdown', text: 'handoff.md has no "## Blockers" heading.' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'Last session: no date in handoff.md.' })).toBeDefined()
  await ui.unmount()
  expect(seen.fills).toEqual([])
})

test('pane with no handoff.md: "No handoff yet" and a button that fills /super-setup', async ($, on) => {
  const { seen } = world(on, { handoff: null })
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'desktop', component: 'Pane', requestId: 'wse-workspace', props: PANE as any })
  expect(await ui.find({ type: 'Text', text: 'No handoff yet' })).toBeDefined()
  await ui.press({ key: 'wse-setup' })
  await ui.unmount()
  expect(seen.fills).toEqual(['/super-setup'])
  expect(seen.submits).toBe(0)
})

test('pane with a handoff.md that exists but cannot be read: says so, never blank, never "No handoff yet"', async ($, on) => {
  world(on, { readError: 'EACCES: permission denied' })
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'wse-workspace', props: PANE as any })
    expect(await ui.find({ type: 'Text', text: /^handoff\.md could not be read: .*EACCES/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: 'No handoff yet' })).toBeUndefined()
    await ui.unmount()
  }
})
