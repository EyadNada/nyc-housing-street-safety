# %% [markdown]
# # Homes on Dangerous Streets?
# ## Affordable Housing and Serious Traffic Crashes in New York City (2022–2025)
#
# **Data Engineering and Visualization, Winter Semester 2026: Project Milestone 1**
# German International University, Faculty of Informatics and Computer Science
#
# | Role | Member | ID | Main sections |
# |---|---|---|---|
# | M1: Lead & Integration | *(name)* | *(ID)* | 1, 2, 8, 9, RQ1–RQ2 |
# | M2: Housing data | *(name)* | *(ID)* | 3, 5, RQ3–RQ4 |
# | M3: Transport data | *(name)* | *(ID)* | 4, 6, RQ5–RQ6 |
# | M4: Website logic | *(name)* | *(ID)* | 11, website callbacks, RQ7–RQ8 |
# | M5: Website visuals & deployment | *(name)* | *(ID)* | website layout & deployment, RQ9–RQ10 |
# | M6: Story & documentation | *(name)* | *(ID)* | 7, 12, 13, 14, RQ11–RQ12 |
#
# **Website:** `https://<your-service>.onrender.com` *(add after deployment)* · **Repository:** `https://github.com/<team>/<repo>` *(add)*
#
# **Our question in one sentence:** *New York City builds thousands of affordable homes every year. Are these homes being built next to the city's most dangerous streets?*
#
# ### How to run this notebook
# 1. Open it in Google Colab (or Jupyter) and run all cells from top to bottom (**Runtime → Run all**).
# 2. The first run downloads both datasets from the NYC Open Data API. Every later run uses the saved copy in `data/raw/`, so all numbers in our text stay the same.
# 3. The last section saves the clean tables in `data/clean/`. The website reads these files.
#
# ### Table of contents
# 1. Project overview and dataset choice
# 2. Extract: loading the data from the API
# 3. EDA: Affordable Housing dataset
# 4. EDA: Serious crashes (SIRTA) dataset
# 5. Pre-integration cleaning: housing
# 6. Pre-integration cleaning: crashes
# 7. Checking that the cleaning worked
# 8. Integration
# 9. Post-integration cleaning
# 10. Research questions (12 questions, 12 charts)
# 11. Load: saving clean tables for the website
# 12. Story, limitations and "so what?" for NYC
# 13. Team contributions
# 14. Prompts log

# %% [markdown]
# ---
# # 1. Project overview and dataset choice *(M1)*
#
# We follow the **ETL** process from Lecture 1, and the scraping pipeline from Lab 1 adapted to an API:
#
# | Lab 1 pipeline (web scraping) | Our pipeline (NYC Open Data API) |
# |---|---|
# | Access a web page → `requests` | Call the API URL → `requests` |
# | Parse the HTML → BeautifulSoup | Read the CSV response → `pandas` |
# | Inspect what to scrape → DevTools | Read the column list and data dictionary on NYC Open Data |
# | Data table → store & process → plot | DataFrame → clean & integrate → plot and website |
#
# **Why not web scraping?** NYC Open Data gives an official API with clean, structured columns. Scraping is only needed when no API exists, and using the API is what the site's terms of use intend.
#
# ### The two datasets
#
# | | Housing: **Affordable Housing Production by Building** | Transportation: **Serious Injury Response, Tracking & Analysis Program (SIRTA)** |
# |---|---|---|
# | Catalog ID | H2 | T4 |
# | Agency | Department of Housing Preservation and Development (HPD) | Department of Transportation (DOT) |
# | Link | https://data.cityofnewyork.us/d/hg8x-zxpr | https://data.cityofnewyork.us/d/xeqp-qz8h |
# | One row is | one building in one affordable-housing project | one serious crash (at least one severe injury or death) |
# | Size | 9,551 rows × 41 columns | 12,947 rows × 23 columns |
# | Time | projects started 2014 to 2026 | crashes January 2022 to March 2026 |
# | Geography | borough, ZIP code, community board, latitude/longitude | borough, police precinct, ZIP code, latitude/longitude |
# | Known issues (found in EDA) | hidden missing values ("CONFIDENTIAL", "----"), mostly-empty unit columns, very skewed sizes, Excel-corrupted addresses | 444 broken records, ZIP missing for 84% of 2022 crashes, placeholder ZIP and time, no coordinates for fatal crashes after 2022 |
#
# ### Why we chose this pair
# 1. **Both are in the catalog**, so no feasibility check is needed.
# 2. **They share three integration fields**: ZIP code, borough and coordinates. They also share time (completion date and crash date).
# 3. **Both are small enough to use completely** (about 9,500 and 13,000 rows). We use the **whole population**, not a sample (Lecture 3), so there is no sampling bias.
# 4. **They have real data-quality problems** (hidden missing values, broken records, corrupted addresses, missing ZIP codes). This lets us show every cleaning method from Lab 2.
# 5. **The story matters for the city.** If new affordable homes are built next to dangerous streets, the people who moved in, often low-income families, face that danger every day. DOT can redesign those streets.
#
# **Different granularities:** a building and a crash are different kinds of events, so their rows cannot be matched one to one. We **aggregate both to ZIP code × year** and also **measure distances** between buildings and crashes (Section 8 explains and justifies both).
#
# **A limitation we state from the start:** SIRTA only contains *serious* crashes (severe injury or death). Our story is about **dangerous streets**, not about all traffic.

