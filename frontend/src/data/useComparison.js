// alpha — renders the backend's comparison shortlists as a human-scale phrase.
//
// The valuation returns, per headline figure, up to three anchors that make its
// magnitude graspable: `[{ anchor, multiple, locales }, ...]`, best-reading
// first. It cannot pick just one, because the anchor a reader relates to
// depends on their language and `POST /api/v1/valuation` takes no locale —
// threading one through would mean re-fetching the whole valuation on every
// language switch. So the backend does the arithmetic, and this does the
// language.
import { useI18n } from 'vue-i18n'
import { formatDecimal, formatPercent } from './formatNumber.js'

/**
 * Format the multiple itself.
 *
 * Under 1 a percentage reads better than a decimal multiplier — "40 %" lands
 * where "0,4×" makes the reader do the conversion. Above it, one decimal place
 * up to 10 and none beyond: "2,1×" is informative, "14,3×" is false precision
 * on a figure already flying an "≈".
 */
export function formatMultiple(multiple, locale = 'en') {
  if (multiple == null || !Number.isFinite(multiple)) return null
  if (multiple < 1) return formatPercent(multiple, { locale })
  const digits = multiple < 10 ? 1 : 0
  return `${formatDecimal(multiple, { locale, maxDigits: digits })}×`
}

// Mirrors scale_anchors.py. Kept in sync by hand because the frontend has to
// re-rank locally: the discount-rate buttons rescale the standing-asset figure
// without a round-trip, which moves every multiple with it.
const MIN_MULTIPLE = 0.25
const MAX_MULTIPLE = 50
const TARGET_MULTIPLE = 2
// How much worse a locale-matching anchor may read before the better-fitting
// universal one wins. ~0.5 decades, so Austria's GDP beats Apple's revenue on
// familiarity but not when it is three times further from a graspable ratio.
const LOCALE_SCORE_SLACK = 0.5

const score = (m) => Math.abs(Math.log10(m) - Math.log10(TARGET_MULTIPLE))

/**
 * Choose the anchor for `locale` from a shortlist.
 *
 * `factor` rescales every multiple, for figures the UI recomputes after the
 * backend ranked them — the standing-asset value triples when the reader picks
 * a 1% discount rate, and a comparison still quoting the 3% ratio would simply
 * be wrong. Rescaling can push an anchor out of the readable window or reorder
 * which reads best, so this re-filters and re-ranks rather than trusting the
 * backend's order.
 *
 * `exclude` drops anchors a neighbouring figure already used. The backend does
 * this too, but only for the choice *it* would have made — once the locale
 * preference below picks differently, two adjacent stock figures can converge
 * on the same anchor again. In German both landed on "Staatsschulden
 * Deutschlands" before this existed.
 *
 * Locale-tagged anchors win — a German reader gets Austria's GDP rather than
 * the UK's — unless the fit is markedly worse. Failing that, an untagged
 * (universal) one, then the best-reading entry regardless.
 */
export function pickAnchor(entries, locale = 'en', { factor = 1, exclude = [] } = {}) {
  if (!Array.isArray(entries) || !entries.length) return null
  if (!Number.isFinite(factor) || factor <= 0) return null

  const taken = new Set(exclude)
  const ranked = entries
    .filter((e) => Number.isFinite(e?.multiple) && e.multiple > 0 && !taken.has(e.anchor))
    .map((e) => ({ ...e, multiple: e.multiple * factor }))
    .filter((e) => e.multiple >= MIN_MULTIPLE && e.multiple <= MAX_MULTIPLE)
    .sort((a, b) => score(a.multiple) - score(b.multiple))
  if (!ranked.length) return null

  const best = ranked[0]
  const local = ranked.find((e) => e.locales?.includes(locale))
  if (local && score(local.multiple) - score(best.multiple) <= LOCALE_SCORE_SLACK) {
    return local
  }
  // No locale match, so take whatever reads best — including anchors tagged for
  // someone else. A tag marks an anchor as *extra* resonant for an audience, not
  // as off-limits to everyone else; an English reader understands the EU's
  // annual budget perfectly well, and "1.1x the EU budget" beats the untagged
  // "5.9x Netflix's annual revenue" that skipping tagged entries would give.
  return best
}

/** Binds the two above to the active locale and the i18n anchor catalogue. */
export function useComparison() {
  const { t, locale } = useI18n()

  /**
   * `entries` is one shortlist off `valuation.comparisons`; `opts` carries the
   * `factor` and `exclude` described on pickAnchor.
   * Returns `{ anchor, multiple, label }` for rendering, or null when there is
   * nothing sensible to say — which the backend signals deliberately for
   * figures too small to compare. `anchor` is exposed so a caller can feed it
   * back as `exclude` for the next figure.
   */
  function compare(entries, opts) {
    const picked = pickAnchor(entries, locale.value, opts)
    if (!picked) return null
    const multiple = formatMultiple(picked.multiple, locale.value)
    if (!multiple) return null
    return {
      anchor: picked.anchor,
      multiple,
      label: t(`comparisons.anchors.${picked.anchor}`),
    }
  }

  return { compare }
}
