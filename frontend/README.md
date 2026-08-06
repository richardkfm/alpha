# alpha — frontend

Full-screen geospatial UI for `alpha`. Built with **Vue 3 + Vite**, with a 3D
MapLibre globe and a 2D Leaflet map. Part of the
[`alpha`](../README.md) monorepo.

## What it does

- **Map** mode renders the ecosystem catalogue as a hero **3D MapLibre globe**
  (auto-spinning) with a 2D **Leaflet** "flat" alternative. Named ecosystems
  across all of alpha's valuation biomes are drawn as colour-coded, separately
  toggleable layers, fetched pre-valued from the backend (`GET /api/v1/regions`)
  rather than hardcoded.
- A **display-style switch** (Layers panel) renders the same areas as filled
  **polygons**, value-proportional **bubbles**, or a value-weighted **heat**
  layer.
- On region click: confirms backend connectivity via `GET /health`, then `POST`s
  the polygon to `/api/v1/valuation` and renders a **side panel** with the area,
  the detected biome, land-cover intactness, the 5 ecosystem-service yields, the
  **Total Ecosystem Value (TEV)**, the capitalised standing-asset value, the
  conversion-liability reframing, and a GDP-comparison callout.
- **Compare** mode puts several ecosystems' TEV breakdowns side by side.
- **Data Hub** mode surfaces every data domain's source/status/as-of (from
  `GET /api/v1/datasets`) plus live ESV-extraction and biome-classification tools.
- A **search bar** values any custom area — `lat, lng`, a `w, s, e, n` box, or a
  pasted GeoJSON polygon.
