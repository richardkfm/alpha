# alpha — Valuation Methodology

This document explains how the `POST /api/v1/valuation` endpoint turns a GeoJSON
polygon into a **Total Ecosystem Value (TEV)**. Every formula and reference value
is documented here and in the code (`backend/valuation.py`,
`backend/reference_data.py`). The non-carbon coefficients are *derived in code*
from the published table cells they rest on (`reference_data.ESV_EVIDENCE`), and
every valuation response reports, per category, whether its coefficient is
literature-based or a flagged estimate (`methodology.<category>.basis`).

> **Status:** the engine uses documented, peer-reviewed *reference values* per
> biome — global summary values, not site measurements. The biome is detected
> from real RESOLVE ecoregion boundaries, realised value is scaled by land-cover
> **intactness**, and carbon prices and FX rates can be wired to live feeds — see
> [`INGESTION.md`](./INGESTION.md) and `live_data.py`.
>
> **Recalibration (2026-10):** every coefficient was re-checked against the
> current literature (ESVD 2024 synthesis, Pan et al. 2024, IPCC defaults, IPCC
> AR6 WGIII) and restated in a single price year. TEV results shifted
> substantially; see [§10](#10-what-changed-in-the-2026-recalibration).

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

## 2. Units and price year

- All reference values are stored as **USD per hectare per year** and converted
  to **USD per m² per year** by dividing by 10,000.
- **Every USD figure is in 2024 US dollars.** Source values are restated with the
  US CPI-U annual average (BLS): 2007 = 207.342, 2015 = 237.017, 2020 = 258.811,
  2024 = 313.689. The ESVD reports PPP "international dollars" (Int$; 1 Int$ =
  1 USD in the US), so a US CPI adjustment is the standard way to bring them
  forward. (2007 → 2024: ×1.513; 2020 → 2024: ×1.212.)
- Carbon: tonnes of CO₂ (tCO₂). Carbon stocks are converted from tonnes of C with
  44/12.

---

## 3. Yield categories

| Category | What it counts (TEEB / ESVD services) | Formula |
| --- | --- | --- |
| **Carbon Capture** | Net CO₂ sequestration | `sequestration (tCO₂/ha/yr) × carbon price (USD/tCO₂) ÷ 10,000` |
| **Climate Regulation** | Air-quality regulation + moderation of extreme events (storm/flood buffering). ESVD "climate regulation" is **excluded**: it is predominantly carbon sequestration, already priced under Carbon Capture. | Σ evidence cells (USD/ha/yr) ÷ 10,000 |
| **Water Filtration** | Waste treatment / water purification + regulation of water flows | Σ evidence cells ÷ 10,000 |
| **Biodiversity Premium** | Habitat services (maintenance of life cycles / nursery, maintenance of genetic diversity / gene pool) + biodiversity-mediated regulation (pollination, biological control) + existence & bequest values (the non-use value of species and habitats) | Σ evidence cells ÷ 10,000 |
| **Soil Nutrient Value** | Erosion prevention + maintenance of soil fertility | Σ evidence cells ÷ 10,000 |

**Excluded:** provisioning services (food, drinking-water supply, raw materials,
genetic / medicinal / ornamental resources) and recreational, aesthetic and
cognitive cultural services. The figure represents the ecosystem value *lost
when the land is sealed or converted* — the quantity that is normally invisible
in a rezoning decision — not the land's market output.

### Total

```
TEV_per_sqm_year = Σ (five category yields, per m²/yr)
TEV_per_year     = TEV_per_sqm_year × area_sqm
```

Both the per-m² and area-scaled totals are returned, per category and in total.

---

## 4. How the non-carbon coefficients are derived

**Sources.**

- **A — de Groot et al. (2012), Online Supporting Information:** per biome ×
  service *median* (and mean), 2007 Int$/ha/yr, with the number of value
  estimates *n*. Covers tropical forests, temperate & boreal forests, coastal
  wetlands, inland wetlands, rivers & lakes, grasslands (and marine/woodland
  biomes alpha does not use).
- **B — Brander et al. (2024), Table 1:** the current ESVD synthesis (4,451
  standardised records). Per biome × service *mean*, 2020 Int$/ha/yr, with *n*.
  Covers every alpha biome except desert.
- **Skew adjustment for B — de Groot, Brander & Solomonides (2020), ESVD
  update report, Table 5:** all-biome mean and median per service (2020
  Int$/ha/yr). ESV distributions are heavily right-skewed: medians are 0.5–53%
  of means (e.g. waste treatment 250 vs 6,552; soil fertility 22 vs 4,199).

**Statistic: median.** The project's policy is conservative values
(lower-to-mid of published ranges). Means are dominated by a few high-value
study sites — and study sites are not a random sample of the world's land — so
alpha uses medians. For a Brander et al. 2024 cell, the median is approximated
as *mean × (ESVD-2020 median ÷ mean for that service)*. That transfer assumes a
biome's skew resembles the all-biome skew; it is an approximation.

**Rule, per biome × service cell:**

1. A candidate is admissible only if it rests on **≥ 3 value estimates**.
2. Of the admissible candidates (A median, B median-equivalent), the one backed
   by more estimates wins; a tie goes to A (a true median).
3. A category = Σ of its admissible cells, in 2024 USD, rounded to whole dollars.
4. A category with **no admissible cell keeps its previous value as a flagged
   estimate** (`reference_data.ESV_EVIDENCE` / `ESV_ESTIMATES`). These are gaps
   in the published syntheses, not sourced numbers.

**ESVD biome mapping.** tropical rainforest → "Tropical & subtropical forests"
(A: tropical forests); temperate forest → "Temperate forest & woodland"
(A: temperate & boreal forests); boreal forest → "Boreal & montane forests &
woodland" (A: temperate & boreal forests); mangrove → "Mangroves" (A: coastal
wetlands); inland wetland → "Inland wetlands"; freshwater → "Rivers and lakes";
temperate grassland → "Rangeland, natural grasslands & savannas"
(A: grasslands); cropland → "Intensive land uses"; tundra → "Polar-alpine";
desert → "Shrubland & shrubby woodland" (proxy — the ESVD has too few desert
values to summarise); **peri-urban → mean of "Urban & industrial areas" and
"Intensive land uses"** (an urban-fringe mosaic of green space and farmland).

