"""Startup connection, explicit refresh preferences, Service A current-term refresh, and safe background status."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from playwright.sync_api import sync_playwright
from sqlalchemy import select

from app.api import routes as auth
from app.api.performance_routes import extract_performance
from app.db.models import PerformanceSnapshot, SyncJob
from app.db.session import SessionLocal, get_default_db_path
from app.services.current_refresh_service import CurrentRefreshService
from app.services.historical_backfill_service import HistoricalBackfillService
from app.services.historical_discovery_service import HistoricalDiscoveryService
from app.services.performance_service import persist_performance
from app.services.startup_service import StartupCoordinator, StartupPreferences
from app.services.sync_job_service import _SYNC_LOCK, SyncJobService

router = APIRouter(prefix="/api/v1/startup", tags=["Startup"])


def login() -> bool:
    if not _SYNC_LOCK.acquire(blocking=False):
        raise ValueError("PORTAL_BUSY")
    try:
        if not auth._portal_session_manager.is_cdp_reachable():
            auth._portal_session_manager.launch_dedicated_browser()
        return bool(auth._login_orchestrator.orchestrate_login().success)
    finally:
        _SYNC_LOCK.release()


def discover() -> dict[str, Any]:
    with SessionLocal() as db:
        inventory = HistoricalDiscoveryService(db).discover_live(auth._portal_session_manager)
    availability = {"marks": "MENU_NOT_FOUND", "results": "MENU_NOT_FOUND"}
    if not _SYNC_LOCK.acquire(blocking=False):
        raise ValueError("PORTAL_BUSY")
    try:
        with sync_playwright() as p:
            browser, page = auth._live_portal_extractor._get_portal_page(p)
            try:
                labels = page.locator("a[href]").evaluate_all("els => els.map(e => (e.textContent || '').trim().toLowerCase())")
                for label in labels:
                    if label in {"marks", "internal marks", "subject marks", "performances"}:
                        availability["marks"] = "MENU_FOUND_UNVERIFIED_FORMAT"
                    if label in {"results", "semester results", "exam results", "examination results", "my report card"}:
                        availability["results"] = "MENU_FOUND_UNVERIFIED_FORMAT"
            finally:
                browser.close()
    finally:
        _SYNC_LOCK.release()
    return {"discovered_terms": len(inventory.terms), "performance": availability}


def approved_scopes() -> tuple[list[str], list[tuple[str, str]]]:
    with SessionLocal() as db:
        jobs = db.scalars(select(SyncJob).where(
            SyncJob.source_scope == "HISTORICAL_MULTI_SEMESTER_BACKFILL", SyncJob.state == "COMPLETED",
        )).all()
        # Successful first-pilot jobs establish only their exact semester summary scope.
        attendance = sorted({key for job in jobs for key in (job.details or {}).get("selected_term_keys", [])})
        performance = sorted({(s.term_key, s.view) for s in db.scalars(select(PerformanceSnapshot).where(
            PerformanceSnapshot.provenance == "LIVE_PORTAL"
        )).all()})
    return attendance, performance


def current_refresh() -> dict[str, Any]:
    """Execute Service A: Current Semester Live Refresh."""
    with SessionLocal() as db:
        service = CurrentRefreshService(db, auth._live_portal_extractor)
        res = service.refresh_current_semester()
        return {
            "state": res.state,
            "message": res.message,
            "term_key": res.term_key,
            "academic_year": res.academic_year,
            "semester": res.semester,
            "class_identifier": res.class_identifier,
            "summary_outcome": res.summary_outcome,
            "daywise_outcome": res.daywise_outcome,
            "month_label": res.month_label,
            "last_sync_time": res.last_sync_time,
            "diagnostic": res.diagnostic,
        }


def refresh() -> int:
    attendance, performance = approved_scopes()
    count = 0
    with SessionLocal() as db:
        inventory = HistoricalDiscoveryService(db).get_persisted_inventory()
        terms = {t.term_key: t for t in inventory.terms if t.details.get("selector_verified")}
        for key in attendance:
            if key not in terms:
                raise ValueError("APPROVED_TERM_UNAVAILABLE")
            job = SyncJobService(db).create_job(source_scope="HISTORICAL_MULTI_SEMESTER_BACKFILL",
                                              details={"selected_term_keys": [key], "automatic_refresh": True})
            result = HistoricalBackfillService(db, auth._live_portal_extractor).run_historical_backfill(job.id, [key])
            if result.state != "COMPLETED":
                raise ValueError("APPROVED_REFRESH_STOPPED")
            count += 1
        for key, view in performance:
            if key not in terms or not _SYNC_LOCK.acquire(blocking=False):
                raise ValueError("PERFORMANCE_REFRESH_UNAVAILABLE")
            try:
                if view.startswith("marks:"):
                    from app.adapters.performance_portal import extract_marks
                    parts = view.split(":")
                    parsed = extract_marks(terms[key], parts[1], parts[2], parts[3] if len(parts) > 3 else None)
                else:
                    parsed = extract_performance(terms[key], view)
                persist_performance(db, key, view, parsed)
                count += 1
            finally:
                _SYNC_LOCK.release()
    return count


coordinator = StartupCoordinator(
    Path(os.environ.get("ATTENDPLAN_STARTUP_SETTINGS_PATH", str(get_default_db_path().parent / "startup.json"))),
    login=login,
    discover=discover,
    refresh=refresh,
    current_refresh=current_refresh,
)


@router.get("/settings")
def settings() -> dict[str, Any]:
    attendance, performance = approved_scopes()
    return {**coordinator.preferences().model_dump(), "approved_scope_count": len(attendance) + len(performance)}


@router.post("/settings")
def update_settings(value: StartupPreferences) -> dict[str, Any]:
    attendance, performance = approved_scopes()
    if value.refresh_approved_scopes and not (attendance or performance):
        raise HTTPException(409, "Approve and complete the first one-semester pilot before enabling automatic refresh.")
    coordinator.save(value)
    return settings()


@router.post("/connect")
def connect() -> dict[str, Any]:
    return coordinator.start()


@router.post("/refresh-current")
def refresh_current_endpoint() -> dict[str, Any]:
    """Dedicated endpoint for manual on-demand refresh of the current semester."""
    return coordinator.start(force=True)


@router.get("/status")
def status() -> dict[str, Any]:
    return coordinator.status()
