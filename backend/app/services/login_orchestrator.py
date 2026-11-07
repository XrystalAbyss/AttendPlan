"""Complete Login Orchestrator for University Keycloak Student Authentication.

Orchestrates the entire authentication lifecycle:
    EXISTING SESSION CHECK
        ↓
    STUDENT LOGIN
        ↓
    AUTOFILL SAVED MOBILE NUMBER
        ↓
    SUBMIT MOBILE NUMBER
        ↓
    WAIT FOR AUTHENTICATOR CHALLENGE
        ↓
    GENERATE TOTP FROM WINDOWS VAULT
        ↓
    AUTOFILL AND SUBMIT TOTP
        ↓
    VERIFY AUTHENTICATED STUDENT SESSION
        ↓
    RETURN TO ATTENDPLAN SYNC CENTER

Strict Security Invariants:
1. Target only allowlisted university authentication hosts (usermanagement.icloudems.com, mrei.icloudems.com).
2. Mobile number retrieved strictly from local settings (%LOCALAPPDATA%/AttendPlan/settings.json).
3. Authenticator TOTP generated strictly in-memory from Windows Credential Manager.
4. Never log, commit, or leak student mobile numbers or TOTP codes.
5. If CAPTCHA or unexpected challenges appear, halt and transition to MANUAL_ACTION_REQUIRED.
6. Prevent repeated submissions to avoid university account lockouts.
"""

from __future__ import annotations

import logging
import urllib.parse
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.adapters.portal_session import (
    ALLOWED_AUTH_HOSTS,
    select_authentication_page,
    PortalSessionManager,
)
from app.domain.totp_models import (
    TotpOriginSecurityError,
)
from app.services.settings_service import SettingsService
from app.services.totp_vault_service import TotpVaultService

logger = logging.getLogger(__name__)


class LoginState(str, Enum):
    """Authoritative states of the authentication orchestrator."""
    DISCONNECTED = "DISCONNECTED"
    SESSION_CHECKING = "SESSION_CHECKING"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    ENTERING_MOBILE = "ENTERING_MOBILE"
    WAITING_FOR_TOTP = "WAITING_FOR_TOTP"
    SUBMITTING_TOTP = "SUBMITTING_TOTP"
    VERIFYING_SESSION = "VERIFYING_SESSION"
    AUTHENTICATED = "AUTHENTICATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    MANUAL_ACTION_REQUIRED = "MANUAL_ACTION_REQUIRED"
    FAILED = "FAILED"


class LoginOrchestrationResult(BaseModel):
    """Result returned by the login orchestrator."""
    state: LoginState
    step: str
    success: bool
    redirected: bool
    message: str
    current_url: Optional[str] = None
    has_saved_mobile: bool = False
    is_totp_enrolled: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


def is_authenticated_student_page(page: Any) -> bool:
    """Verify an actual authenticated student session without relying solely on '/student/' in URL."""
    try:
        url = page.url.lower()
        if urllib.parse.urlsplit(url).hostname not in ALLOWED_AUTH_HOSTS:
            return False
    except Exception:
        return False

    # 1. Never claim authenticated if still on login/auth or portal entry pages
    login_markers = [
        "/auth/",
        "keycloak",
        "login",
        "authenticate",
        "openid-connect",
        "corecampus/index.php",
    ]
    if any(marker in url for marker in login_markers):
        return False

    # 2. Strong explicit authenticated view identifiers
    strong_views = [
        "student_dashboard",
        "subwise_attendace",
        "myattendance",
        "allsubject",
        "student_index",
        "student_home",
    ]
    if any(view in url for view in strong_views):
        return True

    # 3. If URL contains /student/, require an authorized DOM dashboard indicator
    if "/student/" in url:
        try:
            has_indicator = page.evaluate(
                """() => {
                    const hasLogout = !!document.querySelector("a[href*='logout'], #logout, .logout");
                    const hasStudentNav = !!document.querySelector(".student-menu, .nav-student, #student_profile, .profile-name, .user-name");
                    const bodyText = document.body ? document.body.innerText.toLowerCase() : "";
                    const titleText = document.title ? document.title.toLowerCase() : "";
                    return hasLogout || hasStudentNav || bodyText.includes("student dashboard") || titleText.includes("student dashboard");
                }"""
            )
            return bool(has_indicator)
        except Exception:
            return False

    return False


