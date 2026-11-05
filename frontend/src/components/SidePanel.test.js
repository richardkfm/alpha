// @vitest-environment happy-dom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { i18n } from '../i18n/index.js'
import SidePanel from './SidePanel.vue'
import fixture from '../test/valuation.fixture.json'

const region = (id, name) => ({
  id,
  name,
  region: 'Somewhere',
  biome_key: 'tropical_rainforest',
  geojson: fixture.geometry,
})
const AMAZON = region('amazon', 'Amazon Basin')
const CONGO = region('congo', 'Congo Basin')

let downloads
let resolveExport
beforeEach(() => {
  downloads = []
  vi.stubGlobal('fetch', vi.fn(() => new Promise((resolve) => { resolveExport = resolve })))
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
    downloads.push(this.download)
  })
  URL.createObjectURL = vi.fn(() => 'blob:x')
  URL.revokeObjectURL = vi.fn()
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function mountPanel() {
  return mount(SidePanel, {
    global: { plugins: [i18n] },
    props: { region: AMAZON, valuation: fixture.valuation, backendOnline: true },
  })
}

describe('SidePanel export', () => {
  it('names the file after the region that was exported, even if the panel moved on', async () => {
    const panel = mountPanel()
    await panel.findAll('.panel-actions .act')[0].trigger('click') // CSV
    const [url] = fetch.mock.calls[0]
    expect(url).toContain('name=Amazon+Basin')

    await panel.setProps({ region: CONGO })
    resolveExport({ ok: true, status: 200, blob: async () => new Blob(['x']) })
    await flushPromises()
    expect(downloads).toEqual(['alpha-amazon-basin.csv'])
  })

  it("doesn't carry one region's export error over to the next", async () => {
    const panel = mountPanel()
    await panel.findAll('.panel-actions .act')[0].trigger('click')
    resolveExport({ ok: false, status: 500 })
    await flushPromises()
    expect(panel.find('.act-err').exists()).toBe(true)

    await panel.setProps({ region: CONGO })
    expect(panel.find('.act-err').exists()).toBe(false)
  })

  it('a failure that lands after switching region is not shown on the new one', async () => {
    const panel = mountPanel()
    await panel.findAll('.panel-actions .act')[0].trigger('click')
    await panel.setProps({ region: CONGO })
    resolveExport({ ok: false, status: 500 })
    await flushPromises()
    expect(panel.find('.act-err').exists()).toBe(false)
  })
})

describe('SidePanel discount rate', () => {
  const digits = (s) => Number(s.replace(/[^0-9]/g, ''))

  it('recapitalises the conversion liability along with the standing asset', async () => {
    const panel = mountPanel()
    const v = fixture.valuation
    // At the reference rate both figures are the payload's own.
    expect(digits(panel.find('.liab-value').attributes('title'))).toBe(
      Math.round(v.conversion_liability.present_value),
    )
    const rates = panel.findAll('.asset-rates button')
    await rates[0].trigger('click') // 1%
    const asset = digits(panel.find('.asset-value').attributes('title'))
    const liab = digits(panel.find('.liab-value').attributes('title'))
    expect(asset).toBe(Math.round(v.total_ecosystem_value_per_year / 0.01))
    // The liability is the asset times the systemic premium, so it moves with
    // the rate too — it used to stay at the 3% figure and dip below the asset.
    expect(liab / asset).toBeCloseTo(v.systemic.multiplier, 2)
  })
})
