# ATTENDPLAN — PHASE G.4.4
# WINDOWS INSTALLATION LIFECYCLE & LOCAL-LAUNCH SAFETY REPORT

- **Application:** AttendPlan
- **Target Active Release:** `0.1.0-beta.8`
- **Rollback Release:** `0.1.0-beta.7`
- **Installer Binary:** `AttendPlan-0.1.0-beta.8-Setup.exe`
- **File Size:** `81,655,495 bytes` (~77.8 MB)
- **SHA-256 Checksum:** `4e6032591c54cf7f5615beb2fd5795880b6f1f348246b9c6e46e9444b53f34cc`
- **Inno Setup AppId:** `{{C6B5E87D-1F33-4D91-8846-9D923E2A3819}}`
- **Win32 AppMutex:** `AttendPlanDesktopAppMutex`
- **Quality Status:** Fully Qualified & Verified

---

## 1. Executive Summary

Phase G.4.4 completes the permanent Windows installation lifecycle for AttendPlan, addressing every aspect of installation, upgrades, repairs, guarded uninstallation, and safe development runtime switching.

All operations strictly adhere to AttendPlan's non-negotiable principles:
1. **Local-first & privacy first**: student credentials, mobile numbers, and attendance records remain strictly on the local machine (`127.0.0.1` binding).
2. **Absolute data preservation**: existing academic databases containing 5 semesters, 76 courses, 3,584 attendance period observations, 30 batches, 12 attendance snapshots, and 5 continuous evaluation snapshots are 100% preserved and validated with `PRAGMA integrity_check = ok`.
3. **Guarded uninstallation & maintenance**: normal uninstallation preserves student data by default, and a new standalone Maintenance Utility provides storage diagnostics, consistent safety backups, cache cleanups, and guarded resets.

---

## 2. Windows Installation Lifecycle (Inno Setup 6)

### 2.1 Native Named Mutex Protection
In `backend/launcher.py`, the desktop application acquires the Win32 named mutex `AttendPlanDesktopAppMutex` upon launch using `ctypes.windll.kernel32.CreateMutexW` and releases it cleanly on exit.

`installer/attendplan_setup.iss` registers:
```iss
AppMutex=AttendPlanDesktopAppMutex
```
This guarantees that both the installer and uninstaller natively detect when AttendPlan is running and prompt the user to close active instances before file modifications occur, preventing DLL locked-file errors or corrupted runtime states.

### 2.2 In-Place Upgrades & Downgrade Prevention
In `installer/attendplan_setup.iss`, the Pascal script `InitializeSetup()` inspects the Windows user uninstall registry:
`HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{C6B5E87D-1F33-4D91-8846-9D923E2A3819}_is1`
- **Same Version (`0.1.0-beta.8`)**: Alerts the user that AttendPlan is already installed and performs a repair/reinstallation of application files while guaranteeing user records are untouched.
- **Older Version (e.g. `0.1.0-beta.7`)**: Informs the user of the detected version and seamlessly upgrades the application binaries in `{userappdata}\AttendPlan\app` in-place.
- **Newer Version**: Warns the user of potential database incompatibilities if attempting to install an older build over a newer one, allowing cancellation.

### 2.3 Guarded Uninstallation
In `InitializeUninstall()`:
- The user is explicitly asked:
  *"Do you want to keep your saved attendance records, course history, and settings? Click YES to keep your academic data for future reinstallation (Recommended). Click NO to permanently delete all local AttendPlan data."*
- If the user selects **NO**, a secondary high-severity confirmation prompt is displayed warning of permanent loss.
- In `CurUninstallStepChanged(usPostUninstall)`, user data in `%LOCALAPPDATA%\AttendPlan` is removed **only** if the user explicitly confirmed deletion through both prompts. Otherwise, `%LOCALAPPDATA%\AttendPlan` remains 100% intact.

### 2.4 Start Menu Grouping
The installer creates a dedicated application group in the Windows Start Menu:
- `AttendPlan` (`{autoprograms}\AttendPlan\AttendPlan.lnk`)
- `AttendPlan — Maintenance and Reset` (`{autoprograms}\AttendPlan\AttendPlan — Maintenance and Reset.lnk`)
- `Uninstall AttendPlan` (`{autoprograms}\AttendPlan\Uninstall AttendPlan.lnk`)
- Optional Desktop shortcut (`{autodesktop}\AttendPlan.lnk`)

---

## 3. Maintenance, Diagnostic & Storage Utility

To ensure volunteer testers and students can diagnose storage health and perform safe maintenance without requiring developer tools or command-line knowledge, Phase G.4.4 introduces:
- `scripts/AttendPlan-Maintenance.ps1`
- `installer/AttendPlan-Maintenance.cmd`
- Built-in CLI flags in `AttendPlan.exe` (`--check-db`, `--backup-db <dest>`)

### 3.1 Features of the Maintenance Utility
1. **Database Health & Integrity Check**:
   - Inspects database existence, file size, and last modified timestamp.
   - Runs `PRAGMA integrity_check` and reports term, course, observation, and snapshot counts.
   - Verifies `settings.json` presence and reports masked student mobile configuration without exposing plain text.
