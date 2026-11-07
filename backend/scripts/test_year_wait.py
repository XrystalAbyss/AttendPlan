"""Test selecting year and waiting for exam_session to populate."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import choose, control, options

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    print("Selecting 2024-2025...")
    choose(page, "year", "2024-2025")
    
    # Wait for exam_session options to appear
    print("Waiting for exam_session options...")
    page.wait_for_function("() => document.getElementById('exam_session') && document.getElementById('exam_session').options.length > 1", timeout=10000)
    sessions = options(page, "exam_session")
    print(f"Discovered sessions for 2024-2025 ({len(sessions)}):")
    for s in sessions:
        print(" ", s)

    # Wait for class_id options to appear
    page.wait_for_function("() => document.getElementById('class_id') && document.getElementById('class_id').options.length > 1", timeout=10000)
    classes = options(page, "class")
    print(f"Discovered classes for 2024-2025 ({len(classes)}):")
    for c in classes:
        print(" ", c)

    browser.close()