# %% [markdown]
# ---
# # 2. Extract: loading the data from the API *(M1)*
#
# We download both datasets with `requests`, like Lab 1.
# - The parameter `$limit=50000` is larger than both datasets, so we receive **every row**. Neither dataset is sampled.
# - We save a raw copy (a *snapshot*) in `data/raw/`. The datasets are updated every few months, so a fixed snapshot means every member and the TAs get the same numbers as our text.
# - To download fresh data, set `REFRESH_FROM_API = True`.

# %%
# --- Standard libraries ---
import io
import os
import re
import warnings

# --- Data and statistics ---
import numpy as np
import pandas as pd
import requests
from scipy import stats
from sklearn.neighbors import BallTree, KNeighborsClassifier

# --- Plotting (same libraries as Labs 1 and 2) ---
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 160)
%matplotlib inline

# %%
# ---------------------------------------------------------------
# One visual style for every chart in the notebook.
# The same colors are used on the website, so a reader always
# sees the same color for the same meaning (Gestalt: similarity).
# The 3 accent colors were checked for colorblind safety.
# ---------------------------------------------------------------
BLUE = "#2a78d6"    # main color: housing / "near new affordable housing"
ORANGE = "#eb6834"  # second color: crashes / "double hotspot"
AQUA = "#1baf7a"    # third color (used rarely)
GRAY = "#b5b3ab"    # "everything else" (de-emphasis)
INK = "#0b0b0b"
INK_SOFT = "#52514e"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
RED = "#e34948"     # negative side of diverging scales
DIVERGING_MID = "#f0efec"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
BOROUGH_ORDER = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK_SOFT, "axes.titlecolor": INK,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
    "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK_SOFT, "ytick.color": INK_SOFT, "text.color": INK,
    "font.family": "sans-serif", "font.size": 10, "legend.frameon": False,
    "figure.dpi": 100,
})


def finish_chart(ax, title, xlabel=None, ylabel=None, source=True):
    """Apply the same title, axis labels and source note to every chart."""
    ax.set_title(title)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if source:
        ax.figure.text(0.01, -0.02, "Source: NYC Open Data (HPD Affordable Housing Production; DOT SIRTA)",
                       fontsize=8, color=INK_SOFT, ha="left")
    ax.figure.tight_layout()

# %%
# ---------------------------------------------------------------
# Extract step
# ---------------------------------------------------------------
API_BASE_URL = "https://data.cityofnewyork.us/resource/{dataset_id}.csv"
HOUSING_DATASET_ID = "hg8x-zxpr"   # Affordable Housing Production by Building
CRASH_DATASET_ID = "xeqp-qz8h"     # SIRTA serious crashes
RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"
REFRESH_FROM_API = False           # True = download a fresh copy from the API

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CLEAN_DIR, exist_ok=True)


def fetch_from_api(dataset_id, row_limit=50_000):
    """Download one NYC Open Data dataset as CSV through the Socrata API.

    row_limit is larger than the dataset, so the full dataset is returned (no sampling).
    """
    url = API_BASE_URL.format(dataset_id=dataset_id)
    response = requests.get(url, params={"$limit": row_limit}, timeout=120)
    response.raise_for_status()                      # stop with a clear error if the API fails
    return pd.read_csv(io.StringIO(response.text), low_memory=False)


def load_raw_dataset(dataset_id, file_name):
    """Use the saved snapshot if it exists; otherwise download it and save it."""
    path = os.path.join(RAW_DIR, file_name)
    if os.path.exists(path) and not REFRESH_FROM_API:
        source = f"saved snapshot {path}"
    else:
        fetch_from_api(dataset_id).to_csv(path, index=False)
        source = f"NYC Open Data API ({dataset_id}), saved to {path}"
    df = pd.read_csv(path, low_memory=False)
    print(f"Loaded {len(df):,} rows x {df.shape[1]} columns from {source}")
    return df


housing_raw = load_raw_dataset(HOUSING_DATASET_ID, "housing_raw.csv")
crashes_raw = load_raw_dataset(CRASH_DATASET_ID, "sirta_raw.csv")

