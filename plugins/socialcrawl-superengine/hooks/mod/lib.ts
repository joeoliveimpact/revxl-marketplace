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
export type Rec = { sid?: unknown; paths?: unknown; worst?: unknown; committed?: unknown; decision?: unknown; kind?: unknown; limit?: unknown; balance?: unknown; routine?: unknown }

/** Call decisions written by credit-guard.mjs logCall: pass and deny; 706f39d and earlier wrote allow for counted calls. */
export const CALL_DECISIONS = ['pass', 'deny', 'allow'] as const

/** Only guard call lines count; settlement and future record kinds are passed over. */
export const isCall = (rec: Rec): boolean => CALL_DECISIONS.some(d => d === rec.decision)

/** This sid's newest call line: walks back from the end, skipping a line that doesn't parse (a partial last line). */
export function newestFor(jsonl: string, sid: string): Rec | null {
  const lines = jsonl.split('\n')
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const o: unknown = JSON.parse(lines[i] ?? '')
      if (o && typeof o === 'object' && (o as Rec).sid === sid && isCall(o as Rec)) return o as Rec
    } catch { /* not a whole line */ }
  }
  return null
}

/** This sid's newest valid ledger settlement, independent of the call readers. */
export function settleFor(jsonl: string, sid: string): { usage: number; committed: number; was: number } | null {
  const lines = jsonl.split('\n')
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const o = JSON.parse(lines[i] ?? '') as Record<string, unknown> | null
      if (o?.sid === sid && o.decision === 'settle' && o.kind === 'give-back' &&
        isNum(o.usage) && o.usage >= 0 && isNum(o.committed) && o.committed >= 0 && isNum(o.was) && o.was >= 0) {
        return { usage: o.usage, committed: o.committed, was: o.was }
      }
    } catch { /* not a whole line */ }
  }
  return null
}

/** Positive state Usage proves a ledger read even when the counted total did not change. */
export function usageFor(stateText: string | null, settle: ReturnType<typeof settleFor>): number | null {
  const usage = parseBudget(stateText).usage
  if (isNum(usage) && usage > 0) return usage
  return settle ? (isNum(usage) && usage >= 0 ? usage : settle.usage) : null
}

/** Calls still counted at their full hold, when the state records a whole nonnegative count. */
export function fullOf(stateText: string | null): number | null {
  const full = parseBudget(stateText).full
  return Number.isInteger(full) && (full as number) >= 0 ? full as number : null
}

export const usageWords = (usage: number | null): string => usage === null ? 'Usage: none read yet' : `Usage ${fmt(usage)} cr`
export const USAGE_LINE = (usage: number | null): string => usage === null ? 'Usage: none read yet' : `Usage: ${fmt(usage)} cr read from the ledger so far`

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
  const l = last && isCall(last) ? last.limit : null
  return Number.isInteger(l) && (l as number) >= 1 ? (l as number) : null
}

/** The guard's automatic cap: a quarter of a usable whole balance, up to 500; otherwise 500. */
export const autoOf = (balance: unknown): number => (typeof balance === 'number' && Number.isFinite(balance) && balance >= 0) ? Math.min(500, Math.floor(Math.floor(balance) / 4)) : 500

/** A saved budget wins; Automatic trusts a call's limit only when its own balance gives that cap. */
export function limitOf(budget: unknown, last: Rec | null): number | null {
  if (isBudget(budget)) return budget
  const limit = recordLimit(last)
  return limit === autoOf(last?.balance) ? limit : null
}

export type Tone = 'success' | 'warning' | 'error'
export type Band = { gauge: string; text: string; warn: string; tone: Tone }

/** The band's one row: a 10-cell gauge, this session's spending, and one spending warning. */
export function bandOf(spent: number, limit: number | null, last: Rec | null): Band {
  const filled = limit ? Math.min(10, Math.round((spent / limit) * 10)) : 0
  const gauge = '█'.repeat(filled) + '░'.repeat(10 - filled)
  const text = limit ? `${Math.max(0, limit - spent)} cr left of ${limit}` : `${spent} cr counted this session · automatic cap`
  if (last && isCall(last) && last.decision === 'deny') return { gauge, text, warn: ` · ⚠ last call refused: ${refusalShort(last.kind)}`, tone: 'error' }
  const left = limit ? limit - spent : 0
  if (limit && left > 0 && left <= Math.max(1, Math.floor(limit * 0.1))) return { gauge, text, warn: ` · ⚠ ${left} cr left`, tone: 'warning' }
  return { gauge, text, warn: '', tone: 'success' }
}

/** The toast for a counted call: `SocialCrawl: <paths> · counted <worst> cr · <committed> / <limit> cr this session`. */
export function toastOf(r: Rec): string {
  const paths = Array.isArray(r.paths) ? r.paths.join(', ') : ''
  const limit = r.limit === null || r.limit === undefined ? '' : ` / ${String(r.limit)}`
  return `SocialCrawl: ${paths} · counted ${String(r.worst)} cr · ${String(r.committed)}${limit} cr this session`
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
    if (over.length) warn = `your ${Math.max(...over)} cr limit is above it`
  }
  return `SC Total Balance: ${fmt(snap.balance)} cr (${age})${warn ? ` · ⚠ ${warn}` : ''}`
}

// ---- The Settings tab (5a-ii, M5: mobile keeps presets; other surfaces also draw Custom).

