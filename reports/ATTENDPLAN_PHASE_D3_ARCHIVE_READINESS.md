# AttendPlan Phase D.3: Historical Archive Readiness Report
## Semesters 1–3 Preparation, Source Integrity & Calendar-Aware Recovery

**Date:** October 30, 2026  
**Auditor & Architect:** Principal Software Architect & Academic Data Integrity Lead  
**Operating Environment:** Windows 11, SQLite WAL, FastAPI Backend, React 19 / TypeScript Frontend  
**Database Location:** `C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3`  
**Consistent Pre-D.3 Backup:** `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_d3_backup.sqlite3` (1,056,768 bytes)  
**Overall Readiness Status:** **`VERIFIED_OFFLINE` & `AWAITING_USER_APPROVAL`**  

---

## 1. Executive Summary & Authorization Boundary

In strict compliance with **Section 3 of AGENTS.md** and user instructions:
- **No live historical requests were executed** for Semesters 1, 2, or 3.
- The user previously authorized only Semester 4's Jan–May 2026 pilot.
- All preflight audits, SQLite integrity validations, Semester 4 mapping integrity checks, evidence cataloging, calendar configuration, and safe offline simulations have been completed.
- This document reports the complete system readiness and establishes the precise verification checkpoints required prior to any future live extraction.

---

## 2. Mandatory Pre-Import Data Integrity Gate

A read-only forensic audit was performed on the active SQLite database:

| Integrity Check | Command / Operation | Result | Status |
| :--- | :--- | :---: | :---: |
| **SQLite Page Integrity** | `PRAGMA integrity_check;` | `ok` | **PASS** |
| **Foreign Key Constraints** | `PRAGMA foreign_key_check;` | `0 violations` | **PASS** |
| **Pre-D.3 Backup Creation** | `sqlite3.backup` API | `1,056,768 bytes` | **PASS** |
| **Semester 5 Live Baseline** | Isolated Term Query | 260 attended / 313 delivered (83.07%) | **UNTOUCHED** |
| **Semester 4 Course Entities** | Active Term Inventory | Exactly 17 canonical courses | **VERIFIED** |
| **Semester 4 Reassociated FKs** | Observation Grouping | Exactly 554 course-linked observations | **VERIFIED** |
| **Semester 4 Unmapped Observations**| Null `course_id` Query | Exactly 175 observations (0 attended / 0 delivered) | **VERIFIED** |
| **Semester 4 Marks Snapshot** | `performance_snapshots` | Snapshot `marks:6424:3:A` (15 courses) | **PRESERVED** |

### Verification of Phase D.2 Mapping Repairs:
1. **Zero Observation Loss**: All 729 Semester 4 observations ($81 \text{ dates} \times 9 \text{ periods}$) are present in `attendance_period_observations`.
2. **Deterministic Course Binding**: All 554 period observations with course labels map directly to one of the 17 authoritative courses in Semester 4.
3. **Semantic Invariant Compliance**: The 175 blank/free slots are correctly marked with `status = PeriodStatus.NOT_REPORTED`, `delivered = 0, attended = 0`. In accordance with Invariant #11, zero blank slots are counted as absences.
4. **Purged Entities Audit**: The 16 temporary placeholder courses purged in Phase D.2 possessed zero unique curricular data (they were partial label artifacts generated before title-aware matching was introduced). No legitimate data was destroyed.

---

## 3. Semester 4 Reconciled Accounting & Remaining Uncertainty

The Semester 4 reconciliation state is maintained as **`SOURCE_DISCREPANCY`**:

- **Official Master Subject-Wise Summary**: 485 attended / 554 delivered (87.55%)
- **Granular Day-Wise Timetable Observations**: 476 attended / 545 delivered (87.34%)
- **Identified Gap**: Exactly $+9$ attended / $+9$ delivered across two specific dates:
  - `2026-02-26` (Thursday): 4 periods (`CSH213C`, `MCS368C`, `ECH108C`, `CDO232`)
  - `2026-04-08` (Wednesday): 5 periods (`CSH215C`, `CDO232`, `CSH213C`, `CSH214C` $\times 2$)
- **Resolution**: In accordance with **Invariant #3 (Zero Fabricated Data)**, these 9 periods are preserved as `NOT_REPORTED` in day-wise data. They are not artificially marked `PRESENT` to force numerical equality. The discrepancy is documented with full provenance.

---

## 4. Semesters 1–3 Source Evidence & Selector Verification

Forensic inspection of discovery jobs (`c8498eae-6592-4d1a-9a64-c973a8cb1ac0` and `a72fdb3a-00d1-4a51-b4ae-97a3862a6fe2`) revealed the following verified selector options on `myattendance.php`:

