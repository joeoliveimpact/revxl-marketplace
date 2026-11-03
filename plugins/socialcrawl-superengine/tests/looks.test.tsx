import { expect, mock, test } from 'claude-code/testing'

import { ENDPOINTS, esc, hero } from '../hooks/mod/lib'

// 5a-iii, the Lantern look. The draw sweep (kit rule): every band and Budget pane state is mounted on the desktop
// surface and must draw with no refusal (drawn() rejects with one); the same states on the terminal, and the pane on
// mobile, show every Svg has its plain-text fallback. The world beneath is in memory: no fs, network or process.
const PLUGIN = 'socialcrawl-superengine'
const HOME = 'C:/Users/t'
const RX = `${HOME}/.claude/revxl`
const SID = 'sid-1'
const SF = `${RX}/sessions/socialcrawl-${SID}.json`
const CALLS = `${RX}/socialcrawl-calls.jsonl`
const BF = `${RX}/socialcrawl-budget.json`
const T0 = Date.UTC(2026, 9, 21, 12)
const BAND = { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 100, scroll: { offset: 0, bodyRows: 10 }, view: {} }
const PANE = { title: 'SocialCrawl Budget', isFocused: true, bodyColumns: 48, placement: 'dock', scroll: { offset: 0, bodyRows: 60 }, view: {} }
const OUT = (o: unknown) => ({ exitCode: 0, stdout: JSON.stringify(o) + '\n', stderr: '' })
const line = (o: Record<string, unknown>) => JSON.stringify({ sid: SID, paths: ['instagram/profile'], worst: 1, committed: 1, decision: 'pass', kind: 'under-cap', limit: 500, ...o }) + '\n'
const state = (spent: number) => JSON.stringify({ spent })
const textOf = (el: any) => (el.children ?? []).filter((c: unknown) => typeof c === 'string').join('')

type W = { files?: Record<string, string>; busy?: boolean; balance?: number; fail?: boolean
  /** 5b: the plugin's own JSON files by path from its root, and the answer beneath `$.prompt.submit`. */
  plugin?: Record<string, string>; submit?: (e: any) => unknown
  /** 5c: the hook answer beneath `$.model.complete`; absent, nothing answers it. */
  model?: (e: any) => unknown
  /** 5d: the record line a Bash call appends; with it a stat answers from the files, so the toast's check sees the change. */
  bash?: string }

