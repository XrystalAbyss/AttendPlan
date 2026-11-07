"""Step by step test of discovery logic."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.performance_portal import open_performances
from app.adapters.portal_safety import choose, control, options, selected

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    open_performances(page)
    print("On myreportcard.php successfully.")
    
    # Check current year options
    yr_opts = options(page, "year")
    print("Year options:", [o["value"] for o in yr_opts])
    
    # Choose 2024-2025
    print("Choosing 2024-2025...")
    choose(page, "year", "2024-2025")
    
    # Wait for AJAX
    for i in range(10):
        page.wait_for_timeout(500)
        sessions = options(page, "exam_session")
        classes = options(page, "class")
        if sessions or classes:
            print(f"Step {i}: sessions={len(sessions)}, classes={len(classes)}")
            break
    print("Sessions:", sessions)
    print("Classes:", classes)

    browser.close()

