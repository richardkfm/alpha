<script setup>
import { ref, onMounted } from 'vue'

// ----- catalogue -----------------------------------------------------------
const catalog = ref(null)
const loading = ref(false)
const error = ref('')

const STATUS_META = {
  authoritative: { label: 'Authoritative', color: 'var(--forest-overlay)' },
  reference: { label: 'Reference', color: 'var(--teal)' },
  placeholder: { label: 'Placeholder', color: 'var(--gold)' },
}
function statusMeta(s) {
  return STATUS_META[s] || { label: s, color: 'var(--text-muted)' }
}

async function loadCatalog() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/v1/datasets')
    if (!res.ok) throw new Error(`datasets HTTP ${res.status}`)
    catalog.value = await res.json()
  } catch (e) {
    error.value = 'Could not load the data catalogue from the alpha backend.'
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
    esvError.value = 'Extraction failed. Is the backend running?'
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
    clsError.value = 'That is not valid JSON. Paste a GeoJSON Polygon geometry.'
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
    clsError.value = 'Classification failed. Check the geometry and the backend.'
  } finally {
    clsLoading.value = false
  }
}

onMounted(loadCatalog)
</script>

<template>
  <section class="hub">
    <div class="hub-inner">
      <header class="hub-head">
        <h2>Data Hub</h2>
        <p>Every input behind a valuation — where it comes from, how current it is, and what we still need.</p>
      </header>

      <div v-if="loading" class="hub-state">Loading data catalogue…</div>
      <div v-else-if="error" class="hub-state err">{{ error }}</div>

      <template v-else-if="catalog">
        <!-- Sources -->
        <h3 class="section-title">Data sources</h3>
        <div class="cards">
          <article v-for="d in catalog.domains" :key="d.id" class="card">
            <div class="card-top">
              <span class="card-label">{{ d.label }}</span>
              <span class="badge" :style="{ '--c': statusMeta(d.status).color }">
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
              <span v-if="d.as_of" class="asof">as of {{ d.as_of }}</span>
              <span v-for="ep in d.exposed_via" :key="ep" class="endpoint">{{ ep }}</span>
            </div>
          </article>
        </div>

        <!-- Roadmap -->
        <h3 class="section-title">Data we still need</h3>
        <div class="needs">
          <article v-for="n in catalog.needs" :key="n.id" class="need">
            <div class="need-head">
              <span class="need-label">{{ n.label }}</span>
              <span class="phase">{{ n.phase }}</span>
            </div>
            <div class="need-flow">
              <span class="now">{{ n.current }}</span>
              <span class="arrow">→</span>
              <span class="next">{{ n.planned }}</span>
            </div>
            <p class="need-why">{{ n.why }}</p>
          </article>
        </div>

        <!-- Live tools -->
        <h3 class="section-title">Live tools</h3>
        <div class="tools">
          <!-- ESV extractor -->
          <article class="tool">
            <h4>Extract ESV values from text</h4>
            <p class="tool-sub">Pulls structured ecosystem-service values out of report / TNFD-disclosure prose.</p>
            <textarea v-model="esvText" rows="4" spellcheck="false"></textarea>
            <button class="run" :disabled="esvLoading" @click="runExtract">
              {{ esvLoading ? 'Extracting…' : 'Extract' }}
            </button>
            <div v-if="esvError" class="tool-err">{{ esvError }}</div>
            <div v-else-if="esvResult" class="tool-out">
              <div class="out-meta">
                <span class="chip">{{ esvResult.count }} record(s)</span>
                <span class="chip">backend: {{ esvResult.backend }}</span>
                <span v-if="esvResult.fallback_reason" class="chip warn">fallback</span>
              </div>
              <table v-if="esvResult.records && esvResult.records.length">
                <thead>
                  <tr><th>Service</th><th>Value</th><th>Cur.</th><th>Unit</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(r, i) in esvResult.records" :key="i">
                    <td>{{ r.service || r.raw_service || '—' }}</td>
                    <td class="num">{{ r.value ?? '—' }}</td>
                    <td>{{ r.currency || '—' }}</td>
                    <td>{{ r.unit || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="tool-empty">No structured values found in that text.</p>
            </div>
          </article>

          <!-- Biome classifier -->
          <article class="tool">
            <h4>Classify a polygon's biome</h4>
            <p class="tool-sub">Locates a GeoJSON polygon in the ingested boundary data and returns the detected biome + provenance.</p>
            <textarea v-model="geoText" rows="4" spellcheck="false"></textarea>
            <button class="run" :disabled="clsLoading" @click="runClassify">
              {{ clsLoading ? 'Classifying…' : 'Classify' }}
            </button>
            <div v-if="clsError" class="tool-err">{{ clsError }}</div>
            <div v-else-if="clsResult" class="tool-out">
              <div class="cls-biome">{{ clsResult.classification.biome_label }}</div>
              <div class="out-meta">
                <span class="chip">confidence: {{ clsResult.classification.confidence }}</span>
                <span v-if="clsResult.classification.matched_region" class="chip">
                  matched: {{ clsResult.classification.matched_region }}
                </span>
              </div>
              <p class="cls-src">{{ clsResult.boundary_dataset.primary }}</p>
            </div>
          </article>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.hub {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  padding: 70px 18px 28px;
  background: radial-gradient(circle at 30% 8%, #0a1424 0%, var(--bg) 70%);
}
.hub-inner {
  max-width: 1080px;
  margin: 0 auto;
}
.hub-head h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text);
}
.hub-head p {
  margin: 5px 0 0;
  color: var(--text-muted);
  font-size: 0.86rem;
}
.hub-state {
  padding: 40px 0;
  color: var(--text-muted);
}
.hub-state.err {
  color: #f87171;
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
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
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
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
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
  color: #04120c;
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
  font-size: 0.78rem;
  color: #f87171;
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
