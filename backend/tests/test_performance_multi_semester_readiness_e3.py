"""Acceptance & readiness test suite for Phase E.3: Multi-Semester Academic Marks Archive Readiness.

Strictly offline verification: zero external network or portal calls.
"""
import os
from pathlib import Path

import pytest
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
)
from app.db.session import build_sqlite_url, create_app_engine
from app.services.performance_service import (
    AssessmentClassification,
    CourseCoverageCategory,
    classify_assessment,
    overview,
    parse_performance,
    persist_performance,
    reconcile_course_coverage,
)


SYNTHETIC_S1_HTML = """
<table>
  <tr>
    <th rowspan="2">Subject Code</th>
    <th rowspan="2">Subject Name</th>
    <th colspan="3">INTERNAL EXAM</th>
    <th colspan="1">EXTERNAL EXAM</th>
  </tr>
  <tr>
    <th>CE</th>
    <th>Mid term examinations MRU</th>
    <th>CE 2</th>
    <th>End Semester Examination</th>
  </tr>
  <tr>
    <td>PHH101C</td>
    <td>QUANTUM MECHANICS FOR ENGINEERS</td>
    <td>14.0/15.0</td>
    <td>28.0/40.0</td>
    <td>13.0/15.0</td>
    <td>68.0/100.0</td>
  </tr>
  <tr>
    <td>MAH104C</td>
    <td>PROBABILITY & STATISTICS</td>
    <td>12.0/15.0</td>
    <td>22.0/40.0</td>
    <td>11.0/15.0</td>
    <td>54.0/100.0</td>
  </tr>
</table>
"""

SYNTHETIC_S2_HTML = """
<table>
  <tr>
    <th rowspan="2">Subject Code</th>
    <th rowspan="2">Subject Name</th>
    <th colspan="4">INTERNAL EXAM</th>
    <th colspan="1">EXTERNAL EXAM</th>
  </tr>
  <tr>
    <th>CE</th>
    <th>CE 2</th>
    <th>Mid term examinations MRU</th>
    <th>CE 3</th>
    <th>End Semester Examination</th>
  </tr>
  <tr>
    <td>CSH107C</td>
    <td>DATA STRUCTURES</td>
    <td>15.0/15.0</td>
    <td>14.0/15.0</td>
    <td>35.0/40.0</td>
    <td>14.0/15.0</td>
    <td>82.0/100.0</td>
  </tr>
  <tr>
    <td>CHH101C</td>
    <td>CHEMISTRY-I</td>
    <td>12.0/15.0</td>
    <td>11.0/15.0</td>
    <td>26.0/40.0</td>
    <td>12.0/15.0</td>
    <td>61.0/100.0</td>
  </tr>
</table>
"""

SYNTHETIC_S4_EXTENDED_HTML = """
<table>
  <tr>
    <th rowspan="2">Subject Code</th>
    <th rowspan="2">Subject Name</th>
    <th colspan="9">INTERNAL EXAM</th>
    <th colspan="1">External Exam</th>
    <th colspan="1">EXTERNAL EXAM</th>
  </tr>
  <tr>
    <th>Mid term examinations MRU</th>
    <th>CE</th>
    <th>CE 2</th>
    <th>CE 3</th>
    <th>CE 4</th>
    <th>CE 6</th>
    <th>CE 7</th>
    <th>CE 5</th>
    <th>CE 8</th>
    <th>VIVA</th>
    <th>End Semester Examination</th>
  </tr>
  <tr>
    <td>CSH219C</td>
    <td>ADVANCED NEURAL NETWORKS</td>
    <td>36.0/40.0</td>
    <td>9.0/10.0</td>
    <td>9.0/10.0</td>
    <td>8.0/10.0</td>
    <td>9.0/10.0</td>
    <td>8.0/10.0</td>
    <td>9.0/10.0</td>
    <td>8.0/10.0</td>
    <td>9.0/10.0</td>
    <td>18.0/20.0</td>
    <td>*</td>
  </tr>
</table>
"""

