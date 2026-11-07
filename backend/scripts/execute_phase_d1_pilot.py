"""Phase D.1 Live Pilot Execution Script.

Extracts historical day-wise attendance for:
Academic Year: 2025-2026
Semester: 4
Class ID: 2508 (B.Tech CSE AIML-Sem 4)
Approved Months: 2026-01, 2026-02, 2026-03, 2026-04, 2026-05
"""

from __future__ import annotations

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import calendar
import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import PortalSafetyError, validate_result
from app.db.enums import IngestionOutcome, SyncJobState
from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    Course,
    PerformanceSnapshot,
    SyncJob,
)
from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.services.sync_job_service import SyncJobService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PhaseD1Pilot")

AUTHORIZED_TERMS = {
    "academic_year": "2025-2026",
    "semester": 4,
    "class_id": "2508",
    "class_label": "B.Tech CSE AIML-Sem 4",
}

AUTHORIZED_MONTHS = [
    "2026-01",
    "2026-02",
    "2026-03",
    "2026-04",
    "2026-05",
]


def execute_pilot() -> dict[str, Any]:
    db = SessionLocal()
    extractor = LivePortalExtractor()
    ingestion_service = IngestionService(db)
    sync_job_service = SyncJobService(db, extractor)

    results: list[dict[str, Any]] = []

    try:
        # Pre-execution checks
        sem4_term = db.scalars(
            select(AcademicTerm).where(
                AcademicTerm.academic_year == AUTHORIZED_TERMS["academic_year"],
                AcademicTerm.semester_number == AUTHORIZED_TERMS["semester"],
            )
        ).first()

        if not sem4_term:
            raise RuntimeError("Semester 4 AcademicTerm record not found in database!")

        logger.info(
            f"Preflight Verified: Target Term ID={sem4_term.id}, AY={sem4_term.academic_year}, Sem={sem4_term.semester_number}"
        )

        # Baseline counts
        baseline_sem4_batches = db.scalars(
            select(AttendanceObservationBatch).where(
                AttendanceObservationBatch.academic_term_id == sem4_term.id
            )
        ).all()
        baseline_sem5_snaps = db.query(AttendanceSnapshot).filter(
            AttendanceSnapshot.academic_term_id != sem4_term.id
        ).count()
        baseline_marks = db.query(PerformanceSnapshot).count()

        logger.info(
            f"Baselines: Sem 4 Batches={len(baseline_sem4_batches)}, Other Term Snaps={baseline_sem5_snaps}, Marks={baseline_marks}"
        )

        # Iterate sequentially through authorized candidate months
        for month_str in AUTHORIZED_MONTHS:
            year_str, m_str = month_str.split("-")
            y_int, m_int = int(year_str), int(m_str)
            last_day = calendar.monthrange(y_int, m_int)[1]
            from_date_str = f"{y_int:04d}-{m_int:02d}-01"
            to_date_str = f"{y_int:04d}-{m_int:02d}-{last_day:02d}"

            logger.info(f"--- Processing Month: {month_str} ({from_date_str} to {to_date_str}) ---")

            month_job = sync_job_service.create_job(
                source_scope="HISTORICAL_DAYWISE_MONTH",
                academic_term_id=sem4_term.id,
                progress_total=1,
                details={"month": month_str},
            )

            month_record: dict[str, Any] = {
                "month": month_str,
                "job_id": month_job.id,
                "outcome": "UNKNOWN",
                "observations_extracted": 0,
                "attended_periods": 0,
                "delivered_periods": 0,
                "date_count": 0,
                "details": {},
            }

            try:
                sync_job_service.update_job_progress(
                    month_job.id,
                    SyncJobState.SYNCING_DAYWISE,
                    f"Extracting day-wise matrix for {month_str}",
                    extra_details={"month": month_str, "term": AUTHORIZED_TERMS},
                )

                # Extract live day-wise report from portal
                daywise_result = extractor.extract_live_day_wise(
                    academic_year=AUTHORIZED_TERMS["academic_year"],
                    semester=AUTHORIZED_TERMS["semester"],
                    class_id=AUTHORIZED_TERMS["class_id"],
                    month=f"{m_int:02d}",
                    from_date=from_date_str,
                    to_date=to_date_str,
                    show_course_name=True,
                )

                # Validate result
                validate_result(
                    daywise_result,
                    AUTHORIZED_TERMS["academic_year"],
                    AUTHORIZED_TERMS["semester"],
                    AUTHORIZED_TERMS["class_id"],
                    AUTHORIZED_TERMS["class_label"],
                    month=month_str,
                    require_dates=False,
                )

                obs_count = len(daywise_result.batch.observations)
                attended_count = sum(o.attended_period_count for o in daywise_result.batch.observations)
                delivered_count = sum(o.delivered_period_count for o in daywise_result.batch.observations)
                unique_dates = sorted(set(o.attendance_date.isoformat() for o in daywise_result.batch.observations))

                month_record["observations_extracted"] = obs_count
                month_record["attended_periods"] = attended_count
                month_record["delivered_periods"] = delivered_count
                month_record["date_count"] = len(unique_dates)

                if obs_count == 0 or delivered_count == 0:
                    outcome_classification = "NO_REPORTED_PERIODS"
                    sync_job_service.update_job_progress(
                        month_job.id,
                        SyncJobState.COMPLETED,
                        f"Zero reported periods for {month_str}",
                        completed_batches=1,
                        diagnostic="Zero lecture periods scheduled or held in this calendar month.",
                    )
                else:
                    # Ingest batch
                    sync_job_service.update_job_progress(
                        month_job.id,
                        SyncJobState.PERSISTING,
                        f"Persisting {obs_count} observations for {month_str}",
                    )

                    db_batch, outcome = ingestion_service.ingest_daywise_batch(
                        daywise_result.batch,
                        source="LIVE_PORTAL_AUTOMATED_HISTORICAL_DAYWISE",
                    )

                    if outcome == IngestionOutcome.DUPLICATE_SKIPPED:
                        outcome_classification = "DUPLICATE_SKIPPED"
                    else:
                        outcome_classification = "SAVED_VERIFIED"

                    sync_job_service.update_job_progress(
                        month_job.id,
                        SyncJobState.COMPLETED,
                        f"Persisted {obs_count} observations for {month_str}",
                        completed_batches=1,
                        extra_details={"batch_id": db_batch.id, "checksum": db_batch.content_checksum},
                    )

                month_record["outcome"] = outcome_classification
                month_record["details"] = {
                    "unique_dates": unique_dates[:5] + (["..."] if len(unique_dates) > 5 else []),
                    "first_date": unique_dates[0] if unique_dates else None,
                    "last_date": unique_dates[-1] if unique_dates else None,
                }

                logger.info(
                    f"Month {month_str} Outcome={outcome_classification}: Obs={obs_count}, Attended={attended_count}, Delivered={delivered_count}, Days={len(unique_dates)}"
                )

            except PortalSafetyError as pse:
                err_code = str(pse)
                logger.warning(f"PortalSafetyError for {month_str}: {err_code}")
                if "WARNING" in err_code:
                    month_record["outcome"] = "WARNING_PAGE"
                else:
                    month_record["outcome"] = f"PORTAL_ERROR_{err_code}"

                sync_job_service.update_job_progress(
                    month_job.id,
                    SyncJobState.FAILED,
                    f"Month {month_str} stopped: {err_code}",
                    diagnostic=err_code,
                )
            except Exception as ex:
                logger.error(f"Error processing month {month_str}: {ex}", exc_info=True)
                month_record["outcome"] = f"ERROR_{type(ex).__name__}"
                sync_job_service.update_job_progress(
                    month_job.id,
                    SyncJobState.FAILED,
                    f"Month {month_str} failed: {type(ex).__name__}",
                    diagnostic=str(ex),
                )

            results.append(month_record)

            # Enforce conservative pacing
            logger.info("Applying 2.0s pacing delay...")
            time.sleep(2.0)

        # Verification of Post-Flight Invariants
        logger.info("--- Performing Post-Pilot Verification ---")
        post_sem4_batches = db.scalars(
            select(AttendanceObservationBatch).where(
                AttendanceObservationBatch.academic_term_id == sem4_term.id
            )
        ).all()
        post_sem4_obs_count = db.scalars(
            select(AttendancePeriodObservation).where(
                AttendancePeriodObservation.academic_term_id == sem4_term.id
            )
        ).all()

        post_sem5_snaps = db.query(AttendanceSnapshot).filter(
            AttendanceSnapshot.academic_term_id != sem4_term.id
        ).count()
        post_marks = db.query(PerformanceSnapshot).count()

        summary = {
            "term_id": sem4_term.id,
            "academic_year": sem4_term.academic_year,
            "semester": sem4_term.semester_number,
            "class_identifier": sem4_term.class_identifier,
            "months_evaluated": results,
            "total_new_batches_persisted": len(post_sem4_batches),
            "total_sem4_observations_persisted": len(post_sem4_obs_count),
            "sem5_snapshots_unchanged": (post_sem5_snaps == baseline_sem5_snaps),
            "marks_snapshots_unchanged": (post_marks == baseline_marks),
        }

        logger.info(f"Pilot Complete! Persisted Batches: {len(post_sem4_batches)}, Obs: {len(post_sem4_obs_count)}")
        logger.info(f"Preservation Checks: Sem 5 Snaps Unchanged={summary['sem5_snapshots_unchanged']}, Marks Unchanged={summary['marks_snapshots_unchanged']}")

        return summary

    finally:
        db.close()


if __name__ == "__main__":
    out = execute_pilot()
    print("\nFINAL PILOT OUTPUT JSON:")
    print(json.dumps(out, indent=2))
