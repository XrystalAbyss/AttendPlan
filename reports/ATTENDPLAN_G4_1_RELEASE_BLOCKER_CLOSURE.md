# ATTENDPLAN — PHASE G.4.1 FIRST-USER RELEASE-BLOCKER CLOSURE REPORT

**Milestone:** Phase G.4.1  
**Target Release Candidate:** AttendPlan 0.1.0-beta.5  
**Active Git Branch:** `feature/g4-real-beta-recovery`  
**Base Branch:** `main` (`ad75bdc3d131ab582070d9a2f25447b96928ba10`)  
**Repository:** `https://github.com/XrystalAbyss/AttendPlan`  
**Date:** November 14, 2026  
**Auditor / Implementation:** Google Antigravity (Principal Desktop Release Engineer & Security Auditor)

---

## 1. Executive Summary & Mission Objectives

Phase G.4.1 was initiated immediately following real-world friends-beta feedback on candidate `0.1.0-beta.4`. While beta.4 succeeded in providing windowed execution, dedicated Chromium session management, and onboarding guidance, first-user testing exposed several critical release-blocking defects in academic performance retrieval, process shutdown reliability, browser fallback semantics, and documentation consistency.

All identified defects have been systematically remediated in the source tree, verified through comprehensive automated unit and domain test suites, and packaged into a clean, verified release candidate: **`AttendPlan-0.1.0-beta.5-Setup.exe`**. All previous candidate binaries (`beta.1`, `beta.2`, `beta.3`, and `beta.4`) have been strictly preserved on disk and in checksum manifests without overwrites or data loss.

---

## 2. Root Cause Analysis & Defect Remediation

### Defect 1: Performance Import Approval Gating (`view === "results"` vs `view === "marks"`)
- **Root Cause:** In `frontend/src/components/PerformanceView.tsx` line 481, the approval button was wrapped in an invalid condition: `{view === "results" && preview.data && (...)`. Because internal continuous evaluation assessments are categorized under `view === "marks"`, users previewing valid marks scopes could never render the "Approve this performance import" button.
- **Remediation:** Changed gating condition to `{view === "marks" && preview.data && (...)`. Approval is now exclusively rendered for validated marks previews. In addition, when `view === "results"` is selected, previewing is disabled and a clear status disclosure is shown explaining that official semester results live portal imports have been retired.

### Defect 2: Results Live Retrieval Retirement & Type-4 External Exam Scope Rejection
- **Root Cause:** The university portal's live results route is retired/unreachable for live query scraping, and external end-semester exams (`exam_type == "4"`) do not contain continuous evaluation breakdowns.
- **Remediation:**
  1. Both `/api/v1/performance/preview` and `/api/v1/performance/import` now explicitly reject `payload.view == "results"` with HTTP 400.
  2. Both endpoints and `approval_scope` reject `payload.exam_type == "4"` with HTTP 400.
  3. `backend/app/adapters/performance_portal.py` filters out `exam_type == "4"` during `discover_scopes()`, and raises `PortalSafetyError("EXTERNAL_EXAM_SCOPE_REJECTED")` if encountered in `validate_scope()` or `extract_marks()`.

### Defect 3: Single-Use Approval, Expiry, and Strict Payload Reuse
- **Root Cause:** The import endpoint previously permitted fallback re-fetching if `captured_payload` was absent from sync job details.
- **Remediation:** In `backend/app/api/performance_routes.py`, `capture_performance` now strictly requires `payload.approval_id`, validates that the job state is `COMPLETED` within a 30-minute window, atomically transitions it to `APPROVED` (preventing replay attacks), and strictly reuses `job_details["captured_payload"]`. If `captured_payload` is missing, HTTP 409 is returned instead of silently re-fetching.

### Defect 4: Desktop Launcher Process Shutdown Isolation
- **Root Cause:** When `backend/launcher.py` executed as `__main__`, the `/shutdown` endpoint previously executed `import launcher`, which created a distinct module namespace. Modifying `launcher.SHUTDOWN_EVENT` inside the second namespace had zero effect on the main thread running in `__main__`.
- **Remediation:** Attached the shutdown controller directly to FastAPI's `app.state.trigger_shutdown` during launcher initialization. The controller sets `SHUTDOWN_EVENT.set()` and `server.should_exit = True`. The `/shutdown` endpoint now calls `request.app.state.trigger_shutdown()`, verifies that callers originate strictly from local loopback (`127.0.0.1`, `localhost`, `::1`, `testclient`), and rejects cross-site requests (`sec-fetch-site == "cross-site"`).

