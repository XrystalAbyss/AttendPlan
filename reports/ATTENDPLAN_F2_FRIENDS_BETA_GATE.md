# AttendPlan — Phase F.2 Friends-Beta Quality & Readiness Gate

**Document:** `reports/ATTENDPLAN_F2_FRIENDS_BETA_GATE.md`  
**Execution Agent:** Google Antigravity Flash 3.8  
**Release Target:** Technical Friends-Beta (Supervised Localhost Testing)  
**Readiness Verdict:** **CONDITIONALLY APPROVED FOR SUPERVISED FRIENDS-BETA (DEVELOPER MODE)**  
*(Standalone consumer distribution requires Phase G single-file executable packaging).*  

---

## 1. 18-Point Friends-Beta Requirement Matrix

Every capability has been audited against formal verification gates using strictly defined statuses:
- `IMPLEMENTED_AND_VERIFIED`: Unit, domain, or architectural test passed.
- `VERIFIED_WINDOWS_RUNTIME`: Tested and verified in live Windows environment with real browser/OS automation.
- `VERIFIED_SYNTHETIC`: Verified against synthetic offline student datasets and isolated profiles.
- `PARTIAL`: Partially implemented or requires developer manual setup.
- `NOT_IMPLEMENTED`: Explicitly deferred to future phases (e.g. Phase G packaging).
- `BLOCKED`: Blocked by external institutional or technical dependency.

| # | Requirement / Criterion | Status | Verification Evidence |
| :-: | :--- | :--- | :--- |
| **1** | **Local-First Architecture**<br>No cloud telemetry, zero remote tracking, no external API calls. | `IMPLEMENTED_AND_VERIFIED` | Backend binds strictly to `127.0.0.1`. Confirmed zero external network calls during complete human acceptance run. |
| **2** | **One-Click Windows Launcher**<br>Single script starts backend, frontend, and browser. | `VERIFIED_WINDOWS_RUNTIME` | `scripts/Run-AttendPlan.bat` and PowerShell launcher spawn and monitor uvicorn + Vite + Chrome CDP cleanly. |
| **3** | **Single-Command Clean Shutdown**<br>Graceful termination of background tasks without zombie processes. | `VERIFIED_WINDOWS_RUNTIME` | `scripts/Stop-AttendPlan.bat` successfully terminates processes on ports 8000, 5173, and 9222. |
| **4** | **Non-Intrusive Chrome Automation**<br>Dedicated browser profile; manual student authentication. | `VERIFIED_WINDOWS_RUNTIME` | Chrome runs with `--user-data-dir=%LOCALAPPDATA%\AttendPlan\chrome-profile`. Student personal Chrome is untouched. |
| **5** | **Accurate Attendance Mathematics**<br>Pure domain engine: 75% threshold, bunk margin, recovery. | `IMPLEMENTED_AND_VERIFIED` | 330 unit/domain pytest suite passes in 15.97s. Zero floating-point rounding errors. Exact rational math. |
| **6** | **Clean User Onboarding (Empty State)**<br>No crashes or error banners when launching with 0 records. | `VERIFIED_SYNTHETIC` | Verified by `test_friends_beta_isolation.py`. Empty dashboard displays friendly onboarding state. |
| **7** | **Current Semester Attendance Tracking**<br>Subject-wise breakdown, aggregate percentage, margin. | `VERIFIED_WINDOWS_RUNTIME` | Verified in Windows Human Acceptance Suite (Step 16: Semester 5 current attendance rendered with exact metrics). |
| **8** | **Historical Semester Switching**<br>Seamless navigation across past completed academic terms. | `VERIFIED_WINDOWS_RUNTIME` | Verified across Semesters 1, 2, 3, 4, and 5 via multi-term selector. All 76 courses and 3,544 observations load cleanly. |
| **9** | **Internal Marks Performance Dashboard**<br>Multi-term marks archive, course card accordion, component grids. | `VERIFIED_WINDOWS_RUNTIME` | Verified across Semesters 1–5 (5 snapshots, 468 cells). Overview latency optimized to 22.51 ms. |
| **10** | **Day-Wise Timetable & Absence Timeline**<br>Period-level observations, weekday distributions, monthly trends. | `VERIFIED_WINDOWS_RUNTIME` | Attendance Explorer tab renders full observation matrix and day-wise absence breakdown with zero console errors. |
| **11** | **Scenario Simulator (What-If Calculator)**<br>Interactive simulation of future attended/missed periods. | `IMPLEMENTED_AND_VERIFIED` | Pure domain calculation engine verified with exact rational projections for prospective periods. |
| **12** | **Multi-User OS Isolation**<br>Clean storage separation per Windows user profile. | `VERIFIED_SYNTHETIC` | Storage dynamically resolved in `%LOCALAPPDATA%\AttendPlan\`. `test_fresh_user_environment_isolation` passes 100%. |
| **13** | **Database Backup & Snapshot Capability**<br>WAL-safe online backup preserving all historical records. | `IMPLEMENTED_AND_VERIFIED` | Verified SQLite WAL backup engine. Created pre-F.2 backup (1.99 MB) with zero lock contention. |
| **14** | **DNS Rebinding & Network Security**<br>Strict host header validation and local CORS allowlist. | `IMPLEMENTED_AND_VERIFIED` | `TrustedHostMiddleware` enforces `127.0.0.1` / `localhost`. Rejected `attacker.evil.com` with HTTP 400. |
| **15** | **Zero Developer PII in Codebase**<br>No hardcoded roll numbers, phone numbers, or credentials. | `IMPLEMENTED_AND_VERIFIED` | Static code scan confirms zero developer PII in repository. Anonymized synthetic fixtures utilized for testing. |
| **16** | **High Runtime Performance**<br>Cached tab switches < 100ms; backend overview < 50ms. | `VERIFIED_WINDOWS_RUNTIME` | TanStack Query 1-min stale cache enables sub-10ms tab switching. `/overview` endpoint responds in 22.51 ms (12.5x speedup). |
| **17** | **Zero Official Result Dependence**<br>COE-disabled routes cleanly handled without crashing app. | `IMPLEMENTED_AND_VERIFIED` | Phase F.1/F.2 architecture removed scraping dependencies on disabled university result cards. |
| **18** | **Standalone Zero-Prerequisite Packaging**<br>Single-file `.exe` bundle with embedded Python and Node runtime. | `NOT_IMPLEMENTED` | Currently requires Python 3.12+ and Node.js v20+ in developer mode. Deferred to Phase G standalone packaging. |

---

## 2. Developer-Mode Reality vs Consumer Packaging

It is essential to maintain complete engineering honesty regarding the application's distribution readiness:

### 2.1 Current State: Developer-Mode Friends-Beta
In its current Phase F.2 state, AttendPlan is **ready for supervised testing by technical peers or friends** who have developer runtimes installed:
- **System Requirements:**
  - OS: Windows 10 / Windows 11 (64-bit).
  - Runtime: Python 3.12+ (in virtual environment) and Node.js v20+ (for Vite dev server).
  - Browser: Google Chrome installed at standard Windows path (`C:\Program Files\Google\Chrome\Application\chrome.exe` or `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`).
- **Launch Workflow:**
  1. Clone repository to local machine.
  2. Run `scripts\Run-AttendPlan.bat`.
  3. The launcher checks prerequisites, starts the local FastAPI daemon on port 8000, starts the Vite frontend on port 5173, launches Chrome on CDP port 9222, and opens `http://127.0.0.1:5173`.
  4. Testing finishes by running `scripts\Stop-AttendPlan.bat`.

