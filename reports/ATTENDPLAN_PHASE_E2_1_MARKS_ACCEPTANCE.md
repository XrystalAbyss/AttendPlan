# AttendPlan — Phase E.2.1 Marks Pilot Acceptance & Source-Semantics Closure

**Execution Mode**: STRICTLY OFFLINE — ZERO NEW UNIVERSITY PORTAL REQUESTS  
**Auditor**: Principal Academic Records Engineer & Data Integrity Auditor  
**Date**: November 1, 2026  
**Status**: ACCEPTED & CLOSED  

---

## 1. Executive Summary

Phase E.2.1 completes the formal verification, semantic categorization, and source reconciliation of AttendPlan's first imported academic performance pilot snapshot (Semester 3 internal marks).

All acceptance criteria have been verified offline against the persisted SQLite database (`attendplan.sqlite3`), retained source payloads, and automated test suites:

1. **Exact Scope & Fingerprint Verification**:
   - Target Scope: Academic Year `2025-2026`, Semester `3`, Class `1067` (`B.Tech CSE AIML-Sem 3`), Division `A`.
   - Exam Scope: Session `6161` (`MRU-Odd-Semester-Dec-2025-2026-5041`), Exam Type `3` (`INTERNAL EXAM`).
   - Persisted Snapshot ID: `a9410bae-8496-4a0e-a64c-0880aa5cfbdb`.
   - Persisted Storage View: `marks:6161:3:A`.
   - Checksum / Canonical SHA-256 Fingerprint: `bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee`.
   - *Provenance Note*: An earlier exploratory script logged an intermediate SHA-256 string (`b36fcba857...`), but the canonical, immutable snapshot created through the approved preview-to-import pipeline and verified by both `SyncJob` `d5dedd4a-1257-4b32-886b-52c51bdaae93` and `PerformanceSnapshot` is `bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee`.

2. **Assessment Classification Taxonomy**:
   - Implemented `AssessmentClassification` enum with 6 distinct categories.
   - Identified that the portal's internal marks PHP script embeds `EXTERNAL EXAM` (`End Semester Examination`) and `External Exam` (`VIVA`) columns directly in the continuous assessment table.
   - Implemented strict filtering: `END_SEMESTER_SOURCE_FIELD` entries are preserved as raw source fields and strictly excluded from continuous evaluation analytics, preventing confusion with official result cards.

3. **Complete 117-Cell Accounting**:
   - Exactly 13 courses $\times$ 9 assessment columns = 117 assessment cells.
   - 64 `REPORTED` cells (51 internal CEs/midterms, 12 end semester exams, 1 viva) + 53 `UNREPORTED` cells = 117 cells (100% accounted for).

4. **13 Marks vs 16 Attendance Components Reconciliation**:
   - All 13 courses in the marks snapshot match 1:1 with catalog courses (`SOURCE_COURSE_PRESENT`).
   - The 3 remaining attendance components are mathematically and institutionally explained:
     - `MAH204C-TUT` (Discrete Maths Tutorial): Continuous assessments aggregated under lecture code `MAH204C` (`COMPONENT_AGGREGATED`).
     - `EDN248C` (UHV II / SEEK): 0/0 periods delivered, non-credit audit course with no portal marks (`SOURCE_COURSE_ABSENT`).
     - `VAC-CS112` (MongoDB Java Developer Path): Value Added Course evaluated via external certificate, no portal exam entries (`SOURCE_COURSE_ABSENT`).
   - Zero unmapped marks rows (`UNMAPPED_SOURCE_ROW` count: 0).

5. **Security & Preview-to-Import Lifecycle Hardening**:
   - Redacted raw `captured_payload` from generic sync job endpoints (`GET /api/v1/portal/sync/jobs/{job_id}`).
   - Scrubbed raw payload from `SyncJob.details` after snapshot persistence.
   - Enforced preview single-use, 30-minute expiration, cross-term substitution rejection, and sync lock release.

