# %% [markdown]
# ---
# # 10. Research questions
#
# Each team member asks **two** questions, and each question has **one chart** that answers it.
#
# | # | Owner | Question | Chart | Level |
# |---|---|---|---|---|
# | RQ1 | M1 | Do ZIP codes that gained more affordable units also record more serious crashes? | Scatter | A: ZIP |
# | RQ2 | M1 | In each borough, did serious crashes rise or fall alongside housing completions from 2022 to 2025? | Line (small multiples) | C: borough × year |
# | RQ3 | M2 | Are new-construction buildings in more dangerous ZIPs than preservation buildings? | Box plot | A: ZIP |
# | RQ4 | M2 | Do the lowest-income tenants live in more dangerous ZIPs than higher-income tenants? | Bar (ordered bands) | A: ZIP |
# | RQ5 | M3 | Do serious crashes near new affordable housing happen at different times than elsewhere? | Heatmap | B: distance |
# | RQ6 | M3 | Are crashes near new affordable housing more often on local streets than on highways? | 100% stacked bar | B: distance |
# | RQ7 | M4 | Which ZIPs are "double hotspots", in the top 25% for both new housing and serious crashes? | Map | A: ZIP |
# | RQ8 | M4 | Are repeat-danger locations more common near new affordable buildings? | Grouped bar | B: distance |
# | RQ9 | M5 | Do family-sized affordable buildings have fewer serious crashes around them? | Grouped bar | B: distance |
# | RQ10 | M5 | Is a serious crash more likely to be deadly in ZIPs with more or less new affordable housing? | Dot plot | A: ZIP |
# | RQ11 | M6 | Near buildings completed 2023–2025, did serious crashes change in the year after completion? | Dumbbell | B: distance + time |
# | RQ12 | M6 | Which ZIP codes should be first in line for street-safety upgrades? | Ranked bar | A: ZIP |
#
# **A rule for every answer below:** our data shows **associations, not causes**. We write "is associated with" or "goes together with", never "causes" or "leads to". Both datasets are shaped by things we do not measure, such as population density and traffic volume.

# %% [markdown]
# ---
# ## RQ1 *(M1)*: Do ZIP codes that gained more affordable units in 2022–2025 also record more serious crashes?
# **Why it matters:** this is the core link of our project. If the two go together, new residents are being placed where streets are most dangerous.
# **Chart choice:** a scatter plot is the standard form for the **relationship between two numeric variables** (Lecture 4). Each dot is one ZIP. The x-axis is logarithmic because unit counts are very skewed, and ZIPs with no new units are placed at 0. The dark line connects the **median** number of crashes for five groups of ZIPs, from no new housing to the most new housing, so the trend is visible without a regression model.

# %%
rq1 = zip_summary.copy()
rq1["units_axis"] = np.log10(rq1["affordable_units"] + 1)
rq1["housing_group"] = pd.cut(rq1["affordable_units"], [-1, 0, 250, 750, 1500, np.inf],
                              labels=["0", "1–250", "251–750", "751–1,500", "1,500+"])
group_medians = rq1.groupby("housing_group", observed=True).agg(x=("units_axis", "median"), y=("serious_crashes", "median"),
                                                                zips=("zip_code", "size"))
rho_all = stats.spearmanr(rq1["affordable_units"], rq1["serious_crashes"])
with_housing = rq1[rq1["affordable_units"] > 0]
rho_housing = stats.spearmanr(with_housing["affordable_units"], with_housing["serious_crashes"])

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(rq1["units_axis"], rq1["serious_crashes"], s=28, color=BLUE, alpha=0.55, edgecolor=SURFACE, linewidth=0.8)
ax.plot(group_medians["x"], group_medians["y"], color=INK, linewidth=2, marker="o", markersize=6, label="Median per group of ZIPs")
for zip_code, label in [("10475", "10475 Co-op City (preserved)"), ("11207", "11207 East New York"),
                        ("10456", "10456 Morrisania"), ("11101", "11101 Long Island City"),
                        ("11236", "11236 Canarsie (only 2 new units)")]:
    row = rq1[rq1["zip_code"] == zip_code].iloc[0]
    ax.annotate(label, (row["units_axis"], row["serious_crashes"]), xytext=(6, 6), textcoords="offset points",
                fontsize=8.5, color=INK_SOFT)
ax.set_xticks([0, 1, 2, 3, 4], ["0", "10", "100", "1,000", "10,000"])
ax.grid(axis="both")
ax.legend(loc="upper right")
finish_chart(ax, f"More new affordable units, more serious crashes (Spearman ρ = {rho_all.statistic:.2f})",
             "Affordable units completed 2022–2025 (log scale)", "Serious crashes 2022–2025")
plt.show()
print(f"Spearman rho, all {len(rq1)} ZIPs: {rho_all.statistic:.2f} (p = {rho_all.pvalue:.1e})")
print(f"Spearman rho, only the {len(with_housing)} ZIPs with new units: {rho_housing.statistic:.2f} (p = {rho_housing.pvalue:.1e})")
group_medians.round(1)

# %% [markdown]
# **Answer: yes.** ZIP codes that received more new affordable units in 2022–2025 also recorded more serious crashes. The rank correlation is **ρ = 0.61** across all 185 ZIPs, and it stays clearly positive (**ρ = 0.42**) among only the 133 ZIPs that received new units, so the link is not just "housing vs no housing". The median ZIP with no new units had **16** serious crashes in four years; the median ZIP with more than 1,500 new units had **112**, 7 times more.
#
# **Exceptions worth noticing:** 11236 (Canarsie, Brooklyn) had the most serious crashes in the city (178) but only 2 new affordable units. 10475 (Co-op City) has 15,507 units, all from preserving one existing complex, and only 56 crashes.
#
# **Caution:** this is an association. Both affordable housing and serious crashes are concentrated in dense, busy neighbourhoods, so density and traffic volume probably explain part of the link. We cannot say that new housing causes crashes.

# %% [markdown]
# ---
# ## RQ2 *(M1)*: In each borough, did serious crashes rise or fall alongside housing completions from 2022 to 2025?
# **Why it matters:** RQ1 compares places. RQ2 compares **years**: if crashes rose where housing grew, that would be a warning sign for growing neighbourhoods.
# **Chart choice:** a line chart is the form for **change over time**. The two measures have very different sizes (thousands of units, hundreds of crashes), and a chart with two y-axes would invent a relationship. So we **index both to 2022 = 100** on one shared axis, and draw one small panel per borough (small multiples) with only 2 lines each. Lecture 4 recommends at most 4–5 lines per chart.

