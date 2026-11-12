import { expect, mock, test } from 'claude-code/testing'
import * as lib from '../hooks/mod/lib'
import M6_REAL from './costs-real'

import { ENDPOINTS, HOW_IT_WORKS, STYLES, bandDial, chip, detailCards, esc, eyebrow, rowCard, sessionCard } from '../hooks/mod/lib'

// The Lantern look. The draw sweep mounts the band and each of the five tabs on the desktop
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
const PANE = { title: 'SocialCrawl', isFocused: true, bodyColumns: 48, placement: 'dock', scroll: { offset: 0, bodyRows: 60 }, view: {} }
const OUT = (o: unknown) => ({ exitCode: 0, stdout: JSON.stringify(o) + '\n', stderr: '' })
const line = (o: Record<string, unknown>) => JSON.stringify({ sid: SID, paths: ['instagram/profile'], worst: 1, committed: 1, decision: 'pass', kind: 'under-cap', limit: 500, ...o }) + '\n'
const state = (spent: number, usage?: number, full?: number) => JSON.stringify({ spent, usage, full })
const settle = (o: Record<string, unknown> = {}) => JSON.stringify({ ts: '2026-10-15T12:00:00Z', sid: SID,
  decision: 'settle', kind: 'give-back', committed: 1, was: 17, usage: 1, full: 0, over: [], ...o }) + '\n'
const textOf = (el: any) => (el.children ?? []).filter((c: unknown) => typeof c === 'string').join('')

for (const surface of ['desktop', 'terminal', 'mobile'] as const) for (const style of STYLES) {
  test(`EGM B3a: monitor PATCH is text only under request pricing on ${surface}, ${style}`, async ($, on) => {
    world(on, { store: { appearance: style }, plugin: { 'hooks/costs.json': JSON.stringify(M6_REAL) } })
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
    await ui.press({ key: 'tab-Endpoints' })
    await ui.press({ key: 'more-Search' })
    const row = lib.moreOf(M6_REAL, ['web']).find(r => r.call === 'PATCH web/monitors/{monitor_id}')
    expect(row).toBeDefined()
    expect(await ui.find({ type: 'Button', key: row!.key })).toBeUndefined()
    const depends = await ui.find({ type: 'Text', text: `${row!.name} · depends` })
    expect(depends).toBeDefined()
    // Find the heading and row in the same section, not merely somewhere in the pane.
    const sections: any[] = []
    walk(await ui.drawn(), el => {
      if (el.type === 'Box' && el.children?.some((c: any) => c.type === 'Text' && textOf(c) === 'Price depends on the request')) sections.push(el)
    })
    expect(sections.length).toBe(1)
    expect(JSON.stringify(sections[0])).toContain(`${row!.name} · depends`)
    const headingAt = sections[0].children.findIndex((c: any) => c.type === 'Text' && textOf(c) === 'Price depends on the request')
    const rowAt = sections[0].children.findIndex((c: any) => c.type === 'Text' && textOf(c) === `${row!.name} · depends`)
    expect(rowAt).toBeGreaterThan(headingAt)
    expect((await ui.findAll({ type: 'Button' })).some((b: any) => JSON.stringify(b).includes(row!.name))).toBe(false)
    await ui.unmount()
  })
}

test('M6 S1: real Select options fit 64; eight extra platforms or two extra sites cross the limit', () => {
  const m6 = lib as any
  const platform = m6.platformOptions?.(M6_REAL)
  const site = m6.siteOptions?.(M6_REAL)
  expect(platform).toBeDefined()
  expect(site).toBeDefined()
  expect(platform.length).toBe(57)
  expect(site.length).toBe(63)
  const tree = (options: any[]) => ({ type: 'Select', props: { options } })
  selectsOk(tree(platform))
  selectsOk(tree(site))
  const extra = (n: number) => {
    const platforms = Object.fromEntries(Array.from({ length: n }, (_, i) => [`m6_extra_${i}`, {}]))
    const routes = Object.fromEntries(Object.keys(platforms).map(p => [`GET ${p}/one`, { range: [1, 1], desc: 'One call' }]))
    return { ...M6_REAL, ...routes, _platforms: { ...M6_REAL._platforms, ...platforms } }
  }
  const tooManyPlatforms = m6.platformOptions(extra(8))
  const tooManySites = m6.siteOptions(extra(2))
  expect(tooManyPlatforms.length).toBe(65)
  expect(tooManySites.length).toBe(65)
  expect(() => selectsOk(tree(tooManyPlatforms))).toThrow()
  expect(() => selectsOk(tree(tooManySites))).toThrow()
})

