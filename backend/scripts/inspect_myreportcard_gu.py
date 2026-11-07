"""Navigate to My Report Card (myreportcard_gu.php) and inspect controls without submitting."""
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit

def inspect_report_card():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "mrei.icloudems.com" in pg.url), None)
        if not page:
            print("No portal page.")
            browser.close()
            return

        print(f"Starting URL: {page.url}")

        # Click on 'My Report Card' link
        link = page.locator("a[href*='myreportcard_gu.php']").first
        print(f"Clicking link with href: {link.get_attribute('href')}")
        link.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)

        print(f"New URL: {page.url}")
        print(f"Page Title: {page.title()}")

        # Inspect all forms on the page
        forms = page.locator("form").all()
        print(f"\nTotal forms found: {len(forms)}")
        for i, f in enumerate(forms):
            action = f.get_attribute("action")
            method = f.get_attribute("method")
            print(f"  Form {i}: action={action}, method={method}")

        # Inspect all select elements
        selects = page.locator("select").all()
        print(f"\nTotal select elements: {len(selects)}")
        for s in selects:
            s_name = s.get_attribute("name")
            s_id = s.get_attribute("id")
            opts = s.locator("option").evaluate_all(
                "els => els.map(e => ({ value: e.value, text: (e.textContent || '').trim() }))"
            )
            print(f"  Select name='{s_name}', id='{s_id}' ({len(opts)} options):")
            for o in opts[:15]:
                print(f"    - {repr(o['value'])}: {repr(o['text'])}")

        # Inspect submit buttons
        buttons = page.locator("button, input[type='submit'], input[type='button']").all()
        print(f"\nTotal buttons/inputs: {len(buttons)}")
        for b in buttons:
            b_text = (b.inner_text() if b.evaluate("el => el.tagName") == "BUTTON" else b.get_attribute("value")) or ""
            b_name = b.get_attribute("name") or ""
            b_type = b.get_attribute("type") or ""
            print(f"  Button tag={b.evaluate('el => el.tagName')}, type='{b_type}', name='{b_name}', text='{b_text.strip()}'")

        # Check if there is already a table or message rendered on the page
        body_text = page.locator("body").inner_text()
        print(f"\nBody preview (first 500 chars):\n{body_text[:500]}")

        browser.close()

if __name__ == "__main__":
    inspect_report_card()

