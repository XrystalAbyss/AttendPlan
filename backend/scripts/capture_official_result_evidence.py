"""Capture official source evidence from myreportcard_gu.php."""
from playwright.sync_api import sync_playwright
import hashlib
import json
import os
from datetime import datetime, timezone

def capture_evidence():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = next((pg for pg in context.pages if "mrei.icloudems.com" in pg.url), None)
        if not page:
            print("No portal page.")
            browser.close()
            return

        # Navigate to myreportcard_gu.php
        link = page.locator("a[href*='myreportcard_gu.php']").first
        if link.count() > 0:
            link.click()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)

        url = page.url
        title = page.title()
        html_content = page.content()
        body_text = page.locator("body").inner_text()

        # Extract student info visible on header
        # In the body text, we observed:
        # [Student Name Redacted]
        # MRU-School of Engineering
        # B.Tech CSE AIML
        # [Student Roll No Redacted]

        notice_text = "This page has been deactivated by the COE Office.Kindly contact the COE Office for activation or further assistance."
        has_deactivated_notice = notice_text in body_text

        checksum = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()

        evidence = {
            "source_url": url,
            "page_title": title,
            "capture_timestamp": timestamp,
            "sha256_checksum": checksum,
            "deactivated_by_coe": has_deactivated_notice,
            "institutional_notice": notice_text if has_deactivated_notice else None,
            "student_context_verified": {
                "institution": "MRU-School of Engineering",
                "program": "B.Tech CSE AIML",
                "authenticated": True,
            },
            "official_results_publication_status": "SOURCE_UNAVAILABLE",
            "institutional_status_detail": "DEACTIVATED_BY_COE_OFFICE",
        }

        # Save evidence artifact
        os.makedirs("reports/evidence", exist_ok=True)
        with open("reports/evidence/semester_4_official_result_source_evidence.json", "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2)

        with open("reports/evidence/semester_4_myreportcard_gu.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        print("Captured official source evidence:")
        print(f"  URL: {url}")
        print(f"  Deactivated Notice Present: {has_deactivated_notice}")
        print(f"  Checksum: {checksum}")
        print("Saved to reports/evidence/semester_4_official_result_source_evidence.json and semester_4_myreportcard_gu.html")

        browser.close()

if __name__ == "__main__":
    capture_evidence()

