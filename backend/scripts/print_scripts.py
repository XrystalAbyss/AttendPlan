"""Print the entire scripts mentioning acad_year or exam_session."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    scripts = page.locator("script").evaluate_all("""els => els.map(s => s.innerText).filter(t => t.includes('acad_year') || t.includes('exam_session'))""")
    for i, s in enumerate(scripts):
        print(f"=== SCRIPT {i} ===")
        print(s)
    browser.close()

