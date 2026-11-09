"""Text of the Story tab (same findings as Section 12 of the notebook)."""

STORY_MARKDOWN = """
## Homes on dangerous streets?

New York City delivers about **25,000 affordable homes every year**, built new or preserved. They go to the households
who most depend on walking, buses and safe streets. We asked: **are these homes being placed next to the city's most
dangerous streets?**

We combined two NYC Open Data datasets: **Affordable Housing Production by Building** (HPD, about 9,500 buildings)
and **SIRTA serious crashes** (DOT, about 12,500 crashes with a severe injury or death, 2022 – March 2026).

---

### What the data shows

**1. Affordable housing and serious crashes are concentrated in the same places.**
ZIP codes with more new affordable units have more serious crashes (rank correlation 0.61). Just **26 "double
hotspot" ZIPs**, 14% of all ZIPs and mostly in the South and West Bronx and central Brooklyn, received **43% of all
new affordable units**.

**2. The newest and poorest residents are the most exposed.**
New-construction buildings, where every household is new to the area, sit in ZIPs with **28% more serious crashes**
than preserved buildings. Units for extremely-low-income households are in ZIPs **10% more dangerous** than average.

**3. The danger is on local streets, in the evening.**
**96%** of serious crashes within 250 m of new homes are on local streets, not highways, and they lean towards the
evening hours. In the Bronx, more of them happen at spots that already had serious crashes before.

**4. The buildings are not making it worse.**
Crashes did not rise with housing completions over the years, and the year after a building opened was slightly
safer than the year before (−3%). Family buildings sit on calmer blocks. Crashes in high-growth areas are frequent
but less often deadly.

---

### So what? Three recommendations for NYC

1. **Link the housing pipeline to the street-safety pipeline.** When HPD finances a building in one of the 15
   priority ZIPs (see *Explore*), DOT should review the surrounding streets before residents move in.
   These ZIPs hold a third of all new affordable units.
2. **Fix known spots first.** Repeat-danger locations near new homes are places DOT already knows.
   Local-street tools (speed cameras, raised crossings, daylighting, protected bike lanes) are cheap and fast.
3. **Target the evening.** Speed enforcement, signal timing and lighting around residential blocks at the hours when
   crashes near homes happen.

---

### Honest limitations

- **Association, not cause.** Dense, busy neighbourhoods get both more housing and more crashes. We did not measure
  density, traffic or population, so we cannot say that housing causes crashes or the reverse.
- **Only serious crashes**, and no traffic or population data, so there are no rates *per person*.
- **Missing locations.** Missing crash ZIP codes were filled from the nearest crash with a known ZIP (92% accurate in
  our test) or, without coordinates, from crashes on the same street (73%). About 3% still have no ZIP.
- **Fatal crashes have no published location after 2022**, so the map, the heatmap and the street chart show mainly
  severe-injury crashes. ZIP and borough numbers include all deaths.
- **Confidential homes.** 1,949 small buildings have no address; they appear only in borough totals.
- **Our choices.** The 250 m radius, the top-25% hotspot cut-off and the equal weights of the priority score are choices.
  The radius was tested at 150 m and 500 m with the same conclusions.
- **Preserved units** (52% of the total) keep existing tenants in place, and one project (Co-op City, 15,507 units)
  is large enough to move some totals.

---

### How this website works

Choose filters or type a search such as *"Brooklyn 2023 new buildings fatal"*, then press **Generate Report**:
every chart and number updates together. Click a ZIP on the map, the scatter plot or the ranking to open its detail panel.

Data: [Affordable Housing Production by Building](https://data.cityofnewyork.us/d/hg8x-zxpr) ·
[SIRTA serious crashes](https://data.cityofnewyork.us/d/xeqp-qz8h) · snapshot of 9 October 2026.
The full analysis (cleaning, integration, 12 research questions) is in the project notebook on GitHub.
"""