# %% [markdown]
# **Note on column names:** the API uses short field names (for example `postcode`, `all_counted_units`). The "Export" button on the website gives longer display names ("Postcode", "All Counted Units"), so we always use the API.
#
# **Note on data types:** a CSV file stores everything as text. pandas guesses the types, and it guesses wrong for some columns (dates stay text, ZIP codes become decimals like `11432.0`). We fix the types during cleaning (Sections 5 and 6), like the "change data type" step in Lab 3 (Power Query).

# %% [markdown]
# ---
# # 3. EDA: Affordable Housing dataset *(M2)*
#
# We follow the EDA order from Lab 1: **structure → summary statistics → missing values → unique values → hidden missing values → duplicates → distributions → relationships**.
#
# ### 3.1 Structure

# %%
print("Shape (rows, columns):", housing_raw.shape)
housing_raw.head(3).T

# %%
housing_raw.info()

# %% [markdown]
# **What we see:**
# - 9,551 rows and 41 columns. Each row is **one building inside one project** (HPD's definition), so the same building can appear more than once if it joined several projects.
# - Dates (`project_start_date`, `building_completion_date`) are stored as text, so they must be converted.
# - `postcode` is a decimal number (`11432.0`). A ZIP code is a label, not a quantity, so it must become text.
#
# ### 3.2 Data types (Lecture 2)
#
# | Column | Type of data | Why |
# |---|---|---|
# | `borough`, `postcode`, `community_board`, `reporting_construction_type` | Nominal | Names or labels with no order |
# | Income bands (extremely low → middle income) | Ordinal | Ordered categories (from 0–30% to 121–165% of area median income) |
# | `project_start_date`, `building_completion_date` | Interval | Dates: differences make sense, but "twice a date" does not |
# | `total_units`, `all_counted_units`, bedroom counts | Ratio | Counts with a true zero ("200 units is twice 100 units") |
#
# ### 3.3 Summary statistics

# %%
HOUSING_UNIT_COLUMNS = ["total_units", "all_counted_units", "counted_rental_units", "counted_homeownership_units",
                        "extremely_low_income_units", "very_low_income_units", "low_income_units",
                        "moderate_income_units", "middle_income_units"]
housing_raw[HOUSING_UNIT_COLUMNS].describe().round(1).T

# %%
housing_raw.select_dtypes(exclude="number").describe().T     # text columns (works in pandas 2 and 3)

# %% [markdown]
# **What we see:**
# - Units per building are **strongly right-skewed**. The median building has 12 units, but the mean is 46.7 and the largest has 1,320. Most buildings are small homes, and a few are very large towers.
# - Because of this skew, we describe "typical" buildings with the **median**, not the mean (Lecture 3).
# - The top `project_name` value is **"CONFIDENTIAL"** (1,949 rows). This is a hidden missing value, checked in 3.5.
#
# ### 3.4 Missing values

# %%
def missing_value_table(df):
    """Count and percentage of empty cells per column, largest first."""
    table = pd.DataFrame({
        "missing": df.isna().sum(),
        "percent": (df.isna().mean() * 100).round(1),
    })
    return table[table["missing"] > 0].sort_values("missing", ascending=False)


housing_missing = missing_value_table(housing_raw)
housing_missing

# %%
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(housing_missing.index, housing_missing["percent"], color=BLUE, height=0.7)
ax.invert_yaxis()
ax.xaxis.set_major_formatter(mticker.PercentFormatter())
ax.grid(axis="x", visible=True)
finish_chart(ax, "Housing: share of empty cells per column", "Empty cells (% of 9,551 rows)")
plt.show()

# %% [markdown]
# **What we see:** the missing values fall into three groups, and each group needs a different decision (Section 5):
# 1. **Unit columns by income band and bedroom size (up to 99% empty).** Our hypothesis: empty means *zero units*, not *unknown*. Evidence: no unit column ever contains a 0 (the smallest value is 1), so HPD leaves the cell empty instead of writing 0. We test this in 3.6.
# 2. **Location columns (ZIP, coordinates, BBL; about 20% empty).** These are almost all the CONFIDENTIAL projects.
# 3. **Completion dates (17–19% empty).** These projects are **not finished yet**. The value is not lost; the event has not happened.
#
# ### 3.5 Hidden missing values (the "?" lesson from Lab 1)
#
# In Lab 1, the Adult dataset used `"?"` for missing values, so `isna()` showed zero missing values. We look for the same problem here.

# %%
def count_disguised_missing(df, markers):
    """Count cells that hold a placeholder instead of a real value.

    markers: dict {column: list of placeholder values}.
    """
    rows = []
    for column, values in markers.items():
        rows.append({"column": column, "placeholder": ", ".join(map(str, values)),
                     "cells": int(df[column].isin(values).sum())})
    return pd.DataFrame(rows)


