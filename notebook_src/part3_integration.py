# %% [markdown]
# ---
# # 8. Integration *(M1)*
#
# ### 8.1 Why we do not join the raw rows
# The two tables have **no shared ID**: a building and a crash are different things. A join on a shared column such as ZIP code would pair **every building with every crash** in the same ZIP. The project description warns against exactly this ("don't join rows just because a column matches"). Here is how big that wrong join would be:

# %%
buildings_per_zip = housing["zip_code"].value_counts()
crashes_per_zip = crashes["zip_code"].value_counts()
naive_join_rows = int((buildings_per_zip * crashes_per_zip).dropna().sum())
print(f"Buildings: {len(housing):,} | Crashes: {len(crashes):,}")
print(f"A raw row-by-row join on ZIP would create {naive_join_rows:,} rows.")
print("Each crash would be counted once for every building in its ZIP, so all totals would be wrong.")

# %% [markdown]
# More than **700,000** meaningless rows from 9,551 buildings and 12,502 crashes. Each crash would be repeated once for every building in its ZIP, so any sum of crashes would be multiplied many times. The correct method is to **aggregate both datasets to the same level first, then join** (Lab 4's *Merge Queries* on common columns, after aggregation).
#
# ### 8.2 Choosing the level (granularity)
#
# | Possible level | In housing? | In crashes? | Verdict |
# |---|---|---|---|
# | Borough × year | 100% | 100% | Too coarse for analysis (only 5 places), but used for the website's borough views |
# | Community district | 100% | 26% | Rejected: 74% of crashes have no community district |
# | Census tract / neighbourhood (NTA) | 2010 codes | 2020 codes | Rejected: the code versions do not match |
# | **ZIP code × year** | 80% (all non-confidential) | 97% after imputation | **Chosen (Level A)** |
# | **Exact coordinates** | 80% | 81% | **Chosen (Level B)** for distance questions |
#
# **Why ZIP × year fits our questions:**
# - Our questions ask whether *areas* that receive new affordable homes are *areas* with dangerous streets. A ZIP code (about 200 in NYC) is small enough to show differences inside a borough and large enough to hold enough crashes for stable counts (see the median per ZIP in Section 9.4).
# - **Year** fits both datasets: housing is counted by completion year, the year residents move in, and crashes by crash year.
# - **Time window: 2022–2025**, the full years covered by both datasets. 2026 is left out of yearly comparisons because the crash data stops in March 2026.
#
# **Why we also need coordinates (Level B):** a ZIP code is about 4 km² on average. "In the same ZIP" can still mean 2 km away. For questions about the streets *right next to* new homes, we measure real distances.
#
# ### 8.3 Level A: aggregate both datasets to ZIP × year

# %%
WINDOW_YEARS = [2022, 2023, 2024, 2025]

housing_window = housing[housing["in_analysis_window"]]
housing_zip_year = (
    housing_window.dropna(subset=["zip_code"])
    .groupby(["zip_code", "completion_year"])
    .agg(buildings_completed=("building_id", "size"),
         affordable_units=("affordable_units", "sum"),
         deep_affordable_units=("deep_affordable_units", "sum"),
         family_units=("family_units", "sum"),
         new_construction_units=("affordable_units",
                                 lambda u: u[housing_window.loc[u.index, "construction_type"].eq("New Construction")].sum()),
         borough=("borough", lambda b: b.mode()[0]))
    .reset_index()
    .rename(columns={"completion_year": "year"})
)

crashes_window = crashes[crashes["in_analysis_window"]]
crash_zip_year = (
    crashes_window.dropna(subset=["zip_code"])
    .groupby(["zip_code", "year"])
    .agg(serious_crashes=("crash_id", "size"),
         fatal_crashes=("is_fatal", "sum"),
         deaths=("fatalities", "sum"),
         severe_injuries=("severe_injuries", "sum"),
         highway_crashes=("on_highway", "sum"),
         borough=("borough", lambda b: b.mode()[0]))
    .reset_index()
)
print("Housing ZIP-year rows:", len(housing_zip_year), "| key types:", housing_zip_year[["zip_code", "year"]].dtypes.to_dict())
print("Crash ZIP-year rows:  ", len(crash_zip_year), "| key types:", crash_zip_year[["zip_code", "year"]].dtypes.to_dict())

