"""Explicitly reviewed, durable attendance archive. Never imports performance or credentials."""

from __future__ import annotations

import calendar
import threading
import time
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api import routes as portal
from app.adapters.live_portal_extractor import (
    BrowserNotConnectedError,
    SessionNotAuthenticatedError,
)
from app.adapters.portal_safety import PortalSafetyError, validate_result
from app.db.models import SyncJob
from app.db.session import SessionLocal, get_db
from app.services.historical_discovery_service import HistoricalDiscoveryService
from app.services.ingestion_service import IngestionService
from app.services.sync_job_service import _SYNC_LOCK
from app.services.academic_term_calendar_service import AcademicTermCalendarService

router = APIRouter(prefix="/api/v1/attendance-archive", tags=["Attendance archive"])




class Approval(BaseModel):
    plan_id: str
    approved: bool = False


class CalendarUpdateRequest(BaseModel):
    candidate_months: Optional[list[str]] = None
    excluded_months: Optional[list[str]] = None
    approved_exceptional_months: Optional[list[str]] = None
    notes: Optional[str] = None


def make_plan(db: Session, today: date) -> list[dict[str, Any]]:
    terms = HistoricalDiscoveryService(db).get_persisted_inventory().terms
    cal_svc = AcademicTermCalendarService(db=db)
    result: list[dict[str, Any]] = []
    for term in terms:
        if not term.details.get("selector_verified"):
            continue
        years = term.academic_year.split("-")
        if (
            len(years) != 2
            or not all(y.isdigit() for y in years)
            or int(years[1]) - int(years[0]) != 1
        ):
            raise ValueError("INVALID_ACADEMIC_YEAR")
        cal = cal_svc.get_calendar(term.academic_year, term.semester_number, term.class_identifier)
        candidate = cal_svc.get_candidate_months(term.academic_year, term.semester_number, term.class_identifier)
        months = [
            m for m in candidate
            if date(int(m[:4]), int(m[5:]), 1) <= today
        ]
        result.append(
            {
                "term_key": term.term_key,
                "year": term.academic_year,
                "semester": term.semester_number,
                "class_id": term.class_identifier,
                "class_label": term.class_display_label,
                "months": months,
                "calendar_source": cal.source,
                "confidence_status": cal.confidence_status,
                "start_date": cal.start_date,
                "end_date": cal.end_date,
                "excluded_months": cal.excluded_months,
                "approved_exceptional_months": cal.approved_exceptional_months,
            }
        )
    if (
        not result
        or len(result) > 12
        or sum(len(t["months"]) + 1 for t in result) > 180
    ):
        raise ValueError("ARCHIVE_PLAN_OUT_OF_BOUNDS")
    result.sort(key=lambda term: (term["year"], term["semester"]), reverse=True)
    for planned_term in result:
        planned_term["months"].reverse()
    return result


def public(job: SyncJob) -> dict[str, Any]:
    details = job.details or {}
    results = details.get("results", [])
    terms = details.get("terms", [])

    total_planned = sum(len(t.get("months", [])) for t in terms)
    saved_count = sum(1 for r in results if r.get("outcome") in {"SUCCESS", "DUPLICATE_SKIPPED"} and r.get("month"))
    empty_count = sum(1 for r in results if r.get("outcome") == "NO_REPORTED_PERIODS")
    outside_count = sum(1 for r in results if r.get("outcome") == "OUTSIDE_CALENDAR_WINDOW")
    unverified_count = sum(1 for r in results if r.get("outcome") in {"UNVERIFIED", "UNAVAILABLE_OR_UNRECOGNIZED", "WARNING_PAGE"})

    is_processing_complete = (
        job.state in {"COMPLETED", "COMPLETED_WITH_GAPS"}
        or (len(results) >= job.progress_total and job.progress_total > 0)
    )
    is_coverage_complete = is_processing_complete and (unverified_count == 0) and (saved_count + empty_count >= total_planned)

    return {
        "id": job.id,
        "state": job.state,
        "step": job.current_step,
        "completed": job.progress_current,
        "total": job.progress_total,
        "details": details,
        "coverage_metrics": {
            "total_planned_months": total_planned,
            "saved_months_count": saved_count,
            "empty_months_count": empty_count,
            "outside_calendar_count": outside_count,
            "unverified_months_count": unverified_count,
            "processing_status": "IMPORT_PROCESSING_COMPLETE" if is_processing_complete else "IN_PROGRESS",
            "coverage_verdict": "ACADEMIC_SOURCE_COVERAGE_COMPLETE" if is_coverage_complete else "ACADEMIC_SOURCE_COVERAGE_PARTIAL",
        },
    }


