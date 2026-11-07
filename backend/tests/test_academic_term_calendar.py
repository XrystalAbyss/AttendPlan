"""Tests for AcademicTermCalendarService, calendar-aware backfill windows, and precedence."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.models import AcademicTerm, AttendanceObservationBatch, AttendanceSnapshot
from app.main import app
from app.services.academic_term_calendar_service import AcademicTermCalendarService


@pytest.fixture
def calendar_service(tmp_path):
    """Provides a fresh calendar service storing configs in a temporary file."""
    temp_file = tmp_path / "test_term_calendars.json"
    return AcademicTermCalendarService(storage_path=temp_file)


def test_odd_semester_months_default_august_to_november(calendar_service: AcademicTermCalendarService):
    """Odd semesters (1, 3, 5, 7) must default to August through November only."""
    for sem in (1, 3, 5, 7):
        months = calendar_service.get_candidate_months("2025-2026", sem)
        assert months == ["2025-08", "2025-09", "2025-10", "2025-11"]
        # Denominator must be 4
        assert len(months) == 4
        # December, June, July must NOT be included by default
        assert "2025-12" not in months
        assert "2025-06" not in months
        assert "2025-07" not in months


def test_even_semester_months_provisional_january_to_may(calendar_service: AcademicTermCalendarService):
    """Even semesters (2, 4, 6, 8) must default to January through May."""
    for sem in (2, 4, 6, 8):
        months = calendar_service.get_candidate_months("2025-2026", sem)
        assert months == ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
        # Denominator must be 5
        assert len(months) == 5
        # Previous year months must NOT be included
        assert "2025-01" not in months
        assert "2025-05" not in months


def test_academic_year_crossing_odd_to_even(calendar_service: AcademicTermCalendarService):
    """Academic Year 2026-2027 maps odd to 2026 and even to 2027."""
    odd_months = calendar_service.get_candidate_months("2026-2027", 5)
    even_months = calendar_service.get_candidate_months("2026-2027", 6)

    assert all(m.startswith("2026-") for m in odd_months)
    assert all(m.startswith("2027-") for m in even_months)


def test_out_of_window_months_rejected(calendar_service: AcademicTermCalendarService):
    """Out-of-window requests must be rejected unless explicitly approved."""
    # For AY 2025-2026 Sem 5 (Aug-Nov 2025):
    assert calendar_service.is_month_in_window("2025-2026", 5, "2025-09") is True
    assert calendar_service.is_month_in_window("2025-2026", 5, "2025-10") is True
    assert calendar_service.is_month_in_window("2025-2026", 5, "2025-12") is False  # Outside window
    assert calendar_service.is_month_in_window("2025-2026", 5, "2026-01") is False  # Wrong year / outside window
    assert calendar_service.is_month_in_window("2025-2026", 5, "2025-06") is False  # Summer month


def test_exceptional_month_approval(calendar_service: AcademicTermCalendarService):
    """User can explicitly approve an out-of-window month exception."""
    cfg = calendar_service.resolve_term_calendar("2025-2026", 5, class_id="2582")
    cfg.approved_exceptional_months = ["2025-12"]
    calendar_service.save_calendar(cfg)

    assert calendar_service.is_month_in_window("2025-2026", 5, "2025-12", class_id="2582") is True
    # Still rejects unapproved out-of-window months
    assert calendar_service.is_month_in_window("2025-2026", 5, "2026-01", class_id="2582") is False


def test_precedence_user_override_over_defaults(calendar_service: AcademicTermCalendarService):
    """User override takes precedence over defaults and marks status USER_CUSTOMIZED."""
    cfg = calendar_service.resolve_term_calendar("2025-2026", 3, class_id="2500")
    cfg.candidate_months = ["2025-09", "2025-10"]
    cfg.excluded_months = ["2025-08"]
    saved = calendar_service.save_calendar(cfg)

    assert saved.source == "USER_CONFIRMED"
    assert saved.confidence_status == "USER_CUSTOMIZED"
    assert saved.candidate_months == ["2025-09", "2025-10"]
    assert saved.excluded_months == ["2025-08"]

    # Candidate months query reflects the override
    months = calendar_service.get_candidate_months("2025-2026", 3, class_id="2500")
    assert months == ["2025-09", "2025-10"]


def test_calendar_reset_restores_defaults(calendar_service: AcademicTermCalendarService):
    """Resetting a calendar clears user override and returns to default/provisional."""
    cfg = calendar_service.resolve_term_calendar("2025-2026", 3, class_id="2500")
    cfg.candidate_months = ["2025-09"]
    calendar_service.save_calendar(cfg)

    reset_config = calendar_service.reset_calendar("2025-2026", 3, class_id="2500")
    assert reset_config.source == "USER_CONFIGURED_DEFAULT"
    assert reset_config.confidence_status == "PROVISIONAL"
    assert reset_config.candidate_months == ["2025-08", "2025-09", "2025-10", "2025-11"]


def test_db_enrichment_with_confirmed_batches(calendar_service: AcademicTermCalendarService):
    """Database observations enrich calendar config with confirmed teaching months."""
    mock_session = MagicMock()
    mock_term = MagicMock(spec=AcademicTerm)
    mock_term.id = "term-123"
    mock_term.academic_year = "2026-2027"
    mock_term.semester_number = 5
    mock_term.class_identifier = "2582"

    mock_snap = MagicMock(spec=AttendanceSnapshot)
    mock_snap.reporting_start_date = date(2026, 8, 1)
    mock_snap.reporting_end_date = date(2026, 11, 30)
    mock_snap.captured_at = datetime.now()

    mock_batch1 = MagicMock(spec=AttendanceObservationBatch)
    mock_batch1.coverage_start_date = date(2026, 10, 1)
    mock_batch1.coverage_end_date = date(2026, 10, 28)

    # Setup scalars mocks
    def mock_scalars(query):
        scalars_mock = MagicMock()
        q_str = str(query)
        if "academic_terms" in q_str:
            scalars_mock.first.return_value = mock_term
        elif "attendance_snapshots" in q_str:
            scalars_mock.all.return_value = [mock_snap]
        elif "attendance_observation_batches" in q_str:
            scalars_mock.all.return_value = [mock_batch1]
        else:
            scalars_mock.all.return_value = []
            scalars_mock.first.return_value = None
        return scalars_mock

    mock_session.scalars = mock_scalars
    calendar_service.db = mock_session

    config = calendar_service.resolve_term_calendar("2026-2027", 5, class_id="2582")

    assert "2026-10" in config.confirmed_months
    assert config.source == "VERIFIED_PORTAL_RECORDS"
    assert config.confidence_status == "VERIFIED"


def test_calendar_api_endpoints():
    """Verify REST API endpoints for calendar listing, detail, update, and reset."""
    client = TestClient(app)

    # 1. GET /calendars
    res = client.get("/api/v1/attendance-archive/calendars")
    assert res.status_code == 200
    data = res.json()
    assert "calendars" in data

    # 2. GET /calendars/{term_key}
    term_key = "2025-2026_4_2508"
    res = client.get(f"/api/v1/attendance-archive/calendars/{term_key}")
    assert res.status_code == 200
    term_cal = res.json()["calendar"]
    assert term_cal["academic_year"] == "2025-2026"
    assert term_cal["semester_number"] == 4
    assert term_cal["candidate_months"] == ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]

    # 3. POST /calendars/{term_key}
    update_payload = {
        "candidate_months": ["2026-01", "2026-02", "2026-03", "2026-04"],
        "excluded_months": ["2026-05"],
        "approved_exceptional_months": [],
    }
    res = client.post(f"/api/v1/attendance-archive/calendars/{term_key}", json=update_payload)
    assert res.status_code == 200
    saved = res.json()["calendar"]
    assert saved["candidate_months"] == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert saved["source"] == "USER_CONFIRMED"

    # 4. POST /calendars/{term_key}/reset
    res = client.post(f"/api/v1/attendance-archive/calendars/{term_key}/reset")
    assert res.status_code == 200
    reset_data = res.json()["calendar"]
    assert reset_data["source"] == "USER_CONFIGURED_DEFAULT"
    assert "2026-05" in reset_data["candidate_months"]


def test_different_calendar_configs_per_academic_year(calendar_service: AcademicTermCalendarService):
    """Each academic year must maintain independent calendar calculations."""
    cal_2024_sem1 = calendar_service.get_candidate_months("2024-2025", 1)
    cal_2025_sem1 = calendar_service.get_candidate_months("2025-2026", 1)
    cal_2026_sem5 = calendar_service.get_candidate_months("2026-2027", 5)

    assert cal_2024_sem1 == ["2024-08", "2024-09", "2024-10", "2024-11"]
    assert cal_2025_sem1 == ["2025-08", "2025-09", "2025-10", "2025-11"]
    assert cal_2026_sem5 == ["2026-08", "2026-09", "2026-10", "2026-11"]
    # Zero cross-year contamination
    assert not any(m.startswith("2025-") for m in cal_2024_sem1)
    assert not any(m.startswith("2026-") for m in cal_2025_sem1)


def test_make_plan_bounds_months_by_calendar():
    """Plan generator uses academic term calendar service and restricts scopes to verified candidate months."""
    from sqlalchemy.orm import Session
    from app.api.archive_routes import make_plan
    from app.db.models import Base, SyncJob
    from app.db.session import create_app_engine

    engine = create_app_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        # Add verified discovery combinations
        db.add(SyncJob(
            source_scope="HISTORICAL_SELECTOR_DISCOVERY",
            state="COMPLETED",
            details={
                "combinations": [
                    {"academic_year": "2025-2026", "semester": "3", "class_id": "1067", "class_label": "B.Tech CSE AIML-Sem 3"},
                    {"academic_year": "2025-2026", "semester": "4", "class_id": "2508", "class_label": "B.Tech CSE AIML-Sem 4"},
                ]
            }
        ))
        db.commit()

        plan_scopes = make_plan(db, date(2026, 10, 28))
        assert len(plan_scopes) == 2
        for scope in plan_scopes:
            # Months must be bounded (max 5 candidate months per semester)
            assert len(scope["months"]) <= 5
            # No June, July, or summer break months
            for m in scope["months"]:
                assert not m.endswith("-06")
                assert not m.endswith("-07")
                assert not m.endswith("-12")  # December not included by default



def test_semester_3_exceptional_july_2025_scoped_isolation(calendar_service: AcademicTermCalendarService):
    """Verifies approved exceptional July 2025 is scoped strictly to Sem 3 and does not pollute other terms."""
    # Before approval, July 2025 is rejected
    assert calendar_service.is_month_in_window("2025-2026", 3, "2025-07", class_id="1067") is False
    assert "2025-07" not in calendar_service.get_candidate_months("2025-2026", 3, class_id="1067")

    # Approve exception for Semester 3 Class 1067
    cfg = calendar_service.resolve_term_calendar("2025-2026", 3, class_id="1067")
    cfg.approved_exceptional_months = ["2025-07"]
    calendar_service.save_calendar(cfg)

    # Now included and valid for Sem 3
    months_sem3 = calendar_service.get_candidate_months("2025-2026", 3, class_id="1067")
    assert "2025-07" in months_sem3
    assert months_sem3 == ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11"]
    assert calendar_service.is_month_in_window("2025-2026", 3, "2025-07", class_id="1067") is True

    # Must NOT pollute Semester 1 (AY 2024-2025 Sem 1)
    months_sem1 = calendar_service.get_candidate_months("2024-2025", 1, class_id="918")
    assert "2024-07" not in months_sem1
    assert "2025-07" not in months_sem1
    assert calendar_service.is_month_in_window("2024-2025", 1, "2024-07", class_id="918") is False

    # Must NOT pollute Semester 5 (AY 2026-2027 Sem 5)
    months_sem5 = calendar_service.get_candidate_months("2026-2027", 5, class_id="2582")
    assert "2026-07" not in months_sem5
    assert "2025-07" not in months_sem5
    assert calendar_service.is_month_in_window("2026-2027", 5, "2026-07", class_id="2582") is False
