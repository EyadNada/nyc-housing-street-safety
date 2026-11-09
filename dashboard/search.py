"""Search mode: turn a free-text query into filters.

Example: "Brooklyn 2023 new buildings fatal"
    -> boroughs=["Brooklyn"], years 2023-2023, construction="New Construction", severity="Fatal"

How it works: we look for known words and patterns (regular expressions) in the text.
Every pattern uses word boundaries (\\b), the same "match entire words" lesson as Lab 3,
so "new york" does not switch on "new construction" and "bk" does not match inside other words.
"""
import re

BOROUGH_WORDS = {
    "Bronx": ["the bronx", "bronx", "bx"],
    "Brooklyn": ["brooklyn", "bk", "bklyn"],
    "Manhattan": ["manhattan", "mn", "nyc center"],
    "Queens": ["queens", "qn"],
    "Staten Island": ["staten island", "staten", "si"],
}
CONSTRUCTION_PATTERNS = {
    "New Construction": r"\b(new[\s-]*(construction|buildings?|builds?|homes?|housing)|newly built|new)\b(?!\s+york)",
    "Preservation": r"\b(preserv\w*|existing|renovat\w*)\b",
}
SEVERITY_PATTERN = r"\b(fatal\w*|deadly|deaths?|killed|died)\b"
STREET_PATTERNS = {"Highway": r"\b(highways?|expressways?|parkways?)\b", "Local": r"\b(local|neighbou?rhood streets?)\b"}
YEAR_RANGE_PATTERN = r"\b(20[2-3]\d)\s*(?:-|–|to|until|through)\s*(20[2-3]\d)\b"
SINCE_PATTERN = r"\b(?:since|from|after)\s+(20[2-3]\d)\b"
YEAR_PATTERN = r"\b(20[2-3]\d)\b"
ZIP_PATTERN = r"\b(1[01]\d{3})\b"
VALID_YEARS = (2022, 2025)


def parse_search(text, known_zips=None):
    """Return (filters_found, notes).

    filters_found only contains the fields the text mentions, so the dropdowns keep their values
    for everything else. notes is a list of plain-English messages shown to the user.
    """
    query = (text or "").lower().strip()
    found, notes = {}, []
    if not query:
        return found, notes

    boroughs = [name for name, words in BOROUGH_WORDS.items()
                if any(re.search(rf"\b{re.escape(word)}\b", query) for word in words)]
    if boroughs:
        found["boroughs"] = boroughs

    zip_match = re.search(ZIP_PATTERN, query)
    if zip_match:
        zip_code = zip_match.group(1)
        if known_zips is None or zip_code in known_zips:
            found["zip_code"] = zip_code
        else:
            notes.append(f"ZIP {zip_code} has no affordable housing or serious crashes in our data.")
        query = query.replace(zip_code, " ")              # so a ZIP is never read as a year

    years = None
    if match := re.search(YEAR_RANGE_PATTERN, query):
        years = sorted([int(match.group(1)), int(match.group(2))])
    elif match := re.search(SINCE_PATTERN, query):
        years = [int(match.group(1)), VALID_YEARS[1]]
    elif all_years := re.findall(YEAR_PATTERN, query):
        numbers = [int(y) for y in all_years]
        years = [min(numbers), max(numbers)]
    if years:
        clipped = [min(max(y, VALID_YEARS[0]), VALID_YEARS[1]) for y in years]
        if clipped != years:
            notes.append("Our data covers 2022–2025, so the years were limited to that range.")
        found["year_from"], found["year_to"] = clipped

    for value, pattern in CONSTRUCTION_PATTERNS.items():
        if re.search(pattern, query):
            found["construction"] = value
            break
    if re.search(SEVERITY_PATTERN, query):
        found["severity"] = "Fatal"
    for value, pattern in STREET_PATTERNS.items():
        if re.search(pattern, query):
            found["street"] = value
            break

    if not found and not notes:
        notes.append("No filter words recognised. Try a borough, a year, 'new buildings', 'fatal' or a ZIP code.")
    return found, notes


def describe(found):
    """Short readable summary, for example 'Brooklyn · 2023 · New Construction · fatal crashes'."""
    parts = []
    if "boroughs" in found:
        parts.append(", ".join(found["boroughs"]))
    if "year_from" in found:
        same = found["year_from"] == found["year_to"]
        parts.append(f"{found['year_from']}" if same else f"{found['year_from']}–{found['year_to']}")
    if "construction" in found:
        parts.append(found["construction"])
    if found.get("severity") == "Fatal":
        parts.append("fatal crashes")
    if "street" in found:
        parts.append(f"{found['street'].lower()} streets" if found["street"] == "Local" else "highways")
    if "zip_code" in found:
        parts.append(f"ZIP {found['zip_code']}")
    return " · ".join(parts)
