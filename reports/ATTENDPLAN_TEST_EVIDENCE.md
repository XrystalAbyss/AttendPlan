# AttendPlan Comprehensive Test Evidence (Phase B)
**Date:** October 2026  
**Environment:** Windows 11, Python 3.12.10, Node.js v20+, Vite 6.4.4, Playwright, SQLite 3 (WAL mode)

---

## 1. Test Summary & Quality Gates

| Test Suite / Tool | Command | Collected Items | Outcome | Execution Time |
|---|---|---|---|---|
| **Backend Unit & Integration Tests** | `pytest backend/tests` | 234 tests | **234 PASSED**, 0 failed | 15.65s |
| **Current Refresh Suite** | `pytest backend/tests/test_current_refresh.py` | 6 tests | **6 PASSED** | 1.80s |
| **Startup Coordinator Suite** | `pytest backend/tests/test_startup.py` | 9 tests | **9 PASSED** | 1.97s |
| **API Route Inventory & Contract** | `pytest backend/tests/test_api.py` | 5 tests | **5 PASSED** | 1.85s |
| **Historical & Marks Archive** | `pytest backend/tests/test_archive.py backend/tests/test_performance.py` | 17 tests | **17 PASSED** | 3.10s |
| **Database Migrations & Integrity** | `pytest backend/tests/test_migration.py backend/tests/test_database.py` | 7 tests | **7 PASSED** | 4.87s |
| **Launcher Scripts** | `pytest backend/tests/test_launchers.py` | 12 tests | **12 PASSED** | 4.09s |
| **Sanitization & PII Scrubbing** | `pytest backend/tests/test_sanitization.py` | 11 tests | **11 PASSED** | 1.69s |
| **Python Static Linter** | `ruff check backend/app backend/tests` | 79 files | **All checks passed** | 0.82s |
| **Python Static Typechecker** | `mypy backend/app backend/tests` | 79 source files | **Success: no issues found** | 18.20s |
| **Frontend Unit & Component Tests** | `vitest run --run` | 37 tests (13 files) | **37 PASSED**, 0 failed | 12.04s |
| **Frontend TypeScript Typecheck** | `tsc --noEmit` | Entire project | **0 errors** | 2.10s |
| **Frontend Production Build** | `npm.cmd run build` | 1648 modules | **Built cleanly** | 6.64s |

---

## 2. Backend Test Output Log (`pytest backend/tests`)

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.5, pluggy-1.7.0
rootdir: C:\Users\astra\Desktop\Project\AttendPlan
plugins: anyio-4.15.1
collected 234 items

backend\tests\test_analytics_and_reconciliation.py .........             [  3%]
backend\tests\test_api.py .....                                          [  5%]
backend\tests\test_archive.py .....                                      [  8%]
backend\tests\test_attendance_engine.py ...........                      [ 12%]
backend\tests\test_auth_preferences.py ..                                [ 13%]
backend\tests\test_auth_tab_selection.py ....                            [ 15%]
backend\tests\test_current_refresh.py ......                             [ 17%]
backend\tests\test_database.py .....                                     [ 20%]
backend\tests\test_f1_api.py ........                                    [ 23%]
backend\tests\test_f2b_api.py ....                                       [ 25%]
backend\tests\test_f2c_auth_api.py ...                                   [ 26%]
backend\tests\test_historical_analytics.py ...                           [ 27%]
backend\tests\test_historical_api.py .........                           [ 31%]
backend\tests\test_historical_discovery.py ....                          [ 33%]
backend\tests\test_historical_ingestion_and_isolation.py .....           [ 35%]
backend\tests\test_historical_planner.py ...                             [ 36%]
backend\tests\test_html_parser.py ......                                 [ 39%]
backend\tests\test_ingestion_and_daywise.py .......                      [ 42%]
backend\tests\test_keycloak_synthetic_harness.py ......                  [ 44%]
backend\tests\test_launchers.py ............                             [ 50%]
backend\tests\test_login_orchestrator.py ...............                 [ 56%]
backend\tests\test_migration.py ..                                       [ 57%]
backend\tests\test_performance.py ............                           [ 62%]
backend\tests\test_period_ledger.py .                                    [ 62%]
backend\tests\test_portal_discovery.py ..............                    [ 68%]
backend\tests\test_portal_safety.py ....................                 [ 77%]
backend\tests\test_qr_parser.py ........                                 [ 80%]
backend\tests\test_report_scope.py .....                                 [ 82%]
backend\tests\test_sanitization.py ...........                           [ 87%]
backend\tests\test_settings_service.py ....                              [ 89%]
backend\tests\test_startup.py .........                                  [ 93%]
backend\tests\test_sync_job_service.py .....                             [ 95%]
backend\tests\test_totp_engine.py ....                                   [ 97%]
backend\tests\test_totp_vault.py .......                                 [100%]

============================== warnings summary ===============================
backend\.venv\Lib\site-packages\starlette\testclient.py:37
  C:\Users\astra\Desktop\Project\AttendPlan\backend\.venv\Lib\site-packages\starlette\testclient.py:37: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 234 passed, 1 warning in 15.65s =======================