# %% [markdown]
# Before merging we check the **types of the join keys**. ZIP is already text in both tables (fixed in Sections 5.4 and 6.3). The **year** is `Int64` in housing (it came from a date column that has missing values) and `int32` in crashes. We convert both to the same type so the merge cannot fail silently. This is one of the type mismatches handled in Section 9.

# %%
housing_zip_year["year"] = housing_zip_year["year"].astype(int)
crash_zip_year["year"] = crash_zip_year["year"].astype(int)

zip_year_merged = housing_zip_year.merge(
    crash_zip_year, on=["zip_code", "year"], how="outer",
    suffixes=("_housing", "_crashes"), indicator=True, validate="one_to_one",
)
zip_year_merged["_merge"].value_counts()

# %% [markdown]
# We use an **outer** join so that no ZIP-year is lost:
# - **both**: the ZIP had new affordable buildings *and* serious crashes that year.
# - **right_only**: serious crashes but no new affordable building that year. These are very common and important: they are the "no new housing" comparison group.
# - **left_only**: new buildings but no serious crash that year (rare).
#
# `validate="one_to_one"` makes pandas check that each (ZIP, year) appears only once on each side, which proves the aggregation worked.
#
# ### 8.4 Level B: distances between buildings and crashes
# For each crash we find the distance to the nearest affordable building completed in 2022–2025. For each building we count the serious crashes within a radius.
#
# **Method:** a `BallTree` with the **haversine** distance (distance on the Earth's surface), the same structure we used for the ZIP imputation.
#
# **Choosing the radius:** we tested several radii (below). At 500 m, 67% of all crashes in the city count as "near new housing", so "near" no longer separates anything. **250 m** (about 2–3 city blocks, a 3-minute walk) splits the crashes into two comparable groups (42% near, 58% elsewhere) and still describes "the streets around your home". Section 10 repeats the key results at 150 m and 500 m to show that the conclusions do not depend on this choice.

# %%
NEAR_RADIUS_M = 250

new_buildings = (housing_window.dropna(subset=["latitude", "longitude"])
                 .sort_values("building_completion_date")
                 .drop_duplicates("building_id", keep="last")          # 1 building completed twice in the window
                 .reset_index(drop=True))
located_crashes = crashes_window.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)

building_tree = BallTree(to_radians(new_buildings), metric="haversine")
crash_tree = BallTree(to_radians(located_crashes), metric="haversine")

distance_rad, nearest_index = building_tree.query(to_radians(located_crashes), k=1)
located_crashes["distance_to_new_housing_m"] = (distance_rad[:, 0] * EARTH_RADIUS_M).round(0)
located_crashes["near_new_housing"] = located_crashes["distance_to_new_housing_m"] <= NEAR_RADIUS_M

radius_test = pd.DataFrame({"radius (m)": [100, 150, 200, 250, 300, 500]})
radius_test["share of crashes 'near'"] = [
    f"{(located_crashes['distance_to_new_housing_m'] <= r).mean():.0%}" for r in radius_test["radius (m)"]]
print(f"New affordable buildings with coordinates: {len(new_buildings):,}")
print(f"Serious crashes with coordinates (2022–2025): {len(located_crashes):,}")
radius_test

# %%
new_buildings["crashes_within_250m"] = crash_tree.query_radius(
    to_radians(new_buildings), r=NEAR_RADIUS_M / EARTH_RADIUS_M, count_only=True)
print("Serious crashes within 250 m of a new building (2022–2025):")
new_buildings["crashes_within_250m"].describe().round(1)

# %% [markdown]
# ### 8.5 Level C: borough × year (for the website)
# Every crash has a borough, and every building (including the confidential ones) has a borough, so this level uses **100%** of both datasets.

# %%
borough_year = (
    housing_window.groupby(["borough", "completion_year"])
    .agg(affordable_units=("affordable_units", "sum"), buildings_completed=("building_id", "size"))
    .reset_index().rename(columns={"completion_year": "year"})
    .astype({"year": int})
    .merge(crashes_window.groupby(["borough", "year"])
           .agg(serious_crashes=("crash_id", "size"), deaths=("fatalities", "sum")).reset_index(),
           on=["borough", "year"], how="outer", validate="one_to_one")
)
borough_year

