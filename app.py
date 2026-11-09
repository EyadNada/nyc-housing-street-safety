"""Homes on Dangerous Streets? Interactive website (Dash).

Run locally:   python app.py            -> http://127.0.0.1:8050
On Render:     gunicorn app:server      (see README.md)

How the Generate Report button works (the key idea of this file):
1. Dropdowns, the year slider and the search box are read as State. Changing them does NOT redraw anything.
2. Clicking "Generate Report" (or pressing Enter in the search box) is the only Input of `apply_report`.
   It combines the dropdowns with the search words and saves the result in one dcc.Store ("applied-filters").
3. Every chart listens to that Store, so all charts update together, only after the button is clicked.
"""
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from dashboard import data, figures
from dashboard.data import BOROUGHS, YEARS, Filters
from dashboard.search import describe, parse_search
from dashboard.story import STORY_MARKDOWN

app = Dash(__name__, title="Homes on Dangerous Streets? | NYC", suppress_callback_exceptions=True)
server = app.server                               # gunicorn on Render uses this Flask server

DEFAULT = Filters()
CONSTRUCTION_OPTIONS = [{"label": "All affordable buildings", "value": "All"},
                        {"label": "New construction only", "value": "New Construction"},
                        {"label": "Preservation only", "value": "Preservation"}]
SEVERITY_OPTIONS = [{"label": "All serious crashes", "value": "All"},
                    {"label": "Fatal crashes only", "value": "Fatal"}]
STREET_OPTIONS = [{"label": "All streets", "value": "All"}, {"label": "Local streets", "value": "Local"},
                  {"label": "Highways", "value": "Highway"}]


EMPTY_DETAIL = [
    html.H3("ZIP details"),
    html.P("Click a ZIP circle on the map, a dot in the scatter plot or a bar in the ranking, "
           "or search for a ZIP code such as 10453.", className="muted"),
    html.Button("Close", id="close-detail", n_clicks=0, className="close-btn", style={"display": "none"}),
]


def control(label, component):
    return html.Div([html.Label(label, className="control-label"), component], className="control")


def kpi_card(card_id, label):
    return html.Div([html.Div("–", id=card_id, className="kpi-value"), html.Div(label, className="kpi-label")],
                    className="kpi-card")


def chart_card(graph_id, extra=None, wide=False):
    children = [extra] if extra is not None else []
    children.append(dcc.Loading(dcc.Graph(id=graph_id, config={"displaylogo": False}), type="dot", color=figures.BLUE))
    return html.Div(children, className="chart-card wide" if wide else "chart-card")


filters_panel = html.Section([
    html.Div([
        control("Borough", dcc.Dropdown(id="borough-dd", options=BOROUGHS, value=DEFAULT.boroughs, multi=True,
                                        placeholder="Choose boroughs")),
        control("Years (building completion / crash date)",
                dcc.RangeSlider(id="year-slider", min=YEARS[0], max=YEARS[-1], step=1, value=[YEARS[0], YEARS[-1]],
                                marks={y: str(y) for y in YEARS}, allowCross=True)),
        control("Housing: construction type", dcc.Dropdown(id="construction-dd", options=CONSTRUCTION_OPTIONS,
                                                           value="All", clearable=False)),
        control("Crashes: severity", dcc.Dropdown(id="severity-dd", options=SEVERITY_OPTIONS, value="All",
                                                  clearable=False)),
        control("Crashes: street type", dcc.Dropdown(id="street-dd", options=STREET_OPTIONS, value="All",
                                                     clearable=False)),
    ], className="controls-row"),
    html.Div([
        dcc.Input(id="search-box", type="text", debounce=False, className="search-box",
                  placeholder='Search, e.g. "Brooklyn 2023 new buildings fatal" or "10453"'),
        html.Button("Generate Report", id="generate-btn", n_clicks=0, className="generate-btn"),
        html.Button("Reset", id="reset-btn", n_clicks=0, className="reset-btn"),
    ], className="search-row"),
    html.Div(id="report-summary", className="report-summary"),
], className="filters-panel")

kpi_row = html.Section([
    kpi_card("kpi-units", "new affordable units"),
    kpi_card("kpi-buildings", "buildings completed"),
    kpi_card("kpi-crashes", "serious crashes"),
    kpi_card("kpi-deaths", "deaths"),
    kpi_card("kpi-near", "of located crashes within 250 m of new housing"),
    kpi_card("kpi-hotspots", "double-hotspot ZIPs"),
], className="kpi-row")

overview_tab = html.Div([
    html.Div([
        chart_card("map-graph", wide=True),
        html.Aside(id="zip-detail", className="zip-detail", children=EMPTY_DETAIL),
    ], className="map-row"),
    html.Div([chart_card("scatter-graph"), chart_card("trend-graph")], className="chart-grid"),
])

