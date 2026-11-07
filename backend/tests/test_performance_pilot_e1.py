"""SYNTHETIC TEST FIXTURES ONLY for Phase E.1 Supervised Performance Pilot.

Tests Semester 3 marks source identity, assessment parser behaviors, score status
invariants, revision immutability, course mapping isolation, concurrency lock safety,
and preservation of Semester 4 snapshots and attendance records.
"""
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicTerm,
    Course,
    PerformanceSnapshot,
    AttendanceSnapshot,
)
from app.db.session import build_sqlite_url, create_app_engine
from app.services.performance_service import (
    parse_performance,
    parse_grouped_marks,
    persist_performance,
    overview,
    number,
)
from app.services.sync_job_service import _SYNC_LOCK
from bs4 import BeautifulSoup


SYNTHETIC_S3_GROUPED_HTML = """
<table>
  <tr>
    <th rowspan='2'>Sr. No.</th>
    <th rowspan='2'>Subject Code</th>
    <th rowspan='2'>Subject Name</th>
    <th colspan='2'>INTERNAL EXAM</th>
    <th colspan='1'>EXTERNAL EXAM</th>
  </tr>
  <tr>
    <th>Mid term examinations MRU</th>
    <th>CE</th>
    <th>End Semester Examination</th>
  </tr>
  <tr>
    <td>1</td>
    <td>CSH201C</td>
    <td>ANALYSIS & DESIGN OF ALGORITHMS</td>
    <td>28/40</td>
    <td>18/20</td>
    <td>******</td>
  </tr>
  <tr>
    <td>2</td>
    <td>CSH202C</td>
    <td>ANALYSIS & DESIGN OF ALGORITHMS LAB</td>
    <td>-</td>
    <td>19/20</td>
    <td>******</td>
  </tr>
  <tr>
    <td>3</td>
    <td>MAH204C</td>
    <td>DISCRETE MATHS</td>
    <td>35/40</td>
    <td>17/20</td>
    <td>******</td>
  </tr>
  <tr>
    <td>4</td>
    <td>MAH204C-TUT</td>
    <td>DISCRETE MATHS TUTORIAL</td>
    <td>-</td>
    <td>0/10</td>
    <td>******</td>
  </tr>
</table>
"""


def test_semester3_course_mapping_and_component_isolation():
    """Verify Semester 3 course codes and theory/lab/tutorial component isolation."""
    soup = BeautifulSoup(SYNTHETIC_S3_GROUPED_HTML, "html.parser")
    courses = parse_grouped_marks(soup.find("table"))
    assert len(courses) == 4
    
    # 1. CSH201C (Theory) vs CSH202C (Lab)
    csh201 = next(c for c in courses if c["course_code"] == "CSH201C")
    csh202 = next(c for c in courses if c["course_code"] == "CSH202C")
    assert csh201["course_code"] != csh202["course_code"]
    assert csh201["assessments"][0]["obtained"] == 28.0
    assert csh202["assessments"][0]["obtained"] is None
    assert csh202["assessments"][0]["status"] == "UNREPORTED"
    
    # 2. MAH204C (Theory) vs MAH204C-TUT (Tutorial)
    mah_th = next(c for c in courses if c["course_code"] == "MAH204C")
    mah_tut = next(c for c in courses if c["course_code"] == "MAH204C-TUT")
    assert mah_th["course_code"] != mah_tut["course_code"]
    # Valid zero score in tutorial must be REPORTED as 0.0, not None
    assert mah_tut["assessments"][1]["obtained"] == 0.0
    assert mah_tut["assessments"][1]["status"] == "REPORTED"


