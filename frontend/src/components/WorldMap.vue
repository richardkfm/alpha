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
    weight: 2,
    fillColor: '#22c55e',
    fillOpacity: 0.35,
  }
  const hoverStyle = { fillOpacity: 0.6, weight: 3, color: '#2dd4bf' }

  rainforests.forEach((region) => {
    const layer = L.geoJSON(region.geojson, { style: baseStyle })
    layer.bindTooltip(region.name, { sticky: true })
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
</style>
