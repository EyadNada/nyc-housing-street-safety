# %% [markdown]
# ---
# # 5. Pre-integration cleaning: housing *(M2)*
#
# Every step below has the same structure:
# **Problem** (what EDA showed) → **Decision** → **Why this choice, and why not the alternatives** → code → check.
#
# We never change the raw table. Each step works on a copy, so `housing_raw` stays available for the before/after comparison in Section 7.

# %%
housing = housing_raw.copy()
cleaning_log_housing = []   # one line per step, shown as a summary table at the end


def log_step(log, step, rows_affected, decision):
    """Record one cleaning step so we can show a summary table later."""
    log.append({"step": step, "rows affected": int(rows_affected), "decision": decision})

# %% [markdown]
# ### 5.1 Give columns clear names
# **Problem:** some API names are unclear (`_1_br_units`, `all_counted_units`, `postcode`).
# **Decision:** rename them so the code reads like plain English. Descriptive names are part of the clean-code grade.

# %%
housing = housing.rename(columns={
    "postcode": "zip_code",
    "reporting_construction_type": "construction_type",
    "extended_affordability_status": "extended_affordability_only",
    "all_counted_units": "affordable_units",
    "counted_rental_units": "rental_units",
    "counted_homeownership_units": "homeownership_units",
    "studio_units": "br0_units", "_1_br_units": "br1_units", "_2_br_units": "br2_units",
    "_3_br_units": "br3_units", "_4_br_units": "br4_units", "_5_br_units": "br5_units",
    "_6_br_units": "br6plus_units", "unknown_br_units": "br_unknown_units",
})
INCOME_BAND_COLUMNS = ["extremely_low_income_units", "very_low_income_units", "low_income_units",
                       "moderate_income_units", "middle_income_units", "other_income_units"]
BEDROOM_COLUMNS = ["br0_units", "br1_units", "br2_units", "br3_units", "br4_units", "br5_units",
                   "br6plus_units", "br_unknown_units"]
TENURE_COLUMNS = ["rental_units", "homeownership_units"]
UNIT_COLUMNS = INCOME_BAND_COLUMNS + BEDROOM_COLUMNS + TENURE_COLUMNS + ["affordable_units"]
log_step(cleaning_log_housing, "Rename columns", 0, "14 columns renamed to clear names")

# %% [markdown]
# ### 5.2 Hidden missing values → real missing values (with a flag)
# **Problem:** "CONFIDENTIAL", "----" and placeholder BINs (`3000000`) look like values, but they mean "unknown" (Section 3.5).
# **Decision:**
# 1. First save the information in a new column `is_confidential`, so nothing is lost.
# 2. Then turn the placeholders into real missing values (`NaN`). This is the `na_values` idea from Lab 2: pandas only treats `NaN` as missing.
#
# **Why:** if "----" stayed as text, `isna()` would report zero missing addresses, and any count of streets would include a fake street called "----".

# %%
housing["is_confidential"] = housing["project_name"].eq("CONFIDENTIAL")
housing.loc[housing["is_confidential"], "project_name"] = np.nan
for column in ["house_number", "street_name"]:
    housing[column] = housing[column].replace("----", np.nan)
placeholder_bin = housing["bin"].isin(PLACEHOLDER_BINS)
housing.loc[placeholder_bin, "bin"] = np.nan

log_step(cleaning_log_housing, "CONFIDENTIAL / ---- -> NaN + is_confidential flag",
         housing["is_confidential"].sum(), "kept rows; flag added; placeholders set to NaN")
log_step(cleaning_log_housing, "Placeholder BIN (x000000) -> NaN", placeholder_bin.sum(), "set to NaN")
print("Confidential buildings flagged:", housing["is_confidential"].sum())
print("Placeholder BINs removed:", placeholder_bin.sum())
print("Remaining '----' values:", (housing[["house_number", "street_name"]] == "----").sum().sum())

# %% [markdown]
# ### 5.3 Repair house numbers corrupted by Excel
# **Problem:** 31 Queens house numbers were turned into dates ("10-44" became "Oct-44"; "20-10" became "20-Oct").
# **Decision:** reverse Excel's change. A month name becomes its number again.
# **Why:** the address is shown in the website's hover text, and "Oct-44 Jackson Ave" looks broken. Repairing is better than deleting, because the rest of the row is correct.

# %%
MONTH_NUMBER = {month: number for number, month in enumerate(MONTHS.split("|"), start=1)}


def repair_excel_date(house_number):
    """Undo Excel's date conversion of hyphenated Queens house numbers."""
    if not isinstance(house_number, str):
        return house_number
    month_first = re.match(rf"^({MONTHS})-(\d+)$", house_number)        # "Oct-44"  -> "10-44"
    if month_first:
        return f"{MONTH_NUMBER[month_first.group(1)]}-{month_first.group(2)}"
    day_first = re.match(rf"^(\d+)-({MONTHS})$", house_number)          # "20-Oct"  -> "20-10"
    if day_first:
        return f"{day_first.group(1)}-{MONTH_NUMBER[day_first.group(2)]:02d}"
    return house_number


corrupted = housing["house_number"].str.match(excel_date_pattern, na=False)
before_repair = housing.loc[corrupted, "house_number"].head(5).tolist()
housing["house_number"] = housing["house_number"].apply(repair_excel_date)
print("Before:", before_repair)
print("After: ", housing.loc[corrupted, "house_number"].head(5).tolist())
log_step(cleaning_log_housing, "Repair Excel-date house numbers", corrupted.sum(), "month name -> number")

# %% [markdown]
# ### 5.4 Fix data types
# **Problem:** dates are text, ZIP codes are decimals (`11432.0`), IDs are decimals.
# **Decision:** dates → `datetime`. ZIP → 5-character text (`"11432"`), because a ZIP is a label (nominal), not a number to add. IDs and counts → whole numbers. We use pandas' `Int64` type, which allows missing values (normal `int` does not).
# **Why it matters for integration:** if one dataset stores ZIP as `11432.0` and the other as `"11432"`, a join on ZIP finds **no matches**. This is a type mismatch, and we fix it before integrating.

# %%
def to_zip_text(zip_series):
    """11432.0 -> '11432'; missing stays missing."""
    return zip_series.astype("Int64").astype("string")


