"""Search entire student portal DOM for any additional grade/result endpoints."""
from playwright.sync_api import sync_playwright
import re

def search_portal():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "mrei.icloudems.com" in pg.url), None)
        if not page:
            print("No portal page.")
            browser.close()
            return

        # Navigate back to student_index.php
        page.goto("https://mrei.icloudems.com/corecampus/student/student_index.php", wait_until="domcontentloaded")
        content = page.content()

        # Find any references to .php scripts containing 'result', 'grade', 'card', 'marks', 'exam'
        matches = re.findall(r'[\w/\.-]+(?:result|grade|card|marks|exam)[\w/\.-]*\.php', content, re.I)
        unique_matches = sorted(set(matches))
        print(f"Referenced PHP scripts in dashboard DOM matching keywords ({len(unique_matches)}):")
        for m in unique_matches:
            print(f"  - {m}")

        browser.close()

if __name__ == "__main__":
    search_portal()

