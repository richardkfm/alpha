<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { centroid } from '../data/geo.js'
import { biomeColor } from '../data/biomeMeta.js'

const props = defineProps({
  // Biome layer definitions and the region catalogue, both fetched from the
  // backend by the parent (see data/useRegions.js).
  layers: { type: Array, default: () => [] },
  regions: { type: Array, default: () => [] },
  // Value-bubble points (FeatureCollection of Point) for the bubbles display style.
  points: { type: Object, default: () => ({ type: 'FeatureCollection', features: [] }) },
  // 'polygons' | 'bubbles' | 'outline'
  displayStyle: { type: String, default: 'polygons' },
  visibleLayers: { type: Object, required: true },
  isDark: { type: Boolean, default: true },
  // The region currently open in the side panel (or null). Drives the 3D
  // "value column" that rises off the globe when an ecosystem is selected.
  selected: { type: Object, default: null },
})
const emit = defineEmits(['select'])

const mapEl = ref(null)
const spinning = ref(true)
// Mirrors whether a value column is currently raised — gates the caption + spin.
const selectionActive = ref(false)
let map = null
let rafId = null
let lastTs = 0
let interacting = false
let resumeTimer = null
let hasSelection = false

// ----- 3D value column + living textures -----------------------------------
const EMPTY_FC = { type: 'FeatureCollection', features: [] }
// Height range (metres) the selected region rises to, scaled by its annual TEV.
// Tuned to read clearly against the globe at the focus zoom without skewering it.
const COLUMN_MIN_H = 70000
const COLUMN_MAX_H = 540000
// Eased height tween: `h` chases `target` every frame so the column rises and
// settles smoothly rather than popping in.
const column = { h: 0, target: 0, color: '#2dd4bf' }

// How much each biome's overlay "breathes" — lush, wet biomes pulse a little
// more; arid and frozen ones are nearly still. Deliberately subtle throughout.
const BIOME_VITALITY = {
  tropical_rainforest: 1.0,
  mangrove: 0.85,
  wetland: 0.8,
  freshwater: 0.9,
  temperate_forest: 0.7,
  boreal_forest: 0.55,
  temperate_grassland: 0.6,
  cropland: 0.5,
  peri_urban: 0.35,
  tundra: 0.3,
  desert: 0.25,
}
const WATER_BIOMES = new Set(['mangrove', 'wetland', 'freshwater'])
let lastLifeTs = 0

function clamp(v, lo, hi) {
  return v < lo ? lo : v > hi ? hi : v
}

const CARTO_ATTR =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'

function tilesFor(dark) {
  const set = dark ? 'dark_nolabels' : 'light_nolabels'
  return ['a', 'b', 'c', 'd'].map(
    (s) => `https://${s}.basemaps.cartocdn.com/${set}/{z}/{x}/{y}.png`,
  )
}

function skyFor(dark) {
  // Glowing atmosphere rim — cyan/blue leaning for a techie, not-natural feel.
  return dark
    ? {
        'sky-color': '#0a1422',
        'sky-horizon-blend': 0.5,
        'horizon-color': '#163a5e',
        'horizon-fog-blend': 0.6,
        'fog-color': '#091523',
        'fog-ground-blend': 0.4,
      }
    : {
        'sky-color': '#cfe6f5',
        'sky-horizon-blend': 0.5,
        'horizon-color': '#9fc4dd',
        'horizon-fog-blend': 0.6,
        'fog-color': '#dbeaf2',
        'fog-ground-blend': 0.4,
      }
}

function buildStyle(dark) {
  return {
    version: 8,
    projection: { type: 'globe' },
    sources: {
      basemap: {
        type: 'raster',
        tiles: tilesFor(dark),
        tileSize: 256,
        attribution: CARTO_ATTR,
      },
    },
    layers: [
      { id: 'space', type: 'background', paint: { 'background-color': dark ? '#05070d' : '#dfeaf0' } },
      {
        id: 'basemap',
        type: 'raster',
        source: 'basemap',
        paint: { 'raster-opacity': dark ? 0.9 : 0.95, 'raster-fade-duration': 300 },
      },
    ],
  }
}

