# AttendPlan Phase E.0 — Academic Performance Integration Readiness
## Forensic Course Identity Audit, Marks Architecture & Archive Parity Verification

**Document ID**: `ATTENDPLAN_PHASE_E0_MARKS_READINESS`  
**Phase**: E.0 (Readiness, Forensic Audit & Architecture)  
**Date**: 2026-11-01  
**Status**: COMPLETED & FROZEN (Strictly Offline Verification)  
**Execution Policy**: ZERO live portal requests executed; all operations strictly offline.  

---

## 1. Executive Summary & Mission Overview

Phase E.0 establishes the architectural, semantic, and mathematical foundations required to integrate student academic performance (continuous evaluations, sessional tests, practicals, viva, and official semester examination results) into AttendPlan without compromising data provenance, institutional integrity, or the existing five-semester attendance ledger.

### Key Accomplishments of Phase E.0:
1. **Forensic Course Identity Audit**: Confirmed the canonical identities of all 76 courses across Semesters 1 through 5. Definitively resolved the historical documentation confusion regarding `CSH201C`: it is **ANALYSIS & DESIGN OF ALGORITHMS** in Semester 3, whereas **COMPUTER ARCHITECTURE & ORGANISATION** is `CSH301C` in Semester 5.
2. **Exact Five-Semester Archive Parity**: Corrected and formalized the attendance completeness metrics, establishing the exact mathematical distinction between Monthly Report Coverage (18/18 monthly reports = 100%) and Numerical Delivered Parity (**2,064 / 2,078 = 99.33%**).
3. **Performance System Inventory**: Audited the existing Semester 4 performance baseline snapshot (`03d1482b-c997-431f-bc88-071c3bb4c764`), categorizing all 11 assessment types, validating portal masking mechanisms (`******`), and verifying course mapping.
4. **Marks Data Model & Invariant Formalization**: Established immutable schema designs that enforce the critical distinction between a genuine zero score (`0.0`), an unreported/unconducted evaluation (`UNREPORTED`), and a university-masked score (`MASKED_BY_PORTAL`). Enforced zero speculative GPA extrapolation.
5. **Quality Gates & Safety**: Created 3 new invariant tests in `test_course_identity_and_marks_invariants.py`, bringing total pytest suite to **275 passed**. Verified all quality gates (mypy clean across 44 files, ruff clean, 38 frontend tests passing, production build clean in 6.13s).

---

## 2. Correct Archive Completeness Metrics

To avoid semantic confusion between timetable report extraction and period-level numerical coverage, Phase E.0 formally defines both metrics:

### 2.1 Report Coverage vs. Numerical Parity
- **Monthly Timetable Report Coverage**: **18 / 18 Reports (100.0%)** across all authorized historical and current monthly scopes.
- **Delivered Numerical Parity**: **2,064 / 2,078 Delivered Periods (99.33%)**.
- **Attended Numerical Parity**: **1,793 / 1,806 Attended Periods (99.28%)**.

### 2.2 Five-Semester Mathematical Reconciliation
| Semester | Term Key | Class ID | Courses | Subject-Wise (A/D) | Day-Wise Ledger (A/D) | Delta (A/D) | Delivered Parity | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Sem 1** | `2024-2025_s1_918` | 918 | 12 | 275 / 293 | 275 / 293 | +0 / +0 | **100.00%** | `MATCHED` |
| **Sem 2** | `2024-2025_s2_1048` | 1048 | 16 | 381 / 446 | 381 / 445 | +0 / +1 | **99.78%** | `DISCREPANCY` (1 holiday period) |
| **Sem 3** | `2025-2026_s3_1067` | 1067 | 16 | 400 / 463 | 396 / 459 | +4 / +4 | **99.14%** | `SCOPE_MISMATCH` (orientation gap) |
| **Sem 4** | `2025-2026_s4_2508` | 2508 | 17 | 485 / 554 | 476 / 545 | +9 / +9 | **98.38%** | `DISCREPANCY` (pre-timetable window) |
| **Sem 5** | `2026-2027_s5_2582` | 2582 | 15 | 265 / 322 | 265 / 322 | +0 / +0 | **100.00%** | `MATCHED` |
| **OVERALL** | **Five Semesters** | — | **76** | **1,806 / 2,078** | **1,793 / 2,064** | **+13 / +14** | **99.33%** | **CANONICAL ARCHIVE COMPLETE** |

The total delivered gap across the entire student academic career is exactly **14 periods** ($0 + 1 + 4 + 9 + 0 = 14$), all accounted for by verified institutional scheduling phenomena (pre-timetable commencement windows and unrecorded holiday schedules).

---

## 3. Mandatory Course Identity Audit

A full forensic inquiry across all 76 courses in SQLite was executed to establish an incontrovertible registry.

### 3.1 Definitive CSH201C vs CSH301C Resolution
- `CSH201C`: **ANALYSIS & DESIGN OF ALGORITHMS** (Semester 3, Theory, 38/44 periods, taught by Pushpa). Paired with `CSH202C` (*ADA LAB - PR*, 26/30 periods).
- `CSH301C`: **COMPUTER ARCHITECTURE & ORGANISATION** (Semester 5, Theory, 32/41 periods, taught by Ravi Prakash Chaturvedi). Paired with `CSH311C` (*CAOR - PR*, 16/20 periods).
- **Conclusion**: The earlier notation referencing CSH201C as Computer Architecture was a typographical transcription error in scratch documentation. The database and portal data have at all times been canonical and correct.

