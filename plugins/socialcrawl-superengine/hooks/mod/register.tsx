import type { ButtonProps, ElementConstructor, EngineInterface, FsStat, Register, ResolveInput } from 'claude-code'

import { ageOf, bandOf, bandPill, decodeBytes, hero, newestFor, parseBudget, parseHelper, recordLimit, revxlOf, sidOf, spentOf, statusOf, toastOf, isBudget } from './lib'
import { GARBLED, READ_ERROR, SAVED, SESSION_HELP, SESSION_PRESETS, changesOf, choiceOf, fmt, holds, notSaved, objOf, paneTop, parseWrite, warningsOf } from './lib'
import { BUSY, ENDPOINTS, TYPE_ON_DESKTOP, comboText, combosOf, endpointText, priceOf, rangeIn, requestOf, slugOf } from './lib'
import type { Choice, Snap } from './lib'
import { LOADING, NOT_OPENED, NO_NEW, allowOf, askOf, brandSlug, choicesOf, notRefreshed, pathsFor, picksOf, systemOf, tokensLine, usageOf, userHandle } from './lib'
import type { Combo, Endpoint, Suggestion } from './lib'
import { NO_ROUTINE, QUOTES_NOTE, addedSince, callRows, fileHref, isAbsolute, lastRoutine, mapPath, nameOf, outputsOf, routineLines, summaryOf } from './lib'
import { shown } from './lib'

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

/** The band's model, or null when SocialCrawl hasn't been used in this session. */
async function bandData($: Api) {
  const { revxl, sid } = await where($)
  if (!revxl) return null
  const stateFile = `${revxl}/sessions/socialcrawl-${sid}.json`
  const state = await $.fs.read(stateFile).catch(() => null)
  const calls = await $.fs.read(`${revxl}/socialcrawl-calls.jsonl`).catch(() => null)
  const last = calls === null ? null : newestFor(calls, sid)
  if (!last && state === null && !(await $.fs.exists(stateFile).catch(() => false))) return null
  let limit = recordLimit(last)
  if (limit === null) {
    const b = (await budgetOf($, revxl)).sessionBudget
    limit = isBudget(b) ? b : null
  }
  const spent = spentOf(state)
  return { ...bandOf(spent, limit, last), spent, limit }
}

// ---- The Budget pane (5a-ii). Presets change only the pending choice; only Save writes, through the helper's
// atomic budget-write, and "Saved" shows only when the file reads back as chosen (D37). The pane is the only shipped
// writer: no model-callable tool, no prompt but a person's own press (the 5b-5d launcher), /socialcrawl-budget only opens the pane, and the guard refuses
// Claude's own commands that name budget-write (5a-ii R2-1).

const PANE = { id: 'sc-budget', title: 'SocialCrawl Budget' }
// What the person pressed and hasn't saved: only the fields pressed, so every other field shows the file as it is now.
const pane = { pressed: {} as Partial<Choice>, note: '' }