PLACEHOLDER_BINS = [1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]  # borough digit + zeros
count_disguised_missing(housing_raw, {
    "project_name": ["CONFIDENTIAL"],
    "house_number": ["----"],
    "street_name": ["----"],
    "bin": PLACEHOLDER_BINS,
})

# %%
is_confidential = housing_raw["project_name"].eq("CONFIDENTIAL")
print("Confidential rows:", is_confidential.sum())
print("  ... with a ZIP code:     ", housing_raw.loc[is_confidential, "postcode"].notna().sum())
print("  ... with coordinates:    ", housing_raw.loc[is_confidential, "latitude"].notna().sum())
print("  ... with a borough:      ", housing_raw.loc[is_confidential, "borough"].notna().sum())
print("  ... with a community board:", housing_raw.loc[is_confidential, "community_board"].notna().sum())
print("  ... affordable units in total:", int(housing_raw.loc[is_confidential, "all_counted_units"].sum()))
print("Non-confidential rows without a ZIP:", housing_raw.loc[~is_confidential, "postcode"].isna().sum())

# %% [markdown]
# **What we see:**
# - **1,949 CONFIDENTIAL rows** have no address, ZIP or coordinates, but they **do** have a borough and community board. HPD hides the exact address to protect the privacy of homeowners (most are 1-unit homes, only 2,805 units in total). We can still use them for **borough-level** charts.
# - **482 building IDs (BIN) are placeholders** such as `3000000` (borough digit + zeros), meaning "unknown building".
# - Almost all missing ZIP codes come from confidential rows (only 9 others).
#
# One more hidden problem: some **house numbers were corrupted by Excel into dates**. Queens addresses use a hyphen (for example "10-44 Jackson Avenue"), and Excel turned "10-44" into "Oct-44".

# %%
MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
excel_date_pattern = rf"^(?:(?:{MONTHS})-\d+|\d+-(?:{MONTHS}))$"
corrupted_house_numbers = housing_raw["house_number"].str.match(excel_date_pattern, na=False)
print("House numbers turned into dates by Excel:", corrupted_house_numbers.sum())
housing_raw.loc[corrupted_house_numbers, ["house_number", "street_name", "borough"]].head(6)

# %% [markdown]
# ### 3.6 Testing the "empty means zero" hypothesis for unit columns
#
# If an empty unit cell really means 0, then after filling it with 0 the income bands must add up **exactly** to `all_counted_units` in every row. The same must be true for the bedroom sizes and for rental + homeownership.

# %%
INCOME_BAND_COLUMNS = ["extremely_low_income_units", "very_low_income_units", "low_income_units",
                       "moderate_income_units", "middle_income_units", "other_income_units"]
BEDROOM_COLUMNS = ["studio_units", "_1_br_units", "_2_br_units", "_3_br_units", "_4_br_units",
                   "_5_br_units", "_6_br_units", "unknown_br_units"]
TENURE_COLUMNS = ["counted_rental_units", "counted_homeownership_units"]

has_total = housing_raw["all_counted_units"].notna()
checks = {
    "Income bands add up to all_counted_units": housing_raw[INCOME_BAND_COLUMNS].fillna(0).sum(axis=1),
    "Bedroom sizes add up to all_counted_units": housing_raw[BEDROOM_COLUMNS].fillna(0).sum(axis=1),
    "Rental + homeownership add up to all_counted_units": housing_raw[TENURE_COLUMNS].fillna(0).sum(axis=1),
}
for name, row_sums in checks.items():
    match_rate = (row_sums[has_total] == housing_raw.loc[has_total, "all_counted_units"]).mean() * 100
    print(f"{name}: {match_rate:.1f}% of rows")
print("Zeros stored anywhere in these columns:",
      int((housing_raw[INCOME_BAND_COLUMNS + BEDROOM_COLUMNS + TENURE_COLUMNS] == 0).sum().sum()))
print("Rows where all_counted_units is empty:", (~has_total).sum(),
      "| their income bands add up to:", housing_raw.loc[~has_total, INCOME_BAND_COLUMNS].fillna(0).sum().sum())

# %% [markdown]
# **Result:** after filling empty cells with 0, the parts add up **exactly (100%)** to the total in every row, and no zero is stored anywhere. This proves that **empty = 0 units**. The 29 rows with an empty `all_counted_units` also have no units in any band, so they are zero too.
#
# ### 3.7 Duplicates (Lecture 1: "always remove duplicates?")

# %%
print("Fully duplicated rows:", housing_raw.duplicated().sum())
print("Repeated (project, building) pairs:", housing_raw.duplicated(["project_id", "building_id"]).sum())
print("Building IDs that appear in more than one project:", housing_raw["building_id"].dropna().duplicated().sum())

