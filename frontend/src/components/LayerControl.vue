<script setup>
defineProps({
  // Biome layer definitions derived from the backend catalogue (useRegions.js).
  layers: { type: Array, default: () => [] },
  visibleLayers: { type: Object, required: true },
  // Active map display style: 'polygons' | 'bubbles' | 'heat'.
  displayStyle: { type: String, default: 'polygons' },
})
defineEmits(['toggle', 'set-style'])

const STYLES = [
  { id: 'polygons', label: 'Polygons', icon: '▦' },
  { id: 'bubbles', label: 'Bubbles', icon: '⦿' },
  { id: 'heat', label: 'Heat', icon: '◍' },
]
</script>

<template>
  <aside class="layers" aria-label="Map layers">
    <header class="layers-head">
      <span class="layers-title">Layers</span>
      <span class="layers-hint">toggle data overlays</span>
    </header>

    <div class="style-switch" role="group" aria-label="Display style">
      <button
        v-for="s in STYLES"
        :key="s.id"
        class="style-btn"
        :class="{ on: displayStyle === s.id }"
        @click="$emit('set-style', s.id)"
      >
        <span class="style-icon">{{ s.icon }}</span>{{ s.label }}
      </button>
    </div>
    <p v-if="displayStyle !== 'polygons'" class="style-note">
      {{ displayStyle === 'bubbles' ? 'Bubble size' : 'Heat' }} = annual ecosystem value
    </p>

    <ul>
      <li v-for="l in layers" :key="l.id">
        <button
          class="layer-row"
          :class="{ on: visibleLayers[l.id] }"
          role="switch"
          :aria-checked="!!visibleLayers[l.id]"
          @click="$emit('toggle', l.id)"
        >
          <span class="swatch" :style="{ '--c': l.color }"></span>
          <span class="layer-text">
            <span class="layer-label">
              {{ l.label }}
              <span v-if="l.kind === 'placeholder'" class="badge">sample</span>
            </span>
            <span class="layer-sub">{{ l.sublabel }}</span>
          </span>
          <span class="switch" :style="{ '--c': l.color }"><span class="knob"></span></span>
        </button>
      </li>
    </ul>
  </aside>
</template>

<style scoped>
.layers {
  position: absolute;
  left: 18px;
  bottom: 22px;
  z-index: 1000;
  width: 248px;
  max-width: calc(100vw - 36px);
  padding: 14px;
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  box-shadow: var(--shadow-soft);
}

.layers-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}
.layers-title {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--text);
}
.layers-hint {
  font-size: 0.66rem;
  color: var(--text-faint);
}

.style-switch {
  display: flex;
  gap: 2px;
  padding: 3px;
  margin-bottom: 8px;
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
.style-note {
  margin: 0 0 10px;
  font-size: 0.66rem;
  color: var(--text-faint);
  text-align: center;
}

.layers ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.layer-row {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s var(--ease), background 0.18s var(--ease);
}
.layer-row:hover {
  border-color: var(--border);
}
.layer-row.on {
  border-color: color-mix(in srgb, var(--c, var(--accent)) 55%, transparent);
  background: color-mix(in srgb, var(--c, var(--accent)) 9%, var(--bg-deep));
}

.swatch {
  flex: none;
  width: 12px;
  height: 12px;
  border-radius: 4px;
  background: var(--c);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08) inset;
  opacity: 0.4;
  transition: opacity 0.18s var(--ease), box-shadow 0.18s var(--ease);
}
.layer-row.on .swatch {
  opacity: 1;
  box-shadow: 0 0 10px var(--c);
}

.layer-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-right: auto;
  min-width: 0;
}
.layer-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.84rem;
  font-weight: 600;
}
.layer-sub {
  font-size: 0.66rem;
  color: var(--text-faint);
}
.badge {
  font-size: 0.56rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 1px 5px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
}

.switch {
  flex: none;
  position: relative;
  width: 34px;
  height: 19px;
  border-radius: 999px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  transition: background 0.2s var(--ease), border-color 0.2s var(--ease);
}
.layer-row.on .switch {
  background: color-mix(in srgb, var(--c, var(--accent)) 75%, transparent);
  border-color: var(--c, var(--accent));
}
.knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: var(--text);
  opacity: 0.7;
  transition: transform 0.2s var(--ease), opacity 0.2s var(--ease);
}
.layer-row.on .knob {
  transform: translateX(15px);
  opacity: 1;
  background: #05120e;
}
</style>
