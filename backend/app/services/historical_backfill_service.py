"""Historical backfill service for multi-semester attendance synchronization.

Implements controlled two-stage ingestion:
- Stage A: Term-scoped subject-wise summaries (course roster, attended, delivered, credits, faculty)
- Stage B: Term-scoped day-wise attendance matrices (lecture timetable, dates, present/absent observations)
- Controlled sequential pacing (1.5s - 2.5s)
- Single-active-job mutex lock protection
- Cancellation support between discrete term/month operations
- Idempotent deduplication via canonical checksums
- Zero cross-semester contamination
"""

from __future__ import annotations

import logging
import re

from app.adapters.portal_safety import PortalSafetyError, validate_result
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.adapters.daywise_parser import ERPDaywiseParser
from app.adapters.html_parser import ERPAttendanceParser
from app.adapters.live_portal_extractor import (
    LivePortalExtractor,
    SessionNotAuthenticatedError,
)
from app.db.enums import SyncJobState
from app.db.models import SyncJob
from app.services.historical_discovery_service import HistoricalDiscoveryService
from app.services.ingestion_service import IngestionService
from app.services.reconciliation_service import ReconciliationService
from app.services.sync_job_service import _SYNC_LOCK, SyncJobService

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HistoricalBackfillService:
    """Service orchestrating multi-semester historical attendance backfill."""

    def __init__(
        self,
        db: Session,
        extractor: Optional[LivePortalExtractor] = None,
        pacing_delay_seconds: float = 1.5,
    ) -> None:
        self.db = db
        self.extractor = extractor or LivePortalExtractor()
        self.pacing_delay_seconds = pacing_delay_seconds
        self.ingestion_service = IngestionService(db)
        self.sync_job_service = SyncJobService(db, self.extractor)
        self.discovery_service = HistoricalDiscoveryService(db)
        self.reconciliation_service = ReconciliationService(db)

    def run_historical_backfill(
        self,
        job_id: str,
        selected_term_keys: list[str],
        import_daywise: bool = False,
        max_months_per_term: Optional[int] = None,
        requested_month: Optional[str] = None,
    ) -> SyncJob:
        """One explicit term, validated before each durable batch. Retry is idempotent."""
        if not _SYNC_LOCK.acquire(blocking=False):
            return self.sync_job_service.update_job_progress(
                job_id, SyncJobState.FAILED, "Concurrency conflict", diagnostic="Another portal job is active."
            )
        completed = 0
        attempted = 0
        try:
            if len(selected_term_keys) != 1:
                raise ValueError("ONE_TERM_REQUIRED")
            inventory = self.discovery_service.get_persisted_inventory()
            item = next((t for t in inventory.terms if t.term_key == selected_term_keys[0]), None)
            if item is None:
                raise ValueError("UNVERIFIED_TERM_SELECTION")
            if not item.details.get("selector_verified"):
                raise ValueError("FRESH_SELECTOR_DISCOVERY_REQUIRED")
            if import_daywise:
                # Never infer dates from semester parity or enumerate unapproved months.
                if not requested_month or not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", requested_month):
                    raise ValueError("EXPLICIT_MONTH_REQUIRED")
                from app.services.academic_term_calendar_service import AcademicTermCalendarService
                cal_svc = AcademicTermCalendarService(db=self.db)
                is_in_win, reason = cal_svc.validate_month_in_window(item.academic_year, item.semester_number, requested_month, item.class_identifier)
                if not is_in_win:
                    raise ValueError(f"OUTSIDE_CALENDAR_WINDOW: {reason}")
            total = 2 if import_daywise else 1
            self.db.expire_all()
            job = self.sync_job_service.get_job(job_id)
            if job is None:
                raise ValueError("JOB_NOT_FOUND")
            if job.state == SyncJobState.CANCELLED.value:
                return job
            self.sync_job_service.update_job_progress(
                job_id, SyncJobState.SYNCING_SUBJECTS, "Validating subject summary", progress_total=total,
                extra_details={"requested_month": requested_month, "selected_term_keys": selected_term_keys},
            )
            time.sleep(self.pacing_delay_seconds)
            attempted += 1
            sub = self.extractor.extract_live_subject_wise(
                academic_year=item.academic_year, semester=item.semester_number, class_id=item.class_identifier,
            )
            validate_result(sub, item.academic_year, item.semester_number,
                            item.class_identifier or "", item.class_display_label or "")
            self.db.expire_all()
            job = self.sync_job_service.get_job(job_id)
            if job and job.state == SyncJobState.CANCELLED.value:
                return job
            snap, _ = self.ingestion_service.ingest_subject_wise_snapshot(
                sub.snapshot, source="LIVE_PORTAL_AUTOMATED_HISTORICAL_SUBWISE"
            )
            completed += 1
            self.sync_job_service.update_job_progress(
                job_id, SyncJobState.PERSISTING, "Subject summary persisted", progress_current=completed,
                completed_batches=completed, extra_details={"persisted_term_id": snap.academic_term_id},
            )
            if import_daywise:
                self.db.expire_all()
                job = self.sync_job_service.get_job(job_id)
                if job and job.state == SyncJobState.CANCELLED.value:
                    return job
                self.sync_job_service.update_job_progress(job_id, SyncJobState.SYNCING_DAYWISE, "Validating explicit month")
                time.sleep(self.pacing_delay_seconds)
                attempted += 1
                day = self.extractor.extract_live_day_wise(
                    academic_year=item.academic_year, semester=item.semester_number, class_id=item.class_identifier,
                    month=str(int((requested_month or "").split("-")[1])), show_course_name=True,
                )
                validate_result(day, item.academic_year, item.semester_number, item.class_identifier or "",
                                item.class_display_label or "", requested_month)
                self.db.expire_all()
                job = self.sync_job_service.get_job(job_id)
                if job and job.state == SyncJobState.CANCELLED.value:
                    return job
                self.ingestion_service.ingest_daywise_batch(day.batch, source="LIVE_PORTAL_AUTOMATED_HISTORICAL_DAYWISE")
                completed += 1
            return self.sync_job_service.update_job_progress(
                job_id, SyncJobState.COMPLETED, "Requested pilot scope persisted",
                progress_current=completed, completed_batches=completed, failed_batches=0,
                diagnostic="Only the explicitly requested scope completed; semester coverage remains partial.",
            )
        except SessionNotAuthenticatedError:
            state = SyncJobState.SESSION_EXPIRED
            diagnostic = "Manual private authentication required. Committed batches preserved."
        except PortalSafetyError as error:
            state = SyncJobState.SESSION_EXPIRED if str(error) == "SESSION_EXPIRED" else SyncJobState.FAILED
            diagnostic = "Portal validation stopped the import. Committed batches preserved."
        except Exception:
            state = SyncJobState.FAILED
            diagnostic = "Historical import stopped safely. Verify selectors and requested scope before retry."
        finally:
            _SYNC_LOCK.release()
        self.db.rollback()
        return self.sync_job_service.update_job_progress(
            job_id, state, "Historical import stopped", completed_batches=completed,
            failed_batches=max(0, attempted - completed), progress_current=completed, diagnostic=diagnostic,
        )

    def import_term_offline(
        self,
        academic_year: str,
        semester: int,
        class_id: Optional[str],
        subject_html: str,
        daywise_html_list: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Offline ingestion helper for synthetic multi-semester test suites."""
        parser = ERPAttendanceParser()
        domain_snap = parser.parse_html(subject_html)
        db_snap, s_outcome = self.ingestion_service.ingest_subject_wise_snapshot(
            domain_snap,
            source="OFFLINE_HISTORICAL_FIXTURE_SUBWISE",
        )

        daywise_results = []
        if daywise_html_list:
            day_parser = ERPDaywiseParser()
            for d_html in daywise_html_list:
                parsed_batch = day_parser.parse_html(d_html)
                db_batch, b_outcome = self.ingestion_service.ingest_daywise_batch(
                    parsed_batch,
                    source="OFFLINE_HISTORICAL_FIXTURE_DAYWISE",
                )
                daywise_results.append(
                    {
                        "batch_id": db_batch.id,
                        "outcome": b_outcome.value,
                        "obs_count": len(parsed_batch.observations),
                    }
                )

        # Coverage report
        coverage = self.discovery_service.get_term_coverage(db_snap.academic_term_id)

        return {
            "term_id": db_snap.academic_term_id,
            "snapshot_id": db_snap.id,
            "subject_outcome": s_outcome.value,
            "daywise_batches": daywise_results,
            "coverage_state": coverage.coverage_state.value,
            "reconciliation_verdict": coverage.reconciliation_verdict.value,
        }
