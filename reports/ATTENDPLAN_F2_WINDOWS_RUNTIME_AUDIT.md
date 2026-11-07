# AttendPlan — Phase F.2 Windows Runtime Audit Report
**Milestone:** Phase F.2 — Performance, Reliability & Independent-User Acceptance  
**Date:** November 7, 2026  
**Auditor:** Principal Windows Application Engineer  
**Status:** VERIFIED ON WINDOWS 11 RUNTIME  

---

## 1. Executive Summary & Runtime Topology

AttendPlan's Windows runtime environment was subjected to end-to-end launcher lifecycle verification, process isolation testing, port conflict resilience checks, and error recovery auditing.

The application operates as a coordinated 3-tier local system:
1. **Dedicated Chrome Instance**: Binds to `127.0.0.1:9222` using an isolated user profile at `%LOCALAPPDATA%\AttendPlan\chrome-profile`. Completely separated from the user's personal browser profile.
2. **FastAPI Backend (Uvicorn)**: Binds strictly to `127.0.0.1:8000`. Encapsulates SQLite database persistence, background sync job execution, and pure domain mathematics.
3. **React/Vite Frontend**: Served from `127.0.0.1:5173`. Encapsulates client routing, what-if simulations, and offline caching.

---

## 2. Windows Launcher Verification (`Launch-AttendPlan.cmd`)

The primary entry point `Launch-AttendPlan.cmd` dispatches directly to `scripts\Launch-AttendPlan.ps1` with `-ExecutionPolicy Bypass`.

### Lifecycle Steps Verified:
1. **[1/5] Environment Verification**:
   - Locates Python virtual environment at `backend\.venv\Scripts\python.exe`.
   - Locates frontend Node modules at `frontend\node_modules`.
   - Discovers installed Google Chrome executable (`C:\Program Files\Google\Chrome\Application\chrome.exe`).
   - If prerequisites are missing, outputs clear, actionable setup commands in the console and halts safely without crashing.
2. **[2/5] Dedicated Chrome Startup**:
   - Executes `scripts\Launch-Chrome.ps1 -Quiet`.
   - Verifies loopback debugging port `http://127.0.0.1:9222/json/version`.
   - Reuses existing dedicated Chrome window if already open.
3. **[3/5] Backend Startup & Idempotency**:
   - Queries `http://127.0.0.1:8000/health`.
   - If an existing healthy instance is found, reuses it immediately (`Reused existing healthy instance`).
   - If port 8000 is occupied by an unrelated foreign process, halts gracefully with PID notification rather than crashing.
   - If cold start is required, spawns `python.exe -m uvicorn app.main:app` in hidden window style, saves PID to `%LOCALAPPDATA%\AttendPlan\run\backend.pid`, and polls healthcheck with a 15-second timeout.
4. **[4/5] Frontend Startup**:
   - Queries `http://127.0.0.1:5173`.
   - Reuses existing healthy Vite server if present.
   - If cold start is required, spawns `npm.cmd run dev` on port 5173, saves PID to `%LOCALAPPDATA%\AttendPlan\run\frontend.pid`, and awaits HTTP 200 readiness.
5. **[5/5] Dashboard Activation via CDP**:
   - Queries `http://127.0.0.1:9222/json/list` to determine if a dashboard tab is already open.
   - If already present, brings tab into focus.
   - If absent, creates a new tab via `http://127.0.0.1:9222/json/new?http://127.0.0.1:5173` with PUT and GET fallback.
   - Prevents duplicate browser tabs upon repeated launches.

