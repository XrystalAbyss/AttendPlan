# ATTENDPLAN — OFFICIAL ACADEMIC RESULTS SOURCE MATRIX
**Document Version:** 1.1.0 (Phase E.6.1 Forensic Reconciliation)  
**Date:** November 2, 2026  
**Auditor:** Principal Data Integrity Auditor & Google Antigravity Flash 3.8  
**Scope:** Five Academic Semesters (Semesters 1 through 5, AY 2024–2025 to AY 2026–2027)  
**Security Boundary:** Strictly Offline Research & Structural Specification — Zero University Network Calls

---

## 1. Overview & Data Class Disambiguation

AttendPlan enforces a strict institutional separation among three fundamental academic data classes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ACADEMIC DATA CLASSIFICATION                          │
├────────────────────────┬──────────────────────────┬─────────────────────────┤
│ DATA CLASS A           │ DATA CLASS B             │ DATA CLASS C            │
│ Internal Marks Matrix  │ Official Academic Results│ Derived Analytics       │
├────────────────────────┼──────────────────────────┼─────────────────────────┤
│ • Continuous Eval (CE) │ • Letter Grades (A+, B)  │ • Progress tracking     │
│ • Midterm exams (MST)  │ • Numerical Grade Points │ • Credit accumulation   │
│ • Practical / Labs     │ • Official Course Credits│ • Attendance vs marks   │
│ • Type 3 report cards  │ • Official SGPA / CGPA   │   correlation           │
│ • Raw obtained / max   │ • Result Status (PASS)   │ • Strictly labeled as   │
│                        │ • Grade Sheet / Transcr. │   local calculations    │
└────────────────────────┴──────────────────────────┴─────────────────────────┘
```

**Non-Negotiable Invariant:** Letter grades, grade points, SGPA, and CGPA must originate strictly from authoritative university source documents (Data Class B). AttendPlan will **never** synthesize, estimate, or extrapolate letter grades or GPA from raw internal assessment marks (Data Class A).

---

## 2. Five-Semester Academic Archive Source Matrix (Forensically Verified)

The following table provides the authoritative, database-verified source landscape across all five enrolled semesters:

| Semester | Academic Year | Term Key | Class Identifier | Attendance Baseline (Catalog Courses / Periods / Obs) | Class A: Internal Marks Status (Courses / Cols / Cells / SHA-256) | Class B: Official Results Status | Expected Result Source Category |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Semester 1** | 2024–2025 | `2024-2025_s1_918` | Class 918 | 12 courses<br>275 / 293 (93.86%)<br>413 observations | **CAPTURED & VERIFIED**<br>11 courses, 6 cols, 66 cells<br>(48 reported, 18 unreported)<br>SHA-256: `d0bafbaefa6aa5...` | **DISCOVERY_REQUIRED / NOT_FETCHED**<br>(Completed historical term; portal grade sheet availability not yet discovered) | Official Grade Card / Transcript<br>(Credits, Letter Grades, SGPA) |
| **Semester 2** | 2024–2025 | `2024-2025_s2_1048` | Class 1048 | 16 courses<br>381 / 446 (85.43%)<br>550 observations | **CAPTURED & VERIFIED**<br>12 courses, 9 cols, 108 cells<br>(57 reported, 51 unreported)<br>SHA-256: `c8110fdf0233ba...` | **DISCOVERY_REQUIRED / NOT_FETCHED**<br>(Completed historical term; portal grade sheet availability not yet discovered) | Official Grade Card / Transcript<br>(Credits, Letter Grades, SGPA) |
| **Semester 3** | 2025–2026 | `2025-2026_s3_1067` | Class 1067 | 16 courses<br>400 / 463 (86.39%)<br>716 observations | **CAPTURED & VERIFIED**<br>13 courses, 9 cols, 117 cells<br>(64 reported, 53 unreported)<br>SHA-256: `bdae037d0a8ca7...` | **DISCOVERY_REQUIRED / NOT_FETCHED**<br>(Completed historical term; portal grade sheet availability not yet discovered) | Official Grade Card / Transcript<br>(Credits, Letter Grades, SGPA) |
| **Semester 4** | 2025–2026 | `2025-2026_s4_2508` | Class 2508 | 17 courses<br>485 / 554 (87.55%)<br>729 observations | **CAPTURED & VERIFIED**<br>15 courses, 11 cols, 165 cells<br>(59 rep., 91 unrep., 15 masked)<br>SHA-256: `c237d69522cd67...` | **DISCOVERY_REQUIRED / NOT_FETCHED**<br>(Completed historical term; portal grade sheet availability not yet discovered) | Official Grade Card / Transcript<br>(Credits, Letter Grades, SGPA) |
| **Semester 5** | 2026–2027 | `2026-2027_s5_2582` | Class 2582 | 15 courses<br>265 / 322 (82.30%)<br>1,112 observations | **CAPTURED & VERIFIED**<br>4 courses, 3 cols, 12 cells<br>(10 reported, 2 unreported)<br>SHA-256: `4e040f42019bea...` | **NOT_DECLARED_BY_UNIVERSITY / NOT_FETCHED**<br>(Ongoing academic term; end-semester examinations have not concluded) | Future Term Grade Card<br>(Pending term completion) |
| **Total Archive** | **5 Terms** | | | **76 Catalog Courses**<br>**1,806 / 2,078 Periods**<br>**3,520 Observations** | **55 Courses, 468 Cells**<br>**(238 rep., 215 unrep., 15 masked)**<br>**5 Verified Checksums** | **0 Grade Cards Retrieved**<br>**(Strictly Offline Readiness)** | |

---

## 3. Official Results Readiness Status Accounting

To prevent claiming premature operational readiness, the components of Official Academic Results integration are formally audited below:

| System Layer | Implementation Status | Evidence / Notes |
| :--- | :---: | :--- |
| **1. Domain Schemas & Models** | **IMPLEMENTED & VERIFIED** | Pure dataclasses in `app.domain.results_models`: `OfficialCourseResult`, `OfficialSemesterResult`, `OfficialResultSnapshot`, `ResultPublicationStatus`. 100% unit test coverage. |
| **2. Relational Database Persistence** | **NOT IMPLEMENTED** | Dedicated relational tables for official grade sheets do not yet exist in Alembic schema. Only generic `performance_snapshots` table exists. |
| **3. API Endpoints & Routes** | **NOT IMPLEMENTED** | Only preview/overview routes for internal marks (`view="marks"`) are live. No dedicated `/api/v1/results/*` routes have been implemented. |
| **4. Portal Extraction Adapter** | **NOT IMPLEMENTED** | `app.adapters.performance_portal` only implements Type 3 internal report extraction (`myreportcard.php`). No HTML parser for grade sheets or transcript PDFs exists. |
| **5. Local Source Evidence** | **NOT FETCHED** | Zero official grade cards, transcript HTMLs, or result documents have been collected or stored in fixtures. |
| **6. Live Portal Retrieval** | **NOT FETCHED** | Zero live ERP calls executed. No sessions or grade cards queried. |

---

## 4. University Portal Integration Architecture (Discovery Strategy)

### 4.1 Candidate Endpoints for Future Discovery
In the iCloudEMS university portal ecosystem (`mrei.icloudems.com`), candidate endpoints to inspect during a future authorized session:
1. **Module: Internal Assessment Report Card (`myreportcard.php`)**
   - **Path:** `/corecampus/student/reportcard/myreportcard.php`
   - **Currently Used:** `exam_type=3` (Internal Exam).
   - **Candidate Inspection:** `exam_type=4` (External Exam). Must determine if Type 4 publishes raw external exam scores or consolidated grades.
2. **Module: Examination & Grade Card Services**
   - **Candidate Paths to Verify:**
     - `/corecampus/student/examination/grade_card.php`
     - `/corecampus/student/examination/result_card.php`
     - `/corecampus/student/academic/semester_result.php`
   - **Inspection Rule:** Must check actual portal student navigation DOM before constructing request parameters.

### 4.2 Reconciliation with Course Catalog
When official grade cards are eventually retrieved, each course will be matched against the 76-course attendance catalog:
1. **Exact Code Match:** Direct match within identical `academic_term_id`.
2. **Normalized Variant Match:** Matching base course codes (e.g. handling theory/practical combinations).
3. **Credit Verification:** Cross-referencing declared credits against catalog credits.
4. **Reconciliation Categories:**
   - `OFFICIAL_COURSE_MATCHED`: 1-to-1 match with catalog course.
   - `OFFICIAL_COURSE_UNMAPPED`: Course on grade card not found in timetable (e.g. external NPTEL/MOOC).
   - `CATALOG_COURSE_UNREPORTED`: Course present in timetable but missing from grade card (e.g. non-credit audit).

---

## 5. Security & Privacy Guarantees

1. **Local-First Isolation:** Official result records will reside strictly inside local SQLite (`attendplan.sqlite3`).
2. **Zero PII Retention:** Personal names, student roll numbers, and parent details will be scrubbed before hashing and persistence.
3. **Deterministic Canonical Fingerprints:** Canonical SHA-256 hashes will be computed over lexicographically sorted course arrays to guarantee bit-for-bit idempotency.
