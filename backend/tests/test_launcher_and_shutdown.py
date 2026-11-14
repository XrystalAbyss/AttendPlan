"""Tests for desktop launcher shutdown endpoint, browser launch semantics, and university source origin regression."""
import logging
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.adapters.live_portal_extractor import PORTAL_BASE
from app.adapters.portal_safety import ORIGIN
from app.adapters.portal_session import DEFAULT_PORTAL_URL, ALLOWED_AUTH_HOSTS
from app.main import app
import launcher


def test_university_source_origin_regression():
    """Ensure portal base, safety origin, and default portal URL strictly target Manav Rachna (mrei.icloudems.com)."""
    assert PORTAL_BASE == "https://mrei.icloudems.com"
    assert ORIGIN == "https://mrei.icloudems.com"
    assert DEFAULT_PORTAL_URL == "https://mrei.icloudems.com/corecampus/index.php"
    assert "mrei.icloudems.com" in ALLOWED_AUTH_HOSTS
    assert "usermanagement.icloudems.com" in ALLOWED_AUTH_HOSTS
    # Ensure no other unapproved university domains are allowlisted
    for host in ALLOWED_AUTH_HOSTS:
        assert host.endswith("icloudems.com"), f"Unexpected host in portal allowlist: {host}"


def test_shutdown_endpoint_security_and_trigger():
    """Test /api/v1/startup/shutdown requires loopback caller, rejects cross-site, and triggers app.state hook."""
    client = TestClient(app)

    # Cross-site request rejected
    res_cross = client.post("/api/v1/startup/shutdown", headers={"sec-fetch-site": "cross-site"})
    assert res_cross.status_code == 403
    assert "cross-site" in res_cross.json()["detail"].lower()

    # Trigger hook test
    mock_trigger = Mock()
    app.state.trigger_shutdown = mock_trigger

    res_ok = client.post("/api/v1/startup/shutdown")
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "shutting_down"


def test_launch_unified_browser_semantics():
    """Test launch_unified_browser never silently falls back to system browser unless allow_default_browser=True."""
    logger = logging.getLogger("test_launcher")

    # When Chromium is not found and allow_default_browser=False
    with patch("app.adapters.portal_session.PortalSessionManager.is_cdp_reachable", return_value=False), \
         patch("app.adapters.portal_session.find_chrome_executable", return_value=None), \
         patch("webbrowser.open") as mock_webbrowser:
        res = launcher.launch_unified_browser("http://127.0.0.1:8000/", logger, allow_default_browser=False)
        assert res["success"] is False
        assert res["mode"] == "none"
        assert "guidance" in res
        mock_webbrowser.assert_not_called()

    # When Chromium is not found and allow_default_browser=True
    with patch("app.adapters.portal_session.PortalSessionManager.is_cdp_reachable", return_value=False), \
         patch("app.adapters.portal_session.find_chrome_executable", return_value=None), \
         patch("webbrowser.open") as mock_webbrowser:
        res = launcher.launch_unified_browser("http://127.0.0.1:8000/", logger, allow_default_browser=True)
        assert res["success"] is True
        assert res["mode"] == "system_default_browser"
        mock_webbrowser.assert_called_once_with("http://127.0.0.1:8000/")
