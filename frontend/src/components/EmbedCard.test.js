// @vitest-environment happy-dom
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EmbedCard from './EmbedCard.vue'

// Shaped like GET /api/v1/regions/{id}: the backend prices an unsupported
// ?currency= in USD and says so in `currency`.
function regionResponse(currency) {
  return {
    region: {
      id: 'amazon',
      name: 'Amazon Basin',
      biome_key: 'tropical_rainforest',
      currency,
      area: { hectares: 652_000_000 },
      total_ecosystem_value_per_year: 705_000_000_000,
      conversion_liability: { present_value: 37_500_000_000_000 },
    },
    currency,
  }
}

async function mountWith(query, backendCurrency) {
  window.history.replaceState({}, '', `/embed.html?${query}`)
  const fetchMock = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => regionResponse(backendCurrency),
  }))
  vi.stubGlobal('fetch', fetchMock)
  const wrapper = mount(EmbedCard)
  // The card lazy-loads its locale catalogue, so wait past the spinner.
  await vi.waitFor(async () => {
    await flushPromises()
    expect(wrapper.find('.spinner').exists()).toBe(false)
  })
  return { wrapper, fetchMock }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('EmbedCard', () => {
  it('renders instead of crashing when ?currency= is not an ISO code', async () => {
    const { wrapper } = await mountWith('region=amazon&currency=dollars', 'USD')
    const text = wrapper.text()
    expect(text).toContain('Amazon Basin')
    expect(text).not.toContain('Loading')
    expect(text).toContain('$705')
  })

  it('labels figures with the currency the backend priced them in', async () => {
    const { wrapper } = await mountWith('region=amazon&currency=XYZ', 'USD')
    expect(wrapper.text()).not.toContain('XYZ')
    expect(wrapper.text()).toContain('$')
  })

  it('still honours a supported currency and URL-encodes the request', async () => {
    const { wrapper, fetchMock } = await mountWith('region=amazon&currency=eur&locale=de', 'EUR')
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/regions/amazon?currency=EUR')
    expect(wrapper.text()).toContain('€')
  })
})