for (const surface of ['desktop', 'terminal', 'mobile'] as const) {
  for (const style of STYLES) for (const transcripts of ['block', 'allow'] as const) {
    test(`M6 R: More rows, picked platform and closed/full/family glossary draw on ${surface}, ${style}, ${transcripts}`, async ($, on) => {
      const clock = world(on, { files: { [BF]: JSON.stringify({ transcripts }) }, store: { appearance: style }, plugin: { 'hooks/costs.json': JSON.stringify(M6_REAL) } })
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
      const capture = async () => {
        const t: any = await ui.drawn()
        selectsOk(t)
        walk(t, el => {
          if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
          if (surface !== 'desktop') expect(el.type).not.toBe('Svg')
        })
        return t
      }
      await ui.press({ key: 'tab-Endpoints' })
      await capture()
      const lookup = await ui.find({ key: style === 'Cards' ? 'card-prism-lookup' : surface === 'desktop' && style === 'Lantern rows' ? 'row-prism-lookup' : 'prism-lookup' })
      expect(JSON.stringify(lookup)).toContain('1–5 cr · varies')
      expect((await ui.find({ key: 'more-Instagram' }))?.props.label).toBe('More options · 34')
      for (const group of ['Instagram', 'Search']) {
        await ui.press({ key: `more-${group}` })
        await capture()
      }
      const m6 = lib as any
      const rows = m6.moreOf?.(M6_REAL, ['prism', 'search', 'tavily', 'perplexity', 'web'])
      expect(rows).toBeDefined()
      const keys = (await ui.findAll({ type: 'Button' })).map((b: any) => b.props.key).filter((k: string) => rows.some((r: any) => r.key === k))
      expect(keys).toEqual(['priced', 'free'].flatMap(kind => rows.filter((r: any) => r.kind === kind).map((r: any) => r.key)))
      for (const heading of ['Free calls', 'Price depends on the request']) expect((await ui.find({ type: 'Text', text: heading }))?.props.dimColor).toBe(true)
      const allRows = [...m6.moreOf(M6_REAL, ['instagram']), ...rows]
      for (const row of allRows) {
        if (row.kind === 'unpriced') {
          expect(await ui.find({ type: 'Button', key: row.key })).toBeUndefined()
          expect(await ui.find({ type: 'Text', text: `${row.name} · depends` })).toBeDefined()
          continue
        }
        const name = `${row.transcript && transcripts === 'block' ? '🔒 ' : ''}${row.name}`
        const price = row.price ?? 'no price'
        const button = await ui.find({ key: row.key })
        expect(button?.type).toBe('Button')
        if (style === 'Cards') {
          const card = await ui.find({ key: `card-${row.key}` })
          expect(card?.children.map((c: any) => c.type)).toEqual(['Text', 'Text', 'Button'])
          expect(textOf(card.children[0])).toBe(name)
          expect(textOf(card.children[1])).toBe(price)
          expect(button.props.label).toBe('Run  →')
        } else if (style === 'Lantern rows' && surface === 'desktop') {
          const card = await ui.find({ key: `row-${row.key}` })
          expect(card?.children.map((c: any) => c.type)).toEqual(['Svg', 'Button'])
          expect(card.children[0].props.alt).toBe(`${name}, ${price}`)
          expect(button.props.label).toBe('Run')
        } else expect(button.props.label).toBe(`${name} · ${price}`)
      }
      // Check Select bounds after a locked/unlocked press and a free press.
      for (const call of ['GET instagram/media/transcript', 'GET prism/brief-check', 'GET web/monitors']) {
        const row = allRows.find((r: any) => r.call === call)
        expect(row).toBeDefined()
        await ui.press({ key: row.key })
        await clock.settle()
        await capture()
      }
      // H-80 / EGM B3: cover all seven request-priced rows, including economy in More platforms.
      let dependsRows = rows.filter((r: any) => r.kind === 'unpriced').length
      expect((await ui.findAll({ type: 'Text', text: "Ask Claude for these; the pane can't price them, and the guard counts some of them at 0, so have Claude state the price first." })).length).toBe(1)
      await ui.select({ key: 'more-platform', value: 'economy' })
      await capture()
      for (const row of m6.moreOf(M6_REAL, ['economy']).filter((r: any) => r.kind === 'unpriced')) {
        expect(await ui.find({ type: 'Button', key: row.key })).toBeUndefined()
        expect(await ui.find({ type: 'Text', text: `${row.name} · depends` })).toBeDefined()
        dependsRows++
      }
      expect(dependsRows).toBe(7)
      expect((await ui.findAll({ type: 'Text', text: "Ask Claude for these; the pane can't price them, and the guard counts some of them at 0, so have Claude state the price first." })).length).toBe(2)
      expect(await ui.find({ key: 'more-platform' })).toBeDefined()
      for (const value of ['amazon', 'github']) {
        await ui.select({ key: 'more-platform', value })
        const picked = await capture()
        for (const row of m6.moreOf(M6_REAL, [value])) expect(JSON.stringify(picked)).toContain(row.key)
      }
      await ui.press({ key: 'more-Instagram' })
      await capture()
      await ui.press({ key: 'more-Instagram' })
      await capture()
      await ui.press({ key: 'tab-Settings' })
      await clock.settle()
      await capture()
      expect((await ui.find({ key: 'sites-toggle' }))?.props.label).toBe('Show sites and sources')
      expect((await ui.findAll({ type: 'Select' })).length).toBe(0)
      await ui.press({ key: 'sites-toggle' })
      await capture()
      for (const value of ['*', 'google', 'tavily']) {
        await ui.select({ key: 'site', value })
        const t = await capture()
        const expected = value === '*' ? Object.keys(M6_REAL._platforms) : value === 'google' ? ['google', 'google_news', 'google_trends', 'google_shopping'] : ['tavily']
        for (const id of Object.keys(M6_REAL._platforms)) expect(JSON.stringify(t).includes(m6.SITES[id].line)).toBe(expected.includes(id))
      }
      await ui.press({ key: 'sites-toggle' })
      await capture()
      await ui.unmount()
    })
  }
}

