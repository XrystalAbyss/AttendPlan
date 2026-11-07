"""Inspect AJAX calls on myreportcard.php."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import control

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    print("Page URL:", page.url)
    
    # Check all select elements and their onchange attributes
    selects = page.locator("select").evaluate_all("els => els.map(e => ({id: e.id, name: e.name, onchange: e.getAttribute('onchange'), options: [...e.options].map(o => ({val: o.value, text: o.text})) }))")
    for s in selects:
        print(f"Select id={s['id']}, name={s['name']}, onchange={s['onchange']}")
        print(f"  Options ({len(s['options'])}): {s['options'][:5]}...")

    browser.close()

