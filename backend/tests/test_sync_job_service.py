"""Unit tests for SyncJobService state machine and pilot execution."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.daywise_parser import ParsedDaywiseBatch, ParsedObservationItem
from app.adapters.live_portal_extractor import (
    ExtractionValidationReport,
    LiveDayWiseExtractionResult,
    LivePortalExtractor,
    LiveSubjectWiseExtractionResult,
    SessionNotAuthenticatedError,
)
from app.db.enums import BatchStatus, PeriodStatus, SyncJobState
from app.db.models import Base
from app.domain.models import AttendanceSnapshot as DomainSnapshot, CourseRecord, CourseStatus, SnapshotSummary
from app.services.sync_job_service import SyncJobService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def create_dummy_subject_result() -> LiveSubjectWiseExtractionResult:
    course = CourseRecord(
        code="CSH301C",
        name="Operating Systems",
        short_name="OS - PP",
        faculty="Dr. Test",
        credits=3.0,
        attended=15,
        delivered=20,
        percent=75.0,
        status=CourseStatus.SAFE,
        can_skip=0,
        must_attend=0,
        margin_summary="Safe",
    )
    summary = SnapshotSummary(
        total_courses=1,
        active_courses=1,
        unrecorded_courses=0,
        safe_courses=1,
        at_risk_courses=0,
        total_attended=15,
        total_delivered=20,
        overall_percentage=75.0,
        overall_status=CourseStatus.SAFE,
    )
    snap = DomainSnapshot(
        id="snap-test-pilot",
        academic_year="2026-2027",
        semester=5,
        class_name="AIML-5",
        summary=summary,
        courses=[course],
        captured_at="2026-10-19T12:00:00Z",
    )
    return LiveSubjectWiseExtractionResult(
        snapshot=snap,
        raw_html="<table></table>",
        validation=ExtractionValidationReport(is_valid=True, record_count=1),
        academic_year="2026-2027",
        semester=5,
        class_identifier="AIML-5",
        reporting_start_date="2026-08-01",
        reporting_end_date="2026-11-30",
    )


def create_dummy_daywise_result() -> LiveDayWiseExtractionResult:
    obs = ParsedObservationItem(
        attendance_date=date(2026, 10, 1),
        slot_start_time="09:00",
        slot_end_time="09:50",
        source_period_identifier="09:00 - 09:50",
        source_course_label="CSH301C",
        status=PeriodStatus.PRESENT,
        delivered_period_count=1,
        attended_period_count=1,
        course_mapping_confidence=1.0,
    )
    batch = ParsedDaywiseBatch(
        academic_year="2026-2027",
        semester=5,
        class_identifier="AIML-5",
        coverage_start_date=date(2026, 10, 1),
        coverage_end_date=date(2026, 10, 31),
        source_filter_metadata={"month": "10"},
        status=BatchStatus.COMPLETE,
        content_checksum="dummy_checksum_12345",
        observations=[obs],
    )
    return LiveDayWiseExtractionResult(
        batch=batch,
        raw_html="<table></table>",
        validation=ExtractionValidationReport(is_valid=True, record_count=1),
        academic_year="2026-2027",
        semester=5,
        class_identifier="AIML-5",
        selected_month="10",
        coverage_start=date(2026, 10, 1),
        coverage_end=date(2026, 10, 31),
        course_attribution_active=True,
    )


def test_sync_job_lifecycle_and_state_transitions(db_session: Session) -> None:
    """Verifies job creation, updates, and final state assignment in SQLite."""
    service = SyncJobService(db_session)
    job = service.create_job(source_scope="CURRENT_SEMESTER_PILOT", progress_total=4)
    assert job.id is not None
    assert job.state == SyncJobState.IDLE.value
    assert job.progress_total == 4
    assert job.progress_current == 0

    updated = service.update_job_progress(
        job_id=job.id,
        state=SyncJobState.SYNCING_SUBJECTS,
        step="Extracting subjects",
        progress_current=1,
    )
    assert updated.state == SyncJobState.SYNCING_SUBJECTS.value
    assert updated.progress_current == 1


def test_sync_job_cancellation(db_session: Session) -> None:
    """Explicit cancellation transitions state to CANCELLED cleanly."""
    service = SyncJobService(db_session)
    job = service.create_job(source_scope="CURRENT_SEMESTER_PILOT")
    cancelled = service.cancel_job(job.id)
    assert cancelled.state == SyncJobState.CANCELLED.value
    assert cancelled.completion_timestamp is not None


def test_pilot_sync_success_flow(db_session: Session) -> None:
    """Executes full pilot: Subject-Wise + Day-Wise + Persistence + Reconciliation."""
    mock_extractor = MagicMock(spec=LivePortalExtractor)
    mock_extractor.extract_live_subject_wise.return_value = create_dummy_subject_result()
    mock_extractor.extract_live_day_wise.return_value = create_dummy_daywise_result()

    service = SyncJobService(db_session, extractor=mock_extractor)
    job = service.create_job(source_scope="CURRENT_SEMESTER_PILOT")

    completed = service.run_pilot_sync(job_id=job.id, month="10")
    assert completed.state == SyncJobState.COMPLETED.value
    assert completed.completed_batches == 2
    assert completed.failed_batches == 0
    assert completed.academic_term_id is not None
    assert completed.details is not None
    assert "reconciliation_status" in completed.details


def test_pilot_sync_handles_session_expired(db_session: Session) -> None:
    """Session expiration cleanly sets state to SESSION_EXPIRED without crashing."""
    mock_extractor = MagicMock(spec=LivePortalExtractor)
    mock_extractor.extract_live_subject_wise.side_effect = SessionNotAuthenticatedError("Manual login required.")

    service = SyncJobService(db_session, extractor=mock_extractor)
    job = service.create_job(source_scope="CURRENT_SEMESTER_PILOT")

    result = service.run_pilot_sync(job_id=job.id)
    assert result.state == SyncJobState.SESSION_EXPIRED.value
    assert "Manual login required" in (result.safe_diagnostic_message or "")


def test_preview_metadata_never_becomes_latest_sync_job(db_session):
    service = SyncJobService(db_session)
    assert service.get_latest_job() is None
    service.create_job(source_scope="HISTORICAL_SELECTOR_DISCOVERY")
    service.create_job(source_scope="HISTORICAL_PILOT_PREVIEW")
    service.create_job(source_scope="PERFORMANCE_PILOT_PREVIEW")
    assert service.get_latest_job() is None
    imported = service.create_job(source_scope="HISTORICAL_MULTI_SEMESTER_BACKFILL")
    assert service.get_latest_job().id == imported.id
