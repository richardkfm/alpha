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
- **Dark/light theme toggle** — dark is default (deep greens, teal accents).

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

## Structure

```
frontend/
├── index.html
├── vite.config.js              # dev server + /api, /health proxy
└── src/
    ├── main.js
    ├── theme.css               # dark-default palette + .light override
    ├── App.vue                 # topbar, modes, theme toggle, fetch orchestration
    ├── components/
    │   ├── GlobeMap.vue        # 3D MapLibre globe overlays
    │   ├── WorldMap.vue        # 2D Leaflet map overlays
    │   ├── LayerControl.vue    # biome toggles + display-style switch
    │   ├── SearchBar.vue       # value a custom coordinate / box / GeoJSON
    │   ├── SidePanel.vue       # TEV breakdown + GDP callout
    │   ├── CompareDashboard.vue# side-by-side TEV comparison
    │   └── DataHub.vue         # data catalogue + live tools
    └── data/
        ├── useRegions.js       # fetches + derives the region catalogue
        ├── biomeMeta.js        # per-biome palette + legend order
        ├── yields.js           # yield-category metadata
        └── geo.js              # centroid + search-input parsing helpers
```
