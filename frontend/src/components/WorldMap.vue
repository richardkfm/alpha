<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  // Biome layer definitions and the region catalogue, both fetched from the
  // backend by the parent (see data/useRegions.js).
  layers: { type: Array, default: () => [] },
  regions: { type: Array, default: () => [] },
  // Value-bubble points (FeatureCollection of Point).
  points: { type: Object, default: () => ({ type: 'FeatureCollection', features: [] }) },
  // 'polygons' | 'bubbles' | 'outline'
  displayStyle: { type: String, default: 'polygons' },
  visibleLayers: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['select'])
const mapEl = ref(null)
let map = null
const leafletLayers = {} // id -> L.GeoJSON
let bubbleLayer = null // L.LayerGroup of circle markers

onMounted(() => {
  map = L.map(mapEl.value, {
    center: [5, -20],
    zoom: 3,
    worldCopyJump: true,
    zoomControl: true,
  })

  // Dark basemap (CARTO) keeps the neon overlays as the focal point.
  L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }
  ).addTo(map)

  // Build one Leaflet layer per thematic layer from the shared registry, each
  // tinted with its own neon hue.
  props.layers.forEach((def) => {
    const baseStyle = {
      color: def.color,
      weight: 1.5,
      fillColor: def.color,
      fillOpacity: 0.22,
      className: 'region-overlay',
    }
    const hoverStyle = {
      fillOpacity: 0.5,
      weight: 2.5,
      className: 'region-overlay region-overlay--hover',
    }

    const gjLayer = L.geoJSON(def.geojson, {
      style: baseStyle,
      onEachFeature: (feature, lyr) => {
        const name = feature.properties?.name
        if (name) {
          lyr.bindTooltip(name, {
            sticky: true,
            direction: 'top',
            className: 'region-tooltip',
            offset: [0, -6],
          })
        }
        lyr.on('mouseover', () => lyr.setStyle(hoverStyle))
        lyr.on('mouseout', () => gjLayer.resetStyle(lyr))
        // Only the real biome layer is clickable -> drives valuation.
        if (def.kind === 'real') {
          lyr.on('click', () => {
            const region = props.regions.find((r) => r.id === feature.properties?.regionId)
            if (region) emit('select', region)
          })
        }
      },
    })
    leafletLayers[def.id] = gjLayer
  })

  applyStyle()
})

// Points filtered to the currently-visible biomes (drives bubbles).
function visiblePoints() {
  return (props.points.features || []).filter(
    (f) => props.visibleLayers[f.properties.biome_key],
  )
}

function rebuildBubbles() {
  if (bubbleLayer) {
    map.removeLayer(bubbleLayer)
    bubbleLayer = null
  }
  const markers = visiblePoints().map((f) => {
    const [lng, lat] = f.geometry.coordinates
    const p = f.properties
    const m = L.circleMarker([lat, lng], {
      radius: p.r,
      color: p.color,
      weight: 1.4,
      fillColor: p.color,
      fillOpacity: 0.4,
      className: 'region-overlay',
    })
    m.bindTooltip(p.name, { direction: 'top', className: 'region-tooltip', offset: [0, -4] })
    m.on('click', () => {
      const region = props.regions.find((r) => r.id === p.regionId)
      if (region) emit('select', region)
    })
    return m
  })
  bubbleLayer = L.layerGroup(markers)
}

// Reconcile all three styles: polygons and outline honour per-biome toggles;
// bubbles are rebuilt from visible points and added only when their style is on.
function applyStyle() {
  if (!map) return
  const style = props.displayStyle
  for (const def of props.layers) {
    const lyr = leafletLayers[def.id]
    if (!lyr) continue
    const show = (style === 'polygons' || style === 'outline') && !!props.visibleLayers[def.id]
    if (show && !map.hasLayer(lyr)) lyr.addTo(map)
    else if (!show && map.hasLayer(lyr)) map.removeLayer(lyr)
    if (show) {
      if (style === 'outline') {
        lyr.setStyle({ fillOpacity: 0, weight: 2.8, opacity: 1 })
      } else {
        lyr.setStyle({ fillOpacity: 0.22, weight: 1.5, opacity: 0.9 })
      }
    }
  }
  rebuildBubbles()
  if (style === 'bubbles') bubbleLayer.addTo(map)
}

watch(() => props.visibleLayers, applyStyle, { deep: true })
watch(() => props.displayStyle, applyStyle)
watch(() => props.points, applyStyle)

onBeforeUnmount(() => {
  if (map) map.remove()
})
</script>

<template>
  <div ref="mapEl" class="world-map"></div>
</template>

<style scoped>
.world-map {
  position: absolute;
  inset: 0;
  height: 100%;
  width: 100%;
  background: var(--bg);
}
/* ambient brand halo layered over the dark basemap */
.world-map::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--halo);
  pointer-events: none;
  z-index: 450;
}
</style>

<!-- Leaflet renders overlays, tooltips and controls outside this component's
     scoped tree, so these rules are intentionally global. -->
<style>
.region-overlay {
  transition: fill-opacity 0.25s var(--ease), stroke 0.25s var(--ease),
    stroke-width 0.25s var(--ease);
  cursor: pointer;
}
.region-overlay--hover {
  filter: drop-shadow(0 0 10px rgba(45, 212, 191, 0.55));
}

.region-tooltip.leaflet-tooltip {
  background: var(--bg-glass);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 5px 12px;
  font-family: "Inter", system-ui, sans-serif;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.2px;
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
.region-tooltip.leaflet-tooltip::before {
  display: none; /* drop the default pointer caret for a cleaner pill */
}

/* Leaflet zoom + attribution chrome, themed. */
.leaflet-control-zoom a {
  background: var(--bg-glass) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease);
}
.leaflet-control-zoom a:hover {
  color: var(--accent) !important;
  border-color: var(--accent) !important;
}
.leaflet-bar {
  border-radius: var(--radius-sm) !important;
  overflow: hidden;
  box-shadow: var(--shadow-soft) !important;
}
.leaflet-control-attribution {
  background: var(--bg-glass) !important;
  color: var(--text-faint) !important;
  border-radius: 8px 0 0 0;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.leaflet-control-attribution a {
  color: var(--text-muted) !important;
}
</style>
