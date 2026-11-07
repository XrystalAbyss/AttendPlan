"""Synchronization state machine and background job orchestrator.

Implements strict persistent job tracking:
- Mutex lock preventing concurrent portal browser synchronizations
- Safe recovery and persistence across interruptions
- Explicit state transitions: IDLE -> SYNCING_SUBJECTS -> SYNCING_DAYWISE -> PERSISTING -> RECONCILING -> COMPLETED
- Safe pause and state preservation on session expiration
- Cancellation support between discrete batch operations
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.adapters.live_portal_extractor import (
    BrowserNotConnectedError,
    LivePortalExtractor,
    SessionNotAuthenticatedError,
)
from app.db.enums import SyncJobState
from app.db.models import SyncJob
from app.services.ingestion_service import IngestionService
from app.services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)

# Mutex preventing duplicate concurrent browser sync sessions
_SYNC_LOCK = threading.Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SyncJobService:
    """Service orchestrating persistent attendance synchronization jobs."""

    def __init__(self, db: Session, extractor: Optional[LivePortalExtractor] = None) -> None:
        self.db = db
        self.extractor = extractor or LivePortalExtractor()
        self.ingestion_service = IngestionService(db)

    def create_job(
        self,
        source_scope: str = "CURRENT_SEMESTER_PILOT",
        academic_term_id: Optional[str] = None,
        progress_total: int = 1,
        details: Optional[dict[str, Any]] = None,
    ) -> SyncJob:
        """Initialize a new persistent sync job in SQLite."""
        job = SyncJob(
            source_scope=source_scope,
            academic_term_id=academic_term_id,
            state=SyncJobState.IDLE.value,
            current_step="Job initialized",
            start_timestamp=utc_now(),
            progress_total=progress_total,
            progress_current=0,
            completed_batches=0,
            failed_batches=0,
            details=details or {},
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str) -> Optional[SyncJob]:
        """Fetch sync job by ID."""
        return self.db.get(SyncJob, job_id, populate_existing=True)

    def get_latest_job(self) -> Optional[SyncJob]:
        """Fetch most recently created sync job."""
        stmt = select(SyncJob).where(SyncJob.source_scope.notin_([
            "ATTENDANCE_ARCHIVE_PLAN", "HISTORICAL_SELECTOR_DISCOVERY", "HISTORICAL_PILOT_PREVIEW", "PERFORMANCE_PILOT_PREVIEW", "PERFORMANCE_SCOPE_DISCOVERY"
        ])).order_by(desc(SyncJob.created_at)).limit(1)
        return self.db.scalars(stmt).first()

    def get_active_job(self) -> Optional[SyncJob]:
        """Return currently running job if any."""
        active_states = [
            SyncJobState.DISCOVERING.value,
            SyncJobState.SYNCING_SUBJECTS.value,
            SyncJobState.SYNCING_DAYWISE.value,
            SyncJobState.VALIDATING.value,
            SyncJobState.PERSISTING.value,
            SyncJobState.RECONCILING.value,
        ]
        stmt = select(SyncJob).where(SyncJob.state.in_(active_states)).order_by(desc(SyncJob.created_at)).limit(1)
        return self.db.scalars(stmt).first()

    def update_job_progress(
        self,
        job_id: str,
        state: SyncJobState,
        step: str,
        progress_current: Optional[int] = None,
        progress_total: Optional[int] = None,
        completed_batches: Optional[int] = None,
        failed_batches: Optional[int] = None,
        diagnostic: Optional[str] = None,
        extra_details: Optional[dict[str, Any]] = None,
    ) -> SyncJob:
        """Atomically update job status and progress in SQLite."""
        job = self.db.get(SyncJob, job_id, populate_existing=True)
        if not job:
            raise ValueError(f"SyncJob {job_id} not found")

        if job.state == SyncJobState.CANCELLED.value and state != SyncJobState.CANCELLED:
            return job
        job.state = state.value
        job.current_step = step
        if progress_current is not None:
            job.progress_current = progress_current
        if progress_total is not None:
            job.progress_total = progress_total
        if completed_batches is not None:
            job.completed_batches = completed_batches
        if failed_batches is not None:
            job.failed_batches = failed_batches
        if diagnostic is not None:
            job.safe_diagnostic_message = diagnostic[:256]

        if extra_details:
            current_d = dict(job.details or {})
            current_d.update(extra_details)
            job.details = current_d

        if state in [
            SyncJobState.COMPLETED,
            SyncJobState.PARTIALLY_COMPLETED,
            SyncJobState.CANCELLED,
            SyncJobState.FAILED,
            SyncJobState.SESSION_EXPIRED,
        ]:
            job.completion_timestamp = utc_now()

        self.db.commit()
        self.db.refresh(job)
        return job

    def cancel_job(self, job_id: str) -> SyncJob:
        """Request clean cancellation of a sync job."""
        return self.update_job_progress(
            job_id=job_id,
            state=SyncJobState.CANCELLED,
            step="Cancelled by user",
            diagnostic="Sync job cancelled by explicit user action.",
        )

    # ---------------------------------------------------------
    # Gate 4: Current-Semester Pilot Synchronization
    # ---------------------------------------------------------

    def run_pilot_sync(
        self,
        job_id: str,
        month: Optional[str] = None,
        academic_year: Optional[str] = None,
        semester: Optional[int] = None,
        class_id: Optional[str] = None,
    ) -> SyncJob:
        """Execute Gate 4 Pilot: Subject-Wise + 1 Month Day-Wise + Persistence + Reconciliation."""
        if not _SYNC_LOCK.acquire(blocking=False):
            return self.update_job_progress(
                job_id=job_id,
                state=SyncJobState.FAILED,
                step="Concurrency conflict",
                diagnostic="Another browser synchronization job is currently active. Only one job can control the portal at a time.",
            )

        try:
            # Check for cancellation
            job = self.get_job(job_id)
            if job and job.state == SyncJobState.CANCELLED.value:
                return job

            # Step 1: Subject-Wise Sync
            self.update_job_progress(
                job_id=job_id,
                state=SyncJobState.SYNCING_SUBJECTS,
                step="Navigating to Subject-Wise Attendance and extracting roster...",
                progress_total=4,
                progress_current=1,
            )

            try:
                sub_res = self.extractor.extract_live_subject_wise(
                    academic_year=academic_year,
                    semester=semester,
                    class_id=class_id,
                )
            except SessionNotAuthenticatedError as e:
                return self.update_job_progress(
                    job_id=job_id,
                    state=SyncJobState.SESSION_EXPIRED,
                    step="Session authentication required",
                    diagnostic=str(e),
                )
            except BrowserNotConnectedError as e:
                return self.update_job_progress(
                    job_id=job_id,
                    state=SyncJobState.FAILED,
                    step="Browser connection failed",
                    diagnostic=str(e),
                )

            # Persist Subject-Wise Snapshot
            self.update_job_progress(
                job_id=job_id,
                state=SyncJobState.PERSISTING,
                step="Persisting validated subject-wise attendance snapshot to local database...",
                progress_current=2,
            )

            db_snap, outcome = self.ingestion_service.ingest_subject_wise_snapshot(
                sub_res.snapshot,
                source="LIVE_PORTAL_AUTOMATED_SUBWISE",
            )
            term_id = db_snap.academic_term_id

            # Associate term with job
            job = self.get_job(job_id)
            if job:
                job.academic_term_id = term_id
                self.db.commit()

            # Check for cancellation between operations
            current_job = self.get_job(job_id)
            if current_job and current_job.state == SyncJobState.CANCELLED.value:
                return current_job

            # Step 2: Day-Wise Month Sync
            self.update_job_progress(
                job_id=job_id,
                state=SyncJobState.SYNCING_DAYWISE,
                step=f"Navigating to Day-Wise Attendance and extracting calendar matrix (Month: {month or 'active'})...",
                progress_current=3,
                completed_batches=1,
                extra_details={
                    "subject_wise_snapshot_id": db_snap.id,
                    "subject_wise_courses_count": len(sub_res.snapshot.courses),
                    "subject_wise_outcome": outcome.value,
                },
            )

            daywise_batch_id: Optional[str] = None
            daywise_outcome_str = "NOT_ATTEMPTED"
            try:
                day_res = self.extractor.extract_live_day_wise(
                    academic_year=academic_year or sub_res.academic_year,
                    semester=semester or sub_res.semester,
                    class_id=class_id or sub_res.class_identifier,
                    month=month,
                    show_course_name=True,
                )

                db_batch, day_outcome = self.ingestion_service.ingest_daywise_batch(
                    day_res.batch,
                    source="LIVE_PORTAL_AUTOMATED_DAYWISE",
                )
                daywise_batch_id = db_batch.id
                daywise_outcome_str = day_outcome.value
            except Exception as e:
                logger.warning("Day-wise pilot extraction warning: %s", e)
                # Day-wise failure should not destroy the successfully persisted subject snapshot
                return self.update_job_progress(
                    job_id=job_id,
                    state=SyncJobState.PARTIALLY_COMPLETED,
                    step="Subject-Wise synced; Day-Wise extraction incomplete",
                    failed_batches=1,
                    diagnostic=f"Subject-wise snapshot succeeded. Day-wise extraction note: {str(e)[:120]}",
                    extra_details={"daywise_error": str(e)},
                )


            # Step 3: Run Reconciliation
            self.update_job_progress(
                job_id=job_id,
                state=SyncJobState.RECONCILING,
                step="Reconciling subject-wise totals against day-wise observations...",
                progress_current=4,
                completed_batches=2,
            )

            recon_service = ReconciliationService(self.db)
            recon_report = recon_service.generate_reconciliation_report(term_id)

            return self.update_job_progress(
                job_id=job_id,
                state=SyncJobState.COMPLETED,
                step="Current-semester pilot synchronization completed successfully",
                progress_current=4,
                completed_batches=2,
                diagnostic="Subject-wise roster and day-wise calendar observations persisted and reconciled.",
                extra_details={
                    "term_id": term_id,
                    "reconciliation_status": recon_report.reconciliation_status.value,
                    "subject_attended": recon_report.subject_wise_total_attended,
                    "subject_delivered": recon_report.subject_wise_total_delivered,
                    "daywise_attended": recon_report.day_wise_total_attended,
                    "daywise_delivered": recon_report.day_wise_total_delivered,
                    "daywise_batch_id": daywise_batch_id,
                    "daywise_outcome": daywise_outcome_str,
                },
            )

        except Exception as e:
            logger.exception("Unexpected error in pilot sync: %s", e)
            return self.update_job_progress(
                job_id=job_id,
                state=SyncJobState.FAILED,
                step="Pilot sync failed",
                diagnostic=f"Unexpected error: {str(e)[:200]}",
            )
        finally:
            _SYNC_LOCK.release()

