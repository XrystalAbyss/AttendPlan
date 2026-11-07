"""Forensic audit of performance snapshots in active SQLite database."""
import json
import os
import sqlite3
from collections import Counter

def forensic_audit():
    db_path = os.path.expandvars(r"%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3")
    print(f"Active DB path: {db_path}")
    print(f"File size: {os.path.getsize(db_path)} bytes")

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # 1. PRAGMA checks
    integrity = cur.execute("PRAGMA integrity_check").fetchall()
    fk_check = cur.execute("PRAGMA foreign_key_check").fetchall()
    print(f"PRAGMA integrity_check: {integrity}")
    print(f"PRAGMA foreign_key_check: {fk_check}")

    # 2. Academic terms
    terms = cur.execute(
        "SELECT id, institution_key, academic_year, semester_number, class_identifier FROM academic_terms ORDER BY academic_year, semester_number"
    ).fetchall()
    print("\nAcademic terms in database:")
    for t in terms:
        # count courses
        course_count = cur.execute("SELECT count(*) FROM courses WHERE academic_term_id = ?", (t[0],)).fetchone()[0]
        # count snapshots
        att_snap_count = cur.execute("SELECT count(*) FROM attendance_snapshots WHERE academic_term_id = ?", (t[0],)).fetchone()[0]
        obs_batch_count = cur.execute("SELECT count(*) FROM attendance_observation_batches WHERE academic_term_id = ?", (t[0],)).fetchone()[0]
        obs_count = cur.execute("SELECT count(*) FROM attendance_period_observations WHERE academic_term_id = ?", (t[0],)).fetchone()[0]
        print(f"  Term ID {t[0]}: {t[2]} Sem {t[3]} (Class {t[4]}) -> Catalog Courses: {course_count}, Att Snapshots: {att_snap_count}, Obs Batches: {obs_batch_count}, Obs: {obs_count}")

    # 3. Performance snapshots
    snapshots = cur.execute(
        "SELECT id, term_key, view, checksum, provenance, captured_at, payload FROM performance_snapshots ORDER BY term_key"
    ).fetchall()

    print(f"\nTotal Performance Snapshots: {len(snapshots)}")
    total_courses_all = 0
    total_cells_all = 0
    grand_status_counter = Counter()

    for s_id, term_key, view, checksum, provenance, captured_at, payload_json in snapshots:
        payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
        courses = payload.get("courses", [])
        total_courses_all += len(courses)

        term_cells = 0
        term_status_counter = Counter()

        print(f"\n=======================================================")
        print(f"Snapshot: {s_id}")
        print(f"Term Key: {term_key} | View: {view} | Provenance: {provenance}")
        print(f"Captured At: {captured_at}")
        print(f"Stored Checksum: {checksum}")
        print(f"Courses in Snapshot: {len(courses)}")

        course_details = []
        for c in courses:
            c_code = c.get("course_code")
            c_name = c.get("course_name")
            assessments = c.get("assessments", [])
            term_cells += len(assessments)
            for a in assessments:
                st = a.get("status", "UNKNOWN")
                term_status_counter[st] += 1
                grand_status_counter[st] += 1
            course_details.append((c_code, len(assessments)))

        total_cells_all += term_cells
        print(f"Total Assessment Cells for {term_key}: {term_cells}")
        print(f"Status distribution: {dict(term_status_counter)}")
        print(f"Courses & assessment counts: {course_details}")

    print("\n=======================================================")
    print("GRAND TOTALS ACROSS ALL 5 SNAPSHOTS IN ACTIVE DB:")
    print(f"Total Courses in Snapshots: {total_courses_all}")
    print(f"Total Assessment Cells: {total_cells_all}")
    print(f"Grand Status Distribution: {dict(grand_status_counter)}")

if __name__ == "__main__":
    forensic_audit()