function openBudget($: Api) {
  return $.ui.open({ id: PANE.id, title: PANE.title })
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

/** This session's spent and limit, from the guard's own files (as the band reads them). */
async function spendOf($: Api, revxl: string, sid: string, budget: Choice) {
  const state = await $.fs.read(`${revxl}/sessions/socialcrawl-${sid}.json`).catch(() => null)
  const calls = await $.fs.read(`${revxl}/socialcrawl-calls.jsonl`).catch(() => null)
  return { spent: spentOf(state), limit: recordLimit(calls === null ? null : newestFor(calls, sid)) ?? budget.session }
}

function press($: Api, patch: Partial<Choice>) {
  pane.pressed = { ...pane.pressed, ...patch }
  pane.note = ''
  $.ui.invalidate('ui.render')
}

/** After the helper ran: "Saved" only when it said ok and the file reads back as sent; else the reason, and the
 *  pending choice stays. */
async function afterSave($: Api, revxl: string, sent: Record<string, unknown>, r: { exitCode: number; stdout: string } | null) {
  const out = r ? parseWrite(r.exitCode, r.stdout) : { ok: false as const, reason: 'helper' }
  if (!out.ok) pane.note = notSaved(out.reason)
  else {
    const back = await budgetFile($, revxl)
    if (!back.garbled && !back.error && holds(back.b, sent)) {
      pane.pressed = {}
      pane.note = SAVED
    } else pane.note = notSaved('readback')
  }
  $.ui.invalidate('ui.render')
}

// ---- The Endpoints and Combos tabs (5b, D42/D43). /socialcrawl-endpoints and the band's Endpoints button open both
// panes; a press there submits the person's priced pick as their own prompt, one in flight at a time.

const ENDPOINTS_PANE = { id: 'sc-endpoints', title: 'SocialCrawl Endpoints' }
const COMBOS_PANE = { id: 'sc-combos', title: 'SocialCrawl Combos' }
// ponytail: module variables, not host state (that needs a types contract); a hot reload empties the box and drops a
// queued label.
const tabs = { target: '', queued: null as string | null, note: {} as Record<string, string>, json: {} as Record<string, unknown> }

/** Combos first, then Endpoints, so Endpoints is the tab in front. Opens only; writes nothing. */
async function openTabs($: Api) {
  await $.ui.open(COMBOS_PANE)
  await $.ui.open(ENDPOINTS_PANE)
}

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
function launcher($: Api, Button: ElementConstructor<ButtonProps>, pane: string, key: string, name: string, label: string, make: () => string | { note: string } | null) {
  return Button({ key, label: tabs.queued === key ? `Queued · ${name}` : label, onPress: async () => {
    if (tabs.queued !== null) return noteOn($, pane, BUSY)
    const made = make()
    if (made === null) return
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
}

/** An Endpoints row's launcher: the same key, label and text wherever it is drawn (Endpoints, and Suggested in 5c). */
function endpointLauncher($: Api, Button: ElementConstructor<ButtonProps>, pane: string, costs: unknown, x: Endpoint) {
  const r = rangeIn(costs, x.call)
  const price = r ? priceOf(r) : null
  return launcher($, Button, pane, slugOf(x.call), x.name, `${x.name} · ${price ?? 'no price'}`, () => {
    if (price === null) return null
    const req = requestOf(x, tabs.target)
    return 'note' in req ? req : endpointText(x, price, req)
  })
}

/** A Combos option's launcher, the same wherever it is drawn. */
function comboLauncher($: Api, Button: ElementConstructor<ButtonProps>, pane: string, o: Combo) {
  return launcher($, Button, pane, o.key, o.label, `Run · ${o.price ?? 'no price'}`, () => (o.price === null ? null : comboText({ ...o, price: o.price })))
}

/** The rows the Combos tab draws (and the Suggested allowlist reads). */
async function combosNow($: Api) {
  return combosOf(await jsonOf($, 'skills/research-plays/references/packages.json'), await jsonOf($, 'skills/research-plays/curated-workflows.json'))
}

/** The one target box: an Input writing tabs.target; mobile has no field (an Input there draws an empty box: R §5), so
 *  it says where to type. */
function targetBox($: Api, e: ResolveInput<'Pane'>) {
  return e.surface === 'mobile'
    ? $.ui.resolve(e).Text({ dimColor: true, children: [TYPE_ON_DESKTOP] })
    : $.ui.resolve(e).Input({ key: 'target', label: 'Target', placeholder: '@handle, keyword or URL',
      onInput: v => { tabs.target = v }, onSubmit: v => { tabs.target = v } })
}

// ---- The Suggested tab (5c, D45/D46). Its own Button in the Endpoints tab opens it, and only that press starts the
// suggestions: a refresh at open, then after a main-loop turn or a call-record change, only when what it would send
// changed, one call in flight, always detached from the hook that asked.

const SUGGESTED_PANE = { id: 'sc-suggested', title: 'SocialCrawl Suggested' }
// ponytail: module variables, as the other tabs; a hot reload forgets the set and the opened flag (no call until pressed again).
const suggest = { opened: false, inFlight: false, dirty: false, sig: '', prompts: [] as string[], items: [] as Suggestion[], note: '', tokens: 0 }

function openSuggested($: Api) {
  suggest.opened = true
  kick($)
  return $.ui.open(SUGGESTED_PANE)
}

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

// ---- The Round-up tab (5d, D47). The band's Round-up (r) and /socialcrawl-roundup open it; it reads the guard's own
// files and writes nothing. Summarize is a launcher: the pane's facts, sent as the person's own prompt on their press.

const ROUNDUP_PANE = { id: 'sc-roundup', title: 'SocialCrawl Round-up' }
// ponytail: a module list, as the other tabs' state; a hot reload forgets the saved files (the record keeps the calls).
const roundup = { files: [] as { path: string; ts: string }[] }

function openRoundup($: Api) {
  return $.ui.open(ROUNDUP_PANE)
}

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
  const last = text === null ? null : newestFor(addedSince(text, before ? before.size : null), sid)
  if (last && last.decision !== 'deny') {
    $.ui.toast(shown(toastOf(last)))
    await keepOutputs($, command, String((last as { ts?: unknown }).ts))
  }
}

export const register: Register = on => {
  // The heartbeat in every session; balance reads only where a person is at the prompt (never under -p).
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'socialcrawl-budget', description: 'Open the SocialCrawl Budget pane (the budget per run).' }).catch(() => {})
    await $.command.register({ name: 'socialcrawl-endpoints', description: 'Open the SocialCrawl Endpoints and Combos tabs (one-click calls and research packages).' }).catch(() => {})
    await $.command.register({ name: 'socialcrawl-roundup', description: "Open the SocialCrawl Round-up (this session's calls, saved files, total and the last routine)." }).catch(() => {})
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
    if (e.props.hasSurvey) return below
    const band = await bandData($).catch(() => null)
    if (!band) return below
    const { Box, Text, Button } = $.ui.resolve(e)
    // Desktop draws the Lantern pill; the terminal keeps the text gauge (5a-iii S1).
    const desk = e.surface === 'desktop'
    const parts = desk
      ? [$.ui.resolve(e).Svg({ width: 200, ...bandPill(band.spent, band.limit, band.tone) })]
      : [Text({ color: band.tone, children: [band.gauge] }), Text({ children: [` ${band.text}`] })]
    if (band.warn) parts.push(Text({ color: band.tone, children: [band.warn] }))
    parts.push(Button({ key: 'sc-budget-open', label: 'Budget', hotkey: 'd', onPress: () => void openBudget($) }))
    parts.push(Button({ key: 'sc-endpoints-open', label: 'Endpoints', hotkey: 'p', onPress: () => void openTabs($) }))
    parts.push(Button({ key: 'sc-roundup-open', label: 'Round-up', hotkey: 'r', onPress: () => void openRoundup($) }))
    // Layout A: our one row, no plugin name; every band beneath ours below it.
    const row = Box({ key: 'sc-band', flexDirection: 'row', ...(desk ? { gap: 1, alignItems: 'center' as const } : {}), children: parts })
    return Box({ flexDirection: 'column', children: [row, below] })
  })

  // /socialcrawl-budget only opens the pane; it writes nothing.
  on('command.run', { command: 'socialcrawl-budget' }, async $ => {
    await openBudget($)
    return { text: 'Opened the SocialCrawl Budget pane.' }
  })

  // /socialcrawl-endpoints only opens the two tabs; it writes nothing.
  on('command.run', { command: 'socialcrawl-endpoints' }, async $ => {
    await openTabs($)
    return { text: 'Opened the SocialCrawl Endpoints and Combos tabs.' }
  })

  // /socialcrawl-roundup only opens the pane; it writes nothing.
  on('command.run', { command: 'socialcrawl-roundup' }, async $ => {
    await openRoundup($)
    return { text: 'Opened the SocialCrawl Round-up.' }
  })

  on('ui.render', { component: 'Pane', requestId: 'sc-endpoints' }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const costs = await jsonOf($, 'hooks/costs.json')
    const pane = ENDPOINTS_PANE.id
    const groups = [...new Set(ENDPOINTS.map(x => x.group))]
    const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
    return Box({ flexDirection: 'column', gap: 1, children: [
      Button({ key: 'sc-suggested-open', label: 'Suggested  →', onPress: () => void openSuggested($) }),
      targetBox($, e),
      ...groups.map(g => Box({ key: g, flexDirection: 'column', ...card, children: [
        Text({ bold: true, children: [g] }),
        ...ENDPOINTS.filter(x => x.group === g).map(x => endpointLauncher($, Button, pane, costs, x)),
      ] })),
      ...(tabs.note[pane] ? [Text({ color: 'warning', children: [tabs.note[pane]] })] : []),
    ] })
  })

  on('ui.render', { component: 'Pane', requestId: 'sc-combos' }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const rows = await combosNow($)
    const pane = COMBOS_PANE.id
    const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
    return Box({ flexDirection: 'column', gap: 1, children: [
      ...(rows.length ? [] : [Text({ color: 'warning', children: ["The research packages couldn't be read."] })]),
      ...rows.filter(r => r.options.length).map(r => Box({ key: r.row, flexDirection: 'column', ...card, children: [
        Text({ bold: true, children: [r.header] }),
        ...r.options.flatMap(o => [
          Text({ dimColor: true, wrap: 'wrap', children: [o.label] }),
          comboLauncher($, Button, pane, o),
        ]),
      ] })),
      ...(tabs.note[pane] ? [Text({ color: 'warning', children: [tabs.note[pane]] })] : []),
    ] })
  })

  // 5c: a suggestion is drawn as its name, its reason as a dim Text, and the real button through launcher(): a press
  // sends that button's own text. Ids no tab draws any more are left out.
  on('ui.render', { component: 'Pane', requestId: 'sc-suggested' }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const costs = await jsonOf($, 'hooks/costs.json')
    const combos = (await combosNow($)).flatMap(r => r.options)
    const pane = SUGGESTED_PANE.id
    const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
    const shown = suggest.items.flatMap(p => {
      const x = ENDPOINTS.find(y => slugOf(y.call) === p.id)
      const o = combos.find(c => c.key === p.id)
      return x || o ? [{ p, x, o }] : []
    })
    const status = !suggest.opened ? NOT_OPENED : suggest.inFlight ? LOADING : suggest.note
    return Box({ flexDirection: 'column', gap: 1, children: [
      ...(shown.some(s => s.x && s.x.kind !== 'none') ? [targetBox($, e)] : []),
      ...shown.map(({ p, x, o }) => Box({ key: `s-${p.id}`, flexDirection: 'column', ...card, children: [
        Text({ bold: true, children: [x ? `${x.group} · ${x.name}` : o!.label] }),
        Text({ dimColor: true, children: [p.why] }),
        x ? endpointLauncher($, Button, pane, costs, x) : comboLauncher($, Button, pane, o!),
      ] })),
      ...(status ? [Text({ dimColor: true, children: [status] })] : []),
      ...(tabs.note[pane] ? [Text({ color: 'warning', children: [tabs.note[pane]] })] : []),
      Text({ dimColor: true, children: [tokensLine(suggest.tokens)] }),
    ] })
  })

  // 5d: the Round-up. Its top line is the Budget pane's own; this session's calls (refusals apart, never counted); the
  // files its counted calls saved (a file: Link on the terminal for an absolute path, the only surface the engine sends
  // one to, within the 2,048-character address a Link may hold; Text everywhere else); the last routine; and Summarize.
  on('ui.render', { component: 'Pane', requestId: 'sc-roundup' }, async ($, e) => {
    const { Box, Text, Button, Link } = $.ui.resolve(e)
    const { revxl, sid } = await where($)
    if (!revxl) return Text({ children: ['No home folder: the guard keeps no record to show.'] })
    const { spent, limit } = await spendOf($, revxl, sid, choiceOf((await budgetFile($, revxl)).b))
    const now = await $.clock.now()
    const record = (await $.fs.read(`${revxl}/socialcrawl-calls.jsonl`).catch(() => null)) ?? ''
    const rows = callRows(record, sid)
    const routine = lastRoutine(record, sid)
    const files = await Promise.all(roundup.files.map(async f => ({ ...f, gone: await $.fs.stat(f.path).then(() => false, () => true) })))
    const text = summaryOf(rows.paid, roundup.files.map(f => f.path), spent, limit)
    const pane = ROUNDUP_PANE.id
    const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const
    return Box({ flexDirection: 'column', gap: 1, children: [
      e.surface === 'desktop'
        ? $.ui.resolve(e).Svg(hero(spent, limit, reads.snap ? reads.snap.balance : null, reads.snap ? ageOf(now - reads.snap.at) : ''))
        : Box({ key: 'top', ...card, children: [Text({ children: [paneTop(reads.snap, now, spent, limit)] })] }),
      Box({ key: 'calls', flexDirection: 'column', ...card, children: [
        Text({ bold: true, children: ["This session's calls"] }),
        ...(rows.paid.length ? rows.paid : ['No paid calls yet.']).map(r => Text({ children: [shown(r)] })),
      ] }),
      ...(rows.refused.length ? [Box({ key: 'refused', flexDirection: 'column', ...card, children: [
        Text({ dimColor: true, bold: true, children: ['Refused, not counted'] }),
        ...rows.refused.map(r => Text({ dimColor: true, children: [shown(r)] })),
      ] })] : []),
      Text({ dimColor: true, children: [QUOTES_NOTE] }),
      Box({ key: 'files', flexDirection: 'column', ...card, children: [
        Text({ bold: true, children: ['Saved files'] }),
        ...(files.length ? files.map(f => Text({ children: [
          e.surface === 'terminal' && isAbsolute(f.path) && fileHref(f.path).length <= 2048 ? Link({ href: fileHref(f.path), label: nameOf(f.path) }) : nameOf(f.path),
          ...(f.gone ? [' · gone'] : []),
        ] })) : [Text({ children: ['None saved yet.'] })]),
      ] }),
      Box({ key: 'routine', flexDirection: 'column', ...card, children: [
        Text({ bold: true, children: ['Last routine'] }),
        ...(routine ? routineLines(routine) : [NO_ROUTINE]).map(l => Text({ children: [shown(l)] })),
      ] }),
      launcher($, Button, pane, 'sc-roundup-summarize', 'Summarize', 'Summarize  →', () => text),
      ...(tabs.note[pane] ? [Text({ color: 'warning', children: [tabs.note[pane]] })] : []),
    ] })
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

  on('ui.render', { component: 'Pane', requestId: 'sc-budget' }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const { revxl, sid } = await where($)
    if (!revxl) return Text({ children: ['No home folder: the budget file has nowhere to live.'] })
    const file = await budgetFile($, revxl)
    const saved = choiceOf(file.b)
    const p: Choice = { ...saved, ...pane.pressed }
    const sent = changesOf(p, saved, file.garbled)
    const { spent, limit } = await spendOf($, revxl, sid, saved)

    const pick = (key: string, label: string, isOn: boolean, patch: Partial<Choice>) =>
      Button({ key, label, variant: isOn ? 'primary' : 'secondary', onPress: () => press($, patch) })
    const presets = (k: string, vals: number[], cur: number, field: 'session') => ({
      row: vals.map(v => pick(`${k}-${v}`, fmt(v), cur === v, { [field]: v })),
      current: vals.includes(cur) ? [] : [Text({ children: [`Current: ${fmt(cur)}`] })],
    })
    const ses = presets('ps', SESSION_PRESETS, p.session ?? 0, 'session')
    const warns = warningsOf(p, reads.snap ? reads.snap.balance : null, spent)
    const now = await $.clock.now()
    const card = { borderStyle: 'round', borderColor: 'subtle', paddingX: 1 } as const

    return Box({ flexDirection: 'column', gap: 1, children: [
      // The Lantern hero card on desktop; elsewhere the same top line in a round box (5a-iii S2).
      e.surface === 'desktop'
        ? $.ui.resolve(e).Svg(hero(spent, limit, reads.snap ? reads.snap.balance : null, reads.snap ? ageOf(now - reads.snap.at) : ''))
        : Box({ key: 'top', ...card, children: [Text({ children: [paneTop(reads.snap, now, spent, limit)] })] }),
      Box({ key: 'session', flexDirection: 'column', ...card, children: [
        Text({ bold: true, children: ['Budget per run'] }),
        Text({ dimColor: true, children: [SESSION_HELP] }),
        Box({ flexDirection: 'row', gap: 1, children: [...ses.row, pick('ps-auto', 'Automatic', p.session === null, { session: null })] }),
        ...(p.session === null ? [] : ses.current),
      ] }),
      ...(warns.length ? [Box({ key: 'warnings', flexDirection: 'column', children: warns.map(w => Text({ color: 'warning', children: [w] })) })] : []),
      ...(file.garbled ? [Text({ color: 'warning', children: [GARBLED] })] : []),
      ...(file.error ? [Text({ color: 'error', children: [READ_ERROR] })] : [Box({ key: 'save-row', flexDirection: 'row', gap: 1, children: [
        Button({ key: 'save', label: 'Save  →', variant: 'primary', onPress: async () => {
          if (!sent) {
            pane.note = 'Nothing to save: the file already holds this.'
            return $.ui.invalidate('ui.render')
          }
          await afterSave($, revxl, sent, await helper($, 'budget-write', revxl, JSON.stringify(sent)).catch(() => null))
        } }),
        ...(sent ? [Text({ color: 'warning', children: ['Unsaved changes'] })] : []),
      ] })]),
      ...(pane.note ? [Text({ color: pane.note === SAVED ? 'success' : 'error', children: [pane.note] })] : []),
    ] })
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
