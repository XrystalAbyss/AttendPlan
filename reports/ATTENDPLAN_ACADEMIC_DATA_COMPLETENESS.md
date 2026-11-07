# ATTENDPLAN — ACADEMIC DATA COMPLETENESS AUDIT
## Full Dual-Archive Reconciliation: Attendance & Academic Marks

**Auditor:** Principal Software Architect & Academic Records Auditor  
**Date:** November 2, 2026  
**Scope:** Five Semesters (AY 2024–2025 through AY 2026–2027)

---

## 1. Dual-Archive Coverage Summary

| Academic Term | Term Key | Attendance Catalog Courses | Subject-Wise Attended / Delivered | Day-Wise Observations | Marks Source Courses | Total Assessment Cells |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Semester 1** | `2024-2025_s1_918` | 12 | 275 / 293 (93.86%) | 413 | 11 | 66 |
| **Semester 2** | `2024-2025_s2_1048` | 16 | 381 / 446 (85.43%) | 550 | 12 | 108 |
| **Semester 3** | `2025-2026_s3_1067` | 16 | 400 / 463 (86.39%) | 716 | 13 | 117 |
| **Semester 4** | `2025-2026_s4_2508` | 17 | 485 / 554 (87.55%) | 729 | 15 | 165 |
| **Semester 5** | `2026-2027_s5_2582` | 15 | 265 / 322 (82.30%) | 1,112 | 4 | 12 |
| **Total Archive** | **5 Semesters** | **76** | **1,806 / 2,078** | **3,520** | **55** | **468** |

---

## 2. Academic Integrity Principles Satisfied

1. **Localhost & Privacy First**:
   Student attendance records, marks, and session data remain strictly within `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`.
2. **Zero Fabricated Data**:
   Missing evaluations are explicitly retained as `UNREPORTED` (`None`), never defaulted to 0 or 100%. Unrecorded ongoing Semester 5 courses remain `SOURCE_COURSE_ABSENT` pending future evaluations.
3. **Exact Mathematical Modeling**:
   Attendance percentages and bunks are computed via rational arithmetic under the 75% threshold. Performance scores preserve raw obtained/maximum ratios without invented weightage formulas.
4. **Zero Speculative Results**:
   SGPA, CGPA, and letter grades are kept `None`. No external result cards or grading systems were guessed or synthesized.
5. **Deduplication & Revision Provenance**:
   Canonical SHA-256 fingerprints ensure identical reports never duplicate records, while genuine revisions retain their lineage.

---

## 3. Outstanding Academic Source Limitations

1. **ERP Masking in Historical Records**:
   In Semester 4 (`2025-2026_s4_2508`), the university portal renders `*` characters in the `End Semester Examination` column. These remain preserved as `MASKED_BY_PORTAL` without attempting to guess the scores.
2. **Active-Term Publication Incompleteness**:
   In Semester 5 (`2026-2027_s5_2582`), continuous evaluations for 11 practical/elective courses have not yet been uploaded by university instructors. These are correctly catalogued as pending/unrecorded.
3. **Value-Added / Non-Credit Courses**:
   Courses such as `VAC-CS109`, `VAC-CS112`, `VAC-CS512`, and `EDN248C` carry attendance tracking in the university system but do not receive internal assessment marks in `myreportcard.php`.

---

## 4. Next Milestone Roadmap: Official Results & Grades

With both attendance and internal marks fully verified across five semesters, the application is positioned for future results development:
- **Phase F1 / External Results**: Dedicated integration with official university grade cards and SGPA/CGPA result sheets.
- **Unified Academic Dashboard**: Cohesive student intelligence linking 75% attendance threshold monitoring with continuous internal marks and historical SGPA trends.

