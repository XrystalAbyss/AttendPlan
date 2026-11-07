"""Examine sidebar and navigation structure on student dashboard."""
from playwright.sync_api import sync_playwright

def inspect_sidebar():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "mrei.icloudems.com" in pg.url), None)
        if not page:
            print("No portal page.")
            browser.close()
            return

        # Check menu elements
        menu_items = page.locator("ul.sidebar-menu li, .nav li, .menu li, .sidebar li").evaluate_all(
            """els => els.map(e => ({
                text: (e.innerText || '').trim().replace(/\\s+/g, ' '),
                html: e.innerHTML.slice(0, 150)
            }))"""
        )
        print(f"Total menu li items: {len(menu_items)}")
        for i, m in enumerate(menu_items):
            if m["text"]:
                print(f"{i}: {m['text']}")

        browser.close()

if __name__ == "__main__":
    inspect_sidebar()

