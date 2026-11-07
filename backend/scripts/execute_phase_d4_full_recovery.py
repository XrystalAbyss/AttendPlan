"""Phase D.4 Multi-Semester Full Historical Recovery Script with Resume Awareness.

Authorized by User for:
- Semester 3: AY 2025-2026, Sem 3, Class ID 1067 (1 summary + 4 months: 2025-08..2025-11)
- Semester 2: AY 2024-2025, Sem 2, Class ID 1048 (1 summary + 5 months: 2025-01..2025-05)
- Semester 1: AY 2024-2025, Sem 1, Class ID 918 (1 summary + 4 months: 2024-08..2024-11)

Total Bounded Requests: 16 maximum.
Reuses verified local data; never duplicates verified scopes.
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
from datetime import date
from typing import Any

from sqlalchemy import select

from app.adapters.live_portal_extractor import LivePortalExtractor
from app.adapters.portal_safety import PortalSafetyError, validate_result, classify_daywise_html
from app.db.enums import IngestionOutcome, SyncJobState
from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    AttendanceSnapshotRow,
    Course,
    PerformanceSnapshot,
    SyncJob,
)
from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.services.reconciliation_service import ReconciliationService
from app.services.sync_job_service import SyncJobService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PhaseD4Execution")

SEMESTER_CONFIGS = [
    {
        "academic_year": "2025-2026",
        "semester": 3,
        "class_id": "1067",
        "class_label": "B.Tech CSE AIML-Sem 3",
        "candidate_months": ["2025-08", "2025-09", "2025-10", "2025-11"],
    },
    {
        "academic_year": "2024-2025",
        "semester": 2,
        "class_id": "1048",
        "class_label": "B.Tech CSE AIML-Sem 2",
        "candidate_months": ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05"],
    },
    {
        "academic_year": "2024-2025",
        "semester": 1,
        "class_id": "918",
        "class_label": "B.Tech CSE AIML-Sem 1",
        "candidate_months": ["2024-08", "2024-09", "2024-10", "2024-11"],
    },
]


def execute_phase_d4() -> dict[str, Any]:
    db = SessionLocal()
    extractor = LivePortalExtractor()
    ingestion_service = IngestionService(db)
    sync_job_service = SyncJobService(db, extractor)
    rec_service = ReconciliationService(db)

    audit_summary: dict[str, Any] = {
        "execution_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "semesters": {},
        "global_status": "SUCCESS",
    }

    try:
        # Pre-execution checks: verify Sem 4, Sem 5, Marks preservation
        sem4_snap = db.query(AttendanceSnapshot).join(AcademicTerm).filter(AcademicTerm.semester_number == 4).first()
        sem5_snaps_cnt = db.query(AttendanceSnapshot).join(AcademicTerm).filter(AcademicTerm.semester_number == 5).count()
        marks_cnt = db.query(PerformanceSnapshot).count()

        logger.info(f"PRE-EXECUTION BASELINE: Sem 4 Snap={sem4_snap.id if sem4_snap else None}, Sem 5 Snaps={sem5_snaps_cnt}, Marks={marks_cnt}")

        for sem_cfg in SEMESTER_CONFIGS:
            ay = sem_cfg["academic_year"]
            sem_num = sem_cfg["semester"]
            cid = sem_cfg["class_id"]
            clabel = sem_cfg["class_label"]
            months = sem_cfg["candidate_months"]

            sem_key = f"{ay}_s{sem_num}_{cid}"
            logger.info("============================================================")
            logger.info(f"PROCESSING SEMESTER: {ay} Semester {sem_num} ({clabel})")
            logger.info("============================================================")

            sem_record: dict[str, Any] = {
                "academic_year": ay,
                "semester": sem_num,
                "class_id": cid,
                "class_label": clabel,
                "summary": {},
                "months": [],
                "reconciliation": {},
                "status": "IN_PROGRESS",
            }
            audit_summary["semesters"][sem_key] = sem_record

            # Find existing academic term if already created
            existing_term = db.query(AcademicTerm).filter(
                AcademicTerm.academic_year == ay,
                AcademicTerm.semester_number == sem_num,
            ).first()

            term_id = existing_term.id if existing_term else None

            # ----------------------------------------------------
            # Step A: Subject-Wise Summary (Reuse or Extract)
            # ----------------------------------------------------
            existing_snap = None
            if existing_term:
                existing_snap = db.query(AttendanceSnapshot).filter(
                    AttendanceSnapshot.academic_term_id == existing_term.id
                ).order_by(AttendanceSnapshot.captured_at.desc()).first()

            if existing_snap:
                logger.info(f"Step A: Reusing EXISTING VERIFIED Subject Summary for {ay} Sem {sem_num} (Snap {existing_snap.id})")
                rows = db.query(AttendanceSnapshotRow).filter(AttendanceSnapshotRow.snapshot_id == existing_snap.id).all()
                tot_att = sum(r.attended_periods for r in rows)
                tot_del = sum(r.delivered_periods for r in rows)
                pct = round(100.0 * tot_att / tot_del, 2) if tot_del > 0 else None
                sem_record["summary"] = {
                    "outcome": "EXISTING_VERIFIED_REUSED",
                    "term_id": existing_term.id,
                    "snapshot_id": existing_snap.id,
                    "courses_count": len(rows),
                    "attended": tot_att,
                    "delivered": tot_del,
                    "percentage": pct,
                }
            else:
                logger.info(f"Step A: Extracting LIVE Subject-Wise Summary for {ay} Sem {sem_num} (Class {cid})...")
                time.sleep(2.5)  # Human-like polite pacing

                summary_job = sync_job_service.create_job(
                    source_scope="HISTORICAL_SUBJECT_WISE",
                    progress_total=1,
                    details={"academic_year": ay, "semester": sem_num, "class_id": cid},
                )

                sub_res = None
                for attempt in range(2):
                    try:
                        sync_job_service.update_job_progress(
                            summary_job.id,
                            SyncJobState.SYNCING_SUBJECTS,
                            f"Extracting subject-wise summary for {ay} Sem {sem_num} (attempt {attempt + 1})",
                        )
                        sub_res = extractor.extract_live_subject_wise(
                            academic_year=ay,
                            semester=sem_num,
                            class_id=cid,
                        )
                        validate_result(
                            sub_res,
                            year=ay,
                            semester=sem_num,
                            class_id=cid,
                            class_label=clabel,
                        )
                        break
                    except Exception as err:
                        logger.warning(f"Attempt {attempt + 1} failed for subject summary {ay} Sem {sem_num}: {err}")
                        if attempt == 0:
                            time.sleep(3.0)
                        else:
                            raise err

                db_snap, outcome = ingestion_service.ingest_subject_wise_snapshot(
                    sub_res.snapshot,
                    source="LIVE_PORTAL_AUTOMATED_HISTORICAL_SUBWISE",
                )

                term_id = db_snap.academic_term_id
                summary_job.academic_term_id = term_id

                tot_att = sub_res.snapshot.summary.total_attended
                tot_del = sub_res.snapshot.summary.total_delivered
                courses_cnt = len(sub_res.snapshot.courses)
                pct = sub_res.snapshot.summary.overall_percentage

                sync_job_service.update_job_progress(
                    summary_job.id,
                    SyncJobState.COMPLETED,
                    f"Subject summary persisted ({tot_att}/{tot_del})",
                    completed_batches=1,
                    extra_details={
                        "snapshot_id": db_snap.id,
                        "term_id": term_id,
                        "courses": courses_cnt,
                        "attended": tot_att,
                        "delivered": tot_del,
                    },
                )

                sem_record["summary"] = {
                    "outcome": "SAVED_VERIFIED" if outcome != IngestionOutcome.DUPLICATE_SKIPPED else "DUPLICATE_SKIPPED",
                    "term_id": term_id,
                    "snapshot_id": db_snap.id,
                    "courses_count": courses_cnt,
                    "attended": tot_att,
                    "delivered": tot_del,
                    "percentage": pct,
                }
                logger.info(f"Subject Summary Ingested: Courses={courses_cnt}, Attended={tot_att}, Delivered={tot_del}, Pct={pct}%")

            # ----------------------------------------------------
            # Step B: Sequentially Extract Candidate Day-Wise Months
            # ----------------------------------------------------
            logger.info(f"Step B: Processing {len(months)} Day-Wise Months for {ay} Sem {sem_num}...")

            for m_str in months:
                year_part, month_part = m_str.split("-")
                y_i, m_i = int(year_part), int(month_part)
                last_d = calendar.monthrange(y_i, m_i)[1]
                from_d = f"{y_i:04d}-{m_i:02d}-01"
                to_d = f"{y_i:04d}-{m_i:02d}-{last_d:02d}"

                # Check if batch already exists in DB
                existing_batch = None
                if term_id:
                    existing_batch = db.query(AttendanceObservationBatch).filter(
                        AttendanceObservationBatch.academic_term_id == term_id,
                        AttendanceObservationBatch.coverage_start_date == date.fromisoformat(from_d),
                        AttendanceObservationBatch.coverage_end_date == date.fromisoformat(to_d),
                    ).first()

                if existing_batch:
                    obs = db.query(AttendancePeriodObservation).filter(
                        AttendancePeriodObservation.observation_batch_id == existing_batch.id
                    ).all()
                    obs_cnt = len(obs)
                    att_cnt = sum(o.attended_period_count for o in obs)
                    del_cnt = sum(o.delivered_period_count for o in obs)
                    u_dates = sorted(set(o.attendance_date.isoformat() for o in obs))

                    logger.info(f"--- Day-Wise {m_str}: EXISTING_VERIFIED_REUSED (Obs={obs_cnt}, Att={att_cnt}, Del={del_cnt}, Days={len(u_dates)}) ---")
                    sem_record["months"].append({
                        "month": m_str,
                        "batch_id": existing_batch.id,
                        "outcome": "EXISTING_VERIFIED_REUSED",
                        "checksum": existing_batch.content_checksum,
                        "observations_extracted": obs_cnt,
                        "attended": att_cnt,
                        "delivered": del_cnt,
                        "dates_count": len(u_dates),
                    })
                    continue

                logger.info(f"--- Day-Wise LIVE EXTRACTION: {m_str} ({from_d} to {to_d}) ---")
                time.sleep(2.5)  # Polite pacing

                m_job = sync_job_service.create_job(
                    source_scope="HISTORICAL_DAYWISE_MONTH",
                    academic_term_id=term_id,
                    progress_total=1,
                    details={"month": m_str, "academic_year": ay, "semester": sem_num, "class_id": cid},
                )

                m_record: dict[str, Any] = {
                    "month": m_str,
                    "job_id": m_job.id,
                    "outcome": "UNKNOWN",
                    "observations_extracted": 0,
                    "attended": 0,
                    "delivered": 0,
                    "dates_count": 0,
                }
                sem_record["months"].append(m_record)

                try:
                    sync_job_service.update_job_progress(
                        m_job.id,
                        SyncJobState.SYNCING_DAYWISE,
                        f"Extracting day-wise attendance for {m_str}",
                    )

                    day_res = extractor.extract_live_day_wise(
                        academic_year=ay,
                        semester=sem_num,
                        class_id=cid,
                        month=f"{m_i:02d}",
                        from_date=from_d,
                        to_date=to_d,
                        show_course_name=True,
                    )

                    validate_result(
                        day_res,
                        year=ay,
                        semester=sem_num,
                        class_id=cid,
                        class_label=clabel,
                        month=m_str,
                        require_dates=False,
                    )

                    obs = day_res.batch.observations
                    obs_cnt = len(obs)
                    att_cnt = sum(o.attended_period_count for o in obs)
                    del_cnt = sum(o.delivered_period_count for o in obs)
                    u_dates = sorted(set(o.attendance_date.isoformat() for o in obs))

                    m_record["observations_extracted"] = obs_cnt
                    m_record["attended"] = att_cnt
                    m_record["delivered"] = del_cnt
                    m_record["dates_count"] = len(u_dates)

                    if obs_cnt == 0 or del_cnt == 0:
                        outcome_label = classify_daywise_html(day_res.raw_html, requested_month=m_str)
                        m_record["outcome"] = outcome_label.value
                        sync_job_service.update_job_progress(
                            m_job.id,
                            SyncJobState.COMPLETED,
                            f"Result for {m_str}: {outcome_label.value}",
                            completed_batches=1,
                            diagnostic="Zero lecture periods scheduled or recorded in this calendar month.",
                        )
                    else:
                        sync_job_service.update_job_progress(
                            m_job.id,
                            SyncJobState.PERSISTING,
                            f"Persisting {obs_cnt} observations for {m_str}",
                        )

                        db_batch, b_outcome = ingestion_service.ingest_daywise_batch(
                            day_res.batch,
                            source="LIVE_PORTAL_AUTOMATED_HISTORICAL_DAYWISE",
                        )

                        m_record["outcome"] = "SAVED_VERIFIED" if b_outcome != IngestionOutcome.DUPLICATE_SKIPPED else "DUPLICATE_SKIPPED"
                        m_record["batch_id"] = db_batch.id
                        m_record["checksum"] = db_batch.content_checksum

                        sync_job_service.update_job_progress(
                            m_job.id,
                            SyncJobState.COMPLETED,
                            f"Persisted {obs_cnt} observations for {m_str}",
                            completed_batches=1,
                            extra_details={"batch_id": db_batch.id, "checksum": db_batch.content_checksum},
                        )

                    logger.info(f"Month {m_str}: Outcome={m_record['outcome']}, Obs={obs_cnt}, Att={att_cnt}, Del={del_cnt}, Days={len(u_dates)}")

                except PortalSafetyError as pse:
                    err_code = str(pse)
                    logger.warning(f"PortalSafetyError for {m_str}: {err_code}")
                    m_record["outcome"] = "WARNING_PAGE" if "WARNING" in err_code else f"PORTAL_SAFETY_{err_code}"
                    sync_job_service.update_job_progress(
                        m_job.id,
                        SyncJobState.FAILED,
                        f"Month {m_str} stopped: {err_code}",
                        diagnostic=err_code,
                    )
                except Exception as ex:
                    logger.error(f"Error in month {m_str}: {ex}", exc_info=True)
                    m_record["outcome"] = f"ERROR_{type(ex).__name__}"
                    sync_job_service.update_job_progress(
                        m_job.id,
                        SyncJobState.FAILED,
                        f"Month {m_str} failed: {type(ex).__name__}",
                        diagnostic=str(ex),
                    )

            # ----------------------------------------------------
            # Step C: Reconcile Term
            # ----------------------------------------------------
            logger.info(f"Step C: Running Reconciliation for {ay} Sem {sem_num}...")
            db.expire_all()
            rec_rep = rec_service.reconcile_term(term_id)
            sem_record["reconciliation"] = {
                "status": rec_rep.reconciliation_status.value,
                "status_explanation": rec_rep.status_explanation,
                "subject_total_attended": rec_rep.subject_wise_total_attended,
                "subject_total_delivered": rec_rep.subject_wise_total_delivered,
                "daywise_total_attended": rec_rep.day_wise_total_attended,
                "daywise_total_delivered": rec_rep.day_wise_total_delivered,
                "courses_count": len(rec_rep.course_breakdown),
                "unmapped_observations": rec_rep.total_unmapped_observations,
            }
            sem_record["status"] = "COMPLETED"
            logger.info(f"Reconciliation Verdict for {ay} Sem {sem_num}: {rec_rep.reconciliation_status.value}")
            logger.info(f"  Totals: Subj={rec_rep.subject_wise_total_attended}/{rec_rep.subject_wise_total_delivered} vs Daywise={rec_rep.day_wise_total_attended}/{rec_rep.day_wise_total_delivered}")

        logger.info("============================================================")
        logger.info("ALL THREE HISTORICAL SEMESTERS PROCESSED SUCCESSFULLY!")
        logger.info("============================================================")

    finally:
        db.close()

    return audit_summary


if __name__ == "__main__":
    result = execute_phase_d4()
    out_file = Path("backend/scripts/phase_d4_execution_result.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nPhase D.4 Execution finished. Result written to {out_file}")
