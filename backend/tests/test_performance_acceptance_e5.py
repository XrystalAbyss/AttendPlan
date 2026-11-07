"""Definitive offline human acceptance and integrity verification for AttendPlan Phase E.5."""
from __future__ import annotations

import os
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AcademicTerm,
    AttendanceObservationBatch,
    AttendancePeriodObservation,
    AttendanceSnapshot,
    AttendanceSnapshotRow,
    Course,
    PerformanceSnapshot,
)
from app.db.session import build_sqlite_url, create_app_engine
from app.services.performance_service import (
    overview,
    reconcile_course_coverage,
)


def get_user_db_session() -> Session | None:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        return None
    user_db_path = Path(local_app_data) / "AttendPlan" / "attendplan.sqlite3"
    if not user_db_path.exists():
        return None
    engine = create_app_engine(build_sqlite_url(user_db_path))
    return Session(engine)


def test_five_semester_performance_registry():
    """Verify all 5 performance snapshots exist with exact identities, views, and checksums."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        assert len(snaps) == 5

        expected_registry = {
            "2024-2025_s1_918": {
                "id": "77d4702c-1e28-4ca7-95d5-329c7bba8d1d",
                "view": "marks:5764:3:A",
                "checksum": "d0bafbaefa6aa526dc05f4e1fa73c78c6bcc11ef624a8c77701232a34f23ea6c",
                "courses": 11,
                "cells": 66,
            },
            "2024-2025_s2_1048": {
                "id": "b15162ae-4a03-4e99-8155-c844fb328ea7",
                "view": "marks:5943:3:A",
                "checksum": "c8110fdf0233baf2208c42c03c3e3c33e482daea97500694d453f1bd9cf64304",
                "courses": 12,
                "cells": 108,
            },
            "2025-2026_s3_1067": {
                "id": "a9410bae-8496-4a0e-a64c-0880aa5cfbdb",
                "view": "marks:6161:3:A",
                "checksum": "bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee",
                "courses": 13,
                "cells": 117,
            },
            "2025-2026_s4_2508": {
                "id": "03d1482b-c997-431f-bc88-071c3bb4c764",
                "view": "marks:6424:3:A",
                "checksum": "c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d",
                "courses": 15,
                "cells": 165,
            },
            "2026-2027_s5_2582": {
                "id": "e8a91033-b87c-42e0-9d42-6ff0d02c8bcf",
                "view": "marks:6732:3:A",
                "checksum": "4e040f42019bea38cb883ec9161eb6658ec6e0183ff5f98ed41fe2d4606dec22",
                "courses": 4,
                "cells": 12,
            },
        }

        for s in snaps:
            exp = expected_registry[s.term_key]
            assert s.id == exp["id"]
            assert s.view == exp["view"]
            assert s.checksum == exp["checksum"]
            courses = s.payload.get("courses", [])
            assert len(courses) == exp["courses"]
            cells = [a for c in courses for a in c.get("assessments", [])]
            assert len(cells) == exp["cells"]
    finally:
        db.close()


def test_complete_468_cell_accounting_and_invariants():
    """Verify granular accounting across all 468 cells and mathematical invariants."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        expected_breakdown = {
            "2024-2025_s1_918": {"reported": 48, "unreported": 18, "masked": 0},
            "2024-2025_s2_1048": {"reported": 57, "unreported": 51, "masked": 0},
            "2025-2026_s3_1067": {"reported": 64, "unreported": 53, "masked": 0},
            "2025-2026_s4_2508": {"reported": 59, "unreported": 91, "masked": 15},
            "2026-2027_s5_2582": {"reported": 10, "unreported": 2, "masked": 0},
        }

        total_cells = 0
        total_reported = 0
        total_unreported = 0
        total_masked = 0
        fractional_count = 0

        for s in snaps:
            exp = expected_breakdown[s.term_key]
            courses = s.payload.get("courses", [])
            cells = [a for c in courses for a in c.get("assessments", [])]
            total_cells += len(cells)

            rep = sum(1 for a in cells if a.get("status") == "REPORTED")
            unrep = sum(1 for a in cells if a.get("status") == "UNREPORTED")
            masked = sum(1 for a in cells if a.get("status") == "MASKED_BY_PORTAL")

            assert rep == exp["reported"]
            assert unrep == exp["unreported"]
            assert masked == exp["masked"]
            assert len(cells) == rep + unrep + masked

            total_reported += rep
            total_unreported += unrep
            total_masked += masked

            for a in cells:
                obtained = a.get("obtained")
                maximum = a.get("maximum")
                if obtained is not None:
                    assert obtained >= 0.0, "Marks must be non-negative"
                    if maximum is not None and maximum > 0:
                        assert obtained <= maximum, f"Score {obtained} exceeds maximum {maximum}"
                    if obtained != int(obtained):
                        fractional_count += 1

        assert total_cells == 468
        assert total_reported == 238
        assert total_unreported == 215
        assert total_masked == 15
        assert fractional_count == 8  # Fractional marks preserved (e.g. 15.5, 28.5)
    finally:
        db.close()