for column in ["project_start_date", "project_completion_date", "building_completion_date"]:
    housing[column] = pd.to_datetime(housing[column], errors="coerce")
housing["zip_code"] = to_zip_text(housing["zip_code"])
for column in ["building_id", "bin", "bbl", "council_district", "total_units"]:
    housing[column] = housing[column].astype("Int64")
print(housing[["project_start_date", "building_completion_date", "zip_code", "building_id", "total_units"]].dtypes)
log_step(cleaning_log_housing, "Fix data types", len(housing), "dates, ZIP as text, Int64 IDs")

# %% [markdown]
# ### 5.5 Empty unit cells → 0
# **Problem:** income-band, bedroom and tenure columns are up to 99% empty.
# **Decision:** fill them with **0** (`fillna(0)`, Lab 2).
# **Why:** Section 3.6 proved that after filling with 0, the parts add up **exactly** to the total in 100% of rows, and HPD never stores a 0. Empty therefore means "0 units".
#
# **Alternatives we rejected:**
# - *Mean or median imputation:* it would invent units that do not exist (for example 12 "middle income" units in a building that has none), and the parts would no longer add up to the total.
# - *Dropping rows with empty cells:* almost every row has at least one empty band, so we would lose about 99% of the data (the Lab 2 lesson: `dropna()` is not a good option when there are many nulls).

# %%
empty_unit_cells = int(housing[UNIT_COLUMNS].isna().sum().sum())
empty_total = housing["affordable_units"].isna()
housing[UNIT_COLUMNS] = housing[UNIT_COLUMNS].fillna(0).astype("Int64")

band_sum_matches = (housing[INCOME_BAND_COLUMNS].sum(axis=1) == housing["affordable_units"]).mean()
print(f"Empty unit cells filled with 0: {empty_unit_cells:,}")
print(f"Rows where income bands add up to affordable_units after filling: {band_sum_matches:.1%}")
log_step(cleaning_log_housing, "Empty unit cells -> 0", empty_unit_cells, "fillna(0); proven by exact sums")
log_step(cleaning_log_housing, "Empty affordable_units -> 0", empty_total.sum(), "all bands are 0 too")

# %% [markdown]
# ### 5.6 Missing completion dates: keep them as missing
# **Problem:** 1,666 buildings have no completion date.
# **Decision:** keep `NaT` (missing date) and add `is_completed = False`.
# **Why:** the date is missing because **the building is not finished yet**, not because it was lost. Any value we filled in would claim it is finished.
# **Alternatives we rejected:**
# - *Forward fill (`ffill`, Lab 2):* ffill only makes sense for ordered data such as a time series. Neighbouring rows here are unrelated projects, so ffill would copy another project's date.
# - *Dropping the rows:* they are real buildings under construction. The website can still show them in "projects started".

# %%
housing["is_completed"] = housing["building_completion_date"].notna()
print("Buildings not yet completed:", (~housing["is_completed"]).sum())
log_step(cleaning_log_housing, "Missing completion date", (~housing["is_completed"]).sum(),
         "kept as NaT; is_completed flag")

# %% [markdown]
# ### 5.7 Missing locations (confidential buildings): keep the rows
# **Problem:** 1,958 buildings have no ZIP or coordinates (1,949 of them confidential).
# **Decision:** keep the rows. Use them for **borough-level** results, and leave them out only of ZIP-level and distance analyses.
# **Alternatives we rejected:**
# - *Guessing the ZIP from the community board:* one community district contains several ZIP codes, so the guess would often be wrong, and HPD hid these addresses on purpose to protect privacy.
# - *Dropping the rows:* we would lose 1,958 buildings from the borough totals.
#
# ### 5.8 Two sets of coordinates: keep one
# **Problem:** the dataset has two coordinate pairs: `latitude/longitude` (estimated from the street address) and `latitude_internal/longitude_internal` (centre of the tax lot).

# %%
both_pairs = housing.dropna(subset=["latitude", "latitude_internal"])
pair_distance_m = np.hypot((both_pairs["latitude"] - both_pairs["latitude_internal"]) * 111_000,
                           (both_pairs["longitude"] - both_pairs["longitude_internal"]) * 84_000)
print(f"Median distance between the two coordinate pairs: {pair_distance_m.median():.0f} m")
print("Rows with only the street-address pair:", (housing["latitude"].notna() & housing["latitude_internal"].isna()).sum())
print("Rows with only the tax-lot pair:", (housing["latitude"].isna() & housing["latitude_internal"].notna()).sum())

# %% [markdown]
# **Decision:** keep `latitude/longitude` and drop the internal pair.
# **Why:** the two points are only about 31 m apart (less than half a city block), so they carry the same information. The street-address pair is filled in 86 more rows. Keeping both would be **redundant**.
#
# We also drop the 2010 census tract and 2010 neighbourhood codes. The crash data uses the **2020** versions of these codes, so they cannot be matched (for example `BK82` vs `BK0502`).

# %%
housing = housing.drop(columns=["latitude_internal", "longitude_internal", "census_tract",
                                "neighborhood_tabulation_area"])
log_step(cleaning_log_housing, "Drop redundant / incompatible columns", 0,
         "tax-lot coordinates, 2010 tract and NTA codes")

# %% [markdown]
# ### 5.9 Consistency checks (multivariate outliers)
# A **multivariate outlier** is a row whose values are each normal alone, but impossible **together** (Lab 2). We check four rules.

# %%
consistency_checks = pd.DataFrame({
    "rule": ["affordable units <= total units",
             "building completed on or after project start",
             "project completed on or after project start",
             "'extended affordability only' projects are preservation (data dictionary)",
             "coordinates inside New York City"],
    "rows breaking the rule": [
        int((housing["affordable_units"] > housing["total_units"]).sum()),
        int((housing["building_completion_date"] < housing["project_start_date"]).sum()),
        int((housing["project_completion_date"] < housing["project_start_date"]).sum()),
        int((housing["extended_affordability_only"].eq("Yes") & housing["construction_type"].eq("New Construction")).sum()),
        int((~housing["latitude"].between(40.47, 40.92) | ~housing["longitude"].between(-74.26, -73.69))
            [housing["latitude"].notna()].sum()),
    ],
})
consistency_checks

