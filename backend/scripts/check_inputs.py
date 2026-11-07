"""Check values of admnum, br_id, and other hidden inputs on myreportcard.php."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    inputs = page.locator("input,select").evaluate_all("""els => els.map(e => ({id: e.id, name: e.name, type: e.type, value: e.value}))""")
    for i in inputs:
        print(f"Input id={i['id']}, name={i['name']}, type={i['type']}, val={i['value']}")
    browser.close()

