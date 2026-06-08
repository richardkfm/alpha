<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  // Biome layer definitions and the region catalogue, both fetched from the
  // backend by the parent (see data/useRegions.js).
  layers: { type: Array, default: () => [] },
  regions: { type: Array, default: () => [] },
  visibleLayers: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['select'])
const mapEl = ref(null)
let map = null
const leafletLayers = {} // id -> L.GeoJSON

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
    if (props.visibleLayers[def.id]) gjLayer.addTo(map)
  })
})

function applyVisibility() {
  if (!map) return
  for (const def of props.layers) {
    const lyr = leafletLayers[def.id]
    if (!lyr) continue
    const shouldShow = !!props.visibleLayers[def.id]
    if (shouldShow && !map.hasLayer(lyr)) lyr.addTo(map)
    else if (!shouldShow && map.hasLayer(lyr)) map.removeLayer(lyr)
  }
}

watch(() => props.visibleLayers, applyVisibility, { deep: true })

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