export const SESSION_PRESETS = [250, 500, 1000, 2000]
export const SESSION_HELP = "The most one session, or one run with no person at the prompt, may spend, as the guard counts it. Automatic = a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use."
export const GARBLED = "The settings file couldn't be read; saving will replace it."
export const READ_ERROR = "The settings file couldn't be read just now. Close and reopen this pane to try again."
export const READ_ERROR_LOCKED = "The limit and the transcript setting can't be changed here until it can be read."
export const NOTHING_TO_SAVE = 'Nothing to save: the file already holds this.'
export const PRESS_SET_FIRST = 'Press set beside the Custom box first, then Save.'
export const SAVING = 'Saving…'
export const PANE_FAILED = "SocialCrawl couldn't draw this pane. Close and reopen it."
export const SAVED = 'Saved. Every open session uses it from its next paid call.'
export const OWNER = 'socialcrawl-budget-pane'
export const CUSTOM_BAD = 'A custom limit is a whole number from 1 to 20,000.'
export const LOCK_HELP = "Paid transcripts cost far more than free captions. Blocked stops them before they run; Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling."
export const lockPreselected = (routes: string[]): string => `Not saved yet, so paid transcripts still run until you press Save. Blocked is picked for you because ${routes.some(r => r !== 'groq') ? 'a transcript tool was found on this computer' : 'a Groq key is set'}.`
export const LOCK_UNRECOGNISED = "The saved transcript setting is unrecognised, so transcripts are blocked. Save to fix it."
export const SAVE_BUSY = 'Settings are being saved in another window. Press Save again.'
export function routesFound(routes: string[]): string {
  const tools = routes.filter(r => r === 'yt-dlp' || r === 'whisper')
  const groq = routes.includes('groq')
  return tools.length ? `Found on this computer: ${tools.join(', ')}${groq ? '; a Groq key is set' : ''}` : groq ? 'A Groq key is set' : 'No free transcript tool found on this computer'
}

/** Custom accepts digits or grouped thousands, within G's budget range. */
export function customOf(text: string): number | null {
  const s = text.trim()
  const n = Number(s.replace(/,/g, ''))
  return /^(?:\d+|\d{1,3}(,\d{3})+)$/.test(s) && isBudget(n) ? n : null
}

export type Lock = 'block' | 'allow'

/** The transcript lock mirrors G's transcript-locked check, including a file that is not an object. */
export function storedLock(b: Record<string, unknown>, garbled: boolean): 'block' | 'allow' | 'unset' | 'unrecognised' | 'unreadable' {
  if (garbled) return 'unreadable'
  if (!Object.prototype.hasOwnProperty.call(b, 'transcripts')) return 'unset'
  if (b.transcripts === 'block') return 'block'
  return typeof b.transcripts === 'string' && /^allow$/.test(b.transcripts) ? 'allow' : 'unrecognised'
}

/** The helper's single routes line: known labels only, once each, in the helper's order. */
export function parseRoutes(exitCode: number, stdout: string): string[] | null {
  const line = stdout.trim()
  if (exitCode !== 0 || !line || line.includes('\n')) return null
  try {
    const o = JSON.parse(line) as { ok?: unknown; routes?: unknown }
    const routes = o.routes
    if (o.ok === true && Array.isArray(routes)) return ['yt-dlp', 'whisper', 'groq'].filter(x => routes.includes(x))
  } catch { /* not a routes answer */ }
  return null
}

/** A press wins; an unset lock preselects Blocked only when a free route was found. */
export function lockPick(pressed: Lock | undefined, stored: ReturnType<typeof storedLock>, routes: string[] | null): Lock {
  return pressed ?? (stored === 'allow' || (stored === 'unset' && !routes?.length) ? 'allow' : 'block')
}

/** Save fixes an unrecognised value or a route preselection; H supplies block for a fresh unreadable file. */
export function lockToSend(pressed: Lock | undefined, stored: ReturnType<typeof storedLock>, routes: string[] | null): Lock | undefined {
  const want = lockPick(pressed, stored, routes)
  return (pressed !== undefined && stored !== want) || (pressed === undefined && (stored === 'unrecognised' || (stored === 'unset' && !!routes?.length))) ? want : undefined
}

export const STYLES = ['Chips', 'Lantern rows', 'Cards'] as const
export type Style = (typeof STYLES)[number]
export const APPEARANCE_KEY = 'appearance'
export const APPEARANCE_HELP = 'How the Endpoints, Combos and Suggested buttons are drawn. Changes at once; no Save needed.'
export const styleOf = (v: unknown): Style => STYLES.find(x => x === v) ?? 'Lantern rows'

export const HOW_IT_WORKS: readonly { title: string; text: string }[] = [
  { title: 'The band', text: "The band above the prompt shows the credits left of your session limit, or the credits counted so far when no limit is known yet. Usage sits beside it once the guard has read some. The Open SocialCrawl button opens this pane." },
  { title: 'What the limit counts', text: "Before a call runs the guard holds its counted price against the session total, and a call the guard refuses holds nothing. Usage is what SocialCrawl's ledger shows charged on the endpoints this session called while those calls were open, so it can include other spending on the account." },
  { title: 'When credits come back', text: "No sooner than about two minutes after a call returns, and only once the ledger shows a charge on that endpoint this session, the guard can swap a finished call's hold for what was charged; until then the band can read high, a call with no charge there keeps its hold until one appears, and a ledger read can also push the total up. A call that fails, is interrupted, runs in the background, or is piped or chained keeps its hold and can count its hold and its charge together for the rest of the session; nothing comes back without a key, or after three failed ledger reads in a row. A charge the vendor records more than about 2 minutes after its call returns can be counted late, or not at all, so the band can also read low." },
  { title: 'Endpoints', text: 'Fill the Target box with the handle, link or search phrase the call needs, then press a call. Your priced pick goes into the chat as your own message.' },
  { title: 'Combos', text: 'Research packages of one or more calls. A press asks Claude to ask you for what it needs and to show the price before it runs.' },
  { title: 'Suggested', text: "A few picks based on your brand notes, your last few prompts and this session's calls. After you first open this tab it refreshes as the session goes on, and each refresh is one small model call that reads them." },
  { title: 'Round-up', text: "This session's calls and the files they saved. Summarize asks Claude to write up what was pulled and to make no new calls." },
  { title: 'Session credit limit', text: "The most a new call may take the session's total to: the holds still counted plus Usage. A call whose counted price would take the total past it is refused before it runs, and if a ledger read lifts the total past it, every call the guard counts above 0 is refused." },
  { title: 'Transcript endpoints', text: "Blocked refuses transcript calls before they run, and the guard refuses any call whose address is written in an odd encoding. Allowed lets them run and counts a single transcript at one unit's price, a floor, so one that bills many units is counted low; a batch is counted at its ceiling." },
  { title: 'Appearance', text: 'How the buttons on Endpoints, Combos and Suggested are drawn. It changes nothing about what they do or cost.' },
  { title: 'More options', text: "Each group's More options lists the rest of its platforms' calls, and More platforms lists every other site's calls. A press asks Claude to make that one call with what is in the Target box and to ask you for anything else it needs. Calls under \"Price depends on the request\" can't run from here, and neither can transcript calls while they're blocked." },
]

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
export function changesOf(p: Choice, saved: Choice, garbled: boolean, lock?: Lock): Record<string, unknown> | null {
  const sent: Record<string, unknown> = {}
  if (garbled || p.session !== saved.session) sent.sessionBudget = p.session
  if (lock !== undefined) sent.transcripts = lock
  return Object.keys(sent).length ? sent : null
}

