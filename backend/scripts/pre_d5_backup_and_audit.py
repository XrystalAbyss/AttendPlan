import sqlite3
import os
import json
from datetime import datetime
from app.db.session import get_default_db_path

def run_pre_d5_audit():
    db_path = get_default_db_path()
    print(f"Active DB path: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchall()
    print(f"Integrity check: {integrity}")

    cur.execute("PRAGMA foreign_key_check;")
    fk_check = cur.fetchall()
    print(f"FK check: {len(fk_check)} violations")

    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"attendplan_pre_phase_d5_backup_{ts}.sqlite3")

    bck_conn = sqlite3.connect(backup_file)
    with bck_conn:
        conn.backup(bck_conn)
    bck_conn.close()

    size = os.path.getsize(backup_file)
    print(f"WAL-safe backup created at: {backup_file} ({size} bytes)")

    v_conn = sqlite3.connect(backup_file)
    v_cur = v_conn.cursor()
    v_cur.execute("PRAGMA integrity_check;")
    bck_integrity = v_cur.fetchall()
    v_cur.execute("PRAGMA foreign_key_check;")
    bck_fk = v_cur.fetchall()
    v_conn.close()
    print(f"Backup verification: integrity={bck_integrity}, fk_violations={len(bck_fk)}")

    # Audit term-by-term baseline
    terms = cur.execute(
        "SELECT id, academic_year, semester_number, class_identifier FROM academic_terms ORDER BY semester_number"
    ).fetchall()

    term_stats = []
    for term_id, year, sem, class_id in terms:
        courses = cur.execute(
            "SELECT count(*), count(DISTINCT course_code) FROM courses WHERE academic_term_id = ?",
            (term_id,)
        ).fetchone()

        snapshots = cur.execute(
            "SELECT count(*), max(captured_at) FROM attendance_snapshots WHERE academic_term_id = ?",
            (term_id,)
        ).fetchone()

        latest_snap = cur.execute(
            "SELECT id FROM attendance_snapshots WHERE academic_term_id = ? ORDER BY captured_at DESC LIMIT 1",
            (term_id,)
        ).fetchone()

        snap_att, snap_del = 0, 0
        if latest_snap:
            totals = cur.execute(
                "SELECT sum(attended_periods), sum(delivered_periods) FROM attendance_snapshot_rows WHERE snapshot_id = ?",
                (latest_snap[0],)
            ).fetchone()
            snap_att = totals[0] or 0
            snap_del = totals[1] or 0

        batches = cur.execute(
            "SELECT count(*), count(DISTINCT content_checksum) FROM attendance_observation_batches WHERE academic_term_id = ?",
            (term_id,)
        ).fetchone()

        raw_obs = cur.execute(
            """
            SELECT count(o.id), sum(o.attended_period_count), sum(o.delivered_period_count)
            FROM attendance_period_observations o
            JOIN attendance_observation_batches b ON o.observation_batch_id = b.id
            WHERE b.academic_term_id = ?
            """,
            (term_id,)
        ).fetchone()

        # Effective unique observations (by date, slot, and course_id)
        effective_obs = cur.execute(
            """
            SELECT count(DISTINCT o.attendance_date || '|' || coalesce(o.slot_start_time, '') || '|' || coalesce(o.source_period_identifier, '') || '|' || coalesce(o.course_id, 'NONE')),
                   count(DISTINCT o.attendance_date)
            FROM attendance_period_observations o
            JOIN attendance_observation_batches b ON o.observation_batch_id = b.id
            WHERE b.academic_term_id = ?
            """,
            (term_id,)
        ).fetchone()

        marks = cur.execute(
            "SELECT count(*) FROM performance_snapshots WHERE term_key LIKE ?",
            (f"%s{sem}%",)
        ).fetchone()

        term_stats.append({
            "term_id": term_id,
            "year": year,
            "sem": sem,
            "class_identifier": class_id,
            "total_courses": courses[0],
            "unique_codes": courses[1],
            "snapshots_count": snapshots[0],
            "latest_snapshot_totals": f"{snap_att}/{snap_del}",
            "batches_count": batches[0],
            "unique_batch_checksums": batches[1],
            "raw_observations": raw_obs[0] or 0,
            "raw_obs_att_del": f"{raw_obs[1] or 0}/{raw_obs[2] or 0}",
            "distinct_date_slot_course_combos": effective_obs[0] or 0,
            "distinct_dates": effective_obs[1] or 0,
            "marks_count": marks[0] or 0
        })

    print("\n--- BASELINE SANITIZED TERM SUMMARY ---")
    print(json.dumps(term_stats, indent=2))

if __name__ == "__main__":
    run_pre_d5_audit()

