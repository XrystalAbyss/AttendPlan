"""Domain models and exceptions for RFC 6238 TOTP and Vault Management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class TotpVaultError(Exception):
    """Base exception for TOTP vault and authentication operations."""
    pass


class SecureVaultUnavailableError(TotpVaultError):
    """Raised when native Windows Credential Manager or a secure backend is unavailable."""
    pass


class TotpEnrollmentError(TotpVaultError):
    """Raised when enrollment fails due to invalid parameters or formatting."""
    pass


class TotpInvalidSecretError(TotpEnrollmentError):
    """Raised when an authenticator secret cannot be validated as valid Base32."""
    pass


class TotpClockSkewError(TotpVaultError):
    """Raised when local system clock diverges significantly from time servers."""
    pass


class TotpOriginSecurityError(TotpVaultError):
    """Raised when an MFA autofill attempt is requested on an unallowed origin."""
    pass


@dataclass(frozen=True)
class TotpAccountCandidate:
    """Decoded account candidate from QR or migration payload prior to enrollment."""
    issuer: str
    account_name: str
    secret_base32: str
    algorithm: str = "SHA1"
    digits: int = 6
    period: int = 30
    source_type: str = "STANDARD_TOTP"  # STANDARD_TOTP | GOOGLE_MIGRATION | MANUAL_BASE32

    @property
    def masked_account(self) -> str:
        """Return masked representation for safe display (e.g. st***94@university)."""
        acc = self.account_name.strip()
        if not acc:
            return "student_account"
        if len(acc) <= 4:
            return acc[0] + "***"
        prefix = acc[:2]
        suffix = acc[-2:]
        return f"{prefix}***{suffix}"


class TotpEnrollmentMetadata(BaseModel):
    """Non-secret enrollment metadata persisted locally. NEVER contains the secret."""
    enrollment_id: str = Field(..., description="Unique enrollment UUID")
    issuer: str = Field(default="iCloudEMS / Keycloak")
    masked_account: str = Field(..., description="Masked account identifier for UI display")
    enrolled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    digits: int = Field(default=6)
    period: int = Field(default=30)
    algorithm: str = Field(default="SHA1")
    auto_autofill_enabled: bool = Field(default=False)
    auto_submit_enabled: bool = Field(default=False)


class TotpStatusResponse(BaseModel):
    """User-facing authentication vault status. Exposes zero secrets."""
    is_enrolled: bool
    vault_backend: str
    is_secure_backend: bool
    metadata: Optional[TotpEnrollmentMetadata] = None
    clock_skew_seconds: float = 0.0
    auto_autofill_enabled: bool = False
    auto_submit_enabled: bool = False
    details: str = ""


@dataclass(frozen=True)
class TotpCodeResult:
    """In-memory RFC 6238 code result with timing safety margin. NEVER exposed via API."""
    code: str
    time_remaining_seconds: int
    expires_at_timestamp: float
