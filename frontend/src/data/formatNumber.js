// alpha — shared number/currency formatting (pure, framework-free).
//
// Vue components should reach for `useFormat.js`, which binds these to the
// active locale. Keeping the formatters themselves free of Vue makes them
// directly unit-testable.
//
// Every figure in the app runs through here. Two rules drive the design:
//
// 1. Scale words are never hand-rolled. English "billion" is 10^9, but German
//    "Billion" is 10^12 (10^9 is a "Milliarde"), and Spanish has no short form
//    for 10^9 at all. A K/M/B/T suffix table would misreport a €1.5 Mrd. figure
//    as "1,5 Bio." — off by a factor of 1000 on a financial disclosure. CLDR,
//    via Intl's compact notation, gets every locale right; we delegate to it.
// 2. Compact notation only kicks in above COMPACT_FROM. Below its threshold
//    CLDR drops thousands grouping (German renders 1234 as "1234", not
//    "1.234"), and "45,7 Tsd." reads worse than "45.678" anyway.

export const COMPACT_FROM = 1e6
export const SQM_PER_HA = 10_000

const EMPTY = '—'

// Intl.NumberFormat construction is expensive and these run once per animation
// frame during the headline count-ups, so keep the instances around.
const cache = new Map()
function nf(locale, opts) {
  const key = locale + '|' + JSON.stringify(opts)
  let f = cache.get(key)
  if (!f) {
    f = new Intl.NumberFormat(locale, opts)
    cache.set(key, f)
  }
  return f
}

function num(n) {
  if (n == null) return null
  const v = Number(n)
  return Number.isFinite(v) ? v : null
}

// Currency style defaults minimumFractionDigits to 2; without pinning it to 0
// a maximumFractionDigits of 1 clamps the *minimum* down and yields "1234,0 $".
function money(currency, extra) {
  return {
    style: 'currency',
    currency: currency || 'USD',
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 0,
    ...extra,
  }
}

const COMPACT = { notation: 'compact', compactDisplay: 'short', maximumFractionDigits: 1 }

const NBSP = ' '

// Some CLDR data sets omit the separator between a compact scale word and the
// currency symbol. Chromium 141 formats 1.2e12 in es/BRL as "1,2 BR$": the "B"
// (billón, 10^12) fuses with "R$" and the whole thing reads as 1.2 reais rather
// than 1.2 trillion. Node's newer ICU emits "1,2 B R$". Rather than depend on
// whichever ICU the runtime shipped with, guarantee the gap ourselves.
//
// This only ever inserts whitespace — the scale words themselves still come
// from CLDR, so the Milliarde/Billion distinction stays out of our hands.
function needsGap(a, b) {
  return (
    (a === 'compact' && b === 'currency') || (a === 'currency' && b === 'compact')
  )
}

/** Concatenate Intl parts, keeping a scale word and a currency symbol apart. */
export function joinNumberParts(parts) {
  let out = ''
  for (let i = 0; i < parts.length; i++) {
    if (i > 0 && needsGap(parts[i - 1].type, parts[i].type)) out += NBSP
    out += parts[i].value
  }
  return out
}

// --- pure formatters --------------------------------------------------------
// All take an explicit { locale, currency } bag so they stay testable without a
// Vue component context.

/** Headline money: abbreviated once it gets long, fully grouped below that. */
export function formatMoney(n, { locale = 'en', currency = 'USD' } = {}) {
  const v = num(n)
  if (v == null) return EMPTY
  const compact = Math.abs(v) >= COMPACT_FROM
  const f = nf(locale, money(currency, compact ? COMPACT : { maximumFractionDigits: 0 }))
  return compact ? joinNumberParts(f.formatToParts(v)) : f.format(v)
}

/** Every digit, always. Feeds the tooltip/aria-label behind an abbreviated figure. */
export function formatMoneyFull(n, { locale = 'en', currency = 'USD' } = {}) {
  const v = num(n)
  if (v == null) return EMPTY
  return nf(locale, money(currency, { maximumFractionDigits: 0 })).format(v)
}

/**
 * Per-hectare money. Takes a *per-sqm* value — the API's unit — and scales it,
 * because per-sqm yields are sub-cent and unreadable as decimals.
 */
