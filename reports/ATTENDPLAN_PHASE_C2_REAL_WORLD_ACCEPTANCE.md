# AttendPlan — Phase C.2 Real-World Acceptance & Current Attendance Synchronization Report

**Milestone:** Phase C.2 — Real-World Acceptance, Automatic Authentication Closure & Current Attendance Synchronization Verification  
**Date:** 2026-10-28  
**Operating Environment:** Windows 11, Chrome CDP 127.0.0.1:9222, FastAPI 127.0.0.1:8000, React/Vite 127.0.0.1:5173  
**Database:** SQLite WAL `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`  
**Quality Gates:** 254 backend tests passing, 38 frontend tests passing (292 total), 0 failures  
**Acceptance Verdict:** **`VERIFIED_LIVE`**

---

## 1. Actual Git State

- **Branch / Worktree:** Main development branch at `c:\Users\astra\Desktop\Project\AttendPlan`
- **Tracked Repositories Hygiene:** Strictly sanitized. Zero student PII (no roll numbers, mobile numbers, student names, session tokens, or authenticator seeds) committed or tracked.
- **Git State:** Local clean modification tracking. No remote pushing performed.
- **Baseline Preserved:** Previous Phase C.1 baseline (254 backend, 38 frontend) completely maintained; all regressions caught and sealed.

---

## 2. User Authentication Preferences

Inspection of local configuration and Windows Credential Manager:

| Configuration Parameter | Location | Value | Semantic Meaning |
|---|---|---|---|
| `auto_connect` | `startup.json` | `true` | Automatic background connection and readiness on launcher start |
| `auto_refresh_current_term` | `startup.json` | `true` | Automatically synchronize current semester on startup |
| `saved_mobile_number` | `settings.json` | `******9050` (Sanitized) | Persistent authorized mobile number enrolled |
| `auto_mobile_autofill` | `settings.json` | `true` | Mobile number autofill consented and active |
| `auto_login_continuation` | `settings.json` | `true` | Automatic form submission consented and active |
| `totp_vault_enrolled` | Windows Credential Manager | `True` | Hardware-backed local secret enrollment active |
| `auto_totp_autofill` | `totp_metadata.json` | `true` | In-memory dynamic OTP generation consented |
| `auto_totp_submit` | `totp_metadata.json` | `true` | Automatic Keycloak MFA submission consented |

**Consent Verdict:** Authentication automation is **fully approved and enabled** by user configuration. No consent was bypassed.

---

## 3. Root Cause of Pending Live Authentication (Phase C.1 Investigation)

In Phase C.1, execution ended at `LIVE_AUTH_PENDING_USER`. Investigation identified the exact root cause:
1. **Short-Lived Launch Process:** Dedicated Chrome had been spawned via a child sub-process that exited when the sub-command finished, causing Windows to terminate child Chrome before the CDP handshake or navigation could complete.
2. **Persistent Process Fix:** Starting Chrome as a detached persistent process with `--remote-debugging-port=9222` and `--user-data-dir="%LOCALAPPDATA%\AttendPlan\chrome-profile"` allowed the browser to persist.
3. **Execution Verification:** When `LoginOrchestrator.orchestrate_login()` executed against the persistent Chrome instance, it:
   - Located the official Keycloak login form (`https://auth.mrei.ac.in/auth/realms/ManavRachna/...`)
   - Filled the authorized mobile number into the username input
   - Clicked "Sign In"
   - Retrieved the TOTP secret directly from Windows Credential Manager in memory
   - Generated the exact valid 6-digit TOTP code
   - Filled and submitted the MFA form
   - Observed redirect to `https://mrei.icloudems.com/corecampus/student/student_index.php`
   - Reached `LoginState.AUTHENTICATED` with zero human intervention!

---

## 4. Real Windows Launcher Execution

The Windows launcher was tested end-to-end:

```
[Double-Click AttendPlan]
    ↓
[1/5] Checking environment: Python backend\.venv [OK], Node modules [OK], Chrome [OK]
    ↓
[2/5] Dedicated Chrome: CDP 127.0.0.1:9222 verified [OK]
    ↓
[3/5] FastAPI Backend: 127.0.0.1:8000 started (PID active) [OK]
    ↓
[4/5] React/Vite Frontend: 127.0.0.1:5173 started [OK]
    ↓
[5/5] StartupCoordinator: Automatic authentication verified → Current term resolved → Refresh executed [OK]
```

- **Traceable Events:** Backend reported `status: healthy` at `/health`; `coordinator.start()` executed in background without blocking launcher completion.
- **Single-Instance Safety:** Existing PIDs and ports are reused; no runaway processes created.

---

## 5. Current Term Verification

The active term was dynamically verified against live portal controls without hardcoding:

- **Academic Year:** `2026-2027`
- **Semester Number:** `5`
- **Class Identifier:** `2582`
- **Display Label:** `B.Tech CSE AIML-Sem 5`
- **Provenance:** `PORTAL_DEFAULT`
- **Is Verified:** `True`
- **Is Provisional:** `False`

The student's enrollment was independently confirmed through `<select id="acadyear">`, `<select id="semNum">`, and `<select id="classid">`.

---

## 6. Live Subject-Wise Refresh

- **Official URL:** `https://mrei.icloudems.com/corecampus/student/attendance/subwise_attendace_new.php`
- **Source Verification:** Verified same-origin HTTPS, valid anti-tamper parameter `e=...&submit=1`.
- **Course Roster:** 15 distinct university courses parsed and arithmetically verified.
- **Total Attended Periods:** `260` (updated from baseline `231`)
- **Total Delivered Periods:** `313` (updated from baseline `280`)
- **Overall Attendance Percentage:** **`83.07%`** (updated from baseline `82.50%`)
- **Snapshot ID:** `0988216a-db4e-4c5e-b6fe-35588114cf30`
- **Canonical Content Checksum:** `82f1ec17eefd83833e6ff719408d97b21752fdad4b4c752561a34a7b556afbe5`
- **Status Classification:** `CourseStatus.SAFE` (above institutional 75% threshold)

---

## 7. Live Current-Month Day-Wise Refresh

- **Official URL:** `https://mrei.icloudems.com/corecampus/student/attendance/myattendance.php`
- **Target Month:** October 2026 (dynamically derived from `Asia/Kolkata` time: `2026-10-28`)
- **Date Range Window:** `2026-10-01` to `2026-10-28`
- **Course Attribution Toggle:** "Show Course Name" toggle activated and verified.
- **Observations Parsed:** `136` individual period records
- **Month Attended / Delivered Sum:** `73 / 100`
- **Batch ID:** `6dba4b78-bb9e-403a-8539-83f048d28eb0`
- **Batch Content Checksum:** `e1345946cf4288ea08a53005a1a8457f910f007d73585584383fe0256f76373e`
- **Period Status Distribution:** All observations parsed into `PRESENT`, `ABSENT`, or `NOT_REPORTED` without structural header rows.

---

## 8. Three-Layer Agreement (Source vs SQLite vs React UI)

| Metric / Dimension | Layer A: Official Source | Layer B: SQLite Database | Layer C: React Dashboard UI | Verification Status |
|---|---|---|---|---|
| **Active Term** | 2026-2027 Sem 5 | `ed06cbda-...` (2026-2027 Sem 5) | `Session: 2026-2027 • Sem: 5` | **MATCH** |
| **Total Attended** | 260 | 260 | 260 | **MATCH** |
| **Total Delivered** | 313 | 313 | 313 | **MATCH** |
| **Aggregate %** | 83.07% | 83.07% | 83.07% | **MATCH** |
| **Course Count** | 15 courses | 15 courses in snapshot rows | 15 courses rendered | **MATCH** |
| **October Coverage** | 2026-10-01 - 2026-10-28 | 136 observations in batch | 136 observations available | **MATCH** |
| **Sync Status** | Source retrieved | `SyncJob: COMPLETED` | `Connected • Up to date` | **MATCH** |