/** The world beneath the plugin: the guard's files in memory, a fake helper, and another plugin's band below ours. */
function world(on: any, o: W = {}) {
  const files: Record<string, string> = { ...(o.files ?? {}) }
  const norm = (p: string) => p.replace(/\\/g, '/')
  const clock = mock.clock(on, { now: T0 })
  on('env.get', ($: any, e: any) => ({ value: e.name === 'USERPROFILE' ? HOME : undefined }))
  on('session.id', () => ({ value: SID }))
  on('fs.read', ($: any, e: any) => {
    const p = norm(e.path)
    const t = files[p] ?? Object.entries(o.plugin ?? {}).find(([rel]) => p.endsWith(`/${rel}`))?.[1]
    if (o.busy || t === undefined) return { deny: `${o.busy ? 'EBUSY' : 'ENOENT'}: ${p}` }
    return { value: e.as === 'bytes' ? { base64: btoa(String.fromCharCode(...new TextEncoder().encode(t))) } : t }
  })
  on('fs.exists', ($: any, e: any) => ({ value: files[norm(e.path)] !== undefined }))
  on('fs.stat', ($: any, e: any) => {
    const t = o.bash === undefined ? undefined : files[norm(e.path)]
    return t === undefined ? { deny: `ENOENT: ${norm(e.path)}` } : { value: { kind: 'file', size: t.length, mtimeMs: 1, isLink: false } }
  })
  if (o.bash !== undefined) on('tool.call', () => { files[CALLS] = (files[CALLS] ?? '') + o.bash; return { result: { stdout: '', stderr: '', interrupted: false }, text: '' } as never })
  on('process.run', ($: any, e: any) => {
    if (e.argv[2] === 'balance') return { value: OUT({ ok: true, balance: o.balance ?? 4210 }) }
    if (e.argv[2] !== 'budget-write') return { value: OUT({ ok: true }) }
    if (o.fail) return { value: OUT({ ok: false, reason: 'write' }) }
    const p = `${norm(e.argv[3])}/socialcrawl-budget.json`
    let b: Record<string, unknown> = {}
    try { b = JSON.parse(files[p] ?? '{}') } catch { /* a fresh file */ }
    const c = JSON.parse(e.argv[4])
    if ('sessionBudget' in c) { if (c.sessionBudget === null) delete b.sessionBudget; else b.sessionBudget = c.sessionBudget }
    delete b.routines
    files[p] = JSON.stringify(b)
    return { value: OUT({ ok: true, budget: b }) }
  })
  on('prompt.submit', async ($: any, e: any) => (o.submit ? await o.submit(e) : { text: e.text }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.invalidate', ($: any, e: any, next: any) => next(e))
  on('command.register', ($: any, e: any) => ({ value: { command: e.name } }))
  on('session.start', ($: any, e: any) => ({ cwd: e.cwd }))
  on('turn.complete', ($: any, e: any) => ({ text: e.answer }))
  if (o.model) on('model.complete', async ($: any, e: any) => o.model!(e))
  on('ui.render', { component: 'AbovePrompt' }, ($$: any, e: any) => {
    const { Box, Text } = $$.ui.resolve(e)
    return Box({ key: 'lower-band', children: [Text({ children: ['lower band'] })] })
  })
  return clock
}

// ---- A1/A2: the band. Desktop: one Svg pill (its fill the tone's colour, none with no limit), the warning Text when
// one applies, the Budget, Endpoints and Round-up Buttons (5b, 5d). Terminal: the text row, no Svg. The band beneath survives every time.
const BANDS: { name: string; files: Record<string, string>; warn: string | null; alt: string; fill: string | null; text: string }[] = [
  { name: 'normal', files: { [SF]: state(120), [CALLS]: line({ committed: 120 }) }, warn: null, alt: '120 of 500 credits this session', fill: '#62D69A', text: '120 / 500 cr this session' },
  { name: 'near the limit', files: { [SF]: state(460), [CALLS]: line({ committed: 460 }) }, warn: ' · ⚠ 40 cr left', alt: '460 of 500 credits this session', fill: '#F5B14C', text: '460 / 500 cr this session' },
  { name: 'refused', files: { [SF]: state(460), [CALLS]: line({ committed: 460 }) + line({ decision: 'deny', kind: 'over-limit', committed: 460 }) },
    warn: ' · ⚠ last call refused (over-limit)', alt: '460 of 500 credits this session', fill: '#FF5A3C', text: '460 / 500 cr this session' },
  { name: 'no limit', files: { [SF]: state(5), [CALLS]: line({ committed: 5, limit: null }) }, warn: null, alt: '5 credits this session, automatic cap', fill: null, text: '5 cr this session · automatic cap' },
  { name: 'state file only', files: { [SF]: state(0) }, warn: null, alt: '0 credits this session, automatic cap', fill: null, text: '0 cr this session · automatic cap' },
]

for (const surface of ['desktop', 'terminal'] as const) {
  for (const c of BANDS) {
    test(`A1/A2 band draws on ${surface}: ${c.name}`, async ($, on) => {
      world(on, { files: c.files })
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'AbovePrompt', props: BAND as any })
      const t: any = await ui.drawn()   // rejects with the refusal
      expect(t.children.length).toBe(2)
      expect(t.children[0].props.key).toBe('sc-band')
      expect(JSON.stringify(t.children[1])).toContain('lower-band')
      const kids: any[] = t.children[0].children
      expect(kids.filter(k => k.type === 'Button').map(k => [k.props.key, k.props.label, k.props.hotkey])).toEqual([['sc-budget-open', 'Budget', 'd'], ['sc-endpoints-open', 'Endpoints', 'p'], ['sc-roundup-open', 'Round-up', 'r']])
      expect(kids.at(-1).type).toBe('Button')
      expect(kids.filter(k => k.type === 'Text' && textOf(k).includes('⚠')).map(k => [textOf(k), k.props.color])).toEqual(
        c.warn ? [[c.warn, c.name === 'refused' ? 'error' : 'warning']] : [])
      if (surface === 'desktop') {
        expect(kids.map(k => k.type)).toEqual(c.warn ? ['Svg', 'Text', 'Button', 'Button', 'Button'] : ['Svg', 'Button', 'Button', 'Button'])
        expect(kids[0].props.alt).toBe(c.alt)
        const src: string = kids[0].props.source
        expect(src.split('<rect').length - 1).toBe(c.fill ? 2 : 1)
        if (c.fill) expect(src).toContain(`fill="${c.fill}"`)
      } else {
        expect(JSON.stringify(t)).not.toContain('"Svg"')
        expect(kids[0].type).toBe('Text')
        expect(textOf(kids[1])).toBe(` ${c.text}`)
      }
      await ui.unmount()
    })
  }
}

