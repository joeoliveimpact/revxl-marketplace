import { test, expect } from 'claude-code/testing'
import { SUBMIT_RE, USE_RE, capFromAnswer, meterColor, ratioOf, esc, pythonOk, logDays, dotGroup, parseJson, modelOf, kindOf,
  jobsFromLog, hhmm, submitStep, bandOnStart } from '../hooks/mod/logic'

test('cap box answers: buttons, typed amounts, and anything else is Not now', () => {
  expect(capFromAnswer('$5')).toBe(5)
  expect(capFromAnswer('$10')).toBe(10)
  expect(capFromAnswer('$20')).toBe(20)
  expect(capFromAnswer('15')).toBe(15)
  expect(capFromAnswer(' $12.50 ')).toBe(12.5)
  for (const bad of ['Not now', '', undefined, '$0', '1001', 'ten', '-5']) expect(capFromAnswer(bad)).toBe(null)
})

test('meter color: green, amber from 70%, red from 90%', () => {
  expect(meterColor(0.5)).toBe('#22c55e')
  expect(meterColor(0.7)).toBe('#f59e0b')
  expect(meterColor(0.9)).toBe('#ef4444')
})

test('submit detection', () => {
  expect(SUBMIT_RE.test('python "C:/p/scripts/hf_rest.py" submit z-image/turbo b.json')).toBe(true)
  expect(SUBMIT_RE.test('& (Get-Content -Raw higgsfield\\.python) "C:\\p\\scripts\\hf_rest.py" submit x b.json')).toBe(true)
  expect(SUBMIT_RE.test('python "C:/p/scripts/hf_rest.py" estimate x b.json')).toBe(false)
})

test('dot meter: filled dots, empty light-grey dots, one handle', () => {
  const s = dotGroup(0, 0, 30, 9, 0.5, '#22c55e')
  expect(s.includes('fill="#22c55e"')).toBe(true)
  expect(s.includes('fill="#a1a1aa"')).toBe(true)
  expect(s.split('fill="#ffffff"').length - 1).toBe(1)
  expect(dotGroup(0, 0, 30, 9, 0, '#22c55e').includes('fill="#ffffff"')).toBe(false)
})

test('parseJson takes the last JSON line', () => {
  expect(parseJson('noise\n{"ok":true,"n":1}\n')).toEqual({ ok: true, n: 1 })
  expect(parseJson('no json here')).toBe(null)
})

test('model and kind from the endpoint', () => {
  expect(modelOf('bytedance/seedance/v2.5/text-to-video')).toBe('Seedance')
  expect(kindOf('bytedance/seedance/v2.5/text-to-video')).toBe('video')
  expect(modelOf('marketing-studio/image/flare')).toBe('Flare')
  expect(kindOf('marketing-studio/image/flare')).toBe('image')
})

test('jobs: ledger entries joined with the log, newest first, statuses mapped', () => {
  const log = [
    JSON.stringify({ event: 'submit', endpoint: 'marketing-studio/image/flare', estimate_key: 'k1', request_id: 'r1' }),
    JSON.stringify({ event: 'download', request_id: 'r1', files: [
      { url: 'https://x/r1.png', path: 'higgsfield\\2026-10-06\\r1.png', result: 'saved' },
      { url: 'https://x/r1b.png', path: 'higgsfield\\2026-10-06\\r1b.png', result: 'failed' }] }),
    JSON.stringify({ event: 'submit', endpoint: 'bytedance/seedance/v2.5/text-to-video', estimate_key: 'k2', request_id: 'r2' }),
  ]
  const entries = [
    { id: 'k1', state: 'settled', reserved: 0.03, actual: 0.02, created_at: 100 },
    { id: 'k2', state: 'pending', reserved: 0.58, actual: null, created_at: 200 },
  ]
  const jobs = jobsFromLog(log, entries)
  expect(jobs.map(j => j.status)).toEqual(['running', 'done'])
  expect(jobs[1]).toEqual({ time: 100, model: 'Flare', kind: 'image', cost: 0.02, status: 'done',
                             files: ['higgsfield\\2026-10-06\\r1.png'] })
})

test('USE_RE: estimate/submit/wait show the band; check/models/setup do not', () => {
  for (const c of ['estimate', 'submit', 'wait']) expect(USE_RE.test(`python "C:/p/scripts/hf_rest.py" ${c} x`)).toBe(true)
  for (const c of ['check', 'models', 'setup']) expect(USE_RE.test(`python "C:/p/scripts/hf_rest.py" ${c}`)).toBe(false)
})

test('jobs: the same request run twice gets each run\'s own files (first entry <-> first submit)', () => {
  const log = [
    JSON.stringify({ event: 'submit', endpoint: 'marketing-studio/image/flare', estimate_key: 'k1', request_id: 'r1' }),
    JSON.stringify({ event: 'download', request_id: 'r1', files: [{ path: 'higgsfield\\d\\r1.png', result: 'saved' }] }),
    JSON.stringify({ event: 'submit', endpoint: 'marketing-studio/image/flare', estimate_key: 'k1', request_id: 'r2' }),
    JSON.stringify({ event: 'download', request_id: 'r2', files: [{ path: 'higgsfield\\d\\r2.png', result: 'saved' }] }),
  ]
  const entries = [
    { id: 'k1', state: 'settled', reserved: 0.03, actual: 0.02, created_at: 200 },
    { id: 'k1', state: 'settled', reserved: 0.03, actual: 0.02, created_at: 100 },
  ]
  expect(jobsFromLog(log, entries).map(j => [j.time, j.files])).toEqual([[200, ['higgsfield\\d\\r2.png']],
                                                                         [100, ['higgsfield\\d\\r1.png']]])
})

