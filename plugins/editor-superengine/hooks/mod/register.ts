import type { Register, EngineInterface, Timer } from 'claude-code'
import {
  cockpit, act, fill, openSends, normPath, folderKey, videosDir, reelNames, masterCandidates, probeOf, parseJson, isRecord, ok, missing, unreadable,
  CONFIG, PLATFORM, FOLDERS, JSON_FILES, STAGES, SENDS, BOARDS, BOARD_NAME, LABELS, TOGGLE, BATON_UNREAD,
  type Read, type Entry, type Input, type ReelIn, type Probe, type View, type ActionId,
} from './logic'

// Module state. `$` is never stored; helpers receiving it are declared at the top level for the mod loader.
// ponytail: a hot reload or worker respawn drops it (the picked reel, the one autostart); move to $.state if that matters.
let picked: string | undefined   // the reel Switch reel picked: shown while it still exists
let autoOpened = false           // the pane opened itself already in this module's life
let toastQueue = Promise.resolve()   // serialize timer/turn checks so one Send version toasts once

const PANE = 'ed-cockpit'
const TITLE = 'Editor Cockpit'
const OURS = 'editor-superengine'
// Lantern (the shared build signature): near-black cards, hairlines, one coral. Hex only inside Svg markup.
const L = { card: '#111113', line: '#26262B', ink: '#F3F2EF', muted: '#8C8C93', faint: '#3A3A40', acc: '#FF5A3C' }
const FONT = "Geist, 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif"
const ARROW = '  →'   // on the main button, added at draw time only
// Parsed reads by path, kept while the file's mtime is unchanged. ponytail: never evicted; a few paths per reel.
const cache = new Map<string, { mtimeMs: number; value: Read<unknown> }>()
// ffprobe's answer per `<path>|<mtimeMs>`: each master candidate is probed at most once per version.
const probes = new Map<string, Probe>()

/** A settled engine call: its value, missing (the engine's ENOENT / ENOTDIR), or unreadable with the reason. */
const settle = <T>(p: Promise<T>): Promise<Read<T>> => p.then(v => ok(v), (x: unknown) => {
  const why = String((x as Error)?.message ?? x)
  return /\bENO(ENT|TDIR)\b/.test(why) ? missing<T>() : unreadable<T>(why)
})
const why = (x: unknown) => String((x as Error)?.message ?? x)