### Graceful Termination (`Stop-AttendPlan.cmd`):
- Targets only `backend.pid` and `frontend.pid` recorded in `%LOCALAPPDATA%\AttendPlan\run\`.
- Leaves dedicated Chrome open if the student is currently logged in, preserving their portal session.
- Never terminates unrelated personal Chrome instances or system background services.

---

## 3. Playwright Offline Browser Acceptance (24/24 Steps Passed)

The automated Windows human acceptance script `backend/scripts/verify_windows_human_acceptance.py` executed against the live local application under strict offline routing interception (all non-localhost URLs aborted):

```
[PASSED] Step 1: Application server responding - FastAPI on 8000, Vite dev server on 5173
[PASSED] Step 2: Frontend loads - HTTP status 200
[PASSED] Step 3: Root layout mounted - Title: AttendPlan · Attendance & Performance
[PASSED] Step 4: Cached attendance displays immediately - Attendance UI elements rendered
[PASSED] Step 5: Academic navigation available in WorkspaceNav - Tabs: ['Home', 'Attendance', 'Performance', 'Settings']
[PASSED] Step 6: Semester selector lists all 5 terms - All 5 terms discovered and labeled
[PASSED] Step 7: Select semester 1 (2026-2027 Sem 5) - Roster loaded cleanly
[PASSED] Step 8: Select semester 2 (2025-2026 Sem 4) - Roster loaded cleanly
[PASSED] Step 9: Select semester 3 (2025-2026 Sem 3) - Roster loaded cleanly
[PASSED] Step 10: Select semester 4 (2024-2025 Sem 2) - Roster loaded cleanly
[PASSED] Step 11: Select semester 5 (2024-2025 Sem 1) - Roster loaded cleanly
[PASSED] Step 12: Switched to Performance view - PerformanceView active
[PASSED] Step 13: All 5 semesters represented in progression table - 5 progression rows
[PASSED] Step 14: No speculative SGPA/CGPA displayed - Distinct GPA values: {'—'}
[PASSED] Step 15: Semester performance breakdown cards present - Found 5 term articles
[PASSED] Step 16: Course table and assessment columns rendered - Headers verified
[PASSED] Step 17: Assessment breakdown drawers available - Found 55 course drawers
[PASSED] Step 18: Assessment labels and ratios displayed - CE (19/20), Midterm (27/30)
[PASSED] Step 19: Semester 4 masked score labeled MASKED_BY_PORTAL - Verified in DOM
[PASSED] Step 20: Semester 5 partial publication and 4 source courses verified - Verified
[PASSED] Step 21: Source provenance and capture timestamps displayed - 5 provenance tags
[PASSED] Step 22: Live performance capture securely disabled - Policy verified
[PASSED] Step 23: Zero external portal requests attempted during session - 45/45 localhost allowed, 0 external attempted, 0 blocked, 0 ERP calls
[PASSED] Step 24: No browser console errors - 0 console errors, warnings, or exceptions
```

---

## 4. Error Recovery & Resilience Audit

| Failure Scenario | System Handling | Observed Behavior | Integrity Preserved? |
| :--- | :--- | :--- | :--- |
| **Backend unavailable at startup** | Frontend displays retry banner | Displays cached localStorage data where present; shows explicit retry button | Yes (0 corrupted records) |
| **Portal session expired** | Status transitions to `ACTION_REQUIRED` | Top bar prompts "Sign in to Portal" with direct Settings shortcut | Yes (cached attendance intact) |
| **Port 8000 collision** | Launcher detects foreign listener | Halts startup with clear message identifying port conflict | Yes (prevents crash) |
| **Repeated refresh clicks** | React Query mutation locking | Disables button and displays live spinning sync indicator | Yes (duplicate requests suppressed) |
| **DNS rebinding attempt** | `TrustedHostMiddleware` | Returns HTTP 400 Bad Request to non-whitelisted hostnames | Yes (host validation enforced) |
| **Interrupted sync / crash** | Startup recovery service | Rolls back incomplete transaction batches, leaves verified snapshots intact | Yes (database clean) |

---

## 5. Developer-Mode Launcher Transparency

> [!NOTE]  
> In its current Phase F.2 configuration, AttendPlan's Windows launcher operates in **Developer Mode**. It requires:
> - Python 3.12+ with dependencies installed in `backend\.venv`
> - Node.js v20+ with dependencies installed in `frontend\node_modules`
> - Google Chrome installed on the host Windows system.
> 
> A single-click standalone consumer installer (`.msi` / `.exe` bundle embedding Python and static frontend assets) remains a future Phase G release milestone.

