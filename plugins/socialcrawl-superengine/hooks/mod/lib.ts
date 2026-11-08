// Pure helpers of the SocialCrawl mod (0.4.0, slices 5a–5d, 6a and 3g). No `$` here: register.tsx reads, this file decides.
// Every rule that names the guard mirrors credit-guard.mjs (G) at the line given, so the band never
// disagrees with what the guard enforces.

/** The guard's session id (G:318), applied to `$.session.id()`. */
export function sidOf(id: unknown): string {
  return String(id || 'nosession').replace(/[^a-z0-9_-]/gi, '')
}

/** The guard's revxl folder (G:319-320): SC_REVXL_HOME as given (never trimmed) when it holds more than spaces, else <home>/.claude/revxl. */
export function revxlOf(override: string | undefined, home: string | undefined): string | null {
  if (override && override.trim()) return override
  return home ? `${home}/.claude/revxl` : null
}

/** A call-record line (G:482-485): ts, sid, paths, worst, committed, decision, kind, limit, balance, balanceAt, routine. */
export type Rec = { sid?: unknown; paths?: unknown; worst?: unknown; committed?: unknown; decision?: unknown; kind?: unknown; limit?: unknown; routine?: unknown }

/** This sid's newest record line: walks back from the end, skipping a line that doesn't parse (a partial last line). */
export function newestFor(jsonl: string, sid: string): Rec | null {
  const lines = jsonl.split('\n')
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const o: unknown = JSON.parse(lines[i] ?? '')
      if (o && typeof o === 'object' && (o as Rec).sid === sid) return o as Rec
    } catch { /* not a whole line */ }
  }
  return null
}

/** The budget file's bytes as G:326 reads them: FF FE is UTF-16LE, else UTF-8 with one EF BB BF dropped. */
export function decodeBytes(base64: string): string {
  const bin = atob(base64)
  if (bin.charCodeAt(0) === 0xff && bin.charCodeAt(1) === 0xfe) {
    let s = ''
    for (let i = 2; i + 1 < bin.length; i += 2) s += String.fromCharCode(bin.charCodeAt(i) | (bin.charCodeAt(i + 1) << 8))
    return s
  }
  const start = bin.charCodeAt(0) === 0xef && bin.charCodeAt(1) === 0xbb && bin.charCodeAt(2) === 0xbf ? 3 : 0
  const bytes = new Uint8Array(bin.length - start)
  for (let i = start; i < bin.length; i++) bytes[i - start] = bin.charCodeAt(i)
  return new TextDecoder('utf-8').decode(bytes)
}

/** The budget file's object (G:1204-1205): garbled JSON, an array, a string or null is no budget. Never throws. */
export function parseBudget(text: string | null): Record<string, unknown> {
  try {
    const o: unknown = JSON.parse(text ?? '')
    if (o && typeof o === 'object' && !Array.isArray(o)) return o as Record<string, unknown>
  } catch { /* no budget */ }
  return {}
}

/** G:1207: a budget number counts only as a whole number from 1 to 20,000. */
export const isBudget = (v: unknown): v is number => Number.isInteger(v) && (v as number) >= 1 && (v as number) <= 20000

/** The session state file's `spent`: a whole number of 0 or more, else 0. */
export function spentOf(stateText: string | null): number {
  try {
    const s: unknown = (JSON.parse(stateText ?? '') as { spent?: unknown }).spent
    if (Number.isInteger(s) && (s as number) >= 0) return s as number
  } catch { /* 0 */ }
  return 0
}

/** The limit the guard applied, from this sid's newest line: a whole number of 1 or more, else null. */
export function recordLimit(last: Rec | null): number | null {
  const l = last ? last.limit : null
  return Number.isInteger(l) && (l as number) >= 1 ? (l as number) : null
}

export type Tone = 'success' | 'warning' | 'error'
export type Band = { gauge: string; text: string; warn: string; tone: Tone }

/** The band's one row: a 10-cell gauge, this session's spending, and one spending warning. */
export function bandOf(spent: number, limit: number | null, last: Rec | null): Band {
  const filled = limit ? Math.min(10, Math.round((spent / limit) * 10)) : 0
  const gauge = '█'.repeat(filled) + '░'.repeat(10 - filled)
  const text = limit ? `${spent} / ${limit} cr this session` : `${spent} cr this session · automatic cap`
  if (last && last.decision === 'deny') return { gauge, text, warn: ` · ⚠ last call refused (${String(last.kind)})`, tone: 'error' }
  const left = limit ? limit - spent : 0
  if (limit && left > 0 && left <= Math.max(1, Math.floor(limit * 0.1))) return { gauge, text, warn: ` · ⚠ ${left} cr left`, tone: 'warning' }
  return { gauge, text, warn: '', tone: 'success' }
}

/** The toast for a counted call: `SocialCrawl: <paths> · up to <worst> cr · <committed> / <limit> cr this session`. */
export function toastOf(r: Rec): string {
  const paths = Array.isArray(r.paths) ? r.paths.join(', ') : ''
  const limit = r.limit === null || r.limit === undefined ? '' : ` / ${String(r.limit)}`
  return `SocialCrawl: ${paths} · up to ${String(r.worst)} cr · ${String(r.committed)}${limit} cr this session`
}

