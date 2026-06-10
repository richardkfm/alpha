<script setup>
import { ref, computed, onMounted } from 'vue'
import { YIELD_ROWS } from '../data/yields.js'
import { barPct as barPctScale } from '../data/yieldScale.js'
import { BIOME_META, BIOME_ORDER, biomeColor, biomeLabel } from '../data/biomeMeta.js'

const props = defineProps({
  // Pre-valued region catalogue from the backend (data/useRegions.js). Reading
  // live means a currency re-price flows straight through to the comparison.
  regions: { type: Array, default: () => [] },
  // Per-service cross-biome ceilings (max across the whole catalogue), so bars
  // mean the same thing here as in the side panel: magnitude vs the strongest
  // biome, not just relative to the handful of regions currently selected.
  ceilings: { type: Object, default: () => ({}) },
  showLiability: { type: Boolean, default: true },
  showRedLines: { type: Boolean, default: true },
})

const MAX_COMPARE = 5

const selectedIds = ref([])
const query = ref('')
const sortBy = ref('tev') // 'tev' | 'area' | 'name'

const symbol = computed(() => props.regions[0]?.currency_symbol ?? '$')
const currency = computed(() => props.regions[0]?.currency ?? 'USD')

// ----- picker (left) -------------------------------------------------------
const sortedRegions = computed(() => {
  const q = query.value.trim().toLowerCase()
  const list = props.regions.filter(
    (r) =>
      !q ||
      r.name.toLowerCase().includes(q) ||
      (r.region || '').toLowerCase().includes(q) ||
      biomeLabel(r.biome_key).toLowerCase().includes(q),
  )
  const by = {
    tev: (a, b) =>
      b.total_ecosystem_value_per_sqm_year - a.total_ecosystem_value_per_sqm_year,
    area: (a, b) => b.area.sqm - a.area.sqm,
    name: (a, b) => a.name.localeCompare(b.name),
  }
  return [...list].sort(by[sortBy.value] || by.tev)
})

// Group the (filtered, sorted) picker list by biome, in legend order.
const groupedRegions = computed(() => {
  const byBiome = {}
  for (const r of sortedRegions.value) (byBiome[r.biome_key] ||= []).push(r)
  return BIOME_ORDER.filter((k) => byBiome[k]?.length).map((k) => ({
    key: k,
    label: BIOME_META[k].label,
    color: biomeColor(k),
    regions: byBiome[k],
  }))
})

function isSelected(id) {
  return selectedIds.value.includes(id)
}
const atCapacity = computed(() => selectedIds.value.length >= MAX_COMPARE)