/** The read-back: the file holds what was sent (sessionBudget gone for Automatic). */
export function holds(b: Record<string, unknown>, sent: Record<string, unknown>): boolean {
  return !('sessionBudget' in sent && (sent.sessionBudget === null ? 'sessionBudget' in b : b.sessionBudget !== sent.sessionBudget)) &&
    !('transcripts' in sent && b.transcripts !== sent.transcripts)
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
  invalid: 'the helper refused that choice. Pick again and press Save.',
  write: "the settings file couldn't be written. Press Save again.",
  readback: "the settings file didn't read back as chosen. Press Save again.",
  helper: "the save helper didn't give a usable answer. Press Save again.",
}
export const notSaved = (reason: string) => Object.prototype.hasOwnProperty.call(WHY, reason) ? `Not saved: ${WHY[reason]}` : 'Not saved. Press Save again.'
export const aboveBalance = (balance: number) => `⚠ This is above your ${fmt(balance)} cr balance.`
export const belowSpent = (spent: number) => `⚠ This session has already counted ${fmt(spent)} cr; a limit this low stops further counted calls in this session.`

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
export const TARGET_HINT = 'What goes here depends on the call: a handle, a link, a search phrase or a company name. A call that wants a region code reads this box as one and uses US when it is empty.'
export function needOf(kind: string, mobile: boolean): string {
  const what: Record<string, string> = { handle: 'a handle, like @name', channel: 'a channel link or handle', company: 'a company name or page id',
    ad: 'an ad link or ad id', urls: 'one or more post links', query: 'a search phrase', url: 'a link' }
  return `This call needs ${Object.prototype.hasOwnProperty.call(what, kind) ? what[kind] : 'a target'} in the Target box.${mobile ? ' Fill it on your computer first.' : ''}`
}
export const NO_PRICE = "This call has no listed price, so it can't be run from here."
export const NO_POST_STATS = "Post stats can't take that URL from here. Ask Claude in the chat."
export const BUSY = 'One click at a time: wait for the queued one.'

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

export const METERED = ' · varies'
export const TRANSCRIPT_LOCKED = "Transcript calls are blocked right now (see Settings), so this call can't run from here."
export const STARTS_CHARGES: readonly string[] = ['PATCH web/monitors/{monitor_id}']
export const DEPENDS_HELP = "Ask Claude for these; the pane can't price them, and the guard counts some of them at 0, so have Claude state the price first."
export const plural = (n: number, one: string, many = `${one}s`) => n === 1 ? one : many

const costObject = (v: unknown): Record<string, unknown> => v && typeof v === 'object' && !Array.isArray(v) ? v as Record<string, unknown> : {}

/** The displayed price covers options that can raise the guard's count; it varies exactly when the shown ends differ. */
export function rowPrice(costs: unknown, call: string): string | null {
  const r = rangeIn(costs, call)
  if (!r) return null
  const c = costObject(costs)
  const options = costObject(c._conditional)[call]
  const raised = Array.isArray(options) ? options.map(o => costObject(o).credits).filter(isNum) : []
  const span: [number, number] = [r[0], Math.max(r[1], ...raised)]
  return priceOf(span) + (span[0] !== span[1] ? METERED : '')
}

export const GROUP_PLATFORMS: Record<string, readonly string[]> = {
  Instagram: ['instagram'], TikTok: ['tiktok', 'tiktokshop'], YouTube: ['youtube'], LinkedIn: ['linkedin'],
  'Facebook ads': ['facebook'], Reddit: ['reddit'], Search: ['prism', 'search', 'tavily', 'perplexity', 'web'],
}
export type MoreRow = { call: string; platform: string; name: string; price: string | null; kind: 'priced' | 'free' | 'unpriced'; metered: boolean; transcript: boolean; key: string }

/** First-sentence names retain questions and the quickstart's opening words. */
export function callName(desc: unknown, platform: string): string {
  const full = typeof desc === 'string' ? desc : ''
  const first = full.split(/(?<=\?) |\. /)[0]!.replace(/\.$/, '')
  const own = platform.replace(/_/g, ' ').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const tidy = first.replace(/^(?:Get(?! started\b)|List|Fetch|Retrieve) /i, '')
    .replace(new RegExp(`^(?:(?:a|an|the) )?${own}(?:'s)?(?: +|$)`, 'i'), '')
  const name = tidy ? tidy[0]!.toUpperCase() + tidy.slice(1) : full
  return shown(name)
}

/** The transcript lock's path rule, including the guard's slash normalization for brief-check. */
export const isTranscriptRow = (path: string) => path.includes('transcript') || path.replace(/\/+/g, '/').replace(/^\/|\/$/g, '') === 'prism/brief-check'

/** Runtime order and verb-bearing keys preserve distinct GET/POST routes with the same path. */
export function moreOf(costs: unknown, platforms: readonly string[]): MoreRow[] {
  return Object.entries(costObject(costs)).flatMap(([call, entry]) => {
    if (call.startsWith('_') || !/^[A-Z]+ \S+$/.test(call) || ENDPOINTS.some(e => e.call === call)) return []
    const path = pathOf(call), platform = path.split('/')[0]!
    if (!platforms.includes(platform)) return []
    const r = rangeIn(costs, call), data = costObject(entry)
    const kind: MoreRow['kind'] = r === null || (r[0] === 0 && r[1] === 0 && STARTS_CHARGES.includes(call)) ? 'unpriced' : r[0] === 0 && r[1] === 0 ? 'free' : 'priced'
    return [{ call, platform, name: callName(data.desc, platform), kind,
      price: kind === 'unpriced' ? null : kind === 'free' ? 'free' : rowPrice(costs, call), metered: data.metered === true,
      transcript: isTranscriptRow(path), key: `more-${call.split(' ')[0]!.toLowerCase()}-${slugOf(call)}` }]
  })
}

