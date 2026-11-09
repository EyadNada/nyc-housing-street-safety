"""Plotly chart builders for the website. Every function takes already-filtered data and returns a figure.

Colours are the same as in the notebook, so the same meaning always has the same colour:
blue = housing / near new housing, orange = crashes / double hotspot, aqua = third group, gray = everything else.
"""
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from .data import YEARS, safe_divide

BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#b5b3ab"
LIGHT_BLUE, NEUTRAL = "#86b6ef", "#f0efec"
INK, INK_SOFT, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
HOTSPOT_COLORS = {"Double hotspot": ORANGE, "High housing only": BLUE, "High crashes only": AQUA, "Neither": "#d9d7cf"}
HOTSPOT_ORDER = ["Double hotspot", "High housing only", "High crashes only", "Neither"]
TIME_BANDS = ["Night 0–5", "Morning peak 6–9", "Midday 10–15", "Evening peak 16–19", "Late evening 20–23"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAP_STYLE = os.environ.get("MAP_STYLE", "carto-positron")   # "white-bg" works without internet (for tests)

pio.templates["nyc"] = go.layout.Template(layout=go.Layout(
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=12, color=INK_SOFT),
    title=dict(font=dict(size=15, color=INK), x=0.01, xanchor="left"),
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    xaxis=dict(gridcolor=GRID, linecolor="#c3c2b7", zeroline=False, showgrid=False),
    yaxis=dict(gridcolor=GRID, linecolor="#c3c2b7", zeroline=False),
    hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=12)),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=60, r=20, t=70, b=50),
    colorway=[BLUE, ORANGE, AQUA, GRAY],
))
pio.templates.default = "nyc"


def empty_figure(title, message="No data for this selection. Try more boroughs or years."):
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=13, color=INK_SOFT), x=0.5, y=0.5,
                       xref="paper", yref="paper")
    fig.update_layout(title=title, xaxis=dict(visible=False), yaxis=dict(visible=False), height=380)
    return fig


def map_figure(zips, crash_rows, selected_zip=None):
    """Cross-domain map: where serious crashes concentrate (heat) and how much new housing each ZIP got (circles)."""
    title = "Where new affordable housing meets serious crashes"
    if zips.empty and crash_rows.empty:
        return empty_figure(title)
    fig = go.Figure()
    located = crash_rows.dropna(subset=["latitude", "longitude"])
    if not located.empty:
        fig.add_trace(go.Densitymap(
            lat=located["latitude"], lon=located["longitude"], radius=6, name="Serious crash density (gray)",
            colorscale=[[0, "rgba(82,81,78,0)"], [0.35, "rgba(82,81,78,0.22)"], [1, "rgba(11,11,11,0.45)"]],
            showscale=False, hoverinfo="skip", showlegend=True))
    housing_zips = zips[(zips["affordable_units"] > 0) & zips["latitude"].notna()]
    for group in HOTSPOT_ORDER:
        rows = housing_zips[housing_zips["hotspot_group"] == group]
        if rows.empty:
            continue
        fig.add_trace(go.Scattermap(
            lat=rows["latitude"], lon=rows["longitude"], mode="markers", name=group,
            marker=dict(size=7 + np.sqrt(rows["affordable_units"]) * 0.45, color=HOTSPOT_COLORS[group], opacity=0.85),
            customdata=np.stack([rows["zip_code"], rows["borough"], rows["affordable_units"], rows["serious_crashes"],
                                 rows["deaths"]], axis=-1),
            hovertemplate=("<b>ZIP %{customdata[0]}</b> · %{customdata[1]}<br>"
                           "New affordable units: %{customdata[2]:,}<br>Serious crashes: %{customdata[3]:,}<br>"
                           "Deaths: %{customdata[4]}<br><i>Click for details</i><extra>" + group + "</extra>")))
    center, zoom = dict(lat=40.71, lon=-73.93), 9.5
    if selected_zip is not None:
        chosen = zips[zips["zip_code"] == selected_zip]
        if not chosen.empty and pd.notna(chosen["latitude"].iloc[0]):
            center, zoom = dict(lat=chosen["latitude"].iloc[0], lon=chosen["longitude"].iloc[0]), 12.5
            fig.add_trace(go.Scattermap(lat=chosen["latitude"], lon=chosen["longitude"], mode="markers",
                                        marker=dict(size=34, color="rgba(11,11,11,0.15)"), name=f"ZIP {selected_zip}",
                                        hoverinfo="skip"))
    fig.update_layout(title=title, map=dict(style=MAP_STYLE, center=center, zoom=zoom), height=520,
                      margin=dict(l=0, r=0, t=70, b=0), legend=dict(y=1.0))
    return fig


