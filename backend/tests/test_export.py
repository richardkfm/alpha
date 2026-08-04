"""Tests for the Phase 4 export layer (CSV / PDF investor reports)."""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import export  # noqa: E402
from main import app, build_valuation  # noqa: E402

client = TestClient(app)

AMAZON = {
    "type": "Polygon",
    "coordinates": [[[-65, -5], [-60, -5], [-60, -2], [-65, -2], [-65, -5]]],
}


def _result():
    return build_valuation(AMAZON, explicit_biome=None, currency="USD",
                           intactness=None, discount_rate=None)


# --- locale-aware money formatting -----------------------------------------
def test_format_money_english_prefixes_and_groups_with_commas():
    assert export.format_money(1234567, "$", "en") == "$1,234,567"
    assert export.format_money(1234567.891, "$", "en", decimals=2) == "$1,234,567.89"


def test_format_money_german_suffixes_and_swaps_separators():
    # German writes 1.234.567,89 € — dots group, comma decimals, symbol last.
    assert export.format_money(1234567, "€", "de") == "1.234.567 €"
    assert export.format_money(1234567.891, "€", "de", decimals=2) == "1.234.567,89 €"


def test_format_money_spanish_matches_german_conventions():
    assert export.format_money(1234567, "R$", "es") == "1.234.567 R$"


def test_format_money_uses_full_digits_at_every_magnitude():
    # No abbreviation in the PDF: a disclosure document must never leave the
    # reader decoding "Mrd." vs "Bio." (or "billion" vs "Milliarde").
    assert export.format_money(1_500_000_000, "€", "de") == "1.500.000.000 €"
    assert export.format_money(91_234_567_890_123, "€", "de") == "91.234.567.890.123 €"


def test_format_money_handles_missing_and_unparsable_values():
    assert export.format_money(None, "€", "de") == "—"
    assert export.format_money("n/a", "€", "de") == "n/a"


def test_format_money_falls_back_to_english_for_unknown_locale():
    assert export.format_money(1234567, "$", "pt") == "$1,234,567"


def test_format_percent_follows_the_locale_decimal_separator():
    # The discount rate sat beside comma-decimal money as "3.0%" before this.
    assert export.format_percent(0.03, "en") == "3.0%"
    assert export.format_percent(0.03, "de") == "3,0%"
    assert export.format_percent(0.03, "es") == "3,0%"
    assert export.format_percent(None, "de") == "—"


def test_discount_label_localises_its_rate():
    result = {"capitalized_value": {"discount_rate": 0.03}}
    assert "3,0%" in export._discount_label(result, "de")
    assert "3.0%" in export._discount_label(result, "en")
    # No rate, no percentage to mis-punctuate.
    assert export._discount_label({}, "de") == "Capitalised standing value"


# --- serialisers -----------------------------------------------------------
def test_to_csv_parses_and_carries_totals():
    result = _result()
    text = export.to_csv(result, name="Amazon Basin")
    assert text.strip()
    rows = list(csv.reader(io.StringIO(text)))
    flat = ["|".join(r) for r in rows]
    # Region name and the TEV total row both present, and the total matches.
    assert any("Amazon Basin" in line for line in flat)
    total = str(result["total_ecosystem_value_per_year"])
    assert any(r[:1] == ["Total Ecosystem Value"] and total in r for r in rows)


def test_to_pdf_is_a_pdf():
    pdf = export.to_pdf(_result(), name="Amazon Basin")
    assert isinstance(pdf, bytes) and pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_filename_slug():
    assert export.filename_slug({}, "Amazon Basin!") == "amazon-basin"
    assert export.filename_slug({"biome_key": "mangrove"}) == "mangrove"


# --- endpoint --------------------------------------------------------------
def test_export_csv_endpoint_headers_and_totals():
    res = client.post("/api/v1/valuation/export?format=csv&name=Amazon", json=AMAZON)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "attachment" in res.headers["content-disposition"]
    assert res.headers["content-disposition"].endswith('.csv"')
    # The exported total equals the live valuation total (the reuse guarantee).
    api_total = client.post("/api/v1/valuation", json=AMAZON).json()[
        "total_ecosystem_value_per_year"
    ]
    assert str(api_total) in res.text


def test_export_pdf_endpoint():
    res = client.post("/api/v1/valuation/export?format=pdf", json=AMAZON)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content[:4] == b"%PDF"


def test_export_pdf_accepts_locale_and_rejects_unsupported_ones():
    de = client.post("/api/v1/valuation/export?format=pdf&locale=de", json=AMAZON)
    assert de.status_code == 200
    assert de.content[:4] == b"%PDF"
    # A German brief renders different bytes than the English default, since the
    # separators and symbol placement differ throughout.
    en = client.post("/api/v1/valuation/export?format=pdf&locale=en", json=AMAZON)
    assert de.content != en.content
    assert client.post(
        "/api/v1/valuation/export?format=pdf&locale=xx", json=AMAZON
    ).status_code == 422


def test_export_csv_ignores_locale_and_stays_raw():
    """The CSV is the machine-readable sheet — locale must not reformat it."""
    plain = client.post("/api/v1/valuation/export?format=csv", json=AMAZON)
    localised = client.post("/api/v1/valuation/export?format=csv&locale=de", json=AMAZON)
    assert plain.text == localised.text


def test_export_rejects_bad_format():
    res = client.post("/api/v1/valuation/export?format=xlsx", json=AMAZON)
    assert res.status_code == 422


def test_export_rejects_empty_geometry():
    res = client.post("/api/v1/valuation/export?format=csv", json={})
    assert res.status_code == 422
