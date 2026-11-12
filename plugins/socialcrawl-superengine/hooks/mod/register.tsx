import type { ButtonProps, ElementConstructor, EngineInterface, FsStat, Register, ResolveInput, TextProps } from 'claude-code'

import { ageOf, bandOf, bandDial, decodeBytes, detailCards, sessionCard, eyebrow, rowCard, newestFor, parseBudget, parseHelper, limitOf, revxlOf, sidOf, spentOf, statusOf, toastOf } from './lib'
import { GARBLED, READ_ERROR, READ_ERROR_LOCKED, NOTHING_TO_SAVE, PRESS_SET_FIRST, SAVING, PANE_FAILED, SAVED, SESSION_HELP, SESSION_PRESETS, balanceState, changesOf, choiceOf, fmt, holds, notSaved, objOf, parseWrite, warningsOf } from './lib'
import { BUSY, ENDPOINTS, NO_PRICE, comboText, combosOf, endpointText, rowPrice, requestOf, slugOf } from './lib'
import { DEPENDS_HELP, GROUP_PLATFORMS, SITES, TRANSCRIPT_LOCKED, moreOf, moreText, otherPlatforms, platformOptions, plural, siteOptions, sitesFor } from './lib'
import type { MoreRow } from './lib'
import type { Choice, Snap } from './lib'
import { LOADING, NO_NEW, allowOf, askOf, brandSlug, choicesOf, notRefreshed, pathsFor, picksOf, systemOf, tokensLine, usageOf, userHandle } from './lib'
import type { Combo, Endpoint, Suggestion } from './lib'
import { NO_ROUTINE, QUOTES_NOTE, addedSince, callRows, fileHref, isAbsolute, lastRoutine, mapPath, nameOf, outputsOf, routineLines, summaryOf } from './lib'
import { shown } from './lib'
import { APPEARANCE_HELP, APPEARANCE_KEY, CUSTOM_BAD, HOW_IT_WORKS, LOCK_HELP, lockPreselected, LOCK_UNRECOGNISED, SAVE_BUSY, STYLES, chip, customOf, lockPick, lockToSend, parseRoutes, routesFound, storedLock, styleOf } from './lib'
import type { Lock, Style } from './lib'
import { fullOf, settleFor, usageFor, usageWords, USAGE_LINE, TARGET_HINT } from './lib'

// socialcrawl-superengine mod (0.4.0, slices 5a–5d, 6a and 3g): the band above the prompt is this session's spending (from the
// guard's own files), the status line is the account's total balance, a toast follows each counted call, and the
// N6 heartbeat says the mod loaded. The balance and the heartbeat run in helper.mjs through $.process.run: the key
// is read and sent in that process only, never here, where fs.read and http.fetch are events other plugins can hook.

type Api = EngineInterface

// This load's balance reads. ponytail: module state, gone on a hot reload with the timers; the line then stays as
// last set until the next session.
const reads = { snap: null as Snap | null, fail: null as string | null, inFlight: false, timers: false }

/** Where the guard keeps its files for this session (G:318-320). */
async function where($: Api): Promise<{ revxl: string | null; sid: string }> {
  const home = (await $.env.get('USERPROFILE')) || (await $.env.get('HOME'))
  return { revxl: revxlOf(await $.env.get('SC_REVXL_HOME'), home), sid: sidOf(await $.session.id()) }
}

function helper($: Api, ...args: string[]) {
  return $.process.run(['node', `${$.plugin.root}/hooks/mod/helper.mjs`, ...args], { timeoutMs: 8000 })
}

async function budgetOf($: Api, revxl: string): Promise<Record<string, unknown>> {
  try {
    return parseBudget(decodeBytes((await $.fs.read(`${revxl}/socialcrawl-budget.json`, { as: 'bytes' })).base64))
  } catch {
    return {}
  }
}

async function showStatus($: Api) {
  const { revxl } = reads.snap ? await where($) : { revxl: null }
  const budget = revxl ? await budgetOf($, revxl) : {}
  $.ui.status(statusOf(reads.snap, reads.fail, await $.clock.now(), budget))
}

async function readBalance($: Api) {
  if (reads.inFlight) return
  reads.inFlight = true
  try {
    const r = await helper($, 'balance')
    const out = parseHelper(r.exitCode, r.stdout)
    if (out.ok) reads.snap = { balance: out.balance, at: await $.clock.now() }
    reads.fail = out.ok ? null : out.reason
  } catch {
    reads.fail = 'helper'
  } finally {
    reads.inFlight = false
  }
  $.ui.invalidate('ui.render')
  await showStatus($)
}

/** A balance read now (never awaited by the hook), then one 15-minute refresh and a 1-minute age tick for the session. */
function startReads($: Api) {
  $.clock.after(0, () => void readBalance($).catch(() => {}))
  if (reads.timers) return
  reads.timers = true
  $.clock.every(900_000, () => void readBalance($).catch(() => {}))
  $.clock.every(60_000, () => void showStatus($).catch(() => {}))
}

async function heartbeat($: Api) {
  await helper($, 'heartbeat', sidOf(await $.session.id()))
}

