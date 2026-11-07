# AttendPlan Architecture Specification

## 1. Executive Summary
**AttendPlan** is a local-first, privacy-preserving desktop/local web application designed to help university students monitor, analyze, and plan their course attendance against an institutional threshold (specifically, the standard 75% requirement).

The system interfaces with the university's **iCloudEMS (CoreCampus)** ERP portal. Crucially, AttendPlan is built on a **zero-trust, read-only** architecture that strictly avoids storing user passwords, intercepting multi-factor authentication (MFA/OTP), or violating portal security policies.

---

## 2. Architectural Pillars

```
+-----------------------------------------------------------------------------------+
|                                  USER WORKSPACE                                   |
|                                                                                   |
|  [Dedicated Chrome Browser (User-driven)]           [AttendPlan Frontend (React)] |
|    - User data dir: %LOCALAPPDATA%/chrome-profile     - Semester Explorer & Tabs  |
|    - Student logs in via Keycloak + Authenticator     - Roster Table & Badges     |
|    - Read-only loopback CDP (127.0.0.1:9222)          - Absence Analytics (Month) |
|                                                       - Source Reconciliation     |
|                                                       - Portal Discovery View     |
|                                                       - What-If Simulation Drawer |
+--------------------------+----------------------------------------+---------------+
                           |                                        |
                           | CDP Loopback (Read-Only)               | REST / JSON (127.0.0.1)
                           v                                        v
+-----------------------------------------------------------------------------------+
|                        LOCAL BACKEND (FastAPI - 127.0.0.1)                        |
|                                                                                   |
|   +------------------------------------+   +----------------------------------+   |
|   |          Adapters Layer            |   |           Domain Layer           |   |
|   |  - PortalSessionManager (CDP)      |-->|  - Exact Rational Math Engine    |   |
|   |  - LivePortalExtractor (Playwright)|   |  - Deterministic Analytics Engine|   |
|   |  - AcademicTermDiscoveryAdapter    |   |  - Threshold & Margin Invariants |   |
|   |  - SubjectWiseAttendanceAdapter    |   +----------------------------------+   |
|   |  - DayWiseAttendanceAdapter        |                          |               |
|   |  - OverallAttendanceAdapter        |                          |               |
|   |  - Canonical Checksum Calculator   |                          |               |
|   +------------------------------------+                          |               |
|                      |                                            |               |
|                      v                                            v               |
|   +------------------------------------+   +----------------------------------+   |
|   |          Services Layer            |   |        Persistence Layer         |   |
|   |  - IngestionService (Idempotent)   |-->|  - SQLite (WAL Mode, FK Enabled) |   |
|   |  - SyncJobService (State Machine)  |   |  - SyncJob Model & Execution Log |   |
|   |  - AcademicTermCalendarService     |   |  - PerformanceSnapshots          |   |
|   |  - HistoricalBackfillService       |   |  - Alembic Schema Migrations     |   |
|   |  - HistoricalDiscoveryService      |   +----------------------------------+   |
|   |  - ReconciliationService           |                                          |
|   +------------------------------------+                                          |
+-----------------------------------------------------------------------------------+
```

### 2.1 Local-First & Air-Gapped Privacy
- **Host Binding**: The backend binds exclusively to `127.0.0.1`. It never listens on public interfaces (`0.0.0.0`).
- **Data Residence**: All snapshot data, simulated timetables, and user notes reside on the user's local disk in an embedded SQLite database at `%LOCALAPPDATA%/AttendPlan/attendplan.sqlite3`.
- **Zero Credential Capture**: The application never prompts for, transmits, or saves passwords, MFA seeds, or session cookies.
- **Dedicated Browser Profile**: Browser automation operates through a dedicated Chrome profile outside the repository directory (`%LOCALAPPDATA%\AttendPlan\chrome-profile`).
- **No External Telemetry**: The application communicates with no third-party tracking, analytics, or remote telemetry servers.