# %% [markdown]
# **Decisions:**
# - **20 buildings completed before the project "started".** This is **not an error**: HPD's data dictionary says the start date can be the date of the *notice to market* the affordable units, and that notice can come after construction. We keep the rows and flag them (`start_after_completion`). We never use these dates to compute a duration.
# - **2 projects break the data-dictionary rule** (extended affordability, but labelled new construction). We cannot know which of the two fields is wrong, so we keep and flag them (`contradicts_dictionary`). Two rows out of 9,551 cannot change any result.
# - All other rules pass.

# %%
housing["start_after_completion"] = housing["building_completion_date"] < housing["project_start_date"]
housing["contradicts_dictionary"] = (housing["extended_affordability_only"].eq("Yes")
                                     & housing["construction_type"].eq("New Construction"))
log_step(cleaning_log_housing, "Completion before start date", housing["start_after_completion"].sum(),
         "kept + flagged (start can be marketing date)")
log_step(cleaning_log_housing, "Contradicts data dictionary", housing["contradicts_dictionary"].sum(), "kept + flagged")

# %% [markdown]
# ### 5.10 Outliers in building size: detect, explain, keep
# **Method choice (Lab 2):** the Z-score method assumes a roughly normal distribution. Our unit counts are very skewed (skewness 3.7), so we use the **IQR method** for detection.

# %%
q1_units, q3_units = housing["affordable_units"].astype(float).quantile([0.25, 0.75])
iqr_units = q3_units - q1_units
upper_fence = q3_units + 1.5 * iqr_units
housing["is_large_building"] = housing["affordable_units"] > upper_fence
print(f"Q1 = {q1_units:.0f}, Q3 = {q3_units:.0f}, IQR = {iqr_units:.0f}, upper fence = Q3 + 1.5*IQR = {upper_fence:.0f} units")
print(f"Buildings above the fence: {housing['is_large_building'].sum():,} ({housing['is_large_building'].mean():.0%})")
housing.nlargest(5, "total_units")[["project_name", "borough", "total_units", "affordable_units"]]

# %% [markdown]
# **Decision: keep every building and add an `is_large_building` flag.**
# **Why:** the IQR rule flags 1,249 buildings (13%), and they are **real** large buildings, such as 25 Water Street (1,320 apartments, the conversion of a former office tower) and 5 Pointz in Long Island City. Lab 2 says an extreme point is not always an error ("true outlier observation"). Removing them would delete the most important housing projects in the city.
# **How we handle the skew instead:** medians, log scales and rank (Spearman) correlation.
# **Alternative rejected:** *capping* the values at the fence (winsorizing) would make the totals per ZIP wrong.

# %%
log_step(cleaning_log_housing, "Large buildings (IQR)", housing["is_large_building"].sum(),
         "real values: kept + flagged")

# %% [markdown]
# ### 5.11 A shared community-district code
# **Problem:** housing writes community boards as `"BK-05"`, and the crash data writes them as `305` (borough digit + district number). The same place has two spellings.
# **Decision:** create `borough_code` and `community_district` in the crash-data format (`305`) for both datasets.

# %%
BOROUGH_CODE = {"Manhattan": 1, "Bronx": 2, "Brooklyn": 3, "Queens": 4, "Staten Island": 5}
housing["borough_code"] = housing["borough"].map(BOROUGH_CODE).astype("Int64")
housing["community_district"] = (housing["borough_code"] * 100
                                 + housing["community_board"].str[-2:].astype(int)).astype("Int64")
housing[["borough", "community_board", "community_district"]].drop_duplicates().head(4)

# %% [markdown]
# ### 5.12 New columns for the analysis (feature engineering)
# Like the `quote_length` column in Lab 1, we create columns that answer our questions directly:
#
# | New column | Meaning |
# |---|---|
# | `completion_year` | year the building was completed (when residents can move in) |
# | `deep_affordable_units` | extremely low + very low income units (households earning up to 50% of area median income) |
# | `family_units` | apartments with 2 or more bedrooms |
# | `family_share`, `deep_affordable_share` | the above as a share of the building's affordable units |
# | `in_analysis_window` | completed in 2022–2025, the full years covered by both datasets |

# %%
housing["completion_year"] = housing["building_completion_date"].dt.year.astype("Int64")
housing["start_year"] = housing["project_start_date"].dt.year.astype("Int64")
housing["deep_affordable_units"] = housing["extremely_low_income_units"] + housing["very_low_income_units"]
housing["family_units"] = housing[["br2_units", "br3_units", "br4_units", "br5_units", "br6plus_units"]].sum(axis=1)
units_float = housing["affordable_units"].astype(float).replace(0, np.nan)          # avoid division by zero
housing["family_share"] = (housing["family_units"].astype(float) / units_float).round(3)
housing["deep_affordable_share"] = (housing["deep_affordable_units"].astype(float) / units_float).round(3)
housing["in_analysis_window"] = housing["completion_year"].between(2022, 2025).fillna(False).astype(bool)
print("Buildings completed in the 2022–2025 window:", housing["in_analysis_window"].sum())
print("Affordable units completed in the window:", f"{housing.loc[housing['in_analysis_window'], 'affordable_units'].sum():,}")

# %% [markdown]
# ### 5.13 Tidy data: income bands from wide to long (Lecture 2)
# **Problem:** the six income-band columns break the tidy-data rule "column headers are values, not variable names". The band name ("very low income") is a **value** of a variable *income band*.
# **Decision:** `melt` them into a long table with one row per building and income band. This makes "units by income band" a simple `groupby`, and the website uses it for its income-band filter.

# %%
INCOME_BAND_LABELS = {
    "extremely_low_income_units": "1. Extremely low (0–30% AMI)",
    "very_low_income_units": "2. Very low (31–50% AMI)",
    "low_income_units": "3. Low (51–80% AMI)",
    "moderate_income_units": "4. Moderate (81–120% AMI)",
    "middle_income_units": "5. Middle (121–165% AMI)",
    "other_income_units": "6. Other (superintendent units)",
}
housing_income_long = (
    housing.melt(id_vars=["project_id", "building_id", "borough", "zip_code", "completion_year", "in_analysis_window"],
                 value_vars=INCOME_BAND_COLUMNS, var_name="income_band", value_name="units")
    .assign(income_band=lambda d: d["income_band"].map(INCOME_BAND_LABELS))
    .query("units > 0")
    .reset_index(drop=True)
)
print("Long table:", housing_income_long.shape)
housing_income_long.head()