/** The band's facts, shown after a call or when onboarding or the key file exists (existence only). */
async function bandData($: Api) {
  const { revxl, sid } = await where($)
  if (!revxl) return null
  const stateFile = `${revxl}/sessions/socialcrawl-${sid}.json`
  const { state, last, spent, usage, full } = await sessionData($, revxl, sid)
  const home = (await $.env.get('USERPROFILE')) || (await $.env.get('HOME'))
  const marker = home ? await $.fs.exists(`${home}/.claude/socialcrawl-superengine/.superengine`).catch(() => false) : false
  const key = home ? await $.fs.exists(`${home}/.config/socialcrawl/api_key`).catch(() => false) : false
  if (!last && state === null && !(await $.fs.exists(stateFile).catch(() => false)) && !marker && !key) return null
  const b = (await budgetOf($, revxl)).sessionBudget
  const limit = limitOf(b, last)
  return { ...bandOf(spent, limit, last), spent, limit, usage, full }
}

// ---- The Settings tab (5a-ii). Presets change only the pending choice; only Save writes, through the helper's
// atomic budget-write, and "Saved" shows only when the file reads back as chosen (D37). The pane is the only shipped
// writer: no model-callable tool, no prompt but a person's own press (the 5b-5d launcher), /socialcrawl-budget only opens the pane, and the guard refuses
// Claude's own commands that name budget-write (5a-ii R2-1).

const PANE = { id: 'sc-pane', title: 'SocialCrawl' }
type Tab = 'Endpoints' | 'Combos' | 'Suggested' | 'Round-up' | 'Settings'
const TAB_NAMES: Tab[] = ['Endpoints', 'Combos', 'Suggested', 'Round-up', 'Settings']
const ui = { tab: 'Endpoints' as Tab }
// What the person pressed and hasn't saved: only the fields pressed, so every other field shows the file as it is now.
const pane = { pressed: {} as Partial<Choice> & { transcripts?: Lock }, note: '', typed: '', saving: false }
const routes = { found: null as string[] | null, asked: false }
const look = { style: undefined as Style | undefined }
const help = { open: false }
const more = { open: new Set<string>(), platform: '' }
const sites = { open: false, pick: '' }

async function styleNow($: Api): Promise<Style> {
  try { return styleOf(look.style ?? (await $.store.get(APPEARANCE_KEY))) } catch { return styleOf(look.style) }
}

/** Settings asks from a detached timer, retrying failures on activation; a draw never starts a process (M5). */
function askRoutes($: Api) {
  if (routes.asked) return
  routes.asked = true
  $.clock.after(0, () => void helper($, 'routes').then(r => {
    routes.found = parseRoutes(r.exitCode, r.stdout)
    if (routes.found === null) routes.asked = false
    $.ui.invalidate('ui.render')
  }).catch(() => { routes.asked = false }))
}

/** Opening without a tab keeps the user's last tab; Suggested alone starts its refresh. */
function openPane($: Api, tab?: Tab) {
  pane.pressed = {}
  pane.note = ''
  pane.typed = ''
  if (tab) ui.tab = tab
  if (ui.tab === 'Settings') askRoutes($)
  if (ui.tab === 'Suggested') {
    suggest.opened = true
    kick($)
  }
  return $.ui.open({ id: PANE.id, title: PANE.title })
}

/** A tab press clears its note and redraws; Suggested alone starts its refresh. */
function switchTab($: Api, tab: Tab) {
  ui.tab = tab
  tabs.note[tab] = ''
  if (tab === 'Settings') askRoutes($)
  if (tab === 'Suggested') {
    suggest.opened = true
    kick($)
  }
  $.ui.invalidate('ui.render')
}

/** Desktop section headings mirror the Lantern preview; other surfaces keep bold Text. */
function heading($: Api, e: ResolveInput<'Pane'>, title: string, dimColor?: boolean) {
  const { Svg, Text } = $.ui.resolve(e)
  return e.surface === 'desktop' ? Svg(eyebrow(title)) : Text({ bold: true, dimColor, children: [title] })
}

/** Plain-string toggles shared by help, sites and each group's extra calls. */
function toggle($: Api, e: ResolveInput<'Pane'>, key: string, label: string, onPress: () => void) {
  const { Button } = $.ui.resolve(e)
  return Button({ key, label, onPress })
}

/** The budget file as the pane shows it: its object; `garbled` when it reads but isn't a JSON object (saving replaces
 *  it); `error` when it is there but the read was refused (R2-5: never saved over, since the real file may hold a budget). */
async function budgetFile($: Api, revxl: string): Promise<{ b: Record<string, unknown>; garbled: boolean; error: boolean }> {
  const f = `${revxl}/socialcrawl-budget.json`
  try {
    const o = objOf(decodeBytes((await $.fs.read(f, { as: 'bytes' })).base64))
    return { b: o ?? {}, garbled: o === null, error: false }
  } catch {
    return { b: {}, garbled: false, error: await $.fs.exists(f).catch(() => true) }   // unsure is an error: no save
  }
}

/** The band and pane read the same counted total and ledger facts from the guard's two files. */
async function sessionData($: Api, revxl: string, sid: string) {
  const state = await $.fs.read(`${revxl}/sessions/socialcrawl-${sid}.json`).catch(() => null)
  const record = (await $.fs.read(`${revxl}/socialcrawl-calls.jsonl`).catch(() => null)) ?? ''
  return { state, record, last: newestFor(record, sid), spent: spentOf(state), usage: usageFor(state, settleFor(record, sid)), full: fullOf(state) }
}

function press($: Api, patch: Partial<Choice> & { transcripts?: Lock }) {
  if (pane.saving) return
  if ('session' in patch) pane.typed = ''
  pane.pressed = { ...pane.pressed, ...patch }
  pane.note = ''
  $.ui.invalidate('ui.render')
}

/** After the helper ran: "Saved" only when it said ok and the file reads back as sent; else the reason, and the
 *  pending choice stays. */
