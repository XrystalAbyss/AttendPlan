"""Unit tests for SettingsService and persistent mobile identity configuration."""

import json
from pathlib import Path
import pytest

from app.services.settings_service import (
    SettingsService,
    SettingsUpdateRequest,
    mask_mobile_number,
    validate_mobile_number,
)


def test_validate_mobile_number_valid():
    """Verify standard 10-digit Indian mobile formats."""
    assert validate_mobile_number("9876543210") == "9876543210"
    assert validate_mobile_number("8123456789") == "8123456789"
    assert validate_mobile_number("7000000000") == "7000000000"
    assert validate_mobile_number("6999999999") == "6999999999"
    # With spaces, hyphens, and +91 prefix
    assert validate_mobile_number("+91 98765 43210") == "9876543210"
    assert validate_mobile_number("91-9876543210") == "9876543210"
    assert validate_mobile_number("09876543210") == "9876543210"
    assert validate_mobile_number(" 9876-543-210 ") == "9876543210"


def test_validate_mobile_number_invalid():
    """Verify rejection of invalid formats."""
    with pytest.raises(ValueError, match="Invalid mobile number"):
        validate_mobile_number("1234567890")  # starts with 1
    with pytest.raises(ValueError, match="Invalid mobile number"):
        validate_mobile_number("5555555555")  # starts with 5
    with pytest.raises(ValueError, match="Invalid mobile number"):
        validate_mobile_number("987654321")   # only 9 digits
    with pytest.raises(ValueError, match="Invalid mobile number"):
        validate_mobile_number("98765432100") # 11 digits without 91
    with pytest.raises(ValueError, match="Invalid mobile number"):
        validate_mobile_number("abcdefghij")  # non-digits


def test_mask_mobile_number():
    """Verify mobile masking for safe UI display."""
    assert mask_mobile_number(None) is None
    assert mask_mobile_number("") is None
    assert mask_mobile_number("9876543210") == "******3210"
    assert mask_mobile_number("9999") == "9999"
    assert mask_mobile_number("12") == "****"


def test_settings_service_lifecycle(tmp_path: Path):
    """Verify settings loading, persistence, updating, and masking."""
    settings_file = tmp_path / "settings.json"
    service = SettingsService(settings_path=settings_file)

    # 1. Default initial state - safe by default, sensitive automation requires explicit opt-in
    initial = service.load_settings()
    assert initial.saved_mobile_number is None
    assert initial.auto_mobile_autofill is False
    assert initial.auto_login_continuation is False
    assert initial.auto_totp_autofill is False
    assert initial.auto_totp_submit is False

    pub = service.get_public_settings()
    assert pub.has_saved_mobile is False
    assert pub.masked_mobile is None
    assert pub.auto_mobile_autofill is False

    # 2. Update with mobile number and explicitly opt in to automation
    updated = service.update_settings(
        SettingsUpdateRequest(
            mobile_number="9876543210",
            auto_mobile_autofill=True,
            auto_login_continuation=False,
        )
    )
    assert updated.saved_mobile_number == "9876543210"
    assert updated.auto_mobile_autofill is True
    assert updated.auto_login_continuation is False

    # Check persisted file
    assert settings_file.exists()
    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["saved_mobile_number"] == "9876543210"
    assert data["auto_mobile_autofill"] is True
    assert data["auto_login_continuation"] is False

    # Check public DTO masking
    pub2 = service.get_public_settings()
    assert pub2.has_saved_mobile is True
    assert pub2.masked_mobile == "******3210"

    # 3. Clear mobile number
    cleared = service.update_settings(SettingsUpdateRequest(clear_mobile=True))
    assert cleared.saved_mobile_number is None
    assert service.get_public_settings().has_saved_mobile is False
