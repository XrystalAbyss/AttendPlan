"""Comprehensive failure injection and resilience tests for AttendPlan Phase C.1.

Simulates 13 critical failure conditions using isolated synthetic fixtures:
1. University portal timeout
2. Invalid authentication
3. Session expiry
4. Wrong academic term returned
5. Wrong month returned
6. Empty valid report
7. Portal warning page
8. Parser failure
9. Database write failure
10. Browser disconnect
11. Backend restart cleanup
12. Concurrent requests
13. Manual recovery availability
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.live_portal_extractor import (
    ExtractionValidationReport,
    LiveSubjectWiseExtractionResult,
)
from app.adapters.portal_safety import DaywiseScopeOutcome, PortalSafetyError, classify_daywise_html
from app.api.archive_routes import recover_interrupted
from app.db.models import AcademicTerm, AttendanceSnapshot, SyncJob
from app.domain.attendance_engine import calculate_aggregate_metrics
from app.domain.models import AttendanceSnapshot as DomainSnapshot, CourseRecord, CourseStatus, SnapshotSummary
from app.services.current_refresh_service import CurrentRefreshService, _SYNC_LOCK
from app.services.current_term_resolver import ResolvedTerm
from app.services.startup_service import StartupCoordinator


@pytest.fixture
def test_db(tmp_path):
    from app.db.models import Base
    from app.db.session import build_sqlite_url, create_app_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "test_failure_injection.sqlite3"
    engine = create_app_engine(build_sqlite_url(db_path))
    Base.metadata.create_all(bind=engine)
    SessionMaker = sessionmaker(bind=engine)
    with SessionMaker() as session:
        yield session
    engine.dispose()


@pytest.fixture(autouse=True)
def ensure_sync_lock_released():
    """Ensure _SYNC_LOCK is cleanly released before and after every test."""
    if _SYNC_LOCK.locked():
        try:
            _SYNC_LOCK.release()
        except RuntimeError:
            pass
    yield
    if _SYNC_LOCK.locked():
        try:
            _SYNC_LOCK.release()
        except RuntimeError:
            pass


def make_sample_course(code: str, attended: int, delivered: int) -> CourseRecord:
    pct = (attended / delivered * 100.0) if delivered > 0 else None
    status = CourseStatus.UNRECORDED if delivered == 0 else (CourseStatus.SAFE if (pct or 0) >= 75.0 else CourseStatus.AT_RISK)
    return CourseRecord(
        code=code,
        name=f"Course {code}",
        short_name=code,
        attended=attended,
        delivered=delivered,
        percent=pct,
        status=status,
        can_skip=max(0, int(attended / 0.75 - delivered)) if delivered > 0 else 0,
        must_attend=0,
    )


def make_sample_subject_result(year: str, sem: int, class_id: str, courses: list[CourseRecord]) -> LiveSubjectWiseExtractionResult:
    tot_att, tot_del, overall_pct, overall_status = calculate_aggregate_metrics(
        [(c.attended, c.delivered) for c in courses],
        target=0.75,
    )
    summary = SnapshotSummary(
        total_courses=len(courses),
        active_courses=len([c for c in courses if c.status != CourseStatus.UNRECORDED]),
        unrecorded_courses=len([c for c in courses if c.status == CourseStatus.UNRECORDED]),
        safe_courses=len([c for c in courses if c.status == CourseStatus.SAFE]),
        at_risk_courses=len([c for c in courses if c.status == CourseStatus.AT_RISK]),
        total_attended=tot_att,
        total_delivered=tot_del,
        overall_percentage=overall_pct,
        overall_status=overall_status,
    )
    snap = DomainSnapshot(
        id=f"snap-{year}-s{sem}",
        academic_year=year,
        semester=sem,
        class_name=class_id,
        courses=courses,
        summary=summary,
        captured_at=datetime.now(timezone.utc).isoformat(),
    )
    val = ExtractionValidationReport(is_valid=True, record_count=len(courses))
    return LiveSubjectWiseExtractionResult(
        snapshot=snap,
        raw_html="<table></table>",
        validation=val,
        academic_year=year,
        semester=sem,
        class_identifier=class_id,
        reporting_start_date=None,
        reporting_end_date=None,
    )


# 1. University Portal Timeout
def test_failure_injection_portal_timeout(test_db: Session):
    term = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="CLS5")
    test_db.add(term)
    test_db.commit()

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.side_effect = TimeoutError("Portal request timed out after 30s")

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")

        assert res.state == "SYNC_FAILED"
        assert "Portal request timed out" in (res.message or "")
        assert test_db.scalars(select(AttendanceSnapshot)).first() is None
        assert not _SYNC_LOCK.locked()


# 2. Invalid Authentication Redirect
def test_failure_injection_invalid_authentication(test_db: Session):
    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.side_effect = PortalSafetyError("AUTHENTICATION_REQUIRED")

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")

        assert res.state == "SYNC_FAILED"
        assert res.diagnostic == "AUTHENTICATION_REQUIRED"
        assert not _SYNC_LOCK.locked()


# 3. Session Expiry During Day-Wise Extraction
def test_failure_injection_session_expiry_during_daywise(test_db: Session):
    # Subject wise succeeds
    courses = [make_sample_course("CS101", 20, 25)]
    sub_res = make_sample_subject_result("2026-2027", 5, "CLS5", courses)

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.return_value = sub_res
    # Day wise hits session expiry
    mock_extractor.extract_live_day_wise.side_effect = PortalSafetyError("AUTHENTICATION_REQUIRED")

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")

        # Graceful partial sync: subject summary saved, daywise reports unavailable
        assert res.state == "SYNC_PARTIAL"
        assert res.summary_outcome == "SUCCESS"
        assert res.daywise_outcome == "UNAVAILABLE"

        # Subject-wise snapshot was durably persisted
        saved_snap = test_db.scalars(select(AttendanceSnapshot)).first()
        assert saved_snap is not None
        assert saved_snap.record_count == 1
        assert not _SYNC_LOCK.locked()


# 4. Wrong Academic Term Returned
def test_failure_injection_wrong_academic_term(test_db: Session):
    courses = [make_sample_course("CS101", 20, 25)]
    sub_res = make_sample_subject_result("2024-2025", 2, "CLS2", courses)  # Returned older term!
    # Mark validation as failed due to term mismatch
    sub_res.validation = ExtractionValidationReport(is_valid=False, record_count=0, quarantine_reason="RETURNED_ACADEMIC_YEAR_MISMATCH")

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.return_value = sub_res

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")

        assert res.state == "SYNC_FAILED"
        assert res.diagnostic == "RETURNED_ACADEMIC_YEAR_MISMATCH"
        assert test_db.scalars(select(AttendanceSnapshot)).first() is None
        assert not _SYNC_LOCK.locked()


# 5. Wrong Month Returned
def test_failure_injection_wrong_month_returned(test_db: Session):
    html = """
    <div id="report_header">Month: September 2026</div>
    <table id="attendance_table"><tr><td>2026-09-01</td></tr></table>
    """
    outcome = classify_daywise_html(html, requested_month="2026-10")
    assert outcome == DaywiseScopeOutcome.UNVERIFIED_SOURCE


# 6. Empty Valid Report (No Delivered Periods)
def test_failure_injection_empty_valid_report(test_db: Session):
    html = """
    <select name="academic_year"><option value="2026-2027" selected>2026-2027</option></select>
    <select name="semester"><option value="5" selected>5</option></select>
    <div class="table-responsive">
        <p>No records found for the selected duration</p>
    </div>
    """
    outcome = classify_daywise_html(html, requested_month="2026-10")
    assert outcome == DaywiseScopeOutcome.EXPLICIT_EMPTY_RESULT


# 7. Portal Warning Page
def test_failure_injection_portal_warning_page(test_db: Session):
    html = """
    <div class="alert alert-warning">No attendance record found for the selected month.</div>
    """
    outcome = classify_daywise_html(html, requested_month="2026-10")
    assert outcome == DaywiseScopeOutcome.WARNING_PAGE


# 8. Parser Failure on Malformed HTML
def test_failure_injection_parser_failure(test_db: Session):
    html = """
    <select name="academic_year"><option value="2026-2027" selected>2026-2027</option></select>
    <select name="semester"><option value="5" selected>5</option></select>
    <table id="daywise"><tr><td>unparseable non-grid</td></tr></table>
    """
    outcome = classify_daywise_html(html, requested_month="2026-10")
    assert outcome == DaywiseScopeOutcome.PARSER_FAILURE


# 9. Database Write Failure Rollback and Lock Safety
def test_failure_injection_database_write_failure(test_db: Session):
    courses = [make_sample_course("CS101", 10, 15)]
    sub_res = make_sample_subject_result("2026-2027", 5, "CLS5", courses)

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.return_value = sub_res

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)

        with patch.object(test_db, "commit", side_effect=RuntimeError("Disk write I/O error")):
            res = service.refresh_current_semester(month_override="10")
            assert res.state == "SYNC_FAILED"
            assert "Disk write I/O error" in (res.message or "")
            assert not _SYNC_LOCK.locked()


# 10. Browser Disconnect / CDP Crash
def test_failure_injection_browser_disconnect(test_db: Session):
    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.side_effect = ConnectionResetError("CDP connection closed by remote peer")

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")

        assert res.state == "SYNC_FAILED"
        assert "CDP connection closed" in (res.message or "")
        assert not _SYNC_LOCK.locked()


# 11. Backend Restart Interrupted Jobs Cleanup
def test_failure_injection_backend_restart_cleanup(test_db: Session):
    # Seed stale running jobs
    j1 = SyncJob(source_scope="CURRENT_SEMESTER_LIVE_REFRESH", state="RUNNING", current_step="Syncing October")
    j2 = SyncJob(source_scope="ATTENDANCE_ARCHIVE_PLAN", state="SYNCING_SUBWISE", current_step="Syncing Sem 1")
    test_db.add_all([j1, j2])
    test_db.commit()

    recover_interrupted(test_db)

    test_db.refresh(j1)
    test_db.refresh(j2)

    assert j1.state == "FAILED"
    assert j1.safe_diagnostic_message == "INTERRUPTED_BY_APP_RESTART"
    assert j2.state == "PAUSED"


# 12. Concurrent Requests Mutex Lock
def test_failure_injection_concurrent_requests_handled(test_db: Session):
    assert not _SYNC_LOCK.locked()
    _SYNC_LOCK.acquire()
    try:
        mock_extractor = Mock()
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")
        assert res.state == "SYNC_FAILED"
        assert res.diagnostic == "PORTAL_BUSY"
    finally:
        _SYNC_LOCK.release()


# 13. Manual Forced Refresh Always Available
def test_failure_injection_manual_recovery_available(tmp_path):
    refresh_fn = Mock(return_value={"state": "SYNC_COMPLETE", "message": "Forced sync successful", "last_sync_time": "2026-10-28T21:00:00+05:30", "refreshed_scopes": 2})
    coordinator = StartupCoordinator(
        path=tmp_path / "startup.json",
        login=Mock(return_value=True),
        discover=Mock(return_value={}),
        refresh=Mock(return_value=0),
        dispatch=lambda action: action(),
        current_refresh=refresh_fn,
    )
    coordinator.last_attempt = datetime.now(timezone.utc).timestamp()
    status = coordinator.start(force=True)
    assert status["state"] == "SYNC_COMPLETE"
    assert status["message"] == "Forced sync successful"
    refresh_fn.assert_called_once()
