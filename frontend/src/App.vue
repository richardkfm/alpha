<script setup>
import { ref, onMounted, defineAsyncComponent } from 'vue'
import WorldMap from './components/WorldMap.vue'
import SidePanel from './components/SidePanel.vue'
import LayerControl from './components/LayerControl.vue'
import SearchBar from './components/SearchBar.vue'
import { useRegions } from './data/useRegions.js'

// The MapLibre globe (and its ~heavy bundle) loads only when 3D mode is active;
// the Compare dashboard and Data hub load only when their mode is opened.
const GlobeMap = defineAsyncComponent(() => import('./components/GlobeMap.vue'))
const CompareDashboard = defineAsyncComponent(() =>
  import('./components/CompareDashboard.vue'),
)
const DataHub = defineAsyncComponent(() => import('./components/DataHub.vue'))

const selectedRegion = ref(null)
const valuation = ref(null)
const backendOnline = ref(null) // null = unknown, true/false once checked
const loading = ref(false)
const errorMsg = ref('')

// Top-level mode: explore on the map, compare regions, or browse the data hub.
const appMode = ref('map') // 'map' | 'compare' | 'data'

// 2D Leaflet map vs 3D MapLibre globe. The globe is the hero view by default.
const viewMode = ref('3d')

// How the areas are drawn on the map: filled polygons, value bubbles, or outline-only.
const displayStyle = ref('polygons') // 'polygons' | 'bubbles' | 'outline'

// Region catalogue (all biomes, pre-valued) fetched from the backend; drives
// both maps, the layer control, the Compare dashboard, and the value bubbles.
const {
  regions,
  biomeLayers,
  pointFeatures,
  loading: regionsLoading,
  error: regionsError,
  loaded: regionsLoaded,
  load: loadRegions,
} = useRegions()

// Thematic layer visibility, shared by both the 2D map and the 3D globe. Every
// biome layer defaults on so the full dataset is visible immediately.
const visibleLayers = ref({})
function syncLayerVisibility() {
  const next = {}
  for (const l of biomeLayers.value) next[l.id] = visibleLayers.value[l.id] ?? true
  visibleLayers.value = next
}
function toggleLayer(id) {
  visibleLayers.value = { ...visibleLayers.value, [id]: !visibleLayers.value[id] }
}

// Currency toggle (Phase 2). The backend converts USD reference values via FX.
const CURRENCIES = ['USD', 'EUR', 'BRL']
const currency = ref('USD')

// Dark is the default theme.
const isDark = ref(true)

// Conversion analysis mode toggles — let users opt out of modes they find too
// radical without losing the core ESV numbers.
const showLiability = ref(true)
const showSystemic = ref(true)
const showRedLines = ref(true)
function applyTheme() {
  document.documentElement.classList.toggle('light', !isDark.value)
}
function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme()
}

onMounted(async () => {
  applyTheme()
  await loadRegions(currency.value)
  syncLayerVisibility()
})

