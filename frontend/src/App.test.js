// @vitest-environment happy-dom
//
// App-level fetch orchestration: what the side panel shows when requests
// overlap. The maps need WebGL, so they are replaced by inert stubs.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { i18n } from './i18n/index.js'
import fixture from './test/valuation.fixture.json'

vi.mock('./components/GlobeMap.vue', () => ({ __esModule: true, default: { name: 'GlobeMap', render: () => null } }))
vi.mock('./components/WorldMap.vue', () => ({ __esModule: true, default: { name: 'WorldMap', render: () => null } }))

const { default: App } = await import('./App.vue')
const { default: SearchBar } = await import('./components/SearchBar.vue')
const { default: SidePanel } = await import('./components/SidePanel.vue')

const json = (body, status = 200) => ({ ok: status < 400, status, json: async () => body })

function valuationFor(name, currency = 'USD') {
  return { ...fixture.valuation, currency, total_ecosystem_value_per_year: name.length * 1e9, _for: name }
}

// Each POST /api/v1/valuation waits until the test settles it explicitly, so
// the test decides which response lands first.
let pending
beforeEach(() => {
  pending = []
  vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
    if (url === '/health') return Promise.resolve(json({ status: 'ok', version: '0.4.0' }))
    if (url.startsWith('/api/v1/regions')) return Promise.resolve(json({ regions: [] }))
    if (url.startsWith('/api/v1/valuation')) {
      const body = JSON.parse(opts.body)
      const currency = new URLSearchParams(url.split('?')[1]).get('currency')
      return new Promise((resolve) => {
        pending.push({ name: body.name, currency, resolve })
      })
    }
    return Promise.reject(new Error(`unexpected fetch ${url}`))
  }))
})
afterEach(() => vi.unstubAllGlobals())

const area = (name) => ({
  id: null,
  name,
  region: 'test',
  geojson: { ...fixture.geometry, name }, // name rides along so the mock can tell them apart
})

function settle(name, currency = 'USD') {
  const i = pending.findIndex((p) => p.name === name && p.currency === currency)
  const [p] = pending.splice(i, 1)
  p.resolve(json(valuationFor(name, currency)))
}

async function mountApp() {
  const wrapper = mount(App, { global: { plugins: [i18n] } })
  await flushPromises()
  return wrapper
}

describe('side panel request ordering', () => {
  it("keeps the newest region's valuation when an older response lands last", async () => {
    const app = await mountApp()
    const search = app.findComponent(SearchBar)
    search.vm.$emit('search', area('Slow first pick'))
    await flushPromises()
    search.vm.$emit('search', area('Second'))
    await flushPromises()

    settle('Second')
    await flushPromises()
    let panel = app.findComponent(SidePanel)
    expect(panel.props('region').name).toBe('Second')
    expect(panel.props('valuation')._for).toBe('Second')
    expect(panel.props('loading')).toBe(false)

    settle('Slow first pick') // the stale response arrives late
    await flushPromises()
    panel = app.findComponent(SidePanel)
    expect(panel.props('region').name).toBe('Second')
    expect(panel.props('valuation')._for).toBe('Second')
  })

  it("doesn't drop the spinner while the newest request is still loading", async () => {
    const app = await mountApp()
    const search = app.findComponent(SearchBar)
    search.vm.$emit('search', area('A'))
    await flushPromises()
    search.vm.$emit('search', area('B'))
    await flushPromises()
    settle('A')
    await flushPromises()
    const panel = app.findComponent(SidePanel)
    expect(panel.props('loading')).toBe(true)
    expect(panel.props('valuation')).toBe(null)
  })

  it('a re-price superseded by another currency switch does not win', async () => {
    const app = await mountApp()
    app.findComponent(SearchBar).vm.$emit('search', area('Basin'))
    await flushPromises()
    settle('Basin')
    await flushPromises()

    const button = (code) => app.findAll('.currency-btn').find((b) => b.text() === code)
    await button('EUR').trigger('click')
    await button('BRL').trigger('click')
    await flushPromises()
    settle('Basin', 'BRL')
    await flushPromises()
    settle('Basin', 'EUR')
    await flushPromises()
    expect(app.findComponent(SidePanel).props('valuation').currency).toBe('BRL')
  })
})