function addThematicLayers() {
  for (const l of props.layers) {
    const srcId = `layer-${l.id}`
    if (!map.getSource(srcId)) {
      map.addSource(srcId, { type: 'geojson', data: l.geojson, promoteId: 'regionId' })
    }
    // soft outer glow (under), translucent fill, crisp neon outline (over)
    map.addLayer({
      id: `${l.id}-glow`,
      type: 'line',
      source: srcId,
      paint: { 'line-color': l.color, 'line-width': 7, 'line-blur': 7, 'line-opacity': 0.45 },
    })
    map.addLayer({
      id: `${l.id}-fill`,
      type: 'fill',
      source: srcId,
      paint: { 'fill-color': l.color, 'fill-opacity': 0.16 },
    })
    map.addLayer({
      id: `${l.id}-line`,
      type: 'line',
      source: srcId,
      paint: { 'line-color': l.color, 'line-width': 1.4, 'line-opacity': 0.9 },
    })

    // Every biome layer is real -> clicking any region drives its valuation.
    if (l.kind === 'real') {
      const fillId = `${l.id}-fill`
      map.on('click', fillId, (e) => {
        const f = e.features && e.features[0]
        if (!f) return
        const region = props.regions.find((r) => r.id === f.properties.regionId)
        if (region) emit('select', region)
      })
      map.on('mouseenter', fillId, () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', fillId, () => {
        map.getCanvas().style.cursor = ''
      })
    }
  }
  // Value bubbles use a single points source (one Point per region).
  if (!map.getSource('region-points')) {
    map.addSource('region-points', { type: 'geojson', data: visiblePointData(), promoteId: 'regionId' })
  }
  map.addLayer({
    id: 'region-bubbles',
    type: 'circle',
    source: 'region-points',
    paint: {
      'circle-radius': ['get', 'r'],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.45,
      'circle-stroke-color': ['get', 'color'],
      'circle-stroke-width': 1.4,
      'circle-stroke-opacity': 0.95,
    },
  })
  map.on('click', 'region-bubbles', (e) => {
    const f = e.features && e.features[0]
    if (!f) return
    const region = props.regions.find((r) => r.id === f.properties.regionId)
    if (region) emit('select', region)
  })
  map.on('mouseenter', 'region-bubbles', () => {
    map.getCanvas().style.cursor = 'pointer'
  })
  map.on('mouseleave', 'region-bubbles', () => {
    map.getCanvas().style.cursor = ''
  })

  addSelectionLayers()
  applyVisibility()
  // If a region was already selected before the style finished loading, raise it.
  if (props.selected) updateSelection(props.selected)
}

// The selected region becomes a luminous 3D column — its height encodes the
// Total Ecosystem Value, making the balance-sheet metaphor literal. A bright
// footprint ring keeps the selection legible even where extrusions aren't drawn.
function addSelectionLayers() {
  if (!map.getSource('selected-src')) {
    map.addSource('selected-src', { type: 'geojson', data: EMPTY_FC })
  }
  try {
    map.addLayer({
      id: 'selected-extrusion',
      type: 'fill-extrusion',
      source: 'selected-src',
      paint: {
        'fill-extrusion-color': column.color,
        'fill-extrusion-height': 0,
        'fill-extrusion-base': 0,
        'fill-extrusion-opacity': 0.55,
        'fill-extrusion-vertical-gradient': true,
      },
    })
  } catch (_) {
    /* fill-extrusion unsupported on this build — the ring still marks it */
  }
  map.addLayer({
    id: 'selected-ring',
    type: 'line',
    source: 'selected-src',
    paint: {
      'line-color': column.color,
      'line-width': 2.4,
      'line-opacity': 0.95,
      'line-blur': 0.4,
    },
  })
}

