"""Acceptance test suite for Phase E.2.1: Live Marks Pilot Acceptance & Source-Semantics Closure.

Strictly offline verification: zero external network or portal calls.
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    AttendanceSnapshotRow,
    Base,
    Course,
    PerformanceSnapshot,
    SyncJob,
)
from app.db.session import build_sqlite_url, create_app_engine, get_db
from app.main import app
from app.services.performance_service import (
    AssessmentClassification,
    CourseCoverageCategory,
    classify_assessment,
    overview,
    parse_performance,
    persist_performance,
    reconcile_course_coverage,
)


SYNTHETIC_GROUPED_HTML = """
<table>
  <tr>
    <th rowspan="2">Subject Code</th>
    <th rowspan="2">Subject Name</th>
    <th colspan="7">INTERNAL EXAM</th>
    <th colspan="1">EXTERNAL EXAM</th>
    <th colspan="1">External Exam</th>
  </tr>
  <tr>
    <th>CE</th>
    <th>CE 2</th>
    <th>Mid term examinations MRU</th>
    <th>CE 3</th>
    <th>CE 4</th>
    <th>CE 6</th>
    <th>CE 5</th>
    <th>End Semester Examination</th>
    <th>VIVA</th>
  </tr>
  <tr>
    <td>TEST101</td>
    <td>Theory Course</td>
    <td>15.0/20.0</td>
    <td>18.0/20.0</td>
    <td>35.0/40.0</td>
    <td>17.0/20.0</td>
    <td>--</td>
    <td>-</td>
    <td></td>
    <td>78.0/100.0</td>
    <td>--</td>
  </tr>
  <tr>
    <td>TEST102</td>
    <td>Practical Course</td>
    <td>20.0/20.0</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
    <td>45.0/50.0</td>
  </tr>
</table>
"""


def get_user_db_session() -> Session | None:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        return None
    user_db_path = Path(local_app_data) / "AttendPlan" / "attendplan.sqlite3"
    if not user_db_path.exists():
        return None
    engine = create_app_engine(build_sqlite_url(user_db_path))
    return Session(engine)


def test_assessment_classification_taxonomy():
    """Verify exact categorization of all standard and observed assessment headers."""
    # 1. Observed Semester 3 internal continuous evaluations
    assert classify_assessment("INTERNAL EXAM", "CE") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION
    assert classify_assessment("INTERNAL EXAM", "CE 2") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION
    assert classify_assessment("INTERNAL EXAM", "CE 3") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION
    assert classify_assessment("INTERNAL EXAM", "CE 4") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION
    assert classify_assessment("INTERNAL EXAM", "CE 5") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION
    assert classify_assessment("INTERNAL EXAM", "CE 6") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION

    # 2. Observed Semester 3 internal midterm
    assert classify_assessment("INTERNAL EXAM", "Mid term examinations MRU") == AssessmentClassification.INTERNAL_MIDTERM
    assert classify_assessment("INTERNAL", "MST-1") == AssessmentClassification.INTERNAL_MIDTERM
    assert classify_assessment("INTERNAL", "Midterm Exam") == AssessmentClassification.INTERNAL_MIDTERM

    # 3. Observed Semester 3 end-semester source field
    assert classify_assessment("EXTERNAL EXAM", "End Semester Examination") == AssessmentClassification.END_SEMESTER_SOURCE_FIELD
    assert classify_assessment("EXTERNAL", "End-Sem Theory") == AssessmentClassification.END_SEMESTER_SOURCE_FIELD
    assert classify_assessment("EXAM", "ESE") == AssessmentClassification.END_SEMESTER_SOURCE_FIELD

    # 4. Observed Semester 3 viva
    assert classify_assessment("External Exam", "VIVA") == AssessmentClassification.VIVA
    assert classify_assessment("INTERNAL EXAM", "Viva Voce") == AssessmentClassification.VIVA

    # 5. Practical assessments
    assert classify_assessment("INTERNAL EXAM", "Lab Continuous Assessment") == AssessmentClassification.PRACTICAL_ASSESSMENT
    assert classify_assessment("INTERNAL EXAM", "Practical Journal") == AssessmentClassification.PRACTICAL_ASSESSMENT

    # 6. Fallback
    assert classify_assessment("MISC", "Special Bonus") == AssessmentClassification.UNKNOWN_ASSESSMENT


def test_parse_grouped_marks_assigns_classifications():
    """Verify that parser attaches classification to every assessment item."""
    data = parse_performance(SYNTHETIC_GROUPED_HTML)
    assert len(data["courses"]) == 2
    c1 = data["courses"][0]
    classifications = {a["name"]: a["classification"] for a in c1["assessments"]}
    assert classifications["CE"] == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION.value
    assert classifications["Mid term examinations MRU"] == AssessmentClassification.INTERNAL_MIDTERM.value
    assert classifications["End Semester Examination"] == AssessmentClassification.END_SEMESTER_SOURCE_FIELD.value
    assert classifications["VIVA"] == AssessmentClassification.VIVA.value


def test_overview_excludes_end_semester_from_continuous_analytics(tmp_path: Path):
    """Verify overview filters END_SEMESTER_SOURCE_FIELD out of continuous evaluation insights."""
    url = build_sqlite_url(tmp_path / "acceptance_perf.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)
    parsed = parse_performance(SYNTHETIC_GROUPED_HTML)

    with Session(engine) as db:
        persist_performance(db, "2025-2026_s3_1067", "marks:test", parsed)
        data = overview(db)

    insights = data["terms"][0]["insights"]
    # End semester must NOT appear in continuous percentage comparison insights
    for insight in insights:
        if "highest recorded assessment percentage" in insight:
            assert "End Semester Examination" not in insight
    # End semester must be noted as raw source field
    assert any("End Semester Examination entries preserved as raw source fields" in i for i in insights)


def test_live_sem3_marks_117_cell_accounting():
    """Verify complete 117-cell accounting against live persisted Semester 3 marks snapshot."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snap = db.scalars(
            select(PerformanceSnapshot).where(PerformanceSnapshot.term_key == "2025-2026_s3_1067")
        ).first()
        assert snap is not None, "Semester 3 snapshot must exist in database"
        assert snap.checksum == "bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee"

        courses = snap.payload["courses"]
        assert len(courses) == 13

        total_cells = 0
        reported_count = 0
        unreported_count = 0

        for c in courses:
            assessments = c["assessments"]
            assert len(assessments) == 9, "Each of the 13 courses must have exactly 9 assessment columns"
            for a in assessments:
                total_cells += 1
                if a["status"] == "REPORTED":
                    reported_count += 1
                elif a["status"] == "UNREPORTED":
                    unreported_count += 1

        assert total_cells == 117, f"Expected 117 total cells, got {total_cells}"
        assert reported_count == 64, f"Expected 64 reported cells, got {reported_count}"
        assert unreported_count == 53, f"Expected 53 unreported cells, got {unreported_count}"
        assert reported_count + unreported_count == 117
    finally:
        db.close()