explore_tab = html.Div([
    html.Div([
        chart_card("heatmap-graph", extra=dcc.RadioItems(
            id="heatmap-mode", value="difference", inline=True, className="radio",
            options=[{"label": " Difference", "value": "difference"},
                     {"label": " Near new housing", "value": "near"},
                     {"label": " Elsewhere", "value": "elsewhere"}])),
        chart_card("street-graph"),
    ], className="chart-grid"),
    html.Div([chart_card("income-graph"), chart_card("ranking-graph")], className="chart-grid"),
])

app.layout = html.Div([
    html.Header([
        html.Div([
            html.H1("Homes on Dangerous Streets?"),
            html.P("Affordable housing and serious traffic crashes in New York City, 2022–2025"),
        ], className="title-block"),
    ], className="site-header"),
    filters_panel,
    kpi_row,
    dcc.Tabs(id="tabs", value="overview", className="tabs", children=[
        dcc.Tab(label="Overview", value="overview", children=overview_tab, className="tab",
                selected_className="tab--selected"),
        dcc.Tab(label="Explore", value="explore", children=explore_tab, className="tab",
                selected_className="tab--selected"),
        dcc.Tab(label="Story", value="story", className="tab", selected_className="tab--selected",
                children=dcc.Markdown(STORY_MARKDOWN, className="story", link_target="_blank")),
    ]),
    html.Footer("Data: NYC Open Data (HPD Affordable Housing Production by Building; DOT SIRTA). "
                "Associations, not causes. GIU Data Engineering & Visualization, Winter 2026.", className="footer"),
    dcc.Store(id="applied-filters", data=DEFAULT.to_dict()),
    dcc.Store(id="selected-zip", data=None),
], className="page")


# ---------------------------------------------------------------------------
# 1. Generate Report: combine dropdowns + search words into the applied filters
# ---------------------------------------------------------------------------
@app.callback(
    Output("applied-filters", "data"),
    Output("borough-dd", "value"), Output("year-slider", "value"), Output("construction-dd", "value"),
    Output("severity-dd", "value"), Output("street-dd", "value"), Output("search-box", "value"),
    Output("report-summary", "children"),
    Input("generate-btn", "n_clicks"), Input("search-box", "n_submit"), Input("reset-btn", "n_clicks"),
    State("borough-dd", "value"), State("year-slider", "value"), State("construction-dd", "value"),
    State("severity-dd", "value"), State("street-dd", "value"), State("search-box", "value"),
)
def apply_report(_generate, _enter, _reset, boroughs, years, construction, severity, street, search_text):
    if ctx.triggered_id == "reset-btn":
        f, notes, understood = Filters(), [], ""
        search_text = ""
    else:
        f = Filters(boroughs=boroughs or list(BOROUGHS), year_from=min(years), year_to=max(years),
                    construction=construction, severity=severity, street=street)
        found, notes = parse_search(search_text, known_zips=data.ALL_ZIPS)
        for key, value in found.items():               # search words override the matching dropdowns
            setattr(f, key, value)
        if "zip_code" in found and "boroughs" not in found:   # show a searched ZIP inside its own borough
            f.boroughs = [data.ZIP_INFO.set_index("zip_code").loc[found["zip_code"], "borough"]]
        understood = describe(found)
        if f.severity == "Fatal":
            notes.append("Note: the exact locations of fatal crashes are not published after 2022, so the map, "
                         "heatmap and street chart show only 2022 fatal crashes. ZIP and borough numbers include all.")
    summary = [html.Span("Report: ", className="summary-label"), summary_text(f)]
    if understood:
        summary += [html.Span("  ·  Search understood: ", className="summary-label"), understood]
    if notes:
        summary += [html.Div(" ".join(notes), className="summary-note")]
    return (f.to_dict(), f.boroughs, [f.year_from, f.year_to], f.construction, f.severity, f.street,
            search_text, summary)


def summary_text(f):
    boroughs = "all boroughs" if len(f.boroughs) == len(BOROUGHS) else ", ".join(f.boroughs)
    years = str(f.year_from) if f.year_from == f.year_to else f"{f.year_from}–{f.year_to}"
    building = {"All": "all affordable buildings", "New Construction": "new construction",
                "Preservation": "preservation"}[f.construction]
    crash = "fatal crashes" if f.severity == "Fatal" else "all serious crashes"
    street = {"All": "all streets", "Local": "local streets", "Highway": "highways"}[f.street]
    return f"{boroughs} · {years} · {building} · {crash} · {street}"