/** What the helper printed: only its single JSON line counts; anything else is a failure of the helper. */
export type HelperOut = { ok: true; balance: number } | { ok: false; reason: string }
export function parseHelper(exitCode: number, stdout: string): HelperOut {
  const line = stdout.trim()
  if (exitCode !== 0 || line === '' || line.includes('\n')) return { ok: false, reason: 'helper' }
  try {
    const o = JSON.parse(line) as { ok?: unknown; balance?: unknown; reason?: unknown }
    if (o.ok === true && typeof o.balance === 'number' && Number.isFinite(o.balance)) return { ok: true, balance: o.balance }
    if (o.ok === false && typeof o.reason === 'string') return { ok: false, reason: o.reason }
  } catch { /* not JSON */ }
  return { ok: false, reason: 'helper' }
}

/** 4210 as 4,210. */
export function fmt(n: number): string {
  const [whole = '', frac] = String(n).split('.')
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (frac === undefined ? '' : `.${frac}`)
}

/** How long: `N min` (< 60), `N h` (< 48 h), else `N days`. */
export function spanOf(ms: number): string {
  const min = Math.floor(ms / 60_000)
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  return h < 48 ? `${h} h` : `${Math.floor(h / 24)} days`
}

/** How long ago: `just now` (< 1 min), else `N min ago`, `N h ago` or `N days ago`. */
export function ageOf(ms: number): string {
  return ms < 60_000 ? 'just now' : `${spanOf(ms)} ago`
}

export const STALE_MS = 30 * 60_000

/** The newest good balance read: the balance, and when the mod got it. */
export type Snap = { balance: number; at: number }

/**
 * The status line (D35): `SC Total Balance: <n> cr (<age>)`, plus ` · ⚠ <warning>` when one applies (stale wins over D10).
 * `fail` is the latest read's failure (null when it succeeded or none has finished). Undefined clears the line.
 */
export function statusOf(snap: Snap | null, fail: string | null, now: number, budget: Record<string, unknown>): string | undefined {
  if (!snap) return fail === null || fail === 'no-key' ? undefined : 'SC Total Balance: unavailable · ⚠ last check failed'
  const age = ageOf(now - snap.at)
  let warn = ''
  if (now - snap.at > STALE_MS) warn = `not updated for ${spanOf(now - snap.at)}`
  else {
    const over: number[] = []
    if (isBudget(budget.sessionBudget) && budget.sessionBudget > snap.balance) over.push(budget.sessionBudget)
    if (over.length) warn = `your ${Math.max(...over)} budget is above it`
  }
  return `SC Total Balance: ${fmt(snap.balance)} cr (${age})${warn ? ` · ⚠ ${warn}` : ''}`
}

// ---- The Budget pane (5a-ii, D34 layout B: preset buttons only, so it draws on mobile, which has no Input).

export const SESSION_PRESETS = [250, 500, 1000, 2000]
export const SESSION_HELP = 'The most one session, Desktop routine run or claude -p run may spend. Automatic = a quarter of your balance, up to 500.'
export const GARBLED = "The budget file couldn't be read; saving will replace it."
export const READ_ERROR = "The budget file couldn't be read just now. Close and reopen this pane to try again."
export const SAVED = 'Saved. Every open session uses it from its next paid call.'
export const OWNER = 'socialcrawl-budget-pane'

/** The budget file's object, or null when its text is garbled JSON, an array, a string or null. */
export function objOf(text: string): Record<string, unknown> | null {
  try {
    const o: unknown = JSON.parse(text)
    if (o && typeof o === 'object' && !Array.isArray(o)) return o as Record<string, unknown>
  } catch { /* garbled */ }
  return null
}

/** One budget choice. `session` null is Automatic (no sessionBudget key, D32). */
export type Choice = { session: number | null }

/** The file's choice as the guard reads it (G:1207-1214): a number that isn't valid is unset. Any other key, an old
 *  routines block included, is never read (D55). */
export function choiceOf(b: Record<string, unknown>): Choice {
  return { session: isBudget(b.sessionBudget) ? b.sessionBudget : null }
}

/** The helper's argument: sessionBudget when the pending choice differs from the file (always when the file is
 *  garbled, so the fresh file gets the owned key), or null when nothing differs. */
export function changesOf(p: Choice, saved: Choice, garbled: boolean): Record<string, unknown> | null {
  return garbled || p.session !== saved.session ? { sessionBudget: p.session } : null
}

/** The read-back: the file holds what was sent (sessionBudget gone for Automatic). */
export function holds(b: Record<string, unknown>, sent: Record<string, unknown>): boolean {
  return !('sessionBudget' in sent && (sent.sessionBudget === null ? 'sessionBudget' in b : b.sessionBudget !== sent.sessionBudget))
}

