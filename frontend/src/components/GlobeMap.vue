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

// ----- living surface for the raised column --------------------------------
// The single highlighted column gets a procedurally-animated surface keyed to
// its biome: water ripples with foam, sand drifts in the wind, forest canopy
// dapples, grass gusts, tundra twinkles, peri-urban scans. Generated as one
// shared StyleImage that MapLibre re-uploads each frame — no image assets, and
// only ever one object animates at a time (only the selected column uses it).
const TEXTURE_FAMILY = {
  tropical_rainforest: 'forest',
  temperate_forest: 'forest',
  boreal_forest: 'forest',
  mangrove: 'water',
  wetland: 'water',
  freshwater: 'water',
  temperate_grassland: 'grass',
  cropland: 'grass',
  desert: 'sand',
  tundra: 'ice',
  peri_urban: 'urban',
}
const TEX_ID = 'living-column-tex'
// Must be a power of two: other sizes blur in the sprite atlas and make the
// pattern reset at every map-tile boundary, drawing seam lines on the column.
const TEX_SIZE = 256
const TAU = Math.PI * 2
let texActive = false
let texSupported = false
let texLastTs = 0

function hexToRgb(hex) {
  const h = (hex || '#2dd4bf').replace('#', '')
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
}

// Deterministic integer hash → [0,1), so the noise lattice below wraps cleanly.
function hash2(x, y, seed) {
  let h = (Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(seed, 1440662683)) | 0
  h = Math.imul(h ^ (h >>> 13), 1274126177)
  h ^= h >>> 16
  return (h >>> 0) / 4294967296
}

// Multi-octave value noise whose every octave lattice wraps at the texture
// border, so the field tiles seamlessly. Built once (lazily, on first use);
// the per-frame animation *scrolls* this static field, which preserves the
// tiling for free instead of recomputing noise per pixel.
let noiseField = null
function buildNoiseField(size) {
  const field = new Float32Array(size * size)
  let amp = 1
  let total = 0
  for (let oct = 0; oct < 4; oct++) {
    const period = 4 << oct // 4, 8, 16, 32 lattice cells across the tile
    for (let y = 0; y < size; y++) {
      const fy = (y * period) / size
      const y0 = fy | 0
      const y1 = (y0 + 1) % period
      const ty = fy - y0
      const sy = ty * ty * (3 - 2 * ty)
      for (let x = 0; x < size; x++) {
        const fx = (x * period) / size
        const x0 = fx | 0
        const x1 = (x0 + 1) % period
        const tx = fx - x0
        const sx = tx * tx * (3 - 2 * tx)
        const top = hash2(x0, y0, oct) * (1 - sx) + hash2(x1, y0, oct) * sx
        const bot = hash2(x0, y1, oct) * (1 - sx) + hash2(x1, y1, oct) * sx
        field[y * size + x] += (top + (bot - top) * sy) * amp
      }
    }
    total += amp
    amp *= 0.55
  }
  for (let i = 0; i < field.length; i++) field[i] /= total
  return field
}

// Bilinear sample of the noise field at (u, v) in tile units, wrapping both
// axes — so callers may scroll/scale freely (integer scales stay seamless).
function noise(u, v) {
  const size = TEX_SIZE
  const x = (u - Math.floor(u)) * size
  const y = (v - Math.floor(v)) * size
  const x0 = x | 0
  const y0 = y | 0
  const x1 = (x0 + 1) % size
  const y1 = (y0 + 1) % size
  const tx = x - x0
  const ty = y - y0
  const f = noiseField
  const top = f[y0 * size + x0] * (1 - tx) + f[y0 * size + x1] * tx
  const bot = f[y1 * size + x0] * (1 - tx) + f[y1 * size + x1] * tx
  return top + (bot - top) * ty
}

