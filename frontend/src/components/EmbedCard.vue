<script setup>
// alpha — embeddable valuation widget.
//
// A self-contained card meant to live inside a third-party <iframe>
// (/embed.html?region=<id>&currency=<cur>&theme=<dark|light>). It pulls a single
// catalogue region from GET /api/v1/regions/{id} — same-origin, since the iframe
// is served from alpha's own host — and renders the headline Total Ecosystem
// Value, the capitalised standing-asset value, and the conversion liability.
import { ref, computed, onMounted } from 'vue'
import { biomeColor, biomeLabel as englishBiomeLabel } from '../data/biomeMeta.js'
// The embed entry (embed.js) deliberately skips vue-i18n to keep the iframe
// bundle small, so this reaches for the pure formatters and takes its locale
// from the URL instead of the useFormat composable.
import { formatMoney, formatMoneyFull, formatHectares } from '../data/formatNumber.js'

const region = ref(null)
const loading = ref(true)
const errorKey = ref('') // an "embed.*" message key, resolved at render time

const params = new URLSearchParams(window.location.search)
const regionId = params.get('region') || ''
const currency = (params.get('currency') || 'USD').toUpperCase()
// Host pages can request German/Spanish number conventions; anything unknown
// falls back to English rather than letting Intl throw on a bad tag.
const SUPPORTED = ['en', 'de', 'es']
const rawLocale = (params.get('locale') || 'en').slice(0, 2).toLowerCase()
const locale = SUPPORTED.includes(rawLocale) ? rawLocale : 'en'

// The card's labels live in the shared locale catalogue (i18n/locales/*.json,
// "embed" namespace). vue-i18n is deliberately not loaded in the iframe, and
// only the one requested locale is fetched (a lazy chunk), so the iframe never
// downloads the other languages.
const LOADERS = {
  en: () => import('../i18n/locales/en.json'),
  de: () => import('../i18n/locales/de.json'),
  es: () => import('../i18n/locales/es.json'),
}
const messages = ref(null)
function t(key) {
  if (key === 'tagline') return messages.value?.brand?.tagline ?? ''
  return messages.value?.embed?.[key] ?? ''
}
function biomeLabel(key) {
  return messages.value?.biomes?.[key]?.label ?? englishBiomeLabel(key)
}
document.documentElement.lang = locale
const biomeKey = computed(() => region.value?.biome_key ?? 'tropical_rainforest')
const accent = computed(() => biomeColor(biomeKey.value))

// Capitalise the annual flow at the standard 3% reference so the embed shows the
// same standing-asset figure the side panel defaults to.
const standingValue = computed(() => {
  const annual = region.value?.total_ecosystem_value_per_year
  return annual == null ? null : annual / 0.03
})
const liability = computed(() => region.value?.conversion_liability?.present_value ?? null)

const opts = { locale, currency }
const money = (n) => formatMoney(n, opts)
const moneyFull = (n) => formatMoneyFull(n, opts)
const hectares = (n) => formatHectares(n, opts)

async function loadMessages() {
  try {
    messages.value = (await LOADERS[locale]()).default
  } catch {
    // Labels stay blank rather than breaking the figures, which still render.
  }
}

async function loadRegion() {
  if (!regionId) {
    errorKey.value = 'noRegion'
    return
  }
  try {
    const res = await fetch(`/api/v1/regions/${encodeURIComponent(regionId)}?currency=${currency}`)
    if (res.status === 404) throw new Error('not-found')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    region.value = (await res.json()).region
  } catch (e) {
    errorKey.value = e.message === 'not-found' ? 'notFound' : 'failed'
  }
}

onMounted(async () => {
  await Promise.all([loadMessages(), loadRegion()])
  loading.value = false
})
</script>