def scatter_figure(zips):
    """Cross-domain scatter (RQ1): one dot per ZIP, new affordable units vs serious crashes."""
    title = "Each ZIP: new affordable units vs serious crashes"
    if zips.empty:
        return empty_figure(title)
    fig = go.Figure()
    for group in HOTSPOT_ORDER[::-1]:
        rows = zips[zips["hotspot_group"] == group]
        if rows.empty:
            continue
        fig.add_trace(go.Scatter(
            x=rows["affordable_units"] + 1, y=rows["serious_crashes"], mode="markers", name=group,
            marker=dict(size=10, color=HOTSPOT_COLORS[group], line=dict(width=1, color=SURFACE)),
            customdata=np.stack([rows["zip_code"], rows["borough"], rows["community_district"].fillna(""),
                                 rows["affordable_units"], rows["deaths"]], axis=-1),
            hovertemplate=("<b>ZIP %{customdata[0]}</b> · %{customdata[1]} %{customdata[2]}<br>"
                           "New affordable units: %{customdata[3]:,}<br>Serious crashes: %{y}<br>"
                           "Deaths: %{customdata[4]}<extra>" + group + "</extra>")))
    fig.update_xaxes(type="log", title="New affordable units (log scale; 1 = none)", showgrid=True,
                     tickvals=[1, 11, 101, 1001, 10001], ticktext=["0", "10", "100", "1,000", "10,000"])
    fig.update_yaxes(title="Serious crashes", rangemode="tozero")
    fig.update_layout(title=title, height=420, legend=dict(traceorder="reversed"))
    return fig


def trend_figure(by_year, year_from, year_to):
    """Housing completions (bars) and serious crashes (line) per year, in two panels with their own axes."""
    title = "Per year: affordable units completed and serious crashes"
    if by_year[["affordable_units", "serious_crashes"]].sum().sum() == 0:
        return empty_figure(title)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.14,
                        subplot_titles=("Affordable units completed", "Serious crashes"))
    selected = by_year["year"].between(year_from, year_to)
    fig.add_trace(go.Bar(x=by_year["year"], y=by_year["affordable_units"], name="Affordable units",
                         marker_color=np.where(selected, BLUE, "#cde2fb"),
                         hovertemplate="%{x}: %{y:,} units<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=by_year["year"], y=by_year["serious_crashes"], name="Serious crashes",
                             mode="lines+markers", line=dict(color=ORANGE, width=3), marker=dict(size=9),
                             hovertemplate="%{x}: %{y:,} serious crashes<extra></extra>"), row=2, col=1)
    fig.update_yaxes(rangemode="tozero", row=1, col=1)
    fig.update_yaxes(rangemode="tozero", row=2, col=1)
    fig.update_xaxes(tickvals=YEARS, row=2, col=1)
    fig.update_layout(title=title, height=420, showlegend=False)
    fig.update_annotations(font=dict(size=12, color=INK_SOFT), x=0, xanchor="left")
    return fig


def _time_share(rows):
    if rows.empty:
        return pd.DataFrame(0.0, index=TIME_BANDS, columns=WEEKDAYS)
    bands = pd.cut(rows["hour"], [-1, 5, 9, 15, 19, 23], labels=TIME_BANDS)
    table = pd.crosstab(bands, rows["weekday"]).reindex(index=TIME_BANDS, columns=WEEKDAYS).fillna(0)
    return 100 * table / max(table.values.sum(), 1)