### 2.2 Clean Layered Monorepo Architecture
The repository is organized into distinct, decoupled subsystems:
```
AttendPlan/
├── backend/                  # Python 3.12+ FastAPI Application
│   ├── app/
│   │   ├── domain/           # Pure attendance mathematics, analytics & RFC 6238 TOTP engine
│   │   ├── adapters/         # PortalSessionManager, LivePortalExtractor, QRParser & discovery adapters
│   │   ├── db/               # SQLAlchemy 2.0 models, enums & session factory
│   │   ├── services/         # Ingestion, HistoricalPlanner, SyncJobs, Settings, TotpVault & LoginOrchestrator
│   │   └── api/              # FastAPI routers, request/response DTOs (42 endpoints)
│   ├── alembic/              # Database schema migrations
│   └── tests/                # Deterministic unit, integration & sanitization test suites (105 tests)
├── frontend/                 # React 19 + TypeScript + Vite Single Page Application
│   └── src/
│       ├── components/       # Presentational & institutional dashboard components & Auth Modal
│       ├── api/              # Strongly typed fetch client for local REST endpoints
│       └── types/            # Domain interfaces matching Pydantic schemas
└── docs/                     # Living architecture, contracts, and test strategy
```

---

## 3. Verified Route Inventory (51 Endpoints)

