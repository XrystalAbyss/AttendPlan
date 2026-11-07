"""RFC 6238 TOTP Generation Engine with timing safety margins and clock skew detection."""

from __future__ import annotations

import hashlib
import time
from typing import Optional

import pyotp

from app.domain.totp_models import (
    TotpCodeResult,
    TotpClockSkewError,
    TotpInvalidSecretError,
)

# Minimum validity threshold (in seconds) before a TOTP code is considered safe to submit.
# Submitting with < 4 seconds remaining risks server rejecting the code due to network latency.
DEFAULT_SAFETY_MARGIN_SECONDS = 4


def get_hash_digest_for_algorithm(algo: str) -> object:
    """Resolve hashlib digest object from algorithm string."""
    norm = algo.strip().upper()
    if norm == "SHA256":
        return hashlib.sha256
    elif norm == "SHA512":
        return hashlib.sha512
    return hashlib.sha1


class TotpEngine:
    """Pure RFC 6238 Time-Based One-Time Password engine."""

    @classmethod
    def generate_code_at_timestamp(
        cls,
        secret_base32: str,
        timestamp: float,
        digits: int = 6,
        period: int = 30,
        algorithm: str = "SHA1",
    ) -> TotpCodeResult:
        """Deterministic RFC 6238 code generation at an explicit timestamp."""
        try:
            digest_fn = get_hash_digest_for_algorithm(algorithm)
            totp = pyotp.TOTP(
                s=secret_base32,
                digits=digits,
                interval=period,
                digest=digest_fn,
            )
            code = totp.at(int(timestamp))
        except Exception as e:

            raise TotpInvalidSecretError(f"Failed to generate TOTP code: {e}") from e

        time_in_period = int(timestamp) % period
        remaining = period - time_in_period
        expires_at = (int(timestamp) // period + 1) * period

        return TotpCodeResult(
            code=code,
            time_remaining_seconds=remaining,
            expires_at_timestamp=float(expires_at),
        )

    @classmethod
    def generate_current_code(
        cls,
        secret_base32: str,
        digits: int = 6,
        period: int = 30,
        algorithm: str = "SHA1",
        min_safety_margin_seconds: int = DEFAULT_SAFETY_MARGIN_SECONDS,
        wait_if_near_expiry: bool = True,
    ) -> TotpCodeResult:
        """Generate current TOTP code.

        If wait_if_near_expiry is True and remaining seconds < min_safety_margin_seconds,
        pauses execution briefly until the new window starts, guaranteeing that the
        submitted code arrives well within its active window.
        """
        now = time.time()
        result = cls.generate_code_at_timestamp(
            secret_base32=secret_base32,
            timestamp=now,
            digits=digits,
            period=period,
            algorithm=algorithm,
        )

        if wait_if_near_expiry and result.time_remaining_seconds < min_safety_margin_seconds:
            # Wait for next window to ensure high submission reliability
            sleep_time = result.time_remaining_seconds + 0.5
            time.sleep(sleep_time)
            now = time.time()
            result = cls.generate_code_at_timestamp(
                secret_base32=secret_base32,
                timestamp=now,
                digits=digits,
                period=period,
                algorithm=algorithm,
            )

        return result

    @classmethod
    def verify_code(
        cls,
        secret_base32: str,
        code_to_verify: str,
        digits: int = 6,
        period: int = 30,
        algorithm: str = "SHA1",
        valid_window: int = 1,
    ) -> bool:
        """Verify candidate code with standard clock-drift tolerance window."""
        clean_code = code_to_verify.strip()
        if not clean_code or len(clean_code) != digits or not clean_code.isdigit():
            return False

        try:
            digest_fn = get_hash_digest_for_algorithm(algorithm)
            totp = pyotp.TOTP(
                s=secret_base32,
                digits=digits,
                interval=period,
                digest=digest_fn,
            )
            return bool(totp.verify(clean_code, valid_window=valid_window))
        except Exception:
            return False

    @classmethod
    def check_clock_skew(cls, reference_timestamp: Optional[float] = None) -> float:
        """Calculate system clock difference against an authoritative reference timestamp in seconds."""
        if reference_timestamp is None:
            return 0.0
        skew = abs(time.time() - reference_timestamp)
        if skew > 60.0:
            raise TotpClockSkewError(
                f"Severe local clock divergence detected: system clock is skewed by {skew:.1f}s. "
                "RFC 6238 TOTP requires synchronized system time."
            )
        return skew
