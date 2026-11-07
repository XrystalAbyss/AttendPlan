"""Persist truthful Semester 4 official result availability checkpoint (WITHHELD / DEACTIVATED_BY_COE)."""
import json
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domain.results_models import (
    OfficialResultSnapshot,
    OfficialSemesterResult,
    ResultPublicationStatus,
)
from app.services.results_service import (
    get_official_result_snapshot,
    persist_official_result,
)

def run():
    with open("reports/evidence/semester_4_official_result_source_evidence.json", "r", encoding="utf-8") as f:
        evidence = json.load(f)

    # Construct the domain model representing the truthful institutional state
    sem4_result = OfficialSemesterResult(
        term_key="2025-2026_s4_2508",
        academic_year="2025-2026",
        semester_number=4,
        class_identifier="2508",
        exam_session=None,
        exam_session_label="Official Result Card (COE)",
        sgpa=None,
        cgpa=None,
        credits_registered=None,
        credits_earned=None,
        total_points_secured=None,
        publication_status=ResultPublicationStatus.WITHHELD,
        courses=[],
        declaration_date=None,
    )

    raw_evidence_payload = {
        **evidence,
        "status_detail": "DEACTIVATED_BY_COE_OFFICE",
        "institutional_notice": "This page has been deactivated by the COE Office.Kindly contact the COE Office for activation or further assistance.",
    }

    db = SessionLocal()
    try:
        snapshot, verdict = persist_official_result(
            db=db,
            result=sem4_result,
            provenance="LIVE_PORTAL",
            raw_payload=raw_evidence_payload,
        )
        print(f"Persistence Outcome: {verdict}")
        print(f"Snapshot ID: {snapshot.id}")
        print(f"Term Key: {snapshot.term_key}")
        print(f"Publication Status: {snapshot.publication_status}")
        print(f"Canonical Checksum: {snapshot.checksum}")
        print(f"Captured At: {snapshot.captured_at}")

        # Independent Read-Back Verification
        read_back = get_official_result_snapshot(db, "2025-2026_s4_2508")
        assert read_back is not None, "Independent read-back failed: Snapshot not found!"
        assert read_back.id == snapshot.id, "ID mismatch in read-back"
        assert read_back.publication_status == "WITHHELD"
        assert read_back.sgpa is None
        assert read_back.cgpa is None
        assert len(read_back.courses) == 0
        print("Independent SQLite read-back verification: SUCCESS (All invariants satisfied)")

    finally:
        db.close()

if __name__ == "__main__":
    run()
