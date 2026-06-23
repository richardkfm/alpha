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


def test_export_rejects_bad_format():
    res = client.post("/api/v1/valuation/export?format=xlsx", json=AMAZON)
    assert res.status_code == 422


def test_export_rejects_empty_geometry():
    res = client.post("/api/v1/valuation/export?format=csv", json={})
    assert res.status_code == 422
