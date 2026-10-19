// @vitest-environment happy-dom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { i18n } from '../i18n/index.js'
import { useRegions } from './useRegions.js'

const json = (body) => ({ ok: true, status: 200, json: async () => body })
const catalogue = (currency) => ({
  regions: [{ id: 'amazon', name: 'Amazon Basin', biome_key: 'tropical_rainforest', currency, geometry: null }],
})

let pending
beforeEach(() => {
  pending = {}
  vi.stubGlobal('fetch', vi.fn((url) => new Promise((resolve) => {
    pending[new URL(url, 'http://x').searchParams.get('currency')] = () => resolve(json(catalogue(
      new URL(url, 'http://x').searchParams.get('currency'),
    )))
  })))
})
afterEach(() => vi.unstubAllGlobals())

function setup() {
  let api
  mount(defineComponent({ setup() { api = useRegions(); return () => null } }), {
    global: { plugins: [i18n] },
  })
  return api
}

describe('useRegions.load', () => {
  it('keeps the newest currency when an older re-price lands last', async () => {
    const { regions, loading, load } = setup()
    load('EUR')
    load('BRL')
    pending.BRL()
    await flushPromises()
    expect(regions.value[0].currency).toBe('BRL')
    expect(loading.value).toBe(false)

    pending.EUR() // stale response
    await flushPromises()
    expect(regions.value[0].currency).toBe('BRL')
  })

  it('stays loading until the newest request answers', async () => {
    const { loading, load } = setup()
    load('EUR')
    load('BRL')
    pending.EUR()
    await flushPromises()
    expect(loading.value).toBe(true)
    pending.BRL()
    await flushPromises()
    expect(loading.value).toBe(false)
  })
})