# %% [markdown]
# **What we see:** there are **no true duplicates**. 124 buildings appear in more than one project (for example, preserved in 2016 and again in 2023). These are **different events**, and HPD counts the units toward each project, so we **keep** them. This answers the Lecture 1 question: duplicates should not always be removed.
#
# ### 3.8 Distributions

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(housing_raw["all_counted_units"].dropna(), bins=60, color=BLUE)
finish_chart(axes[0], "Affordable units per building (raw scale)", "Affordable units", "Buildings", source=False)
axes[1].hist(np.log10(housing_raw["all_counted_units"].dropna()), bins=40, color=BLUE)
axes[1].xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{10 ** v:,.0f}"))
finish_chart(axes[1], "Same data on a log scale", "Affordable units (log scale)", "Buildings")
plt.show()
print("Skewness of all_counted_units:", round(housing_raw["all_counted_units"].skew(), 2))

# %%
fig, ax = plt.subplots(figsize=(10, 3))
sns.boxplot(x=housing_raw["all_counted_units"], color=BLUE, fliersize=2, ax=ax, width=0.4)
ax.set_xscale("log")
finish_chart(ax, "Box plot of affordable units per building (log scale)", "Affordable units (log scale)")
plt.show()

# %% [markdown]
# **What we see:** a skewness of 3.7 means a long right tail. On the log scale the shape becomes readable: most buildings have between 1 and 100 affordable units. We show the histogram **and** the box plot, because a box plot alone can hide the shape of a distribution (Lecture 4).

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
borough_counts = housing_raw["borough"].value_counts().reindex(BOROUGH_ORDER)
axes[0].bar(borough_counts.index, borough_counts.values, color=BLUE, width=0.6)
axes[0].tick_params(axis="x", rotation=20)
finish_chart(axes[0], "Buildings per borough", None, "Buildings", source=False)
type_units = housing_raw.groupby("reporting_construction_type")["all_counted_units"].sum()
axes[1].bar(type_units.index, type_units.values, color=BLUE, width=0.5)
axes[1].yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
finish_chart(axes[1], "Affordable units by construction type", None, "Affordable units")
plt.show()

# %%
completion_year = pd.to_datetime(housing_raw["building_completion_date"]).dt.year
units_per_year = housing_raw.groupby(completion_year)["all_counted_units"].sum()
fig, ax = plt.subplots(figsize=(10, 4))
bars = ax.bar(units_per_year.index.astype(int), units_per_year.values, color=GRAY, width=0.7)
for bar, year in zip(bars, units_per_year.index.astype(int)):
    if 2022 <= year <= 2025:
        bar.set_color(BLUE)
ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
ax.set_xticks(units_per_year.index.astype(int))
finish_chart(ax, "Affordable units completed per year (blue = our analysis window, 2022–2025)",
             "Year the building was completed", "Affordable units")
plt.show()

# %% [markdown]
# **What we see:** about 22,000–31,000 affordable units are completed every year from 2022 to 2025. 2026 is only partly recorded (the data ends mid-2026). 2020 dips, which matches COVID-19 construction stops.
#
# ### 3.9 Relationships between numeric columns (Lab 1: correlation heatmap)

# %%
corr_columns = ["total_units", "all_counted_units", "extremely_low_income_units", "very_low_income_units",
                "low_income_units", "moderate_income_units", "middle_income_units", "_2_br_units", "_3_br_units"]
corr = housing_raw[corr_columns].fillna(0).corr(method="spearman")
fig, ax = plt.subplots(figsize=(8, 6.5))
sns.heatmap(corr, annot=True, fmt=".2f", cmap=sns.blend_palette([RED, DIVERGING_MID, BLUE], as_cmap=True),
            vmin=-1, vmax=1, linewidths=1, linecolor=SURFACE, ax=ax, cbar_kws={"label": "Spearman correlation"})
ax.grid(False)
finish_chart(ax, "Housing: rank correlation between unit columns")
plt.show()

# %% [markdown]
# Blue means the two columns rise together, red means one rises when the other falls. Middle-income units are slightly negatively related to the low-income bands: buildings usually target either low-income or middle-income tenants, not both.
#
# We use **Spearman** (rank) correlation instead of Pearson, because the unit counts are very skewed. Spearman only uses the order of the values, so a few huge buildings cannot dominate it.
#
# ### 3.10 Where are the buildings?

# %%
fig, ax = plt.subplots(figsize=(7, 7))
located = housing_raw.dropna(subset=["latitude", "longitude"])
ax.scatter(located["longitude"], located["latitude"], s=3, color=BLUE, alpha=0.4, linewidths=0)
ax.set_aspect(1.3)
ax.grid(axis="both")
finish_chart(ax, f"Affordable-housing buildings with coordinates ({len(located):,})", "Longitude", "Latitude")
plt.show()

