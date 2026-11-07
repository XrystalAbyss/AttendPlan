import sqlite3
import json
from app.db.session import get_default_db_path

def inspect_archive():
    db_path = get_default_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchall()

    cur.execute("PRAGMA foreign_key_check;")
    fk_check = cur.fetchall()

    terms_data = []
    terms = cur.execute(
        "SELECT id, academic_year, semester_number, class_identifier FROM academic_terms ORDER BY semester_number"
    ).fetchall()

    for term_id, year, sem, class_ident in terms:
        # Snapshots
        snaps = cur.execute(
            """
            SELECT id, source, captured_at, reporting_start_date, reporting_end_date, record_count, content_checksum
            FROM attendance_snapshots
            WHERE academic_term_id = ?
            ORDER BY captured_at DESC
            """,
            (term_id,)
        ).fetchall()

        latest_snap_id = snaps[0][0] if snaps else None
        snapshot_rows = []
        if latest_snap_id:
            snapshot_rows = cur.execute(
                """
                SELECT c.course_code, c.course_name, r.attended_periods, r.delivered_periods
                FROM attendance_snapshot_rows r
                JOIN courses c ON r.course_id = c.id
                WHERE r.snapshot_id = ?
                ORDER BY c.course_code
                """,
                (latest_snap_id,)
            ).fetchall()

        # Observation batches
        batches = cur.execute(
            """
            SELECT id, coverage_start_date, coverage_end_date, content_checksum, status, source_filter_metadata
            FROM attendance_observation_batches
            WHERE academic_term_id = ?
            ORDER BY coverage_start_date
            """,
            (term_id,)
        ).fetchall()

        # Observations
        obs_stats = cur.execute(
            """
            SELECT count(o.id), sum(o.attended_period_count), sum(o.delivered_period_count), count(DISTINCT o.attendance_date),
                   sum(CASE WHEN o.course_id IS NULL THEN 1 ELSE 0 END)
            FROM attendance_period_observations o
            JOIN attendance_observation_batches b ON o.observation_batch_id = b.id
            WHERE b.academic_term_id = ?
            """,
            (term_id,)
        ).fetchone()

        # Marks snapshots
        marks = cur.execute(
            """
            SELECT count(*), max(captured_at)
            FROM performance_snapshots
            WHERE term_key LIKE ?
            """,
            (f"%s{sem}%",)
        ).fetchone()

        terms_data.append({
            "term_id": term_id,
            "year": year,
            "sem": sem,
            "class_identifier": class_ident,
            "snapshot_count": len(snaps),
            "latest_snapshot": snaps[0] if snaps else None,
            "course_count": len(snapshot_rows),
            "courses_total_attended": sum(c[2] for c in snapshot_rows),
            "courses_total_delivered": sum(c[3] for c in snapshot_rows),
            "courses": snapshot_rows,
            "batch_count": len(batches),
            "batches": batches,
            "total_observations": obs_stats[0] if obs_stats else 0,
            "obs_attended": obs_stats[1] if obs_stats else 0,
            "obs_delivered": obs_stats[2] if obs_stats else 0,
            "distinct_dates": obs_stats[3] if obs_stats else 0,
            "unmapped_observations": obs_stats[4] if obs_stats else 0,
            "marks_count": marks[0] if marks else 0,
        })

    summary = {
        "db_path": db_path,
        "integrity": integrity,
        "foreign_key_violations": len(fk_check),
        "terms": terms_data
    }

    print(json.dumps(summary, default=str, indent=2))

if __name__ == "__main__":
    inspect_archive()
