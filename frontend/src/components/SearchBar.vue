<script setup>
import { ref } from 'vue'
import { parseAreaInput } from '../data/geo.js'

const emit = defineEmits(['search'])

const query = ref('')
const error = ref('')
const open = ref(false)

function submit() {
  error.value = ''
  try {
    const { geometry, label } = parseAreaInput(query.value)
    emit('search', {
      id: 'custom',
      name: label,
      region: 'Custom area — valued on demand',
      geojson: geometry,
    })
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="search" :class="{ open }">
    <form class="search-row" @submit.prevent="submit">
      <span class="search-icon" aria-hidden="true">⌖</span>
      <input
        v-model="query"
        class="search-input"
        type="text"
        placeholder="Value any area — lat, lng or paste GeoJSON"
        aria-label="Search for an area to value"
        @focus="open = true"
        @input="error = ''"
      />
      <button class="search-go" type="submit">Value</button>
      <button
        v-if="query"
        class="search-clear"
        type="button"
        aria-label="Clear"
        @click="query = ''; error = ''"
      >×</button>
    </form>
    <transition name="fade">
      <div v-if="error" class="search-msg err">{{ error }}</div>
      <div v-else-if="open" class="search-msg hint">
        Try <code>-3.1, -60.0</code>, a box <code>-65, -6, -60, -2</code>, or a GeoJSON Polygon.
      </div>
    </transition>
  </div>
</template>

<style scoped>
.search {
  position: absolute;
  top: 74px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  width: min(520px, calc(100vw - 36px));
  pointer-events: auto;
}
.search-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 6px 6px 14px;
  border-radius: 999px;
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  box-shadow: var(--shadow-soft);
}
.search-icon {
  color: var(--accent);
  font-size: 1rem;
}
.search-input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 0.85rem;
}
.search-input::placeholder {
  color: var(--text-faint);
}
.search-go {
  flex: none;
  padding: 7px 16px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(180deg, var(--accent), var(--teal-strong));
  color: #04120c;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.18s var(--ease);
}
.search-go:hover {
  opacity: 0.92;
}
.search-clear {
  flex: none;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid var(--border-soft);
  background: var(--bg-deep);
  color: var(--text-muted);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}
.search-clear:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.search-msg {
  margin: 7px 14px 0;
  font-size: 0.72rem;
  line-height: 1.4;
}
.search-msg.hint {
  color: var(--text-faint);
}
.search-msg.hint code {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  color: var(--text-muted);
  background: var(--bg-glass);
  padding: 1px 5px;
  border-radius: 5px;
}
.search-msg.err {
  color: #f7a8a8;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s var(--ease);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
