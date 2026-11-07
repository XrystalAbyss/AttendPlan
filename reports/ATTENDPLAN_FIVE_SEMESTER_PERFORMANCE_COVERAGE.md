# ATTENDPLAN — FIVE-SEMESTER PERFORMANCE COVERAGE
## Cross-Term Course Reconciliation & Academic Integrity

**Date:** November 2, 2026  
**Scope:** Semesters 1, 2, 3, 4, 5 (Full Historical and Ongoing Academic Span)

---

## 1. Catalog Reconciliation Matrix

| Term Key | Semester | Academic Year | Catalog Courses | Source Present | Aggregated Components | Absent / Unreported Courses | Unmapped Source Rows |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `2024-2025_s1_918` | Sem 1 | 2024–2025 | 12 | 11 | 1 | 0 | **0** |
| `2024-2025_s2_1048` | Sem 2 | 2024–2025 | 16 | 12 | 3 | 1 | **0** |
| `2025-2026_s3_1067` | Sem 3 | 2025–2026 | 16 | 13 | 1 | 2 | **0** |
| `2025-2026_s4_2508` | Sem 4 | 2025–2026 | 17 | 15 | 0 | 2 | **0** |
| `2026-2027_s5_2582` | Sem 5 | 2026–2027 | 15 | 4 | 0 | 11 | **0** |
| **Total** | | | **76** | **55** | **5** | **16** | **0** |

---

## 2. Reconciled Absence & Aggregation Explanations

### A. Aggregated Components (Total: 5)
In the university's academic structure, certain tutorial (`-TUT`) and practical (`-PR`) sections share credit, instruction, and performance evaluations under a parent theory course:
- **`MAH104C-TUT` (Sem 1)**: Tutorial sessions evaluated under parent course `MAH104C` (Probability & Statistics).
- **`CSH107C-TUT` (Sem 2)**: Tutorial sessions evaluated under parent course `CSH107C`.
- **`HLS101C-PR` (Sem 2)**: Practical sessions evaluated under parent course `HLS101C`.
- **`MAH101C-TUT` (Sem 2)**: Tutorial sessions evaluated under parent course `MAH101C`.
- **`MAH204C-TUT` (Sem 3)**: Tutorial sessions evaluated under parent course `MAH204C`.

### B. Absent / Non-Reported Courses (Total: 16)
- **Value-Added / Audit Courses (4)**:
  - `VAC-CS109` (Sem 2)
  - `VAC-CS112` (Sem 3)
  - `EDN248C` (Sem 3)
  - `VAC-CS512` (Sem 4)
  - `CSH220C` (Sem 4)
  These courses carry zero internal assessment marks or represent audit/external certifications where marks are not hosted in `myreportcard.php`.
- **Ongoing Term 5 Pending Evaluations (11)**:
  - In Semester 5 (current ongoing semester), only 4 courses currently have marks recorded in the ERP system. The remaining 11 courses are actively in session with continuous evaluations ongoing.

### C. Zero Unmapped Source Rows
Every single course code retrieved from the live portal matches a registered course in AttendPlan's academic catalog (`unmapped_count == 0` across all terms).

---

## 3. Storage and Provenance Immutability

Each snapshot is stored in SQLite table `performance_snapshots` with:
- Strict academic term foreign key isolation (`term_key`).
- Cryptographic SHA-256 canonical payload checksum.
- Non-sensitive diagnostic view tag (`marks:<session_id>:3:A`).
- Zero PII (zero student roll numbers, passwords, admission identifiers, or cookies).
- Zero refetching during import (preview payload reused verbatim).

