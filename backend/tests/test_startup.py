"""Synthetic startup lifecycle tests: no real browser, credentials, or student records."""
from unittest.mock import Mock

import pytest

from app.services.startup_service import StartupCoordinator, StartupPreferences


def test_startup_disabled_without_explicit_preference(tmp_path):
    login = Mock(return_value=True)
    worker = StartupCoordinator(tmp_path / "startup.json", login, Mock(), Mock(), lambda action: action())
    assert worker.start()["state"] == "DISABLED"
    login.assert_not_called()


def test_saved_login_runs_once_and_discovery_never_imports_by_default(tmp_path):
    login = Mock(return_value=True)
    discovery = Mock(return_value={"discovered_terms":5,"performance":{"marks":"MENU_NOT_FOUND","results":"MENU_NOT_FOUND"}})
    refresh = Mock()
    path = tmp_path / "startup.json"
    unrelated = tmp_path / "settings.json"
    unrelated.write_text("SYNTHETIC_SETTINGS_SENTINEL")
    worker = StartupCoordinator(path,login,discovery,refresh,lambda action: action())
    worker.save(StartupPreferences(auto_connect=True))
    assert worker.start()["state"] == "PREVIEW_READY"
    worker.start()
    login.assert_called_once()
    discovery.assert_called_once()
    refresh.assert_not_called()
    assert unrelated.read_text() == "SYNTHETIC_SETTINGS_SENTINEL"
    assert "mobile" not in path.read_text() and "secret" not in path.read_text()


def test_startup_deduplicates_concurrent_dashboard_opens(tmp_path):
    pending = []
    worker = StartupCoordinator(tmp_path/"startup.json",Mock(return_value=True),Mock(return_value={}),Mock(),pending.append)
    worker.save(StartupPreferences(auto_connect=True))
    assert worker.start()["running"] is True
    worker.start()
    assert len(pending) == 1
    pending[0]()
    assert worker.status()["running"] is False


@pytest.mark.parametrize("failure",["login","discovery"])
def test_startup_failure_stops_without_refresh(tmp_path,failure):
    refresh = Mock()
    login = Mock(return_value=failure != "login")
    discovery = Mock(side_effect=ValueError("SYNTHETIC_ERROR"))
    worker = StartupCoordinator(tmp_path/"startup.json",login,discovery,refresh,lambda action: action())
    worker.save(StartupPreferences(auto_connect=True,refresh_approved_scopes=True))
    state = worker.start()
    assert state["state"] == "ACTION_REQUIRED" and state["running"] is False
    assert "SYNTHETIC_ERROR" not in state["message"]
    refresh.assert_not_called()


def test_refresh_requires_its_own_persisted_opt_in(tmp_path):
    refresh = Mock(return_value=2)
    worker = StartupCoordinator(tmp_path/"startup.json",Mock(return_value=True),Mock(return_value={}),refresh,lambda action: action())
    worker.save(StartupPreferences(auto_connect=True,refresh_approved_scopes=True))
    assert worker.start()["refreshed_scopes"] == 2
    refresh.assert_called_once()


def test_startup_api_rejects_refresh_before_first_pilot(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import startup_routes
    worker = StartupCoordinator(tmp_path/"startup.json",Mock(return_value=True),Mock(return_value={}),Mock(),lambda action: action())
    monkeypatch.setattr(startup_routes,"coordinator",worker)
    monkeypatch.setattr(startup_routes,"approved_scopes",lambda:([],[]))
    client = TestClient(app)
    assert client.post("/api/v1/startup/settings",json={"auto_connect":True,"refresh_approved_scopes":True}).status_code == 409
    assert client.post("/api/v1/startup/settings",json={"auto_connect":True,"refresh_approved_scopes":False}).status_code == 200
    assert client.post("/api/v1/startup/connect").json()["state"] == "PREVIEW_READY"


def test_startup_executes_current_refresh_when_opted_in(tmp_path):
    login = Mock(return_value=True)
    current_refresh = Mock(return_value={"state": "SYNC_COMPLETE", "message": "Refreshed"})
    worker = StartupCoordinator(
        tmp_path / "startup.json",
        login,
        Mock(return_value={}),
        Mock(),
        lambda action: action(),
        current_refresh=current_refresh,
    )
    worker.save(StartupPreferences(auto_connect=True, auto_refresh_current_term=True))
    res = worker.start()
    assert res["state"] == "SYNC_COMPLETE"
    login.assert_called_once()
    current_refresh.assert_called_once()


def test_refresh_current_endpoint_forces_execution(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import startup_routes

    login = Mock(return_value=True)
    current_refresh = Mock(return_value={"state": "SYNC_COMPLETE", "message": "On-demand synced"})
    worker = StartupCoordinator(
        tmp_path / "startup.json",
        login,
        Mock(return_value={}),
        Mock(),
        lambda action: action(),
        current_refresh=current_refresh,
    )
    monkeypatch.setattr(startup_routes, "coordinator", worker)
    client = TestClient(app)
    response = client.post("/api/v1/startup/refresh-current")
    assert response.status_code == 200
    assert response.json()["state"] == "SYNC_COMPLETE"
    current_refresh.assert_called_once()


def test_shutdown_endpoint_signals_clean_exit():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.post("/api/v1/startup/shutdown")
    assert response.status_code == 200
    assert response.json()["status"] == "shutting_down"
