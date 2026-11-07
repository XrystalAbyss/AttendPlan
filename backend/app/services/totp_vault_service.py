"""Windows Credential Manager Vault for local-only TOTP storage.

Strict security invariants:
1. Secret key is stored ONLY in Windows Credential Manager via native WinVaultKeyring.
2. Fail-closed: If native secure credential manager is unavailable, raises SecureVaultUnavailableError.
3. No plaintext keyring fallbacks.
4. Secret is NEVER persisted in SQLite, JSON files, .env, or logs.
5. Secret is NEVER exposed over HTTP endpoints or returned to the frontend.
6. Only non-sensitive metadata (enrollment_id, issuer, masked_account, timestamps) is saved locally.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import keyring
from keyring.backend import KeyringBackend

try:
    from keyring.backends.Windows import WinVaultKeyring
    _SECURE_BACKEND_TYPE: type[KeyringBackend] | None = WinVaultKeyring
except ImportError:
    _SECURE_BACKEND_TYPE = None

from app.adapters.qr_parser import clean_base32_secret
from app.db.session import get_default_db_path
from app.domain.totp_engine import TotpEngine
from app.domain.totp_models import (
    SecureVaultUnavailableError,
    TotpAccountCandidate,
    TotpCodeResult,
    TotpEnrollmentError,
    TotpEnrollmentMetadata,
    TotpStatusResponse,
)

logger = logging.getLogger(__name__)

VAULT_SERVICE_NAME = "AttendPlan_University_MFA"
VAULT_KEY_IDENTIFIER = "student_portal_totp_secret"


def get_metadata_path() -> Path:
    """Resolve location for non-secret TOTP metadata in %LOCALAPPDATA%/AttendPlan."""
    db_path = get_default_db_path()
    return db_path.parent / "totp_metadata.json"


def is_secure_keyring_backend(backend: Optional[KeyringBackend] = None) -> bool:
    """Verify that active keyring backend is an encrypted OS-level store, not an insecure plaintext fallback."""
    b = backend if backend is not None else keyring.get_keyring()
    # A name or positive priority does not establish encrypted Windows storage.
    # Tests replace this type with an in-memory backend, never the real vault.
    return _SECURE_BACKEND_TYPE is not None and isinstance(b, _SECURE_BACKEND_TYPE)


class TotpVaultService:
    """Dedicated service for managing local-only authenticator secret in Windows Credential Manager."""

    def __init__(
        self,
        metadata_path: Optional[Path] = None,
        keyring_backend: Optional[KeyringBackend] = None,
    ) -> None:
        self.metadata_path = metadata_path or get_metadata_path()
        self.keyring_backend = keyring_backend or keyring.get_keyring()
        self._cached_metadata: Optional[TotpEnrollmentMetadata] = None

    def _assert_secure_storage(self) -> None:
        """Enforce fail-closed policy if native Windows Credential Manager is unavailable."""
        if not is_secure_keyring_backend(self.keyring_backend):
            raise SecureVaultUnavailableError(
                "Windows Credential Manager is unavailable or an insecure plaintext keyring is active. "
                "AttendPlan refuses to store TOTP secrets in insecure storage."
            )

    def is_enrolled(self) -> bool:
        """Check if an active enrollment exists in both Windows Credential Manager and local metadata."""
        meta = self.get_masked_account_metadata()
        if not meta:
            return False

        try:
            self._assert_secure_storage()
            secret = self.keyring_backend.get_password(VAULT_SERVICE_NAME, VAULT_KEY_IDENTIFIER)
            return bool(secret and secret.strip())
        except Exception:
            return False

    def get_masked_account_metadata(self) -> Optional[TotpEnrollmentMetadata]:
        """Read non-secret metadata from local JSON file. Never contains the secret key."""
        if self._cached_metadata:
            return self._cached_metadata

        if not self.metadata_path.exists():
            return None

        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cached_metadata = TotpEnrollmentMetadata(**data)
            return self._cached_metadata
        except Exception as e:
            logger.warning("Failed to read non-secret TOTP metadata: %s", e)
            return None

    def _save_metadata(self, metadata: TotpEnrollmentMetadata) -> None:
        """Save non-secret metadata to %LOCALAPPDATA%/AttendPlan/totp_metadata.json."""
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)
        self._cached_metadata = metadata

    def enroll(
        self,
        candidate: TotpAccountCandidate,
        auto_autofill: bool = False,
        auto_submit: bool = False,
    ) -> TotpEnrollmentMetadata:
        """Commit authenticator secret to Windows Credential Manager and save non-secret metadata.

        Validates the secret before committing to storage.
        """
        self._assert_secure_storage()

        # 1. Clean and validate Base32 secret
        clean_secret = clean_base32_secret(candidate.secret_base32)

        # 2. Test generation to ensure RFC 6238 compatibility
        try:
            TotpEngine.generate_current_code(
                secret_base32=clean_secret,
                digits=candidate.digits,
                period=candidate.period,
                algorithm=candidate.algorithm,
                wait_if_near_expiry=False,
            )
        except Exception as e:
            raise TotpEnrollmentError(f"Secret validation failed: cannot generate valid TOTP: {e}") from e

        # 3. Store secret ONLY in Windows Credential Manager
        try:
            self.keyring_backend.set_password(VAULT_SERVICE_NAME, VAULT_KEY_IDENTIFIER, clean_secret)
        except Exception as e:
            raise SecureVaultUnavailableError(f"Failed to persist secret to Windows Credential Manager: {e}") from e

        # 4. Create and save non-secret metadata
        meta = TotpEnrollmentMetadata(
            enrollment_id=str(uuid.uuid4()),
            issuer=candidate.issuer or "iCloudEMS",
            masked_account=candidate.masked_account,
            digits=candidate.digits,
            period=candidate.period,
            algorithm=candidate.algorithm,
            auto_autofill_enabled=auto_autofill,
            auto_submit_enabled=auto_submit,
        )
        self._save_metadata(meta)
        logger.info("Successfully enrolled student TOTP secret into Windows Credential Manager.")
        return meta

    def remove_enrollment(self) -> bool:
        """Delete secret from Windows Credential Manager and wipe metadata file."""
        deleted_from_keyring = False
        try:
            self.keyring_backend.delete_password(VAULT_SERVICE_NAME, VAULT_KEY_IDENTIFIER)
            deleted_from_keyring = True
        except Exception:
            pass

        if self.metadata_path.exists():
            try:
                os.remove(self.metadata_path)
            except Exception:
                pass

        self._cached_metadata = None
        logger.info("Removed student TOTP enrollment from local vault.")
        return deleted_from_keyring

    def update_automation_settings(
        self,
        auto_autofill: Optional[bool] = None,
        auto_submit: Optional[bool] = None,
    ) -> Optional[TotpEnrollmentMetadata]:
        """Update user preferences for automatic fill and submission."""
        meta = self.get_masked_account_metadata()
        if not meta:
            return None

        new_meta = TotpEnrollmentMetadata(
            enrollment_id=meta.enrollment_id,
            issuer=meta.issuer,
            masked_account=meta.masked_account,
            enrolled_at=meta.enrolled_at,
            digits=meta.digits,
            period=meta.period,
            algorithm=meta.algorithm,
            auto_autofill_enabled=auto_autofill if auto_autofill is not None else meta.auto_autofill_enabled,
            auto_submit_enabled=auto_submit if auto_submit is not None else meta.auto_submit_enabled,
        )
        self._save_metadata(new_meta)
        return new_meta

    def generate_current_code(
        self,
        min_safety_margin_seconds: int = 4,
        wait_if_near_expiry: bool = True,
    ) -> TotpCodeResult:
        """Retrieve secret from Windows Credential Manager and generate RFC 6238 code.

        CRITICAL SECURITY REQUIREMENT:
        This method is strictly for internal Python backend automation (e.g. Playwright form filling).
        It must NEVER be called by an HTTP route or exposed to the frontend!
        """
        self._assert_secure_storage()
        meta = self.get_masked_account_metadata()
        if not meta:
            raise TotpEnrollmentError("Cannot generate TOTP code: no authenticator enrolled in local vault.")

        secret = self.keyring_backend.get_password(VAULT_SERVICE_NAME, VAULT_KEY_IDENTIFIER)
        if not secret or not secret.strip():
            raise TotpEnrollmentError("TOTP secret not found in Windows Credential Manager.")

        return TotpEngine.generate_current_code(
            secret_base32=secret.strip(),
            digits=meta.digits,
            period=meta.period,
            algorithm=meta.algorithm,
            min_safety_margin_seconds=min_safety_margin_seconds,
            wait_if_near_expiry=wait_if_near_expiry,
        )

    def verify_enrollment(self, test_code: str) -> bool:
        """Verify candidate code against the currently enrolled secret."""
        meta = self.get_masked_account_metadata()
        if not meta:
            return False

        secret = self.keyring_backend.get_password(VAULT_SERVICE_NAME, VAULT_KEY_IDENTIFIER)
        if not secret:
            return False

        return TotpEngine.verify_code(
            secret_base32=secret.strip(),
            code_to_verify=test_code,
            digits=meta.digits,
            period=meta.period,
            algorithm=meta.algorithm,
            valid_window=1,
        )

    def get_enrollment_status(self) -> TotpStatusResponse:
        """Return non-sensitive status and diagnostics for UI rendering."""
        backend_name = type(self.keyring_backend).__name__
        is_secure = is_secure_keyring_backend(self.keyring_backend)
        enrolled = self.is_enrolled()
        meta = self.get_masked_account_metadata() if enrolled else None

        details = ""
        if not is_secure:
            details = "Windows Credential Manager is unavailable. Secure vault cannot be activated."
        elif enrolled and meta:
            details = f"Enrolled for {meta.issuer} ({meta.masked_account}). Windows Credential Manager active."
        else:
            details = "No authenticator enrolled. University login requires manual MFA."

        return TotpStatusResponse(
            is_enrolled=enrolled,
            vault_backend=backend_name,
            is_secure_backend=is_secure,
            metadata=meta,
            clock_skew_seconds=0.0,
            auto_autofill_enabled=meta.auto_autofill_enabled if meta else False,
            auto_submit_enabled=meta.auto_submit_enabled if meta else False,
            details=details,
        )
