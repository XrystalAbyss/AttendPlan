"""Unit tests for TotpVaultService, Windows Credential Manager isolation, and fail-closed policies."""

import json
from pathlib import Path
from typing import Any
import pytest
from keyring.backend import KeyringBackend


from app.domain.totp_models import (
    SecureVaultUnavailableError,
    TotpAccountCandidate,
)
from app.services.totp_vault_service import (
    VAULT_KEY_IDENTIFIER,
    VAULT_SERVICE_NAME,
    TotpVaultService,
    is_secure_keyring_backend,
)

SYNTHETIC_SECRET = "JBSWY3DPEHPK3PXP"  # Base32 for "Hello!\xde\xad"


class MockSecureKeyring(KeyringBackend):
    """Simulates native Windows Credential Manager (WinVaultKeyring)."""
    priority: Any = 5.0

    def __init__(self):
        self._vault: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._vault.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._vault[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self._vault.pop((service, username), None)


class InsecurePlaintextKeyring(KeyringBackend):
    """Simulates insecure plaintext fallback that AttendPlan MUST reject."""
    priority: Any = 0.0



    def get_password(self, service: str, username: str) -> str | None:
        return None

    def set_password(self, service: str, username: str, password: str) -> None:
        pass

    def delete_password(self, service: str, username: str) -> None:
        pass



def test_is_secure_keyring_backend():
    """Verify classification of keyring backends."""
    assert is_secure_keyring_backend(MockSecureKeyring()) is True
    assert is_secure_keyring_backend(InsecurePlaintextKeyring()) is False


def test_native_windows_backend_type_is_accepted_without_vault_io(monkeypatch):
    from app.services import totp_vault_service as module
    native = pytest.importorskip("keyring.backends.Windows").WinVaultKeyring
    monkeypatch.setattr(module, "_SECURE_BACKEND_TYPE", native)
    # Type inspection only: do not initialize, query, or mutate a native vault.
    assert is_secure_keyring_backend(object.__new__(native)) is True
    assert is_secure_keyring_backend(MockSecureKeyring()) is False
    monkeypatch.setattr(module, "_SECURE_BACKEND_TYPE", None)
    assert is_secure_keyring_backend(object.__new__(native)) is False


@pytest.mark.parametrize("name", ["WindowsStore", "MockVault", "PositivePriorityStore"])
def test_unknown_backends_are_rejected_before_secret_access(tmp_path, name):
    class UntrustedBackend(InsecurePlaintextKeyring):
        priority = 10

        def get_password(self, service, username):
            pytest.fail("Rejected backend must never read a secret")

        def set_password(self, service, username, password):
            pytest.fail("Rejected backend must never store a secret")

    backend = type(name, (UntrustedBackend,), {})()
    assert is_secure_keyring_backend(backend) is False
    vault = TotpVaultService(tmp_path / "metadata.json", backend)
    with pytest.raises(SecureVaultUnavailableError):
        vault.enroll(TotpAccountCandidate(
            issuer="Synthetic", account_name="Synthetic", secret_base32=SYNTHETIC_SECRET,
        ))
    assert not (tmp_path / "metadata.json").exists()


def test_vault_fail_closed_on_insecure_backend(tmp_path: Path):
    """AttendPlan must refuse to store secrets if secure OS vault is unavailable."""
    meta_path = tmp_path / "totp_metadata.json"
    vault = TotpVaultService(metadata_path=meta_path, keyring_backend=InsecurePlaintextKeyring())

    cand = TotpAccountCandidate(
        issuer="iCloudEMS",
        account_name="student@uni.edu",
        secret_base32=SYNTHETIC_SECRET,
    )

    with pytest.raises(SecureVaultUnavailableError, match="Windows Credential Manager is unavailable"):
        vault.enroll(cand)


def test_vault_full_enrollment_lifecycle(tmp_path: Path):
    """Verify normal enrollment, storage isolation, verification, and deletion."""
    meta_path = tmp_path / "totp_metadata.json"
    mock_keyring = MockSecureKeyring()
    vault = TotpVaultService(metadata_path=meta_path, keyring_backend=mock_keyring)

    # 1. Initially not enrolled
    assert vault.is_enrolled() is False
    assert vault.get_masked_account_metadata() is None

    # 2. Enroll candidate
    cand = TotpAccountCandidate(
        issuer="iCloudEMS",
        account_name="student1234@uni.edu",
        secret_base32=SYNTHETIC_SECRET,
    )
    meta = vault.enroll(cand, auto_autofill=True, auto_submit=False)

    assert meta.masked_account == "st***du"
    assert meta.issuer == "iCloudEMS"
    assert vault.is_enrolled() is True

    # 3. Invariant: Secret key is stored ONLY in Windows Credential Manager, NEVER in JSON file
    assert mock_keyring.get_password(VAULT_SERVICE_NAME, VAULT_KEY_IDENTIFIER) == SYNTHETIC_SECRET

    with open(meta_path, "r", encoding="utf-8") as f:
        meta_json = json.load(f)
    assert "secret" not in meta_json
    assert "secret_base32" not in meta_json
    assert meta_json["masked_account"] == "st***du"

    # 4. Generate code in-memory (backend automation only)
    code_res = vault.generate_current_code(min_safety_margin_seconds=0, wait_if_near_expiry=False)
    assert len(code_res.code) == 6
    assert code_res.code.isdigit()

    # 5. Verify enrollment code
    assert vault.verify_enrollment(code_res.code) is True
    assert vault.verify_enrollment("000000") is False

    # 6. Update automation settings
    updated_meta = vault.update_automation_settings(auto_submit=True)
    assert updated_meta is not None
    assert updated_meta.auto_submit_enabled is True

    # 7. Remove enrollment
    assert vault.remove_enrollment() is True
    assert vault.is_enrolled() is False
    assert not meta_path.exists()
    assert mock_keyring.get_password(VAULT_SERVICE_NAME, VAULT_KEY_IDENTIFIER) is None