| Method | Endpoint | Subsystem | Semantic Responsibility |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | System | System health check and uptime diagnostic |
| `GET` | `/api/v1/attendance/sample` | Attendance | Pure in-memory inspection of historical sample snapshot (no DB mutation) |
| `POST` | `/api/v1/demo/seed` | Demo | Explicit user/test-initiated seeding of sample data into SQLite |
| `POST` | `/api/v1/simulation/simulate` | Simulation | What-If lecture change projection |
| `GET` | `/api/v1/terms` | Term | List all academic terms (starts empty on fresh database) |
| `GET` | `/api/v1/terms/{term_id}/attendance` | Attendance | Course roster and margin statistics for a term |
| `GET` | `/api/v1/terms/{term_id}/snapshots` | Provenance | Historical snapshot provenance chain |
| `GET` | `/api/v1/terms/{term_id}/coverage` | Historical Coverage | Detailed term coverage audit (candidate months, dates, periods, errors) |
| `GET` | `/api/v1/terms/{term_id}/analytics/summary` | Analytics | Term summary analytics |
| `GET` | `/api/v1/terms/{term_id}/analytics/monthly` | Analytics | Month-wise attendance breakdown (year-separated) |
| `GET` | `/api/v1/terms/{term_id}/analytics/weekday` | Analytics | Day-of-week attendance patterns (Asia/Kolkata) |
| `GET` | `/api/v1/terms/{term_id}/analytics/daily` | Analytics | Day-by-day period delivery and attendance roster |
| `GET` | `/api/v1/terms/{term_id}/analytics/subjects` | Analytics | 3-dimensional subject absence rankings |
| `GET` | `/api/v1/terms/{term_id}/analytics/calendar` | Analytics | Calendar date observation matrix |
| `GET` | `/api/v1/analytics/academic-history` | Analytics | Cross-semester career attendance progression |
| `GET` | `/api/v1/terms/{term_id}/reconciliation` | Reconciliation | Subject-wise vs Day-wise provenance reconciliation |
| `POST` | `/api/v1/attendance/imports/html` | Ingestion | Multipart HTML upload and ingestion |
| `GET` | `/api/v1/attendance/ingestions` | Ingestion | Audit log of past ingestion events |
| `GET` | `/api/v1/portal/session/status` | Portal Session | Current browser state, loopback CDP connectivity & URL |
| `POST` | `/api/v1/portal/session/launch` | Portal Session | Launch dedicated Chrome process on loopback port 9222 |
| `POST` | `/api/v1/portal/session/close` | Portal Session | Terminate dedicated Chrome browser session cleanly |
| `POST` | `/api/v1/portal/discover/terms` | Discovery | Discover available academic years, semesters, and class mappings |
| `POST` | `/api/v1/portal/discover/subject-wise` | Discovery | Discover Subject-Wise table headers, columns, and records |
| `POST` | `/api/v1/portal/discover/day-wise` | Discovery | Discover Day-Wise timetable schema, time slot rows, and toggle |
| `POST` | `/api/v1/portal/discover/overall` | Discovery | Discover Overall Attendance (allSubject.php) view schema |
| `POST` | `/api/v1/portal/sync/subject-wise` | Live Sync | Trigger Subject-Wise live synchronization |
| `POST` | `/api/v1/portal/sync/day-wise` | Live Sync | Trigger Day-Wise live synchronization |
| `POST` | `/api/v1/portal/sync/pilot` | Live Sync | Execute combined pilot synchronization |
| `GET` | `/api/v1/portal/sync/historical-plan` | Historical Sync | Generate multi-semester sync execution plan |
| `GET` | `/api/v1/portal/sync/jobs/latest` | Sync Jobs | Fetch the most recent active or completed sync job |
| `GET` | `/api/v1/portal/sync/jobs/{job_id}` | Sync Jobs | Query status and progress of a specific sync job |
| `POST` | `/api/v1/portal/sync/jobs/{job_id}/cancel` | Sync Jobs | Gracefully cancel a running sync job |
| `GET` | `/api/v1/auth/settings` | Settings | Retrieve persistent mobile identity (masked) and autofill toggles |
| `POST` | `/api/v1/auth/settings` | Settings | Persist/update registered student mobile identity in settings.json |
| `GET` | `/api/v1/auth/totp/status` | TOTP Vault | Query Windows Credential Manager enrollment and verification status |
| `POST` | `/api/v1/auth/totp/inspect` | TOTP Vault | Inspect Base32, standard URI, migration URI, or QR screenshot |
| `POST` | `/api/v1/auth/totp/enroll` | TOTP Vault | Securely store secret in Windows Credential Manager |
| `POST` | `/api/v1/auth/totp/verify` | TOTP Vault | Verify TOTP engine time synchronization with live 6-digit test code |
| `DELETE` | `/api/v1/auth/totp/enrollment` | TOTP Vault | Purge enrolled TOTP secret from Windows Credential Manager |
| `PATCH` | `/api/v1/auth/totp/settings` | TOTP Vault | Update auto-submit preferences |
| `POST` | `/api/v1/auth/totp/autofill` | TOTP Vault | Generate in-memory TOTP and fill active Keycloak OTP challenge |
| `POST` | `/api/v1/auth/login/orchestrate` | Orchestrator | Execute full automated Keycloak login state machine |
| `GET` | `/api/v1/auth/login/status` | Orchestrator | Query current orchestrator state machine status |
| `GET` | `/api/v1/startup/settings` | Startup | Read startup preferences and approved scope count |
| `POST` | `/api/v1/startup/settings` | Startup | Save startup preferences (auto_connect, auto_refresh_current_term) |
| `POST` | `/api/v1/startup/connect` | Startup | Trigger background connection and current-term refresh if enabled |
| `POST` | `/api/v1/startup/refresh-current` | Startup | Dedicated on-demand refresh for current semester attendance |
| `GET` | `/api/v1/startup/status` | Startup | Real-time state of background connection and refresh jobs |
| `POST` | `/api/v1/attendance-archive/plan` | Archive | Generate bounded historical scope plan across discovered terms |
| `POST` | `/api/v1/attendance-archive/start` | Archive | Start user-approved historical backfill run |
| `GET` | `/api/v1/attendance-archive/status` | Archive | Status and progress of current or last historical archive run |
| `POST` | `/api/v1/attendance-archive/resume` | Archive | Resume interrupted historical archive scopes |
| `POST` | `/api/v1/attendance-archive/cancel` | Archive | Stop historical archive run after current report |

---

## 5. Phase B: Decoupled Service A & Service B Synchronization

AttendPlan Phase B decouples live attendance maintenance from historical archival:

### Service A: Current-Semester Live Refresh (High Priority)
- **Trigger**: Automatic on launch (when opted in via `auto_refresh_current_term`) or manual via `POST /api/v1/startup/refresh-current`.
- **Dynamic Term Resolution**: Resolves active term dynamically via `CurrentTermResolver` (no hardcoded semester or academic year).
- **Extraction Scope**: Latest subject-wise summary + current calendar month day-wise attendance (`Asia/Kolkata` with Windows fallback).
- **Data Ingestion**: Deduplicates snapshots, updates period observations, recalculates metrics via `ReconciliationService`, and invalidates React Query caches.

### Service B: Historical Academic Archive (Lower Priority)
- **Trigger**: Explicit user approval via `ArchiveSync.tsx`.
- **Scope**: Discovers accessible past academic terms, imports prior subject summaries, imports available day-wise periods, and integrates academic marks/results.
- **Safety**: Bounded reports, sequential pacing, durable SQLite checkpoints, and independent lifecycle that never blocks Service A.

