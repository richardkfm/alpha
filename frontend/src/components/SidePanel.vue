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

const hectares = computed(() => props.region.areaSqm / 10_000)

// Human-readable yield rows, in the spec's order.
const YIELD_ROWS = [
  ['carbon_capture_usd', 'Carbon Capture'],
  ['climate_regulation_usd', 'Climate Regulation'],
  ['water_filtration_usd', 'Water Filtration'],
  ['biodiversity_premium_usd', 'Biodiversity Premium'],
  ['soil_nutrient_value_usd', 'Soil Nutrient Value'],
]

const yieldRows = computed(() => {
  if (!props.valuation) return []
  return YIELD_ROWS.map(([key, label]) => ({
    label,
    value: props.valuation.yields[key],
  }))
})

function fmtUsd(n) {
  return n == null ? '—' : `$${Number(n).toFixed(2)}`
}
function fmtInt(n) {
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 })
}
</script>

<template>
  <aside class="panel">
    <button class="close" @click="$emit('close')" aria-label="Close">×</button>

    <header class="panel-head">
      <h2>{{ region.name }}</h2>
      <p class="region">{{ region.region }}</p>
      <span class="conn" :class="{ ok: backendOnline, down: backendOnline === false }">
        <template v-if="backendOnline">● backend online</template>
        <template v-else-if="backendOnline === false">● backend offline</template>
        <template v-else>● checking…</template>
      </span>
    </header>

    <section class="area">
      <div>
        <span class="k">Area</span>
        <span class="v">{{ fmtInt(region.areaSqm) }} sqm</span>
      </div>
      <div>
        <span class="k">&nbsp;</span>
        <span class="v">{{ fmtInt(hectares) }} ha</span>
      </div>
    </section>

    <div v-if="loading" class="state">Calculating ecosystem value…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <template v-else-if="valuation">
      <section class="yields">
        <h3>Ecosystem service yields <small>(USD / sqm / year)</small></h3>
        <ul>
          <li v-for="row in yieldRows" :key="row.label">
            <span>{{ row.label }}</span>
            <span class="num">{{ fmtUsd(row.value) }}</span>
          </li>
        </ul>
      </section>

      <section class="tev">
        <span class="tev-label">Total Ecosystem Value</span>
        <span class="tev-value">{{ fmtUsd(valuation.total_ecosystem_value_usd) }}</span>
        <span class="tev-unit">{{ valuation.currency }} / sqm / year</span>
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
  padding: 64px 22px 28px;
  background: var(--bg-panel);
  border-left: 1px solid var(--border);
  box-shadow: -12px 0 40px rgba(0, 0, 0, 0.35);
}

.close {
  position: absolute;
  top: 14px;
  right: 16px;
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
