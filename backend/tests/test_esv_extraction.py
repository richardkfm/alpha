"""Tests for the Phase 3 LLM-assisted ESV extraction (deterministic backend)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from esv_extraction import extract_deterministic, extract_esv_records  # noqa: E402


SAMPLE = (
    "Carbon sequestration in the study area was valued at $120 per hectare per year. "
    "Water purification services were estimated at US$3,000 per ha per year. "
    "The report also notes that biodiversity habitat value reached €1.2 million annually. "
    "The survey covered 250 plots in 2021."
)


def test_extracts_carbon_record():
    records = extract_deterministic(SAMPLE)
    carbon = [r for r in records if r.service == "carbon_capture"]
    assert carbon, "expected a carbon record"
    assert carbon[0].value == 120.0
    assert carbon[0].currency == "USD"
    assert carbon[0].unit is not None


def test_expands_magnitude_and_thousands_separator():
    records = extract_deterministic(SAMPLE)
    water = next(r for r in records if r.service == "water_filtration")
    assert water.value == 3000.0
    bio = next(r for r in records if r.service == "biodiversity_premium")
    assert bio.value == 1_200_000.0
    assert bio.currency == "EUR"


def test_ignores_non_monetary_sentences():
    # The "250 plots in 2021" sentence has no service+money pairing -> skipped.
    records = extract_deterministic(SAMPLE)
    assert all("plots" not in r.context for r in records)


def test_requires_currency_or_unit_signal():
    # A bare number with a service word but no currency/unit is not an ESV value.
    assert extract_deterministic("Biodiversity scored 8 on the index.") == []


def test_auto_backend_offline_uses_deterministic(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    out = extract_esv_records(SAMPLE, backend="auto")
    assert out["backend"] == "deterministic"
    assert out["count"] >= 3
    assert out["records"][0]["backend"] == "deterministic"


def test_llm_backend_falls_back_when_unreachable(monkeypatch):
    # Point at a closed port so the LLM call fails fast and falls back.
    out = extract_esv_records(SAMPLE, backend="llm", host="http://127.0.0.1:1", timeout=1.0)
    assert out["backend"] == "deterministic"
    assert out["fallback_reason"]
    assert out["count"] >= 3


def test_empty_text_is_handled():
    out = extract_esv_records("   ")
    assert out["count"] == 0
    assert out["records"] == []
