# %% [markdown]
# ### Summary of the 12 answers
#
# | # | Short answer |
# |---|---|
# | RQ1 | **Yes.** ZIPs with more new affordable units have more serious crashes (ρ = 0.61). |
# | RQ2 | **No year-to-year link.** Crashes are flat while completions swing; the link is about places, not years. |
# | RQ3 | **Yes.** New-construction buildings are in ZIPs with 28% more serious crashes than preserved buildings, in every large borough. |
# | RQ4 | **Partly.** Extremely-low-income units are in ZIPs 10% more dangerous than average; the pattern is not a straight line. |
# | RQ5 | **Slightly.** Near new homes, crashes lean towards the evening (+4 points) and away from the morning peak. |
# | RQ6 | **Yes, strongly.** 96% of serious crashes near new homes are on local streets (vs 90% elsewhere). |
# | RQ7 | **26 double hotspots** (14% of ZIPs) received 43% of new affordable units, mostly in the Bronx and Brooklyn. |
# | RQ8 | **Citywide yes, but mixed:** more repeat-danger spots near new homes in the Bronx and Manhattan, fewer in Brooklyn and Queens. |
# | RQ9 | **Yes.** Mostly-family buildings have 16% fewer serious crashes within 250 m, in every large borough. |
# | RQ10 | **High-growth ZIPs have the least deadly crashes** (6.9 vs about 9 deaths per 100), robust to our imputation choices. |
# | RQ11 | **Slightly fewer (−3%)** after completion, except Manhattan (+17%). |
# | RQ12 | **15 priority ZIPs**, 8 in the Bronx, hold 31% of new affordable units. |

# %% [markdown]
# ---
# # 11. Load: saving clean tables for the website *(M4)*
# The **Load** step of ETL. The website does not repeat the cleaning: it reads these clean tables, so it starts quickly and stays inside the memory limit of a free hosting plan.
#
# | File | One row is | Used for |
# |---|---|---|
# | `buildings_clean.csv` | an affordable building (all years) | housing filters, map, income bands |
# | `crashes_clean.csv` | a serious crash, with its distance to new housing | crash filters, map, heatmap |
# | `zip_year.csv` | a ZIP code in one year (Level A) | ZIP-level charts |
# | `zip_summary.csv` | a ZIP code, 2022–2025 totals | map, scatter, ranking |
# | `borough_year.csv` | a borough in one year (Level C) | trend charts |
# | `housing_income_long.csv` | a building × income band (tidy table) | income-band chart |

# %%
BUILDING_EXPORT_COLUMNS = [
    "project_id", "building_id", "project_name", "is_confidential", "house_number", "street_name", "borough",
    "zip_code", "community_board", "community_district", "latitude", "longitude", "construction_type",
    "extended_affordability_only", "project_start_date", "building_completion_date", "completion_year", "start_year",
    "is_completed", "in_analysis_window", "total_units", "affordable_units", "rental_units", "homeownership_units",
    "deep_affordable_units", "family_units", "deep_affordable_share", "family_share", "is_large_building",
] + INCOME_BAND_COLUMNS
buildings_export = housing[BUILDING_EXPORT_COLUMNS].merge(
    new_buildings[["project_id", "building_id", "crashes_within_250m"]], on=["project_id", "building_id"], how="left")

crashes_export = crashes.merge(
    located_crashes[["crash_id", "distance_to_new_housing_m", "near_new_housing"]], on="crash_id", how="left")
crashes_export = crashes_export[[
    "crash_id", "crash_date", "crash_time", "year", "month", "weekday", "hour", "time_unknown", "borough", "precinct",
    "zip_code", "zip_source", "latitude", "longitude", "on_street", "cross_street", "severe_injuries", "fatalities",
    "non_severe_injuries", "people_seriously_hurt", "is_fatal", "on_highway", "similar_severe_3y", "at_repeat_location",
    "in_analysis_window", "distance_to_new_housing_m", "near_new_housing"]]

exports = {
    "buildings_clean.csv": buildings_export,
    "crashes_clean.csv": crashes_export,
    "zip_year.csv": zip_year,
    "zip_summary.csv": zip_summary,
    "borough_year.csv": borough_year,
    "housing_income_long.csv": housing_income_long,
}
for file_name, table in exports.items():
    table.to_csv(os.path.join(CLEAN_DIR, file_name), index=False)
    size_kb = os.path.getsize(os.path.join(CLEAN_DIR, file_name)) / 1024
    print(f"Saved {file_name:26s} {len(table):>6,} rows  {size_kb:>7,.0f} KB")

