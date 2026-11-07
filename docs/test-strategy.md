# AttendPlan Test Strategy

## 1. Test Philosophy
AttendPlan enforces institutional reliability through deterministic offline tests. The test pyramid emphasizes pure domain mathematics, resilient HTML parsing against offline fixtures, relational database integrity, and component-level UI verification.

---

## 2. Test Suites Overview

### 2.1 Backend Tests (`backend/tests/`)
Executed via `pytest`. Current suite contains **265 passing tests (100%)**.

#### Suite 1: Academic Term Calendar & Window Bounds (`test_academic_term_calendar.py`)
- Odd semester defaults: Semesters 1, 3, 5, 7 default strictly to August through November of the academic year start year (denominator 4).
- Even semester provisional defaults: Semesters 2, 4, 6, 8 default to January through May of the academic year end year (denominator 5).
- Academic year boundary crossing: Verifies that academic year `2026-2027` maps Semester 5 to 2026 and Semester 6 to 2027.
- Out-of-window rejection: Requests for June/July summer recess or December examination months are rejected with `OUTSIDE_CALENDAR_WINDOW`.
- User overrides & exceptions: User-approved exceptional months (`EXPLICIT_USER_EXCEPTION`) and custom candidate lists take highest precedence (`USER_CONFIRMED`).
- Database enrichment: Confirmed observation batches and snapshots from SQLite enrich calendar verification status.
- REST API lifecycle: Full verification of `/api/v1/attendance-archive/calendars` listing, detail, update, and reset endpoints.

#### Suite 2: Domain Mathematical Invariants (`test_attendance_engine.py`)
- **Boundary 15/20**: $15/20 \to 75.0\%$, `can_skip = 0`, `must_attend = 0`, status `SAFE`.
- **Under Boundary 10/14**: $10/14 \to 71.4285...\%$, `must_attend = 2`, `can_skip = 0`, status `AT_RISK`.
- **Under Boundary 3/5**: $3/5 \to 60.0\%$, `must_attend = 3`, `can_skip = 0`, status `AT_RISK`.
- **Above Boundary 19/19**: $19/19 \to 100.0\%$, `can_skip = 6` at $t = 0.75$, `must_attend = 0`, status `SAFE`.
- **Zero Case 0/0**: $0/0 \to \text{percent } \text{None}$, `can_skip = None`, `must_attend = None`, status `UNRECORDED`.
- **Simulation Multi-Period**: Missing 2 lab periods changes denominator by 2 ($d \to d + 2$).
- **Bounds Validation**: Reject negative counts ($a < 0$, $d < 0$) and attended exceeding delivered ($a > d$) with `InvalidAttendanceError`.

#### Suite 2: Resilient HTML Parser (`test_html_parser.py`)
- Parse sanitized historical portal fixture table.
- Verify column matching by normalized headers (handles extra whitespace, casing, missing optional columns).
- Verify all 15 expected historical course rows are parsed accurately.
- Handle malformed rows, missing delimiters, non-numeric values gracefully without raising unhandled crashes.

#### Suite 3: Privacy & Sanitization Gate (`test_sanitization.py`)
- Assert tracked test fixtures do NOT contain real student admission numbers, student names, phone numbers, or active session tokens.
- Parameterized verification across `sample_attendance.html`, `synthetic_daywise_attendance.html`, and `synthetic_overall_attendance.html`.

#### Suite 4: Database Persistence & Constraints (`test_database.py`)
- Verify data persists across SQLite engine disposal and session recreation.
- Foreign key enforcement: Rejects orphan child insertions.
- Multi-semester isolation: Identical course codes coexist safely across terms without collision.
- Check constraints: Rejects $a > d$ or negative counts.
- Transaction rollback: Clean rollback on error leaves zero orphaned records.

#### Suite 5: Day-Wise Parsing & Ingestion (`test_ingestion_and_daywise.py`)
- Timetable matrix parsing with period semantics: `P` -> Present, `A` -> Absent, Blank -> `NOT_REPORTED`, explicit cancellation -> `NO_CLASS`.
- Invariant: Blank cells never count as absences.
- Lab period counting: Regression test ensuring two observed 50-minute lab slot rows count as 2 periods, not 4.
- Canonical checksum: SHA-256 remains identical regardless of input row order.
- Idempotent ingestion: Duplicate imports return `DUPLICATE_SKIPPED` without double-counting.

#### Suite 6: Pure Analytics & Reconciliation (`test_analytics_and_reconciliation.py`)
- Monthly analytics: Same month across different years remains strictly separate; verified calendar coverage.
- Weekday analytics: Monday-Sunday mapping and Asia/Kolkata date properties.
- Subject rankings: 3 distinct dimensions (absolute missed, missed rate, total delivered).
- Cross-semester analytics: Never averages course percentages.
- Reconciliation service: Tests `INSUFFICIENT_DATA`, `PARTIAL_COVERAGE`, `MATCHED`, `DISCREPANCY`, and `SCOPE_MISMATCH`.

#### Suite 7: REST API Integration (`test_api.py`, `test_f1_api.py`)
- Fresh database starts empty: `GET /api/v1/terms` returns `[]`.
- Pure in-memory sample endpoint: `GET /api/v1/attendance/sample` causes zero database insertions.
- Explicit demo seeding: `POST /api/v1/demo/seed` seeds data idempotently.

#### Suite 8: Alembic Migrations (`test_migration.py`)
- Automated verification of `upgrade head`, `downgrade base`, and idempotent re-upgrade.

#### Suite 9: Portal Discovery & Session Management (`test_portal_discovery.py`)
- Dedicated profile directory resides outside git repository.
- Loopback binding verification on `127.0.0.1:9222`.
- Initial disconnected state and clean termination.
- Offline term discovery, subject-wise discovery, day-wise timetable discovery, and overall view discovery.
- Discovery API endpoints and 400 error handling on unattached requests.

