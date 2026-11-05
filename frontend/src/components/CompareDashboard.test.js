// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { i18n } from '../i18n/index.js'
import CompareDashboard from './CompareDashboard.vue'

function catalogue(currency = 'USD') {
  return ['a', 'b', 'c', 'd'].map((id, i) => ({
    id,
    name: `Region ${id}`,
    region: 'Somewhere',
    biome_key: 'tropical_rainforest',
    currency,
    area: { sqm: 1e10, hectares: 1e6 },
    intactness: 1,
    total_ecosystem_value_per_sqm_year: 0.1 * (i + 1),
    total_ecosystem_value_per_year: 1e9 * (i + 1),
    yields_per_sqm_year: {
      carbon_capture: 0.01,
      climate_regulation: 0.01,
      water_filtration: 0.01,
      biodiversity_premium: 0.01,
      soil_nutrient_value: 0.01,
    },
    capitalized_value: { asset_value_total: 1e10 },
    conversion_liability: { present_value: 2e10 },
    red_lines: [],
  }))
}

const headNames = (w) => w.findAll('.region-head .rh-name').map((n) => n.text())

describe('CompareDashboard seeding', () => {
  it('seeds the top three once the catalogue arrives after opening', async () => {
    const w = mount(CompareDashboard, { global: { plugins: [i18n] }, props: { regions: [] } })
    expect(headNames(w)).toEqual([])
    await w.setProps({ regions: catalogue() })
    expect(headNames(w)).toEqual(['Region d', 'Region c', 'Region b'])
  })

  it('still seeds immediately when the catalogue is already loaded', async () => {
    const w = mount(CompareDashboard, { global: { plugins: [i18n] }, props: { regions: catalogue() } })
    await flushPromises()
    expect(headNames(w)).toHaveLength(3)
  })

  it('does not re-seed a cleared board when the catalogue is re-priced', async () => {
    const w = mount(CompareDashboard, { global: { plugins: [i18n] }, props: { regions: catalogue() } })
    await flushPromises()
    await w.find('.clear').trigger('click')
    expect(headNames(w)).toEqual([])
    await w.setProps({ regions: catalogue('EUR') })
    expect(headNames(w)).toEqual([])
  })
})
