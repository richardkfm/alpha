"""Tests for the human-scale comparison anchors.

The property that matters most is the flow/stock separation. Everything else
here is about not showing the reader a comparison that is worse than none.
"""
import math

import pytest

import scale_anchors as sa
from valuation import compute_valuation

# A continental-scale polygon, so every headline figure is large enough to have
# a comparison at all.
BASIN = {
    "type": "Polygon",
    "coordinates": [[[-70, -10], [-50, -10], [-50, 5], [-70, 5], [-70, -10]]],
}


# --- the table itself -------------------------------------------------------
def test_every_anchor_is_tagged_dated_and_sourced():
    assert sa.ANCHORS, "an empty table would silently disable the feature"
    for a in sa.ANCHORS:
        assert a["kind"] in (sa.KIND_FLOW, sa.KIND_STOCK), a["key"]
        assert a["usd"] > 0, a["key"]
        assert a["as_of"], a["key"]
        assert a["source"], a["key"]
        assert isinstance(a["locales"], list), a["key"]


def test_anchor_keys_are_unique():
    keys = [a["key"] for a in sa.ANCHORS]
    assert len(keys) == len(set(keys))


def test_both_kinds_span_a_wide_range_of_magnitudes():
    """A narrow table leaves figures with no anchor in the readable window."""
    for kind in (sa.KIND_FLOW, sa.KIND_STOCK):
        values = sorted(a["usd"] for a in sa.ANCHORS if a["kind"] == kind)
        assert len(values) >= 5, kind
        # No gap so wide that a value falling in it misses every anchor. Two
        # neighbours may be at most MAX/MIN apart for the windows to overlap.
        for lo, hi in zip(values, values[1:]):
            assert hi / lo <= sa.MAX_MULTIPLE / sa.MIN_MULTIPLE, (kind, lo, hi)


# --- selection --------------------------------------------------------------
def test_flows_never_draw_stock_anchors_and_vice_versa():
    """The apples-to-oranges guard: a present value is not a year's GDP."""
    stock_keys = {a["key"] for a in sa.ANCHORS if a["kind"] == sa.KIND_STOCK}
    flow_keys = {a["key"] for a in sa.ANCHORS if a["kind"] == sa.KIND_FLOW}

    for value in (5e11, 3e12, 4e13):
        flows = {e["anchor"] for e in sa.rank_anchors(value, sa.KIND_FLOW)}
        stocks = {e["anchor"] for e in sa.rank_anchors(value, sa.KIND_STOCK)}
        assert flows <= flow_keys
        assert stocks <= stock_keys
        assert not (flows & stocks)


def test_multiples_stay_inside_the_readable_window():
    for value in (2e10, 5e11, 3e12, 4e13, 9e13):
        for kind in (sa.KIND_FLOW, sa.KIND_STOCK):
            for entry in sa.rank_anchors(value, kind):
                assert sa.MIN_MULTIPLE <= entry["multiple"] <= sa.MAX_MULTIPLE


def test_best_entry_is_the_one_closest_to_the_target_multiple():
    entries = sa.rank_anchors(1.0e12, sa.KIND_FLOW)
    assert entries
    scores = [abs(math.log10(e["multiple"]) - math.log10(2.0)) for e in entries]
    assert scores == sorted(scores)


def test_the_multiple_actually_reconstructs_the_value():
    value = 7.3e12
    for entry in sa.rank_anchors(value, sa.KIND_STOCK):
        anchor = sa.anchor(entry["anchor"])
        assert entry["multiple"] == pytest.approx(value / anchor["usd"], rel=1e-3)


def test_small_figures_get_no_comparison_at_all():
    """"0.000002x Austria's GDP" is worse than saying nothing."""
    assert sa.rank_anchors(12_000, sa.KIND_FLOW) == []
    assert sa.rank_anchors(5e8, sa.KIND_STOCK) == []
    assert sa.rank_anchors(0, sa.KIND_FLOW) == []
    assert sa.rank_anchors(None, sa.KIND_FLOW) == []
    assert sa.rank_anchors(float("nan"), sa.KIND_FLOW) == []
    assert sa.rank_anchors("not a number", sa.KIND_FLOW) == []


def test_exclude_keeps_two_adjacent_figures_from_sharing_an_anchor():
    first = sa.rank_anchors(3e12, sa.KIND_STOCK)
    assert first
    taken = first[0]["anchor"]
    second = sa.rank_anchors(3e12, sa.KIND_STOCK, exclude=[taken])
    assert taken not in {e["anchor"] for e in second}


def test_ranking_is_deterministic():
    assert sa.rank_anchors(4.2e12, sa.KIND_STOCK) == sa.rank_anchors(4.2e12, sa.KIND_STOCK)


def test_shortlist_carries_the_locale_tags_the_ui_picks_by():
    entries = sa.rank_anchors(1e12, sa.KIND_FLOW, limit=99)
    assert entries
    for entry in entries:
        assert entry["locales"] == sa.anchor(entry["anchor"])["locales"]
    # At least one locale-tagged anchor must be reachable, or the frontend's
    # locale preference can never fire.
    assert any(e["locales"] for e in entries)


# --- wiring into the valuation ----------------------------------------------
def test_valuation_reports_comparisons_for_all_three_headline_figures():
    result = compute_valuation(BASIN, biome="tropical_rainforest")
    cmp = result["comparisons"]
    assert set(cmp) == {
        "total_ecosystem_value_per_year",
        "asset_value_total",
        "conversion_liability",
    }
    assert all(cmp.values()), "a basin this size should compare to something"


def test_comparisons_are_identical_in_every_currency():
    """The multiples are USD ratios, so switching currency must not move them."""
    usd = compute_valuation(BASIN, biome="tropical_rainforest", currency="USD")
    eur = compute_valuation(BASIN, biome="tropical_rainforest", currency="EUR")
    brl = compute_valuation(BASIN, biome="tropical_rainforest", currency="BRL")
    assert usd["comparisons"] == eur["comparisons"] == brl["comparisons"]
    # Guard against the test passing because FX is a no-op.
    assert usd["total_ecosystem_value_per_year"] != brl["total_ecosystem_value_per_year"]


def test_annual_flow_and_standing_asset_use_different_kinds_of_anchor():
    cmp = compute_valuation(BASIN, biome="tropical_rainforest")["comparisons"]
    flow = sa.anchor(cmp["total_ecosystem_value_per_year"][0]["anchor"])
    stock = sa.anchor(cmp["asset_value_total"][0]["anchor"])
    assert flow["kind"] == sa.KIND_FLOW
    assert stock["kind"] == sa.KIND_STOCK


def test_asset_and_liability_do_not_cite_the_same_anchor():
    """They are within a small factor of each other, so without the exclusion
    the panel would print the same anchor twice, inches apart."""
    cmp = compute_valuation(BASIN, biome="tropical_rainforest")["comparisons"]
    assert cmp["asset_value_total"][0]["anchor"] != cmp["conversion_liability"][0]["anchor"]


def test_a_tiny_polygon_gets_empty_shortlists_rather_than_absurd_ones():
    tiny = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]],
    }
    cmp = compute_valuation(tiny, biome="tropical_rainforest")["comparisons"]
    assert cmp["total_ecosystem_value_per_year"] == []
    assert cmp["asset_value_total"] == []