export const SITES: Record<string, { name: string; line: string }> = {
  "aliexpress": {
    "name": "AliExpress",
    "line": "AliExpress product listings: look up products with prices, customer reviews, shipping fees and delivery times, hot products and promotions."
  },
  "amazon": {
    "name": "Amazon",
    "line": "Amazon products: look up a product's price and details, customer reviews, the sellers offering it, ranked category lists and current deals."
  },
  "app_store": {
    "name": "App Store",
    "line": "Apple's App Store: search apps, read an app's details and user reviews, and see the store's free, paid and grossing charts."
  },
  "apple_music": {
    "name": "Apple Music",
    "line": "Apple Music: search songs, albums and artists, look up an artist, album or track, and see a country's Apple Music charts."
  },
  "bluesky": {
    "name": "Bluesky",
    "line": "Bluesky profiles and posts: look up a user's profile and follower count, their posts, one post with its replies, or search posts by keyword."
  },
  "content_analysis": {
    "name": "Mention tracking",
    "line": "Mention tracking across the web: find news, blog, shop and forum pages that mention a keyword, with sentiment and mention volume over time."
  },
  "douyin": {
    "name": "Douyin",
    "line": "Douyin, short-form video in mainland China: search videos and creators, read video comments, and see the live hot-search board."
  },
  "ebay": {
    "name": "eBay",
    "line": "eBay listings: search listings by keyword and look up one listing's price, condition, units sold and seller."
  },
  "economy": {
    "name": "Economy",
    "line": "Spending data: household and travel spending by country, US federal spending and contract awards, and a US importer's suppliers."
  },
  "etsy": {
    "name": "Etsy",
    "line": "Etsy listings: look up a listing's price and details, the products in an Etsy shop, similar listings, and search suggestions."
  },
  "facebook": {
    "name": "Facebook",
    "line": "Facebook pages, groups and posts: look up page posts and comments, group posts, Marketplace listings, events, and ads in the Ad Library."
  },
  "finance": {
    "name": "Markets",
    "line": "Market data: look up quotes for stocks, ETFs, indices, currency and crypto pairs, plus price history, company financial statements and news."
  },
  "g2": {
    "name": "G2",
    "line": "G2 software listings: look up a software product, its written reviews, the products in a category, and the company that sells it."
  },
  "github": {
    "name": "GitHub",
    "line": "GitHub users and repositories: look up a profile, a repository's README, releases and issues, or search issues and pull requests."
  },
  "google": {
    "name": "Google",
    "line": "Google: web search results, local business profiles and their reviews, hotels, advertisers' ads, and keyword search volume by country."
  },
  "google_news": {
    "name": "Google News",
    "line": "Google News: see what is being reported about a topic, with each article's headline, outlet, link and publish time."
  },
  "google_play": {
    "name": "Google Play",
    "line": "Google Play's app store: search apps, read an app's details and user reviews, and see the store charts."
  },
  "google_shopping": {
    "name": "Google Shopping",
    "line": "Google Shopping: search products, see the sellers offering one and their prices, read reviews from several retailers, and see price history."
  },
  "google_trends": {
    "name": "Google Trends",
    "line": "Google Trends: see how search interest in keywords changes over time, related rising searches, and what a country is searching for now."
  },
  "gumtree": {
    "name": "Gumtree",
    "line": "Gumtree UK classified ads: search listings, look up an ad and its seller, and see the searches trending on Gumtree."
  },
  "hackernews": {
    "name": "Hacker News",
    "line": "Hacker News: search stories and comments, read a story's whole comment thread, and look up a user's profile."
  },
  "hm": {
    "name": "H&M",
    "line": "H&M products, stores and suppliers: search products with prices, colours and sizes, list stores in a country, and see a product's factories."
  },
  "home_depot": {
    "name": "Home Depot",
    "line": "Home Depot products: search items, look up price, stock and details, read customer reviews, and find stores near a US ZIP code."
  },
  "instagram": {
    "name": "Instagram",
    "line": "Instagram accounts and posts: look up profiles, posts and reels with likes and views, comments, followers, hashtags and trending reels."
  },
  "jobs": {
    "name": "Job listings",
    "line": "Job listings from LinkedIn, Indeed, Bing and Xing: search openings, look up one job, and see salary ranges for a job title and country."
  },
  "kick": {
    "name": "Kick",
    "line": "Kick clips: when you already have a clip's link, look up its title, views, length, category and channel."
  },
  "klarna": {
    "name": "Klarna",
    "line": "Klarna shopping: look up products, the prices different shops offer, user and expert reviews, price history and buying guides."
  },
  "kohls": {
    "name": "Kohl's",
    "line": "Kohl's products: search items with prices, read customer reviews and buyer questions, and find stores near a location."
  },
  "komi": {
    "name": "Komi",
    "line": "Komi bio-link pages: look up the links a creator lists on their Komi page, with titles, URLs and their bio."
  },
  "kwai": {
    "name": "Kwai",
    "line": "Kwai users and posts: look up a user's follower and like counts, their posts, and a post's video, views and music."
  },
  "linkbio": {
    "name": "Linkbio",
    "line": "Linkbio, a link-in-bio service: look up the links behind a creator's bio link, with titles and URLs."
  },
  "linkedin": {
    "name": "LinkedIn",
    "line": "LinkedIn members and companies: look up a person's profile and work history, company pages, posts and comments, jobs and ads."
  },
  "linkme": {
    "name": "Linkme",
    "line": "Linkme bio-link pages: look up the links a creator shows on their page, in the order they chose, with titles and URLs."
  },
  "linktree": {
    "name": "Linktree",
    "line": "Linktree pages: look up the links behind a creator's bio link, with titles and URLs, in the order the creator set them."
  },
  "naver": {
    "name": "Naver",
    "line": "Naver, Korean web search: look up its blogs, news, Q&A, community cafes, local places and Korean keyword search trends."
  },
  "on_page": {
    "name": "On-page SEO",
    "line": "On-page SEO audit: check one web page's title, meta tags, headings, HTTPS, broken links and page timing."
  },
  "perplexity": {
    "name": "Perplexity",
    "line": "Perplexity: ask a research question about the live web and get a written answer with the web pages it cited."
  },
  "pillar": {
    "name": "Pillar",
    "line": "Pillar bio-link pages: look up the links a creator lists on their Pillar page, with titles, URLs and their bio."
  },
  "pinterest": {
    "name": "Pinterest",
    "line": "Pinterest: search pins, look up a pin or a user's boards, see how often a link was saved, and see a country's Pinterest Trends."
  },
  "polymarket": {
    "name": "Polymarket",
    "line": "Polymarket prediction markets: see what people are willing to bet will happen on a topic, like whether a launch or a regulation lands."
  },
  "prism": {
    "name": "Prism (combined reports)",
    "line": "Combined reports that pull several sites into one answer, such as a brand's reputation, a product's reviews across stores, or a creator check."
  },
  "producthunt": {
    "name": "Product Hunt",
    "line": "Product Hunt's current launches: see the products it is featuring now, each with name, tagline, link and maker, narrowed by topic."
  },
  "quora": {
    "name": "Quora",
    "line": "Quora: search questions, answers, Spaces, topics and profiles by keyword."
  },
  "reddit": {
    "name": "Reddit",
    "line": "Reddit communities (subreddits): search posts and comments, read a post's full comment thread, find communities on a topic, and look up users."
  },
  "rumble": {
    "name": "Rumble",
    "line": "Rumble videos: search videos, list a channel's videos, and look up a video's views, likes and comments."
  },
  "search": {
    "name": "Social search",
    "line": "Social search: run one search across many sites at once, such as Reddit, YouTube, TikTok and Instagram, or search for creators and news."
  },
  "sephora": {
    "name": "Sephora",
    "line": "Sephora products: search items, look up price, ingredients and reviews, browse brands, and check stock at stores nearby."
  },
  "snapchat": {
    "name": "Snapchat",
    "line": "Snapchat profiles: check that a public account exists and see its display name, bio and subscriber count, plus comments on a Spotlight snap."
  },
  "spotify": {
    "name": "Spotify",
    "line": "Spotify music and podcasts: look up artists, tracks and albums, search playlists, and list a podcast's episodes."
  },
  "target": {
    "name": "Target",
    "line": "Target products: look up an item's price, rating and details, read customer reviews, browse categories, and find stores nearby."
  },
  "tavily": {
    "name": "Tavily",
    "line": "Tavily web search: search the web with an optional written answer, pull clean text from pages, and map or crawl a website."
  },
  "telegram": {
    "name": "Telegram",
    "line": "Telegram public channels and groups: look up a channel's profile and subscriber count, and its recent posts with views and reactions."
  },
  "threads": {
    "name": "Threads",
    "line": "Threads profiles and posts: look up a user's profile and recent posts, a post's replies, or search posts and users by keyword."
  },
  "tiktok": {
    "name": "TikTok",
    "line": "TikTok videos and accounts: look up profiles, videos with views and likes, comments, sounds, hashtags, trending videos and ads."
  },
  "tiktokshop": {
    "name": "TikTok Shop",
    "line": "TikTok Shop products: search products, read reviews, see a shop's products or a creator's showcase, and see units sold and estimated sales by market."
  },
  "tripadvisor": {
    "name": "TripAdvisor",
    "line": "Tripadvisor: search hotels, restaurants, attractions and cruises in a destination, and read traveler reviews of each."
  },
  "trustpilot": {
    "name": "Trustpilot",
    "line": "Trustpilot business reviews: find a company and read its customer reviews, which lean toward service, delivery, refund and support issues."
  },
  "truthsocial": {
    "name": "Truth Social",
    "line": "Truth Social profiles and posts: look up a user's profile and follower count, their recent posts, and one post's details."
  },
  "twitch": {
    "name": "Twitch",
    "line": "Twitch streamers: look up a streamer's profile, their videos and upcoming stream schedule, or one clip's details."
  },
  "twitter": {
    "name": "X (Twitter)",
    "line": "X (Twitter) accounts and posts: look up profiles, tweets and their replies, followers and communities, or search tweets and users."
  },
  "us_congress_trades": {
    "name": "US Congress trades",
    "line": "US Congress stock trades: see the trades members of Congress have disclosed, by politician, stock, party or state."
  },
  "utility": {
    "name": "Tools",
    "line": "Tools about the data service itself: list what can be looked up, find the right lookup for a task, identify a link, or explain a failed request."
  },
  "walmart": {
    "name": "Walmart",
    "line": "Walmart products: search items, look up price and details, read customer reviews, browse categories, and see every seller offering a product."
  },
  "wayfair": {
    "name": "Wayfair",
    "line": "Wayfair products: search items, look up price, stock, colour and size options and shipping estimate, and read customer reviews."
  },
  "web": {
    "name": "Web pages",
    "line": "Web pages: read a public page as clean content, search the web, list a site's pages, pull structured data from a page, or crawl a site."
  },
  "xiaohongshu": {
    "name": "Xiaohongshu (RedNote)",
    "line": "Xiaohongshu notes and creators: search notes, look up a creator and their notes, read note comments, and see the hot search board."
  },
  "yelp": {
    "name": "Yelp",
    "line": "Yelp businesses: search businesses by term and location, look up a business's rating and details, and read customer reviews."
  },
  "youtube": {
    "name": "YouTube",
    "line": "YouTube channels and videos: look up a channel, its videos and Shorts, a video's views, comments and transcript, and trending videos."
  }
}