type W = { files?: Record<string, string>; busy?: boolean; balance?: number; fail?: boolean
  routes?: string[] | 'fail'; store?: Record<string, any>
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
  mock.store(on, o.store)
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
    if (e.argv[2] === 'routes') return { value: o.routes === undefined || o.routes === 'fail' ? { exitCode: 0, stdout: '', stderr: '' } : OUT({ ok: true, routes: o.routes }) }
    if (e.argv[2] !== 'budget-write') return { value: OUT({ ok: true }) }
    if (o.fail) return { value: OUT({ ok: false, reason: 'write' }) }
    const p = `${norm(e.argv[3])}/socialcrawl-budget.json`
    let b: Record<string, unknown> = {}
    let garbled = files[p] !== undefined
    try { const x = JSON.parse(files[p] ?? '{}'); if (x && typeof x === 'object' && !Array.isArray(x)) { b = x; garbled = false } } catch { /* a fresh file */ }
    const c = JSON.parse(e.argv[4])
    if ('sessionBudget' in c) { if (c.sessionBudget === null) delete b.sessionBudget; else b.sessionBudget = c.sessionBudget }
    if ('transcripts' in c) b.transcripts = c.transcripts
    else if (garbled) b.transcripts = 'block'
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

// ---- A1/A2: the band. Desktop: one Svg dial, warning Text when one applies, and the Open Button.
// Terminal: the text row, no Svg. The band beneath survives every time.
const BANDS: { name: string; files: Record<string, string>; warn: string | null; alt: string; fill: string | null; text: string }[] = [
  { name: 'normal', files: { [SF]: state(120), [CALLS]: line({ committed: 120 }) }, warn: null, alt: '380 of 500 credits left this session; Usage: none read yet', fill: '#FF5A3C', text: '380 cr left of 500' },
  { name: 'near the limit', files: { [SF]: state(460), [CALLS]: line({ committed: 460 }) }, warn: ' · ⚠ 40 cr left', alt: '40 of 500 credits left this session; Usage: none read yet', fill: '#F5B14C', text: '40 cr left of 500' },
  { name: 'refused', files: { [SF]: state(460), [CALLS]: line({ committed: 460 }) + line({ decision: 'deny', kind: 'over-limit', committed: 460 }) },
    warn: ' · ⚠ last call refused: over the limit', alt: '40 of 500 credits left this session; Usage: none read yet', fill: '#FF5A3C', text: '40 cr left of 500' },
  { name: 'no limit', files: { [SF]: state(5), [CALLS]: line({ committed: 5, limit: null }) }, warn: null, alt: '5 credits counted this session, automatic cap; Usage: none read yet', fill: null, text: '5 cr counted this session · automatic cap' },
  { name: 'state file only', files: { [SF]: state(0) }, warn: null, alt: '0 credits counted this session, automatic cap; Usage: none read yet', fill: null, text: '0 cr counted this session · automatic cap' },
]

for (const surface of ['desktop', 'terminal'] as const) {
  for (const c of BANDS) {
    test(`A1/A2 band draws on ${surface}: ${c.name}`, async ($, on) => {
      world(on, { files: c.files })
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'AbovePrompt', props: BAND as any })
      const t: any = await ui.drawn()   // rejects with the refusal
      selectsOk(t)
      expect(t.children.length).toBe(2)
      expect(t.children[0].props.key).toBe('sc-band')
      expect(JSON.stringify(t.children[1])).toContain('lower-band')
      const kids: any[] = t.children[0].children
      expect(kids.filter(k => k.type === 'Button').map(k => [k.props.key, k.props.label, k.props.hotkey])).toEqual([['sc-open', 'Open SocialCrawl', 'd']])
      expect(kids.at(-1).type).toBe('Button')
      expect(kids.filter(k => k.type === 'Text' && textOf(k).includes('⚠')).map(k => [textOf(k), k.props.color])).toEqual(
        c.warn ? [[c.warn, c.name === 'refused' ? 'error' : 'warning']] : [])
      if (surface === 'desktop') {
        expect(kids.map(k => k.type)).toEqual(c.warn ? ['Svg', 'Text', 'Button'] : ['Svg', 'Button'])
        expect(kids[0].props.alt).toBe(c.alt)
        const src: string = kids[0].props.source
        expect(src.split('<circle').length - 1).toBe(c.fill ? 2 : 1)
        if (c.fill) expect(src).toContain(`stroke="${c.fill}"`)
      } else {
        expect(JSON.stringify(t).includes('"Svg"')).toBe(surface === 'desktop')
        expect(kids[0].type).toBe('Text')
        expect(textOf(kids[1])).toBe(` ${c.text} · Usage: none read yet`)
      }
      await ui.unmount()
    })
  }
}

// ---- A1/A3/A4: Settings. Desktop: two card Svgs first. Terminal and mobile: three round subtle boxes. The one section is a round subtle Box; Save reads `Save  →` wherever it is drawn.
type PaneCase = { name: string; w: W; headline: string; start?: boolean; press?: string[]; primaries?: string[]; shows?: string | RegExp; noSave?: boolean }
const PANES: PaneCase[] = [
  { name: 'no file', w: {}, headline: '0 cr counted · automatic cap', primaries: ['ps-auto', 'save'] },
  { name: 'a preset session', w: { files: { [BF]: '{"sessionBudget":500}' } }, headline: '0 of 500 cr counted', primaries: ['ps-500', 'save'] },
  { name: 'Custom: 750 cr', w: { files: { [BF]: '{"sessionBudget":750}' } }, headline: '0 of 750 cr counted', shows: 'Custom: 750 cr' },
  { name: 'an old routines block is ignored', w: { files: { [BF]: '{"routines":{"enabled":true,"perRun":1000,"perDay":8000}}' } }, headline: '0 cr counted · automatic cap', primaries: ['ps-auto', 'save'] },
  { name: 'the D10 warning', w: { balance: 300 }, headline: '0 cr counted · automatic cap', start: true, press: ['ps-500'], shows: /^⚠ This is above your 300 cr balance\./ },
  { name: 'the below-spent warning', w: { files: { [SF]: state(260) } }, headline: '260 cr counted · automatic cap', press: ['ps-250'], shows: /^⚠ This session has already counted 260 cr;/ },
  { name: 'garbled', w: { files: { [BF]: '{"sessionBudget":' } }, headline: '0 cr counted · automatic cap', shows: "The settings file couldn't be read; saving will replace it." },
  { name: 'read error', w: { busy: true, files: { [BF]: '{"sessionBudget":250}' } }, headline: '0 cr counted · automatic cap', shows: /couldn't be read just now/, noSave: true },
  { name: 'after Saved', w: { files: { [BF]: '{"sessionBudget":500}' } }, headline: '0 of 1,000 cr counted', press: ['ps-1000', 'save'], shows: /^Saved\. / },
  { name: 'after Not saved', w: { files: { [BF]: '{"sessionBudget":500}' }, fail: true }, headline: '0 of 500 cr counted', press: ['ps-250', 'save'], shows: /^Not saved: / },
  { name: 'Nothing to save', w: { files: { [BF]: '{"sessionBudget":500}' } }, headline: '0 of 500 cr counted', press: ['save'], shows: /^Nothing to save: / },
]

for (const surface of ['desktop', 'terminal', 'mobile'] as const) {
  for (const c of PANES) {
    test(`A1/A3 Settings tab draws on ${surface}: ${c.name}`, async ($, on) => {
      const clock = world(on, c.w)
      if (c.start) {
        await $.session.start({ surface: 'terminal', isInteractive: true, cwd: 'C:/ws' } as any)
        await clock.settle()
      }
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
      await ui.press({ key: 'tab-Settings' })
      for (const key of c.press ?? []) await ui.press({ key })
      const t: any = await ui.drawn()   // rejects with the refusal
      selectsOk(t)
      const top = t.children[0]
      if (surface === 'desktop') {
        expect(top.type).toBe('Svg')
        expect(top.props.alt).toMatch(/^This session: .+\.$/)
        expect(top.props.source.replace(/<[^>]*>/g, '')).toContain(c.headline)
        expect(JSON.stringify(t).split('"Svg"').length - 1).toBe(7)
      } else {
        expect([top.type, top.props.borderStyle, top.props.borderColor, top.props.paddingX]).toEqual(['Box', 'round', 'subtle', 1])
        expect(top.children.map((k: any) => k.type)).toEqual(['Text', 'Text'])
        expect(textOf(top.children[0])).toBe(c.headline)
        expect(JSON.stringify(t).includes('"Svg"')).toBe(surface === 'desktop')
      }
      for (const key of ['session', 'transcripts', 'appearance', 'help']) {
        const b = await ui.find({ key })
        expect([b?.type, b?.props.borderStyle, b?.props.borderColor, b?.props.paddingX]).toEqual(['Box', 'round', 'subtle', 1])
      }
      const save = await ui.find({ type: 'Button', key: 'save' })
      if (c.noSave) expect(save).toBeUndefined()
      else expect(save?.props.label).toBe('Save  →')
      if (c.primaries) expect((await ui.findAll({ type: 'Button' })).filter((b: any) => b.props.variant === 'primary' && (b.key.startsWith('ps-') || b.key === 'save')).map((b: any) => b.key)).toEqual(c.primaries)
      if (c.shows) expect(await ui.find({ type: 'Text', text: c.shows })).toBeDefined()
      await ui.unmount()
    })
  }
}

test('S2: the session and detail cards carry the guard and balance facts in words', async ($, on) => {
  const clock = world(on, { files: { [SF]: state(120), [CALLS]: line({ committed: 120 }) } })
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: 'C:/ws' } as any)
  await clock.settle()
  await clock.advance(2 * 60_000)
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'desktop', component: 'Pane', requestId: 'sc-pane', props: PANE as any })
  const t: any = await ui.drawn()
  selectsOk(t)
  expect(t.children[0].props.alt).toBe('This session: 120 of 500 cr counted. 380 cr left before the limit.')
  expect(t.children[0].props.source).toContain('>THIS SESSION<')
  expect(t.children[1].props.alt).toBe("Usage: none read yet. 1 call · 0 refused on record. Account balance: 4,210 cr, checked 2 min ago.")
  await ui.unmount()
})

