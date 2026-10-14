import { test, expect } from 'claude-code/testing'
import { BUTTONS, MIN_VERSION, heartbeatPath, heartbeatRecord, lastText, parseHandoff, sectionText,
  versionAtLeast } from '../hooks/mod/logic'

test('version check: 2.1.287 and later run the mod, older or unreadable fall back to the floor', () => {
  expect(MIN_VERSION).toBe('2.1.287')
  for (const v of ['2.1.287', '2.1.295', '2.1.295-dev', '2.1.300-dev.20261014.t1.sha1', '2.2.0', '3.0.0'])
    expect(versionAtLeast(v, MIN_VERSION)).toBe(true)
  for (const v of ['2.1.286', '2.0.999', '1.9.9', '', undefined, 'dev', '2.1'])
    expect(versionAtLeast(v, MIN_VERSION)).toBe(false)
})

test('band buttons: c Close out, e Continue, k Checkpoint, w Workspace, in that order; no m yet', () => {
  expect(BUTTONS.map(b => b.hotkey)).toEqual(['c', 'e', 'k', 'w'])
  expect(BUTTONS.map(b => b.label)).toEqual(['Close out', 'Continue', 'Checkpoint', 'Workspace'])
  expect(BUTTONS.map(b => b.fill)).toEqual(['/session-closeout', '/session-continue',
    'checkpoint: save progress and keep going', undefined])
  for (const b of BUTTONS) expect(b.key.startsWith('wse-')).toBe(true)
  // Fewzhun's letters (f a s h g) stay free
  for (const b of BUTTONS) expect('fashg'.includes(b.hotkey)).toBe(false)
})

test('heartbeat path: <home>/.claude/revxl/heartbeat/workspace-superengine/<sid>.json; unsafe ids refused', () => {
  const tail = '/.claude/revxl/heartbeat/workspace-superengine/'
  expect(heartbeatPath('C:\\Users\\joe', 'cdd3c1cf-955d-4c5a-95df-df887d026dfe'))
    .toBe('C:/Users/joe' + tail + 'cdd3c1cf-955d-4c5a-95df-df887d026dfe.json')
  expect(heartbeatPath('/Users/joe/', 'abc')).toBe('/Users/joe' + tail + 'abc.json')
  for (const bad of ['', '../x', 'a/b', 'a\\b', '.hidden', 'x'.repeat(129)]) expect(heartbeatPath('C:\\Users\\joe', bad)).toBe(null)
  expect(heartbeatPath(undefined, 'abc')).toBe(null)
  expect(heartbeatPath('', 'abc')).toBe(null)
})

test('heartbeat record: the v1 object, fields in order, ts ISO UTC to the second', () => {
  const r = heartbeatRecord('0.15.3', 'sid-1', Date.UTC(2026, 9, 14, 12, 51, 47, 123))
  expect(Object.keys(r)).toEqual(['v', 'plugin', 'version', 'pane_command', 'session_id', 'ts'])
  expect(r).toEqual({ v: 1, plugin: 'workspace-superengine', version: '0.15.3', pane_command: '/workspace',
    session_id: 'sid-1', ts: '2026-10-14T12:51:47Z' })
  expect(heartbeatRecord(undefined, 'sid-1', 0).version).toBe(null)   // plugin.json unreadable
})

const REAL = ['# handoff.md', '', '## Last session', '2026-10-13 \u2014 shipped 0.15.3', '', '## Blockers',
  '1. Joe\'s review of the plan.', '', '## P0 \u2014 Next Actions', '1. **Adjust the plan**, then build.',
  '   - a sub-bullet is not an item', '2. Draft the Fewzhun note.', '', '## P1 \u2014 Deferred', '1. later'].join('\r\n')
const TEMPLATE = ['# handoff.md', '', '## P0 (do first)', '', '- [ ] Read `CLAUDE.md`.', '- [ ] Add a project row.', '',
  '## P1 (do soon)', '- [ ] not P0', '', '## Blockers', '', '- _none yet_', '', '## Notes for next session'].join('\n')

test('handoff (contract C): the shape closeout writes, CRLF, P0 with a dash heading', () => {
  const h = parseHandoff(REAL)
  expect(h.exists).toBe(true)
  expect(h.p0).toEqual({ found: true, items: ['**Adjust the plan**, then build.', 'Draft the Fewzhun note.'] })
  expect(h.blockers).toEqual({ found: true, items: ['Joe\'s review of the plan.'] })
  expect(h.lastDate).toBe('2026-10-13')
  expect(lastText(h)).toBe('Last session: 2026-10-13')
  expect(sectionText(h.p0, '## P0')).toBe('1. **Adjust the plan**, then build.\n2. Draft the Fewzhun note.')
})

test('handoff: the super-setup template (P0 (do first), - [ ] items, _none yet_ blockers, no Last session)', () => {
  const h = parseHandoff(TEMPLATE)
  expect(h.p0.items).toEqual(['Read `CLAUDE.md`.', 'Add a project row.'])
  expect(h.blockers).toEqual({ found: true, items: [] })
  expect(sectionText(h.blockers, '## Blockers')).toBe('Nothing listed.')
  expect(lastText(h)).toBe('handoff.md has no "## Last session" heading.')
})

test('handoff fallbacks: no file, missing headings, (none), undated Last session; never blank', () => {
  const none = parseHandoff(null)
  expect(none.exists).toBe(false)
  const bare = parseHandoff('# handoff\n\nsome text\n')
  expect(bare.exists).toBe(true)
  expect(sectionText(bare.p0, '## P0')).toBe('handoff.md has no "## P0" heading.')
  expect(sectionText(bare.blockers, '## Blockers')).toBe('handoff.md has no "## Blockers" heading.')
  const undated = parseHandoff('## Last session\nyesterday\n## Blockers\n- (none)\n')
  expect(lastText(undated)).toBe('Last session: no date in handoff.md.')
  expect(undated.blockers.items).toEqual([])
  // a heading that only starts like Blockers is not it
  expect(parseHandoff('## Blockersmith\n- x\n').blockers.found).toBe(false)
})
