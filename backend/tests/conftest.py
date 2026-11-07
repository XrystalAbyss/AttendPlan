"""Always isolate ordinary tests from the user's database, settings and live browser."""
import os
import tempfile
from pathlib import Path

import pytest

# Applied before application imports during test collection, even if the caller has
# a production ATTENDPLAN_DB_PATH configured in their shell.
_sandbox = tempfile.TemporaryDirectory(prefix="attendplan-tests-", ignore_cleanup_errors=True)
os.environ["ATTENDPLAN_DB_PATH"] = str(Path(_sandbox.name) / "app.sqlite3")
os.environ["ATTENDPLAN_STARTUP_SETTINGS_PATH"] = str(Path(_sandbox.name) / "startup.json")
os.environ["ATTENDPLAN_SETTINGS_PATH"] = str(Path(_sandbox.name) / "settings.json")


@pytest.fixture(autouse=True)
def no_live_portal_in_unit_tests(monkeypatch):
    from app.adapters.portal_session import PortalSessionManager
    monkeypatch.setattr(PortalSessionManager, "is_cdp_reachable", lambda self: False)
    monkeypatch.setattr(PortalSessionManager, "get_open_tabs", lambda self: [])


@pytest.fixture(autouse=True)
def isolated_credential_backend(monkeypatch):
    from app.services import totp_vault_service as vault
    from app.api import routes
    from tests.test_totp_vault import MockSecureKeyring

    backend = MockSecureKeyring()
    monkeypatch.setattr(vault, "_SECURE_BACKEND_TYPE", MockSecureKeyring)
    monkeypatch.setattr(vault.keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(routes._vault_service, "keyring_backend", backend)
