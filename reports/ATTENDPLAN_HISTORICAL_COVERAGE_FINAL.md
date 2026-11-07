# ATTENDPLAN — HISTORICAL COVERAGE FINAL AUDIT
## Complete Academic Archive Coverage (Semesters 1 through 5)
### Institutional Ledger & Reconciliation Provenance

**Document Version:** 1.0  
**Audit Date:** 2026-11-01  
**Degree Program:** B.Tech Computer Science & Engineering (Artificial Intelligence & Machine Learning)  
**Database:** `C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3`  
**Integrity State:** Validated (`PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check = 0`)  

---

## 1. Executive Summary

This document constitutes the definitive coverage audit of the AttendPlan historical academic archive following the completion of **Phase D.4**.

AttendPlan now maintains a fully verified, multi-semester attendance repository representing **all five semesters** of the student's undergraduate tenure. Every enrolled course across 5 semesters has been mapped, period observations ingested, and reconciliation metrics computed against official university ERP portal summaries.

---

## 2. Semester Coverage Matrix

```
Degree Program: B.Tech CSE AIML
Total Instruction Periods Delivered: 2,078
Total Instruction Periods Attended:  1,806
Aggregate Cumulative Attendance:     86.91%
Statutory Institutional Threshold:  75.00%
Safety Standing:                    SECURE (+247 Periods above 75% Target)
```

### Term-by-Term Overview

| Semester | Academic Year | Class ID | Enrolled Courses | Portal Window | Subject Att/Del | Daywise Att/Del | Timetable Obs | Coverage State |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Semester 1** | 2024–2025 | 918 | 12 | 2024-07-01 to 2024-12-31 | 275 / 293 (93.86%) | 275 / 293 (93.86%) | 413 | **100% COMPLETE & MATCHED** |
| **Semester 2** | 2024–2025 | 1048 | 16 | 2025-01-13 to 2025-05-02 | 381 / 446 (85.43%) | 296 / 356 (83.15%) | 430 | **COMPLETE (Feb–May Ledger)** |
| **Semester 3** | 2025–2026 | 1067 | 16 | 2025-07-14 to 2025-11-22 | 400 / 463 (86.39%) | 373 / 436 (85.55%) | 680 | **COMPLETE (Aug–Nov Ledger)** |
| **Semester 4** | 2025–2026 | 2508 | 17 | 2026-01-01 to 2026-05-16 | 485 / 554 (87.55%) | 476 / 545 (87.34%) | 729 | **COMPLETE (Jan–May Ledger)** |
| **Semester 5** | 2026–2027 | 2582 | 15 | 2026-08-04 to 2026-11-27 | 265 / 322 (82.30%) | 663 / 838 (Live) | 1,112 | **ACTIVE CURRENT TERM** |
| **TOTALS** | — | — | **76 Courses** | — | **1,806 / 2,078** | — | **3,364 Obs** | **COMPLETE COVERAGE** |

---

## 3. Month-by-Month Observation Ledger

The historical archive indexes **26 observation batches** comprising **3,364 timetable slot observations** across 24 unique calendar months:

### Semester 1 (AY 2024–2025)
- **2024-08**: 98 observations (62 attended / 64 delivered, 14 active days)
- **2024-09**: 105 observations (74 attended / 78 delivered, 15 active days)
- **2024-10**: 112 observations (79 attended / 81 delivered, 16 active days)
- **2024-11**: 98 observations (60 attended / 70 delivered, 14 active days)
- *Total Timetable Days*: 59 instruction days, 293 scheduled periods, 120 holiday/free periods.

### Semester 2 (AY 2024–2025)
- **2025-01**: Unrecorded timetable in ERP filters (`FILTER_SELECTION_MISMATCH`, 0 obs)
- **2025-02**: 152 observations (102 attended / 118 delivered, 19 active days)
- **2025-03**: 88 observations (71 attended / 73 delivered, 11 active days)
- **2025-04**: 176 observations (112 attended / 153 delivered, 22 active days)
- **2025-05**: 14 observations (11 attended / 12 delivered, 2 active days)
- *Total Timetable Days*: 54 instruction days, 356 scheduled periods, 74 holiday/free periods.

### Semester 3 (AY 2025–2026)
- **2025-08**: 200 observations (122 attended / 130 delivered, 20 active days)
- **2025-09**: 170 observations (93 attended / 119 delivered, 17 active days)
- **2025-10**: 160 observations (82 attended / 96 delivered, 16 active days)
- **2025-11**: 150 observations (76 attended / 91 delivered, 15 active days)
- *Total Timetable Days*: 68 instruction days, 436 scheduled periods, 244 holiday/free periods.

