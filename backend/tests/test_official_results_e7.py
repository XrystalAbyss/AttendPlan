"""Phase E.7 regression and integration test suite: Official University Results.

Verifies:
1. Persistence of OfficialResultSnapshot and OfficialCourseResultRow in SQLite.
2. Idempotency and duplicate detection (DUPLICATE_SKIPPED).
3. Handling of WITHHELD publication status with zero courses and None SGPA/CGPA.
4. Clean architectural separation between Data Class A (internal marks) and Data Class B (official results).
5. Invariant against speculative GPA/grade synthesis.
6. Overview integration reporting official results alongside continuous evaluation.
7. Verification of user production DB post-E.7 integrity (if accessible).
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicTerm,
    AttendancePeriodObservation,
    Base,
    OfficialCourseResultRow,
    OfficialResultSnapshot as DBOfficialResultSnapshot,
    PerformanceSnapshot,
)
from app.db.session import build_sqlite_url, create_app_engine
from app.domain.results_models import (
    OfficialCourseResult,
    OfficialSemesterResult,
    ResultPublicationStatus,
)
from app.services.performance_service import overview
from app.services.results_service import (
    get_official_result_snapshot,
    overview_official_results,
    persist_official_result,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    """Temporary SQLite database with full schema initialized."""
    db_file = tmp_path / "test_results.sqlite3"
    url = build_sqlite_url(db_file)
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Create dummy AcademicTerm for Semester 4 to satisfy foreign key / lookup
        term = AcademicTerm(
            academic_year="2025-2026",
            semester_number=4,
            class_identifier="2508",
        )
        session.add(term)
        session.commit()

    yield engine
    engine.dispose()


def test_persist_withheld_official_result(temp_db):
    """Verify that a WITHHELD result (COE deactivated page) persists cleanly with zero courses and None SGPA."""
    with Session(temp_db) as session:
        result = OfficialSemesterResult(
            term_key="2025-2026_s4_2508",
            academic_year="2025-2026",
            semester_number=4,
            class_identifier="2508",
            exam_session=None,
            exam_session_label="Official Result Card (COE)",
            sgpa=None,
            cgpa=None,
            credits_registered=None,
            credits_earned=None,
            total_points_secured=None,
            publication_status=ResultPublicationStatus.WITHHELD,
            courses=[],
            declaration_date=None,
        )

        snapshot_row, status = persist_official_result(
            db=session,
            result=result,
            provenance="LIVE_PORTAL",
            raw_payload={"deactivation_notice": "Deactivated by COE Office"},
        )

        assert status == "COMMITTED"
        assert snapshot_row.id is not None
        assert len(snapshot_row.courses) == 0

        # Read back from database
        snapshot = get_official_result_snapshot(session, "2025-2026_s4_2508")
        assert snapshot is not None
        assert snapshot.publication_status == ResultPublicationStatus.WITHHELD.value
        assert snapshot.sgpa is None
        assert snapshot.cgpa is None
        assert snapshot.credits_earned is None
        assert len(snapshot.courses) == 0


def test_persist_duplicate_idempotency(temp_db):
    """Verify that attempting to re-persist an identical snapshot returns DUPLICATE_SKIPPED without mutating records."""
    with Session(temp_db) as session:
        result = OfficialSemesterResult(
            term_key="2025-2026_s4_2508",
            academic_year="2025-2026",
            semester_number=4,
            class_identifier="2508",
            exam_session=None,
            exam_session_label="Official Result Card (COE)",
            sgpa=None,
            cgpa=None,
            credits_registered=None,
            credits_earned=None,
            total_points_secured=None,
            publication_status=ResultPublicationStatus.WITHHELD,
            courses=[],
        )

        # First persistence
        snap1, status1 = persist_official_result(db=session, result=result, provenance="LIVE_PORTAL")
        assert status1 == "COMMITTED"

        # Second persistence (identical content checksum)
        snap2, status2 = persist_official_result(db=session, result=result, provenance="LIVE_PORTAL")
        assert status2 == "DUPLICATE_SKIPPED"
        assert snap2.id == snap1.id

        # Count snapshots in DB
        count = session.query(DBOfficialResultSnapshot).filter_by(term_key="2025-2026_s4_2508").count()
        assert count == 1


def test_data_class_a_and_b_table_isolation(temp_db):
    """Verify that Data Class A (PerformanceSnapshot) and Data Class B (OfficialResultSnapshot) are strictly isolated."""
    with Session(temp_db) as session:
        # Data Class A row
        perf_snap = PerformanceSnapshot(
            term_key="2025-2026_s4_2508",
            view="marks:6424:3:A",
            checksum="mock_class_a_hash_12345",
            provenance="LIVE_PORTAL",
            payload={"courses": []},
        )
        session.add(perf_snap)
        session.commit()

        # Data Class B row
        result = OfficialSemesterResult(
            term_key="2025-2026_s4_2508",
            academic_year="2025-2026",
            semester_number=4,
            class_identifier="2508",
            exam_session="6424",
            exam_session_label="Official Result Card",
            sgpa=8.2,
            cgpa=8.1,
            credits_registered=20.0,
            credits_earned=20.0,
            total_points_secured=164.0,
            publication_status=ResultPublicationStatus.PUBLISHED,
            courses=[
                OfficialCourseResult(
                    course_code="CSH201B",
                    course_name="Data Structures",
                    credits=4.0,
                    grade="A",
                    grade_point=9.0,
                )
            ],
        )
        snap_b, status_b = persist_official_result(db=session, result=result, provenance="LIVE_PORTAL")
        assert status_b == "COMMITTED"

        # Verify both exist independently under the same term_key
        class_a_count = session.query(PerformanceSnapshot).filter_by(term_key="2025-2026_s4_2508").count()
        class_b_count = session.query(DBOfficialResultSnapshot).filter_by(term_key="2025-2026_s4_2508").count()
        course_b_count = session.query(OfficialCourseResultRow).count()

        assert class_a_count == 1
        assert class_b_count == 1
        assert course_b_count == 1


def test_no_speculative_gpa_or_grade_synthesis(temp_db):
    """Verify that when official results are withheld or unpublished, no synthetic GPA or grades are created."""
    with Session(temp_db) as session:
        result = OfficialSemesterResult(
            term_key="2025-2026_s4_2508",
            academic_year="2025-2026",
            semester_number=4,
            class_identifier="2508",
            publication_status=ResultPublicationStatus.WITHHELD,
            courses=[],
        )
        persist_official_result(db=session, result=result, provenance="LIVE_PORTAL")

        overview_data = overview_official_results(session)
        assert len(overview_data["results"]) == 1
        snapshot_data = overview_data["results"][0]
        assert snapshot_data["publication_status"] == "WITHHELD"
        assert snapshot_data["sgpa"] is None
        assert snapshot_data["cgpa"] is None
        assert snapshot_data["credits_earned"] is None
        assert snapshot_data["courses_count"] == 0


def test_performance_overview_with_official_results(temp_db):
    """Verify that performance_service.overview() seamlessly enriches the term with official results."""
    with Session(temp_db) as session:
        # Add Class A snapshot
        perf_snap = PerformanceSnapshot(
            term_key="2025-2026_s4_2508",
            view="marks:6424:3:A",
            checksum="mock_hash_for_overview",
            provenance="LIVE_PORTAL",
            payload={"courses": [{"course_code": "CSH201B", "percentage": 85.0, "total": 85.0}]},
        )
        session.add(perf_snap)

        # Add Class B withheld snapshot
        result = OfficialSemesterResult(
            term_key="2025-2026_s4_2508",
            academic_year="2025-2026",
            semester_number=4,
            class_identifier="2508",
            publication_status=ResultPublicationStatus.WITHHELD,
            courses=[],
        )
        persist_official_result(
            db=session,
            result=result,
            provenance="LIVE_PORTAL",
            raw_payload={"deactivation_notice": "Deactivated by COE Office"},
        )
        session.commit()

        # Query overview
        ov = overview(session)
        assert len(ov["terms"]) == 1
        term_data = ov["terms"][0]
        assert term_data["term_key"] == "2025-2026_s4_2508"
        assert "official_result" in term_data
        assert term_data["official_result"]["publication_status"] == "WITHHELD"
        assert any("deactivated by COE Office" in insight for insight in term_data["insights"])


def test_user_db_semester_4_official_result_audit():
    """Verify the real user production database has exactly the truthful Semester 4 checkpoint."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        pytest.skip("LOCALAPPDATA not set")
    user_db_path = Path(local_app_data) / "AttendPlan" / "attendplan.sqlite3"
    if not user_db_path.exists():
        pytest.skip("Production database not found")

    engine = create_app_engine(build_sqlite_url(user_db_path))
    with Session(engine) as session:
        # Check Class B official result
        results = session.scalars(select(DBOfficialResultSnapshot)).all()
        assert len(results) == 1
        s4_res = results[0]
        assert s4_res.term_key == "2025-2026_s4_2508"
        assert s4_res.publication_status == "WITHHELD"
        assert s4_res.sgpa is None
        assert s4_res.cgpa is None
        assert len(s4_res.courses) == 0

        # Check Class A internal marks snapshots (must still be 5)
        marks_snaps = session.scalars(select(PerformanceSnapshot)).all()
        assert len(marks_snaps) == 5

        # Check attendance observations (baseline >= 3520, currently 3544 with recent observations)
        obs_count = session.query(AttendancePeriodObservation).count()
        assert obs_count >= 3520