const platformIds = (costs: unknown) => Object.keys(costObject(costObject(costs)._platforms))
export const siteName = (id: string) => SITES[id]?.name ?? id
export const otherPlatforms = (costs: unknown): string[] => platformIds(costs)
  .filter(p => !Object.values(GROUP_PLATFORMS).some(ps => ps.includes(p))).sort((a, b) => siteName(a).localeCompare(siteName(b)))
export const platformOptions = (costs: unknown) => [{ value: '', label: 'Choose a platform…' },
  ...otherPlatforms(costs).map(p => ({ value: p, label: `${siteName(p)} · ${moreOf(costs, [p]).length}` }))]

export const SITE_FAMILIES: Record<string, { name: string; ids: readonly string[] }> = {
  google: { name: 'Google (search, news, trends, shopping)', ids: ['google', 'google_news', 'google_trends', 'google_shopping'] },
  linktree: { name: 'Link-in-bio pages', ids: ['linktree', 'linkbio', 'linkme', 'komi', 'pillar'] },
}
export function siteOptions(costs: unknown) {
  const ids = platformIds(costs)
  const entries = ids.filter(p => !Object.values(SITE_FAMILIES).some(f => f.ids.includes(p))).map(p => ({ value: p, label: siteName(p) }))
  for (const [value, family] of Object.entries(SITE_FAMILIES)) if (family.ids.some(p => ids.includes(p))) entries.push({ value, label: family.name })
  return [{ value: '', label: 'Choose a site…' }, { value: '*', label: 'Full list' }, ...entries.sort((a, b) => a.label.localeCompare(b.label))]
}
export function sitesFor(value: string, costs: unknown): string[] {
  const ids = platformIds(costs)
  if (value === '*') return ids.sort((a, b) => siteName(a).localeCompare(siteName(b)))
  const family = SITE_FAMILIES[value]
  return family ? family.ids.filter(p => ids.includes(p)) : value && ids.includes(value) ? [value] : []
}

