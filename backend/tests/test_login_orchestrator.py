"""Unit tests for LoginOrchestrator and authentication state machine."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.domain.totp_models import (
    TotpAccountCandidate,
)
from app.services.login_orchestrator import (
    LoginOrchestrator,
    LoginState,
)
from app.services.settings_service import AppSettings, SettingsService
from app.services.totp_vault_service import TotpVaultService
from tests.test_totp_vault import MockSecureKeyring

SYNTHETIC_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture
def test_services(tmp_path: Path):
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


def test_login_orchestrator_disconnected_when_cdp_unreachable(test_services):
    """When CDP is not reachable, orchestrator immediately returns DISCONNECTED."""
    orchestrator, _, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = False

    status = orchestrator.get_status()
    assert status.state == LoginState.DISCONNECTED
    assert status.step == "CHECK_BROWSER"

    res = orchestrator.orchestrate_login()
    assert res.state == LoginState.DISCONNECTED
    assert res.step == "BROWSER_CHECK"


def test_login_orchestrator_existing_session_reuse(test_services):
    """When an existing tab is already on authenticated student dashboard, return AUTHENTICATED immediately."""
    orchestrator, _, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True

    # Mock Playwright CDP context with an authenticated page
    mock_page = MagicMock()
    mock_page.url = "https://mrei.icloudems.com/corecampus/student/student_dashboard.php"

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.AUTHENTICATED
        assert res.step == "EXISTING_SESSION_REUSED"
        assert res.success is True
        assert res.redirected is True


def test_login_orchestrator_halt_when_mobile_number_not_configured(test_services):
    """When at Stage 1 (mobile input) but no mobile number is saved, halt at MANUAL_ACTION_REQUIRED."""
    orchestrator, settings_svc, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True

    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"
    mock_page.query_selector.side_effect = lambda sel: mock_username_input if "username" in sel else None
    mock_page.evaluate.return_value = None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.MANUAL_ACTION_REQUIRED
        assert res.step == "MOBILE_INPUT_REQUIRED"
        assert "Settings > Authentication" in res.message


def test_login_orchestrator_halt_when_totp_not_enrolled(test_services):
    """When at Stage 2 (TOTP challenge) but vault is empty, halt at MANUAL_ACTION_REQUIRED."""
    orchestrator, settings_svc, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True

    # Configure mobile number
    settings_svc.save_settings(AppSettings(saved_mobile_number="9876543210"))

    # Mock page where mobile input is already submitted, now showing OTP input
    mock_otp_input = MagicMock()
    mock_otp_input.is_visible.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/login-actions/authenticate"

    def selector_router(sel):
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        return None

    mock_page.query_selector.side_effect = selector_router
    mock_page.evaluate.return_value = None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.MANUAL_ACTION_REQUIRED
        assert res.step == "TOTP_VAULT_NOT_ENROLLED"


def test_login_orchestrator_full_successful_flow(test_services):
    """Verify full end-to-end execution through mobile autofill, TOTP generation, and verification."""
    orchestrator, settings_svc, vault_svc, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True

    # 1. Enroll mobile number and TOTP secret with explicit automation opt-in
    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
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

    # 2. Mock Playwright flow:
    # Page starts at Stage 1, fills username, clicks submit, shows OTP input, fills OTP, redirects to student dashboard
    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True

    mock_login_btn = MagicMock()
    mock_otp_input = MagicMock()
    mock_otp_input.is_visible.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"

    def selector_router(sel):
        if "username" in sel:
            return mock_username_input
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel or "submit" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = selector_router
    mock_page.evaluate.return_value = None  # No error banner

    def mock_click(*args, **kwargs):
        # Simulate redirect upon successful TOTP submission
        mock_page.url = "https://mrei.icloudems.com/corecampus/student/student_dashboard.php"

    mock_login_btn.click.side_effect = mock_click

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.AUTHENTICATED
        assert res.step == "AUTHENTICATED_AND_VERIFIED"
        assert res.success is True
        assert res.redirected is True


def test_login_orchestrator_rejects_unauthorized_origin(test_services):
    """AttendPlan must immediately reject login on unallowed origins."""
    orchestrator, _, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://phishing-site.example.com/login"

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.FAILED
        assert res.step == "SECURITY_ORIGIN_VIOLATION"


def test_login_orchestrator_status_session_expired(test_services):
    """When session status returns SESSION_EXPIRED, orchestrator returns SESSION_EXPIRED."""
    orchestrator, _, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True

    mock_info = MagicMock()
    mock_info.state.value = "SESSION_EXPIRED"
    mock_info.otp_challenge_active = False
    mock_info.current_url = "https://mrei.icloudems.com/corecampus/session_expired.php"
    mock_info.details = "Student session expired."
    session_mgr.check_session_status.return_value = mock_info

    status = orchestrator.get_status()
    assert status.state == LoginState.SESSION_EXPIRED
    assert status.step == "SESSION_EXPIRED"


def test_login_orchestrator_expired_session_recovery(test_services):
    """When page is on an expired session, orchestrator recovers by navigating to portal entry."""
    orchestrator, settings_svc, vault_svc, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True

    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
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

    # Page starts on expired session URL
    mock_page = MagicMock()
    mock_page.url = "https://mrei.icloudems.com/corecampus/session_expired.php"

    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True
    mock_login_btn = MagicMock()
    mock_otp_input = MagicMock()
    mock_otp_input.is_visible.return_value = True

    def selector_router(sel):
        if "username" in sel:
            return mock_username_input
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel or "submit" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = selector_router
    mock_page.evaluate.return_value = None

    def mock_goto(url):
        mock_page.url = url

    mock_page.goto.side_effect = mock_goto

    def mock_click(*args, **kwargs):
        mock_page.url = "https://mrei.icloudems.com/corecampus/student/student_dashboard.php"

    mock_login_btn.click.side_effect = mock_click

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.AUTHENTICATED
        assert res.success is True
        mock_page.goto.assert_called_with("https://mrei.icloudems.com/corecampus/index.php")


def test_login_orchestrator_prevention_of_repeated_mobile_submission(test_services):
    """When mobile form displays an existing error banner, prevent repeated submissions."""
    orchestrator, settings_svc, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True
    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
            auto_mobile_autofill=True,
            auto_login_continuation=True,
        )
    )

    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True
    mock_login_btn = MagicMock()

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"

    def selector_router(sel):
        if "username" in sel:
            return mock_username_input
        if "login" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = selector_router
    # Error banner already present from prior failed submission
    mock_page.evaluate.return_value = "Invalid username or password."

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.FAILED
        assert res.step == "MOBILE_SUBMIT_PREVENTED_REPEATED"
        assert "Repeated submission blocked" in res.message
        # Submit button must NOT be clicked!
        mock_login_btn.click.assert_not_called()


def test_login_orchestrator_prevention_of_repeated_totp_submission(test_services):
    """When TOTP challenge form displays an existing error banner, prevent repeated submissions."""
    orchestrator, settings_svc, vault_svc, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True
    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
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

    def selector_router(sel):
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel or "submit" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = selector_router
    # Existing rejection banner from prior OTP submission
    mock_page.evaluate.return_value = "Invalid authenticator code."

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.FAILED
        assert res.step == "TOTP_SUBMIT_PREVENTED_REPEATED"
        assert "Repeated submissions blocked" in res.message
        mock_login_btn.click.assert_not_called()


def test_login_orchestrator_auto_mobile_autofill_disabled(test_services):
    """When auto_mobile_autofill is disabled, orchestrator halts for manual entry."""
    orchestrator, settings_svc, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True
    settings_svc.save_settings(
        AppSettings(saved_mobile_number="9876543210", auto_mobile_autofill=False)
    )

    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"
    mock_page.query_selector.side_effect = lambda sel: mock_username_input if "username" in sel else None
    mock_page.evaluate.return_value = None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.MANUAL_ACTION_REQUIRED
        assert res.step == "AUTOFILL_DISABLED"
        assert "disabled in Settings" in res.message


def test_login_orchestrator_auto_login_continuation_disabled(test_services):
    """When auto_login_continuation is False, autofills mobile but pauses before submit."""
    orchestrator, settings_svc, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True
    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
            auto_mobile_autofill=True,
            auto_login_continuation=False,
        )
    )

    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True
    mock_login_btn = MagicMock()

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"

    def selector_router(sel):
        if "username" in sel:
            return mock_username_input
        if "login" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = selector_router
    mock_page.evaluate.return_value = None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.MANUAL_ACTION_REQUIRED
        assert res.step == "CONTINUATION_PAUSED"
        assert res.success is True
        mock_username_input.fill.assert_called_with("9876543210")
        mock_login_btn.click.assert_not_called()


def test_login_orchestrator_mobile_rejected_by_server(test_services):
    """When server returns error after mobile submit, halt with FAILED state."""
    orchestrator, settings_svc, _, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True
    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
            auto_mobile_autofill=True,
            auto_login_continuation=True,
        )
    )

    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True
    mock_login_btn = MagicMock()

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"

    def selector_router(sel):
        if "username" in sel:
            return mock_username_input
        if "login" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = selector_router

    # Initial check has no error, but evaluation after click returns error banner
    eval_calls = [None, "User does not exist or mobile number unregistered."]
    mock_page.evaluate.side_effect = lambda script: eval_calls.pop(0) if eval_calls else None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.FAILED
        assert res.step == "MOBILE_SUBMIT_REJECTED"
        assert "User does not exist" in res.message


def test_login_orchestrator_totp_rejected_by_server(test_services):
    """When server rejects submitted TOTP code, halt with FAILED state and abort retries."""
    orchestrator, settings_svc, vault_svc, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True
    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
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
    mock_submit_btn = MagicMock()

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/login-actions/authenticate"

    def selector_router(sel):
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel or "submit" in sel:
            return mock_submit_btn
        return None

    mock_page.query_selector.side_effect = selector_router

    # First check (pre-submit) has no error; second check (post-submit) has rejection error
    eval_calls = [None, "Invalid authenticator code. 2 attempts remaining."]
    mock_page.evaluate.side_effect = lambda script: eval_calls.pop(0) if eval_calls else None

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        assert res.state == LoginState.FAILED
        assert res.step == "TOTP_REJECTED_BY_SERVER"
        assert "Automatic retries aborted" in res.message


def test_login_orchestrator_no_credential_leakage(test_services):
    """Assert that LoginOrchestrationResult never exposes raw mobile or TOTP secret."""
    orchestrator, settings_svc, vault_svc, session_mgr = test_services
    session_mgr.is_cdp_reachable.return_value = True
    synthetic_phone = "9876543210"
    settings_svc.save_settings(
        AppSettings(
            saved_mobile_number=synthetic_phone,
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

    mock_username_input = MagicMock()
    mock_username_input.is_visible.return_value = True
    mock_login_btn = MagicMock()
    mock_otp_input = MagicMock()
    mock_otp_input.is_visible.return_value = True

    mock_page = MagicMock()
    mock_page.url = "https://usermanagement.icloudems.com/auth/realms/mrei/protocol/openid-connect/auth"

    def selector_router(sel):
        if "username" in sel:
            return mock_username_input
        if "otp" in sel or "totp" in sel:
            return mock_otp_input
        if "login" in sel or "submit" in sel:
            return mock_login_btn
        return None

    mock_page.query_selector.side_effect = selector_router
    mock_page.evaluate.return_value = None

    def mock_click(*args, **kwargs):
        mock_page.url = "https://mrei.icloudems.com/corecampus/student/student_dashboard.php"

    mock_login_btn.click.side_effect = mock_click

    mock_browser = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.pages = [mock_page]
    mock_browser.contexts = [mock_ctx]

    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        mock_p_instance = MagicMock()
        mock_p_instance.chromium.connect_over_cdp.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p_instance

        res = orchestrator.orchestrate_login()
        result_dump = res.model_dump_json()

        # Mobile number must NEVER appear in the public orchestration result
        assert synthetic_phone not in result_dump
        # Secret must NEVER appear in the public orchestration result
        assert SYNTHETIC_SECRET not in result_dump
        assert res.has_saved_mobile is True
        assert res.is_totp_enrolled is True

