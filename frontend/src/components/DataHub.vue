<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormat } from '../data/useFormat.js'

const { t } = useI18n()

// The hub's chrome is translated; the catalogue entries themselves (labels,
// notes, citations) come from the backend in English. Figures follow the
// user's locale. The carbon price is quoted in USD by definition
// (price_usd_per_tco2), so that formatter is pinned rather than following the
// app's selected display currency.
const { money: usd, decimal } = useFormat('USD')

// ----- catalogue -----------------------------------------------------------
const catalog = ref(null)
const market = ref(null)
const loading = ref(false)
const error = ref('')

const STATUS_COLORS = {
  authoritative: 'var(--forest-overlay)',
  reference: 'var(--accent)',
  placeholder: 'var(--gold)',
}
function statusMeta(s) {
  if (!STATUS_COLORS[s]) return { label: s, color: 'var(--text-muted)', hint: '' }
  return {
    label: t(`dataHub.status.${s}.label`),
    hint: t(`dataHub.status.${s}.hint`),
    color: STATUS_COLORS[s],
  }
}

// Either live feed off (unconfigured or unreachable) means valuations are
// running on the documented static references — say so in words, not only
// with a pill.
const anyStatic = computed(
  () => !!market.value && (!market.value.carbon?.live || !market.value.fx?.live),
)

async function loadCatalog() {
  loading.value = true
  error.value = ''
  try {
    const [cat, mkt] = await Promise.all([
      fetch('/api/v1/datasets').then((r) => {
        if (!r.ok) throw new Error(`datasets HTTP ${r.status}`)
        return r.json()
      }),
      fetch('/api/v1/market').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ])
    catalog.value = cat
    market.value = mkt
  } catch (e) {
    error.value = t('dataHub.error')
  } finally {
    loading.value = false
  }
}

// ----- live tool: ESV extraction ------------------------------------------
const esvText = ref(
  'Carbon sequestration was valued at US$120 per ha per year, water purification ' +
    'at $3,000 per hectare per year, and biodiversity habitat services at €450/ha/yr.',
)
const esvResult = ref(null)
const esvLoading = ref(false)
const esvError = ref('')

async function runExtract() {
  esvLoading.value = true
  esvError.value = ''
  esvResult.value = null
  try {
    const res = await fetch('/api/v1/extract-esv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: esvText.value, backend: 'auto' }),
    })
    if (!res.ok) throw new Error(`extract HTTP ${res.status}`)
    esvResult.value = await res.json()
  } catch (e) {
    esvError.value = t('dataHub.tools.esv.failed')
  } finally {
    esvLoading.value = false
  }
}

// ----- live tool: biome classification ------------------------------------
const geoText = ref(
  '{"type":"Polygon","coordinates":[[[-65,-5],[-60,-5],[-60,-2],[-65,-2],[-65,-5]]]}',
)
const clsResult = ref(null)
const clsLoading = ref(false)
const clsError = ref('')

