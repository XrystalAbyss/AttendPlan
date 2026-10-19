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
|   |  - AcademicTermDiscoveryAdapter    |   |  - Deterministic Analytics Engine|   |
|   |  - SubjectWiseAttendanceAdapter    |   |  - Threshold & Margin Invariants |   |
|   |  - DayWiseAttendanceAdapter        |   +----------------------------------+   |
|   |  - OverallAttendanceAdapter        |                          |               |
|   |  - Canonical Checksum Calculator   |                          |               |
|   +------------------------------------+                          |               |
|                      |                                            |               |
|                      v                                            v               |
|   +------------------------------------+   +----------------------------------+   |
|   |          Services Layer            |   |        Persistence Layer         |   |
|   |  - IngestionService (Idempotent)   |-->|  - SQLite (WAL Mode, FK Enabled) |   |
|   |  - ReconciliationService           |   |  - Alembic Schema Migrations     |   |
|   +------------------------------------+   +----------------------------------+   |
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
│   │   ├── domain/           # Pure attendance mathematics & analytics engine
│   │   ├── adapters/         # PortalSessionManager, DOM parsers & discovery adapters
│   │   ├── db/               # SQLAlchemy 2.0 models, enums & session factory
│   │   ├── services/         # Ingestion, canonical checksums & reconciliation
│   │   └── api/              # FastAPI routers, request/response DTOs (24 endpoints)
│   ├── alembic/              # Database schema migrations
│   └── tests/                # Deterministic unit, integration & sanitization test suites
├── frontend/                 # React 19 + TypeScript + Vite Single Page Application
│   └── src/
│       ├── components/       # Presentational & institutional dashboard components
│       ├── api/              # Strongly typed fetch client for local REST endpoints
│       └── types/            # Domain interfaces matching Pydantic schemas
└── docs/                     # Living architecture, contracts, and test strategy
```

---

## 3. Verified Route Inventory (24 Endpoints)

| Method | Endpoint | Semantic Responsibility |
| :--- | :--- | :--- |
| `GET` | `/health` | System health check and uptime diagnostic |
| `GET` | `/api/v1/attendance/sample` | Pure in-memory inspection of historical sample snapshot (no DB mutation) |
| `POST` | `/api/v1/demo/seed` | Explicit user/test-initiated seeding of sample data into SQLite |
| `POST` | `/api/v1/simulation/simulate` | What-If lecture change projection |
| `GET` | `/api/v1/terms` | List all academic terms (starts empty on fresh database) |
| `GET` | `/api/v1/terms/{term_id}/attendance` | Course roster and margin statistics for a term |
| `GET` | `/api/v1/terms/{term_id}/snapshots` | Historical snapshot provenance chain |
| `GET` | `/api/v1/terms/{term_id}/analytics/summary` | Term summary analytics |
| `GET` | `/api/v1/terms/{term_id}/analytics/monthly` | Month-wise attendance breakdown (year-separated) |
| `GET` | `/api/v1/terms/{term_id}/analytics/weekday` | Day-of-week attendance patterns (Asia/Kolkata) |
| `GET` | `/api/v1/terms/{term_id}/analytics/daily` | Day-by-day period delivery and attendance roster |
| `GET` | `/api/v1/terms/{term_id}/analytics/subjects` | 3-dimensional subject absence rankings |
| `GET` | `/api/v1/terms/{term_id}/analytics/calendar` | Calendar date observation matrix |
| `GET` | `/api/v1/analytics/academic-history` | Cross-semester career attendance progression |
| `GET` | `/api/v1/terms/{term_id}/reconciliation` | Subject-wise vs Day-wise provenance reconciliation |
| `POST` | `/api/v1/attendance/imports/html` | Multipart HTML upload and ingestion |
| `GET` | `/api/v1/attendance/ingestions` | Audit log of past ingestion events |
| `GET` | `/api/v1/portal/session/status` | Current browser state, loopback CDP connectivity & URL |
| `POST` | `/api/v1/portal/session/launch` | Launch dedicated Chrome process on loopback port 9222 |
| `POST` | `/api/v1/portal/session/close` | Terminate dedicated Chrome browser session cleanly |
| `POST` | `/api/v1/portal/discover/terms` | Discover available academic years, semesters, and class mappings |
| `POST` | `/api/v1/portal/discover/subject-wise` | Discover Subject-Wise table headers, columns, and records |
| `POST` | `/api/v1/portal/discover/day-wise` | Discover Day-Wise timetable schema, time slot rows, and toggle |
| `POST` | `/api/v1/portal/discover/overall` | Discover Overall Attendance (allSubject.php) view schema |