# %%
rq2 = borough_year.copy()
for measure in ["affordable_units", "serious_crashes"]:
    base_2022 = rq2[rq2["year"] == 2022].set_index("borough")[measure]
    rq2[f"{measure}_index"] = 100 * rq2[measure] / rq2["borough"].map(base_2022)

fig, axes = plt.subplots(1, 5, figsize=(15, 3.8), sharey=True)
for ax, borough in zip(axes, BOROUGH_ORDER):
    data = rq2[rq2["borough"] == borough].sort_values("year")
    ax.axhline(100, color="#c3c2b7", linewidth=1)
    ax.plot(data["year"], data["affordable_units_index"], color=BLUE, linewidth=2, marker="o", markersize=5)
    ax.plot(data["year"], data["serious_crashes_index"], color=ORANGE, linewidth=2, marker="o", markersize=5)
    ax.set_xticks(WINDOW_YEARS, ["2022", "23", "24", "25"])
    ax.set_title(borough, fontsize=11)
    ax.text(2025.1, data["affordable_units_index"].iloc[-1], f"{data['affordable_units_index'].iloc[-1]:.0f}",
            color=BLUE, fontsize=8.5, va="center")
    ax.text(2025.1, data["serious_crashes_index"].iloc[-1], f"{data['serious_crashes_index'].iloc[-1]:.0f}",
            color=ORANGE, fontsize=8.5, va="center")
axes[0].set_ylabel("Index (2022 = 100)")
axes[0].plot([], [], color=BLUE, linewidth=2, label="Affordable units completed")
axes[0].plot([], [], color=ORANGE, linewidth=2, label="Serious crashes")
fig.legend(loc="upper right", ncol=2, frameon=False, bbox_to_anchor=(0.99, 1.06))
fig.suptitle("Housing completions swing from year to year; serious crashes stay almost flat",
             x=0.01, ha="left", fontweight="bold", y=1.06)
finish_chart(axes[-1], "Staten Island", None, None)
axes[-1].set_title("Staten Island", fontsize=11)
plt.show()
rq2.pivot(index="borough", columns="year", values=["affordable_units", "serious_crashes"])

# %% [markdown]
# **Answer: no clear year-to-year link.** Serious crashes stayed close to their 2022 level in every borough (index between 90 and 119). Housing completions jumped up and down (index from 14 to 221), because one large project finishing can double a borough's count in a single year. In no borough do the two lines move together. The only clear crash increase is in **Queens (+19% by 2025)**. Queens' housing completions jumped too, but only in 2025, after crashes had already risen in 2023–2024, so the timing does not suggest that new housing drove the increase.
#
# **What it means:** the link found in RQ1 is about **places** (the same dense neighbourhoods get both), not about **years**.
#
# **Caution:** four years is a short time series. Staten Island's housing numbers are very small (386 units in 2022, 54 in 2025), so its index swings strongly.

# %% [markdown]
# ---
# ## RQ3 *(M2)*: Are new-construction buildings located in more dangerous ZIPs than preservation buildings?
# **Why it matters:** in a **new-construction** building, every household is new to the area. In a **preservation** project the residents already live there; the city only keeps their rents affordable. If new construction goes to more dangerous ZIPs, the city is moving families *into* danger.
# **Chart choice:** a box plot compares **distributions** between groups (Lecture 4). We add the individual buildings as faint dots, because a box alone can hide the shape (Lecture 4).

# %%
rq3 = housing_window.dropna(subset=["zip_code"]).copy()
crashes_per_year_by_zip = zip_summary.set_index("zip_code")["serious_crashes"] / len(WINDOW_YEARS)
rq3["zip_crashes_per_year"] = rq3["zip_code"].map(crashes_per_year_by_zip)
type_order = ["New Construction", "Preservation"]

fig, ax = plt.subplots(figsize=(9, 4.5))
sns.stripplot(data=rq3, x="zip_crashes_per_year", y="construction_type", order=type_order, color=GRAY,
              size=2, alpha=0.35, jitter=0.25, ax=ax)
sns.boxplot(data=rq3, x="zip_crashes_per_year", y="construction_type", order=type_order, width=0.45,
            showfliers=False, boxprops=dict(facecolor="none", edgecolor=INK), medianprops=dict(color=BLUE, linewidth=3),
            whiskerprops=dict(color=INK), capprops=dict(color=INK), ax=ax)
medians_rq3 = rq3.groupby("construction_type")["zip_crashes_per_year"].median()
for i, building_type in enumerate(type_order):
    ax.text(medians_rq3[building_type], i - 0.3, f"median {medians_rq3[building_type]:.1f}", color=BLUE,
            ha="center", fontsize=9, fontweight="bold")
ax.grid(axis="x", visible=True)
ax.grid(axis="y", visible=False)
finish_chart(ax, "New buildings sit in ZIPs with more serious crashes than preserved buildings",
             "Serious crashes per year in the building's ZIP (2022–2025 average)", "")
plt.show()
mann_whitney = stats.mannwhitneyu(rq3.loc[rq3["construction_type"] == "New Construction", "zip_crashes_per_year"],
                                  rq3.loc[rq3["construction_type"] == "Preservation", "zip_crashes_per_year"])
print(rq3.groupby("construction_type").agg(buildings=("building_id", "size"), units=("affordable_units", "sum"),
                                           median=("zip_crashes_per_year", "median"),
                                           mean=("zip_crashes_per_year", "mean")).round(1))
print(f"Mann-Whitney U test p-value: {mann_whitney.pvalue:.1e}")

# %% [markdown]
# **Answer: yes.** The median new-construction building is in a ZIP with **26.8** serious crashes per year, against **21.0** for preservation buildings, which is 28% more. The difference is very unlikely to be chance (Mann-Whitney U test, p < 0.001). We use this test because it compares two groups **without assuming a normal distribution**. The gap also appears **inside every large borough** (Bronx 30.2 vs 23.5, Brooklyn 26.0 vs 23.2, Manhattan 21.8 vs 12.8, Queens 24.0 vs 11.0), so it is not only because new buildings are in a different borough.
#
# **What it means:** the buildings where every household is *new to the area* are the ones in the more dangerous ZIPs, and new residents do not yet know which crossings are dangerous.
#
# **Caution:** new construction needs empty land, which is more common along wide, busy corridors. The type of street may explain part of the link.

