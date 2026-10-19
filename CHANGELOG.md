# Changelog

All notable changes to `alpha` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions are shared by the backend and frontend and track the phase in
[`ARCHITECTURE.md`](./ARCHITECTURE.md): `0.4.x` is the Phase 4 API & export
layer.

This file starts at 0.4.0. Earlier phases predate it and are described in
`ARCHITECTURE.md` rather than reconstructed here.

## [Unreleased]

### Data & accuracy

- **Full recalibration of every biome coefficient** (`backend/reference_data.py`,
  `backend/METHODOLOGY.md`). Non-carbon values are now derived in code from the
  published ESVD table cells they rest on (Brander et al. 2024; de Groot et al.
  2012 medians), on a median basis, with ≥3 value estimates per cell. All figures
  are restated in **2024 USD** (BLS CPI-U). The 15 of 55 coefficients without
  enough evidence are kept as **flagged estimates**, and every valuation now
  reports `basis` / `evidence_n` / `price_year` per category. TEV per hectare
  moved substantially: rainforest −37%, mangrove +237%, wetland −67%,
  freshwater −72%, peri-urban +344% (table in METHODOLOGY §10).
- **Carbon price $40 → $80/tCO2** (2024 USD): the low end of the IPCC AR6 WGIII
  2 °C-pathway range for 2030, close to the 2025 EU ETS average. The old
  justification was wrong on two counts: $40 was below the AR6 range, and
  China's ETS was quoted at ~$30–40 when it trades at ~$9.
- **Sequestration** now comes from Pan et al. 2024 (forests: tropical 2.4,
  temperate 3.2, boreal 1.0 tCO2/ha/yr) and the IPCC 2013 Wetlands Supplement
  (mangrove 5.9). Cropland (IPCC Tier 1) and tundra (Natali et al. 2019) are set
  to 0.
- **Carbon debt** no longer assumes the entire 1 m soil stock is released. It is
  now vegetation × intactness plus soil × an IPCC-based release fraction, with
  pools from IPCC SRLULUCF / the Wetlands Supplement.
- **Double counting and scope fixes:** ESVD "climate regulation" (carbon) is no
  longer counted on top of carbon capture, and drinking-water supply
  (provisioning) no longer inflates freshwater.
- **Static FX refreshed** to the ECB 2026-10-16 rates (EUR 0.8887, BRL 5.0828).
  The old EUR 0.92 "2025-12" rate was stale.
- **Land-cover legend** (`backend/landcover.py`) now hints at the
  boreal/cropland/freshwater/tundra/desert biomes. Optional biome-aware
  intactness stops a biome's own natural cover (e.g. bare ground in a desert)
  being scored as degraded.
- **Data Hub provenance** (`backend/datasets.py`, `live_data.py`) cites the
  new sources and dates. New `tests/test_reference_data.py` pins every
  coefficient and checks unit, FX and CPI round-trips and totals = Σ services.

### Changed

- **Carbon price reference bumped $30 → $40/tCO2** (`backend/reference_data.py`,
  `backend/METHODOLOGY.md`). Compliance-market prices have moved well past the
  2022 IPCC AR6 anchor since — EU ETS has been trading at ~$65-95/tCO2 through
  2025-2026 — so the old figure was understating carbon-capture yield by a
  wide margin. Still a static, blended reference (not EU-ETS-pinned, since the
  app values land worldwide), just a less stale one.
- **`CARBON_PRICE_URL` now understands most providers' payloads as-is**
  (`backend/live_data.py`): recognises common field names (`price`, `value`,
  `price_usd_per_tco2`, …) and common nesting (`{"data": [...]}`), and rejects
  a response outside a $1-500/tCO2 plausibility band instead of trusting it
  blindly — falls back to the static reference either way. `docker-compose.yml`
  and `.env.example` now pass `CARBON_PRICE_URL` / `CARBON_PRICE_USD_PER_TCO2`
  through, and document candidate free/keyed providers; previously these were
  only mentioned in the module's docstring and had no effect via `.env`. There
  is still no single free, keyless, officially-documented carbon spot feed to
  default to the way Frankfurter is for FX, so an operator still has to wire
  one in.

### Added

- **Ranked live carbon-price provider recommendation.** `backend/live_data.py`'s
  docstring and `.env.example` now name a specific order to try for
  `CARBON_PRICE_URL` — Trading Economics' "EU Carbon Permits" first (free
  guest tier, single-symbol JSON works with this module as-is, but prices in
  EUR), Nasdaq Data Link's `CHRIS/ICE_C1` EUA futures dataset second (needs a
  small shim), and the World Bank Carbon Pricing Dashboard for periodically
  refreshing the *static* reference price rather than live wiring — instead
  of a flat, unranked candidate list. None have been reachable from this
  project's sandboxed sessions to verify live, so this is evaluated on paper;
  verify against the provider's current docs before relying on one.
