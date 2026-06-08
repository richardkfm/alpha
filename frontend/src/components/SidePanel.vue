<script setup>
import { computed, ref } from 'vue'
// Shared yield-category metadata, also used by the Compare dashboard.
import { YIELD_ROWS } from '../data/yields.js'

const props = defineProps({
  region: { type: Object, required: true },
  valuation: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  backendOnline: { type: Boolean, default: null },
  error: { type: String, default: '' },
})
defineEmits(['close'])

const symbol = computed(() => props.valuation?.currency_symbol ?? '$')

// Phase 3: the backend now detects the biome from ingested boundary data.
const classification = computed(() => props.valuation?.classification ?? null)

const yieldRows = computed(() => {
  if (!props.valuation) return []
  const values = YIELD_ROWS.map((r) => props.valuation.yields_per_sqm_year[r.key] ?? 0)
  const max = Math.max(...values, 0) || 1
  return YIELD_ROWS.map(({ key, label, color }) => {
    const value = props.valuation.yields_per_sqm_year[key]
    return {
      label,
      color,
      value,
      // bar width relative to the largest service; floor keeps tiny bars visible
      pct: Math.max(((value ?? 0) / max) * 100, 3),
    }
  })
})

// --- Standing natural-asset value (capitalised perpetual flow) -------------
// Capitalise the annual flow locally so the discount rate can be explored
// without a server round-trip: asset = annual / rate.
const DISCOUNT_RATES = [0.01, 0.03, 0.05]
const discountRate = ref(0.03)
const assetValue = computed(() => {
  const annual = props.valuation?.total_ecosystem_value_per_year
  if (annual == null) return null
  return annual / discountRate.value
})

// Intactness: share of the intact-biome potential the land currently delivers.
const intactness = computed(() => props.valuation?.intactness ?? null)
const potentialAnnual = computed(
  () => props.valuation?.potential?.total_ecosystem_value_per_year ?? null,
)

function fmtPct(n) {
  return n == null ? '—' : `${Math.round(n * 100)}%`
}

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

    <div v-if="loading" class="skeleton" aria-label="Calculating ecosystem value">
      <div class="sk-line sk-row"></div>
      <div class="sk-block"></div>
      <div class="sk-line"></div>
      <div class="sk-line short"></div>
      <div class="sk-hero"></div>
      <span class="sk-note">Calculating ecosystem value…</span>
    </div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <template v-else-if="valuation">
      <section class="area">
        <div>
          <span class="k">Polygon area</span>
          <span class="v num">{{ fmtInt(valuation.area.sqm) }} <em>sqm</em></span>
        </div>
        <div>
          <span class="k">&nbsp;</span>
          <span class="v num">{{ fmtInt(valuation.area.hectares) }} <em>ha</em></span>
        </div>
      </section>

      <section v-if="classification" class="biome">
        <span class="k">Detected biome</span>
        <span class="v">{{ classification.biome_label }}</span>
        <span
          class="biome-src"
          :class="{ inferred: classification.confidence === 'default' }"
        >
          <template v-if="classification.confidence === 'matched'">
            classified from {{ classification.matched_region }} · WWF ecoregions
          </template>
          <template v-else-if="classification.confidence === 'explicit'">
            biome supplied by caller
          </template>
          <template v-else>no boundary match — default biome</template>
        </span>
      </section>

      <section v-if="intactness != null && intactness < 1" class="intactness">
        <div class="intact-head">
          <span class="k">Land-cover intactness</span>
          <span class="intact-pct">{{ fmtPct(intactness) }}</span>
        </div>
        <div class="intact-track">
          <div class="intact-bar" :style="{ width: fmtPct(intactness) }"></div>
        </div>
        <span class="intact-note">
          Delivering {{ fmtPct(intactness) }} of its intact potential of
          {{ fmtTotal(potentialAnnual) }} {{ valuation.currency }}/yr.
        </span>
      </section>

      <section class="yields">
        <h3>
          Ecosystem service yields
          <small>({{ valuation.currency }} / sqm / year)</small>
        </h3>
        <ul>
          <li v-for="row in yieldRows" :key="row.label">
            <div class="yield-meta">
              <span class="yield-dot" :style="{ background: row.color }"></span>
              <span class="yield-label">{{ row.label }}</span>
              <span class="num yield-num">{{ fmtPerSqm(row.value) }}</span>
            </div>
            <div class="yield-track">
              <div
                class="yield-bar"
                :style="{ width: row.pct + '%', background: row.color }"
              ></div>
            </div>
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

      <section class="asset">
        <div class="asset-head">
          <span class="asset-label">Standing natural asset value</span>
          <div class="asset-rates" role="group" aria-label="Discount rate">
            <button
              v-for="r in DISCOUNT_RATES"
              :key="r"
              :class="{ on: discountRate === r }"
              @click="discountRate = r"
            >{{ Math.round(r * 100) }}%</button>
          </div>
        </div>
        <span class="asset-value">{{ fmtTotal(assetValue) }} <em>{{ valuation.currency }}</em></span>
        <span class="asset-sub">
          capitalised perpetual value at {{ Math.round(discountRate * 100) }}% — what this
          area is worth on the balance sheet, left standing
        </span>
      </section>

      <section v-if="region.gdpCallout" class="callout">
        <span class="callout-mark">“</span>{{ region.gdpCallout }}
      </section>

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
  width: min(420px, 94vw);
  overflow-y: auto;
  padding: 78px 22px 30px; /* clears the floating topbar */
  background: linear-gradient(180deg, var(--bg-panel), var(--bg-deep));
  border-left: 1px solid var(--border);
  box-shadow: var(--shadow-panel);
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.close {
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease),
    transform 0.18s var(--ease);
}
.close:hover {
  border-color: var(--accent);
  color: var(--accent);
  transform: rotate(90deg);
}