# %% [markdown]
# ### Housing cleaning summary

# %%
pd.DataFrame(cleaning_log_housing)

# %% [markdown]
# ---
# # 6. Pre-integration cleaning: crashes *(M3)*

# %%
crashes = crashes_raw.copy()
cleaning_log_crashes = []

crashes = crashes.rename(columns={
    "open_data_crash_id": "crash_id",
    "crash_borough": "borough",
    "crash_police_precinct": "precinct",
    "zipcode": "zip_code",
    "total_non_severe_injuries": "non_severe_injuries",
    "total_severe_injuries": "severe_injuries",
    "total_fatalities": "fatalities",
    "similar_fatalities_severe": "similar_severe_3y",
    "similar_fatalities_all": "similar_all_3y",
    "census_tract_2020_": "census_tract_2020",
    "neighborhood_tabulation_area_nta_2020_": "nta_2020",
})
log_step(cleaning_log_crashes, "Rename columns", 0, "11 columns renamed to clear names")

# %% [markdown]
# ### 6.1 Remove the 444 broken records
# **Problem:** 444 rows have no crash ID, date, time or injuries, only location codes (Section 4.3).
# **Decision:** drop them. We detect them with the rule "no crash ID", because `isna().all()` misses them.
# **Why:** a crash without a date or an outcome cannot be counted in any year, borough or severity group. There is nothing to impute from: no other column says when it happened or what happened. Lab 2's rule applies here: dropping is right when the row carries no usable information.

# %%
broken = crashes["crash_id"].isna()
crashes = crashes[~broken].copy()
print("Broken records removed:", broken.sum(), "| crashes left:", len(crashes))
log_step(cleaning_log_crashes, "Drop records with no crash data", broken.sum(), "dropped (nothing to impute)")

# %% [markdown]
# ### 6.2 One crash ID used twice
# **Problem:** crash `4597666` appears on 13 Jan 2023 **and** 13 Jan 2026, with the same time (21:01), street and precinct.
# **Decision:** keep the **2023** record and drop the 2026 copy.
# **Why:** a primary key must be unique, and everything except the year is identical, so this is one crash entered twice with a wrong year. We keep the earlier record because it is the original entry. The 2026 copy reports one death; it may be a later update, but we cannot verify that. Either choice changes 1 row out of 12,503 (0.008%).

# %%
duplicate_mask = crashes["crash_id"].duplicated(keep=False) & pd.to_datetime(crashes["crash_date"]).dt.year.eq(2026)
crashes = crashes[~duplicate_mask].copy()
print("Duplicate removed:", duplicate_mask.sum(), "| crash IDs now unique:", crashes["crash_id"].is_unique)
log_step(cleaning_log_crashes, "Duplicated crash ID", duplicate_mask.sum(), "kept original 2023 entry")

# %% [markdown]
# ### 6.3 Fix data types and standardize the time
# **Decision:** dates → `datetime`; times → one format `HH:MM` ("6:56" → "06:56"); precinct, IDs and counts → whole numbers; ZIP → 5-character text (same format as housing).

# %%
crashes["crash_date"] = pd.to_datetime(crashes["crash_date"])
crashes["crash_time"] = pd.to_datetime(crashes["crash_time"], format="%H:%M").dt.strftime("%H:%M")
for column in ["crash_id", "precinct", "severe_injuries", "fatalities", "non_severe_injuries",
               "similar_severe_3y", "similar_all_3y", "community_board", "council_district", "bin", "bbl"]:
    crashes[column] = crashes[column].astype("Int64")
print("Time formats left:", crashes["crash_time"].str.len().value_counts().to_dict(), "(all 5 characters)")
log_step(cleaning_log_crashes, "Fix data types + time format", len(crashes), "HH:MM, Int64, datetime")

# %% [markdown]
# ### 6.4 Placeholders: ZIP 10000 and the midnight default
# **ZIP `10000`:** not a real ZIP code → set to missing. Section 6.7 fills it again from the coordinates.
#
# **Midnight (`00:00`):** 204 crashes, twice the busiest real hour, so it is most likely the default for an unknown time.
# **Decision:** keep these crashes (their date, place and injuries are real) but add a flag `time_unknown`. Only the time-of-day analysis (RQ5) leaves them out.
# **Alternatives rejected:** *dropping* them would lose 204 real crashes from every other analysis. *Imputing a time* has no basis, because no other column tells us the hour.

# %%
fake_zip = crashes["zip_code"].eq(10000)
crashes.loc[fake_zip, "zip_code"] = np.nan
crashes["zip_code"] = to_zip_text(crashes["zip_code"])
crashes["time_unknown"] = crashes["crash_time"].eq("00:00")
print("ZIP 10000 set to missing:", fake_zip.sum(), "| midnight crashes flagged:", crashes["time_unknown"].sum())
log_step(cleaning_log_crashes, "ZIP 10000 -> NaN", fake_zip.sum(), "placeholder removed (refilled in 6.7)")
log_step(cleaning_log_crashes, "Time 00:00 -> time_unknown flag", crashes["time_unknown"].sum(),
         "kept; excluded only from hour analysis")

# %% [markdown]
# ### 6.5 Missing borough: precinct 116 is in Queens
# **Problem:** 46 crashes have no borough, and all are in police precinct 116.
# **Decision:** fill in **Queens**, using two independent pieces of evidence:
# 1. NYPD numbers precincts by borough, and the 100s are Queens (precinct 116 opened recently in south-east Queens).
# 2. The coordinates of these crashes all lie in south-east Queens (checked below).
#
# **Why not leave them missing:** the borough is a filter on our website. With an empty borough, these crashes would disappear from every borough view.

# %%
missing_borough = crashes["borough"].isna()
print("Precincts of crashes without a borough:", crashes.loc[missing_borough, "precinct"].value_counts().to_dict())
print(crashes.loc[missing_borough, ["latitude", "longitude"]].agg(["min", "max"]).round(3))
precinct_to_borough = crashes.dropna(subset=["borough"]).groupby("precinct")["borough"].agg(lambda b: b.mode()[0])
inconsistent = (crashes["precinct"].map(precinct_to_borough) != crashes["borough"]) & crashes["borough"].notna()
print("Crashes whose precinct and borough disagree:", int(inconsistent.sum()))
crashes.loc[missing_borough & crashes["precinct"].eq(116), "borough"] = "Queens"
log_step(cleaning_log_crashes, "Missing borough (precinct 116)", missing_borough.sum(), "filled with Queens")

