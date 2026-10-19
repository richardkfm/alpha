// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { i18n } from '../i18n/index.js'
import SearchBar from './SearchBar.vue'
import SidePanel from './SidePanel.vue'
import fixture from '../test/valuation.fixture.json'

const global = { plugins: [i18n] }

async function searchFor(text) {
  const bar = mount(SearchBar, { global })
  await bar.find('input').setValue(text)
  await bar.find('form').trigger('submit')
  const events = bar.emitted('search')
  expect(events).toHaveLength(1)
  return events[0][0]
}

function panelFor(region) {
  return mount(SidePanel, {
    global,
    props: { region, valuation: fixture.valuation, backendOnline: true },
  })
}

describe('custom search areas', () => {
  it('are valued but never offered as an embeddable catalogue region', async () => {
    const region = await searchFor('-3.1, -60.0')
    expect(region.geojson.type).toBe('Polygon')
    expect(region.id).toBeFalsy()

    const panel = panelFor(region)
    const actions = panel.findAll('.panel-actions .act').map((b) => b.text())
    expect(actions.length).toBe(2) // CSV + PDF only
    expect(panel.find('.embed-box').exists()).toBe(false)
  })

  it('a catalogue region still gets the embed snippet', async () => {
    const panel = panelFor({
      id: 'amazon',
      name: 'Amazon Basin',
      region: 'South America',
      biome_key: 'tropical_rainforest',
      geojson: fixture.geometry,
    })
    const buttons = panel.findAll('.panel-actions .act')
    expect(buttons.length).toBe(3)
    await buttons[2].trigger('click')
    expect(panel.find('.embed-code').text()).toContain('/embed.html?region=amazon')
  })
})
