// The point of this suite is one specific class of bug: scale words.
//
// English "billion" is 10^9, but German "Billion" is 10^12 — 10^9 is a
// "Milliarde". Spanish "billón" is likewise 10^12, and Spanish has no short
// form for 10^9 at all. Hand-rolling a K/M/B/T table would silently report a
// €1.5 Mrd. figure as "1,5 Bio." — wrong by a factor of 1000, on a number
// presented as a financial disclosure. These tests pin the CLDR output that
// keeps us honest.
import { describe, it, expect } from 'vitest'
import * as F from './formatNumber.js'

export const { COMPACT_FROM, SQM_PER_HA } = F

// Intl separates an amount from its symbol with a non-breaking space (U+00A0),
// and that is correct — it stops "91,2 Bio." wrapping away from its "€". It
// just makes test literals unreadable, so normalise it for assertions only.
const plainSpaces = (s) => (typeof s === 'string' ? s.replace(/[  ]/g, ' ') : s)
const wrap =
  (fn) =>
  (...args) =>
    plainSpaces(fn(...args))

const formatMoney = wrap(F.formatMoney)
const formatMoneyFull = wrap(F.formatMoneyFull)
const formatPerHa = wrap(F.formatPerHa)
const formatCount = wrap(F.formatCount)
const formatHectares = wrap(F.formatHectares)
const formatDecimal = wrap(F.formatDecimal)
const formatPercent = wrap(F.formatPercent)
const formatLikeTarget = wrap(F.formatLikeTarget)

describe('non-breaking spaces', () => {
  it('are what Intl actually emits, so the UI keeps amount and symbol together', () => {
    expect(F.formatMoney(1.5e9, { locale: 'de', currency: 'EUR' })).toContain(' ')
  })
})

// A Node built with small-icu silently falls back to English for every locale,
// which would turn the German expectations below green but meaningless.
describe('ICU', () => {
  it('has full locale data (otherwise every de/es assertion is vacuous)', () => {
    expect(new Intl.NumberFormat('de').resolvedOptions().locale).toBe('de')
    expect(new Intl.NumberFormat('es').resolvedOptions().locale).toBe('es')
  })
})

describe('formatMoney — scale words per locale', () => {
  it('uses German Mrd. for 10^9 and Bio. for 10^12, never confusing the two', () => {
    const de = { locale: 'de', currency: 'EUR' }
    expect(formatMoney(1.5e9, de)).toBe('1,5 Mrd. €')
    expect(formatMoney(2.75e12, de)).toBe('2,8 Bio. €')
    expect(formatMoney(9.12e13, de)).toBe('91,2 Bio. €')
    // The regression that matters: 10^9 must not be labelled "Bio.".
    expect(formatMoney(1.5e9, de)).not.toContain('Bio.')
  })

  it('uses English B for 10^9 and T for 10^12', () => {
    const en = { locale: 'en', currency: 'USD' }
    expect(formatMoney(1.5e9, en)).toBe('$1.5B')
    expect(formatMoney(2.75e12, en)).toBe('$2.8T')
    expect(formatMoney(9.12e13, en)).toBe('$91.2T')
  })

  it('respects that Spanish has no short form for 10^9 and reads B as 10^12', () => {
    const es = { locale: 'es', currency: 'BRL' }
    expect(formatMoney(1.5e9, es)).toBe('1500 M R$')
    expect(formatMoney(2.75e12, es)).toBe('2,8 B R$')
  })
})

describe('formatMoney — symbol placement and separators', () => {
  it('prefixes in English and suffixes in German', () => {
    expect(formatMoney(45678, { locale: 'en', currency: 'USD' })).toBe('$45,678')
    expect(formatMoney(45678, { locale: 'de', currency: 'EUR' })).toBe('45.678 €')
  })

  it('keeps the symbol correct when locale and currency disagree', () => {
    // A German user viewing USD is a supported combination.
    expect(formatMoney(1.5e9, { locale: 'de', currency: 'USD' })).toBe('1,5 Mrd. $')
  })
})

describe('formatMoney — the compact threshold', () => {
  it('stays fully grouped below COMPACT_FROM', () => {
    expect(COMPACT_FROM).toBe(1e6)
    expect(formatMoney(999999, { locale: 'de', currency: 'EUR' })).toBe('999.999 €')
    expect(formatMoney(999999, { locale: 'en', currency: 'USD' })).toBe('$999,999')
  })

  it('does not drop thousands separators just under the threshold', () => {
    // CLDR's compact patterns omit grouping, so German would render 1234 as
    // "1234 €". Falling back to the full format below the threshold avoids it.
    expect(formatMoney(1234, { locale: 'de', currency: 'EUR' })).toBe('1.234 €')
  })

  it('never emits a stray ",0" from clamped fraction digits', () => {
    // Currency style defaults minimumFractionDigits to 2; without pinning it to
    // 0 the maximum of 1 clamps the minimum up and yields "1234,0 $".
    expect(formatMoney(1234, { locale: 'de', currency: 'USD' })).not.toContain(',0')
    expect(formatMoney(45678, { locale: 'de', currency: 'EUR' })).not.toContain(',0')
  })
})