// 0..1 prominence for a region's column, from its annual TEV vs the catalogue
// max (sqrt-compressed so mid-value regions still read). Custom search areas
// carry no pre-computed value, so they rise to a neutral mid height.
function valueWeight(region) {
  const v = region?.total_ecosystem_value_per_year
  if (v == null) return 0.5
  const max = Math.max(...props.regions.map((r) => r.total_ecosystem_value_per_year || 0), 1)
  return clamp(Math.sqrt(v) / Math.sqrt(max), 0, 1)
}

// Raise (or lower) the value column to match the selected region, and tilt the
// camera so the column reads as 3D. Passing null lowers and clears it.
function updateSelection(region) {
  if (!map || !map.getSource('selected-src')) return
  const geom = region && (region.geojson || region.geometry)
  if (!geom) {
    hasSelection = false
    selectionActive.value = false
    column.target = 0 // tween down; the source clears once it bottoms out
    try {
      map.easeTo({ pitch: 0, duration: 900, essential: true })
    } catch (_) {
      /* ignore */
    }
    return
  }

  column.color = biomeColor(region.biome_key)
  if (map.getLayer('selected-extrusion')) {
    map.setPaintProperty('selected-extrusion', 'fill-extrusion-color', column.color)
  }
  map.setPaintProperty('selected-ring', 'line-color', column.color)
  map.getSource('selected-src').setData({
    type: 'FeatureCollection',
    features: [{ type: 'Feature', properties: {}, geometry: geom }],
  })
  column.target = COLUMN_MIN_H + valueWeight(region) * (COLUMN_MAX_H - COLUMN_MIN_H)

  hasSelection = true
  selectionActive.value = true
  const c = centroid(geom)
  if (c) {
    try {
      map.easeTo({
        center: c,
        zoom: Math.max(map.getZoom(), 2.7),
        pitch: 52,
        duration: 1300,
        essential: true,
      })
    } catch (_) {
      /* ignore */
    }
  }
}

// Frame-rate-independent easing of the column height toward its target.
function tweenColumn(dt) {
  if (!map.getLayer('selected-extrusion')) return
  const k = Math.min(1, dt * 5.5)
  const next = column.h + (column.target - column.h) * k
  // Snap-and-clear once a lowering column has effectively bottomed out.
  if (column.target === 0 && next < 200) {
    if (column.h !== 0) {
      column.h = 0
      map.setPaintProperty('selected-extrusion', 'fill-extrusion-height', 0)
      const src = map.getSource('selected-src')
      if (src) src.setData(EMPTY_FC)
    }
    return
  }
  if (Math.abs(next - column.h) >= 1) {
    column.h = next
    map.setPaintProperty('selected-extrusion', 'fill-extrusion-height', Math.max(0, next))
  }
}

// Subtle "life": breathe each visible biome overlay on a slow sine, offset per
// biome so they shimmer out of phase (alive, not a synchronised global flash).
// Wet biomes get a faint faster harmonic suggesting moving water. Throttled to
// ~18fps so the paint-property churn stays cheap.
function updateBiomeLife(ts) {
  if (props.displayStyle === 'bubbles') return
  if (ts - lastLifeTs < 55) return
  lastLifeTs = ts
  const t = ts / 1000
  const fill = props.displayStyle === 'polygons'
  let i = 0
  for (const l of props.layers) {
    if (!props.visibleLayers[l.id]) {
      i++
      continue
    }
    const vit = BIOME_VITALITY[l.id] ?? 0.5
    const phase = i * 0.7
    const breath = Math.sin(t * 0.5 + phase)
    const shimmer = WATER_BIOMES.has(l.id) ? Math.sin(t * 1.7 + phase) : 0
    if (map.getLayer(`${l.id}-glow`)) {
      const o = 0.45 + vit * 0.1 * breath + 0.04 * shimmer
      map.setPaintProperty(`${l.id}-glow`, 'line-opacity', clamp(o, 0.2, 0.7))
    }
    if (fill && map.getLayer(`${l.id}-fill`)) {
      const o = 0.16 * (1 + vit * 0.22 * breath + 0.1 * shimmer)
      map.setPaintProperty(`${l.id}-fill`, 'fill-opacity', clamp(o, 0.07, 0.26))
    }
    i++
  }
}

