"""Local configuration service for persistent student identity and login automation settings.

Stores non-secret configuration only in %LOCALAPPDATA%/AttendPlan/settings.json.
Never logs, commits, or transmits the saved mobile number except to legitimate Keycloak forms.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.db.session import get_default_db_path

logger = logging.getLogger(__name__)

INDIAN_MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")


def get_settings_file_path() -> Path:
    """Resolve location for settings.json in %LOCALAPPDATA%/AttendPlan."""
    env_override = os.environ.get("ATTENDPLAN_SETTINGS_PATH")
    if env_override:
        return Path(env_override)
    db_path = get_default_db_path()
    return db_path.parent / "settings.json"


def validate_mobile_number(raw: str) -> str:
    """Validate and normalize a 10-digit Indian student mobile number."""
    cleaned = re.sub(r"[\s\-\+]", "", raw)
    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    if not INDIAN_MOBILE_REGEX.match(cleaned):
        raise ValueError(
            "Invalid mobile number format. Expected a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."
        )
    return cleaned


def mask_mobile_number(number: Optional[str]) -> Optional[str]:
    """Return masked representation for safe UI display (e.g. ******9940)."""
    if not number:
        return None
    cleaned = re.sub(r"\D", "", number)
    if len(cleaned) < 4:
        return "****"
    return "*" * (len(cleaned) - 4) + cleaned[-4:]


class AppSettings(BaseModel):
    """Local settings structure saved in settings.json.
    
    All automation toggles default to False (safe by default).
    Sensitive automation requires explicit first-time user opt-in.
    Once opted in, user preferences are persisted locally.
    """
    saved_mobile_number: Optional[str] = Field(default=None)
    auto_mobile_autofill: bool = Field(default=False)
    auto_login_continuation: bool = Field(default=False)
    auto_totp_autofill: bool = Field(default=False)
    auto_totp_submit: bool = Field(default=False)


class SettingsPublicResponse(BaseModel):
    """Non-sensitive settings representation for UI display."""
    has_saved_mobile: bool
    masked_mobile: Optional[str] = None
    auto_mobile_autofill: bool
    auto_login_continuation: bool
    auto_totp_autofill: bool
    auto_totp_submit: bool


class SettingsUpdateRequest(BaseModel):
    """User request to update authentication and login settings."""
    mobile_number: Optional[str] = None
    clear_mobile: bool = False
    auto_mobile_autofill: Optional[bool] = None
    auto_login_continuation: Optional[bool] = None
    auto_totp_autofill: Optional[bool] = None
    auto_totp_submit: Optional[bool] = None


class SettingsService:
    """Service managing persistent local settings in %LOCALAPPDATA%/AttendPlan/settings.json."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        self.settings_path = settings_path or get_settings_file_path()
        self._cached_settings: Optional[AppSettings] = None

    def load_settings(self) -> AppSettings:
        """Load settings from JSON file or return default configuration."""
        if self._cached_settings:
            return self._cached_settings

        if not self.settings_path.exists():
            self._cached_settings = AppSettings()
            return self._cached_settings

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cached_settings = AppSettings(**data)
            return self._cached_settings
        except Exception as e:
            logger.warning("Failed to load settings from %s: %s. Using defaults.", self.settings_path, e)
            self._cached_settings = AppSettings()
            return self._cached_settings

    def save_settings(self, settings: AppSettings) -> None:
        """Atomically persist settings to settings.json."""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.settings_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, indent=2)
        os.replace(temp_path, self.settings_path)
        self._cached_settings = settings
        logger.info("Persisted AttendPlan settings to %s", self.settings_path)

    def update_settings(self, req: SettingsUpdateRequest) -> AppSettings:
        """Update settings with optional mobile number and automation toggles."""
        current = self.load_settings()

        new_mobile = current.saved_mobile_number
        if req.clear_mobile:
            new_mobile = None
        elif req.mobile_number is not None and req.mobile_number.strip():
            new_mobile = validate_mobile_number(req.mobile_number)

        updated = AppSettings(
            saved_mobile_number=new_mobile,
            auto_mobile_autofill=req.auto_mobile_autofill if req.auto_mobile_autofill is not None else current.auto_mobile_autofill,
            auto_login_continuation=req.auto_login_continuation if req.auto_login_continuation is not None else current.auto_login_continuation,
            auto_totp_autofill=req.auto_totp_autofill if req.auto_totp_autofill is not None else current.auto_totp_autofill,
            auto_totp_submit=req.auto_totp_submit if req.auto_totp_submit is not None else current.auto_totp_submit,
        )
        self.save_settings(updated)
        return updated

    def get_public_settings(self) -> SettingsPublicResponse:
        """Return non-sensitive settings DTO with masked mobile number for UI rendering."""
        s = self.load_settings()
        return SettingsPublicResponse(
            has_saved_mobile=bool(s.saved_mobile_number),
            masked_mobile=mask_mobile_number(s.saved_mobile_number),
            auto_mobile_autofill=s.auto_mobile_autofill,
            auto_login_continuation=s.auto_login_continuation,
            auto_totp_autofill=s.auto_totp_autofill,
            auto_totp_submit=s.auto_totp_submit,
        )