# ---------------------------------------------------------------------------
# 2. Which ZIP is selected (drill-through): search, or a click on map / scatter / ranking
# ---------------------------------------------------------------------------
@app.callback(
    Output("selected-zip", "data"),
    Input("applied-filters", "data"), Input("map-graph", "clickData"), Input("scatter-graph", "clickData"),
    Input("ranking-graph", "clickData"), Input("close-detail", "n_clicks"),
    prevent_initial_call=True,
)
def select_zip(applied, map_click, scatter_click, ranking_click, _close):
    trigger = ctx.triggered_id
    if trigger == "applied-filters":
        return applied.get("zip_code")
    if trigger == "close-detail":
        return None
    click = {"map-graph": map_click, "scatter-graph": scatter_click, "ranking-graph": ranking_click}.get(trigger)
    try:
        return str(click["points"][0]["customdata"][0])
    except (TypeError, KeyError, IndexError):
        return no_update


# ---------------------------------------------------------------------------
# 3. Draw every chart and number from the applied filters
# ---------------------------------------------------------------------------
@app.callback(
    Output("kpi-units", "children"), Output("kpi-buildings", "children"), Output("kpi-crashes", "children"),
    Output("kpi-deaths", "children"), Output("kpi-near", "children"), Output("kpi-hotspots", "children"),
    Output("scatter-graph", "figure"), Output("trend-graph", "figure"), Output("street-graph", "figure"),
    Output("income-graph", "figure"), Output("ranking-graph", "figure"),
    Input("applied-filters", "data"),
)
def draw_report(applied):
    f = Filters.from_dict(applied)
    building_rows, crash_rows = data.filter_buildings(f), data.filter_crashes(f)
    zips = data.zip_table(building_rows, crash_rows)
    k = data.kpis(building_rows, crash_rows, zips)
    return (f"{k['units']:,}", f"{k['buildings']:,}", f"{k['crashes']:,}", f"{k['deaths']:,}",
            "n/a" if k["near_share"] is None else f"{k['near_share']:.0%}", f"{k['double_hotspots']}",
            figures.scatter_figure(zips),
            figures.trend_figure(data.borough_year_table(f), f.year_from, f.year_to),
            figures.street_figure(crash_rows),
            figures.income_figure(data.filter_income(f, building_rows), crash_rows, f.year_to - f.year_from + 1),
            figures.ranking_figure(zips))


@app.callback(Output("heatmap-graph", "figure"), Input("applied-filters", "data"), Input("heatmap-mode", "value"))
def draw_heatmap(applied, mode):
    return figures.heatmap_figure(data.filter_crashes(Filters.from_dict(applied)), mode)


@app.callback(Output("map-graph", "figure"), Output("zip-detail", "children"),
              Input("applied-filters", "data"), Input("selected-zip", "data"))
def draw_map_and_detail(applied, selected_zip):
    f = Filters.from_dict(applied)
    building_rows, crash_rows = data.filter_buildings(f), data.filter_crashes(f)
    zips = data.zip_table(building_rows, crash_rows)
    return figures.map_figure(zips, crash_rows, selected_zip), zip_detail_panel(selected_zip, f)


def zip_detail_panel(zip_code, f):
    detail = data.zip_detail(zip_code, f)
    if detail is None:
        return EMPTY_DETAIL
    all_boroughs = Filters(**{**f.to_dict(), "boroughs": list(BOROUGHS)})
    building_rows = data.filter_buildings(all_boroughs)
    crash_rows = data.filter_crashes(all_boroughs)
    streets = [html.Li(f"{name}: {count} serious crash{'' if count == 1 else 'es'}")
               for name, count in detail["top_streets"]]
    return [
        html.Div([html.H3(f"ZIP {detail['zip_code']}"),
                  html.Button("× Close", id="close-detail", n_clicks=0, className="close-btn")], className="detail-head"),
        html.P(f"{detail['borough']} {detail['community_district']}", className="muted"),
        html.Div([
            html.Div([html.Strong(f"{detail['units']:,}"), html.Span("new affordable units")]),
            html.Div([html.Strong(f"{detail['buildings']:,}"), html.Span("buildings")]),
            html.Div([html.Strong(f"{detail['crashes']:,}"), html.Span("serious crashes")]),
            html.Div([html.Strong(f"{detail['deaths']:,}"), html.Span("deaths")]),
        ], className="detail-stats"),
        html.P(f"{detail['local_share']:.0%} of its serious crashes were on local streets.", className="muted"),
        html.H4("Streets with the most serious crashes") if streets else None,
        html.Ul(streets) if streets else None,
        dcc.Graph(figure=figures.zip_trend_figure(
            zip_code, building_rows[building_rows["zip_code"] == zip_code],
            crash_rows[crash_rows["zip_code"] == zip_code]), config={"displayModeBar": False}),
    ]


if __name__ == "__main__":
    app.run(debug=True)
