"""Checks that the website's numbers match the notebook (run: pytest)."""
from dashboard import data
from dashboard.data import Filters


def test_default_totals_match_notebook():
    f = Filters()
    buildings, crashes = data.filter_buildings(f), data.filter_crashes(f)
    assert buildings["affordable_units"].sum() == 101_249        # Section 5.12
    assert len(crashes) == 11_958                                 # Section 6.12 (2022–2025)
    zips = data.zip_table(buildings, crashes)
    assert (zips["hotspot_group"] == "Double hotspot").sum() == 26   # RQ7


def test_empty_selection_does_not_crash():
    f = Filters(boroughs=["Staten Island"], year_from=2025, year_to=2025, construction="New Construction",
                severity="Fatal", street="Highway")
    buildings, crashes = data.filter_buildings(f), data.filter_crashes(f)
    zips = data.zip_table(buildings, crashes)
    k = data.kpis(buildings, crashes, zips)
    assert k["crashes"] == 0 and k["near_share"] is None


def test_safe_divide():
    assert data.safe_divide(5, 0) == 0.0 and data.safe_divide(1, 4) == 0.25