# %% [markdown]
# ### Insights from the housing EDA
# 1. **Units are very skewed.** We use medians, log scales and rank correlation.
# 2. **Three kinds of missing values need three different decisions:** empty unit cells mean 0 (proven in 3.6), empty locations are confidential homes, and empty completion dates mean "not finished yet".
# 3. **Hidden missing values exist:** "CONFIDENTIAL", "----", placeholder BINs, and Excel-corrupted house numbers.
# 4. **There are no true duplicates.** Repeated buildings are separate projects.
# 5. **The income-band columns break the tidy-data rule from Lecture 2** ("column headers are values, not variable names"). We reshape them into a long table in Section 5.

# %% [markdown]
# ---
# # 4. EDA: Serious crashes (SIRTA) dataset *(M3)*
#
# ### 4.1 Structure

# %%
print("Shape (rows, columns):", crashes_raw.shape)
crashes_raw.head(3).T

# %%
crashes_raw.info()

# %% [markdown]
# **What we see:** 12,947 rows and 23 columns. As in the housing data, dates are text and ZIP codes are decimals. The police precinct is stored as a decimal (`46.0`).
#
# **Data types (Lecture 2):** `crash_borough`, `zipcode`, `crash_police_precinct` and `on_street` are **nominal**. `crash_date` is **interval**. `total_severe_injuries`, `total_fatalities` and `total_non_severe_injuries` are **ratio** (counts).
#
# ### 4.2 Missing values

# %%
crash_missing = missing_value_table(crashes_raw)
crash_missing

# %%
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(crash_missing.index, crash_missing["percent"], color=ORANGE, height=0.7)
ax.invert_yaxis()
ax.xaxis.set_major_formatter(mticker.PercentFormatter())
ax.grid(axis="x", visible=True)
finish_chart(ax, "Crashes: share of empty cells per column", "Empty cells (% of 12,947 rows)")
plt.show()

# %% [markdown]
# **What we see:** exactly **444 rows** are missing the crash ID, date, time, precinct and injury counts together. That looks like a group of broken rows. We check them next.
#
# ### 4.3 Hidden problem 1: 444 broken records

# %%
broken_records = crashes_raw[crashes_raw["open_data_crash_id"].isna()]
print("Rows without a crash ID:", len(broken_records))
print("Fully empty rows found by isna().all():", crashes_raw.isna().all(axis=1).sum())
print("\nColumns that still have values in these rows:")
print(broken_records.notna().sum()[broken_records.notna().sum() > 0])

# %% [markdown]
# **What we see:** the standard check `isna().all()` finds **zero** empty rows, but the 444 rows still contain **no crash information at all**: no ID, date, time or injuries. Only location codes (community board, council district, census tract) are filled. These are probably location attributes that lost their crash during the agency's data processing. Without a date or an outcome they cannot be counted as crashes. We decide what to do in Section 6.
#
# ### 4.4 Hidden problem 2: placeholders in ZIP and time

# %%
crashes_valid = crashes_raw[crashes_raw["open_data_crash_id"].notna()]
print("ZIP code = 10000 (not a real NYC ZIP):", (crashes_valid["zipcode"] == 10000).sum())
print("\nMost common exact crash times:")
print(crashes_valid["crash_time"].value_counts().head(5))
print("\nTime written with one hour digit (e.g. '6:56'):", (crashes_valid["crash_time"].str.len() == 4).sum(),
      "| with two digits (e.g. '06:56'):", (crashes_valid["crash_time"].str.len() == 5).sum())

# %% [markdown]
# **What we see:**
# - **37 crashes have ZIP `10000`**, which is not a real NYC ZIP code (Manhattan starts at 10001). It is a placeholder.
# - **Midnight is the most common time (163 + 41 = 204 crashes)**, twice as common as 15:00, the busiest real hour. Real traffic at midnight is much lighter, so "00:00" is very likely the **default value when the time is unknown**. This is the same kind of problem as the "?" in Lab 1.
# - Times use two formats ("0:55" and "00:55"), which we standardize.
#
# ### 4.5 Duplicates

# %%
print("Fully duplicated rows (valid records):", crashes_valid.duplicated().sum())
duplicate_ids = crashes_valid[crashes_valid["open_data_crash_id"].duplicated(keep=False)]
duplicate_ids[["open_data_crash_id", "crash_date", "crash_time", "crash_borough", "on_street",
               "total_severe_injuries", "total_fatalities", "similar_fatalities_severe"]]

# %%
same_location = crashes_valid.duplicated(["latitude", "longitude"]) & crashes_valid["latitude"].notna()
print("Crashes that share exact coordinates with an earlier crash:", same_location.sum())

