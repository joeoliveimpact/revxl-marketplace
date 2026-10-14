// Pure helpers for the workspace-superengine mod: no engine calls, so claude plugin test can check them.

/** Oldest Claude Code this mod runs on. Mods ship on by default from 2.1.287 (the mods tutorial, 10.06.26), and
 *  every API the mod calls is in the 2.1.286 declarations already. Older: the plain hooks and skills (the floor). */
export const MIN_VERSION = '2.1.287'

/** True when version `v` (`2.1.295`, `2.1.295-dev`, `2.1.295-dev.2026...`) is at least `min`. Unreadable: false. */
export function versionAtLeast(v: string | undefined, min: string): boolean {
  const a = /^(\d+)\.(\d+)\.(\d+)/.exec(v ?? ''), b = /^(\d+)\.(\d+)\.(\d+)/.exec(min)
  if (!a || !b) return false
  for (let i = 1; i <= 3; i++) if (Number(a[i]) !== Number(b[i])) return Number(a[i]) > Number(b[i])
  return true
}

/** The band's buttons, in order (plan N5). `fill` goes into the prompt box and is never sent; no `fill` opens the pane. */
export const BUTTONS: readonly { key: string; label: string; hotkey: string; fill?: string }[] = [
  { key: 'wse-close', label: 'Close out', hotkey: 'c', fill: '/session-closeout' },
  { key: 'wse-continue', label: 'Continue', hotkey: 'e', fill: '/session-continue' },
  { key: 'wse-checkpoint', label: 'Checkpoint', hotkey: 'k', fill: 'checkpoint: save progress and keep going' },
  { key: 'wse-workspace', label: 'Workspace', hotkey: 'w' },
]

// ---- N6 heartbeat (Joe 10.14.26: the mod writes it directly, one $.fs.write; hooks/session-start prunes) ----
// Reader rule (Step 5): a heartbeat file that cannot be read or parsed, or lacks these fields, is "not confirmed",
// never "loaded".

const SID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/

/** <home>/.claude/revxl/heartbeat/workspace-superengine/<sid>.json, or null with no home or a session id that could
 *  leave the folder. */
export function heartbeatPath(home: string | undefined, sid: string): string | null {
  if (!home || !SID.test(sid)) return null
  return `${home.replace(/\\/g, '/').replace(/\/+$/, '')}/.claude/revxl/heartbeat/workspace-superengine/${sid}.json`
}

/** The v1 record, fields in the agreed order; `ts` is ISO 8601 UTC to the second. */
export function heartbeatRecord(version: unknown, sid: string, nowMs: number) {
  return { v: 1, plugin: 'workspace-superengine', version: typeof version === 'string' ? version : null,
    pane_command: '/workspace', session_id: sid, ts: new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, 'Z') }
}

// ---- Workspace pane: handoff.md per contract C (03-reader-slice-rollout.md) ----

export type Section = { found: boolean; items: string[] }
export type Handoff = { exists: boolean; p0: Section; blockers: Section; lastFound: boolean; lastDate: string | null }

const EMPTY = /^(\(none\)|_none yet_)$/i
const ITEM = /^(?:\d+\.|- \[[ xX]\]|-)\s+(.*)$/

/** A `## ` section: from the first heading `isIt` accepts to the next `## ` line. */
function section(lines: string[], isIt: (h: string) => boolean): { found: boolean; head: string; body: string[] } {
  const at = lines.findIndex(l => l.startsWith('## ') && isIt(l))
  if (at < 0) return { found: false, head: '', body: [] }
  const end = lines.findIndex((l, i) => i > at && l.startsWith('## '))
  return { found: true, head: lines[at]!, body: lines.slice(at + 1, end < 0 ? undefined : end) }
}

/** Top-level `N.`, `- ` and `- [ ]` lines; `(none)` and `_none yet_` count as nothing. */
function items(body: string[]): string[] {
  return body.map(l => ITEM.exec(l)?.[1]?.trim() ?? '').filter(t => t && !EMPTY.test(t))
}

/** handoff.md's text, or null when the file is not there. */
export function parseHandoff(text: string | null): Handoff {
  if (text === null) return { exists: false, p0: { found: false, items: [] }, blockers: { found: false, items: [] },
    lastFound: false, lastDate: null }
  const lines = text.split(/\r?\n/)
  const p0 = section(lines, h => h.startsWith('## P0'))
  const bl = section(lines, h => /^## Blockers\b/.test(h))
  const last = section(lines, h => /^## Last session\b/.test(h))
  return {
    exists: true,
    p0: { found: p0.found, items: items(p0.body) },
    blockers: { found: bl.found, items: items(bl.body) },
    lastFound: last.found,
    lastDate: last.found ? /\d{4}-\d{2}-\d{2}/.exec([last.head, ...last.body].join('\n'))?.[0] ?? null : null,
  }
}

/** The pane's lines for one section: its items numbered, or a sentence saying why there are none (never blank). */
export function sectionText(s: Section, heading: string): string {
  if (!s.found) return `handoff.md has no "${heading}" heading.`
  if (!s.items.length) return 'Nothing listed.'
  return s.items.map((t, i) => `${i + 1}. ${t}`).join('\n')
}

/** The pane's freshness line. */
export function lastText(h: Handoff): string {
  if (!h.lastFound) return 'handoff.md has no "## Last session" heading.'
  return h.lastDate ? `Last session: ${h.lastDate}` : 'Last session: no date in handoff.md.'
}