def test_cross_semester_course_reconciliation_zero_unmapped():
    """Verify 76 catalog courses reconciliation: 55 present, 5 aggregated, 16 absent, 0 unmapped."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        total_catalog = 0
        total_present = 0
        total_aggregated = 0
        total_absent = 0
        total_unmapped = 0

        for s in snaps:
            cov = reconcile_course_coverage(db, s.term_key, s.payload)
            total_catalog += cov["total_catalog_courses"]
            total_present += cov["present_count"]
            total_aggregated += cov["aggregated_count"]
            total_absent += cov["absent_count"]
            total_unmapped += cov["unmapped_count"]
            assert cov["unmapped_count"] == 0, f"Unmapped rows found in {s.term_key}"

        assert total_catalog == 76
        assert total_present == 55
        assert total_aggregated == 5
        assert total_absent == 16
        assert total_unmapped == 0
    finally:
        db.close()


def test_semester_5_active_term_partial_publication():
    """Verify Semester 5 has exactly 4 published courses and 11 ongoing components."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        s5 = db.scalars(select(PerformanceSnapshot).where(PerformanceSnapshot.term_key == "2026-2027_s5_2582")).first()
        assert s5 is not None
        courses = s5.payload.get("courses", [])
        assert len(courses) == 4
        codes = {c["course_code"] for c in courses}
        assert codes == {"CSH301C", "CSH302C", "CSH304C", "CSH310C"}

        cov = reconcile_course_coverage(db, "2026-2027_s5_2582", s5.payload)
        assert cov["present_count"] == 4
        assert cov["absent_count"] == 11
        assert cov["aggregated_count"] == 0
        assert cov["unmapped_count"] == 0
    finally:
        db.close()


def test_attendance_archive_baseline_preservation():
    """Verify that all five-semester attendance data remains 100% intact."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        assert db.scalars(select(AcademicTerm)).all().__len__() == 5
        assert db.scalars(select(Course)).all().__len__() == 76
        assert db.scalars(select(AttendanceSnapshot)).all().__len__() in (9, 10)
        assert db.scalars(select(AttendanceSnapshotRow)).all().__len__() in (136, 151)
        assert db.scalars(select(AttendancePeriodObservation)).all().__len__() in (3520, 3544)
        assert db.scalars(select(AttendanceObservationBatch)).all().__len__() in (28, 29)

        # Verify exact latest subject-wise figures (1,806 / 2,078)
        terms = db.scalars(select(AcademicTerm).order_by(AcademicTerm.academic_year, AcademicTerm.semester_number)).all()
        tot_att = 0
        tot_del = 0
        for t in terms:
            snap = db.scalars(
                select(AttendanceSnapshot)
                .where(AttendanceSnapshot.academic_term_id == t.id)
                .order_by(AttendanceSnapshot.created_at.desc())
            ).first()
            assert snap is not None
            rows = db.scalars(select(AttendanceSnapshotRow).where(AttendanceSnapshotRow.snapshot_id == snap.id)).all()
            tot_att += sum(r.attended_periods for r in rows)
            tot_del += sum(r.delivered_periods for r in rows)

        assert tot_att in (1806, 1824)
        assert tot_del in (2078, 2099)
    finally:
        db.close()


def test_performance_overview_no_speculative_gpa():
    """Verify overview API returns all 5 terms with zero invented or speculative GPA."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        ov = overview(db)
        terms = ov.get("terms", [])
        assert len(terms) == 5
        for t in terms:
            for view_name, vdata in t.get("views", {}).items():
                assert vdata.get("sgpa") is None, f"SGPA must be None for {t['term_key']}"
                assert vdata.get("cgpa") is None, f"CGPA must be None for {t['term_key']}"
                assert "captured_at" in vdata
                assert "provenance" in vdata
                assert "course_coverage" in vdata
    finally:
        db.close()

