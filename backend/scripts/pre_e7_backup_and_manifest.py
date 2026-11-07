"""Generate sanitized pre-execution database inventory and create consistent WAL-safe backup for Phase E.7."""
import datetime
import json
import os
import sqlite3

def run():
    db_path = os.path.expandvars(r"%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3")
    print(f"Target active database: {db_path}")
    assert os.path.exists(db_path), f"Database not found at {db_path}"

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # 1. Integrity and Foreign Key Checks
    integrity = cur.execute("PRAGMA integrity_check").fetchall()
    fk_check = cur.execute("PRAGMA foreign_key_check").fetchall()
    assert integrity == [("ok",)], f"Integrity check failed: {integrity}"
    assert fk_check == [], f"Foreign key violations found: {fk_check}"
    print(f"Active DB Integrity: {integrity[0][0]}")
    print(f"Active DB FK Check: {len(fk_check)} violations")

    # 2. Migration version
    alembic_ver = cur.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    print(f"Alembic version: {alembic_ver}")

    # 3. Academic terms and catalog courses
    terms = cur.execute(
        "SELECT id, institution_key, academic_year, semester_number, class_identifier FROM academic_terms ORDER BY academic_year, semester_number"
    ).fetchall()
    print(f"\nAcademic Terms ({len(terms)}):")
    total_catalog_courses = 0
    term_catalog_counts = {}
    for t in terms:
        c_count = cur.execute("SELECT count(*) FROM courses WHERE academic_term_id = ?", (t[0],)).fetchone()[0]
        total_catalog_courses += c_count
        term_catalog_counts[f"{t[2]}_s{t[3]}"] = c_count
        print(f"  Term {t[0]}: {t[2]} Semester {t[3]} (Class {t[4]}) -> {c_count} catalog courses")
    print(f"Total catalog courses: {total_catalog_courses}")

    # 4. Attendance snapshots and observation batches
    att_snaps = cur.execute("SELECT count(*) FROM attendance_snapshots").fetchone()[0]
    att_batches = cur.execute("SELECT count(*) FROM attendance_observation_batches").fetchone()[0]
    att_obs = cur.execute("SELECT count(*) FROM attendance_period_observations").fetchone()[0]
    print(f"\nAttendance Baseline:")
    print(f"  Attendance Snapshots: {att_snaps}")
    print(f"  Observation Batches: {att_batches}")
    print(f"  Period Observations: {att_obs}")

    # 5. Performance snapshots (Class A Internal Marks)
    perf_snaps = cur.execute(
        "SELECT id, term_key, view, checksum, provenance, captured_at, payload FROM performance_snapshots ORDER BY term_key"
    ).fetchall()
    print(f"\nInternal Marks Performance Snapshots ({len(perf_snaps)}):")
    total_perf_courses = 0
    total_perf_cells = 0
    perf_status_dist = {}
    for s_id, term_key, view, checksum, provenance, captured_at, payload_str in perf_snaps:
        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        courses = payload.get("courses", [])
        total_perf_courses += len(courses)
        cells = sum(len(c.get("assessments", [])) for c in courses)
        total_perf_cells += cells
        for c in courses:
            for a in c.get("assessments", []):
                st = a.get("status", "UNKNOWN")
                perf_status_dist[st] = perf_status_dist.get(st, 0) + 1
        print(f"  {term_key} ({s_id}): view={view}, courses={len(courses)}, cells={cells}, checksum={checksum[:16]}...")
    print(f"Total Performance Courses: {total_perf_courses}")
    print(f"Total Assessment Cells: {total_perf_cells}")
    print(f"Status Distribution: {perf_status_dist}")

    # 6. Checkpoints in SyncJobs
    sync_jobs_count = cur.execute("SELECT count(*) FROM sync_jobs").fetchone()[0]
    print(f"\nSync Jobs Count: {sync_jobs_count}")

    # 7. Create WAL-safe online backup
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.expandvars(r"%LOCALAPPDATA%\AttendPlan\backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"attendplan_pre_phase_e7_backup_{timestamp}.sqlite3")

    con_dst = sqlite3.connect(backup_path)
    con.backup(con_dst)
    con_dst.close()
    con.close()

    print(f"\nBackup successfully created: {backup_path}")
    print(f"Backup file size: {os.path.getsize(backup_path)} bytes")

    # 8. Verify the backup independently
    con_chk = sqlite3.connect(backup_path)
    chk_integrity = con_chk.execute("PRAGMA integrity_check").fetchall()
    chk_fk = con_chk.execute("PRAGMA foreign_key_check").fetchall()
    con_chk.close()
    assert chk_integrity == [("ok",)], f"Backup integrity check failed: {chk_integrity}"
    assert chk_fk == [], f"Backup foreign key violations: {chk_fk}"
    print(f"Backup verification: PRAGMA integrity_check = {chk_integrity[0][0]}, PRAGMA foreign_key_check = {chk_fk}")

    # Write sanitized pre-execution manifest
    manifest = {
        "timestamp": datetime.datetime.now().isoformat(),
        "database_path": db_path,
        "backup_path": backup_path,
        "alembic_version": alembic_ver,
        "academic_terms_count": len(terms),
        "total_catalog_courses": total_catalog_courses,
        "attendance_snapshots_count": att_snaps,
        "observation_batches_count": att_batches,
        "period_observations_count": att_obs,
        "performance_snapshots_count": len(perf_snaps),
        "performance_courses_count": total_perf_courses,
        "performance_assessment_cells": total_perf_cells,
        "status_distribution": perf_status_dist,
        "sync_jobs_count": sync_jobs_count,
    }
    with open("reports/attendplan_pre_e7_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("Pre-E.7 manifest saved to reports/attendplan_pre_e7_manifest.json")

if __name__ == "__main__":
    run()
