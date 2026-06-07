<script setup>
import { ref, onMounted } from 'vue'
import WorldMap from './components/WorldMap.vue'
import SidePanel from './components/SidePanel.vue'

const selectedRegion = ref(null)
const valuation = ref(null)
const backendOnline = ref(null) // null = unknown, true/false once checked
const loading = ref(false)
const errorMsg = ref('')

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

// Per spec: on region click, confirm backend connectivity via GET /health,
// then fetch the mock TEV breakdown for that region's polygon.
async function onRegionSelect(region) {
  selectedRegion.value = region
  valuation.value = null
  errorMsg.value = ''
  loading.value = true
  try {
    const health = await fetch('/health').then((r) => r.json())
    backendOnline.value = health.status === 'ok'

    const res = await fetch('/api/v1/valuation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(region.geojson),
    })
    if (!res.ok) throw new Error(`valuation HTTP ${res.status}`)
    valuation.value = await res.json()
  } catch (e) {
    backendOnline.value = false
    errorMsg.value = 'Could not reach the alpha backend. Is it running on :8000?'
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
      <button class="theme-toggle" @click="toggleTheme">
        {{ isDark ? '☀ Light' : '☾ Dark' }}
      </button>
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
  z-index: 1000;
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