# %% [markdown]
# ---
# ## RQ4 *(M2)*: Do the lowest-income tenants live in more dangerous ZIPs than higher-income tenants?
# **Why it matters:** this is an **equity** question. Low-income households are less likely to own a car and more likely to walk, so dangerous streets hurt them most.
# **Method:** for every affordable unit completed in 2022–2025 we look up the serious crashes per year in its ZIP. Then we take the average **per unit**, separately for each income band. A band with many units in dangerous ZIPs gets a high value. The data comes from the long (tidy) income table built in Section 5.13.
# **Chart choice:** a bar chart compares **magnitudes** across categories. The income bands have a natural order, so the bars use one blue that gets darker with income (an ordinal ramp), and the order is never sorted by value.

# %%
rq4 = housing_income_long[housing_income_long["in_analysis_window"]].dropna(subset=["zip_code"]).copy()
rq4 = rq4[~rq4["income_band"].str.startswith("6.")]                      # superintendent units are not tenants
rq4["zip_crashes_per_year"] = rq4["zip_code"].map(crashes_per_year_by_zip)


def unit_weighted_crashes(df):
    return (df["units"] * df["zip_crashes_per_year"]).sum() / df["units"].sum()


band_exposure = rq4.groupby("income_band").apply(unit_weighted_crashes, include_groups=False).rename("all ZIPs")
band_exposure_no_coop = (rq4[rq4["zip_code"] != "10475"].groupby("income_band")
                         .apply(unit_weighted_crashes, include_groups=False).rename("without Co-op City (10475)"))
band_units = rq4.groupby("income_band")["units"].sum().rename("units")
all_units_average = unit_weighted_crashes(rq4)

fig, ax = plt.subplots(figsize=(10, 4.8))
labels = [band.split(". ", 1)[1].replace(" (", "\n(") for band in band_exposure.index]
bars = ax.bar(labels, band_exposure.values, color=BLUE_RAMP[2:7], width=0.62)
for bar, value, units in zip(bars, band_exposure.values, band_units.values):
    ax.text(bar.get_x() + bar.get_width() / 2, value + 0.4, f"{value:.1f}", ha="center", fontweight="bold")
    ax.text(bar.get_x() + bar.get_width() / 2, 1, f"{units:,.0f}\nunits", ha="center", fontsize=8,
            color="white" if value > 0 else INK)
ax.axhline(all_units_average, color=INK_SOFT, linewidth=1)
ax.text(-0.45, all_units_average + 0.5, f"average of all new affordable units: {all_units_average:.1f}",
        color=INK_SOFT, fontsize=8.5, ha="left")
ax.set_ylim(0, band_exposure.max() * 1.18)
finish_chart(ax, "Serious crashes per year in the ZIP where new affordable units are, by income band",
             "Income band (share of area median income, AMI)", "Serious crashes per year\nin the unit's ZIP (unit average)")
plt.show()
pd.concat([band_units, band_exposure, band_exposure_no_coop], axis=1).round(1)

# %% [markdown]
# **Answer: partly yes, but it is not a straight line.** Extremely-low-income units (for households earning up to 30% of the area median) are in ZIPs with **24.4** serious crashes per year on average, **10% above** the average for all new affordable units (22.2).
# - Very-low-income units look the safest (19.5), but that is caused by **one project**: Co-op City (10475) holds 38% of all very-low-income units, in a calmer ZIP. Without it, very low (22.8) and low (22.7) are much closer to extremely low.
# - Middle-income units have the highest value (26.1), because many of them were built in busy ZIPs in the Bronx and in Long Island City (11101).
#
# **What it means:** the poorest tenants, who are the most likely to walk, take the bus and not own a car, live in more dangerous ZIPs than the average affordable-housing tenant.
#
# **Caution:** this measures the ZIP, not the block. One very large project can move a band's average, which is why we show the result with and without Co-op City.

# %% [markdown]
# ---
# ## RQ5 *(M3)*: Do serious crashes near new affordable housing happen at different times of the day and week than crashes elsewhere?
# **Why it matters:** if crashes near new homes peak at specific times, such as the school run or the evening return home, DOT can target enforcement and signal timing at those hours.
# **Method:** crashes within 250 m of a building completed in 2022–2025 are "near new housing", all others are "elsewhere". For each group we compute the share of its crashes that fall in each time band × weekday cell, then subtract: **near minus elsewhere**, in percentage points. Crashes with the default time 00:00 are left out (Section 6.4).
# **Chart choice:** a heatmap shows a **grid of values**. Because the values are differences that can be positive or negative, we use a **diverging** scale: orange = more common near new housing, blue = less common, gray = no difference.

