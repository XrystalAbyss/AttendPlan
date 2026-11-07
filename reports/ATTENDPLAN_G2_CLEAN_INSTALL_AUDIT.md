# AttendPlan — Phase G.2: Clean Installation & Upgrade Audit

**Document Reference:** `ATTENDPLAN_G2_CLEAN_INSTALL_AUDIT.md`  
**Phase:** G.2 Supervised Friends Beta & Release Hardening  
**Date:** 2026-11-07  
**Build Target:** `AttendPlan-0.1.0-beta.2-Setup.exe`  
**Classification:** `VERIFIED_WINDOWS_RUNTIME` / `NOT_VERIFIED_CLEAN_MACHINE` (No standalone VM available)  

---

## 1. Audit Methodology & Scope

To ensure AttendPlan installs, upgrades, and uninstalls cleanly on student Windows systems without corrupting existing data or leaving orphaned artifacts:
1. **Host Environment Assessment:**
   - Operating System: Windows 11 Pro 64-bit (`10.0.26200-SP0`).
   - Virtual Machine / Sandbox Availability: Windows Sandbox and Hyper-V/VirtualBox CLI tools are not available on this developer workstation.
   - Formal Compliance Classification: Per engineering rules, because an isolated VM was not present, clean-machine verification is classified honestly as `NOT_VERIFIED_CLEAN_MACHINE (No independent VM/Sandbox on host)`. Local directory isolation and packaging validation are classified as `VERIFIED_WINDOWS_RUNTIME`.
2. **Directory Isolation Test:**
   - Verified that the installer defaults to `%LOCALAPPDATA%\AttendPlan\app` without requiring administrator privileges (`PrivilegesRequired=lowest`).
   - Verified that student user data is stored strictly in `%LOCALAPPDATA%\AttendPlan\` (`attendplan.sqlite3`, `backups/`, `logs/`, `chrome-profile/`).
3. **In-Place Upgrade Test (Beta 1 to Beta 2):**
   - Simulated upgrade from `0.1.0-beta.1` to `0.1.0-beta.2`.
   - Verified that existing SQLite database files, WAL logs, and backup files are preserved untouched across installer runs.

---

## 2. Directory Layout & Storage Topology

```
%LOCALAPPDATA%\AttendPlan\
├── app\                                # Application binaries (overwritten on upgrade)
│   ├── AttendPlan.exe                  # Packaged launcher executable
│   └── _internal\                      # Python 3.12 runtime, Playwright, React assets
├── attendplan.sqlite3                  # Student SQLite database (PRESERVED ON UPGRADE)
├── attendplan.sqlite3-wal              # SQLite Write-Ahead Log (PRESERVED ON UPGRADE)
├── attendplan.sqlite3-shm              # SQLite Shared Memory (PRESERVED ON UPGRADE)
├── backups\                            # Automatic and user-exported snapshots (PRESERVED)
│   └── attendplan_backup_*.sqlite3
├── logs\                               # Rotating runtime logs (PRESERVED)
│   └── attendplan.log
└── chrome-profile\                     # Dedicated isolated Chrome profile (PRESERVED)
```

---

## 3. Fresh User Initialization Invariants

When a student launches AttendPlan for the first time without an existing database:
1. `get_default_db_path()` creates `%LOCALAPPDATA%\AttendPlan\` if absent.
2. `init_db()` executes `Base.metadata.create_all()` creating all 11 database tables:
   - `academic_terms`
   - `courses`
   - `attendance_period_observations`
   - `attendance_sync_batches`
   - `academic_history_snapshots`
   - `day_wise_attendance_records`
   - `sync_jobs`
   - `performance_snapshots`
   - `official_semester_results`
   - `official_course_results`
   - `alembic_version`
3. Head revision stamping: `init_db()` automatically inserts `('f2e2_official_results',)` into `alembic_version`, ensuring the database is instantly compatible with all future schema migrations.
4. First-run onboarding flow is triggered in the frontend (`FirstRunOnboarding.tsx`), offering:
   - "Load Sample Data (Offline Demonstration)"
   - "Connect iCloudEMS Account (Step-by-Step Sync)"

---

## 4. Upgrade Safety Verification (Beta 1 -> Beta 2)

| Verification Check | Target Invariant | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Non-Admin Installation** | Installs into `%LOCALAPPDATA%` without UAC prompt | Confirmed (`PrivilegesRequired=lowest`) | PASS |
| **Existing Database Preservation** | Existing `attendplan.sqlite3` not touched by installer | Confirmed (Inno Setup ignores external files) | PASS |
| **Backups Preservation** | Existing `%LOCALAPPDATA%\AttendPlan\backups\` intact | Confirmed | PASS |
| **Start Menu Shortcut** | Shortcut points to `%LOCALAPPDATA%\AttendPlan\app\AttendPlan.exe` | Confirmed | PASS |
| **Uninstaller Cleanliness** | Uninstaller removes `app\` binaries; preserves user data | Confirmed | PASS |

---

## 5. Audit Recommendations for Beta Distribution

1. **Inform Students of User Mode:** Clearly state in the installation guide that AttendPlan does not require administrator rights and will not trigger a Windows UAC prompt for admin credentials.
2. **Standard SmartScreen Notice:** Because AttendPlan is packaged with an open-source development certificate rather than an expensive commercial EV Code Signing certificate, Windows Defender SmartScreen may display an "Unknown Publisher" warning. Provide explicit instructions: Click **"More info"** -> **"Run anyway"**.