- **Currency toggle** (USD / EUR / BRL) re-prices everything via the backend.
- **Language toggle** (EN / DE / ES) — translates the UI and switches every
  figure to that locale's number conventions. See
  [Numbers & localisation](#numbers--localisation).
- **Dark/light theme toggle** — dark is default (deep greens, teal accents).
- **Export & embed** (Phase 4): the side panel offers ↓ CSV / ↓ PDF investor
  reports (`POST /api/v1/valuation/export`) and an **Embed** snippet. The
  embeddable widget is a separate, lightweight Vite entry (`embed.html` →
  `src/embed.js` → `EmbedCard.vue`) so the iframe skips the globe bundle.

## Run with Docker (recommended)

From the repo root:

```bash
docker compose up --build
```

App: http://localhost:3000

## Run standalone (local dev)

The dev server proxies `/api` and `/health` to the backend. For a backend on the
host, point the proxy at it via `BACKEND_ORIGIN`:

```bash
npm install
BACKEND_ORIGIN=http://localhost:8000 npm run dev
```

App: http://localhost:3000

## Tests

```bash
npm test
```

Vitest, no jsdom — the formatters in `src/data/formatNumber.js` are deliberately
pure so they can be tested without a Vue component context. The suite is mostly
a locale × magnitude table; see below for what it is guarding.

## Numbers & localisation

Every figure in the app goes through `src/data/formatNumber.js` (pure) via
`src/data/useFormat.js` (binds the active locale and the region's currency).
Two rules hold it together:

- **Scale words are never hand-rolled.** English *billion* is 10⁹, German
  *Billion* is 10¹² (10⁹ is a *Milliarde*), and Spanish has no short form for
  10⁹ at all — `1.5e9` is `$1.5B` in English, `1,5 Mrd. €` in German and
  `1500 M R$` in Spanish. A `K/M/B/T` suffix table would render a €1.5 Mrd.
  figure as "1,5 Bio.", wrong by a factor of 1000 on a financial disclosure.
  CLDR gets every locale right, so `Intl`'s compact notation supplies the word.
- **Nothing reaches the DOM unformatted.** German writes one thousand as
  `1.000` and one-and-a-half as `1,5` — the inverse of English. A number
  interpolated raw into an i18n message reads off by a factor of 1000 to half
  the users. `formatNumber.test.js` pins both the scale words and the
  separators per locale.

Abbreviation kicks in at 1,000,000 (`COMPACT_FROM`); below that CLDR drops
thousands grouping, and "45,7 Tsd." reads worse than "45.678" anyway. Every
abbreviated figure carries the exact value in a `title` and an `aria-label`.

Per-service yields are stored and served **per m²** but displayed **per
hectare** (`formatPerHa` scales by `SQM_PER_HA` at the formatting boundary
only) — per-m² figures are sub-cent and unreadable.

### Human-scale comparisons

Formatting makes a figure legible; it does not make it comprehensible. Each of
the side panel's three hero numbers therefore carries a one-line anchor to
something the reader already has a feel for, via `src/data/useComparison.js`.

The backend ships a ranked, language-free shortlist per figure
(`valuation.comparisons`) and this picks from it, because the anchor a reader
relates to depends on their language and `POST /api/v1/valuation` takes no
locale — threading one through would mean re-fetching the whole valuation on
every language switch. Three rules:

- **Locale preference.** A German reader gets the EU budget over the UK's GDP,
  unless the local anchor fits markedly worse. A tag means "extra resonant
  here", not "off-limits to everyone else", so with no match we simply take the
  best-reading anchor.
- **Rescaling.** The discount-rate buttons recapitalise the standing asset
  client-side, so its multiple is rescaled and the shortlist re-ranked — a
  comparison still quoting the 3% ratio at 1% would be wrong.
- **No repeats.** The standing asset and the conversion liability are both
  stocks of a similar size sitting inches apart, so whatever the asset used is
  excluded from the liability's choice. The backend does this too, but only for
  the anchor *it* would have picked; once the locale preference chooses
  differently that guard misses.

Multiples under 1 render as a percentage (`40 %`, not `0,4×`), and everything
goes through `formatNumber` so the decimal separator follows the locale.

The embed card is the one exception to `useFormat`: `embed.js` skips vue-i18n
to keep the iframe bundle small, so `EmbedCard.vue` calls the pure formatters
directly and takes its locale from `?locale=`.

## Structure

```
frontend/
├── index.html
├── embed.html                  # lightweight embeddable-widget entry (Phase 4)
├── vite.config.js              # dev server + /api, /health proxy; 2 build entries
└── src/
    ├── main.js
    ├── embed.js                # entry for embed.html — mounts EmbedCard only
    ├── theme.css               # dark-default palette + .light override
    ├── App.vue                 # topbar, modes, theme toggle, fetch orchestration
    ├── components/
    │   ├── GlobeMap.vue        # 3D MapLibre globe overlays
    │   ├── WorldMap.vue        # 2D Leaflet map overlays
    │   ├── LayerControl.vue    # biome toggles + display-style switch
    │   ├── SearchBar.vue       # value a custom coordinate / box / GeoJSON
    │   ├── SidePanel.vue       # TEV breakdown + GDP callout + export/embed
    │   ├── EmbedCard.vue       # compact single-region widget (the iframe body)
    │   ├── CompareDashboard.vue# side-by-side TEV comparison
    │   └── DataHub.vue         # data catalogue + live tools
    ├── i18n/
    │   ├── index.js            # vue-i18n setup; locale persisted to localStorage
    │   └── locales/            # en.json, de.json, es.json
    └── data/
        ├── useRegions.js       # fetches + derives the region catalogue
        ├── biomeMeta.js        # per-biome palette + legend order
        ├── useBiomeMeta.js     # translated biome labels over biomeMeta
        ├── yields.js           # yield-category metadata
        ├── yieldScale.js       # cross-biome bar ceilings (panel + Compare)
        ├── useCountUp.js       # eases headline KPIs toward their value
        ├── formatNumber.js     # pure locale-correct number/currency formatting
        ├── formatNumber.test.js
        ├── useFormat.js        # binds formatNumber to the active locale
        ├── useComparison.js    # "≈ 2,7× Staatsschulden Deutschlands"
        ├── useComparison.test.js
        └── geo.js              # centroid + search-input parsing helpers
```
