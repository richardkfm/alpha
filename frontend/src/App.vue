<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'
import WorldMap from './components/WorldMap.vue'
import SidePanel from './components/SidePanel.vue'
import LayerControl from './components/LayerControl.vue'
import SearchBar from './components/SearchBar.vue'
import BrandLogo from './components/BrandLogo.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import OnboardingGuide from './components/OnboardingGuide.vue'
import { useRegions } from './data/useRegions.js'
import { serviceCeilings } from './data/yieldScale.js'
import { version as frontendVersion } from '../package.json'

const { t } = useI18n()

// Tiny build/version footer so a deployed instance can be confirmed at a
// glance instead of guessed at. The frontend version is bundled at build time
// from package.json; the backend version comes from /health, so a mismatch
// (mid-deploy, or a stale cached frontend) is visible rather than silent.
const backendVersion = ref(null)

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
  ecoLayers,
  pointFeatures,
  loading: regionsLoading,
  error: regionsError,
  loaded: regionsLoaded,
  load: loadRegions,
  ecoLoading,
  ecoLoaded,
  loadEcoregions,
} = useRegions()

// Per-service cross-biome ceilings (max across the catalogue), so yield bars in
// the side panel and Compare dashboard show magnitude vs the strongest biome
// rather than maxing out the dominant service of every region. Re-priced
// catalogue ⇒ ceilings track the active currency, matching the values they scale.
const serviceMax = computed(() => serviceCeilings(regions.value))

// When Outline mode is active use the detailed ecoregion geometry (lazy-loaded
// on first use). All other modes use the lightweight catalogue geometry.
const activeLayers = computed(() =>
  displayStyle.value === 'outline' ? ecoLayers.value : biomeLayers.value
)

watch(displayStyle, (style) => {
  if (style === 'outline') loadEcoregions()
})

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
function setAllLayers(on) {
  visibleLayers.value = Object.fromEntries(biomeLayers.value.map((l) => [l.id, on]))
}

// Currency toggle (Phase 2). The backend converts USD reference values via FX.
const CURRENCIES = ['USD', 'EUR', 'BRL']
const currency = ref('USD')

// Dark is the default theme; an explicit choice is remembered per browser.
// Storage can be unavailable (private mode, blocked site data), so every access
// is guarded and the app simply falls back to the default.
const THEME_KEY = 'alpha-theme'
function readStored(key) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}
function writeStored(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    /* storage unavailable — the choice just isn't remembered */
  }
}
const isDark = ref(readStored(THEME_KEY) !== 'light')

// First-run orientation: a short guide shown until it is dismissed once, and
// re-openable from the "?" button in the topbar.
const GUIDE_KEY = 'alpha-guide-seen'
const showGuide = ref(readStored(GUIDE_KEY) !== '1')
function closeGuide() {
  showGuide.value = false
  writeStored(GUIDE_KEY, '1')
}
function goToMode(mode) {
  closeGuide()
  appMode.value = mode
}

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
  writeStored(THEME_KEY, isDark.value ? 'dark' : 'light')
  applyTheme()
}

// Esc dismisses the top-most layer: the guide first, then the side panel. The
// panel itself never steals focus, so a global listener keeps the map
// interactions uninterrupted. The search input handles its own Esc.
function onKeydown(e) {
  if (e.key !== 'Escape') return
  if (showGuide.value) closeGuide()
  else if (selectedRegion.value && appMode.value === 'map') closePanel()
}

function retryRegions() {
  loadRegions(currency.value).then(syncLayerVisibility)
}

