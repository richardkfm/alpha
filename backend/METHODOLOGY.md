# alpha — Valuation Methodology (Phase 2)

This document explains how the `POST /api/v1/valuation` endpoint turns a GeoJSON
polygon into a **Total Ecosystem Value (TEV)**. Every formula and reference value
is documented here and in the code (`backend/valuation.py`,
`backend/reference_data.py`).

> **Status:** Phase 2 uses documented, peer-reviewed *reference values* per biome.
> They are scientifically defensible estimates, **not** live measurements. Phase 3
> replaces the static biome lookup with real land-cover classification; Phase 4
> wires carbon prices and FX rates to live feeds.

---

## 1. Area

The polygon area is computed geodesically (not in planar degrees) using the
spherical-excess formula (Chamberlain & Duquette, JPL — the same algorithm used
by OpenLayers and Google Maps geometry), on a sphere of mean Earth radius
`R = 6,371,008.8 m` (IUGG).

For a `Polygon`, the area is the exterior ring minus any holes; for a
`MultiPolygon`, it is the sum over member polygons. Result in **m²**, with
hectares = m² ÷ 10,000.

See `geodesic_area_sqm()` in `valuation.py`.

---

## 2. Yield categories

All reference values are stored as **USD per hectare per year** and converted to
**USD per m² per year** by dividing by 10,000.

| Category | Formula | Source |
| --- | --- | --- |
| **Carbon Capture** | `sequestration (tCO₂/ha/yr) × carbon price (USD/tCO₂) ÷ 10,000` | Pan et al. 2011 (net forest sink); IPCC AR6 WGIII 2022 (carbon price) |
| **Climate Regulation** | ESVD climate-regulation reference (USD/ha/yr) ÷ 10,000, excluding the carbon already counted | de Groot et al. 2012; Costanza et al. 2014 |
| **Water Filtration** | ESVD water purification + flow regulation (USD/ha/yr) ÷ 10,000 | de Groot et al. 2012 (ESVD) |
| **Biodiversity Premium** | ESVD genetic resources + habitat/refugia (USD/ha/yr) ÷ 10,000 | de Groot et al. 2012 (ESVD) |
| **Soil Nutrient Value** | ESVD erosion prevention + soil-fertility maintenance (USD/ha/yr) ÷ 10,000 | de Groot et al. 2012 (ESVD) |

**Carbon price:** a single transparent reference of **$30/tCO₂** is applied to
every biome's sequestration rate. It sits between voluntary nature-based credit
prices (~$10–15) and central social-cost-of-carbon / compliance estimates ($50+),
within the IPCC AR6 WGIII range for sub-2 °C pathways.

### Total

```
TEV_per_sqm_year = Σ (five category yields, per m²/yr)
TEV_per_year     = TEV_per_sqm_year × area_sqm
```

Both the per-m² and area-scaled totals are returned, per category and in total.

---

## 3. Biome reference table

Reference values (USD/ha/yr unless noted) live in `reference_data.py::BIOMES`.
Values are deliberately conservative (lower-to-mid of published ranges).

| Biome | Sequestration (tCO₂/ha/yr) | Climate | Water | Biodiversity | Soil |
| --- | --- | --- | --- | --- | --- |
| Tropical Rainforest | 2.3 | 360 | 200 | 500 | 120 |
| Temperate Forest | 1.5 | 250 | 150 | 250 | 100 |
| Mangrove | 6.0 | 500 | 900 | 800 | 300 |
| Inland Wetland | 1.0 | 400 | 3,000 | 1,200 | 250 |
| Temperate Grassland | 0.5 | 80 | 60 | 120 | 200 |

The default biome is `tropical_rainforest`. Phase 3 will select the biome from
real land-cover data instead of defaulting/accepting it as input.

---

## 4. Currency

The engine returns values in **USD** (default), **EUR**, or **BRL**. Conversion
uses indicative static rates relative to USD (`reference_data.py::CURRENCIES`,
`as_of` 2025-12). Select via the `currency` query parameter or request-body
field. Phase 4 connects to a live FX source.

---

## 5. Worked example

A 1 ha (10,000 m²) tropical-rainforest polygon, in USD:

```
carbon_capture      = 2.3 × 30 / 10,000   = 0.0069  USD/m²/yr  →  69    USD/yr
climate_regulation  = 360 / 10,000        = 0.0360  USD/m²/yr  →  360   USD/yr
water_filtration    = 200 / 10,000        = 0.0200  USD/m²/yr  →  200   USD/yr
biodiversity_premium= 500 / 10,000        = 0.0500  USD/m²/yr  →  500   USD/yr
soil_nutrient_value = 120 / 10,000        = 0.0120  USD/m²/yr  →  120   USD/yr
------------------------------------------------------------------------------
TEV                 = 0.1249 USD/m²/yr    →  1,249 USD/yr for the hectare
```

---

## References

- de Groot, R. et al. (2012). *Global estimates of the value of ecosystems and
  their services in monetary units.* Ecosystem Services 1(1): 50–61.
- Costanza, R. et al. (2014). *Changes in the global value of ecosystem services.*
  Global Environmental Change 26: 152–158.
- Pan, Y. et al. (2011). *A Large and Persistent Carbon Sink in the World's
  Forests.* Science 333(6045): 988–993.
- IPCC AR6 WGIII (2022), Ch. 7 & Annex III.
- ESVD — Ecosystem Services Valuation Database (esvd.net).
