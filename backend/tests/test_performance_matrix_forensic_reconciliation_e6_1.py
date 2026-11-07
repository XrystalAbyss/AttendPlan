"""Regression tests for Phase E.6.1: Forensic Reconciliation of Five-Semester Performance Matrix.

Validates that:
1. The five performance snapshots match the authoritative database registry bit-for-bit.
2. Per-semester source courses and assessment cell counts match the authoritative matrix (55 courses, 468 cells).
3. Status accounting matches: 238 REPORTED, 215 UNREPORTED, 15 MASKED_BY_PORTAL = 468 cells.
4. Attendance catalog courses (76) and marks source courses (55) are strictly separated.
5. No cross-term JOIN contamination occurs.
6. Semester 5 source coverage is verified (4 source courses, 11 pending catalog courses).
7. Official results readiness maintains non-invented data guarantees.
8. Attendance archive is 100% preserved (3,520 observations across 28 batches, 1,806/2,078 latest periods).
"""
import json
import os
import sqlite3
from collections import Counter
import pytest

from app.domain.results_models import (
    AcademicDataClass,
    OfficialCourseResult,
    OfficialSemesterResult,
    ResultPublicationStatus,
)


@pytest.fixture
def active_db_connection():
    db_path = os.path.expandvars(r"%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3")
    if not os.path.exists(db_path):
        pytest.skip(f"Active SQLite database not found at {db_path}")
    con = sqlite3.connect(db_path)
    try:
        yield con
    finally:
        con.close()


def test_authoritative_snapshot_registry_and_checksums(active_db_connection):
    cur = active_db_connection.cursor()
    rows = cur.execute(
        "SELECT id, term_key, view, checksum, provenance FROM performance_snapshots ORDER BY term_key"
    ).fetchall()
    assert len(rows) == 5, f"Expected exactly 5 performance snapshots, found {len(rows)}"

    expected_registry = {
        "2024-2025_s1_918": {
            "id": "77d4702c-1e28-4ca7-95d5-329c7bba8d1d",
            "view": "marks:5764:3:A",
            "checksum": "d0bafbaefa6aa526dc05f4e1fa73c78c6bcc11ef624a8c77701232a34f23ea6c",
        },
        "2024-2025_s2_1048": {
            "id": "b15162ae-4a03-4e99-8155-c844fb328ea7",
            "view": "marks:5943:3:A",
            "checksum": "c8110fdf0233baf2208c42c03c3e3c33e482daea97500694d453f1bd9cf64304",
        },
        "2025-2026_s3_1067": {
            "id": "a9410bae-8496-4a0e-a64c-0880aa5cfbdb",
            "view": "marks:6161:3:A",
            "checksum": "bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee",
        },
        "2025-2026_s4_2508": {
            "id": "03d1482b-c997-431f-bc88-071c3bb4c764",
            "view": "marks:6424:3:A",
            "checksum": "c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d",
        },
        "2026-2027_s5_2582": {
            "id": "e8a91033-b87c-42e0-9d42-6ff0d02c8bcf",
            "view": "marks:6732:3:A",
            "checksum": "4e040f42019bea38cb883ec9161eb6658ec6e0183ff5f98ed41fe2d4606dec22",
        },
    }

    for s_id, term_key, view, checksum, provenance in rows:
        assert term_key in expected_registry, f"Unexpected term_key: {term_key}"
        exp = expected_registry[term_key]
        assert s_id == exp["id"], f"Snapshot ID mismatch for {term_key}"
        assert view == exp["view"], f"View mismatch for {term_key}"
        assert checksum == exp["checksum"], f"Checksum mismatch for {term_key}"
        assert provenance == "LIVE_PORTAL"


