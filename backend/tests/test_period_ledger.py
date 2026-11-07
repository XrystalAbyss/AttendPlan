"""Synthetic ledger tests: semester isolation, unknown statuses and unmapped subjects."""
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.api import routes

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import AcademicTerm, AttendanceObservationBatch, AttendancePeriodObservation, Base, Course
from app.db.session import build_sqlite_url, create_app_engine, get_db
from app.main import app


def test_period_ledger_preserves_mapping_status_and_term_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_app_engine(build_sqlite_url(tmp_path / "synthetic-ledger.sqlite3"))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for key in ["one", "two"]:
            db.add(AcademicTerm(id=key, academic_year="2026-2027", semester_number=1))
            db.flush()
            db.add(Course(id="c"+key, academic_term_id=key, course_code="TEST101", course_name="Synthetic Subject"))
            db.add(AttendanceObservationBatch(id="b"+key, academic_term_id=key, coverage_start_date=date(2026,9,1), coverage_end_date=date(2026,10,31), content_checksum=key))
            db.flush()
            db.add(AttendancePeriodObservation(id="p"+key, observation_batch_id="b"+key, academic_term_id=key, attendance_date=date(2026,9,3), course_id="c"+key, status="PRESENT", attended_period_count=2, delivered_period_count=2))
        db.add(AttendancePeriodObservation(id="unknown", observation_batch_id="bone", academic_term_id="one", attendance_date=date(2026,10,3), source_course_label="Unmapped synthetic", status="UNKNOWN", attended_period_count=0, delivered_period_count=0))
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/terms/one/attendance/periods")
                assert response.status_code == 200
                rows = response.json()["periods"]
                assert len(rows) == 2
                assert rows[0]["course_code"] == "TEST101" and rows[0]["attended"] == 2
                assert rows[1]["course_code"] is None and rows[1]["status"] == "UNKNOWN"
                assert client.get("/api/v1/terms/missing/attendance/periods").status_code == 404
                assert client.post("/api/v1/terms/one/attendance/month-preview?month=2026-13").status_code == 422
                scope = SimpleNamespace(details={"selector_verified": True}, academic_year="2026-2027", semester_number=1, class_identifier="synthetic-class")
                monkeypatch.setattr(routes.HistoricalDiscoveryService, "get_persisted_inventory", lambda self: SimpleNamespace(terms=[scope]))
                observation = SimpleNamespace(attendance_date=date(2026, 9, 3), slot_start_time=None, slot_end_time=None,
                    source_period_identifier="1", source_course_label="Synthetic Subject", status=SimpleNamespace(value="PRESENT"), attended_period_count=1, delivered_period_count=1)
                monkeypatch.setattr(routes._live_portal_extractor, "extract_live_day_wise", lambda **kwargs: SimpleNamespace(batch=SimpleNamespace(observations=[observation])))
                preview = client.post("/api/v1/terms/one/attendance/month-preview?month=2026-09")
                assert preview.status_code == 200
                assert preview.json()["persisted"] is False
                assert preview.json()["periods"][0]["course_code"] == "TEST101"
                assert len(client.get("/api/v1/terms/one/attendance/periods").json()["periods"]) == 2
                assert client.post("/api/v1/terms/one/attendance/month-preview?month=2027-09").status_code == 409
                assert client.post("/api/v1/terms/one/attendance/month-preview?month=2024-09").status_code == 422
        finally:
            app.dependency_overrides.clear()
    engine.dispose()