onMounted(async () => {
  applyTheme()
  window.addEventListener('keydown', onKeydown)
  fetch('/health')
    .then((r) => r.json())
    .then((h) => { backendVersion.value = h.version || null })
    .catch(() => {})
  await loadRegions(currency.value)
  syncLayerVisibility()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

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
    errorMsg.value = t('errors.backendUnreachable')
    loading.value = false
    return
  }
  try {
    valuation.value = await fetchValuation(region)
  } catch (e) {
    errorMsg.value = e.message
      ? t('errors.valuationFailed', { message: e.message })
      : t('errors.valuationFailedGeneric')
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
    errorMsg.value = t('errors.repriceFailed', { code })
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
          <BrandLogo :size="34" />
        </span>
        <span class="brand-text">
          <span class="brand-mark">alpha</span>
          <span class="brand-tag">{{ t('brand.tagline') }}</span>
        </span>
      </div>
      <div class="controls">
        <div class="viewmode" role="group" :aria-label="t('nav.appMode')">
          <button
            class="view-btn"
            :class="{ active: appMode === 'map' }"
            :aria-pressed="appMode === 'map'"
            :title="t('nav.mapHint')"
            @click="appMode = 'map'"
          >
            <span class="btn-icon" aria-hidden="true">◍</span>{{ t('nav.map') }}
          </button>
          <button
            class="view-btn"
            :class="{ active: appMode === 'compare' }"
            :aria-pressed="appMode === 'compare'"
            :title="t('nav.compareHint')"
            @click="appMode = 'compare'"
          >
            <span class="btn-icon" aria-hidden="true">⊞</span>{{ t('nav.compare') }}
          </button>
          <button
            class="view-btn"
            :class="{ active: appMode === 'data' }"
            :aria-pressed="appMode === 'data'"
            :title="t('nav.dataHint')"
            @click="appMode = 'data'"
          >
            <span class="btn-icon" aria-hidden="true">⛁</span>{{ t('nav.data') }}
          </button>
        </div>
        <div
          v-if="appMode === 'map'"
          class="viewmode"
          role="group"
          :aria-label="t('nav.mapView')"
        >
          <button
            class="view-btn"
            :class="{ active: viewMode === '3d' }"
            :aria-pressed="viewMode === '3d'"
            :title="t('nav.globeHint')"
            @click="viewMode = '3d'"
          >
            <span class="btn-icon" aria-hidden="true">◐</span>{{ t('nav.globe') }}
          </button>
          <button
            class="view-btn"
            :class="{ active: viewMode === '2d' }"
            :aria-pressed="viewMode === '2d'"
            :title="t('nav.flatHint')"
            @click="viewMode = '2d'"
          >
            <span class="btn-icon" aria-hidden="true">▦</span>{{ t('nav.flat') }}
          </button>
        </div>
        <div class="currency" role="group" :aria-label="t('currency.group')">
          <button
            v-for="c in CURRENCIES"
            :key="c"
            class="currency-btn"
            :class="{ active: c === currency }"
            :aria-pressed="c === currency"
            @click="setCurrency(c)"
          >
            {{ c }}
          </button>
        </div>
        <LanguageSwitcher />
        <button
          class="theme-toggle"
          @click="toggleTheme"
          :aria-label="isDark ? t('theme.switchToLight') : t('theme.switchToDark')"
          :title="isDark ? t('theme.switchToLight') : t('theme.switchToDark')"
        >
          <span class="toggle-icon" aria-hidden="true">{{ isDark ? '☀' : '☾' }}</span>
          <span class="toggle-label">{{ isDark ? t('theme.light') : t('theme.dark') }}</span>
        </button>
        <button
          class="help-btn"
          :class="{ active: showGuide }"
          :aria-label="t('guide.open')"
          :title="t('guide.open')"
          @click="showGuide = true"
        >?</button>
      </div>
    </header>

    <main class="stage">
      <transition name="view" mode="out-in">
        <CompareDashboard
          v-if="appMode === 'compare'"
          key="compare"
          :regions="regions"
          :ceilings="serviceMax"
          :show-liability="showLiability"
          :show-red-lines="showRedLines"
          :loading="regionsLoading && !regionsLoaded"
          :error="regionsLoaded ? '' : regionsError"
          @retry="retryRegions"
        />
        <DataHub v-else-if="appMode === 'data'" key="data" />

        <div v-else key="map" class="map-view" :class="{ 'has-panel': !!selectedRegion }">
        <div v-if="!regionsLoaded && regionsLoading" class="stage-state" role="status">
          <span class="spinner" aria-hidden="true"></span>
          {{ t('stage.loading') }}
        </div>
        <div v-else-if="regionsError && !regionsLoaded" class="stage-state">
          <div class="state-card" role="alert">
            <span class="state-icon" aria-hidden="true">!</span>
            <h2 class="state-title">{{ t('stage.errorTitle') }}</h2>
            <p class="state-body">{{ regionsError }}</p>
            <p class="state-hint">{{ t('stage.errorHint') }}</p>
            <button class="state-retry" :disabled="regionsLoading" @click="retryRegions">
              {{ regionsLoading ? t('stage.retrying') : t('stage.retry') }}
            </button>
          </div>
        </div>

        <template v-else>
          <GlobeMap
            v-if="viewMode === '3d'"
            :layers="activeLayers"
            :regions="regions"
            :points="pointFeatures"
            :display-style="displayStyle"
            :visible-layers="visibleLayers"
            :is-dark="isDark"
            :selected="selectedRegion"
            @select="onRegionSelect"
          />
          <WorldMap
            v-else
            :layers="activeLayers"
            :regions="regions"
            :points="pointFeatures"
            :display-style="displayStyle"
            :visible-layers="visibleLayers"
            :is-dark="isDark"
            @select="onRegionSelect"
          />

          <LayerControl
            :layers="biomeLayers"
            :visible-layers="visibleLayers"
            :display-style="displayStyle"
            :style-loading="displayStyle === 'outline' && ecoLoading"
            @toggle="toggleLayer"
            @set-all="setAllLayers"
            @set-style="displayStyle = $event"
          />

          <SearchBar @search="onRegionSelect" />

          <transition name="hint">
            <div v-if="!selectedRegion && !showGuide" class="hint" aria-hidden="true">
              <span class="hint-pulse"></span>
              <span class="hint-text">{{ t('stage.hint') }}</span>
            </div>
          </transition>

          <transition name="panel">
            <SidePanel
              v-if="selectedRegion"
              :region="selectedRegion"
              :valuation="valuation"
              :ceilings="serviceMax"
              :loading="loading"
              :backend-online="backendOnline"
              :error="errorMsg"
              v-model:show-liability="showLiability"
              v-model:show-systemic="showSystemic"
              v-model:show-red-lines="showRedLines"
              @close="closePanel"
              @retry="onRegionSelect(selectedRegion)"
            />
          </transition>
        </template>
        </div>
      </transition>
    </main>

    <transition name="guide">
      <OnboardingGuide v-if="showGuide" @close="closeGuide" @go="goToMode" />
    </transition>

    <!-- Non-blocking notice when a re-price fails after the catalogue loaded:
         the map keeps the last good figures instead of being replaced. -->
    <transition name="toast">
      <div v-if="regionsError && regionsLoaded" class="toast" role="status">
        <span class="toast-dot" aria-hidden="true"></span>
        <span>{{ t('stage.refreshFailed') }}</span>
        <button class="toast-btn" :disabled="regionsLoading" @click="retryRegions">
          {{ t('stage.retry') }}
        </button>
      </div>
    </transition>

    <div class="build-footer" :title="backendVersion ? `frontend v${frontendVersion} · backend v${backendVersion}` : `frontend v${frontendVersion}`">
      v{{ frontendVersion }}<template v-if="backendVersion && backendVersion !== frontendVersion"> · api v{{ backendVersion }}</template>
    </div>
  </div>
</template>


<style scoped>
.app {
  position: relative;
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
  gap: var(--space-4);
  padding: 14px 18px;
  pointer-events: none;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: none;
  padding: 8px 16px 8px 10px;
  border-radius: var(--radius-pill);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-soft);
  pointer-events: auto;
}

.brand-logo {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  color: var(--text); /* geodesic mesh strokes inherit this */
  background: radial-gradient(circle at 30% 25%, var(--accent-bg), transparent 70%);
  transition: transform 0.5s var(--ease);
}
.brand:hover .brand-logo {
  transform: rotate(14deg);
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
  font-size: var(--fs-xs);
  color: var(--text-muted);
  letter-spacing: 0.2px;
}

.controls {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  padding: 6px;
  border-radius: var(--radius-pill);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-soft);
  pointer-events: auto;
}