// ---- A1/A3/A4: the Budget pane. Desktop: the hero Svg first. Terminal and mobile: a round subtle Box holding the top
// line, no Svg. The one section is a round subtle Box; Save reads `Save  →` wherever it is drawn.
type PaneCase = { name: string; w: W; start?: boolean; press?: string[]; primaries?: string[]; shows?: string | RegExp; noSave?: boolean }
const PANES: PaneCase[] = [
  { name: 'no file', w: {}, primaries: ['ps-auto', 'save'] },
  { name: 'a preset session', w: { files: { [BF]: '{"sessionBudget":500}' } }, primaries: ['ps-500', 'save'] },
  { name: 'Current: 750', w: { files: { [BF]: '{"sessionBudget":750}' } }, shows: 'Current: 750' },
  { name: 'an old routines block is ignored', w: { files: { [BF]: '{"routines":{"enabled":true,"perRun":1000,"perDay":8000}}' } }, primaries: ['ps-auto', 'save'] },
  { name: 'the D10 warning', w: { balance: 300 }, start: true, press: ['ps-500'], shows: /^⚠ This is above your 300 balance\./ },
  { name: 'the below-spent warning', w: { files: { [SF]: state(260) } }, press: ['ps-250'], shows: /^⚠ This session has already spent 260 cr;/ },
  { name: 'garbled', w: { files: { [BF]: '{"sessionBudget":' } }, shows: "The budget file couldn't be read; saving will replace it." },
  { name: 'read error', w: { busy: true, files: { [BF]: '{"sessionBudget":250}' } }, shows: /couldn't be read just now/, noSave: true },
  { name: 'after Saved', w: { files: { [BF]: '{"sessionBudget":500}' } }, press: ['ps-1000', 'save'], shows: /^Saved\. / },
  { name: 'after Not saved', w: { files: { [BF]: '{"sessionBudget":500}' }, fail: true }, press: ['ps-250', 'save'], shows: /^Not saved: / },
  { name: 'Nothing to save', w: { files: { [BF]: '{"sessionBudget":500}' } }, press: ['save'], shows: /^Nothing to save: / },
]

for (const surface of ['desktop', 'terminal', 'mobile'] as const) {
  for (const c of PANES) {
    test(`A1/A3 Budget pane draws on ${surface}: ${c.name}`, async ($, on) => {
      const clock = world(on, c.w)
      if (c.start) {
        await $.session.start({ surface: 'terminal', isInteractive: true, cwd: 'C:/ws' } as any)
        await clock.settle()
      }
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-budget', props: PANE as any })
      for (const key of c.press ?? []) await ui.press({ key })
      const t: any = await ui.drawn()   // rejects with the refusal
      const top = t.children[0]
      if (surface === 'desktop') {
        expect(top.type).toBe('Svg')
        expect(top.props.alt).toMatch(/^This session .+\. Total balance .+\.$/)
        expect(JSON.stringify(t).split('"Svg"').length - 1).toBe(1)
      } else {
        expect([top.type, top.props.borderStyle, top.props.borderColor, top.props.paddingX]).toEqual(['Box', 'round', 'subtle', 1])
        expect(top.children.map((k: any) => k.type)).toEqual(['Text'])
        expect(textOf(top.children[0])).toMatch(/^Balance .+ · this session /)
        expect(JSON.stringify(t)).not.toContain('"Svg"')
      }
      for (const key of ['session']) {
        const b = await ui.find({ key })
        expect([b?.type, b?.props.borderStyle, b?.props.borderColor, b?.props.paddingX]).toEqual(['Box', 'round', 'subtle', 1])
      }
      const save = await ui.find({ type: 'Button', key: 'save' })
      if (c.noSave) expect(save).toBeUndefined()
      else expect(save?.props.label).toBe('Save  →')
      if (c.primaries) expect((await ui.findAll({ type: 'Button' })).filter((b: any) => b.props.variant === 'primary').map((b: any) => b.key)).toEqual(c.primaries)
      if (c.shows) expect(await ui.find({ type: 'Text', text: c.shows })).toBeDefined()
      await ui.unmount()
    })
  }
}

test("S2: the hero's alt carries the top line's facts in words; the limit is the coral part", async ($, on) => {
  const clock = world(on, { files: { [SF]: state(120), [CALLS]: line({ committed: 120 }) } })
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: 'C:/ws' } as any)
  await clock.settle()
  await clock.advance(2 * 60_000)
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'desktop', component: 'Pane', requestId: 'sc-budget', props: PANE as any })
  const top: any = (await ui.drawn() as any).children[0]
  expect(top.props.alt).toBe('This session 120 of 500 credits. Total balance 4,210 credits, 2 min ago.')
  expect(top.props.source).toContain('>THIS SESSION<')
  expect(top.props.source).toContain('fill="#FF5A3C">500 cr</tspan>')
  expect(top.props.source).toContain('>Total balance 4,210 cr · 2 min ago<')
})

