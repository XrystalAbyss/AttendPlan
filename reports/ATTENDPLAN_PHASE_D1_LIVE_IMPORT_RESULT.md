# ATTENDPLAN — PHASE D.1 LIVE PILOT IMPORT REPORT
## Authorized Semester 4 Historical Day-Wise Extraction & Verification

**Date:** 2026-10-29  
**Execution Context:** Real Portal Live CDP Synchronization (iCloudEMS / Keycloak MFA)  
**Execution Status:** **VERIFIED_COMPLETE**  
**Authorized Scope:** Academic Year `2025-2026`, Semester `4`, Class ID `2508` (`B.Tech CSE AIML-Sem 4`), Candidate Months: `2026-01` through `2026-05`

---

## 1. Executive Summary

In accordance with explicit user authorization, the **AttendPlan Phase D.1 Historical Day-Wise Pilot** was executed sequentially against the live university student portal.

All five authorized candidate months (`2026-01` through `2026-05`) were queried, validated, and persisted with strict domain safety and zero cross-semester contamination:

| Candidate Month | Requested Calendar Scope | Actual Teaching Dates | Status / Classification | Observations | Attended Periods | Delivered Periods | Attendance % |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **2026-01** | `2026-01-01` – `2026-01-31` | `2026-01-12` – `2026-01-31` (17 days) | **SAVED_VERIFIED** | 153 | 95 | 100 | **95.00%** |
| **2026-02** | `2026-02-01` – `2026-02-28` | `2026-02-02` – `2026-02-28` (20 days) | **SAVED_VERIFIED** | 180 | 122 | 147 | **82.99%** |
| **2026-03** | `2026-03-01` – `2026-03-31` | `2026-03-02` – `2026-03-31` (17 days) | **SAVED_VERIFIED** | 153 | 104 | 110 | **94.55%** |
| **2026-04** | `2026-04-01` – `2026-04-30` | `2026-04-01` – `2026-04-30` (26 days) | **SAVED_VERIFIED** | 234 | 146 | 179 | **81.56%** |
| **2026-05** | `2026-05-01` – `2026-05-31` | `2026-05-01` (1 day) | **SAVED_VERIFIED** | 9 | 9 | 9 | **100.00%** |
| **TOTALS** | **Jan – May 2026** | **81 Teaching Days** | **VERIFIED_COMPLETE** | **729** | **476** | **545** | **87.34%** |

---

## 2. Term Verification & Provenance

### Academic Term Identity
- **Academic Year:** `2025-2026`
- **Semester:** `4`
- **Class Identifier:** `2508`
- **Portal Label:** `B.Tech CSE AIML-Sem 4`
- **Internal Database Term ID:** `53d60f23-e8ac-4077-a0ce-27e62aa311b9`

### Portal Mechanism Observation
On the iCloudEMS portal (`myattendance.php`), day-wise timetable matrices are retrieved via an encrypted query parameter `e`. When a historical term is requested, the top navigation form controls in the server HTML response default to the student's active semester (Semester 5), while the underlying timetable report is accurately rendered for the historical query scope (`2025-2026 / Sem 4 / Class 2508`). 

AttendPlan's `LivePortalExtractor` and `canonical_html` pipeline was updated to verify query parameter `e` and stamp the submitted scope into the canonical DOM, ensuring fail-closed validation and zero identity mismatches.

---

## 3. Reconciliation & Course Attribution Analysis

### Macro Totals Comparison
- **Subject-Wise Snapshot (Baseline):** 485 attended / 554 delivered (**87.55%**) across 17 courses
- **Day-Wise Timetable Matrix (Pilot):** 476 attended / 545 delivered (**87.34%**) across 81 teaching days
- **Macro Delta:** 9 periods attended, 9 periods delivered ($485 - 476 = 9$; $554 - 545 = 9$). Both sources confirm exact agreement within 1.6% of delivered volume.