### Semester 4 (AY 2025–2026)
- **2026-01**: 153 observations (95 attended / 100 delivered, 17 active days)
- **2026-02**: 180 observations (122 attended / 147 delivered, 20 active days)
- **2026-03**: 153 observations (104 attended / 110 delivered, 17 active days)
- **2026-04**: 234 observations (146 attended / 179 delivered, 25 active days)
- **2026-05**: 9 observations (9 attended / 9 delivered, 2 active days)
- *Total Timetable Days*: 81 instruction days, 545 scheduled periods, 184 holiday/free periods.

### Semester 5 (AY 2026–2027, Ongoing Live Sync)
- **2026-08**: 2 observation batches (August instruction)
- **2026-09**: 2 observation batches (September instruction)
- **2026-10**: 5 observation batches (October instruction, including 2026-10-28 and 2026-10-30 snapshots)
- *Total Observations*: 1,112 slot records across 53 active instruction days.

---

## 4. Reconciliation Findings & Mathematical Provenance

### Invariant Audit:
1. **Semester 1 Perfect Parity**:
   Every single course has exact equality between Subject Summary ($S$) and Day-wise ($D$):
   $$\forall c \in \text{Courses}(S_1): \quad S_{att}(c) = D_{att}(c) \quad \land \quad S_{del}(c) = D_{del}(c)$$
   No date window loss, no unmapped periods, 100% course mapping fidelity.

2. **Semester 3 July Window Truncation**:
   The subject-wise report covers `2025-07-14` to `2025-11-22`.
   The day-wise import covers months `2025-08` through `2025-11`.
   The delta across all courses is:
   $$\Delta_{att} = 400 - 373 = 27, \quad \Delta_{del} = 463 - 436 = 27$$
   Because $\Delta_{att} = \Delta_{del}$, the student attended **100% of the 27 periods held in late July 2025**.

3. **Semester 2 January Start Window**:
   The subject-wise report covers `2025-01-13` to `2025-05-02`.
   The day-wise import covers months `2025-02` through `2025-05`.
   The delta across all courses is:
   $$\Delta_{att} = 381 - 296 = 85, \quad \Delta_{del} = 446 - 356 = 90 \quad (94.4\% \text{ attendance})$$

4. **Semester 4 May Examination Window**:
   The subject-wise report covers `2026-01-01` to `2026-05-16`.
   The day-wise import covers dates through `2026-05-02`.
   The delta is exactly $9$ attended and $9$ delivered (100% attendance during exam period).

---

## 5. Course Catalog & Component Disambiguation

Because university ERP databases frequently reuse base course codes across lecture and practical/tutorial components, AttendPlan has established canonical course identifiers:

- Theory courses retain primary code (e.g. `MAH104C`, `CSH107C`, `MAH204C`).
- Tutorial components receive `-TUT` suffix (e.g. `MAH104C-TUT`, `CSH107C-TUT`, `MAH204C-TUT`).
- Practical / Laboratory components receive `-PR` suffix (e.g. `CSS104C-PR`, `HLS101C-PR`).
- Value-added courses preserve prefix formatting (e.g. `VAC-CS109`, `VAC-CS112`).

This ensures multi-term isolation, zero unique constraint collisions, and seamless aggregation in institutional analytics.

---

## 6. Academic Standing & Margin Calculations

Under the institutional 75% attendance threshold:
- **Cumulative Periods Delivered**: 2,078
- **Cumulative Periods Attended**: 1,806
- **Current Degree Percentage**: **86.91%**
- **Safe Absence Margin (Bunk Margin)**:
  $$\text{safe\_bunks} = \max\left(0, \left\lfloor \frac{1806}{0.75} - 2078 \right\rfloor\right) = \lfloor 2408.0 - 2078 \rfloor = \mathbf{330 \text{ periods}}$$
  The student could theoretically miss up to 330 instruction periods across their degree while remaining at or above the 75.0% threshold.

---

## 7. Operational Readiness & Release Status

AttendPlan's multi-semester historical archive is declared **COMPLETE and PRODUCTION READY**:
- All 5 semesters loaded in local SQLite database.
- 267 backend automated tests passing.
- 38 frontend automated tests passing.
- Full TypeScript and Python typing validated.
- Production UI build verified.
- Dedicated Chrome profile and live sync workflow completely preserved.