# %% [markdown]
# ---
# # 12. Story: Homes on Dangerous Streets? *(M6)*
#
# ### The question
# New York City delivers about 25,000 affordable homes every year, built new or preserved. These homes go to the households who most depend on walking, buses and safe streets. **Are they being placed next to the city's most dangerous streets?**
#
# ### What the data shows
# 1. **Yes, affordable housing and serious crashes are concentrated in the same places.** ZIPs with more new affordable units have more serious crashes (RQ1). 26 "double hotspot" ZIPs, mostly in the South and West Bronx and central Brooklyn, received **43% of all new affordable units** (RQ7).
# 2. **Those most exposed are the newest and poorest residents.** New-construction buildings, where every household is new to the area, are in ZIPs with 28% more serious crashes than preserved buildings (RQ3). Extremely-low-income units are in ZIPs 10% more dangerous than average (RQ4).
# 3. **The danger is on local streets, in the evening.** 96% of serious crashes near new homes are on local streets, not highways (RQ6), and they lean towards the evening hours (RQ5). In the Bronx, more of them happen at spots that already had serious crashes before (RQ8).
# 4. **It is not getting worse because of the buildings.** Crashes did not rise with housing completions over the years (RQ2), and the year after a building opened was slightly safer than the year before (RQ11). Family buildings are on calmer blocks (RQ9). Crashes in high-growth areas are frequent but less often deadly (RQ10).
#
# ### So what? Three recommendations for NYC
# 1. **Link the housing pipeline to the street-safety pipeline.** When HPD finances a building in one of our 15 priority ZIPs (RQ12), DOT should review the surrounding streets *before* residents move in. These 15 ZIPs hold a third of all new affordable units.
# 2. **Fix known spots first.** In the Bronx, repeat-danger locations near new homes are a list DOT already has (RQ8). Local-street tools are cheap and fast (RQ6).
# 3. **Target the evening.** Speed enforcement, signal timing and lighting around residential blocks in the evening hours match when crashes near homes happen (RQ5).
#
# ### Honest limitations
# - **Association, not cause.** Dense, busy neighbourhoods get both more housing and more crashes. We did not measure density, traffic volume or population, so we cannot say housing causes crashes or the reverse.
# - **Only serious crashes.** SIRTA covers crashes with a severe injury or death, so we describe dangerous streets, not all traffic. Without traffic or population data we cannot compute rates *per person* or *per car*.
# - **Missing locations.** Missing crash ZIPs were filled in two steps: from coordinates (92% accurate in our test) and, for crashes without coordinates, from the street and precinct (73% accurate). About 3% of crashes still have no ZIP and appear only in borough results. Coordinate coverage changes by year, which we corrected for in RQ11.
# - **Fatal crashes have no published location after 2022.** Distance-based results (RQ5, RQ6, RQ8, RQ9, RQ11) therefore describe mainly severe-injury crashes. ZIP-level and borough-level results include all fatal crashes.
# - **Confidential homes.** 1,949 small confidential buildings have no address. They are in borough totals but not in ZIP or distance results.
# - **Our choices.** The 250 m radius, the 25% hotspot cut-off and the equal weights of the priority score are choices. We tested the radius (150 m and 500 m give the same conclusions), and the website lets users change the filters.
# - **Preservation is not new residents.** Preserved units (52% of the total) keep existing tenants in place. One project (Co-op City, 15,507 units) is large enough to move some totals, which we point out wherever it matters.
# - **Snapshot.** We used the data as published on 9 October 2026. Both datasets are updated regularly, so later downloads may differ slightly.

# %% [markdown]
# ---
# # 13. Team contributions *(M6)*
#
# | Member | Research questions | Cleaning & integration | Website | Documentation |
# |---|---|---|---|---|
# | M1: Lead & Integration | RQ1, RQ2 | Extract (2), integration (8), post-integration cleaning (9) | Data loading for the app | GitHub repository |
# | M2: Housing data | RQ3, RQ4 | Housing EDA (3), housing cleaning (5) | Housing filters | Housing markdown cells |
# | M3: Transport data | RQ5, RQ6 | Crash EDA (4), crash cleaning and ZIP imputation (6) | Crash filters | Crash markdown cells |
# | M4: Website logic | RQ7, RQ8 | Load step (11) | Callbacks, search parser, Generate Report button | Website section of README |
# | M5: Website visuals & deployment | RQ9, RQ10 | Chart style and colours | Layout, charts, map, deployment on Render | Deployment guide |
# | M6: Story & documentation | RQ11, RQ12 | Cleaning verification (7) | Story tab | Story (12), README, prompts log (14), final check |
#
# *Every member reviewed the full notebook and can explain each step.*

# %% [markdown]
# ---
# # 14. Prompts log *(M6)*
#
# The project rules ask us to include all prompts used. We used **Claude (Anthropic)** as an assistant for planning, dataset selection, code drafts and explanations. Every result in this notebook comes from the code above, which we ran and checked ourselves.
#
# The full log, with every prompt word for word and what we used the answer for, is in [`docs/prompts_log.md`](docs/prompts_log.md). The prompts were:
#
# | # | Date | Prompt (summary; full text in the log) | Used for |
# |---|---|---|---|
# | 1 | 9 Oct 2026 | Shared the project description and data catalog; asked for a careful analysis, a list of what was needed, and a work split for 6 members | Requirements checklist, team roles |
# | 2 | 9 Oct 2026 | Asked the assistant to choose the easiest dataset pair and divide the roles | Dataset choice (H2 + T4) |
# | 3 | 9 Oct 2026 | Shared Lectures 1–4 | Course methods and terms |
# | 4–8 | 9 Oct 2026 | Shared Labs 1–4 one by one | Methods reused (EDA, cleaning, Dash, dashboard design) |
# | 9 | 9 Oct 2026 | Asked the assistant to make all decisions for full marks | Final research questions and plan |
# | 10 | 9 Oct 2026 | Uploaded the two raw CSV files from the API | Notebook and website |
#
# *Members: add any prompt you send to an AI tool to `docs/prompts_log.md` before submission.*