.panel-head h2 {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.2px;
  color: var(--text);
}
.region {
  margin: 5px 0 10px;
  color: var(--text-muted);
  font-size: 0.84rem;
  line-height: 1.4;
}
.conn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: var(--text-muted);
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
}
.conn.ok {
  color: var(--teal);
}
.conn.down {
  color: #f87171;
}

.area {
  display: flex;
  gap: 12px;
  margin: 18px 0;
}
.area > div {
  flex: 1;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
}
.area .k {
  display: block;
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-faint);
  margin-bottom: 4px;
}
.area .v {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text);
}
.area .v em {
  font-style: normal;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-muted);
}

.biome {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin: 0 0 18px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
}
.biome .k {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-faint);
}
.biome .v {
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--text);
}
.biome-src {
  font-size: 0.72rem;
  color: var(--teal);
}
.biome-src.inferred {
  color: var(--text-muted);
}

.state {
  padding: 18px 0;
  color: var(--text-muted);
}
.state.err {
  color: #f87171;
}

/* loading skeleton */
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 8px 0;
}
.sk-line,
.sk-block,
.sk-hero,
.sk-row {
  border-radius: var(--radius-sm);
  background: linear-gradient(
    100deg,
    var(--bg-elevated) 30%,
    var(--border) 50%,
    var(--bg-elevated) 70%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}
.sk-line {
  height: 14px;
}
.sk-line.short {
  width: 60%;
}
.sk-row {
  height: 56px;
}
.sk-block {
  height: 84px;
}
.sk-hero {
  height: 110px;
  border-radius: var(--radius);
}
.sk-note {
  font-size: 0.8rem;
  color: var(--text-muted);
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

.yields {
  margin-top: 22px;
}
.yields h3 {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  margin: 6px 0 14px;
}
.yields h3 small {
  color: var(--text-faint);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}
.yields ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.yield-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  margin-bottom: 6px;
}
.yield-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.yield-label {
  color: var(--text);
}
.yield-num {
  margin-left: auto;
  color: var(--text-muted);
  font-weight: 600;
  font-size: 0.82rem;
}
.yield-track {
  height: 7px;
  border-radius: 999px;
  background: var(--bg-elevated);
  overflow: hidden;
}
.yield-bar {
  height: 100%;
  border-radius: 999px;
  transform-origin: left;
  animation: grow 0.6s var(--ease) both;
  box-shadow: 0 0 10px -2px currentColor;
}
@keyframes grow {
  from {
    transform: scaleX(0);
  }
}

.tev {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin: 24px 0 14px;
  padding: 18px 18px 16px;
  border-radius: var(--radius);
  background: radial-gradient(
      120% 140% at 0% 0%,
      rgba(45, 212, 191, 0.14),
      transparent 60%
    ),
    var(--bg-elevated);
  border: 1px solid rgba(45, 212, 191, 0.4);
  box-shadow: var(--shadow-glow);
  overflow: hidden;
}
.tev::after {
  content: '';
  position: absolute;
  right: -40px;
  top: -40px;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(45, 212, 191, 0.18), transparent 70%);
  pointer-events: none;
}
.tev-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text-muted);
}
.tev-value {
  font-size: 2.4rem;
  font-weight: 800;
  line-height: 1.05;
  margin: 2px 0;
  background: linear-gradient(95deg, var(--accent), var(--forest-overlay));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.tev-unit {
  font-size: 0.76rem;
  color: var(--text-muted);
}

.tev-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin: 0 0 16px;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
}
.tev-total .k {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}
.tev-total .v {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--gold);
}

.intactness {
  margin: 0 0 18px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
}
.intact-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}
.intact-head .k {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-faint);
}
.intact-pct {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 1rem;
  font-weight: 700;
  color: var(--accent);
}
.intact-track {
  height: 7px;
  border-radius: 999px;
  background: var(--bg-deep);
  overflow: hidden;
}
.intact-bar {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), var(--forest-overlay));
  box-shadow: 0 0 10px -2px var(--accent);
}
.intact-note {
  display: block;
  margin-top: 8px;
  font-size: 0.72rem;
  color: var(--text-muted);
  line-height: 1.4;
}

.asset {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0 0 16px;
  padding: 14px 16px;
  border-radius: var(--radius);
  background: radial-gradient(120% 140% at 100% 0%, rgba(231, 200, 115, 0.14), transparent 60%),
    var(--bg-elevated);
  border: 1px solid rgba(231, 200, 115, 0.4);
}
.asset-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.asset-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--text-muted);
}
.asset-rates {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.asset-rates button {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.68rem;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.15s var(--ease), background 0.15s var(--ease);
}
.asset-rates button.on {
  background: var(--gold);
  color: #1c1606;
}
.asset-value {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 1.9rem;
  font-weight: 800;
  line-height: 1.05;
  color: var(--gold);
}
.asset-value em {
  font-style: normal;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
}
.asset-sub {
  font-size: 0.72rem;
  color: var(--text-muted);
  line-height: 1.4;
}

.callout {
  position: relative;
  margin: 16px 0;
  padding: 14px 16px 14px 18px;
  border-left: 3px solid var(--accent);
  background: var(--bg-elevated);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--text);
}
.callout-mark {
  color: var(--accent);
  font-size: 1.4rem;
  font-weight: 800;
  line-height: 0;
  margin-right: 2px;
  vertical-align: -0.2em;
}

.method {
  font-size: 0.72rem;
  color: var(--text-faint);
  font-style: italic;
  line-height: 1.5;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border-soft);
}
</style>