# %% [markdown]
# Latitude 40.64–40.68 and longitude −73.79 to −73.73 is exactly south-east Queens (Rosedale, Laurelton, Springfield Gardens). Every other crash's precinct agrees with its borough, so precinct is a reliable source.
#
# ### 6.6 Does the reported ZIP match the borough? (multivariate check)

# %%
zip_to_borough = housing.dropna(subset=["zip_code"]).groupby("zip_code")["borough"].agg(lambda b: b.mode()[0])
reported = crashes.dropna(subset=["zip_code"])
zip_borough = reported["zip_code"].map(zip_to_borough)
mismatch = reported[zip_borough.notna() & (zip_borough != reported["borough"])]
print("Crashes whose reported ZIP belongs to another borough:", len(mismatch))
mismatch[["crash_id", "zip_code", "borough", "on_street"]]

# %% [markdown]
# Only 4 mismatches, and all are ZIPs **11237** (Bushwick) and **11385** (Ridgewood). These two ZIP codes cross the Brooklyn–Queens border, so both boroughs are correct. **Decision:** keep them. This check also shows that the reported ZIPs are reliable.
#
# ### 6.7 Fill missing ZIP codes from the coordinates (Hot Deck imputation)
# **Problem:** 42% of crashes have no ZIP, and the share depends on the year (84% missing in 2022, 20% in 2025). Dropping them would create the fake trend explained in Section 4.7.
#
# **Decision: nearest-neighbour Hot Deck imputation.** Lab 2 names Hot Deck imputation: a missing value is copied from a similar *donor* row. For a crash without a ZIP but **with coordinates**, the most similar donor is the **nearest crash that has a known ZIP**, in the **same borough**.
#
# **Alternatives we rejected:**
# - *Mode (most common ZIP):* every missing crash in a borough would get the same ZIP. With about 40 ZIPs per borough, that is wrong almost every time.
# - *Mean:* a ZIP is nominal, so the average of 10451 and 11201 means nothing.
# - *Dropping:* creates the fake trend.
#
# **Before using the method, we test it.** We hide the ZIP of 20% of the crashes whose ZIP we *do* know, predict it, and count how often we are right. We also try several numbers of neighbours *k*.

# %%
EARTH_RADIUS_M = 6_371_000


def to_radians(df):
    """Latitude/longitude in degrees -> radians, as the haversine distance needs."""
    return np.radians(df[["latitude", "longitude"]].to_numpy())


def zip_imputation_accuracy(donors, k, test_share=0.2, seed=42):
    """Hide the ZIP of test_share of donors, predict it from the k nearest crashes (same borough)."""
    rng = np.random.default_rng(seed)
    correct, tested = 0, 0
    for _, borough_rows in donors.groupby("borough"):
        order = rng.permutation(len(borough_rows))
        cut = int(len(borough_rows) * (1 - test_share))
        train, test = borough_rows.iloc[order[:cut]], borough_rows.iloc[order[cut:]]
        model = KNeighborsClassifier(n_neighbors=k, metric="haversine", algorithm="ball_tree", weights="distance")
        model.fit(to_radians(train), train["zip_code"])
        correct += (model.predict(to_radians(test)) == test["zip_code"].to_numpy()).sum()
        tested += len(test)
    return correct / tested


has_zip = crashes["zip_code"].notna()
has_coordinates = crashes["latitude"].notna()
zip_donors = crashes[has_zip & has_coordinates]
validation = pd.DataFrame({"k (neighbours)": [1, 3, 5, 9]})
validation["accuracy on hidden ZIPs"] = [zip_imputation_accuracy(zip_donors, k) for k in validation["k (neighbours)"]]
validation["accuracy on hidden ZIPs"] = validation["accuracy on hidden ZIPs"].map("{:.1%}".format)
validation

# %% [markdown]
# **Result:** with **k = 1** (copy the ZIP of the single nearest crash) the method finds the correct ZIP for about **92%** of the hidden crashes, slightly better than larger *k*. The remaining errors are mostly crashes on a ZIP border, where the neighbouring ZIP is still very close. We use k = 1. It is also the easiest version to explain: *"we copy the ZIP of the nearest crash."*

# %%
crashes["zip_source"] = np.where(has_zip, "reported", "missing")
needs_zip = ~has_zip & has_coordinates
for borough, donors_in_borough in zip_donors.groupby("borough"):
    targets = crashes[needs_zip & crashes["borough"].eq(borough)]
    if targets.empty:
        continue
    model = KNeighborsClassifier(n_neighbors=1, metric="haversine", algorithm="ball_tree")
    model.fit(to_radians(donors_in_borough), donors_in_borough["zip_code"])
    crashes.loc[targets.index, "zip_code"] = model.predict(to_radians(targets))
    crashes.loc[targets.index, "zip_source"] = "imputed (coordinates)"

crashes["year"] = crashes["crash_date"].dt.year
print("ZIP codes filled from coordinates:", needs_zip.sum(),
      "| still missing (no coordinates either):", (crashes["zip_source"] == "missing").sum())
pd.crosstab(crashes["year"], crashes["zip_source"], normalize="index").mul(100).round(1)

# %% [markdown]
# **After this first step, the ZIP is known for 88–96% of crashes in every year**, instead of 16–80%. The fake trend is gone. The column `zip_source` keeps the origin of every ZIP, so a reader can always tell real values from imputed ones.
#
# 1,130 crashes (9%) still have **neither a ZIP nor coordinates**, and 318 of them are **fatal** (Section 4.7). They get a second chance in Section 6.9, after the street names are cleaned.

# %%
log_step(cleaning_log_crashes, "Missing ZIP -> Hot Deck from coordinates", needs_zip.sum(),
         "copied from nearest crash in same borough (92% accurate in test)")

# %% [markdown]
# ### 6.8 Standardize street names (the "match entire cell contents" lesson from Lab 3)
# **Problem:** the same street is written in different ways ("3 AVE" / "3 AVENUE", "E 149 ST" / "EAST 149 STREET", lower and upper case).
# **Decision:** upper case, single spaces, and abbreviations replaced **only as whole words**.
#
# **Why whole words matter:** in Lab 3 we used *Match entire cell contents* when replacing "F" with "Female", because otherwise every "F" inside other words would change too. The same trap exists here:

