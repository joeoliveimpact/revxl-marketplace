import { test, expect } from 'claude-code/testing'
import { SUBMIT_RE, capFromAnswer, meterColor, dotGroup, parseJson, modelOf, kindOf, jobsFromLog, hhmm, submitStep } from '../hooks/mod/logic'

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
