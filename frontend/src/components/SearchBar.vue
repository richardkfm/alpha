<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { parseAreaInput } from '../data/geo.js'

const emit = defineEmits(['search'])
const { t } = useI18n()

const query = ref('')
const error = ref('')
const open = ref(false)
const input = ref(null)

// geo.js is a pure parser and speaks English; its messages and labels are
// mapped onto translated strings here. Anything unrecognised (e.g. a message
// added to the parser later) falls through unchanged rather than vanishing.
const ERROR_KEYS = {
  'Enter coordinates or paste a GeoJSON polygon.': 'search.errors.empty',
  'That looks like JSON but could not be parsed.': 'search.errors.badJson',
  'Paste a GeoJSON Polygon or MultiPolygon (or a Feature wrapping one).': 'search.errors.notPolygon',
  'Point out of range — expected "lat, lng".': 'search.errors.outOfRange',
  'Enter "lat, lng", a "w, s, e, n" box, or paste a GeoJSON polygon.': 'search.errors.unrecognised',
}
function translateError(message) {
  const key = ERROR_KEYS[message]
  return key ? t(key) : message
}
function translateLabel(label) {
  if (label === 'Custom polygon') return t('search.labels.polygon')
  if (label === 'Bounding box') return t('search.labels.box')
  const point = /^Point (.+)$/.exec(label || '')
  if (point) return t('search.labels.point', { coords: point[1] })
  return label
}

function submit() {
  error.value = ''
  try {
    const { geometry, label } = parseAreaInput(query.value)
    open.value = false
    emit('search', {
      // No `id`: only catalogue regions carry one, and SidePanel offers the
      // embed snippet for anything with an id. 'custom' produced an
      // /embed.html?region=custom iframe that could only say "Region not found."
      id: null,
      name: translateLabel(label),
      region: t('search.customAreaLabel'),
      geojson: geometry,
    })
  } catch (e) {
    error.value = translateError(e.message)
  }
}

function clear() {
  query.value = ''
  error.value = ''
  input.value?.focus()
}

// Esc inside the field clears it (or, if already empty, leaves the field) —
// handled here so the app-level Esc (close panel) doesn't fire at the same time.
function onEscape(e) {
  e.stopPropagation()
  if (query.value || error.value) {
    query.value = ''
    error.value = ''
  } else {
    open.value = false
    input.value?.blur()
  }
}
</script>

<template>
  <div class="search" :class="{ open }">
    <form class="search-row" role="search" @submit.prevent="submit">
      <span class="search-icon" aria-hidden="true">⌖</span>
      <input
        ref="input"
        v-model="query"
        class="search-input"
        type="text"
        :placeholder="t('search.placeholder')"
        :aria-label="t('search.ariaLabel')"
        :aria-invalid="!!error"
        aria-describedby="search-msg"
        @focus="open = true"
        @blur="open = false"
        @input="error = ''"
        @keydown.esc="onEscape"
      />
      <button
        v-if="query"
        class="search-clear"
        type="button"
        :aria-label="t('search.clear')"
        :title="t('search.clear')"
        @mousedown.prevent
        @click="clear"
      >×</button>
      <button class="search-go" type="submit">{{ t('search.submit') }}</button>
    </form>
    <div id="search-msg" aria-live="polite">
      <transition name="fade">
        <div v-if="error" class="search-msg err">
          <span class="msg-icon" aria-hidden="true">!</span>{{ error }}
        </div>
        <div v-else-if="open" class="search-msg hint">
          <i18n-t keypath="search.hint" tag="span" scope="global">
            <template #point><code>-3.1, -60.0</code></template>
            <template #box><code>-65, -6, -60, -2</code></template>
          </i18n-t>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.search {
  position: absolute;
  top: calc(var(--topbar-h) + 2px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  width: min(520px, calc(100vw - 36px));
  pointer-events: auto;
  transition: left 0.42s var(--ease), width 0.42s var(--ease);
}
.search-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 6px 6px 14px;
  border-radius: var(--radius-pill);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-soft);
  transition: border-color 0.18s var(--ease), box-shadow 0.18s var(--ease);
}
.search.open .search-row {
  border-color: var(--accent-border);
  box-shadow: var(--shadow-soft), 0 0 0 3px var(--accent-bg);
}
.search-icon {
  color: var(--accent);
  font-size: 1rem;
}
.search-input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font: inherit;
  font-size: 0.85rem;
}
.search-input::placeholder {
  color: var(--text-faint);
}
.search-go {
  flex: none;
  padding: 7px 16px;
  border-radius: var(--radius-pill);
  border: none;
  background: linear-gradient(180deg, var(--accent), var(--teal-strong));
  color: var(--on-accent);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.18s var(--ease);
}
.search-go:hover {
  opacity: 0.92;
}
.search-clear {
  flex: none;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid var(--border-soft);
  background: var(--bg-deep);
  color: var(--text-muted);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}
.search-clear:hover {
  color: var(--accent);
  border-color: var(--accent);
}
/* Messages sit on their own glass strip so they stay legible over any basemap. */
.search-msg {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 6px 8px 0;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-glass);
  border: 1px solid var(--border-soft);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow: var(--shadow-soft);
  font-size: var(--fs-xs);
  line-height: 1.4;
}
.search-msg.hint {
  color: var(--text-muted);
}
.search-msg.hint code {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  color: var(--text);
  background: var(--bg-elevated);
  padding: 1px 5px;
  border-radius: 5px;
}
.search-msg.err {
  color: var(--text);
  border-color: var(--danger-border);
}
.msg-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 0.66rem;
  font-weight: 900;
  color: var(--danger);
  border: 1px solid var(--danger-border);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s var(--ease);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
