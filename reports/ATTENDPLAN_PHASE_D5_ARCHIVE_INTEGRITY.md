# ATTENDPLAN — PHASE D.5 INTEGRITY AUDIT REPORT
## Five-Semester Archive Integrity Closure & Effective Ledger Verification
### Definitive Technical & Operational Audit

**Document Version:** 1.0  
**Audit Date:** 2026-11-01  
**Operating System:** Windows 11 x64  
**Runtime:** Python 3.12.10, Node.js v20.18, Vite 6.4.4, SQLite 3.45 (WAL mode)  
**Security Posture:** Localhost bound (`127.0.0.1`), Zero Credential/OTP Persistence, Zero Student PII  
**Status:** **`VERIFIED_COMPLETE (SUCCESS)`**  

---

## 1. Executive Summary & Audit Declaration

Phase D.5 was initiated to conduct a rigorous integrity audit of AttendPlan's five-semester attendance archive following the Phase D.4 recovery.

All required investigations and data repairs have been completed successfully:
1. **Semester 5 Day-Wise Discrepancy Resolved**:
   - The reported **663/838** figure is definitively proven to be an artifact of summing **raw historical ingestions** across 9 progressive batches (including duplicate syncs in August, duplicate syncs in September, and 5 progressive October syncs).
   - The **Canonical Effective Ledger** resolves these 1,112 raw rows into **424 unique period slots** totaling **265 attended / 322 delivered (82.30%)**.
   - Remediation of placeholder course `PROFESSIONAL COMPETANCY ENHANCEMENT-III (PP)` into official entity `CDO331` established **100% course-level matching across all 15 courses** in Semester 5 ($\Delta = 0/0$).
2. **Semester 1 Parity Verified**:
   - Subject Summary (275/293) and Day-Wise observations (275/293 across 413 slots) exhibit 100% exact equality across all 12 courses.
   - Reconciliation engine upgraded so that identical course-by-course and aggregate parity correctly yields `ReconciliationStatus.MATCHED`.
3. **Semester 2 January 2025 Source Gap Investigated**:
   - The `PORTAL_SAFETY_FILTER_SELECTION_MISMATCH` outcome was caused by JavaScript `onchange` postback timing during month dropdown selection, preventing form submission.
   - Status accurately labeled: `JANUARY_SOURCE_UNVERIFIED`.
   - A bounded single-request proposal has been prepared for user approval.
4. **Semester 3 July 2025 Source Gap Investigated**:
   - The +27/+27 difference corresponds to the pre-August orientation/class window (July 14–31, 2025). July was outside the approved candidate months.
   - Status accurately labeled: `UNVERIFIED_JULY_DAYWISE_DATA`.
   - A bounded single-request proposal has been prepared for user approval.
5. **Semester 4 9/9 Discrepancy Preserved**:
   - Preserved as `ReconciliationStatus.DISCREPANCY` (or `SOURCE_DISCREPANCY`) with explanation (May 2–16 examination/project period credited in ERP summary).
6. **Internal Component Identities Audited**:
   - Derived suffixes (`-TUT` and `-PR`) are properly stored with canonical `CourseType.TUTORIAL` and `CourseType.LAB` designations, preventing constraint collisions while preserving official course codes.
7. **Current-Month Rollover (November 2026) Verified**:
   - The runtime dynamically resolves Asia/Kolkata timezone, selects `2026-11`, binds to active Semester 5 (`2582`), and safely handles initial first-day zero-period states without data loss or historical triggering.
8. **Quality Gates Passed**:
   - **269 backend tests passed** (`pytest`)
   - **38 frontend tests passed** (`vitest`)
   - Zero lint errors (`ruff`), zero type errors (`mypy`, `tsc`)
   - Clean production bundle build (`vite build`)
   - Verified SQLite database integrity (`ok`) and foreign keys (`0 violations`).

---

## 2. Pre-Audit & Post-Remediation Database Baseline

Active Database: `C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3`  
WAL-Safe Backup: `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_d5_backup_20261101_150029.sqlite3` (1,777,664 bytes)

### Sanitized Baseline Summary by Academic Term:

