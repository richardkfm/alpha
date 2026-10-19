<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { YIELD_ROWS } from '../data/yields.js'
import { barPct as barPctScale } from '../data/yieldScale.js'
import { useBiomeMeta } from '../data/useBiomeMeta.js'
import { useFormat } from '../data/useFormat.js'

const { t } = useI18n()
const { BIOME_ORDER, biomeColor, biomeLabel } = useBiomeMeta()
const translatedYieldRows = computed(() =>
  YIELD_ROWS.map((r) => ({ ...r, label: t(`yields.${r.key}`) })),
)

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
  // Catalogue fetch state, so the view can say "loading" / "unreachable"
  // instead of rendering an empty picker.
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['retry'])

const MAX_COMPARE = 5

const selectedIds = ref([])
const query = ref('')
const sortBy = ref('tev') // 'tev' | 'area' | 'name'

// Intl places the currency symbol itself, so currency_symbol goes unread here.
const { money, moneyFull, perHa, hectares, percent, currency } = useFormat(
  () => props.regions[0]?.currency,
)

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
    label: biomeLabel(k),
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

// Seed the comparison with the three highest-intensity ecosystems so the view
// is never empty on first open — or as soon as the catalogue arrives, if it was
// still loading (or retried) when the view opened.
function seed() {
  if (!selectedIds.value.length && props.regions.length) {
    selectedIds.value = [...props.regions]
      .sort(
        (a, b) =>
          b.total_ecosystem_value_per_sqm_year - a.total_ecosystem_value_per_sqm_year,
      )
      .slice(0, 3)
      .map((r) => r.id)
  }
}
onMounted(seed)
watch(() => props.regions.length, seed)
</script>

