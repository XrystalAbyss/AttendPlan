import os
import sqlite3
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.session import get_default_db_path

db_path = get_default_db_path()
print(f"Active SQLite DB: {db_path} (exists: {db_path.exists()})")

backup_dir = db_path.parent / "backups"
backup_dir.mkdir(parents=True, exist_ok=True)
backup_file = backup_dir / "attendplan_pre_phase_d4_final_backup.sqlite3"

# 1. Connect to active DB and run integrity and FK checks
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("PRAGMA integrity_check;")
integrity = cursor.fetchall()
print(f"Pre-flight PRAGMA integrity_check: {integrity}")

cursor.execute("PRAGMA foreign_key_check;")
fk_violations = cursor.fetchall()
print(f"Pre-flight PRAGMA foreign_key_check: {len(fk_violations)} violations")

# 2. Record sanitized counts
tables = [
    "academic_terms",
    "courses",
    "attendance_snapshots",
    "attendance_snapshot_rows",
    "attendance_observation_batches",
    "attendance_period_observations",
    "sync_jobs",
    "performance_snapshots",
]

counts = {}
for t in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {t};")
        counts[t] = cursor.fetchone()[0]
    except Exception as e:
        counts[t] = f"Error: {e}"

print("Pre-flight Table Counts:")
for t, c in counts.items():
    print(f"  - {t}: {c}")

# Check Sem 4 and Sem 5 specifics
cursor.execute("""
    SELECT t.semester_number, t.academic_year, COUNT(c.id), COUNT(DISTINCT s.id)
    FROM academic_terms t
    LEFT JOIN courses c ON c.academic_term_id = t.id
    LEFT JOIN attendance_snapshots s ON s.academic_term_id = t.id
    GROUP BY t.id;
""")
term_summary = cursor.fetchall()
print("\nTerm Summary in DB:")
for row in term_summary:
    print(f"  Sem {row[0]} ({row[1]}): {row[2]} courses, {row[3]} snapshots")

# 3. Create consistent SQLite backup using backup API
print(f"\nCreating consistent backup to: {backup_file}")
bck_conn = sqlite3.connect(str(backup_file))
with bck_conn:
    conn.backup(bck_conn)
bck_conn.close()
conn.close()

# Verify backup
v_conn = sqlite3.connect(str(backup_file))
v_cursor = v_conn.cursor()
v_cursor.execute("PRAGMA integrity_check;")
b_integ = v_cursor.fetchall()
v_cursor.execute("PRAGMA foreign_key_check;")
b_fk = v_cursor.fetchall()
v_conn.close()

print(f"Backup verified! Size: {backup_file.stat().st_size} bytes")
print(f"Backup integrity: {b_integ}, FK violations: {len(b_fk)}")
