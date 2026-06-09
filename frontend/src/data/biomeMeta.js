// alpha — per-biome display metadata.
//
// Single source of truth for the map-overlay palette and the layer-toggle
// labels, keyed by the backend `biome_key` (see backend/reference_data.BIOMES).
// The palette is deliberately a techie multi-hue neon set (not "all green") so
// the five biomes read as distinct data layers on the globe and the flat map.

// `short` is the compact chip label used where space is tight (LayerControl);
// the full label + sublabel still travel along for tooltips and panels.
export const BIOME_META = {
  tropical_rainforest: {
    label: 'Tropical Rainforest',
    short: 'Rainforest',
    sublabel: 'tropical moist broadleaf',
    color: '#2dd4bf', // teal
  },
  mangrove: {
    label: 'Mangrove',
    short: 'Mangrove',
    sublabel: 'blue-carbon coastal',
    color: '#38bdf8', // electric blue
  },
  wetland: {
    label: 'Inland Wetland',
    short: 'Wetland',
    sublabel: 'freshwater & flooded',
    color: '#818cf8', // indigo
  },
  temperate_forest: {
    label: 'Temperate Forest',
    short: 'Temperate',
    sublabel: 'broadleaf & conifer',
    color: '#a3e635', // lime
  },
  temperate_grassland: {
    label: 'Temperate Grassland',
    short: 'Grassland',
    sublabel: 'steppe & prairie',
    color: '#f5b14e', // amber
  },
  boreal_forest: {
    label: 'Boreal Forest',
    short: 'Boreal',
    sublabel: 'northern taiga',
    color: '#10b981', // emerald
  },
  cropland: {
    label: 'Cropland & Agriculture',
    short: 'Cropland',
    sublabel: 'farmland & managed crops',
    color: '#fb923c', // orange
  },
  freshwater: {
    label: 'Freshwater',
    short: 'Freshwater',
    sublabel: 'lakes, rivers & reservoirs',
    color: '#22d3ee', // cyan
  },
  peri_urban: {
    label: 'Peri-urban Land',
    short: 'Peri-urban',
    sublabel: 'urban fringe & managed open',
    color: '#f472b6', // magenta
  },
  tundra: {
    label: 'Tundra',
    short: 'Tundra',
    sublabel: 'arctic & alpine',
    color: '#9fb6c2', // icy grey-blue
  },
  desert: {
    label: 'Desert & Xeric',
    short: 'Desert',
    sublabel: 'deserts & dry shrubland',
    color: '#c2a878', // sand / khaki
  },
}

// Render + legend order for the layers and the Compare picker.
export const BIOME_ORDER = [
  'tropical_rainforest',
  'boreal_forest',
  'temperate_forest',
  'mangrove',
  'wetland',
  'freshwater',
  'temperate_grassland',
  'cropland',
  'peri_urban',
  'tundra',
  'desert',
]

export function biomeColor(key) {
  return BIOME_META[key]?.color ?? '#2dd4bf'
}

export function biomeLabel(key) {
  return BIOME_META[key]?.label ?? key
}
