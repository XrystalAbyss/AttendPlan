# AttendPlan Phase E.1 — Supervised Academic Marks Integration Pilot
## Semester 3 Internal Assessments Pilot Preparation & Performance Architecture

**Document ID**: `ATTENDPLAN_PHASE_E1_MARKS_PILOT`  
**Phase**: E.1 (Supervised Academic Marks Integration Pilot)  
**Date**: 2026-11-01  
**Status**: `AWAITING_USER_APPROVAL` (Offline Verification Complete)  
**Target Academic Term**: Academic Year 2025–2026, Semester 3 (Class ID 1067)  
**Execution Policy**: Zero live portal extractions executed prior to explicit user authorization.  

---

## 1. Executive Summary & Verification State

Phase E.1 executes the offline preparation and safety hardening for AttendPlan's first supervised live academic marks integration pilot: **Semester 3 Internal Academic Assessments** (Academic Year 2025–2026, Class ID 1067).
All offline preflights, database checks, schema verifications, course roster mappings, and automated quality gates have passed with 100% success. In accordance with the non-negotiable authorization boundary, **zero live portal requests were executed**, and the application is stopped at `AWAITING_USER_APPROVAL` pending user review of the authorization manifest.

### Key Verification Outcomes:
- **Verification Status**: `AWAITING_USER_APPROVAL`
- **Attendance Archive Denominator Reconciled**: Reconciled the historical 18/18 documentation metric against the exact stored batches, establishing that the five-semester archive spans **19 distinct historical calendar months** and **3 active semester months** (**22 distinct calendar months** with instructional observations), encompassing **2,064 / 2,078 delivered periods (99.33% parity)** across **334 active instructional days**.
- **Semester 3 Target Isolated**: Verified all 16 canonical Semester 3 courses in SQLite (`CDO231`, `CSH201C`, `CSH202C`, `CSH203C`, `CSH204C`, `CSH205C`, `CSH206C`, `CSH207C`, `CSH208C`, `CSS210C`, `CSW209C`, `EDN248C`, `MAH204C`, `MAH204C-TUT`, `RDO201C`, `VAC-CS112`), with distinct theory, lab, and tutorial identities.
- **Quality Gates Cleared**: **280 backend tests passed** (including 5 new pilot invariant tests), **38 frontend tests passed** (13 test files), ruff clean (0 errors), mypy clean (44 files), tsc clean, production bundle built cleanly in 5.85s.
- **Data Safety Verified**: Fresh consistent backup created (`attendplan_pre_phase_e1_backup_20261101_204052.sqlite3`), foreign keys clean, and existing Semester 4 snapshot (`marks:6424:3:A`) completely preserved.

---

## 2. Git Status & Codebase Baseline

The working repository is in a healthy, verified state. All Phase E.0 and E.1 improvements are contained cleanly in tracked files, with zero Git pushes and zero external network transmissions.

---

## 3. Attendance Archive Denominator & Coverage Reconciliation

In earlier planning phases, the archive coverage was described as *"18/18 monthly reports"*. To ensure mathematical and institutional precision under `AGENTS.md`, this value was forensically audited against the underlying database tables (`attendance_observation_batches`, `attendance_period_observations`, and `academic_terms`):

### 3.1 Distinct Calendar Months Breakdown
| Semester | Academic Year | Distinct Months Present | Stored Year-Months | Delivered Periods (Snap/Ledger) | Attended Periods (Snap/Ledger) |
| :---: | :---: | :---: | :--- | :---: | :---: |
| **Sem 1** | 2024–2025 | 4 | `2024-08`, `2024-09`, `2024-10`, `2024-11` | 293 / 293 | 275 / 275 |
| **Sem 2** | 2024–2025 | 5 | `2025-01`, `2025-02`, `2025-03`, `2025-04`, `2025-05` | 446 / 445 | 381 / 381 |
| **Sem 3** | 2025–2026 | 5 | `2025-07`, `2025-08`, `2025-09`, `2025-10`, `2025-11` | 463 / 459 | 400 / 396 |
| **Sem 4** | 2025–2026 | 5 | `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05` | 554 / 545 | 485 / 476 |
| **Sem 5 (Active)** | 2026–2027 | 3 | `2026-08`, `2026-09`, `2026-10` | 322 / 322 | 265 / 265 |
| **OVERALL** | — | **22** | **22 Distinct Calendar Months** | **2,078 / 2,064** | **1,806 / 1,793** |

