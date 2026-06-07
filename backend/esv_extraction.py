"""alpha — Phase 3 LLM-assisted ESV extraction.

Ecosystem-service valuations are buried in prose inside scientific reports, ESVD
exports, and corporate TNFD nature disclosures. This module extracts them into the
structured shape alpha values with: ``{service, value, unit, currency, biome,
context}``.

Two interchangeable backends, selected at call time:

  - **deterministic** (default, offline): a transparent regex pass that pulls
    monetary figures and their nearest service keyword out of report text. No
    dependencies, fully reproducible — used in CI and whenever no model is
    configured.
  - **llm**: an Ollama / llama.cpp-compatible HTTP backend (the project's
    self-hosted, AGPL-friendly inference target). Configured via ``OLLAMA_HOST``
    (default ``http://localhost:11434``) and ``OLLAMA_MODEL`` (default
    ``llama3.1``). Uses only the Python standard library (``urllib``) so the
    backend gains no new dependency. If the model is unreachable or returns
    unparseable output, the call transparently falls back to the deterministic
    extractor rather than failing.

PDF→text extraction itself is intentionally out of scope here: deployments feed
already-extracted text (pdfminer/Tika in the ingestion pipeline) into these
functions. See ``backend/INGESTION.md``.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Optional

from reference_data import CURRENCIES, YIELD_CATEGORIES

# Map free-text service phrases to alpha's canonical yield categories.
SERVICE_KEYWORDS: dict[str, str] = {
    "carbon": "carbon_capture",
    "sequestration": "carbon_capture",
    "co2": "carbon_capture",
    "climate regulation": "climate_regulation",
    "cooling": "climate_regulation",
    "temperature regulation": "climate_regulation",
    "water purification": "water_filtration",
    "water filtration": "water_filtration",
    "water treatment": "water_filtration",
    "flow regulation": "water_filtration",
    "biodiversity": "biodiversity_premium",
    "habitat": "biodiversity_premium",
    "genetic resources": "biodiversity_premium",
    "soil": "soil_nutrient_value",
    "erosion": "soil_nutrient_value",
    "nutrient": "soil_nutrient_value",
}

# Currency symbol / code -> ISO code we support.
_CURRENCY_SYMBOLS = {"$": "USD", "US$": "USD", "€": "EUR", "R$": "BRL"}

# A monetary figure with an optional currency marker and a magnitude suffix.
_MONEY_RE = re.compile(
    r"(?P<sym>US\$|R\$|[$€])?\s?(?P<num>\d[\d,]*(?:\.\d+)?)\s?(?P<mag>billion|million|bn|m|k|thousand)?\b",
    re.IGNORECASE,
)

_MAGNITUDES = {
    "k": 1e3,
    "thousand": 1e3,
    "m": 1e6,
    "million": 1e6,
    "bn": 1e9,
    "billion": 1e9,
}

# A per-area / per-year unit phrase near the figure (USD/ha/yr and friends).
_UNIT_RE = re.compile(
    r"(?:per\s+(?:ha|hectare|sqm|m2|km2)(?:\s*(?:per\s+year|/yr|/year|annually))?|"
    r"/\s?ha(?:/yr)?|ha-?1\s?yr-?1|USD\s?ha-?1)",
    re.IGNORECASE,
)


@dataclass
class ESVRecord:
    """One extracted ecosystem-service value."""

    service: Optional[str]          # canonical YIELD_CATEGORIES key, if recognised
    raw_service: Optional[str]      # the phrase that matched
    value: Optional[float]          # numeric value, magnitude-expanded
    currency: Optional[str]         # ISO code if detected
    unit: Optional[str]             # the per-area/per-year unit phrase, if present
    context: str                    # the source sentence/snippet
    backend: str                    # "deterministic" or "llm"


def _normalise_currency(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    token = token.strip()
    if token.upper() in CURRENCIES:
        return token.upper()
    return _CURRENCY_SYMBOLS.get(token)


def _expand_magnitude(num: str, mag: Optional[str]) -> float:
    value = float(num.replace(",", ""))
    if mag:
        value *= _MAGNITUDES.get(mag.lower(), 1.0)
    return value


def _match_service(text: str) -> tuple[Optional[str], Optional[str]]:
    """Return (canonical_key, matched_phrase) for the first service keyword seen."""
    lowered = text.lower()
    best: Optional[tuple[int, str, str]] = None
    for phrase, key in SERVICE_KEYWORDS.items():
        idx = lowered.find(phrase)
        if idx != -1 and (best is None or idx < best[0]):
            best = (idx, key, phrase)
    if best is None:
        return None, None
    return best[1], best[2]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?;])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def extract_deterministic(text: str) -> list[ESVRecord]:
    """Regex extraction: one record per sentence that pairs a service with a value.

    Transparent and reproducible — the offline default and the CI baseline.
    """
    records: list[ESVRecord] = []
    for sentence in _split_sentences(text):
        service_key, raw_service = _match_service(sentence)
        if service_key is None:
            continue
        money = _MONEY_RE.search(sentence)
        if not money or not money.group("num"):
            continue
        # Require a real monetary signal: a currency marker or a per-area unit,
        # so we don't capture stray years/counts.
        unit_match = _UNIT_RE.search(sentence)
        currency = _normalise_currency(money.group("sym"))
        if currency is None and unit_match is None:
            continue
        records.append(
            ESVRecord(
                service=service_key,
                raw_service=raw_service,
                value=_expand_magnitude(money.group("num"), money.group("mag")),
                currency=currency,
                unit=unit_match.group(0) if unit_match else None,
                context=sentence,
                backend="deterministic",
            )
        )
    return records


_LLM_SYSTEM = (
    "You extract ecosystem-service valuations from scientific and TNFD report "
    "text. Return ONLY a JSON array. Each element must have keys: service (one of "
    + ", ".join(YIELD_CATEGORIES)
    + " or null), value (number or null), currency (USD/EUR/BRL or null), unit "
    "(string or null), context (the source sentence). Do not invent values."
)


def _ollama_extract(text: str, host: str, model: str, timeout: float) -> list[ESVRecord]:
    """Call an Ollama-compatible /api/chat endpoint and parse its JSON reply."""
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": text},
        ],
    }
    req = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    content = body.get("message", {}).get("content", "")
    parsed = json.loads(content)
    # Models may wrap the array in an object; accept either shape.
    if isinstance(parsed, dict):
        parsed = parsed.get("records") or parsed.get("results") or next(
            (v for v in parsed.values() if isinstance(v, list)), []
        )

    records: list[ESVRecord] = []
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        service = item.get("service")
        if service not in YIELD_CATEGORIES:
            service = None
        records.append(
            ESVRecord(
                service=service,
                raw_service=item.get("raw_service") or service,
                value=_coerce_float(item.get("value")),
                currency=_normalise_currency(item.get("currency")),
                unit=item.get("unit"),
                context=str(item.get("context", "")),
                backend="llm",
            )
        )
    return records


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def extract_esv_records(
    text: str,
    *,
    backend: str = "auto",
    host: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Extract ESV records from report text.

    ``backend``:
      - ``"deterministic"`` — regex only.
      - ``"llm"`` — Ollama-compatible model, falling back to regex on any error.
      - ``"auto"`` (default) — use the LLM when ``OLLAMA_HOST`` is configured,
        otherwise the deterministic extractor.

    Returns ``{backend, model, records: [...], count, fallback_reason}``.
    """
    text = (text or "").strip()
    if not text:
        return {"backend": "deterministic", "model": None, "records": [], "count": 0,
                "fallback_reason": "empty input"}

    host = host or os.environ.get("OLLAMA_HOST")
    model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")

    want_llm = backend == "llm" or (backend == "auto" and bool(host))
    if want_llm:
        host = host or "http://localhost:11434"
        try:
            records = _ollama_extract(text, host, model, timeout)
            return {"backend": "llm", "model": model,
                    "records": [asdict(r) for r in records], "count": len(records),
                    "fallback_reason": None}
        except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as exc:
            records = extract_deterministic(text)
            return {"backend": "deterministic", "model": None,
                    "records": [asdict(r) for r in records], "count": len(records),
                    "fallback_reason": f"llm unavailable ({type(exc).__name__}); used deterministic"}

    records = extract_deterministic(text)
    return {"backend": "deterministic", "model": None,
            "records": [asdict(r) for r in records], "count": len(records),
            "fallback_reason": None}