---

## 5. Biome reference table

2024 USD/ha/yr unless noted. **E** = flagged estimate (no admissible published
evidence; value retained from the previous calibration and unverified). *n* =
value estimates behind the literature-based figure.

| Biome | Sequestration (tCO₂/ha/yr) | Climate | Water | Biodiversity | Soil | TEV @ $80/tCO₂ |
| --- | --- | --- | --- | --- | --- | --- |
| Tropical Rainforest | 2.4 | 6 (n 26) | 11 (n 11) | 569 (n 106) | 17 (n 18) | **795** |
| Temperate Forest | 3.2 | 294 (n 302) | 47 (n 6) | 714 (n 23) | 50 (n 18) | **1,361** |
| Boreal Forest (Taiga) | 1.0 | 180 **E** | 0 (n 3) | 259 (n 10) | 150 **E** | **669** |
| Mangrove | 5.9 | 1,116 (n 36) | 147 (n 17) | 4,987 (n 46) | 2,522 (n 24) | **9,244** |
| Inland Wetland | 1.0 **E** | 1,035 (n 29) | 186 (n 27) | 82 (n 24) | 250 **E** | **1,633** |
| Freshwater (Lakes & Rivers) | 0.0 | 626 (n 7) | 183 (n 10) | 404 (n 4) | 0 **E** | **1,213** |
| Temperate Grassland | 0.5 **E** | 1 (n 8) | 2 (n 6) | 59 (n 10) | 200 **E** | **302** |
| Cropland & Agriculture | 0.0 | 179 (n 28) | 77 (n 49) | 393 (n 105) | 17 (n 106) | **666** |
| Peri-urban / Managed Open Land | 0.6 **E** | 1,796 (n 28) | 56 (n 9) | 219 (n 6) | 120 **E** | **2,239** |
| Tundra | 0.0 | 40 **E** | 30 **E** | 60 **E** | 0 (n 3) | **130** |
| Desert & Xeric Shrubland | 0.1 **E** | 3 (n 3) | 10 **E** | 0 (n 3) | 20 **E** | **41** |

