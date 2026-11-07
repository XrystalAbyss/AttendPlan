"""Tests for historical multi-semester API endpoints (Milestone F2-E)."""

from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db
from app.main import app
from app.services.historical_backfill_service import HistoricalBackfillService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)


    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, session_factory
    finally:
        app.dependency_overrides.clear()


def test_historical_terms_empty_db(client_with_db):
    client, _ = client_with_db
    response = client.get("/api/v1/historical/terms")
    assert response.status_code == 200
    data = response.json()
    assert "terms" in data
    assert "discovered_years" in data
    assert data["total_terms_count"] == 0


def test_historical_discover_with_html_payload(client_with_db):
    client, _ = client_with_db
    html_content = (FIXTURES_DIR / "synthetic_historical_terms_discovery.html").read_text(encoding="utf-8")

    response = client.post("/api/v1/historical/discover", json={"html_content": html_content})
    assert response.status_code == 200
    data = response.json()
    assert data["total_terms_count"] > 0
    assert "2026-2027" in data["discovered_years"]
    assert data["total_terms_count"] == 1
    assert data["terms"][0]["status"] == "NOT_CHECKED"
    assert data["provenance"] == "USER_SUPPLIED_HTML"


def test_historical_preview_endpoint(client_with_db):
    client, session_factory = client_with_db
    # First seed a term
    db = session_factory()
    s4_sub_html = (FIXTURES_DIR / "synthetic_semester4_subjectwise.html").read_text(encoding="utf-8")
    backfill = HistoricalBackfillService(db)
    backfill.import_term_offline(
        academic_year="2025-2026",
        semester=4,

        class_id="2140",
        subject_html=s4_sub_html,
    )
    db.close()

    response = client.post("/api/v1/historical/preview", json={})
    assert response.status_code == 200
    data = response.json()
    assert "selected_terms" in data
    assert "total_estimated_requests" in data
    assert data["requires_user_approval"] is True


def test_term_coverage_endpoint(client_with_db):
    client, session_factory = client_with_db
    db = session_factory()
    s4_sub_html = (FIXTURES_DIR / "synthetic_semester4_subjectwise.html").read_text(encoding="utf-8")
    s4_day_html = (FIXTURES_DIR / "synthetic_semester4_daywise.html").read_text(encoding="utf-8")
    backfill = HistoricalBackfillService(db)
    res = backfill.import_term_offline(
        academic_year="2025-2026",
        semester=4,
        class_id="2140",
        subject_html=s4_sub_html,
        daywise_html_list=[s4_day_html],
    )
    term_id = res["term_id"]
    db.close()

    response = client.get(f"/api/v1/terms/{term_id}/coverage")
    assert response.status_code == 200
    cov = response.json()
    assert cov["term_id"] == term_id
    assert cov["academic_year"] == "2025-2026"
    assert cov["semester_number"] == 4
    assert cov["has_subject_summary"] is True
    assert cov["unique_instructional_dates"] > 0
    assert cov["unique_instructional_periods"] > 0


def test_historical_overview_endpoint(client_with_db):
    client, session_factory = client_with_db
    db = session_factory()
    s4_sub_html = (FIXTURES_DIR / "synthetic_semester4_subjectwise.html").read_text(encoding="utf-8")
    backfill = HistoricalBackfillService(db)
    backfill.import_term_offline(
        academic_year="2025-2026",
        semester=4,
        class_id="2140",
        subject_html=s4_sub_html,
    )
    db.close()

    response = client.get("/api/v1/historical/overview")
    assert response.status_code == 200
    data = response.json()
    assert "semesters" in data
    assert len(data["semesters"]) >= 1
    assert data["semesters"][0]["semester_number"] == 4


def test_synthetic_seed_disabled_by_default(client_with_db, monkeypatch):
    monkeypatch.delenv("ATTENDPLAN_ALLOW_SYNTHETIC_IMPORT", raising=False)
    client, factory = client_with_db
    assert client.post("/api/v1/demo/seed").status_code == 403
    with factory() as db:
        from app.db.models import AcademicTerm
        from sqlalchemy import select
        assert db.scalars(select(AcademicTerm)).all() == []


def test_historical_pilot_disabled_by_default(client_with_db, monkeypatch):
    monkeypatch.delenv("ATTENDPLAN_ENABLE_HISTORICAL_PILOT", raising=False)
    client, _ = client_with_db
    response = client.post("/api/v1/historical/import", json={"selected_term_keys": ["unverified_s4_1"]})
    assert response.status_code == 409


def test_historical_pilot_rejects_bulk(client_with_db, monkeypatch):
    monkeypatch.setenv("ATTENDPLAN_ENABLE_HISTORICAL_PILOT", "1")
    client, _ = client_with_db
    response = client.post("/api/v1/historical/import", json={"selected_term_keys": ["a", "b"]})
    assert response.status_code == 400


def test_historical_import_requires_fresh_matching_preview(client_with_db, monkeypatch):
    from types import SimpleNamespace
    from app.api import routes
    from app.db.models import SyncJob, AttendanceSnapshot
    from app.adapters.html_parser import ERPAttendanceParser
    from sqlalchemy import select

    client, factory = client_with_db
    html = (FIXTURES_DIR / "synthetic_semester4_subjectwise.html").read_text(encoding="utf-8")
    with factory() as db:
        db.add(SyncJob(source_scope="HISTORICAL_SELECTOR_DISCOVERY",state="COMPLETED",details={"combinations":[
            {"academic_year":"2025-2026","semester":"4","class_id":"2140","class_label":"B.Tech CSE AIML-Sem 4"}
        ]}))
        db.commit()
    monkeypatch.setenv("ATTENDPLAN_ENABLE_HISTORICAL_PILOT","1")
    calls = []
    def extract(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(snapshot=ERPAttendanceParser().parse_html(html),academic_year="2025-2026",semester=4,
            class_identifier="B.Tech CSE AIML-Sem 4",validation=SimpleNamespace(is_valid=True,quarantined=False,percentage_deviations=[]))
    monkeypatch.setattr(routes._live_portal_extractor,"extract_live_subject_wise",extract)
    monkeypatch.setattr("app.services.historical_backfill_service.time.sleep",lambda seconds: None)
    body = {"selected_term_keys":["2025-2026_s4_2140"]}
    assert client.post("/api/v1/historical/import",json=body).status_code == 409
    preview = client.post("/api/v1/historical/preview",json=body).json()
    assert preview["total_estimated_requests"] == 1
    approved = {**body,"approval_id":preview["approval_id"]}
    assert client.post("/api/v1/historical/import",json={**approved,"import_daywise":True}).status_code == 400
    response = client.post("/api/v1/historical/import",json=approved)
    assert response.status_code == 200
    assert response.json()["state"] == "COMPLETED"
    assert len(calls) == 2
    assert client.post("/api/v1/historical/import",json=approved).status_code == 409
    with factory() as db:
        assert len(db.scalars(select(AttendanceSnapshot)).all()) == 1
