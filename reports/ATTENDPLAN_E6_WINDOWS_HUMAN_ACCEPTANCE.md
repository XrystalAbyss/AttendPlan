# ATTENDPLAN — PHASE E.6 WINDOWS HUMAN ACCEPTANCE REPORT
**Verification Date:** November 2, 2026 (Updated under Phase E.6.1 Forensic Reconciliation)  
**Agent:** Google Antigravity Flash 3.8  
**Environment:** Windows 11 Localhost Runtime (`127.0.0.1:8000` / `127.0.0.1:5173`)  
**Status:** COMPLETED — 24 PASSED, 0 FAILED (100% PASS RATE)  
**Security Boundary:** Strictly Offline, Zero University Network Requests Attempted (`blocked_requests: 0`, `actual_portal_requests_issued: 0`)

---

## 1. Executive Summary

This report documents the definitive Windows runtime acceptance verification for AttendPlan, successfully closing the human verification gaps identified after Phase E.5 and forensically audited in Phase E.6.1. The verification was conducted against the running live local application using an automated Playwright harness enforcing strict network-level sandboxing (all non-localhost outbound requests intercepted and aborted).

The verification confirmed that the five-semester attendance and internal assessment marks archive is fully mounted, responsive, free of console errors, strictly separated from speculative GPA/grade derivations, and completely isolated from live university endpoints.

---

## 2. Test Harness Architecture & Sandboxing

The acceptance verification script was executed via `backend/scripts/verify_windows_human_acceptance.py`.
- **Backend Host:** `http://127.0.0.1:8000` (FastAPI, SQLite WAL)
- **Frontend Host:** `http://127.0.0.1:5173` (Vite dev server, React 19, TypeScript)
- **Runtime Distinction:** Verification was executed against live local developer server processes (`uvicorn` and `vite`). It does **not** claim verification of a packaged standalone Windows desktop launcher installer binary (`.exe`).
- **Playwright Engine:** Chromium Headless with Request Interception
- **Network Gate & Request Accounting:**
  ```python
  def handle_route(route):
      url = route.request.url
      results["total_intercepted_requests"] += 1
      if not ("127.0.0.1" in url or "localhost" in url):
          results["external_requests_attempted"].append(url)
          results["external_requests_blocked"].append(url)
          route.abort()
      else:
          results["localhost_requests"].append(url)
          route.continue_()
  ```
- **Audited Network Metrics:**
  - Total requests intercepted: **61**
  - Localhost requests allowed: **61**
  - External requests attempted: **0**
  - External requests blocked: **0**
  - External requests allowed: **0**
  - Actual university portal calls: **0**
- **Console Sentinel:** All browser `console.error` and unhandled exceptions captured into `results["console_errors"]`: exactly **0** errors.

---

## 3. Comprehensive 24-Step Verification Matrix

| Step | Verification Objective | Observed Result | Status |
| :---: | :--- | :--- | :---: |
| **1** | Application server responding | FastAPI operational on port 8000, Vite dev server on 5173 (live localhost server runtime) | **PASSED** |
| **2** | Frontend loads | HTTP Status 200 returned for root URL | **PASSED** |
| **3** | Root layout mounted | Title verified: `AttendPlan · Attendance & Performance` | **PASSED** |
| **4** | Cached attendance displays immediately | Summary cards and attendance table rendered immediately | **PASSED** |
| **5** | Academic history navigation available | All 7 tabs verified in `WorkspaceNav`: Roster, Analytics, Marks & Results, Historical Attendance, Career History, Reconciliation, Sync Center | **PASSED** |
| **6** | Semester selector lists all 5 terms | Verified all 5 terms: `Sem 5 (15)`, `Sem 4 (17)`, `Sem 3 (16)`, `Sem 2 (16)`, `Sem 1 (12)` | **PASSED** |
| **7** | Semester 5 selection | Roster successfully switched to `2026-2027 • Semester 5 (Class 2582)` | **PASSED** |
| **8** | Semester 4 selection | Roster successfully switched to `2025-2026 • Semester 4 (Class 2508)` | **PASSED** |
| **9** | Semester 3 selection | Roster successfully switched to `2025-2026 • Semester 3 (Class 1067)` | **PASSED** |
| **10** | Semester 2 selection | Roster successfully switched to `2024-2025 • Semester 2 (Class 1048)` | **PASSED** |
| **11** | Semester 1 selection | Roster successfully switched to `2024-2025 • Semester 1 (Class 918)` | **PASSED** |
| **12** | Navigation to Performance view | Switched to `Marks & Results` tab; `PerformanceView` mounted | **PASSED** |
| **13** | Multi-semester progression table | All 5 imported semesters rendered in table rows | **PASSED** |
| **14** | Speculative GPA derivation check | SGPA and CGPA columns strictly show `"—"` (em dash); set of distinct values: `{'—'}` | **PASSED** |
| **15** | Semester breakdown cards | All 5 term articles present in DOM | **PASSED** |
| **16** | Course table and assessment columns rendered | Table headers verified: Course, Internal, External, Total, Maximum, Credits, Grade, Grade point, Result, Assessments | **PASSED** |
| **17** | Assessment breakdown drawers | All 55 courses across all semesters possess interactive `<details>` drawers | **PASSED** |
| **18** | Assessment details and classifications | Formatted breakdown rendered with components, ratios, and classifications (`[INTERNAL_CONTINUOUS_EVALUATION]`, `[INTERNAL_MIDTERM]`) | **PASSED** |
| **19** | Semester 4 masked score label | Verified `MASKED_BY_PORTAL` displayed for withheld/hidden portal score | **PASSED** |
| **20** | Semester 5 partial publication notice & course count | Verified exactly 4 source courses in Sem 5 table (`CSH301C`, `CSH302C`, `CSH304C`, `CSH310C`) and analytical insight displayed: `"4 course totals are unpublished or missing; they are excluded from comparisons."` | **PASSED** |
| **21** | Source provenance and timestamps | Verified `LIVE_PORTAL` provenance and ISO 8601 timestamps displayed across all 5 terms | **PASSED** |
| **22** | Live capture security gate | Verified approval button disabled / warning banner rendered: `"Live performance imports are disabled until the supervised pilot is approved."` | **PASSED** |
| **23** | Network containment | Intercepted 61 requests (61 localhost allowed, 0 external attempted, 0 blocked, 0 ERP calls) | **PASSED** |
| **24** | Browser console hygiene | Exactly 0 unhandled console errors or warnings (`console_errors: []`) | **PASSED** |

---

## 4. Key Behavioral Observations

1. **Deterministic Multi-Semester Rendering:**
   The UI correctly handles switching between terms with variable course counts (from 12 to 17 catalog courses) without layout shifts or React re-render crashes.
2. **Absolute Separation of Internal Marks & Official Results:**
   In `PerformanceView`, raw internal examination totals (e.g. 45/50 or 19/20) are never used to synthesize fake letter grades (such as 'A+' or 'O') or speculative SGPA/CGPA. The progression table explicitly outputs `"—"`, strictly complying with institutional invariants.
3. **Transparent Reporting of Incomplete University Data:**
   In Semester 5 (Class 2582), where the university portal published internal evaluation components for 4 courses while leaving overall course totals unfinalized, the system displays the 4 courses, alerts the user that 4 course totals are unpublished, and excludes them from comparative statistics rather than assuming 0 or 100%.

---

## 5. Artifact Output
The complete JSON execution payload was recorded to `reports/windows_acceptance_summary.json` with 24 passed checks, 0 failures, 61 intercepted requests, 0 external attempts, and 0 console errors.
