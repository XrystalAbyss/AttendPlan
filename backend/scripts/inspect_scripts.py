"""Find event listeners on #acad_year and how exam_session is populated."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    
    # Check jQuery events attached to #acad_year
    events = page.evaluate("""() => {
        const jq = window.jQuery;
        if (!jq) return 'No jQuery';
        const el = jq('#acad_year');
        const ev = jq._data(el[0], 'events');
        return ev ? Object.keys(ev) : 'No events on #acad_year';
    }""")
    print("jQuery events on #acad_year:", events)

    # Search page scripts for 'acad_year'
    scripts = page.locator("script").evaluate_all("""els => els.map(s => s.innerText).filter(t => t.includes('acad_year') || t.includes('exam_session'))""")
    print(f"Inline scripts mentioning acad_year/exam_session: {len(scripts)}")
    for i, s in enumerate(scripts):
        print(f"--- Script {i} ---")
        print(s[:500])

    browser.close()

