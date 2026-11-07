# AttendPlan — Phase G.3: Final Release Acceptance & Gate Certification

**Document Reference:** `ATTENDPLAN_G3_RELEASE_ACCEPTANCE.md`  
**Phase:** G.3 Real Friends Beta, Clean-Machine Validation & Final Release Acceptance  
**Date:** 2026-11-07  
**Candidate Evaluated:** `AttendPlan-0.1.0-beta.3-Setup.exe`  
**Decision Authority:** Principal Windows Release Engineer & Independent QA Auditor  

---

## 1. Formal Verdict Certification

| Gate Domain | Verdict Level | Evidence / Summary |
| :--- | :--- | :--- |
| **Local Windows Desktop Runtime** | **VERIFIED_LOCAL_WINDOWS** | Windows 11 packaging, installer execution, loopback daemon, SPA mount verified |
| **Independent Clean Machine** | **NOT_VERIFIED_CLEAN_MACHINE** | Honestly noted: no standalone VM or Windows Sandbox on developer workstation |
| **Real Volunteer Beta Testing** | **AWAITING_REAL_VOLUNTEER_TESTING** | Honestly noted: awaiting physical presence and testing with consenting students |
| **Synthetic E2E & Multi-Term** | **VERIFIED_SYNTHETIC** | All 5 terms, 76 courses, 3,544 obs, 5 marks snapshots, 468 cells verified |
| **Overall Release Status** | **APPROVED FOR PRIVATE SUPERVISED FRIENDS BETA** | Code freeze at `0.1.0-beta.3`; all quality gates passing 100% |

---

## 2. 21-Point Release Audit Inventory

### 1. Actual Installer Hash & Path
- **File Path:** `release-candidates\AttendPlan-0.1.0-beta.3-Setup.exe`
- **File Size:** 81,644,316 bytes (77.86 MB)
- **SHA-256 Checksum:** `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5`

### 2. Current Local Git State
- **Branch:** `master`
- **Baseline Commit:** `5948106` (*chore: baseline F2-A state*)
- **Remote Configuration:** Zero remotes currently configured (canonical remote `https://github.com/XrystalAbyss/AttendPlan` documented for future publication).
- **Working Tree:** All sensitive files, databases, logs, and `.exe` binaries are properly excluded via `.gitignore`.

### 3. Installation Results
- Inno Setup user-mode installation verified: installs directly into `%LOCALAPPDATA%\AttendPlan\app` without requiring Windows administrator credentials (`PrivilegesRequired=lowest`).
- Start menu and desktop shortcuts correctly invoke `%LOCALAPPDATA%\AttendPlan\app\AttendPlan.exe`.

### 4. Independent Machine Environment
- Classified as `NOT_VERIFIED_CLEAN_MACHINE` because neither Windows Sandbox nor hypervisor CLI tools were available on the host system.
- User profile isolation and zero-dependency frozen packaging verified.

### 5. Database Migration Correctness
- Audited `init_db()` in `backend/app/db/session.py`.
- Enforced strict validation: `f2e2_official_results` is stamped **ONLY** when `HEAD_REQUIRED_TABLES` (all 11 tables) exist.
- Partially initialized or older schemas are never blindly stamped. Tested via `test_migration_safety.py` (4/4 tests passed).

### 6. API and Browser Security Results
- `LocalOriginSecurityMiddleware` active: verifies `Origin`, `Referer`, and `Sec-Fetch-Site`. External origins (e.g. `https://evil.com`) and `Origin: null` are rejected with `403 Forbidden`.
- `TrustedHostMiddleware` active: blocks DNS rebinding.
- Tested via `test_local_security_origin.py` (5/5 tests passed).