/** One prompt for both More lists; Claude reads the platform reference before building the call. */
export function moreText(row: MoreRow & { price: string }, target: string): string {
  const t = shown(target.trim()).replace(/"/g, "'")
  const file = row.key.replace(/[^a-z0-9-]/g, '')
  return `[SocialCrawl launcher] My pick from the Endpoints tab, priced ${row.price}: make exactly one SocialCrawl call to ${row.call}. ` +
    (t ? `The Target box holds "${t}".` : 'The Target box is empty.') +
    ` Read what this call needs in the socialcrawl skill's reference for that platform, ask me for anything missing, then use one plain curl in the Bash tool with the API key header from the socialcrawl skill, save the reply with -o /tmp/sc-${file}.json, then summarise it.`
}

/** URL-encoded, with ' as %27 too (the guard's plain URL holds no '). */
const enc = (s: string) => encodeURIComponent(s).replace(/'/g, '%27')

/** What a press asks for: the call's full URL (and post-stats' JSON body), or the note saying why nothing is sent. */
export function requestOf(e: Endpoint, target: string, mobile = false): { url: string; body?: string } | { note: string } {
  const t = target.trim()
  const missing = needOf(e.kind, mobile)
  const url = BASE + pathOf(e.call)
  const one = (param: string, v: string) => (v ? { url: `${url}?${param}=${enc(v)}` } : { note: missing })
  if (e.kind === 'none') return { url }
  if (e.kind === 'region') return one('region', t || 'US')
  if (!t) return { note: missing }
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

/** A brand's folder name: lowercase letters and digits only (`My Brand` is `mybrand`). */
export const brandSlug = (handle: string) => handle.toLowerCase().replace(/[^a-z0-9]/g, '')

/** This sid's call paths from the call record, newest first, at most 20: the paths alone, never a line's other fields. */
export function pathsFor(jsonl: string, sid: string): string[] {
  const out: string[] = []
  for (const l of jsonl.split('\n')) {
    try {
      const o = JSON.parse(l) as Rec
      if (o && isCall(o) && o.sid === sid && Array.isArray(o.paths)) for (const p of o.paths) if (typeof p === 'string') out.push(p)
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

export const LOADING = 'Finding suggestions…'
export const NO_NEW = 'No new suggestions'
export const notRefreshed = (why: string) => `Couldn't refresh: ${shown(why)}`
export const tokensLine = (n: number) => `Suggestions used ${fmt(n)} model tokens this session (not credits)`

// ---- The Round-up tab (5d, D47). This session's calls and the last routine come from the call record (D58: the
// guard writes `routine` on every line); the saved files from the Bash command of a counted call; the total is the Settings tab's own. The
// credits are the guard's quotes (`worst`, G:483), never the charge. register.tsx reads; this file decides.

/** A call-record line with its `ts`, or null when it isn't a JSON object with a string sid. */
type Line = Rec & { sid: string; ts?: unknown }
function lineOf(l: string): Line | null {
  try {
    const o: unknown = JSON.parse(l)
    return o && typeof o === 'object' && typeof (o as Rec).sid === 'string' && isCall(o as Rec) ? (o as Line) : null
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
const counted = (r: Rec) => isCall(r) && r.decision !== 'deny'

/** The record's text written since it was `size` bytes (R2-1): the bytes after `size` when the file grew, else all of
 *  it (no size known, or the file was cut or rotated). */
export function addedSince(text: string, size: number | null): string {
  const bytes = new TextEncoder().encode(text)
  return size !== null && size <= bytes.length ? new TextDecoder().decode(bytes.subarray(size)) : text
}

/** This sid's rows, newest first (a line that isn't whole is skipped): pass as `HH:MM · <paths without
 *  /v1/> · counted <worst> cr`, one per command; deny as `HH:MM · <paths> · refused: <reason>`, never counted. */
export function callRows(jsonl: string, sid: string): { paid: string[]; refused: string[] } {
  const out = { paid: [] as string[], refused: [] as string[] }
  for (const l of jsonl.split('\n').reverse()) {
    const r = lineOf(l)
    if (!r || r.sid !== sid) continue
    const head = `${hhmm(r.ts)} · ${(Array.isArray(r.paths) ? r.paths : []).filter((p): p is string => typeof p === 'string').map(p => p.replace(/^\/v1\//, '')).join(', ')}`
    if (counted(r)) out.paid.push(`${head} · counted ${String(r.worst)} cr`)
    else if (r.decision === 'deny') out.refused.push(`${head} · refused: ${refusalOf(r.kind)}`)
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
  return [`Ran ${whenOf(r.from)} to ${whenOf(r.to)}`, `Run total at its last call: ${String(r.spent)} cr (later changes to it are not shown)`,
    `Refused: ${r.refused.length ? r.refused.map(([k, n]) => `${n} ${refusalShort(k)}`).join(', ') : 'none'}`]
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
export function summaryOf(paid: readonly string[], files: readonly string[], spent: number, limit: number | null, usage: number | null): string {
  const list = (xs: readonly string[], quote: boolean) => {
    const kept = xs.filter(x => safeFact(x) && !(quote && x.includes('"'))).slice(0, 20)
    const left = xs.length - kept.length
    return (kept.map(x => (quote ? `"${x}"` : x)).join('; ') || 'none') + (left ? ` (${left} more not listed here.)` : '.')
  }
  return 'Summarize what this session pulled, using only the facts below and the Read tool for the saved files. ' +
    `Make no new calls and run no commands. Calls: ${list(paid, false)} Saved files: ${list(files, true)} ` +
    `Counted: ${fmt(spent)} of ${limit ? fmt(limit) : 'automatic cap'} credits. ${usage === null ? 'No Usage read yet.' : `Usage read from the ledger: ${fmt(usage)} ${plural(usage, 'credit')}.`}`
}

export const QUOTES_NOTE = "Each row shows what the guard counted before the call ran. Usage is what the guard has read back from SocialCrawl's ledger."
export const NO_ROUTINE = 'No routine run found.'

/** Text made safe to draw (display only): control, line separator, format and bidi characters become spaces. */
export const shown = (s: string) => s.replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]/g, ' ')

const REFUSALS: Record<string, [string, string]> = {
  'over-limit': ['over the limit', 'Raise the limit in Settings to go further (20,000 is the highest).'],
  'transcript-locked': ['transcripts blocked', 'Change this in Settings.'],
  'not-plain': ['not one plain call', 'Ask Claude to run it as one plain call.'],
  lost: ['session total lost', 'Start a new session to continue.'],
  error: ['guard could not read or save its files', "Try the call again; if it keeps happening, ask Claude to check the guard's session and settings files."],
}
export function refusalShort(kind: unknown): string {
  return typeof kind === 'string' && Object.prototype.hasOwnProperty.call(REFUSALS, kind) ? REFUSALS[kind]![0] : 'refused by the guard'
}
export function refusalOf(kind: unknown): string {
  const fix = typeof kind === 'string' && Object.prototype.hasOwnProperty.call(REFUSALS, kind) ? REFUSALS[kind]![1] : ''
  return `${refusalShort(kind)}.${fix ? ` ${fix}` : ''}`
}
export const balanceState = (fail: string | null): string => fail === null ? 'not checked yet' : fail === 'no-key' ? 'no usable SocialCrawl key found' : 'last check failed'

// ---- The Lantern look (M2). Svg draws on desktop; register.tsx draws the same facts as Text elsewhere.
// Hex lives only here; every value in markup is numeric or passes esc().

const L = { card: '#111113', card2: '#17171A', line: '#26262B', faint: '#34343A', ink: '#F3F2EF', muted: '#8C8C93', acc: '#FF5A3C', acc2: '#FF8A70',
  good: '#62D69A', warn: '#F5B14C', lamp: '#45211C', font: "Geist, 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif" }

function short(n: number): string {
  if (n < 1000) return String(n)
  const k = n / 1000
  return `${k >= 10 ? Math.round(k) : Math.round(k * 10) / 10}k`
}
export type Drawing = { source: string; alt: string }
export const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;').replace(/"/g, '&quot;')

const svg = (w: number, h: number, body: string, defs = '') =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${defs ? `<defs>${defs}</defs>` : ''}${body}</svg>`
const text = (x: number, y: number, size: number, fill: string, s: string, more = '') =>
  `<text x="${x}" y="${y}" font-family="${L.font}" font-size="${size}" fill="${fill}" ${more}>${s}</text>`
const eyebrowAt = (x: number, y: number, s: string, more = '') => text(x, y, 9, L.muted, esc(s), `letter-spacing="1.8" ${more}`)
const lamp = (id: string, cx: string, cy: string, base: string) =>
  `<radialGradient id="${id}" cx="${cx}" cy="${cy}" r="75%"><stop offset="0" stop-color="${L.lamp}"/><stop offset="1" stop-color="${base}"/></radialGradient>`

const share = (spent: number, limit: number | null) => limit === null ? 0 : Math.max(0, Math.min(1, spent / limit))
const arcFill = (tone: Tone) => tone === 'warning' ? L.warn : L.acc

/** The band's 270-degree dial: the spending share along the track, credits left inside. */
export function bandDial(spent: number, limit: number | null, tone: Tone, usage: number | null): Drawing & { width: number } {
  const left = limit === null ? null : Math.max(0, limit - spent)
  const of = limit === null ? 'automatic cap' : `of ${fmt(limit)} cr`
  const width = Math.round(48 + Math.max(of.length * 7.2, usageWords(usage).length * 6.2, 40) + 24)
  const c = 2 * Math.PI * 15, sweep = c * 0.75, lit = sweep * share(spent, limit)
  const ring = (stroke: string, len: number) =>
    `<circle cx="23" cy="23" r="15" fill="none" stroke="${stroke}" stroke-width="4" stroke-linecap="round" stroke-dasharray="${len.toFixed(2)} ${c.toFixed(2)}" transform="rotate(135 23 23)"/>`
  return {
    source: svg(width, 58, `<rect x="1" y="1" width="${width - 2}" height="56" rx="21" fill="url(#b)" stroke="${L.line}"/>` +
      ring(L.faint, sweep) + (lit > 0.5 ? ring(arcFill(tone), lit) : '') +
      text(23, 27, 11, L.ink, short(left === null ? spent : left), 'text-anchor="middle" font-weight="600"') +
      eyebrowAt(48, 17, limit === null ? 'COUNTED' : 'LEFT') + text(48, 33, 12, L.ink, esc(of), 'font-weight="500"') +
      text(48, 48, 10, L.muted, esc(usageWords(usage))), lamp('b', '8%', '50%', L.card)),
    alt: (limit === null ? `${fmt(spent)} ${plural(spent, 'credit')} counted this session, automatic cap` : `${fmt(left!)} of ${fmt(limit)} credits left this session`) + `; ${usageWords(usage)}`,
    width,
  }
}

/** Card 1: this session's spending, 48 lantern ticks and the credits left before the limit. */
export function sessionCard(spent: number, limit: number | null, tone: Tone): Drawing {
  const n = 48, x0 = 22, pitch = 356 / n, lit = Math.round(share(spent, limit) * n)
  const left = limit === null ? null : Math.max(0, limit - spent)
  let ticks = ''
  for (let i = 0; i < n; i++) {
    const on = i < lit, lead = on && i === lit - 1
    ticks += `<rect x="${(x0 + i * pitch).toFixed(1)}" y="${lead ? 76 : 79}" width="4.6" height="${lead ? 20 : 14}" rx="2.3" fill="${on ? (lead && tone !== 'warning' ? L.acc2 : arcFill(tone)) : L.faint}"/>`
  }
  const head = limit === null ? `${fmt(spent)} cr counted · automatic cap` : `${fmt(spent)} of ${fmt(limit)} cr counted`
  const headline = `${fmt(spent)}<tspan font-size="14" fill="${L.muted}" letter-spacing="0">${limit === null ? ' cr counted · automatic cap' : ` of <tspan fill="${L.ink}" font-weight="500">${fmt(limit)} cr</tspan> counted`}</tspan>`
  const foot = left === null ? "Automatic cap: a quarter of your account balance as the guard first read it this session, up to 500; 500 while the guard has no balance it can use" : `${fmt(left)} cr left before the limit`
  return {
    source: svg(400, 136, '<rect x="1" y="1" width="398" height="134" rx="20" fill="url(#h)" stroke="' + L.line + '"/>' +
      eyebrowAt(22, 28, 'THIS SESSION') + text(22, 62, 32, L.ink, headline, 'font-weight="300" letter-spacing="-0.6"') +
      (left === null ? '' : eyebrowAt(378, 28, 'LEFT', 'text-anchor="end"') + text(378, 54, 20, L.good, `${fmt(left)}<tspan font-size="12" fill="${L.muted}"> cr</tspan>`, 'text-anchor="end" font-weight="500"')) +
      ticks + text(22, 122, 11, L.muted, esc(foot)) + (limit === null ? '' : text(378, 122, 11, L.muted, `${Math.round(share(spent, limit) * 100)}%`, 'text-anchor="end"')), lamp('h', '88%', '0%', L.card)),
    alt: `This session: ${head}. ${foot}.`,
  }
}

/** Cards 2 and 3: ledger Usage and the latest account balance snapshot. */
export function detailCards(calls: number, refused: number, balance: number | null, age: string, unavailable: string, usage: number | null, full: number | null): Drawing {
  const tile = (x: number, bar: string) => `<rect x="${x}" y="1" width="194" height="112" rx="16" fill="${L.card2}" stroke="${L.line}"/><rect x="${x + 18}" y="1" width="28" height="3" rx="1.5" fill="${bar}"/>`
  const bal = balance === null ? 'unavailable' : `${fmt(balance)} cr`
  const used = usage === null ? 'none read yet' : `${fmt(usage)} cr`
  const count = `${calls} ${plural(calls, 'call')} · ${refused} refused on record`
  const still = full !== null && full > 0 ? `${full} still counted in full` : ''
  return {
    source: svg(400, 114, tile(1, L.good) + eyebrowAt(19, 26, 'USAGE') + text(19, 56, usage === null ? 16 : 24, L.good, esc(used), 'font-weight="300"') +
      text(19, 78, 10, L.muted, esc(count)) + (still ? text(19, 98, 10, L.muted, esc(still)) : '') + tile(205, L.acc) + eyebrowAt(223, 26, 'ACCOUNT BALANCE') +
      text(223, 56, balance === null ? 16 : 24, L.ink, esc(bal), 'font-weight="300"') + text(223, 78, 11, L.muted, esc(balance === null ? unavailable : `checked ${age}`))),
    alt: `Usage: ${used}. ${count}${still ? ` · ${still}` : ''}. Account balance: ${bal}${balance === null ? `, ${unavailable}` : `, checked ${age}`}.`,
  }
}

/** A section's heading: a coral dot and letter-spaced capitals. */
export function eyebrow(label: string): Drawing {
  return { source: svg(400, 16, `<circle cx="5" cy="8" r="3" fill="${L.acc}"/>` + text(16, 12, 10, L.ink, esc(label.toUpperCase()), 'letter-spacing="2.2" font-weight="600"')), alt: label }
}

/** The preview's route chip: the found labels, with the same accessible words on other surfaces. */
export function chip(words: string, found: boolean): Drawing {
  const w = Math.min(400, Math.round(words.length * 6.3) + 34)
  return {
    source: svg(w, 22, `<rect x="1" y="1" width="${w - 2}" height="20" rx="10" fill="${L.card2}" stroke="${L.line}"/><circle cx="12" cy="11" r="3.5" fill="${found ? L.good : L.muted}"/>` +
      text(22, 15, 11, found ? L.ink : L.muted, esc(words))),
    alt: words,
  }
}

/** One endpoint as a Lantern row: its name (wrapped onto up to four lines when long, so every row is the same
 *  shape), and its price in a coral-edged pill at the right. */
export function rowCard(name: string, price: string): Drawing & { width: number } {
  const w = 300, pw = price ? Math.round(price.length * 6.4) + 18 : 0
  const max = Math.max(12, Math.floor((w - 14 - pw - 16) / 6.5))
  const lines: string[] = []
  for (const word of name.split(' ')) {
    const last = lines[lines.length - 1]
    if (last !== undefined && `${last} ${word}`.length <= max) lines[lines.length - 1] = `${last} ${word}`
    else lines.push(word)
  }
  const shown = lines.length > 4 ? [...lines.slice(0, 3), `${lines[3]}…`] : lines
  const h = 28 + 15 * (shown.length - 1), mid = h / 2
  return {
    source: svg(w, h, `<rect x="1" y="1" width="${w - 2}" height="${h - 2}" rx="13" fill="${L.card2}" stroke="${L.line}"/>` +
      shown.map((l, i) => text(14, 18 + 15 * i, 12, L.ink, esc(l), 'font-weight="500"')).join('') +
      (price ? `<rect x="${w - pw - 6}" y="${mid - 9}" width="${pw}" height="18" rx="9" fill="${L.card}" stroke="${L.acc}"/>` +
      text(w - 6 - pw / 2, mid + 4, 10.5, L.acc2, esc(price), 'text-anchor="middle" font-weight="600"') : '')),
    alt: price ? `${name}, ${price}` : name,
    width: w,
  }
}
