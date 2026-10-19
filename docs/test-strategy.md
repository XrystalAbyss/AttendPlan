# AttendPlan Test Strategy

## 1. Test Philosophy
AttendPlan enforces institutional reliability through deterministic offline tests. The test pyramid emphasizes pure domain mathematics, resilient HTML parsing against offline fixtures, relational database integrity, and component-level UI verification.

---

## 2. Test Suites Overview

### 2.1 Backend Tests (`backend/tests/`)
Executed via `pytest`. Current suite contains **69 passing tests (100%)**.

#### Suite 1: Domain Mathematical Invariants (`test_attendance_engine.py`)
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

#### Suite 7: REST API Integration & Route Inventory (`test_api.py`, `test_f1_api.py`)
- Fresh database starts empty: `GET /api/v1/terms` returns `[]`.
- Pure in-memory sample endpoint: `GET /api/v1/attendance/sample` causes zero database insertions.
- Explicit demo seeding: `POST /api/v1/demo/seed` seeds data idempotently.
- Verified route inventory: Automated test validating exact 24 FastAPI application routes.

#### Suite 8: Alembic Migrations (`test_migration.py`)
- Automated verification of `upgrade head`, `downgrade base`, and idempotent re-upgrade.

#### Suite 9: Portal Discovery & Session Management (`test_portal_discovery.py`)
- Dedicated profile directory resides outside git repository.
- Loopback binding verification on `127.0.0.1:9222`.
- Initial disconnected state and clean termination.
- Offline term discovery, subject-wise discovery, day-wise timetable discovery, and overall view discovery.
- Discovery API endpoints and 400 error handling on unattached requests.

---

## 3. Frontend Tests (`frontend/src/tests/`)
Executed via `vitest`. Current suite contains **15 passing tests across 5 test files (100%)**:
1. `AttendanceTable.test.tsx` (4 tests): Roster rendering, margin badges, status filters.
2. `SemesterSelector.test.tsx` (2 tests): Multi-semester dropdown, selection dispatch.
3. `AbsenceAnalyticsView.test.tsx` (3 tests): Monthly & weekday breakdown, ranking dimensions.
4. `ReconciliationView.test.tsx` (3 tests): Scope mismatch & discrepancy badges, audit logs.
5. `PortalDiscoveryView.test.tsx` (3 tests): Header diagnostics, manual fallback toggle, discovery cards.