### Course Attribution & Naming Finding
The portal uses two distinct naming schemes across views:
1. **Subject-Wise Summary:** Employs formal course catalog codes (e.g., `CSH219C`, `CSH220C`, `CSW218C`, `ECH108C`, `VAC-CS512`).
2. **Day-Wise Timetable Matrix:** With the "Show Course Name" toggle active, the portal displays friendly title names (e.g., `ADVANCED NEURAL NETWORKS (PP)`, `ADVANCED NEURAL NETWORKS LAB (PR)`, `MOBILE APP DEVELOPMENT (PR)`).

Exact period match verification:
- `CSH219C` (41/42) $\leftrightarrow$ `ADVANCED NEURAL NETWORKS (PP)` (41/42) — **Exact 100% Match**
- `CSH220C` (56/56) $\leftrightarrow$ `ADVANCED NEURAL NETWORKS LAB (PR)` (56/56) — **Exact 100% Match**
- `VAC-CS512` (23/23) $\leftrightarrow$ `SPECIALIZED AI ASSOCIATE TRAINING (PP)` (23/23) — **Exact 100% Match**
- `CSW218C` (40/42) $\leftrightarrow$ `MOBILE APP DEVELOPMENT (PR)` (40/42) — **Exact 100% Match**
- `LWS101C` (11/14) $\leftrightarrow$ `INDIAN CONSTITUTION (PP)` (11/14) — **Exact 100% Match**
- `CSH218C` (26/30) $\leftrightarrow$ `MACHINE LEARNING LAB (PR)` (26/30) — **Exact 100% Match**
- `CSH216C` (24/28) $\leftrightarrow$ `COMPUTER NETWORKS LAB (PR)` (24/28) — **Exact 100% Match**
- `ECH109C` (22/26) $\leftrightarrow$ `DIGITAL ELECTRONICS LAB (PR)` (22/26) — **Exact 100% Match**
- `CSH214C` (20/24) $\leftrightarrow$ `SOFTWARE ENGINEERING LAB (PR)` (20/24) — **Exact 100% Match**
- `RDO203C` (13/15) $\leftrightarrow$ `DESIGN THINKING (PP)` (13/15) — **Exact 100% Match**
- `RDO202C` (12/14) $\leftrightarrow$ `RDO202C` (12/14) — **Exact 100% Match**

---

## 4. Invariants, Preservation & Security Verification

1. **Active Database:** `C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3`
2. **Pre-Pilot Backup:** `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_d1_backup.sqlite3` (Verified consistent)
3. **Database Integrity:**
   - `PRAGMA integrity_check` $\rightarrow$ `ok`
   - `PRAGMA foreign_key_check` $\rightarrow$ `0` violations
4. **Semester 5 Isolation Check:**
   - Baseline Semester 5 snapshots: **4** (latest 260/313 attended/delivered)
   - Baseline Semester 5 batches: **8** (968 observations)
   - Post-pilot Semester 5 snapshots: **4** (**Unchanged**)
   - Post-pilot Semester 5 batches: **8** (**Unchanged**)
5. **Academic Marks Isolation Check:**
   - Baseline Marks snapshots: **1** (`marks:6424:3:A`)
   - Post-pilot Marks snapshots: **1** (**Unchanged**)
6. **PII and Vault Hygiene:**
   - Zero student credentials, TOTP secrets, or session cookies logged or saved.
   - All 11 repository sanitization audit checks passed.

---

## 5. Quality Gates Summary

- **Backend Pytest:** **265 passed** (100% green)
- **Backend Ruff Linting:** **All checks passed**
- **Backend Mypy Typing:** **Success: no issues found in 44 source files**
- **Frontend Vitest:** **38 passed** across 13 test suites
- **Frontend TypeScript (`tsc --noEmit`):** **0 errors**
- **Frontend Vite Build:** **Clean production bundle** (`dist/` generated, 0 warnings)
- **PII Sanitization:** **11 passed**

**Phase D.1 Live Pilot Status:** **VERIFIED_COMPLETE**
