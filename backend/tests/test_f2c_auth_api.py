"""Integration tests for F2-C & Addendum authentication and settings endpoints."""

from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_totp_vault import MockSecureKeyring

SYNTHETIC_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture
def auth_client(tmp_path: Path):
    """Test client with isolated test settings and keyring."""
    settings_file = tmp_path / "settings.json"
    meta_file = tmp_path / "totp_metadata.json"
    keyring = MockSecureKeyring()

    with patch("app.api.routes._settings_service.settings_path", settings_file), \
         patch("app.api.routes._vault_service.metadata_path", meta_file), \
         patch("app.api.routes._vault_service.keyring_backend", keyring), \
         patch("app.api.routes._login_orchestrator.settings_service.settings_path", settings_file), \
         patch("app.api.routes._login_orchestrator.vault_service.metadata_path", meta_file), \
         patch("app.api.routes._login_orchestrator.vault_service.keyring_backend", keyring):
        client = TestClient(app)
        yield client, settings_file, meta_file, keyring


def test_auth_settings_lifecycle_api(auth_client):
    client, settings_file, _, _ = auth_client

    # 1. GET initial settings (all automation flags default to False - explicit opt-in required)
    r = client.get("/api/v1/auth/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["has_saved_mobile"] is False
    assert data["masked_mobile"] is None
    assert data["auto_mobile_autofill"] is False

    # 2. POST update settings with valid mobile and opt-in
    r = client.post("/api/v1/auth/settings", json={
        "mobile_number": "9876543210",
        "auto_mobile_autofill": True,
        "auto_login_continuation": False
    })
    assert r.status_code == 200
    data = r.json()
    assert data["has_saved_mobile"] is True
    assert data["masked_mobile"] == "******3210"
    assert data["auto_login_continuation"] is False

    # 3. POST update with invalid mobile format
    r = client.post("/api/v1/auth/settings", json={"mobile_number": "12345"})
    assert r.status_code == 422
    assert "Invalid mobile number" in r.json()["detail"]

    # 4. Clear mobile
    r = client.post("/api/v1/auth/settings", json={"clear_mobile": True})
    assert r.status_code == 200
    assert r.json()["has_saved_mobile"] is False


def test_totp_status_and_enrollment_api(auth_client):
    client, _, meta_file, keyring = auth_client

    # 1. GET status initially
    r = client.get("/api/v1/auth/totp/status")
    assert r.status_code == 200
    assert r.json()["is_enrolled"] is False

    # 2. Inspect raw Base32
    r = client.post("/api/v1/auth/totp/inspect", data={"provisioning_input": SYNTHETIC_SECRET})
    assert r.status_code == 200
    candidates = r.json()["candidates"]
    assert len(candidates) == 1
    assert candidates[0]["source_type"] == "MANUAL_BASE32"

    # 3. Enroll secret
    r = client.post("/api/v1/auth/totp/enroll", json={
        "secret_base32": SYNTHETIC_SECRET,
        "issuer": "iCloudEMS",
        "account_label": "student123"
    })
    assert r.status_code == 200
    assert r.json()["masked_account"] == "st***23"

    # Invariant check: API response must NOT contain the secret
    assert "secret" not in r.json()

    # 4. Status should now be enrolled
    r = client.get("/api/v1/auth/totp/status")
    assert r.status_code == 200
    assert r.json()["is_enrolled"] is True

    # 5. Delete enrollment
    r = client.delete("/api/v1/auth/totp/enrollment")
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.get("/api/v1/auth/totp/status")
    assert r.json()["is_enrolled"] is False


def test_login_orchestrator_status_api(auth_client):
    client, _, _, _ = auth_client

    r = client.get("/api/v1/auth/login/status")
    assert r.status_code == 200
    data = r.json()
    assert "state" in data
    assert "step" in data
