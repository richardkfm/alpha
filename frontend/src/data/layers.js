// alpha — shared thematic layer registry.
//
// Single source of truth for the map layers, consumed by BOTH the 2D Leaflet
// map (WorldMap.vue) and the 3D MapLibre globe (GlobeMap.vue) so the layer
// toggles behave identically in either mode.
//
// `kind`:
//   'real'        — backed by real (if coarse) data; clicking values the region.
//   'placeholder' — illustrative sample geometry, clearly badged in the UI.
//                   Wired into the toggle system now, ready to swap for real
//                   datasets (soil grids, hydrology, etc.) later.
//
// Palette is deliberately techie/neon (multi-hue), not "all green".

import { rainforests } from './rainforests.js'

// Biome layer — REAL. Reuse the rainforest polygons; carry `regionId` so a click
// on the globe/map resolves back to the full region metadata for valuation.
const rainforestFeatures = rainforests.map((r) => ({
  type: 'Feature',
  properties: { regionId: r.id, name: r.name },
  geometry: r.geojson,
}))

// Helper: a coarse rectangular footprint [west, south, east, north] -> polygon.
// Used only for the illustrative placeholder layers.
function box(w, s, e, n, props) {
  return {
    type: 'Feature',
    properties: props,
    geometry: {
      type: 'Polygon',
      coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    },
  }
}

// Water layer — PLACEHOLDER. Coarse footprints over well-known freshwater /
// wetland systems. Illustrative only.
const waterFeatures = [
  box(-60, -20, -55, -16, { name: 'Pantanal wetlands' }),
  box(-95, 32, -88, 40, { name: 'Mississippi basin' }),
  box(104, 9, 107, 11, { name: 'Mekong delta' }),
  box(29, 0, 34, 4, { name: 'Lake Victoria basin' }),
  box(60, 55, 70, 62, { name: 'West Siberian wetlands' }),
]

// Soil layer — PLACEHOLDER. Coarse footprints over major soil / breadbasket
// belts. Illustrative only.
const soilFeatures = [
  box(-100, 38, -90, 45, { name: 'North American prairie soils' }),
  box(28, 47, 40, 52, { name: 'Ukrainian chernozem belt' }),
  box(74, 25, 86, 30, { name: 'Indo-Gangetic plain' }),
  box(-65, -36, -58, -32, { name: 'Pampas' }),
  box(10, 12, 25, 16, { name: 'Sahel cropland' }),
]

function fc(features) {
  return { type: 'FeatureCollection', features }
}

// Order = render + legend order. `defaultOn` controls initial visibility.
export const layers = [
  {
    id: 'rainforest',
    label: 'Rainforests',
    sublabel: 'biome boundaries',
    kind: 'real',
    color: '#2dd4bf', // teal
    defaultOn: true,
    geojson: fc(rainforestFeatures),
  },
  {
    id: 'water',
    label: 'Water',
    sublabel: 'freshwater & wetlands',
    kind: 'placeholder',
    color: '#38bdf8', // electric blue
    defaultOn: false,
    geojson: fc(waterFeatures),
  },
  {
    id: 'soil',
    label: 'Soil',
    sublabel: 'soil & nutrient belts',
    kind: 'placeholder',
    color: '#f5b14e', // amber
    defaultOn: false,
    geojson: fc(soilFeatures),
  },
]

// Convenience: initial { id: bool } visibility map for App-level state.
export const defaultVisibleLayers = Object.fromEntries(
  layers.map((l) => [l.id, l.defaultOn]),
)
