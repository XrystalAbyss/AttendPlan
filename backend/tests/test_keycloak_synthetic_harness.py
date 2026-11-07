"""Synthetic Keycloak Test Harness for AttendPlan F2-C End-to-End Login Verification.

Simulates all Keycloak authentication stages and security boundaries offline:
1. Mobile number detection and autofill
2. Mobile form submission
3. TOTP challenge detection and local vault generation
4. Successful authentication to verified student dashboard
5. Incorrect OTP rejection and retry-lockout prevention
6. Expired session auto-recovery
7. Unauthorized origin refusal
8. Unauthenticated '/student/' URL rejection
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.domain.totp_models import (
    TotpAccountCandidate,
)
from app.services.login_orchestrator import (
    LoginOrchestrator,
    LoginState,
    is_authenticated_student_page,
)
from app.services.settings_service import AppSettings, SettingsService
from app.services.totp_vault_service import TotpVaultService
from tests.test_totp_vault import MockSecureKeyring

SYNTHETIC_PHONE = "9876543210"
SYNTHETIC_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture
def keycloak_harness(tmp_path: Path):
    """Initializes isolated orchestrator and services for synthetic testing."""
    settings_file = tmp_path / "settings.json"
    meta_file = tmp_path / "totp_metadata.json"
    keyring = MockSecureKeyring()

    settings_svc = SettingsService(settings_path=settings_file)
    vault_svc = TotpVaultService(metadata_path=meta_file, keyring_backend=keyring)
    session_mgr = MagicMock()

    orchestrator = LoginOrchestrator(
        session_manager=session_mgr,
        settings_service=settings_svc,
        vault_service=vault_svc,
    )
    return orchestrator, settings_svc, vault_svc, session_mgr


def test_harness_mobile_input_and_submission(keycloak_harness):
    """Scenario 1 & 2: Mobile input detection and automated submission."""
    orchestrator, settings_svc, _, session_mgr = keycloak_harness
    session_mgr.is_cdp_reachable.return_value = True

    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number=SYNTHETIC_PHONE,
            auto_mobile_autofill=True,
            auto_login_continuation=True,
        )
    )

    mock_user_input = MagicMock()
    mock_user_input.is_visible.return_value = True
    mock_login_btn = MagicMock()
    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"

    def query_selector(sel):
        if "username" in sel:
            return mock_user_input
        if "login" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = query_selector
    mock_page.evaluate.return_value = None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_p = MagicMock()
        mock_p.chromium.connect_over_cdp.return_value = mock_browser
        mock_pw.return_value.__enter__.return_value = mock_p

        # Calling orchestrator when at mobile stage should autofill and submit
        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.MANUAL_ACTION_REQUIRED
        assert res.step == "TOTP_VAULT_NOT_ENROLLED"
        mock_user_input.fill.assert_called_with(SYNTHETIC_PHONE)
        mock_login_btn.click.assert_called()


def test_harness_successful_authentication_full_flow(keycloak_harness):
    """Scenario 3 & 4: Full flow with mobile autofill, TOTP generation from vault, and dashboard redirect."""
    orchestrator, settings_svc, vault_svc, session_mgr = keycloak_harness
    session_mgr.is_cdp_reachable.return_value = True

    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number=SYNTHETIC_PHONE,
            auto_mobile_autofill=True,
            auto_login_continuation=True,
            auto_totp_autofill=True,
            auto_totp_submit=True,
        )
    )
    cand = TotpAccountCandidate(
        issuer="iCloudEMS",
        account_name="student@university",
        secret_base32=SYNTHETIC_SECRET,
    )
    vault_svc.enroll(cand, auto_autofill=True, auto_submit=True)

    mock_user_input = MagicMock()
    mock_user_input.is_visible.return_value = True
    mock_login_btn = MagicMock()
    mock_otp_input = MagicMock()
    mock_otp_input.is_visible.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"

    def query_selector(sel):
        if "username" in sel:
            return mock_user_input
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel or "submit" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = query_selector
    mock_page.evaluate.return_value = None

    def on_click(*args, **kwargs):
        mock_page.url = "https://mrei.icloudems.com/corecampus/student/student_dashboard.php"

    mock_login_btn.click.side_effect = on_click

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_p = MagicMock()
        mock_p.chromium.connect_over_cdp.return_value = mock_browser
        mock_pw.return_value.__enter__.return_value = mock_p

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.AUTHENTICATED
        assert res.step == "AUTHENTICATED_AND_VERIFIED"
        assert res.success is True
        assert res.redirected is True
        assert "student_dashboard.php" in res.current_url


def test_harness_incorrect_otp_rejection(keycloak_harness):
    """Scenario 5: Server rejects OTP code; orchestrator aborts retries to protect account."""
    orchestrator, settings_svc, vault_svc, session_mgr = keycloak_harness
    session_mgr.is_cdp_reachable.return_value = True

    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number=SYNTHETIC_PHONE,
            auto_mobile_autofill=True,
            auto_login_continuation=True,
            auto_totp_autofill=True,
            auto_totp_submit=True,
        )
    )
    cand = TotpAccountCandidate(
        issuer="iCloudEMS",
        account_name="student@university",
        secret_base32=SYNTHETIC_SECRET,
    )
    vault_svc.enroll(cand, auto_autofill=True, auto_submit=True)

    mock_otp_input = MagicMock()
    mock_otp_input.is_visible.return_value = True
    mock_login_btn = MagicMock()

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/login-actions/authenticate"

    def query_selector(sel):
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel or "submit" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = query_selector

    # Pre-submit has no error; post-submit returns invalid code banner
    responses = [None, "Invalid authenticator code. 2 attempts remaining."]
    mock_page.evaluate.side_effect = lambda script: responses.pop(0) if responses else None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_p = MagicMock()
        mock_p.chromium.connect_over_cdp.return_value = mock_browser
        mock_pw.return_value.__enter__.return_value = mock_p

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.FAILED
        assert res.step == "TOTP_REJECTED_BY_SERVER"
        assert "Automatic retries aborted" in res.message


def test_harness_expired_session_recovery(keycloak_harness):
    """Scenario 6: Expired session triggers clean navigation back to portal entry."""
    orchestrator, settings_svc, vault_svc, session_mgr = keycloak_harness
    session_mgr.is_cdp_reachable.return_value = True

    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number=SYNTHETIC_PHONE,
            auto_mobile_autofill=True,
            auto_login_continuation=True,
            auto_totp_autofill=True,
            auto_totp_submit=True,
        )
    )
    cand = TotpAccountCandidate(
        issuer="iCloudEMS",
        account_name="student@university",
        secret_base32=SYNTHETIC_SECRET,
    )
    vault_svc.enroll(cand, auto_autofill=True, auto_submit=True)

    mock_page = MagicMock()
    mock_page.url = "https://mrei.icloudems.com/corecampus/session_expired.php"

    mock_user_input = MagicMock()
    mock_user_input.is_visible.return_value = True
    mock_login_btn = MagicMock()
    mock_otp_input = MagicMock()
    mock_otp_input.is_visible.return_value = True

    def query_selector(sel):
        if "username" in sel:
            return mock_user_input
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = query_selector
    mock_page.evaluate.return_value = None

    def on_goto(url):
        mock_page.url = url

    mock_page.goto.side_effect = on_goto

    def on_click(*args, **kwargs):
        mock_page.url = "https://mrei.icloudems.com/corecampus/student/student_dashboard.php"

    mock_login_btn.click.side_effect = on_click

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_p = MagicMock()
        mock_p.chromium.connect_over_cdp.return_value = mock_browser
        mock_pw.return_value.__enter__.return_value = mock_p

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.AUTHENTICATED
        mock_page.goto.assert_called_with("https://mrei.icloudems.com/corecampus/index.php")


def test_harness_unexpected_origin_refusal(keycloak_harness):
    """Scenario 7: External or phishing origin triggers immediate security refusal."""
    orchestrator, _, _, session_mgr = keycloak_harness
    session_mgr.is_cdp_reachable.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://unauthorized-phishing-host.com/login"

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_p = MagicMock()
        mock_p.chromium.connect_over_cdp.return_value = mock_browser
        mock_pw.return_value.__enter__.return_value = mock_p

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.FAILED
        assert res.step == "SECURITY_ORIGIN_VIOLATION"
        assert "Refusing automated login on unauthorized origin" in res.message


def test_harness_unauthenticated_student_url_rejected():
    """Scenario 8: URL containing '/student/' without genuine dashboard indicators must not claim authenticated."""
    # A login page that happens to have '/student/' in its path or query
    mock_page_login = MagicMock()
    mock_page_login.url = "https://mrei.icloudems.com/student/login.php"
    assert is_authenticated_student_page(mock_page_login) is False

    # A Keycloak auth endpoint with /student/ in redirect_uri
    mock_page_kc = MagicMock()
    mock_page_kc.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth?redirect_uri=https://mrei.icloudems.com/corecampus/student/index.php"
    assert is_authenticated_student_page(mock_page_kc) is False

    # A legitimate student dashboard page
    mock_page_dashboard = MagicMock()
    mock_page_dashboard.url = "https://mrei.icloudems.com/corecampus/student/student_dashboard.php"
    assert is_authenticated_student_page(mock_page_dashboard) is True
