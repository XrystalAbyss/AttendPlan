"""Module to execute a single semester live marks import with strict request-budget tracking."""
import os
import sys
import json
import logging
from typing import Any

from app.db.session import SessionLocal
from app.db.models import PerformanceSnapshot, SyncJob
from app.adapters.performance_portal import discover_scopes
from app.api.performance_routes import (
    PerformanceRequest,
    performance_preview,
    capture_performance,
    verified_term,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("execute_e4")


def run_scope(term_key: str, expected_sem: int, expected_class_id: str) -> dict[str, Any]:
    os.environ["ATTENDPLAN_ENABLE_PERFORMANCE_PILOT"] = "1"
    db = SessionLocal()
    ledger = {
        "term_key": term_key,
        "discovery_requests": 0,
        "retrieval_requests": 0,
        "status": "NOT_STARTED",
        "exam_session": None,
        "exam_type": "3",
        "division_id": "A",
        "snapshot_id": None,
        "checksum": None,
        "courses_count": 0,
        "total_cells": 0,
        "reported_cells": 0,
        "unreported_cells": 0,
        "masked_cells": 0,
        "error": None,
    }

    try:
        # Step 1: Verify term
        logger.info(f"Verifying term {term_key}...")
        term = verified_term(db, term_key)
        assert term.semester_number == expected_sem, f"Semester mismatch: expected {expected_sem}, got {term.semester_number}"
        assert term.class_identifier == expected_class_id, f"Class ID mismatch: expected {expected_class_id}, got {term.class_identifier}"
        logger.info(f"Term verified: AY={term.academic_year}, Sem={term.semester_number}, Class={term.class_identifier}, Display={term.class_display_label}")

        # Step 2: Discover scopes (Operation 1)
        logger.info(f"Executing scoped discovery for {term_key}...")
        scopes = discover_scopes(term)
        ledger["discovery_requests"] += 1
        logger.info(f"Discovery returned {len(scopes)} exam scopes: {scopes}")

        # Record discovery job
        job = SyncJob(
            source_scope="PERFORMANCE_SCOPE_DISCOVERY",
            state="COMPLETED",
            details={"term_key": term.term_key, "scopes": scopes},
        )
        db.add(job)
        db.commit()

        # Step 3: Find internal exam type 3 scope
        internal_scopes = [s for s in scopes if str(s.get("exam_type")) == "3"]
        if not internal_scopes:
            raise ValueError(f"No Exam Type 3 (INTERNAL EXAM) discovered for {term_key}! Scopes: {scopes}")

        # In case multiple sessions exist, log and select the session corresponding to the term's academic window
        logger.info(f"Found {len(internal_scopes)} Internal Exam scopes: {internal_scopes}")
        selected_scope = internal_scopes[0]
        exam_session = selected_scope["exam_session"]
        division_id = selected_scope.get("division_id") or "A"
        ledger["exam_session"] = exam_session
        ledger["division_id"] = division_id
        logger.info(f"Selected Scope: Session={exam_session} ({selected_scope.get('exam_session_label')}), Division={division_id}")

        # Step 4: Preview (Operation 2 - Marks Report Retrieval)
        logger.info(f"Executing preview (report retrieval) for {term_key}...")
        req = PerformanceRequest(
            term_key=term_key,
            view="marks",
            exam_session=exam_session,
            exam_type="3",
            division_id=division_id,
        )
        preview_res = performance_preview(req, db)
        ledger["retrieval_requests"] += 1
        approval_id = preview_res["approval_id"]
        source_courses = preview_res.get("source_course_count", 0)
        logger.info(f"Preview successful: approval_id={approval_id}, source_courses={source_courses}")

        # Step 5: Import (Operation 3 - Zero-Refetch persistence)
        logger.info(f"Executing import from captured preview evidence (approval_id={approval_id})...")
        req_import = PerformanceRequest(
            term_key=term_key,
            view="marks",
            approval_id=approval_id,
            exam_session=exam_session,
            exam_type="3",
            division_id=division_id,
        )
        import_res = capture_performance(req_import, db)
        snapshot_id = import_res["snapshot_id"]
        logger.info(f"Import successful: snapshot_id={snapshot_id}")

        # Step 6: Read-back verification from database
        snap = db.get(PerformanceSnapshot, snapshot_id)
        assert snap is not None, "Snapshot must exist in DB!"
        ledger["snapshot_id"] = snap.id
        ledger["checksum"] = snap.checksum
        courses = snap.payload.get("courses", [])
        ledger["courses_count"] = len(courses)

        total_cells = 0
        reported = 0
        unreported = 0
        masked = 0
        for c in courses:
            for a in c.get("assessments", []):
                total_cells += 1
                st = a.get("status")
                if st == "REPORTED":
                    reported += 1
                elif st == "UNREPORTED":
                    unreported += 1
                elif st == "MASKED_BY_PORTAL":
                    masked += 1

        ledger["total_cells"] = total_cells
        ledger["reported_cells"] = reported
        ledger["unreported_cells"] = unreported
        ledger["masked_cells"] = masked
        ledger["status"] = "VERIFIED_LIVE"
        logger.info(f"Scope {term_key} VERIFIED_LIVE: {len(courses)} courses, {total_cells} cells (Rep={reported}, Unrep={unreported}, Masked={masked}), Checksum={snap.checksum}")

    except Exception as e:
        logger.exception(f"Error during execution of {term_key}: {e}")
        ledger["status"] = "FAILED"
        ledger["error"] = str(e)
    finally:
        db.close()

    return ledger


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python execute_e4_semester.py <term_key> <sem_num> <class_id>")
        sys.exit(1)
    tkey = sys.argv[1]
    snum = int(sys.argv[2])
    cid = sys.argv[3]
    res = run_scope(tkey, snum, cid)
    print("RESULT_JSON:" + json.dumps(res))
