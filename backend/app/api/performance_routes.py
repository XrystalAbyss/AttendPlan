"""Read-only performance overview and separately approved one-term capture."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit

from fastapi import APIRouter, Depends, HTTPException
from playwright.sync_api import sync_playwright
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import PortalSafetyError, canonical_html, check_page, verify_filters
from app.db.models import SyncJob
from app.db.session import get_db
from app.services.historical_discovery_service import HistoricalDiscoveryService
from app.services.performance_service import overview, parse_performance, persist_performance
from app.services.sync_job_service import _SYNC_LOCK

router = APIRouter(prefix="/api/v1/performance", tags=["Performance"])


class PerformanceRequest(BaseModel):
    term_key: str
    view: Literal["marks", "results"]
    approval_id: str | None = None
    exam_session: str | None = None
    exam_type: str | None = None
    division_id: str | None = None


def verified_term(db: Session, key: str) -> Any:
    inventory = HistoricalDiscoveryService(db).get_persisted_inventory()
    term = next((t for t in inventory.terms if t.term_key == key and t.details.get("selector_verified")), None)
    if term is None:
        raise HTTPException(409, "Run verified term discovery first.")
    return term


@router.get("/overview")
def performance_overview(db: Session = Depends(get_db)) -> dict[str, Any]:
    data = overview(db)
    data["discovered_terms"] = HistoricalDiscoveryService(db).get_discovered_term_labels()
    data["live_capture_enabled"] = True
    return data


@router.get("/official-results")
def performance_official_results(db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.services.results_service import overview_official_results
    return overview_official_results(db)


@router.post("/discover-scopes")
def performance_scopes(payload: PerformanceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.adapters.performance_portal import discover_scopes
    term = verified_term(db, payload.term_key)
    if not _SYNC_LOCK.acquire(blocking=False):
        raise HTTPException(409, "Another portal job is active.")
    try:
        scopes = discover_scopes(term)
        job = SyncJob(source_scope="PERFORMANCE_SCOPE_DISCOVERY", state="COMPLETED",
                      details={"term_key": term.term_key, "scopes": scopes})
        db.add(job)
        db.commit()
        return {"term_key": term.term_key, "scopes": scopes}
    except Exception as error:
        logging.getLogger(__name__).warning("Performance scope discovery stopped: %s", type(error).__name__)
        db.rollback()
        raise HTTPException(409, "Performance exam filters could not be verified. No marks were imported.") from None
    finally:
        _SYNC_LOCK.release()


def approval_scope(payload: PerformanceRequest) -> dict[str, Any]:
    if payload.view == "results":
        raise HTTPException(
            400,
            "Official semester results view has been retired by COE / University and is unavailable for live import.",
        )
    if payload.exam_type == "4":
        raise HTTPException(
            400,
            "External examination scope (type 4) is rejected. Only continuous evaluation internal marks (type 3) are supported.",
        )
    scope = {"term_key": payload.term_key, "view": payload.view}
    if payload.exam_session is not None or payload.exam_type is not None:
        if not payload.exam_session or not payload.exam_type:
            raise HTTPException(400, "Both exam session and exam type are required.")
        scope.update(exam_session=payload.exam_session, exam_type=payload.exam_type)
    if payload.division_id is not None:
        scope["division_id"] = payload.division_id
    return scope


@router.post("/preview")
def performance_preview(payload: PerformanceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.view == "results":
        raise HTTPException(
            400,
            "Official semester results view has been retired by COE / University and is unavailable for live import.",
        )
    if payload.exam_type == "4":
        raise HTTPException(
            400,
            "External examination scope (type 4) is rejected. Only continuous evaluation internal marks (type 3) are supported.",
        )
    term = verified_term(db, payload.term_key)
    if payload.view == "marks":
        if not payload.exam_session or not payload.exam_type:
            raise HTTPException(400, "Discover and select an exam session and exam type before previewing marks.")
        discoveries = db.scalars(select(SyncJob).where(SyncJob.source_scope == "PERFORMANCE_SCOPE_DISCOVERY").order_by(SyncJob.created_at.desc())).all()
        discovery = next((j for j in discoveries if (j.details or {}).get("term_key") == payload.term_key), None)
        scopes = (discovery.details or {}).get("scopes", []) if discovery else []
        if not any(option["exam_session"] == payload.exam_session and option["exam_type"] == payload.exam_type and option.get("division_id") == payload.division_id for option in scopes):
            raise HTTPException(409, "This exam scope was not discovered for the selected semester.")
    source_course_count = None
    if payload.view == "marks":
        from app.adapters.performance_portal import extract_marks
        if not _SYNC_LOCK.acquire(blocking=False):
            raise HTTPException(409, "The portal is busy. Wait for discovery to finish before previewing marks.")
        try:
            source = extract_marks(term, payload.exam_session or "", payload.exam_type or "", payload.division_id)
            source_course_count = len(source["courses"])
        except Exception as err:
            logging.getLogger(__name__).exception("Error during extract_marks in preview: %s", err)
            raise HTTPException(409, f"Marks could not be validated for this exact scope: {err}. No marks were imported.") from None
        finally:
            _SYNC_LOCK.release()
    details = approval_scope(payload)
    if payload.view == "marks" and source is not None:
        details["captured_payload"] = source
        details["source_fingerprint"] = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
        details["captured_at"] = datetime.now(timezone.utc).isoformat()
    job = SyncJob(source_scope="PERFORMANCE_PILOT_PREVIEW", state="COMPLETED",
                  details=details)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"approval_id": job.id, "term_key": term.term_key, "label": term.display_label,
            "class_label": term.class_display_label, "view": payload.view,
            "exam_session": payload.exam_session, "exam_type": payload.exam_type, "division_id": payload.division_id,
            "source_course_count": source_course_count, "requires_user_approval": True, "scope": "One semester, one portal view, no other semesters or attendance changes."}


def extract_performance(term: Any, view: str) -> dict[str, Any]:
    labels = {"marks": {"marks", "internal marks", "subject marks"},
              "results": {"results", "semester results", "exam results", "examination results", "my report card"}}[view]
    extractor = LivePortalExtractor()
    with sync_playwright() as playwright:
        browser, page = extractor._get_portal_page(playwright)
        try:
            # Resolve real menu links only; never invent or brute-force exam URLs.
            links = page.locator("a[href]")
            candidates = []
            for index in range(links.count()):
                link = links.nth(index)
                if " ".join(link.inner_text().lower().split()) not in labels:
                    continue
                destination = urlsplit(urljoin(page.url, link.get_attribute("href") or ""))
                if (destination.scheme, destination.netloc) != ("https", "mrei.icloudems.com") or not destination.path.startswith("/corecampus/student/"):
                    raise PortalSafetyError("UNEXPECTED_PERFORMANCE_MENU_TARGET")
                candidates.append((link, destination.path))
            candidates = list({path: (link, path) for link, path in candidates}.values())
            if len(candidates) != 1:
                raise PortalSafetyError("PERFORMANCE_MENU_MISSING_OR_AMBIGUOUS")
            link, expected_path = candidates[0]
            link.click(timeout=8000)
            page.wait_for_load_state("networkidle", timeout=8000)
            check_page(page)
            if urlsplit(page.url).path != expected_path:
                raise PortalSafetyError("PERFORMANCE_ROUTE_MISMATCH")
            extractor._apply_filters(page, term.academic_year, term.semester_number, term.class_identifier)
            button = page.locator('#search, #getresult, button:has-text("Search"), button:has-text("View Result")')
            if button.count() != 1:
                raise PortalSafetyError("PERFORMANCE_SEARCH_NOT_VERIFIED")
            action = urlsplit(button.evaluate("el => el.form ? el.form.action : location.href"))
            if (action.scheme, action.netloc, action.path) != ("https", "mrei.icloudems.com", expected_path):
                raise PortalSafetyError("UNEXPECTED_PERFORMANCE_FORM_TARGET")
            button.click(timeout=8000)
            page.wait_for_load_state("networkidle", timeout=8000)
            verify_filters(page, term.academic_year, term.semester_number, term.class_identifier)
            if urlsplit(page.url).path != expected_path:
                raise PortalSafetyError("PERFORMANCE_ROUTE_MISMATCH")
            return parse_performance(canonical_html(page))
        finally:
            browser.close()


@router.post("/import")
def capture_performance(payload: PerformanceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.view == "results":
        raise HTTPException(
            400,
            "Official semester results view has been retired by COE / University and is unavailable for live import.",
        )
    if payload.exam_type == "4":
        raise HTTPException(
            400,
            "External examination scope (type 4) is rejected. Only continuous evaluation internal marks (type 3) are supported.",
        )
    if not payload.approval_id:
        raise HTTPException(400, "approval_id is required to import approved performance preview.")
    verified_term(db, payload.term_key)
    job = db.get(SyncJob, payload.approval_id)
    expected_scope = approval_scope(payload)
    job_details = (job.details or {}) if job else {}
    if not job or job.source_scope != "PERFORMANCE_PILOT_PREVIEW" or not all(job_details.get(k) == v for k, v in expected_scope.items()):
        raise HTTPException(409, "Preview and approve this exact semester and view first.")
    if not _SYNC_LOCK.acquire(blocking=False):
        raise HTTPException(409, "Another portal job is active.")
    try:
        claimed = db.execute(update(SyncJob).where(
            SyncJob.id == job.id, SyncJob.state == "COMPLETED",
            SyncJob.created_at >= datetime.now(timezone.utc) - timedelta(minutes=30),
        ).values(state="APPROVED").returning(SyncJob.id).execution_options(synchronize_session=False)).scalar_one_or_none()
        if claimed is None:
            raise HTTPException(409, "Preview expired or was already used.")
        db.commit()
        if not payload.exam_session or not payload.exam_type:
            raise HTTPException(400, "Exam session and exam type are required for marks import.")
        storage_view = f"marks:{payload.exam_session}:{payload.exam_type}:{payload.division_id or ''}"
        if "captured_payload" not in job_details or not job_details["captured_payload"]:
            raise HTTPException(409, "Preview captured payload is missing or invalid. Please re-preview.")
        parsed = job_details["captured_payload"]
        snap = persist_performance(db, payload.term_key, storage_view, parsed)
        sanitized_details = dict(job.details or {})
        courses = parsed.get("courses", []) if isinstance(parsed, dict) else []
        sanitized_details["captured_payload"] = {
            "redacted": True,
            "course_count": len(courses),
            "summary": "Source payload persisted in PerformanceSnapshot and scrubbed from sync job details."
        }
        job.details = sanitized_details
        db.commit()
        return {"snapshot_id": snap.id, "term_key": snap.term_key, "view": snap.view, "provenance": snap.provenance}
    except HTTPException:
        raise
    except Exception as error:
        logging.getLogger(__name__).warning("Performance scope discovery stopped: %s", type(error).__name__)
        db.rollback()
        raise HTTPException(409, "Performance route, filters, or result format could not be verified. No result snapshot was stored.") from None
    finally:
        _SYNC_LOCK.release()
