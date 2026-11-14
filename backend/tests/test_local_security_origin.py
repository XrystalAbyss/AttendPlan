"""Test local origin security middleware and CSRF protections."""

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_allowed_loopback_origins_succeed(monkeypatch):
    """Verify that requests from approved loopback origins succeed based on environment."""
    # Production mode: only bound port (8000) allowed
    monkeypatch.delenv("ATTENDPLAN_ENV", raising=False)
    prod_origins = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
    for org in prod_origins:
        response = client.get("/api/v1/startup/status", headers={"Origin": org})
        assert response.status_code == 200, f"Origin {org} failed: {response.status_code}"

    # Unrelated loopback port is blocked in production
    res_bad_port = client.get("/api/v1/startup/status", headers={"Origin": "http://127.0.0.1:8001"})
    assert res_bad_port.status_code == 403

    # Development mode: Vite dev ports are also permitted
    monkeypatch.setenv("ATTENDPLAN_ENV", "development")
    dev_origins = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    for org in dev_origins:
        response = client.get("/api/v1/startup/status", headers={"Origin": org})
        assert response.status_code == 200, f"Dev origin {org} failed: {response.status_code}"


def test_external_origins_are_forbidden():
    """Verify that cross-origin requests from external web origins are blocked."""
    evil_origins = [
        "https://evil.com",
        "http://attacker.local",
        "https://mrei.icloudems.com.attacker.com",
        "http://192.168.1.50:8000",
        "http://10.0.0.1:8000",
    ]
    for org in evil_origins:
        # GET request with external origin
        res_get = client.get("/api/v1/terms", headers={"Origin": org})
        assert res_get.status_code == 403, f"Evil origin GET {org} was not blocked: {res_get.status_code}"
        assert "blocked" in res_get.json()["detail"].lower()

        # Mutating POST request with external origin
        res_post = client.post("/api/v1/portal/session/launch", headers={"Origin": org})
        assert res_post.status_code == 403, f"Evil origin POST {org} was not blocked: {res_post.status_code}"
        assert "blocked" in res_post.json()["detail"].lower()


def test_cross_site_fetch_site_is_forbidden():
    """Verify that browser requests marked as Sec-Fetch-Site: cross-site are rejected."""
    res = client.get("/api/v1/startup/status", headers={"Sec-Fetch-Site": "cross-site"})
    assert res.status_code == 403
    assert "cross-site access prohibited" in res.json()["detail"]


def test_external_referer_is_forbidden():
    """Verify that requests with an external Referer header are rejected."""
    res = client.get("/api/v1/startup/status", headers={"Referer": "https://malicious-forum.com/thread/123"})
    assert res.status_code == 403
    assert "referer not permitted" in res.json()["detail"]


def test_direct_local_requests_without_origin_succeed():
    """Verify that native client requests without Origin header (e.g. desktop app or curl) succeed."""
    res = client.get("/api/v1/startup/status")
    assert res.status_code == 200