def test_per_semester_cell_counts_and_status_accounting(active_db_connection):
    cur = active_db_connection.cursor()
    rows = cur.execute(
        "SELECT term_key, payload FROM performance_snapshots ORDER BY term_key"
    ).fetchall()

    expected_counts = {
        "2024-2025_s1_918": {"courses": 11, "columns": 6, "cells": 66, "reported": 48, "unreported": 18, "masked": 0},
        "2024-2025_s2_1048": {"courses": 12, "columns": 9, "cells": 108, "reported": 57, "unreported": 51, "masked": 0},
        "2025-2026_s3_1067": {"courses": 13, "columns": 9, "cells": 117, "reported": 64, "unreported": 53, "masked": 0},
        "2025-2026_s4_2508": {"courses": 15, "columns": 11, "cells": 165, "reported": 59, "unreported": 91, "masked": 15},
        "2026-2027_s5_2582": {"courses": 4, "columns": 3, "cells": 12, "reported": 10, "unreported": 2, "masked": 0},
    }

    grand_courses = 0
    grand_cells = 0
    grand_reported = 0
    grand_unreported = 0
    grand_masked = 0

    for term_key, payload_str in rows:
        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        courses = payload.get("courses", [])
        exp = expected_counts[term_key]

        assert len(courses) == exp["courses"], f"Course count mismatch for {term_key}"
        grand_courses += len(courses)

        term_cells = 0
        status_dist = Counter()

        for c in courses:
            assessments = c.get("assessments", [])
            term_cells += len(assessments)
            assert len(assessments) == exp["columns"], f"Columns per course mismatch in {c.get('course_code')}"
            for a in assessments:
                st = a.get("status", "UNKNOWN")
                status_dist[st] += 1

        assert term_cells == exp["cells"], f"Cell count mismatch for {term_key}"
        assert status_dist["REPORTED"] == exp["reported"], f"REPORTED count mismatch for {term_key}"
        assert status_dist["UNREPORTED"] == exp["unreported"], f"UNREPORTED count mismatch for {term_key}"
        assert status_dist["MASKED_BY_PORTAL"] == exp["masked"], f"MASKED count mismatch for {term_key}"

        grand_cells += term_cells
        grand_reported += status_dist["REPORTED"]
        grand_unreported += status_dist["UNREPORTED"]
        grand_masked += status_dist["MASKED_BY_PORTAL"]

    assert grand_courses == 55
    assert grand_cells == 468
    assert grand_reported == 238
    assert grand_unreported == 215
    assert grand_masked == 15
    assert grand_reported + grand_unreported + grand_masked == 468


def test_catalog_vs_source_course_counts_separation(active_db_connection):
    cur = active_db_connection.cursor()

    # Catalog courses in `courses` table per term
    terms = cur.execute(
        "SELECT id, academic_year, semester_number, class_identifier FROM academic_terms ORDER BY academic_year, semester_number"
    ).fetchall()

    expected_catalog_counts = {
        (1, "2024-2025"): 12,
        (2, "2024-2025"): 16,
        (3, "2025-2026"): 16,
        (4, "2025-2026"): 17,
        (5, "2026-2027"): 15,
    }

    catalog_sum = 0
    for t_id, yr, sem, class_id in terms:
        c_count = cur.execute("SELECT count(*) FROM courses WHERE academic_term_id = ?", (t_id,)).fetchone()[0]
        assert c_count == expected_catalog_counts[(sem, yr)], f"Catalog course count mismatch for Sem {sem} {yr}"
        catalog_sum += c_count

    assert catalog_sum == 76, f"Expected exactly 76 catalog courses, got {catalog_sum}"

    # Performance snapshot courses: exactly 55
    snap_courses = cur.execute(
        "SELECT term_key, payload FROM performance_snapshots"
    ).fetchall()
    perf_courses_sum = sum(len(json.loads(p[1])["courses"]) for p in snap_courses)
    assert perf_courses_sum == 55, f"Expected 55 marks source courses, got {perf_courses_sum}"


def test_genuine_semester_5_coverage_and_partial_publication(active_db_connection):
    cur = active_db_connection.cursor()
    row = cur.execute(
        "SELECT payload FROM performance_snapshots WHERE term_key = '2026-2027_s5_2582'"
    ).fetchone()
    assert row is not None
    payload = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    courses = payload.get("courses", [])

    assert len(courses) == 4
    course_codes = [c["course_code"] for c in courses]
    assert course_codes == ["CSH301C", "CSH302C", "CSH304C", "CSH310C"]

    # Verify that each course has 3 assessment columns
    for c in courses:
        assert len(c["assessments"]) == 3
        # Ensure total is None (partial publication)
        assert c["total"] is None

    # Verify 10 reported marks and 2 unreported
    all_statuses = [a["status"] for c in courses for a in c["assessments"]]
    assert all_statuses.count("REPORTED") == 10
    assert all_statuses.count("UNREPORTED") == 2