// All text slots in the Lantern builders escape markup; zero, automatic and exceeded caps stay finite.
test('A6: Lantern markup escapes hostile labels and ages, and its numbers never contain NaN', () => {
  const bad = `<script>&'"`
  expect(esc(bad)).toBe('&lt;script&gt;&amp;&#39;&quot;')
  const drawings = [detailCards(2, 1, 3, bad, 'not checked yet', null, null), rowCard(bad, bad), eyebrow(bad), chip(bad, true), chip(bad, false)]
  for (const spent of [0, 1, 1200, 3000]) for (const limit of [null, 2000]) {
    drawings.push(sessionCard(spent, limit, 'warning'), bandDial(spent, limit, 'success', null))
  }
  for (const d of drawings) {
    expect(d.source).not.toContain('<script')
    expect(d.source).not.toContain('NaN')
    expect(d.source.match(/&(?!(amp|lt|gt|quot|#39);)/g)).toBeNull()
    expect(typeof d.alt).toBe('string')
    expect(d.alt.length).toBeGreaterThan(0)
  }
  expect(rowCard('A long label '.repeat(20), '1 cr').source.match(/<text /g)?.length).toBe(5)
  expect(rowCard('Name', '').source.match(/<rect /g)?.length).toBe(1)
  expect(rowCard('Name', '').alt).toBe('Name')
  expect(bandDial(1200, 2000, 'success', null).alt).toBe('800 of 2,000 credits left this session; Usage: none read yet')
  expect(bandDial(5, null, 'warning', null).alt).toBe('5 credits counted this session, automatic cap; Usage: none read yet')
  expect(chip('Found on this computer: yt-dlp', true).alt).toBe('Found on this computer: yt-dlp')
  expect(chip(bad, true).source).not.toBe(chip(bad, false).source)
})

// ---- 5b A10: the Endpoints and Combos tabs keep the kit's rules on every surface and in every state: each draws with no
// refusal (drawn() rejects with one), every Button a plain string label with no children, every card a round subtle
// Box, desktop Lantern rows and headings, and the target an Input except on mobile. The JSON files are synthetic; the world is in memory.
const TAB_COSTS: Record<string, unknown> = Object.fromEntries(ENDPOINTS.map(x => [x.call, { credits: 0, range: [1, 5], metered: (M6_REAL as any)[x.call].metered === true }]))
const TAB_PK = { rows: [
  { id: 'website', options: [{ id: 'web-scrape', label: 'One web page', quote: { low: 1, high: 5 }, ceiling: 5 }, { id: 'site-teardown', label: 'Site teardown', curated: 'site-teardown' }] },
  { id: 'free_web', options: [] },
  { id: 'people_saying', options: [{ id: 'voice-of-customer', label: 'Voice-of-Customer mining, a label long enough to wrap in a 48-column dock', curated: 'voice-of-customer' }] },
] }
const TAB_CW = { workflows: [{ id: 'site-teardown', quote: { low: 2, high: 5 }, ceiling: 5 }, { id: 'voice-of-customer', quote: { low: 25, high: 1050 }, ceiling: 120 }] }
const CARD_KEYS = new Set(['c1', 'c2', 'c3', 'session', 'calls', 'refused', 'files', 'routine',
  ...ENDPOINTS.map(x => x.group), ...TAB_PK.rows.map(r => r.id)])
const tabFiles = (costs: unknown = TAB_COSTS, cw: unknown = TAB_CW) => ({ 'hooks/costs.json': JSON.stringify(costs),
  'skills/research-plays/references/packages.json': JSON.stringify(TAB_PK), 'skills/research-plays/curated-workflows.json': JSON.stringify(cw) })
type TabCase = { name: string; costs?: unknown; cw?: unknown; type?: string; press?: string; submit?: 'sleep' | 'drop'; shows: { text: string | RegExp } | { key: string; label: string } }
const TABS: Record<'sc-endpoints' | 'sc-combos', TabCase[]> = {
  'sc-endpoints': [
    { name: 'idle', shows: { key: 'instagram-profile', label: 'Profile · 1–5 cr · varies' } },
    { name: 'typed', type: 'nike', shows: { key: 'tiktok-ads-top', label: 'Top ads · 1–5 cr · varies' } },
    { name: 'queued', type: 'nike', press: 'instagram-profile', submit: 'sleep', shows: { key: 'instagram-profile', label: 'Queued · Profile' } },
    { name: 'dropped', type: 'nike', press: 'instagram-profile', submit: 'drop', shows: { text: 'Not sent: busy' } },
    { name: 'no-price', costs: { ...TAB_COSTS, 'GET tiktok/ads/top': { credits: 1, range: null } }, shows: { key: 'tiktok-ads-top', label: 'Top ads · no price' } },
    { name: 'empty-target', press: 'instagram-profile', shows: { text: 'This call needs a handle, like @name in the Target box.' } },
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

for (const surface of ['desktop', 'terminal'] as const) {
  test(`Combos labels appear once on ${surface}, with dim wrapping Text on terminal`, async ($, on) => {
    world(on, { plugin: tabFiles() })
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
    await ui.press({ key: 'tab-Combos' })
    const t: any = await ui.drawn()
    selectsOk(t)
    for (const o of TAB_PK.rows.flatMap(r => r.options)) {
      const labels: string[] = []
      walk(t, el => {
        if (el.type === 'Text') labels.push(textOf(el))
        if (el.type === 'Svg') labels.push(el.props.alt)
      })
      expect(labels.reduce((n, text) => n + text.split(o.label).length - 1, 0)).toBe(1)
      const label = await ui.find({ type: 'Text', text: o.label })
      if (surface === 'terminal') expect(label?.props).toMatchObject({ dimColor: true, wrap: 'wrap' })
      else expect(label).toBeUndefined()
    }
    await ui.unmount()
  })
}

for (const surface of ['desktop', 'terminal', 'vscode', 'mobile'] as const) {
  for (const id of ['sc-endpoints', 'sc-combos'] as const) {
    for (const c of TABS[id]) {
      test(`A10 ${id === 'sc-endpoints' ? 'Endpoints' : 'Combos'} tab draws on ${surface}: ${c.name}`, async ($, on) => {
        const at: { clock?: any } = {}
        at.clock = world(on, { plugin: tabFiles(c.costs, c.cw), submit: async (e: any) => {
          if (c.submit === 'drop') return { drop: 'busy' }
          await at.clock.sleep(5000)
          return { text: e.text }
        } })
        const mount = async (s: typeof surface) => {
          const ui = await $.ui.mount({ plugin: PLUGIN, surface: s, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
          await ui.press({ key: id === 'sc-endpoints' ? 'tab-Endpoints' : 'tab-Combos' })
          return ui
        }
        if (c.type !== undefined) {   // typed where there is a box; the target is the module's, so mobile draws with it too
          const desk = await mount('desktop')
          await desk.input({ key: 'target', text: c.type })
          await desk.unmount()
        }
        const ui = await mount(surface)
        const pressed = c.press ? ui.press({ key: c.press }) : null
        await at.clock.settle()
        const t: any = await ui.drawn()   // rejects with the refusal
      selectsOk(t)
        expect(JSON.stringify(t).includes('"Svg"')).toBe(surface === 'desktop')
        expect(JSON.stringify(t).includes('"Input"')).toBe(id === 'sc-endpoints' && surface !== 'mobile')
        walk(t, el => {
          if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
          if (el.type === 'Box' && (CARD_KEYS.has(el.props?.key) || el.props?.key?.startsWith('s-'))) expect([el.props.borderStyle, el.props.borderColor, el.props.paddingX]).toEqual(['round', 'subtle', 1])
        })
        if ('text' in c.shows) expect(await ui.find({ type: 'Text', text: surface === 'mobile' && c.name === 'empty-target' ? 'This call needs a handle, like @name in the Target box. Fill it on your computer first.' : c.shows.text })).toBeDefined()
        else expect((await ui.find({ type: 'Button', key: c.shows.key }))?.props.label).toBe(surface === 'desktop' ? (c.shows.label.startsWith('Queued') ? 'Queued' : 'Run') : c.shows.label)
        await at.clock.advance(5000)
        await pressed
        await ui.unmount()
      })
    }
  }
}

// ---- 5c A11: the Suggested tab on every surface and in every state draws with no refusal; every Button is a plain
// string label (a suggestion's Button is the real tab's own), every card a round subtle Box, the reason a Text
// with no line break, the target box only where a shown Endpoints suggestion takes a target (never on mobile), and the
// token footer always. Every model call is faked beneath the plugin.
const SUG_USE = { input_tokens: 1, output_tokens: 1, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 }
const SUG_ANSWER = (ids: string[]) => ({ isAnswered: true, text: ids.map(id => JSON.stringify({ id, why: `why ${id}\nsecond line` })).join('\n'), usage: SUG_USE })
const THREE = ['instagram-profile', 'website:web-scrape', 'tiktok-ads-top']
const SIX = [...THREE, 'people_saying:voice-of-customer', 'tiktok-trending', 'youtube-shorts-trending']
type SugCase = { name: string; outs?: unknown[]; sleep?: boolean; again?: boolean; keys: string[]; shows?: string; input: boolean }
const SUG_CASES: SugCase[] = [
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
    test(`A11 Suggested tab draws on ${surface}: ${c.name}`, async ($, on) => {
      const outs = [...(c.outs ?? [])]
      const at: { clock?: any } = {}
      at.clock = world(on, { plugin: tabFiles(), model: async () => {
        if (c.sleep) await at.clock.sleep(5000)
        return { value: outs.shift() }
      } })
      if (c.outs) {
        const ends = await $.ui.mount({ plugin: PLUGIN, surface: 'desktop', component: 'Pane', requestId: 'sc-pane', props: { ...PANE, title: 'sc-endpoints' } as any })
        await ends.press({ key: 'tab-Suggested' })
        await ends.unmount()
        await at.clock.settle()
      }
      if (c.again) {
        await $.prompt.submit({ text: 'a new direction', wait: false, origin: { kind: 'composer' } } as any)
        await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as any)
        await at.clock.settle()
      }
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: { ...PANE, title: 'SocialCrawl Suggested' } as any })
      const t: any = await ui.drawn()   // rejects with the refusal
      selectsOk(t)
      expect(JSON.stringify(t).includes('"Svg"')).toBe(surface === 'desktop')
      expect(JSON.stringify(t).includes('"Input"')).toBe((c.outs ? c.input : true) && surface !== 'mobile')
      walk(t, el => {
        if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
        if (el.type === 'Box' && (CARD_KEYS.has(el.props?.key) || el.props?.key?.startsWith('s-'))) expect([el.props.borderStyle, el.props.borderColor, el.props.paddingX]).toEqual(['round', 'subtle', 1])
        if (el.type === 'Text') expect(textOf(el)).not.toMatch(/[\n\r]/)
      })
      expect((await ui.findAll({ type: 'Button' })).filter((b: any) => !b.key.startsWith('tab-')).map((b: any) => b.key)).toEqual(c.outs ? c.keys : ENDPOINTS.map(x => x.call.split(' ')[1]!.replaceAll('/', '-')))
      expect((await ui.findAll({ type: 'Text', text: /^why / })).map((x: any) => x.text)).toEqual(c.keys.map(k => `why ${k} second line`))
      if (c.shows) expect(await ui.find({ type: 'Text', text: c.shows })).toBeDefined()
      if (c.outs) expect(await ui.find({ type: 'Text', text: /^Suggestions used \d+ model tokens this session \(not credits\)$/ })).toBeDefined()
      else expect((await ui.find({ key: 'tab-Endpoints' }))?.props.variant).toBe('primary')
      await at.clock.advance(5000)
      await ui.unmount()
    })
  }
}

// ---- 5d A14: Round-up on every surface and in every state draws with no refusal: cards and section Svgs on desktop,
// every Button a plain string label, every keyed card a round subtle Box, no Text with a line break, a file: Link on
// the terminal only and only for an absolute path (R2-6), and both dim notes always. The record is in memory.
const RU_REC = line({ ts: '2026-10-21T12:01:00.000Z' }) + line({ ts: '2026-10-21T12:02:00.000Z', paths: ['/v1/tiktok/ads/top'], worst: 100, decision: 'deny', kind: 'over-limit' })
type RuCase = { name: string; files?: Record<string, string>; bash?: string; command?: string; queued?: boolean; shows: string | RegExp }
const RU_CASES: RuCase[] = [
  { name: 'no calls yet', shows: 'No paid calls yet.' },
  { name: 'paid and refused', files: { [SF]: state(1), [CALLS]: RU_REC }, shows: /tiktok\/ads\/top · refused: over the limit\. Raise the limit in Settings to go further \(20,000 is the highest\)\.$/ },
  { name: 'saved files present and gone', files: { [SF]: state(1), [CALLS]: '', [`${HOME}/sc-a.json`]: '{}' }, bash: line({}),
    command: 'curl -s "$U" -o ~/sc-a.json && curl -s "$U" -o ~/sc-gone.json && curl -s "$U" > rel.json', shows: 'rel.json' },
  { name: 'routine found', files: { [SF]: state(1), [CALLS]: line({ sid: 'r1', decision: 'pass', committed: 40, routine: true }) + line({ sid: 'r1', decision: 'deny', kind: 'day-limit', routine: true }) }, shows: 'Refused: 1 refused by the guard' },
  { name: 'routine none', files: { [SF]: state(1), [CALLS]: line({ sid: 'plain' }) }, shows: 'No routine run found.' },
  { name: 'queued', files: { [SF]: state(1), [CALLS]: RU_REC }, queued: true, shows: /tiktok\/ads\/top · refused: over the limit\. Raise the limit in Settings to go further \(20,000 is the highest\)\.$/ },
]

for (const surface of ['desktop', 'terminal', 'vscode', 'mobile'] as const) {
  for (const c of RU_CASES) {
    test(`A14 Round-up tab draws on ${surface}: ${c.name}`, async ($, on) => {
      const at: { clock?: any } = {}
      at.clock = world(on, { files: c.files, bash: c.bash, submit: async (e: any) => {
        await at.clock.sleep(5000)
        return { text: e.text }
      } })
      if (c.command) await $.tool.call({ tool: 'Bash', command: c.command } as any)
      const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: { ...PANE, title: 'SocialCrawl Round-up' } as any })
      await ui.press({ key: 'tab-Round-up' })
      const pressed = c.queued ? ui.press({ key: 'sc-roundup-summarize' }) : null
      await at.clock.settle()
      const t: any = await ui.drawn()   // rejects with the refusal
      selectsOk(t)
      expect(JSON.stringify(t).split('"Svg"').length - 1).toBe(surface === 'desktop' ? (c.files?.[CALLS] === RU_REC || c.queued ? 6 : 5) : 0)
      expect(JSON.stringify(t)).not.toContain('"Input"')
      const links: [string, string][] = []
      walk(t, el => {
        if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
        if (el.type === 'Box' && (CARD_KEYS.has(el.props?.key) || el.props?.key?.startsWith('s-'))) expect([el.props.borderStyle, el.props.borderColor, el.props.paddingX]).toEqual(['round', 'subtle', 1])
        if (el.type === 'Text') expect(textOf(el)).not.toMatch(/[\n\r]/)
        if (el.type === 'Link') links.push([el.props.href, el.props.label])
      })
      // R2-6: a file: Link on the terminal for an absolute path; Text everywhere else, and for the relative rel.json.
      expect(links).toEqual(c.command && surface === 'terminal' ? [['file:///C:/Users/t/sc-a.json', 'sc-a.json'], ['file:///C:/Users/t/sc-gone.json', 'sc-gone.json']] : [])
      if (surface !== 'terminal') expect(JSON.stringify(t)).not.toMatch(/"Link"|file:/)
      if (c.command) for (const name of ['sc-a.json', 'sc-gone.json', 'rel.json']) expect(JSON.stringify(t)).toContain(`"${name}"`)
      if (c.command) expect((await ui.findAll({ type: 'Text', text: / · gone$/ })).length).toBe(2)
      expect((await ui.find({ type: 'Button', key: 'sc-roundup-summarize' }))?.props.label).toBe(c.queued ? 'Queued · Summarize' : 'Summarize  →')
      for (const shown of [c.shows, "Each row shows what the guard counted before the call ran. Usage is what the guard has read back from SocialCrawl's ledger."]) {
        expect(await ui.find({ type: 'Text', text: shown })).toBeDefined()
      }
      await at.clock.advance(5000)
      await pressed
      await ui.unmount()
    })
  }
}

// M5: every new Settings state and every launcher style draws on all three supported surfaces.
for (const surface of ['desktop', 'terminal', 'mobile'] as const) {
  const states: { name: string; w: W; picked: string; shows?: string; open?: boolean }[] = [
    { name: 'unset, routes unknown', w: {}, picked: 'tr-allow' },
    { name: 'stored block', w: { files: { [BF]: '{"transcripts":"block"}' } }, picked: 'tr-block' },
    { name: 'stored allow', w: { files: { [BF]: '{"transcripts":"allow"}' } }, picked: 'tr-allow' },
    ...['nope', true, 1, null].map(transcripts => ({ name: `unrecognised ${JSON.stringify(transcripts)}`, w: { files: { [BF]: JSON.stringify({ transcripts }) } }, picked: 'tr-block', shows: "The saved transcript setting is unrecognised, so transcripts are blocked. Save to fix it." })),
    ...['{', '[]', 'null', '"string"'].map(raw => ({ name: `unreadable ${raw}`, w: { files: { [BF]: raw } }, picked: 'tr-block', shows: "The settings file couldn't be read; saving will replace it." })),
    { name: 'free tool found', w: { routes: ['yt-dlp'] }, picked: 'tr-block', shows: "Not saved yet, so paid transcripts still run until you press Save. Blocked is picked for you because a transcript tool was found on this computer." },
    { name: 'no free tool', w: { routes: [] }, picked: 'tr-allow', shows: 'No free transcript tool found on this computer' },
    { name: 'routes failed', w: { routes: 'fail' }, picked: 'tr-allow' },
    { name: 'help open', w: {}, picked: 'tr-allow', open: true },
  ]
  for (const c of states) test(`M5 Settings draws on ${surface}: ${c.name}`, async ($, on) => {
    const clock = world(on, c.w)
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
    await ui.press({ key: 'tab-Settings' })
    await clock.settle()
    if (c.open) await ui.press({ key: 'help-toggle' })
    const tree: any = await ui.drawn()
    selectsOk(tree)
    expect((await ui.find({ key: c.picked }))?.props.variant).toBe('primary')
    if (c.shows) expect(JSON.stringify(tree)).toContain(c.shows)
    expect(!!(await ui.find({ key: 'limit-custom' }))).toBe(surface !== 'mobile')
    for (const entry of HOW_IT_WORKS) expect(!!(await ui.find({ type: 'Text', text: entry.text }))).toBe(!!c.open)
    if (c.open) expect((await ui.find({ key: 'help-toggle' }))?.props.label).toBe('Hide')
    walk(tree, el => { if (el.type === 'Button') expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []]) })
    await ui.unmount()
  })

  for (const style of STYLES) for (const tab of ['Endpoints', 'Combos', 'Suggested']) test(`M5 ${style} ${tab} draws on ${surface}`, async ($, on) => {
    const clock = world(on, { store: { appearance: style }, plugin: tabFiles(), model: () => ({ value: SUG_ANSWER(THREE) }) })
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
    await ui.press({ key: `tab-${tab}` })
    await clock.settle()
    const tree: any = await ui.drawn()
    selectsOk(tree)
    const buttons: any[] = []
    const cards: any[] = []
    walk(tree, el => {
      expect(el.props ?? {}).not.toHaveProperty('hover')
      if (el.type === 'Button') {
        expect([typeof el.props.label, el.children ?? []]).toEqual(['string', []])
        if (!el.props.key.startsWith('tab-')) buttons.push(el)
      }
      if (el.type === 'Box' && el.props?.key?.startsWith('card-')) cards.push(el)
    })
    expect(buttons.length).toBeGreaterThan(0)
    expect(cards.length).toBe(style === 'Cards' ? buttons.length : 0)
    if (style === 'Cards') for (const card of cards) {
      expect(card.props).toMatchObject({ flexDirection: 'column', borderStyle: 'round', borderColor: 'subtle', paddingX: 1, minWidth: 20 })
      expect(card.children.map((x: any) => x.type)).toEqual(['Text', 'Text', 'Button'])
      expect(card.children[0].props).toMatchObject({ bold: true, wrap: 'wrap' })
      expect(card.children[1].props.color).toBe('claude')
      expect(textOf(card.children[0]).length).toBeGreaterThan(0)
      expect(textOf(card.children[1])).toMatch(/cr( · varies)?$/)
    }
    if (style === 'Chips' && tab === 'Endpoints') {
      const flow = await ui.find({ key: 'flow-Instagram' })
      expect(flow?.props).toMatchObject({ flexDirection: 'row', flexWrap: 'wrap', gap: 1 })
      expect(flow?.children.every((x: any) => x.type === 'Button')).toBe(true)
    }
    if (style === 'Chips' && tab === 'Combos') expect((await ui.find({ type: 'Text', text: TAB_PK.rows[0]!.options[0]!.label }))?.props).toMatchObject({ dimColor: true, wrap: 'wrap' })
    await ui.unmount()
  })
}

