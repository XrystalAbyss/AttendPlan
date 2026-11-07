import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from app.adapters.live_portal_extractor import LivePortalExtractor, SUBWISE_URL_PATH
from app.adapters.portal_safety import canonical_html

extractor = LivePortalExtractor()
with sync_playwright() as p:
    browser, page = extractor._get_portal_page(p)
    try:
        extractor.navigate_to_view(page, SUBWISE_URL_PATH, "select, #aca, table", timeout_ms=8000)
        for sem, year, cid in [
            (3, "2025-2026", "1067"),
            (2, "2024-2025", "1048"),
            (1, "2024-2025", "918"),
        ]:
            extractor._apply_filters(page, year, sem, cid)
            submitted = extractor._search(page, SUBWISE_URL_PATH)
            html_content = canonical_html(page, submitted)
            soup = BeautifulSoup(html_content, "html.parser")
            print(f"\n==================== SEMESTER {sem} ({year}, cid={cid}) ====================")
            # Find table
            for tbl in soup.find_all("table"):
                headers = [th.get_text(" ", strip=True) for th in tbl.find_all("th")]
                if any("Course" in h for h in headers) or any("Attended" in h for h in headers):
                    print("HEADERS:", headers)
                    for tr in tbl.find_all("tr"):
                        tds = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                        if len(tds) >= 4 and any("/" in t for t in tds):
                            print("ROW:", tds)
    finally:
        browser.close()