### 3.2 Multi-Semester Course Isolation (Rule 2.13)
- Exactly one course code appears in multiple terms: `RDO202C` (**RESEARCH & INNOVATION**) appears in Semester 4 and Semester 5.
- In Semester 4: UUID `dc9726b2-7001-456f-8d3a-b99851e59e03` (Faculty: URMILA PILANIA PILANIA).
- In Semester 5: UUID `4861b80e-8673-4ff4-9d4b-a53998c41383` (Faculty: None).
- Both are strictly isolated by `academic_term_id` and have independent relational entries.

### 3.3 Blank Cell Semantics (Invariant 11)
- All 927 unmapped observations in the database correspond strictly to unscheduled timetable blocks or institutional recess ($d=0, a=0$, status `NOT_REPORTED`).
- Exactly zero instructional meetings with delivered periods > 0 were left unmapped.

---

## 4. Academic Performance System Inventory

### 4.1 Existing Semester 4 Snapshot Baseline
- **Snapshot ID**: `03d1482b-c997-431f-bc88-071c3bb4c764` (`marks:6424:3:A`) captured on 2026-10-20.
- **Coverage**: 15 Semester 4 courses, each containing 11 assessment columns.
- **Assessment Categories**: Midterm examinations MRU, Continuous Evaluation 1–8 (`CE` to `CE 8`), oral defense (`VIVA`), and End Semester Examination.
- **Portal Masking**: All 15 courses have End Semester Examination marked as `MASKED_BY_PORTAL` with raw cell content `******`.
- **SGPA / CGPA**: Recorded as `None` in this internal marks view (final GPA appears only on the official `results` grade card).

### 4.2 Score Representation Invariants
| Score Case | Raw Portal Text | Stored Obtained | Stored Percentage | Stored Status | Mathematical Handling |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Evaluated Zero** | `0/20` or `0` | `0.0` | `0.0%` | `REPORTED` | Included in numerical averages as a true zero score. |
| **Unreported / Not Held** | `-`, `--`, empty | `None` | `None` | `UNREPORTED` | Excluded from calculations; remains strictly unknown. |
| **Masked by Institution** | `******` | `None` | `None` | `MASKED_BY_PORTAL` | Excluded from calculations; never guessed or decoded. |
| **Student Absence** | `AB`, `Absent` | `None` | `None` | `ABSENT` | Recorded as formal absence. |

---

## 5. Daily Sync & Concurrency Protection

To protect current Semester 5 attendance synchronization (daily refresh) from being blocked or corrupted by marks imports:

1. **Global Process Mutex (`_SYNC_LOCK`)**: Acquired non-blocking across both attendance and performance workflows. If an attendance sync or performance preview is active, conflicting calls immediately return `409 Conflict`.
2. **Decoupled Data Stores**: Performance snapshots are stored in `performance_snapshots` and are completely decoupled from `attendance_snapshots`, `courses`, and `attendance_period_observations`.
3. **Bounded Budget Policy**: Any future live marks import operates under a strictly bounded request budget (maximum 1 discovery query and 1 report fetch per approved term).

---

## 6. Quality Gates & Release Verification

All automated quality gates have passed with zero errors:

- **Backend Unit Tests**: **275 passed** (including 3 new tests in `test_course_identity_and_marks_invariants.py`).
- **Backend Linting**: `ruff check backend/app backend/tests` — **All checks passed!**
- **Backend Type Checking**: `mypy backend/app` — **Success: no issues found in 44 source files**.
- **Frontend Unit Tests**: `vitest run` — **13 test files passed, 38 tests passed**.
- **Frontend Type Checking**: `tsc --noEmit` — **Clean (0 errors)**.
- **Frontend Production Bundle**: `npm run build` — **Built cleanly in 6.13s** (`dist/` generated).
- **Database Integrity**: `PRAGMA integrity_check` = `ok`; `PRAGMA foreign_key_check` = `[]`.
- **Database Backup**: `attendplan_pre_phase_e0_backup_20261101_190916.sqlite3` safely preserved.

---

## 7. Deliverables & Artifacts Generated

1. `reports/ATTENDPLAN_COURSE_IDENTITY_AUDIT.md`: Complete forensic course registry of all 76 courses across Semesters 1–5.
2. `reports/ATTENDPLAN_PERFORMANCE_SOURCE_MATRIX.md`: Comprehensive assessment schema inventory and bounded retrieval plan.
3. `reports/ATTENDPLAN_PHASE_E0_MARKS_READINESS.md`: This executive readiness and verification report.
4. Artifact: `ATTENDPLAN_PHASE_E0_MARKS_READINESS.md`.

---

## 8. Checkpoint & Next Steps

**Current State**: `AWAITING_USER_APPROVAL`  
Phase E.0 is complete. Zero live portal requests were made during this phase. No further action or live marks extraction will proceed until explicit authorization is granted by the user.