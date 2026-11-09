"""Unit tests for the search parser (run: pytest)."""
from dashboard.search import describe, parse_search

ZIPS = {"10453", "11207", "11101"}


def test_full_query():
    found, notes = parse_search("Brooklyn 2023 new buildings fatal", ZIPS)
    assert found == {"boroughs": ["Brooklyn"], "year_from": 2023, "year_to": 2023,
                     "construction": "New Construction", "severity": "Fatal"}
    assert notes == []


def test_year_range_and_preservation():
    found, _ = parse_search("the bronx 2022-2024 preservation", ZIPS)
    assert found["boroughs"] == ["Bronx"] and (found["year_from"], found["year_to"]) == (2022, 2024)
    assert found["construction"] == "Preservation"


def test_new_york_is_not_new_construction():
    found, _ = parse_search("new york highways since 2024", ZIPS)
    assert "construction" not in found
    assert found["street"] == "Highway" and (found["year_from"], found["year_to"]) == (2024, 2025)


def test_zip_is_not_read_as_year():
    found, _ = parse_search("10453", ZIPS)
    assert found == {"zip_code": "10453"}


def test_unknown_zip_and_out_of_range_year():
    found, notes = parse_search("10001 queens 2021", ZIPS)
    assert "zip_code" not in found and found["year_from"] == 2022
    assert len(notes) == 2


def test_nothing_recognised():
    found, notes = parse_search("hello there", ZIPS)
    assert found == {} and notes


def test_describe():
    assert describe({"boroughs": ["Queens"], "year_from": 2022, "year_to": 2025, "severity": "Fatal"}) == \
        "Queens · 2022–2025 · fatal crashes"