async function runClassify() {
  clsLoading.value = true
  clsError.value = ''
  clsResult.value = null
  let body
  try {
    body = JSON.parse(geoText.value)
  } catch (e) {
    clsError.value = t('dataHub.tools.classify.invalidJson')
    clsLoading.value = false
    return
  }
  try {
    const res = await fetch('/api/v1/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`classify HTTP ${res.status}`)
    clsResult.value = await res.json()
  } catch (e) {
    clsError.value = t('dataHub.tools.classify.failed')
  } finally {
    clsLoading.value = false
  }
}

onMounted(loadCatalog)
</script>

<template>
  <section class="hub">
    <div class="hub-scroll">
    <div class="hub-inner">
      <header class="hub-head">
        <h2>{{ t('dataHub.title') }}</h2>
        <p>{{ t('dataHub.subtitle') }}</p>
      </header>

      <div v-if="market" class="market">
        <div class="market-item">
          <span class="market-k">{{ t('dataHub.market.carbon') }}</span>
          <span class="market-v">{{ usd(market.carbon.price_usd_per_tco2) }}<em>/tCO₂e</em></span>
          <span
            class="live-pill"
            :class="{ on: market.carbon.live }"
            :title="market.carbon.live ? t('dataHub.market.liveTitle') : t('dataHub.market.staticTitle')"
          >{{ market.carbon.live ? t('dataHub.market.live') : t('dataHub.market.static') }}</span>
        </div>
        <div class="market-item">
          <span class="market-k">{{ t('dataHub.market.fx') }}</span>
          <span class="market-v">
            <template v-for="(v, code) in market.fx.rates_per_usd" :key="code">
              <span v-if="code !== 'USD'" class="fx">{{ code }} {{ decimal(v) }}</span>
            </template>
          </span>
          <span
            class="live-pill"
            :class="{ on: market.fx.live }"
            :title="market.fx.live ? t('dataHub.market.liveTitle') : t('dataHub.market.staticTitle')"
          >{{ market.fx.live ? t('dataHub.market.live') : t('dataHub.market.static') }}</span>
        </div>
        <span class="market-asof">{{ t('dataHub.asOf', { date: market.fx.as_of || '—' }) }}</span>
        <p v-if="anyStatic" class="market-note">
          <span class="note-dot" aria-hidden="true"></span>{{ t('dataHub.market.fallbackNote') }}
        </p>
      </div>
      <p v-else-if="catalog" class="market market-missing">{{ t('dataHub.market.unavailable') }}</p>

      <div v-if="loading" class="hub-state" role="status">
        <span class="spinner" aria-hidden="true"></span>{{ t('dataHub.loading') }}
      </div>
      <div v-else-if="error" class="hub-state err" role="alert">
        <span class="err-icon" aria-hidden="true">!</span>
        <span>{{ error }}</span>
        <button class="run" @click="loadCatalog">{{ t('stage.retry') }}</button>
      </div>

      <template v-else-if="catalog">
        <!-- Sources -->
        <h3 class="section-title">{{ t('dataHub.sections.sources') }}</h3>
        <div class="cards">
          <article v-for="d in catalog.domains" :key="d.id" class="card">
            <div class="card-top">
              <span class="card-label">{{ d.label }}</span>
              <span
                class="badge"
                :style="{ '--c': statusMeta(d.status).color }"
                :title="statusMeta(d.status).hint"
              >
                {{ statusMeta(d.status).label }}
              </span>
            </div>
            <p class="card-note">{{ d.note }}</p>
            <ul class="cites">
              <li v-for="(s, i) in d.sources" :key="i">
                <a v-if="s.url" :href="s.url" target="_blank" rel="noopener">{{ s.citation }}</a>
                <span v-else>{{ s.citation }}</span>
              </li>
            </ul>
            <div class="card-foot">
              <span v-if="d.as_of" class="asof">{{ t('dataHub.asOf', { date: d.as_of }) }}</span>
              <span v-for="ep in d.exposed_via" :key="ep" class="endpoint">{{ ep }}</span>
            </div>
          </article>
        </div>

        <!-- Roadmap -->
        <h3 class="section-title">{{ t('dataHub.sections.needs') }}</h3>
        <div class="needs">
          <article v-for="n in catalog.needs" :key="n.id" class="need">
            <div class="need-head">
              <span class="need-label">{{ n.label }}</span>
              <span class="phase">{{ n.phase }}</span>
            </div>
            <div class="need-flow">
              <span class="now">{{ n.current }}</span>
              <span class="arrow" aria-hidden="true">→</span>
              <span class="next">{{ n.planned }}</span>
            </div>
            <p class="need-why">{{ n.why }}</p>
          </article>
        </div>

        <!-- Live tools -->
        <h3 class="section-title">{{ t('dataHub.sections.tools') }}</h3>
        <div class="tools">
          <!-- ESV extractor -->
          <article class="tool">
            <h4>{{ t('dataHub.tools.esv.title') }}</h4>
            <p class="tool-sub">{{ t('dataHub.tools.esv.sub') }}</p>
            <textarea v-model="esvText" rows="4" spellcheck="false" :aria-label="t('dataHub.tools.esv.title')"></textarea>
            <button class="run" :disabled="esvLoading || !esvText.trim()" @click="runExtract">
              {{ esvLoading ? t('dataHub.tools.esv.running') : t('dataHub.tools.esv.run') }}
            </button>
            <div v-if="esvError" class="tool-err" role="alert">{{ esvError }}</div>
            <div v-else-if="esvResult" class="tool-out" aria-live="polite">
              <div class="out-meta">
                <span class="chip">{{ t('dataHub.tools.esv.records', { n: esvResult.count }, esvResult.count) }}</span>
                <span class="chip">{{ t('dataHub.tools.esv.backend', { name: esvResult.backend }) }}</span>
                <span v-if="esvResult.fallback_reason" class="chip warn" :title="esvResult.fallback_reason">{{ t('dataHub.tools.esv.fallback') }}</span>
              </div>
              <table v-if="esvResult.records && esvResult.records.length">
                <thead>
                  <tr>
                    <th>{{ t('dataHub.tools.esv.cols.service') }}</th>
                    <th>{{ t('dataHub.tools.esv.cols.value') }}</th>
                    <th>{{ t('dataHub.tools.esv.cols.currency') }}</th>
                    <th>{{ t('dataHub.tools.esv.cols.unit') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, i) in esvResult.records" :key="i">
                    <td>{{ r.service || r.raw_service || '—' }}</td>
                    <td class="num">{{ decimal(r.value, 2) }}</td>
                    <td>{{ r.currency || '—' }}</td>
                    <td>{{ r.unit || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="tool-empty">{{ t('dataHub.tools.esv.empty') }}</p>
            </div>
          </article>

          <!-- Biome classifier -->
          <article class="tool">
            <h4>{{ t('dataHub.tools.classify.title') }}</h4>
            <p class="tool-sub">{{ t('dataHub.tools.classify.sub') }}</p>
            <textarea v-model="geoText" rows="4" spellcheck="false" :aria-label="t('dataHub.tools.classify.title')"></textarea>
            <button class="run" :disabled="clsLoading || !geoText.trim()" @click="runClassify">
              {{ clsLoading ? t('dataHub.tools.classify.running') : t('dataHub.tools.classify.run') }}
            </button>
            <div v-if="clsError" class="tool-err" role="alert">{{ clsError }}</div>
            <div v-else-if="clsResult" class="tool-out" aria-live="polite">
              <div class="cls-biome">{{ clsResult.classification.biome_label }}</div>
              <div class="out-meta">
                <span class="chip">{{ t('dataHub.tools.classify.confidence', { value: clsResult.classification.confidence }) }}</span>
                <span v-if="clsResult.classification.matched_region" class="chip">
                  {{ t('dataHub.tools.classify.matched', { value: clsResult.classification.matched_region }) }}
                </span>
              </div>
              <p class="cls-src">{{ clsResult.boundary_dataset.primary }}</p>
            </div>
          </article>
        </div>
      </template>
    </div>
    </div>
  </section>
</template>

<style scoped>
.hub {
  position: absolute;
  inset: 0;
  background: var(--stage-bg);
}
/* Scrolls below the floating topbar, so content never slides under the brand
   and controls; the top edge fades rather than cutting off hard. */
.hub-scroll {
  position: absolute;
  inset: var(--topbar-h) 0 0;
  overflow-y: auto;
  padding: var(--space-3) 18px 28px;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 var(--space-4));
  mask-image: linear-gradient(to bottom, transparent 0, #000 var(--space-4));
}
.hub-inner {
  max-width: 1080px;
  margin: 0 auto;
}
.hub-head h2 {
  margin: 0;
  font-size: var(--fs-xl);
  font-weight: 800;
  color: var(--text);
}
.hub-head p {
  margin: 5px 0 0;
  color: var(--text-muted);
  font-size: 0.86rem;
}
.market {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 18px;
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
}
.market-missing {
  color: var(--text-muted);
  font-size: var(--fs-sm);
}
.market-note {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-basis: 100%;
  margin: 0;
  padding-top: 10px;
  border-top: 1px solid var(--border-soft);
  font-size: var(--fs-xs);
  line-height: 1.45;
  color: var(--text-muted);
}
.note-dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gold);
}
.market-item {
  display: flex;
  align-items: center;
  gap: 9px;
}
.market-k {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-faint);
}
.market-v {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text);
}
.market-v em {
  font-style: normal;
  font-size: 0.66rem;
  color: var(--text-muted);
}
.fx {
  color: var(--text);
}
.live-pill {
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  cursor: help;
  padding: 2px 7px;
  border-radius: 999px;
  color: var(--text-muted);
  border: 1px solid var(--border-soft);
  background: var(--bg-deep);
}
.live-pill.on {
  color: var(--on-accent);
  background: var(--accent);
  border-color: var(--accent);
}
.market-asof {
  margin-left: auto;
  font-size: 0.66rem;
  color: var(--text-faint);
}

