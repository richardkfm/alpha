<script setup>
import { computed } from 'vue'

const props = defineProps({
  region: { type: Object, required: true },
  valuation: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  backendOnline: { type: Boolean, default: null },
  error: { type: String, default: '' },
})
defineEmits(['close'])

// Human-readable yield rows, in the spec's order.
const YIELD_ROWS = [
  ['carbon_capture', 'Carbon Capture'],
  ['climate_regulation', 'Climate Regulation'],
  ['water_filtration', 'Water Filtration'],
  ['biodiversity_premium', 'Biodiversity Premium'],
  ['soil_nutrient_value', 'Soil Nutrient Value'],
]

const symbol = computed(() => props.valuation?.currency_symbol ?? '$')

const yieldRows = computed(() => {
  if (!props.valuation) return []
  return YIELD_ROWS.map(([key, label]) => ({
    label,
    value: props.valuation.yields_per_sqm_year[key],
  }))
})

// Per-sqm yields are sub-cent — show 4 decimals; area totals use grouping.
function fmtPerSqm(n) {
  return n == null ? '—' : `${symbol.value}${Number(n).toFixed(4)}`
}
function fmtTotal(n) {
  if (n == null) return '—'
  return symbol.value + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 })
}
function fmtInt(n) {
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 })
}
</script>

<template>
  <aside class="panel">
    <header class="panel-head">
      <div class="title-row">
        <h2>{{ region.name }}</h2>
        <button class="close" @click="$emit('close')" aria-label="Close">×</button>
      </div>
      <p class="region">{{ region.region }}</p>
      <span class="conn" :class="{ ok: backendOnline, down: backendOnline === false }">
        <template v-if="backendOnline">● backend online</template>
        <template v-else-if="backendOnline === false">● backend offline</template>
        <template v-else>● checking…</template>
      </span>
    </header>

    <div v-if="loading" class="state">Calculating ecosystem value…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <template v-else-if="valuation">
      <section class="area">
        <div>
          <span class="k">Polygon area</span>
          <span class="v">{{ fmtInt(valuation.area.sqm) }} sqm</span>
        </div>
        <div>
          <span class="k">&nbsp;</span>
          <span class="v">{{ fmtInt(valuation.area.hectares) }} ha</span>
        </div>
      </section>

      <section class="yields">
        <h3>
          Ecosystem service yields
          <small>({{ valuation.currency }} / sqm / year)</small>
        </h3>
        <ul>
          <li v-for="row in yieldRows" :key="row.label">
            <span>{{ row.label }}</span>
            <span class="num">{{ fmtPerSqm(row.value) }}</span>
          </li>
        </ul>
      </section>

      <section class="tev">
        <span class="tev-label">Total Ecosystem Value</span>
        <span class="tev-value">{{ fmtPerSqm(valuation.total_ecosystem_value_per_sqm_year) }}</span>
        <span class="tev-unit">{{ valuation.currency }} / sqm / year</span>
      </section>

      <section class="tev-total">
        <span class="k">Value of this area, per year</span>
        <span class="v">{{ fmtTotal(valuation.total_ecosystem_value_per_year) }} {{ valuation.currency }}</span>
      </section>

      <section class="callout">{{ region.gdpCallout }}</section>

      <p class="method">{{ valuation.methodology_note }}</p>
    </template>
  </aside>
</template>

<style scoped>
.panel {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 1100;
  height: 100%;
  width: min(400px, 92vw);
  overflow-y: auto;
  padding: 60px 22px 28px; /* clears the floating topbar */
  background: var(--bg-panel);
  border-left: 1px solid var(--border);
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.35);
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.close {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
}
.close:hover {
  border-color: var(--accent);
}

.panel-head h2 {
  margin: 0;
  font-size: 1.35rem;
  color: var(--text);
}
.region {
  margin: 4px 0 8px;
  color: var(--text-muted);
  font-size: 0.85rem;
}
.conn {
  font-size: 0.72rem;
  color: var(--text-muted);
}
.conn.ok {
  color: var(--teal);
}
.conn.down {
  color: #f87171;
}

.area {
  display: flex;
  gap: 18px;
  margin: 16px 0;
  padding: 12px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.area .k {
  display: block;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}
.area .v {
  font-size: 0.95rem;
  font-weight: 600;
}

.state {
  padding: 18px 0;
  color: var(--text-muted);
}
.state.err {
  color: #f87171;
}

.yields h3 {
  font-size: 0.9rem;
  margin: 6px 0 10px;
}
.yields h3 small {
  color: var(--text-muted);
  font-weight: 400;
}
.yields ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.yields li {
  display: flex;
  justify-content: space-between;
  padding: 9px 0;
  border-bottom: 1px dashed var(--border);
  font-size: 0.9rem;
}
.yields .num {
  font-variant-numeric: tabular-nums;
  color: var(--text);
  font-weight: 600;
}

.tev {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin: 18px 0;
  padding: 16px;
  border-radius: 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--accent);
}
.tev-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
}
.tev-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--accent);
  line-height: 1.1;
}
.tev-unit {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.tev-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin: -6px 0 14px;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
}
.tev-total .k {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}
.tev-total .v {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.callout {
  margin: 14px 0;
  padding: 12px 14px;
  border-left: 3px solid var(--accent);
  background: var(--bg-elevated);
  border-radius: 0 8px 8px 0;
  font-size: 0.86rem;
  color: var(--text);
}

.method {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-style: italic;
}
</style>