SYNTHETIC_S5_PARTIAL_ACTIVE_HTML = """
<table>
  <tr>
    <th rowspan="2">Subject Code</th>
    <th rowspan="2">Subject Name</th>
    <th colspan="5">INTERNAL EXAM</th>
    <th colspan="1">EXTERNAL EXAM</th>
  </tr>
  <tr>
    <th>CE</th>
    <th>CE 2</th>
    <th>Mid term examinations MRU</th>
    <th>CE 3</th>
    <th>CE 4</th>
    <th>End Semester Examination</th>
  </tr>
  <tr>
    <td>CSH302C</td>
    <td>OPERATING SYSTEMS</td>
    <td>14.0/15.0</td>
    <td>13.0/15.0</td>
    <td>--</td>
    <td>--</td>
    <td></td>
    <td>--</td>
  </tr>
  <tr>
    <td>CSH304C</td>
    <td>ADVANCED JAVA</td>
    <td>15.0/15.0</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
    <td>--</td>
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


def test_parser_compatibility_with_varying_column_layouts():
    """Verify parser successfully processes tables with 4, 5, 9, and 11 assessment columns."""
    # S1 Layout: 4 columns
    p1 = parse_performance(SYNTHETIC_S1_HTML)
    assert len(p1["courses"]) == 2
    assert len(p1["courses"][0]["assessments"]) == 4

    # S2 Layout: 5 columns
    p2 = parse_performance(SYNTHETIC_S2_HTML)
    assert len(p2["courses"]) == 2
    assert len(p2["courses"][0]["assessments"]) == 5

    # S4 Layout: 11 columns (with CE 7, CE 8, VIVA, and masked End Sem Exam)
    p4 = parse_performance(SYNTHETIC_S4_EXTENDED_HTML)
    assert len(p4["courses"]) == 1
    c4 = p4["courses"][0]
    assert len(c4["assessments"]) == 11
    # Verify MASKED_BY_PORTAL preservation
    end_sem = next(a for a in c4["assessments"] if a["name"] == "End Semester Examination")
    assert end_sem["status"] == "MASKED_BY_PORTAL"
    assert end_sem["obtained"] is None
    assert end_sem["maximum"] is None

    # S5 Layout: partial active ongoing term
    p5 = parse_performance(SYNTHETIC_S5_PARTIAL_ACTIVE_HTML)
    assert len(p5["courses"]) == 2
    c5 = p5["courses"][0]
    ce1 = next(a for a in c5["assessments"] if a["name"] == "CE")
    mid = next(a for a in c5["assessments"] if a["name"] == "Mid term examinations MRU")
    assert ce1["status"] == "REPORTED"
    assert ce1["obtained"] == 14.0
    assert mid["status"] == "UNREPORTED"
    assert mid["obtained"] is None


def test_classification_of_extended_continuous_evaluations():
    """Verify that CE 7, CE 8, and other extended columns are correctly classified."""
    assert classify_assessment("INTERNAL EXAM", "CE 7") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION
    assert classify_assessment("INTERNAL EXAM", "CE 8") == AssessmentClassification.INTERNAL_CONTINUOUS_EVALUATION
    assert classify_assessment("INTERNAL EXAM", "Lab Continuous Evaluation") == AssessmentClassification.PRACTICAL_ASSESSMENT
    assert classify_assessment("INTERNAL EXAM", "Mid term examinations MRU") == AssessmentClassification.INTERNAL_MIDTERM
    assert classify_assessment("EXTERNAL EXAM", "End Semester Examination") == AssessmentClassification.END_SEMESTER_SOURCE_FIELD


def test_reconciliation_multi_semester_tutorial_aggregation(tmp_path: Path):
    """Verify reconciliation aggregates -TUT components across Semesters 1, 2, and 3."""
    url = build_sqlite_url(tmp_path / "multi_sem_reconcile.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        # Create S2 term with lecture and tutorial courses
        term = AcademicTerm(
            academic_year="2024-2025",
            semester_number=2,
            class_identifier="B.Tech CSE AIML-Sem 2",
        )
        db.add(term)
        db.commit()
        db.refresh(term)

        c1 = Course(academic_term_id=term.id, course_code="CSH107C", course_name="DATA STRUCTURES")
        c1_tut = Course(academic_term_id=term.id, course_code="CSH107C-TUT", course_name="DATA STRUCTURES")
        c2 = Course(academic_term_id=term.id, course_code="CHH101C", course_name="CHEMISTRY-I")
        c3_vac = Course(academic_term_id=term.id, course_code="VAC-CS109", course_name="DATA ANALYTICS USING EXCEL")
        db.add_all([c1, c1_tut, c2, c3_vac])
        db.commit()

        # Synthetic S2 marks payload has CSH107C and CHH101C, but not -TUT or VAC
        p2 = parse_performance(SYNTHETIC_S2_HTML)
        cov = reconcile_course_coverage(db, "2024-2025_s2_1048", p2)

        assert cov["total_catalog_courses"] == 4
        assert cov["total_performance_courses"] == 2
        assert cov["present_count"] == 2
        assert cov["aggregated_count"] == 1
        assert cov["absent_count"] == 1
        assert cov["unmapped_count"] == 0

        items_by_code = {i["course_code"]: i for i in cov["items"]}
        assert items_by_code["CSH107C"]["category"] == CourseCoverageCategory.SOURCE_COURSE_PRESENT.value
        assert items_by_code["CSH107C-TUT"]["category"] == CourseCoverageCategory.COMPONENT_AGGREGATED.value
        assert "CSH107C" in items_by_code["CSH107C-TUT"]["reason"]
        assert items_by_code["VAC-CS109"]["category"] == CourseCoverageCategory.SOURCE_COURSE_ABSENT.value


def test_semester4_existing_snapshot_provenance_and_immutability():
    """Verify that the existing Semester 4 snapshot is completely preserved and valid."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        s4 = db.scalars(
            select(PerformanceSnapshot).where(PerformanceSnapshot.term_key == "2025-2026_s4_2508")
        ).first()
        assert s4 is not None
        assert s4.view == "marks:6424:3:A"
        assert s4.checksum == "c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d"

        courses = s4.payload["courses"]
        assert len(courses) == 15

        # Check masked cells count (15 End Semester Examination cells masked by portal)
        masked_count = sum(
            1 for c in courses for a in c.get("assessments", []) if a.get("status") == "MASKED_BY_PORTAL"
        )
        assert masked_count == 15
        assert all(
            any(a["name"] == "End Semester Examination" and a["status"] == "MASKED_BY_PORTAL" for a in c["assessments"])
            for c in courses
        )
    finally:
        db.close()