<template>
  <a
    class="card"
    href="/"
    target="_blank"
    rel="noopener"
    :title="t('open')"
    :style="{ '--biome': accent }"
  >
    <div v-if="loading" class="state" role="status">
      <span class="spinner" aria-hidden="true"></span>
    </div>
    <div v-else-if="errorKey" class="state err" role="alert">{{ t(errorKey) }}</div>

    <template v-else>
      <header class="head">
        <span class="biome-dot" aria-hidden="true"></span>
        <span class="titles">
          <span class="name">{{ region.name }}</span>
          <span class="biome">{{ biomeLabel(biomeKey) }} · {{ hectares(region.area?.hectares) }} ha</span>
        </span>
      </header>

      <div class="tev">
        <span class="tev-k">{{ t('tev') }}</span>
        <!-- The period rides on the figure's baseline, not in a caption under
             it: in a 340x240 embed the caption is the first thing a reader's
             eye skips, and an unlabelled total reads as a stock, not a flow.
             The currency code is gone from the caption too — money() already
             renders the symbol, so it only ever said "1,4 Bio. € EUR". -->
        <span
          class="tev-v"
          :title="moneyFull(region.total_ecosystem_value_per_year)"
          :aria-label="`${moneyFull(region.total_ecosystem_value_per_year)} ${t('perYearAria')}`"
        >
          <span class="tev-n">{{ money(region.total_ecosystem_value_per_year) }}</span>
          <span class="tev-per" aria-hidden="true">{{ t('perYear') }}</span>
        </span>
        <span class="tev-u">{{ t('wholeArea') }}</span>
      </div>

      <div class="row">
        <div class="cell">
          <span class="cell-k">{{ t('standing') }}</span>
          <span class="cell-v" :title="moneyFull(standingValue)" :aria-label="moneyFull(standingValue)">{{ money(standingValue) }}</span>
        </div>
        <div class="cell">
          <span class="cell-k">{{ t('liability') }}</span>
          <span class="cell-v warn" :title="moneyFull(liability)" :aria-label="moneyFull(liability)">{{ money(liability) }}</span>
        </div>
      </div>

      <footer class="foot">
        <span class="brand">alpha</span>
        <span class="tag">{{ t('tagline') }}</span>
      </footer>
    </template>
  </a>
</template>

<style scoped>
/* theme.css is always loaded by embed.js, so tokens are used directly — the
   card follows ?theme= exactly like the main app. Only the biome hue is local
   (--biome), so the shared --accent token keeps its meaning. */
.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  box-sizing: border-box;
  padding: var(--space-4) 18px;
  background: var(--bg-panel);
  color: var(--text);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  text-decoration: none;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  transition: border-color 0.18s var(--ease);
}
.card:hover {
  border-color: color-mix(in srgb, var(--biome) 50%, var(--border));
}
.state {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin: auto;
  color: var(--text-muted);
  font-size: 0.85rem;
}
.state.err {
  color: var(--danger);
}
.head {
  display: flex;
  align-items: center;
  gap: 9px;
}
.biome-dot {
  flex: none;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--biome);
  box-shadow: 0 0 10px var(--biome);
}
.titles {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
}
.name {
  font-size: 1rem;
  font-weight: 800;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.biome {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}
.tev {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}
.tev-k {
  font-size: var(--fs-2xs);
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
}
.tev-v {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0 6px;
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-weight: 800;
  color: color-mix(in srgb, var(--biome) 75%, var(--text));
}
.tev-n {
  font-size: 1.8rem;
}
.tev-per {
  font-size: 0.95rem;
}
.tev-u {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}
.row {
  display: flex;
  gap: 10px;
}
.cell {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-2) 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
}
.cell-k {
  font-size: var(--fs-2xs);
  color: var(--text-muted);
}
.cell-v {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--gold);
}
.cell-v.warn {
  color: var(--danger);
}
.foot {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-top: auto;
  padding-top: var(--space-1);
}
.brand {
  font-weight: 800;
  font-size: 0.82rem;
  color: var(--accent);
}
.tag {
  font-size: var(--fs-2xs);
  color: var(--text-muted);
}
</style>