# %%
TIME_BANDS = ["Night\n0–5", "Morning peak\n6–9", "Midday\n10–15", "Evening peak\n16–19", "Late evening\n20–23"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
rq5 = located_crashes[~located_crashes["time_unknown"]].copy()
rq5["time_band"] = pd.cut(rq5["hour"], [-1, 5, 9, 15, 19, 23], labels=TIME_BANDS)
rq5["group"] = np.where(rq5["near_new_housing"], "near", "elsewhere")


def time_share(df):
    table = pd.crosstab(df["time_band"], df["weekday"]).reindex(index=TIME_BANDS, columns=WEEKDAYS).fillna(0)
    return 100 * table / table.values.sum()


share_near = time_share(rq5[rq5["group"] == "near"])
share_elsewhere = time_share(rq5[rq5["group"] == "elsewhere"])
difference = share_near - share_elsewhere
limit = np.abs(difference.values).max()

fig, ax = plt.subplots(figsize=(11, 4.8))
sns.heatmap(difference, annot=True, fmt="+.1f", cmap=sns.blend_palette([BLUE, DIVERGING_MID, ORANGE], as_cmap=True),
            vmin=-limit, vmax=limit, linewidths=2, linecolor=SURFACE, ax=ax,
            cbar_kws={"label": "Near new housing minus elsewhere\n(percentage points)"})
ax.grid(False)
ax.set_xlabel("")
ax.set_ylabel("")
ax.set_xticklabels([d[:3] for d in WEEKDAYS], rotation=0)
ax.set_yticklabels(TIME_BANDS, rotation=0)
finish_chart(ax, "When are serious crashes near new affordable housing more common than elsewhere?", None, None)
plt.show()
band_totals = pd.DataFrame({"near new housing (%)": share_near.sum(axis=1), "elsewhere (%)": share_elsewhere.sum(axis=1)})
band_totals["difference (pp)"] = band_totals["near new housing (%)"] - band_totals["elsewhere (%)"]
print("Crashes used:", rq5["group"].value_counts().to_dict())
band_totals.round(1)

# %% [markdown]
# **Answer: yes, slightly. The evening is more dangerous near new homes and the morning is less.** Near new affordable housing, **21.2%** of serious crashes happen in the late evening (20:00–23:59), compared with **18.1%** elsewhere (+3.0 percentage points). With the evening peak (16:00–19:59, +1.0) that is 4 points more of the crashes in the evening. The **morning peak** (6:00–9:59) is **2.4 points lower** near new housing. The strongest single cells are Saturday evening and Saturday late evening (+0.8 each).
#
# **What it means:** around residential blocks, danger peaks when people come home or go out and when it is dark, not at the morning commute. The matching tools are evening speed enforcement and better street lighting.
#
# **Caution:** the differences are small (at most 3 points). The 204 crashes with an unknown time (00:00) were left out. Fatal crashes after 2022 have no coordinates (Section 4.7), so this result describes mainly severe-injury crashes.

# %% [markdown]
# ---
# ## RQ6 *(M3)*: Are serious crashes near new affordable housing more often on local streets than on highways?
# **Why it matters:** local streets can be redesigned quickly (speed humps, daylighting, bike lanes, signal timing). Highways are much harder to change. If the danger near new homes is on local streets, the city has cheap, fast tools to fix it.
# **Method:** DOT gives every highway crash a *highway reference marker*. A crash without one happened on a local street.
# **Chart choice:** a **100% stacked bar** shows a part-to-whole split for each group. We use horizontal bars because the group names are long.

# %%
rq6 = located_crashes.copy()
rq6["group"] = np.where(rq6["near_new_housing"], "near new housing", "elsewhere")
highway_share = rq6.groupby(["borough", "group"])["on_highway"].mean().unstack()
highway_share.loc["All NYC"] = rq6.groupby("group")["on_highway"].mean()
row_order = [(b, g) for b in ["All NYC"] + BOROUGH_ORDER for g in ["near new housing", "elsewhere"]]
values = [highway_share.loc[b, g] * 100 for b, g in row_order]

fig, ax = plt.subplots(figsize=(10, 6.2))
y_positions = []
y = 0
for i, (borough, group) in enumerate(row_order):
    y_positions.append(y)
    y += 1 if group == "near new housing" else 1.6
y_positions = np.array(y_positions)
local = 100 - np.array(values)
ax.barh(y_positions, local, color=[BLUE if g == "near new housing" else "#86b6ef" for _, g in row_order], height=0.8,
        label="Local street")
ax.barh(y_positions, values, left=local, color=GRAY, height=0.8, label="Highway")
for yp, value in zip(y_positions, values):
    ax.text(101, yp, f"{value:.0f}% highway", va="center", fontsize=8.5, color=INK_SOFT)
ax.set_yticks(y_positions, [f"{b} – {g}" for b, g in row_order])
ax.invert_yaxis()
ax.set_xlim(0, 118)
ax.set_xticks(range(0, 101, 25))
ax.xaxis.set_major_formatter(mticker.PercentFormatter())
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.legend(loc="lower right", ncol=2, bbox_to_anchor=(1, -0.16))
finish_chart(ax, "Near new affordable housing, serious crashes are almost all on local streets", "Share of serious crashes", None)
plt.show()


def share_by_radius(radius, column):
    near = located_crashes["distance_to_new_housing_m"] <= radius
    return located_crashes.loc[near, column].mean() * 100, located_crashes.loc[~near, column].mean() * 100


sensitivity_rq6 = pd.DataFrame([(r, *share_by_radius(r, "on_highway")) for r in [150, 250, 500]],
                               columns=["radius (m)", "highway share near (%)", "highway share elsewhere (%)"]).round(1)
sensitivity_rq6

# %% [markdown]
# **Answer: yes, strongly.** Only **4%** of serious crashes near new affordable housing are on highways, against **10%** elsewhere. In other words, **96% of the danger near new homes is on local streets**. The pattern holds in every borough (for example Queens 4% vs 15%, Bronx 8% vs 15%) and at every radius we tested (150 m: 3% vs 9%; 500 m: 5% vs 13%), so it does not depend on our 250 m choice.
#
# **What it means:** this is good news for policy. Local streets can be fixed quickly and cheaply with tools DOT already uses (speed cameras, raised crossings, daylighting corners, protected bike lanes), while highways are much harder to change.
#
# **Caution:** the highway reference marker is our only highway indicator. A highway crash recorded without a marker would be counted as a local street. Fatal crashes after 2022 have no coordinates, so this result describes mainly severe-injury crashes.

# %% [markdown]
# ---
# ## RQ7 *(M4)*: Which ZIP codes are "double hotspots", in the top 25% for both new affordable units and serious crashes?
# **Why it matters:** these are the places where the city's housing investment and its traffic danger meet. They are natural first candidates for street redesign.
# **Method:** a ZIP is in the top 25% (top quartile) for housing if its new affordable units are above the 75th percentile of all ZIPs, and likewise for crashes. That gives four groups.
# **Chart choice:** a **map** shows spatial patterns. Each circle is a ZIP at its centre point (Section 9.4), sized by new affordable units. Only the double hotspots get the strong orange; the other groups are softer, so the eye goes to the answer first (Lecture 3: pre-attentive processing).

# %%
units_q75 = zip_summary["affordable_units"].quantile(0.75)
crashes_q75 = zip_summary["serious_crashes"].quantile(0.75)
zip_summary["hotspot_group"] = np.select(
    [(zip_summary["affordable_units"] >= units_q75) & (zip_summary["serious_crashes"] >= crashes_q75),
     zip_summary["affordable_units"] >= units_q75,
     zip_summary["serious_crashes"] >= crashes_q75],
    ["Double hotspot", "High housing only", "High crashes only"], default="Neither")
HOTSPOT_COLORS = {"Double hotspot": ORANGE, "High housing only": BLUE, "High crashes only": AQUA, "Neither": "#d9d7cf"}

fig, ax = plt.subplots(figsize=(9, 9))
ax.scatter(located_crashes["longitude"], located_crashes["latitude"], s=1, color="#e6e4dc", linewidths=0, zorder=1)
for group in ["Neither", "High crashes only", "High housing only", "Double hotspot"]:
    data = zip_summary[zip_summary["hotspot_group"] == group]
    ax.scatter(data["longitude"], data["latitude"], s=20 + np.sqrt(data["affordable_units"]) * 4,
               color=HOTSPOT_COLORS[group], edgecolor=SURFACE, linewidth=1, alpha=0.9, zorder=2,
               label=f"{group} ({len(data)})")
top_double = zip_summary[zip_summary["hotspot_group"] == "Double hotspot"].nlargest(6, "serious_crashes")
for _, row in top_double.iterrows():
    ax.annotate(row["zip_code"], (row["longitude"], row["latitude"]), xytext=(7, -3), textcoords="offset points",
                fontsize=8.5, fontweight="bold", color=INK)
ax.set_aspect(1.3)
ax.grid(False)
ax.set_xticks([])
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)
ax.legend(loc="upper left", title="ZIP group (circle size = new affordable units)", title_fontsize=9, markerscale=0.7)
finish_chart(ax, f"Double hotspots: top 25% for new affordable units (≥ {units_q75:,.0f}) and serious crashes (≥ {crashes_q75:.0f})")
plt.show()
print("Thresholds (75th percentile):", round(units_q75), "units |", round(crashes_q75), "serious crashes")
double_hotspots = (zip_summary[zip_summary["hotspot_group"] == "Double hotspot"]
                   .sort_values("serious_crashes", ascending=False)
                   [["zip_code", "borough", "community_district", "affordable_units", "serious_crashes", "deaths"]])
