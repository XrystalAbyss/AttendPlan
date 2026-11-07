import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from app.adapters.live_portal_extractor import LivePortalExtractor, DAYWISE_URL_PATH, SUBWISE_URL_PATH
from app.adapters.portal_safety import canonical_html, choose

extractor = LivePortalExtractor()
with sync_playwright() as p:
    browser, page = extractor._get_portal_page(p)
    try:
        extractor.navigate_to_view(page, SUBWISE_URL_PATH, "select, #aca, table", timeout_ms=8000)
        extractor.navigate_to_view(page, DAYWISE_URL_PATH, "select, #aca, table", timeout_ms=8000)
        test_scopes = [
            (3, "2025-2026", "1067", "2025-09"),
            (2, "2024-2025", "1048", "2025-02"),
            (1, "2024-2025", "918", "2024-09"),
        ]
        for sem, year, cid, month in test_scopes:
            extractor._apply_filters(page, year, sem, cid)
            choose(page, "month", month)
            submitted = extractor._search(page, DAYWISE_URL_PATH)
            html_content = canonical_html(page, submitted)
            soup = BeautifulSoup(html_content, "html.parser")
            print(f"\n==================== SEMESTER {sem} {month} ====================")
            labels = set()
            for td in soup.find_all("td"):
                text = td.get_text(" ", strip=True)
                # Find course labels inside td
                lines = [line.strip() for line in td.strings if line.strip()]
                for l in lines:
                    if l in ("P", "A", "NA", "L", "OD") or re.match(r"^\d{1,2}:\d{2}", l) or re.match(r"^\d+$", l):
                        continue
                    if len(l) > 2:
                        labels.add(l)
            print(f"Extracted {len(labels)} unique labels:")
            for l in sorted(labels):
                print(f"  - {l}")
    finally:
        browser.close()

