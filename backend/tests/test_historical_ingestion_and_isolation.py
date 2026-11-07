"""Tests for multi-semester ingestion, isolation, idempotency, and coverage (Milestone F2-E)."""

from __future__ import annotations

from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.enums import IngestionOutcome
from app.db.models import (
    AcademicTerm,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    Base,
    Course,
)
from app.domain.historical_models import CoverageState
from app.services.historical_backfill_service import HistoricalBackfillService
from app.services.historical_discovery_service import HistoricalDiscoveryService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_multi_semester_backfill_isolation_and_coverage(test_db: Session):
    backfill_service = HistoricalBackfillService(test_db)
    discovery_service = HistoricalDiscoveryService(test_db)

    # 1. Ingest Semester 1
    s1_html = (FIXTURES_DIR / "synthetic_semester1_subjectwise.html").read_text(encoding="utf-8")
    res_s1 = backfill_service.import_term_offline(
        academic_year="2024-2025",
        semester=1,
        class_id="1050",
        subject_html=s1_html,
    )
    assert res_s1["subject_outcome"] == IngestionOutcome.SUCCESS.value

    # 2. Ingest Semester 2
    s2_html = (FIXTURES_DIR / "synthetic_semester2_subjectwise.html").read_text(encoding="utf-8")
    res_s2 = backfill_service.import_term_offline(
        academic_year="2024-2025",
        semester=2,
        class_id="1410",
        subject_html=s2_html,
    )
    assert res_s2["subject_outcome"] == IngestionOutcome.SUCCESS.value

    # 3. Ingest Semester 3
    s3_html = (FIXTURES_DIR / "synthetic_semester3_subjectwise.html").read_text(encoding="utf-8")
    res_s3 = backfill_service.import_term_offline(
        academic_year="2025-2026",
        semester=3,
        class_id="1820",
        subject_html=s3_html,
    )
    assert res_s3["subject_outcome"] == IngestionOutcome.SUCCESS.value

    # 4. Ingest Semester 4 (Subject-wise + Day-wise March 2026)
    s4_sub_html = (FIXTURES_DIR / "synthetic_semester4_subjectwise.html").read_text(encoding="utf-8")
    s4_day_html = (FIXTURES_DIR / "synthetic_semester4_daywise.html").read_text(encoding="utf-8")
    res_s4 = backfill_service.import_term_offline(
        academic_year="2025-2026",
        semester=4,
        class_id="2140",
        subject_html=s4_sub_html,
        daywise_html_list=[s4_day_html],
    )
    assert res_s4["subject_outcome"] == IngestionOutcome.SUCCESS.value
    assert len(res_s4["daywise_batches"]) == 1
    assert res_s4["daywise_batches"][0]["outcome"] == IngestionOutcome.SUCCESS.value

    # 5. Ingest existing Semester 5 pilot fixture
    s5_sub_path = Path(__file__).parent.parent / "app" / "adapters" / "sample_attendance.html"
    if s5_sub_path.exists():
        s5_sub_html = s5_sub_path.read_text(encoding="utf-8")
    else:
        # Fallback to test fixture
        s5_sub_html = (FIXTURES_DIR / "sample_attendance.html").read_text(encoding="utf-8")

    res_s5 = backfill_service.import_term_offline(
        academic_year="2026-2027",
        semester=5,
        class_id="2582",
        subject_html=s5_sub_html,
    )
    assert res_s5["subject_outcome"] == IngestionOutcome.SUCCESS.value

    # -------------------------------------------------------------
    # Multi-Semester Isolation Verification (Domain Invariant #13)
    # -------------------------------------------------------------
    terms = test_db.scalars(select(AcademicTerm).order_by(AcademicTerm.semester_number)).all()
    assert len(terms) == 5

    # Each term has distinct ID
    term_ids = {t.id for t in terms}
    assert len(term_ids) == 5

    # Courses in Semester 4 are strictly separated from Semester 5
    s4_term = next(t for t in terms if t.semester_number == 4)
    s5_term = next(t for t in terms if t.semester_number == 5)

    s4_courses = test_db.scalars(select(Course).where(Course.academic_term_id == s4_term.id)).all()
    s5_courses = test_db.scalars(select(Course).where(Course.academic_term_id == s5_term.id)).all()

    s4_course_ids = {c.id for c in s4_courses}
    s5_course_ids = {c.id for c in s5_courses}
    assert s4_course_ids.isdisjoint(s5_course_ids)

    # -------------------------------------------------------------
    # Structural Header Row Exclusion Verification
    # -------------------------------------------------------------
    s4_obs = test_db.scalars(
        select(AttendancePeriodObservation).where(AttendancePeriodObservation.academic_term_id == s4_term.id)
    ).all()

    # Verify that "Lecture Timings" structural header was NOT parsed as an observation
    for o in s4_obs:
        assert "lecture timing" not in (o.source_period_identifier or "").lower()
        assert "total" not in (o.source_period_identifier or "").lower()

    # -------------------------------------------------------------
    # Idempotency & Deduplication Verification
    # -------------------------------------------------------------
    # Resync Semester 4 again with identical HTML
    res_s4_repeat = backfill_service.import_term_offline(
        academic_year="2025-2026",
        semester=4,
        class_id="2140",
        subject_html=s4_sub_html,
        daywise_html_list=[s4_day_html],
    )
    # Both subject-wise and day-wise should be DUPLICATE_SKIPPED
    assert res_s4_repeat["subject_outcome"] == IngestionOutcome.DUPLICATE_SKIPPED.value
    assert res_s4_repeat["daywise_batches"][0]["outcome"] == IngestionOutcome.DUPLICATE_SKIPPED.value

    # Observation count should remain unchanged
    s4_obs_after = test_db.scalars(
        select(AttendancePeriodObservation).where(AttendancePeriodObservation.academic_term_id == s4_term.id)
    ).all()
    assert len(s4_obs_after) == len(s4_obs)

    # Snapshot count should remain 1
    s4_snaps = test_db.scalars(
        select(AttendanceSnapshot).where(AttendanceSnapshot.academic_term_id == s4_term.id)
    ).all()
    assert len(s4_snaps) == 1

    # -------------------------------------------------------------
    # Coverage Tracking Verification
    # -------------------------------------------------------------
    cov_s4 = discovery_service.get_term_coverage(s4_term.id)
    assert cov_s4.has_subject_summary is True
    assert cov_s4.unique_instructional_dates > 0
    assert cov_s4.unique_instructional_periods > 0
    # Because only March was imported, coverage is PARTIAL (not complete for all 5 candidate months)
    assert cov_s4.coverage_state == CoverageState.PARTIAL