---

## 9. Authentication-to-Refresh Resume

- **Offline / Expired Startup Test:** When started without a session, cached SQLite attendance displays immediately.
- **Automatic Resume Test:** Once the authenticated session was established, `StartupCoordinator` initiated the current refresh job automatically without requiring the user to click Refresh.
- **Single Job Invariant:** Exactly 1 refresh job was created and processed to completion.

---

## 10. Repeated Startup & Idempotency Verification

A second consecutive refresh was executed to test deduplication and stability under repeated launches:

```
INFO:app.services.current_term_resolver:Resolved active term: 2026-2027 Sem 5
=== SECOND REFRESH RESULT ===
State: UP_TO_DATE
Message: Attendance is already up to date (October 2026).
Term Key: 2026-2027-S5
Summary Outcome: DUPLICATE_SKIPPED
Daywise Outcome: DUPLICATE_SKIPPED
Month Label: October 2026
Last Sync Time: 2026-10-28T21:46:27.463158+05:30
Diagnostic: None
```

- **Zero Duplicates:** Database snapshot count remained at 5; observation batches remained at 6.
- **Truthful Provenance:** Refresh was reported as `DUPLICATE_SKIPPED` (the portal was contacted, values verified, and matched canonical checksums).
- **Freshness Timestamp:** `last_sync_time` was updated to reflect successful live source verification.

---

## 11. Historical Archive Isolation

- **Semester 4 Baseline:** Snapshot `63ed56cc-d2e1-4b65-bf87-882fb42fb11c` (17 courses, 485 attended / 554 delivered = 87.55%) remains isolated under term `53d60f23-e8ac-4077-a0ce-27e62aa311b9`.
- **Semester 5 History:** Previous snapshots (`af361c48-...` 231/280, `f13ca77e-...` 230/279, `54591284-...` 185/213) remain intact as immutable historical records.
- **No Archive Sweep:** No historical terms were queried, scanned, or backfilled during current-term startup.

---

## 12. Newly Discovered Defects & Fixes

1. **Defect:** `LivePortalExtractor.navigate_to_view` networkidle timeout on iCloudEMS.
   - **Root Cause:** Persistent tracking/polling connections prevented `wait_for_load_state("networkidle")` from completing within 8000ms.
   - **Fix:** Added 3000ms networkidle timeout with resilient fallback to `domcontentloaded`.
2. **Defect:** Selector readiness race condition in `navigate_to_view`.
   - **Root Cause:** Calling `control(page, "year")` immediately executed `locator.count()`, which returned 0 and raised `REQUIRED_FILTER_MISSING_OR_AMBIGUOUS` before DOM attachment.
   - **Fix:** Switched to `page.locator(SELECTORS["year"]).wait_for(state="visible", timeout=timeout_ms)` before calling `control()`.
3. **Defect:** Class label punctuation divergence (`B.Tech CSE AIML-Sem 5` vs `B.Tech CSE AIML Sem 5`).
   - **Root Cause:** Portal HTML table dropped the hyphen present in the dropdown, causing ingestion service to create a parallel duplicate term.
   - **Fix:** Updated `IngestionService._resolve_or_create_term` to normalize whitespace and hyphens when checking existing terms for the same academic year and semester.
4. **Defect:** `CurrentRefreshService` lock release safety.
   - **Root Cause:** If an error occurred before entering the `try` block, `_SYNC_LOCK` was left held.
   - **Fix:** Moved `try:` immediately after `_SYNC_LOCK.acquire(blocking=False)` and handled `job_id=None` safely in `_fail_job`.

---

## 13. Quality Gate Results

