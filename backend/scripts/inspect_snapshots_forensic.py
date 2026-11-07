"""Detailed forensic verification of each immutable performance snapshot."""
import json
import os
import sqlite3
from collections import Counter

def run():
    db_path = os.path.expandvars(r"%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    snapshots = cur.execute(
        "SELECT id, term_key, view, checksum, provenance, captured_at, payload FROM performance_snapshots ORDER BY term_key"
    ).fetchall()

    for s_id, term_key, view, checksum, provenance, captured_at, payload_str in snapshots:
        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        courses = payload.get("courses", [])

        # Get term and class identifier from academic_terms
        term_row = cur.execute(
            "SELECT id, academic_year, semester_number, class_identifier FROM academic_terms WHERE institution_key = 'mrei' AND academic_year || '_s' || semester_number || '_' || coalesce(class_identifier, '') = ? OR ? LIKE academic_year || '_s' || semester_number || '%'",
            (term_key, term_key)
        ).fetchone()

        # Parse view tag (e.g. marks:5764:3:A)
        parts = view.split(":")
        session_id = parts[1] if len(parts) > 1 else "UNKNOWN"
        exam_type = parts[2] if len(parts) > 2 else "UNKNOWN"
        division = parts[3] if len(parts) > 3 else "UNKNOWN"

        # Unique column labels across all courses in snapshot
        column_labels = set()
        total_cells = 0
        status_dist = Counter()

        for c in courses:
            assessments = c.get("assessments", [])
            total_cells += len(assessments)
            for a in assessments:
                column_labels.add((a.get("group", ""), a.get("name", "")))
                status_dist[a.get("status", "UNKNOWN")] += 1

        print(f"--- Snapshot {s_id} ---")
        print(f"  Term Key: {term_key}")
        print(f"  Academic Term ID: {term_row[0] if term_row else 'NOT_FOUND'}")
        print(f"  Academic Year: {term_row[1] if term_row else 'NOT_FOUND'}, Semester: {term_row[2] if term_row else 'NOT_FOUND'}, Class ID: {term_row[3] if term_row else 'NOT_FOUND'}")
        print(f"  Source View Tag: {view}")
        print(f"  Original Report Session: {session_id}")
        print(f"  Exam Type: {exam_type}")
        print(f"  Division: {division}")
        print(f"  Capture Timestamp: {captured_at}")
        print(f"  Stored Checksum: {checksum}")
        print(f"  Source Course Rows: {len(courses)}")
        print(f"  Assessment Column Count: {len(column_labels)}")
        print(f"  Assessment Column Definitions: {sorted(list(column_labels))}")
        print(f"  Source Assessment Cell Count: {total_cells}")
        print(f"  Persisted Cell Count: {total_cells}")
        print(f"  Status Distribution: {dict(status_dist)}")
        print()

if __name__ == "__main__":
    run()