describe('formatMoneyFull', () => {
  it('always spells out every digit, for tooltips behind an abbreviation', () => {
    expect(formatMoneyFull(9.12e13, { locale: 'de', currency: 'EUR' })).toBe(
      '91.200.000.000.000 €',
    )
    expect(formatMoneyFull(9.12e13, { locale: 'en', currency: 'USD' })).toBe(
      '$91,200,000,000,000',
    )
  })
})

describe('formatPerHa', () => {
  it('scales a per-sqm value by SQM_PER_HA so sub-cent figures become readable', () => {
    expect(SQM_PER_HA).toBe(10_000)
    // 0.4567 $/m²/yr is unreadable; 4,567 $/ha/yr is not.
    expect(formatPerHa(0.4567, { locale: 'en', currency: 'USD' })).toBe('$4,567')
    expect(formatPerHa(0.4567, { locale: 'de', currency: 'EUR' })).toBe('4.567 €')
  })

  it('keeps two decimals for values that would otherwise round away', () => {
    expect(formatPerHa(0.0042, { locale: 'de', currency: 'EUR' })).toBe('42,00 €')
  })
})

describe('formatHectares and formatCount', () => {
  it('abbreviates huge hectare figures but keeps decimals for small ones', () => {
    expect(formatHectares(5.5e8, { locale: 'de' })).toBe('550 Mio.')
    expect(formatHectares(42.5, { locale: 'de' })).toBe('42,50')
    expect(formatHectares(45678, { locale: 'de' })).toBe('45.678')
  })

  it('groups plain counts without a currency', () => {
    expect(formatCount(1234567, { locale: 'de' })).toBe('1.234.567')
    expect(formatCount(1234567, { locale: 'en' })).toBe('1,234,567')
  })
})

describe('formatDecimal and formatPercent', () => {
  it('drops trailing zeros on FX-style rates', () => {
    expect(formatDecimal(5.4, { locale: 'de' })).toBe('5,4')
    expect(formatDecimal(0.9231, { locale: 'en' })).toBe('0.9231')
  })

  it('renders a 0..1 share as a whole percentage', () => {
    expect(formatPercent(0.734, { locale: 'en' })).toBe('73%')
    expect(formatPercent(1, { locale: 'en' })).toBe('100%')
  })
})

describe('formatLikeTarget — count-up stability', () => {
  it('holds one scale word for the whole animation', () => {
    // Formatting each frame independently would walk the suffix
    // Tsd. → Mio. → Mrd. → Bio. and jump the string width on every step.
    const target = 9.12e13
    const opts = { locale: 'de', currency: 'EUR' }
    const frames = [0, 0.25, 0.5, 0.75, 1].map((p) => formatLikeTarget(target * p, target, opts))
    expect(frames).toEqual([
      '0,0 Bio. €',
      '22,8 Bio. €',
      '45,6 Bio. €',
      '68,4 Bio. €',
      '91,2 Bio. €',
    ])
    expect(frames.every((f) => f.endsWith('Bio. €'))).toBe(true)
  })

  it('settles on exactly what formatMoney would print', () => {
    for (const [locale, currency] of [
      ['en', 'USD'],
      ['de', 'EUR'],
      ['es', 'BRL'],
    ]) {
      for (const target of [2.75e12, 1.5e9, 4.2e6]) {
        const opts = { locale, currency }
        expect(formatLikeTarget(target, target, opts)).toBe(formatMoney(target, opts))
      }
    }
  })

  it('holds the Spanish 10^6 scale across a 10^9 target, which has no short form', () => {
    const target = 1.5e9
    const opts = { locale: 'es', currency: 'BRL' }
    // CLDR drops the fraction at a four-digit mantissa, so the frames follow
    // suit rather than ending on a "1500,0 M" that matches nothing else.
    expect(formatLikeTarget(target / 2, target, opts)).toBe('750 M R$')
    expect(formatLikeTarget(target, target, opts)).toBe('1500 M R$')
  })

  it('falls back to plain formatting below the compact threshold', () => {
    const opts = { locale: 'de', currency: 'EUR' }
    expect(formatLikeTarget(500, 999999, opts)).toBe(formatMoney(500, opts))
  })

  it('keeps the sign on negative targets', () => {
    const opts = { locale: 'de', currency: 'EUR' }
    expect(formatLikeTarget(-7.5e8, -1.5e9, opts)).toBe('-0,8 Mrd. €')
  })
})

describe('missing values', () => {
  it('renders an em dash rather than NaN or "null"', () => {
    for (const fn of [
      formatMoney,
      formatMoneyFull,
      formatPerHa,
      formatCount,
      formatHectares,
      formatDecimal,
      formatPercent,
    ]) {
      expect(fn(null, { locale: 'de', currency: 'EUR' })).toBe('—')
      expect(fn(undefined, { locale: 'de', currency: 'EUR' })).toBe('—')
      expect(fn(NaN, { locale: 'de', currency: 'EUR' })).toBe('—')
      expect(fn('not a number', { locale: 'de', currency: 'EUR' })).toBe('—')
    }
    expect(formatLikeTarget(null, 1e12, { locale: 'de', currency: 'EUR' })).toBe('—')
  })

  it('treats zero as a real value, not a missing one', () => {
    expect(formatMoney(0, { locale: 'de', currency: 'EUR' })).toBe('0 €')
    expect(formatCount(0, { locale: 'de' })).toBe('0')
  })
})