### 3.2 Key Reconciliations:
1. **Why was it called 18/18?**: In Phase D.4, 16 historical requests were planned (4 per term for Sem 1–3, plus 5 for Sem 4 = 17). During D.6, two missing months (`2025-01` in Sem 2 and `2025-07` in Sem 3) were successfully recovered, bringing the historical reporting months to **19** ($4 + 5 + 5 + 5$). Preliminary E.0 notes had counted 18 prior to full reconciliation.
2. **Active Semester Months**: Semester 5 contains 3 completed months (`2026-08`, `2026-09`, `2026-10`) with progressive daily sync batches, plus active ongoing November 2026 syncing.
3. **Delivered Numerical Parity**: **2,064 / 2,078 = 99.33%**.
4. **Instructional Calendar Coverage**: Exactly **334 distinct instructional days** across the five terms.

---

## 4. Semester 3 Course Roster & Component Architecture

The 16 canonical courses for Semester 3 are verified in SQLite with distinct UUIDs:

| Course Code | Official Course Name | Component Type | Faculty Instructor | Snapshot Att/Del | Ledger Att/Del |
| :--- | :--- | :---: | :--- | :---: | :---: |
| `CDO231` | PROFESSIONAL COMPETANCY ENHANCEMENT-I | THEORY | Geetika | 49 / 57 | 49 / 57 |
| `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS | THEORY | PUSHPA | 38 / 44 | 37 / 43 |
| `CSH202C` | ANALYSIS & DESIGN OF ALGORITHMS LAB | LAB | PUSHPA | 26 / 30 | 26 / 30 |
| `CSH203C` | DATABASE MANAGEMENT SYSTEMS | THEORY | ANU PRIYA SHARMA | 32 / 35 | 32 / 35 |
| `CSH204C` | DATABASE MANAGEMENT SYSTEMS LAB | LAB | ANU PRIYA SHARMA | 21 / 23 | 21 / 23 |
| `CSH205C` | OOPS USING JAVA | THEORY | MEENA CHAUDHARY | 39 / 43 | 39 / 43 |
| `CSH206C` | OOPS USING JAVA LAB | LAB | MEENA CHAUDHARY | 26 / 29 | 26 / 29 |
| `CSH207C` | ARTIFICIAL INTELLIGENCE | THEORY | ABHISHEK SAXENA | 37 / 41 | 37 / 41 |
| `CSH208C` | ARTIFICIAL INTELLIGENCE LAB | LAB | ABHISHEK SAXENA | 28 / 31 | 28 / 31 |
| `CSS210C` | ADVANCED PYTHON FOR AI | THEORY | Harshvardhan Palawat | 27 / 32 | 26 / 31 |
| `CSW209C` | WEB DESIGNING-II | LAB | ANU PRIYA SHARMA | 27 / 31 | 27 / 31 |
| `EDN248C` | UHV II/ SEEK | THEORY | None | 0 / 0 | 0 / 0 |
| `MAH204C` | DISCRETE MATHS | THEORY | KUSHAL LALWANI | 37 / 48 | 36 / 46 |
| `MAH204C-TUT` | DISCRETE MATHS | TUTORIAL | KUSHAL LALWANI | 9 / 10 | 9 / 10 |
| `RDO201C` | SOCIAL INTERNSHIP-POST 2ND SEM | THEORY | None | 0 / 0 | 0 / 0 |
| `VAC-CS112` | MONGODB JAVA DEVELOPER PATH | THEORY | PUSHPA | 9 / 9 | 9 / 9 |
| **TOTAL** | **16 Courses** | — | — | **400 / 463** | **396 / 459** |

---

## 5. Performance Source Identity & Route Contract

- **Portal Route**: `https://mrei.icloudems.com/corecampus/student/grades/new/myreportcard.php`
- **Query Handler**: `/corecampus/student/grades/new/save/myreportcardSave.php`
- **Security Contract**: The form accepts only academic filter options (`year`, `exam_session`, `class`, `division`, `exam_type`), never editable grade values or student uploads.
- **Parser Adaptability**: The parser in `backend/app/services/performance_service.py` is dynamic and source-driven, handling variable column counts, grouped headers, and distinct continuous evaluation breakdowns without hardcoded assumptions.

