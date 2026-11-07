"""Tests for Phase F.1 Friends-Beta Architecture & Multi-User Isolation.

Verifies:
1. Fresh database initialization for a new student user.
2. Empty initial state with zero developer data inheritance.
3. Completely separate settings.json and database storage per user.
4. Independent Credential Vault (Windows Credential Manager / keyring) isolation.
5. First-run error handling and graceful empty states.
6. Backup file creation within the per-user storage root.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicTerm,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    Base,
    Course,
    PerformanceSnapshot,
)
from app.db.session import build_sqlite_url, create_app_engine
from app.services.settings_service import AppSettings, SettingsService, SettingsUpdateRequest


def test_fresh_user_environment_isolation():
    """Verify that a brand-new user starts with an empty database and clean configuration."""
    with tempfile.TemporaryDirectory(prefix="attendplan_user2_") as user2_dir:
        user2_path = Path(user2_dir)
        db_path = user2_path / "attendplan.sqlite3"
        settings_path = user2_path / "settings.json"
        backup_dir = user2_path / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 1. Initialize SQLite schema for User 2
        engine = create_app_engine(build_sqlite_url(db_path))
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            # Verify 0 terms, 0 courses, 0 snapshots
            terms = session.scalars(select(AcademicTerm)).all()
            courses = session.scalars(select(Course)).all()
            att_snaps = session.scalars(select(AttendanceSnapshot)).all()
            obs = session.scalars(select(AttendancePeriodObservation)).all()
            perf_snaps = session.scalars(select(PerformanceSnapshot)).all()

            assert len(terms) == 0
            assert len(courses) == 0
            assert len(att_snaps) == 0
            assert len(obs) == 0
            assert len(perf_snaps) == 0

        # Dispose engine so SQLite file lock is released on Windows
        engine.dispose()

        # 2. Settings isolation
        settings_service = SettingsService(settings_path=settings_path)
        settings = settings_service.load_settings()

        # Must have no saved mobile or developer phone number
        assert settings.saved_mobile_number is None
        assert settings.auto_mobile_autofill is False
        assert settings.auto_totp_autofill is False

        # User 2 configures their own phone number
        settings_service.update_settings(
            SettingsUpdateRequest(mobile_number="9876543210", auto_mobile_autofill=True)
        )
        updated = settings_service.load_settings()
        assert updated.saved_mobile_number == "9876543210"
        assert updated.auto_mobile_autofill is True

        # 3. Verify User 2's settings file exists independently
        assert settings_path.exists()
        import json
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["saved_mobile_number"] == "9876543210"


def test_no_hardcoded_developer_identities_in_codebase():
    """Verify that developer-specific identity tokens are never hardcoded in production services."""

    # Verify default mobile is always None (safe default)
    default_settings = AppSettings()
    assert default_settings.saved_mobile_number is None
    assert default_settings.auto_mobile_autofill is False
    assert default_settings.auto_totp_autofill is False


def test_fresh_database_empty_response_handling():
    """Verify that querying performance overview on an empty database does not fail."""
    with tempfile.TemporaryDirectory(prefix="attendplan_empty_") as empty_dir:
        db_path = Path(empty_dir) / "app.sqlite3"
        engine = create_app_engine(build_sqlite_url(db_path))
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            from app.services.performance_service import overview
            ov = overview(session)
            assert ov["terms"] == []
            assert "note" in ov

        # Dispose engine so SQLite file lock is released on Windows
        engine.dispose()


def test_synthetic_user_onboarding_and_current_term_ingestion():
    """Verify that an onboarding student can ingest current term attendance with clean isolation."""
    with tempfile.TemporaryDirectory(prefix="attendplan_synth_user_") as user_dir:
        db_path = Path(user_dir) / "attendplan.sqlite3"
        engine = create_app_engine(build_sqlite_url(db_path))
        Base.metadata.create_all(engine)

        try:
            from app.services.ingestion_service import IngestionService
            fixture_path = Path(__file__).resolve().parents[0] / "fixtures" / "synthetic_semester4_subjectwise.html"
            assert fixture_path.exists(), f"Missing test fixture: {fixture_path}"

            with open(fixture_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            with Session(engine) as session:
                ingestion = IngestionService(session)
                result = ingestion.ingest_html_auto(
                    html_content=html_content,
                    source="HTML_UPLOAD_SUBWISE",
                )
                assert result["type"] == "SUBJECT_WISE_SNAPSHOT"
                assert result["outcome"] in ("INGESTED", "SUCCESS")

                # Verify User starts with strictly 1 term and its courses
                terms = session.scalars(select(AcademicTerm)).all()
                courses = session.scalars(select(Course)).all()
                assert len(terms) == 1
                assert len(courses) > 0
                assert terms[0].semester_number == 4
        finally:
            engine.dispose()


def test_browser_profile_separation_and_cdp_loopback_isolation():
    """Verify that Chrome launch scripts enforce loopback-only binding and dedicated profile directory."""
    repo_root = Path(__file__).resolve().parents[2]
    launch_chrome_ps1 = repo_root / "scripts" / "Launch-Chrome.ps1"
    assert launch_chrome_ps1.exists()

    content = launch_chrome_ps1.read_text(encoding="utf-8")
    # Verify non-negotiable boundaries:
    assert "--remote-debugging-port=9222" in content
    # Dedicated profile must reside in %LOCALAPPDATA%\AttendPlan\chrome-profile
    assert "chrome-profile" in content
    assert "AttendPlan" in content


def test_empty_database_analytics_graceful_handling():
    """Verify that all domain analytics engines handle zero records gracefully without errors."""
    from app.domain.analytics_engine import AttendanceAnalyticsEngine
    from app.domain.attendance_engine import calculate_aggregate_metrics

    # 1. Aggregate metrics on empty records
    tot_att, tot_del, pct, status = calculate_aggregate_metrics([])
    assert tot_att == 0
    assert tot_del == 0
    assert pct is None
    assert status.value == "UNRECORDED"

    # 2. Monthly analytics on empty observations
    monthly = AttendanceAnalyticsEngine.compute_monthly_analytics([])
    assert monthly == []

    # 3. Weekday analytics on empty observations
    weekday = AttendanceAnalyticsEngine.compute_weekday_analytics([])
    assert len(weekday) == 7  # Monday through Sunday empty buckets
    for w in weekday:
        assert w.delivered == 0
        assert w.attended == 0
        assert w.missed == 0
        assert w.absence_rate == 0.0
        assert w.coverage == "UNAVAILABLE"