#### Suite 10: Sync Job State Machine & Pilot Execution (`test_sync_job_service.py`)
- Job state transitions through 15 states.
- Mutual exclusion lock (`_SYNC_LOCK`) rejecting concurrent execution with HTTP 409 Conflict.
- Pilot sync orchestration (Subject snapshot + 1 month day-wise + SQLite persistence + reconciliation).
- Cancellation propagation.

#### Suite 11: Historical Sync Planner (`test_historical_planner.py`)
- Academic year discovery and semester seasonality mapping (Odd: Aug-Dec, Even: Jan-May).
- Exact HTTP request estimation formula without recursive brute-forcing.
- Skip logic for already persisted terms/batches.

#### Suite 12: F2-B REST API Endpoints & Route Inventory (`test_f2b_api.py`)
- Verified route inventory: Automated test validating exact FastAPI application routes.
- Subject-wise live sync endpoint (`/api/v1/portal/sync/subject-wise`).
- Day-wise live sync endpoint (`/api/v1/portal/sync/day-wise`).
- Historical sync plan endpoint (`/api/v1/portal/sync/historical-plan`).

#### Suite 13: Windows Launchers & Port Guardrails (`test_launchers.py`)
- Validates double-click launcher scripts (`Launch-AttendPlan.ps1`, `Launch-Chrome.ps1`, `Stop-AttendPlan.ps1`).
- Modern DevTools HTTP PUT `/json/new` target creation with GET fallback.
- Ownership-checked shutdown guardrails protecting unrelated processes.

#### Suite 14: Historical Term Discovery (`test_historical_discovery.py`)
- Selectors discovery across 5 academic years, 5 semesters, and 5 distinct class IDs.
- Discovery statuses: `AVAILABLE`, `EMPTY`, `INACCESSIBLE`, `UNKNOWN`, `FAILED`, `NOT_CHECKED`.
- Invariant: Zero assumption of hardcoded year-to-semester mapping.

#### Suite 15: Historical Ingestion, Deduplication & Isolation (`test_historical_ingestion_and_isolation.py`)
- Multi-semester isolation: Identical course codes in Semesters 1 and 4 coexist cleanly without count pollution.
- Structural row exclusion: Table rows containing `"Lecture Timings"` are excluded from period observations.
- Idempotency: Re-running backfill on the same semester updates views without duplicate records or inflated absence totals.
- Existing Semester 5 data verification: Zero regression on active semester pilot records.

#### Suite 16: Multi-Term Historical Analytics (`test_historical_analytics.py`)
- Exact rational percentage calculation without floating point distortion around 75% boundary.
- Cross-semester aggregate formula: $\frac{\sum a_i}{\sum d_i}$, never the average of percentages.
- Weekday and monthly breakdown aggregation from actual recorded dates without data invention.

#### Suite 17: Historical REST API Integration (`test_historical_api.py`)
- Route inventory check verifying all registered application endpoints.
- Endpoints: `/historical/terms`, `/historical/discover`, `/historical/preview`, `/historical/import`, `/historical/overview`, and `/terms/{term_id}/coverage`.

#### Suite 18: Current-Term Live Refresh & Service A (`test_current_refresh.py`)
- Dynamic term resolution without hardcoded semester values (`resolve_current_term`).
- Subject-wise summary extraction and deduplication into immutable snapshots.
- Day-wise current month period extraction and transactional ingestion.
- Multi-term isolation preventing cross-term contamination.
- Reconciliation metric recalculation.

#### Suite 19: Startup Coordinator & Preferences (`test_startup.py`)
- Automatic startup triggering with `auto_refresh_current_term`.
- Execution debounce and concurrent tab deduplication.
- Dedicated manual on-demand `/refresh-current` endpoint.

---

## 3. Frontend Tests (`frontend/src/tests/`)
Executed via `vitest`. Current suite contains **37 passing tests across 13 test files (100%)**:
1. `AttendanceTable.test.tsx` (4 tests): Roster rendering, margin badges, status filters, lab badges.
2. `SemesterSelector.test.tsx` (2 tests): Multi-semester dropdown, selection dispatch.
3. `AbsenceAnalyticsView.test.tsx` (3 tests): Monthly & weekday breakdown, ranking dimensions.
4. `ReconciliationView.test.tsx` (3 tests): Scope mismatch & discrepancy badges, audit logs.
5. `PortalDiscoveryView.test.tsx` (5 tests): Header diagnostics, manual fallback toggle, discovery cards, Live Sync Center, and Historical Sync Planner.
6. `AuthenticationSettingsModal.test.tsx` (4 tests): Saved mobile masking, TOTP vault tab, auto-login state machine display.
7. `HistoricalAttendanceView.test.tsx` (3 tests): Discovered term roster rendering, unrecorded course `--` formatting, and multi-term sync controls.
8. `StartupConnection.test.tsx` (3 tests): Saved attendance display, background connect, manual current refresh action.
9. `PerformanceView.test.tsx` (2 tests): Missing-data states, single semester preview.
10. `AttendanceExplorer.test.tsx` (2 tests): Missing months without fabricating absence, single month preview.
11. `SummaryCards.test.tsx` (2 tests): Zero-buffer caution subjects separate from safe subjects, zero delivered unrecorded display.
12. `standing.test.ts` (1 test): Domain standing calculations and threshold logic.
13. `ThemeSwitch.test.tsx` (3 tests): Theme toggles and preference persistence.

**Total Automated Test Count across Monorepo**: **271 passing tests** (234 backend + 37 frontend).