function toggle(id) {
  if (isSelected(id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  } else if (!atCapacity.value) {
    selectedIds.value = [...selectedIds.value, id]
  }
}
function clearAll() {
  selectedIds.value = []
}

// ----- comparison (right) --------------------------------------------------
// Resolve selected ids to live region objects, preserving pick order.
const selected = computed(() =>
  selectedIds.value
    .map((id) => props.regions.find((r) => r.id === id))
    .filter(Boolean),
)

// Bars scale against the fixed cross-biome ceiling (max across the whole
// catalogue), so a taller bar means a genuinely higher value for that service —
// comparable across biomes, not just within the current selection.
function barPct(region, key) {
  return barPctScale(region.yields_per_sqm_year[key], props.ceilings[key])
}

const gridCols = computed(
  () => `minmax(120px, 168px) repeat(${selected.value.length}, minmax(150px, 1fr))`,
)

// ----- formatting ----------------------------------------------------------
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

// Seed the comparison with the three highest-intensity ecosystems so the view
// is never empty on first open.
onMounted(() => {
  if (!selectedIds.value.length && props.regions.length) {
    selectedIds.value = [...props.regions]
      .sort(
        (a, b) =>
          b.total_ecosystem_value_per_sqm_year - a.total_ecosystem_value_per_sqm_year,
      )
      .slice(0, 3)
      .map((r) => r.id)
  }
})
</script>

<template>
  <section class="compare">
    <!-- Picker -->
    <aside class="picker">
      <header class="picker-head">
        <div class="picker-title">
          <span>Regions</span>
          <span class="picker-count">{{ regions.length }}</span>
        </div>
        <input
          v-model="query"
          class="search"
          type="search"
          placeholder="Search ecosystems…"
          aria-label="Search regions"
        />
        <div class="sort" role="group" aria-label="Sort regions">
          <button :class="{ on: sortBy === 'tev' }" @click="sortBy = 'tev'">Value</button>
          <button :class="{ on: sortBy === 'area' }" @click="sortBy = 'area'">Area</button>
          <button :class="{ on: sortBy === 'name' }" @click="sortBy = 'name'">A–Z</button>
        </div>
      </header>

      <div class="picker-list">
        <div v-for="g in groupedRegions" :key="g.key" class="group">
          <div class="group-head">
            <span class="group-dot" :style="{ background: g.color }"></span>
            {{ g.label }}
          </div>
          <button
            v-for="r in g.regions"
            :key="r.id"
            class="pick"
            :class="{ on: isSelected(r.id) }"
            :disabled="!isSelected(r.id) && atCapacity"
            @click="toggle(r.id)"
          >
            <span class="pick-check" :style="{ '--c': g.color }"></span>
            <span class="pick-text">
              <span class="pick-name">{{ r.name }}</span>
              <span class="pick-sub">{{ fmtPerSqm(r.total_ecosystem_value_per_sqm_year) }} / sqm · {{ fmtInt(r.area.hectares) }} ha</span>
            </span>
          </button>
        </div>
      </div>
    </aside>

    <!-- Comparison board -->
    <div class="board">
      <header class="board-head">
        <div>
          <h2>Compare ecosystems</h2>
          <p>Total Ecosystem Value side by side — {{ currency }} per sqm per year. Add up to {{ MAX_COMPARE }}.</p>
        </div>
        <button v-if="selected.length" class="clear" @click="clearAll">Clear</button>
      </header>

      <div v-if="!selected.length" class="empty">
        <span class="empty-mark">⊞</span>
        <p>Pick regions from the left to compare their ecosystem-service yields and Total Ecosystem Value.</p>
      </div>

      <div v-else class="matrix-scroll">
        <div class="matrix" :style="{ gridTemplateColumns: gridCols }">
          <!-- header row -->
          <div class="cell corner"></div>
          <div v-for="r in selected" :key="'h-' + r.id" class="cell region-head">
            <button class="remove" @click="toggle(r.id)" aria-label="Remove">×</button>
            <span class="rh-name">{{ r.name }}</span>
            <span class="rh-biome" :style="{ '--c': biomeColor(r.biome_key) }">
              <span class="rh-dot"></span>{{ r.biome_label }}
            </span>
            <span class="rh-region">{{ r.region }}</span>
          </div>

          <!-- TEV / sqm hero row -->
          <div class="cell rowlabel strong">TEV / sqm / yr</div>
          <div v-for="r in selected" :key="'t-' + r.id" class="cell tev-cell">
            {{ fmtPerSqm(r.total_ecosystem_value_per_sqm_year) }}
          </div>

          <!-- annual total (area-scaled) -->
          <div class="cell rowlabel">Annual value (whole area)</div>
          <div v-for="r in selected" :key="'a-' + r.id" class="cell num-cell gold">
            {{ fmtTotal(r.total_ecosystem_value_per_year) }}
          </div>

          <!-- standing natural-asset value (capitalised) -->
          <div class="cell rowlabel strong">Standing asset value</div>
          <div v-for="r in selected" :key="'as-' + r.id" class="cell num-cell asset">
            {{ fmtTotal(r.capitalized_value && r.capitalized_value.asset_value_total) }}
          </div>

          <!-- conversion liability (the perpetual debt of building over it) -->
          <template v-if="showLiability">
            <div class="cell rowlabel">Conversion liability</div>
            <div v-for="r in selected" :key="'cl-' + r.id" class="cell num-cell liab">
              {{ fmtTotal(r.conversion_liability && r.conversion_liability.present_value) }}
            </div>
          </template>

          <!-- irreversible / un-nettable losses -->
          <template v-if="showRedLines">
            <div class="cell rowlabel">Red lines</div>
            <div v-for="r in selected" :key="'rl-' + r.id" class="cell num-cell muted">
              {{ r.red_lines ? r.red_lines.length : 0 }} irreversible
            </div>
          </template>

          <!-- area -->
          <div class="cell rowlabel">Area</div>
          <div v-for="r in selected" :key="'ar-' + r.id" class="cell num-cell muted">
            {{ fmtInt(r.area.hectares) }} ha
          </div>

          <!-- land-cover intactness -->
          <div class="cell rowlabel">Intactness</div>
          <div v-for="r in selected" :key="'in-' + r.id" class="cell num-cell muted">
            {{ r.intactness != null ? Math.round(r.intactness * 100) + '%' : '—' }}
          </div>

          <!-- yield breakdown rows -->
          <template v-for="cat in YIELD_ROWS" :key="cat.key">
            <div class="cell rowlabel">
              <span class="yl-dot" :style="{ background: cat.color }"></span>{{ cat.label }}
            </div>
            <div v-for="r in selected" :key="cat.key + '-' + r.id" class="cell bar-cell">
              <div class="bar-track">
                <div
                  class="bar"
                  :style="{ width: barPct(r, cat.key) + '%', background: cat.color }"
                ></div>
              </div>
              <span class="bar-num">{{ fmtPerSqm(r.yields_per_sqm_year[cat.key]) }}</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.compare {
  position: absolute;
  inset: 0;
  display: flex;
  padding: 70px 18px 18px;
  gap: 16px;
  background: radial-gradient(circle at 30% 10%, #0a1424 0%, var(--bg) 70%);
}

/* ----- picker ----- */
.picker {
  flex: none;
  width: 290px;
  max-width: 42vw;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  box-shadow: var(--shadow-soft);
  overflow: hidden;
}
.picker-head {
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--border-soft);
}
.picker-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--text);
  margin-bottom: 10px;
}
.picker-count {
  font-size: 0.66rem;
  color: var(--text-muted);
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
}
.search {
  width: 100%;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  color: var(--text);
  font-size: 0.82rem;
  outline: none;
  transition: border-color 0.18s var(--ease);
}
.search:focus {
  border-color: var(--accent);
}
.sort {
  display: flex;
  gap: 4px;
  margin-top: 10px;
}
.sort button {
  flex: 1;
  padding: 5px 8px;
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.sort button.on {
  color: var(--accent);
  border-color: var(--accent);
}

.picker-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.group + .group {
  margin-top: 12px;
}
.group-head {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 2px 6px;
}
.group-dot {
  width: 9px;
  height: 9px;
  border-radius: 3px;
}
.pick {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 9px;
  margin-bottom: 5px;
  border-radius: var(--radius-sm);
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s var(--ease), background 0.18s var(--ease);
}
.pick:hover:not(:disabled) {
  border-color: var(--border);
}
.pick:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pick.on {
  border-color: color-mix(in srgb, var(--c, var(--accent)) 60%, transparent);
  background: color-mix(in srgb, var(--c, var(--accent)) 10%, var(--bg-deep));
}
.pick-check {
  flex: none;
  width: 16px;
  height: 16px;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  position: relative;
  transition: background 0.18s var(--ease), border-color 0.18s var(--ease);
}
.pick.on .pick-check {
  background: var(--c, var(--accent));
  border-color: var(--c, var(--accent));
}
.pick.on .pick-check::after {
  content: '✓';
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 0.7rem;
  font-weight: 800;
  color: #05120e;
}
.pick-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.pick-name {
  font-size: 0.83rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pick-sub {
  font-size: 0.66rem;
  color: var(--text-faint);
}

/* ----- board ----- */
.board {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  box-shadow: var(--shadow-soft);
  overflow: hidden;
}
.board-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--border-soft);
}
.board-head h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text);
}
.board-head p {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}
.clear {
  flex: none;
  padding: 6px 13px;
  font-size: 0.74rem;
  font-weight: 700;
  border-radius: 999px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.clear:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  padding: 30px;
  text-align: center;
}
.empty-mark {
  font-size: 2.4rem;
  color: var(--accent);
  opacity: 0.7;
}
.empty p {
  max-width: 340px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.matrix-scroll {
  flex: 1;
  overflow: auto;
  padding: 6px 18px 18px;
}
.matrix {
  display: grid;
  align-items: stretch;
  gap: 1px;
  min-width: min-content;
}
.cell {
  padding: 10px 12px;
  background: var(--bg-deep);
}
.corner {
  background: transparent;
  position: sticky;
  left: 0;
  z-index: 2;
}
.rowlabel {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.74rem;
  color: var(--text-muted);
  background: var(--bg);
  position: sticky;
  left: 0;
  z-index: 2;
}
.rowlabel.strong {
  color: var(--text);
  font-weight: 700;
}
.yl-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.region-head {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: var(--bg-elevated);
  border-top-left-radius: var(--radius-sm);
  border-top-right-radius: var(--radius-sm);
}
.remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg-deep);
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.remove:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.rh-name {
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--text);
  padding-right: 22px;
  line-height: 1.2;
}
.rh-biome {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--c, var(--accent));
}
.rh-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c, var(--accent));
}
.rh-region {
  font-size: 0.66rem;
  color: var(--text-faint);
  line-height: 1.3;
}

.tev-cell {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 7%, var(--bg-deep));
}
.num-cell {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text);
}
.num-cell.gold {
  color: var(--gold);
}
.num-cell.asset {
  color: var(--gold);
  font-size: 1rem;
  font-weight: 800;
  background: color-mix(in srgb, var(--gold) 8%, var(--bg-deep));
}
.num-cell.liab {
  color: #f87171;
  font-weight: 700;
  background: color-mix(in srgb, #f87171 8%, var(--bg-deep));
}
.num-cell.muted {
  color: var(--text-muted);
  font-weight: 600;
}

.bar-cell {
  display: flex;
  flex-direction: column;
  gap: 5px;
  justify-content: center;
}
.bar-track {
  height: 7px;
  border-radius: 999px;
  background: var(--bg-elevated);
  overflow: hidden;
}
.bar {
  height: 100%;
  border-radius: 999px;
  transform-origin: left;
  animation: grow 0.5s var(--ease) both;
  box-shadow: 0 0 10px -2px currentColor;
}
@keyframes grow {
  from {
    transform: scaleX(0);
  }
}
.bar-num {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-muted);
}

@media (max-width: 720px) {
  .picker {
    width: 220px;
  }
}
</style>