The per-cell derivation (source, statistic, raw value, *n*, 2024-USD value) is in
`reference_data.ESV_EVIDENCE` and is returned by `esv_provenance(biome, category)`.
`backend/tests/test_reference_data.py` pins every value above.

**Reading the table.**

- **Rankings follow the literature, not intuition.** Per hectare, the published
  syntheses rank urban green space and cropland at or above tropical forest for
  these services: Costanza et al. (2014, 2007$/ha/yr) put urban at 6,661, cropland
  at 5,567 and tropical forest at 5,382; Brander et al. (2024, 2020 Int$) put urban
  at 64,167 against 8,166 for tropical forest. These values scale with the number
  of people who benefit nearby. Mangroves and wetlands lead, and deserts and
  tundra trail, in every synthesis.
- **Tropical forest regulating services are thin in the evidence base.**
  Tropical-forest water regulation is the starkest case: de Groot (n = 2) gives a
  median of 342 Int$, while the ESVD 2024 mean from 7 estimates is 2.5 Int$. The
  rule takes the larger sample. Most of the rainforest's non-carbon value here is
  biodiversity, carried by existence & bequest values (n = 33).
- **Peri-urban** borrows the ESVD urban air-quality value, which is dominated by
  one UK national study (ESVD 2020 report, §3). It transfers UK
  population-exposure benefits to the urban fringe worldwide. Treat it as an
  upper-end figure.
- **Temperate forest** air-quality regulation (n = 302) comes overwhelmingly from
  the same UK study; its pollination value rests on 4 estimates.

---

## 6. Carbon

### 6.1 Sequestration (the annual flow priced under Carbon Capture)

| Biome | tCO₂/ha/yr | Basis | Source |
| --- | --- | --- | --- |
| Tropical Rainforest | 2.4 | literature | Pan et al. 2024, Table 1: tropical intact forest sink 0.88 PgC/yr (2010–2019) ÷ ~1,365 Mha ≈ 0.65 tC/ha/yr |
| Temperate Forest | 3.2 | literature | Pan et al. 2024: 0.68 PgC/yr ÷ ~786 Mha ≈ 0.86 tC/ha/yr |
| Boreal Forest | 1.0 | literature | Pan et al. 2024: 0.32 PgC/yr ÷ ~1,210 Mha ≈ 0.26 tC/ha/yr |
| Mangrove | 5.9 | literature | IPCC 2013 Wetlands Supplement Table 4.12: soil C accumulation 1.62 tC/ha/yr (n = 69, 95% CI 1.3–2.0); biomass growth excluded (conservative) |
| Inland Wetland | 1.0 | **estimate** | Unverified (peat accumulation) |
| Freshwater | 0.0 | — | Not monetised: no dependable net sink |
| Temperate Grassland | 0.5 | **estimate** | Unverified |
| Cropland | 0.0 | literature | IPCC 2006 GL Vol. 4 §5.2.1: no net accumulation of biomass carbon in annual crops; long-term cultivation loses soil carbon (Table 5.5) |
| Peri-urban | 0.6 | **estimate** | Unverified |
| Tundra | 0.0 | literature | Natali et al. 2019: across the permafrost region, winter CO₂ loss (1,662 TgC/yr) exceeds growing-season uptake (1,032 TgC/yr) — a net source, so no sink is credited |
| Desert | 0.1 | **estimate** | Unverified |

Pan et al. (2024) report forest areas as changes in their text (temperate
+52 Mha = +7%, boreal +12 Mha = +1%, tropical intact −467 Mha from ~1,754 Mha in
1990). Per-hectare rates derived from those rounded percentages are good to about
±7%.

### 6.2 Carbon price — $80/tCO₂ (2024 USD)

One transparent *social* reference price is applied to every biome. It values the
climate damage avoided, not what the landholder could sell a credit for:

- **IPCC AR6 WGIII (2022), Ch. 3 Executive Summary {3.6.1}:** in pathways that
  limit warming to 2 °C (>67%), marginal abatement costs of carbon in 2030 are
  about **90 (interquartile 60–120) USD2015/tCO₂**. For 1.5 °C (>50%, no or
  limited overshoot) they are about 220 (170–290). $80 is the *bottom* of the
  2 °C range (60 USD2015 = $79 in 2024 dollars).