async function afterSave($: Api, revxl: string, sent: Record<string, unknown>, r: { exitCode: number; stdout: string } | null) {
  const out = r ? parseWrite(r.exitCode, r.stdout) : { ok: false as const, reason: 'helper' }
  if (!out.ok) pane.note = out.reason === 'busy' ? SAVE_BUSY : notSaved(out.reason)
  else {
    const back = await budgetFile($, revxl)
    if (!back.garbled && !back.error && holds(back.b, sent)) {
      pane.pressed = {}
      pane.note = SAVED
    } else pane.note = notSaved('readback')
  }
  $.ui.invalidate('ui.render')
}

// ---- The Endpoints and Combos tabs (5b, D42/D43). A press submits the user's priced pick, one in flight at a time.

// ponytail: module variables, not host state (that needs a types contract); a hot reload empties the box and drops a
// queued label.
const tabs = { target: '', queued: null as string | null, note: {} as Record<string, string>, json: {} as Record<string, unknown> }

/** A plugin JSON file, parsed; kept after the first good read. */
async function jsonOf($: Api, rel: string): Promise<unknown> {
  if (tabs.json[rel] == null) {
    try {
      const o: unknown = JSON.parse(await $.fs.read(`${$.plugin.root}/${rel}`))
      if (o && typeof o === 'object') tabs.json[rel] = o
    } catch { /* unread: no price */ }
  }
  return tabs.json[rel] ?? null
}

function noteOn($: Api, pane: string, text: string) {
  tabs.note[pane] = text
  $.ui.invalidate('ui.render')
}

/** A launcher Button. Its press, and only its press, submits: `make()` at press time gives the prompt, a note, or
 *  null (no price: nothing sent). There is no `disabled`, so the one-at-a-time rule is checked here. */
function launcher($: Api, Button: ElementConstructor<ButtonProps>, pane: string, key: string, name: string, label: string, make: () => string | { note: string } | null, e: ResolveInput<'Pane'>, price = '', style: Style = 'Lantern rows') {
  const card = style === 'Cards' && key !== 'sc-roundup-summarize'
  const row = style === 'Lantern rows' && e.surface === 'desktop' && key !== 'sc-roundup-summarize'
  const button = Button({ key,
    label: tabs.queued === key ? (row || card ? 'Queued' : `Queued · ${name}`) : card ? 'Run  →' : row ? 'Run' : label,
    onPress: async () => {
    if (tabs.queued !== null) return noteOn($, pane, BUSY)
    const made = make()
    if (made === null) return noteOn($, pane, NO_PRICE)
    if (typeof made !== 'string') return noteOn($, pane, made.note)
    tabs.queued = key
    noteOn($, pane, '')
    try {
      const r = await $.prompt.submit({ text: made, asUser: true })
      if (r.drop !== undefined) tabs.note[pane] = `Not sent: ${r.drop}`
    } catch {
      tabs.note[pane] = 'Not sent.'
    } finally {
      tabs.queued = null
      $.ui.invalidate('ui.render')
    }
  } })
  const { Box, Svg, Text } = $.ui.resolve(e)
  if (card) return Box({ key: `card-${key}`, flexDirection: 'column', borderStyle: 'round', borderColor: 'subtle', paddingX: 1, minWidth: 20, children: [
    Text({ bold: true, wrap: 'wrap', children: [name] }), Text({ color: 'claude', children: [price] }), button,
  ] })
  return row ? Box({ key: `row-${key}`, flexDirection: 'row', gap: 1, alignItems: 'center', children: [Svg(rowCard(name, price)), button] }) : button
}

/** An Endpoints row's launcher: the same key, label and text wherever it is drawn (Endpoints, and Suggested in 5c). */
function endpointLauncher($: Api, Button: ElementConstructor<ButtonProps>, pane: string, costs: unknown, x: Endpoint, e: ResolveInput<'Pane'>, style: Style) {
  const price = rowPrice(costs, x.call)
  return launcher($, Button, pane, slugOf(x.call), x.name, `${x.name} · ${price ?? 'no price'}`, () => {
    if (price === null) return null
    const req = requestOf(x, tabs.target, e.surface === 'mobile')
    return 'note' in req ? req : endpointText(x, price, req)
  }, e, price ?? 'no price', style)
}

/** Priced and free calls use the existing launcher; request-dependent prices are text only. */
function moreRows($: Api, e: ResolveInput<'Pane'>, rows: MoreRow[], locked: boolean, style: Style) {
  const { Text, Button } = $.ui.resolve(e)
  const launch = (row: MoreRow) => {
    const name = `${row.transcript && locked ? '🔒 ' : ''}${row.name}`
    const price = row.price!
    return launcher($, Button, 'Endpoints', row.key, name, `${name} · ${price}`, () =>
      row.transcript && locked ? { note: TRANSCRIPT_LOCKED } : moreText({ ...row, price }, tabs.target), e, price, style)
  }
  const free = rows.filter(r => r.kind === 'free')
  const depends = rows.filter(r => r.kind === 'unpriced')
  return [
    ...rows.filter(r => r.kind === 'priced').map(launch),
    ...(free.length ? [Text({ dimColor: true, children: ['Free calls'] }), ...free.map(launch)] : []),
    ...(depends.length ? [Text({ dimColor: true, children: ['Price depends on the request'] }),
      Text({ dimColor: true, children: [DEPENDS_HELP] }),
      ...depends.map(r => Text({ wrap: 'wrap', children: [`${r.name} · depends`] }))] : []),
  ]
}