- **Case-insensitive field matching in the live carbon-price parser**
  (`_extract_carbon_price`): several real providers (Trading Economics
  included) title-case their JSON keys (`"Last"`, `"Close"`), which the
  previous lowercase-only match would have silently missed, falling back to
  the static reference with no error.
- **Build/version footer.** A small `v0.4.0` marker now sits in the bottom
  corner of the map (`frontend/src/App.vue`), sourced from `package.json` at
  build time, so a deployed instance can be confirmed at a glance. `GET
  /health` now also echoes the API's own version; if the two ever diverge
  (mid-deploy, or a stale cached frontend) the footer appends `· api vX.Y.Z`
  instead of hiding the mismatch.
- **Human-scale comparisons on the headline figures.** Each of the three hero
  numbers in the side panel now carries a one-line anchor to something the
  reader already has a feel for — `≈ 2,7× Staatsschulden Deutschlands`. The
  formatting work made these figures legible; this makes them comprehensible.
  - Anchors live in `backend/scale_anchors.py` as dated, sourced reference data
    and are listed in the Data Hub like every other input. `POST
    /api/v1/valuation` returns a language-free shortlist per figure; the UI
    renders the phrase from its own i18n catalogue, so no English leaks into a
    translated panel.
  - **Flows are only ever compared to flows and present values to present
    values.** Total Ecosystem Value is a per-year flow while the standing asset
    and conversion liability are stocks; comparing a present value to a
    country's annual GDP would be an apples-to-oranges error.
  - Anchor choice follows the reader's language — a German reader gets the EU
    budget or Germany's national debt, an English reader US or UK figures —
    falling back to the best-fitting anchor when nothing is tagged for them.
  - Figures below ~1 billion USD get no comparison at all. `0.000002× Austria's
    GDP` is worse than saying nothing.
  - The PDF brief carries the same cue next to each headline row.

### Design & UI

- **First-run guide.** A short, dismissible orientation card explains what to
  click, what the three headline figures mean (standing asset, annual TEV,
  conversion liability), how to value a custom area and where display styles,
  Compare and the Data Hub live. Shown once, re-openable from a new **?**
  button in the topbar; Esc or a backdrop click closes it.
- **Loading, empty and error states everywhere.** Backend-unreachable now shows
  a card with a **Try again** button instead of a bare red line; the side panel
  error, Data Hub and Compare all get retry actions; a failed currency re-price
  keeps the last good figures and shows a small notice instead of blanking the
  map; Compare says when a search matches nothing (with "Clear search"), shows
  an "n / 5 selected" counter and explains the cap; the Data Hub says in words
  when live market feeds have fallen back to static references.
- **Fully localised UI.** Compare, Data Hub, globe controls, search errors and
  the embeddable card were English-only; every string now goes through the
  en/de/es catalogues. The embed card lazy-loads just its one locale.
- **Design tokens.** `theme.css` gains a spacing scale, type scale, pill radius,
  semantic status colours (`--danger`, `--warn`, `--accent-bg`, `--gold-bg`, …),
  `--on-accent`, `--stage-bg` and topbar/map-control offsets; hard-coded hex and
  rgba colours in components were replaced with them. Buttons and inputs now
  inherit Inter.
- **Light theme fixed and legible.** Compare, Data Hub, the loading stage and the
  globe no longer paint a dark navy blob behind light-theme content; the flat
  map switches to the light Positron basemap; light accent, gold, faint-text
  and danger colours were darkened for contrast on white. The theme choice is
  remembered per browser.
- **Layout & discoverability.** Mode buttons carry tooltips; the Biomes panel is
  collapsible (collapsed by default on phones), labels its display-style switch
  and states what the active style encodes; Outline shows a spinner while
  detailed borders load. Zoom controls no longer hide under the topbar, clicked
  flat-map shapes lose the stray focus rectangle, the 3D column caption no
  longer sits under the Biomes panel, and the search bar re-centres beside an
  open side panel. Data Hub content scrolls below the topbar instead of under
  it. On phones the topbar wraps to a scrollable control strip and Compare
  stacks vertically. Map / Compare / Data switch with a short fade.
- **Keyboard.** Esc closes the guide, then the side panel; inside the search
  field it clears the input first. Toggle buttons expose `aria-pressed`.

### Bug fixes

- **API input validation:** malformed GeoJSON (empty rings, non-numeric or NaN
  positions, latitudes outside ±90°) now gets a `422` instead of a `500` or a
  nonsense area, and an unknown explicit `biome` is a `422` rather than being
  silently valued as tropical rainforest.
