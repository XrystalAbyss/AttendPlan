# ATTENDPLAN — PHASE D.6
# Targeted Historical Gap Recovery: Offline Preparation & Verification
## Scope A (January 2025) & Scope B (July 2025)

**Phase Status:** **AWAITING_USER_APPROVAL**  
**Execution Boundary:** **STRICT OFFLINE PREPARATION COMPLETED — ZERO LIVE REQUESTS EXECUTED**  
**Audit Timestamp:** 2026-11-01T16:45:00+05:30  
**Security Boundary:** Localhost Bound (`127.0.0.1`), Read-Only ERP Portal Adapter, Zero Credential Storage  

---

## 1. Executive Summary & Authorization Boundary

Phase D.6 targets the safe offline engineering preparation for recovering the two remaining unverified calendar gaps in the AttendPlan historical attendance archive:
1. **Scope A — Semester 2 (January 2025)**: Academic Year `2024-2025`, Semester `2`, Class ID `1048` (`B.Tech CSE AIML-Sem 2`). Unverified gap: $\Delta = +85 \text{ attended} / +90 \text{ delivered}$.
2. **Scope B — Semester 3 (July 2025)**: Academic Year `2025-2026`, Semester `3`, Class ID `1067` (`B.Tech CSE AIML-Sem 3`). Unverified gap: $\Delta = +27 \text{ attended} / +27 \text{ delivered}$.

### Strict Authorization Boundary
In accordance with `AGENTS.md` and Phase D.6 operating rules:
- **Neither Scope A nor Scope B has been executed live.**
- **Zero requests have been sent to the university portal.**
- **No synthetic or placeholder attendance has been fabricated in SQLite.**
- The pre-execution technical audit, postback selector hardening, calendar exception model, documentation reconciliation, and offline regression test suites have all been completed and verified.
- The system is stopped at **`AWAITING_USER_APPROVAL`** pending the user's explicit authorization for the exact two-request live execution.

---

## 2. Preflight & Database Integrity Verification

Before beginning offline technical preparation, full SQLite physical and relational checks were executed:
- **`PRAGMA integrity_check;`**: Returned `ok` (0 physical corruption flags).
- **`PRAGMA foreign_key_check;`**: Returned empty list (0 relational integrity violations).
- **Consistent WAL Checkpoint & Backup**:
  - `PRAGMA wal_checkpoint(TRUNCATE);` executed cleanly.
  - Consistent SQLite backup created at:
    `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_d6_backup_20261101_163511.sqlite3` (1,781,760 bytes).

---

## 3. Semester 4 Discrepancy Documentation Resolution

### 3.1 Documentation Conflict
In earlier Phase D.1/D.2 reports, Semester 4 was noted to have 9 uncredited periods associated with `NOT_REPORTED` timetable slots on February 26, 2026 and April 8, 2026. However, in Phase D.4 narrative documentation, a conflicting conjecture referenced "May 2–16 exam periods".

### 3.2 Definitive Database Audit
A forensic query of the SQLite database (`academic_term_id = '53d60f23-e8ac-4077-a0ce-27e62aa311b9'`) established the exact physical reality:
- **Official Subject-Wise Summary (Snapshot Rows)**: 17 courses, **485 attended / 554 delivered**.
- **Day-Wise Observations (January–May 2026)**:
  - `PRESENT`: 476 periods.
  - `ABSENT`: 69 periods.
  - `NOT_REPORTED`: 184 periods.
  - Delivered periods recorded in day-wise ledger (`PRESENT + ABSENT`): $476 + 69 = \mathbf{545}$.
- **Mathematical Discrepancy**:
  - $\Delta \text{Attended} = 485 - 476 = \mathbf{9}$.
  - $\Delta \text{Delivered} = 554 - 545 = \mathbf{9}$.

### 3.3 Course-by-Course Root Cause
Every single one of the 9 discrepant periods is 100% accounted for by specific `NOT_REPORTED` periods that were credited in the university's subject summary:

| Course Code | Course Name | Summary ($a/d$) | Day-Wise ($a/d$) | Delta | Specific Date & Period Details |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `CSH215C` | Computer Networks | 36 / 42 | 35 / 41 | **+1 / +1** | 2026-04-08 (08:10–09:00): `COMPUTER NETWORKS (PP)` `NOT_REPORTED` |
| `ECH108C` | Digital Electronics | 31 / 39 | 30 / 38 | **+1 / +1** | 2026-02-26 (12:20–13:10): `DIGITAL ELECTRONICS (PP)` `NOT_REPORTED` |
| `MCS368C` | Entrepreneurship | 21 / 24 | 20 / 23 | **+1 / +1** | 2026-02-26 (10:40–11:30): `ENTREPRENEURSHIP (PP)` `NOT_REPORTED` |
| `CDO232` | PCE-II | 47 / 58 | 45 / 56 | **+2 / +2** | 2026-02-26 (13:10–14:00) & 2026-04-08 (09:00–09:50) `NOT_REPORTED` |
| `CSH213C` | Software Engineering | 25 / 33 | 23 / 31 | **+2 / +2** | 2026-02-26 (09:50–10:40) & 2026-04-08 (12:20–13:10) `NOT_REPORTED` |
| `CSH214C` | Software Engineering Lab | 22 / 26 | 20 / 24 | **+2 / +2** | 2026-04-08 (14:00–15:40, 2-period lab block) `NOT_REPORTED` |
| *11 other courses* | *(Various)* | *(Matches)* | *(Matches)* | **0 / 0** | Exact 100% parity |
| **Total** | | **485 / 554** | **476 / 545** | **+9 / +9** | **Feb 26 (4 periods) + Apr 8 (5 periods) = exactly 9** |

### 3.4 Resolution of the May 2026 Conjecture
Inspection of the May 2026 observations in SQLite revealed:
- Classes were held only on **May 1, 2026** (9 periods: 1 DT, 1 ML, 3 ANN, 4 ANN Lab).
- All 9 periods were attended (`PRESENT`) and **matched their subject summaries perfectly**.
- There were zero unrecorded or missing classes in May 2026.
- **Conclusion**: The phrase "May 2–16 exam periods" in Phase D.4 was an unverified hypothesis. The authoritative explanation is that the university awarded institutional credit for 4 periods on February 26, 2026 and 5 periods on April 8, 2026 despite recording them as `NOT_REPORTED` on the timetable matrix.

---

## 4. Scope A: Semester 2 (January 2025) Offline Technical Preparation

### 4.1 Scope Specification
- **Academic Year:** `2024-2025`
- **Semester:** `2`
- **Class Identifier:** `1048` (`B.Tech CSE AIML-Sem 2`)
- **Target Calendar Month:** `2025-01` (`2025-01-01` to `2025-01-31`)
- **Unverified Gap:** 85 attended / 90 delivered.

### 4.2 Portal DOM & Asynchronous Postback Analysis
Direct inspection of `myattendance.php` revealed:
1. The month dropdown `<select id="month">` carries attribute `name="users"` (not `name="month"`).
2. It has CSS class `select2-hidden-accessible` and is initialized as a **jQuery Select2** widget.
3. It has an inline event handler `onchange="getMonthDate(this.value, acadyear.value)"`.
4. `getMonthDate` initiates two asynchronous `XMLHttpRequest` calls:
   - `getClassesSurvey1.php?year=...&method=getMonthFromDate&month=...`
   - `getClassesSurvey1.php?year=...&method=getMonthToDate&month=...`
   These update `#from_date` and `#to_date` and destroy/re-initialize the jQuery datepicker.
5. In Phase D.4, when `choose(page, "month", candidates[0])` was called, the cascading script or Select2 widget was still updating the DOM, causing `selected(page, "month")` to read stale state and trigger `FILTER_SELECTION_MISMATCH`.

### 4.3 Technical Hardening in `portal_safety.py`
The `choose()` safety harness was upgraded with Select2 synchronization and graceful postback settlement:
```python
def choose(page: Any, kind: str, value: str) -> None:
    check_page(page)
    if value not in {o["value"] for o in options(page, kind)}:
        raise PortalSafetyError("REQUESTED_FILTER_UNAVAILABLE")
    try:
        ctrl = control(page, kind)
        ctrl.select_option(value=value, timeout=8000)
        try:
            ctrl.evaluate("(el, val) => { const jq = window.jQuery; if (jq) { jq(el).val(val).trigger('change'); } }", value)
        except Exception:
            pass
        page.wait_for_load_state("networkidle", timeout=8000)
        page.wait_for_timeout(1500)
        check_page(page)
        if selected(page, kind)[0] != value:
            # Retry once after DOM settles in case cascading script reset it
            ctrl.select_option(value=value, timeout=8000)
            try:
                ctrl.evaluate("(el, val) => { const jq = window.jQuery; if (jq) { jq(el).val(val).trigger('change'); } }", value)
            except Exception:
                pass
            page.wait_for_timeout(1000)
            check_page(page)
            if selected(page, kind)[0] != value:
                raise PortalSafetyError("FILTER_SELECTION_MISMATCH")
    except PortalSafetyError:
        raise
    except Exception:
        raise PortalSafetyError("FILTER_RELOAD_NOT_VERIFIED") from None
```

