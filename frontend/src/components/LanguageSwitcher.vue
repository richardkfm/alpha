<script setup>
import { useI18n } from 'vue-i18n'
import { SUPPORTED_LOCALES, setLocale } from '../i18n/index.js'

const { locale, t } = useI18n()

const LABELS = { en: 'EN', de: 'DE', es: 'ES' }
</script>

<template>
  <div class="language" role="group" :aria-label="t('language.group')">
    <button
      v-for="code in SUPPORTED_LOCALES"
      :key="code"
      class="language-btn"
      :class="{ active: code === locale }"
      @click="setLocale(code)"
    >
      {{ LABELS[code] }}
    </button>
  </div>
</template>

<style scoped>
.language {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.language-btn {
  background: transparent;
  color: var(--text-muted);
  border: none;
  padding: 6px 10px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.18s var(--ease), background 0.18s var(--ease);
}
.language-btn:hover {
  color: var(--text);
}
.language-btn.active {
  background: var(--bg-elevated);
  color: var(--accent);
  box-shadow: inset 0 0 0 1px var(--border);
}
</style>