# %% [markdown]
# ---
# # 9. Post-integration cleaning *(M1)*
# The join itself creates new problems, which the project description asks us to fix: **nulls created by the join, redundant columns, and type mismatches**.
#
# ### 9.1 Nulls created by the join
# **Problem:** in an outer join, a ZIP-year with crashes but no new building gets `NaN` in every housing column (and the other way round).

# %%
count_columns_housing = ["buildings_completed", "affordable_units", "deep_affordable_units", "family_units",
                         "new_construction_units"]
count_columns_crashes = ["serious_crashes", "fatal_crashes", "deaths", "severe_injuries", "highway_crashes"]
print("Missing values created by the join:")
zip_year_merged[count_columns_housing + count_columns_crashes].isna().sum()

# %% [markdown]
# **Decision:** fill these with **0**.
# **Why:** here `NaN` does not mean "unknown". It means **"no record"**: no building was completed, or no serious crash was recorded, in that ZIP that year. For a count, no record means zero. (This is different from the crash ZIP problem in Section 6.7, where the crash existed but its ZIP was unknown.)
#
# **A second, hidden gap:** a ZIP-year with *no building and no crash* does not appear at all. If ZIP 10280 had crashes in 2023 only, the table has no rows for its other years, and an average over years would use 1 year instead of 4. **Decision:** build the **complete grid** (every ZIP × every year) and fill the empty combinations with 0 too.

# %%
all_zips = sorted(set(zip_year_merged["zip_code"]))
complete_grid = pd.MultiIndex.from_product([all_zips, WINDOW_YEARS], names=["zip_code", "year"]).to_frame(index=False)
zip_year = complete_grid.merge(zip_year_merged, on=["zip_code", "year"], how="left")
print(f"Rows before completing the grid: {len(zip_year_merged)} | after: {len(zip_year)} "
      f"({len(all_zips)} ZIPs x {len(WINDOW_YEARS)} years)")
zip_year[count_columns_housing + count_columns_crashes] = zip_year[count_columns_housing + count_columns_crashes].fillna(0)

# %% [markdown]
# ### 9.2 Redundant and conflicting columns
# **Problem:** both tables had a `borough` column, so after the join there are two (`borough_housing`, `borough_crashes`), and many rows have only one of them. There is also the helper column `_merge`.
# **Decision:** keep **one** borough per ZIP, the borough where most of the ZIP's buildings and crashes are, and turn `_merge` into two readable flags before dropping it.

# %%
borough_votes = pd.concat([
    housing.dropna(subset=["zip_code"])[["zip_code", "borough"]],
    crashes.dropna(subset=["zip_code"])[["zip_code", "borough"]],
])
zip_borough = borough_votes.groupby("zip_code")["borough"].agg(lambda b: b.mode()[0])
conflicts = zip_year.dropna(subset=["borough_housing", "borough_crashes"])
conflicts = conflicts[conflicts["borough_housing"] != conflicts["borough_crashes"]]
print("ZIP-years where the two borough columns disagree:", len(conflicts),
      "| ZIPs:", sorted(conflicts["zip_code"].unique()))

zip_year["borough"] = zip_year["zip_code"].map(zip_borough)
zip_year["had_new_housing"] = zip_year["affordable_units"] > 0
zip_year["had_serious_crash"] = zip_year["serious_crashes"] > 0
zip_year = zip_year.drop(columns=["borough_housing", "borough_crashes", "_merge"])
print("Columns now:", list(zip_year.columns))

# %% [markdown]
# Because both sides were aggregated with the most common borough per ZIP, the two columns never disagree. They are still **redundant** (the same information twice) and **half empty** (each one only exists for its own side of the join), so one clean `borough` column replaces them. Border ZIPs such as 11385 get one consistent borough everywhere.
#
# ### 9.3 Type mismatches after the join
# We met three type mismatches during integration:
# 1. **ZIP code:** decimal (`11432.0`) in both raw files. Fixed before the join (Sections 5.4 and 6.3), otherwise no ZIP would match.
# 2. **Year:** `Int64` in housing and `int32` in crashes. Fixed just before the merge (Section 8.3).
# 3. **Counts after the join:** columns that contained missing values use pandas' special nullable type `Int64`, with a special `<NA>` value, while other counts are normal integers. Plotting and NumPy functions do not always accept `<NA>`, so mixing the two types causes errors later (for example on the website).
#
# **Decision for 3:** after filling the nulls, convert every count to the standard integer type `int64`.