class LoginOrchestrator:
    """Manages full Keycloak authentication flow using Playwright CDP connection."""

    def __init__(
        self,
        session_manager: Optional[PortalSessionManager] = None,
        settings_service: Optional[SettingsService] = None,
        vault_service: Optional[TotpVaultService] = None,
    ) -> None:
        self.session_manager = session_manager or PortalSessionManager()
        self.settings_service = settings_service or SettingsService()
        self.vault_service = vault_service or TotpVaultService()
        self._current_state = LoginState.DISCONNECTED
        self._last_result: Optional[LoginOrchestrationResult] = None
        self._mobile_submission_attempted: bool = False
        self._totp_submission_attempted: bool = False

    @property
    def current_state(self) -> LoginState:
        return self._current_state

    def get_status(self) -> LoginOrchestrationResult:
        """Inspect current status without mutating login state."""
        has_mobile = bool(self.settings_service.load_settings().saved_mobile_number)
        is_totp = self.vault_service.is_enrolled()

        if not self.session_manager.is_cdp_reachable():
            self._current_state = LoginState.DISCONNECTED
            return LoginOrchestrationResult(
                state=LoginState.DISCONNECTED,
                step="CHECK_BROWSER",
                success=False,
                redirected=False,
                message="Dedicated Chrome browser is not connected on port 9222.",
                has_saved_mobile=has_mobile,
                is_totp_enrolled=is_totp,
            )

        info = self.session_manager.check_session_status()
        if info.state.value == "AUTHENTICATED":
            self._current_state = LoginState.AUTHENTICATED
            return LoginOrchestrationResult(
                state=LoginState.AUTHENTICATED,
                step="SESSION_VERIFIED",
                success=True,
                redirected=True,
                message="Active authenticated student session verified.",
                current_url=info.current_url,
                has_saved_mobile=has_mobile,
                is_totp_enrolled=is_totp,
            )

        if info.otp_challenge_active:
            self._current_state = LoginState.WAITING_FOR_TOTP
            return LoginOrchestrationResult(
                state=LoginState.WAITING_FOR_TOTP,
                step="TOTP_CHALLENGE",
                success=False,
                redirected=False,
                message="Keycloak Google Authenticator (TOTP) challenge is waiting for input.",
                current_url=info.current_url,
                has_saved_mobile=has_mobile,
                is_totp_enrolled=is_totp,
            )

        if info.state.value == "SESSION_EXPIRED":
            self._current_state = LoginState.SESSION_EXPIRED
            return LoginOrchestrationResult(
                state=LoginState.SESSION_EXPIRED,
                step="SESSION_EXPIRED",
                success=False,
                redirected=False,
                message=info.details or "Student portal session has expired. Automated login recovery available.",
                current_url=info.current_url,
                has_saved_mobile=has_mobile,
                is_totp_enrolled=is_totp,
            )

        return LoginOrchestrationResult(
            state=self._current_state if self._current_state != LoginState.DISCONNECTED else LoginState.LOGIN_REQUIRED,
            step="STANDBY",
            success=False,
            redirected=False,
            message=info.details or "Portal login required.",
            current_url=info.current_url,
            has_saved_mobile=has_mobile,
            is_totp_enrolled=is_totp,
        )

    def orchestrate_login(self, force_submit: Optional[bool] = None) -> LoginOrchestrationResult:
        """Execute the end-to-end automated login sequence."""
        settings = self.settings_service.load_settings()
        has_mobile = bool(settings.saved_mobile_number)
        is_totp = self.vault_service.is_enrolled()

        # Reset submission tracking for this orchestration run
        self._mobile_submission_attempted = False
        self._totp_submission_attempted = False

        # Step 1: Verify browser reachability
        if not self.session_manager.is_cdp_reachable():
            self._current_state = LoginState.DISCONNECTED
            return LoginOrchestrationResult(
                state=LoginState.DISCONNECTED,
                step="BROWSER_CHECK",
                success=False,
                redirected=False,
                message="Dedicated Chrome browser is not running. Please launch the browser from AttendPlan.",
                has_saved_mobile=has_mobile,
                is_totp_enrolled=is_totp,
            )

        self._current_state = LoginState.SESSION_CHECKING

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(self.session_manager.cdp_url)
            try:
                if not browser.contexts:
                    self._current_state = LoginState.FAILED
                    return LoginOrchestrationResult(
                        state=LoginState.FAILED,
                        step="CONTEXT_CHECK",
                        success=False,
                        redirected=False,
                        message="No browser contexts available in dedicated Chrome instance.",
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=is_totp,
                    )

                ctx = browser.contexts[0]

                # A visible MFA challenge has priority over a stale dashboard tab.
                auth_page = select_authentication_page(ctx.pages, require_otp=True)
                if auth_page is None:
                    for page in ctx.pages:
                        if is_authenticated_student_page(page):
                            self._current_state = LoginState.AUTHENTICATED
                            return LoginOrchestrationResult(
                                state=LoginState.AUTHENTICATED, step="EXISTING_SESSION_REUSED", success=True,
                                redirected=True, message="Existing authenticated session detected. Skipping login sequence.",
                                current_url=page.url, has_saved_mobile=has_mobile, is_totp_enrolled=is_totp,
                            )
                    auth_page = select_authentication_page(ctx.pages)
                if auth_page is None:
                    if ctx.pages:
                        existing_host = urllib.parse.urlsplit(ctx.pages[0].url).hostname or ""
                        if existing_host not in {"", "127.0.0.1", "localhost"}:
                            raise TotpOriginSecurityError("Refusing automated login on unauthorized origin.")
                    auth_page = ctx.new_page()
                    auth_page.goto("https://mrei.icloudems.com/corecampus/index.php")
                    auth_page.wait_for_timeout(2000)

                # Verify origin security allowlist
                parsed = urllib.parse.urlparse(auth_page.url)
                if parsed.hostname and parsed.hostname not in ALLOWED_AUTH_HOSTS:
                    self._current_state = LoginState.FAILED
                    raise TotpOriginSecurityError(
                        f"Refusing automated login on unauthorized origin: {parsed.hostname}. "
                        f"Allowed origins: {', '.join(sorted(ALLOWED_AUTH_HOSTS))}"
                    )

                # Detect and recover from expired session
                url_lower = auth_page.url.lower()
                is_session_expired = (
                    "timeout" in url_lower
                    or "session_expired" in url_lower
                    or "expired" in url_lower
                    or "error.php" in url_lower
                )
                if not is_session_expired and "corecampus" in url_lower:
                    try:
                        has_expired_text = auth_page.evaluate(
                            """() => {
                                const b = document.body ? document.body.innerText.toLowerCase() : "";
                                return b.includes("session expired") || b.includes("session has expired") || b.includes("please login again");
                            }"""
                        )
                        if isinstance(has_expired_text, bool) and has_expired_text:
                            is_session_expired = True
                    except Exception:
                        pass

                if is_session_expired:
                    logger.info("Expired student session detected. Initiating recovery to university portal entry.")
                    self._current_state = LoginState.SESSION_EXPIRED
                    auth_page.goto("https://mrei.icloudems.com/corecampus/index.php")
                    auth_page.wait_for_timeout(2000)
                    self._current_state = LoginState.LOGIN_REQUIRED

                # Step 3: Check if on portal entry page (mrei.icloudems.com/corecampus/index.php)
                if "corecampus/index.php" in auth_page.url.lower():
                    # Click Student Login button to redirect to Keycloak
                    student_login_btn = auth_page.query_selector(
                        "a[href*='keycloak'], a[href*='student'], button:has-text('Student'), a:has-text('Student')"
                    )
                    if student_login_btn:
                        student_login_btn.click()
                        auth_page.wait_for_timeout(2500)
                # Re-verify origin after potential redirect

                parsed = urllib.parse.urlparse(auth_page.url)
                if parsed.hostname and parsed.hostname not in ALLOWED_AUTH_HOSTS:
                    self._current_state = LoginState.FAILED
                    return LoginOrchestrationResult(
                        state=LoginState.FAILED,
                        step="ORIGIN_VERIFICATION",
                        success=False,
                        redirected=False,
                        message=f"Browser redirected to unauthorized origin: {parsed.hostname}",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=is_totp,
                    )

                # Step 4: First Factor - Mobile Number Identification
                # Verified locator from live Keycloak inspection: input#username, name='username'
                username_input = auth_page.query_selector("input#username, input[name='username']")

                # Check if we are at Stage 1 (Mobile number input form)
                if username_input and username_input.is_visible():
                    self._current_state = LoginState.ENTERING_MOBILE

                    # Prevent repeated mobile submissions: check for existing error banners
                    existing_error = auth_page.evaluate(
                        """() => {
                            const el = document.querySelector('.alert-error, .kc-feedback-text, #input-error, .alert-danger');
                            return el ? el.innerText.trim() : null;
                        }"""
                    )
                    if (isinstance(existing_error, str) and existing_error.strip()) or self._mobile_submission_attempted:
                        err_text = str(existing_error) if existing_error else "Previous mobile submission failed or is pending."
                        self._current_state = LoginState.FAILED
                        return LoginOrchestrationResult(
                            state=LoginState.FAILED,
                            step="MOBILE_SUBMIT_PREVENTED_REPEATED",
                            success=False,
                            redirected=False,
                            message=f"Keycloak mobile submission error: {err_text}. Repeated submission blocked to prevent account lockout.",
                            current_url=auth_page.url,
                            has_saved_mobile=True,
                            is_totp_enrolled=is_totp,
                        )

                    if not has_mobile or not settings.saved_mobile_number:
                        self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                        return LoginOrchestrationResult(
                            state=LoginState.MANUAL_ACTION_REQUIRED,
                            step="MOBILE_INPUT_REQUIRED",
                            success=False,
                            redirected=False,
                            message="Mobile number required. Please configure your registered 10-digit mobile number in Settings > Authentication.",
                            current_url=auth_page.url,
                            has_saved_mobile=False,
                            is_totp_enrolled=is_totp,
                        )

                    if not settings.auto_mobile_autofill:
                        self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                        return LoginOrchestrationResult(
                            state=LoginState.MANUAL_ACTION_REQUIRED,
                            step="AUTOFILL_DISABLED",
                            success=False,
                            redirected=False,
                            message="Automatic mobile autofill is disabled in Settings. Please enter your mobile number manually.",
                            current_url=auth_page.url,
                            has_saved_mobile=True,
                            is_totp_enrolled=is_totp,
                        )

                    # Autofill the saved mobile number
                    username_input.fill("")
                    username_input.fill(settings.saved_mobile_number)

                    if not settings.auto_login_continuation:
                        self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                        return LoginOrchestrationResult(
                            state=LoginState.MANUAL_ACTION_REQUIRED,
                            step="CONTINUATION_PAUSED",
                            success=True,
                            redirected=False,
                            message="Saved mobile number autofilled. Continuation paused as requested in Settings.",
                            current_url=auth_page.url,
                            has_saved_mobile=True,
                            is_totp_enrolled=is_totp,
                        )

                    # Submit mobile number using verified submit button: input#login, input[name='login']
                    login_btn = auth_page.query_selector(
                        "input#login, input[name='login'], button#kc-login, input[type='submit']"
                    )
                    if not login_btn:
                        self._current_state = LoginState.FAILED
                        return LoginOrchestrationResult(
                            state=LoginState.FAILED,
                            step="SUBMIT_BUTTON_NOT_FOUND",
                            success=False,
                            redirected=False,
                            message="Could not find submit button on Keycloak mobile login form.",
                            current_url=auth_page.url,
                            has_saved_mobile=True,
                            is_totp_enrolled=is_totp,
                        )

                    self._mobile_submission_attempted = True
                    login_btn.click()
                    auth_page.wait_for_timeout(2500)

                    # Check for immediate form error banners
                    error_banner = auth_page.evaluate(
                        """() => {
                            const el = document.querySelector('.alert-error, .kc-feedback-text, #input-error, .alert-danger');
                            return el ? el.innerText.trim() : null;
                        }"""
                    )
                    if error_banner:
                        self._current_state = LoginState.FAILED
                        return LoginOrchestrationResult(
                            state=LoginState.FAILED,
                            step="MOBILE_SUBMIT_REJECTED",
                            success=False,
                            redirected=False,
                            message=f"Keycloak rejected mobile number submission: {error_banner}",
                            current_url=auth_page.url,
                            has_saved_mobile=True,
                            is_totp_enrolled=is_totp,
                        )

                # Step 5: Second Factor - Authenticator TOTP Challenge
                self._current_state = LoginState.WAITING_FOR_TOTP

                # Check for anti-bot / CAPTCHA barriers
                captcha_el = auth_page.query_selector(".g-recaptcha, iframe[src*='recaptcha'], iframe[src*='turnstile'], #captcha")
                if captcha_el and captcha_el.is_visible():
                    self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                    return LoginOrchestrationResult(
                        state=LoginState.MANUAL_ACTION_REQUIRED,
                        step="CAPTCHA_DETECTED",
                        success=False,
                        redirected=False,
                        message="CAPTCHA challenge detected. Please complete the CAPTCHA in Chrome.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=is_totp,
                    )

                # Verified OTP input locators on Keycloak
                otp_input = auth_page.query_selector(
                    "input#otp, input[name='otp'], input#totp, input[name='totp'], input[name='login-otp'], input[autocomplete='one-time-code']"
                )

                if not otp_input or not otp_input.is_visible():
                    # Check if already authenticated (some portals do not require MFA if session cookie remains)
                    if is_authenticated_student_page(auth_page):
                        self._current_state = LoginState.AUTHENTICATED
                        return LoginOrchestrationResult(
                            state=LoginState.AUTHENTICATED,
                            step="AUTHENTICATED_WITHOUT_MFA",
                            success=True,
                            redirected=True,
                            message="Authenticated successfully. Redirected to student dashboard.",
                            current_url=auth_page.url,
                            has_saved_mobile=has_mobile,
                            is_totp_enrolled=is_totp,
                        )

                    self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                    return LoginOrchestrationResult(
                        state=LoginState.MANUAL_ACTION_REQUIRED,
                        step="WAITING_FOR_STAGE",
                        success=False,
                        redirected=False,
                        message="Neither mobile nor TOTP challenge inputs are currently visible. Please check Chrome.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=is_totp,
                    )

                # Prevent repeated TOTP submissions: check for existing OTP rejection banners
                existing_otp_error = auth_page.evaluate(
                    """() => {
                        const err = document.querySelector('.alert-error, .kc-feedback-text, #input-error-otp, .alert-danger');
                        return err ? err.innerText.trim() : null;
                    }"""
                )
                if (isinstance(existing_otp_error, str) and existing_otp_error.strip()) or self._totp_submission_attempted:
                    err_msg = str(existing_otp_error) if existing_otp_error else "Previous TOTP submission failed."
                    self._current_state = LoginState.FAILED
                    return LoginOrchestrationResult(
                        state=LoginState.FAILED,
                        step="TOTP_SUBMIT_PREVENTED_REPEATED",
                        success=False,
                        redirected=False,
                        message=f"Keycloak TOTP submission error: {err_msg}. Repeated submissions blocked to prevent account lockout.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=True,
                    )

                # Step 6: Generate TOTP from Windows Vault
                if not is_totp:
                    self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                    return LoginOrchestrationResult(
                        state=LoginState.MANUAL_ACTION_REQUIRED,
                        step="TOTP_VAULT_NOT_ENROLLED",
                        success=False,
                        redirected=False,
                        message="Google Authenticator challenge detected, but no authenticator secret is enrolled in Windows Credential Manager. Please enter the OTP manually or enroll in Settings.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=False,
                    )

                totp_preferences = self.vault_service.get_masked_account_metadata()
                if not totp_preferences or not totp_preferences.auto_autofill_enabled:
                    self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                    return LoginOrchestrationResult(
                        state=LoginState.MANUAL_ACTION_REQUIRED,
                        step="TOTP_AUTOFILL_DISABLED",
                        success=False,
                        redirected=False,
                        message="Automatic TOTP autofill is disabled in Settings. Please enter the OTP manually.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=True,
                    )

                self._current_state = LoginState.SUBMITTING_TOTP

                # Generate code safely in memory (wait if < 4s remaining to avoid latency expiry)
                code_result = self.vault_service.generate_current_code(
                    min_safety_margin_seconds=4,
                    wait_if_near_expiry=True,
                )

                # Autofill code into field
                otp_input.fill("")
                otp_input.fill(code_result.code)

                should_submit = force_submit if force_submit is not None else totp_preferences.auto_submit_enabled
                if not should_submit:
                    self._current_state = LoginState.MANUAL_ACTION_REQUIRED
                    return LoginOrchestrationResult(
                        state=LoginState.MANUAL_ACTION_REQUIRED,
                        step="TOTP_FILLED_NO_SUBMIT",
                        success=True,
                        redirected=False,
                        message=f"TOTP code autofilled ({code_result.time_remaining_seconds}s remaining in window). Please click Log In in Chrome.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=True,
                    )

                # Submit TOTP form
                totp_submit_btn = auth_page.query_selector(
                    "input#kc-login, input#login, button#kc-login, input[type='submit']"
                )
                if totp_submit_btn:
                    self._totp_submission_attempted = True
                    try:
                        totp_submit_btn.click(timeout=3000)
                    except Exception:
                        auth_page.evaluate("b => b.click()", totp_submit_btn)

                self._current_state = LoginState.VERIFYING_SESSION
                auth_page.wait_for_timeout(3000)

                # Step 7: Verify Authenticated Session
                if is_authenticated_student_page(auth_page):
                    self._current_state = LoginState.AUTHENTICATED
                    return LoginOrchestrationResult(
                        state=LoginState.AUTHENTICATED,
                        step="AUTHENTICATED_AND_VERIFIED",
                        success=True,
                        redirected=True,
                        message="Full automated authentication sequence completed successfully. Student dashboard session active.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=True,
                    )

                # Check if server rejected the code
                server_error = auth_page.evaluate(
                    """() => {
                        const err = document.querySelector('.alert-error, .kc-feedback-text, #input-error-otp, .alert-danger');
                        return err ? err.innerText.trim() : null;
                    }"""
                )
                if isinstance(server_error, str) and server_error.strip():
                    self._current_state = LoginState.FAILED
                    return LoginOrchestrationResult(
                        state=LoginState.FAILED,
                        step="TOTP_REJECTED_BY_SERVER",
                        success=False,
                        redirected=False,
                        message=f"University authentication server rejected the TOTP code: {server_error}. Automatic retries aborted to prevent account lockout.",
                        current_url=auth_page.url,
                        has_saved_mobile=has_mobile,
                        is_totp_enrolled=True,
                    )

                # Still waiting or pending redirect
                self._current_state = LoginState.VERIFYING_SESSION
                return LoginOrchestrationResult(
                    state=LoginState.VERIFYING_SESSION,
                    step="REDIRECT_PENDING",
                    success=True,
                    redirected=False,
                    message="Credentials submitted. Awaiting portal session redirect.",
                    current_url=auth_page.url,
                    has_saved_mobile=has_mobile,
                    is_totp_enrolled=True,
                )

            except TotpOriginSecurityError as e:
                self._current_state = LoginState.FAILED
                return LoginOrchestrationResult(
                    state=LoginState.FAILED,
                    step="SECURITY_ORIGIN_VIOLATION",
                    success=False,
                    redirected=False,
                    message=str(e),
                    has_saved_mobile=has_mobile,
                    is_totp_enrolled=is_totp,
                )
            except Exception as e:
                self._current_state = LoginState.FAILED
                logger.error("Login orchestration stopped: %s", type(e).__name__)
                return LoginOrchestrationResult(
                    state=LoginState.FAILED,
                    step="UNEXPECTED_ERROR",
                    success=False,
                    redirected=False,
                    message="Login flow stopped. Check the private browser before retrying; authentication details are not logged.",
                    has_saved_mobile=has_mobile,
                    is_totp_enrolled=is_totp,
                )
            finally:
                browser.close()