test('jobs: an entry refunded as not_sent takes no submit; the next run of the same key gets the files', () => {
  const log = [
    JSON.stringify({ event: 'submit', endpoint: 'marketing-studio/image/flare', estimate_key: 'K', request_id: 'r1' }),
    JSON.stringify({ event: 'download', request_id: 'r1', files: [{ path: 'higgsfield\\d\\r1.png', result: 'saved' }] }),
  ]
  const entries = [
    { id: 'K', state: 'refunded', reason: 'not_sent', reserved: 0.03, actual: 0, created_at: 100 },
    { id: 'K', state: 'settled', reason: 'actual', reserved: 0.03, actual: 0.02, created_at: 200 },
  ]
  expect(jobsFromLog(log, entries).map(j => [j.time, j.model, j.files])).toEqual([
    [200, 'Flare', ['higgsfield\\d\\r1.png']], [100, 'Higgsfield', []]])
})

test('logDays: oldest entry day to today, local dates, at most 7 days back', () => {
  const now = new Date(2026, 9, 6, 12).getTime(), at = (d: number) => new Date(2026, 9, d, 9).getTime() / 1000
  expect(logDays(now, [])).toEqual(['2026-10-06'])
  expect(logDays(now, [{ created_at: at(6) }, { created_at: at(4) }])).toEqual(['2026-10-04', '2026-10-05', '2026-10-06'])
  expect(logDays(now, [{ created_at: at(1) - 30 * 86400 }])).toEqual(['2026-09-29', '2026-09-30', '2026-10-01', '2026-10-02',
    '2026-10-03', '2026-10-04', '2026-10-05', '2026-10-06'])
})

test('esc: model names are safe inside SVG text', () => {
  expect(esc('A&B <x> "q"')).toBe('A&amp;B &lt;x&gt; &quot;q&quot;')
})

test('ratioOf: the meter share, 0 for no usable cap', () => {
  expect(ratioOf(2.5, 5)).toBe(0.5)
  expect(ratioOf(9, 5)).toBe(1)
  expect(ratioOf(1, 0)).toBe(0)
  expect(ratioOf(1, -5)).toBe(0)
  expect(Number.isNaN(ratioOf(0, 0))).toBe(false)
})

test('pythonOk: only an absolute path to python/py runs as the interpreter', () => {
  for (const p of ['C:\\Users\\j\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', 'C:/Py/py.exe',
                   '/opt/homebrew/bin/python3', '/usr/bin/python3.12']) expect(pythonOk(p)).toBe(true)
  for (const p of ['py', 'python', 'relative/python3', 'C:/x/evil.exe', '/bin/sh', 'C:/x/python.exe.bat', ''])
    expect(pythonOk(p)).toBe(false)
})

test('hhmm: local time as H:MM without Intl', () => {
  const d = new Date(2026, 9, 6, 9, 5)
  expect(hhmm(d.getTime() / 1000)).toBe('9:05')
})

test('submitStep: the mod refuses only on a Not now click; everything else is the guard\'s call', () => {
  const noCap = { ok: true, session_cap_set: false }, capped = { ok: true, session_cap_set: true }
  expect(submitStep(capped, '', undefined)).toEqual({ kind: 'pass' })                              // S1 cap already picked
  expect(submitStep(noCap, '', '$10')).toEqual({ kind: 'set', usd: 10 })                           // S2 a dollar pick
  expect(submitStep(noCap, '', 'Not now')).toEqual({ kind: 'refuse' })                             // S3 the explicit click
  for (const a of [undefined, '', 'ten', '$0']) expect(submitStep(noCap, '', a)).toEqual({ kind: 'pass' })  // S4 closed / junk
  expect(submitStep(null, 'the spend record gave no answer', '$5')).toEqual({ kind: 'pass' })      // S5 ledger unreadable
})

test('bandOnStart: a reopened chat shows the band only if it already picked a cap or spent', () => {
  expect(bandOnStart({ ok: true, session_cap_set: true, session_spent: 0 }, '')).toBe(true)        // B1 picked cap
  expect(bandOnStart({ ok: true, session_cap_set: false, session_spent: 0.08 }, '')).toBe(true)    // B2 spent, no pick
  expect(bandOnStart({ ok: true, session_cap_set: false, session_spent: 0 }, '')).toBe(false)      // B3 untouched chat
  expect(bandOnStart(null, 'Higgsfield setup is not finished in this folder')).toBe(false)          // B4 not a Higgsfield folder
  expect(bandOnStart({ ok: false, session_cap_set: true, session_spent: 1 }, 'bad')).toBe(false)   // B5 unreadable record
  expect(bandOnStart({ ok: true }, '')).toBe(false)                                                  // B6 fields missing
})
