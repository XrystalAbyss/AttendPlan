"""Idempotent remediation script to bind Semester 4 day-wise observations to genuine course entities."""
import re
import sqlite3
import os
from pathlib import Path

base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
db_path = Path(base) / "AttendPlan" / "attendplan.sqlite3"

con = sqlite3.connect(str(db_path))
cur = con.cursor()

sem4_id = "53d60f23-e8ac-4077-a0ce-27e62aa311b9"

def normalize_title(t: str) -> str:
    return re.sub(r"\s*\((?:PP|PR|TH|IA)\)\s*", "", t, flags=re.I).strip().upper()

# 1. Fetch genuine 17 courses (the ones in snapshot rows)
snap_id = cur.execute(
    "SELECT id FROM attendance_snapshots WHERE academic_term_id = ?;", (sem4_id,)
).fetchone()[0]

gen_courses = cur.execute("""
    SELECT c.id, c.course_code, c.course_name, c.course_type
    FROM courses c
    JOIN attendance_snapshot_rows r ON r.course_id = c.id
    WHERE r.snapshot_id = ?;
""", (snap_id,)).fetchall()

print(f"Genuine snapshot courses found: {len(gen_courses)}")

course_lookup = {}
for cid, code, name, ctype in gen_courses:
    norm_n = normalize_title(name)
    course_lookup[(norm_n, ctype)] = cid
    course_lookup[(code, ctype)] = cid
    # Also key without type as fallback
    if norm_n not in course_lookup:
        course_lookup[norm_n] = cid
    if code not in course_lookup:
        course_lookup[code] = cid

# 2. Update observations
obs_rows = cur.execute("""
    SELECT id, source_course_label
    FROM attendance_period_observations
    WHERE academic_term_id = ? AND source_course_label IS NOT NULL;
""", (sem4_id,)).fetchall()

updated_count = 0
for oid, label in obs_rows:
    norm_lbl = normalize_title(label)
    ctype = "LAB" if "(PR)" in label else "THEORY"
    target_cid = course_lookup.get((norm_lbl, ctype)) or course_lookup.get(norm_lbl) or course_lookup.get(label)
    if target_cid:
        cur.execute(
            "UPDATE attendance_period_observations SET course_id = ?, course_mapping_confidence = 1.0 WHERE id = ?;",
            (target_cid, oid),
        )
        updated_count += 1

print(f"Updated {updated_count} observation course_id bindings.")

# 3. Delete unused placeholder courses (courses in Sem 4 with no snapshot rows)
deleted = cur.execute("""
    DELETE FROM courses
    WHERE academic_term_id = ?
      AND id NOT IN (SELECT course_id FROM attendance_snapshot_rows WHERE snapshot_id = ?);
""", (sem4_id, snap_id)).rowcount

print(f"Deleted {deleted} redundant placeholder course entities.")

# 4. PRAGMA integrity and foreign keys
con.commit()
integ = cur.execute("PRAGMA integrity_check;").fetchall()
fk = cur.execute("PRAGMA foreign_key_check;").fetchall()
print("Integrity Check:", integ)
print("Foreign Key Violations:", len(fk))

con.close()
print("Semester 4 course remediation complete!")

