"""Inspect portal options for 2024-2025 and 2026-2027."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import choose, control, options

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    print("=== Current Year:", control(page, "year").input_value())
    
    for yr in ["2024-2025", "2026-2027"]:
        print(f"\n=================== TESTING YEAR {yr} ===================")
        choose(page, "year", yr)
        page.wait_for_timeout(2000)
        sessions = options(page, "exam_session")
        print(f"Total sessions for {yr}: {len(sessions)}")
        for s in sessions:
            print(f"Session {s['value']} : {s['label']}")
            choose(page, "exam_session", s["value"])
            page.wait_for_timeout(1000)
            classes = options(page, "class")
            print(f"  Classes count: {len(classes)}")
            for c in classes:
                if "aiml" in c["label"].lower() or c["value"] in ("918", "1048", "2582"):
                    print(f"    Target Class matched: {c['value']} -> {c['label']}")
                    choose(page, "class", c["value"])
                    page.wait_for_timeout(1000)
                    divs = options(page, "division")
                    exams = options(page, "exam_type")
                    print(f"      Divisions: {divs}")
                    print(f"      Exam Types: {exams}")

    browser.close()