// ---- A6: escaping. A hostile string in an Svg text slot (the age) comes out as entities, never as markup.
test('A6: a hostile age in the hero card is escaped; every & in the markup starts a well-formed entity', () => {
  const bad = `<script>&'"`
  expect(esc(bad)).toBe('&lt;script&gt;&amp;&#39;&quot;')
  const { source } = hero(1, 2, 3, bad)
  expect(source).not.toContain('<script')
  expect(source).toContain('Total balance 3 cr · &lt;script&gt;&amp;&#39;&quot;<')
  expect(source.match(/&(?!(amp|lt|gt|quot|#39);)/g)).toBeNull()
})

// ---- 5b A10: the Endpoints and Combos tabs keep the kit's rules on every surface and in every state: each draws with no
// refusal (drawn() rejects with one), every Button a plain string label with no children, every card a round subtle
// Box, no Svg (so no hex), and the box an Input except on mobile. The JSON files are synthetic; the world is in memory.
const TAB_COSTS: Record<string, unknown> = Object.fromEntries(ENDPOINTS.map(x => [x.call, { credits: 0, range: [1, 5] }]))
const TAB_PK = { rows: [
  { id: 'website', options: [{ id: 'web-scrape', label: 'One web page', quote: { low: 1, high: 5 }, ceiling: 5 }, { id: 'site-teardown', label: 'Site teardown', curated: 'site-teardown' }] },
  { id: 'free_web', options: [] },
  { id: 'people_saying', options: [{ id: 'voice-of-customer', label: 'Voice-of-Customer mining, a label long enough to wrap in a 48-column dock', curated: 'voice-of-customer' }] },
] }
const TAB_CW = { workflows: [{ id: 'site-teardown', quote: { low: 2, high: 5 }, ceiling: 5 }, { id: 'voice-of-customer', quote: { low: 25, high: 1050 }, ceiling: 120 }] }
const tabFiles = (costs: unknown = TAB_COSTS, cw: unknown = TAB_CW) => ({ 'hooks/costs.json': JSON.stringify(costs),
  'skills/research-plays/references/packages.json': JSON.stringify(TAB_PK), 'skills/research-plays/curated-workflows.json': JSON.stringify(cw) })
type TabCase = { name: string; costs?: unknown; cw?: unknown; type?: string; press?: string; submit?: 'sleep' | 'drop'; shows: { text: string | RegExp } | { key: string; label: string } }
const TABS: Record<'sc-endpoints' | 'sc-combos', TabCase[]> = {
  'sc-endpoints': [
    { name: 'idle', shows: { key: 'instagram-profile', label: 'Profile · 1–5 cr' } },
    { name: 'typed', type: 'nike', shows: { key: 'tiktok-ads-top', label: 'Top ads · 1–5 cr' } },
    { name: 'queued', type: 'nike', press: 'instagram-profile', submit: 'sleep', shows: { key: 'instagram-profile', label: 'Queued · Profile' } },
    { name: 'dropped', type: 'nike', press: 'instagram-profile', submit: 'drop', shows: { text: 'Not sent: busy' } },
    { name: 'no-price', costs: { ...TAB_COSTS, 'GET tiktok/ads/top': { credits: 1, range: null } }, shows: { key: 'tiktok-ads-top', label: 'Top ads · no price' } },
    { name: 'empty-target', press: 'instagram-profile', shows: { text: 'Type a target first.' } },
    { name: 'post-stats-refused', type: 'https://www.tiktok.com/@a/video/1', press: 'prism-post-stats', shows: { text: "Post stats can't take that URL from here. Ask Claude in the chat." } },
  ],
  'sc-combos': [
    { name: 'idle', shows: { key: 'people_saying:voice-of-customer', label: 'Run · 25–120 cr' } },
    { name: 'queued', press: 'website:web-scrape', submit: 'sleep', shows: { key: 'website:web-scrape', label: 'Queued · One web page' } },
    { name: 'dropped', press: 'website:web-scrape', submit: 'drop', shows: { text: 'Not sent: busy' } },
    { name: 'no-price', cw: { workflows: [TAB_CW.workflows[0]] }, shows: { key: 'people_saying:voice-of-customer', label: 'Run · no price' } },
  ],
}
const walk = (el: any, f: (el: any) => void) => { f(el); for (const c of el?.children ?? []) if (c && typeof c === 'object') walk(c, f) }

for (const surface of ['desktop', 'terminal', 'vscode', 'mobile'] as const) {
  for (const id of ['sc-endpoints', 'sc-combos'] as const) {
    for (const c of TABS[id]) {
      test(`A10 ${id} draws on ${surface}: ${c.name}`, async ($, on) => {
        const at: { clock?: any } = {}
        at.clock = world(on, { plugin: tabFiles(c.costs, c.cw), submit: async (e: any) => {
          if (c.submit === 'drop') return { drop: 'busy' }
          await at.clock.sleep(5000)
          return { text: e.text }
        } })
        const mount = (s: typeof surface) => $.ui.mount({ plugin: PLUGIN, surface: s, component: 'Pane', requestId: id, props: { ...PANE, title: id } as any })
        if (c.type !== undefined) {   // typed where there is a box; the target is the module's, so mobile draws with it too
          const desk = await mount('desktop')
          await desk.input({ key: 'target', text: c.type })
          await desk.unmount()
        }
        const ui = await mount(surface)
        const pressed = c.press ? ui.press({ key: c.press }) : null
        await at.clock.settle()
        const t: any = await ui.drawn()   // rejects with the refusal
        expect(JSON.stringify(t)).not.toContain('"Svg"')
        expect(JSON.stringify(t).includes('"Input"')).toBe(id === 'sc-endpoints' && surface !== 'mobile')
        walk(t, el => {
          if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
          if (el.type === 'Box' && el.props?.key) expect([el.props.borderStyle, el.props.borderColor, el.props.paddingX]).toEqual(['round', 'subtle', 1])
        })
        if ('text' in c.shows) expect(await ui.find({ type: 'Text', text: c.shows.text })).toBeDefined()
        else expect((await ui.find({ type: 'Button', key: c.shows.key }))?.props.label).toBe(c.shows.label)
        await at.clock.advance(5000)
        await pressed
        await ui.unmount()
      })
    }
  }
}

// ---- 5c A11: the Suggested tab on every surface and in every state draws with no refusal; every Button is a plain
// string label (a suggestion's Button is the real tab's own), every card a round subtle Box, no Svg, the reason a Text
// with no line break, the target box only where a shown Endpoints suggestion takes a target (never on mobile), and the
// token footer always. Every model call is faked beneath the plugin.
const SUG_USE = { input_tokens: 1, output_tokens: 1, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 }
const SUG_ANSWER = (ids: string[]) => ({ isAnswered: true, text: ids.map(id => JSON.stringify({ id, why: `why ${id}\nsecond line` })).join('\n'), usage: SUG_USE })
const THREE = ['instagram-profile', 'website:web-scrape', 'tiktok-ads-top']
const SIX = [...THREE, 'people_saying:voice-of-customer', 'tiktok-trending', 'youtube-shorts-trending']
type SugCase = { name: string; outs?: unknown[]; sleep?: boolean; again?: boolean; keys: string[]; shows?: string; input: boolean }
const SUG_CASES: SugCase[] = [
  { name: 'not opened yet', keys: [], shows: 'Press Suggested in the Endpoints tab to get suggestions.', input: false },
  { name: 'loading', outs: [SUG_ANSWER(['instagram-profile'])], sleep: true, keys: [], shows: 'Finding suggestions…', input: false },
  { name: '1 item', outs: [SUG_ANSWER(['instagram-profile'])], keys: ['instagram-profile'], input: true },
  { name: '3 items', outs: [SUG_ANSWER(THREE)], keys: THREE, input: true },
  { name: '6 items', outs: [SUG_ANSWER([...SIX, 'reddit-omni-search'])], keys: SIX, input: true },
  { name: 'an error, the last set kept', outs: [SUG_ANSWER(THREE), { isAnswered: false, reason: 'api-error', status: 429, error: 'rate_limit', usage: { ...SUG_USE, input_tokens: 0, output_tokens: 0 } }],
    again: true, keys: THREE, shows: "Couldn't refresh: rate_limit", input: true },
  { name: 'no new suggestions', outs: [SUG_ANSWER(['not-a-button'])], keys: [], shows: 'No new suggestions', input: false },
]

for (const surface of ['desktop', 'terminal', 'vscode', 'mobile'] as const) {
  for (const c of SUG_CASES) {
    test(`A11 sc-suggested draws on ${surface}: ${c.name}`, async ($, on) => {
      const outs = [...(c.outs ?? [])]
      const at: { clock?: any } = {}
      at.clock = world(on, { plugin: tabFiles(), model: async () => {
        if (c.sleep) await at.clock.sleep(5000)
        return { value: outs.shift() }
      } })
      if (c.outs) {
        const ends = await $.ui.mount({ plugin: PLUGIN, surface: 'desktop', component: 'Pane', requestId: 'sc-endpoints', props: { ...PANE, title: 'sc-endpoints' } as any })
        await ends.press({ key: 'sc-suggested-open' })
        await ends.unmount()
        await at.clock.settle()
      }
      if (c.again) {
        await $.prompt.submit({ text: 'a new direction', wait: false, origin: { kind: 'composer' } } as any)
        await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as any)
        await at.clock.settle()
      }
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-suggested', props: { ...PANE, title: 'SocialCrawl Suggested' } as any })
      const t: any = await ui.drawn()   // rejects with the refusal
      expect(JSON.stringify(t)).not.toContain('"Svg"')
      expect(JSON.stringify(t).includes('"Input"')).toBe(c.input && surface !== 'mobile')
      walk(t, el => {
        if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
        if (el.type === 'Box' && el.props?.key) expect([el.props.borderStyle, el.props.borderColor, el.props.paddingX]).toEqual(['round', 'subtle', 1])
        if (el.type === 'Text') expect(textOf(el)).not.toMatch(/[\n\r]/)
      })
      expect((await ui.findAll({ type: 'Button' })).map((b: any) => b.key)).toEqual(c.keys)
      expect((await ui.findAll({ type: 'Text', text: /^why / })).map((x: any) => x.text)).toEqual(c.keys.map(k => `why ${k} second line`))
      if (c.shows) expect(await ui.find({ type: 'Text', text: c.shows })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: /^Suggestions used \d+ tokens this session$/ })).toBeDefined()
      await at.clock.advance(5000)
      await ui.unmount()
    })
  }
}

// ---- 5d A14: the Round-up on every surface and in every state draws with no refusal: the hero Svg on desktop alone,
// every Button a plain string label, every keyed card a round subtle Box, no Text with a line break, a file: Link on
// the terminal only and only for an absolute path (R2-6), and both dim notes always. The record is in memory.
const RU_REC = line({ ts: '2026-10-21T12:01:00.000Z' }) + line({ ts: '2026-10-21T12:02:00.000Z', paths: ['/v1/tiktok/ads/top'], worst: 100, decision: 'deny', kind: 'over-limit' })
type RuCase = { name: string; files?: Record<string, string>; bash?: string; command?: string; queued?: boolean; shows: string }
const RU_CASES: RuCase[] = [
  { name: 'no calls yet', shows: 'No paid calls yet.' },
  { name: 'paid and refused', files: { [SF]: state(1), [CALLS]: RU_REC }, shows: 'Refused, not counted' },
  { name: 'saved files present and gone', files: { [SF]: state(1), [CALLS]: '', [`${HOME}/sc-a.json`]: '{}' }, bash: line({}),
    command: 'curl -s "$U" -o ~/sc-a.json && curl -s "$U" -o ~/sc-gone.json && curl -s "$U" > rel.json', shows: 'Saved files' },
  { name: 'routine found', files: { [SF]: state(1), [CALLS]: line({ sid: 'r1', decision: 'allow', committed: 40, routine: true }) + line({ sid: 'r1', decision: 'deny', kind: 'day-limit', routine: true }) }, shows: 'Refused: 1 day-limit' },
  { name: 'routine none', files: { [SF]: state(1), [CALLS]: line({ sid: 'plain' }) }, shows: 'No routine run found.' },
  { name: 'queued', files: { [SF]: state(1), [CALLS]: RU_REC }, queued: true, shows: 'Refused, not counted' },
]

for (const surface of ['desktop', 'terminal', 'vscode', 'mobile'] as const) {
  for (const c of RU_CASES) {
    test(`A14 sc-roundup draws on ${surface}: ${c.name}`, async ($, on) => {
      const at: { clock?: any } = {}
      at.clock = world(on, { files: c.files, bash: c.bash, submit: async (e: any) => {
        await at.clock.sleep(5000)
        return { text: e.text }
      } })
      if (c.command) await $.tool.call({ tool: 'Bash', command: c.command } as any)
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-roundup', props: { ...PANE, title: 'SocialCrawl Round-up' } as any })
      const pressed = c.queued ? ui.press({ key: 'sc-roundup-summarize' }) : null
      await at.clock.settle()
      const t: any = await ui.drawn()   // rejects with the refusal
      expect(JSON.stringify(t).split('"Svg"').length - 1).toBe(surface === 'desktop' ? 1 : 0)
      expect(JSON.stringify(t)).not.toContain('"Input"')
      const links: [string, string][] = []
      walk(t, el => {
        if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
        if (el.type === 'Box' && el.props?.key) expect([el.props.borderStyle, el.props.borderColor, el.props.paddingX]).toEqual(['round', 'subtle', 1])
        if (el.type === 'Text') expect(textOf(el)).not.toMatch(/[\n\r]/)
        if (el.type === 'Link') links.push([el.props.href, el.props.label])
      })
      // R2-6: a file: Link on the terminal for an absolute path; Text everywhere else, and for the relative rel.json.
      expect(links).toEqual(c.command && surface === 'terminal' ? [['file:///C:/Users/t/sc-a.json', 'sc-a.json'], ['file:///C:/Users/t/sc-gone.json', 'sc-gone.json']] : [])
      if (surface !== 'terminal') expect(JSON.stringify(t)).not.toMatch(/"Link"|file:/)
      if (c.command) for (const name of ['sc-a.json', 'sc-gone.json', 'rel.json']) expect(JSON.stringify(t)).toContain(`"${name}"`)
      if (c.command) expect((await ui.findAll({ type: 'Text', text: / · gone$/ })).length).toBe(2)
      expect((await ui.find({ type: 'Button', key: 'sc-roundup-summarize' }))?.props.label).toBe(c.queued ? 'Queued · Summarize' : 'Summarize  →')
      for (const shown of [c.shows, "Credits are the guard's quotes; the real charge is in the debrief."]) {
        expect(await ui.find({ type: 'Text', text: shown })).toBeDefined()
      }
      await at.clock.advance(5000)
      await pressed
      await ui.unmount()
    })
  }
}
