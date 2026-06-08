"""alpha — Phase 4 live market data (FX + carbon price) with graceful fallback.

Self-hosted / AGPL-friendly and standard-library only (``urllib``): an in-memory
TTL cache plus a transparent fallback to the documented static reference values
whenever a feed is disabled, unconfigured, or unreachable — so a valuation never
fails because an upstream is down, and an offline deployment keeps working.

Configuration (all optional)
----------------------------
- ``ALPHA_LIVE_DATA``      enable live fetching ("1"/"true"); default off (static).
- ``ALPHA_LIVE_TTL``       cache lifetime in seconds (default 3600).
- ``ALPHA_FX_URL``         FX endpoint returning ``{"rates": {CODE: per_USD}}``
                           (default Frankfurter / ECB).
- ``CARBON_PRICE_USD_PER_TCO2``  direct numeric override for the carbon price.
- ``CARBON_PRICE_URL``     JSON endpoint returning ``{"price_usd_per_tco2": N}``.

There is no free, keyless live carbon-spot feed, so carbon stays on the cited
reference price unless an operator wires ``CARBON_PRICE_URL`` or sets the direct
override — matching the project's "plug in your own source" deployment model.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Dict, Optional, Tuple

from reference_data import CARBON_PRICE_USD_PER_TCO2 as REF_CARBON
from reference_data import CURRENCIES, FX_AS_OF

_DEFAULT_FX_URL = "https://api.frankfurter.dev/v1/latest?base=USD"
_cache: Dict[str, Tuple[float, Any]] = {}


def _ttl() -> float:
    try:
        return float(os.environ.get("ALPHA_LIVE_TTL", "3600"))
    except ValueError:
        return 3600.0


def live_enabled() -> bool:
    return os.environ.get("ALPHA_LIVE_DATA", "").strip().lower() in ("1", "true", "yes", "on")


def _cached(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and entry[0] > time.time():
        return entry[1]
    return None


def _store(key: str, value: Any) -> Any:
    _cache[key] = (time.time() + _ttl(), value)
    return value


def _fetch_json(url: str, timeout: float = 6.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "alpha/0.3 (+ecosystem-valuation)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (configurable URL)
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Carbon price
# ---------------------------------------------------------------------------
def get_carbon_price() -> Tuple[float, Dict[str, Any]]:
    """Return ``(price_usd_per_tco2, meta)``; meta carries source/as_of/live."""
    ref_meta = {
        "source": "IPCC AR6 WGIII (2022) reference price",
        "as_of": "2022",
        "live": False,
    }

    override = os.environ.get("CARBON_PRICE_USD_PER_TCO2")
    if override:
        try:
            return float(override), {
                "source": "operator override (CARBON_PRICE_USD_PER_TCO2)",
                "as_of": "configured",
                "live": True,
            }
        except ValueError:
            pass

    url = os.environ.get("CARBON_PRICE_URL")
    if not live_enabled() or not url:
        return REF_CARBON, ref_meta

    cached = _cached("carbon")
    if cached:
        return cached
    try:
        data = _fetch_json(url)
        price = float(data["price_usd_per_tco2"])
        return _store(
            "carbon",
            (price, {"source": url, "as_of": str(data.get("as_of", "")), "live": True}),
        )
    except Exception:
        return REF_CARBON, {**ref_meta, "note": "live carbon feed unreachable — using reference price"}


# ---------------------------------------------------------------------------
# FX rates
# ---------------------------------------------------------------------------
def _static_rates() -> Dict[str, float]:
    return {code: c["rate_per_usd"] for code, c in CURRENCIES.items()}


def get_fx_rates() -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Return ``(rates_per_usd, meta)`` covering every supported currency."""
    static_meta = {"source": "static reference rates", "as_of": FX_AS_OF, "live": False}
    if not live_enabled():
        return _static_rates(), static_meta

    cached = _cached("fx")
    if cached:
        return cached
    try:
        symbols = ",".join(c for c in CURRENCIES if c != "USD")
        url = os.environ.get("ALPHA_FX_URL", _DEFAULT_FX_URL)
        sep = "&" if "?" in url else "?"
        data = _fetch_json(f"{url}{sep}symbols={symbols}")
        api_rates = data.get("rates", {}) or {}
        rates = {"USD": 1.0}
        for code in CURRENCIES:
            if code == "USD":
                continue
            val = api_rates.get(code)
            # fall back per-currency if a symbol is missing from the response
            rates[code] = float(val) if val else CURRENCIES[code]["rate_per_usd"]
        meta = {
            "source": "Frankfurter (European Central Bank)",
            "as_of": str(data.get("date", "")),
            "live": True,
            "url": url,
        }
        return _store("fx", (rates, meta))
    except Exception:
        return _static_rates(), {**static_meta, "note": "live FX unreachable — using reference rates"}


def market_snapshot() -> Dict[str, Any]:
    """Combined carbon + FX snapshot with provenance, for the API / Data Hub."""
    carbon_price, carbon_meta = get_carbon_price()
    rates, fx_meta = get_fx_rates()
    return {
        "carbon": {"price_usd_per_tco2": round(carbon_price, 4), **carbon_meta},
        "fx": {"base": "USD", "rates_per_usd": {k: round(v, 6) for k, v in rates.items()}, **fx_meta},
    }
