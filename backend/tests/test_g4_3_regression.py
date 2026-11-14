"""Regression test suite for Phase G.4.3: Local Launcher & First-Run State Recovery.

Covers:
- /health endpoint returns mode, runtime, and database_path without leaking secrets.
- Development backend allows development frontend origins (127.0.0.1:5173, localhost:5173) on operational endpoints.
- Production backend blocks non-8000 origins on operational endpoints.
- Launch scripts (Launch-AttendPlan.cmd, Launch-AttendPlan.ps1) configure ATTENDPLAN_ENV=development.
- Saved mobile configuration in SettingsService surfaces has_saved_mobile and masked_mobile.
"""

from pathlib import Path
from starlette.testclient import TestClient

from app.main import app
from app.services.settings_service import SettingsService

client = TestClient(app)


def test_health_endpoint_contract():
    """Verify /health exposes mode, runtime, database_status and no personal paths or sensitive tokens."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "mode" in data
    assert data["mode"] in ("development", "production")
    assert "runtime" in data
    assert data["runtime"] in ("source", "frozen")
    assert data.get("database_status") == "connected"
    # Ensure personal filesystem paths and secrets are NOT exposed
    assert "database_path" not in data
    assert "instance_token" not in data
    assert "cookie" not in data
    assert "password" not in data

    # Verify diagnostic status endpoint preserves database_path safely
    res_status = client.get("/api/v1/startup/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "database_path" in status_data


def test_development_mode_allows_dev_origins_on_terms(monkeypatch):
    """Verify development mode enables Vite dev origins (5173) on /api/v1/terms."""
    from app.db.session import init_db

    # Ensure tables exist in any test sandbox
    init_db()

    monkeypatch.setenv("ATTENDPLAN_ENV", "development")
    dev_origins = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    for origin in dev_origins:
        res = client.get("/api/v1/terms", headers={"Origin": origin})
        assert res.status_code == 200, f"Origin {origin} failed with {res.status_code}: {res.text}"
        assert res.headers.get("access-control-allow-origin") == origin


def test_production_mode_blocks_dev_origins_on_terms(monkeypatch):
    """Verify production mode rejects Vite dev origins (5173) on /api/v1/terms with 403."""
    monkeypatch.delenv("ATTENDPLAN_ENV", raising=False)
    res = client.get("/api/v1/terms", headers={"Origin": "http://127.0.0.1:5173"})
    assert res.status_code == 403
    assert "blocked" in res.json()["detail"].lower()


def test_launch_scripts_configure_development_env():
    """Verify Launch-AttendPlan.cmd and Launch-AttendPlan.ps1 contain ATTENDPLAN_ENV=development."""
    repo_root = Path(__file__).resolve().parent.parent.parent

    cmd_script = repo_root / "Launch-AttendPlan.cmd"
    assert cmd_script.exists(), "Launch-AttendPlan.cmd missing"
    cmd_text = cmd_script.read_text(encoding="utf-8")
    assert "ATTENDPLAN_ENV=development" in cmd_text

    ps1_script = repo_root / "scripts" / "Launch-AttendPlan.ps1"
    assert ps1_script.exists(), "Launch-AttendPlan.ps1 missing"
    ps1_text = ps1_script.read_text(encoding="utf-8")
    assert '$env:ATTENDPLAN_ENV = "development"' in ps1_text
    assert 'EnvironmentVariables["ATTENDPLAN_ENV"] = "development"' in ps1_text


def test_settings_service_surfaces_saved_mobile_safely(tmp_path):
    """Verify SettingsService returns has_saved_mobile and masked_mobile when configured."""
    from app.services.settings_service import SettingsUpdateRequest
    settings_file = tmp_path / "settings.json"
    service = SettingsService(settings_path=settings_file)

    # Initially empty
    summary = service.get_public_settings()
    assert summary.has_saved_mobile is False
    assert summary.masked_mobile is None

    # Save mobile number
    service.update_settings(SettingsUpdateRequest(mobile_number="9876543210"))
    summary2 = service.get_public_settings()
    assert summary2.has_saved_mobile is True
    assert summary2.masked_mobile == "******3210"

    # API endpoint also preserves
    res = client.get("/api/v1/auth/settings")
    assert res.status_code == 200
    assert "has_saved_mobile" in res.json()
    assert "masked_mobile" in res.json()