/* Segmented controls (mode, map view, currency) share one look with the
   language switcher and the layer panel's display-style switch. */
.viewmode,
.currency {
  display: inline-flex;
  flex: none;
  gap: 2px;
  padding: 3px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-pill);
}
.view-btn,
.currency-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--text-muted);
  border: none;
  padding: 6px 12px;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.3px;
  white-space: nowrap;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: color 0.18s var(--ease), background 0.18s var(--ease);
}
.btn-icon {
  font-size: 0.85rem;
  line-height: 1;
}
.view-btn:hover,
.currency-btn:hover {
  color: var(--text);
}
.view-btn.active {
  background: var(--bg-elevated);
  color: var(--accent);
  box-shadow: inset 0 0 0 1px var(--border);
}
.currency-btn.active {
  background: linear-gradient(180deg, var(--accent), var(--teal-strong));
  color: var(--on-accent);
  box-shadow: 0 2px 10px var(--accent-bg);
}

.theme-toggle,
.help-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  gap: 7px;
  pointer-events: auto;
  background: var(--bg-deep);
  color: var(--text);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-pill);
  padding: 7px 14px;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.18s var(--ease), color 0.18s var(--ease);
}
.help-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  font-weight: 800;
}
.theme-toggle:hover,
.help-btn:hover,
.help-btn.active {
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
.map-view {
  position: absolute;
  inset: 0;
}
/* With the side panel open, keep the search bar centred over the visible map
   rather than half-hidden under the panel. (On phones the panel covers the
   whole map anyway.) */
@media (min-width: 861px) {
  .map-view.has-panel :deep(.search) {
    left: calc((100% - min(420px, 94vw)) / 2);
    /* 300px leaves room for the spin toggle / zoom buttons on either side. */
    width: min(520px, calc(100% - min(420px, 94vw) - 300px));
  }
}

/* Full-stage loading / error state while the region catalogue is fetched. */
.stage-state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--topbar-h) var(--space-4) var(--space-4);
  color: var(--text-muted);
  font-size: var(--fs-md);
  background: var(--stage-bg);
}
.state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  max-width: 420px;
  padding: var(--space-6);
  text-align: center;
  border-radius: var(--radius-lg);
  background: var(--bg-glass);
  border: 1px solid var(--danger-border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-soft);
}
.state-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-weight: 900;
  font-size: 1.2rem;
  color: var(--danger);
  background: var(--danger-bg);
  border: 1px solid var(--danger-border);
}
.state-title {
  margin: var(--space-1) 0 0;
  font-size: var(--fs-lg);
  font-weight: 800;
  color: var(--text);
}
.state-body {
  margin: 0;
  font-size: var(--fs-md);
  line-height: 1.5;
  color: var(--text-muted);
}
.state-hint {
  margin: 0;
  font-size: var(--fs-xs);
  line-height: 1.5;
  color: var(--text-faint);
}
.state-retry {
  margin-top: var(--space-2);
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
.state-retry:disabled {
  opacity: 0.6;
  cursor: progress;
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
  border-radius: var(--radius-pill);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
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
  box-shadow: 0 0 0 0 var(--accent-border);
  animation: pulse 2s infinite var(--ease);
}
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 var(--accent-border);
  }
  70% {
    box-shadow: 0 0 0 12px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
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

/* Guide fade. */
.guide-enter-active,
.guide-leave-active {
  transition: opacity 0.3s var(--ease);
}
.guide-enter-from,
.guide-leave-to {
  opacity: 0;
}

/* Re-price failure notice. */
.toast {
  position: absolute;
  left: 50%;
  bottom: 84px;
  transform: translateX(-50%);
  z-index: 1250;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  max-width: calc(100vw - 32px);
  padding: 8px 8px 8px 14px;
  border-radius: var(--radius-pill);
  background: var(--bg-glass);
  border: 1px solid var(--danger-border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-soft);
  color: var(--text);
  font-size: var(--fs-sm);
}
.toast-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger);
}
.toast-btn {
  flex: none;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-soft);
  background: var(--bg-deep);
  color: var(--accent);
  font: inherit;
  font-size: var(--fs-xs);
  font-weight: 700;
  cursor: pointer;
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s var(--ease), transform 0.3s var(--ease);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}