# %%
print("Before:", zip_year[["affordable_units", "serious_crashes", "deaths"]].dtypes.to_dict())
zip_year[count_columns_housing + count_columns_crashes] = zip_year[count_columns_housing + count_columns_crashes].astype(int)
print("After: ", zip_year[["affordable_units", "serious_crashes", "deaths"]].dtypes.to_dict())

# %% [markdown]
# ### 9.4 One summary row per ZIP, plus a map position
# For most research questions we need the **4-year total per ZIP**. We also add:
# - `affordable_units_since_2014`: all affordable units completed in the ZIP since 2014 (the total *stock* of new affordable housing, not only 2022–2025).
# - A **map position** for each ZIP: the average coordinates of all buildings and crashes in that ZIP. This gives a good centre point without any extra map dataset.
# - `community_district`: the most common community district of the ZIP's buildings, to name the area (for example "BX 05").

# %%
zip_summary = zip_year.groupby(["zip_code", "borough"], as_index=False)[count_columns_housing + count_columns_crashes].sum()
stock = housing[housing["completion_year"].between(2014, 2025)].groupby("zip_code")["affordable_units"].sum()
zip_summary["affordable_units_since_2014"] = zip_summary["zip_code"].map(stock).fillna(0).astype(int)

zip_points = pd.concat([housing[["zip_code", "latitude", "longitude"]],
                        crashes[["zip_code", "latitude", "longitude"]]]).dropna()
zip_summary = zip_summary.merge(zip_points.groupby("zip_code")[["latitude", "longitude"]].mean().round(5),
                                on="zip_code", how="left")
zip_cd = housing.dropna(subset=["zip_code"]).groupby("zip_code")["community_board"].agg(lambda c: c.mode()[0])
zip_summary["community_district"] = zip_summary["zip_code"].map(zip_cd).str.replace("-", " ")

zip_summary["deaths_per_100_crashes"] = (100 * zip_summary["deaths"] / zip_summary["serious_crashes"].replace(0, np.nan)).round(1)
zip_summary["highway_share"] = (zip_summary["highway_crashes"] / zip_summary["serious_crashes"].replace(0, np.nan)).round(3)
print("ZIPs:", len(zip_summary), "| with new affordable units 2022–2025:", (zip_summary["affordable_units"] > 0).sum())
print("Median serious crashes per ZIP (2022–2025):", int(zip_summary["serious_crashes"].median()))
zip_summary.sort_values("affordable_units", ascending=False).head()

# %% [markdown]
# ### 9.5 Final checks on the integrated tables
# The most important check is **conservation**: the integrated table must contain exactly the same number of crashes and units as the cleaned datasets. Nothing may be lost or counted twice by the join.

# %%
assert not zip_year.duplicated(["zip_code", "year"]).any(), "duplicate ZIP-year"
assert zip_year[count_columns_housing + count_columns_crashes].notna().all().all(), "nulls left after the join"
assert zip_year["borough"].notna().all(), "ZIP without borough"
assert zip_year["serious_crashes"].sum() == crashes_window["zip_code"].notna().sum(), "crashes lost or duplicated"
assert zip_year["affordable_units"].sum() == housing_window.dropna(subset=["zip_code"])["affordable_units"].sum(), "units lost"
assert borough_year["serious_crashes"].sum() == len(crashes_window), "borough table lost crashes"
print("Integration checks passed:")
print(f"  ZIP x year table: {len(zip_year)} rows, {zip_year['serious_crashes'].sum():,} crashes, "
      f"{zip_year['affordable_units'].sum():,} affordable units")
print(f"  Crashes without a ZIP (kept only in borough results): {crashes_window['zip_code'].isna().sum():,}")
print(f"  Confidential units without a ZIP (kept only in borough results): "
      f"{housing_window[housing_window['zip_code'].isna()]['affordable_units'].sum():,}")
