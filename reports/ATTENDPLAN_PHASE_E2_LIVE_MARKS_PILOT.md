# ATTENDPLAN — PHASE E.2 LIVE MARKS PILOT EXECUTION REPORT
## Semester 3 Internal Academic Marks Integration & Integrity Verification

---

### 1. Executive Summary & Authorization Provenance

- **Execution Milestone**: Phase E.2 Live Execution — Supervised Semester 3 Internal Academic Marks Integration.
- **Authorization Authority**: Explicit user authorization granted (`AUTHORIZATION: EXPLICITLY GRANTED BY USER`).
- **Target Term**: Academic Year `2025–2026`, Semester `3`, Class ID `1067` (`B.Tech CSE AIML-Sem 3`), Division `A`.
- **Target Source Scope**: Official university continuous evaluations / internal assessments via:
  `https://mrei.icloudems.com/corecampus/student/grades/new/myreportcard.php` -> `myreportcardSave.php`
- **Execution Budget**:
  - Exactly 1 scope discovery operation executed and recorded in `sync_jobs`.
  - Exactly 1 marks report preview retrieval executed on live portal.
  - Zero refetches on import (evidence captured during preview, persisted locally).
- **Execution Outcome**: **100% SUCCESSFUL**.
  - All 13 courses and 117 individual continuous evaluation assessments ingested.
  - Snapshot persisted immutably with ID `a9410bae-8496-4a0e-a64c-0880aa5cfbdb` (`marks:6161:3:A`).
  - Pre-existing Semester 4 marks snapshot (`03d1482b-c997-431f-bc88-071c3bb4c764`) preserved untouched.
  - Full 5-semester attendance ledger (9 snapshots, 136 rows, 3,520 observations, 76 courses) preserved intact.
  - `PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check = []`.

---

### 2. Exact Pilot Scope & Scope Discovery

#### Scope Parameters
- **Academic Year**: `2025-2026`
- **Semester Number**: `3`
- **Class Identifier**: `1067`
- **Class Label**: `B.Tech CSE AIML-Sem 3`
- **Division**: `A`
- **Exam Session**: `6161` (`MRU-Odd-Semester-Dec-2025-2026-5041`)
- **Exam Type**: `3` (`INTERNAL EXAM`)

#### Discovered Scopes for Term `2025-2026_s3_1067`
From registered `SyncJob` `10829b4b-20fb-4993-bde2-d7c9de1173f7` (`PERFORMANCE_SCOPE_DISCOVERY`):
1. Session `6161` (`MRU-Odd-Semester-Dec-2025-2026-5041`), Type `3` (`INTERNAL EXAM`), Division `A` *(Target Selected)*
2. Session `6161` (`MRU-Odd-Semester-Dec-2025-2026-5041`), Type `4` (`EXTERNAL EXAM`), Division `A`

---

### 3. Zero-Refetch Protocol Verification

Per AGENTS.md and Section 3 of Phase E.2, preview and import must not fetch two independent copies of the same report.

1. **Preview Phase (`POST /api/v1/performance/preview`)**:
   - Filtered and queried `myreportcard.php` for `session=6161`, `type=3`, `class=1067`, `div=A`.
   - Extracted and parsed 13 courses and 117 assessment cells.
   - Generated SHA-256 source payload fingerprint: `b36fcba857fc73ad4397793d4086ad47754d5c957e8fa134d1561da7227bf347`.
   - Stored structured payload into `SyncJob.details["captured_payload"]` under `approval_id: d5dedd4a-1257-4b32-886b-52c51bdaae93`.
2. **Import Phase (`POST /api/v1/performance/import`)**:
   - Verified active pilot flag `ATTENDPLAN_ENABLE_PERFORMANCE_PILOT=1`.
   - Validated `approval_id` claim within 30-minute expiry window.
   - Atomic state transition from `COMPLETED` to `APPROVED`.
   - **ZERO portal network calls**: Reused stored payload directly from `job.details["captured_payload"]`.
   - Called pure `persist_performance(db, term_key, storage_view, parsed)` with hash deduplication.
   - Unit test `test_preview_to_import_zero_refetch` in `test_performance_pilot_e1.py` proves `extract_marks` call count remains exactly 1.

---

### 4. Complete Table of Semester 3 Official Internal Marks

All continuous evaluation scores, components, and statuses parsed faithfully from the official university report card:

| # | Course Code | Course Title | Assessment Name | Scored | Maximum | Ratio (%) | Status |
|---|---|---|---|---|---|---|---|
| 1 | `CDO231` | PROFESSIONAL COMPETANCY ENHANCEMENT-I - PP | Continuous Evaluation (CE) | 14.0 | 20.0 | 70.00% | `REPORTED` |
| 2 | `CDO231` | PROFESSIONAL COMPETANCY ENHANCEMENT-I - PP | Mid Term Examinations MRU | 24.0 | 30.0 | 80.00% | `REPORTED` |
| 3 | `CDO231` | PROFESSIONAL COMPETANCY ENHANCEMENT-I - PP | End Semester Examination | 36.0 | 50.0 | 72.00% | `REPORTED` |
| 4 | `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS - PP | Continuous Evaluation (CE) | 12.0 | 15.0 | 80.00% | `REPORTED` |
| 5 | `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS - PP | CE 2 | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 6 | `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS - PP | Mid Term Examinations MRU | 21.0 | 40.0 | 52.50% | `REPORTED` |
| 7 | `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS - PP | CE 3 | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 8 | `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS - PP | CE 4 | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 9 | `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS - PP | End Semester Examination | 58.0 | 100.0 | 58.00% | `REPORTED` |
| 10 | `CSH202C` | ANALYSIS & DESIGN OF ALGORITHMS LAB - PR | Continuous Evaluation (CE) | 7.0 | 10.0 | 70.00% | `REPORTED` |
| 11 | `CSH202C` | ANALYSIS & DESIGN OF ALGORITHMS LAB - PR | CE 2 | 8.0 | 10.0 | 80.00% | `REPORTED` |
| 12 | `CSH202C` | ANALYSIS & DESIGN OF ALGORITHMS LAB - PR | Mid Term Examinations MRU | 7.0 | 10.0 | 70.00% | `REPORTED` |
| 13 | `CSH202C` | ANALYSIS & DESIGN OF ALGORITHMS LAB - PR | End Semester Examination | 16.0 | 20.0 | 80.00% | `REPORTED` |
| 14 | `CSH203C` | DATABASE MANAGEMENT SYSTEMS - PP | Continuous Evaluation (CE) | 12.0 | 15.0 | 80.00% | `REPORTED` |
| 15 | `CSH203C` | DATABASE MANAGEMENT SYSTEMS - PP | CE 2 | 14.0 | 15.0 | 93.33% | `REPORTED` |
| 16 | `CSH203C` | DATABASE MANAGEMENT SYSTEMS - PP | Mid Term Examinations MRU | 39.0 | 40.0 | 97.50% | `REPORTED` |
| 17 | `CSH203C` | DATABASE MANAGEMENT SYSTEMS - PP | CE 3 | 14.0 | 15.0 | 93.33% | `REPORTED` |
| 18 | `CSH203C` | DATABASE MANAGEMENT SYSTEMS - PP | CE 4 | 14.0 | 15.0 | 93.33% | `REPORTED` |
| 19 | `CSH203C` | DATABASE MANAGEMENT SYSTEMS - PP | End Semester Examination | 90.0 | 100.0 | 90.00% | `REPORTED` |
| 20 | `CSH204C` | DATABASE MANAGEMENT SYSTEMS LAB - PR | Continuous Evaluation (CE) | 9.0 | 10.0 | 90.00% | `REPORTED` |
| 21 | `CSH204C` | DATABASE MANAGEMENT SYSTEMS LAB - PR | CE 2 | 10.0 | 10.0 | 100.00% | `REPORTED` |
| 22 | `CSH204C` | DATABASE MANAGEMENT SYSTEMS LAB - PR | Mid Term Examinations MRU | 10.0 | 10.0 | 100.00% | `REPORTED` |
| 23 | `CSH204C` | DATABASE MANAGEMENT SYSTEMS LAB - PR | End Semester Examination | 19.0 | 20.0 | 95.00% | `REPORTED` |
| 24 | `CSH205C` | OOPS USING JAVA - PP | Continuous Evaluation (CE) | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 25 | `CSH205C` | OOPS USING JAVA - PP | CE 2 | 15.0 | 15.0 | 100.00% | `REPORTED` |
| 26 | `CSH205C` | OOPS USING JAVA - PP | Mid Term Examinations MRU | 30.0 | 40.0 | 75.00% | `REPORTED` |
| 27 | `CSH205C` | OOPS USING JAVA - PP | CE 3 | 15.0 | 15.0 | 100.00% | `REPORTED` |
| 28 | `CSH205C` | OOPS USING JAVA - PP | CE 4 | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 29 | `CSH205C` | OOPS USING JAVA - PP | End Semester Examination | 73.0 | 100.0 | 73.00% | `REPORTED` |
| 30 | `CSH206C` | OOPS USING JAVA LAB - PR | Continuous Evaluation (CE) | 4.0 | 5.0 | 80.00% | `REPORTED` |
| 31 | `CSH206C` | OOPS USING JAVA LAB - PR | CE 2 | 4.0 | 5.0 | 80.00% | `REPORTED` |
| 32 | `CSH206C` | OOPS USING JAVA LAB - PR | Mid Term Examinations MRU | 8.0 | 10.0 | 80.00% | `REPORTED` |
| 33 | `CSH206C` | OOPS USING JAVA LAB - PR | CE 3 | 8.0 | 10.0 | 80.00% | `REPORTED` |
| 34 | `CSH206C` | OOPS USING JAVA LAB - PR | End Semester Examination | 19.0 | 20.0 | 95.00% | `REPORTED` |
| 35 | `CSH207C` | ARTIFICIAL INTELLIGENCE - PP | Continuous Evaluation (CE) | 15.0 | 15.0 | 100.00% | `REPORTED` |
| 36 | `CSH207C` | ARTIFICIAL INTELLIGENCE - PP | CE 2 | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 37 | `CSH207C` | ARTIFICIAL INTELLIGENCE - PP | Mid Term Examinations MRU | 30.0 | 40.0 | 75.00% | `REPORTED` |
| 38 | `CSH207C` | ARTIFICIAL INTELLIGENCE - PP | CE 3 | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 39 | `CSH207C` | ARTIFICIAL INTELLIGENCE - PP | CE 4 | 13.0 | 15.0 | 86.67% | `REPORTED` |
| 40 | `CSH207C` | ARTIFICIAL INTELLIGENCE - PP | End Semester Examination | 86.0 | 100.0 | 86.00% | `REPORTED` |
| 41 | `CSH208C` | ARTIFICIAL INTELLIGENCE LAB - PR | Continuous Evaluation (CE) | 10.0 | 10.0 | 100.00% | `REPORTED` |
| 42 | `CSH208C` | ARTIFICIAL INTELLIGENCE LAB - PR | CE 2 | 8.0 | 10.0 | 80.00% | `REPORTED` |
| 43 | `CSH208C` | ARTIFICIAL INTELLIGENCE LAB - PR | Mid Term Examinations MRU | 9.0 | 10.0 | 90.00% | `REPORTED` |
| 44 | `CSH208C` | ARTIFICIAL INTELLIGENCE LAB - PR | End Semester Examination | 18.0 | 20.0 | 90.00% | `REPORTED` |
| 45 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | Continuous Evaluation (CE) | 15.0 | 15.0 | 100.00% | `REPORTED` |
| 46 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | CE 2 | 7.0 | 10.0 | 70.00% | `REPORTED` |
| 47 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | Mid Term Examinations MRU | 6.0 | 10.0 | 60.00% | `REPORTED` |
| 48 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | CE 3 | 9.0 | 15.0 | 60.00% | `REPORTED` |
| 49 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | CE 4 | 6.0 | 10.0 | 60.00% | `REPORTED` |
| 50 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | CE 5 | 6.0 | 10.0 | 60.00% | `REPORTED` |
| 51 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | CE 6 | 6.0 | 10.0 | 60.00% | `REPORTED` |
| 52 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | End Semester Examination | 43.0 | 50.0 | 86.00% | `REPORTED` |
| 53 | `CSS210C` | ADVANCED PYTHON FOR AI - PP | VIVA | 17.0 | 20.0 | 85.00% | `REPORTED` |
| 54 | `CSW209C` | WEB DESIGNING-II - PR | Continuous Evaluation (CE) | 9.0 | 10.0 | 90.00% | `REPORTED` |
| 55 | `CSW209C` | WEB DESIGNING-II - PR | CE 2 | 9.0 | 10.0 | 90.00% | `REPORTED` |
| 56 | `CSW209C` | WEB DESIGNING-II - PR | CE 3 | 7.0 | 10.0 | 70.00% | `REPORTED` |
| 57 | `CSW209C` | WEB DESIGNING-II - PR | End Semester Examination | 19.0 | 20.0 | 95.00% | `REPORTED` |
| 58 | `MAH204C` | DISCRETE MATHS - PP | Continuous Evaluation (CE) | 19.0 | 20.0 | 95.00% | `REPORTED` |
| 59 | `MAH204C` | DISCRETE MATHS - PP | CE 2 | 10.0 | 10.0 | 100.00% | `REPORTED` |
| 60 | `MAH204C` | DISCRETE MATHS - PP | Mid Term Examinations MRU | 17.0 | 40.0 | 42.50% | `REPORTED` |
| 61 | `MAH204C` | DISCRETE MATHS - PP | CE 3 | 8.0 | 10.0 | 80.00% | `REPORTED` |
| 62 | `MAH204C` | DISCRETE MATHS - PP | CE 4 | 19.0 | 20.0 | 95.00% | `REPORTED` |
| 63 | `MAH204C` | DISCRETE MATHS - PP | End Semester Examination | 73.5 | 100.0 | 73.50% | `REPORTED` |
| 64 | `RDO201C` | SOCIAL INTERNSHIP-POST 2ND SEM - PP | Continuous Evaluation (CE) | 86.0 | 100.0 | 86.00% | `REPORTED` |