- **Antimeridian-crossing polygons** (`178 … -179`) are valued and classified
  correctly — previously ~119× too large and located half a planet away. The
  frontend's centroid (globe fly-to, bubbles) got the same fix.
- **Exports:** region names with `<`, non-Latin scripts (`Москва`) or accents
  no longer crash the PDF/CSV download; the CSV neutralises formula-like names.
- **Live data:** an unreachable FX/carbon feed is remembered for 60 s instead
  of costing a 6 s timeout on every request; a `nan`/negative
  `CARBON_PRICE_USD_PER_TCO2` override is ignored.
- **ESV extraction:** a leading year (`In 2019, … $120 per ha`) is no longer
  taken as the value, ISO codes (`EUR 150`) are recognised, and a malformed
  LLM reply falls back to the regex extractor instead of a `500`.
- **`ingest.py`** works again (it imported a removed `DATA_PATH`).
- **UI races / stale state:** a slow valuation for a previously clicked region,
  or an out-of-order currency re-price, can no longer overwrite the current
  panel or catalogue; exports are named after the region actually exported;
  Compare seeds itself when opened before the catalogue arrives; a failed
  re-price keeps the map on screen.
- **Outline mode** now really draws the detailed RESOLVE ecoregion borders
  (both maps ignored the swapped geometry).
- **Side panel:** the conversion liability follows the selected discount rate
  like the standing asset it is a premium on; custom search areas no longer
  offer a broken embed snippet.
- **Embed widget:** an unsupported `?currency=` no longer crashes the card or
  mislabels dollar figures.
- **Search box:** rejects non-numeric input instead of dropping tokens, accepts
  a trailing comma, and range-checks bounding boxes.
- **Start-up:** blocked `localStorage` no longer prevents the app from loading.
- **Deployment:** `scripts/gen-env.sh` generates a URL-safe password (base64's
  `/` broke `DATABASE_URL`); the frontend image no longer copies a host
  `node_modules` and installs from the lockfile.

## [0.4.0]

### Added

- **Locale-correct number formatting across the UI.** Every figure now runs
  through a shared formatter (`frontend/src/data/formatNumber.js`, bound to the
  active locale by `useFormat.js`). Large amounts abbreviate above 1,000,000 and
  carry an exact-value tooltip and `aria-label`.
- **Locale-aware PDF export.** `POST /api/v1/valuation/export` takes
  `?locale=en|de|es`, which sets the brief's separators and currency-symbol
  placement (`1.234.567 €` vs `$1,234,567`). The PDF uses full digits — no
  abbreviations in a disclosure document. The CSV is unaffected and stays raw.
- **Frontend test suite.** `vitest`, plus `npm test`. The suite pins the
  scale-word and separator conventions per locale.
- Phase-4 export & embed: CSV/PDF investor reports and the embeddable
  single-region widget (`frontend/embed.html`).

### Changed

- **Per-hectare display.** The UI and the PDF report per-service yields per
  hectare rather than per m², since per-m² figures are sub-cent. The API
  contract and the CSV keep the raw per-sqm values.
- **The side panel leads with totals, not per-unit rates.** The standing-asset
  value moved above the yield breakdown, and the Total Ecosystem Value block's
  headline is the whole-area annual total; the per-hectare rate is still shown,
  demoted beneath it.
- The TEV headline carries its period on its own baseline (`212,5 Mrd. € / Jahr`)
  rather than in a caption underneath. The figures either side of it are stocks,
  so an unlabelled flow was a plausible misreading.

### Fixed

- **Scale words are no longer hand-rolled.** English *billion* is 10⁹ but German
  *Billion* is 10¹² (10⁹ is a *Milliarde*), and Spanish has no short form for
  10⁹ at all. All scale words now come from CLDR via `Intl`'s compact notation,
  so a €1.5 Mrd. figure can never render as "1,5 Bio." — a factor-of-1000 error
  on a financial disclosure.
- A compact scale word could fuse with the currency symbol on some ICU builds:
  Chromium 141 renders 1.2e12 in es/BRL as `1,2 BR$`, which reads as 1.2 reais
  rather than 1.2 trillion. The separator is now guaranteed regardless of the
  runtime's ICU version.
- The systemic-premium multiplier was interpolated into its sentence unformatted,
  so a German reader saw `×1.595 systemisch` — one thousand five hundred
  ninety-five, rather than 1.6.
- The PDF's discount rate used Python's `{:.1%}`, printing `@ 3.0%` beside
  comma-decimal money in an otherwise localised German report.
- Currency amounts no longer emit a stray `,0` from clamped fraction digits, and
  keep their thousands separators just below the abbreviation threshold.

[Unreleased]: https://github.com/richardkfm/alpha/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/richardkfm/alpha/releases/tag/v0.4.0
