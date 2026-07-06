import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import de from './locales/de.json'
import es from './locales/es.json'

export const SUPPORTED_LOCALES = ['en', 'de', 'es']
const STORAGE_KEY = 'alpha-locale'

// Prefer a saved choice, then the browser's language list, then English.
function detectLocale() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && SUPPORTED_LOCALES.includes(saved)) return saved

  for (const lang of navigator.languages || [navigator.language || '']) {
    const short = lang.slice(0, 2).toLowerCase()
    if (SUPPORTED_LOCALES.includes(short)) return short
  }
  return 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: { en, de, es },
})

export function setLocale(locale) {
  if (!SUPPORTED_LOCALES.includes(locale)) return
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale
}

document.documentElement.lang = i18n.global.locale.value