print("Double hotspots per borough:", double_hotspots["borough"].value_counts().to_dict())
print("Share of all new affordable units (ZIP-level) in double hotspots:",
      f"{double_hotspots['affordable_units'].sum() / zip_summary['affordable_units'].sum():.0%}")
double_hotspots.head(10)

# %% [markdown]
# **Answer: 26 ZIP codes are double hotspots**: 11 in the Bronx, 8 in Brooklyn, 4 in Manhattan, 3 in Queens, and none in Staten Island. The map shows two clear clusters: the **South and West Bronx** (10451–10457, 10459–10460, 10467–10468) and **central and eastern Brooklyn** (11206–11208, 11212–11213, 11221, 11226, 11233).
#
# These 26 ZIPs are only **14% of all ZIPs**, but they received **43% of all new affordable units** (with a known ZIP) and **40% of all deeply affordable units**, and they recorded **27% of the city's serious crashes**.
#
# **What it means:** more than 40% of the city's new affordable housing went to a small group of neighbourhoods that also have some of the most dangerous streets. Focusing street-safety work on these 26 ZIPs would protect a large share of new residents.
#
# **Caution:** the 25% cut-off is a choice; a ZIP just below a threshold is not much safer than one just above it. The website lets users explore every ZIP.

# %% [markdown]
# ---
# ## RQ8 *(M4)*: Are repeat-danger locations more common near new affordable buildings?
# **Why it matters:** SIRTA records, for every crash, how many *similar* serious crashes happened at the **same spot** in the previous 3 years. A crash at such a spot is a sign of a **known, unfixed danger**. Those spots are the cheapest wins for the city: the problem is known and the place is known.
# **Method:** share of crashes with `similar_severe_3y > 0`, only for crashes where this value is known (Section 6.11).
# **Chart choice:** a grouped bar chart compares two groups inside each borough. "Near new housing" is the strong blue and "elsewhere" is gray, because the near group is the focus.

# %%
rq8 = located_crashes[located_crashes["at_repeat_location"].notna()].copy()
rq8["at_repeat_location"] = rq8["at_repeat_location"].astype(bool)
repeat_share = rq8.groupby(["borough", "near_new_housing"])["at_repeat_location"].mean().unstack() * 100
repeat_share.loc["All NYC"] = rq8.groupby("near_new_housing")["at_repeat_location"].mean() * 100
repeat_share = repeat_share.reindex(["All NYC"] + BOROUGH_ORDER[:4])   # Staten Island: only 13 crashes near new housing

fig, ax = plt.subplots(figsize=(10, 4.8))
x = np.arange(len(repeat_share))
ax.bar(x - 0.2, repeat_share[True], width=0.38, color=BLUE, label="Within 250 m of new affordable housing")
ax.bar(x + 0.2, repeat_share[False], width=0.38, color=GRAY, label="Elsewhere")
for xi, (near_value, far_value) in enumerate(zip(repeat_share[True], repeat_share[False])):
    ax.text(xi - 0.2, near_value + 0.2, f"{near_value:.1f}%", ha="center", fontsize=8.5, color=INK)
    ax.text(xi + 0.2, far_value + 0.2, f"{far_value:.1f}%", ha="center", fontsize=8.5, color=INK_SOFT)
ax.set_xticks(x, repeat_share.index)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.set_ylim(0, repeat_share.max().max() * 1.25)
ax.legend(loc="upper right")
finish_chart(ax, "Share of serious crashes at a spot that already had a similar serious crash in the past 3 years",
             None, "Crashes at repeat-danger spots")
plt.show()
sensitivity_rq8 = pd.DataFrame([(r, *share_by_radius(r, "at_repeat_location")) for r in [150, 250, 500]],
                               columns=["radius (m)", "repeat share near (%)", "repeat share elsewhere (%)"]).round(1)
print("Crashes used:", len(rq8))
sensitivity_rq8

# %% [markdown]
# **Answer: across the city, yes, but it depends strongly on the borough.** Citywide, **7.8%** of serious crashes near new affordable housing happened at a spot that already had a similar serious crash in the previous three years, against **6.5%** elsewhere. The result is the same at 150 m (8.6% vs 6.6%) and 500 m (7.8% vs 5.6%).
#
# But the gap comes mainly from the **Bronx (11.2% vs 8.9%)** and Manhattan (8.5% vs 7.6%). In **Brooklyn and Queens it is the other way round** (5.3% vs 5.8%; 5.3% vs 6.2%). Part of the citywide gap exists only because many "near" crashes are in the Bronx, where repeat spots are common in general. A citywide average can hide opposite patterns inside the groups, so we always check by borough.
#
# **What it means:** in the Bronx, new affordable homes are being built next to danger spots that were **already known**. These are the cheapest places to act, because DOT already knows where the problem is.
#
# **Caution:** Staten Island is not shown (only 13 crashes there were near new housing). The "similar crash" field is missing for 1,393 crashes, which we left out instead of counting them as zero. Fatal crashes after 2022 have no coordinates, so this result describes mainly severe-injury crashes.

