// alpha — locale-aware biome metadata.
//
// Colors and render order stay in biomeMeta.js (language-neutral); the display
// text lives in the i18n catalogue (i18n/locales/*.json, "biomes" namespace)
// so it can be looked up here through vue-i18n once per component instead of
// duplicated at every call site.
import { useI18n } from 'vue-i18n'
import { BIOME_ORDER, biomeColor } from './biomeMeta.js'

export function useBiomeMeta() {
  const { t } = useI18n()

  const biomeLabel = (key) => t(`biomes.${key}.label`)
  const biomeShort = (key) => t(`biomes.${key}.short`)
  const biomeSublabel = (key) => t(`biomes.${key}.sublabel`)

  return { BIOME_ORDER, biomeColor, biomeLabel, biomeShort, biomeSublabel }
}