/* Narrower desktops: drop the decorative labels before anything wraps. */
@media (max-width: 1180px) {
  .toggle-label,
  .btn-icon {
    display: none;
  }
  .theme-toggle {
    width: 34px;
    height: 34px;
    padding: 0;
  }
}
@media (max-width: 1040px) {
  .brand-tag {
    display: none;
  }
}

/* Phones / small tablets: the brand gets its own row and the controls become a
   single horizontally scrollable strip, so nothing is cut off. */
@media (max-width: 860px) {
  .app {
    --topbar-h: 118px;
    --map-ctrl-top: 178px; /* below the search bar, which shares the row on desktop */
  }
  .topbar {
    flex-wrap: wrap;
    gap: var(--space-2);
    padding: 10px 12px;
  }
  .brand {
    padding: 4px 12px 4px 6px;
  }
  .brand-logo {
    width: 32px;
    height: 32px;
  }
  .controls {
    width: 100%;
    overflow-x: auto;
    scrollbar-width: none;
    border-radius: var(--radius);
  }
  .controls::-webkit-scrollbar {
    display: none;
  }
  .hint {
    bottom: 96px; /* above the collapsed Biomes panel */
    font-size: var(--fs-xs);
  }
}

.build-footer {
  position: absolute;
  left: 10px;
  bottom: 6px;
  z-index: 1000;
  font-size: 0.66rem;
  letter-spacing: 0.2px;
  color: var(--text-muted);
  opacity: 0.55;
  pointer-events: none;
  user-select: none;
}
</style>
