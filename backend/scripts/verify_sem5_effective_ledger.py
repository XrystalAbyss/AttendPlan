import sqlite3
from app.db.session import get_default_db_path

def verify_sem5_effective_ledger():
    conn = sqlite3.connect(get_default_db_path())
    cur = conn.cursor()

    term_id = cur.execute(
        "SELECT id FROM academic_terms WHERE semester_number = 5"
    ).fetchone()[0]

    # Latest batch IDs for each month:
    # Aug: 20cab324-6659-4804-8903-75ae01be7a47
    # Sep: 783331dc-1062-4f0f-b82e-41bfd95a6f5c
    # Oct: 355dfb7a-74d3-44fe-aa8f-126295a0b02c
    latest_batch_ids = [
        "20cab324-6659-4804-8903-75ae01be7a47",
        "783331dc-1062-4f0f-b82e-41bfd95a6f5c",
        "355dfb7a-74d3-44fe-aa8f-126295a0b02c"
    ]

    # Latest snapshot
    latest_snap_id = cur.execute(
        "SELECT id, captured_at FROM attendance_snapshots WHERE academic_term_id = ? ORDER BY captured_at DESC LIMIT 1",
        (term_id,)
    ).fetchone()[0]

    print(f"Latest Snapshot ID: {latest_snap_id}")

    print("\n=== SEMESTER 5 COURSE-BY-COURSE EFFECTIVE LEDGER MATCH ===")
    rows = cur.execute(
        """
        SELECT c.course_code, c.course_name,
               r.attended_periods as snap_att, r.delivered_periods as snap_del,
               coalesce(sum(o.attended_period_count), 0) as day_att,
               coalesce(sum(o.delivered_period_count), 0) as day_del
        FROM courses c
        JOIN attendance_snapshot_rows r ON r.course_id = c.id AND r.snapshot_id = ?
        LEFT JOIN attendance_period_observations o ON o.course_id = c.id
             AND o.observation_batch_id IN (?, ?, ?)
        WHERE c.academic_term_id = ?
        GROUP BY c.id
        ORDER BY c.course_code
        """,
        (latest_snap_id, *latest_batch_ids, term_id)
    ).fetchall()

    total_snap_att, total_snap_del = 0, 0
    total_day_att, total_day_del = 0, 0

    for r in rows:
        code, name, s_att, s_del, d_att, d_del = r
        total_snap_att += s_att
        total_snap_del += s_del
        total_day_att += d_att
        total_day_del += d_del
        match = "EXACT MATCH" if (s_att == d_att and s_del == d_del) else f"DIFF ({s_att - d_att:+}, {s_del - d_del:+})"
        print(f"{code:15} | {name[:30]:30} | Snap: {s_att:2}/{s_del:2} | Day: {d_att:2}/{d_del:2} | {match}")

    print("-" * 80)
    print(f"TOTALS          | Snapshot: {total_snap_att}/{total_snap_del} | Effective Daywise: {total_day_att}/{total_day_del}")

if __name__ == "__main__":
    verify_sem5_effective_ledger()

