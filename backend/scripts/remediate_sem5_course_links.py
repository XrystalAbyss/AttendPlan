"""Idempotent remediation script to bind Semester 5 day-wise observations to official CDO331 course entity."""
import sqlite3
import os
from pathlib import Path
from app.db.session import get_default_db_path

def remediate_sem5():
    db_path = get_default_db_path()
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    cur.execute("PRAGMA foreign_keys = ON;")

    sem5_id = cur.execute(
        "SELECT id FROM academic_terms WHERE semester_number = 5;"
    ).fetchone()[0]

    # Find genuine CDO331
    cdo331_row = cur.execute(
        "SELECT id FROM courses WHERE academic_term_id = ? AND course_code = 'CDO331';",
        (sem5_id,)
    ).fetchone()

    placeholder_row = cur.execute(
        "SELECT id FROM courses WHERE academic_term_id = ? AND course_code = 'PROFESSIONAL COMPETANCY ENHANCEMENT-III (PP)';",
        (sem5_id,)
    ).fetchone()

    if not cdo331_row:
        print("Genuine CDO331 not found in Semester 5! Aborting.")
        con.close()
        return

    cdo331_id = cdo331_row[0]

    if placeholder_row:
        placeholder_id = placeholder_row[0]
        # Update observations
        updated = cur.execute(
            """
            UPDATE attendance_period_observations
            SET course_id = ?, course_mapping_confidence = 1.0
            WHERE course_id = ?;
            """,
            (cdo331_id, placeholder_id)
        ).rowcount
        print(f"Updated {updated} observations to CDO331 ({cdo331_id}).")

        # Delete placeholder
        deleted = cur.execute(
            "DELETE FROM courses WHERE id = ?;",
            (placeholder_id,)
        ).rowcount
        print(f"Deleted {deleted} placeholder course entity ({placeholder_id}).")
    else:
        print("Placeholder course already resolved or not present.")

    con.commit()

    integ = cur.execute("PRAGMA integrity_check;").fetchall()
    fk = cur.execute("PRAGMA foreign_key_check;").fetchall()
    print("Integrity Check:", integ)
    print("Foreign Key Violations:", len(fk))

    con.close()
    print("Semester 5 course remediation complete!")

if __name__ == "__main__":
    remediate_sem5()