```

---

## 3. Frontend Test Output Log (`vitest run --run`)

```text
 RUN  v2.1.9 C:/Users/astra/Desktop/Project/AttendPlan/frontend

 ✓ src/tests/ReconciliationView.test.tsx (3 tests) 1963ms
   ✓ ReconciliationView Component > renders reconciliation status badge and explanation 1183ms
   ✓ ReconciliationView Component > renders course breakdown and variance 402ms
   ✓ ReconciliationView Component > renders immutable snapshots list with canonical checksum 375ms
 ✓ src/tests/SemesterSelector.test.tsx (2 tests) 1972ms
   ✓ SemesterSelector Component > renders selected semester details and aggregate percentage 758ms
   ✓ SemesterSelector Component > calls onSelectTerm when changing dropdown selection 1182ms
 ✓ src/tests/SummaryCards.test.tsx (2 tests) 2384ms
   ✓ Attendance overview > keeps zero-buffer caution subjects separate from subjects safe to miss 2034ms
   ✓ Attendance overview > presents zero delivered periods as unknown rather than risk or a percentage 336ms
 ✓ src/tests/AttendanceExplorer.test.tsx (2 tests) 3141ms
   ✓ offers missing months without fabricating absence and previews only the chosen month 3096ms
 ✓ src/tests/AbsenceAnalyticsView.test.tsx (3 tests) 3071ms
   ✓ AbsenceAnalyticsView Component > renders insufficient data warning when no daywise observations exist 722ms
   ✓ AbsenceAnalyticsView Component > renders monthly and weekday breakdowns when data is present 491ms
   ✓ AbsenceAnalyticsView Component > switches ranking tabs between absolute missed, missed rate, and total delivered 1838ms
 ✓ src/tests/PerformanceView.test.tsx (2 tests) 3939ms
   ✓ PerformanceView > shows the missing-data state without inventing results 2093ms
   ✓ PerformanceView > previews one exact semester and keeps capture disabled 1842ms
 ✓ src/tests/StartupConnection.test.tsx (3 tests) 3588ms
   ✓ StartupConnection > keeps saved data available and does not connect without opt-in 1030ms
   ✓ StartupConnection > uses the background connect endpoint without calling import or vault endpoints 704ms
   ✓ StartupConnection > triggers manual current-semester refresh when button is clicked 1845ms
 ✓ src/tests/AuthenticationSettingsModal.test.tsx (4 tests) 3754ms
   ✓ AuthenticationSettingsModal > renders modal header and navigation tabs when open 1613ms
   ✓ AuthenticationSettingsModal > displays masked saved mobile number and automation preferences 673ms
   ✓ AuthenticationSettingsModal > switches to Google Authenticator Vault tab and displays Windows Credential Manager status 1042ms
   ✓ AuthenticationSettingsModal > switches to Automated Login tab and displays login status badge 409ms
 ✓ src/tests/standing.test.ts (1 test) 2ms
 ✓ src/tests/AttendanceTable.test.tsx (4 tests) 4154ms
   ✓ AttendanceTable Component > renders all courses with their codes and titles 1533ms
   ✓ AttendanceTable Component > renders safe bunk margin and consecutive needed correctly 737ms
   ✓ AttendanceTable Component > filters courses when clicking filter pills 1693ms
 ✓ src/tests/ThemeSwitch.test.tsx (3 tests) 111ms
 ✓ src/tests/HistoricalAttendanceView.test.tsx (3 tests) 4473ms
   ✓ HistoricalAttendanceView Component > renders historical attendance header, actions, and discovered terms 3118ms
   ✓ HistoricalAttendanceView Component > renders course roster with exact data and unrecorded courses as '--' 934ms
   ✓ HistoricalAttendanceView Component > allows selecting one semester and triggering preview 405ms
 ✓ src/tests/PortalDiscoveryView.test.tsx (5 tests) 5066ms
   ✓ PortalDiscoveryView Component > renders portal discovery header, diagnostic panels, and initial disconnected state 3297ms
   ✓ PortalDiscoveryView Component > toggles manual HTML fallback input on button click 846ms
   ✓ PortalDiscoveryView Component > renders discovery area cards for Terms, Subject-Wise, Day-Wise, and Overall 380ms
   ✓ PortalDiscoveryView Component > renders F2-B Historical Sync Planner and displays generated multi-semester plan 337ms

 Test Files  13 passed (13)
      Tests  37 passed (37)
   Start at  19:56:17
   Duration  12.04s (transform 7.43s, setup 3.25s, collect 41.50s, tests 37.62s, environment 21.85s, prepare 3.91s)
```

---

## 4. Frontend Production Bundle Build Log

```text
> frontend@0.1.0 build
> tsc -b && vite build

vite v6.4.4 building for production...
transforming...
✓ 1648 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.22 kB │ gzip:   0.57 kB
dist/assets/index-BpM9aCbX.css   71.00 kB │ gzip:  13.08 kB
dist/assets/index-q5KK7X_n.js   465.15 kB │ gzip: 122.79 kB
✓ built in 6.64s
```

---

## 5. Typecheck & Linting Evidence

### `ruff check backend/app backend/tests`
```text
All checks passed!
```

### `mypy backend/app backend/tests`
```text
Success: no issues found in 79 source files
```

### `npm.cmd run typecheck`
```text
> frontend@0.1.0 typecheck
> tsc --noEmit
(Exit code: 0, 0 errors)
```
