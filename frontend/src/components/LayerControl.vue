<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  // Biome layer definitions derived from the backend catalogue (useRegions.js).
  layers: { type: Array, default: () => [] },
  visibleLayers: { type: Object, required: true },
  // Active map display style: 'polygons' | 'bubbles' | 'outline'.
  displayStyle: { type: String, default: 'polygons' },
  // True while the selected style's data is still arriving (Outline lazy-loads
  // the detailed ecoregion borders), so the button can say so.
  styleLoading: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle', 'set-all', 'set-style'])
const { t } = useI18n()

// On a phone the open panel covers most of the globe, so start it collapsed
// there; on desktop it starts open so the display styles are discoverable.
const collapsed = ref(typeof window !== 'undefined' && window.innerWidth < 720)

const STYLES = computed(() => [
  { id: 'polygons', label: t('layerControl.style.polygons.label'), icon: '▦', hint: t('layerControl.style.polygons.hint') },
  { id: 'bubbles', label: t('layerControl.style.bubbles.label'), icon: '⦿', hint: t('layerControl.style.bubbles.hint') },
  { id: 'outline', label: t('layerControl.style.outline.label'), icon: '□', hint: t('layerControl.style.outline.hint') },
])

// One-line explanation of the active style, so what the bubbles/outlines
// encode is visible without hovering.
const activeHint = computed(() => STYLES.value.find((s) => s.id === props.displayStyle)?.hint ?? '')

const onCount = computed(
  () => props.layers.filter((l) => props.visibleLayers[l.id]).length,
)
const allOn = computed(() => onCount.value === props.layers.length)

function chipTitle(l) {
  return t('layerControl.chipTitle', { label: l.label, sublabel: l.sublabel, count: l.count }, l.count)
}
</script>

<template>
  <aside class="layers" :class="{ collapsed }" :aria-label="t('layerControl.ariaLabel')">
    <header class="layers-head">
      <button
        class="collapse-btn"
        :aria-expanded="!collapsed"
        aria-controls="layer-body"
        :title="collapsed ? t('layerControl.expand') : t('layerControl.collapse')"
        @click="collapsed = !collapsed"
      >
        <span class="caret" aria-hidden="true">▾</span>
        <span class="layers-title">
          {{ t('layerControl.title') }}
          <span class="layers-count num">{{ onCount }}/{{ layers.length }}</span>
        </span>
      </button>
      <button v-if="!collapsed" class="bulk-btn" @click="emit('set-all', !allOn)">
        {{ allOn ? t('layerControl.hideAll') : t('layerControl.showAll') }}
      </button>
    </header>

    <div v-show="!collapsed" id="layer-body">
    <div class="chips">
      <button
        v-for="l in layers"
        :key="l.id"
        class="chip"
        :class="{ on: visibleLayers[l.id] }"
        :style="{ '--c': l.color }"
        role="switch"
        :aria-checked="!!visibleLayers[l.id]"
        :title="chipTitle(l)"
        @click="emit('toggle', l.id)"
      >
        <span class="chip-dot"></span>
        <span class="chip-label">{{ l.short || l.label }}</span>
        <span class="chip-count num">{{ l.count }}</span>
      </button>
    </div>

    <span class="style-heading">{{ t('layerControl.styleGroup') }}</span>
    <div class="style-switch" role="group" :aria-label="t('layerControl.styleGroup')">
      <button
        v-for="s in STYLES"
        :key="s.id"
        class="style-btn"
        :class="{ on: displayStyle === s.id }"
        :aria-pressed="displayStyle === s.id"
        :title="s.hint"
        @click="emit('set-style', s.id)"
      >
        <span
          v-if="styleLoading && displayStyle === s.id"
          class="spinner spinner-xs"
          aria-hidden="true"
        ></span>
        <span v-else class="style-icon" aria-hidden="true">{{ s.icon }}</span>{{ s.label }}
      </button>
    </div>
    <p class="style-hint" aria-live="polite">
      {{ styleLoading ? t('layerControl.styleLoading') : activeHint }}
    </p>
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
  max-height: calc(100% - var(--topbar-h) - 90px);
  overflow-y: auto;
  padding: var(--space-3);
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-soft);
  transition: width 0.25s var(--ease);
}
.layers.collapsed {
  width: auto;
}

.layers-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.layers:not(.collapsed) .layers-head {
  margin-bottom: 10px;
}
.collapse-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px 2px 0;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.caret {
  display: inline-block;
  font-size: 0.7rem;
  color: var(--text-muted);
  transition: transform 0.2s var(--ease);
}
.layers.collapsed .caret {
  transform: rotate(-90deg);
}
.collapse-btn:hover .caret {
  color: var(--accent);
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

.style-heading {
  display: block;
  margin: var(--space-3) 2px 6px;
  font-size: var(--fs-2xs);
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--text-faint);
}
.style-hint {
  margin: 6px 2px 0;
  font-size: var(--fs-2xs);
  line-height: 1.4;
  color: var(--text-muted);
}
.spinner-xs {
  width: 11px;
  height: 11px;
  border-width: 1.5px;
}
.style-switch {
  display: flex;
  gap: 2px;
  padding: 3px;
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
/* Phones: sit clear of the basemap attribution strip along the bottom edge. */
@media (max-width: 860px) {
  .layers {
    left: 12px;
    bottom: 40px;
  }
}
.style-icon {
  font-size: 0.85rem;
  line-height: 1;
}
</style>
