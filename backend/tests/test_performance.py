"""SYNTHETIC TEST FIXTURES only; no real academic records or credentials."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Base, PerformanceSnapshot, SyncJob
from app.db.session import build_sqlite_url, create_app_engine, get_db
from app.main import app
from app.services.performance_service import overview, parse_performance, persist_performance

SYNTHETIC_MARKS = """<table><tr><th>Course Code</th><th>Subject Name</th><th>Internal</th><th>External</th><th>Total</th><th>Max Marks</th><th>Credits</th><th>Grade</th></tr>
<tr><td>TEST101</td><td>Synthetic Mathematics</td><td>28</td><td>52</td><td>80</td><td>100</td><td>4</td><td>A</td></tr>
<tr><td>TEST102</td><td>Synthetic Computing</td><td>--</td><td>--</td><td>--</td><td>100</td><td>3</td><td>Pending</td></tr></table>
<p>SGPA: 8.2 CGPA: 8.1</p>"""


def test_marks_and_results_keep_missing_unknown():
    data = parse_performance(SYNTHETIC_MARKS)
    assert data["sgpa"] == 8.2 and data["cgpa"] == 8.1
    assert data["courses"][0]["percentage"] == 80
    assert data["courses"][1]["total"] is None
    assert data["courses"][1]["percentage"] is None


@pytest.mark.parametrize("html", [
    "<p>No results published</p>", SYNTHETIC_MARKS.replace("<td>80</td>", "<td>101</td>"),
    SYNTHETIC_MARKS.replace("<td>80</td>", "<td>-1</td>"),
    SYNTHETIC_MARKS.replace("<td>80</td>", "<td>NaN</td>"),
    SYNTHETIC_MARKS.replace("TEST102", "TEST101"),
    SYNTHETIC_MARKS + "<p>SGPA: 7.1</p>",
])
def test_unsupported_or_invalid_marks_quarantined(html):
    with pytest.raises(ValueError):
        parse_performance(html)


def test_result_only_does_not_invent_subject_marks():
    data = parse_performance("<p>SGPA: 7.9</p>")
    assert data["courses"] == [] and data["cgpa"] is None


def test_performance_durability_dedup_and_semester_isolation(tmp_path: Path):
    url = build_sqlite_url(tmp_path / "results.sqlite3")
    engine = create_app_engine(url)
    Base.metadata.create_all(engine)
    parsed = parse_performance(SYNTHETIC_MARKS)
    with Session(engine) as db:
        first = persist_performance(db, "synthetic_s1_class", "marks", parsed).id
        persist_performance(db, "synthetic_s2_class", "marks", parsed)
    engine.dispose()
    engine = create_app_engine(url)
    with Session(engine) as db:
        assert persist_performance(db, "synthetic_s1_class", "marks", parsed).id == first
        assert len(db.scalars(select(PerformanceSnapshot)).all()) == 2
        data = overview(db)
        assert len(data["terms"]) == 2
        assert "missing" in " ".join(data["terms"][0]["insights"])
    engine.dispose()


def test_performance_api_requires_own_exact_scope_approval(tmp_path, monkeypatch):
    engine = create_app_engine(build_sqlite_url(tmp_path / "api.sqlite3"))
    Base.metadata.create_all(engine)
    def override():
        with Session(engine) as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        monkeypatch.delenv("ATTENDPLAN_ENABLE_PERFORMANCE_PILOT", raising=False)
        assert client.get("/api/v1/performance/overview").json()["terms"] == []
        assert client.post("/api/v1/performance/import", json={"term_key":"x", "view":"marks"}).status_code == 400
        with Session(engine) as db:
            db.add(SyncJob(source_scope="HISTORICAL_SELECTOR_DISCOVERY", state="COMPLETED", details={"combinations":[
                {"academic_year":"2025-2026","semester":"4","class_id":"2140","class_label":"Synthetic Class Four"}
            ]}))
            db.commit()
        body = {"term_key":"2025-2026_s4_2140", "view":"marks"}
        # Results preview and import must be rejected with 400 (retired)
        assert client.post("/api/v1/performance/preview", json={"term_key": body["term_key"], "view": "results"}).status_code == 400
        assert client.post("/api/v1/performance/import", json={"term_key": body["term_key"], "view": "results"}).status_code == 400

        # Type-4 external exam must be rejected with 400
        type4_body = {"term_key": body["term_key"], "view": "marks", "exam_session": "SYNTHETIC-EXAM", "exam_type": "4", "division_id": "A"}
        assert client.post("/api/v1/performance/preview", json=type4_body).status_code == 400
        assert client.post("/api/v1/performance/import", json=type4_body).status_code == 400

        # Incomplete marks scope must return 400
        assert client.post("/api/v1/performance/preview", json=body).status_code == 400

        marks = {"term_key": body["term_key"], "view": "marks", "exam_session": "SYNTHETIC-EXAM", "exam_type": "3", "division_id": "A"}
        # Undiscovered scope returns 409
        assert client.post("/api/v1/performance/preview", json=marks).status_code == 409

        with Session(engine) as db:
            db.add(SyncJob(source_scope="PERFORMANCE_SCOPE_DISCOVERY", state="COMPLETED", details={
                "term_key": body["term_key"], "scopes": [{"exam_session": "SYNTHETIC-EXAM", "exam_type": "3", "division_id": "A"}]
            }))
            db.commit()

        from app.adapters import performance_portal
        monkeypatch.setattr(performance_portal, "extract_marks", lambda *args: parse_performance(SYNTHETIC_MARKS))
        mark_preview = client.post("/api/v1/performance/preview", json=marks)
        assert mark_preview.status_code == 200
        preview_data = mark_preview.json()
        assert preview_data["source_course_count"] == 2
        approval_id = preview_data["approval_id"]

        # Scope tampering returns 409
        assert client.post("/api/v1/performance/import", json={**marks, "approval_id": approval_id, "division_id": "B"}).status_code == 409

        # Import without approval_id returns 400
        assert client.post("/api/v1/performance/import", json=marks).status_code == 400

        # First import succeeds and marks the approval consumed
        assert client.post("/api/v1/performance/import", json={**marks, "approval_id": approval_id}).status_code == 200

        # Replay attempt fails with 409
        assert client.post("/api/v1/performance/import", json={**marks, "approval_id": approval_id}).status_code == 409

        with Session(engine) as db:
            snapshots = db.scalars(select(PerformanceSnapshot)).all()
            assert {s.view for s in snapshots} == {"marks:SYNTHETIC-EXAM:3:A"}

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


SYNTHETIC_GROUPED = """<table><tr><th rowspan='2'>Sr. No.</th><th rowspan='2'>Subject Code</th><th rowspan='2'>Subject Name</th><th colspan='2'>INTERNAL EXAM</th><th colspan='1'>EXTERNAL EXAM</th></tr>
<tr><th>Mid term examinations MRU</th><th>CE</th><th>End Semester Examination</th></tr>
<tr><td>1</td><td>SYN101</td><td>Synthetic Mathematics</td><td>15/30</td><td>4/5</td><td>******</td></tr>
<tr><td>2</td><td>SYN102</td><td>Synthetic Computing</td><td>27/30</td><td>-</td><td>******</td></tr></table>"""


def test_grouped_assessments_preserve_masking_and_do_not_invent_weighted_totals():
    result = parse_performance(SYNTHETIC_GROUPED)
    assert len(result["courses"]) == 2
    course = result["courses"][0]
    assert course["total"] is None and course["internal"] is None and course["percentage"] is None
    assert course["assessments"][0]["obtained"] == 15
    assert course["assessments"][0]["maximum"] == 30
    assert course["assessments"][2]["obtained"] is None
    assert course["assessments"][2]["status"] == "MASKED_BY_PORTAL"
    assert result["sgpa"] is None and result["cgpa"] is None


def test_grouped_assessments_reject_impossible_marks_and_header_mismatch():
    with pytest.raises(ValueError):
        parse_performance(SYNTHETIC_GROUPED.replace("15/30","31/30"))
    with pytest.raises(ValueError):
        parse_performance(SYNTHETIC_GROUPED.replace("colspan='2'","colspan='3'"))
