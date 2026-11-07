# AttendPlan Engineering Roadmap

## Milestone Overview

| Milestone | Code | Focus | Status |
| :--- | :--- | :--- | :--- |
| **Foundation 0** | **F0** | Core Math Engine, Resilient HTML Parser, Sanitized Fixture, Local API & Frontend Shell | **Complete** |
| **Foundation 1** | **F1** | Local Persistence (SQLite + Alembic), Historical Archives, Date-Wise Analytics & Reconciliation | **Complete** |
| **Foundation 2-A** | **F2-A** | Accuracy Corrections + Authenticated Portal Discovery | **Complete** |
| **Foundation 2-B** | **F2-B** | Live Synchronization, Incremental Ingestion & Multi-Semester Archival | **Complete** |
| **Foundation 2-C** | **F2-C** | Automated Keycloak Login Orchestrator & Windows Credential Vault | **Complete** |
| **Foundation 2-D** | **F2-D** | Two-File Windows Launcher, Port Guardrails & Operational Hygiene | **Complete** |
| **Foundation 2-E** | **F2-E** | Historical Multi-Semester Backfill, Live Pilot Gate, Reconciliation & Multi-Term Analytics | **Complete** |
| **Phase B Recovery**| **Phase B** | Automatic Current Refresh, Decoupled Archive, Marks Integration & Full Regression Closure | **Complete** |
| **Phase C.2** | **Phase C.2** | Real-World Acceptance, Automatic Authentication Closure & Current Attendance Synchronization | **Complete (VERIFIED_LIVE)** |
| **Phase D** | **Phase D** | Calendar-Aware Multi-Semester Historical Archive, Marks Integration & Coverage Recovery | **Complete (VERIFIED_OFFLINE / VERIFIED_WINDOWS_RUNTIME)** |
| **Phase D.1** | **Phase D.1** | Authorized Semester 4 Historical Day-Wise Live Pilot (Jan–May 2026) | **Complete (VERIFIED_LIVE)** |
| **Foundation 3** | **F3** | Timetable Simulation Engine, Day-Bunk Impact Matrix, Multi-Week Projections | Planned |
| **Foundation 4** | **F4** | Desktop Packaging, Offline Notification Alarms, Data Backup & Export | Planned |

---

## Phase D: Calendar-Aware Multi-Semester Historical Archive & Academic Marks
- [x] **Teaching Window Modeling**: Implemented `AcademicTermCalendarService` with odd (Aug–Nov) and even (Jan–May) institutional windows.
- [x] **Accurate Month-to-Year Mapping**: YearMonth resolution prevents cross-semester and cross-calendar year collisions.
- [x] **Out-of-Window Prevention**: Out-of-window requests skipped with `OUTSIDE_CALENDAR_WINDOW` without issuing portal requests.
- [x] **Request Bounding**: Total historical synchronization bounded from 107 requests to 26 requests across all 5 registered semesters.
- [x] **True Denominators**: Coverage denominators reflect candidate teaching months ($4$ or $5$) rather than an arbitrary 12-month calendar year.
- [x] **Decoupled Academic Performance**: Academic marks snapshots (`PerformanceSnapshot`) maintained independently of attendance lecture windows.
- [x] **Interactive Month Customization UI**: Extended `ArchiveSync.tsx` with inline chip controls to add, remove, and reset semester teaching months.
- [x] **Complete Quality Gates**: 265 backend tests passed, 38 frontend tests passed (303 total), 0 failures.

---

## Phase B: Comprehensive System Recovery (October 2026)
- [x] **Decoupled Architecture**: Separated high-priority Service A (Current-Term Refresh) from lower-priority Service B (Historical Archive).
- [x] **Empty Month Scope Bug Resolved**: Fixed `portal_safety.py` so empty historical months return `NO_REPORTED_PERIODS` instead of raising scope mismatches.
- [x] **Startup Debounce & Controls**: Upgraded `StartupCoordinator` with 30s debounce, multi-tab deduplication, and on-demand `/refresh-current`.
- [x] **Dynamic Term Resolution**: Dynamic detection of active term via `CurrentTermResolver` without hardcoded semester values.
- [x] **Self-Updating Dashboard**: Automatic query invalidation across all attendance, reconciliation, and analytics views upon sync completion.
- [x] **Quality Gate Completion**: 234 backend tests passing, 37 frontend tests passing, clean typechecks, and zero lint errors.

---

## F2-E Scope (Historical Multi-Semester Backfill & Reconciliation)
- [x] **Historical Term Discovery**: Inspect real `sel_academic_year`, `sel_sem`, and `sel_class` options without assuming static mappings.
- [x] **Discrete Discovery Statuses**: `AVAILABLE`, `EMPTY`, `INACCESSIBLE`, `UNKNOWN`, `FAILED`, `NOT_CHECKED`.
- [x] **Two-Stage Extraction**:
  - Stage A: Subject-wise summaries with rational percentages and unrecorded course handling ($d=0$).
  - Stage B: Day-wise timetable matrix parsing with "Lecture Timings" structural header row exclusion.
- [x] **Controlled Batching & Safety**: Single active sync mutex (`_SYNC_LOCK`), 1.5s–2.5s pacing, session expiry detection, graceful user cancellation.
- [x] **Term Isolation & Deduplication**: Compound key scoping `(academic_term_id, course_code)`, canonical SHA-256 fingerprint deduplication, zero collision between repeated course codes across semesters.
- [x] **Coverage & Reconciliation Model**: `TermCoverageReport` tracking attempted vs completed months, unmapped periods, and explicit reconciliation verdicts (`MATCHED`, `SCOPE_MISMATCH`, `SOURCE_DISCREPANCY`).
- [x] **Multi-Semester Analytics Foundation**: Cross-semester overview, term summaries, subject history, weekday and monthly patterns without data invention.
- [x] **Focused Frontend Interface**: 7-section Historical Attendance tab with term switcher, summary card, course table, coverage audit, monthly & weekday breakdowns, and live preview/sync controls.

---

## F2-B Scope (Live Integration & State Machine)
- [x] **LivePortalExtractor**: Resilient Playwright CDP controller connecting to dedicated Chrome loopback (`127.0.0.1:9222`).
- [x] **Subject-Wise Live Extraction**: Dynamic academic year, semester, and class discovery; extracts course roster; calculates rational percentages; compares against portal with deviation thresholds.
- [x] **Day-Wise Timetable Live Extraction**: Horizontal timetable scrolling, P/A/blank parsing (blank evaluates as `NOT_REPORTED`), Show Course Name attribution.
- [x] **SyncJob State Machine**: 15 discrete states backed by SQLite `sync_jobs` table.
- [x] **Concurrency & Mutex**: Threading lock prevents duplicate concurrent sync jobs.
- [x] **Current-Semester Pilot Sync**: One-click orchestration of subject snapshot + 1 month day-wise timetable + transactional persistence + reconciliation.
- [x] **Historical Sync Planner**: Dynamic term discovery, seasonal month mapping, exact HTTP request estimation, sequential execution safeguards, no brute-forcing.
- [x] **Frontend Sync Center**: Live sync controls, real-time job progress bar, manual HTML fallback, and React Query cache invalidation.