/** The engine accepts between 1 and 64 Select options; one invalid Select refuses the whole pane. */
function selectsOk(tree: any) {
  walk(tree, el => {
    if (el.type === 'Select') {
      expect(el.props.options.length).toBeGreaterThanOrEqual(1)
      expect(el.props.options.length).toBeLessThanOrEqual(64)
    }
  })
}

test('selectsOk accepts 64 options and rejects 65 (and zero)', () => {
  const tree = (n: number) => ({ type: 'Box', children: [{ type: 'Select', props: { options: Array.from({ length: n }, (_, i) => ({ value: String(i), label: String(i) })) } }] })
  expect(() => selectsOk(tree(64))).not.toThrow()
  expect(() => selectsOk(tree(65))).toThrow()
  expect(() => selectsOk(tree(0))).toThrow()
})

// Frozen Pass A preserves the old exact wording and the mislabelled Suggested case above.
for (const surface of ['desktop', 'terminal'] as const) {
  test(`Mfix X4: Settings draws literal transcript, appearance and route help on ${surface}`, async ($, on) => {
    const clock = world(on, { routes: ['yt-dlp', 'whisper', 'groq'] })
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
    await ui.press({ key: 'tab-Settings' })
    await clock.settle()
    expect((await ui.find({ type: 'Text', text: "Paid transcripts cost far more than free captions. Blocked stops them before they run; Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling." }))?.text).toBe("Paid transcripts cost far more than free captions. Blocked stops them before they run; Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling.")
    expect((await ui.find({ type: 'Text', text: 'How the Endpoints, Combos and Suggested buttons are drawn. Changes at once; no Save needed.' }))?.text).toBe('How the Endpoints, Combos and Suggested buttons are drawn. Changes at once; no Save needed.')
    expect(await ui.find({ type: 'Text', text: 'Not saved yet, so paid transcripts still run until you press Save. Blocked is picked for you because a transcript tool was found on this computer.' })).toBeDefined()
    expect(JSON.stringify(await ui.drawn())).toContain('Found on this computer: yt-dlp, whisper; a Groq key is set')
  })
}