# %% [markdown]
# **What we see:**
# - **One crash ID appears twice**, with the same time, street and precinct, but dates three years apart (13 Jan 2023 and 13 Jan 2026). An ID is supposed to be unique, so one of the two is a data-entry error.
# - **3,538 crashes share coordinates with another crash.** These are **not duplicates**: they have different IDs and dates. Crashes are mapped to the nearest intersection, so dangerous intersections appear many times. This is exactly the "repeat location" pattern we study in RQ8.
#
# ### 4.6 Distributions of crash outcomes

# %%
fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
for ax, column, title in zip(axes, ["total_severe_injuries", "total_fatalities", "total_non_severe_injuries"],
                             ["Severe injuries per crash", "Deaths per crash", "Non-severe injuries per crash"]):
    counts = crashes_valid[column].value_counts().sort_index()
    ax.bar(counts.index.astype(int).astype(str), counts.values, color=ORANGE, width=0.7)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    finish_chart(ax, title, "People per crash", "Crashes (log scale)", source=(ax is axes[-1]))
plt.show()
q1, q3 = crashes_valid["total_severe_injuries"].quantile([0.25, 0.75])
print(f"Severe injuries: Q1 = {q1:.0f}, Q3 = {q3:.0f}, so IQR = {q3 - q1:.0f}")
print("Share of crashes with exactly 1 severe injury:",
      f"{(crashes_valid['total_severe_injuries'] == 1).mean():.0%}")
print("Crashes with 0 severe injuries AND 0 deaths:",
      ((crashes_valid["total_severe_injuries"] == 0) & (crashes_valid["total_fatalities"] == 0)).sum())

# %% [markdown]
# **What we see:**
# - 87% of crashes have exactly one severe injury. Q1 = Q3 = 1, so **IQR = 0**. The IQR rule from Lab 2 would mark *every* crash with 0 or 2+ severe injuries as an outlier, which makes no sense. We need domain rules for this column (Section 6).
# - **No crash has 0 severe injuries and 0 deaths.** This matches SIRTA's definition (every crash has a severe injury or a death), so the outcome columns are consistent.
#
# ### 4.7 Crashes over time and by borough

# %%
crash_month = pd.to_datetime(crashes_valid["crash_date"]).dt.to_period("M").dt.to_timestamp()
monthly = crash_month.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(monthly.index, monthly.values, color=ORANGE, linewidth=2)
ax.set_ylim(0, monthly.max() * 1.15)
finish_chart(ax, "Serious crashes per month (January 2022 – March 2026)", None, "Serious crashes")
plt.show()

# %%
year_zip = crashes_valid.assign(year=pd.to_datetime(crashes_valid["crash_date"]).dt.year).groupby("year").agg(
    crashes=("open_data_crash_id", "size"),
    zip_reported=("zipcode", lambda z: z.notna().mean() * 100),
    coordinates=("latitude", lambda z: z.notna().mean() * 100),
).round(1)
year_zip

# %% [markdown]
# **What we see, and this is our most important EDA finding:**
# - Serious crashes are fairly stable at about 230–290 per month, with summer peaks.
# - **Only 16% of 2022 crashes have a ZIP code**, compared with 68–80% in later years. **If we dropped crashes without a ZIP, 2022 would look about 80% safer than it really was**, and every trend chart would show a fake rise in crashes. Dropping is therefore the wrong choice. Section 6 fills the ZIP from the coordinates instead.
# - Coordinates are much more complete (66–89%), so they can be used to fill the ZIP.
#
# **A second, hidden pattern: fatal crashes lose their exact location after 2022.**

# %%
location_by_severity = crashes_valid.assign(
    year=pd.to_datetime(crashes_valid["crash_date"]).dt.year,
    crash_type=np.where(crashes_valid["total_fatalities"] > 0, "fatal", "severe injury only"),
).groupby(["year", "crash_type"]).agg(
    crashes=("open_data_crash_id", "size"),
    coordinates=("latitude", lambda v: v.notna().mean() * 100),
    zip_reported=("zipcode", lambda v: v.notna().mean() * 100),
    street_name=("on_street", lambda v: v.notna().mean() * 100),
    precinct=("crash_police_precinct", lambda v: v.notna().mean() * 100),
).round(0)
location_by_severity

# %% [markdown]
# **What we see:** from 2023 onward, **no fatal crash has coordinates (0%)**, while 84% of fatal crashes in 2022 and 72–95% of non-fatal crashes do. The precinct is always known, and the street name usually is. The agency seems to have stopped publishing the exact location of deadly crashes. This matters for us in two ways:
# 1. Fatal crashes after 2022 **cannot be placed on a map or measured by distance**. Our distance questions (RQ5, RQ6, RQ8, RQ9, RQ11) therefore describe mostly severe-injury crashes. We state this in each answer.
# 2. 30–44% of these fatal crashes also have no ZIP, and coordinates cannot fill it. If we ignored this, every death rate per ZIP would be too low. Section 6.9 fills these ZIPs from the **street name and precinct** instead.