### 4.4 Offline Verification
- Synthetic test `test_choose_select2_sync_and_retry_success` was added to `backend/tests/test_portal_safety.py` and passed.
- Fail-closed test `test_choose_persistent_mismatch_raises_fail_closed` verifies that persistent mismatches still fail-closed without exception.

---

## 5. Scope B: Semester 3 (July 2025) Offline Technical Preparation

### 5.1 Scope Specification
- **Academic Year:** `2025-2026`
- **Semester:** `3`
- **Class Identifier:** `1067` (`B.Tech CSE AIML-Sem 3`)
- **Target Calendar Month:** `2025-07` (`2025-07-01` to `2025-07-31`)
- **Unverified Gap:** 27 attended / 27 delivered.

### 5.2 Calendar Exception Logic Discovery & Bug Remediation
During testing of `AcademicTermCalendarService`, an edge-case bug in candidate month resolution was uncovered:
- Default odd semesters (1, 3, 5, 7) exclude July (`start_year-07`) in `excluded_months`.
- In `get_candidate_months()`, `approved_exceptional_months` was added to candidate months, but then `months.difference_update(cal.excluded_months)` stripped it back out.
- **Remediation**: Updated `get_candidate_months()` so that approved exceptions are excluded from `difference_update`:
  ```python
  if include_exceptions:
      months.update(cal.approved_exceptional_months)
      excluded = set(cal.excluded_months) - set(cal.approved_exceptional_months)
      months.difference_update(excluded)
  ```
- **Strict Isolation**: Tested and verified that configuring `approved_exceptional_months = ["2025-07"]` on term `2025-2026-S3-1067` applies **only** to Semester 3. Semester 1 (`2024-2025-S1-918`) and Semester 5 (`2026-2027-S5-2582`) remain strictly protected against July queries.

---

## 6. Full Quality Gates & Release Verification

All engineering quality gates pass cleanly across backend and frontend:

| Gate | Tool | Target | Result | Parity / Details |
| :--- | :--- | :--- | :---: | :--- |
| **Python Unit Tests** | `pytest` | `backend/tests` | **PASS** | **272 passed**, 0 failed (up from 269 in Phase D.5) |
| **Python Linting** | `ruff` | `backend/app backend/tests` | **PASS** | 0 warnings, 0 errors |
| **Python Typing** | `mypy` | `backend/app` | **PASS** | 0 issues across 44 source files |
| **Frontend Unit Tests** | `vitest` | `frontend/src/tests` | **PASS** | **38 passed** across 13 test suites |
| **TypeScript Typecheck** | `tsc` | `frontend` | **PASS** | `--noEmit` clean, 0 type errors |
| **Production Build** | `vite build` | `frontend` | **PASS** | Production bundle built cleanly in 4.32s |

---

## 7. Formal Live Authorization Checkpoint

The offline preparation is complete and verified. The execution harness is halted at the authorization gate:

```
================================================================================
ATTENDPLAN PHASE D.6 LIVE EXECUTION CHECKPOINT: AWAITING_USER_APPROVAL
================================================================================
TARGET SCOPE:
  1. Scope A: AY 2024-2025, Semester 2, Class ID 1048, Month: 2025-01 (1 request)
  2. Scope B: AY 2025-2026, Semester 3, Class ID 1067, Month: 2025-07 (1 request)

MAXIMUM REQUEST BUDGET: Exactly 2 live requests.
AUTHENTICATION: Active CDP session on 127.0.0.1:9222 (no stored credentials).
STATE: AWAITING EXPLICIT USER AUTHORIZATION BEFORE PROCEEDING.
================================================================================
```

