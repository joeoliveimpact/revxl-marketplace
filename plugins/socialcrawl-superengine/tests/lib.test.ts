import { expect, test } from 'claude-code/testing'

import { ageOf, fmt, revxlOf, sidOf, spanOf } from '../hooks/mod/lib'
import { bandPill, hero, whyOf } from '../hooks/mod/lib'

// The pure rules beneath the status line and the paths (hooks/mod/lib.ts).
test('ageOf: just now, N min, N h up to 48 h, then days', () => {
  const MIN = 60_000
  const cases: [number, string][] = [[0, 'just now'], [59_999, 'just now'], [MIN, '1 min ago'], [59 * MIN, '59 min ago'],
    [60 * MIN, '1 h ago'], [47 * 60 * MIN + 59 * MIN, '47 h ago'], [48 * 60 * MIN, '2 days ago'], [10 * 24 * 60 * MIN, '10 days ago']]
  for (const [ms, text] of cases) expect(ageOf(ms), String(ms)).toBe(text)
})

test('spanOf: the stale warning span, with no "ago"', () => {
  expect([31 * 60_000, 3 * 3_600_000, 50 * 3_600_000].map(spanOf)).toEqual(['31 min', '3 h', '2 days'])
})

test('fmt: thousands commas', () => {
  expect([0, 999, 1000, 4210, 1234567, -1234, 1234.5].map(fmt)).toEqual(['0', '999', '1,000', '4,210', '1,234,567', '-1,234', '1,234.5'])
})

test('sidOf and revxlOf mirror the guard (G:318-320)', () => {
  expect(sidOf('a.b/c\\d e')).toBe('abcde')
  expect(sidOf(undefined)).toBe('nosession')
  expect(sidOf('')).toBe('nosession')
  expect(revxlOf('  /x  ', 'C:/h')).toBe('  /x  ')
  expect(revxlOf('   ', 'C:/h')).toBe('C:/h/.claude/revxl')
  expect(revxlOf(undefined, undefined)).toBeNull()
})

// 6a T2 (5c F-2): a reason's format and bidi characters are blanked too, as control and line-separator ones are.
test('T2 whyOf: zero-width, bidi override and isolate, BOM, BEL and U+2028 each become a space', () => {
  expect(whyOf('a\u200bb\u202ec\u2066d\ufeffe\u0007f\u2028g')).toBe('a b c d e f g')
})

// 6a T3 (K4): the hero alt writes every number with commas, as the balance already was.
test('T3 hero alt: 1,200 of 2,000 credits and a 4,210 balance', () => {
  expect(hero(1200, 2000, 4210, '2 min ago').alt).toBe('This session 1,200 of 2,000 credits. Total balance 4,210 credits, 2 min ago.')
})

// MK T5 (6a F-7, OQ8): the band pill alt writes its numbers with commas, as the hero alt does.
test('T5 bandPill alt: 1,200 of 2,000 credits this session', () => {
  expect(bandPill(1200, 2000, 'success').alt).toBe('1,200 of 2,000 credits this session')
})