/** The helper's line after a save: ok only as its single JSON line with ok true; anything else is a failure. */
export function parseWrite(exitCode: number, stdout: string): { ok: true } | { ok: false; reason: string } {
  const line = stdout.trim()
  if (exitCode !== 0 || line === '' || line.includes('\n')) return { ok: false, reason: 'helper' }
  try {
    const o = JSON.parse(line) as { ok?: unknown; reason?: unknown }
    if (o.ok === true) return { ok: true }
    if (o.ok === false && typeof o.reason === 'string') return { ok: false, reason: o.reason }
  } catch { /* not JSON */ }
  return { ok: false, reason: 'helper' }
}

const WHY: Record<string, string> = {
  invalid: 'the helper refused these numbers',
  write: "the budget file couldn't be written",
  readback: "the budget file didn't read back as chosen",
  helper: "the save helper didn't answer",
}
export const notSaved = (reason: string) => `Not saved: ${WHY[reason] ?? reason}.`
export const aboveBalance = (balance: number) => `⚠ This is above your ${fmt(balance)} balance. Allowed; SocialCrawl stops at zero.`
export const belowSpent = (spent: number) => `⚠ This session has already spent ${fmt(spent)} cr; a budget this low stops further paid calls in this session.`

/** The pane's top line: `Balance 4,210 cr (2 min ago) · this session 120 / 500 cr`. */
export function paneTop(snap: Snap | null, now: number, spent: number, limit: number | null): string {
  const bal = snap ? `Balance ${fmt(snap.balance)} cr (${ageOf(now - snap.at)})` : 'Balance unavailable'
  return `${bal} · this session ${fmt(spent)}${limit ? ` / ${fmt(limit)} cr` : ' cr · automatic cap'}`
}

/** The D10 and below-spent warnings for a pending choice, in the pane's order. */
export function warningsOf(p: Choice, balance: number | null, spent: number): string[] {
  const out: string[] = []
  if (balance !== null && p.session !== null && p.session > balance) out.push(aboveBalance(balance))
  if (p.session !== null && p.session <= spent) out.push(belowSpent(spent))
  return out
}

// ---- The Endpoints and Combos tabs (5b, D22, D42, D43). A press is the person's pick of one priced call or package,
// sent as their prompt. Prices come from costs.json `range`, never `credits` (price.mjs:8-12); register.tsx reads the
// JSON files with $.fs.read and hands the parsed objects here.

/** What the one target box becomes for a call. */
export type Kind = 'handle' | 'url' | 'query' | 'region' | 'none' | 'channel' | 'company' | 'ad' | 'urls'
export type Endpoint = { group: string; call: string; name: string; kind: Kind }

const ep = (group: string, call: string, name: string, kind: Kind): Endpoint => ({ group, call, name, kind })
/** The 29 calls (D22), in group order. */
export const ENDPOINTS: readonly Endpoint[] = [
  ep('Instagram', 'GET instagram/profile/posts', 'Profile posts', 'handle'),
  ep('Instagram', 'GET instagram/profile', 'Profile', 'handle'),
  ep('Instagram', 'GET instagram/post/comments', 'Post comments', 'url'),
  ep('Instagram', 'GET instagram/search/profiles', 'Search profiles', 'query'),
  ep('TikTok', 'GET tiktok/user/audience', 'Audience', 'handle'),
  ep('TikTok', 'GET tiktok/post/comments', 'Post comments', 'url'),
  ep('TikTok', 'GET tiktok/search/users', 'Search users', 'query'),
  ep('TikTok', 'GET tiktok/trending', 'Trending feed', 'region'),
  ep('TikTok', 'GET tiktok/ads/top', 'Top ads', 'none'),
  ep('YouTube', 'GET youtube/video/comments', 'Video comments', 'url'),
  ep('YouTube', 'GET youtube/shorts/trending', 'Trending Shorts', 'none'),
  ep('YouTube', 'GET youtube/channel', 'Channel', 'channel'),
  ep('YouTube', 'GET youtube/channel/videos', 'Channel videos', 'handle'),
  ep('LinkedIn', 'GET linkedin/profile', 'Profile', 'url'),
  ep('LinkedIn', 'GET linkedin/profile/complete', 'Full profile', 'url'),
  ep('Facebook ads', 'GET facebook/adlibrary/search/companies', 'Find advertisers', 'query'),
  ep('Facebook ads', 'GET facebook/adlibrary/company/ads', "Advertiser's ads", 'company'),
  ep('Facebook ads', 'GET facebook/adlibrary/ad', 'One ad', 'ad'),
  ep('Reddit', 'GET reddit/omni-search', 'Search threads', 'query'),
  ep('Search', 'GET prism/creator-card', 'Creator card', 'handle'),
  ep('Search', 'GET search/creators', 'Find creators', 'query'),
  ep('Search', 'GET search/forums', 'Search forums', 'query'),
  ep('Search', 'GET search/news', 'Search news', 'query'),
  ep('Search', 'GET tavily/search', 'Web search (Tavily)', 'query'),
  ep('Search', 'GET perplexity/research', 'Research (Perplexity)', 'query'),
  ep('Search', 'GET web/scrape', 'Scrape a page', 'url'),
  ep('Search', 'GET prism/comments', 'All comments on a post', 'url'),
  ep('Search', 'GET prism/lookup', 'Look up a post URL', 'url'),
  ep('Search', 'POST prism/post-stats', 'Post stats (URL list)', 'urls'),
]

