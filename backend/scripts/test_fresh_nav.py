"""Test navigating fresh to myreportcard.php and checking options."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    print("Navigating to myreportcard.php...")
    page.goto("https://mrei.icloudems.com/corecampus/student/grades/new/myreportcard.php")
    page.wait_for_load_state("networkidle")
    # Wait for acad_year to appear and have options
    page.wait_for_selector("#acad_year option:not([value=''])", state="attached", timeout=10000)
    
    # Wait 2 seconds for initial getMyReportForm AJAX to complete
    page.wait_for_timeout(2000)
    
    # Check what year is selected and what exam_session options exist
    sel_year = page.evaluate("() => document.getElementById('acad_year').value")
    sessions = page.evaluate("() => [...document.getElementById('exam_session').options].map(o => ({val: o.value, text: o.text}))")
    classes = page.evaluate("() => [...document.getElementById('class_id').options].map(o => ({val: o.value, text: o.text}))")
    print("Selected Year:", sel_year)
    print(f"Sessions ({len(sessions)}):", sessions)
    print(f"Classes ({len(classes)}):", classes)

    browser.close()
