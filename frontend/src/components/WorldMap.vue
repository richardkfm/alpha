<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { rainforests } from '../data/rainforests.js'

const emit = defineEmits(['select'])
const mapEl = ref(null)
let map = null

onMounted(() => {
  map = L.map(mapEl.value, {
    center: [5, -20],
    zoom: 3,
    worldCopyJump: true,
    zoomControl: true,
  })

  // Dark basemap (CARTO) keeps the green overlays as the focal point.
  L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }
  ).addTo(map)

  const baseStyle = {
    color: '#22c55e',
    weight: 1.5,
    fillColor: '#22c55e',
    fillOpacity: 0.28,
    className: 'region-overlay',
  }
  const hoverStyle = {
    fillOpacity: 0.55,
    weight: 2.5,
    color: '#2dd4bf',
    className: 'region-overlay region-overlay--hover',
  }

  rainforests.forEach((region) => {
    const layer = L.geoJSON(region.geojson, { style: baseStyle })
    layer.bindTooltip(region.name, {
      sticky: true,
      direction: 'top',
      className: 'region-tooltip',
      offset: [0, -6],
    })
    layer.on('mouseover', () => layer.setStyle(hoverStyle))
    layer.on('mouseout', () => layer.setStyle(baseStyle))
    layer.on('click', () => emit('select', region))
    layer.addTo(map)
  })
})

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
