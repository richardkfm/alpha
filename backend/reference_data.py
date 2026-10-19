"""alpha — valuation reference data.

Documented reference values and citations for the Total Ecosystem Value (TEV)
engine. Every figure here is a biome-level reference estimate drawn from the
peer-reviewed literature, not a live measurement. Each non-carbon coefficient is
*derived in code* from the published table cells it rests on (``ESV_EVIDENCE``),
so the provenance of every number — source, statistic, number of underlying
value estimates and price year — travels with it. Coefficients the literature
cannot support are kept as explicitly flagged estimates (``ESV_ESTIMATES``,
``SEQUESTRATION[...]["basis"] == "estimate"``).

Price year: **all USD figures are 2024 US dollars** (``PRICE_YEAR``), inflated
from each source's price year with the US CPI-U annual average (BLS). The ESVD
reports "international dollars" (Int$, PPP-adjusted, where 1 Int$ = 1 USD in the
US), so a US CPI-U adjustment is the standard way to bring them forward.

Primary sources (full references in ``backend/METHODOLOGY.md``)
---------------------------------------------------------------
- Brander, L.M. et al. (2024). Economic values for ecosystem services: A global
  synthesis and way forward. *Ecosystem Services* 66: 101606 — Table 1, mean
  ESVD values per biome x service (2020 Int$/ha/yr) with the number of value
  estimates behind each mean.
- de Groot, R. et al. (2012). Global estimates of the value of ecosystems and
  their services in monetary units. *Ecosystem Services* 1(1): 50-61, and its
  Online Supporting Information — per biome x service mean *and median*
  (2007 Int$/ha/yr) with n.
- de Groot, R., Brander, L., Solomonides, S. (2020). Update of global
  ecosystem service valuation database (ESVD). FSD report 2020-06 — Table 5,
  all-biome mean and median per service (2020 Int$/ha/yr).
- Pan, Y. et al. (2024). The enduring world forest carbon sink. *Nature* 631:
  563-569 — forest sinks by biome, 2010-2019.
- IPCC (2014). 2013 Supplement to the 2006 IPCC Guidelines: Wetlands, Ch. 4
  (coastal wetlands) and Ch. 2 (drained inland organic soils).
- IPCC (2006). Guidelines for National GHG Inventories, Vol. 4 Ch. 5 (cropland).
- IPCC (2000). Special Report on Land Use, Land-Use Change and Forestry, Table 1.
- IPCC AR6 WGIII (2022), Ch. 3 Executive Summary — carbon prices in pathways
  limiting warming to 2 °C / 1.5 °C.

All monetary reference values are expressed in USD per hectare per year and
converted to USD per square metre per year (÷ 10,000) by the engine.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Units and price year.
# ---------------------------------------------------------------------------
# Hectare -> square metre.
SQM_PER_HECTARE = 10_000.0

# Molecular-weight ratio CO2 / C (44.01 / 12.011, conventionally 44/12).
TCO2_PER_TC = 44.0 / 12.0

# Single consistent price year for every USD figure in this module.
PRICE_YEAR = 2024

# US CPI-U, U.S. city average, all items, annual average (1982-84 = 100).
# Source: US Bureau of Labor Statistics, "Historical CPI-U", December 2024
# release (https://www.bls.gov/cpi/tables/supplemental-files/).
CPI_U_ANNUAL_AVERAGE: dict[int, float] = {
    2007: 207.342,
    2015: 237.017,
    2020: 258.811,
    2024: 313.689,
}


def inflate_usd(value: float, from_year: int, to_year: int = PRICE_YEAR) -> float:
    """Restate a USD (or Int$) amount from ``from_year`` prices in ``to_year`` prices."""
    return value * CPI_U_ANNUAL_AVERAGE[to_year] / CPI_U_ANNUAL_AVERAGE[from_year]


# ---------------------------------------------------------------------------
# Carbon price (USD per tonne CO2, 2024 USD).
#
# A single transparent *social* reference price for the carbon an ecosystem
# sequesters or stores — the value its loss imposes on everyone else, not what
# the landholder could sell a credit for. Anchored on two independent figures
# that happen to agree:
#
#   * IPCC AR6 WGIII (2022), Ch. 3 Executive Summary {3.6.1}: in pathways that
#     limit warming to 2 °C (>67%), marginal abatement costs of carbon are about
#     90 (interquartile range 60-120) USD2015/tCO2 in 2030; for 1.5 °C (>50%,
#     no/limited overshoot) about 220 (170-290). The *bottom* of the 2 °C range,
#     60 USD2015, is $79 in 2024 dollars.
#   * EU ETS, the largest liquid compliance market and the source recommended
#     for a live feed in ``live_data.py``: front-December EUAs averaged
#     EUR 74.40/t in 2025 (LSEG), about $84 at the 2025 average ECB rate
#     (~1.13 USD/EUR).
#
# $80 therefore sits at the low end of what the IPCC finds necessary for
# well-below-2 °C and roughly where the main compliance market trades, so
# switching the live EU-ETS feed on does not jolt valuations. It is deliberately
# conservative against social-cost-of-carbon estimates: US EPA (2023) $190/tCO2
# (2020 USD, 2% near-term discount rate; ~$230 in 2024 USD), Rennert et al.
# (2022, Nature) $185. Other markets trade far lower — California-Quebec 2025
# auctions settled $25.87-29.27, China's national ETS averaged CNY 62.36/t in
# 2025 (~$9) — but those are policy-constrained prices, not estimates of the
# damage avoided.
#
# The previous reference ($40) was described as "within the IPCC AR6 range for
# sub-2 °C pathways"; it was not (the 2030 interquartile range starts at $60 in
# 2015 dollars). ``live_data.py`` lets an operator override this with a live
# market price via ``CARBON_PRICE_URL`` or ``CARBON_PRICE_USD_PER_TCO2``.
# ---------------------------------------------------------------------------
CARBON_PRICE_USD_PER_TCO2 = 80.0
CARBON_PRICE_AS_OF = "2025"
CARBON_PRICE_SOURCE = (
    "IPCC AR6 WGIII (2022) Ch. 3 — low end of the 2 °C-pathway 2030 range "
    "(60 USD2015 ≈ $79 in 2024 USD); cross-checked against the 2025 EU ETS "
    "average (EUR 74.40/t ≈ $84)"
)


# ---------------------------------------------------------------------------
# Non-carbon ecosystem-service values — the evidence base.
#
# alpha's four non-carbon categories map onto TEEB / ESVD services as:
#
#   climate_regulation   <- air-quality regulation + moderation of extreme events
#                           (ESVD "climate regulation" is *excluded*: it is
#                           predominantly carbon sequestration, which alpha prices
#                           explicitly under carbon_capture — counting both would
#                           double count)
#   water_filtration     <- waste treatment / water purification
#                           + regulation of water flows
#   biodiversity_premium <- habitat services (maintenance of life cycles /
#                           nursery, maintenance of genetic diversity / gene pool)
#                           + biodiversity-mediated regulation (pollination,
#                           biological control) + existence & bequest values
#                           (the non-use value of species and habitats)
#   soil_nutrient_value  <- erosion prevention + maintenance of soil fertility
#
# Provisioning services (food, water supply, raw materials, genetic/medicinal/
# ornamental resources) and recreational/aesthetic/cognitive cultural services
# are excluded: the figure is the ecosystem value *lost when the land is sealed
# or converted* that a rezoning decision does not otherwise see.
#
# Statistic: a central *median* value, matching the project's conservative
# (lower-to-mid of published ranges) policy. ESV distributions are heavily
# right-skewed — across the ESVD, medians are 0.5-53% of the means — so means are
# dominated by a few high-value study sites.
#
# Selection rule, applied per biome x service cell:
#   1. Candidate A — de Groot et al. 2012 SOM median (2007 Int$/ha/yr), where
#      that synthesis covers the biome.
#   2. Candidate B — Brander et al. 2024 Table 1 ESVD mean (2020 Int$/ha/yr)
#      multiplied by that service's all-biome median/mean ratio from the ESVD
#      2020 report (Table 5) — a "median-equivalent". The ratio transfer
#      assumes within-biome skew resembles the all-biome skew; it is an
#      approximation, documented as such.
#   3. A candidate is admissible only if it rests on >= 3 value estimates
#      (``MIN_VALUE_ESTIMATES``). Of the admissible candidates, the one backed
#      by more estimates wins (ties go to the de Groot median, a true median).
#   4. A category's value is the sum of its admissible cells. A category with no
#      admissible cell keeps its previous value as an explicitly flagged
#      *estimate* (``ESV_ESTIMATES``) rather than being silently zeroed or
#      filled with a guess dressed up as a citation.
# ---------------------------------------------------------------------------
MIN_VALUE_ESTIMATES = 3

SOURCE_DG2012 = "dG2012"
SOURCE_ESVD2024 = "ESVD2024"

SOURCES: dict[str, dict] = {
    SOURCE_DG2012: {
        "citation": (
            "de Groot, R. et al. (2012). Global estimates of the value of ecosystems "
            "and their services in monetary units. Ecosystem Services 1(1): 50-61; "
            "Online Supporting Information, per-biome service tables"
        ),
        "statistic": "median",
        "price_year": 2007,
        "unit": "Int$/ha/yr",
    },
    SOURCE_ESVD2024: {
        "citation": (
            "Brander, L.M. et al. (2024). Economic values for ecosystem services: A "
            "global synthesis and way forward. Ecosystem Services 66: 101606, Table 1 "
            "(ESVD); skew-adjusted with de Groot, Brander & Solomonides (2020), ESVD "
            "update report, Table 5"
        ),
        "statistic": "mean x ESVD-2020 median/mean ratio",
        "price_year": 2020,
        "unit": "Int$/ha/yr",
    },
}

# ESVD 2020 update report, Table 5: all-biome (mean, median) per service,
# Int$/ha/yr, 2020 price levels, after trimming the top/bottom 2.5%.
ESVD_2020_SERVICE_MEAN_MEDIAN: dict[str, tuple[float, float]] = {
    "air_quality_regulation": (4226.0, 912.0),
    "moderation_of_extreme_events": (4095.0, 262.0),
    "regulation_of_water_flows": (1785.0, 73.0),
    "waste_treatment": (6552.0, 250.0),
    "erosion_prevention": (3852.0, 1137.0),
    "maintenance_of_soil_fertility": (4199.0, 22.0),
    "pollination": (2595.0, 71.0),
    "biological_control": (2184.0, 443.0),
    "maintenance_of_life_cycles": (958.0, 506.0),
    "maintenance_of_genetic_diversity": (6629.0, 1778.0),
    "existence_and_bequest_values": (3408.0, 263.0),
}


def esvd_median_mean_ratio(service: str) -> float:
    mean, median = ESVD_2020_SERVICE_MEAN_MEDIAN[service]
    return median / mean


def _dg(service: str, median: float, n: int) -> dict:
    return {"service": service, "source": SOURCE_DG2012, "value": median, "n": n}


def _esvd(service: str, mean: float, n: int) -> dict:
    return {"service": service, "source": SOURCE_ESVD2024, "value": mean, "n": n}


def evidence_cell_usd_ha_yr(cell: dict) -> float:
    """A single evidence cell restated in 2024 USD/ha/yr (median basis)."""
    if cell["source"] == SOURCE_DG2012:
        return inflate_usd(cell["value"], SOURCES[SOURCE_DG2012]["price_year"])
    return inflate_usd(
        cell["value"] * esvd_median_mean_ratio(cell["service"]),
        SOURCES[SOURCE_ESVD2024]["price_year"],
    )


# The admissible cell chosen for each biome x category (rule above). ESVD biome
# used: tropical_rainforest -> "Tropical & subtropical forests" (de Groot:
# "Tropical forests"); temperate_forest -> "Temperate forest and woodland"
# (de Groot: "Temperate & boreal forests"); boreal_forest -> "Boreal and montane
# forests & woodland" (de Groot: "Temperate & boreal forests"); mangrove ->
# "Mangroves" (de Groot: "Coastal wetlands"); wetland -> "Inland wetlands";
# freshwater -> "Rivers and lakes"; temperate_grassland -> "Rangeland, natural
# grasslands & savannas" (de Groot: "Grasslands"); cropland -> "Intensive land
# uses"; tundra -> "Polar-alpine"; desert -> "Shrubland and shrubby woodland"
# (proxy: the ESVD has too few desert values to summarise); peri_urban -> the
# mean of "Urban and industrial areas" and "Intensive land uses" (an urban-fringe
# mosaic of green space and farmland; see ``_PERI_URBAN_MOSAIC``).
ESV_EVIDENCE: dict[str, dict[str, list[dict]]] = {
    "tropical_rainforest": {
        "climate_regulation": [_esvd("moderation_of_extreme_events", 77, 26)],
        "water_filtration": [
            _dg("waste_treatment", 7, 4),
            _esvd("regulation_of_water_flows", 2.5, 7),
        ],
        "biodiversity_premium": [
            _dg("maintenance_of_genetic_diversity", 12, 6),
            _esvd("pollination", 260, 67),
            _esvd("existence_and_bequest_values", 5795, 33),
        ],
        "soil_nutrient_value": [
            _esvd("erosion_prevention", 47, 13),
            _esvd("maintenance_of_soil_fertility", 1.4, 5),
        ],
    },
    "temperate_forest": {
        "climate_regulation": [_esvd("air_quality_regulation", 1124, 302)],
        "water_filtration": [
            _dg("waste_treatment", 0, 3),
            _esvd("regulation_of_water_flows", 940, 3),
        ],
        "biodiversity_premium": [
            _dg("maintenance_of_genetic_diversity", 171, 10),
            _esvd("pollination", 8993, 4),
            _esvd("existence_and_bequest_values", 1676, 9),
        ],
        "soil_nutrient_value": [
            _esvd("erosion_prevention", 138, 10),
            _esvd("maintenance_of_soil_fertility", 48, 8),
        ],
    },
    "boreal_forest": {
        "climate_regulation": [],
        "water_filtration": [_dg("waste_treatment", 0, 3)],
        "biodiversity_premium": [_dg("maintenance_of_genetic_diversity", 171, 10)],
        "soil_nutrient_value": [],
    },
    "mangrove": {
        "climate_regulation": [_esvd("moderation_of_extreme_events", 14388, 36)],
        "water_filtration": [_esvd("waste_treatment", 3189, 17)],
        "biodiversity_premium": [
            _dg("maintenance_of_life_cycles", 1127, 20),
            _esvd("maintenance_of_genetic_diversity", 5982, 10),
            _esvd("existence_and_bequest_values", 14299, 16),
        ],
        "soil_nutrient_value": [
            _esvd("erosion_prevention", 7030, 19),
            _esvd("maintenance_of_soil_fertility", 1028, 5),
        ],
    },
    "wetland": {
        "climate_regulation": [
            _esvd("air_quality_regulation", 2485, 9),
            _esvd("moderation_of_extreme_events", 4969, 20),
        ],
        "water_filtration": [
            _esvd("waste_treatment", 2603, 18),
            _esvd("regulation_of_water_flows", 1314, 9),
        ],
        "biodiversity_premium": [
            _dg("maintenance_of_genetic_diversity", 50, 15),
            _esvd("existence_and_bequest_values", 63, 9),
        ],
        "soil_nutrient_value": [],
    },
    "freshwater": {
        "climate_regulation": [_esvd("moderation_of_extreme_events", 8077, 7)],
        "water_filtration": [
            _esvd("waste_treatment", 2189, 6),
            _esvd("regulation_of_water_flows", 1657, 4),
        ],
        "biodiversity_premium": [_esvd("maintenance_of_life_cycles", 631, 4)],
        "soil_nutrient_value": [],
    },
    "temperate_grassland": {
        "climate_regulation": [_esvd("air_quality_regulation", 3.1, 8)],
        "water_filtration": [_esvd("regulation_of_water_flows", 36, 6)],
        "biodiversity_premium": [
            _esvd("maintenance_of_genetic_diversity", 117, 6),
            _esvd("existence_and_bequest_values", 225, 4),
        ],
        "soil_nutrient_value": [],
    },
    "cropland": {
        "climate_regulation": [
            _esvd("air_quality_regulation", 506, 7),
            _esvd("moderation_of_extreme_events", 607, 21),
        ],
        "water_filtration": [
            _esvd("waste_treatment", 965, 22),
            _esvd("regulation_of_water_flows", 649, 27),
        ],
        "biodiversity_premium": [
            _esvd("maintenance_of_life_cycles", 1.5, 4),
            _esvd("pollination", 211, 34),
            _esvd("biological_control", 921, 51),
            _esvd("existence_and_bequest_values", 1701, 16),
        ],
        "soil_nutrient_value": [
            _esvd("erosion_prevention", 39, 27),
            _esvd("maintenance_of_soil_fertility", 410, 79),
        ],
    },
    "tundra": {
        "climate_regulation": [],
        "water_filtration": [],
        "biodiversity_premium": [],
        "soil_nutrient_value": [_esvd("maintenance_of_soil_fertility", 0.53, 3)],
    },
    "desert": {
        "climate_regulation": [_esvd("moderation_of_extreme_events", 42, 3)],
        "water_filtration": [],
        "biodiversity_premium": [_esvd("existence_and_bequest_values", 3.7, 3)],
        "soil_nutrient_value": [],
    },
}

# Peri-urban land has no ESVD biome of its own. It is valued as a 50/50 mosaic
# of ESVD "Urban and industrial areas" (urban green-blue space) and "Intensive
# land uses" (the farmland it borders). Caveat: the ESVD's urban air-quality
# values are dominated by one UK national study (ESVD 2020 report, §3), so the
# urban half transfers UK population-exposure benefits to the fringe.
_PERI_URBAN_URBAN_HALF: dict[str, list[dict]] = {
    "climate_regulation": [
        _esvd("air_quality_regulation", 10384, 93),
        _esvd("moderation_of_extreme_events", 8991, 5),
    ],
    "water_filtration": [
        _esvd("waste_treatment", 98, 5),
        _esvd("regulation_of_water_flows", 620, 4),
    ],
    "biodiversity_premium": [_esvd("existence_and_bequest_values", 481, 6)],
    "soil_nutrient_value": [],
}
_PERI_URBAN_MOSAIC = (_PERI_URBAN_URBAN_HALF, ESV_EVIDENCE["cropland"])

# Categories with no admissible evidence keep their previous value, flagged as
# an unverified estimate (USD/ha/yr, treated as 2024 USD). Each is a gap in the
# published syntheses, not a sourced number.
ESV_ESTIMATES: dict[tuple[str, str], float] = {
    ("boreal_forest", "climate_regulation"): 180.0,   # ESVD: n=1 (air), n=2 (extreme events)
    ("boreal_forest", "soil_nutrient_value"): 150.0,  # ESVD: n=2 each
    ("wetland", "soil_nutrient_value"): 250.0,        # de Groot: n=2 each; ESVD: n<=1
    ("freshwater", "soil_nutrient_value"): 0.0,       # open water: no soil column
    ("temperate_grassland", "soil_nutrient_value"): 200.0,  # n=2 in both syntheses
    ("peri_urban", "soil_nutrient_value"): 120.0,     # ESVD urban: no values
    ("tundra", "climate_regulation"): 40.0,           # ESVD polar-alpine: n<=1
    ("tundra", "water_filtration"): 30.0,             # ESVD polar-alpine: none
    ("tundra", "biodiversity_premium"): 60.0,         # ESVD polar-alpine: n<=1
    ("desert", "water_filtration"): 10.0,             # ESVD shrubland: n=1
    ("desert", "soil_nutrient_value"): 20.0,          # ESVD shrubland: n=1
}

ESV_CATEGORIES = (
    "climate_regulation",
    "water_filtration",
    "biodiversity_premium",
    "soil_nutrient_value",
)


def _sum_cells(cells: list[dict]) -> float:
    return sum(evidence_cell_usd_ha_yr(c) for c in cells)


def _esv_category_value(biome_key: str, category: str) -> tuple[float, str]:
    """(USD2024/ha/yr, basis) for one biome x non-carbon category."""
    if (biome_key, category) in ESV_ESTIMATES:
        return ESV_ESTIMATES[(biome_key, category)], "estimate"
    if biome_key == "peri_urban":
        halves = [_sum_cells(half[category]) for half in _PERI_URBAN_MOSAIC]
        return round(sum(halves) / len(halves)), "literature"
    return round(_sum_cells(ESV_EVIDENCE[biome_key][category])), "literature"


# ---------------------------------------------------------------------------
# Net carbon sequestration (tCO2/ha/yr) — the annual flow priced under
# carbon_capture. ``basis`` is "literature" when derived from a verified source,
# "estimate" when it could not be verified and is kept as a flagged estimate.
#
# Forest rates are Pan et al. (2024) Table 1 sinks for 2010-2019 divided by the
# biome's forest area. The paper gives areas as changes in its text
# (temperate +52 Mha = +7%, boreal +12 Mha = +1%, tropical intact forest -467 Mha
# from ~1,754 Mha in 1990), giving ~786, ~1,210 and ~1,365 Mha around 2015;
# because those percentages are rounded, the per-hectare rates are good to about
# ±7%.
# ---------------------------------------------------------------------------
SEQUESTRATION: dict[str, dict] = {
    "tropical_rainforest": {
        "tco2_ha_yr": 2.4,  # 0.88 PgC/yr / ~1,365 Mha = 0.65 tC/ha/yr
        "basis": "literature",
        "source": "Pan et al. 2024, Table 1 (tropical intact forest sink, 2010-2019)",
    },
    "temperate_forest": {
        "tco2_ha_yr": 3.2,  # 0.68 PgC/yr / ~786 Mha = 0.86 tC/ha/yr
        "basis": "literature",
        "source": "Pan et al. 2024, Table 1 (temperate forest sink, 2010-2019)",
    },
    "boreal_forest": {
        "tco2_ha_yr": 1.0,  # 0.32 PgC/yr / ~1,210 Mha = 0.26 tC/ha/yr
        "basis": "literature",
        "source": "Pan et al. 2024, Table 1 (boreal forest sink, 2010-2019)",
    },
    "mangrove": {
        "tco2_ha_yr": 5.9,  # 1.62 tC/ha/yr soil accretion (n=69, 95% CI 1.3-2.0)
        "basis": "literature",
        "source": "IPCC 2013 Wetlands Supplement, Table 4.12 (mangrove soil C accumulation; biomass growth excluded)",
    },
    "wetland": {
        "tco2_ha_yr": 1.0,
        "basis": "estimate",
        "source": "Unverified estimate (peat accumulation; not checked against a primary source)",
    },
    "freshwater": {
        "tco2_ha_yr": 0.0,
        "basis": "literature",
        "source": "Not monetised: open water has no dependable net sink (sediment burial is offset by outgassing)",
    },
    "temperate_grassland": {
        "tco2_ha_yr": 0.5,
        "basis": "estimate",
        "source": "Unverified estimate (soil carbon accrual in unmanaged grassland)",
    },
    "cropland": {
        "tco2_ha_yr": 0.0,
        "basis": "literature",
        "source": "IPCC 2006 GL Vol. 4 §5.2.1: annual crops have no net accumulation of biomass carbon; cultivated soils lose, not gain, carbon (Table 5.5)",
    },
    "peri_urban": {
        "tco2_ha_yr": 0.6,
        "basis": "estimate",
        "source": "Unverified estimate (urban-fringe tree and soil uptake)",
    },
    "tundra": {
        "tco2_ha_yr": 0.0,
        "basis": "literature",
        "source": "Natali et al. 2019 (Nature Climate Change): winter CO2 loss (1,662 TgC/yr) exceeds growing-season uptake (1,032 TgC/yr) across the permafrost region",
    },
    "desert": {
        "tco2_ha_yr": 0.1,
        "basis": "estimate",
        "source": "Unverified estimate",
    },
}


# ---------------------------------------------------------------------------
# Biome reference table — assembled from the evidence above. Keys are the ones
# the rest of the backend and the API expose; the four ``*_usd_ha_yr`` values
# are 2024 USD per hectare per year.
# ---------------------------------------------------------------------------
_BIOME_LABELS: dict[str, str] = {
    "tropical_rainforest": "Tropical Rainforest",
    "temperate_forest": "Temperate Forest",
    "mangrove": "Mangrove",
    "wetland": "Inland Wetland",
    "temperate_grassland": "Temperate Grassland",
    "boreal_forest": "Boreal Forest (Taiga)",
    "cropland": "Cropland & Agriculture",
    "freshwater": "Freshwater (Lakes & Rivers)",
    "peri_urban": "Peri-urban / Managed Open Land",
    "tundra": "Tundra",
    "desert": "Desert & Xeric Shrubland",
}


def _build_biomes() -> dict[str, dict]:
    biomes: dict[str, dict] = {}
    for key, label in _BIOME_LABELS.items():
        entry: dict = {
            "label": label,
            "sequestration_tco2_ha_yr": SEQUESTRATION[key]["tco2_ha_yr"],
        }
        for cat in ESV_CATEGORIES:
            entry[f"{cat}_usd_ha_yr"] = float(_esv_category_value(key, cat)[0])
        biomes[key] = entry
    return biomes


BIOMES: dict[str, dict] = _build_biomes()

DEFAULT_BIOME = "tropical_rainforest"


def esv_provenance(biome_key: str, category: str) -> dict:
    """Machine-readable provenance for one biome x non-carbon category."""
    value, basis = _esv_category_value(biome_key, category)
    if basis == "estimate":
        return {
            "basis": "estimate",
            "value_usd_ha_yr": value,
            "price_year": PRICE_YEAR,
            "evidence": [],
            "note": "No admissible published value (fewer than "
            f"{MIN_VALUE_ESTIMATES} estimates); unverified estimate.",
        }
    if biome_key == "peri_urban":
        cells = [c for half in _PERI_URBAN_MOSAIC for c in half[category]]
    else:
        cells = ESV_EVIDENCE[biome_key][category]
    return {
        "basis": "literature",
        "value_usd_ha_yr": value,
        "price_year": PRICE_YEAR,
        "evidence": [
            {
                "service": c["service"],
                "source": c["source"],
                "statistic": SOURCES[c["source"]]["statistic"],
                "source_value": c["value"],
                "source_price_year": SOURCES[c["source"]]["price_year"],
                "n_estimates": c["n"],
                "usd_ha_yr": round(evidence_cell_usd_ha_yr(c), 2),
            }
            for c in cells
        ],
    }


# ---------------------------------------------------------------------------
# Capitalisation discount rate.
#
# Ecosystem services are a perpetual annual flow; capitalising them into a
# present-value "standing natural asset" (asset_value = annual / rate) lets a
# hectare of intact land sit on a balance sheet next to its development price.
# 3% sits between the Stern Review (~1.4%) and DICE-style market-based rates
# (~4-5%); the UK Green Book uses 3.5% (declining over long horizons) and US EPA's
# 2023 social cost of carbon is built on 2%. The UI offers 1% / 3% / 5%.
# ---------------------------------------------------------------------------
DEFAULT_DISCOUNT_RATE = 0.03

# ---------------------------------------------------------------------------
# Default land-cover intactness by biome — the fraction of the reference yield a
# typical parcel of this biome still delivers, used until real per-polygon
# land-cover sampling (``landcover.py``) is wired in. These are heuristic
# judgements, not literature-derived values. A region may override this with an
# explicit ``intactness`` property.
# ---------------------------------------------------------------------------
BIOME_DEFAULT_INTACTNESS: dict[str, float] = {
    "tropical_rainforest": 0.85,
    "temperate_forest": 0.80,
    "boreal_forest": 0.90,
    "mangrove": 0.85,
    "wetland": 0.85,
    "freshwater": 0.95,
    "temperate_grassland": 0.80,
    "cropland": 0.45,
    "peri_urban": 0.50,
    "tundra": 0.95,
    "desert": 0.90,
}


def biome_default_intactness(biome_key: str) -> float:
    """Default intactness for a biome (1.0 if unknown)."""
    return BIOME_DEFAULT_INTACTNESS.get(biome_key, 1.0)


# ---------------------------------------------------------------------------
# Systemic / irreversibility layer — the "cost of conversion" reframing.
#
# A parcel's loss is more than its isolated annual value: it depends on how rare
# and load-bearing the wider system is, and some losses cannot be undone at any
# price. These weights are deliberately value-laden (heuristic, not
# literature-derived) and kept SEPARATE from the per-sqm ESV (the headline TEV is
# unchanged); they drive a systemic premium and red-line flags so the tool frames
# conversion as a permanent, externalised liability rather than a price a
# developer can outbid.
# ---------------------------------------------------------------------------

# Scarcity / irreplaceability in [0,1]: how rare, threatened and load-bearing the
# biome is globally (share already lost, endemism, time to recover). Higher -> a
# larger systemic premium when the parcel is still intact.
BIOME_SCARCITY_WEIGHT: dict[str, float] = {
    "tropical_rainforest": 0.70,
    "temperate_forest": 0.50,
    "boreal_forest": 0.60,
    "mangrove": 0.90,
    "wetland": 0.85,
    "freshwater": 0.70,
    "temperate_grassland": 0.60,
    "cropland": 0.10,
    "peri_urban": 0.15,
    "tundra": 0.80,
    "desert": 0.40,
}

# ---------------------------------------------------------------------------
# Ecosystem carbon pools and the carbon debt of conversion.
#
# Clearing or sealing land releases (a) the vegetation carbon it carries and
# (b) part of its soil carbon — not all of it. The one-time carbon debt is
#
#     debt_tCO2/ha = (vegetation_tC/ha x intactness
#                     + soil_tC/ha (0-1 m) x soil_release_fraction) x 44/12
#
# Vegetation scales with intactness (a half-cleared parcel has half the biomass
# left to lose); soil carbon does not (it persists after clearing).
#
# Pools: IPCC (2000) SRLULUCF Table 1, "Global carbon stocks in vegetation and
# soil carbon pools down to a depth of 1 m" (area, Gt C) -> t C/ha. Mangroves are
# not in that table and use IPCC 2013 Wetlands Supplement Ch. 4 defaults.
#
# Soil release fractions (share of the 0-1 m stock emitted):
#   * mineral soils — IPCC 2006 Vol. 4 Table 5.5: long-term cultivation leaves
#     F_LU of the top-30 cm stock after 20 years (0.48 tropical moist/wet, 0.69
#     temperate/boreal moist, 0.80 temperate/boreal dry), so 1 - F_LU is lost from
#     that layer; times the share of the 0-1 m stock held near the surface —
#     Jobbágy & Jackson (2000): top 20 cm = 50% (forests), 42% (grasslands), 33%
#     (shrublands). Using the top-20 cm share for the 30 cm layer is conservative.
#   * mangrove soils — midpoint of Pendleton et al. (2012)'s 25-100% release of
#     near-surface carbon on conversion.
#   * inland wetland (organic) soils — IPCC 2013 Wetlands Supplement Table 2.1:
#     drained organic soils under cropland emit 7.9 tC/ha/yr (boreal/temperate),
#     over the IPCC default 20-year transition.
# ---------------------------------------------------------------------------
# IPCC 2000 SRLULUCF Table 1: biome -> (area 1e9 ha, vegetation Gt C, soil Gt C)
SRLULUCF_TABLE_1: dict[str, tuple[float, float, float]] = {
    "Tropical forests": (1.76, 212.0, 216.0),
    "Temperate forests": (1.04, 59.0, 100.0),
    "Boreal forests": (1.37, 88.0, 471.0),
    "Temperate grasslands": (1.25, 9.0, 295.0),
    "Deserts and semideserts": (4.55, 8.0, 191.0),
    "Tundra": (0.95, 6.0, 121.0),
    "Wetlands": (0.35, 15.0, 225.0),
    "Croplands": (1.60, 3.0, 128.0),
}


def _srlulucf_density(name: str) -> tuple[float, float]:
    """(vegetation, soil) t C/ha from SRLULUCF Table 1 (Gt C / 1e9 ha = t C/ha)."""
    area, veg, soil = SRLULUCF_TABLE_1[name]
    return veg / area, soil / area


# IPCC 2006 Vol. 4 Table 5.5 F_LU (long-term cultivated) and Jobbágy & Jackson
# (2000) top-20 cm share of the 0-1 m SOC stock.
F_LU_TROPICAL_MOIST = 0.48
F_LU_TEMPERATE_MOIST = 0.69
F_LU_TEMPERATE_DRY = 0.80
TOPSOIL_SHARE_FOREST = 0.50
TOPSOIL_SHARE_GRASSLAND = 0.42
TOPSOIL_SHARE_SHRUBLAND = 0.33

# IPCC 2013 Wetlands Supplement: mangrove above-ground biomass (Table 4.3,
# tropical wet, t d.m./ha), root:shoot ratio (Table 4.5), carbon fraction
# (Table 4.2), soil carbon stock (Table 4.11, aggregated organic + mineral).
MANGROVE_AGB_T_DM_HA = 192.0
MANGROVE_ROOT_SHOOT = 0.49
MANGROVE_CARBON_FRACTION = 0.451
MANGROVE_SOIL_TC_HA = 386.0
MANGROVE_SOIL_RELEASE = (0.25 + 1.00) / 2  # Pendleton et al. 2012 range midpoint

# IPCC 2013 Wetlands Supplement Table 2.1, cropland drained (boreal/temperate).
DRAINED_ORGANIC_SOIL_EF_TC_HA_YR = 7.9
IPCC_TRANSITION_YEARS = 20


def _mineral_release(f_lu: float, topsoil_share: float) -> float:
    return round((1.0 - f_lu) * topsoil_share, 4)


def _pool(veg_tc: float, soil_tc: float, release: float, basis: str, source: str) -> dict:
    return {
        "vegetation_tc_ha": round(veg_tc, 2),
        "soil_tc_ha": round(soil_tc, 2),
        "soil_release_fraction": release,
        "basis": basis,
        "source": source,
    }


_wet_veg, _wet_soil = _srlulucf_density("Wetlands")
_crop_veg, _crop_soil = _srlulucf_density("Croplands")

BIOME_CARBON_POOLS: dict[str, dict] = {
    "tropical_rainforest": _pool(
        *_srlulucf_density("Tropical forests"),
        _mineral_release(F_LU_TROPICAL_MOIST, TOPSOIL_SHARE_FOREST),
        "literature", "IPCC 2000 SRLULUCF Table 1; IPCC 2006 Table 5.5; Jobbágy & Jackson 2000",
    ),
    "temperate_forest": _pool(
        *_srlulucf_density("Temperate forests"),
        _mineral_release(F_LU_TEMPERATE_MOIST, TOPSOIL_SHARE_FOREST),
        "literature", "IPCC 2000 SRLULUCF Table 1; IPCC 2006 Table 5.5; Jobbágy & Jackson 2000",
    ),
    "boreal_forest": _pool(
        *_srlulucf_density("Boreal forests"),
        _mineral_release(F_LU_TEMPERATE_MOIST, TOPSOIL_SHARE_FOREST),
        "literature", "IPCC 2000 SRLULUCF Table 1; IPCC 2006 Table 5.5 (mineral-soil factor; "
        "understates losses from boreal peat)",
    ),
    "mangrove": _pool(
        MANGROVE_AGB_T_DM_HA * (1 + MANGROVE_ROOT_SHOOT) * MANGROVE_CARBON_FRACTION,
        MANGROVE_SOIL_TC_HA,
        MANGROVE_SOIL_RELEASE,
        "literature", "IPCC 2013 Wetlands Supplement Tables 4.2, 4.3, 4.5, 4.11; Pendleton et al. 2012",
    ),
    "wetland": _pool(
        _wet_veg, _wet_soil,
        round(DRAINED_ORGANIC_SOIL_EF_TC_HA_YR * IPCC_TRANSITION_YEARS / _wet_soil, 4),
        "literature", "IPCC 2000 SRLULUCF Table 1; IPCC 2013 Wetlands Supplement Table 2.1",
    ),
    "freshwater": _pool(
        0.0, 0.0, 0.0, "literature", "Not assessed: open water (sediment carbon not counted)",
    ),
    "temperate_grassland": _pool(
        *_srlulucf_density("Temperate grasslands"),
        _mineral_release(F_LU_TEMPERATE_DRY, TOPSOIL_SHARE_GRASSLAND),
        "literature", "IPCC 2000 SRLULUCF Table 1; IPCC 2006 Table 5.5; Jobbágy & Jackson 2000",
    ),
    "cropland": _pool(
        _crop_veg, _crop_soil,
        _mineral_release(F_LU_TEMPERATE_MOIST, TOPSOIL_SHARE_GRASSLAND),
        "estimate", "IPCC 2000 SRLULUCF Table 1 stocks; release on sealing is an unverified "
        "proxy using the cultivation factor",
    ),
    "peri_urban": _pool(
        _crop_veg, _crop_soil,
        _mineral_release(F_LU_TEMPERATE_MOIST, TOPSOIL_SHARE_GRASSLAND),
        "estimate", "Proxy: cropland pools (no SRLULUCF class for peri-urban land)",
    ),
    "tundra": _pool(
        *_srlulucf_density("Tundra"),
        _mineral_release(F_LU_TEMPERATE_MOIST, TOPSOIL_SHARE_FOREST),
        "estimate", "IPCC 2000 SRLULUCF Table 1 stocks; release is a mineral-soil proxy that "
        "does not capture permafrost thaw (flagged as a red line instead)",
    ),
    "desert": _pool(
        *_srlulucf_density("Deserts and semideserts"),
        _mineral_release(F_LU_TEMPERATE_DRY, TOPSOIL_SHARE_SHRUBLAND),
        "literature", "IPCC 2000 SRLULUCF Table 1; IPCC 2006 Table 5.5; Jobbágy & Jackson 2000",
    ),
}


def biome_carbon_stock_tco2_ha(biome_key: str) -> float:
    """Total ecosystem carbon (vegetation + 0-1 m soil), tCO2/ha — for reference."""
    pool = BIOME_CARBON_POOLS.get(biome_key)
    if not pool:
        return 0.0
    return (pool["vegetation_tc_ha"] + pool["soil_tc_ha"]) * TCO2_PER_TC


def biome_carbon_debt_tco2_ha(biome_key: str, intactness: float = 1.0) -> float:
    """One-time CO2 released per hectare when the land is cleared or sealed."""
    pool = BIOME_CARBON_POOLS.get(biome_key)
    if not pool:
        return 0.0
    intactness = min(max(intactness, 0.0), 1.0)
    tc = pool["vegetation_tc_ha"] * intactness + pool["soil_tc_ha"] * pool["soil_release_fraction"]
    return tc * TCO2_PER_TC


# Backwards-compatible view: total stock per biome (tCO2/ha).
BIOME_CARBON_STOCK_TCO2_HA: dict[str, float] = {
    key: round(biome_carbon_stock_tco2_ha(key), 1) for key in BIOME_CARBON_POOLS
}

# Non-substitutable / irreversible losses — flagged, not monetised. Marked outside
# the money figures on purpose: they cannot be netted against revenue at any price.
_RL_BIODIVERSITY = {
    "service": "biodiversity_premium",
    "label": "Species & habitat",
    "reason": "Extinctions are irreversible — biodiversity cannot be recreated at any price.",
}
_RL_OLD_GROWTH = {
    "service": "biodiversity_premium",
    "label": "Old-growth structure",
    "reason": "Centuries to regenerate the structure and soils, if ever.",
}
_RL_PEAT = {
    "service": "carbon_capture",
    "label": "Ancient soil & peat carbon",
    "reason": "Stored over millennia, released in years — not recoverable on human timescales.",
}
_RL_PERMAFROST = {
    "service": "carbon_capture",
    "label": "Permafrost carbon",
    "reason": "Thaw is self-reinforcing and irreversible on human timescales.",
}
_RL_AQUIFER = {
    "service": "water_filtration",
    "label": "Aquifer & water supply",
    "reason": "Aquifers, once depleted or contaminated, may never recover.",
}
_RL_TOPSOIL = {
    "service": "soil_nutrient_value",
    "label": "Topsoil",
    "reason": "Fertile topsoil takes centuries to build and is lost in a single conversion.",
}

BIOME_RED_LINES: dict[str, list[dict]] = {
    "tropical_rainforest": [_RL_BIODIVERSITY, _RL_OLD_GROWTH],
    "temperate_forest": [_RL_BIODIVERSITY, _RL_OLD_GROWTH],
    "boreal_forest": [_RL_BIODIVERSITY, _RL_PEAT],
    "mangrove": [_RL_BIODIVERSITY, _RL_PEAT],
    "wetland": [_RL_BIODIVERSITY, _RL_PEAT, _RL_AQUIFER],
    "freshwater": [_RL_AQUIFER, _RL_BIODIVERSITY],
    "temperate_grassland": [_RL_TOPSOIL, _RL_BIODIVERSITY],
    "cropland": [_RL_TOPSOIL],
    "peri_urban": [],
    "tundra": [_RL_PERMAFROST, _RL_BIODIVERSITY],
    "desert": [_RL_BIODIVERSITY],
}


def biome_scarcity_weight(biome_key: str) -> float:
    return BIOME_SCARCITY_WEIGHT.get(biome_key, 0.3)


def biome_red_lines(biome_key: str) -> list[dict]:
    return list(BIOME_RED_LINES.get(biome_key, []))


# Order in which yield categories are reported (matches the product spec).
YIELD_CATEGORIES = (
    "carbon_capture",
    "climate_regulation",
    "water_filtration",
    "biodiversity_premium",
    "soil_nutrient_value",
)


# ---------------------------------------------------------------------------
# Currency conversion.
#
# Static fallback rates relative to USD (units of currency per 1 USD): the
# European Central Bank reference rates for 2026-10-16, as served by Frankfurter
# (the same feed ``live_data.py`` uses when ALPHA_LIVE_DATA is on). They only
# convert the 2024-USD figures for display; they are not a price-year adjustment.
# ---------------------------------------------------------------------------
FX_AS_OF = "2026-10-16"
FX_SOURCE = "European Central Bank reference rates (via Frankfurter)"

CURRENCIES: dict[str, dict] = {
    "USD": {"label": "US Dollar", "symbol": "$", "rate_per_usd": 1.0},
    "EUR": {"label": "Euro", "symbol": "€", "rate_per_usd": 0.8887},
    "BRL": {"label": "Brazilian Real", "symbol": "R$", "rate_per_usd": 5.0828},
}

DEFAULT_CURRENCY = "USD"


def biome_per_sqm_usd(biome_key: str, carbon_price: float | None = None) -> dict[str, float]:
    """Return the 5 reference yields for a biome, in USD per sqm per year.

    Carbon is derived from the biome's sequestration rate and a carbon price; the
    other four are converted from USD/ha/yr to USD/sqm/yr. ``carbon_price``
    defaults to the static reference (``CARBON_PRICE_USD_PER_TCO2``); the API layer
    may inject a live market price (see ``live_data.py``).
    """
    b = BIOMES[biome_key]
    price = CARBON_PRICE_USD_PER_TCO2 if carbon_price is None else carbon_price
    carbon_usd_ha_yr = b["sequestration_tco2_ha_yr"] * price
    return {
        "carbon_capture": carbon_usd_ha_yr / SQM_PER_HECTARE,
        "climate_regulation": b["climate_regulation_usd_ha_yr"] / SQM_PER_HECTARE,
        "water_filtration": b["water_filtration_usd_ha_yr"] / SQM_PER_HECTARE,
        "biodiversity_premium": b["biodiversity_premium_usd_ha_yr"] / SQM_PER_HECTARE,
        "soil_nutrient_value": b["soil_nutrient_value_usd_ha_yr"] / SQM_PER_HECTARE,
    }
