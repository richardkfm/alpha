<script setup>
import { ref, onMounted, defineAsyncComponent } from 'vue'
import WorldMap from './components/WorldMap.vue'
import SidePanel from './components/SidePanel.vue'
import LayerControl from './components/LayerControl.vue'
import { defaultVisibleLayers } from './data/layers.js'

// The MapLibre globe (and its ~heavy bundle) loads only when 3D mode is active.
const GlobeMap = defineAsyncComponent(() => import('./components/GlobeMap.vue'))

const selectedRegion = ref(null)
const valuation = ref(null)
const backendOnline = ref(null) // null = unknown, true/false once checked
const loading = ref(false)
const errorMsg = ref('')

// 2D Leaflet map vs 3D MapLibre globe. The globe is the hero view by default.
const viewMode = ref('3d')

// Thematic layer visibility, shared by both the 2D map and the 3D globe.
const visibleLayers = ref({ ...defaultVisibleLayers })
function toggleLayer(id) {
  visibleLayers.value = { ...visibleLayers.value, [id]: !visibleLayers.value[id] }
}

// Currency toggle (Phase 2). The backend converts USD reference values via FX.
const CURRENCIES = ['USD', 'EUR', 'BRL']
const currency = ref('USD')

// Dark is the default theme.
const isDark = ref(true)
function applyTheme() {
  document.documentElement.classList.toggle('light', !isDark.value)
}
function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme()
}
onMounted(applyTheme)

// Fetch the Phase 2 TEV breakdown for a region's polygon in the chosen currency.
async function fetchValuation(region) {
  const res = await fetch(`/api/v1/valuation?currency=${currency.value}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(region.geojson),
  })
  if (!res.ok) throw new Error(`valuation HTTP ${res.status}`)
  return res.json()
}

// On region click, confirm backend connectivity via GET /health, then value it.
async function onRegionSelect(region) {
  selectedRegion.value = region
  valuation.value = null
  errorMsg.value = ''
  loading.value = true
  try {
    const health = await fetch('/health').then((r) => r.json())
    backendOnline.value = health.status === 'ok'
    valuation.value = await fetchValuation(region)
  } catch (e) {
    backendOnline.value = false
    errorMsg.value = 'Could not reach the alpha backend. Is it running on :8000?'
  } finally {
    loading.value = false
  }
}

// Re-price the currently selected region when the currency changes.
async function setCurrency(code) {
  if (code === currency.value) return
  currency.value = code
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
          <svg viewBox="0 0 32 32" width="30" height="30">
            <defs>
              <linearGradient id="leafGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="var(--teal)" />
                <stop offset="1" stop-color="var(--forest-overlay)" />
              </linearGradient>
            </defs>
            <path
              d="M16 2C8.8 6 5 11.5 5 18.5 5 24.3 9.4 29 16 30c6.6-1 11-5.7 11-11.5C27 11.5 23.2 6 16 2Z"
              fill="url(#leafGrad)"
              opacity="0.18"
            />
            <path
              d="M16 4.5c-5.8 3.4-9 8-9 14 0 4.2 2.7 7.7 7 9.1V11.2a1 1 0 0 1 2 0v16.6c.66.1 1.33.16 2 .2V8.4a1 1 0 0 1 2 0v19.4c4.3-1.4 7-4.9 7-9.1 0-6-3.2-10.6-9-14Z"
              fill="url(#leafGrad)"
            />
          </svg>
        </span>
        <span class="brand-text">
          <span class="brand-mark">alpha</span>
          <span class="brand-tag">putting nature on the balance sheet</span>
        </span>
      </div>
      <div class="controls">
        <div class="viewmode" role="group" aria-label="Map view">
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
      <GlobeMap
        v-if="viewMode === '3d'"
        :visible-layers="visibleLayers"
        :is-dark="isDark"
        @select="onRegionSelect"
      />
      <WorldMap v-else :visible-layers="visibleLayers" @select="onRegionSelect" />

      <LayerControl :visible-layers="visibleLayers" @toggle="toggleLayer" />

      <transition name="hint">
        <div v-if="!selectedRegion" class="hint" aria-hidden="true">
          <span class="hint-pulse"></span>
          <span class="hint-text">Select a rainforest biome to reveal its Total Ecosystem Value</span>
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
          @close="closePanel"
        />
      </transition>
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
