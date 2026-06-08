// alpha — region catalogue composable.
//
// Fetches the backend region catalogue (GET /api/v1/regions) — dozens of named
// ecosystems across all five biomes, each pre-valued in the chosen currency —
// and derives the map layer definitions from it. This is the single source of
// truth consumed by both maps (WorldMap / GlobeMap), the LayerControl, and the
// Compare dashboard, replacing the old hardcoded 4-region file.
import { ref, computed } from 'vue'
import { BIOME_META, BIOME_ORDER, biomeColor } from './biomeMeta.js'
import { centroid } from './geo.js'

export function useRegions() {
  const regions = ref([])
  const loading = ref(false)
  const error = ref('')
  const loaded = ref(false)

  // Fetch (or re-price) the catalogue. Called on mount and when the currency
  // changes so the map, picker and Compare numbers all reflect one currency.
  async function load(currency = 'USD') {
    loading.value = true
    error.value = ''
    try {
      const res = await fetch(`/api/v1/regions?currency=${currency}`)
      if (!res.ok) throw new Error(`regions HTTP ${res.status}`)
      const body = await res.json()
      regions.value = (body.regions || []).map((r) => ({
        ...r,
        // Alias geometry -> geojson and gdp_callout -> gdpCallout so the existing
        // valuation POST (App.fetchValuation) and SidePanel keep working unchanged.
        geojson: r.geometry,
        gdpCallout: r.gdp_callout,
      }))
      loaded.value = true
    } catch (e) {
      error.value = 'Could not load region data from the alpha backend. Is it running on :8000?'
    } finally {
      loading.value = false
    }
  }

  // One toggleable map layer per biome (in legend order), built from whichever
  // regions are present. Geometry is currency-independent, so the maps build
  // from this once and ignore later currency re-prices.
  const biomeLayers = computed(() => {
    const byBiome = {}
    for (const r of regions.value) {
      ;(byBiome[r.biome_key] ||= []).push(r)
    }
    return BIOME_ORDER.filter((key) => byBiome[key]?.length).map((key) => ({
      id: key,
      label: BIOME_META[key].label,
      sublabel: BIOME_META[key].sublabel,
      kind: 'real',
      color: biomeColor(key),
      count: byBiome[key].length,
      geojson: {
        type: 'FeatureCollection',
        features: byBiome[key].map((r) => ({
          type: 'Feature',
          properties: { regionId: r.id, name: r.name },
          geometry: r.geometry,
        })),
      },
    }))
  })

  // Value "bubble" / heat points: one Point per region at its centroid, carrying
  // a sqrt-scaled pixel radius and a normalised heat weight derived from the
  // annual Total Ecosystem Value. Relative sizes are FX-invariant (every value
  // scales by the same rate), so these stay stable across currency re-prices.
  const pointFeatures = computed(() => {
    const values = regions.value.map((r) => r.total_ecosystem_value_per_year || 0)
    const maxValue = Math.max(...values, 1)
    const maxRoot = Math.sqrt(maxValue) || 1
    const R_MIN = 6
    const R_MAX = 40
    const features = []
    for (const r of regions.value) {
      const c = centroid(r.geometry)
      if (!c) continue
      const value = r.total_ecosystem_value_per_year || 0
      const wt = value / maxValue
      const radius = R_MIN + (Math.sqrt(value) / maxRoot) * (R_MAX - R_MIN)
      features.push({
        type: 'Feature',
        properties: {
          regionId: r.id,
          name: r.name,
          biome_key: r.biome_key,
          color: biomeColor(r.biome_key),
          value,
          r: Math.round(radius * 10) / 10,
          wt: Math.round(wt * 1000) / 1000,
        },
        geometry: { type: 'Point', coordinates: c },
      })
    }
    return { type: 'FeatureCollection', features }
  })

  return { regions, biomeLayers, pointFeatures, loading, error, loaded, load }
}
