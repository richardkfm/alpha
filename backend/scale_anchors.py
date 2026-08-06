"""alpha — human-scale comparison anchors for the headline figures.

The valuation engine produces numbers nobody has an intuition for. A standing
rainforest worth 7.1 trillion euros is legible after the formatting work, but
still not *comprehensible*. Anchoring it to something the reader already has a
feel for — "roughly twice Apple's market capitalisation" — is what makes the
magnitude land.

Two rules govern the table below.

1. **Flows are only ever compared to flows, stocks only to stocks.** Total
   Ecosystem Value is a per-year flow; the standing-asset value and the
   conversion liability are present values. Comparing a present value to a
   country's annual GDP is an apples-to-oranges error, and alpha is careful
   about exactly this distinction elsewhere (it is why the TEV headline carries
   a "/ yr" marker). Every anchor is tagged, and ``rank_anchors`` will not cross
   the two.
2. **Every anchor is dated and sourced.** These are indicative reference values
   that drift year to year, like the FX and carbon references in
   ``reference_data.py``. They are surfaced in the Data Hub with the same
   provenance treatment, and are *approximations offered as approximations* —
   the UI renders them behind a "≈".

This module does no I/O and computes no valuations; it only ranks.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

# Anchor kinds. A per-year quantity vs. a present value / accumulated total.
KIND_FLOW = "flow"
KIND_STOCK = "stock"

# Below this the exercise is absurd: a two-hectare garden worth $12,000 is not
# usefully "0.000002x Austria's GDP". Better to show nothing.
MIN_VALUE_USD = 1e9

# A comparison only reads well when the multiple is a small, graspable number.
# Outside this window the anchor is the wrong size and is discarded.
MIN_MULTIPLE = 0.25
MAX_MULTIPLE = 50.0

# The multiple we aim for. "2x Austria's GDP" reads better than "0.9x" (which
# invites "so, about the same?") or "18x" (which is back to being abstract).
_TARGET_MULTIPLE = 2.0

# ---------------------------------------------------------------------------
# The table.
#
# ``locales`` lists the audiences an anchor resonates with; an empty list means
# universal. This only biases *selection* — see ``rank_anchors``, which returns
# a shortlist and lets the UI make the final locale-aware pick, since the
# valuation endpoint has no idea what language the reader is using.
#
# Values are rounded hard on purpose. Spurious precision on a figure introduced
# by "≈" would be a false promise, and these all drift year to year.
# ---------------------------------------------------------------------------
ANCHORS: List[Dict[str, Any]] = [
    # --- annual flows ------------------------------------------------------
    {
        "key": "nasa_annual_budget",
        "kind": KIND_FLOW,
        "usd": 2.5e10,
        "locales": [],
        "as_of": "2025",
        "source": "NASA FY2025 enacted budget request",
    },
    {
        "key": "revenue_netflix",
        "kind": KIND_FLOW,
        "usd": 3.9e10,
        "locales": [],
        "as_of": "2024",
        "source": "Netflix Inc. FY2024 annual report",
    },
    {
        "key": "eu_annual_budget",
        "kind": KIND_FLOW,
        "usd": 2.1e11,
        "locales": ["de", "es"],
        "as_of": "2025",
        "source": "European Commission, 2025 budget (commitments)",
    },
    {
        "key": "revenue_apple",
        "kind": KIND_FLOW,
        "usd": 3.9e11,
        "locales": [],
        "as_of": "FY2024",
        "source": "Apple Inc. Form 10-K, FY2024 net sales",
    },
    {
        "key": "gdp_austria",
        "kind": KIND_FLOW,
        "usd": 5.2e11,
        "locales": ["de"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "revenue_walmart",
        "kind": KIND_FLOW,
        "usd": 6.8e11,
        "locales": [],
        "as_of": "FY2025",
        "source": "Walmart Inc. Form 10-K, FY2025 total revenue",
    },
    {
        "key": "gdp_switzerland",
        "kind": KIND_FLOW,
        "usd": 9.4e11,
        "locales": ["de"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "gdp_spain",
        "kind": KIND_FLOW,
        "usd": 1.73e12,
        "locales": ["es"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "gdp_mexico",
        "kind": KIND_FLOW,
        "usd": 1.85e12,
        "locales": ["es"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "gdp_brazil",
        "kind": KIND_FLOW,
        "usd": 2.2e12,
        "locales": ["es"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "military_spending_world",
        "kind": KIND_FLOW,
        "usd": 2.7e12,
        "locales": [],
        "as_of": "2024",
        "source": "SIPRI Military Expenditure Database",
    },
    {
        "key": "gdp_uk",
        "kind": KIND_FLOW,
        "usd": 3.6e12,
        "locales": ["en"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "gdp_germany",
        "kind": KIND_FLOW,
        "usd": 4.7e12,
        "locales": ["de"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "gdp_usa",
        "kind": KIND_FLOW,
        "usd": 2.9e13,
        "locales": ["en"],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (nominal GDP)",
    },
    {
        "key": "gdp_world",
        "kind": KIND_FLOW,
        "usd": 1.1e14,
        "locales": [],
        "as_of": "2024",
        "source": "IMF World Economic Outlook (world nominal GDP)",
    },
    # --- stocks / present values -------------------------------------------
    {
        "key": "apollo_programme",
        "kind": KIND_STOCK,
        "usd": 2.8e11,
        "locales": [],
        "as_of": "2024 prices",
        "source": "NASA historical programme cost, inflation-adjusted",
    },
    {
        "key": "debt_germany",
        "kind": KIND_STOCK,
        "usd": 2.9e12,
        "locales": ["de"],
        "as_of": "2024",
        "source": "Eurostat general government gross debt",
    },
    {
        "key": "marketcap_apple",
        "kind": KIND_STOCK,
        "usd": 3.5e12,
        "locales": [],
        "as_of": "2025-12",
        "source": "market capitalisation, exchange close",
    },
    {
        "key": "marketcap_nvidia",
        "kind": KIND_STOCK,
        "usd": 4.3e12,
        "locales": [],
        "as_of": "2025-12",
        "source": "market capitalisation, exchange close",
    },
    {
        "key": "all_gold_ever_mined",
        "kind": KIND_STOCK,
        "usd": 1.8e13,
        "locales": [],
        "as_of": "2025",
        "source": "World Gold Council above-ground stocks at spot price",
    },
    {
        "key": "debt_usa",
        "kind": KIND_STOCK,
        "usd": 3.6e13,
        "locales": ["en"],
        "as_of": "2025",
        "source": "US Treasury, total public debt outstanding",
    },
    {
        "key": "global_equity_marketcap",
        "kind": KIND_STOCK,
        "usd": 1.2e14,
        "locales": [],
        "as_of": "2025",
        "source": "World Federation of Exchanges, domestic market cap",
    },
]

_BY_KEY: Dict[str, Dict[str, Any]] = {a["key"]: a for a in ANCHORS}


def anchor(key: str) -> Dict[str, Any] | None:
    """Look up a single anchor by key."""
    return _BY_KEY.get(key)


def _score(multiple: float) -> float:
    """Distance from the ideal multiple, in orders of magnitude. Lower is better."""
    return abs(math.log10(multiple) - math.log10(_TARGET_MULTIPLE))


def rank_anchors(
    value_usd: float | None,
    kind: str,
    limit: int = 3,
    exclude: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """Shortlist the anchors that make `value_usd` graspable, best first.

    Returns up to `limit` entries of ``{"anchor", "multiple", "locales"}``, or an
    empty list when nothing sensible fits — a figure below ``MIN_VALUE_USD``, or
    one where every anchor lands outside the readable multiple window.

    A *shortlist* rather than a single winner, because picking the anchor an
    audience relates to needs the UI language, and ``POST /api/v1/valuation``
    does not take one. Threading a locale through would mean re-fetching the
    whole valuation on every language switch; returning candidates lets the
    frontend choose client-side. The list is ordered by how well the multiple
    reads, so a caller that ignores locale entirely still gets a good answer by
    taking the first entry.

    `exclude` drops anchors already spoken for. The standing-asset value and the
    conversion liability are both stocks of a similar magnitude, so without it
    they almost always pick the same anchor and the panel says "Apple's market
    cap" twice.
    """
    if value_usd is None:
        return []
    try:
        value = float(value_usd)
    except (TypeError, ValueError):
        return []
    if not math.isfinite(value) or abs(value) < MIN_VALUE_USD:
        return []

    excluded = set(exclude)
    scored: List[Tuple[float, str, Dict[str, Any]]] = []
    for a in ANCHORS:
        if a["kind"] != kind or a["key"] in excluded:
            continue
        multiple = abs(value) / a["usd"]
        if not (MIN_MULTIPLE <= multiple <= MAX_MULTIPLE):
            continue
        # Key breaks ties so the same input always yields the same output.
        scored.append((_score(multiple), a["key"], {
            "anchor": a["key"],
            "multiple": round(multiple, 3),
            "locales": list(a["locales"]),
        }))

    scored.sort(key=lambda row: (row[0], row[1]))
    return [entry for _, _, entry in scored[:limit]]


def anchor_provenance() -> List[Dict[str, str]]:
    """Source + as-of per anchor, for the Data Hub's data catalogue."""
    return [
        {"key": a["key"], "kind": a["kind"], "source": a["source"], "as_of": a["as_of"]}
        for a in ANCHORS
    ]