// Points filtered to the currently-visible biomes (drives bubbles).
function visiblePointData() {
  return {
    type: 'FeatureCollection',
    features: (props.points.features || []).filter(
      (f) => props.visibleLayers[f.properties.biome_key],
    ),
  }
}

function updatePoints() {
  const src = map && map.getSource('region-points')
  if (src) src.setData(visiblePointData())
}

// Visibility is the product of the active display style and the per-biome toggles.
function applyVisibility() {
  if (!map) return
  const style = props.displayStyle
  for (const l of props.layers) {
    const show = (style === 'polygons' || style === 'outline') && props.visibleLayers[l.id]
    const v = show ? 'visible' : 'none'
    if (map.getLayer(`${l.id}-glow`)) map.setLayoutProperty(`${l.id}-glow`, 'visibility', v)
    if (map.getLayer(`${l.id}-line`)) {
      map.setLayoutProperty(`${l.id}-line`, 'visibility', v)
      map.setPaintProperty(`${l.id}-line`, 'line-width', style === 'outline' ? 2.5 : 1.4)
      map.setPaintProperty(`${l.id}-line`, 'line-opacity', style === 'outline' ? 1.0 : 0.9)
    }
    if (map.getLayer(`${l.id}-fill`)) {
      map.setLayoutProperty(`${l.id}-fill`, 'visibility', v)
      map.setPaintProperty(`${l.id}-fill`, 'fill-opacity', style === 'outline' ? 0 : 0.16)
    }
  }
  if (map.getLayer('region-bubbles')) {
    map.setLayoutProperty('region-bubbles', 'visibility', style === 'bubbles' ? 'visible' : 'none')
  }
  updatePoints()
}

// ----- auto-spin -----------------------------------------------------------
function frame(ts) {
  if (map) {
    const dt = lastTs ? (ts - lastTs) / 1000 : 0
    lastTs = ts
    // Auto-spin idles while the user interacts or a region is focused in 3D.
    if (spinning.value && !interacting && !hasSelection && map.getZoom() < 3.6) {
      const c = map.getCenter()
      c.lng -= dt * 3.2 // ~deg/sec -> a full revolution in ~110s
      map.jumpTo({ center: c })
    }
    tweenColumn(dt)
    updateBiomeLife(ts)
  }
  rafId = requestAnimationFrame(frame)
}

function pauseSpinTemporarily() {
  interacting = true
  if (resumeTimer) clearTimeout(resumeTimer)
  resumeTimer = setTimeout(() => {
    interacting = false
  }, 2800)
}

function toggleSpin() {
  spinning.value = !spinning.value
}

function updateTheme() {
  if (!map) return
  const src = map.getSource('basemap')
  if (src && src.setTiles) src.setTiles(tilesFor(props.isDark))
  if (map.getLayer('space')) {
    map.setPaintProperty('space', 'background-color', props.isDark ? '#05070d' : '#dfeaf0')
  }
  if (map.getLayer('basemap')) {
    map.setPaintProperty('basemap', 'raster-opacity', props.isDark ? 0.9 : 0.95)
  }
  try {
    map.setSky(skyFor(props.isDark))
  } catch (_) {
    /* setSky unsupported on this build — ignore */
  }
}