for (const surface of ['desktop', 'terminal', 'mobile'] as const) {
  test(`Mfix X5: opened Suggested never draws the deleted invitation on ${surface}`, async ($, on) => {
    const clock = world(on, { plugin: tabFiles(), model: () => ({ value: SUG_ANSWER(THREE) }) })
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: 'sc-pane', props: PANE as any })
    const neverInvitation = async () => expect(JSON.stringify(await ui.drawn())).not.toContain('Open the Suggested tab to load suggestions.')
    await ui.press({ key: 'tab-Suggested' })
    await neverInvitation()
    await clock.settle()
    await neverInvitation()
    await ui.press({ key: 'tab-Endpoints' })
    await ui.press({ key: 'tab-Suggested' })
    await neverInvitation()
    await clock.settle()
    await neverInvitation()
    // The branch is unreachable already; removal of its export gives this item its red assertion in Pass A.
    expect((lib as any).NOT_OPENED).toBeUndefined()
  })
}

for (const usage of [null, 1]) test(`M3 U2: desktop dial source and alt agree on Usage ${usage} and widen for it`, () => {
  const dial = (lib.bandDial as any)(17, 500, 'success', usage)
  const words = usage === null ? 'Usage: none read yet' : 'Usage 1 cr'
  expect(dial.source).toContain(words)
  expect(dial.alt).toBe(`483 of 500 credits left this session; ${words}`)
  expect(dial.width).toBeGreaterThan(Math.round(48 + Math.max('of 500 cr'.length * 7.2, 40) + 16))
  expect(dial.source).toContain(`width="${dial.width}"`)
})