// Fetch the Phase 2 TEV breakdown for a region's polygon in the chosen currency.
// Catalogue regions carry an authoritative biome_key, so we pass it through to
// keep the side-panel value consistent with the map/Compare numbers; custom
// search areas have none, so the backend auto-classifies them from the geometry.
async function fetchValuation(region) {
  const params = new URLSearchParams({ currency: currency.value })
  if (region.biome_key) params.set('biome', region.biome_key)
  if (region.intactness != null) params.set('intactness', region.intactness)
  const res = await fetch(`/api/v1/valuation?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(region.geojson),
  })
  if (!res.ok) {
    // Surface the backend's own validation message (e.g. zero-area geometry)
    // instead of a bare HTTP status, so search/paste mistakes are actionable.
    const detail = await res
      .json()
      .then((b) => b.detail)
      .catch(() => null)
    throw new Error(detail || `valuation HTTP ${res.status}`)
  }
  return res.json()
}

// On region click, confirm backend connectivity via GET /health, then value it.
// Connectivity and valuation are reported separately: a reachable backend that
// rejects a geometry must not masquerade as "backend offline".
async function onRegionSelect(region) {
  selectedRegion.value = region
  valuation.value = null
  errorMsg.value = ''
  loading.value = true
  try {
    const health = await fetch('/health').then((r) => r.json())
    backendOnline.value = health.status === 'ok'
  } catch (e) {
    backendOnline.value = false
    errorMsg.value = 'Could not reach the alpha backend. Is it running on :8000?'
    loading.value = false
    return
  }
  try {
    valuation.value = await fetchValuation(region)
  } catch (e) {
    errorMsg.value = e.message
      ? `Could not value this area: ${e.message}`
      : 'Could not value this area.'
  } finally {
    loading.value = false
  }
}

// Re-price the currently selected region when the currency changes.
async function setCurrency(code) {
  if (code === currency.value) return
  currency.value = code
  // Re-price the whole catalogue (map geometry is currency-independent, so the
  // maps don't rebuild — only the Compare numbers and a selected region update).
  loadRegions(code)
  if (!selectedRegion.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    valuation.value = await fetchValuation(selectedRegion.value)
  } catch (e) {
    errorMsg.value = 'Could not re-price in ' + code + '.'
  } finally {
    loading.value = false
  }
}

function closePanel() {
  selectedRegion.value = null
}
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="brand-logo" aria-hidden="true">
          <svg viewBox="0 0 32 32" width="30" height="30" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <clipPath id="logo-clip">
                <circle cx="16" cy="16" r="14.5"/>
              </clipPath>
            </defs>
            <!-- teal filled face (upper-left triangle) -->
            <polygon
              points="16,1.5 3,9 10,12.5"
              fill="var(--teal)"
              opacity="0.9"
              clip-path="url(#logo-clip)"
            />
            <!-- wireframe mesh -->
            <g
              stroke="rgba(203,213,225,0.55)"
              stroke-width="0.9"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
              clip-path="url(#logo-clip)"
            >
              <polygon points="16,1.5 29,9 29,23 16,30.5 3,23 3,9"/>
              <line x1="16" y1="1.5" x2="16" y2="9"/>
              <line x1="29" y1="9" x2="22" y2="12.5"/>
              <line x1="29" y1="23" x2="22" y2="19.5"/>
              <line x1="16" y1="30.5" x2="16" y2="23"/>
              <line x1="3" y1="23" x2="10" y2="19.5"/>
              <line x1="3" y1="9" x2="10" y2="12.5"/>
              <polygon points="16,9 22,12.5 22,19.5 16,23 10,19.5 10,12.5"/>
              <line x1="16" y1="9" x2="16" y2="16"/>
              <line x1="22" y1="12.5" x2="16" y2="16"/>
              <line x1="22" y1="19.5" x2="16" y2="16"/>
              <line x1="16" y1="23" x2="16" y2="16"/>
              <line x1="10" y1="19.5" x2="16" y2="16"/>
              <line x1="10" y1="12.5" x2="16" y2="16"/>
            </g>
            <!-- outer circle -->
            <circle cx="16" cy="16" r="14.5" stroke="rgba(203,213,225,0.55)" stroke-width="0.9" fill="none"/>
            <!-- teal equatorial line -->
            <line x1="1.5" y1="16" x2="30.5" y2="16" stroke="var(--teal)" stroke-width="1.1" opacity="0.85"/>
          </svg>
        </span>
        <span class="brand-text">
          <span class="brand-mark">alpha</span>
          <span class="brand-tag">putting nature on the balance sheet</span>
        </span>
      </div>
      <div class="controls">
        <div class="viewmode" role="group" aria-label="App mode">
          <button
            class="view-btn"
            :class="{ active: appMode === 'map' }"
            @click="appMode = 'map'"
          >
            ◍ Map
          </button>
          <button
            class="view-btn"
            :class="{ active: appMode === 'compare' }"
            @click="appMode = 'compare'"
          >
            ⊞ Compare
          </button>
          <button
            class="view-btn"
            :class="{ active: appMode === 'data' }"
            @click="appMode = 'data'"
          >
            ⛁ Data
          </button>
        </div>
        <div
          v-if="appMode === 'map'"
          class="viewmode"
          role="group"
          aria-label="Map view"
        >
          <button
            class="view-btn"
            :class="{ active: viewMode === '3d' }"
            @click="viewMode = '3d'"
          >
            ◐ Globe
          </button>
          <button
            class="view-btn"
            :class="{ active: viewMode === '2d' }"
            @click="viewMode = '2d'"
          >
            ▦ Flat
          </button>
        </div>
        <div class="currency" role="group" aria-label="Currency">
          <button
            v-for="c in CURRENCIES"
            :key="c"
            class="currency-btn"
            :class="{ active: c === currency }"
            @click="setCurrency(c)"
          >
            {{ c }}
          </button>
        </div>
        <button class="theme-toggle" @click="toggleTheme" :aria-label="isDark ? 'Switch to light theme' : 'Switch to dark theme'">
          <span class="toggle-icon">{{ isDark ? '☀' : '☾' }}</span>
          <span class="toggle-label">{{ isDark ? 'Light' : 'Dark' }}</span>
        </button>
      </div>
    </header>

    <main class="stage">
      <CompareDashboard
        v-if="appMode === 'compare'"
        :regions="regions"
        :show-liability="showLiability"
        :show-red-lines="showRedLines"
      />
      <DataHub v-else-if="appMode === 'data'" />

      <template v-else>
        <div v-if="!regionsLoaded && regionsLoading" class="stage-state">
          <span class="stage-spinner"></span>
          Loading ecosystem data…
        </div>
        <div v-else-if="regionsError" class="stage-state err">{{ regionsError }}</div>

        <template v-else>
          <GlobeMap
            v-if="viewMode === '3d'"
            :layers="biomeLayers"
            :regions="regions"
            :points="pointFeatures"
            :display-style="displayStyle"
            :visible-layers="visibleLayers"
            :is-dark="isDark"
            @select="onRegionSelect"
          />
          <WorldMap
            v-else
            :layers="biomeLayers"
            :regions="regions"
            :points="pointFeatures"
            :display-style="displayStyle"
            :visible-layers="visibleLayers"
            @select="onRegionSelect"
          />

          <LayerControl
            :layers="biomeLayers"
            :visible-layers="visibleLayers"
            :display-style="displayStyle"
            @toggle="toggleLayer"
            @set-style="displayStyle = $event"
          />

          <SearchBar @search="onRegionSelect" />

          <transition name="hint">
            <div v-if="!selectedRegion" class="hint" aria-hidden="true">
              <span class="hint-pulse"></span>
              <span class="hint-text">Select any ecosystem to reveal its Total Ecosystem Value</span>
            </div>
          </transition>

          <transition name="panel">
            <SidePanel
              v-if="selectedRegion"
              :region="selectedRegion"
              :valuation="valuation"
              :loading="loading"
              :backend-online="backendOnline"
              :error="errorMsg"
              v-model:show-liability="showLiability"
              v-model:show-systemic="showSystemic"
              v-model:show-red-lines="showRedLines"
              @close="closePanel"
            />
          </transition>
        </template>
      </template>
    </main>
  </div>
</template>

<style scoped>
.app {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.topbar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1300; /* above the side panel (1100) so the controls stay clickable */
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  pointer-events: none;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px 8px 10px;
  border-radius: 999px;
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  box-shadow: var(--shadow-soft);
  pointer-events: auto;
}

.brand-logo {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 25%, rgba(45, 212, 191, 0.22), transparent 70%);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.brand-mark {
  font-size: 1.22rem;
  font-weight: 800;
  letter-spacing: 0.3px;
  background: linear-gradient(92deg, var(--accent), var(--forest-overlay));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.brand-tag {
  font-size: 0.72rem;
  color: var(--text-muted);
  letter-spacing: 0.2px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px;
  border-radius: 999px;
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  box-shadow: var(--shadow-soft);
  pointer-events: auto;
}

.viewmode {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.view-btn {
  background: transparent;
  color: var(--text-muted);
  border: none;
  padding: 6px 12px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.3px;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.18s var(--ease), background 0.18s var(--ease);
}
.view-btn:hover {
  color: var(--text);
}
.view-btn.active {
  background: var(--bg-elevated);
  color: var(--accent);
  box-shadow: inset 0 0 0 1px var(--border);
}

.currency {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.currency-btn {
  background: transparent;
  color: var(--text-muted);
  border: none;
  padding: 6px 13px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.18s var(--ease), background 0.18s var(--ease);
}
.currency-btn:hover {
  color: var(--text);
}
.currency-btn.active {
  background: linear-gradient(180deg, var(--accent), var(--teal-strong));
  color: #04120c;
  box-shadow: 0 2px 10px rgba(45, 212, 191, 0.3);
}

.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  pointer-events: auto;
  background: var(--bg-deep);
  color: var(--text);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.18s var(--ease), color 0.18s var(--ease);
}
.theme-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.toggle-icon {
  font-size: 0.95rem;
  line-height: 1;
}

.stage {
  position: relative;
  flex: 1;
  min-height: 0;
}

/* Full-stage loading / error state while the region catalogue is fetched. */
.stage-state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 0.9rem;
  background: radial-gradient(circle at 50% 40%, #0a1424 0%, var(--bg) 70%);
}
.stage-state.err {
  color: #f87171;
}
.stage-spinner {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  animation: stage-spin 0.8s linear infinite;
}
@keyframes stage-spin {
  to {
    transform: rotate(360deg);
  }
}

/* Inviting call-to-action while no region is selected. */
.hint {
  position: absolute;
  left: 50%;
  bottom: 30px;
  transform: translateX(-50%);
  z-index: 1000;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px 10px 14px;
  border-radius: 999px;
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  box-shadow: var(--shadow-soft);
  color: var(--text-muted);
  font-size: 0.82rem;
  pointer-events: none;
  max-width: calc(100vw - 40px);
}
.hint-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hint-pulse {
  flex: none;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.6);
  animation: pulse 2s infinite var(--ease);
}
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(45, 212, 191, 0.55);
  }
  70% {
    box-shadow: 0 0 0 12px rgba(45, 212, 191, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(45, 212, 191, 0);
  }
}

.hint-enter-active,
.hint-leave-active {
  transition: opacity 0.4s var(--ease), transform 0.4s var(--ease);
}
.hint-enter-from,
.hint-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}

/* Side panel slide-in. */
.panel-enter-active,
.panel-leave-active {
  transition: transform 0.42s var(--ease), opacity 0.42s var(--ease);
}
.panel-enter-from,
.panel-leave-to {
  transform: translateX(28px);
  opacity: 0;
}

@media (max-width: 560px) {
  .brand-tag {
    display: none;
  }
  .toggle-label {
    display: none;
  }
}
</style>
