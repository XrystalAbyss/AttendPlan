"""Inspect the navigation links on the authenticated student dashboard."""
from urllib.parse import urlsplit, urljoin
from playwright.sync_api import sync_playwright

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "mrei.icloudems.com" in pg.url), None)
        if not page:
            print("No mrei.icloudems.com page found.")
            browser.close()
            return

        print(f"Current URL: {page.url}")
        print(f"Title: {page.title()}")

        # Extract all navigation menu links and their visible labels
        all_links = page.locator("a[href]").evaluate_all(
            """els => els.map(e => ({
                text: (e.innerText || e.textContent || '').trim().replace(/\\s+/g, ' '),
                href: e.getAttribute('href') || '',
                id: e.id || '',
                className: e.className || ''
            }))"""
        )

        print(f"Total links found: {len(all_links)}")

        # Search for examination, result, grade, report card, marks
        keywords = ["result", "grade", "report", "exam", "card", "transcript", "mark", "performance", "score", "academic"]
        matching = []
        for l in all_links:
            text = l["text"]
            href = l["href"]
            if any(kw in text.lower() or kw in href.lower() for kw in keywords):
                matching.append(l)

        print(f"\nMatching Examination / Results / Grades links ({len(matching)}):")
        for m in matching:
            print(f"  Text: {repr(m['text'])} | Href: {repr(m['href'])}")

        browser.close()

if __name__ == "__main__":
    inspect()