# %% [markdown]
# ---
# ## RQ9 *(M5)*: Do buildings where most affordable apartments are family-sized (2+ bedrooms) have fewer serious crashes around them?
# **Why it matters:** family apartments mean children, who walk to school and play outside. If family buildings are on calmer streets, that is good news. If not, they are the first place to add school-zone safety.
# **Method:** for every building completed in 2022–2025 we count the serious crashes within 250 m (2022–2025). We compare three groups: under 25%, 25–50%, and over 50% of the building's affordable units with 2+ bedrooms. We compare **inside each borough**, because boroughs differ a lot in density (Manhattan has far more crashes per block than Staten Island).
# **Chart choice:** grouped bars by borough. The three groups are ordered, so they use three steps of one blue (light = few family units, dark = mostly family units).

# %%
rq9 = new_buildings.dropna(subset=["family_share"]).copy()
FAMILY_GROUPS = ["Under 25% family-sized", "25–50% family-sized", "Over 50% family-sized"]
rq9["family_group"] = pd.cut(rq9["family_share"], [-0.01, 0.25, 0.5, 1.0], labels=FAMILY_GROUPS)
family_means = rq9.groupby(["borough", "family_group"], observed=False)["crashes_within_250m"].mean().unstack()
family_means.loc["All NYC"] = rq9.groupby("family_group", observed=False)["crashes_within_250m"].mean()
family_counts = rq9.groupby(["borough", "family_group"], observed=False).size().unstack()
family_means = family_means.reindex(["All NYC"] + BOROUGH_ORDER[:4])   # Staten Island: only 9 new buildings

fig, ax = plt.subplots(figsize=(11, 4.8))
x = np.arange(len(family_means))
for offset, group, color in zip([-0.27, 0, 0.27], FAMILY_GROUPS, [BLUE_RAMP[1], BLUE_RAMP[3], BLUE_RAMP[5]]):
    ax.bar(x + offset, family_means[group], width=0.26, color=color, label=group)
    for xi, value in zip(x, family_means[group]):
        if pd.notna(value):
            ax.text(xi + offset, value + 0.12, f"{value:.1f}", ha="center", fontsize=8, color=INK_SOFT)
ax.set_xticks(x, family_means.index)
ax.legend(loc="upper right", ncol=3, bbox_to_anchor=(1, 1.02))
ax.set_ylim(0, family_means.max().max() * 1.25)
finish_chart(ax, "Buildings with mostly family-sized apartments have fewer serious crashes nearby, in every large borough",
             None, "Average serious crashes within 250 m\n(2022–2025, per building)")
plt.show()
print("Buildings per group:")
family_counts

# %% [markdown]
# **Answer: yes.** Buildings where more than half of the affordable apartments have 2+ bedrooms had on average **5.1** serious crashes within 250 m in 2022–2025, against **6.1** for buildings with mostly studios and 1-bedrooms, 16% fewer. The pattern holds **inside each of the four large boroughs** (Bronx 5.6 vs 6.9, Brooklyn 5.0 vs 5.5, Manhattan 7.0 vs 8.7, Queens 2.3 vs 3.3), so it does not come from family buildings being in a calmer borough.
#
# **What it means:** good news. The buildings with the most children are, on average, on calmer blocks. But "calmer" still means about 5 serious crashes within a 3-minute walk in four years, so school-zone safety still matters.
#
# **Caution:** family buildings are often lower-rise buildings on side streets. The type of street, not the size of the apartments, probably explains most of the difference. Staten Island is not shown (only 9 new buildings). The counts include only crashes with coordinates, which leaves out fatal crashes after 2022.

# %% [markdown]
# ---
# ## RQ10 *(M5)*: Is a serious crash more likely to be deadly in ZIPs with more new affordable housing, or with less?
# **Why it matters:** the number of crashes shows how *often* people get hurt. The share of crashes that kill someone shows how *severe* crashes are. Deadly crashes are linked to speed, and wide fast roads are common at the edge of the city, where less housing is built.
# **Method:** we split ZIPs into three groups: no new affordable units, lower growth (below the median of ZIPs with new units) and higher growth (above it). For each group we compute **deaths per 100 serious crashes**, a rate rather than a count. A chi-square test checks whether the share of fatal crashes really differs between the groups.
# **Chart choice:** a dot plot shows a rate per group without implying a "total". Each row is a borough, and each dot is a group.

# %%
median_growth = zip_summary.loc[zip_summary["affordable_units"] > 0, "affordable_units"].median()
zip_summary["growth_group"] = np.select(
    [zip_summary["affordable_units"] == 0, zip_summary["affordable_units"] < median_growth],
    ["No new affordable units", "Lower growth"], default="Higher growth")
GROWTH_ORDER = ["No new affordable units", "Lower growth", "Higher growth"]
GROWTH_COLORS = {"No new affordable units": GRAY, "Lower growth": "#86b6ef", "Higher growth": BLUE}

rq10 = zip_summary.groupby(["borough", "growth_group"])[["serious_crashes", "deaths", "fatal_crashes"]].sum()
rq10_all = zip_summary.groupby("growth_group")[["serious_crashes", "deaths", "fatal_crashes"]].sum()
rq10_all.index = pd.MultiIndex.from_product([["All NYC"], rq10_all.index], names=["borough", "growth_group"])
rq10 = pd.concat([rq10_all, rq10])
rq10["deaths_per_100"] = 100 * rq10["deaths"] / rq10["serious_crashes"]

fig, ax = plt.subplots(figsize=(10, 4.8))
rows = ["All NYC"] + BOROUGH_ORDER
for group in GROWTH_ORDER:
    data = rq10.xs(group, level="growth_group").reindex(rows)
    sizes = np.where(data["serious_crashes"] >= 100, 80, 30)
    ax.scatter(data["deaths_per_100"], np.arange(len(rows)), s=sizes, color=GROWTH_COLORS[group],
               edgecolor=SURFACE, linewidth=1, zorder=3, label=group)
