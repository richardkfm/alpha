<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
// Shared yield-category metadata, also used by the Compare dashboard.
import { YIELD_ROWS } from '../data/yields.js'
// Cross-biome bar scale, shared with the Compare dashboard.
import { barPct } from '../data/yieldScale.js'
import { useBiomeMeta } from '../data/useBiomeMeta.js'
import { useCountUp } from '../data/useCountUp.js'
import { useFormat } from '../data/useFormat.js'

const { t, locale } = useI18n()
const { biomeColor, biomeLabel, biomeSublabel: translatedBiomeSublabel } = useBiomeMeta()

const props = defineProps({
  region: { type: Object, required: true },
  valuation: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  backendOnline: { type: Boolean, default: null },
  error: { type: String, default: '' },
  showLiability: { type: Boolean, default: true },
  showSystemic: { type: Boolean, default: true },
  showRedLines: { type: Boolean, default: true },
  // Per-service cross-biome ceilings (max across the catalogue) so each bar
  // shows magnitude vs the strongest biome, not just composition within this one.
  ceilings: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close', 'update:showLiability', 'update:showSystemic', 'update:showRedLines'])

// Intl places the currency symbol itself (de wants "1.234 €", not "€1.234"), so
// the API's currency_symbol field is no longer read here.
const { money, moneyFull, perHa, count, hectares, decimal, percent, likeTarget } = useFormat(
  () => props.valuation?.currency,
)

// Phase 3: the backend now detects the biome from ingested boundary data.
const classification = computed(() => props.valuation?.classification ?? null)
const biomeKey = computed(() => classification.value?.biome_key ?? props.region.biome_key)
const biomeHue = computed(() => biomeColor(biomeKey.value))
// The backend's classification.biome_label is English-only; prefer the
// frontend's translated biome catalogue keyed by biome_key instead.
const biomeName = computed(() => biomeLabel(biomeKey.value))
const biomeSublabel = computed(() => translatedBiomeSublabel(biomeKey.value))

// Provenance compressed into a badge; the full sentence lives in its tooltip.
const provenance = computed(() => {
  const c = classification.value
  if (!c) return null
  if (c.confidence === 'matched') {
    const from =
      c.matched_region && c.matched_region !== 'N/A'
        ? t('sidePanel.provenance.resolveMatchFrom', { region: c.matched_region })
        : t('sidePanel.provenance.resolveMatchFromBoundaries')
    return {
      label: t('sidePanel.provenance.resolveMatchLabel'),
      title: t('sidePanel.provenance.resolveMatchTitle', { from }),
      sure: true,
    }
  }
  if (c.confidence === 'explicit') {
    return {
      label: t('sidePanel.provenance.catalogueLabel'),
      title: t('sidePanel.provenance.catalogueTitle'),
      sure: true,
    }
  }
  return {
    label: t('sidePanel.provenance.defaultLabel'),
    title: t('sidePanel.provenance.defaultTitle'),
    sure: false,
  }
})

const yieldRows = computed(() => {
  if (!props.valuation) return []
  const values = YIELD_ROWS.map((r) => props.valuation.yields_per_sqm_year[r.key] ?? 0)
  const total = values.reduce((a, b) => a + b, 0) || 1
  return YIELD_ROWS.map(({ key, color }) => {
    const value = props.valuation.yields_per_sqm_year[key]
    return {
      label: t(`yields.${key}`),
      color,
      value,
      // share = composition within this region; bar = magnitude vs the
      // strongest biome for this service, so a desert reads as low, not maxed.
      share: Math.round(((value ?? 0) / total) * 100),
      pct: barPct(value, props.ceilings[key]),
    }
  })
})

// --- Standing natural-asset value (capitalised perpetual flow) -------------
// Capitalise the annual flow locally so the discount rate can be explored
// without a server round-trip: asset = annual / rate.
const DISCOUNT_RATES = [0.01, 0.03, 0.05]
const discountRate = ref(0.03)
const assetValue = computed(() => {
  const annual = props.valuation?.total_ecosystem_value_per_year
  if (annual == null) return null
  return annual / discountRate.value
})

// Cost-of-conversion reframing: a permanent liability + red lines, never a
// price to net against revenue.
const liability = computed(() => props.valuation?.conversion_liability ?? null)
const systemicMult = computed(() => props.valuation?.systemic?.multiplier ?? 1)
const redLines = computed(() => props.valuation?.red_lines ?? [])

// Intactness: share of the intact-biome potential the land currently delivers.
const intactness = computed(() => props.valuation?.intactness ?? null)
const potentialAnnual = computed(
  () => props.valuation?.potential?.total_ecosystem_value_per_year ?? null,
)

// Headline figures ease toward their value instead of snapping.
const annualTotal = computed(
  () => props.valuation?.total_ecosystem_value_per_year ?? null,
)
const annualAnim = useCountUp(annualTotal)
const assetAnim = useCountUp(assetValue)
const liabAnim = useCountUp(computed(() => liability.value?.present_value ?? null))

// The intactness bar reads its width off a bare percentage, so it needs the
// unlocalised form — `percent()` would give it "73 %" in German.
function pctWidth(n) {
  return n == null ? '0%' : `${Math.round(n * 100)}%`
}

// --- Phase 4: export + embed -----------------------------------------------
function slugify(s) {
  return String(s || 'valuation')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '') || 'valuation'
}

// Download a CSV/PDF investor report. Posts the same geometry + params as the
// valuation call (App.fetchValuation) so the report matches the panel exactly;
// the backend renders it and we save the returned blob.
const exporting = ref('')
const exportError = ref('')
async function downloadExport(format) {
  if (!props.valuation || exporting.value) return
  exporting.value = format
  exportError.value = ''
  try {
    // `locale` drives number formatting in the PDF brief, so a German user's
    // report reads "1.234.567 €" rather than "€1,234,567".
    const params = new URLSearchParams({
      format,
      currency: props.valuation.currency,
      locale: locale.value,
    })
    if (props.region.name) params.set('name', props.region.name)
    if (props.region.biome_key) params.set('biome', props.region.biome_key)
    if (props.region.intactness != null) params.set('intactness', props.region.intactness)
    const res = await fetch(`/api/v1/valuation/export?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(props.region.geojson),
    })
    if (!res.ok) throw new Error(`export HTTP ${res.status}`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alpha-${slugify(props.region.name || props.region.biome_key)}.${format}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    exportError.value = t('sidePanel.actions.exportFailed')
  } finally {
    exporting.value = ''
  }
}

// Embeddable widget: a copy-paste <iframe> snippet for a catalogue region (only
// those carry a stable id). The iframe loads /embed.html from this same origin,
// so its API calls are same-origin — no CORS/host config needed by the embedder.
const showEmbed = ref(false)
const copied = ref(false)
const embedSnippet = computed(() => {
  if (!props.region?.id) return ''
  const origin = window.location.origin
  const cur = props.valuation?.currency || 'USD'
  const theme = document.documentElement.classList.contains('light') ? 'light' : 'dark'
  // Carry the locale through so the embedded card uses the same number
  // conventions the user is looking at right now.
  const src = `${origin}/embed.html?region=${encodeURIComponent(props.region.id)}&currency=${cur}&theme=${theme}&locale=${locale.value}`
  return `<iframe src="${src}" width="340" height="240" style="border:0;border-radius:14px" loading="lazy" title="alpha — ${props.region.name} ecosystem value"></iframe>`
})
async function copyEmbed() {
  try {
    await navigator.clipboard.writeText(embedSnippet.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1600)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <aside class="panel">
    <header class="panel-head">
      <div class="title-row">
        <h2>{{ region.name }}</h2>
        <button class="close" @click="$emit('close')" :aria-label="t('sidePanel.close')">×</button>
      </div>
      <div class="subtitle-row">
        <p class="region">{{ region.region }}</p>
        <span
          class="conn"
          :class="{ ok: backendOnline, down: backendOnline === false }"
          :title="backendOnline ? t('sidePanel.connection.titleOk') : backendOnline === false ? t('sidePanel.connection.titleDown') : t('sidePanel.connection.titleChecking')"
        >
          <span class="conn-dot"></span>
          {{ backendOnline ? t('sidePanel.connection.live') : backendOnline === false ? t('sidePanel.connection.offline') : t('sidePanel.connection.checking') }}
        </span>
      </div>

      <div v-if="valuation" class="panel-actions">
        <button class="act" :disabled="!!exporting" @click="downloadExport('csv')">
          {{ exporting === 'csv' ? t('sidePanel.actions.working') : t('sidePanel.actions.csv') }}
        </button>
        <button class="act" :disabled="!!exporting" @click="downloadExport('pdf')">
          {{ exporting === 'pdf' ? t('sidePanel.actions.working') : t('sidePanel.actions.pdf') }}
        </button>
        <button
          v-if="region.id"
          class="act"
          :class="{ on: showEmbed }"
          @click="showEmbed = !showEmbed"
        >{{ t('sidePanel.actions.embed') }}</button>
      </div>
      <p v-if="exportError" class="act-err">{{ exportError }}</p>

      <div v-if="showEmbed && region.id" class="embed-box">
        <p class="embed-hint">{{ t('sidePanel.embed.hint', { name: region.name }) }}</p>
        <code class="embed-code">{{ embedSnippet }}</code>
        <button class="embed-copy" @click="copyEmbed">{{ copied ? t('sidePanel.embed.copied') : t('sidePanel.embed.copy') }}</button>
      </div>
    </header>

    <div v-if="loading" class="skeleton" :aria-label="t('sidePanel.loading.ariaLabel')">
      <div class="sk-line sk-row"></div>
      <div class="sk-block"></div>
      <div class="sk-line"></div>
      <div class="sk-line short"></div>
      <div class="sk-hero"></div>
      <span class="sk-note">{{ t('sidePanel.loading.note') }}</span>
    </div>
    <div v-else-if="error" class="state err">{{ error }}</div>

    <template v-else-if="valuation">
      <section v-if="classification" class="biome" :style="{ '--biome': biomeHue }">
        <span class="biome-dot" aria-hidden="true"></span>
        <span class="biome-text">
          <span class="biome-name">{{ biomeName }}</span>
          <span v-if="biomeSublabel" class="biome-sub">{{ biomeSublabel }}</span>
        </span>
        <span
          v-if="provenance"
          class="biome-badge"
          :class="{ inferred: !provenance.sure }"
          :title="provenance.title"
        >{{ provenance.label }}</span>
      </section>

      <section class="stats">
        <div class="stat">
          <span class="k">{{ t('sidePanel.stats.area') }}</span>
          <span class="v num" :title="count(valuation.area.hectares)"
            >{{ hectares(valuation.area.hectares) }} <em>ha</em></span
          >
          <span class="stat-sub num" :title="`${count(valuation.area.sqm)} m²`"
            >{{ decimal(valuation.area.sqm, 0) }} m²</span
          >
        </div>
        <div v-if="intactness != null && intactness < 1" class="stat">
          <span class="k">{{ t('sidePanel.stats.intactness') }}</span>
          <span class="v num">{{ percent(intactness) }}</span>
          <span class="intact-track" aria-hidden="true">
            <span class="intact-bar" :style="{ width: pctWidth(intactness) }"></span>
          </span>
          <span class="stat-sub" :title="t('sidePanel.stats.intactnessTitle', { pct: percent(intactness) })">
            {{ t('sidePanel.stats.potentialSub', { value: money(potentialAnnual) }) }}
          </span>
        </div>
      </section>

      <!-- Leads the value sections: the standing-asset figure is the headline
           number the panel exists to deliver, so it comes before the flow that
           it capitalises and before the per-service breakdown. -->
      <section class="asset">
        <div class="asset-head">
          <span class="asset-label">{{ t('sidePanel.asset.label') }}</span>
          <div class="asset-rates" role="group" :aria-label="t('sidePanel.asset.discountGroup')">
            <button
              v-for="r in DISCOUNT_RATES"
              :key="r"
              :class="{ on: discountRate === r }"
              @click="discountRate = r"
            >{{ Math.round(r * 100) }}%</button>
          </div>
        </div>
        <!-- Intl renders the symbol itself now, so repeating the ISO code here
             would read as "7,1 Bio. € EUR". -->
        <span class="asset-value" :title="moneyFull(assetValue)" :aria-label="moneyFull(assetValue)"
          >{{ likeTarget(assetAnim, assetValue) }}</span
        >
        <span
          class="asset-sub"
          :title="t('sidePanel.asset.subTitle')"
        >{{ t('sidePanel.asset.sub', { rate: Math.round(discountRate * 100) }) }}</span>
      </section>

      <section class="yields">
        <h3>
          {{ t('sidePanel.yields.heading') }}
          <small>{{ t('sidePanel.yields.unit', { currency: valuation.currency }) }}</small>
        </h3>
        <p class="yields-scale">{{ t('sidePanel.yields.scale') }}</p>
        <ul>
          <li
            v-for="row in yieldRows"
            :key="row.label"
            :title="t('sidePanel.yields.rowTitle', { label: row.label, share: row.share })"
          >
            <div class="yield-meta">
              <span class="yield-dot" :style="{ background: row.color }"></span>
              <span class="yield-label">{{ row.label }}</span>
              <span class="yield-share num">{{ row.share }}%</span>
              <span class="num yield-num">{{ perHa(row.value) }}</span>
            </div>
            <div class="yield-track">
              <div
                class="yield-bar"
                :style="{ width: row.pct + '%', background: row.color }"
              ></div>
            </div>
          </li>
        </ul>
      </section>

      <!-- The whole-area total is the hero: this section is headed "Total
           Ecosystem Value", so leading with the per-hectare rate invited
           reading a continental basin as being worth ~1.062 $. The rate is
           still here, demoted and glued to its unit. -->
      <section class="tev">
        <span class="tev-label">{{ t('sidePanel.tev.label') }}</span>
        <span class="tev-value" :title="moneyFull(annualTotal)" :aria-label="moneyFull(annualTotal)">{{
          likeTarget(annualAnim, annualTotal)
        }}</span>
        <!-- No currency code in these unit strings: the amount above already
             carries its symbol, so "527 € EUR / ha / Jahr" read as a stutter. -->
        <span class="tev-unit">{{ t('sidePanel.tev.annualUnit') }}</span>
        <div class="tev-annual">
          <span class="tev-annual-v num">{{ perHa(valuation.total_ecosystem_value_per_sqm_year) }}</span>
          <span class="tev-annual-k">{{ t('sidePanel.tev.unit') }}</span>
        </div>
      </section>

      <section v-if="liability" class="conversion">
        <div class="conv-header">
          <h3>{{ t('sidePanel.conversion.heading') }}</h3>
          <div class="conv-modes" role="group" :aria-label="t('sidePanel.conversion.modesGroup')">
            <button :class="{ on: showLiability }" @click="emit('update:showLiability', !showLiability)" :title="t('sidePanel.conversion.liabilityTitle')">{{ t('sidePanel.conversion.liability') }}</button>
            <button :class="{ on: showSystemic }" @click="emit('update:showSystemic', !showSystemic)" :title="t('sidePanel.conversion.systemicTitle')">{{ t('sidePanel.conversion.systemic') }}</button>
            <button :class="{ on: showRedLines }" @click="emit('update:showRedLines', !showRedLines)" :title="t('sidePanel.conversion.redLinesTitle')">{{ t('sidePanel.conversion.redLines') }}</button>
          </div>
        </div>

        <template v-if="showLiability">
          <div class="liab">
            <span class="liab-label">{{ t('sidePanel.conversion.perpetualLiability') }}</span>
            <span
              class="liab-value"
              :title="moneyFull(liability.present_value)"
              :aria-label="moneyFull(liability.present_value)"
              >{{ likeTarget(liabAnim, liability.present_value) }}</span
            >
            <span class="liab-sub" :title="liability.note">
              {{ t('sidePanel.conversion.liabilitySub', { loss: money(liability.annual_loss), incidence: liability.incidence }) }}
            </span>
          </div>
        </template>

        <div v-if="systemicMult > 1.05 && showSystemic" class="systemic-tag">
          <strong>{{ t('sidePanel.conversion.systemicTagBold', { mult: systemicMult }) }}</strong>
          {{ t('sidePanel.conversion.systemicTagRest') }}
        </div>

        <div v-if="liability.carbon_debt_onetime > 0 && showSystemic" class="carbon-debt">
          {{ t('sidePanel.conversion.carbonDebt', { amount: money(liability.carbon_debt_onetime) }) }}
        </div>

        <div v-if="redLines.length && showRedLines" class="redlines">
          <span
            class="rl-head"
            :title="t('sidePanel.conversion.redLinesHeadTitle')"
          >{{ t('sidePanel.conversion.redLinesHead') }}</span>
          <ul>
            <li v-for="rl in redLines" :key="rl.label">
              <strong>{{ rl.label }}</strong> — {{ rl.reason }}
            </li>
          </ul>
        </div>
      </section>

      <section v-if="region.gdpCallout" class="callout">
        <span class="callout-mark">“</span>{{ region.gdpCallout }}
      </section>

      <details class="method">
        <summary>{{ t('sidePanel.methodology') }}</summary>
        <p>{{ valuation.methodology_note }}</p>
      </details>
    </template>
  </aside>
</template>

<style scoped>
.panel {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 1100;
  height: 100%;
  width: min(420px, 94vw);
  overflow-y: auto;
  padding: 78px 22px 30px; /* clears the floating topbar */
  background: linear-gradient(180deg, var(--bg-panel), var(--bg-deep));
  border-left: 1px solid var(--border);
  box-shadow: var(--shadow-panel);
}

/* Sections cascade in as the valuation lands. */
.panel section,
.panel .method {
  animation: rise 0.45s var(--ease) both;
}
.panel section:nth-of-type(2) { animation-delay: 0.04s; }
.panel section:nth-of-type(3) { animation-delay: 0.08s; }
.panel section:nth-of-type(4) { animation-delay: 0.12s; }
.panel section:nth-of-type(5) { animation-delay: 0.16s; }
.panel section:nth-of-type(6) { animation-delay: 0.2s; }
.panel section:nth-of-type(7) { animation-delay: 0.24s; }
.panel .method { animation-delay: 0.28s; }
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.close {
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-muted);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.18s var(--ease), border-color 0.18s var(--ease),
    transform 0.18s var(--ease);
}
.close:hover {
  border-color: var(--accent);
  color: var(--accent);
  transform: rotate(90deg);
}

.panel-head h2 {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.2px;
  color: var(--text);
}
.subtitle-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin: 5px 0 14px;
}
.region {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.84rem;
  line-height: 1.4;
}

/* Export + embed actions (Phase 4). */
.panel-actions {
  display: flex;
  gap: 6px;
  margin: 0 0 12px;
}
.act {
  border: 1px solid var(--border-soft);
  background: var(--bg-deep);
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.2px;
  padding: 5px 11px;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.15s var(--ease), border-color 0.15s var(--ease),
    background 0.15s var(--ease);
}
.act:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}
.act.on {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--bg-elevated);
}
.act:disabled {
  opacity: 0.55;
  cursor: progress;
}
.act-err {
  margin: -6px 0 12px;
  color: #f87171;
  font-size: 0.74rem;
}
.embed-box {
  margin: 0 0 14px;
  padding: 10px 12px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: var(--bg-deep);
}
.embed-hint {
  margin: 0 0 7px;
  color: var(--text-muted);
  font-size: 0.74rem;
}
.embed-code {
  display: block;
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 0.68rem;
  color: var(--text);
  word-break: break-all;
  line-height: 1.45;
  background: var(--bg-elevated);
  border-radius: 8px;
  padding: 8px 9px;
  margin-bottom: 8px;
}
.embed-copy {
  border: 1px solid var(--accent);
  background: transparent;
  color: var(--accent);
  font-size: 0.72rem;
  font-weight: 700;
  padding: 5px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s var(--ease), color 0.15s var(--ease);
}
.embed-copy:hover {
  background: var(--accent);
  color: #04120c;
}
.conn {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--text-faint);
  cursor: default;
}
.conn-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-faint);
}
.conn.ok {
  color: var(--teal);
}
.conn.ok .conn-dot {
  background: var(--teal);
  box-shadow: 0 0 6px var(--teal);
}
.conn.down {
  color: #f87171;
}
.conn.down .conn-dot {
  background: #f87171;
}

/* Biome identity card, keyed to the biome's map colour. */
.biome {
  display: flex;
  align-items: center;
  gap: 11px;
  margin: 0 0 12px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--biome) 8%, var(--bg-elevated));
  border: 1px solid color-mix(in srgb, var(--biome) 35%, transparent);
}
.biome-dot {
  flex: none;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--biome);
  box-shadow: 0 0 10px var(--biome);
}
.biome-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  margin-right: auto;
}
.biome-name {
  font-size: 0.98rem;
  font-weight: 700;
  color: var(--text);
}
.biome-sub {
  font-size: 0.7rem;
  color: var(--text-muted);
}
.biome-badge {
  flex: none;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 999px;
  color: color-mix(in srgb, var(--biome) 80%, var(--text));
  border: 1px solid color-mix(in srgb, var(--biome) 40%, transparent);
  background: color-mix(in srgb, var(--biome) 10%, transparent);
  cursor: help;
}
.biome-badge.inferred {
  color: var(--text-muted);
  border-color: var(--border);
  background: var(--bg-deep);
}

/* Compact stat cards: area + intactness side by side. */
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 0 0 18px;
}
.stat:only-child {
  grid-column: 1 / -1;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
}
.stat .k {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-faint);
}
.stat .v {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text);
}
.stat .v em {
  font-style: normal;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-muted);
}
.stat-sub {
  font-size: 0.68rem;
  color: var(--text-muted);
}
.intact-track {
  display: block;
  height: 5px;
  margin: 3px 0 1px;
  border-radius: 999px;
  background: var(--bg-deep);
  overflow: hidden;
}
.intact-bar {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), var(--forest-overlay));
  box-shadow: 0 0 10px -2px var(--accent);
}

.state {
  padding: 18px 0;
  color: var(--text-muted);
}
.state.err {
  color: #f87171;
}

/* loading skeleton */
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 8px 0;
}
.sk-line,
.sk-block,
.sk-hero,
.sk-row {
  border-radius: var(--radius-sm);
  background: linear-gradient(
    100deg,
    var(--bg-elevated) 30%,
    var(--border) 50%,
    var(--bg-elevated) 70%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite linear;
}
.sk-line {
  height: 14px;
}
.sk-line.short {
  width: 60%;
}
.sk-row {
  height: 56px;
}
.sk-block {
  height: 84px;
}
.sk-hero {
  height: 110px;
  border-radius: var(--radius);
}
.sk-note {
  font-size: 0.8rem;
  color: var(--text-muted);
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

.yields {
  margin-top: 22px;
}
.yields h3 {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  margin: 6px 0 14px;
}
.yields h3 small {
  color: var(--text-faint);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}
.yields-scale {
  margin: -8px 0 14px;
  font-size: 0.68rem;
  font-style: italic;
  color: var(--text-faint);
}
.yields ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.yield-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  margin-bottom: 6px;
}
.yield-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.yield-label {
  color: var(--text);
}
.yield-share {
  margin-left: auto;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--text-faint);
}
.yield-num {
  color: var(--text-muted);
  font-weight: 600;
  font-size: 0.82rem;
}
.yield-track {
  height: 7px;
  border-radius: 999px;
  background: var(--bg-elevated);
  overflow: hidden;
}
.yield-bar {
  height: 100%;
  border-radius: 999px;
  transform-origin: left;
  animation: grow 0.6s var(--ease) both;
  box-shadow: 0 0 10px -2px currentColor;
}
@keyframes grow {
  from {
    transform: scaleX(0);
  }
}

.tev {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin: 24px 0 14px;
  padding: 18px 18px 14px;
  border-radius: var(--radius);
  background: radial-gradient(
      120% 140% at 0% 0%,
      rgba(45, 212, 191, 0.14),
      transparent 60%
    ),
    var(--bg-elevated);
  border: 1px solid rgba(45, 212, 191, 0.4);
  box-shadow: var(--shadow-glow);
  overflow: hidden;
}
.tev::after {
  content: '';
  position: absolute;
  right: -40px;
  top: -40px;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(45, 212, 191, 0.18), transparent 70%);
  pointer-events: none;
}
.tev-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--text-muted);
}
.tev-value {
  font-size: 2.4rem;
  font-weight: 800;
  line-height: 1.05;
  margin: 2px 0;
  background: linear-gradient(95deg, var(--accent), var(--forest-overlay));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.tev-unit {
  font-size: 0.76rem;
  color: var(--text-muted);
}
.tev-annual {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-top: 12px;
  padding-top: 11px;
  border-top: 1px dashed color-mix(in srgb, var(--accent) 30%, transparent);
  width: 100%;
}
.tev-annual-v {
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--gold);
}
.tev-annual-k {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.asset {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0 0 16px;
  padding: 14px 16px;
  border-radius: var(--radius);
  background: radial-gradient(120% 140% at 100% 0%, rgba(231, 200, 115, 0.14), transparent 60%),
    var(--bg-elevated);
  border: 1px solid rgba(231, 200, 115, 0.4);
}
.asset-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.asset-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--text-muted);
}
.asset-rates {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  border-radius: 999px;
}
.asset-rates button {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.68rem;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.15s var(--ease), background 0.15s var(--ease);
}
.asset-rates button.on {
  background: var(--gold);
  color: #1c1606;
}
.asset-value {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 1.9rem;
  font-weight: 800;
  line-height: 1.05;
  color: var(--gold);
}
.asset-value em {
  font-style: normal;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
}
.asset-sub {
  font-size: 0.72rem;
  color: var(--text-muted);
  line-height: 1.4;
  cursor: help;
}

.conversion {
  margin: 18px 0;
  padding: 16px;
  border-radius: var(--radius);
  background: linear-gradient(180deg, rgba(248, 113, 113, 0.06), transparent),
    var(--bg-elevated);
  border: 1px solid rgba(248, 113, 113, 0.32);
}
.conv-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.conversion h3 {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.3px;
  color: #f8a8a8;
}
.conv-modes {
  display: flex;
  gap: 4px;
}
.conv-modes button {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s var(--ease), background 0.15s var(--ease), border-color 0.15s var(--ease);
}
.conv-modes button.on {
  background: rgba(248, 113, 113, 0.18);
  border-color: rgba(248, 113, 113, 0.6);
  color: #f8a8a8;
}
.liab {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.liab-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
}
.liab-value {
  font-family: 'Spline Sans Mono', ui-monospace, monospace;
  font-size: 1.7rem;
  font-weight: 800;
  line-height: 1.05;
  color: #f87171;
}
.liab-value em {
  font-style: normal;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
}
.liab-sub {
  margin-top: 4px;
  font-size: 0.74rem;
  color: var(--text-muted);
  line-height: 1.45;
}
.systemic-tag,
.carbon-debt {
  margin-top: 12px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-deep);
  border: 1px solid var(--border-soft);
  font-size: 0.74rem;
  color: var(--text-muted);
  line-height: 1.45;
}
.systemic-tag strong {
  color: var(--accent);
}
.redlines {
  margin-top: 12px;
  padding: 11px 13px;
  border-radius: var(--radius-sm);
  background: rgba(248, 113, 113, 0.07);
  border: 1px solid rgba(248, 113, 113, 0.28);
}
.rl-head {
  display: block;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: #f8a8a8;
  margin-bottom: 7px;
  cursor: help;
}
.redlines ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.redlines li {
  font-size: 0.74rem;
  color: var(--text);
  line-height: 1.4;
}
.redlines li strong {
  color: #f8a8a8;
}

.callout {
  position: relative;
  margin: 16px 0;
  padding: 14px 16px 14px 18px;
  border-left: 3px solid var(--accent);
  background: var(--bg-elevated);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--text);
}
.callout-mark {
  color: var(--accent);
  font-size: 1.4rem;
  font-weight: 800;
  line-height: 0;
  margin-right: 2px;
  vertical-align: -0.2em;
}

.method {
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft);
}
.method summary {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-faint);
  cursor: pointer;
  user-select: none;
  transition: color 0.18s var(--ease);
}
.method summary:hover {
  color: var(--text-muted);
}
.method p {
  margin: 8px 0 0;
  font-size: 0.72rem;
  color: var(--text-faint);
  font-style: italic;
  line-height: 1.5;
}
</style>