# %%
print("Naive replace:    ", "3 AVENUE".replace("AVE", "AVENUE"), "  <- broken")
print("Whole-word regex: ", re.sub(r"\bAVE\b", "AVENUE", "3 AVENUE"), "  <- correct")

# %%
STREET_WORDS = [
    (r"^ST\b", "SAINT"),            # "ST NICHOLAS AVE" -> "SAINT NICHOLAS ..."  (ST at the start = Saint)
    (r"\bST$", "STREET"),           # "EAST 149 ST"     -> "... STREET"          (ST at the end = Street)
    (r"^E\b", "EAST"), (r"^W\b", "WEST"), (r"^N\b", "NORTH"), (r"^S\b", "SOUTH"),
    (r"\bAVE?\b", "AVENUE"), (r"\bBLVD\b", "BOULEVARD"), (r"\bPKWY\b", "PARKWAY"),
    (r"\bEXPY\b", "EXPRESSWAY"), (r"\bRD\b", "ROAD"), (r"\bPL\b", "PLACE"), (r"\bDR\b", "DRIVE"),
]


def standardize_street(name):
    """Upper case, single spaces, and whole-word abbreviation replacement."""
    if not isinstance(name, str):
        return name
    name = re.sub(r"\s+", " ", name.upper().strip())
    for pattern, full_word in STREET_WORDS:
        name = re.sub(pattern, full_word, name)
    return name


streets_before = crashes["on_street"].nunique()
for column in ["on_street", "cross_street", "address"]:
    crashes[column] = crashes[column].apply(standardize_street)
print(f"Different street names: {streets_before:,} before -> {crashes['on_street'].nunique():,} after")
log_step(cleaning_log_crashes, "Standardize street names", crashes["on_street"].notna().sum(),
         "upper case, whole-word abbreviations")

# %% [markdown]
# The number of different street names dropped from 2,819 to 2,009. About 800 "different" streets were the same street written in different ways, which would have split their crash counts.
#
# ### 6.9 Second Hot Deck step: ZIP from the street name and precinct
# **Problem:** 1,130 crashes have no ZIP and no coordinates, and 318 of them are fatal. Fatal crashes after 2022 never have coordinates (Section 4.7), so leaving these ZIPs empty would remove about a third of all deaths from every ZIP-level result, and every death rate per ZIP would be too low.
#
# **Decision:** a second Hot Deck step with a different donor rule. Every crash has a **police precinct**, and most have a **street name**. A donor is a crash with a known ZIP on the **same street, in the same precinct** (and at the same cross street when we know it). We copy the most common ZIP among those donors.
#
# We test it the same way as before: hide 20% of the **reported** ZIPs and predict them.

# %%
def street_lookup_tables(donors):
    """Most common ZIP per (precinct, street, cross street) and per (precinct, street)."""
    by_crossing = (donors.dropna(subset=["cross_street"])
                   .groupby(["precinct", "on_street", "cross_street"])["zip_code"].agg(lambda z: z.mode()[0]))
    by_street = donors.groupby(["precinct", "on_street"])["zip_code"].agg(lambda z: z.mode()[0])
    return by_crossing, by_street


def predict_zip_from_street(rows, by_crossing, by_street):
    """Use the exact crossing when possible, otherwise the street inside the precinct."""
    crossing_keys = pd.MultiIndex.from_frame(rows[["precinct", "on_street", "cross_street"]])
    street_keys = pd.MultiIndex.from_frame(rows[["precinct", "on_street"]])
    from_crossing = pd.Series(by_crossing.reindex(crossing_keys).to_numpy(), index=rows.index)
    from_street = pd.Series(by_street.reindex(street_keys).to_numpy(), index=rows.index)
    return from_crossing.fillna(from_street)


street_donors = crashes[crashes["zip_code"].notna() & crashes["on_street"].notna()]
reported_donors = street_donors[street_donors["zip_source"] == "reported"]
test_rows = reported_donors.sample(frac=0.2, random_state=42)
train_rows = street_donors.drop(test_rows.index)
predicted = predict_zip_from_street(test_rows, *street_lookup_tables(train_rows))
found = predicted.notna()
print(f"Test: a donor was found for {found.mean():.0%} of hidden ZIPs; "
      f"the copied ZIP was correct for {(predicted[found] == test_rows.loc[found, 'zip_code']).mean():.0%} of them")

# %%
still_missing = crashes["zip_code"].isna() & crashes["on_street"].notna()
street_prediction = predict_zip_from_street(crashes[still_missing], *street_lookup_tables(street_donors)).dropna()
crashes.loc[street_prediction.index, "zip_code"] = street_prediction
crashes.loc[street_prediction.index, "zip_source"] = "imputed (street)"
print("ZIP codes filled from street + precinct:", len(street_prediction),
      "| of them fatal:", int(crashes.loc[street_prediction.index, "fatalities"].gt(0).sum()),
      "| still missing:", (crashes["zip_source"] == "missing").sum())

crashes["is_fatal_crash"] = crashes["fatalities"] > 0
zip_known = (crashes.assign(zip_known=crashes["zip_code"].notna())
             .pivot_table(index="year", columns="is_fatal_crash", values="zip_known", aggfunc="mean")
             .mul(100).round(1).rename(columns={False: "severe-injury crashes: ZIP known (%)",
                                                True: "fatal crashes: ZIP known (%)"}))
crashes = crashes.drop(columns="is_fatal_crash")
zip_known

# %% [markdown]
# **Result:** a donor is found for 81% of hidden ZIPs, and the copied ZIP is right **73%** of the time. Errors usually land in the neighbouring ZIP on the same street. This is less accurate than the coordinate method (92%), so:
# - We use it **only** for crashes that have no coordinates, as a second step.
# - It gets its own label, `zip_source = "imputed (street)"`, so any analysis can leave these ZIPs out.
# - In RQ10, the question about deaths, we show the result **with and without** street-imputed ZIPs.
#
# **Why accept 73% accuracy:** the alternative is not "no error", it is a **systematic** error. Without this step, a third of the fatal crashes from 2023–2025 would be missing from every ZIP. With it, more than 92% of fatal crashes have a ZIP in every year. A 73%-accurate guess along the same street is a smaller and more honest error than silently dropping a third of the deaths. RQ10 shows how much this matters: without this step, the death rate in ZIPs without new housing looks almost half as high as it really is.