/** A Combos option's launcher, the same wherever it is drawn. */
function comboLauncher($: Api, Button: ElementConstructor<ButtonProps>, pane: string, o: Combo, e: ResolveInput<'Pane'>, style: Style) {
  return launcher($, Button, pane, o.key, o.label, `Run · ${o.price ?? 'no price'}`, () => (o.price === null ? null : comboText({ ...o, price: o.price })), e, o.price ?? 'no price', style)
}

/** The rows the Combos tab draws (and the Suggested allowlist reads). */
async function combosNow($: Api) {
  return combosOf(await jsonOf($, 'skills/research-plays/references/packages.json'), await jsonOf($, 'skills/research-plays/curated-workflows.json'))
}

/** The one target box: an Input writing tabs.target; mobile has no field (an Input there draws an empty box: R §5), so
 *  it says where to type. */
function targetBox($: Api, e: ResolveInput<'Pane'>) {
  const { Text, Input } = $.ui.resolve(e)
  return e.surface === 'mobile'
    ? [Text({ dimColor: true, children: [tabs.target ? `Target: ${shown(tabs.target)}` : 'No target yet. Fill the Target box on your computer.'] })]
    : [Input({ key: 'target', label: 'Target', placeholder: '@handle, keyword or URL',
      onInput: v => { tabs.target = v }, onSubmit: v => { tabs.target = v } }),
      Text({ dimColor: true, wrap: 'wrap', children: [TARGET_HINT] }),
    ]
}

// ---- The Suggested tab (5c, D45/D46). Activating it starts the suggestions: a refresh at open, then after a main-loop turn or a call-record change, only when what it would send
// changed, one call in flight, always detached from the hook that asked.

// ponytail: module variables, as the other tabs; a hot reload forgets the set and the opened flag (no call until pressed again).
const suggest = { opened: false, inFlight: false, dirty: false, sig: '', prompts: [] as string[], items: [] as Suggestion[], note: '', tokens: 0 }

/** A refresh from a timer, never awaited by the hook that asked; a rejection keeps the last set and says so. */
function kick($: Api) {
  if (suggest.opened) $.clock.after(0, () => void refresh($).catch(() => { suggest.note = notRefreshed('refused'); $.ui.invalidate('ui.render') }))
}

/** The brand's business-config.md (D45): the handle in this workspace's config, under its `user:` block, slugged; else
 *  the only brand folder holding one; else none. No other brand file is named. */
async function brandFile($: Api, revxl: string): Promise<string | null> {
  const at = (slug: string) => `${revxl}/${slug}/voc/business-config.md`
  const root = await $.session.root().catch(() => null)
  const yml = root === null ? null : await $.fs.read(`${root}/.claude/workspace.yml`).catch(() => null)
  const slug = brandSlug((yml === null ? null : userHandle(yml)) ?? '')
  if (slug && (await $.fs.exists(at(slug)).catch(() => false))) return at(slug)
  const held: string[] = []
  for (const d of await $.fs.list(revxl).catch(() => [])) if (d.kind === 'dir' && (await $.fs.exists(at(d.name)).catch(() => false))) held.push(at(d.name))
  return held.length === 1 ? held[0]! : null
}

/** One refresh: what it would send, and the call only when that changed. The set is replaced only by a reply with at
 *  least one allowed id; anything else keeps it and says why. */
async function refresh($: Api) {
  if (suggest.inFlight) {
    suggest.dirty = true
    return
  }
  suggest.inFlight = true
  try {
    const { revxl, sid } = await where($)
    const file = revxl ? await brandFile($, revxl) : null
    const st = file ? await $.fs.stat(file).catch(() => null) : null
    const calls = revxl ? await $.fs.read(`${revxl}/socialcrawl-calls.jsonl`).catch(() => null) : null
    const paths = calls === null ? [] : pathsFor(calls, sid)
    const prompts = suggest.prompts
    const sig = JSON.stringify([file, st && `${st.size}:${st.mtimeMs}`, prompts, paths])
    if (sig === suggest.sig) return
    suggest.sig = sig
    $.ui.invalidate('ui.render')
    const brand = file ? await $.fs.read(file).catch(() => null) : null
    const combos = await combosNow($)
    const ok = allowOf(combos)
    const ask = askOf(prompts, paths)
    const r = await $.model.complete({ model: 'haiku', effort: 'low', maxTokens: 400, timeoutMs: 20000, system: systemOf(choicesOf(await jsonOf($, 'hooks/costs.json'), combos)),
      prompt: brand ? [{ text: brand, cache: true }, { text: ask }] : [{ text: ask }] })
    suggest.tokens += usageOf(r.usage)
    const picks = r.isAnswered ? picksOf(r.text, ok) : []
    if (picks.length) {
      suggest.items = picks
      suggest.note = ''
    } else suggest.note = r.isAnswered ? NO_NEW : notRefreshed(r.reason === 'api-error' ? r.error : r.reason)
  } finally {
    suggest.inFlight = false
    $.ui.invalidate('ui.render')
    if (suggest.dirty) {
      suggest.dirty = false
      kick($)
    }
  }
}

// ---- The Round-up tab (5d, D47). It reads the guard's files and writes nothing. Summarize is a launcher: the pane's facts, sent as the person's own prompt on their press.

// ponytail: a module list, as the other tabs' state; a hot reload forgets the saved files (the record keeps the calls).
const roundup = { files: [] as { path: string; ts: string }[] }

/** After a new counted line: the Bash command's -o, > and >> files, mapped for this machine, newest first, each once.
 *  Its command text only: no read, no run. */
