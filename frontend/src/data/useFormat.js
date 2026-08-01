// alpha — locale-bound number formatting for components.
//
// A thin Vue wrapper over the pure formatters in formatNumber.js: it supplies
// the active i18n locale and the region's currency so call sites read as
// `money(value)` instead of threading an options bag through every template.
import { computed, unref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  formatMoney,
  formatMoneyFull,
  formatPerHa,
  formatCount,
  formatHectares,
  formatDecimal,
  formatPercent,
  formatLikeTarget,
} from './formatNumber.js'

export { COMPACT_FROM, SQM_PER_HA } from './formatNumber.js'

/**
 * Binds the formatters to the active locale and a currency source.
 * `currencySource` may be a ref, a getter, or a plain string.
 *
 * The locale is read inside each call rather than snapshotted at setup, so a
 * language switch re-renders every figure.
 */
export function useFormat(currencySource) {
  const { locale } = useI18n()
  const currency = computed(() => {
    const c = typeof currencySource === 'function' ? currencySource() : unref(currencySource)
    return c || 'USD'
  })
  const opts = () => ({ locale: locale.value, currency: currency.value })

  return {
    currency,
    money: (n) => formatMoney(n, opts()),
    moneyFull: (n) => formatMoneyFull(n, opts()),
    perHa: (n) => formatPerHa(n, opts()),
    count: (n) => formatCount(n, opts()),
    hectares: (n) => formatHectares(n, opts()),
    decimal: (n, maxDigits) => formatDecimal(n, { ...opts(), maxDigits }),
    percent: (n) => formatPercent(n, opts()),
    likeTarget: (n, target) => formatLikeTarget(n, target, opts()),
  }
}