for i, borough in enumerate(rows):
    row_values = rq10.loc[borough, "deaths_per_100"]
    ax.plot([row_values.min(), row_values.max()], [i, i], color="#c3c2b7", linewidth=1, zorder=1)
ax.set_yticks(np.arange(len(rows)), rows)
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.legend(loc="upper center", title="ZIP group", title_fontsize=9, ncol=3, bbox_to_anchor=(0.5, -0.16))
finish_chart(ax, "Deaths per 100 serious crashes, by how much new affordable housing the ZIP received",
             "Deaths per 100 serious crashes (small dots: fewer than 100 crashes)", None)
plt.show()
contingency = rq10_all.assign(non_fatal=lambda d: d["serious_crashes"] - d["fatal_crashes"])[["fatal_crashes", "non_fatal"]]
chi2 = stats.chi2_contingency(contingency.to_numpy())
print(f"Median new units among ZIPs with new housing: {median_growth:,.0f}")
print(f"Chi-square test (fatal vs non-fatal crashes across the 3 groups): p = {chi2.pvalue:.3f}")

# Robustness check: the same rates without the ZIPs filled from street names (Section 6.9)
crash_growth = crashes_window.dropna(subset=["zip_code"]).assign(
    growth_group=lambda d: d["zip_code"].map(zip_summary.set_index("zip_code")["growth_group"]))


def deaths_per_100(rows):
    return 100 * rows["fatalities"].sum() / len(rows)


robustness_rq10 = pd.DataFrame({
    "all ZIPs (main result)": crash_growth.groupby("growth_group").apply(deaths_per_100, include_groups=False),
    "without street-imputed ZIPs": crash_growth[crash_growth["zip_source"] != "imputed (street)"]
                                   .groupby("growth_group").apply(deaths_per_100, include_groups=False),
}).reindex(GROWTH_ORDER).round(1)
print("\nRobustness check, deaths per 100 serious crashes:")
print(robustness_rq10)
rq10.round(1)

# %% [markdown]
# **Answer: crashes in the ZIPs with the most new affordable housing are the least deadly.** Citywide, there were **6.9 deaths per 100 serious crashes** in higher-growth ZIPs, against **8.9** in lower-growth ZIPs and **9.0** in ZIPs with no new affordable units. The chi-square test (p = 0.002) shows the difference is very unlikely to be chance. Higher-growth ZIPs have the lowest rate in four of the five boroughs; **Manhattan is the exception**.
#
# **Robustness check:** without the ZIPs filled from street names (Section 6.9), higher-growth ZIPs still have the lowest rate (5.4 vs 7.1 and 5.2). But the rate for ZIPs with **no** new housing falls from 9.0 to 5.2, because most of their missing deaths come back only through that step. Leaving the fatal crashes without a ZIP out would have hidden almost half of the deaths in these areas. This is a clear example of why our cleaning decisions matter.
#
# **What it means:** together with RQ1 the picture is: high-growth ZIPs have **more** serious crashes, but each crash is **less often deadly**. One possible explanation, which we did not test, is **speed**: crowded streets are slower, while the outer neighbourhoods have wider, faster roads. It is not explained by highways: only 7% of crashes in lower-growth ZIPs were on highways.
#
# **Caution:** Staten Island and the "no new housing" groups have few crashes (small dots), so their values are less stable.

# %% [markdown]
# ---
# ## RQ11 *(M6)*: Near buildings completed in 2023–2025, were there fewer or more serious crashes in the 12 months after completion than in the 12 months before?
# **Why it matters:** new buildings bring new residents, deliveries and construction traffic, and sometimes street improvements. Before/after comparisons are how the city evaluates street projects too.
# **Method:**
# 1. We take buildings completed between January 2023 and March 2025, so both 12-month windows lie inside the crash data (January 2022 – March 2026).
# 2. For each building we count serious crashes within 250 m in the 12 months **before** and **after** its completion date.
# 3. **A trap we had to avoid:** the share of crashes that have coordinates changes from year to year (66% in 2024 vs 88% in 2025, Section 4.7). A raw before/after count would partly measure *data quality*, not safety. So we **adjust the "after" count by the citywide change**: if the city as a whole had 4% fewer located crashes in the after-period, we scale the after-count up by the same 4%. What remains is the *local* change around the building, not affected by citywide ups and downs or by how many crashes have coordinates.
#
# **Chart choice:** a **dumbbell chart** is the standard form for **before → after per group**: gray dot = before, blue dot = after, connected by a line.

# %%
all_located = crashes.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)   # includes Jan–Mar 2026
all_located_tree = BallTree(to_radians(all_located), metric="haversine")
crash_dates = all_located["crash_date"].to_numpy()
sorted_dates = np.sort(crash_dates)
ONE_YEAR = pd.Timedelta(days=365)

rq11 = new_buildings[new_buildings["building_completion_date"].between("2023-01-01", "2025-03-31")].copy()
nearby = all_located_tree.query_radius(to_radians(rq11), r=NEAR_RADIUS_M / EARTH_RADIUS_M)


def count_in_window(dates, start, end):
    """Number of dates with start <= date < end."""
    return int(((dates >= np.datetime64(start)) & (dates < np.datetime64(end))).sum())


def city_count(start, end):
    return int(np.searchsorted(sorted_dates, np.datetime64(end)) - np.searchsorted(sorted_dates, np.datetime64(start)))


records = []
for completion, crash_index in zip(rq11["building_completion_date"], nearby):
    dates_near = crash_dates[crash_index]
    records.append({
        "near_before": count_in_window(dates_near, completion - ONE_YEAR, completion),
        "near_after": count_in_window(dates_near, completion, completion + ONE_YEAR),
        "city_before": city_count(completion - ONE_YEAR, completion),
        "city_after": city_count(completion, completion + ONE_YEAR),
    })
rq11 = pd.concat([rq11.reset_index(drop=True), pd.DataFrame(records)], axis=1)

