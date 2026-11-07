"""Test choosing session 5764 and class 918."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.performance_portal import open_performances, validate_scope
from app.adapters.portal_safety import choose, control, options, selected

class MockTerm:
    academic_year = "2024-2025"
    semester_number = 1
    class_identifier = "918"

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    open_performances(page)
    choose(page, "year", "2024-2025")
    choose(page, "exam_session", "5764")
    choose(page, "class", "918")
    
    print("Class selected:", selected(page, "class"))
    print("Divisions:", options(page, "division"))
    print("Division selected:", selected(page, "division"))
    print("Exams:", options(page, "exam_type"))

    validate_scope(page, MockTerm(), "5764")
    print("validate_scope PASSED!")
    browser.close()