- **EU ETS:** front-December EUAs averaged **€74.40/t in 2025** (LSEG), about
  **$84** at the 2025 average ECB rate (~1.13 USD/EUR). This is the feed
  `live_data.py` recommends wiring live, so enabling it does not jolt
  valuations.
- **Sensitivity (not applied):** social-cost-of-carbon estimates are higher.
  US EPA (2023) gives $190/tCO₂ (2020 USD, 2% near-term discount rate; ≈ $230 in
  2024 USD), and Rennert et al. (2022) give $185. Policy-constrained markets are
  lower: California–Québec auctions settled at $25.87–29.27 in 2025, and China's
  national ETS averaged CNY 62.36/t (~$9) in 2025.

The previous $40 reference was described as "within the IPCC AR6 range for
sub-2 °C pathways". It was not: the 2030 interquartile range starts at $60 in
2015 dollars. The same text quoted China's ETS at ~$30–40, which was also wrong.

### 6.3 Carbon debt of conversion

Clearing or sealing land releases the vegetation carbon it carries and *part* of
its soil carbon — not the whole soil profile:

```
debt (tCO₂/ha) = (vegetation tC/ha × intactness
                  + soil tC/ha (0–1 m) × soil release fraction) × 44/12
carbon_debt_onetime = debt × area_ha × carbon price
```

Vegetation scales with intactness, because a half-cleared parcel has half its
biomass left to lose. Soil carbon persists after clearing, so it does not.

| Biome | Veg. tC/ha | Soil tC/ha | Release | Debt tCO₂/ha | Basis / source |
| --- | --- | --- | --- | --- | --- |
| Tropical Rainforest | 120.5 | 122.7 | 0.26 | 559 | SRLULUCF; (1 − 0.48) × 0.50 |
| Temperate Forest | 56.7 | 96.2 | 0.155 | 263 | SRLULUCF; (1 − 0.69) × 0.50 |
| Boreal Forest | 64.2 | 343.8 | 0.155 | 431 | SRLULUCF; mineral-soil factor (understates peat losses) |
| Mangrove | 129.0 | 386.0 | 0.625 | 1,358 | IPCC 2013 Tables 4.2/4.3/4.5/4.11; Pendleton et al. 2012 midpoint of 25–100% |
| Inland Wetland | 42.9 | 642.9 | 0.246 | 737 | SRLULUCF; drained organic soil 7.9 tC/ha/yr × 20 yr (IPCC 2013 Table 2.1) |
| Freshwater | 0 | 0 | — | 0 | Not assessed (open water) |
| Temperate Grassland | 7.2 | 236.0 | 0.084 | 99 | SRLULUCF; (1 − 0.80) × 0.42 |
| Cropland | 1.9 | 80.0 | 0.13 | 45 | **estimate** — SRLULUCF stocks; release on sealing is a proxy |
| Peri-urban | 1.9 | 80.0 | 0.13 | 45 | **estimate** — cropland pools as proxy |
| Tundra | 6.3 | 127.4 | 0.155 | 96 | **estimate** — mineral-soil proxy; permafrost thaw is a red line instead |
| Desert | 1.8 | 42.0 | 0.066 | 17 | SRLULUCF; (1 − 0.80) × 0.33 |

- **Pools:** IPCC (2000) SRLULUCF Table 1, "Global carbon stocks in vegetation and
  soil carbon pools down to a depth of 1 m" (Gt C ÷ 10⁹ ha = t C/ha). Mangroves
  use the IPCC 2013 Wetlands Supplement: above-ground biomass 192 t d.m./ha
  (tropical wet), root:shoot 0.49, carbon fraction 0.451, and an aggregated soil
  stock of 386 tC/ha.
- **Mineral-soil release** = (1 − F_LU) × topsoil share. F_LU is the IPCC 2006
  Vol. 4 Table 5.5 stock-change factor for long-term cultivation, applied to the
  top 30 cm over 20 years: 0.48 tropical moist/wet, 0.69 temperate/boreal moist,
  0.80 temperate/boreal dry. The topsoil share is the fraction of the 0–1 m
  stock held in the top 20 cm (Jobbágy & Jackson 2000): 50% for forests, 42% for
  grasslands, 33% for shrublands. Using the 20 cm share for a 30 cm layer is
  conservative.

