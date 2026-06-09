<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

const props = defineProps({
  // Biome layer definitions and the region catalogue, both fetched from the
  // backend by the parent (see data/useRegions.js).
  layers: { type: Array, default: () => [] },
  regions: { type: Array, default: () => [] },
  // Value-bubble / heat points (FeatureCollection of Point) for the non-polygon
  // display styles.
  points: { type: Object, default: () => ({ type: 'FeatureCollection', features: [] }) },
  // 'polygons' | 'bubbles' | 'heat'
  displayStyle: { type: String, default: 'polygons' },
  visibleLayers: { type: Object, required: true },
  isDark: { type: Boolean, default: true },
})
const emit = defineEmits(['select'])

const mapEl = ref(null)
const spinning = ref(true)
let map = null
let rafId = null
let lastTs = 0
let interacting = false
let resumeTimer = null

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
  // Value bubbles + heat share a single points source (one Point per region).
  if (!map.getSource('region-points')) {
    map.addSource('region-points', { type: 'geojson', data: visiblePointData(), promoteId: 'regionId' })
  }
  map.addLayer({
    id: 'region-heat',
    type: 'heatmap',
    source: 'region-points',
    paint: {
      'heatmap-weight': ['get', 'wt'],
      'heatmap-intensity': 2.0,
      'heatmap-radius': 48,
      'heatmap-opacity': 0.92,
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(5,7,13,0)',
        0.1, 'rgba(56,189,248,0.7)',
        0.35, 'rgba(45,212,191,0.85)',
        0.6, 'rgba(163,230,53,0.95)',
        1, 'rgba(245,177,78,1)',
      ],
    },
  })
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

  applyVisibility()
}

// Points filtered to the currently-visible biomes (drives bubbles + heat).
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

// Visibility is the product of the active display style and the per-biome
// toggles: polygons honour both; bubbles/heat are filtered via the source data.
function applyVisibility() {
  if (!map) return
  const polysOn = props.displayStyle === 'polygons'
  for (const l of props.layers) {
    const v = polysOn && props.visibleLayers[l.id] ? 'visible' : 'none'
    for (const suffix of ['-glow', '-fill', '-line']) {
      const id = l.id + suffix
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', v)
    }
  }
  if (map.getLayer('region-bubbles')) {
    map.setLayoutProperty('region-bubbles', 'visibility', props.displayStyle === 'bubbles' ? 'visible' : 'none')
  }
  if (map.getLayer('region-heat')) {
    map.setLayoutProperty('region-heat', 'visibility', props.displayStyle === 'heat' ? 'visible' : 'none')
  }
  updatePoints()
}

// ----- auto-spin -----------------------------------------------------------
function frame(ts) {
  if (map) {
    const dt = lastTs ? (ts - lastTs) / 1000 : 0
    lastTs = ts
    if (spinning.value && !interacting && map.getZoom() < 3.6) {
      const c = map.getCenter()
      c.lng -= dt * 3.2 // ~deg/sec -> a full revolution in ~110s
      map.jumpTo({ center: c })
    }
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
