// @vitest-environment happy-dom
//
// Outline mode swaps each biome layer's geometry for the detailed RESOLVE
// ecoregions once they lazy-load. Both maps must redraw with the new geometry
// rather than keep what they were mounted with.
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// --- a minimal MapLibre stand-in (the real one needs WebGL) ---------------
const fakeMaps = []
class FakeMap {
  constructor() {
    this.sources = {}
    this.layers = {}
    this.handlers = {}
    fakeMaps.push(this)
  }
  on(ev, layerOrFn, fn) {
    ;(this.handlers[ev] ||= []).push(fn || layerOrFn)
  }
  fire(ev) {
    for (const fn of this.handlers[ev] || []) fn({})
  }
  addControl() {}
  addSource(id, src) {
    this.sources[id] = { ...src, setData: vi.fn(function (d) { this.data = d }) }
  }
  getSource(id) { return this.sources[id] }
  addLayer(layer) { this.layers[layer.id] = layer }
  getLayer(id) { return this.layers[id] }
  setLayoutProperty() {}
  setPaintProperty() {}
  setProjection() {}
  setSky() {}
  hasImage() { return false }
  addImage() {}
  getZoom() { return 1 }
  getCenter() { return { lng: 0, lat: 0 } }
  jumpTo() {}
  easeTo() {}
  getCanvas() { return { style: {} } }
  getStyle() { return { layers: [] } }
  remove() {}
}
vi.mock('maplibre-gl', () => ({
  __esModule: true,
  default: { Map: FakeMap, NavigationControl: class {} },
}))
vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))
vi.mock('@maplibre/maplibre-gl-leaflet', () => ({
  __esModule: true,
  maplibreGL: () => ({ addTo() {} }),
}))

const { default: GlobeMap } = await import('./GlobeMap.vue')
const { default: WorldMap } = await import('./WorldMap.vue')

const square = (lng, lat, d = 1) => ({
  type: 'Polygon',
  coordinates: [[[lng - d, lat - d], [lng + d, lat - d], [lng + d, lat + d], [lng - d, lat + d], [lng - d, lat - d]]],
})
const fc = (...geoms) => ({
  type: 'FeatureCollection',
  features: geoms.map((geometry, i) => ({ type: 'Feature', properties: { name: `f${i}` }, geometry })),
})
const layer = (geojson) => ({ id: 'tundra', kind: 'real', color: '#ccc', label: 'Tundra', geojson })

const COARSE = [layer(fc(square(100, 70, 5)))]
const DETAILED = [layer(fc(square(95, 68), square(100, 70), square(105, 72)))]

vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {}))) // basemap styles never arrive

describe('Outline mode geometry swap', () => {
  it('GlobeMap pushes the new geometry into the existing source', async () => {
    const w = mount(GlobeMap, {
      props: { layers: COARSE, visibleLayers: { tundra: true }, displayStyle: 'outline' },
      attachTo: document.body,
    })
    const map = fakeMaps.at(-1)
    map.fire('load')
    const src = map.getSource('layer-tundra')
    expect(src.data).toStrictEqual(COARSE[0].geojson)

    await w.setProps({ layers: DETAILED })
    expect(src.setData).toHaveBeenCalledWith(DETAILED[0].geojson)

    src.setData.mockClear()
    await w.setProps({ layers: DETAILED.map((l) => ({ ...l })) }) // same geometry object
    expect(src.setData).not.toHaveBeenCalled()
    w.unmount()
  })

  it('WorldMap redraws its Leaflet layer with the new features', async () => {
    const w = mount(WorldMap, {
      props: { layers: COARSE, visibleLayers: { tundra: true }, displayStyle: 'outline' },
      attachTo: document.body,
    })
    expect(w.findAll('path.region-overlay')).toHaveLength(1)
    await w.setProps({ layers: DETAILED })
    expect(w.findAll('path.region-overlay')).toHaveLength(3)
    await w.setProps({ layers: COARSE })
    expect(w.findAll('path.region-overlay')).toHaveLength(1)
    w.unmount()
  })
})
