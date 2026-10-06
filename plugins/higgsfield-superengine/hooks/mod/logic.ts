// Pure helpers for the higgsfield-superengine spend mod: no engine calls, so claude plugin test can check them.

export const SUBMIT_RE = /hf_rest\.py["']?\s+submit\b/i
/** A command that uses Higgsfield (price, generate, fetch): it shows the band. */
export const USE_RE = /hf_rest\.py["']?\s+(estimate|submit|wait)\b/i

export type Job = { time: number; model: string; kind: 'video' | 'image'; cost: number
  status: 'running' | 'done' | 'refunded' | 'charged'; files: string[] }

/** The cap a cap-box answer means, or null for Not now / closed / anything that is not a sane dollar amount. */
export function capFromAnswer(a: string | undefined): number | null {
  const m = /^\s*\$?\s*(\d{1,4}(?:\.\d{1,2})?)\s*$/.exec(a ?? '')
  if (!m) return null
  const n = Number(m[1])
  return n > 0 && n <= 1000 ? n : null
}

export function meterColor(ratio: number): string {
  return ratio >= 0.9 ? '#ef4444' : ratio >= 0.7 ? '#f59e0b' : '#22c55e'
}

/** Share of the cap spent, 0..1; 0 when there is no usable cap (no NaN on the meter). */
export function ratioOf(spent: number, cap: number): number {
  return cap > 0 && spent > 0 ? Math.min(spent / cap, 1) : 0
}

/** Text made safe inside an SVG <text> element. */
export function esc(s: string): string {
  return s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' } as Record<string, string>)[c]!)
}

/** higgsfield/.python is run as argv[0] only if it is an absolute path to a python (or py) interpreter. */
export function pythonOk(p: string): boolean {
  return /^([A-Za-z]:[\\/]|\/|\\\\)/.test(p) && /^(python3?(\.\d+)?|py)(\.exe)?$/i.test(p.split(/[\\/]/).pop() ?? '')
}

/** Local YYYY-MM-DD log folders, oldest first: from the oldest entry's day to today, at most 7 days back. */
export function logDays(nowMs: number, entries: any[]): string[] {
  const now = new Date(nowMs), days: string[] = []
  const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const first = ymd(new Date(Math.min(nowMs, ...entries.map(e => Number(e?.created_at) * 1000).filter(Number.isFinite))))
  for (let back = 0; back <= 7; back++) {
    days.unshift(ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() - back)))   // calendar days: DST-safe
    if (days[0]! <= first) break
  }
  return days
}

/** Dot-matrix meter (Claude Code effort-slider look) as SVG elements: empty dots light grey, filled dots brighten
 *  toward a white handle at the fill point. */
export function dotGroup(x: number, y: number, w: number, h: number, ratio: number, color: string, handle = true): string {
  const cell = h >= 18 ? 4 : 3, dot = cell - 1
  const cols = Math.floor(w / cell), rows = Math.max(1, Math.floor(h / cell))
  const fill = Math.round(cols * Math.min(Math.max(ratio, 0), 1))
  let out = ''
  for (let c = 0; c < cols; c++) {
    for (let r = 0; r < rows; r++) {
      const jitter = 0.55 + 0.45 * (((c * 31 + r * 17) % 7) / 6)
      const cx = x + c * cell, cy = y + r * cell
      out += c < fill
        ? `<rect x="${cx}" y="${cy}" width="${dot}" height="${dot}" rx="${dot / 2}" fill="${color}" fill-opacity="${((0.25 + 0.75 * ((c + 1) / Math.max(fill, 1))) * jitter).toFixed(2)}"/>`
        : `<rect x="${cx}" y="${cy}" width="${dot}" height="${dot}" rx="${dot / 2}" fill="#a1a1aa" fill-opacity="${(0.32 * jitter).toFixed(2)}"/>`
    }
  }
  if (handle && fill > 0) {
    const hw = Math.max(cell * 2, 6), hx = Math.min(x + fill * cell - hw / 2, x + w - hw)
    out += `<rect x="${hx}" y="${y - 1}" width="${hw}" height="${rows * cell + 1}" rx="${hw / 2.4}" fill="#ffffff"/>`
  }
  return out
}