.hub-state {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: var(--space-6) var(--space-4);
  border-radius: var(--radius);
  color: var(--text-muted);
  font-size: var(--fs-md);
}
.hub-state.err {
  color: var(--text);
  background: var(--danger-bg);
  border: 1px solid var(--danger-border);
}
.hub-state .run {
  margin-top: 0;
  margin-left: auto;
}
.err-icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-weight: 900;
  color: var(--danger);
  border: 1px solid var(--danger-border);
}

.section-title {
  margin: 26px 0 12px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* cards */
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
}
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.card-label {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}
.badge {
  flex: none;
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--c);
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--c) 50%, transparent);
  background: color-mix(in srgb, var(--c) 12%, transparent);
}
.card-note {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-muted);
  line-height: 1.45;
}
.cites {
  margin: 0;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cites li {
  font-size: 0.7rem;
  color: var(--text-faint);
  line-height: 1.4;
}
.cites a {
  color: var(--accent);
  text-decoration: none;
}
.cites a:hover {
  text-decoration: underline;
}
.card-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: auto;
  padding-top: 4px;
}
.asof {
  font-size: 0.66rem;
  color: var(--text-muted);
  margin-right: 4px;
}
.endpoint {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 0.62rem;
  color: var(--text-muted);
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
}

/* needs */
.needs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}
.need {
  padding: 13px 16px;
  border-radius: var(--radius);
  background: var(--bg-panel);
  border: 1px solid var(--border-soft);
  border-left: 3px solid var(--gold);
}
.need-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.need-label {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text);
}
.phase {
  flex: none;
  font-size: 0.62rem;
  font-weight: 700;
  color: var(--gold);
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--gold) 45%, transparent);
}
.need-flow {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 0.74rem;
  margin-bottom: 6px;
}
.now {
  color: var(--text-muted);
}
.arrow {
  color: var(--accent);
  font-weight: 800;
}
.next {
  color: var(--text);
  font-weight: 600;
}
.need-why {
  margin: 0;
  font-size: 0.72rem;
  color: var(--text-faint);
  line-height: 1.45;
}

