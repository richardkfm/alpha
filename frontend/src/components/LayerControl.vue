<script setup>
import { computed } from 'vue'

const props = defineProps({
  // Biome layer definitions derived from the backend catalogue (useRegions.js).
  layers: { type: Array, default: () => [] },
  visibleLayers: { type: Object, required: true },
  // Active map display style: 'polygons' | 'bubbles' | 'outline'.
  displayStyle: { type: String, default: 'polygons' },
})
const emit = defineEmits(['toggle', 'set-all', 'set-style'])

const STYLES = [
  { id: 'polygons', label: 'Fill', icon: '▦', hint: 'Filled biome polygons' },
  { id: 'bubbles', label: 'Bubbles', icon: '⦿', hint: 'Bubble size = annual ecosystem value' },
  { id: 'outline', label: 'Outline', icon: '□', hint: 'Detailed ecoregion borders, no fill' },
]

const onCount = computed(
  () => props.layers.filter((l) => props.visibleLayers[l.id]).length,
)
const allOn = computed(() => onCount.value === props.layers.length)
</script>

<template>
  <aside class="layers" aria-label="Biome layers">
    <header class="layers-head">
      <span class="layers-title">
        Biomes
        <span class="layers-count num">{{ onCount }}/{{ layers.length }}</span>
      </span>
      <button class="bulk-btn" @click="emit('set-all', !allOn)">
        {{ allOn ? 'Hide all' : 'Show all' }}
      </button>
    </header>

    <div class="chips">
      <button
        v-for="l in layers"
        :key="l.id"
        class="chip"
        :class="{ on: visibleLayers[l.id] }"
        :style="{ '--c': l.color }"
        role="switch"
        :aria-checked="!!visibleLayers[l.id]"
        :title="`${l.label} — ${l.sublabel} · ${l.count} region${l.count === 1 ? '' : 's'}`"
        @click="emit('toggle', l.id)"
      >
        <span class="chip-dot"></span>
        <span class="chip-label">{{ l.short || l.label }}</span>
        <span class="chip-count num">{{ l.count }}</span>
      </button>
    </div>

    <div class="style-switch" role="group" aria-label="Display style">
      <button
        v-for="s in STYLES"
        :key="s.id"
        class="style-btn"
        :class="{ on: displayStyle === s.id }"
        :title="s.hint"
        @click="emit('set-style', s.id)"
      >
        <span class="style-icon" aria-hidden="true">{{ s.icon }}</span>{{ s.label }}
      </button>
    </div>
  </aside>
</template>

<style scoped>
.layers {
  position: absolute;
  left: 18px;
  bottom: 22px;
  z-index: 1000;
  width: 264px;
  max-width: calc(100vw - 36px);
  max-height: calc(100vh - 90px);
  overflow-y: auto;
  padding: 13px 13px 11px;
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  box-shadow: var(--shadow-soft);
}

.layers-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.layers-title {
  display: inline-flex;
  align-items: baseline;
  gap: 7px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--text);
}
.layers-count {
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--text-faint);
}
.bulk-btn {
  border: 1px solid var(--border-soft);
  background: var(--bg-deep);
  color: var(--text-muted);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.3px;
  padding: 3px 9px;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.bulk-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.chips {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}
.chip {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  padding: 7px 9px;
  border-radius: 999px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  color: var(--text-muted);
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s var(--ease), background 0.18s var(--ease),
    color 0.18s var(--ease), transform 0.12s var(--ease);
}
.chip:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--c) 45%, var(--border));
}
.chip:active {
  transform: translateY(0);
}
.chip.on {
  color: var(--text);
  border-color: color-mix(in srgb, var(--c) 55%, transparent);
  background: color-mix(in srgb, var(--c) 12%, var(--bg-deep));
}

.chip-dot {
  flex: none;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--c);
  opacity: 0.35;
  transition: opacity 0.18s var(--ease), box-shadow 0.18s var(--ease);
}
.chip.on .chip-dot {
  opacity: 1;
  box-shadow: 0 0 8px var(--c);
}

.chip-label {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.chip-count {
  margin-left: auto;
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--text-faint);
}
.chip.on .chip-count {
  color: color-mix(in srgb, var(--c) 75%, var(--text));
}

.style-switch {
  display: flex;
  gap: 2px;
  padding: 3px;
  margin-top: 10px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.style-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 6px 4px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.2px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.18s var(--ease), background 0.18s var(--ease);
}
.style-btn:hover {
  color: var(--text);
}
.style-btn.on {
  background: var(--bg-elevated);
  color: var(--accent);
  box-shadow: inset 0 0 0 1px var(--border);
}
.style-icon {
  font-size: 0.85rem;
  line-height: 1;
}
</style>
