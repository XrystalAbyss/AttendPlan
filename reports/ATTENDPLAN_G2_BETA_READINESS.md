# AttendPlan — Phase G.2: Supervised Friends Beta Readiness Audit

**Document Reference:** `ATTENDPLAN_G2_BETA_READINESS.md`  
**Phase:** G.2 Supervised Friends Beta & Release Hardening  
**Date:** 2026-11-07  
**Build Target:** `AttendPlan-0.1.0-beta.2-Setup.exe`  
**Distribution State:** PRIVATE, SUPERVISED FRIENDS-BETA ONLY  

---

## 1. Executive Summary

Phase G.2 transitions AttendPlan from the baseline release candidate (`0.1.0-beta.1`) into a hardened, field-ready distribution package (`0.1.0-beta.2`).

During Phase G.2:
1. **Baseline Invariants Preserved**: The baseline installer `AttendPlan-0.1.0-beta.1-Setup.exe` (SHA-256: `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc`, 81,630,124 bytes) remains completely unmodified. Developer personal database integrity was verified with zero data loss (5 terms, 76 courses, 3,544 observations, 5 marks snapshots, 468 assessment cells).
2. **Packaged Candidate Hardening**: Critical defects discovered during testing were remedied:
   - Loopback cross-origin / drive-by CSRF vulnerability addressed via `LocalOriginSecurityMiddleware`.
   - Dynamic API base URL resolution implemented across all frontend components.
   - Dual port collision handling implemented in `backend/launcher.py` (ports 8000–8010) and `portal_session.py` (ports 9222–9230).
   - Database backup export and dedicated browser session disconnect features added to the UI and API.
   - Fresh user Alembic version table initialization stamped to head revision (`f2e2_official_results`).
3. **Hardened Release Candidate Produced**: `AttendPlan-0.1.0-beta.2-Setup.exe` (SHA-256: `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311`, 81,636,792 bytes).

---

## 2. Release Candidates Matrix

| Attribute | Baseline Candidate (G.1) | Hardened Candidate (G.2) |
| :--- | :--- | :--- |
| **Filename** | `AttendPlan-0.1.0-beta.1-Setup.exe` | `AttendPlan-0.1.0-beta.2-Setup.exe` |
| **Version** | `0.1.0-beta.1` | `0.1.0-beta.2` |
| **File Size (Bytes)** | 81,630,124 | 81,636,792 |
| **SHA-256 Checksum** | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` | `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311` |
| **Privileges Required** | Lowest (Standard Non-Admin User) | Lowest (Standard Non-Admin User) |
| **Install Directory** | `%LOCALAPPDATA%\AttendPlan\app` | `%LOCALAPPDATA%\AttendPlan\app` |
| **Origin Security Middleware** | No (Loopback host only) | **Yes (`LocalOriginSecurityMiddleware`)** |
| **Frontend Serving Port** | Hardcoded `http://127.0.0.1:8000` | **Dynamic (`window.location.host`)** |
| **Port Collision Handling** | Unhandled (WinError 10048) | **Graceful auto-increment (8000–8010)** |
| **CDP Collision Handling** | Strict 9222 | **Reachable verification & 9222–9230 scan** |
| **Backup Export API / UI** | Manual file copy | **Dedicated API endpoint & UI button** |
| **Browser Disconnect** | Process terminate only | **CDP release & UI button** |
| **Status** | SUPERSEDED | **ACTIVE FRIENDS-BETA CANDIDATE** |

---

## 3. Defects Identified and Resolved

### Defect 1: Loopback Cross-Origin / Drive-by API Access
- **Symptom:** Requests sent from external websites (e.g. `Origin: https://evil.com` or `sec-fetch-site: cross-site`) to `http://127.0.0.1:8000/api/v1/portal/session/launch` were returning `200 OK`.
- **Root Cause:** Standard CORS middleware was allowing specified loopback origins but was not actively rejecting external web origins on state-changing endpoints.
- **Resolution:** Introduced `LocalOriginSecurityMiddleware` in `backend/app/main.py`. Any request to `/api/` bearing an unauthorized `Origin`, `Referer`, or `sec-fetch-site: cross-site` is immediately rejected with `403 Forbidden`.

### Defect 2: Hardcoded Loopback Port in Frontend Components
- **Symptom:** Several UI components (`App.tsx`, `SettingsView.tsx`, `ArchiveSync.tsx`, `AttendanceExplorer.tsx`, `FirstRunOnboarding.tsx`, `HomeView.tsx`, `PerformanceView.tsx`, `StartupConnection.tsx`) made direct calls to `http://127.0.0.1:8000`.
- **Root Cause:** Hardcoded strings prevented frontend operation when the backend was running on an alternate port (e.g., 8001).
- **Resolution:** Replaced all hardcoded occurrences with dynamic `API_BASE` (`typeof window !== "undefined" && window.location.port === "5173" ? "http://127.0.0.1:8000" : ""`), allowing relative URLs in production builds.

### Defect 3: Single-Port Collision Failure
- **Symptom:** If port 8000 was occupied by an unrelated Windows service, the launcher would fail to bind Uvicorn, leading to a 15-second timeout.
- **Root Cause:** `launcher.py` lacked alternative port discovery.
- **Resolution:** Added `is_port_in_use()` and `find_available_port()` in `backend/launcher.py`. If port 8000 is occupied by an external application, AttendPlan automatically discovers and binds the next available port in 8001–8010.

### Defect 4: CDP Port Ambiguity
- **Symptom:** Non-CDP services running on port 9222 could cause Playwright connection hangs.
- **Root Cause:** `is_cdp_reachable()` only checked HTTP 200 without validating JSON payload content.
- **Resolution:** Updated `is_cdp_reachable()` to parse the JSON response and verify the presence of `"Browser"` or `"webSocketDebuggerUrl"`. Added `find_working_cdp_port()` to discover alternative ports (9223–9230) if 9222 is in use.

### Defect 5: Unstamped Alembic Table on Clean User Profile
- **Symptom:** Initializing an empty database with `init_db()` created all 11 tables but did not stamp `alembic_version`, potentially interfering with future migration commands.
- **Root Cause:** `init_db()` called `Base.metadata.create_all()` without invoking Alembic stamping.
- **Resolution:** Updated `init_db()` to automatically populate `alembic_version` with head revision `'f2e2_official_results'`.

---

## 4. Friends Beta Release Scope

AttendPlan is prepared for a **private, supervised friends beta** with designated student volunteers.
- **Distribution Scope:** Private link or direct executable transfer to consented student testers.
- **Data Boundaries:** 100% local-first. Zero telemetry, zero external tracking, zero cloud synchronization.
- **University Interactions:** Read-only portal extraction strictly through user-authenticated local Chrome CDP.

