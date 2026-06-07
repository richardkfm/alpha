<script setup>
import { ref, onMounted } from 'vue'
import WorldMap from './components/WorldMap.vue'
import SidePanel from './components/SidePanel.vue'

const selectedRegion = ref(null)
const valuation = ref(null)
const backendOnline = ref(null) // null = unknown, true/false once checked
const loading = ref(false)
const errorMsg = ref('')

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
        <span class="brand-mark">alpha</span>
        <span class="brand-tag">putting nature on the balance sheet</span>
      </div>
      <div class="controls">
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
        <button class="theme-toggle" @click="toggleTheme">
          {{ isDark ? '☀ Light' : '☾ Dark' }}
        </button>
      </div>
    </header>

    <main class="stage">
      <WorldMap @select="onRegionSelect" />
      <SidePanel
        v-if="selectedRegion"
        :region="selectedRegion"
        :valuation="valuation"
        :loading="loading"
        :backend-online="backendOnline"
        :error="errorMsg"
        @close="closePanel"
      />
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
  padding: 12px 18px;
  background: linear-gradient(180deg, rgba(11, 20, 17, 0.92), rgba(11, 20, 17, 0));
  pointer-events: none;
}

.brand {
  display: flex;
  align-items: baseline;
  gap: 12px;
  pointer-events: auto;
}

.brand-mark {
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: var(--accent);
}

.brand-tag {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  pointer-events: auto;
}

.currency {
  display: inline-flex;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 999px;
  overflow: hidden;
}
.currency-btn {
  background: transparent;
  color: var(--text-muted);
  border: none;
  padding: 6px 12px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}
.currency-btn:hover {
  color: var(--text);
}
.currency-btn.active {
  background: var(--accent);
  color: #07120d;
}

.theme-toggle {
  pointer-events: auto;
  background: var(--bg-elevated);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}
.theme-toggle:hover {
  border-color: var(--accent);
}

.stage {
  position: relative;
  flex: 1;
  min-height: 0;
}
</style>