async function keepOutputs($: Api, command: unknown, ts: string) {
  const outs = outputsOf(typeof command === 'string' ? command : '')
  if (!outs.length) return
  const temp = await $.env.get('TEMP')
  const home = (await $.env.get('USERPROFILE')) || (await $.env.get('HOME'))
  const paths = [...new Set(outs.map(p => mapPath(p, temp, home)))]
  roundup.files = [...paths.map(path => ({ path, ts })), ...roundup.files.filter(f => !paths.includes(f.path))]
}

const same = (a: FsStat | null, b: FsStat | null) => (a === null || b === null ? a === b : a.size === b.size && a.mtimeMs === b.mtimeMs)

/** After a Bash call: when the call record changed, the toast for this session's newest counted line among the lines
 *  this call added (and, 5d, the files that command saved). An older line of this session is never toasted again. */
async function toastAfter($: Api, file: string, sid: string, before: FsStat | null, command: unknown) {
  if (same(before, await $.fs.stat(file).catch(() => null))) return
  kick($)
  $.ui.invalidate('ui.render')
  const text = await $.fs.read(file).catch(() => null)
  const added = text === null ? '' : addedSince(text, before ? before.size : null)
  const last = newestFor(added, sid)
  if (last && last.decision !== 'deny') {
    $.ui.toast(shown(toastOf(last)))
    await keepOutputs($, command, String((last as { ts?: unknown }).ts))
  }
  const settle = settleFor(added, sid)
  if (settle) $.ui.toast(`SocialCrawl: Usage ${fmt(settle.usage)} cr · session total ${fmt(settle.was)} → ${fmt(settle.committed)} cr`)
}

