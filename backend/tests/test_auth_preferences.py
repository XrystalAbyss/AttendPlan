"""Conflicting legacy flags must respect the user's canonical vault opt-in."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.domain.totp_models import TotpAccountCandidate
from app.services.login_orchestrator import LoginOrchestrator
from app.services.settings_service import AppSettings, SettingsService
from app.services.totp_vault_service import TotpVaultService
from tests.test_totp_vault import MockSecureKeyring, SYNTHETIC_SECRET


@pytest.mark.parametrize("enabled", [True, False])
def test_vault_preference_is_canonical_with_conflicting_old_app_flags(
    tmp_path, enabled
):
    settings = SettingsService(tmp_path / "settings.json")
    settings.save_settings(
        AppSettings(
            saved_mobile_number="9876543210",
            auto_mobile_autofill=True,
            auto_login_continuation=True,
            auto_totp_autofill=not enabled,
            auto_totp_submit=not enabled,
        )
    )
    vault = TotpVaultService(tmp_path / "metadata.json", MockSecureKeyring())
    candidate = TotpAccountCandidate(
        issuer="Synthetic",
        account_name="Synthetic",
        secret_base32=SYNTHETIC_SECRET,
        source_type="MANUAL_BASE32",
    )
    vault.enroll(candidate, auto_autofill=enabled, auto_submit=enabled)
    page = MagicMock()
    page.url = "https://usermanagement.icloudems.com/auth/login"
    page.evaluate.return_value = None
    otp = MagicMock()
    otp.is_visible.return_value = True
    submit = MagicMock()

    def query(selector):
        if "otp" in selector:
            return otp
        if "submit" in selector or "kc-login" in selector:
            return submit
        return None

    page.query_selector.side_effect = query
    submit.click.side_effect = lambda **kwargs: setattr(
        page,
        "url",
        "https://mrei.icloudems.com/corecampus/student/student_dashboard.php",
    )
    browser = MagicMock()
    browser.contexts[0].pages = [page]
    manager = MagicMock()
    manager.is_cdp_reachable.return_value = True
    orchestrator = LoginOrchestrator(manager, settings, vault)
    with patch("playwright.sync_api.sync_playwright") as playwright, patch.object(
        vault,
        "generate_current_code",
        return_value=SimpleNamespace(code="123456", time_remaining_seconds=20),
    ) as generate:
        playwright.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value = browser
        result = orchestrator.orchestrate_login()
        if enabled:
            assert result.state.value == "AUTHENTICATED"
            generate.assert_called_once()
            otp.fill.assert_any_call("123456")
        else:
            generate.assert_not_called()
            otp.fill.assert_not_called()