def heatmap_figure(crash_rows, mode="difference"):
    """RQ5: time band x weekday. mode = 'near', 'elsewhere' or 'difference' (near minus elsewhere)."""
    title = {"near": "When serious crashes happen within 250 m of new affordable housing",
             "elsewhere": "When serious crashes happen elsewhere",
             "difference": "Near new housing minus elsewhere (percentage points)"}[mode]
    rows = crash_rows[~crash_rows["time_unknown"]].dropna(subset=["near_new_housing"])
    near, elsewhere = rows[rows["near_new_housing"].astype(bool)], rows[~rows["near_new_housing"].astype(bool)]
    if (mode == "near" and near.empty) or (mode == "elsewhere" and elsewhere.empty) or \
       (mode == "difference" and (near.empty or elsewhere.empty)):
        return empty_figure(title)
    if mode == "difference":
        values = (_time_share(near) - _time_share(elsewhere)).astype(float)
        limit = max(float(np.abs(values.to_numpy()).max()), 0.1)
        colorscale, zmin, zmax = [[0, BLUE], [0.5, NEUTRAL], [1, ORANGE]], -limit, limit
        labels = values.map(lambda v: f"{v:+.1f}")
    else:
        values = _time_share(near if mode == "near" else elsewhere).astype(float)
        colorscale, zmin, zmax = [[0, "#f3f8fe"], [1, "#184f95"]], 0, float(values.to_numpy().max())
        labels = values.map(lambda v: f"{v:.1f}%")
    fig = go.Figure(go.Heatmap(
        z=values.to_numpy(), x=[d[:3] for d in WEEKDAYS], y=TIME_BANDS, colorscale=colorscale, zmin=zmin, zmax=zmax,
        text=labels.to_numpy(), texttemplate="%{text}", textfont=dict(size=11), xgap=3, ygap=3,
        hovertemplate="%{y}, %{x}: %{text}<extra></extra>",
        colorbar=dict(title=dict(text="pp" if mode == "difference" else "% of crashes", side="right"), thickness=12)))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(title=title, height=380, margin=dict(l=130, r=20, t=70, b=40))
    return fig


def street_figure(crash_rows):
    """RQ6: share of serious crashes on local streets vs highways, near new housing and elsewhere."""
    title = "Local streets or highways?"
    rows = crash_rows.dropna(subset=["near_new_housing"])
    if rows.empty:
        return empty_figure(title)
    groups = []
    for label, part in [("Within 250 m of new housing", rows[rows["near_new_housing"].astype(bool)]),
                        ("Elsewhere", rows[~rows["near_new_housing"].astype(bool)])]:
        highway = 100 * safe_divide(int(part["on_highway"].sum()), len(part))
        groups.append((label, 100 - highway, highway, len(part)))
    labels = [g[0] for g in groups]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=[g[1] for g in groups], orientation="h", name="Local street",
                         marker_color=[BLUE, LIGHT_BLUE], text=[f"{g[1]:.0f}% local" for g in groups],
                         textposition="inside", insidetextanchor="start",
                         customdata=[g[3] for g in groups],
                         hovertemplate="%{y}<br>Local streets: %{x:.1f}% of %{customdata:,} crashes<extra></extra>"))
    fig.add_trace(go.Bar(y=labels, x=[g[2] for g in groups], orientation="h", name="Highway", marker_color=GRAY,
                         hovertemplate="%{y}<br>Highways: %{x:.1f}%<extra></extra>"))
    fig.update_layout(barmode="stack", title=title, height=260, xaxis=dict(range=[0, 100], ticksuffix="%"),
                      yaxis=dict(autorange="reversed"), bargap=0.35, margin=dict(l=190, r=20, t=70, b=40))
    return fig


