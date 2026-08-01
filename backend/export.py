"""alpha — investor-report export (Phase 4).

Serialise a valuation result (as produced by ``main.build_valuation`` /
``valuation.compute_valuation``) into a downloadable **CSV** data sheet or a
one-page **PDF** brief.

These are *pure serialisers*: they perform no valuation maths, so an exported
report always carries byte-for-byte the same figures as ``POST
/api/v1/valuation``. CSV uses the standard library; PDF uses ``reportlab``
(pure-Python, no system libraries).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Human labels for the five yield categories, in the product-spec order. Mirrors
# frontend/src/data/yields.js and reference_data.YIELD_CATEGORIES so the report
# reads like the web UI.
_SERVICE_LABELS: List[Tuple[str, str]] = [
    ("carbon_capture", "Carbon Capture"),
    ("climate_regulation", "Climate Regulation"),
    ("water_filtration", "Water Filtration"),
    ("biodiversity_premium", "Biodiversity Premium"),
    ("soil_nutrient_value", "Soil Nutrient Value"),
]


# Square metres in a hectare. Per-sqm yields are sub-cent, so the PDF reports
# them per hectare — matching what the web UI shows. The CSV deliberately keeps
# the API's raw per-sqm figures, since it is the machine-readable sheet.
SQM_PER_HA = 10_000

# Number conventions per supported UI locale: (thousands, decimal, template).
# Deliberately hand-rolled rather than using the stdlib ``locale`` module, which
# mutates process-global state and is unsafe inside a server process.
_NUMBER_STYLES: Dict[str, Tuple[str, str, str]] = {
    "en": (",", ".", "{sym}{num}"),
    "de": (".", ",", "{num} {sym}"),
    "es": (".", ",", "{num} {sym}"),
}
DEFAULT_LOCALE = "en"


def format_money(
    value: Any, symbol: str = "$", locale: str = DEFAULT_LOCALE, decimals: int = 0
) -> str:
    """Group and place a currency amount the way `locale` writes numbers.

    German and Spanish swap the separators and put the symbol after the amount
    (``1.234.567 €``), where English prefixes it (``$1,234,567``). Full digits
    throughout — a disclosure document should never make the reader decode an
    abbreviation, which also keeps the report clear of the Milliarde/Billion
    false friend entirely.
    """
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    thousands, decimal, template = _NUMBER_STYLES.get(
        locale, _NUMBER_STYLES[DEFAULT_LOCALE]
    )
    # Format with Python's own separators, then swap via a placeholder so the
    # two-step substitution cannot collide (both styles reuse "." and ",").
    num = f"{v:,.{decimals}f}".replace(",", "\x00").replace(".", decimal)
    num = num.replace("\x00", thousands)
    return template.format(sym=symbol, num=num)


def report_title(result: Dict[str, Any], name: Optional[str] = None) -> str:
    """Headline for the report: the region name (if given) plus its biome."""
    biome = result.get("biome", "Ecosystem")
    return f"{name} — {biome}" if name else biome


def filename_slug(result: Dict[str, Any], name: Optional[str] = None) -> str:
    """URL/filename-safe slug from the region name (or biome key)."""
    base = str(name or result.get("biome_key") or "valuation")
    slug = "".join(c if c.isalnum() else "-" for c in base.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "valuation"


def _generated_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _discount_label(result: Dict[str, Any]) -> str:
    rate = (result.get("capitalized_value") or {}).get("discount_rate")
    if isinstance(rate, (int, float)):
        return f"Capitalised standing value (@ {rate:.1%})"
    return "Capitalised standing value"


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def to_csv(result: Dict[str, Any], name: Optional[str] = None) -> str:
    """Render the valuation as a multi-block CSV data sheet (spreadsheet-ready)."""
    out = io.StringIO()
    w = csv.writer(out)
    cur = result.get("currency", "USD")
    area = result.get("area", {})
    mkt = result.get("market", {})
    carbon = mkt.get("carbon") or {}
    fx = mkt.get("fx") or {}
    cls = result.get("classification") or {}

    # Block 1 — summary / provenance.
    w.writerow(["alpha — Total Ecosystem Value report"])
    w.writerow(["Field", "Value"])
    w.writerow(["Region", name or "—"])
    w.writerow(["Biome", result.get("biome", "")])
    w.writerow(["Biome source", f"{cls.get('confidence', '')} ({cls.get('source', '')})"])
    w.writerow(["Currency", cur])
    w.writerow(["Area (m^2)", area.get("sqm", "")])
    w.writerow(["Area (hectares)", area.get("hectares", "")])
    w.writerow(["Intactness", result.get("intactness", "")])
    w.writerow(["Carbon price (USD/tCO2e)", carbon.get("price_usd_per_tco2", "")])
    w.writerow([f"FX rate ({cur} per USD)", fx.get("rate_per_usd", "")])
    w.writerow(["Generated (UTC)", _generated_utc()])
    w.writerow([])

    # Block 2 — per-service breakdown + totals.
    w.writerow(["Ecosystem service", f"Per m^2/yr ({cur})", f"Area total/yr ({cur})"])
    ps = result.get("yields_per_sqm_year", {})
    tot = result.get("yields_total_year", {})
    for key, label in _SERVICE_LABELS:
        w.writerow([label, ps.get(key, ""), tot.get(key, "")])
    w.writerow([
        "Total Ecosystem Value",
        result.get("total_ecosystem_value_per_sqm_year", ""),
        result.get("total_ecosystem_value_per_year", ""),
    ])
    pot = result.get("potential", {})
    w.writerow([
        "Potential (fully intact) TEV",
        pot.get("total_ecosystem_value_per_sqm_year", ""),
        pot.get("total_ecosystem_value_per_year", ""),
    ])
    cap = result.get("capitalized_value", {})
    w.writerow([
        _discount_label(result),
        cap.get("asset_value_per_sqm", ""),
        cap.get("asset_value_total", ""),
    ])
    w.writerow([])

    # Block 3 — conversion liability (a permanent externalised cost, not a price).
    lia = result.get("conversion_liability", {})
    sysm = result.get("systemic", {})
    w.writerow(["Conversion liability", f"Value ({cur})"])
    w.writerow(["Annual loss", lia.get("annual_loss", "")])
    w.writerow(["Present value (perpetual)", lia.get("present_value", "")])
    w.writerow(["One-time carbon debt", lia.get("carbon_debt_onetime", "")])
    w.writerow(["Systemic multiplier", sysm.get("multiplier", "")])
    w.writerow([])

    # Block 4 — red lines (non-monetised, irreversible losses).
    red = result.get("red_lines") or []
    if red:
        w.writerow(["Red lines (non-monetised, irreversible)", "Reason"])
        for r in red:
            if isinstance(r, dict):
                w.writerow([r.get("label", ""), r.get("reason", "")])
            else:
                w.writerow([str(r), ""])
        w.writerow([])

    # Block 5 — methodology footer.
    w.writerow(["Methodology"])
    w.writerow([result.get("methodology_note", "")])
    return out.getvalue()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def to_pdf(
    result: Dict[str, Any], name: Optional[str] = None, locale: str = DEFAULT_LOCALE
) -> bytes:
    """Render the valuation as a one-page PDF investor brief.

    ``locale`` selects the number conventions only (separators and symbol
    placement); the report's prose stays English.
    """
    # Imported lazily so the CSV path (and the rest of the API) has no hard
    # dependency on reportlab being installed.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    cur = result.get("currency", "USD")
    sym = result.get("currency_symbol", "")
    area = result.get("area", {})

    accent = colors.HexColor("#0f766e")
    ink = colors.HexColor("#0c1814")
    muted = colors.HexColor("#475569")
    line = colors.HexColor("#cbd5e1")

    styles = getSampleStyleSheet()
    h_title = ParagraphStyle("aTitle", parent=styles["Title"], textColor=ink, fontSize=20, spaceAfter=2)
    h_sub = ParagraphStyle("aSub", parent=styles["Normal"], textColor=muted, fontSize=10, spaceAfter=10)
    h_sec = ParagraphStyle("aSec", parent=styles["Heading2"], textColor=accent, fontSize=12, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("aBody", parent=styles["Normal"], textColor=ink, fontSize=9, leading=12)
    foot = ParagraphStyle("aFoot", parent=styles["Normal"], textColor=muted, fontSize=7.5, leading=10)

    def money(value: Any, per_sqm: bool = False) -> str:
        """Whole-area totals, or a per-sqm yield rescaled to a per-hectare one."""
        if per_sqm:
            if value is None:
                return "—"
            try:
                value = float(value) * SQM_PER_HA
            except (TypeError, ValueError):
                return str(value)
            return format_money(value, sym, locale, decimals=2)
        return format_money(value, sym, locale, decimals=0)

    elements: List[Any] = []
    elements.append(Paragraph("alpha · Total Ecosystem Value", h_sec))
    elements.append(Paragraph(report_title(result, name), h_title))
    cls = result.get("classification") or {}
    elements.append(
        Paragraph(
            f"{cur} · {format_money(area.get('hectares', 0), '', locale, 1).strip()} ha"
            f" · biome: {cls.get('confidence', '')}"
            f" · generated {_generated_utc()}",
            h_sub,
        )
    )

    # Headline figures.
    headline = [
        ["Total Ecosystem Value / yr", money(result.get("total_ecosystem_value_per_year"))],
        [_discount_label(result), money((result.get("capitalized_value") or {}).get("asset_value_total"))],
        ["Conversion liability (present value)", money((result.get("conversion_liability") or {}).get("present_value"))],
    ]
    t = Table(headline, colWidths=[110 * mm, 60 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("TEXTCOLOR", (0, 0), (0, -1), muted),
                ("TEXTCOLOR", (1, 0), (1, -1), ink),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, line),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(t)

    # Per-service breakdown.
    elements.append(Paragraph("Ecosystem-service yields", h_sec))
    ps = result.get("yields_per_sqm_year", {})
    tot = result.get("yields_total_year", {})
    rows = [["Service", f"Per ha/yr ({cur})", f"Area total/yr ({cur})"]]
    for key, label in _SERVICE_LABELS:
        rows.append([label, money(ps.get(key), per_sqm=True), money(tot.get(key))])
    rows.append([
        "Total Ecosystem Value",
        money(result.get("total_ecosystem_value_per_sqm_year"), per_sqm=True),
        money(result.get("total_ecosystem_value_per_year")),
    ])
    st = Table(rows, colWidths=[80 * mm, 45 * mm, 45 * mm])
    st.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f1f5f9")]),
                ("LINEABOVE", (0, -1), (-1, -1), 0.6, accent),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(st)

    # Conversion-liability framing.
    lia = result.get("conversion_liability", {})
    if lia:
        elements.append(Paragraph("Cost of conversion", h_sec))
        elements.append(
            Paragraph(
                f"Annual loss {money(lia.get('annual_loss'))} · present value "
                f"{money(lia.get('present_value'))} · one-time carbon debt "
                f"{money(lia.get('carbon_debt_onetime'))}. "
                f"{lia.get('note', '')}",
                body,
            )
        )

    # Red lines.
    red = result.get("red_lines") or []
    if red:
        elements.append(Paragraph("Red lines — non-monetised, irreversible", h_sec))
        for r in red:
            if isinstance(r, dict):
                elements.append(Paragraph(f"<b>{r.get('label', '')}</b> — {r.get('reason', '')}", body))
            else:
                elements.append(Paragraph(str(r), body))

    # Methodology footer.
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(result.get("methodology_note", ""), foot))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title=report_title(result, name),
        author="alpha",
    )
    doc.build(elements)
    return buf.getvalue()