/** The API base, as the socialcrawl skill gives it (SKILL.md "Making API Calls"). */
const BASE = 'https://www.socialcrawl.dev/v1/'
/** The API host, from pieces: in a post-stats body the guard reads it as a call outside the URL word (G:1000-1001). */
const API_HOST = 'social' + 'crawl.dev'
export const NEED_TARGET = 'Type a target first.'
export const NO_POST_STATS = "Post stats can't take that URL from here. Ask Claude in the chat."
export const BUSY = 'One click at a time: wait for the queued one.'
export const TYPE_ON_DESKTOP = 'Type targets on desktop or in the terminal.'

const pathOf = (call: string) => call.slice(call.indexOf(' ') + 1)
/** A call's Button key and its -o file's name: the path with "-" for "/". */
export const slugOf = (call: string) => pathOf(call).replace(/\//g, '-')

/** A price from a range: `N cr` when flat, else `lo–hi cr`. */
export const priceOf = (range: readonly [number, number]) => (range[0] === range[1] ? `${range[1]} cr` : `${range[0]}–${range[1]} cr`)

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

/** costs.json's `range` for a "VERB path" key; null when the entry is missing or its range isn't two numbers. */
export function rangeIn(costs: unknown, call: string): [number, number] | null {
  const e = costs && typeof costs === 'object' ? (costs as Record<string, unknown>)[call] : undefined
  const r = e && typeof e === 'object' ? (e as { range?: unknown }).range : undefined
  return Array.isArray(r) && r.length === 2 && isNum(r[0]) && isNum(r[1]) ? [r[0], r[1]] : null
}

/** URL-encoded, with ' as %27 too (the guard's plain URL holds no '). */
const enc = (s: string) => encodeURIComponent(s).replace(/'/g, '%27')

/** What a press asks for: the call's full URL (and post-stats' JSON body), or the note saying why nothing is sent. */
export function requestOf(e: Endpoint, target: string): { url: string; body?: string } | { note: string } {
  const t = target.trim()
  const url = BASE + pathOf(e.call)
  const one = (param: string, v: string) => (v ? { url: `${url}?${param}=${enc(v)}` } : { note: NEED_TARGET })
  if (e.kind === 'none') return { url }
  if (e.kind === 'region') return one('region', t || 'US')
  if (!t) return { note: NEED_TARGET }
  if (e.kind === 'handle') return one('handle', t.replace(/^@/, ''))
  if (e.kind === 'channel') return /^http/i.test(t) ? one('url', t) : one('handle', t.replace(/^@/, ''))
  if (e.kind === 'company') return /^\d+$/.test(t) ? one('pageId', t) : one('companyName', t)
  if (e.kind === 'ad') return /^\d+$/.test(t) ? one('id', t) : one('url', t)
  if (e.kind === 'urls') {
    // A -d body holding @ isn't a plain curl (G:958); ' or " can't sit in it either, nor the API host (G:1000-1001).
    const urls = t.split(/[\s,]+/).filter(Boolean)
    return urls.length <= 100 && urls.every(u => /^https?:\/\//i.test(u) && !/[@'"]/.test(u) && !u.toLowerCase().includes(API_HOST)) ? { url, body: JSON.stringify({ urls }) } : { note: NO_POST_STATS }
  }
  return one(e.kind, t)
}

/** The Endpoints pick, as the prompt it submits (one line). */
export function endpointText(e: Endpoint, price: string, req: { url: string; body?: string }): string {
  return `[SocialCrawl launcher] My pick from the Endpoints tab, priced ${price}: make exactly one SocialCrawl call, ` +
    `${e.call.slice(0, e.call.indexOf(' '))} ${req.url}${req.body ? ` with body ${req.body}` : ''}. Use one plain curl in the Bash tool ` +
    `with the API key header from the socialcrawl skill, save the reply with -o /tmp/sc-${slugOf(e.call)}.json, then summarise it.`
}

/** One Combos option: its Button key `row:id` (an id can sit in two rows), its packages.json row and id, its curated
 *  id (or null) and its `quote.low–ceiling` price (or null). */
export type Combo = { key: string; row: string; id: string; label: string; curated: string | null; price: string | null }

/** packages.json's rows in file order, each with its header and options; a curated option is priced from its workflow. */
export function combosOf(packages: unknown, curated: unknown): { row: string; header: string; options: Combo[] }[] {
  const rows = packages && typeof packages === 'object' ? (packages as { rows?: unknown }).rows : undefined
  const flows = curated && typeof curated === 'object' ? (curated as { workflows?: unknown }).workflows : undefined
  const flow = (id: string) => (Array.isArray(flows) ? flows.find((w: unknown) => (w as { id?: unknown } | null)?.id === id) : undefined) as Record<string, unknown> | undefined
  const price = (o: Record<string, unknown> | undefined) => {
    const low = (o?.quote as { low?: unknown } | undefined)?.low
    return isNum(low) && isNum(o?.ceiling) ? priceOf([low, o.ceiling]) : null
  }
  return (Array.isArray(rows) ? rows : []).map((r: Record<string, unknown>) => {
    const row = String(r.id)
    const options = (Array.isArray(r.options) ? r.options : []).map((o: Record<string, unknown>) => {
      const cur = typeof o.curated === 'string' ? o.curated : null
      return { key: `${row}:${String(o.id)}`, row, id: String(o.id), label: String(o.label), curated: cur, price: price(cur ? flow(cur) : o) }
    })
    return { row, header: row.charAt(0).toUpperCase() + row.slice(1).replace(/_/g, ' '), options }
  })
}

/** The Combos pick, as the prompt it submits (one line). */
export function comboText(c: Combo & { price: string }): string {
  return `[SocialCrawl launcher] My pick from the Combos tab, priced ${c.price}: run the research-plays option "${c.label}" ` +
    `(packages.json row ${c.row}, option ${c.id}${c.curated ? `, curated ${c.curated}` : ''}). Ask me only for what it can't run ` +
    `without, show the price gate, then run it.`
}

// ---- The Suggested tab (5c, D45/D46). Haiku reads the brand's business-config.md, the person's last prompts and this
// session's call paths, and answers ids. Only an id that is a real Endpoints or Combos button key is kept, and a press
// runs that button's own text: Haiku's words reach a dim Text and nothing else.

/** One suggestion: a button key and a one-line reason. */
export type Suggestion = { id: string; why: string }

/** The allowed ids: the Endpoints keys from ENDPOINTS and the Combos keys from the rows the Combos tab draws. */
export function allowOf(combos: readonly { options: readonly Combo[] }[]): Set<string> {
  return new Set([...ENDPOINTS.map(x => slugOf(x.call)), ...combos.flatMap(r => r.options.map(o => o.key))])
}

/** Every allowed id with its name and price, for the system text. */
export function choicesOf(costs: unknown, combos: readonly { options: readonly Combo[] }[]): { id: string; name: string; price: string }[] {
  return [
    ...ENDPOINTS.map(x => {
      const r = rangeIn(costs, x.call)
      return { id: slugOf(x.call), name: `${x.group} ${x.name}`, price: r ? priceOf(r) : 'no price' }
    }),
    ...combos.flatMap(r => r.options).map(o => ({ id: o.key, name: o.label, price: o.price ?? 'no price' })),
  ]
}

/** A reason made safe to draw: control characters, format and direction characters and line breaks become spaces; one line of at most 120 characters. */
export const whyOf = (v: unknown) => shown(typeof v === 'string' ? v : '').replace(/ {2,}/g, ' ').trim().slice(0, 120)

/** Haiku's reply as suggestions: one JSON line each, kept only when its id is in `ok` exactly (no trimming, no case
 *  folding); a repeat or a line that isn't JSON is skipped; the first 6. */
export function picksOf(reply: string, ok: ReadonlySet<string>): Suggestion[] {
  const out: Suggestion[] = []
  for (const l of reply.split('\n')) {
    let o: { id?: unknown; why?: unknown } | null
    try { o = JSON.parse(l) } catch { continue }
    const id = o?.id
    if (typeof id === 'string' && ok.has(id) && !out.some(p => p.id === id)) out.push({ id, why: whyOf(o?.why) })
    if (out.length === 6) break
  }
  return out
}

/** The `handle:` directly inside the top-level `user:` block of a workspace config, or null; a handle under any other
 *  key is never read. */
export function userHandle(yml: string): string | null {
  let inUser = false
  for (const l of yml.split(/\r?\n/)) {
    if (/^\s*(#|$)/.test(l)) continue
    if (/^\S/.test(l)) inUser = /^user:\s*(#.*)?$/.test(l)
    else if (inUser) {
      const m = /^\s+handle:\s*(["']?)([^"'\n]*?)\1\s*(#.*)?$/.exec(l)
      if (m) return m[2]!.trim() || null
    }
  }
  return null
}

/** A brand's folder name: lowercase letters and digits only (`Maria G Fit` is `mariagfit`). */
export const brandSlug = (handle: string) => handle.toLowerCase().replace(/[^a-z0-9]/g, '')

/** This sid's call paths from the call record, newest first, at most 20: the paths alone, never a line's other fields. */
export function pathsFor(jsonl: string, sid: string): string[] {
  const out: string[] = []
  for (const l of jsonl.split('\n')) {
    try {
      const o = JSON.parse(l) as Rec
      if (o && o.sid === sid && Array.isArray(o.paths)) for (const p of o.paths) if (typeof p === 'string') out.push(p)
    } catch { /* not a whole line */ }
  }
  return out.slice(-20).reverse()
}

/** The system text: the reply's shape and the allowed ids with their names and prices. */
export function systemOf(choices: readonly { id: string; name: string; price: string }[]): string {
  return 'You suggest the next SocialCrawl research step for a person, from their brand, their recent requests and the calls ' +
    'they already made. Reply with 3 to 6 lines and nothing else, each one JSON object: {"id":"<an id from the list>","why":"<one ' +
    'short reason>"}. Use only ids from this list, copied exactly (id | name | price):\n' + choices.map(c => `${c.id} | ${c.name} | ${c.price}`).join('\n')
}

/** The request after the brand block: the recent prompts, oldest first, and this session's call paths, newest first. */
export function askOf(prompts: readonly string[], paths: readonly string[]): string {
  const list = (xs: readonly string[]) => (xs.length ? xs.map(x => `- ${x}`).join('\n') : '- none yet')
  return `The person's recent requests, oldest first:\n${list(prompts)}\n\nSocialCrawl calls made this session, newest first:\n${list(paths)}`
}

/** A completion's tokens: its four usage counts summed (a count that isn't a number is 0). */
export function usageOf(u: unknown): number {
  const o = (u && typeof u === 'object' ? u : {}) as Record<string, unknown>
  return ['input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'].reduce((n, k) => {
    const v = o[k]
    return n + (isNum(v) ? v : 0)
  }, 0)
}

export const NOT_OPENED = 'Press Suggested in the Endpoints tab to get suggestions.'
export const LOADING = 'Finding suggestions…'
export const NO_NEW = 'No new suggestions'
export const notRefreshed = (why: string) => `Couldn't refresh: ${shown(why)}`
export const tokensLine = (n: number) => `Suggestions used ${fmt(n)} tokens this session`

// ---- The Round-up tab (5d, D47). This session's calls and the last routine come from the call record (D58: the
// guard writes `routine` on every line); the saved files from the Bash command of a counted call; the total is the Budget pane's own. The
// credits are the guard's quotes (`worst`, G:483), never the charge. register.tsx reads; this file decides.

/** A call-record line with its `ts`, or null when it isn't a JSON object with a string sid. */
type Line = Rec & { sid: string; ts?: unknown }
function lineOf(l: string): Line | null {
  try {
    const o: unknown = JSON.parse(l)
    return o && typeof o === 'object' && typeof (o as Rec).sid === 'string' ? (o as Line) : null
  } catch {
    return null
  }
}

const pad = (n: number) => String(n).padStart(2, '0')
/** A record `ts` (UTC) as local `HH:MM`; `--:--` when it isn't a time. */
function hhmm(ts: unknown): string {
  const d = new Date(String(ts))
  return Number.isNaN(d.getTime()) ? '--:--' : `${pad(d.getHours())}:${pad(d.getMinutes())}`
}
/** A record `ts` as local `YYYY-MM-DD HH:MM`. */
const whenOf = (ts: unknown) => {
  const d = new Date(String(ts))
  return Number.isNaN(d.getTime()) ? 'an unknown time' : `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${hhmm(ts)}`
}
const counted = (r: Rec) => r.decision === 'pass' || r.decision === 'allow'

/** The record's text written since it was `size` bytes (R2-1): the bytes after `size` when the file grew, else all of
 *  it (no size known, or the file was cut or rotated). */
export function addedSince(text: string, size: number | null): string {
  const bytes = new TextEncoder().encode(text)
  return size !== null && size <= bytes.length ? new TextDecoder().decode(bytes.subarray(size)) : text
}

/** This sid's rows, newest first (a line that isn't whole is skipped): pass and allow as `HH:MM · <paths without
 *  /v1/> · up to <worst> cr`, one per command; deny as `HH:MM · <paths> · refused (<kind>)`, never counted. */
export function callRows(jsonl: string, sid: string): { paid: string[]; refused: string[] } {
  const out = { paid: [] as string[], refused: [] as string[] }
  for (const l of jsonl.split('\n').reverse()) {
    const r = lineOf(l)
    if (!r || r.sid !== sid) continue
    const head = `${hhmm(r.ts)} · ${(Array.isArray(r.paths) ? r.paths : []).filter((p): p is string => typeof p === 'string').map(p => p.replace(/^\/v1\//, '')).join(', ')}`
    if (counted(r)) out.paid.push(`${head} · up to ${String(r.worst)} cr`)
    else if (r.decision === 'deny') out.refused.push(`${head} · refused (${String(r.kind)})`)
  }
  return out
}

/** The last routine: the newest other sid with a line whose `routine` is true, which the guard writes on every line
 *  of a Desktop routine run (D58). When it ran, the committed of its newest counted line, and its refusals by kind.
 *  Null when there is none. */
export function lastRoutine(jsonl: string, sid: string): { from: unknown; to: unknown; spent: unknown; refused: [string, number][] } | null {
  const lines = jsonl.split('\n').map(lineOf).filter((r): r is Line => r !== null && r.sid !== sid)
  const routines = new Set(lines.filter(r => r.routine === true).map(r => r.sid))
  const newest = [...lines].reverse().find(r => routines.has(r.sid))
  if (!newest) return null
  const its = lines.filter(r => r.sid === newest.sid)
  const paid = its.filter(counted)
  const refused = new Map<string, number>()
  for (const r of its) if (r.decision === 'deny') refused.set(String(r.kind), (refused.get(String(r.kind)) ?? 0) + 1)
  return { from: its[0]!.ts, to: newest.ts, spent: paid.length ? paid[paid.length - 1]!.committed : 0, refused: [...refused] }
}

/** The last routine's lines as the pane draws them. */
export function routineLines(r: NonNullable<ReturnType<typeof lastRoutine>>): string[] {
  return [`Ran ${whenOf(r.from)} to ${whenOf(r.to)}`, `Spent: ${String(r.spent)} cr`,
    `Refused: ${r.refused.length ? r.refused.map(([k, n]) => `${n} ${k}`).join(', ') : 'none'}`]
}

/** A Bash command's output files: the word after `-o`, `>` or `>>`, quotes taken off; `2>…`, `&>…`, `>&…`, `-` and
 *  /dev/null are not files. Quotes are read, so a `>` inside one is text. An unbalanced quote gives none. */
export function outputsOf(cmd: string): string[] {
  const toks: { op?: string; w?: string }[] = []
  const OP = /\d*(?:>>|>&|>)|&>>?|&&|\|\||[;&|()<\n]/y
  let i = 0
  while (i < cmd.length) {
    const c = cmd[i]!
    if (c === ' ' || c === '\t') { i++; continue }
    if (c === '#') {   // a comment runs to the end of its line
      while (i < cmd.length && cmd[i] !== '\n') i++
      continue
    }
    OP.lastIndex = i
    const m = OP.exec(cmd)
    if (m) {
      toks.push({ op: m[0] })
      i += m[0].length
      continue
    }
    let w = ''
    while (i < cmd.length && !' \t\n;&|()<>'.includes(cmd[i]!)) {
      const q = cmd[i]!
      if (q === "'" || q === '"') {
        let e = i + 1
        while (e < cmd.length && cmd[e] !== q) e += q === '"' && cmd[e] === '\\' ? 2 : 1
        if (e >= cmd.length) return []
        w += cmd.slice(i + 1, e)
        i = e + 1
      } else w += cmd[i++]
    }
    toks.push({ w })
  }
  const out: string[] = []
  toks.forEach((t, k) => {
    const to = toks[k + 1]?.w
    if ((t.w === '-o' || t.op === '>' || t.op === '>>') && to && to !== '-' && to !== '/dev/null') out.push(to)
  })
  return [...new Set(out)]
}

/** Where a Bash path is for this machine: `/tmp/…` under TEMP (Git Bash's /tmp is %TEMP%, measured), `/c/…` as
 *  `C:/…`, `~/…` under the home; anything else as given. */
export function mapPath(p: string, temp: string | undefined, home: string | undefined): string {
  const fwd = (s: string) => s.replace(/\\/g, '/').replace(/\/+$/, '')
  let m = /^\/tmp(\/.*)?$/.exec(p)
  if (m && temp) return fwd(temp) + (m[1] ?? '')
  m = /^\/([a-zA-Z])(\/.*)?$/.exec(p)
  if (m) return `${m[1]!.toUpperCase()}:${m[2] ?? '/'}`
  m = /^~(\/.*)?$/.exec(p)
  if (m && home) return fwd(home) + (m[1] ?? '')
  return p
}

/** A path's file name, cut to 120 characters (a long one would fill the tree's text room and push Summarize out). */
export const nameOf = (p: string) => {
  const n = shown(p.split(/[\\/]/).filter(Boolean).pop() ?? p)
  return n.length > 120 ? `${n.slice(0, 119)}…` : n
}
/** A path with a drive or a leading slash; a relative one has no folder the mod knows (R2-6). */
export const isAbsolute = (p: string) => /^(?:[a-zA-Z]:)?[\\/]/.test(p)
/** A path as a `file:///` link. */
export const fileHref = (p: string) => `file:///${encodeURI(p.replace(/\\/g, '/').replace(/^\/+/, '')).replace(/[#?]/g, encodeURIComponent)}`

/** What Summarize may not carry (D47): the research suggester's wake word, intent phrases, URL shape (RS:63-72, as
 *  written there) and `@`; the guard's folder, its files and its save step; and (R2-2) control, line separator,
 *  format and bidi characters. */
export const UNSAFE = [/social[\s-]?crawl/i, /research/i, /\blook(?:ing|ed|s)?\s+into\b/i, /\bfind(?:ing|s)?\s+out\s+about\b/i,
  /(?:\bhttps?:\/\/[^\s<>"')]+)|(?:\bwww\.[a-z0-9][a-z0-9-]*\.[a-z]{2,})|(?:\b[a-z0-9][a-z0-9-]*\.[a-z]{2,}\/[^\s<>"')]*)/i,
  /@/, /revxl/i, /budget-?write/i, /credit-guard/i, /sessions\//i,
  /[\u0000-\u001f\u007f-\u009f\u2028\u2029\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]/]
/** A fact Summarize may carry: at most 300 characters, and nothing in UNSAFE, read as written and lowercased (as
 *  research-suggest reads a prompt, RS:290). */
export const safeFact = (s: string) => s.length <= 300 && !UNSAFE.some(re => re.test(s) || re.test(s.toLowerCase()))

/** Summarize's prompt: the pane's paid rows, saved files (each in double quotes) and total, and an ask for the Read
 *  tool only. A row or path that isn't a safeFact (or a path holding a `"`) is left out; at most 20 of each are listed;
 *  the rest are counted, so the text wakes no suggester and names no guard file. */
export function summaryOf(paid: readonly string[], files: readonly string[], spent: number, limit: number | null): string {
  const list = (xs: readonly string[], quote: boolean) => {
    const kept = xs.filter(x => safeFact(x) && !(quote && x.includes('"'))).slice(0, 20)
    const left = xs.length - kept.length
    return (kept.map(x => (quote ? `"${x}"` : x)).join('; ') || 'none') + (left ? ` (${left} more not listed here.)` : '.')
  }
  return 'Summarize what this session pulled, using only the facts below and the Read tool for the saved files. ' +
    `Make no new calls and run no commands. Calls: ${list(paid, false)} Saved files: ${list(files, true)} ` +
    `Total: ${fmt(spent)} of ${limit ? fmt(limit) : 'automatic cap'} credits (quotes, not charges).`
}

export const QUOTES_NOTE = "Credits are the guard's quotes; the real charge is in the debrief."
export const NO_ROUTINE = 'No routine run found.'

/** Text made safe to draw (display only): control, line separator, format and bidi characters become spaces. */
export const shown = (s: string) => s.replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]/g, ' ')

// ---- The Lantern look (5a-iii, D40: Look A, paper cards). Svg draws on the desktop surface only, and register.tsx
// draws a Text twin of each builder elsewhere. Hex lives in this section and nowhere else: Box and Text colours stay
// on theme keys (light theme untested). Every value in the markup is a number through fmt, or passes esc().

/** The Lantern palette. `lamp` is coral at 22% over `card`, mixed here: the demo's glow, with no transparency. */
const L = { card: '#111113', line: '#26262B', ink: '#F3F2EF', muted: '#8C8C93', acc: '#FF5A3C', good: '#62D69A', warn: '#F5B14C',
  lamp: '#45211C', font: "Geist, 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif" }
const TONE_FILL: Record<Tone, string> = { success: L.good, warning: L.warn, error: L.acc }

/** Text made safe for SVG markup: & < > ' and " as entities. */
export const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;').replace(/"/g, '&quot;')

const svg = (w: number, h: number, body: string, defs = '') =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${defs ? `<defs>${defs}</defs>` : ''}${body}</svg>`

/** An Svg's props: the markup and the same facts in words. */
export type Drawing = { source: string; alt: string }

/** The band's pill: a track, the spent part in the tone's colour and `<spent> / <limit> cr` in the centre; with no
 *  limit, an empty track and `<spent> cr · automatic cap`. */
export function bandPill(spent: number, limit: number | null, tone: Tone): Drawing {
  const w = 200
  const fill = limit ? `<rect x="4" y="4" width="${Math.max(8, Math.round((w - 8) * Math.min(1, spent / limit)))}" height="14" rx="7" fill="${TONE_FILL[tone]}"/>` : ''
  const label = limit ? `${fmt(spent)} / ${fmt(limit)} cr` : `${fmt(spent)} cr · automatic cap`
  return {
    source: svg(w, 22, `<rect x="1" y="1" width="${w - 2}" height="20" rx="10" fill="${L.card}" stroke="${L.line}"/>${fill}` +
      `<text x="${w / 2}" y="15" text-anchor="middle" font-family="${L.font}" font-size="11" font-weight="600" fill="${L.ink}">${esc(label)}</text>`),
    alt: limit ? `${fmt(spent)} of ${fmt(limit)} credits this session` : `${fmt(spent)} credits this session, automatic cap`,
  }
}

/** The Budget pane's hero card: THIS SESSION, `<spent> of <limit> cr` with the limit in coral (or `<spent> cr ·
 *  automatic cap`), `Total balance <n> cr · <age>` (or `Total balance unavailable`) and the coral lamp glow. */
export function hero(spent: number, limit: number | null, balance: number | null, age: string): Drawing {
  const glow = `<radialGradient id="lamp" cx="85%" cy="0%" r="70%"><stop offset="0" stop-color="${L.lamp}"/><stop offset="1" stop-color="${L.card}"/></radialGradient>`
  const head = limit
    ? `${fmt(spent)} <tspan fill="${L.muted}" font-size="18">of</tspan> <tspan font-weight="600" fill="${L.acc}">${fmt(limit)} cr</tspan>`
    : `${fmt(spent)} cr <tspan fill="${L.muted}" font-size="18">· automatic cap</tspan>`
  const bal = balance === null ? 'Total balance unavailable' : `Total balance ${fmt(balance)} cr · ${age}`
  return {
    source: svg(400, 112, `<rect x="1" y="1" width="398" height="110" rx="20" fill="url(#lamp)" stroke="${L.line}"/>` +
      `<text x="22" y="30" font-family="${L.font}" font-size="10" letter-spacing="2.2" fill="${L.muted}">THIS SESSION</text>` +
      `<text x="22" y="66" font-family="${L.font}" font-size="28" font-weight="300" letter-spacing="-0.5" fill="${L.ink}">${head}</text>` +
      `<text x="22" y="94" font-family="${L.font}" font-size="12" fill="${L.muted}">${esc(bal)}</text>`, glow),
    alt: `This session ${limit ? `${fmt(spent)} of ${fmt(limit)} credits` : `${fmt(spent)} credits, automatic cap`}. ` +
      `${balance === null ? 'Total balance unavailable' : `Total balance ${fmt(balance)} credits, ${age}`}.`,
  }
}