test('M3 U8: no-limit desktop dial shows COUNTED and short spent instead of auto', () => {
  const dial = (lib.bandDial as any)(1234, null, 'success', null)
  expect(dial.source).toContain('>COUNTED<')
  expect(dial.source).toContain('>1.2k<')
  expect(dial.source).toContain('automatic cap')
  expect(dial.source).not.toContain('>auto<')
})

for (const limit of [500, null]) test(`M3 U5: desktop session card source and alt say counted with limit ${limit}`, () => {
  const card = lib.sessionCard(17, limit, 'success')
  const head = limit === null ? '17 cr counted · automatic cap' : '17 of 500 cr counted'
  expect(card.source.replace(/<[^>]*>/g, '')).toContain(head)
  expect(card.alt).toContain(head)
  if (limit === null) {
    const foot = "Automatic cap: a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use"
    expect(card.source).toContain(lib.esc(foot))
    expect(card.alt).toContain(foot)
  }
})

for (const usage of [null, 1]) for (const full of [0, 2]) test(`M3 U5: desktop Usage tile renders usage ${usage}, full ${full}, and account balance`, () => {
  const card = (lib.detailCards as any)(3, 1, 4210, 'just now', 'not checked yet', usage, full)
  expect(card.source).toContain('>USAGE<')
  expect(card.source).toContain(usage === null ? '>none read yet<' : '>1 cr<')
  expect(card.source).toContain('3 calls · 1 refused on record')
  if (full > 0) expect(card.source).toContain('2 still counted in full')
  else expect(card.source).not.toContain('still counted in full')
  expect(card.source).toContain('ACCOUNT BALANCE')
  expect(card.source).toContain('4,210 cr')
  expect(card.alt).toContain('Account balance')
})

test('M3 U8: mounted desktop band without a limit draws short counted spent', async ($, on) => {
  world(on, { files: { [SF]: state(1234, 1, 0), [CALLS]: line({ limit: null, committed: 1234 }) + settle({ committed: 1234 }) } })
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'desktop', component: 'AbovePrompt', props: BAND as any })
  const tree: any = await ui.drawn()
  const dial = tree.children[0].children.find((n: any) => n.type === 'Svg')
  expect(dial?.props.source).toContain('>COUNTED<')
  expect(dial?.props.source).toContain('>1.2k<')
  expect(dial?.props.source).not.toContain('>auto<')
  expect(dial?.props.alt).toContain('; Usage 1 cr')
  await ui.unmount()
})
