"""End-to-end browser test of the website (run while `python app.py` is serving on port 8050).

    python tests/browser_check.py [screenshot_folder]

It checks the things the project is graded on: the page loads without errors, the Generate Report
button updates the charts, the search box applies filters, a ZIP search opens the detail panel,
and Reset restores the defaults.
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8050/"
SHOTS = Path(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
SHOTS.mkdir(parents=True, exist_ok=True)


def kpi(page, card_id):
    return page.locator(f"#{card_id}").inner_text()


def wait_for_update(page, card_id, old_value, timeout=15000):
    page.wait_for_function(
        "([id, old]) => document.getElementById(id) && document.getElementById(id).innerText !== old",
        arg=[card_id, old_value], timeout=timeout)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(URL)
    page.wait_for_function("document.getElementById('kpi-units') && document.getElementById('kpi-units').innerText !== '–'", timeout=30000)
    page.wait_for_timeout(2500)
    start = {k: kpi(page, k) for k in ["kpi-units", "kpi-crashes", "kpi-deaths", "kpi-near", "kpi-hotspots"]}
    print("Default report:", start)
    page.screenshot(path=str(SHOTS / "01_overview.png"), full_page=True)

    # 1. Changing a dropdown alone must NOT change the charts (State), only Generate Report does (Input)
    page.click("#severity-dd")
    page.click("text=Fatal crashes only")
    page.wait_for_timeout(1500)
    assert kpi(page, "kpi-crashes") == start["kpi-crashes"], "charts changed before Generate Report"
    page.click("#generate-btn")
    wait_for_update(page, "kpi-crashes", start["kpi-crashes"])
    print("After choosing 'Fatal only' + Generate Report:", kpi(page, "kpi-crashes"), "crashes")

    # 2. Search mode
    before = kpi(page, "kpi-units")
    page.fill("#search-box", "Brooklyn 2023 new buildings")
    page.click("#generate-btn")
    wait_for_update(page, "kpi-units", before)
    page.wait_for_timeout(2000)
    print("Search 'Brooklyn 2023 new buildings':", kpi(page, "kpi-units"), "units,", kpi(page, "kpi-crashes"), "crashes")
    print("  summary:", page.locator("#report-summary").inner_text().replace("\n", " "))
    page.screenshot(path=str(SHOTS / "02_search_brooklyn.png"), full_page=True)

    # 3. ZIP search opens the drill-through panel
    page.fill("#search-box", "10453")
    page.press("#search-box", "Enter")
    page.wait_for_selector("text=ZIP 10453", timeout=15000)
    page.wait_for_timeout(2500)
    print("ZIP panel:", page.locator("#zip-detail").inner_text().split("\n")[:8])
    page.screenshot(path=str(SHOTS / "03_zip_detail.png"), full_page=False)

    # 4. Reset
    page.click("#reset-btn")
    page.wait_for_function("([id, v]) => document.getElementById(id).innerText === v",
                           arg=["kpi-units", start["kpi-units"]], timeout=15000)
    print("Reset restored defaults:", kpi(page, "kpi-units"))

    # 5. Explore and Story tabs
    page.click("text=Explore")
    page.wait_for_timeout(3000)
    page.screenshot(path=str(SHOTS / "04_explore.png"), full_page=True)
    page.click("text=Story")
    page.wait_for_timeout(1000)
    page.screenshot(path=str(SHOTS / "05_story.png"), full_page=True)

    # 6. Phone width
    phone = browser.new_page(viewport={"width": 390, "height": 844})
    phone.goto(URL)
    phone.wait_for_function("document.getElementById('kpi-units') && document.getElementById('kpi-units').innerText !== '–'", timeout=30000)
    phone.wait_for_timeout(2500)
    width = phone.evaluate("document.documentElement.scrollWidth")
    print("Phone layout scroll width:", width, "(viewport 390)")
    phone.screenshot(path=str(SHOTS / "06_phone.png"), full_page=False)

    real_errors = [e for e in errors if "favicon" not in e]
    print("Browser console errors:", real_errors if real_errors else "none")
    browser.close()