# %%
fig, ax = plt.subplots(figsize=(8, 4))
borough_crashes = crashes_valid["crash_borough"].value_counts().reindex(BOROUGH_ORDER)
ax.bar(borough_crashes.index, borough_crashes.values, color=ORANGE, width=0.6)
finish_chart(ax, "Serious crashes per borough (2022 – March 2026)", None, "Serious crashes")
plt.show()
print("Crashes with no borough:", crashes_valid["crash_borough"].isna().sum(),
      "| their police precincts:", crashes_valid.loc[crashes_valid["crash_borough"].isna(),
                                                      "crash_police_precinct"].value_counts().to_dict())

# %% [markdown]
# **What we see:** Brooklyn has the most serious crashes. 46 crashes have no borough, and **all of them are in police precinct 116**, a new precinct in south-east Queens. No other crash in that precinct has a borough written, so the borough was probably never filled in for the new precinct. We fix this in Section 6.

# %%
fig, ax = plt.subplots(figsize=(7, 7))
located_crashes = crashes_valid.dropna(subset=["latitude", "longitude"])
ax.scatter(located_crashes["longitude"], located_crashes["latitude"], s=3, color=ORANGE, alpha=0.35, linewidths=0)
ax.set_aspect(1.3)
ax.grid(axis="both")
finish_chart(ax, f"Serious crashes with coordinates ({len(located_crashes):,})", "Longitude", "Latitude")
plt.show()
print("Latitude range:", located_crashes["latitude"].min(), "to", located_crashes["latitude"].max())
print("Longitude range:", located_crashes["longitude"].min(), "to", located_crashes["longitude"].max())

# %% [markdown]
# All coordinates fall inside New York City (latitude 40.49–40.92, longitude −74.26 to −73.70), so there are **no impossible locations**. Highways show up clearly as lines of dots.
#
# ### 4.8 Street names

# %%
street_suffix = crashes_valid["on_street"].str.extract(r"\b(AVE|ST|BLVD|PKWY|EXPY|RD|PL)$")[0]
print("Street names ending in an abbreviation:", street_suffix.value_counts().to_dict())
print("Street names in lower or mixed case:",
      (crashes_valid["on_street"].dropna() != crashes_valid["on_street"].dropna().str.upper()).sum())
print("Addresses with repeated spaces:", crashes_valid["address"].dropna().str.contains("  ").sum())

# %% [markdown]
# Street names mix full words and abbreviations ("3 AVENUE" and "3 AVE"), and there are case and spacing differences. The same street must have one spelling before we can count crashes per street.
#
# ### 4.9 Automated EDA (Lab 1 tools)
#
# Lab 1 showed two automated EDA tools. We used **ydata-profiling** to create a full report for each raw dataset. The reports are saved in `reports/` (`housing_profile.html`, `crashes_profile.html`). They confirmed everything above: the skewed units, the empty unit columns, and the 444 rows with no crash ID.
#
# The tools are slow and need extra installs, so they only run when the flag below is `True`.

# %%
RUN_AUTOMATED_PROFILING = False

if RUN_AUTOMATED_PROFILING:
    # !pip install ydata-profiling   (Colab: run this once)
    from ydata_profiling import ProfileReport
    os.makedirs("reports", exist_ok=True)
    ProfileReport(housing_raw, title="Affordable Housing - raw data", minimal=True).to_file("reports/housing_profile.html")
    ProfileReport(crashes_raw, title="SIRTA crashes - raw data", minimal=True).to_file("reports/crashes_profile.html")

# %% [markdown]
# ### Insights from the crash EDA
# 1. **444 broken records** have no crash data, and `isna().all()` does not find them.
# 2. **Hidden missing values:** ZIP `10000` and midnight `00:00` as a default time.
# 3. **ZIP coverage depends on the year (16% in 2022 vs 80% in 2025).** Dropping rows without a ZIP would create a fake trend, so the ZIP must be imputed.
# 4. **Fatal crashes have no coordinates after 2022**, so distance-based results describe mostly severe-injury crashes, and fatal crashes need a second way to recover their ZIP.
# 5. **IQR fails on crash outcomes** (IQR = 0), so we use domain rules.
# 6. **One duplicated ID** with a three-year date difference. Repeated coordinates are dangerous intersections, not duplicates.
# 7. **46 crashes without a borough**, all in the new precinct 116 (Queens).
