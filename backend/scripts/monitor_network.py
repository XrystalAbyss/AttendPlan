"""Monitor network traffic when acad_year changes."""
from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor

with sync_playwright() as p:
    browser, page = LivePortalExtractor()._get_portal_page(p)
    
    def log_response(response):
        if "myreportcardSave.php" in response.url:
            try:
                print(f"[HTTP {response.status}] {response.url}")
                print("  Response text:", response.text()[:200])
            except Exception as e:
                print(f"[HTTP {response.status}] {response.url}: {e}")

    page.on("response", log_response)
    
    print("Triggering acad_year change to 2024-2025...")
    page.evaluate("""() => {
        const jq = window.jQuery;
        $('#acad_year').val('2024-2025').trigger('change');
    }""")
    page.wait_for_timeout(4000)

    print("\nTriggering acad_year change to 2025-2026...")
    page.evaluate("""() => {
        const jq = window.jQuery;
        $('#acad_year').val('2025-2026').trigger('change');
    }""")
    page.wait_for_timeout(4000)

    print("\nTriggering acad_year change to 2026-2027...")
    page.evaluate("""() => {
        const jq = window.jQuery;
        $('#acad_year').val('2026-2027').trigger('change');
    }""")
    page.wait_for_timeout(4000)

    browser.close()