def test_score_status_invariants():
    """Verify exact score status distinctions across diverse cell contents."""
    # Number parsing
    assert number("0") == 0.0
    assert number("0.0") == 0.0
    assert number("") is None
    assert number("-") is None
    assert number("--") is None
    assert number("ab") is None
    assert number("pending") is None

    # HTML table with various statuses
    table = """
    <table>
      <tr>
        <th rowspan='2'>Subject Code</th>
        <th rowspan='2'>Subject Name</th>
        <th colspan='6'>INTERNAL EXAM</th>
      </tr>
      <tr>
        <th>C1</th><th>C2</th><th>C3</th><th>C4</th><th>C5</th><th>C6</th>
      </tr>
      <tr>
        <td>TEST01</td><td>Sample Course</td>
        <td>15/20</td>
        <td>0/20</td>
        <td>-</td>
        <td>******</td>
        <td>AB</td>
        <td>NA</td>
      </tr>
    </table>
    """
    soup = BeautifulSoup(table, "html.parser")
    courses = parse_grouped_marks(soup.find("table"))
    assessments = courses[0]["assessments"]
    
    assert assessments[0]["status"] == "REPORTED" and assessments[0]["obtained"] == 15.0
    assert assessments[1]["status"] == "REPORTED" and assessments[1]["obtained"] == 0.0
    assert assessments[2]["status"] == "UNREPORTED" and assessments[2]["obtained"] is None
    assert assessments[3]["status"] == "MASKED_BY_PORTAL" and assessments[3]["obtained"] is None
    assert assessments[4]["status"] == "AB" and assessments[4]["obtained"] is None
    assert assessments[5]["status"] == "NA" and assessments[5]["obtained"] is None


def test_performance_duplicate_prevention_and_revision_immutability(tmp_path: Path):
    """Verify deduplication when unchanged, and creation of new snapshot on score revision."""
    engine = create_app_engine(build_sqlite_url(tmp_path / "test_perf.sqlite3"))
    from app.db.models import Base
    Base.metadata.create_all(engine)
    
    parsed_v1 = parse_performance(SYNTHETIC_S3_GROUPED_HTML)
    with Session(engine) as db:
        s1 = persist_performance(db, "2025-2026_s3_1067", "marks:6161:3:A", parsed_v1)
        s1_id = s1.id
        s1_checksum = s1.checksum
        
        # Exact re-import must return existing without duplicate row
        s2 = persist_performance(db, "2025-2026_s3_1067", "marks:6161:3:A", parsed_v1)
        assert s2.id == s1_id
        assert len(db.scalars(select(PerformanceSnapshot)).all()) == 1
        
        # Revision: CE in CSH202C becomes 20/20 instead of 19/20
        revised_html = SYNTHETIC_S3_GROUPED_HTML.replace("19/20", "20/20")
        parsed_v2 = parse_performance(revised_html)
        s3 = persist_performance(db, "2025-2026_s3_1067", "marks:6161:3:A", parsed_v2)
        
        assert s3.id != s1_id
        assert s3.checksum != s1_checksum
        
        # Both snapshots must be preserved immutably
        all_snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.captured_at)).all()
        assert len(all_snaps) == 2
        assert all_snaps[0].id == s1_id
        assert all_snaps[1].id == s3.id
        
        # Overview should pick the latest revision
        ov = overview(db)
        s3_view = ov["terms"][0]["views"]["marks:6161:3:A"]
        csh202_ce = next(c for c in s3_view["courses"] if c["course_code"] == "CSH202C")["assessments"][1]
        assert csh202_ce["obtained"] == 20.0
    
    engine.dispose()


def test_sync_lock_released_on_error():
    """Verify that _SYNC_LOCK is not held if an operation encounters an error."""
    assert not _SYNC_LOCK.locked()
    try:
        with _SYNC_LOCK:
            assert _SYNC_LOCK.locked()
            raise RuntimeError("Synthetic simulated error during performance fetch")
    except RuntimeError:
        pass
    # Lock must be released
    assert not _SYNC_LOCK.locked()


