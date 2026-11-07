import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from app.adapters.live_portal_extractor import LivePortalExtractor, SUBWISE_URL_PATH
from app.adapters.html_parser import ERPAttendanceParser
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
            
            parser = ERPAttendanceParser()
            snapshot = parser.parse_html(html_content)
            print(f"\n==================== SEMESTER {sem} ({year}, cid={cid}) ====================")
            print(f"Total courses parsed: {len(snapshot.courses)}")
            print(f"Total Attended: {snapshot.summary.total_attended}")
            print(f"Total Delivered: {snapshot.summary.total_delivered}")
            print(f"Overall %: {snapshot.summary.overall_percentage}")
            for c in snapshot.courses:
                print(f"  {c.code:<14} | {c.name[:30]:<30} | {c.short_name:<16} | {c.attended}/{c.delivered} | {c.percent}%")
    finally:
        browser.close()