# %%
log_step(cleaning_log_crashes, "Missing ZIP (no coordinates) -> Hot Deck from street + precinct",
         len(street_prediction), "copied from crashes on the same street in the same precinct (73% accurate)")

# %% [markdown]
# ### 6.10 Crash outcomes: domain rules instead of IQR
# **Problem:** IQR = 0 for severe injuries (Section 4.6), so the IQR rule from Lab 2 would mark every crash with 0 or 2+ severe injuries as an outlier.
# **Decision:** use rules that come from what the data **means**:

# %%
outcome_rules = pd.DataFrame({
    "rule": ["no negative counts",
             "every crash has a severe injury or a death (SIRTA definition)",
             "crashes with 5+ people seriously hurt (checked by hand, real multi-victim crashes)"],
    "rows": [int((crashes[["severe_injuries", "fatalities", "non_severe_injuries"]] < 0).any(axis=1).sum()),
             int(((crashes["severe_injuries"] + crashes["fatalities"]) == 0).sum()),
             int(((crashes["severe_injuries"] + crashes["fatalities"]) >= 5).sum())],
})
outcome_rules

# %% [markdown]
# No row breaks the first two rules. The 16 crashes with 5 or more people seriously hurt are rare but **real** (for example a vehicle hitting a crowd or a bus crash). **Decision:** keep them all.
#
# ### 6.11 "Similar crashes in the last 3 years": unknown is not zero
# **Problem:** `similar_severe_3y` (how many similar serious crashes happened at the same place in the 3 previous years) is missing for 1,393 crashes.
# **Decision:** keep it **missing**. RQ8 uses only crashes where the value is known.
# **Why not `fillna(0)`:** 0 is a real answer ("no similar crash here before"). Filling unknown values with 0 would claim 1,393 locations had no earlier crashes, and RQ8 would underestimate repeat-danger locations.

# %% [markdown]
# ### 6.12 New columns for the analysis

# %%
crashes["month"] = crashes["crash_date"].dt.to_period("M").dt.to_timestamp()
crashes["weekday"] = crashes["crash_date"].dt.day_name()
crashes["hour"] = crashes["crash_time"].str[:2].astype(int)
crashes["people_seriously_hurt"] = crashes["severe_injuries"] + crashes["fatalities"]
crashes["is_fatal"] = crashes["fatalities"] > 0
crashes["on_highway"] = crashes["highway_reference_marker"].notna()      # DOT gives highway crashes a reference marker
crashes["at_repeat_location"] = (crashes["similar_severe_3y"] > 0).astype("boolean")  # stays <NA> when unknown
crashes["in_analysis_window"] = crashes["year"].between(2022, 2025)        # 2026 is only January–March
crashes["community_district"] = crashes["community_board"]
print("Crashes in the 2022–2025 window:", crashes["in_analysis_window"].sum())
print("Fatal crashes:", crashes["is_fatal"].sum(), "| on highways:", crashes["on_highway"].sum())

# %% [markdown]
# ### 6.13 Drop columns we do not need
# **Decision:** drop `bin`, `bbl`, `census_tract_2020`, `nta_2020` and `council_district`.
# **Why:** they are 72–80% empty, and the 2020 census and neighbourhood codes cannot be matched with the 2010 codes in the housing data. After imputation, ZIP is known for 97% of crashes, so ZIP is the better shared geography. We keep `community_district` (74% empty) only for reference.

# %%
crashes = crashes.drop(columns=["bin", "bbl", "census_tract_2020", "nta_2020", "council_district", "community_board"])
log_step(cleaning_log_crashes, "Drop mostly-empty / incompatible columns", 0,
         "5 columns dropped; community board kept as community_district")
pd.DataFrame(cleaning_log_crashes)

# %% [markdown]
# ---
# # 7. Checking that the cleaning worked *(M6)*
#
# The project asks for **charts that prove the cleaning worked**. We show three before/after comparisons and then run automatic checks.
#
# ### 7.1 Missing values before and after

# %%
def missing_share(df, columns):
    return df[columns].isna().mean().mul(100)


housing_check = pd.DataFrame({
    "before": missing_share(housing_raw.rename(columns={"postcode": "zip_code", "all_counted_units": "affordable_units",
                                                        "very_low_income_units": "very_low_income_units"}),
                            ["very_low_income_units", "affordable_units", "zip_code"]),
    "after": missing_share(housing, ["very_low_income_units", "affordable_units", "zip_code"]),
}).rename(index={"very_low_income_units": "Housing: very-low-income units", "affordable_units": "Housing: affordable units",
                 "zip_code": "Housing: ZIP code"})
crash_check = pd.DataFrame({
    "before": missing_share(crashes_raw.rename(columns={"crash_borough": "borough", "zipcode": "zip_code",
                                                        "open_data_crash_id": "crash_id"}),
                            ["crash_id", "borough", "zip_code"]),
    "after": missing_share(crashes, ["crash_id", "borough", "zip_code"]),
}).rename(index={"crash_id": "Crashes: crash ID", "borough": "Crashes: borough", "zip_code": "Crashes: ZIP code"})
missing_before_after = pd.concat([housing_check, crash_check])

fig, ax = plt.subplots(figsize=(9, 4.5))
positions = np.arange(len(missing_before_after))
ax.barh(positions - 0.2, missing_before_after["before"], height=0.38, color=GRAY, label="Before cleaning")
ax.barh(positions + 0.2, missing_before_after["after"], height=0.38, color=BLUE, label="After cleaning")
for y, value in zip(positions, missing_before_after["after"]):
    ax.text(value + 0.8, y + 0.2, f"{value:.1f}%", va="center", fontsize=9, color=INK_SOFT)
ax.set_yticks(positions, missing_before_after.index)
ax.invert_yaxis()
ax.grid(axis="x", visible=True)
ax.xaxis.set_major_formatter(mticker.PercentFormatter())
ax.legend(loc="lower right")
finish_chart(ax, "Empty cells before and after cleaning", "Empty cells (% of rows)")
plt.show()

