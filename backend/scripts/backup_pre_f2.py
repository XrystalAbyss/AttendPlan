"""Pre-F.2 WAL-safe SQLite database backup and verification script."""
import datetime
import shutil
import sqlite3
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import get_default_db_path

def main():
    db_path = get_default_db_path()
    if not db_path.exists():
        print(f"ERROR: Database file {db_path} does not exist!")
        return 1

    print(f"Source Database: {db_path}")

    # Check database integrity first
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check")
    integrity = cur.fetchall()
    print(f"Integrity check: {integrity}")
    cur.execute("PRAGMA foreign_key_check")
    fk_check = cur.fetchall()
    print(f"Foreign key check: {fk_check}")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Found {len(tables)} tables:")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM \"{t}\"")
        cnt = cur.fetchone()[0]
        print(f"  {t}: {cnt} rows")

    # Perform WAL-safe backup using SQLite Online Backup API
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"attendplan_pre_phase_f2_backup_{timestamp}.sqlite3"

    print(f"\nPerforming WAL-safe backup to: {backup_path}")
    backup_conn = sqlite3.connect(backup_path)
    with backup_conn:
        conn.backup(backup_conn, pages=100)
    backup_conn.close()
    conn.close()

    # Verify backup
    b_conn = sqlite3.connect(backup_path)
    b_cur = b_conn.cursor()
    b_cur.execute("PRAGMA integrity_check")
    b_integrity = b_cur.fetchall()
    b_cur.execute("SELECT COUNT(*) FROM courses")
    courses_count = b_cur.fetchone()[0]
    b_cur.execute("SELECT COUNT(*) FROM performance_snapshots")
    perf_count = b_cur.fetchone()[0]
    b_conn.close()

    size = backup_path.stat().st_size
    print(f"Backup verified: integrity={b_integrity}, size={size:,} bytes, courses={courses_count}, perf_snaps={perf_count}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