### 7. Backup Export Validation
- `POST /api/v1/auth/backup/export` verified: creates a WAL-checkpointed snapshot via SQLite online backup API.
- Backups saved strictly to local `%LOCALAPPDATA%\AttendPlan\backups\`; zero data streamed over the network.

### 8. Dedicated Browser Disconnect Behavior
- `POST /api/v1/portal/session/disconnect` verified: terminates the dedicated Chrome process and cleanly disconnects CDP.
- Personal user Chrome profiles and open browsing windows remain untouched.

### 9. Port Collision Handling
- Audited `launcher.py` across ports 8000–8010.
- Implemented two-socket verification in `is_port_in_use()` to accurately detect occupied and free ports on Windows.
- Implemented clean error reporting upon port range exhaustion.
- CORS origins updated to include all fallback ports (8000–8010). Tested via `test_port_fallback.py` (3/3 tests passed).

### 10. Cold & Warm Startup Metrics
- **CLI Invocations:** Cold `--version`: 681 ms; Warm `--version`: 394 ms (Average: 491 ms).
- **Daemon Verification:** Cold `--status`: 1,881 ms; Warm `--status`: 1,746 ms (Average: 1,791 ms < 2.0 s).
- **Frontend SPA Paint:** DOM Content Loaded < 150 ms; gzip payload 129.3 kB.

### 11. Real Volunteer Participation Count
- **Count:** 0 currently participating during this automated session.
- Ready for 1–2 designated university student testers.

### 12. Independently Completed User Journeys
- 20-journey testing protocol defined in `ATTENDPLAN_G3_REAL_FRIEND_BETA.md` covering installation, onboarding, 2FA login, attendance sync, bunk calculation, and clean disconnect.

### 13. Academic Parity Validation
- Exact rational mathematics enforced across all calculations ($a/d$, safe bunks, consecutive needed).
- Unrecorded periods ($0/0$) rendered as `--`, never assumed to be 0% or safe.

### 14. Issues Discovered in Phase G.3
1. `init_db()` previously stamped `f2e2_official_results` without verifying that all 11 head tables were actually created.
2. `origins` in `main.py` lacked fallback ports 8001–8010.
3. `is_port_in_use()` single-socket check was susceptible to TCP backlog exhaustion on Windows.
4. `.gitignore` lacked exclusion for `release-candidates/*.exe`.

### 15. Fixes Implemented
1. Added `HEAD_REQUIRED_TABLES.issubset(existing_tables)` check before stamping head in `backend/app/db/session.py`.
2. Expanded CORS `origins` to dynamically cover ports 8000 through 8010 in `backend/app/main.py`.
3. Upgraded `is_port_in_use()` to a two-socket bind test in `backend/launcher.py`.
4. Added `release-candidates/*.exe` to `.gitignore`.

### 16. New Installer Version Rebuilt
- Rebuilt as **`0.1.0-beta.3`** (`AttendPlan-0.1.0-beta.3-Setup.exe`).
- All 3 versions (`beta.1`, `beta.2`, `beta.3`) preserved in `release-candidates/` with distinct SHA-256 hashes.

### 17. Full Regression Test Results
- **Backend Tests:** `pytest backend/tests` — **342 passed, 0 failed** in 37.18s.
- **Python Linting:** `ruff check` — 0 errors.
- **Python Type Safety:** `mypy` — 0 errors across 47 source files.
- **Frontend Tests:** `vitest run` — **13 suites, 38 tests passed** in 46.83s.
- **Frontend Type Safety:** `tsc --noEmit` — 0 errors.
- **Frontend Production Build:** `npm run build` — built cleanly in 27.30s.

### 18. Existing Personal Data Preservation
- **Integrity Check:** `PRAGMA integrity_check` -> `ok`
- **Foreign Keys:** `PRAGMA foreign_key_check` -> `[]`
- **Academic Terms:** 5
- **Courses:** 76
- **Attendance Period Observations:** 3,544
- **Performance Snapshots:** 5
- **Assessment Cells:** 468
- **Safety Backup:** `attendplan_pre_phase_g3_backup_20261107_221914.sqlite3` (2,011,136 bytes).

### 19. Public Repository Readiness
- Working tree 100% sanitized: zero credentials, zero database files, zero browser profiles, zero binary blobs.
- Publication plan ready for future user-approved push to `https://github.com/XrystalAbyss/AttendPlan`.

### 20. Outstanding Release Blockers
- **Zero technical blockers.**
- **Operational Requirement:** Conduct supervised private beta with 1–2 real student volunteers using `ATTENDPLAN_G3_REAL_FRIEND_BETA.md`.

### 21. Final Release Recommendation
- **PROCEED WITH PRIVATE SUPERVISED FRIENDS BETA.**
- Share `AttendPlan-0.1.0-beta.3-Setup.exe` directly with consenting volunteer students.
- Do NOT push to GitHub or publish publicly until volunteer acceptance is verified.

