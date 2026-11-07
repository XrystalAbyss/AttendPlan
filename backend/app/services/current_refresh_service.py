"""Service A: Current Semester Live Refresh.

Orchestrates verified, high-priority synchronization of:
1. Current academic term resolution (dynamic, non-hardcoded)
2. Current semester subject-wise summary extraction & persistence
3. Current calendar month day-wise attendance extraction (Asia/Kolkata timezone)
4. Reconciliation recalculation & frontend publication
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.adapters.live_portal_extractor import (
    BrowserNotConnectedError,
    LivePortalExtractor,
    SessionNotAuthenticatedError,
)
from app.adapters.portal_safety import PortalSafetyError
from app.db.enums import SyncJobState
from app.services.current_term_resolver import ResolvedTerm, resolve_current_term
from app.services.ingestion_service import IngestionService
from app.services.reconciliation_service import ReconciliationService
from app.services.sync_job_service import _SYNC_LOCK, SyncJobService

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def kolkata_now() -> datetime:
    try:
        import zoneinfo
        return datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
    except Exception:
        from datetime import timedelta
        return datetime.now(timezone(timedelta(hours=5, minutes=30)))


@dataclass
class CurrentRefreshResult:
    state: str  # "SYNC_COMPLETE" | "SYNC_PARTIAL" | "UP_TO_DATE" | "SYNC_FAILED" | "SESSION_EXPIRED" | "ACTION_REQUIRED"
    message: str
    term_key: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    class_identifier: Optional[str] = None
    summary_outcome: Optional[str] = None
    daywise_outcome: Optional[str] = None
    month_label: Optional[str] = None
    last_sync_time: Optional[str] = None
    job_id: Optional[str] = None
    diagnostic: Optional[str] = None


class CurrentRefreshService:
    """Service A orchestrating live synchronization for the active term."""

    def __init__(self, db: Session, extractor: Optional[LivePortalExtractor] = None) -> None:
        self.db = db
        self.extractor = extractor or LivePortalExtractor()
        self.ingestion_service = IngestionService(db)
        self.sync_job_service = SyncJobService(db, self.extractor)

    def refresh_current_semester(
        self,
        month_override: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> CurrentRefreshResult:
        """Execute complete current-semester refresh."""
        now_ist = kolkata_now()
        month_str = month_override or str(now_ist.month)
        month_display = now_ist.strftime("%B %Y")

        if not _SYNC_LOCK.acquire(blocking=False):
            logger.warning("Current semester refresh rejected: portal lock is busy")
            return CurrentRefreshResult(
                state="SYNC_FAILED",
                message="Another portal operation is in progress. Please wait.",
                diagnostic="PORTAL_BUSY",
            )

        try:
            job = None
            if job_id:
                job = self.sync_job_service.get_job(job_id)
            if not job:
                job = self.sync_job_service.create_job(
                    source_scope="CURRENT_SEMESTER_LIVE_REFRESH",
                    progress_total=3,
                    details={"requested_month": month_str, "timezone": "Asia/Kolkata"},
                )
            job_id = job.id
            # 1. Resolve Current Term
            self.sync_job_service.update_job_progress(
                job_id,
                SyncJobState.DISCOVERING,
                "Resolving current academic term...",
                progress_current=1,
            )

            try:
                term: ResolvedTerm = resolve_current_term(self.extractor, self.db)
                if term.is_provisional or not term.is_verified:
                    return self._fail_job(job_id, "CURRENT_TERM_UNVERIFIED", "Active term cannot be verified against live portal.")
            except PortalSafetyError as err:
                return self._fail_job(job_id, str(err), "Failed to verify current term.")
            except (SessionNotAuthenticatedError, BrowserNotConnectedError) as err:
                return self._auth_required_job(job_id, str(err))

            term_key = f"{term.academic_year}-S{term.semester_number}"
            logger.info("Service A resolved current term: %s (%s)", term_key, term.class_display_label)

            # 2. Extract & Ingest Subject-Wise Summary
            self.sync_job_service.update_job_progress(
                job_id,
                SyncJobState.SYNCING_SUBJECTS,
                f"Extracting subject-wise summary for {term_key}...",
                progress_current=2,
                extra_details={
                    "academic_year": term.academic_year,
                    "semester": term.semester_number,
                    "class_identifier": term.class_identifier,
                },
            )

            sub_res = self.extractor.extract_live_subject_wise(
                academic_year=term.academic_year,
                semester=term.semester_number,
                class_id=term.class_identifier,
            )

            if not sub_res.validation.is_valid:
                logger.warning("Subject-wise extraction validation failed: %s", sub_res.validation.quarantine_reason)
                return self._fail_job(
                    job_id,
                    sub_res.validation.quarantine_reason or "VALIDATION_FAILED",
                    f"Subject-wise validation rejected: {sub_res.validation.quarantine_reason}",
                )

            snap, s_outcome = self.ingestion_service.ingest_subject_wise_snapshot(
                sub_res.snapshot,
                source="LIVE_PORTAL_AUTOMATED_SUBWISE",
            )
            term_id = snap.academic_term_id

            # Associate term with job
            job_record = self.sync_job_service.get_job(job_id)
            if job_record:
                job_record.academic_term_id = term_id
                self.db.commit()

            # 3. Extract & Ingest Current Month Day-Wise Attendance
            self.sync_job_service.update_job_progress(
                job_id,
                SyncJobState.SYNCING_DAYWISE,
                f"Extracting {month_display} day-wise attendance...",
                progress_current=3,
                completed_batches=1,
                extra_details={"summary_outcome": s_outcome.value, "snapshot_id": snap.id},
            )

            daywise_outcome = "NOT_ATTEMPTED"
            daywise_error = None
            try:
                day_res = self.extractor.extract_live_day_wise(
                    academic_year=term.academic_year,
                    semester=term.semester_number,
                    class_id=term.class_identifier,
                    month=month_str,
                    show_course_name=True,
                )
                db_batch, d_outcome = self.ingestion_service.ingest_daywise_batch(
                    day_res.batch,
                    source="LIVE_PORTAL_AUTOMATED_DAYWISE",
                )
                daywise_outcome = d_outcome.value
            except Exception as e:
                logger.warning("Current month day-wise extraction unavailable: %s", e, exc_info=True)
                daywise_outcome = "UNAVAILABLE"
                daywise_error = str(e)

            # 4. Reconciliation
            self.sync_job_service.update_job_progress(
                job_id,
                SyncJobState.RECONCILING,
                "Recalculating statistics and reconciliation...",
            )
            recon_service = ReconciliationService(self.db)
            recon_service.generate_reconciliation_report(term_id)

            # 5. Evaluate final status
            sync_time = now_ist.isoformat()
            if daywise_outcome in ("SUCCESS", "DUPLICATE_SKIPPED"):
                if s_outcome.value == "DUPLICATE_SKIPPED" and daywise_outcome == "DUPLICATE_SKIPPED":
                    final_state = "UP_TO_DATE"
                    final_message = f"Attendance is already up to date ({month_display})."
                else:
                    final_state = "SYNC_COMPLETE"
                    final_message = f"Current semester attendance refreshed successfully ({month_display})."
                job_state = SyncJobState.COMPLETED
            else:
                final_state = "SYNC_PARTIAL"
                final_message = f"Subject summary refreshed; {now_ist.strftime('%B')} day-wise records not yet available."
                job_state = SyncJobState.PARTIALLY_COMPLETED

            self.sync_job_service.update_job_progress(
                job_id,
                job_state,
                final_message,
                completed_batches=2 if daywise_outcome != "UNAVAILABLE" else 1,
                failed_batches=0 if daywise_outcome != "UNAVAILABLE" else 1,
                diagnostic="Partial: day-wise incomplete." if daywise_error else None,
                extra_details={
                    "last_sync_time": sync_time,
                    "summary_outcome": s_outcome.value,
                    "daywise_outcome": daywise_outcome,
                    "daywise_error": daywise_error,
                    "term_key": term_key,
                },
            )

            return CurrentRefreshResult(
                state=final_state,
                message=final_message,
                term_key=term_key,
                academic_year=term.academic_year,
                semester=term.semester_number,
                class_identifier=term.class_identifier,
                summary_outcome=s_outcome.value,
                daywise_outcome=daywise_outcome,
                month_label=month_display,
                last_sync_time=sync_time,
                job_id=job_id,
            )

        except SessionNotAuthenticatedError as e:
            return self._auth_required_job(job_id, str(e))
        except BrowserNotConnectedError as e:
            return self._fail_job(job_id, str(e), "Dedicated Chrome browser is not connected.")
        except PortalSafetyError as e:
            return self._fail_job(job_id, str(e), f"Portal validation stopped: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during current semester refresh: %s", e)
            return self._fail_job(job_id, str(e), f"Refresh error: {str(e)[:100]}")
        finally:
            _SYNC_LOCK.release()

    def _auth_required_job(self, job_id: Optional[str], reason: str) -> CurrentRefreshResult:
        if job_id:
            try:
                self.sync_job_service.update_job_progress(
                    job_id,
                    SyncJobState.SESSION_EXPIRED,
                    "Portal authentication required. Showing saved attendance.",
                    diagnostic=reason[:128],
                )
            except Exception:
                pass
        return CurrentRefreshResult(
            state="AUTHENTICATION_REQUIRED",
            message="University portal login required. Showing saved attendance.",
            diagnostic=reason,
            job_id=job_id,
        )

    def _fail_job(self, job_id: Optional[str], diagnostic: str, message: str) -> CurrentRefreshResult:
        if job_id:
            try:
                self.sync_job_service.update_job_progress(
                    job_id,
                    SyncJobState.FAILED,
                    message,
                    diagnostic=diagnostic[:128],
                )
            except Exception:
                pass
        return CurrentRefreshResult(
            state="SYNC_FAILED",
            message=message,
            diagnostic=diagnostic,
            job_id=job_id,
        )
