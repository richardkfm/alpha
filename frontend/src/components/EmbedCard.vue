<script setup>
// alpha — embeddable valuation widget.
//
// A self-contained card meant to live inside a third-party <iframe>
// (/embed.html?region=<id>&currency=<cur>&theme=<dark|light>). It pulls a single
// catalogue region from GET /api/v1/regions/{id} — same-origin, since the iframe
// is served from alpha's own host — and renders the headline Total Ecosystem
// Value, the capitalised standing-asset value, and the conversion liability.
import { ref, computed, onMounted } from 'vue'
import { biomeColor, biomeLabel } from '../data/biomeMeta.js'

const region = ref(null)
const loading = ref(true)
const error = ref('')

const params = new URLSearchParams(window.location.search)
const regionId = params.get('region') || ''
const currency = (params.get('currency') || 'USD').toUpperCase()

const symbol = computed(() => region.value?.currency_symbol ?? '$')
const biomeKey = computed(() => region.value?.biome_key ?? 'tropical_rainforest')
const accent = computed(() => biomeColor(biomeKey.value))

// Capitalise the annual flow at the standard 3% reference so the embed shows the
// same standing-asset figure the side panel defaults to.
const standingValue = computed(() => {
  const annual = region.value?.total_ecosystem_value_per_year
  return annual == null ? null : annual / 0.03
})
const liability = computed(() => region.value?.conversion_liability?.present_value ?? null)

function fmtTotal(n) {
  if (n == null) return '—'
  return symbol.value + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 })
}
function fmtHa(n) {
  if (n == null) return '—'
  const v = Number(n)
  return v.toLocaleString('en-US', { maximumFractionDigits: v < 100 ? 1 : 0 })
}

onMounted(async () => {
  if (!regionId) {
    error.value = 'No region specified.'
    loading.value = false
    return
  }
  try {
    const res = await fetch(`/api/v1/regions/${encodeURIComponent(regionId)}?currency=${currency}`)
    if (res.status === 404) throw new Error('Region not found.')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    region.value = (await res.json()).region
  } catch (e) {
    error.value = e.message === 'Region not found.' ? e.message : 'Could not load valuation.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <a
    class="card"
    href="/"
    target="_blank"
    rel="noopener"
    title="Open alpha"
    :style="{ '--accent': accent }"
  >
    <div v-if="loading" class="state">Loading…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <template v-else>
      <header class="head">
        <span class="biome-dot" aria-hidden="true"></span>
        <span class="titles">
          <span class="name">{{ region.name }}</span>
          <span class="biome">{{ biomeLabel(biomeKey) }} · {{ fmtHa(region.area?.hectares) }} ha</span>
        </span>
      </header>

      <div class="tev">
        <span class="tev-k">Total Ecosystem Value</span>
        <span class="tev-v">{{ fmtTotal(region.total_ecosystem_value_per_year) }}</span>
        <span class="tev-u">{{ region.currency }} / year</span>
      </div>

      <div class="row">
        <div class="cell">
          <span class="cell-k">Standing asset</span>
          <span class="cell-v">{{ fmtTotal(standingValue) }}</span>
        </div>
        <div class="cell">
          <span class="cell-k">If converted (liability)</span>
          <span class="cell-v warn">{{ fmtTotal(liability) }}</span>
        </div>
      </div>

      <footer class="foot">
        <span class="brand">alpha</span>
        <span class="tag">putting nature on the balance sheet</span>
      </footer>
    </template>
  </a>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  box-sizing: border-box;
  padding: 16px 18px;
  background: var(--bg, #0c1814);
  color: var(--text, #e8f0ee);
  border-radius: 14px;
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  text-decoration: none;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
.state {
  margin: auto;
  color: var(--text-muted, #93a3a0);
  font-size: 0.85rem;
}
.state.err {
  color: #f87171;
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
  background: var(--accent);
  box-shadow: 0 0 10px var(--accent);
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
  color: var(--text, #e8f0ee);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.biome {
  font-size: 0.72rem;
  color: var(--text-muted, #93a3a0);
}
.tev {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}
.tev-k {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted, #93a3a0);
}
.tev-v {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--accent);
}
.tev-u {
  font-size: 0.72rem;
  color: var(--text-muted, #93a3a0);
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
  padding: 8px 10px;
  background: var(--bg-deep, rgba(0, 0, 0, 0.25));
  border: 1px solid var(--border-soft, rgba(255, 255, 255, 0.06));
  border-radius: 9px;
}
.cell-k {
  font-size: 0.64rem;
  color: var(--text-muted, #93a3a0);
}
.cell-v {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 0.92rem;
  font-weight: 700;
}
.cell-v.warn {
  color: #f6a96b;
}
.foot {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-top: auto;
  padding-top: 4px;
}
.brand {
  font-weight: 800;
  font-size: 0.82rem;
  color: var(--accent);
}
.tag {
  font-size: 0.64rem;
  color: var(--text-muted, #93a3a0);
}
</style>