| Term / Semester | Academic Year | Class Identifier | Official Courses | Derived Components | Subject Snapshots | Batches | Raw Obs | Effective Slots | Subject Att/Del | Effective Day Att/Del | Reconciliation Status |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Sem 1** | 2024–2025 | B.Tech CSE AIML-Sem 1 (`918`) | 12 | 2 (`-TUT`, `-PR`) | 1 | 4 | 413 | 413 | 275 / 293 (93.86%) | 275 / 293 (93.86%) | `MATCHED` |
| **Sem 2** | 2024–2025 | B.Tech CSE AIML-Sem 2 (`1048`) | 16 | 3 (`-TUT`, `-PR`) | 1 | 4 | 430 | 430 | 381 / 446 (85.43%) | 296 / 356 (83.15%) | `SCOPE_MISMATCH` (Jan gap) |
| **Sem 3** | 2025–2026 | B.Tech CSE AIML-Sem 3 (`1067`) | 16 | 1 (`-TUT`) | 1 | 4 | 680 | 680 | 400 / 463 (86.39%) | 373 / 436 (85.55%) | `SCOPE_MISMATCH` (July gap) |
| **Sem 4** | 2025–2026 | B.Tech CSE AIML-Sem 4 (`2508`) | 17 | 0 | 1 | 5 | 729 | 729 | 485 / 554 (87.55%) | 476 / 545 (87.34%) | `DISCREPANCY` (Exam 9/9) |
| **Sem 5** | 2026–2027 | B.Tech CSE AIML-Sem 5 (`2582`) | 15 | 0 | 5 | 9 | 1,112 | 424 | 265 / 322 (82.30%) | 265 / 322 (82.30%) | `MATCHED` |
| **TOTALS** | — | — | **76** | **6** | **9** | **26** | **3,364** | **2,676** | **1,806 / 2,078** | — | — |

---

## 3. Semester 5 Raw History vs. Effective Ledger Audit