rq11_borough = rq11.groupby("borough")[["near_before", "near_after", "city_before", "city_after"]].sum()
rq11_borough.loc["All NYC"] = rq11[["near_before", "near_after", "city_before", "city_after"]].sum()
rq11_borough["buildings"] = rq11.groupby("borough").size()
rq11_borough.loc["All NYC", "buildings"] = len(rq11)
# crashes per building per year; the "after" count is scaled by city_before / city_after,
# so a citywide change (or a change in how many crashes have coordinates) cannot look like a local change
rq11_borough["before_per_building"] = rq11_borough["near_before"] / rq11_borough["buildings"]
rq11_borough["after_per_building_adjusted"] = (rq11_borough["near_after"] * rq11_borough["city_before"]
                                               / rq11_borough["city_after"] / rq11_borough["buildings"])
rq11_borough["change_%"] = 100 * (rq11_borough["after_per_building_adjusted"] / rq11_borough["before_per_building"] - 1)
rq11_borough = rq11_borough.reindex(["All NYC"] + BOROUGH_ORDER)

fig, ax = plt.subplots(figsize=(10, 4.6))
for i, (borough, row) in enumerate(rq11_borough.iterrows()):
    before, after = row["before_per_building"], row["after_per_building_adjusted"]
    ax.plot([before, after], [i, i], color="#c3c2b7", linewidth=2.5, zorder=1)
    ax.scatter(before, i, s=90, color=GRAY, zorder=2, edgecolor=SURFACE, linewidth=1)
    ax.scatter(after, i, s=90, color=BLUE, zorder=3, edgecolor=SURFACE, linewidth=1)
    ax.text(max(before, after) + 0.08, i,
            f"{row['change_%']:+.0f}%  ({int(row['buildings'])} buildings)", va="center", fontsize=8.5, color=INK_SOFT)
ax.scatter([], [], s=90, color=GRAY, label="12 months before completion")
ax.scatter([], [], s=90, color=BLUE, label="12 months after completion")
ax.set_yticks(range(len(rq11_borough)), rq11_borough.index)
ax.invert_yaxis()
ax.set_xlim(0, rq11_borough[["before_per_building", "after_per_building_adjusted"]].max().max() * 1.5)
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.16))
finish_chart(ax, "Serious crashes within 250 m of a new building, before and after it opened",
             "Serious crashes within 250 m per building per year (after-period adjusted for citywide change)", None)
plt.show()
rq11_borough.round(2)

# %% [markdown]
# **Answer: overall, slightly fewer.** Around the 1,268 buildings completed between January 2023 and March 2025, there were **1.43** serious crashes per building per year within 250 m before completion, and **1.38** after, a **3% decrease** after adjusting for citywide changes. Brooklyn and Queens fell by about 10% and the Bronx by 4%. **Manhattan is the exception, with a 17% increase** around its 162 new buildings.
#
# **What it means:** we see no sign that completing a building brought more serious crashes to its block, except in Manhattan, where new buildings are often large and the streets around them were already busy. That is worth a closer look by DOT.
#
# **Caution:** this is a simple before/after comparison, not proof of an effect. Serious crashes are rare (about 1–2 per building per year), so changes of a few percent can be random. Staten Island had only 4 buildings. Fatal crashes after 2022 have no coordinates, so the counts are mainly severe-injury crashes.

# %% [markdown]
# ---
# ## RQ12 *(M6)*: Which ZIP codes should be first in line for street-safety upgrades, based on both housing growth and crash risk?
# **Why it matters:** this turns our analysis into a **decision**: a ranked list that DOT and HPD could use together.
# **Method:** a simple, transparent **priority score**, the average of two percentile ranks (Lab 4's "ranking" measure):
# - rank of new affordable units 2022–2025 (how many new residents are affected), and
# - rank of serious crashes 2022–2025 (how dangerous the streets are).
#
# Both ranks run from 0 to 1, so the score runs from 0 to 1. Using **ranks** instead of raw numbers stops one huge project (Co-op City) or one extreme ZIP from dominating the list.
# **Chart choice:** a ranked horizontal bar chart. Bars are sorted by score and each bar is labelled with the two numbers behind it, so the ranking can be checked.

# %%
zip_summary["housing_rank"] = zip_summary["affordable_units"].rank(pct=True)
zip_summary["crash_rank"] = zip_summary["serious_crashes"].rank(pct=True)
zip_summary["priority_score"] = ((zip_summary["housing_rank"] + zip_summary["crash_rank"]) / 2).round(3)
top15 = zip_summary.nlargest(15, "priority_score").iloc[::-1]

fig, ax = plt.subplots(figsize=(10, 6.5))
ax.barh([f"{z}  ({cd})" for z, cd in zip(top15["zip_code"], top15["community_district"])],
        top15["priority_score"], color=ORANGE, height=0.68)
for i, (_, row) in enumerate(top15.iterrows()):
    ax.text(row["priority_score"] + 0.005, i, f"{row['affordable_units']:,} units · {row['serious_crashes']} crashes",
            va="center", fontsize=8.5, color=INK_SOFT)
ax.set_xlim(0.8, 1.06)
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
all_double = (top15["hotspot_group"] == "Double hotspot").all()
finish_chart(ax, "Top 15 ZIP codes for street-safety upgrades (priority score)"
             + (": all 15 are double hotspots (RQ7)" if all_double else ""),
             "Priority score = average of housing rank and crash rank (0–1)", None)
plt.show()
top15_table = top15.iloc[::-1][["zip_code", "borough", "community_district", "affordable_units", "serious_crashes",
                                "deaths", "priority_score"]]
print("Top 15 by borough:", top15_table["borough"].value_counts().to_dict())
top15_table

# %% [markdown]
# **Answer:** the 15 ZIPs with the highest priority scores are **all double hotspots** from RQ7: 8 in the Bronx, 5 in Brooklyn, 1 in Queens (11101, Long Island City) and 1 in Manhattan (10029, East Harlem). The top three, **10452** (Highbridge/Concourse), **10453** (University Heights/Fordham) and **10456** (Morrisania), are neighbours in the West and South Bronx. Together, the 15 ZIPs received **31% of all new affordable units** (31,208) and recorded **18% of all serious crashes** (2,026 crashes, 129 deaths) in 2022–2025.
#
# **What it means:** this is our recommendation to the city, a short ranked list where one street-safety programme would protect about a third of the residents of new affordable housing.
#
# **Caution:** the score gives housing and crashes equal weight, and that is a choice. Weighting deaths instead of crashes would move 10467 (17 deaths, the most in the top 15) higher. The website lets users compare the ZIPs themselves.