@router.post("/plan")
def plan(summary_only: bool = False, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        scopes = make_plan(db, date.today())
        if summary_only:
            for scope in scopes:
                scope["months"] = []
    except ValueError:
        raise HTTPException(
            409, "Discover and verify available semesters first."
        ) from None
    job = SyncJob(
        source_scope="ATTENDANCE_ARCHIVE_PLAN",
        state="PREVIEW_READY",
        current_step="Review semester/month scope",
        progress_total=sum(len(t["months"]) + 1 for t in scopes),
        details={"terms": scopes},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return public(job)


def run(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(SyncJob, job_id)
        if job is None:
            return
        if not _SYNC_LOCK.acquire(blocking=False):
            job.state = "STOPPED"
            job.current_step = "Portal busy; start a new reviewed plan."
            db.commit()
            return
        results: list[dict[str, Any]] = list((job.details or {}).get("results", []))

        def save(state: str, step: str) -> None:
            job.state = state
            job.current_step = step
            job.progress_current = len(results)
            if state in {
                "COMPLETED",
                "COMPLETED_WITH_GAPS",
                "CANCELLED",
                "ACTION_REQUIRED",
            }:
                job.completion_timestamp = datetime.now(timezone.utc)
            job.details = {**(job.details or {}), "results": list(results)}
            db.commit()

        try:
            save("CONNECTING", "Connecting with existing private login")
            if not portal._login_orchestrator.orchestrate_login().success:
                save(
                    "ACTION_REQUIRED",
                    "Private login needs attention; saved records retained.",
                )
                return
            ingest = IngestionService(db)
            for term in (job.details or {})["terms"]:
                db.refresh(job)
                if (job.details or {}).get("cancel_requested"):
                    save(
                        "CANCELLED", "Stopped between requests; saved batches retained."
                    )
                    return
                save("SYNCING", "Reading " + term["term_key"] + " summary")
                summary_class = term["class_label"]
                if not any(
                    r["term_key"] == term["term_key"] and r.get("scope") == "summary"
                    for r in results
                ):
                    try:
                        summary = (
                            portal._live_portal_extractor.extract_live_subject_wise(
                                academic_year=term["year"],
                                semester=term["semester"],
                                class_id=term["class_id"],
                            )
                        )
                        validate_result(
                            summary,
                            term["year"],
                            term["semester"],
                            term["class_id"],
                            term["class_label"],
                        )
                        snapshot, outcome = ingest.ingest_subject_wise_snapshot(
                            summary.snapshot, source="LIVE_PORTAL_ARCHIVE_SUMMARY"
                        )
                        results.append(
                            {
                                "term_key": term["term_key"],
                                "scope": "summary",
                                "outcome": outcome.value,
                                "courses": snapshot.record_count,
                            }
                        )
                        summary_class = summary.snapshot.class_name
                    except (SessionNotAuthenticatedError, BrowserNotConnectedError):
                        raise
                    except PortalSafetyError as error:
                        if str(error) in {
                            "SESSION_EXPIRED",
                            "PORTAL_ACCESS_DENIED_OR_EXPIRED",
                        }:
                            raise
                        db.rollback()
                        results.append(
                            {
                                "term_key": term["term_key"],
                                "scope": "summary",
                                "outcome": "UNVERIFIED",
                                "code": str(error),
                            }
                        )
                    except Exception as error:
                        db.rollback()
                        results.append(
                            {
                                "term_key": term["term_key"],
                                "scope": "summary",
                                "outcome": "UNAVAILABLE_OR_UNRECOGNIZED",
                                "error_type": type(error).__name__,
                            }
                        )
                for month in term["months"]:
                    if any(
                        r["term_key"] == term["term_key"] and r.get("month") == month
                        for r in results
                    ):
                        continue
                    db.refresh(job)
                    if (job.details or {}).get("cancel_requested"):
                        save(
                            "CANCELLED",
                            "Stopped between requests; saved batches retained.",
                        )
                        return
                    cal_svc = AcademicTermCalendarService(db=db)
                    is_in_win, reason = cal_svc.validate_month_in_window(
                        term["year"], term["semester"], month, term.get("class_id")
                    )
                    if not is_in_win:
                        results.append(
                            {
                                "term_key": term["term_key"],
                                "month": month,
                                "outcome": "OUTSIDE_CALENDAR_WINDOW",
                                "reason": reason,
                            }
                        )
                        continue

                    save("SYNCING", term["term_key"] + " · " + month)
                    time.sleep(1.5)
                    try:
                        end = f"{month}-{calendar.monthrange(int(month[:4]),int(month[5:]))[1]:02d}"
                        source = portal._live_portal_extractor.extract_live_day_wise(
                            academic_year=term["year"],
                            semester=term["semester"],
                            class_id=term["class_id"],
                            month=month[5:],
                            from_date=month + "-01",
                            to_date=end,
                            show_course_name=True,
                        )
                        validate_result(
                            source,
                            term["year"],
                            term["semester"],
                            term["class_id"],
                            term["class_label"],
                            month,
                        )
                        if not any(
                            o.delivered_period_count for o in source.batch.observations
                        ):
                            results.append(
                                {
                                    "term_key": term["term_key"],
                                    "month": month,
                                    "outcome": "NO_REPORTED_PERIODS",
                                }
                            )
                            continue
                        # Summary terms are stored under their verified class label. Bind
                        # the numeric daywise class ID to that same term, never create a parallel semester.
                        normalized = replace(
                            source.batch, class_identifier=summary_class
                        )
                        batch, outcome = ingest.ingest_daywise_batch(
                            normalized, source="LIVE_PORTAL_ARCHIVE_MONTH"
                        )
                        results.append(
                            {
                                "term_key": term["term_key"],
                                "month": month,
                                "outcome": outcome.value,
                                "period_records": len(source.batch.observations),
                                "delivered": sum(
                                    o.delivered_period_count
                                    for o in source.batch.observations
                                ),
                            }
                        )
                    except (SessionNotAuthenticatedError, BrowserNotConnectedError):
                        raise
                    except PortalSafetyError as error:
                        if str(error) in {
                            "SESSION_EXPIRED",
                            "PORTAL_ACCESS_DENIED_OR_EXPIRED",
                        }:
                            raise
                        db.rollback()
                        results.append(
                            {
                                "term_key": term["term_key"],
                                "month": month,
                                "outcome": "UNVERIFIED",
                                "code": str(error),
                            }
                        )
                    except Exception as error:
                        db.rollback()
                        results.append(
                            {
                                "term_key": term["term_key"],
                                "month": month,
                                "outcome": "UNAVAILABLE_OR_UNRECOGNIZED",
                                "error_type": type(error).__name__,
                            }
                        )
            gaps = any(
                r["outcome"] in {"UNVERIFIED", "UNAVAILABLE_OR_UNRECOGNIZED"}
                for r in results
            )
            save(
                "COMPLETED_WITH_GAPS" if gaps else "COMPLETED",
                "Available verified attendance saved; missing reports are not absences.",
            )
        except Exception as error:
            db.rollback()
            save(
                "ACTION_REQUIRED",
                "Portal validation stopped ("
                + (
                    str(error)
                    if isinstance(error, PortalSafetyError)
                    else type(error).__name__
                )
                + "); saved batches retained.",
            )
        finally:
            _SYNC_LOCK.release()


@router.post("/start")
def start(value: Approval, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not value.approved:
        raise HTTPException(400, "Explicit approval of the displayed plan is required.")
    if _SYNC_LOCK.locked():
        raise HTTPException(409, "Portal busy; wait for the active operation.")
    job = db.get(SyncJob, value.plan_id)
    if job is None or job.source_scope != "ATTENDANCE_ARCHIVE_PLAN":
        raise HTTPException(409, "Create a fresh archive plan first.")
    claimed = db.execute(
        update(SyncJob)
        .where(
            SyncJob.id == job.id,
            SyncJob.state == "PREVIEW_READY",
            SyncJob.created_at >= datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        .values(state="APPROVED")
        .returning(SyncJob.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if claimed is None:
        raise HTTPException(409, "Plan expired or was already used.")
    db.commit()
    db.refresh(job)
    threading.Thread(target=run, args=(job.id,), daemon=True).start()
    return public(job)


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict[str, Any]:
    job = db.scalars(
        select(SyncJob)
        .where(SyncJob.source_scope == "ATTENDANCE_ARCHIVE_PLAN")
        .order_by(SyncJob.created_at.desc())
    ).first()
    return (
        public(job)
        if job
        else {"state": "IDLE", "completed": 0, "total": 0, "details": {}}
    )


@router.post("/cancel")
def cancel(db: Session = Depends(get_db)) -> dict[str, Any]:
    job = db.scalars(
        select(SyncJob)
        .where(SyncJob.source_scope == "ATTENDANCE_ARCHIVE_PLAN")
        .order_by(SyncJob.created_at.desc())
    ).first()
    if job is None:
        raise HTTPException(404, "No archive run exists.")
    job.details = {**(job.details or {}), "cancel_requested": True}
    db.commit()
    return public(job)


def recover_interrupted(db: Session) -> None:
    archive_active_states = [
        "APPROVED",
        "CONNECTING",
        "SYNCING",
        "DISCOVERING",
        "SYNCING_SUBJECTS",
        "SYNCING_SUBWISE",
        "SYNCING_DAYWISE",
        "RUNNING",
    ]
    archive_jobs = db.scalars(
        select(SyncJob).where(
            SyncJob.source_scope == "ATTENDANCE_ARCHIVE_PLAN",
            SyncJob.state.in_(archive_active_states),
        )
    ).all()
    for job in archive_jobs:
        job.state = "PAUSED"
        job.current_step = "App restarted. Saved reports retained; continue remaining approved reports."

    # 2. Other jobs (Service A current refresh, pilot, etc.): transition to FAILED to prevent stale RUNNING jobs
    active_states = [
        "CONNECTING",
        "SYNCING",
        "DISCOVERING",
        "SYNCING_SUBJECTS",
        "SYNCING_DAYWISE",
        "VALIDATING",
        "PERSISTING",
        "RECONCILING",
        "RUNNING",
    ]
    interrupted_jobs = db.scalars(
        select(SyncJob).where(
            SyncJob.source_scope != "ATTENDANCE_ARCHIVE_PLAN",
            SyncJob.state.in_(active_states),
        )
    ).all()
    for job in interrupted_jobs:
        job.state = "FAILED"
        job.current_step = "App restarted during refresh. Refresh again on startup."
        job.safe_diagnostic_message = "INTERRUPTED_BY_APP_RESTART"
    db.commit()


@router.post("/resume")
def resume(value: Approval, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not value.approved:
        raise HTTPException(400, "Confirm continuation of the original reviewed scope.")
    if _SYNC_LOCK.locked():
        raise HTTPException(409, "Portal busy; wait for the active operation.")
    job = db.get(SyncJob, value.plan_id)
    if not job or job.source_scope != "ATTENDANCE_ARCHIVE_PLAN":
        raise HTTPException(404, "Archive run not found.")
    claimed = db.execute(
        update(SyncJob)
        .where(
            SyncJob.id == job.id,
            SyncJob.state.in_(["PAUSED", "ACTION_REQUIRED", "CANCELLED", "STOPPED"]),
        )
        .values(state="APPROVED")
        .returning(SyncJob.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if claimed is None:
        raise HTTPException(409, "This run cannot be resumed in its current state.")
    db.refresh(job)
    job.details = {**(job.details or {}), "cancel_requested": False}
    db.commit()
    db.refresh(job)
    threading.Thread(target=run, args=(job.id,), daemon=True).start()
    return public(job)


def _parse_term_key(term_key: str) -> tuple[str, int, str | None]:
    clean = term_key.strip()
    if "_" in clean:
        parts = clean.split("_")
        acad = parts[0]
        s_part = parts[1].lower().replace("s", "")
        sem = int(s_part) if s_part.isdigit() else 1
        cid = parts[2] if len(parts) > 2 and parts[2] != "default" else None
        return acad, sem, cid
    if "-S" in clean or "-s" in clean:
        parts = clean.replace("-s", "-S").split("-S")
        acad = parts[0]
        rest = parts[1].split("-")
        sem = int(rest[0]) if rest[0].isdigit() else 1
        cid = rest[1] if len(rest) > 1 else None
        return acad, sem, cid
    return clean, 1, None


@router.get("/calendars")
def get_all_calendars(db: Session = Depends(get_db)) -> dict[str, Any]:
    """List calendar configurations for all discovered terms."""
    cal_svc = AcademicTermCalendarService(db=db)
    terms = HistoricalDiscoveryService(db).get_persisted_inventory().terms
    configs = []
    seen = set()
    for term in terms:
        cal = cal_svc.get_calendar(term.academic_year, term.semester_number, term.class_identifier)
        configs.append(cal.to_dict())
        seen.add(cal.term_key)
    for cal in cal_svc.get_all_calendars():
        if cal.term_key not in seen:
            configs.append(cal.to_dict())
            seen.add(cal.term_key)
    return {"calendars": configs}


@router.get("/calendars/{term_key}")
def get_term_calendar(term_key: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve calendar configuration for a specific term key."""
    cal_svc = AcademicTermCalendarService(db=db)
    terms = HistoricalDiscoveryService(db).get_persisted_inventory().terms
    target = next((t for t in terms if t.term_key == term_key or f"{t.academic_year}-S{t.semester_number}" == term_key), None)
    if target:
        cal = cal_svc.get_calendar(target.academic_year, target.semester_number, target.class_identifier)
    else:
        try:
            acad, sem, cid = _parse_term_key(term_key)
            cal = cal_svc.get_calendar(acad, sem, cid)
        except Exception:
            raise HTTPException(404, f"Term {term_key} not found.")
    return {"calendar": cal.to_dict()}


@router.post("/calendars/{term_key}")
def update_term_calendar(
    term_key: str,
    payload: CalendarUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """User-confirmed update of candidate months, excluded months, and exceptions for a term."""
    cal_svc = AcademicTermCalendarService(db=db)
    terms = HistoricalDiscoveryService(db).get_persisted_inventory().terms
    target = next((t for t in terms if t.term_key == term_key or f"{t.academic_year}-S{t.semester_number}" == term_key), None)
    if target:
        cal = cal_svc.get_calendar(target.academic_year, target.semester_number, target.class_identifier)
    else:
        try:
            acad, sem, cid = _parse_term_key(term_key)
            cal = cal_svc.get_calendar(acad, sem, cid)
        except Exception:
            raise HTTPException(404, f"Term {term_key} not found.")
    if payload.candidate_months is not None:
        cal.candidate_months = sorted(set(payload.candidate_months))
    if payload.excluded_months is not None:
        cal.excluded_months = sorted(set(payload.excluded_months))
    if payload.approved_exceptional_months is not None:
        cal.approved_exceptional_months = sorted(set(payload.approved_exceptional_months))
    if payload.notes is not None:
        cal.notes = payload.notes
    saved = cal_svc.save_calendar(cal)
    return {"calendar": saved.to_dict()}


@router.post("/calendars/{term_key}/reset")
def reset_term_calendar(term_key: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Reset a term calendar configuration to provisional defaults."""
    cal_svc = AcademicTermCalendarService(db=db)
    terms = HistoricalDiscoveryService(db).get_persisted_inventory().terms
    target = next((t for t in terms if t.term_key == term_key or f"{t.academic_year}-S{t.semester_number}" == term_key), None)
    if target:
        res = cal_svc.reset_calendar(target.academic_year, target.semester_number, target.class_identifier)
    else:
        try:
            acad, sem, cid = _parse_term_key(term_key)
            res = cal_svc.reset_calendar(acad, sem, cid)
        except Exception:
            raise HTTPException(404, f"Term {term_key} not found.")
    return {"calendar": res.to_dict()}