# %% [markdown]
# **Reading the chart:** the very-low-income column goes from 64% empty to 0% (empty meant zero). Crash IDs and boroughs are now complete. Crash ZIPs drop from 42% to 3% empty. Housing ZIPs stay about 20% empty **on purpose**: they are the confidential homes, which we keep for borough-level results.
#
# ### 7.2 The key check: ZIP coverage per year

# %%
coverage_before = crashes_raw.assign(year=pd.to_datetime(crashes_raw["crash_date"]).dt.year).dropna(subset=["year"])
coverage_before = coverage_before.groupby("year")["zipcode"].apply(lambda z: (z.notna() & (z != 10000)).mean() * 100)
coverage_after = crashes.groupby("year")["zip_code"].apply(lambda z: z.notna().mean() * 100)
years = coverage_after.index.astype(int)

fig, ax = plt.subplots(figsize=(9, 4.2))
x = np.arange(len(years))
ax.bar(x - 0.2, coverage_before.reindex(coverage_after.index).values, width=0.38, color=GRAY, label="Before (reported only)")
ax.bar(x + 0.2, coverage_after.values, width=0.38, color=BLUE, label="After (reported + imputed)")
for xi, value in zip(x, coverage_before.reindex(coverage_after.index).values):
    ax.text(xi - 0.2, value + 1.5, f"{value:.0f}%", ha="center", fontsize=9, color=INK_SOFT)
for xi, value in zip(x, coverage_after.values):
    ax.text(xi + 0.2, value + 1.5, f"{value:.0f}%", ha="center", fontsize=9, color=INK)
ax.set_xticks(x, [f"{y}" + (" (Jan–Mar)" if y == 2026 else "") for y in years])
ax.set_ylim(0, 122)
ax.set_yticks(range(0, 101, 20))
ax.yaxis.set_major_formatter(mticker.PercentFormatter())
ax.legend(loc="upper left", ncol=2)
finish_chart(ax, "Crashes with a known ZIP code, before and after imputation", None, "Crashes with a ZIP")
plt.show()

# %% [markdown]
# **Reading the chart:** before cleaning, 2022 had a ZIP for only 16% of crashes, so a ZIP-level count would show 2022 as far safer than later years. After the two imputation steps every year is above 95%, so **years can now be compared fairly**.
#
# ### 7.3 The cleaning did not distort the data

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
before_units = housing_raw["all_counted_units"].dropna()
after_units = housing["affordable_units"].astype(float)
axes[0].boxplot([np.log10(before_units), np.log10(after_units.replace(0, np.nan).dropna())], orientation="horizontal",
                tick_labels=["Before", "After"], widths=0.5, patch_artist=True,
                boxprops=dict(facecolor=BLUE_RAMP[1], edgecolor=INK_SOFT), medianprops=dict(color=INK))
axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{10 ** v:,.0f}"))
axes[0].grid(axis="x", visible=True)
finish_chart(axes[0], "Affordable units per building", "Units (log scale)", source=False)
monthly_before = pd.to_datetime(crashes_raw["crash_date"]).dt.to_period("M").value_counts().sort_index()
monthly_after = crashes["crash_date"].dt.to_period("M").value_counts().sort_index()
axes[1].plot(monthly_before.index.to_timestamp(), monthly_before.values, color=GRAY, linewidth=4, label="Before")
axes[1].plot(monthly_after.index.to_timestamp(), monthly_after.values, color=ORANGE, linewidth=1.5, label="After")
axes[1].set_ylim(0, None)
axes[1].xaxis.set_major_locator(mdates.YearLocator())
axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axes[1].legend(loc="lower right")
finish_chart(axes[1], "Serious crashes per month", None, "Crashes")
plt.show()

# %% [markdown]
# Both lines overlap almost exactly: the cleaning removed only broken records and one duplicate, and **did not change** the shape of the data. Building sizes are identical before and after (zeros were only filled into the *part* columns, not the totals).
#
# ### 7.4 Automatic checks
# These `assert` statements stop the notebook with an error if any cleaning rule is broken. They protect us when the data is downloaded again in the future.

# %%
assert crashes["crash_id"].is_unique, "duplicate crash IDs"
assert crashes["borough"].notna().all(), "crash without borough"
assert not crashes["zip_code"].eq("10000").any(), "placeholder ZIP left"
assert (crashes["crash_time"].str.len() == 5).all(), "time not in HH:MM"
assert not (housing[["house_number", "street_name"]] == "----").any().any(), "'----' left"
assert (housing[INCOME_BAND_COLUMNS].sum(axis=1) == housing["affordable_units"]).all(), "income bands do not add up"
assert housing["zip_code"].dropna().str.fullmatch(r"\d{5}").all(), "ZIP not 5 digits"
assert crashes["zip_code"].dropna().str.fullmatch(r"\d{5}").all(), "ZIP not 5 digits"
print("All cleaning checks passed.")
print(f"Housing: {len(housing_raw):,} -> {len(housing):,} rows | Crashes: {len(crashes_raw):,} -> {len(crashes):,} rows")

# %% [markdown]
# ### 7.5 Automated before/after report (Lab 1: Sweetviz `compare`)
# In Lab 1, Sweetviz compared a train and a test set. We use the same function to compare the crash data **before and after cleaning**. The report is saved as `reports/crashes_before_after.html`. Like the profiling reports, it only runs when the flag is `True`.

# %%
RUN_SWEETVIZ_COMPARE = False

if RUN_SWEETVIZ_COMPARE:
    # !pip install sweetviz   (Colab: run this once)
    import sweetviz as sv
    shared_columns = ["borough", "severe_injuries", "fatalities", "non_severe_injuries", "zip_code", "latitude"]
    before = crashes_raw.rename(columns={"crash_borough": "borough", "total_severe_injuries": "severe_injuries",
                                         "total_fatalities": "fatalities", "total_non_severe_injuries": "non_severe_injuries",
                                         "zipcode": "zip_code"})[shared_columns]
    after = crashes[shared_columns].astype({"zip_code": "float", "severe_injuries": "float", "fatalities": "float",
                                           "non_severe_injuries": "float"})
    sv.compare([before.astype({"zip_code": "float"}), "Before cleaning"], [after, "After cleaning"]).show_html(
        "reports/crashes_before_after.html", open_browser=False)