2. **Immediate Consistent Safety Backup**:
   - Creates a timestamped SQLite online backup (`attendplan_backup_<timestamp>.sqlite3`) in `%LOCALAPPDATA%\AttendPlan\backups\`.
   - Computes and verifies SHA-256 checksum and reports size.
3. **Clean Regenerable Caches**:
   - Safely cleans Chromium profile caches (`Cache`, `Code Cache`, `DawnGraphiteCache`, `GPUCache`) and temporary logs.
   - Explicitly preserves `attendplan.sqlite3`, `settings.json`, and historical backups.
4. **Standard Safe Uninstall**:
   - Reads the official Inno Setup uninstaller path from registry and launches it with data preservation enabled.
5. **Full Clean Reset**:
   - High-severity operation requiring the user to type `DELETE` in capital letters.
   - Automatically writes an emergency pre-reset backup to the user's Desktop (`%USERPROFILE%\Desktop\AttendPlan_Emergency_Backup_<timestamp>.sqlite3`).
   - Cleans the `%LOCALAPPDATA%\AttendPlan` directory safely.

---

## 4. Local Launcher & Safe Runtime Switching

In `scripts/Launch-AttendPlan.ps1`:
- Added parameter `[switch]$ForceSwitch = $false`.
- When port 8000 is occupied by an existing production/frozen instance of AttendPlan:
  1. Inspects PID and process details via `Get-NetTCPConnection` and `Get-Process`.
  2. Queries `/api/v1/startup/status` to inspect `active_sync` and `state`.
  3. **Strictly refuses to interrupt** if an attendance or marks sync task is actively running.
  4. Displays a clear conflict explanation (process name, PID, executable path, runtime mode, database path).
  5. In interactive sessions, prompts the user:
     `"Existing AttendPlan process is running. Shut down existing instance to start development environment? [y/N]: "`
  6. If approved, requests graceful shutdown using `X-AttendPlan-Instance` and waits up to 10 seconds for verified process termination and port release.
  7. If canceled, exits cleanly without modifying the running application.

---

## 5. Security & Settings Recovery Hardening

1. **Sanitized `/health` Endpoint**:
   - In `backend/app/api/routes.py`, removed the raw personal filesystem path (`str(get_default_db_path())`) from the unauthenticated `/health` response.
   - Replaced with `database_status: "connected"`.
   - Preserved `database_path` strictly inside the authenticated diagnostic endpoint `/api/v1/startup/status`.
2. **Settings Recovery State Machine in Frontend**:
   - In `frontend/src/components/FirstRunOnboarding.tsx`, replaced boolean flags with an explicit state machine:
     `settingsLoadState: "loading" | "saved_found" | "empty" | "unavailable"`
   - If settings cannot be read (e.g. network/port blip), renders an actionable alert banner:
     *"Local Settings Unavailable: Could not communicate with local configuration store. AttendPlan is protecting your existing setup."* with a **Retry Reading Settings** button.
   - When entering a new mobile number, `handleSaveMobile` performs a verified read-back to confirm persistent storage before advancing the wizard.

---

## 6. Verification & Quality Gates

All six quality gates passed completely:

| Quality Gate | Tool / Suite | Verdict | Details |
|---|---|---|---|
| **Python Unit & Domain** | `pytest backend/tests` | **PASS** | 360 passed, 0 failed in 33.95s |
| **Data Sanitization & Privacy** | `pytest backend/tests/test_sanitization.py` | **PASS** | 14 passed, 0 failed (zero PII in tree) |
| **Backend Code Quality** | `ruff check backend/app backend/tests` | **PASS** | All checks passed cleanly |
| **Backend Static Typing** | `mypy backend/app` | **PASS** | Success (0 issues in 46 source files) |
| **Frontend Unit & Component** | `vitest run` | **PASS** | 45 passed across 14 test files |
| **Frontend Static Typing** | `tsc --noEmit` | **PASS** | Clean compilation, 0 errors |
| **Frontend Production Build** | `vite build` | **PASS** | Production bundle built in 5.54s |
| **PyInstaller Package** | `pyinstaller attendplan.spec` | **PASS** | Self-contained Windows bundle built |
| **Inno Setup Packaging** | `ISCC attendplan_setup.iss` | **PASS** | `AttendPlan-0.1.0-beta.8-Setup.exe` built |
| **Database Parity & Health** | `PRAGMA integrity_check` | **PASS** | `ok`, 5 terms, 76 courses, 3,584 observations |

---

## 7. Artifacts & Release Manifest

- **Setup Executable:** `release-candidates\AttendPlan-0.1.0-beta.8-Setup.exe`
- **SHA-256:** `4e6032591c54cf7f5615beb2fd5795880b6f1f348246b9c6e46e9444b53f34cc`
- **Release Manifest:** `release-candidates/RELEASE_MANIFEST.json` (updated)
- **Checksum Registry:** `release-candidates/SHA256SUMS.txt` (updated)
- **Safety Database Backup:** `C:\Users\astra\AppData\Local\AttendPlan\backups\pre_g4_4_safety_backup.sqlite3`
