"""Unit tests for TotpEngine RFC 6238 implementation and timing margins."""

import time
import pytest

from app.domain.totp_engine import TotpEngine
from app.domain.totp_models import (
    TotpClockSkewError,
    TotpInvalidSecretError,
)

# RFC 6238 standard test secret (ASCII: "12345678901234567890")
# Base32: GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ
RFC_TEST_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def test_rfc_6238_test_vectors():
    """Verify deterministic output matches RFC 6238 test vectors at specified UNIX epochs."""
    # Timestamp: 59s -> 1 period
    res_59 = TotpEngine.generate_code_at_timestamp(
        secret_base32=RFC_TEST_SECRET,
        timestamp=59.0,
        digits=8,
        period=30,
        algorithm="SHA1",
    )
    assert res_59.code == "94287082"
    assert res_59.time_remaining_seconds == 1
    assert res_59.expires_at_timestamp == 60.0

    # Timestamp: 1111111109s
    res_1111111109 = TotpEngine.generate_code_at_timestamp(
        secret_base32=RFC_TEST_SECRET,
        timestamp=1111111109.0,
        digits=8,
        period=30,
        algorithm="SHA1",
    )
    assert res_1111111109.code == "07081804"

    # Timestamp: 1234567890s
    res_1234567890 = TotpEngine.generate_code_at_timestamp(
        secret_base32=RFC_TEST_SECRET,
        timestamp=1234567890.0,
        digits=8,
        period=30,
        algorithm="SHA1",
    )
    assert res_1234567890.code == "89005924"


def test_standard_6_digit_generation_and_verification():
    """Verify 6-digit TOTP generation and verification window."""
    now = time.time()
    result = TotpEngine.generate_code_at_timestamp(
        secret_base32=RFC_TEST_SECRET,
        timestamp=now,
        digits=6,
        period=30,
        algorithm="SHA1",
    )

    assert len(result.code) == 6
    assert result.code.isdigit()
    assert 0 <= result.time_remaining_seconds <= 30

    # Verify code
    assert TotpEngine.verify_code(
        secret_base32=RFC_TEST_SECRET,
        code_to_verify=result.code,
        digits=6,
        period=30,
        algorithm="SHA1",
    ) is True

    # Reject invalid code
    assert TotpEngine.verify_code(
        secret_base32=RFC_TEST_SECRET,
        code_to_verify="000000",
        digits=6,
        period=30,
        algorithm="SHA1",
    ) is False


def test_invalid_secret_rejection():
    """Verify that malformed secrets raise TotpInvalidSecretError."""
    with pytest.raises(TotpInvalidSecretError):
        TotpEngine.generate_code_at_timestamp(
            secret_base32="!!!NOT_BASE32!!!",
            timestamp=1000.0,
        )


def test_clock_skew_detection():
    """Verify clock skew calculation and detection of severe divergence (> 60s)."""
    now = time.time()
    # Normal skew (< 1s)
    skew = TotpEngine.check_clock_skew(now + 0.5)
    assert skew < 2.0

    # Severe divergence
    with pytest.raises(TotpClockSkewError, match="Severe local clock divergence"):
        TotpEngine.check_clock_skew(now + 120.0)
