"""Background connection lifecycle and startup synchronization coordinator.

Saved attendance records are never cleared on connection or sync failure.
Coordinates Service A (Current Semester Live Refresh) on startup and Service B (Historical Archive).
"""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class StartupPreferences(BaseModel):
    auto_connect: bool = False
    auto_refresh_current_term: bool = True
    refresh_approved_scopes: bool = False
    last_sync_time: Optional[str] = None


class StartupCoordinator:
    """Coordinates application startup, session readiness, and current-term refresh."""

    def __init__(
        self,
        path: Path,
        login: Callable[[], bool],
        discover: Callable[[], dict[str, Any]],
        refresh: Callable[[], int],
        dispatch: Callable[[Callable[[], None]], None] | None = None,
        current_refresh: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.path = path
        self.login = login
        self.discover = discover
        self.refresh = refresh
        self.current_refresh = current_refresh
        self.dispatch = dispatch or (lambda action: threading.Thread(target=action, daemon=True).start())
        self.lock = threading.Lock()
        self.busy = False
        self.last_attempt = float("-inf")
        self.state: dict[str, Any] = {
            "state": "IDLE",
            "message": "Saved data is available locally.",
            "running": False,
            "refreshed_scopes": 0,
            "last_sync_time": None,
        }

    def preferences(self) -> StartupPreferences:
        try:
            return StartupPreferences.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return StartupPreferences()

    def save(self, value: StartupPreferences) -> None:
        # Separate non-secret file; never rewrites mobile settings or the vault.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(value.model_dump_json(indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def status(self) -> dict[str, Any]:
        with self.lock:
            prefs = self.preferences()
            return {
                **self.state,
                "running": self.busy,
                "last_sync_time": self.state.get("last_sync_time") or prefs.last_sync_time,
            }

    def start(self, force: bool = False) -> dict[str, Any]:
        preferences = self.preferences()
        with self.lock:
            if not force and not preferences.auto_connect:
                return {**self.state, "state": "DISABLED", "running": False, "last_sync_time": preferences.last_sync_time}
            # Multiple tabs and React StrictMode must not duplicate active executions.
            if self.busy:
                return {**self.state, "running": True, "last_sync_time": preferences.last_sync_time}
            if not force and (time.monotonic() - self.last_attempt < 30):
                return {**self.state, "running": False, "last_sync_time": preferences.last_sync_time}
            self.busy = True
            self.last_attempt = time.monotonic()
            self.state = {
                "state": "CHECKING_PORTAL_SESSION",
                "message": "Checking university portal session...",
                "running": True,
                "refreshed_scopes": 0,
                "last_sync_time": preferences.last_sync_time,
            }
        self.dispatch(lambda: self._run(preferences, force))
        return self.status()

    def _set(self, **values: Any) -> None:
        with self.lock:
            self.state.update(values)

    def _run(self, preferences: StartupPreferences, force: bool = False) -> None:
        try:
            # 1. Check or establish authorized session
            if not self.login():
                self._set(
                    state="ACTION_REQUIRED",
                    message="Portal login required in browser. Showing saved attendance.",
                )
                return

            # 2. Execute Service A (Current Semester Live Refresh)
            if (preferences.auto_refresh_current_term or force) and self.current_refresh:
                self._set(
                    state="REFRESHING_CURRENT_SUMMARY",
                    message="Refreshing current semester attendance...",
                )
                refresh_result = self.current_refresh()
                self._set(**refresh_result)
                if refresh_result.get("last_sync_time"):
                    preferences.last_sync_time = refresh_result["last_sync_time"]
                    try:
                        self.save(preferences)
                    except Exception:
                        pass
            elif not self.current_refresh:
                # Fallback discovery path if current_refresh not configured (e.g. basic tests)
                self._set(state="DISCOVERING", message="Checking available semesters; saved records remain visible.")
                discovery = self.discover()
                self._set(**discovery)
                if preferences.refresh_approved_scopes:
                    self._set(state="REFRESHING", message="Refreshing approved semester scopes.")
                    count = self.refresh()
                    self._set(refreshed_scopes=count)
                self._set(state="PREVIEW_READY", message="Connection checked. Newly discovered scopes require a preview and approval before import.")

            # 3. Optional Service B (Historical recovery if opted in)
            if preferences.refresh_approved_scopes and self.current_refresh:
                try:
                    count = self.refresh()
                    self._set(refreshed_scopes=count)
                except Exception as e:
                    logger.warning("Historical approved scope refresh stopped: %s", e)

        except Exception as e:
            logger.exception("Startup synchronization stopped: %s", e)
            self._set(
                state="ACTION_REQUIRED",
                message="Connection or portal validation stopped. Saved records are unchanged.",
            )
        finally:
            with self.lock:
                self.busy = False