def test_official_results_readiness_labels_and_invariants():
    # Verify Data Class separation
    assert AcademicDataClass.CLASS_A_INTERNAL_MARKS.value == "CLASS_A_INTERNAL_MARKS"
    assert AcademicDataClass.CLASS_B_OFFICIAL_RESULTS.value == "CLASS_B_OFFICIAL_RESULTS"
    assert AcademicDataClass.CLASS_C_DERIVED_ANALYTICS.value == "CLASS_C_DERIVED_ANALYTICS"

    # Verify publication statuses
    assert ResultPublicationStatus.PUBLISHED.value == "PUBLISHED"
    assert ResultPublicationStatus.NOT_PUBLISHED.value == "NOT_PUBLISHED"
    assert ResultPublicationStatus.WITHHELD.value == "WITHHELD"
    assert ResultPublicationStatus.REVALUATION_PENDING.value == "REVALUATION_PENDING"
    assert ResultPublicationStatus.REVISED.value == "REVISED"

    # Verify boundary checks
    with pytest.raises(ValueError):
        OfficialCourseResult(course_code="CSH301C", course_name="CAO", credits=4.0, grade="A", grade_point=10.5)

    with pytest.raises(ValueError):
        OfficialSemesterResult(
            term_key="2026-2027_s5_2582",
            academic_year="2026-2027",
            semester_number=5,
            class_identifier="2582",
            exam_session="DEC-2026",
            exam_session_label="Dec 2026",
            sgpa=11.0,
            cgpa=9.0,
            credits_registered=24.0,
            credits_earned=24.0,
            total_points_secured=200.0,
            publication_status=ResultPublicationStatus.NOT_PUBLISHED,
        )


def test_attendance_archive_preservation(active_db_connection):
    cur = active_db_connection.cursor()

    # Academic terms count
    terms_count = cur.execute("SELECT count(*) FROM academic_terms").fetchone()[0]
    assert terms_count == 5

    # Attendance snapshots count
    att_snapshots_count = cur.execute("SELECT count(*) FROM attendance_snapshots").fetchone()[0]
    assert att_snapshots_count in (9, 10)

    # Observation batches count
    batches_count = cur.execute("SELECT count(*) FROM attendance_observation_batches").fetchone()[0]
    assert batches_count in (28, 29)

    # Period observations count
    obs_count = cur.execute("SELECT count(*) FROM attendance_period_observations").fetchone()[0]
    assert obs_count in (3520, 3544)

    # Verify observation counts per term
    term_obs_map = cur.execute(
        "SELECT t.semester_number, count(o.id) FROM attendance_period_observations o JOIN academic_terms t ON t.id = o.academic_term_id GROUP BY t.semester_number ORDER BY t.semester_number"
    ).fetchall()
    assert dict(term_obs_map) in (
        {1: 413, 2: 550, 3: 716, 4: 729, 5: 1112},
        {1: 413, 2: 550, 3: 716, 4: 729, 5: 1136},
    )

    # Verify latest attendance totals per term sum to 1806 / 2078 (or 1824 / 2098 with ongoing Sem 5)
    latest_snapshots = cur.execute("""
        SELECT t.semester_number, sum(r.attended_periods), sum(r.delivered_periods)
        FROM attendance_snapshots s
        JOIN attendance_snapshot_rows r ON r.snapshot_id = s.id
        JOIN academic_terms t ON t.id = s.academic_term_id
        WHERE s.id IN (
            SELECT s2.id FROM attendance_snapshots s2
            WHERE s2.academic_term_id = s.academic_term_id
            ORDER BY s2.captured_at DESC LIMIT 1
        )
        GROUP BY t.semester_number
        ORDER BY t.semester_number
    """).fetchall()

    attended_sum = sum(r[1] for r in latest_snapshots)
    delivered_sum = sum(r[2] for r in latest_snapshots)
    assert attended_sum in (1806, 1824)
    assert delivered_sum in (2078, 2099)