*Note: Unscheduled/unapplicable assessment components (e.g. Mid Term Examinations MRU for `CSW209C` or `RDO201C`, CE 5 and CE 6 for standard lecture courses) are preserved with status `UNREPORTED`, `obtained: None`, `maximum: None`. Zero unrecorded scores were treated as 0.*

---

### 5. Data Integrity, Deduplication, & Immutability Verification

- **Snapshot ID**: `a9410bae-8496-4a0e-a64c-0880aa5cfbdb`
- **Term Key**: `2025-2026_s3_1067`
- **Storage View**: `marks:6161:3:A`
- **Data Provenance**: `LIVE_PORTAL`
- **Payload Checksum**: `b36fcba857fc73ad4397793d4086ad47754d5c957e8fa134d1561da7227bf347` (SHA-256 over canonical sorted JSON)
- **Deduplication Check**: Re-executing `persist_performance` with an identical payload returns existing row `a9410bae-8496-4a0e-a64c-0880aa5cfbdb` without duplicate insertions.
- **SQLite Engine PRAGMA Verification**:
  - `PRAGMA integrity_check` -> `[('ok',)]`
  - `PRAGMA foreign_key_check` -> `[]` (zero orphaned records)

---

### 6. Five-Semester Archive Preservation Audit

| Dataset Category | Prior Count (Pre-E.2) | Post-Import Count (Phase E.2) | Integrity Assessment |
|---|---|---|---|
| **Semester 4 Marks Snapshot** | 1 (`marks:6424:3:A`, 15 courses) | 1 (`03d1482b-c997-431f-bc88-071c3bb4c764`) | **Identical & Preserved** |
| **Semester 3 Marks Snapshot** | 0 | 1 (`a9410bae-8496-4a0e-a64c-0880aa5cfbdb`) | **Ingested Successfully** |
| **Total Academic Terms** | 5 (Semesters 1, 2, 3, 4, 5) | 5 (Semesters 1, 2, 3, 4, 5) | **Identical & Preserved** |
| **Total Catalog Courses** | 76 | 76 | **Identical & Preserved** |
| **Attendance Snapshots** | 9 | 9 | **Identical & Preserved** |
| **Attendance Snapshot Rows** | 136 | 136 | **Identical & Preserved** |
| **Attendance Period Observations**| 3,520 | 3,520 | **Identical & Preserved** |
| **Instructional Calendar parities**| 2,064 / 2,078 delivered periods | 2,064 / 2,078 delivered periods | **100% Preserved** |

---

### 7. Quality Gate Verification Table

| Quality Gate | Verification Command | Exit Code | Result | Diagnostics |
|---|---|---|---|---|
| **Python Unit & Integration Tests** | `pytest backend/tests/test_performance_pilot_e1.py` | `0` | **PASS** | 6 passed (isolation, zero-refetch, immutability, attendance preservation) |
| **Python Linting** | `ruff check backend/app backend/tests` | `0` | **PASS** | All checks passed cleanly |
| **Python Static Typing** | `mypy backend/app` | `0` | **PASS** | Success: no issues found in 44 source files |
| **Frontend Unit & Component Tests** | `vitest run --fileParallelism=false` | `0` | **PASS** | 13 test files passed, 38 tests passed |
| **Frontend TypeScript Typechecking** | `tsc --noEmit` | `0` | **PASS** | Zero type errors |
| **Frontend Production Build** | `npm run build` | `0` | **PASS** | Production bundle generated in `dist/` in 5.37s |
| **Database Foreign Key Integrity** | `PRAGMA foreign_key_check;` | `0` | **PASS** | Empty list (`[]`) |
| **Database Physical Integrity** | `PRAGMA integrity_check;` | `0` | **PASS** | `ok` |