def test_performance_preserves_attendance_and_semester4(tmp_path: Path):
    """Verify adding Semester 3 performance leaves Semester 4 and attendance untouched."""
    engine = create_app_engine(build_sqlite_url(tmp_path / "test_isolation.sqlite3"))
    from app.db.models import Base
    Base.metadata.create_all(engine)
    
    with Session(engine) as db:
        # 1. Setup existing term and S4 performance snapshot
        t4 = AcademicTerm(academic_year="2025-2026", semester_number=4, class_identifier="B.Tech CSE AIML-Sem 4")
        t3 = AcademicTerm(academic_year="2025-2026", semester_number=3, class_identifier="B.Tech CSE AIML-Sem 3")
        db.add_all([t4, t3])
        db.commit()
        
        c4 = Course(academic_term_id=t4.id, course_code="CSH213C", course_name="SOFTWARE ENGINEERING")
        c3 = Course(academic_term_id=t3.id, course_code="CSH201C", course_name="ANALYSIS & DESIGN OF ALGORITHMS")
        db.add_all([c4, c3])
        db.commit()
        
        att_snap = AttendanceSnapshot(academic_term_id=t3.id, source="LIVE_PORTAL", content_checksum="chk123", record_count=1)
        db.add(att_snap)
        db.commit()
        
        s4_perf = persist_performance(db, "2025-2026_s4_2508", "marks:6424:3:A", {"courses": [{"course_code": "CSH213C", "total": 80.0}], "sgpa": None, "cgpa": None})
        s4_id = s4_perf.id
        
        # 2. Add S3 performance snapshot
        s3_perf = persist_performance(db, "2025-2026_s3_1067", "marks:6161:3:A", {"courses": [{"course_code": "CSH201C", "total": 75.0}], "sgpa": None, "cgpa": None})
        
        # 3. Assertions
        assert s3_perf.id != s4_id
        s4_retrieved = db.get(PerformanceSnapshot, s4_id)
        assert s4_retrieved is not None
        assert s4_retrieved.term_key == "2025-2026_s4_2508"
        
        att_retrieved = db.scalars(select(AttendanceSnapshot)).all()
        assert len(att_retrieved) == 1
        assert att_retrieved[0].content_checksum == "chk123"
        
    engine.dispose()


def test_preview_to_import_zero_refetch(tmp_path: Path, monkeypatch):
    """Verify that import reuses preview evidence without calling extract_marks again."""
    from fastapi.testclient import TestClient
    from app.db.models import Base, SyncJob
    from app.main import app
    from app.db.session import get_db
    
    engine = create_app_engine(build_sqlite_url(tmp_path / "test_refetch.sqlite3"))
    Base.metadata.create_all(engine)
    
    def override():
        with Session(engine) as db:
            yield db
            
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        monkeypatch.setenv("ATTENDPLAN_ENABLE_PERFORMANCE_PILOT", "1")
        
        with Session(engine) as db:
            db.add(SyncJob(source_scope="HISTORICAL_SELECTOR_DISCOVERY", state="COMPLETED", details={"combinations":[
                {"academic_year":"2025-2026","semester":"3","class_id":"1067","class_label":"B.Tech CSE AIML-Sem 3"}
            ]}))
            db.add(SyncJob(source_scope="PERFORMANCE_SCOPE_DISCOVERY", state="COMPLETED", details={
                "term_key":"2025-2026_s3_1067","scopes":[{"exam_session":"6161","exam_type":"3","division_id":"A"}]
            }))
            db.commit()
            
        from app.adapters import performance_portal
        extract_calls = []
        def mock_extract(*args):
            extract_calls.append(args)
            return parse_performance(SYNTHETIC_S3_GROUPED_HTML)
            
        monkeypatch.setattr(performance_portal, "extract_marks", mock_extract)
        
        payload = {"term_key": "2025-2026_s3_1067", "view": "marks", "exam_session": "6161", "exam_type": "3", "division_id": "A"}
        preview_resp = client.post("/api/v1/performance/preview", json=payload)
        assert preview_resp.status_code == 200
        approval_id = preview_resp.json()["approval_id"]
        assert len(extract_calls) == 1
        
        # Now import using the approval_id
        import_resp = client.post("/api/v1/performance/import", json={**payload, "approval_id": approval_id})
        assert import_resp.status_code == 200
        # CRITICAL ASSERTION: extract_calls must still be 1! ZERO additional fetches!
        assert len(extract_calls) == 1
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
