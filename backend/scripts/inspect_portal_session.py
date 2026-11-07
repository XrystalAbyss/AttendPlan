"""Safe read-only inspection of portal session and navigation menu on CDP."""
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit, urljoin
import json

def inspect_session():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        portal_page = next((pg for pg in context.pages if "mrei.icloudems.com" in pg.url), None)
        if not portal_page:
            print("ERROR: No mrei.icloudems.com page found in browser contexts.")
            browser.close()
            return

        print(f"Current Portal Page URL: {portal_page.url}")
        title = portal_page.title()
        print(f"Page Title: {title}")

        # Check for login form vs authenticated student portal
        login_form = portal_page.locator("input[name='user_id'], input[name='username'], input[type='password']")
        if login_form.count() > 0:
            print("STATUS: NOT_AUTHENTICATED (Login form detected)")
            browser.close()
            return

        # Check authenticated state indicators
        body_text = portal_page.locator("body").inner_text()
        is_authenticated = "Logout" in body_text or "Log Out" in body_text or "Dashboard" in body_text or "Student" in body_text
        print(f"STATUS: {'AUTHENTICATED' if is_authenticated else 'UNKNOWN'}")

        # Inspect all anchor tags to find Result / Grade Card / Examination menu items
        links = portal_page.locator("a[href]").all()
        print(f"Total links on page: {len(links)}")

        relevant_links = []
        for l in links:
            try:
                href = l.get_attribute("href") or ""
                text = l.inner_text().strip()
                norm_text = text.lower()
                norm_href = href.lower()
                keywords = ["result", "grade", "report", "exam", "card", "transcript", "mark"]
                if any(kw in norm_text or kw in norm_href for kw in keywords):
                    full_url = urljoin(portal_page.url, href)
                    relevant_links.append({
                        "text": text.replace("\n", " "),
                        "href": href,
                        "full_url": full_url,
                        "visible": l.is_visible()
                    })
            except Exception:
                continue

        print(f"\nFound {len(relevant_links)} candidate examination/result/grade links:")
        for rl in relevant_links:
            print(f"  - [{rl['text']}] -> href: {rl['href']} (visible: {rl['visible']})")

        browser.close()

if __name__ == "__main__":
    inspect_session()