The previous calibration released the *entire* 0–1 m soil stock (e.g.
900 tCO₂/ha for rainforest, 1,800 for tundra), which overstates committed
emissions several-fold for mineral soils.

---

## 7. Currency

The engine returns values in **USD** (default), **EUR**, or **BRL**. The static
fallback rates are the **European Central Bank reference rates for 2026-10-16**
(EUR 0.8887/USD, BRL 5.0828/USD, via Frankfurter), which is the same source
`live_data.py` uses when `ALPHA_LIVE_DATA` is on. The previous static EUR rate
(0.92, labelled 2025-12) was stale: the ECB rate through December 2025 was
0.851–0.859. FX only converts the 2024-USD figures for display; it is not a
price-year adjustment. Human-scale comparisons are always ranked on the USD
figure, so they do not change with the display currency.

---

## 8. Worked example

A 1 ha (10,000 m²) tropical-rainforest polygon, fully intact, in USD (2024):

```
carbon_capture       = 2.4 × 80 / 10,000 = 0.0192  USD/m²/yr  →  192  USD/yr
climate_regulation   =    6 / 10,000     = 0.0006  USD/m²/yr  →    6  USD/yr
water_filtration     =   11 / 10,000     = 0.0011  USD/m²/yr  →   11  USD/yr
biodiversity_premium =  569 / 10,000     = 0.0569  USD/m²/yr  →  569  USD/yr
soil_nutrient_value  =   17 / 10,000     = 0.0017  USD/m²/yr  →   17  USD/yr
------------------------------------------------------------------------------
TEV                  = 0.0795 USD/m²/yr  →  795 USD/yr for the hectare
asset value (3%)     = 795 / 0.03        = 26,500 USD
carbon debt          = 558.7 tCO₂ × 80   = 44,696 USD (one-time)
```

---

## 9. Standing-asset value & the cost of conversion

Two layers sit on top of the annual TEV. Both are reported separately so the
per-m²/yr figure stays untouched.

**Capitalisation.** The annual flow is treated as a perpetuity, so its present
value is `asset = annual ÷ discount_rate`. The 3% reference sits between the
Stern Review (~1.4%) and DICE-style market-based rates (~4–5%). The UK Green
Book uses 3.5% (declining over long horizons), and US EPA's 2023 social cost of
carbon is built on 2%. The UI offers 1%, 3% and 5%. This is the land's value *as
a standing natural asset* — a balance-sheet number, not an annual one.

**Cost of conversion — deliberately *not* a price to outbid.** Converting land is
framed as a permanent, externalised **liability**, never netted against
development revenue, because a parcel's loss is more than its isolated value:

- **Systemic premium** — `multiplier = 1 + scarcity × intactness`. Rare, intact
  systems are load-bearing; fragmenting one degrades the wider network beyond the
  parcel. The liability uses the systemic-weighted asset value.
- **Irreversible carbon debt** — §6.3. Distinct from the annual sequestration
  flow.
- **Red lines** — non-substitutable / irreversible losses (extinction, ancient
  soil & peat, permafrost, aquifers) are **flagged, not monetised**. They cannot
  be netted against revenue at any price and are listed outside the figures.

The scarcity weights, default intactness per biome and red lines are
value-laden **heuristic judgements, not literature-derived values**, and are kept
separate from the ESV in `reference_data.py` (`BIOME_SCARCITY_WEIGHT`,
`BIOME_DEFAULT_INTACTNESS`, `BIOME_RED_LINES`).

---

## 10. What changed in the 2026 recalibration

TEV per hectare at full intactness, USD/yr (old: $40/tCO₂, undated USD; new:
$80/tCO₂, 2024 USD):