def income_figure(income_rows, crash_rows, years_selected):
    """RQ4: average serious crashes per year in the ZIP of each new affordable unit, by income band."""
    title = "Danger around new units, by tenant income band"
    rows = income_rows.dropna(subset=["zip_code"])
    rows = rows[~rows["income_band"].str.startswith("6.")]
    if rows.empty or crash_rows.empty:
        return empty_figure(title)
    per_year = crash_rows.dropna(subset=["zip_code"]).groupby("zip_code").size() / max(years_selected, 1)
    rows = rows.assign(zip_crashes=rows["zip_code"].map(per_year).fillna(0))
    exposure = rows.groupby("income_band").apply(
        lambda g: safe_divide((g["units"] * g["zip_crashes"]).sum(), g["units"].sum()), include_groups=False)
    units = rows.groupby("income_band")["units"].sum()
    labels = [band.split(". ", 1)[1].replace(" (", "<br>(") for band in exposure.index]
    ramp = ["#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"][:len(labels)]
    fig = go.Figure(go.Bar(x=labels, y=exposure.values, marker_color=ramp, customdata=units.values,
                           text=[f"{v:.1f}" for v in exposure.values], textposition="outside",
                           hovertemplate="%{x}<br>%{y:.1f} serious crashes per year in the unit's ZIP"
                                         "<br>%{customdata:,} units<extra></extra>"))
    fig.update_layout(title=title, height=380, xaxis=dict(tickangle=0),
                      yaxis=dict(title="Serious crashes / year in the unit's ZIP",
                                 range=[0, float(exposure.max()) * 1.18]))
    return fig


def ranking_figure(zips, top_n=10):
    """RQ12: ZIPs with the highest priority score (housing rank + crash rank)."""
    title = f"Top {top_n} priority ZIPs for street-safety upgrades"
    rows = zips[(zips["affordable_units"] > 0) & (zips["serious_crashes"] > 0)]
    if rows.empty:
        return empty_figure(title)
    top = rows.nlargest(top_n, "priority_score").iloc[::-1]
    fig = go.Figure(go.Bar(
        y=[f"{z} ({cd})" if isinstance(cd, str) else z for z, cd in zip(top["zip_code"], top["community_district"])],
        x=top["priority_score"], orientation="h",
        marker_color=[ORANGE if g == "Double hotspot" else BLUE for g in top["hotspot_group"]],
        customdata=np.stack([top["zip_code"], top["affordable_units"], top["serious_crashes"], top["deaths"]], axis=-1),
        text=[f"{u:,} units · {c} crashes" for u, c in zip(top["affordable_units"], top["serious_crashes"])],
        textposition="outside", cliponaxis=False,
        hovertemplate=("<b>ZIP %{customdata[0]}</b><br>Priority score: %{x:.3f}<br>New affordable units: "
                       "%{customdata[1]:,}<br>Serious crashes: %{customdata[2]}<br>Deaths: %{customdata[3]}"
                       "<br><i>Click for details</i><extra></extra>")))
    low = max(0, top["priority_score"].min() - 0.05)
    ticks = [round(v, 2) for v in np.arange(np.ceil(low * 20) / 20, 1.0001, 0.05)]
    fig.update_layout(title=title, height=420, xaxis=dict(range=[low, 1.14], title="Priority score (0–1)",
                                                          showgrid=True, tickvals=ticks),
                      margin=dict(l=120, r=20, t=70, b=50))
    return fig


def zip_trend_figure(zip_code, building_rows, crash_rows):
    """Small chart in the ZIP detail panel."""
    units = building_rows.groupby("completion_year")["affordable_units"].sum().reindex(YEARS, fill_value=0)
    crashes = crash_rows.groupby("year").size().reindex(YEARS, fill_value=0)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Affordable units completed", "Serious crashes"),
                        horizontal_spacing=0.15)
    fig.add_trace(go.Bar(x=YEARS, y=units.values, marker_color=BLUE, hovertemplate="%{x}: %{y:,}<extra></extra>"), 1, 1)
    fig.add_trace(go.Bar(x=YEARS, y=crashes.values, marker_color=ORANGE, hovertemplate="%{x}: %{y}<extra></extra>"), 1, 2)
    fig.update_layout(height=230, showlegend=False, margin=dict(l=40, r=10, t=40, b=30))
    fig.update_xaxes(tickvals=YEARS)
    fig.update_annotations(font=dict(size=12, color=INK_SOFT))
    return fig
