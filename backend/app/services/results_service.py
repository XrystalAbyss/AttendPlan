"""Official Academic Results Ingestion, Reconciliation, and Retrieval Service (Data Class B).

Maintains complete independence from Class A internal marks (performance_snapshots).
Enforces canonical bit-for-bit checksumming, idempotent deduplication, and atomic persistence.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicTerm,
    OfficialCourseResultRow,
    OfficialResultSnapshot as OfficialResultSnapshotModel,
)
from app.domain.results_models import (
    OfficialResultSnapshot,
    OfficialSemesterResult,
)

logger = logging.getLogger(__name__)


class ResultsIngestionError(Exception):
    """Base exception for official results ingestion failures."""
    pass


def find_academic_term(db: Session, term_key: str) -> Optional[AcademicTerm]:
    """Resolve AcademicTerm by matching term_key convention."""
    terms = db.scalars(select(AcademicTerm)).all()
    for term in terms:
        # standard term_key formatting
        expected_key = f"{term.academic_year}_s{term.semester_number}_{term.class_identifier or ''}"
        if expected_key == term_key or term_key.startswith(f"{term.academic_year}_s{term.semester_number}"):
            return term
    return None


def persist_official_result(
    db: Session,
    result: OfficialSemesterResult,
    provenance: str = "LIVE_PORTAL",
    raw_payload: Optional[dict[str, Any]] = None,
) -> tuple[OfficialResultSnapshotModel, str]:
    """Persist an official semester result snapshot and course rows idempotently.

    Returns:
        (snapshot_model, status_verdict) where status_verdict is 'COMMITTED' or 'DUPLICATE_SKIPPED'.
    """
    checksum = OfficialResultSnapshot.compute_canonical_checksum(result)

    # Check for existing identical snapshot
    existing = db.scalar(
        select(OfficialResultSnapshotModel).where(
            OfficialResultSnapshotModel.term_key == result.term_key,
            OfficialResultSnapshotModel.checksum == checksum,
        )
    )
    if existing:
        logger.info(
            "Official result snapshot for term %s with checksum %s already exists (DUPLICATE_SKIPPED)",
            result.term_key,
            checksum,
        )
        return existing, "DUPLICATE_SKIPPED"

    # Find the academic term
    academic_term = find_academic_term(db, result.term_key)
    if not academic_term:
        raise ResultsIngestionError(f"Academic term not found for term_key: {result.term_key}")

    # Build catalog course map for reconciliation
    catalog_courses = {c.course_code: c for c in academic_term.courses}

    # Prepare raw payload for full provenance retention
    stored_payload = raw_payload or {
        "term_key": result.term_key,
        "academic_year": result.academic_year,
        "semester_number": result.semester_number,
        "class_identifier": result.class_identifier,
        "exam_session": result.exam_session,
        "exam_session_label": result.exam_session_label,
        "publication_status": result.publication_status.value,
        "declaration_date": result.declaration_date,
        "credits_registered": result.credits_registered,
        "credits_earned": result.credits_earned,
        "total_points_secured": result.total_points_secured,
        "sgpa": result.sgpa,
        "cgpa": result.cgpa,
        "courses": [
            {
                "course_code": c.course_code,
                "course_name": c.course_name,
                "credits": c.credits,
                "grade": c.grade,
                "grade_point": c.grade_point,
                "result_status": c.result_status,
            }
            for c in result.courses
        ],
    }

    snapshot = OfficialResultSnapshotModel(
        academic_term_id=academic_term.id,
        term_key=result.term_key,
        academic_year=result.academic_year,
        semester_number=result.semester_number,
        class_identifier=result.class_identifier,
        exam_session=result.exam_session,
        exam_session_label=result.exam_session_label,
        source_origin="LIVE_PORTAL_RESULT_CARD",
        publication_status=result.publication_status.value,
        declaration_date=result.declaration_date,
        credits_registered=result.credits_registered,
        credits_earned=result.credits_earned,
        total_points_secured=result.total_points_secured,
        sgpa=result.sgpa,
        cgpa=result.cgpa,
        checksum=checksum,
        provenance=provenance,
        raw_payload=stored_payload,
        captured_at=datetime.now(timezone.utc),
    )

    db.add(snapshot)
    db.flush()  # assign snapshot.id

    for course_result in result.courses:
        catalog_match = catalog_courses.get(course_result.course_code)
        course_row = OfficialCourseResultRow(
            snapshot_id=snapshot.id,
            course_id=catalog_match.id if catalog_match else None,
            course_code=course_result.course_code,
            course_name=course_result.course_name or (catalog_match.course_name if catalog_match else None),
            credits=course_result.credits,
            grade=course_result.grade,
            grade_point=course_result.grade_point,
            result_status=course_result.result_status,
            raw_data={
                "internal_marks": course_result.internal_marks,
                "external_marks": course_result.external_marks,
                "total_marks": course_result.total_marks,
            },
        )
        db.add(course_row)

    db.commit()
    db.refresh(snapshot)
    logger.info("Committed official result snapshot %s for term %s", snapshot.id, result.term_key)
    return snapshot, "COMMITTED"


def get_official_result_snapshot(db: Session, term_key: str) -> Optional[OfficialResultSnapshotModel]:
    """Retrieve the latest official result snapshot for a term."""
    return db.scalar(
        select(OfficialResultSnapshotModel)
        .where(OfficialResultSnapshotModel.term_key == term_key)
        .order_by(OfficialResultSnapshotModel.captured_at.desc())
    )


def overview_official_results(db: Session) -> dict[str, Any]:
    """Aggregate all official semester results across all terms."""
    snapshots = db.scalars(
        select(OfficialResultSnapshotModel).order_by(
            OfficialResultSnapshotModel.academic_year.asc(),
            OfficialResultSnapshotModel.semester_number.asc(),
        )
    ).all()

    # Deduplicate to latest snapshot per term_key
    latest_by_term: dict[str, OfficialResultSnapshotModel] = {}
    for snap in snapshots:
        latest_by_term[snap.term_key] = snap

    results_data = []
    for term_key, snap in sorted(latest_by_term.items(), key=lambda x: (x[1].academic_year, x[1].semester_number)):
        course_rows = []
        for c in snap.courses:
            course_rows.append({
                "course_code": c.course_code,
                "course_name": c.course_name,
                "credits": c.credits,
                "grade": c.grade,
                "grade_point": c.grade_point,
                "result_status": c.result_status,
                "catalog_mapped": c.course_id is not None,
            })

        results_data.append({
            "snapshot_id": snap.id,
            "term_key": snap.term_key,
            "academic_year": snap.academic_year,
            "semester_number": snap.semester_number,
            "class_identifier": snap.class_identifier,
            "exam_session": snap.exam_session,
            "exam_session_label": snap.exam_session_label,
            "publication_status": snap.publication_status,
            "declaration_date": snap.declaration_date,
            "credits_registered": snap.credits_registered,
            "credits_earned": snap.credits_earned,
            "total_points_secured": snap.total_points_secured,
            "sgpa": snap.sgpa,
            "cgpa": snap.cgpa,
            "checksum": snap.checksum,
            "provenance": snap.provenance,
            "captured_at": snap.captured_at.isoformat(),
            "courses_count": len(course_rows),
            "courses": course_rows,
        })

    return {
        "results": results_data,
        "total_terms_with_results": len(results_data),
        "note": "Official University Results (Data Class B) are distinct from internal assessment marks.",
    }

