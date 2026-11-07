"""Academic term calendar service for semester-specific teaching windows.

Enforces institutional calendar boundaries:
- Odd semesters (1, 3, 5, 7): Autumn session (Aug, Sep, Oct, Nov).
- Even semesters (2, 4, 6, 8): Spring session (Jan, Feb, Mar, Apr, May).
- Accurate YearMonth resolution based on academic year start/end years.
- Calendar source hierarchy (USER_CONFIRMED > OFFICIAL_ACADEMIC_CALENDAR > VERIFIED_PORTAL_RECORDS > USER_CONFIGURED_DEFAULT).
- Out-of-window protection (prevents scanning June/July/December or wrong semesters).
- Local persistence in term_calendars.json.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AcademicTerm, AttendanceObservationBatch, AttendanceSnapshot
from app.db.session import get_default_db_path

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TermCalendarConfig:
    """Configured and verified teaching calendar for a single academic term."""

    term_key: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str] = None
    start_date: Optional[str] = None  # ISO format "YYYY-MM-DD"
    end_date: Optional[str] = None    # ISO format "YYYY-MM-DD"
    candidate_months: list[str] = field(default_factory=list)  # ["YYYY-MM", ...]
    confirmed_months: list[str] = field(default_factory=list)  # Months with verified classes
    excluded_months: list[str] = field(default_factory=list)   # Explicitly excluded months
    approved_exceptional_months: list[str] = field(default_factory=list)  # e.g. makeup classes
    source: str = "USER_CONFIGURED_DEFAULT"  # OFFICIAL_ACADEMIC_CALENDAR | VERIFIED_PORTAL_RECORDS | USER_CONFIRMED | USER_CONFIGURED_DEFAULT | INFERRED_CANDIDATE
    source_verification_timestamp: Optional[str] = None
    confidence_status: str = "PROVISIONAL"  # VERIFIED | PROVISIONAL | USER_CUSTOMIZED
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TermCalendarConfig:
        return cls(
            term_key=data.get("term_key", ""),
            academic_year=data.get("academic_year", ""),
            semester_number=int(data.get("semester_number", 0)),
            class_identifier=data.get("class_identifier"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            candidate_months=list(data.get("candidate_months", [])),
            confirmed_months=list(data.get("confirmed_months", [])),
            excluded_months=list(data.get("excluded_months", [])),
            approved_exceptional_months=list(data.get("approved_exceptional_months", [])),
            source=data.get("source", "USER_CONFIGURED_DEFAULT"),
            source_verification_timestamp=data.get("source_verification_timestamp"),
            confidence_status=data.get("confidence_status", "PROVISIONAL"),
            notes=data.get("notes"),
        )


def make_term_key(academic_year: str, semester: int, class_id: Optional[str] = None) -> str:
    """Canonical key identifying an academic term."""
    key = f"{academic_year}-S{semester}"
    if class_id:
        key += f"-{class_id}"
    return key


class AcademicTermCalendarService:
    """Manages academic semester calendars, teaching windows, and out-of-window guards."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        db: Optional[Session] = None,
        storage_path: Optional[Path] = None,
    ) -> None:
        target_path = storage_path or config_path
        if target_path:
            self.config_path = Path(target_path)
        else:
            env_path = os.environ.get("ATTENDPLAN_CALENDARS_PATH")
            if env_path:
                self.config_path = Path(env_path)
            else:
                self.config_path = get_default_db_path().parent / "term_calendars.json"
        self.db = db
        self._cache: dict[str, TermCalendarConfig] = {}
        self._load()

    def _load(self) -> None:
        """Load persisted calendar overrides from disk."""
        if not self.config_path.exists():
            self._cache = {}
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._cache = {
                    k: TermCalendarConfig.from_dict(v)
                    for k, v in data.items()
                    if isinstance(v, dict)
                }
        except Exception as e:
            logger.warning("Failed to load term_calendars.json: %s", e)
            self._cache = {}

    def _persist(self) -> None:
        """Atomically persist calendar configurations to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.config_path.with_suffix(".tmp")
            data = {k: v.to_dict() for k, v in self._cache.items()}
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.config_path)
        except Exception as e:
            logger.error("Failed to persist term_calendars.json: %s", e)

    def parse_academic_years(self, academic_year: str) -> tuple[int, int]:
        """Parse '2025-2026' into start year 2025 and end year 2026."""
        parts = academic_year.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
        # Fallback to single year
        y = int(parts[0]) if parts[0].isdigit() else date.today().year
        return y, y + 1

    def generate_default_candidate_months(self, academic_year: str, semester: int) -> tuple[list[str], list[str]]:
        """Generate standard candidate teaching months and default excluded months for a semester.

        Odd semesters (1, 3, 5, 7): August to November of the academic year's start year.
        Even semesters (2, 4, 6, 8): January to May of the academic year's end year.
        """
        start_year, end_year = self.parse_academic_years(academic_year)
        if semester % 2 == 1:
            # Odd semester
            candidate = [
                f"{start_year}-08",
                f"{start_year}-09",
                f"{start_year}-10",
                f"{start_year}-11",
            ]
            excluded = [
                f"{start_year}-06",
                f"{start_year}-07",
                f"{start_year}-12",
            ]
        else:
            # Even semester
            candidate = [
                f"{end_year}-01",
                f"{end_year}-02",
                f"{end_year}-03",
                f"{end_year}-04",
                f"{end_year}-05",
            ]
            excluded = [
                f"{end_year}-06",
                f"{end_year}-07",
            ]
        return candidate, excluded

    def resolve_term_calendar(
        self,
        academic_year: str,
        semester: int,
        class_id: Optional[str] = None,
    ) -> TermCalendarConfig:
        """Resolve the effective calendar for a term, applying precedence hierarchy."""
        return self.get_calendar(academic_year, semester, class_id)

    def get_calendar(
        self,
        academic_year: str,
        semester: int,
        class_id: Optional[str] = None,
    ) -> TermCalendarConfig:
        """Resolve the effective calendar for a term, applying precedence hierarchy."""
        term_key = make_term_key(academic_year, semester, class_id)
        # Check cache / user custom config first
        if term_key in self._cache:
            custom = self._cache[term_key]
            if custom.source == "USER_CONFIRMED":
                return custom

        # Also check without class_id
        generic_key = make_term_key(academic_year, semester)
        if generic_key in self._cache and self._cache[generic_key].source == "USER_CONFIRMED":
            return self._cache[generic_key]

        # Generate default candidate months
        default_candidate, default_excluded = self.generate_default_candidate_months(academic_year, semester)
        config = TermCalendarConfig(
            term_key=term_key,
            academic_year=academic_year,
            semester_number=semester,
            class_identifier=class_id,
            candidate_months=default_candidate,
            excluded_months=default_excluded,
            source="USER_CONFIGURED_DEFAULT",
            confidence_status="PROVISIONAL",
        )

        # Inspect DB evidence if available
        if self.db is not None:
            self._enrich_from_database(config)

        # Cache provisional if not previously cached
        if term_key not in self._cache:
            self._cache[term_key] = config

        return config

    def _enrich_from_database(self, config: TermCalendarConfig) -> None:
        """Enrich provisional calendar with verified portal evidence from SQLite."""
        if self.db is None:
            return
        try:
            term = self.db.scalars(
                select(AcademicTerm).where(
                    AcademicTerm.academic_year == config.academic_year,
                    AcademicTerm.semester_number == config.semester_number,
                )
            ).first()
            if not term or not hasattr(term, "id"):
                return

            # Check existing snapshots for date range
            snapshots = self.db.scalars(
                select(AttendanceSnapshot)
                .where(AttendanceSnapshot.academic_term_id == term.id)
                .order_by(AttendanceSnapshot.captured_at.desc())
            ).all()
            if isinstance(snapshots, (list, tuple)):
                for snap in snapshots:
                    if getattr(snap, "reporting_start_date", None) and getattr(snap, "reporting_end_date", None):
                        config.start_date = snap.reporting_start_date.isoformat()
                        config.end_date = snap.reporting_end_date.isoformat()
                        if config.source != "USER_CONFIRMED":
                            config.source = "VERIFIED_PORTAL_RECORDS"
                            config.confidence_status = "VERIFIED"
                            config.source_verification_timestamp = getattr(snap, "captured_at", datetime.now()).isoformat()
                        break

            # Check existing observation batches for confirmed months
            batches = self.db.scalars(
                select(AttendanceObservationBatch).where(
                    AttendanceObservationBatch.academic_term_id == term.id
                )
            ).all()
            if isinstance(batches, (list, tuple)):
                confirmed = set(config.confirmed_months)
                for b in batches:
                    if getattr(b, "coverage_start_date", None):
                        m_str = f"{b.coverage_start_date.year:04d}-{b.coverage_start_date.month:02d}"
                        confirmed.add(m_str)
                config.confirmed_months = sorted(confirmed)
        except Exception as e:
            logger.debug("Database enrichment skipped: %s", e)

    def save_calendar(self, config: TermCalendarConfig) -> TermCalendarConfig:
        """Save user-confirmed or updated calendar configuration."""
        config.source = "USER_CONFIRMED"
        config.confidence_status = "USER_CUSTOMIZED"
        config.source_verification_timestamp = utc_now_iso()
        self._cache[config.term_key] = config
        self._persist()
        return config

    def reset_calendar(self, academic_year: str, semester: int, class_id: Optional[str] = None) -> TermCalendarConfig:
        """Reset a term calendar configuration back to provisional defaults."""
        term_key = make_term_key(academic_year, semester, class_id)
        if term_key in self._cache:
            del self._cache[term_key]
            self._persist()
        return self.get_calendar(academic_year, semester, class_id)

    def get_candidate_months(
        self,
        academic_year: str,
        semester: int,
        class_id: Optional[str] = None,
        include_exceptions: bool = True,
    ) -> list[str]:
        """Return the effective candidate YearMonth strings for a term in chronological order."""
        cal = self.get_calendar(academic_year, semester, class_id)
        months = set(cal.candidate_months)
        if include_exceptions:
            months.update(cal.approved_exceptional_months)
            excluded = set(cal.excluded_months) - set(cal.approved_exceptional_months)
            months.difference_update(excluded)
        else:
            months.difference_update(cal.excluded_months)
        return sorted(months)

    def is_month_in_window(
        self,
        academic_year: str,
        semester: int,
        year_month: str,
        class_id: Optional[str] = None,
        with_reason: bool = False,
    ) -> bool | tuple[bool, str]:
        """Validate whether a requested YearMonth (YYYY-MM) falls within the teaching calendar window.

        Returns boolean by default, or (is_allowed, reason) if with_reason=True.
        """
        cal = self.get_calendar(academic_year, semester, class_id)
        if year_month in cal.approved_exceptional_months:
            outcome = (True, "EXPLICIT_USER_EXCEPTION")
        elif year_month in cal.excluded_months:
            outcome = (False, "EXPLICITLY_EXCLUDED_MONTH")
        elif year_month in cal.candidate_months:
            outcome = (True, "IN_CALENDAR_WINDOW")
        else:
            outcome = (False, "OUTSIDE_CALENDAR_WINDOW")

        if with_reason:
            return outcome
        return outcome[0]

    def validate_month_in_window(
        self,
        academic_year: str,
        semester: int,
        year_month: str,
        class_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Validate whether a requested YearMonth falls within the window and return (allowed, reason)."""
        res = self.is_month_in_window(academic_year, semester, year_month, class_id, with_reason=True)
        assert isinstance(res, tuple)
        return res

    def get_all_calendars(self) -> list[TermCalendarConfig]:
        """Retrieve all active calendar configurations."""
        return list(self._cache.values())