| Biome | Old | New | Change |
| --- | --- | --- | --- |
| Tropical Rainforest | 1,272 | 795 | −37% |
| Temperate Forest | 810 | 1,361 | +68% |
| Boreal Forest | 648 | 669 | +3% |
| Mangrove | 2,740 | 9,244 | +237% |
| Inland Wetland | 4,890 | 1,633 | −67% |
| Freshwater | 4,400 | 1,213 | −72% |
| Temperate Grassland | 480 | 302 | −37% |
| Cropland | 342 | 666 | +95% |
| Peri-urban | 504 | 2,239 | +344% |
| Tundra | 222 | 130 | −41% |
| Desert | 94 | 41 | −56% |

Main drivers:

- The previous values matched no published table. The new ones follow the ESVD
  syntheses.
- Freshwater and wetland water values had included drinking-water *supply*
  (provisioning) or were close to skewed means. The new figures are medians of
  purification and flow regulation only.
- The carbon price doubled.
- Forest sinks were updated from Pan et al. 2024.
- Cropland and tundra sinks were set to zero per IPCC and Natali et al.
- Existence values now feed the biodiversity premium.

## 11. Known limitations

- Global summary values are Europe-weighted (Brander et al. 2024, §5.2) and are
  not designed for site-level value transfer (ESVD 2020 report).
- The skew adjustment for ESVD 2024 cells uses all-biome median/mean ratios.
- 15 of the 55 coefficients (11 biomes × 4 categories + sequestration) are
  flagged estimates (§5, §6.1). Tundra and desert are the thinnest.
- Values are average, not marginal, and assume all services can be delivered
  simultaneously.

---

## References

- Brander, L.M. et al. (2024). Economic values for
  ecosystem services: A global synthesis and way forward. *Ecosystem Services*
  66: 101606. https://doi.org/10.1016/j.ecoser.2024.101606
- de Groot, R., Brander, L., van der Ploeg, S., et al. (2012). Global estimates
  of the value of ecosystems and their services in monetary units. *Ecosystem
  Services* 1(1): 50–61, and Online Supporting Information.
  https://doi.org/10.1016/j.ecoser.2012.07.005
- de Groot, R., Brander, L., Solomonides, S. (2020). *Update of global ecosystem
  service valuation database (ESVD).* FSD report 2020-06, Wageningen.
- Costanza, R. et al. (2014). Changes in the global
  value of ecosystem services. *Global Environmental Change* 26: 152–158
  (cross-check of biome totals).
- Pan, Y. et al. (2024). The enduring world forest
  carbon sink. *Nature* 631: 563–569. https://doi.org/10.1038/s41586-024-07602-x
- IPCC (2014). *2013 Supplement to the 2006 IPCC Guidelines for National
  Greenhouse Gas Inventories: Wetlands* — Ch. 2 (Table 2.1) and Ch. 4
  (Tables 4.2, 4.3, 4.5, 4.11, 4.12).
- IPCC (2006). *Guidelines for National Greenhouse Gas Inventories*, Vol. 4,
  Ch. 5 (Cropland), §5.2.1 and Table 5.5.
- IPCC (2000). *Land Use, Land-Use Change and Forestry* (Special Report), Table 1.
- IPCC (2022). *Climate Change 2022: Mitigation of Climate Change*, WGIII Ch. 3,
  Executive Summary {3.6.1}.
- Jobbágy, E.G., Jackson, R.B. (2000). The vertical distribution of soil organic
  carbon and its relation to climate and vegetation. *Ecological Applications*
  10(2): 423–436.
- Pendleton, L., Donato, D.C., Murray, B.C., et al. (2012). Estimating global
  "blue carbon" emissions from conversion and degradation of vegetated coastal
  ecosystems. *PLoS ONE* 7(9): e43542.
- Natali, S.M. et al. (2019). Large loss of CO₂ in winter observed across the
  northern permafrost region. *Nature Climate Change* 9: 852–857.
- US EPA (2023). *Report on the Social Cost of Greenhouse Gases.* Rennert, K. et
  al. (2022). Comprehensive evidence implies a higher social cost of CO₂.
  *Nature*. (Sensitivity only.)
- US Bureau of Labor Statistics. CPI-U, U.S. city average, all items, annual
  averages.
- European Central Bank euro foreign exchange reference rates (via Frankfurter).
- ESVD — Ecosystem Services Valuation Database (esvd.net).
