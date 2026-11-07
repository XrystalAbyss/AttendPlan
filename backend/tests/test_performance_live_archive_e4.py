"""Unit and regression tests for AttendPlan Phase E.4 five-semester marks archive."""
from __future__ import annotations

import json
import os
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PerformanceSnapshot
from app.db.session import build_sqlite_url, create_app_engine
from app.services.performance_service import reconcile_course_coverage, overview


def get_user_db_session() -> Session | None:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        return None
    user_db_path = Path(local_app_data) / "AttendPlan" / "attendplan.sqlite3"
    if not user_db_path.exists():
        return None
    engine = create_app_engine(build_sqlite_url(user_db_path))
    return Session(engine)


def test_five_semester_snapshots_exist():
    """Verify all 5 semesters have their verified marks snapshots."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        assert len(snaps) == 5

        term_keys = [s.term_key for s in snaps]
        assert term_keys == [
            "2024-2025_s1_918",
            "2024-2025_s2_1048",
            "2025-2026_s3_1067",
            "2025-2026_s4_2508",
            "2026-2027_s5_2582",
        ]

        expected_checksums = {
            "2024-2025_s1_918": "d0bafbaefa6aa526dc05f4e1fa73c78c6bcc11ef624a8c77701232a34f23ea6c",
            "2024-2025_s2_1048": "c8110fdf0233baf2208c42c03c3e3c33e482daea97500694d453f1bd9cf64304",
            "2025-2026_s3_1067": "bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee",
            "2025-2026_s4_2508": "c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d",
            "2026-2027_s5_2582": "4e040f42019bea38cb883ec9161eb6658ec6e0183ff5f98ed41fe2d4606dec22",
        }

        for s in snaps:
            assert s.checksum == expected_checksums[s.term_key]
    finally:
        db.close()


def test_five_semester_cell_and_course_accounting():
    """Verify total course counts and assessment cells across all 5 semesters."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        expected_counts = {
            "2024-2025_s1_918": {"courses": 11, "cells": 66, "reported": 48, "unreported": 18, "masked": 0},
            "2024-2025_s2_1048": {"courses": 12, "cells": 108, "reported": 57, "unreported": 51, "masked": 0},
            "2025-2026_s3_1067": {"courses": 13, "cells": 117, "reported": 64, "unreported": 53, "masked": 0},
            "2025-2026_s4_2508": {"courses": 15, "cells": 165, "reported": 59, "unreported": 91, "masked": 15},
            "2026-2027_s5_2582": {"courses": 4, "cells": 12, "reported": 10, "unreported": 2, "masked": 0},
        }

        total_courses = 0
        total_cells = 0

        for s in snaps:
            exp = expected_counts[s.term_key]
            courses = s.payload.get("courses", [])
            assert len(courses) == exp["courses"]
            total_courses += len(courses)

            cells = [a for c in courses for a in c.get("assessments", [])]
            assert len(cells) == exp["cells"]
            total_cells += len(cells)

            rep = sum(1 for a in cells if a.get("status") == "REPORTED")
            unrep = sum(1 for a in cells if a.get("status") == "UNREPORTED")
            masked = sum(1 for a in cells if a.get("status") == "MASKED_BY_PORTAL")

            assert rep == exp["reported"]
            assert unrep == exp["unreported"]
            assert masked == exp["masked"]

        assert total_courses == 55
        assert total_cells == 468
    finally:
        db.close()


def test_five_semester_coverage_zero_unmapped():
    """Verify that catalog reconciliation yields ZERO unmapped source courses across all terms."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snaps = db.scalars(select(PerformanceSnapshot).order_by(PerformanceSnapshot.term_key)).all()
        for s in snaps:
            cov = reconcile_course_coverage(db, s.term_key, s.payload)
            assert cov["unmapped_count"] == 0, f"Found unmapped courses in {s.term_key}"
            assert cov["total_performance_courses"] == len(s.payload.get("courses", []))
    finally:
        db.close()


def test_five_semester_overview():
    """Verify overview API returns all 5 terms with performance views."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        ov = overview(db)
        terms = ov.get("terms", [])
        assert len(terms) == 5
        keys = [t["term_key"] for t in terms]
        assert "2024-2025_s1_918" in keys
        assert "2024-2025_s2_1048" in keys
        assert "2025-2026_s3_1067" in keys
        assert "2025-2026_s4_2508" in keys
        assert "2026-2027_s5_2582" in keys
    finally:
        db.close()


def test_performance_snapshots_zero_pii():
    """Verify zero student PII (roll numbers, admission numbers, names) in snapshots."""
    db = get_user_db_session()
    if db is None:
        pytest.skip("User production database not accessible")
    try:
        snaps = db.scalars(select(PerformanceSnapshot)).all()
        for s in snaps:
            raw = json.dumps(s.payload).lower()
            for pii in ["2023mru", "roll_no", "rollno", "admnum", "student_name", "father_name"]:
                assert pii not in raw, f"Possible PII leak '{pii}' in {s.term_key}"
    finally:
        db.close()