export function formatPerHa(nPerSqm, { locale = 'en', currency = 'USD' } = {}) {
  const v = num(nPerSqm)
  if (v == null) return EMPTY
  const perHa = v * SQM_PER_HA
  const digits = Math.abs(perHa) < 100 ? 2 : 0
  if (Math.abs(perHa) >= COMPACT_FROM) {
    return joinNumberParts(nf(locale, money(currency, COMPACT)).formatToParts(perHa))
  }
  return nf(
    locale,
    money(currency, { minimumFractionDigits: digits, maximumFractionDigits: digits }),
  ).format(perHa)
}

/** Plain grouped integer — counts, square metres, hectare tables. */
export function formatCount(n, { locale = 'en' } = {}) {
  const v = num(n)
  if (v == null) return EMPTY
  return nf(locale, { maximumFractionDigits: 0 }).format(v)
}

/** Hectares: abbreviated when huge, but never rounded to a meaningless "0 ha". */
export function formatHectares(n, { locale = 'en' } = {}) {
  const v = num(n)
  if (v == null) return EMPTY
  if (Math.abs(v) >= COMPACT_FROM) return nf(locale, { ...COMPACT }).format(v)
  const digits = Math.abs(v) < 100 ? 2 : 0
  return nf(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v)
}

/**
 * Grouped decimal for values that are neither money nor whole counts — FX
 * rates, extracted report figures. `maxDigits` caps the fraction; trailing
 * zeros are dropped so 5.4 stays "5,4" rather than "5,4000".
 */
export function formatDecimal(n, { locale = 'en', maxDigits = 4 } = {}) {
  const v = num(n)
  if (v == null) return EMPTY
  if (Math.abs(v) >= COMPACT_FROM) return nf(locale, { ...COMPACT }).format(v)
  return nf(locale, { maximumFractionDigits: maxDigits }).format(v)
}

/** Takes a 0..1 share. */
export function formatPercent(n, { locale = 'en' } = {}) {
  const v = num(n)
  if (v == null) return EMPTY
  return nf(locale, { style: 'percent', maximumFractionDigits: 0 }).format(v)
}

/**
 * Format `n` on the scale `target` settles at.
 *
 * The headline KPIs count up (see useCountUp), and formatting each frame on its
 * own merits would walk the suffix K → Mio. → Mrd. → Bio. and jump the string
 * width on every step. Locking the scale to the destination means only the
 * digits move. The divisor is recovered from the target's own formatted parts
 * rather than a 10**n table, so it stays right for Spanish, which skips 10^9.
 */
export function formatLikeTarget(n, target, opts = {}) {
  const v = num(n)
  const t = num(target)
  if (v == null) return EMPTY
  if (t == null || Math.abs(t) < COMPACT_FROM) return formatMoney(v, opts)

  const { locale = 'en', currency = 'USD' } = opts
  const f = nf(locale, money(currency, COMPACT))
  const parts = f.formatToParts(t)
  if (!parts.some((p) => p.type === 'compact')) return formatMoney(v, opts)

  // Reassemble the target's own output, swapping its digits for the scaled
  // frame value and leaving the literals, symbol and scale word untouched.
  const mantissa = mantissaOf(parts)
  if (mantissa === 0) return formatMoney(v, opts)
  const scaled = v / (t / mantissa)
  // Match the target's own precision — CLDR drops the fraction once the
  // mantissa reaches four digits ("1500 M"), and the final frame has to land on
  // exactly the string formatMoney would print for the same number.
  const places = parts.find((p) => p.type === 'fraction')?.value.length ?? 0
  const digits = nf(locale, {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  }).format(scaled)

  // Numeric parts (including any group separators between them) collapse into
  // the single re-scaled digit string; everything else — literals, scale word,
  // symbol — is carried over untouched.
  const NUMERIC = ['integer', 'decimal', 'fraction', 'group', 'minusSign']
  let injected = false
  const rebuilt = []
  for (const p of parts) {
    if (NUMERIC.includes(p.type)) {
      if (injected) continue
      injected = true
      rebuilt.push({ type: 'integer', value: digits })
    } else {
      rebuilt.push(p)
    }
  }
  return joinNumberParts(rebuilt)
}

// Rebuild the numeric value of a formatted number from its parts, so we learn
// what the compact form divided by without assuming which power it picked.
function mantissaOf(parts) {
  let s = ''
  for (const p of parts) {
    if (p.type === 'integer') s += p.value
    else if (p.type === 'decimal') s += '.'
    else if (p.type === 'fraction') s += p.value
    else if (p.type === 'minusSign') s += '-'
  }
  return Number(s) || 0
}