def test_live_sem3_course_coverage_reconciliation():
    """Verify reconciliation between 13 marks courses and 16 attendance components."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snap = db.scalars(
            select(PerformanceSnapshot).where(PerformanceSnapshot.term_key == "2025-2026_s3_1067")
        ).first()
        assert snap is not None

        cov = reconcile_course_coverage(db, "2025-2026_s3_1067", snap.payload)
        assert cov["total_catalog_courses"] == 16
        assert cov["total_performance_courses"] == 13
        assert cov["present_count"] == 13
        assert cov["aggregated_count"] == 1
        assert cov["absent_count"] == 2
        assert cov["unmapped_count"] == 0

        items_by_code = {i["course_code"]: i for i in cov["items"]}

        # 1. Component aggregated
        assert items_by_code["MAH204C-TUT"]["category"] == CourseCoverageCategory.COMPONENT_AGGREGATED.value
        assert "MAH204C" in items_by_code["MAH204C-TUT"]["reason"]

        # 2. Absent components
        assert items_by_code["EDN248C"]["category"] == CourseCoverageCategory.SOURCE_COURSE_ABSENT.value
        assert items_by_code["VAC-CS112"]["category"] == CourseCoverageCategory.SOURCE_COURSE_ABSENT.value

        # 3. Present courses
        assert items_by_code["CSH201C"]["category"] == CourseCoverageCategory.SOURCE_COURSE_PRESENT.value
        assert items_by_code["MAH204C"]["category"] == CourseCoverageCategory.SOURCE_COURSE_PRESENT.value
    finally:
        db.close()


def test_sync_job_details_payload_redaction(tmp_path: Path):
    """Verify that generic sync job queries redact captured_payload."""
    url = build_sqlite_url(tmp_path / "sync_security.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        job = SyncJob(
            source_scope="PERFORMANCE_PILOT_PREVIEW",
            state="COMPLETED",
            details={
                "term_key": "2025-2026_s3_1067",
                "view": "marks",
                "captured_payload": {"courses": [{"course_code": "SEC101"}]},
            },
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/portal/sync/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["details"]["captured_payload"]["redacted"] is True
        assert data["details"]["captured_payload"]["course_count"] == 1
        assert "courses" not in data["details"]["captured_payload"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_preview_approval_single_use_and_replay_prevention(tmp_path: Path):
    """Verify preview cannot be re-imported once claimed and approved."""
    url = build_sqlite_url(tmp_path / "replay_test.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        job = SyncJob(
            source_scope="PERFORMANCE_PILOT_PREVIEW",
            state="COMPLETED",
            details={
                "term_key": "2025-2026_s3_1067",
                "view": "marks",
                "exam_session": "6161",
                "exam_type": "3",
                "division_id": "A",
                "captured_payload": parse_performance(SYNTHETIC_GROUPED_HTML),
            },
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    with Session(engine) as db:
        from app.api.performance_routes import capture_performance, PerformanceRequest
        with patch.dict("os.environ", {"ATTENDPLAN_ENABLE_PERFORMANCE_PILOT": "1"}):
            with patch("app.api.performance_routes.verified_term") as mock_term:
                mock_term.return_value.term_key = "2025-2026_s3_1067"
                req = PerformanceRequest(
                    term_key="2025-2026_s3_1067",
                    view="marks",
                    approval_id=job_id,
                    exam_session="6161",
                    exam_type="3",
                    division_id="A",
                )
                res = capture_performance(req, db)
                assert res["snapshot_id"] is not None

                # Verify replay is rejected
                with pytest.raises(Exception) as exc_info:
                    capture_performance(req, db)
                assert "409" in str(exc_info.value) or "expired or was already used" in str(exc_info.value)


def test_preview_expiry_after_30_minutes(tmp_path: Path):
    """Verify that a preview older than 30 minutes is rejected."""
    url = build_sqlite_url(tmp_path / "expiry_test.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        job = SyncJob(
            source_scope="PERFORMANCE_PILOT_PREVIEW",
            state="COMPLETED",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=35),
            details={
                "term_key": "2025-2026_s3_1067",
                "view": "marks",
                "exam_session": "6161",
                "exam_type": "3",
                "division_id": "A",
                "captured_payload": parse_performance(SYNTHETIC_GROUPED_HTML),
            },
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    with Session(engine) as db:
        from app.api.performance_routes import capture_performance, PerformanceRequest
        with patch.dict("os.environ", {"ATTENDPLAN_ENABLE_PERFORMANCE_PILOT": "1"}):
            with patch("app.api.performance_routes.verified_term") as mock_term:
                mock_term.return_value.term_key = "2025-2026_s3_1067"
                req = PerformanceRequest(
                    term_key="2025-2026_s3_1067",
                    view="marks",
                    approval_id=job_id,
                    exam_session="6161",
                    exam_type="3",
                    division_id="A",
                )
                with pytest.raises(Exception) as exc_info:
                    capture_performance(req, db)
                assert "409" in str(exc_info.value) or "expired" in str(exc_info.value)


def test_cross_term_substitution_rejection(tmp_path: Path):
    """Verify preview approval cannot be reused across different academic terms or views."""
    url = build_sqlite_url(tmp_path / "substitution_test.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        job = SyncJob(
            source_scope="PERFORMANCE_PILOT_PREVIEW",
            state="COMPLETED",
            details={
                "term_key": "2025-2026_s3_1067",
                "view": "marks",
                "exam_session": "6161",
                "exam_type": "3",
                "division_id": "A",
            },
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    with Session(engine) as db:
        from app.api.performance_routes import capture_performance, PerformanceRequest
        with patch.dict("os.environ", {"ATTENDPLAN_ENABLE_PERFORMANCE_PILOT": "1"}):
            with patch("app.api.performance_routes.verified_term") as mock_term:
                mock_term.return_value.term_key = "2025-2026_s4_2508"
                # Mismatched term_key
                req = PerformanceRequest(
                    term_key="2025-2026_s4_2508",
                    view="marks",
                    approval_id=job_id,
                    exam_session="6161",
                    exam_type="3",
                    division_id="A",
                )
                with pytest.raises(Exception) as exc_info:
                    capture_performance(req, db)
                assert "409" in str(exc_info.value)


def test_database_baseline_preservation():
    """Verify that all historical attendance and marks records remain completely intact."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        assert db.scalars(select(AcademicTerm)).all().__len__() == 5
        assert db.scalars(select(Course)).all().__len__() == 76
        assert db.scalars(select(AttendanceSnapshot)).all().__len__() in (9, 10)
        assert db.scalars(select(AttendanceSnapshotRow)).all().__len__() in (136, 151)
        assert db.scalars(select(AttendancePeriodObservation)).all().__len__() in (3520, 3544)
        assert db.scalars(select(AttendanceObservationBatch)).all().__len__() in (28, 29)

        # Verify performance snapshots count and integrity
        perf_snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        assert len(perf_snaps) in (2, 5)
        s3 = next(s for s in perf_snaps if s.term_key == "2025-2026_s3_1067")
        s4 = next(s for s in perf_snaps if s.term_key == "2025-2026_s4_2508")
        assert s3.checksum == "bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee"
        assert s4.checksum == "c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d"
    finally:
        db.close()