// Paint one frame of the biome surface into an RGBA buffer. `m` modulates the
// biome colour's brightness (the moving relief); `hi` blends toward white for
// crests / glints / sparkles. Every spatial wave runs an integer number of
// cycles per tile (TAU * k * u) and every noise lookup wraps, so the image
// repeats with no visible border.
function paintTexture(data, size, t, family, rgb) {
  const [r, g, b] = rgb
  for (let y = 0; y < size; y++) {
    const v = y / size
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4
      const u = x / size
      let m = 1
      let hi = 0
      switch (family) {
        case 'water': {
          // Two crossing wave trains, bent by a slowly drifting swell.
          const swell = noise(u * 2 + t * 0.02, v * 2 - t * 0.012)
          const w1 = Math.sin(TAU * (3 * u + v) + t * 1.1 + swell * 4)
          const w2 = Math.sin(TAU * (u - 2 * v) - t * 0.8 + swell * 3)
          const wave = (w1 + 0.7 * w2) / 1.7
          m = 0.6 + 0.26 * wave + 0.3 * (swell - 0.5)
          hi = Math.max(0, wave - 0.72) * 1.6 + Math.max(0, swell - 0.78) * 1.5 // foam
          break
        }
        case 'sand': {
          // Sharp ripple crests (1-|sin|) over broad dune light, drifting slowly.
          const warp = noise(u + t * 0.015, v)
          const dune = noise(u * 2 - t * 0.05, v * 2)
          const ridge = 1 - Math.abs(Math.sin(TAU * (5 * u + 2 * v) + warp * 5 + t * 0.4))
          m = 0.7 + 0.34 * (dune - 0.5) + 0.24 * (ridge - 0.45)
          break
        }
        case 'forest': {
          // Clumpy canopy (noise²) with independent light patches sliding over it.
          const canopy = noise(u * 2 + t * 0.025, v * 2 - t * 0.014)
          const light = noise(u * 3 - t * 0.035, v * 3 + t * 0.02)
          m = 0.5 + 0.62 * canopy * canopy + 0.28 * (light - 0.5)
          hi = Math.max(0, canopy * light - 0.52) * 0.9 // sun through the leaves
          break
        }
        case 'grass': {
          // Fine streaky tufts; a noise-bent gust front sweeps across them.
          const tuft = noise(u * 6, v * 2 + t * 0.01)
          const bend = noise(u, v)
          const gust = Math.sin(TAU * (2 * u + v) - t * 1.4 + bend * 2.5)
          m = 0.66 + 0.2 * (tuft - 0.5) * (1.3 + gust) + 0.14 * gust
          break
        }
        case 'ice': {
          const sheet = noise(u * 2 + t * 0.008, v * 2)
          m = 0.82 + 0.24 * (sheet - 0.5)
          const sp = hash2(x, y, 97)
          if (sp > 0.985) hi = Math.max(0, Math.sin(t * 2.5 + sp * 700) - 0.55) * 1.4 // twinkles
          break
        }
        case 'urban': {
          const cell = size >> 4 // 16 blocks per tile edge — divides evenly, no seam
          const gx = x % cell
          const gy = y % cell
          const lit = hash2((x / cell) | 0, (y / cell) | 0, 11 + ((t * 0.5) | 0))
          m = 0.6
          if (gx < 1 || gy < 1) m += 0.22 // street grid
          else if (gx > 3 && gx < cell - 3 && gy > 3 && gy < cell - 3 && lit > 0.72) m += 0.16 // lit blocks
          m += 0.08 * Math.sin(TAU * 2 * v - t * 1.3) // scan line
          break
        }
      }
      m = clamp(m, 0.22, 1.4)
      const f = hi > 0 ? Math.min(1, hi) : 0
      data[i] = Math.min(255, r * m + (255 - r * m) * f)
      data[i + 1] = Math.min(255, g * m + (255 - g * m) * f)
      data[i + 2] = Math.min(255, b * m + (255 - b * m) * f)
      data[i + 3] = 255
    }
  }
}

// One shared animated image. MapLibre calls render() each map frame; returning
// true re-uploads the texture. We throttle to ~30fps and idle (false) whenever
// no column is raised, so an unselected globe does no texture work.
const livingTex = {
  width: TEX_SIZE,
  height: TEX_SIZE,
  data: new Uint8Array(TEX_SIZE * TEX_SIZE * 4),
  family: 'forest',
  rgb: [45, 212, 191],
  start: 0,
  render() {
    if (!texActive) return false
    const now = performance.now()
    if (now - texLastTs < 33) return false
    texLastTs = now
    if (!noiseField) noiseField = buildNoiseField(TEX_SIZE)
    paintTexture(this.data, TEX_SIZE, (now - this.start) / 1000, this.family, this.rgb)
    return true
  },
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
  // Register the shared animated surface once. If unsupported, the column simply
  // falls back to its flat biome colour.
  try {
    if (!(map.hasImage && map.hasImage(TEX_ID))) {
      livingTex.start = performance.now()
      map.addImage(TEX_ID, livingTex)
    }
    texSupported = true
  } catch (_) {
    texSupported = false
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
        // Near-solid: lower opacity lets the far wall's pattern bleed through
        // the near one, which reads as moiré on the textured column.
        'fill-extrusion-opacity': 0.85,
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
    // Wrap the raised column in its biome's living surface (only this one object
    // animates). Colour is baked into the texture, so it tints to the biome.
    if (texSupported) {
      livingTex.family = TEXTURE_FAMILY[region.biome_key] ?? 'forest'
      livingTex.rgb = hexToRgb(column.color)
      livingTex.start = performance.now()
      texActive = true
      map.setPaintProperty('selected-extrusion', 'fill-extrusion-pattern', TEX_ID)
    }
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
  // Snap-and-clear once a lowering column has effectively bottomed out — the
  // living surface keeps moving during the descent, then idles here.
  if (column.target === 0 && next < 200) {
    if (column.h !== 0) {
      column.h = 0
      map.setPaintProperty('selected-extrusion', 'fill-extrusion-height', 0)
      if (texActive) {
        texActive = false
        map.setPaintProperty('selected-extrusion', 'fill-extrusion-pattern', undefined)
      }
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
