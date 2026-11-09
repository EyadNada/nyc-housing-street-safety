# Homes on Dangerous Streets?
### Affordable housing and serious traffic crashes in New York City (2022–2025)

**Data Engineering and Visualization, Winter Semester 2026: Project Milestone 1**
German International University, Faculty of Informatics and Computer Science

| | Link |
|---|---|
| Live website | `https://<your-service>.onrender.com` *(add after deployment)* |
| Notebook | [`Milestone1_Housing_x_StreetSafety.ipynb`](Milestone1_Housing_x_StreetSafety.ipynb) |
| Housing dataset | [Affordable Housing Production by Building (HPD)](https://data.cityofnewyork.us/d/hg8x-zxpr), catalog H2 |
| Transportation dataset | [Serious Injury Response, Tracking & Analysis Program, SIRTA (DOT)](https://data.cityofnewyork.us/d/xeqp-qz8h), catalog T4 |

## Team

| Role | Name | ID | GitHub |
|---|---|---|---|
| M1: Lead & Integration | | | |
| M2: Housing data | | | |
| M3: Transport data | | | |
| M4: Website logic | | | |
| M5: Website visuals & deployment | | | |
| M6: Story & documentation | | | |

## The question and the answer in short

New York City delivers about 25,000 affordable homes a year. **Are they being placed next to the city's most dangerous streets?**

- **Yes, in the same places.** ZIP codes with more new affordable units have more serious crashes (rank correlation 0.61). 26 "double hotspot" ZIPs (14% of ZIPs) received 43% of all new affordable units.
- **The newest and poorest residents are the most exposed.** New-construction buildings sit in ZIPs with 28% more serious crashes than preserved buildings.
- **The danger is on local streets** (96% of serious crashes near new homes), so it can be fixed with tools DOT already uses.
- **The buildings are not making it worse.** Crashes did not rise with completions, and the year after a building opened was slightly safer.

All results are **associations, not causes**. See Section 12 of the notebook for the full story and limitations.

## Repository structure

```
Milestone1_Housing_x_StreetSafety.ipynb   the full analysis (EDA, cleaning, integration, 12 research questions, story)
notebook_src/                             the notebook as plain Python files (easier to review; build_notebook.sh rebuilds it)
data/raw/                                 raw snapshots downloaded from the NYC Open Data API (9 Oct 2026)
data/clean/                               clean tables written by the notebook (Section 11) and read by the website
app.py                                    the Dash website: layout and callbacks
dashboard/data.py                         loading, filtering and aggregating the clean tables
dashboard/figures.py                      the Plotly charts
dashboard/search.py                       the search box: turns text into filters
dashboard/story.py                        text of the Story tab
assets/style.css                          website style (Dash loads it automatically)
reports/                                  automated EDA reports (ydata-profiling, Sweetviz)
tests/                                    unit tests and an end-to-end browser test
docs/prompts_log.md                       every AI prompt we used
requirements.txt                          packages for the website (Render)
requirements-notebook.txt                 packages for running the notebook locally
render.yaml, .python-version              deployment settings for Render
```

## How to run the notebook

**Google Colab (recommended):** open the notebook from GitHub in Colab (File → Open notebook → GitHub tab, paste the repository URL), then **Runtime → Run all**. On the first run it downloads both datasets from the API. Colab already has every package we use.

**Locally:**
```bash
pip install -r requirements-notebook.txt
jupyter notebook Milestone1_Housing_x_StreetSafety.ipynb
```
The notebook uses the saved snapshot in `data/raw/`, so the numbers match our text. Set `REFRESH_FROM_API = True` in Section 2 to download fresh data.

## How to run the website locally

```bash
pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:8050.

### What the website does
- **Five filters:** borough, years, construction type (housing), crash severity and street type (transportation).
- **Search mode:** type, for example, `Brooklyn 2023 new buildings fatal`, `the bronx 2022-2024 preservation` or a ZIP code like `10453`. The words override the matching filters, and the page shows what the search understood.
- **Generate Report:** charts change **only** when this button is clicked (or Enter is pressed in the search box). The filters are read as Dash `State`, and the button is the only `Input`. Every chart then reads the same stored filters, so they always update together.
- **Charts:** a cross-domain map (crash density + ZIP circles by hotspot group), a ZIP scatter plot (housing vs crashes), yearly trends, a time-of-day heatmap, local vs highway crashes, danger by income band, and a priority ranking.
- **Drill-through:** click a ZIP on the map, the scatter plot or the ranking (or search for it) to open its detail panel.
- **Story tab:** the question, the findings, three recommendations and the limitations.

## How to deploy on Render (free)

1. Push this repository to GitHub.
2. Create a free account at [render.com](https://render.com) and connect your GitHub account.
3. Click **New + → Blueprint**, choose this repository, and confirm. Render reads `render.yaml` and creates the web service.
   *(Alternative without Blueprint: **New + → Web Service**, choose the repository, Build Command `pip install -r requirements.txt`, Start Command `gunicorn app:server --workers 1 --threads 4 --timeout 120`, Instance type **Free**.)*
4. Wait for the build to finish (a few minutes), then open the `onrender.com` link and test every filter, the search box and the Generate Report button.
5. Put the link at the top of this README and in the submission email.

**Notes:**
- `.python-version` pins Python 3.13, the version we tested. Without it, Render would use its newest default.
- A free service goes to sleep after 15 minutes without visitors, and the first visit after that takes about a minute to load. Open the site once before showing it.
- The website uses about 125 MB of memory because it reads the small clean tables, not the raw data.

## Tests

```bash
pip install pytest playwright
pytest tests/test_search.py tests/test_data.py         # search parser and website numbers
python app.py &                                          # then, in another terminal:
python tests/browser_check.py                            # end-to-end: filters, search, Generate Report, ZIP panel, reset
```

## Team contributions

| Member | Research questions | Cleaning & integration | Website | Documentation |
|---|---|---|---|---|
| M1: Lead & Integration | RQ1, RQ2 | Extract, integration, post-integration cleaning | Data loading (`dashboard/data.py`) | GitHub repository |
| M2: Housing data | RQ3, RQ4 | Housing EDA and cleaning | Housing filters | Housing markdown cells |
| M3: Transport data | RQ5, RQ6 | Crash EDA, cleaning and ZIP imputation | Crash filters | Crash markdown cells |
| M4: Website logic | RQ7, RQ8 | Load step | Callbacks, search parser, Generate Report button | Website section of this README |
| M5: Website visuals & deployment | RQ9, RQ10 | Chart style and colours | Layout, charts, map, Render deployment | Deployment guide |
| M6: Story & documentation | RQ11, RQ12 | Cleaning verification | Story tab | Story, README, prompts log, final check |

## Use of AI

We used Claude (Anthropic) as an assistant for planning, dataset selection, code drafts and explanations. Every prompt is listed in [`docs/prompts_log.md`](docs/prompts_log.md). All results come from code we ran and checked.
