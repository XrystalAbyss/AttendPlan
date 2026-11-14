import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.session import build_sqlite_url, create_app_engine, get_db
from app.main import app
from app.api import routes

# Temporary SQLite file for F2-B test suite
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
    app.dependency_overrides.pop(get_db, None)
    test_engine.dispose()
    if _temp_path.exists():
        try:
            _temp_path.unlink()
        except Exception:
            pass



def test_get_historical_sync_plan_endpoint() -> None:
    """GET /api/v1/portal/sync/historical-plan returns structured terms and request estimates."""
    resp = client.get("/api/v1/portal/sync/historical-plan")
    assert resp.status_code == 200
    data = resp.json()
    assert "discovered_academic_years" in data
    assert "terms" in data
    assert len(data["terms"]) >= 1
    assert data["total_estimated_requests"] >= 1
    assert "pacing_guidance" in data


def test_sync_job_not_found() -> None:
    """GET /api/v1/portal/sync/jobs/{job_id} returns 404 for unknown job ID."""
    resp = client.get("/api/v1/portal/sync/jobs/non-existent-uuid")
    assert resp.status_code == 404


def test_sync_subject_wise_browser_not_connected() -> None:
    """POST /api/v1/portal/sync/subject-wise returns 503 when browser is disconnected."""
    routes._live_portal_extractor.session_manager.cdp_port = 19222
    resp = client.post("/api/v1/portal/sync/subject-wise", json={"persist": False})
    # Reset port back
    routes._live_portal_extractor.session_manager.cdp_port = 9222
    assert resp.status_code in [401, 503]


def test_sync_day_wise_browser_not_connected() -> None:
    """POST /api/v1/portal/sync/day-wise returns 503 when browser is disconnected."""
    routes._live_portal_extractor.session_manager.cdp_port = 19222
    resp = client.post("/api/v1/portal/sync/day-wise", json={"persist": False})
    # Reset port back
    routes._live_portal_extractor.session_manager.cdp_port = 9222
    assert resp.status_code in [401, 503]
