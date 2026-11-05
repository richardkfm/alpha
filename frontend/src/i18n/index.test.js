// @vitest-environment happy-dom
//
// Browsers throw a SecurityError from the localStorage accessor itself when
// site data is blocked (privacy settings, some embedded/sandboxed contexts).
// The i18n module runs at app start-up, so a throw there blanks the whole app.
import { describe, it, expect, vi, afterEach } from 'vitest'

const realDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage')

function blockStorage() {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    get() {
      throw new DOMException('The operation is insecure.', 'SecurityError')
    },
  })
}

afterEach(() => {
  if (realDescriptor) Object.defineProperty(window, 'localStorage', realDescriptor)
  vi.resetModules()
})

describe('i18n with blocked storage', () => {
  it('still boots, falling back to the browser language', async () => {
    blockStorage()
    vi.resetModules()
    const mod = await import('./index.js')
    expect(mod.SUPPORTED_LOCALES).toContain(mod.i18n.global.locale.value)
  })

  it('still switches language when the choice cannot be saved', async () => {
    blockStorage()
    vi.resetModules()
    const { i18n, setLocale } = await import('./index.js')
    expect(() => setLocale('de')).not.toThrow()
    expect(i18n.global.locale.value).toBe('de')
    expect(document.documentElement.lang).toBe('de')
  })

  it('persists and restores the choice when storage works', async () => {
    vi.resetModules()
    const first = await import('./index.js')
    first.setLocale('es')
    vi.resetModules()
    const second = await import('./index.js')
    expect(second.i18n.global.locale.value).toBe('es')
    localStorage.removeItem('alpha-locale')
  })
})