def test_file_database_restart_and_retry_durability(tmp_path):
    from app.db.session import build_sqlite_url, create_app_engine

    path = tmp_path / "durability.sqlite3"
    subject = (FIXTURES_DIR / "synthetic_semester4_subjectwise.html").read_text(encoding="utf-8")
    daywise = (FIXTURES_DIR / "synthetic_semester4_daywise.html").read_text(encoding="utf-8")
    engine = create_app_engine(build_sqlite_url(path))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = HistoricalBackfillService(db).import_term_offline(
            "2025-2026", 4, "2140", subject, [daywise]
        )
        term_id = result["term_id"]
        before = len(db.scalars(select(AttendancePeriodObservation)).all())
        assert before > 0
    engine.dispose()

    # A new engine and connection must see committed records, and retry must not inflate them.
    engine = create_app_engine(build_sqlite_url(path))
    with Session(engine) as db:
        assert db.get(AcademicTerm, term_id) is not None
        assert len(db.scalars(select(AttendancePeriodObservation)).all()) == before
        retry = HistoricalBackfillService(db).import_term_offline(
            "2025-2026", 4, "2140", subject, [daywise]
        )
        assert retry["subject_outcome"] == "DUPLICATE_SKIPPED"
        assert retry["daywise_batches"][0]["outcome"] == "DUPLICATE_SKIPPED"
        assert len(db.scalars(select(AttendancePeriodObservation)).all()) == before
    engine.dispose()


def test_unverified_term_never_contacts_portal(test_db):
    from unittest.mock import Mock
    from app.services.sync_job_service import SyncJobService

    extractor = Mock()
    job = SyncJobService(test_db, extractor).create_job()
    result = HistoricalBackfillService(test_db, extractor, pacing_delay_seconds=0).run_historical_backfill(
        job.id, ["2025-2026_s4_2140"]
    )
    assert result.state == "FAILED"
    extractor.extract_live_subject_wise.assert_not_called()


def test_daywise_session_expiry_stops_and_preserves_subjects(test_db):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app.adapters.html_parser import ERPAttendanceParser
    from app.adapters.live_portal_extractor import SessionNotAuthenticatedError
    from app.services.sync_job_service import SyncJobService

    html = (FIXTURES_DIR / "synthetic_semester4_subjectwise.html").read_text(encoding="utf-8")
    service = HistoricalBackfillService(test_db, pacing_delay_seconds=0)
    service.import_term_offline("2025-2026", 4, "2140", html)
    from app.db.models import SyncJob
    test_db.add(SyncJob(source_scope="HISTORICAL_SELECTOR_DISCOVERY", state="COMPLETED", details={
        "combinations": [{"academic_year":"2025-2026", "semester":"4", "class_id":"2140", "class_label":"B.Tech CSE AIML-Sem 4"}]
    }))
    test_db.commit()
    key = HistoricalDiscoveryService(test_db).get_persisted_inventory().terms[0].term_key
    extractor = Mock()
    extractor.extract_live_subject_wise.return_value = SimpleNamespace(
        snapshot=ERPAttendanceParser().parse_html(html),
        academic_year="2025-2026", semester=4, class_identifier="B.Tech CSE AIML-Sem 4",
        validation=SimpleNamespace(is_valid=True, quarantined=False, percentage_deviations=[]),
    )
    extractor.extract_live_day_wise.side_effect = SessionNotAuthenticatedError("expired")
    job = SyncJobService(test_db, extractor).create_job()
    result = HistoricalBackfillService(test_db, extractor, pacing_delay_seconds=0).run_historical_backfill(
        job.id, [key], import_daywise=True, requested_month="2026-03"
    )
    assert result.state == "SESSION_EXPIRED"
    assert result.completed_batches == 1
    assert result.failed_batches == 1
    assert extractor.extract_live_day_wise.call_count == 1
    assert len(test_db.scalars(select(AttendanceSnapshot)).all()) == 1
    assert len(test_db.scalars(select(Course)).all()) > 0


def test_cancellation_from_other_session_is_not_overwritten(tmp_path):
    from app.db.session import build_sqlite_url, create_app_engine
    from app.db.enums import SyncJobState
    from app.services.sync_job_service import SyncJobService
    engine = create_app_engine(build_sqlite_url(tmp_path / "cancel.sqlite3"))
    Base.metadata.create_all(engine)
    with Session(engine) as first:
        job = SyncJobService(first).create_job()
        with Session(engine) as second:
            SyncJobService(second).cancel_job(job.id)
        updated = SyncJobService(first).update_job_progress(job.id, SyncJobState.COMPLETED, "Late completion")
        assert updated.state == "CANCELLED"
    engine.dispose()