export function parseJson(stdout: string): any | null {
  for (const line of stdout.split(/\r?\n/).reverse()) {
    const t = line.trim()
    if (t.startsWith('{')) { try { return JSON.parse(t) } catch { /* keep looking */ } }
  }
  return null
}

const MODELS: [RegExp, string][] = [[/seedance/i, 'Seedance'], [/kling/i, 'Kling'], [/flare/i, 'Flare'],
  [/soul/i, 'Soul'], [/z-image/i, 'Z-Image'], [/hailuo|minimax/i, 'Hailuo'], [/wan/i, 'Wan'],
  [/genjutsu/i, 'Genjutsu'], [/ltx|lightricks/i, 'LTX'], [/grok/i, 'Grok'], [/qwen|alibaba/i, 'Qwen']]
const VIDEO = /video|seedance|kling|wan|hailuo|genjutsu|ltx|veo/i

export function modelOf(ep: string): string {
  return (MODELS.find(([re]) => re.test(ep)) ?? [null, ep.split('/').slice(-2).join(' ')])[1] as string
}

export function kindOf(ep: string): 'video' | 'image' {
  return VIDEO.test(ep) ? 'video' : 'image'
}

const STATUS: Record<string, Job['status']> = { pending: 'running', settled: 'done', refunded: 'refunded',
  assumed_charged: 'charged' }

/** One row per ledger entry of this session, joined with the workspace log by estimate key and request id. The same
 *  request run again has the same key: its entries pair with its submit lines in order (first entry <-> first submit). */
export function jobsFromLog(logLines: string[], entries: any[]): Job[] {
  const submits = new Map<string, any[]>(), files = new Map<string, string[]>(), taken = new Map<string, number>()
  for (const l of logLines) {
    let o: any
    try { o = JSON.parse(l) } catch { continue }
    if (o?.event === 'submit' && o.estimate_key) submits.set(o.estimate_key, [...(submits.get(o.estimate_key) ?? []), o])
    if (o?.event === 'download' && o.request_id && Array.isArray(o.files))
      files.set(o.request_id, o.files.map((f: any) => typeof f === 'string' ? f
        : (f && (f.result === 'saved' || f.result === 'exists') && typeof f.path === 'string') ? f.path : null)
        .filter(Boolean))
  }
  return [...entries].sort((a, b) => a.created_at - b.created_at).map(e => {
    const n = taken.get(e.id) ?? 0
    taken.set(e.id, n + 1)
    const s = submits.get(e.id)?.[n] ?? {}
    const ep = String(s.endpoint ?? '')
    return { time: e.created_at, model: ep ? modelOf(ep) : 'Higgsfield', kind: kindOf(ep),
             cost: e.state === 'pending' ? e.reserved : (e.actual ?? 0), status: STATUS[e.state] ?? 'running',
             files: (s.request_id && files.get(s.request_id)) || [] }
  }).sort((a, b) => b.time - a.time)
}

/** H:MM local time from epoch seconds (no Intl: its presence in the mod runtime is unproven). */
export function hhmm(t: number): string {
  const d = new Date(t * 1000)
  return `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

export type Step = { kind: 'pass' } | { kind: 'set'; usd: number } | { kind: 'refuse' }

/** What the mod does with a paid submit. It refuses only on the person's explicit Not now; a closed box, no
 *  window, junk, or an unreadable ledger all pass to the guard, whose 24 h rule (and ledger checks) decide. */
export function submitStep(status: any, err: string, answer: string | undefined): Step {
  if (err || !status || status.session_cap_set) return { kind: 'pass' }
  if (answer === 'Not now') return { kind: 'refuse' }
  const usd = capFromAnswer(answer)
  return usd === null ? { kind: 'pass' } : { kind: 'set', usd }
}