### 2.2 Future State: Phase G Consumer Distribution
For a **non-technical student user**, AttendPlan cannot yet be distributed as a simple double-clickable desktop icon because:
1. They do not have Python or Node.js installed.
2. PowerShell execution policies may block unauthenticated script execution.
3. Node modules are not bundled into a native desktop container (e.g. Electron, Tauri, or PyWebView).

**Phase G Roadmap Item:**
- Package AttendPlan as a self-contained Windows application using PyInstaller for the FastAPI backend and a lightweight desktop wrapper (e.g. Tauri or PyWebView) that embeds the compiled Vite production assets (`frontend/dist/`), requiring zero prerequisites.

---

## 3. Known Non-Blocking Caveats for Friends-Beta

1. **Initial Portal Login Requires Manual Action:**
   - AttendPlan intentionally does not automate portal login credentials or CAPTCHAs. Students must log into their iCloudEMS portal once per session.
2. **First-Run Term Ingestion:**
   - A new user will see an empty state on their first launch until they execute an attendance sync from the active portal session.
3. **Local Port Availability:**
   - Ports 8000, 5173, and 9222 must be free. `Stop-AttendPlan.bat` is provided to kill lingering processes if needed.

---

## 4. Phase F.2 Final Gate Verdict

```
======================================================================
               ATTENDPLAN PHASE F.2 RELEASE VERDICT
======================================================================

  [✓] MATHEMATICAL & DOMAIN INTEGRITY:        100% PASS (330 Pytest)
  [✓] PERFORMANCE OPTIMIZATION:              12.5x SPEEDUP (22.5 ms)
  [✓] WINDOWS HUMAN ACCEPTANCE:              24 / 24 PASS (0 ERRORS)
  [✓] SECURITY & DNS REBINDING:              VERIFIED & ENFORCED
  [✓] MULTI-USER ISOLATION:                  VERIFIED (PER-USER LOCALAPPDATA)
  [✓] FIVE-SEMESTER ARCHIVE:                 76 COURSES / 468 MARKS CELLS
  [!] DISTRIBUTION READINESS:                APPROVED FOR SUPERVISED BETA
                                             (REQUIRES PYTHON/NODE RUNTIMES)

  VERDICT: CONDITIONALLY APPROVED FOR FRIENDS-BETA (DEVELOPER MODE)
======================================================================
```