onMounted(() => {
  map = new maplibregl.Map({
    container: mapEl.value,
    style: buildStyle(props.isDark),
    center: [-30, 12],
    zoom: 1.6,
    minZoom: 0.5,
    maxZoom: 7,
    attributionControl: { compact: true },
    dragRotate: false,
  })

  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

  // Pause auto-spin while the user is interacting, resume after a short idle.
  for (const ev of ['mousedown', 'touchstart', 'wheel', 'dragstart', 'zoomstart']) {
    map.on(ev, pauseSpinTemporarily)
  }

  map.on('load', () => {
    try {
      map.setProjection({ type: 'globe' })
    } catch (_) {
      /* older builds read projection from the style */
    }
    try {
      map.setSky(skyFor(props.isDark))
    } catch (_) {
      /* ignore */
    }
    addThematicLayers()
  })

  rafId = requestAnimationFrame(frame)
})

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
  if (resumeTimer) clearTimeout(resumeTimer)
  if (map) map.remove()
})

watch(() => props.visibleLayers, applyVisibility, { deep: true })
watch(() => props.displayStyle, applyVisibility)
watch(() => props.points, updatePoints)
watch(() => props.isDark, updateTheme)
watch(() => props.selected, (region) => updateSelection(region))
</script>

<template>
  <div class="globe-wrap">
    <div ref="mapEl" class="globe"></div>
    <button
      class="spin-toggle"
      :class="{ active: spinning }"
      @click="toggleSpin"
      :title="spinning ? 'Pause rotation' : 'Resume rotation'"
    >
      <span class="spin-dot"></span>
      {{ spinning ? 'Spinning' : 'Paused' }}
    </button>
    <transition name="cap">
      <div v-if="selectionActive" class="column-cap" aria-hidden="true">
        <span class="column-cap-bar"></span>
        Column height = annual ecosystem value
      </div>
    </transition>
  </div>
</template>

<style scoped>
.globe-wrap {
  position: absolute;
  inset: 0;
}
.globe {
  position: absolute;
  inset: 0;
  height: 100%;
  width: 100%;
  background: radial-gradient(circle at 50% 40%, #0a1424 0%, var(--space, #05070d) 70%);
}

.spin-toggle {
  position: absolute;
  left: 18px;
  top: 74px;
  z-index: 900;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 13px;
  border-radius: 999px;
  background: var(--bg-glass);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.3px;
  cursor: pointer;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: var(--shadow-soft);
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.spin-toggle:hover {
  color: var(--text);
  border-color: var(--accent);
}
.spin-toggle.active {
  color: var(--accent);
}
.spin-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 8px currentColor;
}
.spin-toggle.active .spin-dot {
  animation: spin-pulse 1.6s infinite var(--ease);
}
@keyframes spin-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

/* Explains the 3D column metaphor while a region is raised. */
.column-cap {
  position: absolute;
  left: 18px;
  bottom: 30px;
  z-index: 900;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 8px 14px;
  border-radius: 999px;
  background: var(--bg-glass);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.2px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: var(--shadow-soft);
  pointer-events: none;
}
.column-cap-bar {
  width: 8px;
  height: 16px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--accent), transparent);
  box-shadow: 0 0 8px var(--accent);
}
.cap-enter-active,
.cap-leave-active {
  transition: opacity 0.4s var(--ease), transform 0.4s var(--ease);
}
.cap-enter-from,
.cap-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>

<!-- MapLibre renders controls/popups outside the scoped tree -> global theming. -->
<style>
.maplibregl-ctrl-group {
  background: var(--bg-glass) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft) !important;
  overflow: hidden;
}
.maplibregl-ctrl-group button {
  background: transparent !important;
}
.maplibregl-ctrl-group button + button {
  border-top: 1px solid var(--border-soft) !important;
}
.maplibregl-ctrl-group button .maplibregl-ctrl-icon {
  filter: invert(0.85) hue-rotate(120deg);
}
.maplibregl-ctrl-attrib {
  background: var(--bg-glass) !important;
  color: var(--text-faint) !important;
  border-radius: 8px 0 0 0;
}
.maplibregl-ctrl-attrib a {
  color: var(--text-muted) !important;
}
.maplibregl-ctrl-attrib-button {
  filter: invert(0.8);
}
</style>