// ---- Desktop drawings (Svg is drawn on the desktop surface only)
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#8217;')
const svg = (w: number, h: number, body: string, defs = '') =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${defs ? `<defs>${defs}</defs>` : ''}${body}</svg>`

/** Hero card (Look A): eyebrow, headline with its last word in coral, sub lines, lamp glow. */
function hero(v: View) {
  const sp = v.head.lastIndexOf(' '), h = 92 + v.sub.length * 16
  return svg(400, h, `<rect x="1" y="1" width="398" height="${h - 2}" rx="20" fill="${L.card}" stroke="${L.line}"/>`
    + `<rect x="1" y="1" width="398" height="${h - 2}" rx="20" fill="url(#lamp)"/>`
    + `<text x="22" y="30" font-family="${FONT}" font-size="10" letter-spacing="2.2" fill="${L.muted}">${esc(v.eyebrow)}</text>`
    + `<text x="22" y="64" font-family="${FONT}" font-size="25" font-weight="300" letter-spacing="-0.5" fill="${L.ink}">${esc(v.head.slice(0, sp + 1))}<tspan font-weight="600" fill="${L.acc}">${esc(v.head.slice(sp + 1))}</tspan></text>`
    + v.sub.map((l, i) => `<text x="22" y="${90 + i * 16}" font-family="${FONT}" font-size="12" fill="${L.muted}">${esc(l)}</text>`).join(''),
  `<radialGradient id="lamp" cx="85%" cy="0%" r="70%"><stop offset="0" stop-color="${L.acc}" stop-opacity=".22"/><stop offset="1" stop-color="${L.acc}" stop-opacity="0"/></radialGradient>`)
}

/** The nine-stage stepper: checks on the stages done, a ring on the current one (pulsing when animated), white rings
 *  with no reel; an open optional stage (Grade) is dashed. */
function stepper(v: View, animate: boolean) {
  const n = STAGES.length, pad = 22, step = (400 - pad * 2) / (n - 1), idle = v.cur < 0
  const track = `<line x1="${pad}" y1="16" x2="${400 - pad}" y2="16" stroke="${idle ? L.ink : L.faint}" stroke-opacity="${idle ? 0.5 : 1}" stroke-width="2"/>`
    + (v.cur > 0 ? `<line x1="${pad}" y1="16" x2="${pad + step * v.cur}" y2="16" stroke="${L.acc}" stroke-width="2"/>` : '')
  const dots = STAGES.map((s, i) => {
    const x = pad + step * i
    const body = v.done[i]
      ? `<circle cx="${x}" cy="16" r="8" fill="${L.acc}"/><path d="M${x - 3.5} 16 l2.5 2.5 l4.5 -5" stroke="${L.card}" stroke-width="2" fill="none" stroke-linecap="round"/>`
      : i === v.cur
        ? `<circle cx="${x}" cy="16" r="8" fill="${L.card}" stroke="${L.acc}" stroke-width="2"/><circle cx="${x}" cy="16" r="3.5" fill="${L.acc}">${animate ? '<animate attributeName="r" values="2.5;5;2.5" dur="1.6s" repeatCount="indefinite"/>' : ''}</circle>`
        : `<circle cx="${x}" cy="16" r="8" fill="${idle ? L.ink : L.card}" stroke="${idle ? L.ink : L.faint}" stroke-width="2"${s.optional ? ' stroke-dasharray="3 3"' : ''}/>`
    return body + `<text x="${x}" y="40" text-anchor="middle" font-family="${FONT}" font-size="9.5" fill="${i === v.cur ? L.ink : L.muted}"${i === v.cur ? ' font-weight="700"' : ''}>${esc(s.short)}</text>`
  }).join('')
  return svg(400, 48, track + dots)
}

/** The band's one-line stepper (desktop). */
function pill(v: View) {
  const w = 230
  return svg(w, 22, `<rect x="1" y="1" width="${w - 2}" height="20" rx="10" fill="${L.card}" stroke="${L.line}"/>`
    + `<circle cx="13" cy="11" r="4" fill="${v.cur < 0 ? L.muted : L.acc}"/>`
    + `<text x="24" y="15" font-family="${FONT}" font-size="11" font-weight="600" fill="${L.ink}">${esc(v.pill)}</text>`)
}

/** The text stepper off Desktop: ■ done, ◐ current, □ the rest. */
const glyphs = (v: View) => STAGES.map((_, i) => (v.done[i] ? '■' : i === v.cur ? '◐' : '□')).join('')

// ---- reads

/** The engine calls the loader makes, as closures each hook spells on its own `$`: the loader never holds `$`. */
type Io = {
  cwd: () => Promise<string>
  now: () => Promise<number>
  stat: (path: string) => Promise<{ mtimeMs: number }>
  read: (path: string) => Promise<string>
  list: (path: string) => Promise<Entry[]>
  store: (key: string) => Promise<unknown>
  run?: (argv: string[]) => Promise<{ exitCode: number; stdout: string }>   // ffprobe: given only on a refresh, never on a draw
}

/** cockpit()'s input. Every file failure becomes missing or unreadable, never a throw (only a failed cwd throws);
 *  a file is read through the mtime cache. With `io.run`, each new master candidate is ffprobed once. */
async function load(io: Io): Promise<{ root: string; input: Input }> {
  const root = normPath(await io.cwd())
  const now = await io.now()
  /** One file through the mtime cache: the stat decides, the read runs only on a miss; a failed read is not kept. */
  const file = async <T>(path: string, parse: (r: Read<string>) => Read<T>): Promise<Read<T>> => {
    const st = await settle(io.stat(path))
    if (st.status !== 'ok') return st
    const hit = cache.get(path)
    if (hit && hit.mtimeMs === st.value.mtimeMs) return hit.value as Read<T>
    const text = await settle(io.read(path))
    if (text.status !== 'ok') return text
    const value = parse(text)
    cache.set(path, { mtimeMs: st.value.mtimeMs, value })
    return value
  }
  const config = await file(`${root}/${CONFIG}`, parseJson)   // missing or broken: defaults, never an error card
  const vdir = `${root}/${videosDir(config)}`
  const videos = await settle(io.list(vdir))
  let ffprobe: string | undefined
  if (io.run) {
    const p = await file(`${root}/${PLATFORM}`, parseJson)
    const tools = p.status === 'ok' && isRecord(p.value) && isRecord(p.value.tools) ? p.value.tools : {}
    ffprobe = typeof tools.ffprobe === 'string' && tools.ffprobe ? tools.ffprobe : undefined
  }
  // ponytail: four listings per reel on every draw; cache them by folder if a workspace grows past a few dozen reels.
  const reels = await Promise.all(reelNames(videos).map(async (name): Promise<ReelIn> => {
    const dir = `${vdir}/${name}`
    const got = await Promise.all(FOLDERS.map(f => settle(io.list(f === 'root' ? dir : `${dir}/${f}`))))
    const lists = Object.fromEntries(FOLDERS.map((f, i) => [f, got[i]!])) as ReelIn['lists']
    const listed = (n: string) => lists.root.status === 'ok' && lists.root.value.some(x => x.name === n && x.kind === 'file')
    const json = Object.fromEntries(await Promise.all(JSON_FILES.map(async n =>
      [n, listed(n) ? await file(`${dir}/${n}`, parseJson) : missing()] as const)))
    const r: ReelIn = { name, lists, json, probe: {} }
    for (const x of masterCandidates(r)) {
      const path = `${dir}/renders/${x.name}`, key = `${path}|${x.mtimeMs}`
      if (io.run && ffprobe && !probes.has(key)) {
        const argv = [ffprobe, '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', path]
        probes.set(key, await io.run(argv).then(probeOf, () => 'unknown' as const))
      }
      r.probe[x.name] = probes.get(key) ?? 'unknown'   // not probed (no ffprobe, or a draw before any refresh): by existence
    }
    return r
  }))
  // ponytail: a store that cannot be read counts as empty (no baseline: nothing open; no acks).
  const base = await io.store('editorBaseline').catch(() => undefined)
  const acked = await io.store('editorAcked').catch(() => undefined)
  const b = isRecord(base) ? base[folderKey(root)] : undefined
  return { root, input: { now, videos, reels, baseline: typeof b === 'number' ? b : undefined,
    acked: isRecord(acked) ? acked : {}, configFound: config.status !== 'missing' } }
}

/** A refresh: load with ffprobe on, then pin the baton (a failed load pins the short line). */
async function repin(io: Io, status: (t: string) => void, log: (what: string, x: unknown) => void): Promise<{ line: string; input?: Input }> {
  try {
    const { input } = await load(io), line = cockpit(input, picked).baton
    status(line)
    return { line, input }
  } catch (x) {
    log('status line', x)
    status(BATON_UNREAD)
    return { line: BATON_UNREAD }
  }
}

/** Reads for background checks and prompt context: no processes, UI actions or writes. */
const sendIo = ($: EngineInterface): Io => ({
  cwd: () => $.session.cwd(), now: () => $.clock.now(), stat: p => $.fs.stat(p), read: p => $.fs.read(p),
  list: p => $.fs.list(p), store: k => $.store.get(k),
})

const pending = (input: Input) => input.reels.flatMap(r => openSends(r, input.baseline, input.acked).map(s => ({ ...s, reel: r.name })))
const sendPhrase = (s: { reel: string; board: keyof typeof BOARD_NAME }) => fill(LABELS.send.phrase!, s.reel, BOARD_NAME[s.board])

/** An optional session-presence record, never a skill input. */
async function heartbeat($: EngineInterface) {
  const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
  if (!home) return
  const id = await $.session.id()
  const version = JSON.parse(await $.fs.read(`${$.plugin.root}/.claude-plugin/plugin.json`)).version
  const ts = new Date(await $.clock.now()).toISOString().replace(/\.\d{3}Z$/, 'Z')
  await $.fs.write(`${normPath(home)}/.claude/revxl/heartbeat/${OURS}/${id}.json`, JSON.stringify({
    v: 1, plugin: OURS, version, pane_command: '/editor', session_id: id, ts,
  }))
}

/** Export the current workspace's Send state for hub_rows, with one write; failures never interrupt editing. */
async function exportCockpit($: EngineInterface) {
  try {
    const root = normPath(await $.session.cwd())
    const config = parseJson(await settle($.fs.read(`${root}/${CONFIG}`)))
    const paths = config.status === 'ok' && isRecord(config.value) && isRecord(config.value.paths) ? config.value.paths : {}
    const rel = typeof paths.editor === 'string' && paths.editor ? paths.editor.replace(/\\/g, '/') : 'editor'
    const parts = rel.split('/').filter(s => s !== '' && s !== '.')
    if (rel.startsWith('/') || rel.includes(':') || parts.includes('..') || !parts.length) return
    const baselines = await $.store.get('editorBaseline'), acked = await $.store.get('editorAcked')
    const baseline = isRecord(baselines) ? baselines[folderKey(root)] : undefined
    await $.fs.write(`${root}/${parts.join('/')}/hub/cockpit-state.json`, JSON.stringify({
      baseline: typeof baseline === 'number' ? baseline : null, acked: isRecord(acked) ? acked : {},
    }))
  } catch { /* The Cockpit store remains authoritative if the export is unavailable. */ }
}

/** A successful main-agent Read acknowledges only a known Send directly under a real reel. */
async function ack($: EngineInterface, filePath: string) {
  const root = normPath(await $.session.cwd())
  const config = parseJson(await settle($.fs.read(`${root}/${CONFIG}`)))
  const videos = `${root}/${videosDir(config)}`
  const key = (p: string) => /^[A-Za-z]:\//.test(root) ? p.toLowerCase() : p
  const path = key(normPath(filePath)), prefix = `${key(videos)}/`
  if (!path.startsWith(prefix)) return
  const parts = path.slice(prefix.length).split('/')
  if (parts.length !== 2) return
  const send = SENDS.find(s => key(s.file) === parts[1])
  if (!send) return
  const name = reelNames(await settle($.fs.list(videos))).find(n => key(n) === parts[0])
  if (!name) return
  const stat = await $.fs.stat(`${videos}/${name}/${send.file}`)
  if (stat.kind !== 'file' || stat.isLink) return
  const old = await $.store.get('editorAcked'), map = isRecord(old) ? old : {}
  await $.store.set('editorAcked', { ...map, [`${name}/${send.file}`]: stat.mtimeMs })
  await exportCockpit($)
}

/** Kept at the top level so the mod loader can follow every use of `$`. */
async function checkSends($: EngineInterface) {
  toastQueue = toastQueue.then(async () => {
    const sends = pending((await load(sendIo($))).input)
    const old = await $.store.get('editorToasted')
    const toasted = new Set(Array.isArray(old) ? old.filter((x): x is string => typeof x === 'string') : [])
    for (const s of sends) {
      const id = `${s.reel}/${s.file}@${s.mtimeMs}`
      if (toasted.has(id)) continue
      toasted.add(id)
      await $.store.set('editorToasted', [...toasted])
      $.ui.toast(`${BOARD_NAME[s.board]} Send for ${s.reel}. Say "${sendPhrase(s)}".`)
    }
  }).catch(() => {})
  await toastQueue
}

export const register: Register = on => {
  let sendTimer: Timer | undefined
  // Serialize concurrent Reads so a store read-modify-write cannot lose acknowledgement keys.
  let ackQueue = Promise.resolve()

  on('session.start', async ($, e, next) => {
    const r = await next(e)
    $.clock.after(0, () => void heartbeat($).catch(() => {}))
    sendTimer?.cancel()
    const log = (what: string, x: unknown) => $.ui.log(`${OURS}: ${what}: ${why(x)}`, { to: 'debug' })
    await $.command.register({ name: 'editor', description: 'Open the Editor Cockpit' }).catch(x => log('/editor not registered', x))
    let here: string | undefined
    try {
      // The Send baseline: set once, at the first session start in this workspace, never moved.
      here = folderKey(await $.session.cwd())
      const b = await $.store.get('editorBaseline'), map = isRecord(b) ? b : {}
      if (typeof map[here] !== 'number') await $.store.set('editorBaseline', { ...map, [here]: await $.clock.now() })
    } catch (x) {
      log('baseline', x)
    }
    await exportCockpit($)
    sendTimer = $.clock.every(3000, () => void checkSends($))
    const io: Io = { cwd: () => $.session.cwd(), now: () => $.clock.now(), stat: p => $.fs.stat(p), read: p => $.fs.read(p),
      list: p => $.fs.list(p), store: k => $.store.get(k), run: argv => $.process.run(argv, { timeoutMs: 15_000 }) }
    const { input } = await repin(io, t => $.ui.status(t), log)
    // Autostart: unfocused, at most once, only in an editor workspace not switched off. Never gated on isInteractive
    // or surface: Claude Code Desktop starts sessions with isInteractive false and surface null.
    try {
      const off = await $.store.get('autostartOff')
      if (!autoOpened && input?.configFound && here !== undefined && !(Array.isArray(off) && off.includes(here))) {
        autoOpened = true
        await $.ui.open({ id: PANE, title: TITLE })
      }
    } catch (x) {
      log('autostart', x)
    }
    return r
  })

  on('prompt.submit', async ($, e, next) => {
    let brief = ''
    try {
      const sends = pending((await load(sendIo($))).input)
      if (sends.length) brief = [
        'Open editor Sends. Nothing is acted on without the person\'s next message. Wait for their explicit go-ahead.',
        ...sends.map(s => `${BOARD_NAME[s.board]} Send for ${s.reel}: "${sendPhrase(s)}"`),
      ].join('\n')
    } catch { /* An unavailable workspace must not block the person's prompt. */ }
    return next(brief ? { ...e, context: [...(e.context ?? []), brief] } : e)
  })

  on('tool.call', { tool: 'Read' }, async ($, e, next) => {
    const r = await next(e)
    if (!e.agentId && !('deny' in r)) {
      ackQueue = ackQueue.then(() => ack($, e.file_path)).catch(() => {})
      await ackQueue
    }
    return r
  })

  // /editor: answers its own command (no next), so it opens the pane as the person's own ask.
  on('command.run', { command: 'editor' }, async $ => {
    const log = (what: string, x: unknown) => $.ui.log(`${OURS}: ${what}: ${why(x)}`, { to: 'debug' })
    const io: Io = { cwd: () => $.session.cwd(), now: () => $.clock.now(), stat: p => $.fs.stat(p), read: p => $.fs.read(p),
      list: p => $.fs.list(p), store: k => $.store.get(k), run: argv => $.process.run(argv, { timeoutMs: 15_000 }) }
    const { line } = await repin(io, t => $.ui.status(t), log)
    try {
      const opened = await $.ui.open({ id: PANE, title: TITLE, focus: true })
      return { text: opened.isPlaced ? 'Opened the Editor Cockpit.' : `The Editor Cockpit couldn't be shown here. ${line}` }
    } catch (x) {
      log('/editor open', x)
      $.ui.toast('Editor Cockpit could not open')
      return { text: 'The Editor Cockpit could not open.' }
    }
  })

  // Main loop only. A skill may have written files: pin the baton again, then the band and the pane redraw.
  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined && e.reason === 'answer') {
      const log = (what: string, x: unknown) => $.ui.log(`${OURS}: ${what}: ${why(x)}`, { to: 'debug' })
      const io: Io = { cwd: () => $.session.cwd(), now: () => $.clock.now(), stat: p => $.fs.stat(p), read: p => $.fs.read(p),
        list: p => $.fs.list(p), store: k => $.store.get(k), run: argv => $.process.run(argv, { timeoutMs: 15_000 }) }
      await repin(io, t => $.ui.status(t), log)
      await checkSends($)
      $.ui.invalidate('ui.render')
    }
    return next(e)
  })

  // The band: shown only while a reel is in progress, our row first, other plugins' bands beneath it untouched.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const below = await next(e)
    if ((e as any).props?.hasSurvey) return below
    const log = (what: string, x: unknown) => $.ui.log(`${OURS}: band ${what}: ${why(x)}`, { to: 'debug' })
    const io: Io = { cwd: () => $.session.cwd(), now: () => $.clock.now(), stat: p => $.fs.stat(p), read: p => $.fs.read(p),
      list: p => $.fs.list(p), store: k => $.store.get(k) }
    let v: View
    try { v = cockpit((await load(io)).input, picked) } catch (x) { log('read', x); return below }
    if (v.state === 'nothing') return below
    const { Box, Text, Button, Svg }: any = $.ui.resolve(e)
    const say = (text?: string) => { if (text) void $.prompt.submit({ text, asUser: true }).catch(x => log('press', x)) }
    const progress = Box({ key: 'ed-progress', flexDirection: 'column', children: [
      Text({ bold: true, children: ['Editing progress'] }),
      e.surface === 'desktop' ? Svg({ alt: v.alt, width: 230, source: pill(v) })
        : Text({ children: [Text({ color: 'claude', children: [glyphs(v)] }), ` ${v.pill}`] })] })
    const row = Box({ key: 'ed-band', flexDirection: 'row', flexWrap: 'wrap', columnGap: 1, children: [
      progress,
      Button({ key: 'band-next', label: LABELS.next.label, onPress: () => say(act('next', v).phrase) }),
      ...(v.board ? [Button({ key: 'band-board', label: LABELS[v.board].label, onPress: () => say(act(v.board!, v).phrase) })] : []),
      Button({ key: 'band-cockpit', label: LABELS.cockpit.label, onPress: () => void $.ui.open({ id: PANE, title: TITLE, focus: true }).catch(x => {
        log('open', x)
        $.ui.toast('Editor Cockpit could not open')
      }) }),
    ] })
    return Box({ flexDirection: 'column', children: below ? [row, below] : [row] })
  })

  // The pane: one screen, Look A. The whole body sits in one try; the catch draws the error card.
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button, Svg }: any = $.ui.resolve(e)   // Svg: drawn on the desktop surface only
    const log = (what: string, x: unknown) => $.ui.log(`${OURS}: cockpit ${what}: ${why(x)}`, { to: 'debug' })
    const say = (text?: string) => { if (text) void $.prompt.submit({ text, asUser: true }).catch(x => log('press', x)) }
    try {
      const io: Io = { cwd: () => $.session.cwd(), now: () => $.clock.now(), stat: p => $.fs.stat(p), read: p => $.fs.read(p),
        list: p => $.fs.list(p), store: k => $.store.get(k) }
      const { root, input } = await load(io)
      const v = cockpit(input, picked), desk = e.surface === 'desktop', here = folderKey(root)
      const offNow = await $.store.get('autostartOff').then(x => Array.isArray(x) && x.includes(here), () => false)

      const button = (key: string, id: ActionId, label = act(id, v).label, primary = false) =>
        Button({ key, label, ...(primary ? { variant: 'primary' } : {}), onPress: () => say(act(id, v).phrase) })
      const row = (key: string, children: unknown[]) => Box({ key, flexDirection: 'row', flexWrap: 'wrap', columnGap: 1, children })
      const card = (key: string, title: string, child: unknown) =>
        Box({ key, flexDirection: 'column', borderStyle: 'round', borderColor: 'subtle', paddingX: 1, children: [Text({ bold: true, children: [title] }), child] })
      // Switch reel asks straight from the press: the 3 latest reels + Editor hub. Free "Other" text is ignored.
      const switchReel = () => void (async () => {
        const answer = (await $.ui.ask('Which reel do you want to work on?', { header: 'Editor', options: [...v.latest, LABELS.hub.label] })).trim()
        if (v.latest.includes(answer)) {
          picked = answer
          const io2: Io = { ...io, run: argv => $.process.run(argv, { timeoutMs: 15_000 }) }
          await repin(io2, t => $.ui.status(t), log)
          $.ui.invalidate('ui.render')
        } else if (answer === LABELS.hub.label) say(act('hub', v).phrase)
      })().catch(x => log('switch reel', x))   // dismissed, or a -p run

      const heroCard = desk ? Svg({ alt: `${v.eyebrow}: ${v.head}. ${v.sub.join(' ')}`, source: hero(v) })
        : Box({ key: 'hero', flexDirection: 'column', borderStyle: 'round', borderColor: 'subtle', paddingX: 1, children: [
          Text({ dimColor: true, children: [v.eyebrow] }), Text({ bold: true, children: [v.head] }),
          ...v.sub.map(l => Text({ dimColor: true, children: [l] }))] })
      const stepperCard = card('progress', 'Editing progress', desk ? Svg({ alt: v.alt, source: stepper(v, true), isInteractive: true })
        : Text({ children: [Text({ color: 'claude', children: [glyphs(v)] }), v.cur < 0 ? '' : ` ${STAGES[v.cur]!.name}`] }))
      // Each board marked: ✓ its stage done, ● the current stage's board.
      const boards = card('boards', 'Boards', row('board-row', BOARDS.map(b => {
        const i = STAGES.findIndex(s => s.board === b)
        return button(`board-${b}`, b, `${BOARD_NAME[b]}${v.done[i] ? ' ✓' : v.board === b ? ' ●' : ''}`)
      })))
      const toggle = input.configFound || offNow ? [row('autostart-act', [Button({ key: 'autostart', label: offNow ? TOGGLE.on : TOGGLE.off,
        onPress: () => void (async () => {
          const x = await $.store.get('autostartOff'), rest = (Array.isArray(x) ? x : []).filter(f => f !== here)
          await $.store.set('autostartOff', offNow ? rest : [...rest, here])
          $.ui.invalidate('ui.render')
        })().catch(x => log('autostart', x)) })])] : []

      return Box({ key: 'cockpit', flexDirection: 'column', rowGap: 1, children: [
        heroCard,
        row('main-act', [button('main', v.main, `${act(v.main, v).label}${ARROW}`, true)]),
        row('quick', [button('hub', 'hub'), button('next', 'next'), Button({ key: 'switch', label: LABELS.switch.label, onPress: switchReel })]),
        stepperCard,
        boards,
        ...toggle,
      ] })
    } catch (x) {
      log('draw', x)
      return Box({ key: 'cockpit-error', flexDirection: 'column', borderStyle: 'round', borderColor: 'error', paddingX: 1, children: [
        Text({ bold: true, children: ['Something went wrong drawing your Editor Cockpit'] }),
        Box({ key: 'error-act', flexDirection: 'row', children: [Button({ key: 'error-next', label: LABELS.next.label, variant: 'primary',
          onPress: () => say(act('next', {}).phrase) })] }),
      ] })
    }
  })
}