export const register: Register = on => {
  // The heartbeat in every session; balance reads only where a person is at the prompt (never under -p).
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'socialcrawl-budget', description: 'Open SocialCrawl on its Settings tab.' }).catch(() => {})
    $.clock.after(0, () => void heartbeat($).catch(() => {}))
    if (e.isInteractive === true) startReads($)
    return next(e)
  })

  // Desktop and remote clients (the terminal never raises attach; Desktop's start reports isInteractive false).
  on('session.attach', async ($, e, next) => {
    startReads($)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const below = await next(e)
    try {
      if (e.props.hasSurvey) return below
      const band = await bandData($).catch(() => null)
      if (!band) return below
      const { Box, Text, Button } = $.ui.resolve(e)
      // Desktop draws the Lantern dial; the terminal keeps the text gauge (5a-iii S1).
      const desk = e.surface === 'desktop'
      const parts = desk
        ? [$.ui.resolve(e).Svg({ ...bandDial(band.spent, band.limit, band.tone, band.usage) })]
        : [Text({ color: band.tone, children: [band.gauge] }), Text({ children: [` ${band.text} · ${usageWords(band.usage)}`] })]
      if (band.warn) parts.push(Text({ color: band.tone, children: [band.warn] }))
      parts.push(Button({ key: 'sc-open', label: 'Open SocialCrawl', hotkey: 'd', onPress: () => void openPane($) }))
      // Layout A: our one row, no plugin name; every band beneath ours below it.
      const row = Box({ key: 'sc-band', flexDirection: 'row', ...(desk ? { gap: 1, alignItems: 'center' as const } : {}), children: parts })
      return Box({ flexDirection: 'column', children: [row, below] })
    } catch { return below }
  })

  // /socialcrawl-budget only opens the pane; it writes nothing.
  on('command.run', { command: 'socialcrawl-budget' }, async $ => {
    await openPane($, 'Settings')
    return { text: 'Opened SocialCrawl on Settings.' }
  })

  on('ui.render', { component: 'Pane', requestId: 'sc-pane' }, async ($, e) => {
    const Text: ElementConstructor<TextProps> = $.ui.resolve(e).Text
    try {
      const { Box, Button } = $.ui.resolve(e)
      const style = await styleNow($)
      const { revxl, sid } = await where($)
      if (!revxl) return Text({ children: ["SocialCrawl can't find your home folder, so there is nothing to show."] })
      const { spent, record, last, usage, full } = await sessionData($, revxl, sid)
      const limit = limitOf((await budgetFile($, revxl)).b.sessionBudget, last)
      const calls = callRows(record, sid)
      const tone = bandOf(spent, limit, newestFor(record, sid)).tone
      const now = await $.clock.now()
      const balance = reads.snap ? reads.snap.balance : null
      const age = reads.snap ? ageOf(now - reads.snap.at) : ''
      const left = limit === null ? null : Math.max(0, limit - spent)
      const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
      const top = e.surface === 'desktop'
        ? [$.ui.resolve(e).Svg(sessionCard(spent, limit, tone)), $.ui.resolve(e).Svg(detailCards(calls.paid.length, calls.refused.length, balance, age, balanceState(reads.fail), usage, full))]
        : [Box({ key: 'c1', flexDirection: 'column', ...card, children: [Text({ bold: true, children: [limit === null ? `${fmt(spent)} cr counted · automatic cap` : `${fmt(spent)} of ${fmt(limit)} cr counted`] }),
            Text({ children: [left === null ? "Automatic cap: a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use" : `${fmt(left)} cr left before the limit`] })] }),
          Box({ key: 'c2', flexDirection: 'column', ...card, children: [Text({ bold: true, children: ['Usage'] }),
            Text({ children: [usage === null ? 'none read yet' : `${fmt(usage)} cr read from the ledger`] }),
            Text({ children: [`${calls.paid.length} ${plural(calls.paid.length, 'call')} · ${calls.refused.length} refused on record${full !== null && full > 0 ? ` · ${full} still counted in full` : ''}`] })] }),
          Box({ key: 'c3', flexDirection: 'column', ...card, children: [Text({ bold: true, children: ['Account balance'] }), Text({ children: [balance === null ? `unavailable · ${balanceState(reads.fail)}` : `${fmt(balance)} cr · checked ${age}`] })] })]
      const tabRow = Box({ key: 'tabs', flexDirection: 'row', flexWrap: 'wrap', gap: 1, children: TAB_NAMES.map(label =>
        Button({ key: `tab-${label}`, label, variant: ui.tab === label ? 'primary' : 'secondary', onPress: () => switchTab($, label) })) })
      let body: ReturnType<typeof Box> | undefined
      if (ui.tab === 'Endpoints') {
        const { Box, Text, Button, Select } = $.ui.resolve(e)
        const costs = await jsonOf($, 'hooks/costs.json')
        const file = await budgetFile($, revxl)
        const lock = storedLock(file.b, file.garbled || file.error)
        const locked = lock === 'block' || lock === 'unrecognised' || lock === 'unreadable'
        const pane = 'Endpoints'
        const groups = [...new Set(ENDPOINTS.map(x => x.group))]
        const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
        body = Box({ flexDirection: 'column', gap: 1, children: [
          ...targetBox($, e),
          ...groups.map(g => {
            const launchers = ENDPOINTS.filter(x => x.group === g).map(x => endpointLauncher($, Button, pane, costs, x, e, style))
            const rows = moreOf(costs, GROUP_PLATFORMS[g] ?? [])
            return Box({ key: g, flexDirection: 'column', ...card, children: [
              heading($, e, g),
              ...(style === 'Lantern rows' ? launchers : [Box({ key: `flow-${g}`, flexDirection: 'row', flexWrap: 'wrap', gap: 1, children: launchers })]),
              ...(more.open.has(g) ? moreRows($, e, rows, locked, style) : []),
              ...(rows.length ? [toggle($, e, `more-${g}`, more.open.has(g) ? 'Fewer options' : `More options · ${rows.length}`, () => {
                if (more.open.has(g)) more.open.delete(g)
                else more.open.add(g)
                $.ui.invalidate('ui.render')
              })] : []),
            ] })
          }),
          Box({ key: 'more-platforms', flexDirection: 'column', ...card, children: [
            heading($, e, `More platforms · ${otherPlatforms(costs).length}`),
            Select({ key: 'more-platform', label: 'Platform', options: platformOptions(costs), value: more.platform, onSelect: value => {
              more.platform = value
              $.ui.invalidate('ui.render')
            } }),
            ...moreRows($, e, moreOf(costs, more.platform ? [more.platform] : []), locked, style),
          ] }),
        ] })
      }
      else if (ui.tab === 'Combos') {
        const { Box, Text, Button } = $.ui.resolve(e)
        const rows = await combosNow($)
        const pane = 'Combos'
        const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
        body = Box({ flexDirection: 'column', gap: 1, children: [
          ...(rows.length ? [] : [Text({ color: 'warning', children: ["The research packages couldn't be read."] })]),
          ...rows.filter(r => r.options.length).map(r => Box({ key: r.row, flexDirection: 'column', ...card, children: [
            heading($, e, r.header),
            ...(style === 'Cards' ? [Box({ key: `flow-${r.row}`, flexDirection: 'row', flexWrap: 'wrap', gap: 1, children: r.options.map(o => comboLauncher($, Button, pane, o, e, style)) })] : r.options.flatMap(o => [
              ...(style === 'Lantern rows' && e.surface === 'desktop' ? [] : [Text({ dimColor: true, wrap: 'wrap', children: [o.label] })]),
              comboLauncher($, Button, pane, o, e, style),
            ])),
          ] })),
        ] })
      }
      else if (ui.tab === 'Suggested') {
        const { Box, Text, Button } = $.ui.resolve(e)
        const costs = await jsonOf($, 'hooks/costs.json')
        const combos = (await combosNow($)).flatMap(r => r.options)
        const pane = 'Suggested'
        const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
        const shown = suggest.items.flatMap(p => {
          const x = ENDPOINTS.find(y => slugOf(y.call) === p.id)
          const o = combos.find(c => c.key === p.id)
          return x || o ? [{ p, x, o }] : []
        })
        const status = suggest.inFlight ? LOADING : suggest.note
        body = Box({ flexDirection: 'column', gap: 1, children: [
          ...(shown.some(s => s.x && s.x.kind !== 'none') ? targetBox($, e) : []),
          ...shown.map(({ p, x, o }) => Box({ key: `s-${p.id}`, flexDirection: 'column', ...card, children: [
            Text({ bold: true, children: [x ? `${x.group} · ${x.name}` : o!.label] }),
            Text({ dimColor: true, children: [p.why] }),
            x ? endpointLauncher($, Button, pane, costs, x, e, style) : comboLauncher($, Button, pane, o!, e, style),
          ] })),
          ...(status ? [Text({ dimColor: true, children: [status] })] : []),
          Text({ dimColor: true, children: [tokensLine(suggest.tokens)] }),
        ] })
      }
      else if (ui.tab === 'Round-up') {
        const { Box, Text, Button, Link } = $.ui.resolve(e)
        const rows = callRows(record, sid)
        const routine = lastRoutine(record, sid)
        const files = await Promise.all(roundup.files.map(async f => ({ ...f, gone: await $.fs.stat(f.path).then(() => false, () => true) })))
        const text = summaryOf(rows.paid, roundup.files.map(f => f.path), spent, limit, usage)
        const pane = 'Round-up'
        const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
        body = Box({ flexDirection: 'column', gap: 1, children: [
          Box({ key: 'calls', flexDirection: 'column', ...card, children: [
            heading($, e, "This session's calls"),
            ...(rows.paid.length ? rows.paid : ['No paid calls yet.']).map(r => Text({ children: [shown(r)] })),
          ] }),
          Text({ dimColor: true, children: [USAGE_LINE(usage)] }),
          ...(rows.refused.length ? [Box({ key: 'refused', flexDirection: 'column', ...card, children: [
            heading($, e, 'Refused on record, not counted', true),
            ...rows.refused.map(r => Text({ dimColor: true, children: [shown(r)] })),
          ] })] : []),
          Text({ dimColor: true, children: [QUOTES_NOTE] }),
          Box({ key: 'files', flexDirection: 'column', ...card, children: [
            heading($, e, 'Saved files'),
            ...(files.length ? files.map(f => Text({ children: [
              e.surface === 'terminal' && isAbsolute(f.path) && fileHref(f.path).length <= 2048 ? Link({ href: fileHref(f.path), label: nameOf(f.path) }) : nameOf(f.path),
              ...(f.gone ? [' · gone'] : []),
            ] })) : [Text({ children: ['None saved yet.'] })]),
          ] }),
          Box({ key: 'routine', flexDirection: 'column', ...card, children: [
            heading($, e, 'Last routine'),
            ...(routine ? routineLines(routine) : [NO_ROUTINE]).map(l => Text({ children: [shown(l)] })),
          ] }),
          launcher($, Button, pane, 'sc-roundup-summarize', 'Summarize', 'Summarize  →', () => text, e),
        ] })
      }
      else if (ui.tab === 'Settings') {
        const { Box, Text, Button, Select } = $.ui.resolve(e)
        const costs = await jsonOf($, 'hooks/costs.json')
        const file = await budgetFile($, revxl)
        const saved = choiceOf(file.b)
        const p: Choice = { ...saved, ...pane.pressed }
        const stored = storedLock(file.b, file.garbled || file.error)
        const picked = file.error ? 'block' : lockPick(pane.pressed.transcripts, stored, routes.found)
        const sent = changesOf(p, saved, file.garbled, lockToSend(pane.pressed.transcripts, stored, routes.found))

        const pick = (key: string, label: string, isOn: boolean, onPress: () => unknown) => Button({ key, label, variant: isOn ? 'primary' : 'secondary', onPress })
        const presets = (k: string, vals: number[], cur: number, field: 'session') => ({
          row: vals.map(v => pick(`${k}-${v}`, fmt(v), cur === v, () => press($, { [field]: v }))),
          current: vals.includes(cur) ? [] : [Text({ children: [`Custom: ${fmt(cur)} cr`] })],
        })
        const ses = presets('ps', SESSION_PRESETS, p.session ?? 0, 'session')
        const warns = warningsOf(p, reads.snap ? reads.snap.balance : null, spent)
        const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const

        body = Box({ flexDirection: 'column', gap: 1, children: [
          Box({ key: 'session', flexDirection: 'column', ...card, children: [
            heading($, e, 'Session credit limit'),
            Text({ dimColor: true, children: [SESSION_HELP] }),
            ...(file.error ? [] : [Box({ flexDirection: 'row', flexWrap: 'wrap', gap: 1, children: [...ses.row, pick('ps-auto', 'Automatic', p.session === null, () => press($, { session: null }))] })]),
            ...(file.error || !['desktop', 'terminal'].includes(e.surface) ? [] : [$.ui.resolve(e).Input({ key: 'limit-custom', label: 'Custom', placeholder: '1 to 20,000', submitLabel: 'set',
              onInput: v => { if (!pane.saving) pane.typed = v }, onSubmit: v => {
                if (pane.saving) return
                pane.typed = ''
                const n = customOf(v)
                if (n !== null) press($, { session: n })
                else { pane.note = CUSTOM_BAD; $.ui.invalidate('ui.render') }
              } })]),
            ...(file.error || p.session === null ? [] : ses.current),
          ] }),
          Box({ key: 'transcripts', flexDirection: 'column', ...card, children: [
            heading($, e, 'Transcript endpoints'),
            Text({ dimColor: true, wrap: 'wrap', children: [LOCK_HELP] }),
            ...(routes.found === null ? [] : [e.surface === 'desktop' ? $.ui.resolve(e).Svg(chip(routesFound(routes.found), routes.found.length > 0)) :
              Text({ color: routes.found.length ? 'success' : undefined, children: [routesFound(routes.found)] })]),
            ...(file.error ? [] : [Box({ flexDirection: 'row', gap: 1, children: [
              pick('tr-block', pane.pressed.transcripts === undefined && stored === 'unset' && routes.found?.length ? 'Blocked · not saved' : 'Blocked', picked === 'block', () => press($, { transcripts: 'block' })),
              pick('tr-allow', 'Allowed', picked === 'allow', () => press($, { transcripts: 'allow' })),
            ] })]),
            ...(pane.pressed.transcripts !== undefined ? [] : stored === 'unrecognised' ? [Text({ color: 'warning', children: [LOCK_UNRECOGNISED] })] :
              stored === 'unset' && routes.found?.length ? [Text({ color: 'warning', children: [lockPreselected(routes.found)] })] : []),
          ] }),
          ...(warns.length ? [Box({ key: 'warnings', flexDirection: 'column', children: warns.map(w => Text({ color: 'warning', children: [w] })) })] : []),
          ...(file.garbled ? [Text({ color: 'warning', children: [GARBLED] })] : []),
          ...(file.error ? [Text({ color: 'error', children: [READ_ERROR] }), Text({ dimColor: true, children: [READ_ERROR_LOCKED] })] : [Box({ key: 'save-row', flexDirection: 'row', gap: 1, children: [
            Button({ key: 'save', label: 'Save  →', variant: 'primary', onPress: async () => {
              if (pane.saving) return
              if (pane.typed !== '') {
                pane.note = PRESS_SET_FIRST
                return $.ui.invalidate('ui.render')
              }
              const fresh = await budgetFile($, revxl)
              if (fresh.error) {
                pane.note = READ_ERROR
                return $.ui.invalidate('ui.render')
              }
              const saved = choiceOf(fresh.b)
              const p: Choice = { ...saved, ...pane.pressed }
              const stored = storedLock(fresh.b, fresh.garbled)
              let lock = lockToSend(pane.pressed.transcripts, stored, routes.found)
              if (lock === undefined && pane.pressed.transcripts === undefined && picked === 'block' && lockPick(undefined, stored, routes.found) !== 'block') lock = 'block'
              const sent = changesOf(p, saved, fresh.garbled, lock)
              if (!sent) {
                pane.note = NOTHING_TO_SAVE
                return $.ui.invalidate('ui.render')
              }
              if (pane.saving) return
              pane.saving = true
              try {
                $.ui.invalidate('ui.render')
                await afterSave($, revxl, sent, await helper($, 'budget-write', revxl, JSON.stringify(sent)).catch(() => null))
              } finally {
                pane.saving = false
                $.ui.invalidate('ui.render')
              }
            } }),
            ...(pane.saving ? [Text({ dimColor: true, children: [SAVING] })] : sent ? [Text({ color: 'warning', children: ['Unsaved changes'] })] : []),
          ] })]),
          Box({ key: 'appearance', flexDirection: 'column', ...card, children: [
            heading($, e, 'Appearance'),
            Text({ dimColor: true, wrap: 'wrap', children: [APPEARANCE_HELP] }),
            Box({ flexDirection: 'row', flexWrap: 'wrap', gap: 1, children: STYLES.map(x => pick(`style-${x.split(' ')[0]!.toLowerCase()}`, x, style === x, async () => {
              look.style = x
              try { await $.store.set(APPEARANCE_KEY, x) } catch {}
              $.ui.invalidate('ui.render')
            })) }),
          ] }),
          Box({ key: 'help', flexDirection: 'column', ...card, children: [
            heading($, e, 'How it works'),
            toggle($, e, 'help-toggle', help.open ? 'Hide' : 'Show how everything works', () => { help.open = !help.open; $.ui.invalidate('ui.render') }),
            ...(help.open ? HOW_IT_WORKS.flatMap(x => [Text({ bold: true, children: [x.title] }), Text({ dimColor: true, wrap: 'wrap', children: [x.text] })]) : []),
          ] }),
          Box({ key: 'sites', flexDirection: 'column', ...card, children: [
            heading($, e, `Sites and sources · ${sitesFor('*', costs).length}`),
            toggle($, e, 'sites-toggle', sites.open ? 'Hide' : 'Show sites and sources', () => { sites.open = !sites.open; $.ui.invalidate('ui.render') }),
            ...(sites.open ? [Select({ key: 'site', label: 'Site', options: siteOptions(costs), value: sites.pick, onSelect: value => {
              sites.pick = value
              $.ui.invalidate('ui.render')
            } }), ...sitesFor(sites.pick, costs).map(id => Text({ wrap: 'wrap', children: [
              Text({ bold: true, children: [SITES[id]?.name ?? id] }), Text({ dimColor: true, children: ['  ' + (SITES[id]?.line ?? '')] }),
            ] }))] : []),
          ] }),
        ] })
      }
      return Box({ flexDirection: 'column', gap: 1, children: [...top, tabRow,
        ...(tabs.note[ui.tab] ? [Text({ color: 'warning', children: [tabs.note[ui.tab]] })] : []),
        ...(ui.tab === 'Settings' && pane.note ? [Text({ dimColor: pane.note === NOTHING_TO_SAVE, color: pane.note === NOTHING_TO_SAVE ? undefined : pane.note === SAVED ? 'success' : 'error', children: [pane.note] })] : []),
        body!,
      ] })
    } catch { return Text({ children: [PANE_FAILED] }) }
  })


  // 5c: the person's own last 5 prompts (typed, or sent from the phone), never another session's, a task's, a
  // routine's or a plugin's. Records only: the prompt goes on unchanged.
  on('prompt.submit', async ($, e, next) => {
    if (e.origin.kind === 'composer' || e.origin.kind === 'bridge') suggest.prompts = [...suggest.prompts, e.text.slice(0, 500)].slice(-5)
    return next(e)
  }).catch(($, e, next) => next(e))

  // 5c: the main loop's turn end asks for a refresh (a subagent's never does).
  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined) kick($)
    return next(e)
  })


  // The toast never reads the balance and never runs a process: two stats, and one read only when the record changed.
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    let at: { file: string; sid: string; before: FsStat | null } | null = null
    try {
      const { revxl, sid } = await where($)
      if (revxl) {
        const file = `${revxl}/socialcrawl-calls.jsonl`
        at = { file, sid, before: await $.fs.stat(file).catch(() => null) }
      }
    } catch { /* no toast */ }
    const ran = await next(e)
    if (at) await toastAfter($, at.file, at.sid, at.before, e.command).catch(() => {})
    return ran
  }).catch(($, e, next) => next(e))
}