| Test / Check | Tool / Runner | Result | Notes |
|---|---|---|---|
| **Backend Unit & Domain Tests** | `pytest backend\tests` | **254 passed** | 0 failures in 19.66s |
| **Backend Linting** | `ruff check backend\app backend\tests` | **Clean** | All checks passed |
| **Backend Static Typing** | `mypy backend\app` | **Clean** | 43 source files verified |
| **Frontend Unit & Component Tests** | `vitest run` (`npm test`) | **38 passed** | 13 test files passed in 23.82s |
| **Frontend TypeScript Typecheck** | `tsc --noEmit` (`npm run typecheck`) | **Clean** | 0 type errors |
| **Frontend Production Build** | `vite build` (`npm run build`) | **Clean** | Bundle generated in 5.15s |
| **SQLite DB Integrity** | `PRAGMA integrity_check` | **ok** | Clean SQLite database |
| **SQLite Foreign Key Integrity** | `PRAGMA foreign_key_check` | **ok** | 0 foreign key violations |
| **Total Automated Tests** | Pytest + Vitest | **292 passed** | Baseline 100% preserved |

---

## 14. Acceptance Test Matrix Summary

- **A. App launched with valid session:** Auto-sync completed to `UP_TO_DATE` (`VERIFIED_LIVE`).
- **B. App launched with expired session:** Gracefully entered `ACTION_REQUIRED` / prompted login (`VERIFIED_SYNTHETIC`).
- **C. App launched with automatic login enabled:** Keycloak mobile entry + Windows Credential Manager TOTP completed automatically (`VERIFIED_LIVE`).
- **D. App launched with automatic login disabled:** Waited for manual private user login without silent override (`VERIFIED_SYNTHETIC`).
- **E. User authenticates after launch:** Pending refresh resumed automatically without clicking Refresh (`VERIFIED_LIVE`).
- **F. Current portal values unchanged:** Deduplicated cleanly with `DUPLICATE_SKIPPED`, timestamp updated (`VERIFIED_LIVE`).
- **G. Current portal values changed:** New snapshot persisted (260/313), history preserved (`VERIFIED_LIVE`).
- **H. Current-month partial attendance:** 136 observations parsed and upserted cleanly (`VERIFIED_LIVE`).
- **I. Warning or no timetable:** Classified truthfully without synthetic data (`VERIFIED_OFFLINE`).
- **J. Backend restarts during refresh:** Interrupted jobs recovered to `PAUSED`/`FAILED` on startup (`VERIFIED_SYNTHETIC`).
- **K. Second application launch:** Handled idempotently, zero duplicate rows (`VERIFIED_LIVE`).
- **L. Historical archive is incomplete:** Isolated from current term; no archive sweep triggered (`VERIFIED_LIVE`).
- **M. SQLite rejects a write:** Caught cleanly by transaction boundary, lock released (`VERIFIED_SYNTHETIC`).
- **N. Portal cannot verify current term:** Aborts safely with `CURRENT_TERM_UNVERIFIED` (`VERIFIED_SYNTHETIC`).
- **O. Frontend remains open while data changes:** UI reactive polling reflects updated snapshot (`VERIFIED_WINDOWS_RUNTIME`).

---

## 15. Real Acceptance Verdict

### **Verdict:** **`VERIFIED_LIVE`**

**Justification:**
1. Real official attendance was retrieved directly from iCloudEMS over Chrome DevTools Protocol (`127.0.0.1:9222`).
2. Subject-wise attendance updated truthfully from `231/280 (82.50%)` to `260/313 (83.07%)`.
3. Day-wise timetable matrix for the current month (`October 2026`) retrieved `136` period observations (`73/100`).
4. Data provenance, checksum deduplication, and multi-semester isolation were fully verified in the local SQLite database.
5. React dashboard automatically updated and verified across all three reporting layers with zero manual Refresh clicks.
6. All 292 automated tests and quality gates pass with zero regressions.

---

## 16. Recommended Next Milestone

With the normal daily workflow (`Double-Click AttendPlan → Show Cached Attendance → Auto-Authenticate → Fetch Current Term & Month → Persist → Update Dashboard`) fully proven and accepted live:
- **Phase D: Historical Archive Completion & Academic Marks Pilot:** Safely backfill remaining historical semesters (Semesters 1-3) and evaluate internal marks integration under user supervision.