/* tools */
.tools {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 12px;
}
.tool {
  padding: 16px;
  border-radius: var(--radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
}
.tool h4 {
  margin: 0;
  font-size: 0.98rem;
  font-weight: 700;
  color: var(--text);
}
.tool-sub {
  margin: 4px 0 10px;
  font-size: 0.74rem;
  color: var(--text-muted);
  line-height: 1.4;
}
.tool textarea {
  width: 100%;
  resize: vertical;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  color: var(--text);
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 0.76rem;
  line-height: 1.5;
  outline: none;
  transition: border-color 0.18s var(--ease);
}
.tool textarea:focus {
  border-color: var(--accent);
}
.run {
  margin-top: 10px;
  padding: 8px 18px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(180deg, var(--accent), var(--teal-strong));
  color: var(--on-accent);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.18s var(--ease);
}
.run:disabled {
  opacity: 0.6;
  cursor: progress;
}
.tool-err {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--danger-bg);
  border: 1px solid var(--danger-border);
  font-size: 0.78rem;
  color: var(--text);
}
.tool-out {
  margin-top: 12px;
}
.out-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.chip {
  font-size: 0.66rem;
  font-weight: 600;
  color: var(--text-muted);
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
}
.chip.warn {
  color: var(--gold);
  border-color: color-mix(in srgb, var(--gold) 45%, transparent);
}
.tool table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.74rem;
}
.tool th {
  text-align: left;
  font-size: 0.64rem;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--text-faint);
  padding: 4px 8px;
  border-bottom: 1px solid var(--border-soft);
}
.tool td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-soft);
  color: var(--text);
}
.tool td.num {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
}
.tool-empty {
  font-size: 0.76rem;
  color: var(--text-muted);
}
.cls-biome {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--accent);
  margin-bottom: 8px;
}
.cls-src {
  margin: 8px 0 0;
  font-size: 0.68rem;
  color: var(--text-faint);
  line-height: 1.4;
}
</style>