---

## 6. Score Status Invariants & Mathematical Rules

In accordance with Rule 2.5 and Section 6 of the prompt, the system maintains strict distinctions across all score states:

- **Evaluated Zero (`0.0`)**: Recorded as `obtained = 0.0, status = 'REPORTED'`. Treated as a valid numerical zero score.
- **Unreported / Not Held (`None`)**: Empty, `-`, or `--` cells are recorded as `obtained = None, status = 'UNREPORTED'`. Never coerced to zero.
- **Masked by Portal (`None`)**: `******` cells are recorded as `obtained = None, status = 'MASKED_BY_PORTAL'`.
- **Student Absence (`None`)**: `AB` or `Absent` is recorded as `obtained = None, status = 'AB'`.
- **Zero Speculative GPA**: AttendPlan never calculates unofficial GPAs from partial continuous evaluations. Only portal-declared SGPA/CGPA is recorded.

---

## 7. Storage Immutability, Deduplication & Revision Tracking

- **Table**: `performance_snapshots` in `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`.
- **Deduplication**: Keyed by `(term_key, view, checksum)`. Re-executing an identical report returns `existing` without inserting duplicate rows (`DUPLICATE_SKIPPED`).
- **Revision Immutability**: If the university updates marks or releases new tests, a new snapshot record is inserted with a distinct UUID and timestamp. Previous snapshots are permanently preserved.
- **Semester 4 Preservation**: Semester 4 snapshot `03d1482b-c997-431f-bc88-071c3bb4c764` is verified untouched.
- **Attendance Ledger Preservation**: Attendance tables remain strictly isolated and unaffected.

---

## 8. Attendance & Daily Sync Concurrency Protection

- **Global Mutex (`_SYNC_LOCK`)**: Shared across attendance refresh, historical backfill, and performance imports.
- **Non-Blocking Acquisition**: Performance routes attempt non-blocking lock acquisition. If daily sync or startup refresh is active, the performance request aborts with `409 Conflict: Another portal job is active.`
- **Fail-Safe Release**: All operations employ `try ... finally: _SYNC_LOCK.release()`, verified by synthetic crash injection tests.

---

## 9. Quality Gates & Release Verification Summary

| Quality Check | Command | Verified Result |
| :--- | :--- | :---: |
| **Backend Test Suite** | `pytest backend/tests` | **280 passed, 0 failed** (19.72s) |
| **Backend Linting** | `ruff check backend/app backend/tests` | **All checks passed!** |
| **Backend Typing** | `mypy backend/app` | **Success: no issues found in 44 files** |
| **Frontend Test Suite** | `npm test -- --run` | **38 passed (13 test files)** |
| **Frontend Typecheck** | `npx tsc --noEmit` | **Clean (0 errors)** |
| **Frontend Production Build** | `npm run build` | **Built in 5.85s (`dist/` generated)** |
| **Database Integrity** | `PRAGMA integrity_check` | **ok** |
| **Foreign Key Integrity** | `PRAGMA foreign_key_check` | **[] (0 violations)** |
| **Preflight Backup** | `attendplan_pre_phase_e1_backup_...` | **Created and verified** |

---

## 10. Checkpoint & Authorization Status

**Current Operational State**: `AWAITING_USER_APPROVAL`  

The Phase E.1 offline preparation is complete. All safety barriers, course mappings, rate limits, and request budgets are locked. No live portal requests will be initiated without explicit authorization from the user.