### 3.1 Investigation of the 663/838 Figure
In Phase D.4, diagnostic reporting executed a raw query summing `attendance_period_observations` across all 9 batches in Semester 5.
As detailed in [ATTENDPLAN_EFFECTIVE_LEDGER_AUDIT.md](file:///c:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_EFFECTIVE_LEDGER_AUDIT.md):
- August 2026 had 2 batches (102/115 and 104/116).
- September 2026 had 2 batches (81/96 and 83/97).
- October 2026 had 5 batches representing progressive captures between Oct 16 and Oct 30 (47/68 + 47/68 + 48/69 + 73/100 + 78/109).

Summing raw batches:
$$\sum \text{Attended} = 47 + 47 + 81 + 102 + 48 + 73 + 83 + 104 + 78 = \mathbf{663}$$
$$\sum \text{Delivered} = 68 + 68 + 96 + 115 + 69 + 100 + 97 + 116 + 109 = \mathbf{838}$$

### 3.2 Canonical Effective Ledger Resolution
`app.services.current_observations.latest_observations` selects the latest observation for each unique `(attendance_date, slot_start_time, slot_end_time)` tuple based on batch observation timestamp:
$$\text{August Effective: } 104 / 116 \quad (\text{Batch } 20cab324)$$
$$\text{September Effective: } 83 / 97 \quad (\text{Batch } 783331dc)$$
$$\text{October Effective: } 78 / 109 \quad (\text{Batch } 355dfb7a)$$
$$\text{Total Effective: } 104 + 83 + 78 = \mathbf{265 \text{ attended}}, \quad 116 + 97 + 109 = \mathbf{322 \text{ delivered}}$$

This matches the latest Subject-Wise Summary snapshot of October 30, 2026 ($265/322 = 82.30\%$) **identically**.

### 3.3 Course Remapping & Parity
The placeholder course `PROFESSIONAL COMPETANCY ENHANCEMENT-III (PP)` was remapped to official course `CDO331` via `remediate_sem5_course_links.py`. All 15 courses now exhibit **100% course-level matching**.

---

## 4. Multi-Semester Coverage Truthfulness & Gap Analysis

To maintain institutional accuracy, AttendPlan tracks data completeness across multiple dimensions:

| Semester | Academic Year | Subject Summary Coverage | Day-Wise Coverage | Instructional Date Scope | Course Mapping Confidence | Reconciliation Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Sem 1** | 2024–2025 | `COMPLETE` (12 courses) | `COMPLETE` (4 months) | Aug 8 to Nov 22, 2024 | 1.0 (100% mapped) | `MATCHED` (100% exact parity) |
| **Sem 2** | 2024–2025 | `COMPLETE` (16 courses) | `PARTIAL` (Feb–May saved) | Feb 1 to May 2, 2025 | 1.0 (100% mapped) | `SCOPE_MISMATCH` (Jan 13–31 gap: +85/+90) |
| **Sem 3** | 2025–2026 | `COMPLETE` (16 courses) | `PARTIAL` (Aug–Nov saved) | Aug 1 to Nov 21, 2025 | 1.0 (100% mapped) | `SCOPE_MISMATCH` (July 14–31 gap: +27/+27) |
| **Sem 4** | 2025–2026 | `COMPLETE` (17 courses) | `COMPLETE` (5 months) | Jan 1 to May 2, 2026 | 1.0 (100% mapped) | `DISCREPANCY` (Exam 9/9 credit) |
| **Sem 5** | 2026–2027 | `COMPLETE` (15 courses) | `COMPLETE` (Aug–Oct saved) | Aug 4 to Oct 30, 2026 | 1.0 (100% mapped) | `MATCHED` (Live active term) |

---

## 5. Course Code Component Integrity Engine

In university ERPs, multiple course components (e.g., Theory and Tutorial) share the exact base code (e.g., `MAH204C`).
To ensure multi-component support without SQLite unique constraint violations:
1. `html_parser.py` appends canonical component tags (`-TUT` for tutorials, `-PR` for labs).
2. `ingestion_service.py` assigns `CourseType.TUTORIAL` to `-TUT` courses and `CourseType.LAB` to `-PR` courses.
3. The underlying base code remains retrievable via regex stripping (`-(TUT|PR|\d+)$`), guaranteeing that derived identifiers are not conflated with official university course codes.
4. Database unique constraint `UniqueConstraint("academic_term_id", "course_code")` is satisfied with zero collisions across terms.

---

## 6. Current Month Rollover Verification (November 2026)

With system date advancing into November 2026:
1. **Timezone Accuracy**: `current_refresh_service.kolkata_now()` computes local time in `Asia/Kolkata` (UTC+05:30).
2. **Current Month Selection**: Service A selects month `"11"` (`November 2026`).
3. **Empty Initial Month Handling**: If the portal has not yet recorded November periods (e.g., start of month/Sunday), `CurrentRefreshService` returns `SYNC_PARTIAL`, preserving all cached October records without error or period fabrication.
4. **Regression Tested**: `test_current_month_rollover_november_2026` passed cleanly in automated test suite.

---

## 7. Cumulative Degree Attendance Analytics

- **Official Basis**: Cumulative degree statistics are computed strictly from the latest official Subject-Wise Snapshots of each term.
- **Arithmetic**:
  $$\text{Total Attended: } 275 (\text{S1}) + 381 (\text{S2}) + 400 (\text{S3}) + 485 (\text{S4}) + 265 (\text{S5}) = \mathbf{1,806}$$
  $$\text{Total Delivered: } 293 (\text{S1}) + 446 (\text{S2}) + 463 (\text{S3}) + 554 (\text{S4}) + 322 (\text{S5}) = \mathbf{2,078}$$
  $$\text{Cumulative Percentage: } \frac{1,806}{2,078} = \mathbf{86.91\%} \quad (\text{Target: } 75.00\%)$$
- **Regulatory Clarification**: Cumulative degree attendance is descriptive institutional analytics. University statutory requirements enforce the 75% threshold on a per-course basis within each active semester. High cumulative attendance does not grant examination eligibility in an active course below threshold.

---

## 8. Quality Gates & Release Verification

| Quality Gate | Tool / Runner | Command | Result | Details |
| :--- | :--- | :--- | :---: | :--- |
| **Backend Unit & Domain Tests** | `pytest` | `pytest backend/tests` | **PASS** | **269 passed**, 1 warning in 38.43s |
| **Python Code Quality & Linting** | `ruff` | `ruff check backend/app backend/tests` | **PASS** | All checks passed cleanly |
| **Python Static Type Safety** | `mypy` | `mypy backend/app` | **PASS** | Success: 0 issues in 44 source files |
| **Frontend Test Suite** | `vitest` | `npm.cmd test -- --run` | **PASS** | **13 test files passed, 38 tests passed** |
| **Frontend TypeScript Types** | `tsc` | `npx.cmd tsc --noEmit` | **PASS** | Zero type errors |
| **Frontend Production Build** | `vite` | `npm.cmd run build` | **PASS** | Production bundle built cleanly in 19.47s |
| **SQLite Schema & Data Integrity** | `sqlite3` | `PRAGMA integrity_check` | **PASS** | `ok` |
| **SQLite Foreign Key Consistency** | `sqlite3` | `PRAGMA foreign_key_check` | **PASS** | 0 violations across all 10 tables |

---

## 9. Next Steps & User Authorization Boundary

Phase D.5 has successfully verified and hardened the Five-Semester Attendance Archive.
In accordance with instructions, **zero live portal requests were executed during this audit**.

Two bounded, optional recovery proposals are ready for user review in [ATTENDPLAN_HISTORICAL_GAP_RECOVERY_PLAN.md](file:///c:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_HISTORICAL_GAP_RECOVERY_PLAN.md):
1. **Semester 2 (January 2025)**: 1 live request to recover early-semester timetable slots.
2. **Semester 3 (July 2025)**: 1 live request to recover late-July orientation/class slots.
Total budget: **2 requests maximum**.

