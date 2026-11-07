# AttendPlan — Phase G.3: Clean Windows Machine Validation Report

**Document Reference:** `ATTENDPLAN_G3_CLEAN_WINDOWS_VALIDATION.md`  
**Phase:** G.3 Real Friends Beta, Clean-Machine Validation & Final Release Acceptance  
**Date:** 2026-11-07  
**Candidate Evaluated:** `AttendPlan-0.1.0-beta.3-Setup.exe` (SHA-256: `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5`)  
**Formal Gate Classification:** `NOT_VERIFIED_CLEAN_MACHINE (No independent VM/Sandbox on host)` / `VERIFIED_LOCAL_WINDOWS`  

---

## 1. Clean Machine Environment Assessment

Per Phase G.3 specifications, clean machine verification requires testing on an isolated Windows environment completely devoid of developer artifacts:
- No Python runtime or virtual environments.
- No Node.js or npm packages.
- No Git source control or developer repository clones.
- No VS Code or IDE configuration files.
- No developer browser profiles, cookies, or university session tokens.
- No existing `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3` database.

### Host Inspection Results:
1. **Windows Sandbox Check:** Evaluated CLI commands `WindowsSandbox`, `VBoxManage`, `vmrun`, and Hyper-V cmdlets on host `10.0.26200-SP0`. None were installed or active.
2. **Strict Invariant Adherence:** As explicitly mandated by project quality rules, AttendPlan **never fabricates verification evidence**. Because a genuinely clean virtual machine was unavailable on this workstation, this specific gate is formally classified as:
   ```
   NOT_VERIFIED_CLEAN_MACHINE (No independent VM/Sandbox on host)
   ```

---

## 2. Local Windows 11 Packaging & Installation Audit

While clean-machine isolation was constrained by host capabilities, full local runtime installation, upgrade safety, and isolated profile lifecycle tests were executed directly on Windows 11 64-bit:

### 2.1 Installation Lifecycle Verification

| Step | Test Procedure | Expected Invariant | Observed Result | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **1. User Mode Elevation** | Execute `AttendPlan-0.1.0-beta.3-Setup.exe` | No UAC elevation prompt (`PrivilegesRequired=lowest`) | Installed into `%LOCALAPPDATA%\AttendPlan\app` without elevation | **PASS** |
| **2. Start Menu Shortcut** | Inspect Start Menu & Desktop entries | Shortcut points to `%LOCALAPPDATA%\AttendPlan\app\AttendPlan.exe` | Verified correct path and working directory | **PASS** |
| **3. Clean Initialization** | Initialize with an empty database directory | Schema creates all 11 tables and stamps `f2e2_official_results` | Verified via `test_migration_safety.py` (clean DB test) | **PASS** |
| **4. In-Place Reinstall** | Run installer over existing installation | Application binaries updated; database & backups preserved | `attendplan.sqlite3` and `backups/` untouched | **PASS** |
| **5. Clean Uninstall** | Run `%LOCALAPPDATA%\AttendPlan\app\unins000.exe` | Binaries removed; user academic data preserved | `app\` directory deleted; database remains intact | **PASS** |

---

## 3. Database Migration Safety Audit (The G.2 Stamping Fix)

In Phase G.2, `init_db()` was updated to stamp `alembic_version` with `f2e2_official_results`.  
In Phase G.3, this behavior was audited and hardened against schema drift:

### Hardening Invariant:
`f2e2_official_results` must **NEVER** be stamped blindly on an incomplete or partially initialized database.

```python
HEAD_REQUIRED_TABLES = {
    "academic_terms",
    "courses",
    "attendance_snapshots",
    "attendance_snapshot_rows",
    "attendance_observation_batches",
    "attendance_period_observations",
    "ingestion_events",
    "sync_jobs",
    "performance_snapshots",
    "official_result_snapshots",
    "official_course_result_rows",
}
```

In `backend/app/db/session.py`, `init_db()` now uses SQLAlchemy's `inspect(conn)` to verify that `HEAD_REQUIRED_TABLES.issubset(existing_tables)` before executing the insert. If any head table is missing, stamping is refused.

### Automated Test Matrix (`backend/tests/test_migration_safety.py`):
1. `test_clean_db_stamps_head_revision`: Empty database -> all tables created -> stamps `f2e2_official_results` (PASS).
2. `test_partial_schema_does_not_blindly_stamp_head`: Partial database missing head tables -> stamping refused (PASS).
3. `test_older_valid_database_preserves_its_alembic_revision`: Database with existing revision `f2e1_performance_snapshots` -> revision preserved untouched (PASS).
4. `test_init_db_is_idempotent`: Multiple runs on full database -> single head revision retained (PASS).

---

## 4. Recommendations for Clean-Machine Volunteer Gate

Before distributing the installer widely, the developer should supervise the installation on a real student volunteer's personal Windows laptop following [ATTENDPLAN_G3_REAL_FRIEND_BETA.md](file:///C:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_G3_REAL_FRIEND_BETA.md).

