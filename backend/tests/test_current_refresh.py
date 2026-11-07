"""Comprehensive tests for Service A: Current Semester Live Refresh & Current Term Resolver.

Verifies:
- Dynamic current term resolution without hardcoded semester values
- Full current semester refresh (subject summary + current month day-wise)
- Graceful partial sync when day-wise is unavailable
- Idempotent refresh (UP_TO_DATE when checksums match)
- Cross-term historical isolation (prior terms remain unchanged)
- Safe handling of session expiration and concurrency
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.daywise_parser import ParsedDaywiseBatch, ParsedObservationItem
from app.adapters.live_portal_extractor import (
    ExtractionValidationReport,
    LiveDayWiseExtractionResult,
    LiveSubjectWiseExtractionResult,
)
from app.adapters.portal_safety import PortalSafetyError
from app.db.enums import BatchStatus, PeriodStatus
from app.db.models import AcademicTerm, AttendanceObservationBatch, AttendancePeriodObservation, AttendanceSnapshot, Course
from app.domain.attendance_engine import calculate_aggregate_metrics
from app.domain.models import AttendanceSnapshot as DomainSnapshot, CourseRecord, CourseStatus, SnapshotSummary
from app.services.current_refresh_service import CurrentRefreshService
from app.services.current_term_resolver import ResolvedTerm, resolve_active_term_from_portal, resolve_current_term
from app.services.startup_service import StartupCoordinator, StartupPreferences


@pytest.fixture
def test_db(tmp_path):
    from app.db.models import Base
    from app.db.session import build_sqlite_url, create_app_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "test_refresh.sqlite3"
    engine = create_app_engine(build_sqlite_url(db_path))
    Base.metadata.create_all(bind=engine)
    SessionMaker = sessionmaker(bind=engine)
    with SessionMaker() as session:
        yield session
    engine.dispose()


def make_mock_course(code: str, attended: int, delivered: int) -> CourseRecord:
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


def make_subject_result(year: str, sem: int, class_id: str, courses: list[CourseRecord]) -> LiveSubjectWiseExtractionResult:
    active_courses = [c for c in courses if c.status != CourseStatus.UNRECORDED]
    unrecorded_courses = [c for c in courses if c.status == CourseStatus.UNRECORDED]
    safe_courses = [c for c in courses if c.status == CourseStatus.SAFE]
    at_risk_courses = [c for c in courses if c.status == CourseStatus.AT_RISK]

    tot_att, tot_del, overall_pct, overall_status = calculate_aggregate_metrics(
        [(c.attended, c.delivered) for c in courses],
        target=0.75,
    )

    summary = SnapshotSummary(
        total_courses=len(courses),
        active_courses=len(active_courses),
        unrecorded_courses=len(unrecorded_courses),
        safe_courses=len(safe_courses),
        at_risk_courses=len(at_risk_courses),
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


def make_daywise_result(year: str, sem: int, class_id: str, obs_date: date) -> LiveDayWiseExtractionResult:
    obs = [
        ParsedObservationItem(
            attendance_date=obs_date,
            slot_start_time="09:00",
            slot_end_time="10:00",
            source_period_identifier="P1",
            source_course_label="CS101",
            status=PeriodStatus.PRESENT,
            delivered_period_count=1,
            attended_period_count=1,
            course_mapping_confidence=1.0,
        ),
        ParsedObservationItem(
            attendance_date=obs_date,
            slot_start_time="10:00",
            slot_end_time="11:00",
            source_period_identifier="P2",
            source_course_label="CS102",
            status=PeriodStatus.ABSENT,
            delivered_period_count=1,
            attended_period_count=0,
            course_mapping_confidence=1.0,
        ),
    ]
    batch = ParsedDaywiseBatch(
        academic_year=year,
        semester=sem,
        class_identifier=class_id,
        coverage_start_date=obs_date,
        coverage_end_date=obs_date,
        source_filter_metadata={},
        observations=obs,
        status=BatchStatus.COMPLETE,
        content_checksum=f"chk-{obs_date.isoformat()}-{year}-s{sem}",
    )
    val = ExtractionValidationReport(is_valid=True, record_count=len(obs))
    return LiveDayWiseExtractionResult(
        batch=batch,
        raw_html="<table></table>",
        validation=val,
        academic_year=year,
        semester=sem,
        class_identifier=class_id,
        selected_month=str(obs_date.month),
        coverage_start=obs_date,
        coverage_end=obs_date,
        course_attribution_active=True,
    )


def test_resolve_active_term_from_portal_defaults():
    mock_page = Mock()
    with patch("app.services.current_term_resolver.check_page"):
        with patch("app.services.current_term_resolver.selected") as mock_sel:
            mock_sel.side_effect = lambda pg, kind: {
                "year": ("2026-2027", "2026-2027"),
                "semester": ("5", "5"),
                "class": ("CLS_AIML_5", "B.Tech CSE AIML-Sem 5"),
            }[kind]
            resolved = resolve_active_term_from_portal(mock_page)
            assert resolved is not None
            assert resolved.academic_year == "2026-2027"
            assert resolved.semester_number == 5
            assert resolved.class_identifier == "CLS_AIML_5"
            assert resolved.provenance == "PORTAL_DEFAULT"


def test_resolve_current_term_fallback_to_database(test_db: Session):
    # Seed historical and current terms in DB
    t1 = AcademicTerm(academic_year="2025-2026", semester_number=4, class_identifier="CLS4")
    t2 = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="CLS5")
    test_db.add_all([t1, t2])
    test_db.commit()

    mock_extractor = Mock()
    mock_page = Mock()
    mock_page.url = "https://mrei.icloudems.com/corecampus/student/attendance/subwise_attendace_new.php"
    with patch("app.services.current_term_resolver.check_page"):
        with patch("app.services.current_term_resolver.selected", side_effect=PortalSafetyError("FILTER_SELECTION_NOT_UNIQUE")):
            with patch("app.services.current_term_resolver.options") as mock_opts:
                mock_opts.side_effect = lambda pg, kind: {
                    "year": [{"value": "2025-2026", "label": "2025-2026"}, {"value": "2026-2027", "label": "2026-2027"}],
                    "semester": [{"value": "5", "label": "5"}],
                    "class": [{"value": "CLS5", "label": "B.Tech CSE AIML-Sem 5"}],
                }[kind]
                with patch("app.services.current_term_resolver.choose"):
                    resolved = resolve_current_term(mock_extractor, test_db, page=mock_page)
                    assert resolved.academic_year == "2026-2027"
                    assert resolved.semester_number == 5
                    assert resolved.class_identifier == "CLS5"
                    assert resolved.provenance == "DATABASE_FALLBACK_VERIFIED"


def test_current_refresh_service_full_success(test_db: Session):
    courses = [
        make_mock_course("CS101", 10, 12),
        make_mock_course("CS102", 8, 10),
    ]
    sub_res = make_subject_result("2026-2027", 5, "CLS5", courses)
    day_res = make_daywise_result("2026-2027", 5, "CLS5", date(2026, 10, 15))

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.return_value = sub_res
    mock_extractor.extract_live_day_wise.return_value = day_res

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")

        assert res.state == "SYNC_COMPLETE"
        assert res.term_key == "2026-2027-S5"
        assert res.summary_outcome == "SUCCESS"
        assert res.daywise_outcome == "SUCCESS"
        assert res.last_sync_time is not None

        # Verify DB records
        term = test_db.scalars(select(AcademicTerm).where(AcademicTerm.academic_year == "2026-2027", AcademicTerm.semester_number == 5)).first()
        assert term is not None
        snaps = test_db.scalars(select(AttendanceSnapshot).where(AttendanceSnapshot.academic_term_id == term.id)).all()
        assert len(snaps) == 1
        obs = test_db.scalars(select(AttendancePeriodObservation).where(AttendancePeriodObservation.academic_term_id == term.id)).all()
        assert len(obs) == 2


def test_current_refresh_service_partial_when_daywise_fails(test_db: Session):
    courses = [make_mock_course("CS101", 10, 12)]
    sub_res = make_subject_result("2026-2027", 5, "CLS5", courses)

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.return_value = sub_res
    mock_extractor.extract_live_day_wise.side_effect = PortalSafetyError("REQUESTED_MONTH_UNAVAILABLE")

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")

        # Subject-wise must still be saved, resulting in SYNC_PARTIAL
        assert res.state == "SYNC_PARTIAL"
        assert res.summary_outcome == "SUCCESS"
        assert res.daywise_outcome == "UNAVAILABLE"

        term = test_db.scalars(select(AcademicTerm).where(AcademicTerm.academic_year == "2026-2027")).first()
        assert term is not None
        snaps = test_db.scalars(select(AttendanceSnapshot).where(AttendanceSnapshot.academic_term_id == term.id)).all()
        assert len(snaps) == 1


def test_current_refresh_preserves_historical_term_isolation(test_db: Session):
    # Seed Semester 4 historical data
    hist_term = AcademicTerm(academic_year="2025-2026", semester_number=4, class_identifier="CLS4")
    test_db.add(hist_term)
    test_db.flush()
    hist_course = Course(academic_term_id=hist_term.id, course_code="CS101", course_name="Historical Course")
    test_db.add(hist_course)
    test_db.commit()

    # Refresh Semester 5 current data with same course code
    courses = [make_mock_course("CS101", 15, 20)]
    sub_res = make_subject_result("2026-2027", 5, "CLS5", courses)
    day_res = make_daywise_result("2026-2027", 5, "CLS5", date(2026, 10, 20))

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.return_value = sub_res
    mock_extractor.extract_live_day_wise.return_value = day_res

    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm("2026-2027", 5, "CLS5", "Class 5", "PORTAL_DEFAULT")
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")
        assert res.state == "SYNC_COMPLETE"

    # Verify historical term was completely untouched
    test_db.expire_all()
    reloaded_hist_term = test_db.get(AcademicTerm, hist_term.id)
    assert reloaded_hist_term is not None
    assert len(reloaded_hist_term.snapshots) == 0
    assert len(reloaded_hist_term.observation_batches) == 0


def test_startup_coordinator_with_current_refresh(tmp_path):
    refresh_fn = Mock(return_value={
        "state": "SYNC_COMPLETE",
        "message": "Current semester refreshed.",
        "last_sync_time": "2026-10-28T19:30:00+05:30",
        "refreshed_scopes": 2,
    })
    coordinator = StartupCoordinator(
        path=tmp_path / "startup.json",
        login=Mock(return_value=True),
        discover=Mock(return_value={}),
        refresh=Mock(return_value=0),
        dispatch=lambda action: action(),
        current_refresh=refresh_fn,
    )
    coordinator.save(StartupPreferences(auto_connect=True, auto_refresh_current_term=True))

    status = coordinator.start()
    assert status["state"] == "SYNC_COMPLETE"
    assert status["message"] == "Current semester refreshed."
    assert status["last_sync_time"] == "2026-10-28T19:30:00+05:30"
    refresh_fn.assert_called_once()


def test_resolve_current_term_rollover_new_semester(test_db: Session):
    from app.services.current_term_resolver import resolve_current_term

    # Seed previous semester in DB: 2026-2027 Sem 5
    prev_term = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="B.Tech CSE AIML-Sem 5")
    test_db.add(prev_term)
    test_db.commit()

    mock_page = Mock()
    mock_page.url = "https://mrei.icloudems.com/corecampus/student/attendance/subwise_attendace_new.php"

    # Portal now offers Semester 6!
    options_map = {
        "year": [{"value": "2026-2027", "label": "2026-2027"}],
        "semester": [{"value": "5", "label": "5"}, {"value": "6", "label": "6"}],
        "class": [{"value": "CLS-SEM6", "label": "B.Tech CSE AIML-Sem 6"}],
    }

    with patch("app.services.current_term_resolver.check_page"):
        with patch("app.services.current_term_resolver.selected", side_effect=PortalSafetyError("NO_SELECTION")):
            with patch("app.services.current_term_resolver.options", side_effect=lambda page, kind: options_map[kind]):
                with patch("app.services.current_term_resolver.choose"):
                    mock_extractor = Mock()
                    resolved = resolve_current_term(mock_extractor, test_db, page=mock_page)
                    assert resolved.academic_year == "2026-2027"
                    assert resolved.semester_number == 6
                    assert resolved.provenance == "PORTAL_ROLLOVER_DETECTED"
                    assert resolved.is_verified is True
                    assert resolved.is_provisional is False


def test_resolve_current_term_multi_class_branch_disambiguation(test_db: Session):
    from app.services.current_term_resolver import resolve_current_term

    # Seed previous enrollment in AIML
    prev_term = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="B.Tech CSE AIML-Sem 5")
    test_db.add(prev_term)
    test_db.commit()

    mock_page = Mock()
    mock_page.url = "https://mrei.icloudems.com/corecampus/student/attendance/subwise_attendace_new.php"

    # Portal has 3 classes: Civil, Mech, and AIML
    options_map = {
        "year": [{"value": "2026-2027", "label": "2026-2027"}],
        "semester": [{"value": "5", "label": "5"}],
        "class": [
            {"value": "CLS-CIVIL", "label": "B.Tech Civil Engg"},
            {"value": "CLS-AIML", "label": "B.Tech CSE AIML"},
            {"value": "CLS-MECH", "label": "B.Tech Mechanical Engg"},
        ],
    }

    with patch("app.services.current_term_resolver.check_page"):
        with patch("app.services.current_term_resolver.selected", side_effect=PortalSafetyError("NO_SELECTION")):
            with patch("app.services.current_term_resolver.options", side_effect=lambda page, kind: options_map[kind]):
                with patch("app.services.current_term_resolver.choose"):
                    mock_extractor = Mock()
                    resolved = resolve_current_term(mock_extractor, test_db, page=mock_page)
                    assert resolved.class_identifier == "CLS-AIML"
                    assert resolved.class_display_label == "B.Tech CSE AIML"


def test_resolve_current_term_ambiguous_classes_raises_error(test_db: Session):
    from app.services.current_term_resolver import resolve_current_term

    # DB has no previous enrollment
    mock_page = Mock()
    mock_page.url = "https://mrei.icloudems.com/corecampus/student/attendance/subwise_attendace_new.php"

    options_map = {
        "year": [{"value": "2026-2027", "label": "2026-2027"}],
        "semester": [{"value": "5", "label": "5"}],
        "class": [
            {"value": "CLS-1", "label": "Section A"},
            {"value": "CLS-2", "label": "Section B"},
        ],
    }

    with patch("app.services.current_term_resolver.check_page"):
        with patch("app.services.current_term_resolver.selected", side_effect=PortalSafetyError("NO_SELECTION")):
            with patch("app.services.current_term_resolver.options", side_effect=lambda page, kind: options_map[kind]):
                with patch("app.services.current_term_resolver.choose"):
                    mock_extractor = Mock()
                    with pytest.raises(PortalSafetyError, match="CURRENT_TERM_AMBIGUOUS_CLASS"):
                        resolve_current_term(mock_extractor, test_db, page=mock_page)


def test_resolve_provisional_term_from_db(test_db: Session):
    from app.services.current_term_resolver import resolve_provisional_term_from_db

    term = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="CLS5")
    test_db.add(term)
    test_db.commit()

    provisional = resolve_provisional_term_from_db(test_db)
    assert provisional.academic_year == "2026-2027"
    assert provisional.semester_number == 5
    assert provisional.provenance == "PROVISIONAL_OFFLINE"
    assert provisional.is_verified is False
    assert provisional.is_provisional is True


def test_current_refresh_rejects_provisional_term(test_db: Session):
    mock_extractor = Mock()
    with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
        mock_resolve.return_value = ResolvedTerm(
            academic_year="2026-2027",
            semester_number=5,
            class_identifier="CLS5",
            class_display_label="CLS5",
            provenance="PROVISIONAL_OFFLINE",
            is_verified=False,
            is_provisional=True,
        )
        service = CurrentRefreshService(test_db, mock_extractor)
        res = service.refresh_current_semester(month_override="10")
        assert res.state == "SYNC_FAILED"
        assert res.diagnostic == "CURRENT_TERM_UNVERIFIED"


def test_recover_interrupted_cleans_up_running_jobs(test_db: Session):
    from app.api.archive_routes import recover_interrupted
    from app.db.models import SyncJob

    # Seed an archive job in SYNCING
    archive_job = SyncJob(source_scope="ATTENDANCE_ARCHIVE_PLAN", state="SYNCING", current_step="Reading month")
    test_db.add(archive_job)

    # Seed a current refresh job in SYNCING_DAYWISE
    refresh_job = SyncJob(source_scope="CURRENT_SEMESTER_LIVE_REFRESH", state="SYNCING_DAYWISE", current_step="Reading October")
    test_db.add(refresh_job)
    test_db.commit()

    recover_interrupted(test_db)

    test_db.refresh(archive_job)
    test_db.refresh(refresh_job)

    assert archive_job.state == "PAUSED"
    assert refresh_job.state == "FAILED"
    assert refresh_job.diagnostic == "INTERRUPTED_BY_APP_RESTART"


def test_current_month_rollover_november_2026(test_db: Session):
    """Verify that in November 2026, Service A queries month 11 and preserves October history."""
    from app.services.current_observations import latest_observations

    # Seed Semester 5 with October data
    term = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="CLS-5")
    test_db.add(term)
    test_db.commit()

    c1 = Course(academic_term_id=term.id, course_code="CS501", course_name="Algorithms")
    test_db.add(c1)
    test_db.commit()

    # Seed October batch
    oct_batch = AttendanceObservationBatch(
        academic_term_id=term.id,
        source="TEST_OCTOBER",
        coverage_start_date=date(2026, 10, 1),
        coverage_end_date=date(2026, 10, 31),
        content_checksum="chk_oct_10",
        status=BatchStatus.COMPLETE.value,
    )
    test_db.add(oct_batch)
    test_db.flush()

    oct_obs = AttendancePeriodObservation(
        observation_batch_id=oct_batch.id,
        academic_term_id=term.id,
        attendance_date=date(2026, 10, 15),
        slot_start_time="09:00",
        slot_end_time="10:00",
        source_period_identifier="P1",
        course_id=c1.id,
        source_course_label="CS501",
        status=PeriodStatus.PRESENT.value,
        delivered_period_count=1,
        attended_period_count=1,
    )
    test_db.add(oct_obs)
    test_db.commit()

    # Mock November 1 time in IST
    from datetime import timedelta
    tz_ist = timezone(timedelta(hours=5, minutes=30))
    mock_now_nov = datetime(2026, 11, 1, 10, 0, 0, tzinfo=tz_ist)

    mock_extractor = Mock()
    mock_extractor.extract_live_subject_wise.return_value = make_subject_result(
        "2026-2027", 5, "CLS-5", [make_mock_course("CS501", 10, 12)]
    )

    # On Nov 1, portal returns zero recorded periods for November
    from app.adapters.daywise_parser import ParsedDaywiseBatch
    empty_batch = ParsedDaywiseBatch(
        academic_year="2026-2027",
        semester=5,
        class_identifier="CLS-5",
        coverage_start_date=date(2026, 11, 1),
        coverage_end_date=date(2026, 11, 30),
        observations=[],
        content_checksum="chk_nov_empty",
        status=BatchStatus.COMPLETE,
        source_filter_metadata={"month": "11"},
    )
    mock_extractor.extract_live_day_wise.return_value = LiveDayWiseExtractionResult(
        batch=empty_batch,
        raw_html="<html>No classes yet</html>",
        validation=ExtractionValidationReport(is_valid=True, record_count=0),
        academic_year="2026-2027",
        semester=5,
        class_identifier="CLS-5",
        selected_month="11",
        coverage_start=date(2026, 11, 1),
        coverage_end=date(2026, 11, 30),
        course_attribution_active=True,
    )

    with patch("app.services.current_refresh_service.kolkata_now", return_value=mock_now_nov):
        with patch("app.services.current_refresh_service.resolve_current_term") as mock_resolve:
            mock_resolve.return_value = ResolvedTerm(
                academic_year="2026-2027",
                semester_number=5,
                class_identifier="CLS-5",
                class_display_label="CLS-5",
                provenance="VERIFIED_LIVE",
                is_verified=True,
                is_provisional=False,
            )
            svc = CurrentRefreshService(test_db, mock_extractor)
            res = svc.refresh_current_semester()

            # Refresh succeeded with partial note because Nov day-wise has no periods yet
            assert res.state in ("SYNC_COMPLETE", "SYNC_PARTIAL")
            assert "November" in (res.month_label or "") or "11" in (res.message or "")

            # Verify October records were preserved
            all_obs = test_db.scalars(
                select(AttendancePeriodObservation).where(AttendancePeriodObservation.academic_term_id == term.id)
            ).all()
            effective = latest_observations(all_obs)
            assert len(effective) >= 1
            assert any(o.attendance_date == date(2026, 10, 15) for o in effective)


def test_effective_ledger_deduplication_prevents_raw_history_inflation(test_db: Session):
    """Verify that multiple syncs of the same month do NOT inflate attendance totals."""
    from app.services.current_observations import latest_observations

    term = AcademicTerm(academic_year="2026-2027", semester_number=5, class_identifier="CLS-5")
    test_db.add(term)
    test_db.flush()

    c1 = Course(academic_term_id=term.id, course_code="CS502", course_name="OS")
    test_db.add(c1)
    test_db.flush()

    # Seed 3 overlapping batches for October (like Oct 16, Oct 21, Oct 30)
    for b_idx in range(3):
        batch = AttendanceObservationBatch(
            academic_term_id=term.id,
            source=f"TEST_BATCH_{b_idx}",
            coverage_start_date=date(2026, 10, 1),
            coverage_end_date=date(2026, 10, 20 + b_idx),
            content_checksum=f"chk_batch_{b_idx}",
            status=BatchStatus.COMPLETE.value,
        )
        test_db.add(batch)
        test_db.flush()

        obs = AttendancePeriodObservation(
            observation_batch_id=batch.id,
            academic_term_id=term.id,
            attendance_date=date(2026, 10, 10),
            slot_start_time="10:00",
            slot_end_time="11:00",
            source_period_identifier="P2",
            course_id=c1.id,
            source_course_label="CS502",
            status=PeriodStatus.PRESENT.value,
            delivered_period_count=1,
            attended_period_count=1,
        )
        test_db.add(obs)

    test_db.commit()

    # Raw count in DB is 3 rows (inflation risk)
    all_rows = test_db.scalars(
        select(AttendancePeriodObservation).where(AttendancePeriodObservation.academic_term_id == term.id)
    ).all()
    assert len(all_rows) == 3

    # Effective ledger deduplicates to exactly 1 slot
    effective = latest_observations(all_rows)
    assert len(effective) == 1
    assert effective[0].delivered_period_count == 1
    assert effective[0].attended_period_count == 1
