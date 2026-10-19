"""Tests for the Phase 3 LLM-assisted ESV extraction (deterministic backend)."""
import io
import json
import os
import sys
import urllib.request

import pytest

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


def test_a_leading_year_is_not_mistaken_for_the_value():
    [rec] = extract_deterministic("In 2019, carbon sequestration was valued at $120 per ha per year.")
    assert rec.value == 120.0
    assert rec.currency == "USD"


def test_unit_only_figure_is_the_one_before_the_unit():
    [rec] = extract_deterministic("A 2021 survey put soil erosion control at 85 per hectare.")
    assert rec.value == 85.0
    assert rec.currency is None


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.mark.parametrize(
    "reply",
    [
        {"message": None},
        [1, 2, 3],
        {"message": {"content": None}},
        {"message": {"content": "not json at all"}},
    ],
)
def test_llm_backend_falls_back_on_a_malformed_reply(monkeypatch, reply):
    payload = json.dumps(reply).encode()
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=None: _FakeResponse(payload)
    )
    out = extract_esv_records(SAMPLE, backend="llm", host="http://llm.invalid")
    assert out["backend"] == "deterministic"
    assert out["fallback_reason"]
    assert out["count"] >= 3


def test_llm_record_with_a_non_string_currency_is_tolerated(monkeypatch):
    content = json.dumps([{"service": "carbon_capture", "value": 9, "currency": 5}])
    payload = json.dumps({"message": {"content": content}}).encode()
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=None: _FakeResponse(payload)
    )
    out = extract_esv_records(SAMPLE, backend="llm", host="http://llm.invalid")
    assert out["backend"] == "llm"
    assert out["records"][0]["currency"] is None
    assert out["records"][0]["value"] == 9.0


def test_iso_currency_codes_are_recognised():
    [rec] = extract_deterministic("Soil erosion prevention: EUR 150 per ha.")
    assert (rec.value, rec.currency) == (150.0, "EUR")
    [rec] = extract_deterministic("Carbon storage was worth BRL 2,400 per ha per year.")
    assert (rec.value, rec.currency) == (2400.0, "BRL")