<template>
  <section class="compare">
    <!-- Picker -->
    <aside class="picker" :aria-label="t('compare.regions')">
      <header class="picker-head">
        <div class="picker-title">
          <span>{{ t('compare.regions') }}</span>
          <span class="picker-count num">{{ regions.length }}</span>
          <span class="picker-cap num" :class="{ full: atCapacity }" :title="t('compare.capacityTitle', { max: MAX_COMPARE })">
            {{ t('compare.selected', { n: selectedIds.length, max: MAX_COMPARE }) }}
          </span>
        </div>
        <input
          v-model="query"
          class="search"
          type="search"
          :placeholder="t('compare.searchPlaceholder')"
          :aria-label="t('compare.searchLabel')"
          @keydown.esc.stop="query = ''"
        />
        <div class="sort" role="group" :aria-label="t('compare.sortGroup')">
          <button :class="{ on: sortBy === 'tev' }" :aria-pressed="sortBy === 'tev'" @click="sortBy = 'tev'">{{ t('compare.sort.value') }}</button>
          <button :class="{ on: sortBy === 'area' }" :aria-pressed="sortBy === 'area'" @click="sortBy = 'area'">{{ t('compare.sort.area') }}</button>
          <button :class="{ on: sortBy === 'name' }" :aria-pressed="sortBy === 'name'" @click="sortBy = 'name'">{{ t('compare.sort.name') }}</button>
        </div>
      </header>

      <div class="picker-list">
        <div v-if="loading && !regions.length" class="picker-state" role="status">
          <span class="spinner" aria-hidden="true"></span>{{ t('compare.loading') }}
        </div>
        <div v-else-if="!regions.length" class="picker-state">
          {{ t('compare.noRegions') }}
        </div>
        <div v-else-if="!groupedRegions.length" class="picker-state">
          <span>{{ t('compare.noResults', { query: query.trim() }) }}</span>
          <button class="link-btn" @click="query = ''">{{ t('compare.clearSearch') }}</button>
        </div>
        <p v-else-if="atCapacity" class="capacity-note">{{ t('compare.capacityFull') }}</p>
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
            :aria-pressed="isSelected(r.id)"
            :disabled="!isSelected(r.id) && atCapacity"
            :title="!isSelected(r.id) && atCapacity ? t('compare.capacityFull') : r.name"
            @click="toggle(r.id)"
          >
            <span class="pick-check" :style="{ '--c': g.color }" aria-hidden="true"></span>
            <span class="pick-text">
              <span class="pick-name">{{ r.name }}</span>
              <span class="pick-sub num">{{ t('compare.pickSub', { value: perHa(r.total_ecosystem_value_per_sqm_year), area: hectares(r.area.hectares) }) }}</span>
            </span>
          </button>
        </div>
      </div>
    </aside>

    <!-- Comparison board -->
    <div class="board">
      <header class="board-head">
        <div>
          <h2>{{ t('compare.title') }}</h2>
          <p>{{ t('compare.subtitle', { currency, max: MAX_COMPARE }) }}</p>
        </div>
        <button v-if="selected.length" class="clear" @click="clearAll">{{ t('compare.clear') }}</button>
      </header>

      <div v-if="error && !regions.length" class="empty" role="alert">
        <span class="empty-mark err" aria-hidden="true">!</span>
        <p>{{ error }}</p>
        <button class="retry" :disabled="loading" @click="emit('retry')">
          {{ loading ? t('stage.retrying') : t('stage.retry') }}
        </button>
      </div>

      <div v-else-if="loading && !regions.length" class="empty" role="status">
        <span class="spinner" aria-hidden="true"></span>
        <p>{{ t('compare.loading') }}</p>
      </div>

      <div v-else-if="!selected.length" class="empty">
        <span class="empty-mark" aria-hidden="true">⊞</span>
        <p>{{ t('compare.empty') }}</p>
      </div>

      <div v-else class="matrix-scroll">
        <div class="matrix" :style="{ gridTemplateColumns: gridCols }">
          <!-- header row -->
          <div class="cell corner"></div>
          <div v-for="r in selected" :key="'h-' + r.id" class="cell region-head">
            <button
              class="remove"
              @click="toggle(r.id)"
              :aria-label="t('compare.remove', { name: r.name })"
              :title="t('compare.remove', { name: r.name })"
            >×</button>
            <span class="rh-name">{{ r.name }}</span>
            <span class="rh-biome" :style="{ '--c': biomeColor(r.biome_key) }">
              <span class="rh-dot"></span>{{ biomeLabel(r.biome_key) }}
            </span>
            <span class="rh-region">{{ r.region }}</span>
          </div>

          <!-- TEV / ha hero row -->
          <div class="cell rowlabel strong">{{ t('compare.rows.tevHa') }}</div>
          <div v-for="r in selected" :key="'t-' + r.id" class="cell tev-cell num">
            {{ perHa(r.total_ecosystem_value_per_sqm_year) }}
          </div>

          <!-- annual total (area-scaled) -->
          <div class="cell rowlabel">{{ t('compare.rows.annual') }}</div>
          <div
            v-for="r in selected"
            :key="'a-' + r.id"
            class="cell num-cell gold num"
            :title="moneyFull(r.total_ecosystem_value_per_year)"
          >
            {{ money(r.total_ecosystem_value_per_year) }}
          </div>

          <!-- standing natural-asset value (capitalised) -->
          <div class="cell rowlabel strong">{{ t('compare.rows.asset') }}</div>
          <div
            v-for="r in selected"
            :key="'as-' + r.id"
            class="cell num-cell asset num"
            :title="moneyFull(r.capitalized_value && r.capitalized_value.asset_value_total)"
          >
            {{ money(r.capitalized_value && r.capitalized_value.asset_value_total) }}
          </div>

          <!-- conversion liability (the perpetual debt of building over it) -->
          <template v-if="showLiability">
            <div class="cell rowlabel">{{ t('compare.rows.liability') }}</div>
            <div
              v-for="r in selected"
              :key="'cl-' + r.id"
              class="cell num-cell liab num"
              :title="moneyFull(r.conversion_liability && r.conversion_liability.present_value)"
            >
              {{ money(r.conversion_liability && r.conversion_liability.present_value) }}
            </div>
          </template>

          <!-- irreversible / un-nettable losses -->
          <template v-if="showRedLines">
            <div class="cell rowlabel">{{ t('compare.rows.redLines') }}</div>
            <div v-for="r in selected" :key="'rl-' + r.id" class="cell num-cell muted">
              {{ t('compare.rows.redLinesCount', { n: r.red_lines?.length ?? 0 }, r.red_lines?.length ?? 0) }}
            </div>
          </template>

          <!-- area -->
          <div class="cell rowlabel">{{ t('compare.rows.area') }}</div>
          <div v-for="r in selected" :key="'ar-' + r.id" class="cell num-cell muted num">
            {{ hectares(r.area.hectares) }} ha
          </div>

          <!-- land-cover intactness -->
          <div class="cell rowlabel">{{ t('compare.rows.intactness') }}</div>
          <div v-for="r in selected" :key="'in-' + r.id" class="cell num-cell muted num">
            {{ percent(r.intactness) }}
          </div>

          <!-- yield breakdown rows -->
          <template v-for="cat in translatedYieldRows" :key="cat.key">
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
              <span class="bar-num num">{{ perHa(r.yields_per_sqm_year[cat.key]) }}</span>
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
  padding: var(--topbar-h) 18px 18px;
  gap: var(--space-4);
  background: var(--stage-bg);
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
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
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
.picker-cap {
  margin-left: auto;
  font-size: var(--fs-2xs);
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text-faint);
}
.picker-cap.full {
  color: var(--gold);
}
.picker-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6) var(--space-3);
  text-align: center;
  font-size: var(--fs-sm);
  line-height: 1.5;
  color: var(--text-muted);
}
.link-btn {
  border: none;
  background: none;
  padding: 0;
  color: var(--accent);
  font: inherit;
  font-size: var(--fs-xs);
  font-weight: 700;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.capacity-note {
  margin: 0 2px var(--space-3);
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  background: var(--gold-bg);
  border: 1px solid var(--gold-border);
  font-size: var(--fs-xs);
  line-height: 1.4;
  color: var(--text-muted);
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
  color: var(--on-accent);
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
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
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
  font-size: var(--fs-lg);
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
  padding: 5px 12px;
  font-size: var(--fs-xs);
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
.empty-mark.err {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  font-size: 1.3rem;
  font-weight: 900;
  opacity: 1;
  color: var(--danger);
  background: var(--danger-bg);
  border: 1px solid var(--danger-border);
}
.retry {
  padding: 8px 20px;
  border-radius: var(--radius-pill);
  border: none;
  background: linear-gradient(180deg, var(--accent), var(--teal-strong));
  color: var(--on-accent);
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: 700;
  cursor: pointer;
}
.retry:disabled {
  opacity: 0.6;
  cursor: progress;
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
  color: var(--danger);
  font-weight: 700;
  background: color-mix(in srgb, var(--danger) 8%, var(--bg-deep));
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

/* Phones: stack the picker above the board instead of squeezing both. */
@media (max-width: 720px) {
  .compare {
    flex-direction: column;
    padding: var(--topbar-h) 12px 12px;
    gap: var(--space-3);
  }
  .picker {
    width: 100%;
    max-width: none;
    max-height: 42%;
  }
  .board {
    flex: 1;
    min-height: 0;
  }
}
</style>
