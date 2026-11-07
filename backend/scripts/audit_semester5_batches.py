import sqlite3
import json
from app.db.session import get_default_db_path

def audit_sem5():
    conn = sqlite3.connect(get_default_db_path())
    cur = conn.cursor()

    term_id = cur.execute(
        "SELECT id FROM academic_terms WHERE semester_number = 5"
    ).fetchone()[0]

    batches = cur.execute(
        """
        SELECT id, source, observed_at, coverage_start_date, coverage_end_date,
               source_filter_metadata, content_checksum, status, created_at
        FROM attendance_observation_batches
        WHERE academic_term_id = ?
        ORDER BY created_at ASC
        """,
        (term_id,)
    ).fetchall()

    print(f"=== SEMESTER 5 BATCHES ({len(batches)}) ===")
    for b in batches:
        b_id, src, obs_at, s_date, e_date, meta, csum, status, created = b
        obs = cur.execute(
            """
            SELECT count(*), sum(attended_period_count), sum(delivered_period_count),
                   min(attendance_date), max(attendance_date), count(DISTINCT attendance_date)
            FROM attendance_period_observations
            WHERE observation_batch_id = ?
            """,
            (b_id,)
        ).fetchone()

        status_counts = cur.execute(
            """
            SELECT status, count(*)
            FROM attendance_period_observations
            WHERE observation_batch_id = ?
            GROUP BY status
            """,
            (b_id,)
        ).fetchall()

        print(f"\nBatch ID: {b_id}")
        print(f"  Created: {created} | Observed: {obs_at} | Range: {s_date} to {e_date}")
        print(f"  Meta: {meta} | Status: {status} | Checksum: {csum[:12]}...")
        print(f"  Obs count: {obs[0]} | Attended: {obs[1]} | Delivered: {obs[2]}")
        print(f"  Dates: {obs[3]} to {obs[4]} ({obs[5]} distinct days)")
        print(f"  Status breakdown: {status_counts}")

if __name__ == "__main__":
    audit_sem5()