### Defect 5: Chromium Fallback Silently Launching Firefox
- **Root Cause:** In `launcher.py`, if Chromium was not detected, `launch_unified_browser()` silently called `webbrowser.open(target_url)`, launching the user's default browser (e.g., Firefox), fragmenting the user experience and violating CDP integration expectations.
- **Remediation:** Refactored `launch_unified_browser()` to accept `allow_default_browser: bool = False`. If Chromium is unavailable, it returns `{"success": False, "mode": "none", "guidance": "..."}` without launching any browser. Added `--open-default-browser` CLI flag to permit system browser fallback only when explicitly requested in degraded mode.

### Defect 6: Documentation Citation Typo (`portal.amity.edu` -> `mrei.icloudems.com`)
- **Root Cause:** An editorial typo in `reports/ATTENDPLAN_G4_REAL_BETA_RECOVERY.md` mistakenly cited `portal.amity.edu`.
- **Remediation:** Corrected the citation to `https://mrei.icloudems.com/corecampus/index.php`. Added an automated regression test (`test_university_source_origin_regression` in `test_launcher_and_shutdown.py`) that strictly asserts all portal origins, base URLs, and allowlists match Manav Rachna (`mrei.icloudems.com`).

### Defect 7: Installer Checksum Reconciliation and SmartScreen Disclosures
- **Root Cause:** Clarified cryptographic checksums and authenticode signing status for Windows SmartScreen.
- **Remediation:** Verified the physical binary `AttendPlan-0.1.0-beta.4-Setup.exe` with `Get-FileHash` (`160664cdb70f068f142c0611398b1f1bb579b38ee47dc2dc7d1bf7bd87df1486`, 81,650,698 bytes) and confirmed `Status: NotSigned`. Clarified in documentation that SmartScreen warnings occur due to the absence of a commercial EV code-signing certificate (which costs hundreds of dollars annually and is not viable for non-commercial student open source), rather than any security fault.

---

## 3. Physical Release Candidates & Checksum Audit

All five historical and current installer binaries are physically present in `release-candidates/` with zero data loss or file modification:

| Release Candidate | Version | File Size (Bytes) | SHA-256 Checksum | Authenticode Status | Release Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`AttendPlan-0.1.0-beta.1-Setup.exe`** | `0.1.0-beta.1` | 81,630,124 | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` | NotSigned | Historical Baseline |
| **`AttendPlan-0.1.0-beta.2-Setup.exe`** | `0.1.0-beta.2` | 81,636,792 | `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311` | NotSigned | Superseded by beta.3 |
| **`AttendPlan-0.1.0-beta.3-Setup.exe`** | `0.1.0-beta.3` | 81,644,316 | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` | NotSigned | Superseded by beta.4 |
| **`AttendPlan-0.1.0-beta.4-Setup.exe`** | `0.1.0-beta.4` | 81,650,698 | `160664cdb70f068f142c0611398b1f1bb579b38ee47dc2dc7d1bf7bd87df1486` | NotSigned | Superseded by beta.5 |
| **`AttendPlan-0.1.0-beta.5-Setup.exe`** | `0.1.0-beta.5` | 81,653,350 | `ca31c1d34e8d902eaffbc0710e94bcdc6afe2baee77fe3611608cabe1e6d6aa8` | NotSigned | **Active Friends-Beta Candidate** |

Both `release-candidates/SHA256SUMS.txt` and `release-candidates/RELEASE_MANIFEST.json` have been synchronized to reflect these exact values.

---

## 4. Verification Evidence & Quality Gates

### Gate 1: Security & Sanitization Audit
```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_sanitization.py -v
============================== 14 passed in 5.94s ==============================
```
- Zero student PII (names, roll numbers, credentials, tokens) in tracked repositories, fixtures, code, or documentation.

### Gate 2: Full Backend Test Suite
```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q
349 passed, 1 warning in 37.62s
```
- All 349 backend tests passed cleanly (including 12 in `test_performance.py` and 3 in `test_launcher_and_shutdown.py`).