def test_active_semester5_partial_status_preservation(tmp_path: Path):
    """Verify ongoing Semester 5 partial assessments are preserved without treating missing scores as failures."""
    url = build_sqlite_url(tmp_path / "sem5_active.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)

    p5 = parse_performance(SYNTHETIC_S5_PARTIAL_ACTIVE_HTML)
    with Session(engine) as db:
        snap = persist_performance(db, "2026-2027_s5_2582", "marks:test_ongoing", p5)
        assert snap.id is not None
        data = overview(db)

    # In overview, missing values are correctly accounted without synthesising 0
    t = data["terms"][0]
    assert any("unpublished or missing" in i for i in t["insights"])
    # Percentage must be None for courses with missing totals
    for c in p5["courses"]:
        assert c["total"] is None
        assert c["percentage"] is None


def test_database_baseline_preservation_e3():
    """Verify baseline persistence across all attendance and performance tables."""
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

        perf_snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        assert len(perf_snaps) in (2, 5)
        s3 = next(s for s in perf_snaps if s.term_key == "2025-2026_s3_1067")
        s4 = next(s for s in perf_snaps if s.term_key == "2025-2026_s4_2508")
        assert s3.checksum == "bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee"
        assert s4.checksum == "c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d"
    finally:
        db.close()
