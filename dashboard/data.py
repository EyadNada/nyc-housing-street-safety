"""Load the clean tables written by the notebook (Section 11) and filter / aggregate them.

The website never repeats the cleaning. It only reads data/clean/*.csv, filters the rows
the user asked for, and aggregates them to the level each chart needs.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "clean"

BOROUGHS = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]
YEARS = [2022, 2023, 2024, 2025]
CONSTRUCTION_TYPES = ["New Construction", "Preservation"]
NEAR_RADIUS_M = 250


@dataclass
class Filters:
    """Everything the user can choose. One object travels from the controls to every chart."""
    boroughs: list = field(default_factory=lambda: list(BOROUGHS))
    year_from: int = 2022
    year_to: int = 2025
    construction: str = "All"          # "All", "New Construction", "Preservation"
    severity: str = "All"              # "All" (every serious crash) or "Fatal"
    street: str = "All"                # "All", "Local", "Highway"
    zip_code: str | None = None        # set by search ("10453") or by clicking a ZIP

    def to_dict(self):
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, values):
        return cls(**{k: v for k, v in (values or {}).items() if k in cls.__dataclass_fields__})


def _load_tables():
    buildings = pd.read_csv(DATA_DIR / "buildings_clean.csv", dtype={"zip_code": "string"},
                            parse_dates=["building_completion_date", "project_start_date"], low_memory=False)
    buildings = buildings[buildings["in_analysis_window"]].copy()          # completed 2022–2025
    buildings["completion_year"] = buildings["completion_year"].astype(int)

    crashes = pd.read_csv(DATA_DIR / "crashes_clean.csv", dtype={"zip_code": "string"},
                          parse_dates=["crash_date"], low_memory=False)
    crashes = crashes[crashes["in_analysis_window"]].copy()                 # 2022–2025 (2026 is partial)
    crashes["year"] = crashes["year"].astype(int)
    crashes["near_new_housing"] = crashes["near_new_housing"].astype("boolean")
    crashes["at_repeat_location"] = crashes["at_repeat_location"].astype("boolean")

    income = pd.read_csv(DATA_DIR / "housing_income_long.csv", dtype={"zip_code": "string"})
    income = income[income["in_analysis_window"]].copy()

    zip_info = pd.read_csv(DATA_DIR / "zip_summary.csv", dtype={"zip_code": "string"})
    zip_info = zip_info[["zip_code", "borough", "community_district", "latitude", "longitude"]]
    return buildings, crashes, income, zip_info


BUILDINGS, CRASHES, INCOME, ZIP_INFO = _load_tables()
ALL_ZIPS = set(ZIP_INFO["zip_code"])


def filter_buildings(f: Filters) -> pd.DataFrame:
    rows = BUILDINGS[BUILDINGS["borough"].isin(f.boroughs)
                     & BUILDINGS["completion_year"].between(f.year_from, f.year_to)]
    if f.construction != "All":
        rows = rows[rows["construction_type"] == f.construction]
    return rows


def filter_crashes(f: Filters) -> pd.DataFrame:
    rows = CRASHES[CRASHES["borough"].isin(f.boroughs) & CRASHES["year"].between(f.year_from, f.year_to)]
    if f.severity == "Fatal":
        rows = rows[rows["is_fatal"]]
    if f.street == "Highway":
        rows = rows[rows["on_highway"]]
    elif f.street == "Local":
        rows = rows[~rows["on_highway"]]
    return rows


def filter_income(f: Filters, building_rows: pd.DataFrame) -> pd.DataFrame:
    keys = building_rows[["project_id", "building_id"]].drop_duplicates()
    return INCOME.merge(keys, on=["project_id", "building_id"], how="inner")


def safe_divide(numerator, denominator):
    """Like DAX DIVIDE(x, y, 0) from Lab 3: returns 0 instead of an error when the filter leaves nothing."""
    return numerator / denominator if denominator else 0.0


def zip_table(building_rows: pd.DataFrame, crash_rows: pd.DataFrame) -> pd.DataFrame:
    """Level A for the current filters: one row per ZIP with units, crashes and a hotspot group."""
    housing = building_rows.dropna(subset=["zip_code"]).groupby("zip_code").agg(
        affordable_units=("affordable_units", "sum"), buildings=("building_id", "size"),
        deep_affordable_units=("deep_affordable_units", "sum"))
    crashes = crash_rows.dropna(subset=["zip_code"]).groupby("zip_code").agg(
        serious_crashes=("crash_id", "size"), deaths=("fatalities", "sum"))
    table = housing.join(crashes, how="outer").fillna(0).reset_index()     # post-join nulls -> 0 (no record = zero)
    table = table.merge(ZIP_INFO, on="zip_code", how="left")
    count_columns = ["affordable_units", "buildings", "deep_affordable_units", "serious_crashes", "deaths"]
    table[count_columns] = table[count_columns].astype(int)
    if table.empty:
        table["hotspot_group"] = pd.Series(dtype="string")
        table["priority_score"] = pd.Series(dtype=float)
        return table
    units_q75 = table["affordable_units"].quantile(0.75)
    crashes_q75 = table["serious_crashes"].quantile(0.75)
    high_units = (table["affordable_units"] >= units_q75) & (table["affordable_units"] > 0)
    high_crashes = (table["serious_crashes"] >= crashes_q75) & (table["serious_crashes"] > 0)
    table["hotspot_group"] = np.select([high_units & high_crashes, high_units, high_crashes],
                                       ["Double hotspot", "High housing only", "High crashes only"], "Neither")
    table["priority_score"] = ((table["affordable_units"].rank(pct=True)
                                + table["serious_crashes"].rank(pct=True)) / 2).round(3)
    return table


def kpis(building_rows: pd.DataFrame, crash_rows: pd.DataFrame, zips: pd.DataFrame) -> dict:
    located = crash_rows.dropna(subset=["near_new_housing"])
    return {
        "units": int(building_rows["affordable_units"].sum()),
        "buildings": int(len(building_rows)),
        "crashes": int(len(crash_rows)),
        "deaths": int(crash_rows["fatalities"].sum()),
        "near_share": safe_divide(int(located["near_new_housing"].sum()), len(located)) if len(located) else None,
        "double_hotspots": int((zips["hotspot_group"] == "Double hotspot").sum()) if not zips.empty else 0,
    }


def borough_year_table(f: Filters) -> pd.DataFrame:
    """Trend data: all 4 years for the chosen boroughs and categories (the year filter is shown as a band)."""
    full_years = Filters(**{**f.to_dict(), "year_from": YEARS[0], "year_to": YEARS[-1]})
    units = filter_buildings(full_years).groupby("completion_year")["affordable_units"].sum()
    crashes = filter_crashes(full_years).groupby("year").size()
    table = pd.DataFrame({"year": YEARS})
    table["affordable_units"] = table["year"].map(units).fillna(0).astype(int)
    table["serious_crashes"] = table["year"].map(crashes).fillna(0).astype(int)
    return table


def zip_detail(zip_code: str, f: Filters) -> dict | None:
    """Drill-through panel: numbers for one ZIP inside the current filters."""
    if not zip_code or zip_code not in ALL_ZIPS:
        return None
    info = ZIP_INFO.set_index("zip_code").loc[zip_code]
    f = Filters(**{**f.to_dict(), "boroughs": list(BOROUGHS)})     # a chosen ZIP ignores the borough filter
    building_rows = filter_buildings(f)
    building_rows = building_rows[building_rows["zip_code"] == zip_code]
    crash_rows = filter_crashes(f)
    crash_rows = crash_rows[crash_rows["zip_code"] == zip_code]
    top_streets = crash_rows["on_street"].dropna().value_counts().head(3)
    return {
        "zip_code": zip_code,
        "borough": info["borough"],
        "community_district": info["community_district"] if isinstance(info["community_district"], str) else "",
        "units": int(building_rows["affordable_units"].sum()),
        "buildings": int(len(building_rows)),
        "crashes": int(len(crash_rows)),
        "deaths": int(crash_rows["fatalities"].sum()),
        "local_share": safe_divide(int((~crash_rows["on_highway"]).sum()), len(crash_rows)),
        "top_streets": [(street.title(), int(count)) for street, count in top_streets.items()],
    }