### Gate 3: Python Linting & Formatting
```powershell
.\backend\.venv\Scripts\python.exe -m ruff check backend/app backend/launcher.py backend/tests/test_launcher_and_shutdown.py
All checks passed!
```

### Gate 4: Python Static Type Checking
```powershell
.\backend\.venv\Scripts\python.exe -m mypy backend/app backend/launcher.py
Success: no issues found in 47 source files
```

### Gate 5: Frontend Unit & Integration Tests
```cmd
npm --prefix frontend test -- --run
Test Files  13 passed (13)
     Tests  41 passed (41)
  Duration  106.79s
```
- All 41 frontend tests passed across 13 test files (including 5 in `PerformanceView.test.tsx`).

### Gate 6: Frontend TypeScript Check
```cmd
npm --prefix frontend run typecheck
> tsc --noEmit
(0 errors)
```

### Gate 7: Production Frontend Build
```cmd
npm --prefix frontend run build
dist/index.html                   1.22 kB │ gzip:   0.56 kB
dist/assets/index-BPThgNRJ.css   79.96 kB │ gzip:  14.19 kB
dist/assets/index-BTXvsBWw.js   463.82 kB │ gzip: 123.42 kB
✓ built in 14.01s
```

### Gate 8: Standalone Windows Packaging
- PyInstaller: compiled self-contained runtime into `dist/AttendPlan` (no external Python needed).
- Inno Setup 6: generated `release-candidates/AttendPlan-0.1.0-beta.5-Setup.exe` in 153.8 sec.

---

## 5. Summary of Files Changed

- `backend/app/adapters/performance_portal.py`: Exclude Type-4 scopes during discovery and raise `PortalSafetyError` on Type-4 validation or extraction.
- `backend/app/api/performance_routes.py`: Reject `view == "results"` with 400; reject `exam_type == "4"` with 400; enforce `approval_id`, 30-minute expiry, single-use approval, and strict reuse of `captured_payload`.
- `backend/app/api/startup_routes.py`: Connect `/shutdown` to `app.state.trigger_shutdown`; restrict to loopback callers; reject cross-site requests.
- `backend/launcher.py`: Refactor `launch_unified_browser` to eliminate silent Firefox fallback; add `--open-default-browser` flag; inject shutdown controller into `app.state`; bump version to `0.1.0-beta.5`.
- `backend/app/__init__.py`: Bump `__version__` to `0.1.0-beta.5`.
- `frontend/src/components/PerformanceView.tsx`: Unblock marks approval button (`view === "marks"`); show retirement banner for results; render course count in preview; add action button in empty state; display error alerts.
- `frontend/src/components/SettingsView.tsx`: Bump displayed version to `0.1.0-beta.5 (Supervised Friends Beta)`.
- `installer/attendplan_setup.iss`: Bump `MyAppVersion` to `0.1.0-beta.5`.
- `backend/tests/test_performance.py`: Update tests to enforce 400 on results/type-4 scopes, verify preview count, and test single-use replay protection.
- `backend/tests/test_launcher_and_shutdown.py`: New regression tests for shutdown endpoint security, browser fallback semantics, and university source allowlist.
- `frontend/src/tests/PerformanceView.test.tsx`: Expanded test suite covering empty state action, marks approval flow, results view retirement, scope change reset, and error display.
- `release-candidates/RELEASE_MANIFEST.json`: Added `AttendPlan-0.1.0-beta.5-Setup.exe` as active candidate; preserved all historical candidates.
- `release-candidates/SHA256SUMS.txt`: Added beta.5 checksum; preserved beta.1 through beta.4.
- `README.md` & `docs/FRIENDS_BETA_TESTING_GUIDE.md`: Updated version references, test counts, and installer checksum.
- `reports/ATTENDPLAN_G4_REAL_BETA_RECOVERY.md`: Corrected university portal citation typo.

---

## 6. Next Actions

1. Commit changes to `feature/g4-real-beta-recovery`.
2. Push branch to `origin feature/g4-real-beta-recovery`.
3. Open Pull Request to merge `feature/g4-real-beta-recovery` into `main`.
4. Distribute `AttendPlan-0.1.0-beta.5-Setup.exe` to volunteer students for supervised friends-beta testing.