6. **Preservation Invariant**:
   - All 5 academic terms, 76 courses, 9 attendance snapshots, 136 rows, 3,520 period observations, 28 batches, and Semester 4 marks snapshot (`03d1482b...`) remain 100% intact.

---

## 2. Assessment Classification Taxonomy

The university ERP portal (`myreportcardSave.php`) renders a grouped HTML table with 9 assessment columns grouped under three top-level headers.

To prevent mixing continuous evaluations with external exams or oral tests, AttendPlan defines the following formal taxonomy:

| Assessment Column | Source Group Header | Classification Enum | Semantic Interpretation & Policy |
| :--- | :--- | :--- | :--- |
| `CE` | `INTERNAL EXAM` | `INTERNAL_CONTINUOUS_EVALUATION` | Continuous Evaluation 1 (class test, quiz, or lab assessment). |
| `CE 2` | `INTERNAL EXAM` | `INTERNAL_CONTINUOUS_EVALUATION` | Continuous Evaluation 2. |
| `CE 3` | `INTERNAL EXAM` | `INTERNAL_CONTINUOUS_EVALUATION` | Continuous Evaluation 3. |
| `CE 4` | `INTERNAL EXAM` | `INTERNAL_CONTINUOUS_EVALUATION` | Continuous Evaluation 4. |
| `CE 5` | `INTERNAL EXAM` | `INTERNAL_CONTINUOUS_EVALUATION` | Continuous Evaluation 5 (specialized lab / AI courses). |
| `CE 6` | `INTERNAL EXAM` | `INTERNAL_CONTINUOUS_EVALUATION` | Continuous Evaluation 6 (specialized lab / AI courses). |
| `Mid term examinations MRU` | `INTERNAL EXAM` | `INTERNAL_MIDTERM` | Centrally scheduled Mid-Semester / Mid-Term examination. |
| `End Semester Examination` | `EXTERNAL EXAM` | `END_SEMESTER_SOURCE_FIELD` | Raw end-semester exam score. Preserved as a raw source field; **excluded** from continuous evaluation analytics; not treated as official grade-card result. |
| `VIVA` | `External Exam` | `VIVA` | Oral examination / practical viva voce. |

### Analytics Filtering Invariant
In `overview()` (`backend/app/services/performance_service.py`), items classified as `END_SEMESTER_SOURCE_FIELD` are filtered out when ranking assessment ratios. An explicit insight is emitted:
> `marks:6161:3:A: 13 End Semester Examination entries preserved as raw source fields; excluded from continuous evaluation analytics.`

---

## 3. 117-Cell Accounting Summary

| Assessment Column | Total Cells | REPORTED | UNREPORTED | Key Highlights |
| :--- | :---: | :---: | :---: | :--- |
| `CE` | 13 | 13 | 0 | 100% reported across all 13 subjects (70.0% – 100.0%). |
| `CE 2` | 13 | 11 | 2 | Unreported for `CDO231` (single CE course) and `RDO201C` (internship). |
| `Mid term examinations MRU`| 13 | 11 | 2 | Unreported for `CDO231` and `RDO201C`. |
| `CE 3` | 13 | 8 | 5 | Reported for 8 core theory/lab courses; unreported for non-continuous/internship. |
| `CE 4` | 13 | 6 | 7 | Reported for 6 advanced courses. |
| `CE 5` | 13 | 1 | 12 | Reported solely for `CSS210C` (Advanced Python for AI: 6.0/10.0). |
| `CE 6` | 13 | 1 | 12 | Reported solely for `CSS210C` (Advanced Python for AI: 6.0/10.0). |
| `End Semester Examination` | 13 | 12 | 1 | Reported for 12 courses; unreported only for `RDO201C` (internship). |
| `VIVA` | 13 | 1 | 12 | Reported solely for `CSS210C` (Advanced Python for AI: 17.0/20.0 = 85.0%). |
| **Total** | **117** | **64** | **53** | **Exact sum: 64 + 53 = 117 cells (100.0%)** |

---

## 4. Course Coverage Reconciliation

