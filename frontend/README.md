# alpha — frontend

Full-screen Leaflet world map for `alpha`. Built with **Vue 3 + Vite**. Part of
the [`alpha`](../README.md) monorepo.

## What it does (Phase 1)

- Renders a full-screen Leaflet map on a dark basemap.
- Overlays the **4 major rainforest biomes** as green polygons (Amazon, Congo,
  Southeast Asia, Central America) from `src/data/rainforests.js`.
- On region click: confirms backend connectivity via `GET /health`, then `POST`s
  the region polygon to `/api/v1/valuation` and renders a **side panel** with the
  area, the 5 ecosystem-service yields, the **Total Ecosystem Value (TEV)**, and a
  GDP-comparison callout.
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
├── vite.config.js          # dev server + /api, /health proxy
└── src/
    ├── main.js
    ├── theme.css           # dark-default palette + .light override
    ├── App.vue             # topbar, theme toggle, fetch orchestration
    ├── components/
    │   ├── WorldMap.vue    # Leaflet map + green region overlays
    │   └── SidePanel.vue   # TEV breakdown + GDP callout
    └── data/
        └── rainforests.js  # hardcoded GeoJSON + metadata for the 4 biomes
```
