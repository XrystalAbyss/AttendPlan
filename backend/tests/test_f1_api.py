"""Integration tests for AttendPlan F1 API endpoints."""

from __future__ import annotations

import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.session import build_sqlite_url, create_app_engine, get_db
from app.main import app

# Create a temporary SQLite file for integration tests so connections share state
_temp_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
_temp_path = Path(_temp_file.name)
_temp_file.close()

test_engine = create_app_engine(build_sqlite_url(_temp_path))
Base.metadata.create_all(bind=test_engine)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def cleanup_temp_db():
    yield
    test_engine.dispose()
    if _temp_path.exists():
        try:
            _temp_path.unlink()
        except Exception:
            pass


class TestF1ApiEndpoints:
    def test_fresh_db_is_empty_and_no_silent_seeding(self) -> None:
        """A newly installed application must start with an empty real database.
        GET /api/v1/terms must return [] and GET /api/v1/attendance/sample must never write to DB."""
        # 1. Terms must be empty initially
        response = client.get("/api/v1/terms")
        assert response.status_code == 200
        terms = response.json()
        assert len(terms) == 0

        # 2. Sample endpoint must return sample data in-memory without inserting into DB
        sample_resp = client.get("/api/v1/attendance/sample")
        assert sample_resp.status_code == 200
        sample_data = sample_resp.json()
        assert len(sample_data["courses"]) == 15

        # 3. Verify DB is STILL empty after GET /sample
        response_after = client.get("/api/v1/terms")
        assert response_after.status_code == 200
        assert len(response_after.json()) == 0

    def test_explicit_demo_seeding(self) -> None:
        """Explicit POST /api/v1/demo/seed populates the database."""
        seed_resp = client.post("/api/v1/demo/seed")
        assert seed_resp.status_code == 200
        seed_data = seed_resp.json()
        assert seed_data["outcome"] == "SUCCESS"

        # Now GET /api/v1/terms has the seeded term
        response = client.get("/api/v1/terms")
        assert response.status_code == 200
        terms = response.json()
        assert len(terms) >= 1
        term = terms[0]
        assert term["academic_year"] == "2026-2027"
        assert term["semester_number"] == 5
        assert term["total_courses"] == 15
        assert term["total_attended"] == 185
        assert term["total_delivered"] == 213
        assert term["overall_percentage"] == 86.85
        assert term["overall_status"] == "SAFE"

    def test_unknown_term_returns_404(self) -> None:
        """Endpoints with invalid term_id must return 404."""
        non_existent = "non_existent_term_999"
        assert client.get(f"/api/v1/terms/{non_existent}/attendance").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/snapshots").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/analytics/summary").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/analytics/monthly").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/analytics/weekday").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/analytics/daily").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/analytics/subjects").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/analytics/calendar").status_code == 404
        assert client.get(f"/api/v1/terms/{non_existent}/reconciliation").status_code == 404

    def test_get_term_attendance_and_snapshots(self) -> None:
        """GET /api/v1/terms/{term_id}/attendance returns course roster and summary."""
        # 1. Get term_id
        terms = client.get("/api/v1/terms").json()
        term_id = terms[0]["id"]

        # 2. Get term attendance
        att_resp = client.get(f"/api/v1/terms/{term_id}/attendance")
        assert att_resp.status_code == 200
        att_data = att_resp.json()
        assert att_data["term_id"] == term_id
        assert len(att_data["courses"]) == 15
        assert att_data["summary"]["total_courses"] == 15
        assert att_data["summary"]["total_attended"] == 185

        # 3. Get term snapshots
        snaps_resp = client.get(f"/api/v1/terms/{term_id}/snapshots")
        assert snaps_resp.status_code == 200
        snaps = snaps_resp.json()
        assert len(snaps) >= 1
        assert "content_checksum" in snaps[0]
        assert snaps[0]["record_count"] == 15

    def test_term_analytics_endpoints(self) -> None:
        """Verify summary, monthly, weekday, daily, and subject analytics endpoints."""
        terms = client.get("/api/v1/terms").json()
        term_id = terms[0]["id"]

        # 1. Summary analytics
        summary_resp = client.get(f"/api/v1/terms/{term_id}/analytics/summary")
        assert summary_resp.status_code == 200
        summary_data = summary_resp.json()
        assert summary_data["total_courses"] == 15
        assert summary_data["overall_percentage"] == 86.85
        assert summary_data["overall_status"] == "SAFE"

        # 2. Monthly analytics (initially empty before day-wise upload)
        monthly_resp = client.get(f"/api/v1/terms/{term_id}/analytics/monthly")
        assert monthly_resp.status_code == 200
        monthly_data = monthly_resp.json()
        assert isinstance(monthly_data, list)

        # 3. Weekday analytics
        weekday_resp = client.get(f"/api/v1/terms/{term_id}/analytics/weekday")
        assert weekday_resp.status_code == 200
        weekday_data = weekday_resp.json()
        assert len(weekday_data) == 7

        # 4. Daily analytics
        daily_resp = client.get(f"/api/v1/terms/{term_id}/analytics/daily")
        assert daily_resp.status_code == 200
        assert isinstance(daily_resp.json(), list)

        # 5. Subject analytics
        subj_resp = client.get(f"/api/v1/terms/{term_id}/analytics/subjects")
        assert subj_resp.status_code == 200
        subj_data = subj_resp.json()
        assert len(subj_data["subjects"]) == 15
        assert "rankings" in subj_data
        assert "by_absolute_missed" in subj_data["rankings"]
        assert "by_missed_rate" in subj_data["rankings"]
        assert "by_total_delivered" in subj_data["rankings"]

    def test_academic_history_endpoint(self) -> None:
        """GET /api/v1/analytics/academic-history returns multi-semester summary."""
        resp = client.get("/api/v1/analytics/academic-history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["semesters"]) >= 1
        sem = data["semesters"][0]
        assert sem["academic_year"] == "2026-2027"
        assert sem["semester_number"] == 5
        assert sem["percentage"] == 86.85
        assert sem["status"] == "SAFE"

    def test_reconciliation_endpoint(self) -> None:
        """GET /api/v1/terms/{term_id}/reconciliation returns provenance and status."""
        terms = client.get("/api/v1/terms").json()
        term_id = terms[0]["id"]

        resp = client.get(f"/api/v1/terms/{term_id}/reconciliation")
        assert resp.status_code == 200
        rec_data = resp.json()
        assert rec_data["term_id"] == term_id
        assert rec_data["subject_wise_available"] is True
        assert rec_data["subject_wise_total_attended"] == 185
        assert rec_data["subject_wise_total_delivered"] == 213
        # Initially day-wise has not been imported for this term
        assert rec_data["day_wise_available"] is False
        assert rec_data["reconciliation_status"] == "PARTIAL_COVERAGE"

    def test_html_import_and_ingestion_logging(self) -> None:
        """POST /api/v1/attendance/imports/html accepts HTML and logs event."""
        fixture_path = (
            Path(__file__).parent / "fixtures" / "sample_attendance.html"
        )
        with open(fixture_path, "rb") as f:
            file_bytes = f.read()

        response = client.post(
            "/api/v1/attendance/imports/html",
            files={"file": ("sample_attendance.html", file_bytes, "text/html")},
            data={
                "source_type": "SUBJECT_WISE",
                "academic_year": "2026-2027",
                "semester_number": "5",
                "class_identifier": "B.Tech CSE AIML-Sem 5",
            },
        )
        assert response.status_code == 200
        import_res = response.json()
        # Check outcome
        assert import_res["outcome"] in ["SUCCESS", "IMPORTED", "DUPLICATE_SKIPPED"]
        assert import_res["details"]["record_count"] == 15

        # Check ingestion log
        ing_resp = client.get("/api/v1/attendance/ingestions?limit=10&offset=0")
        assert ing_resp.status_code == 200
        logs = ing_resp.json()
        assert len(logs) >= 1
        assert logs[0]["source"] in ["AUTO_SEED_SAMPLE", "DEMO_FIXTURE_SEED", "SUBJECT_WISE_HTML_UPLOAD", "USER_HTML_IMPORT"]
