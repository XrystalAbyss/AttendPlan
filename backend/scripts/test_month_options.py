import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from playwright.sync_api import sync_playwright
from app.adapters.live_portal_extractor import LivePortalExtractor, DAYWISE_URL_PATH, SUBWISE_URL_PATH
from app.adapters.portal_safety import options

extractor = LivePortalExtractor()
with sync_playwright() as p:
    browser, page = extractor._get_portal_page(p)
    try:
        extractor.navigate_to_view(page, SUBWISE_URL_PATH, "select, #aca", timeout_ms=8000)
        extractor.navigate_to_view(page, DAYWISE_URL_PATH, "select, #aca", timeout_ms=8000)
        print("Month options:", options(page, "month"))
    finally:
        browser.close()

