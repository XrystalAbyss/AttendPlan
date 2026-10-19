# AttendPlan Engineering Roadmap

## Milestone Overview

| Milestone | Code | Focus | Status |
| :--- | :--- | :--- | :--- |
| **Foundation 0** | **F0** | Core Math Engine, Resilient HTML Parser, Sanitized Fixture, Local API & Frontend Shell | **Complete** |
| **Foundation 1** | **F1** | Local Persistence (SQLite + Alembic), Historical Archives, Date-Wise Analytics & Reconciliation | **Complete** |
| **Foundation 2-A** | **F2-A** | Accuracy Corrections + Authenticated Portal Discovery | **Complete** |
| **Foundation 2-B** | **F2-B** | Live Synchronization, Incremental Ingestion & Multi-Semester Archival | Planned (Next) |
| **Foundation 3** | **F3** | Timetable Simulation Engine, Day-Bunk Impact Matrix, Multi-Week Projections | Planned |
| **Foundation 4** | **F4** | Desktop Packaging, Offline Notification Alarms, Data Backup & Export | Planned |

---

## F2-A Scope (Completed)

### Gate A: Data Accuracy & System Integrity Corrections
- [x] **Period Counting**: Eliminated automatic 2x multiplier on lab rows. Preserved independently observed 50-minute slot cells (weight 1 each). Added regression tests ensuring two observed lab slots are not counted as four periods.
- [x] **Blank Cell Semantics**: Blank timetable cells evaluate as `PeriodStatus.NOT_REPORTED` ($d=0, a=0$). `NO_CLASS` is reserved strictly for explicit holiday/cancellation markers. Never treated as absences.
- [x] **Data Coverage**: Removed arbitrary `>= 10` dates rule. Implemented formal `CoverageStatus` (`COMPLETE`, `PARTIAL`, `UNKNOWN`, `UNAVAILABLE`).
- [x] **Sample Data Isolation**: Normal API reads (`GET /terms`, `GET /attendance/sample`) never write to SQLite. Fresh installation begins with empty real database (`[]`). Provided explicit `POST /api/v1/demo/seed` for demo data.
- [x] **Reconciliation Safety**: Verified date window scope compatibility. Returns `ReconciliationStatus.SCOPE_MISMATCH` instead of false `DISCREPANCY` when day-wise observations represent a partial date subset.
- [x] **Reporting Consistency**: Created automatically verified route inventory auditing all 24 FastAPI endpoints.
- [x] **Migration Safety**: Preserved schema forward-compatibility and verified SQLite batch mode migrations.

### Gate B: Authenticated Portal Discovery
- [x] **Zero Credential Capture**: Strictly no capture, storage, or prompting for OTPs, passwords, or session tokens.
- [x] **Browser Strategy**: Dedicated Chrome profile in `%LOCALAPPDATA%\AttendPlan\chrome-profile` outside the workspace. Loopback CDP binding strictly on `127.0.0.1:9222`.
- [x] **Guided Flow**: State machine handling `DISCONNECTED`, `BROWSER_READY`, `LOGIN_REQUIRED`, `AUTHENTICATED`, `DISCOVERING`, `DISCOVERY_COMPLETE`, `SESSION_EXPIRED`, `ERROR`, and `MANUAL_IMPORT_AVAILABLE`.
- [x] **Discovery Adapters**: Implemented pure DOM adapters for Terms, Subject-Wise, Day-Wise (Show Course Name toggle, time slots, P/A cells), and Overall Attendance (`allSubject.php`).
- [x] **Sanitized Fixtures**: Created `synthetic_overall_attendance.html`, `synthetic_daywise_attendance.html`, and `sample_attendance.html` with zero PII.
- [x] **Frontend F2-A Scope**: Added Portal Discovery view with connection status, diagnostic panels, guided action buttons, and manual HTML fallback.
- [x] **Quality Gates**: 69 backend tests passing (100%), 15 frontend tests passing (100%), mypy clean across all 32 source files, ruff clean, and production build passing.

---

## F2-B Scope (Planned Next)
- Live end-to-end synchronization with user-authenticated browser.
- Incremental snapshot generation for current active semester.
- Dynamic multi-month day-wise extraction iterating over semester date boundaries.
- User-approved one-click archival of historical completed terms.