| Course Code | Course Name | In Marks? | Coverage Category | Resolution & Institutional Rationale |
| :--- | :--- | :---: | :--- | :--- |
| `CDO231` | Professional Competency Enhancement-I | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH201C` | Analysis & Design of Algorithms | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH202C` | Analysis & Design of Algorithms Lab | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH203C` | Database Management Systems | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH204C` | Database Management Systems Lab | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH205C` | OOPS Using Java | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH206C` | OOPS Using Java Lab | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH207C` | Artificial Intelligence | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSH208C` | Artificial Intelligence Lab | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSS210C` | Advanced Python for AI | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `CSW209C` | Web Designing-II | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `EDN248C` | UHV II / SEEK | No | `SOURCE_COURSE_ABSENT` | 0/0 delivered periods; audit / non-credit course without university marks. |
| `MAH204C` | Discrete Maths | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match (theory lecture). |
| `MAH204C-TUT`| Discrete Maths Tutorial | No | `COMPONENT_AGGREGATED` | Tutorial component (10/13 periods); continuous assessments aggregated into `MAH204C`. |
| `RDO201C` | Social Internship-Post 2nd Sem | Yes | `SOURCE_COURSE_PRESENT` | Direct 1:1 match. |
| `VAC-CS112` | MongoDB Java Developer Path | No | `SOURCE_COURSE_ABSENT` | Value Added Course (18/18 periods); evaluated by external industry certificate. |

- Total Catalog Courses: **16**
- Total Marks Courses: **13**
- Present Count: **13**
- Aggregated Count: **1**
- Absent Count: **2**
- Unmapped Marks Count: **0**

---

## 5. Security & Privacy Audit Verification

1. **Zero PII Exposure**:
   - Automated scans of the SQLite database and sync logs confirm zero passwords, OTPs, session cookies, or student personal information.
2. **Payload Redaction in Generic Sync APIs**:
   - `sanitize_sync_job_details()` implemented in `backend/app/api/routes.py`.
   - `GET /api/v1/portal/sync/jobs/{job_id}` and `GET /api/v1/portal/sync/jobs/latest` redact `captured_payload` to `{"redacted": True, "course_count": N, "summary": "..."}`.
3. **Post-Import Payload Scrubbing**:
   - `capture_performance()` in `backend/app/api/performance_routes.py` scrubs `captured_payload` from `SyncJob.details` once persisted to `PerformanceSnapshot`.
4. **Preview Token State Machine**:
   - Tested single-use transition (`COMPLETED` -> `APPROVED`), 30-minute expiry window, and cross-term substitution rejection.

---

## 6. Release Verification & Quality Gates

| Quality Gate | Tool / Command | Result | Details |
| :--- | :--- | :---: | :--- |
| Backend Unit & Acceptance Tests | `pytest backend/tests` | **PASS** | **291 passed**, 0 failures, 1 warning (deprecation). |
| New Acceptance Tests | `pytest backend/tests/test_performance_acceptance_e2_1.py` | **PASS** | **10 passed**, 0 failures. |
| Python Linting | `ruff check backend/app backend/tests` | **PASS** | Zero linting errors. |
| Python Type Checking | `mypy backend/app` | **PASS** | 44 source files checked, zero issues. |
| Frontend Unit Tests | `vitest run --run` | **PASS** | 13 test files, **38 passed**, 0 failures. |
| Frontend Type Checking | `tsc --noEmit` | **PASS** | Zero TypeScript compilation errors. |
| Frontend Production Build | `npm run build` (Vite) | **PASS** | Built cleanly in 4.18s. |
| Database Baseline Integrity | `PRAGMA integrity_check` | **PASS** | `ok`, zero FK violations, 5 terms preserved. |

---

## 7. Acceptance Declaration

Phase E.2.1 has met all criteria. The Semester 3 internal marks pilot snapshot is formally accepted into AttendPlan's local database. No new university requests were executed during this phase.

AttendPlan remains in a fully functional, verified, and test-covered state.