| Academic Year | Semester | Portal Class ID | Portal Dropdown Label | Candidate Teaching Months | Confidence | Status |
| :---: | :---: | :---: | :--- | :--- | :---: | :---: |
| **2024–2025** | **1** | `918` | `B.Tech CSE AIML-Sem 1` | `2024-08`, `2024-09`, `2024-10`, `2024-11` (4 mos) | `PROVISIONAL` | Ready for live verification |
| **2024–2025** | **2** | `1048` | `B.Tech CSE AIML-Sem 2` | `2025-01`, `2025-02`, `2025-03`, `2025-04`, `2025-05` (5 mos) | `PROVISIONAL` | Ready for live verification |
| **2025–2026** | **3** | `1067` | `B.Tech CSE AIML-Sem 3` | `2025-08`, `2025-09`, `2025-10`, `2025-11` (4 mos) | `PROVISIONAL` | Ready for live verification |

> [!NOTE]
> Synthetic test fixtures in `backend/tests/fixtures/` use legacy synthetic IDs (`1050`, `1410`, `1820`). The real portal discovery logs independently verified that the student's actual enrolled section IDs are **`918`**, **`1048`**, and **`1067`**.

---

## 5. Calendar Configuration & Guard Integrity

The `AcademicTermCalendarService` enforces strict temporal boundaries:
- **Odd Semesters (1, 3)**: August through November (4 months). Non-teaching months June, July, and December are excluded.
- **Even Semester (2)**: January through May (5 months). Non-teaching months June and July are excluded.
- **Total Historical Requests Ceiling**: Exactly **16 requests maximum**:
  - Semester 3: 1 summary + 4 months = **5 requests**
  - Semester 2: 1 summary + 5 months = **6 requests**
  - Semester 1: 1 summary + 4 months = **5 requests**
- **Temporal Invariant Guards**: Attempts to request out-of-window months (e.g. `2025-06` or `2024-12`) are intercepted and rejected with `OUTSIDE_CALENDAR_WINDOW`, resulting in **zero network calls**.

---

## 6. Academic Performance & Marks Audit

Forensic inspection of `performance_snapshots` and discovery job `e7c87a5d-9e89-415a-ba88-3c4f6a427145`:

| Assessment Type | Exam Session Discovered | Route / Adapter | Extraction Feasibility | AttendPlan Handling |
| :--- | :--- | :---: | :---: | :--- |
| **Internal / Sessional (Odd)** | `6161` (Dec 2025–2026) | `myreportcard.php` | `SUPPORTED` | Extract Sessional 1, Sessional 2, CE 1–8 |
| **Internal / Sessional (Even)**| `6424` (May 2025–2026) | `myreportcard.php` | `VERIFIED` | Stored in snapshot `marks:6424:3:A` (15 courses) |
| **External / End-Semester** | `6161` / `6424` (Type 4) | `myreportcard.php` | `MASKED_BY_PORTAL` | Display masked badge; record zero/null |
| **Official SGPA / CGPA** | Controller of Exams | Not on reportcard | `UNAVAILABLE_ON_PORTAL` | Direct user to official university grade transcript |

Marks extraction remains completely decoupled from attendance requests and is **not included in the 16 attendance requests ceiling**.

---

## 7. Current Semester Protection (`Launch-AttendPlan.cmd`)

The Phase C.2 daily workflow for Semester 5 remains completely autonomous:
1. `Launch-AttendPlan.cmd` starts backend and frontend with localhost binding (`127.0.0.1`).
2. Cached attendance records load immediately from SQLite.
3. Automated Keycloak authentication reuses existing CDP Chrome session without prompting for credentials.
4. Refresh service updates Semester 5 subject summary and current month day-wise records.
5. All background historical jobs execute under a strict single-job mutex (`_SYNC_LOCK`), preventing race conditions or deadlock with current-term refreshes.

---

## 8. Quality Gates & Verification Summary

| Gate | Target | Result | Status |
| :--- | :--- | :---: | :---: |
| **Backend Unit & Domain Tests** | `pytest backend/tests` | 267 passed in 7.53s | **PASS** |
| **Backend Static Analysis** | `ruff check backend/app backend/tests` | All checks passed | **PASS** |
| **Backend Type Safety** | `mypy backend/app` | 0 issues in 44 files | **PASS** |
| **Frontend Unit & Component Tests** | `vitest run` | 38 passed in 18.55s | **PASS** |
| **Frontend TypeScript Compilation** | `tsc --noEmit` | 0 type errors | **PASS** |
| **Frontend Production Build** | `vite build` | Production bundle built | **PASS** |
| **SQLite Page Integrity** | `PRAGMA integrity_check;` | `ok` | **PASS** |
| **Foreign Key Integrity** | `PRAGMA foreign_key_check;` | 0 violations | **PASS** |
| **Sanitization & PII Audit** | `test_sanitization.py` | 0 PII leaks | **PASS** |

---

## 9. Next Steps: Checkpoint Awaiting User Approval

All safe offline engineering, data validation, and import planning are complete.

The system is now paused at:
**`AWAITING_USER_APPROVAL`**

Before initiating any live historical extraction on the university portal, explicit user approval is required for the scope detailed in `reports/ATTENDPLAN_SEMESTERS_1_3_IMPORT_PLAN.md`.

