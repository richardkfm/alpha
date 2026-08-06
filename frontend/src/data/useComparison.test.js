// The pure half of useComparison: how a multiple is written, and which anchor
// out of the backend's shortlist a given reader sees.
import { describe, it, expect } from 'vitest'
import { formatMultiple, pickAnchor } from './useComparison.js'

// Intl separates a number from "%" with a narrow no-break space (U+202F) in
// German and a regular NBSP elsewhere. Both are correct and both are invisible
// in a test literal, so normalise every flavour of whitespace for assertions.
const plainSpaces = (s) => (typeof s === 'string' ? s.replace(/\s/g, ' ') : s)

// Shortlist shaped like the one POST /api/v1/valuation returns.
const SHORTLIST = [
  { anchor: 'eu_annual_budget', multiple: 2.2, locales: ['de', 'es'] },
  { anchor: 'revenue_apple', multiple: 1.18, locales: [] },
  { anchor: 'gdp_uk', multiple: 0.9, locales: ['en'] },
]

describe('formatMultiple', () => {
  it('switches to a percentage below 1, where a decimal multiplier reads badly', () => {
    // "0,4x" makes the reader do the conversion; "40 %" does not.
    expect(plainSpaces(formatMultiple(0.4, 'de'))).toBe('40 %')
    expect(formatMultiple(0.4, 'en')).toBe('40%')
    expect(formatMultiple(0.999, 'en')).toBe('100%')
  })

  it('keeps one decimal under 10x and drops it above', () => {
    expect(formatMultiple(2.14, 'en')).toBe('2.1×')
    expect(formatMultiple(9.9, 'en')).toBe('9.9×')
    expect(formatMultiple(14.3, 'en')).toBe('14×')
    expect(formatMultiple(1, 'en')).toBe('1×')
  })

  it('follows the locale decimal separator', () => {
    // The whole point of the formatting work: 2,1 is German for 2.1.
    expect(formatMultiple(2.14, 'de')).toBe('2,1×')
    expect(formatMultiple(2.14, 'es')).toBe('2,1×')
  })

  it('returns null rather than a broken string for a missing multiple', () => {
    for (const bad of [null, undefined, NaN, Infinity]) {
      expect(formatMultiple(bad, 'en')).toBeNull()
    }
  })
})

describe('pickAnchor — locale preference', () => {
  it('prefers an anchor tagged for the reader over a better-fitting neutral one', () => {
    expect(pickAnchor(SHORTLIST, 'de').anchor).toBe('eu_annual_budget')
    expect(pickAnchor(SHORTLIST, 'en').anchor).toBe('gdp_uk')
  })

  it('falls back to the best-reading anchor, tagged for someone else or not', () => {
    // A tag marks an anchor as extra resonant for an audience, not as
    // off-limits to the rest. Skipping tagged entries here would hand a French
    // reader the untagged "1.18x Apple's annual revenue" over the crisper
    // "2.2x the EU's annual budget".
    expect(pickAnchor(SHORTLIST, 'fr').anchor).toBe('eu_annual_budget')
  })

  it('drops a local anchor that reads much worse than the best fit', () => {
    // 0.26x survives the window but is a poor comparison; 2.0x is not.
    const entries = [
      { anchor: 'marketcap_apple', multiple: 2.0, locales: [] },
      { anchor: 'gdp_austria', multiple: 0.26, locales: ['de'] },
    ]
    expect(pickAnchor(entries, 'de').anchor).toBe('marketcap_apple')
  })

  it('returns the best entry when every candidate is locale-tagged elsewhere', () => {
    const entries = [{ anchor: 'gdp_uk', multiple: 2.0, locales: ['en'] }]
    expect(pickAnchor(entries, 'de').anchor).toBe('gdp_uk')
  })

  it('has nothing to say about an empty or missing shortlist', () => {
    for (const bad of [[], null, undefined, 'nope']) {
      expect(pickAnchor(bad, 'en')).toBeNull()
    }
  })
})

describe('pickAnchor — exclusion', () => {
  // Regression: the standing asset and the conversion liability are both stocks
  // within a small factor of each other, sitting a few centimetres apart in the
  // panel. The backend excludes the anchor *it* would have picked, but once the
  // locale preference chooses differently that guard misses — in German both
  // figures came out as "Staatsschulden Deutschlands".
  it('skips an anchor a neighbouring figure already used', () => {
    expect(pickAnchor(SHORTLIST, 'de', { exclude: ['eu_annual_budget'] }).anchor).toBe(
      'revenue_apple',
    )
  })

  it('still honours locale preference among what is left', () => {
    const entries = [
      { anchor: 'marketcap_apple', multiple: 2.0, locales: [] }, // best fit overall
      { anchor: 'debt_germany', multiple: 2.6, locales: ['de'] },
      { anchor: 'gdp_austria', multiple: 1.5, locales: ['de'] },
    ]
    expect(pickAnchor(entries, 'de').anchor).toBe('debt_germany')
    // With that one taken, the reader gets the *other* German anchor, not the
    // untagged best fit.
    expect(pickAnchor(entries, 'de', { exclude: ['debt_germany'] }).anchor).toBe('gdp_austria')
  })

  it('says nothing rather than repeating when everything is taken', () => {
    const all = SHORTLIST.map((e) => e.anchor)
    expect(pickAnchor(SHORTLIST, 'de', { exclude: all })).toBeNull()
  })
})

describe('pickAnchor — rescaling', () => {
  // The discount-rate buttons recapitalise the standing asset client-side, so
  // its multiple has to move with it. At 1% the figure is 3x what the backend
  // ranked, and a comparison still quoting the 3% ratio would be wrong.
  it('scales every multiple by the factor', () => {
    const picked = pickAnchor(SHORTLIST, 'de', { factor: 3 })
    expect(picked.multiple).toBeCloseTo(6.6, 5)
  })

  it('re-ranks after scaling instead of trusting the original order', () => {
    const entries = [
      { anchor: 'a', multiple: 2.0, locales: [] }, // best at 1x, 20x after
      { anchor: 'b', multiple: 0.25, locales: [] }, // poor at 1x, 2.5x after
    ]
    expect(pickAnchor(entries, 'en', { factor: 1 }).anchor).toBe('a')
    expect(pickAnchor(entries, 'en', { factor: 10 }).anchor).toBe('b')
  })

  it('drops anchors that scaling pushes out of the readable window', () => {
    const entries = [{ anchor: 'a', multiple: 2.0, locales: [] }]
    expect(pickAnchor(entries, 'en', { factor: 100 })).toBeNull() // 200x
    expect(pickAnchor(entries, 'en', { factor: 0.01 })).toBeNull() // 0.02x
  })

  it('ignores a nonsensical factor rather than emitting a nonsensical multiple', () => {
    for (const bad of [0, -1, NaN, undefined]) {
      // undefined falls back to the 1 default; the rest are rejected.
      const got = pickAnchor(SHORTLIST, 'de', { factor: bad })
      if (bad === undefined) expect(got.multiple).toBeCloseTo(2.2, 5)
      else expect(got).toBeNull()
    }
  })
})
