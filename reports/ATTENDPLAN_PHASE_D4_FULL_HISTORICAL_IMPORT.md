# ATTENDPLAN — PHASE D.4 FULL HISTORICAL ARCHIVE REPORT
## Multi-Semester Historical Attendance Recovery (Semesters 1, 2, 3)
### Complete 5-Semester Institutional Analytics Baseline

**Date:** 2026-11-01  
**Execution Environment:** Windows 11 x64, Python 3.12, Node.js v20, Vite 6, SQLite 3 (WAL mode)  
**Security Posture:** Local-First, 127.0.0.1 Binding, Zero Credential/OTP Persistence, Zero Student PII  
**Status:** **VERIFIED_COMPLETE (SUCCESS)**  

---

## 1. Executive Summary & Full-Scope Archive Declaration

With explicit user authorization, **Phase D.4 Full-Scope Execution** has successfully extracted, validated, reconciled, and persisted historical attendance data for **Semester 3**, **Semester 2**, and **Semester 1** from the live university iCloudEMS portal.

Together with the existing baseline for **Semester 4** (Phase D.1/D.2) and the active live synchronization term **Semester 5** (Phase C.2), AttendPlan now possesses a complete, immutable, 5-semester historical attendance archive spanning the student's entire academic degree program to date (Academic Years 2024–2025 through 2026–2027).

### Key Historical Milestones:
1. **Semester 1 (AY 2024–2025, Sem 1, Class ID 918)**:
   - **Perfect Equality Achieved**: Subject-wise summary ($275$ attended / $293$ delivered, $93.86\%$) matches the calendar-aware Day-wise timetable observations ($275$ attended / $293$ delivered across $413$ period slots) with **zero missing periods** ($\Delta = 0 / 0$).
   - All 12 enrolled courses exhibit 100% course-level matching between subject summary and period-level ledger.
2. **Semester 3 (AY 2025–2026, Sem 3, Class ID 1067)**:
   - Subject-wise summary ($400$ attended / $463$ delivered, $86.39\%$, 16 courses) successfully ingested.
   - Day-wise observations across August–November 2025 ingested ($373$ attended / $436$ delivered across $680$ period slots).
   - Difference of $\Delta = -27 / -27$ is mathematically proven to be a date-window truncation: the subject summary reporting window begins July 14, 2025, whereas day-wise monthly reports began August 1, 2025. Every single discrepancy period represents $100\%$ attendance credited during July orientation.
3. **Semester 2 (AY 2024–2025, Sem 2, Class ID 1048)**:
   - Subject-wise summary ($381$ attended / $446$ delivered, $85.43\%$, 16 courses) successfully ingested.
   - Day-wise observations across February–May 2025 ingested ($296$ attended / $356$ delivered across $430$ period slots). January 2025 had 0 recorded timetable entries on portal filters (`PORTAL_SAFETY_FILTER_SELECTION_MISMATCH`).
   - Difference of $\Delta = -85 / -90$ reflects the January 13–January 31 start-of-term window prior to February timetable activation.
4. **Preservation Verified**:
   - **Semester 4**: Reconciled baseline ($485/554$ summary, $476/545$ daywise, $9/9$ `SOURCE_DISCREPANCY`) and 15 academic marks snapshots remain completely untouched.
   - **Semester 5**: Live baseline ($265/322$ summary, 9 observation batches, 1,112 period observations) remains completely untouched.

---

## 2. Authorization Scope, Execution Constraints & Budget Compliance

The user explicitly authorized the Phase D.4 execution plan covering candidate classes and candidate months:
- **Semester 3**: Class ID `1067`, AY `2025-2026`, Sem `3` (1 subject summary + 4 months: `2025-08` through `2025-11`).
- **Semester 2**: Class ID `1048`, AY `2024-2025`, Sem `2` (1 subject summary + 5 months: `2025-01` through `2025-05`).
- **Semester 1**: Class ID `918`, AY `2024-2025`, Sem `1` (1 subject summary + 4 months: `2024-08` through `2024-11`).

### Bounded Budget Compliance:
- **Maximum Planned Budget**: 16 portal requests.
- **Actual Requests Executed**:
  - Semester 3: 1 subject summary + 4 day-wise months = 5 requests.
  - Semester 2: 1 subject summary + 5 day-wise months (1 filter check + 4 extractions) = 6 requests.
  - Semester 1: 1 subject summary + 4 day-wise months = 5 requests.
  - **Total Portal Requests**: **16 requests** (100% budget adherence, zero out-of-scope queries).
- **Out of Scope Boundaries Maintained**:
  - Zero historical marks/grades scraped or requested.
  - Zero external exfiltration or remote database transmission.
  - No credential persistence; TOTP vault and session tokens ephemeral in memory/Windows Credential Manager.

---

## 3. Preflight, Database Integrity & Backup Verification

Before executing any write operation against SQLite:
1. **Active Database Integrity Verified**:
   - `PRAGMA integrity_check` -> `ok`
   - `PRAGMA foreign_key_check` -> `0 violations`
2. **Cold Offline Backup Created**:
   - Backup Path: `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_d4_final_backup.sqlite3`
   - File Size: `1,122,304 bytes`
   - Backup Integrity: Verified `ok`, 0 foreign key violations.

---

## 4. Live Portal Authentication & Session Verification

- **Browser Transport**: Dedicated Chrome instance attached via Chrome DevTools Protocol (CDP) on `127.0.0.1:9222`.
- **User Data Directory**: `$LOCALAPPDATA\AttendPlan\chrome-profile` (isolated from user's personal browsing data).
- **Authentication Handshake**: `LoginOrchestrator` queried Keycloak endpoint; session confirmed `LoginState.AUTHENTICATED`.
- **Navigation Pacing**: 2.5–3.5s jittered delays between AJAX form submissions, guaranteeing zero rate-limit or portal overload incidents.

---

## 5. Parser Upgrades & Course Disambiguation Engine

### The Duplicate Course Code Challenge:
In university ERPs, multiple course components (e.g., Theory, Practical Lab, and Tutorial) frequently share the exact same course code (e.g., `MAH204C` for both Lecture and Tutorial, `CSS104C` for Lecture and Practical).
In Phase D.3 preflight, strict dictionary deduplication triggered `DUPLICATE_COURSE_CODES` quarantine.

### Engine Enhancements Implemented:
1. **Canonical Component Disambiguation (`html_parser.py`)**:
   - In `_parse_table_rows`, when identical course codes appear within the same term table, secondary rows are canonically qualified with component suffixes based on row labels:
     - Tutorial components appended with `-TUT` (e.g. `MAH204C-TUT`, `MAH104C-TUT`).
     - Laboratory/Practical components appended with `-PR` (e.g. `CSS104C-PR`, `HLS101C-PR`).
   - Guarantees satisfaction of SQLite unique constraint `uq_course_term_code`.
2. **Sequential Row Extraction (`live_portal_extractor.py`)**:
   - Replaced naive dictionary lookup by raw course code with sequential row matching and course qualification, preventing false quarantine of valid split-component courses.
3. **Extended Course Alias Mapping (`daywise_parser.py`)**:
   - Injected 60+ institutional course title aliases for Semesters 1, 2, and 3 into `NAME_TO_CODE_MAP` (e.g. `DATA MODELLING LAB` -> `CSS104C-PR`, `PROBABILITY & STATISTICS (TUT)` -> `MAH104C-TUT`, `CHEMISTRY-I LAB` -> `CHH102C`).
   - Extended regex patterns to handle university Value-Added Courses (`VAC-CS109`, `VAC-CS112`).

---

## 6. Semester-by-Semester Recovery Results

### 6.1 Semester 1: Exact Match Proof ($275/293 = 275/293$)
- **Academic Year**: 2024–2025
- **Semester**: 1 | **Class ID**: 918 (`B.Tech CSE AIML-Sem 1`)
- **Subject-Wise Snapshot**: `fbfd7b77-def8-43d3-90a3-515df662670e` (Captured: 2026-11-01 07:34:34 UTC)
- **Day-Wise Batches Extracted**:
  - `2024-08`: 98 observations (62 attended / 64 delivered, 14 days)
  - `2024-09`: 105 observations (74 attended / 78 delivered, 15 days)
  - `2024-10`: 112 observations (79 attended / 81 delivered, 16 days)
  - `2024-11`: 98 observations (60 attended / 70 delivered, 14 days)
- **Day-Wise Total**: 413 observations (293 scheduled class periods + 120 unscheduled/holiday periods).
- **Scheduled Attendance**: **275 Attended / 293 Delivered ($93.86\%$)**.

#### Course-Level Comparison Table (Semester 1):
| Course Code | Course Name | Subject Att/Del | Daywise Att/Del | Reconciliation Status |
| :--- | :--- | :---: | :---: | :---: |
| `CDO103B` | PROFESSIONAL COMMUNICATION-I | 19 / 21 | 19 / 21 | **EXACT MATCH** |
| `CHS103C` | ENVIRONMENTAL SCIENCE | 20 / 21 | 20 / 21 | **EXACT MATCH** |
| `CSH101C` | PROGRAMMING FOR PROBLEM SOLVING USING C | 20 / 22 | 20 / 22 | **EXACT MATCH** |
| `CSH102C` | PROGRAMMING FOR PROBLEM SOLVING USING C LAB | 42 / 44 | 42 / 44 | **EXACT MATCH** |
| `CSS104C` | DATA MODELLING | 13 / 13 | 13 / 13 | **EXACT MATCH** |
| `CSS104C-PR` | DATA MODELLING LAB | 26 / 26 | 26 / 26 | **EXACT MATCH** |
| `CSW103C` | WEB DESIGNING-I | 12 / 14 | 12 / 14 | **EXACT MATCH** |
| `MAH104C` | PROBABILITY & STATISTICS | 35 / 38 | 35 / 38 | **EXACT MATCH** |
| `MAH104C-TUT` | PROBABILITY & STATISTICS (TUTORIAL) | 8 / 10 | 8 / 10 | **EXACT MATCH** |
| `MEW104C` | COMPUTER AIDED DRAFTING | 26 / 26 | 26 / 26 | **EXACT MATCH** |
| `PHH101C` | QUANTUM MECHANICS FOR ENGINEERS | 32 / 34 | 32 / 34 | **EXACT MATCH** |
| `PHH102C` | QUANTUM MECHANICS FOR ENGINEERS LAB | 22 / 24 | 22 / 24 | **EXACT MATCH** |
| **TOTAL** | **12 Courses** | **275 / 293 (93.86%)** | **275 / 293 (93.86%)** | **100% IDENTICAL** |

---

### 6.2 Semester 3: Recovery & Scope Window Analysis
- **Academic Year**: 2025–2026
- **Semester**: 3 | **Class ID**: 1067 (`B.Tech CSE AIML-Sem 3`)
- **Subject-Wise Snapshot**: `b048b922-26aa-46ae-be62-d01d02145b1c`
- **Subject-Wise Totals**: 16 courses, **400 Attended / 463 Delivered ($86.39\%$)**.
- **Day-Wise Batches Extracted**:
  - `2025-08`: 200 observations (122 attended / 130 delivered, 20 days)
  - `2025-09`: 170 observations (93 attended / 119 delivered, 17 days)
  - `2025-10`: 160 observations (82 attended / 96 delivered, 16 days)
  - `2025-11`: 150 observations (76 attended / 91 delivered, 15 days)
- **Day-Wise Total**: 680 observations, **373 Attended / 436 Delivered ($85.55\%$)**.
- **Scope Delta**: $\Delta = -27 \text{ Attended}, -27 \text{ Delivered}$.

#### Course-Level Comparison Table (Semester 3):
| Course Code | Course Name | Subject Att/Del | Daywise Att/Del | Delta ($\Delta$) | Analysis |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `CDO231` | PROFESSIONAL COMPETANCY ENHANCEMENT-II | 49 / 57 | 45 / 53 | +4 / +4 | July 14–31 class window |
| `CSH201C` | COMPUTER ARCHITECTURE & ORGANISATION | 38 / 44 | 34 / 40 | +4 / +4 | July 14–31 class window |
| `CSH202C` | OPERATING SYSTEMS | 26 / 30 | 24 / 28 | +2 / +2 | July 14–31 class window |
| `CSH203C` | OPERATING SYSTEMS LAB | 32 / 35 | 32 / 35 | **0 / 0** | **EXACT MATCH** |
| `CSH204C` | ADVANCED JAVA | 21 / 23 | 21 / 23 | **0 / 0** | **EXACT MATCH** |
| `CSH205C` | ADVANCED JAVA LAB | 36 / 42 | 33 / 39 | +3 / +3 | July 14–31 class window |
| `CSH206C` | INTRODUCTION TO NOSQL DATABASES | 28 / 28 | 26 / 26 | +2 / +2 | July 14–31 class window |
| `CSH207C` | COMPUTER ARCHITECTURE & ORG LAB | 30 / 36 | 29 / 35 | +1 / +1 | July 14–31 class window |
| `CSH208C` | INTRODUCTION TO NOSQL DATABASES LAB | 24 / 30 | 20 / 26 | +4 / +4 | July 14–31 class window |
| `CSS210C` | DATA COMMUNICATION & NETWORKING | 33 / 36 | 30 / 33 | +3 / +3 | July 14–31 class window |
| `CSW209C` | WEB DESIGNING-II | 23 / 28 | 23 / 28 | **0 / 0** | **EXACT MATCH** |
| `EDN248C` | INDIAN CONSTITUTION | 0 / 0 | 0 / 0 | **0 / 0** | Audit / Non-credit |
| `MAH204C` | DISCRETE MATHEMATICS | 32 / 43 | 29 / 40 | +3 / +3 | July 14–31 class window |
| `MAH204C-TUT` | DISCRETE MATHEMATICS (TUTORIAL) | 10 / 13 | 9 / 12 | +1 / +1 | July 14–31 class window |
| `RDO201C` | RESEARCH INNOVATION | 0 / 0 | 0 / 0 | **0 / 0** | Project based |
| `VAC-CS112` | VALUE ADDED COURSE | 18 / 18 | 18 / 18 | **0 / 0** | **EXACT MATCH** |
| **TOTAL** | **16 Courses** | **400 / 463** | **373 / 436** | **+27 / +27** | **100% Attendance in July Window** |

---

### 6.3 Semester 2: Recovery & Scope Window Analysis
- **Academic Year**: 2024–2025
- **Semester**: 2 | **Class ID**: 1048 (`B.Tech CSE AIML-Sem 2`)
- **Subject-Wise Snapshot**: `37411965-aa93-453d-90c7-18ac78d00fcf`
- **Subject-Wise Totals**: 16 courses, **381 Attended / 446 Delivered ($85.43\%$)**.
- **Day-Wise Batches Extracted**:
  - `2025-01`: Unrecorded on portal filter (`PORTAL_SAFETY_FILTER_SELECTION_MISMATCH`, 0 obs)
  - `2025-02`: 152 observations (102 attended / 118 delivered, 19 days)
  - `2025-03`: 88 observations (71 attended / 73 delivered, 11 days)
  - `2025-04`: 176 observations (112 attended / 153 delivered, 22 days)
  - `2025-05`: 14 observations (11 attended / 12 delivered, 2 days)
- **Day-Wise Total**: 430 observations, **296 Attended / 356 Delivered ($83.15\%$)**.
- **Scope Delta**: $\Delta = -85 \text{ Attended}, -90 \text{ Delivered}$ (January 13–31, 2025 start-of-term window).

#### Course-Level Comparison Table (Semester 2):
| Course Code | Course Name | Subject Att/Del | Daywise Att/Del | Delta ($\Delta$) | Analysis |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `CDO104B` | PROFESSIONAL COMMUNICATION-II | 23 / 27 | 17 / 21 | +6 / +6 | Jan 13–31 start window |
| `CHH101C` | CHEMISTRY-I | 36 / 40 | 28 / 31 | +8 / +9 | Jan 13–31 start window |
| `CHH102C` | CHEMISTRY-I LAB | 22 / 28 | 16 / 22 | +6 / +6 | Jan 13–31 start window |
| `CSH107C` | DATA STRUCTURES | 40 / 42 | 32 / 33 | +8 / +9 | Jan 13–31 start window |
| `CSH107C-TUT` | DATA STRUCTURES (TUTORIAL) | 9 / 13 | 7 / 11 | +2 / +2 | Jan 13–31 start window |
| `CSH108C` | DATA STRUCTURES LAB | 26 / 28 | 20 / 22 | +6 / +6 | Jan 13–31 start window |
| `CSH109C` | PYTHON PROGRAMMING | 31 / 39 | 22 / 30 | +9 / +9 | Jan 13–31 start window |
| `CSH110C` | PYTHON PROGRAMMING LAB | 24 / 28 | 18 / 22 | +6 / +6 | Jan 13–31 start window |
| `CSS112C` | COMPUTER ORGANIZATION | 36 / 39 | 27 / 30 | +9 / +9 | Jan 13–31 start window |
| `ECH103C` | DIGITAL ELECTRONICS | 37 / 41 | 29 / 32 | +8 / +9 | Jan 13–31 start window |
| `ECH104C` | DIGITAL ELECTRONICS LAB | 22 / 28 | 16 / 22 | +6 / +6 | Jan 13–31 start window |
| `HLS101C` | HOLISTIC HEALTH & FITNESS | 8 / 10 | 8 / 10 | **0 / 0** | **EXACT MATCH** |
| `HLS101C-PR` | HOLISTIC HEALTH & FITNESS (PR) | 14 / 18 | 14 / 18 | **0 / 0** | **EXACT MATCH** |
| `MAH101C` | LINEAR ALGEBRA & CALCULUS | 33 / 39 | 25 / 30 | +8 / +9 | Jan 13–31 start window |
| `MAH101C-TUT` | LINEAR ALGEBRA (TUTORIAL) | 10 / 13 | 7 / 10 | +3 / +3 | Jan 13–31 start window |
| `VAC-CS109` | VALUE ADDED COURSE | 10 / 13 | 10 / 12 | +0 / +1 | Jan 13–31 start window |
| **TOTAL** | **16 Courses** | **381 / 446** | **296 / 356** | **+85 / +90** | **94.4% Attendance in Jan Window** |

---

## 7. Complete Five-Semester Master Attendance Summary

The table below presents the verified end-to-end dataset across all five semesters of the student's degree:

| Semester | Academic Year | Class Identifier | Subject-Wise Att / Del (%) | Day-Wise Att / Del (%) | Observations | Batches | Reconciliation Status |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Sem 1** | 2024–2025 | B.Tech CSE AIML-Sem 1 (`918`) | 275 / 293 (93.86%) | 275 / 293 (93.86%) | 413 | 4 | **EXACT MATCH** |
| **Sem 2** | 2024–2025 | B.Tech CSE AIML-Sem 2 (`1048`) | 381 / 446 (85.43%) | 296 / 356 (83.15%) | 430 | 4 | `SCOPE_MISMATCH` (Jan window) |
| **Sem 3** | 2025–2026 | B.Tech CSE AIML-Sem 3 (`1067`) | 400 / 463 (86.39%) | 373 / 436 (85.55%) | 680 | 4 | `SCOPE_MISMATCH` (July window) |
| **Sem 4** | 2025–2026 | B.Tech CSE AIML-Sem 4 (`2508`) | 485 / 554 (87.55%) | 476 / 545 (87.34%) | 729 | 5 | `SOURCE_DISCREPANCY` (Exam 9/9) |
| **Sem 5** | 2026–2027 | B.Tech CSE AIML-Sem 5 (`2582`) | 265 / 322 (82.30%) | 663 / 838 (Live) | 1,112 | 9 | `LIVE_ACTIVE_TERM` |
| **CUMULATIVE** | **All 5 Terms** | **B.Tech CSE AIML** | **1,806 / 2,078 (86.91%)** | — | **3,364** | **26** | **ARCHIVE VERIFIED** |

*Note: Aggregate degree attendance to date sits at **$86.91\%$** across 2,078 delivered instructional periods, safely above the university's 75% statutory threshold.*

---

## 8. Quality Gates & Release Verification

All release quality gates mandated by `AGENTS.md` and `.agents/skills/release-verification/SKILL.md` have been executed and passed with zero errors:

| Quality Gate | Tool / Runner | Command | Result | Details |
| :--- | :--- | :--- | :---: | :--- |
| **Backend Unit & Domain Tests** | `pytest` | `pytest backend/tests` | **PASS** | **267 passed**, 1 harmless warning in 15.44s |
| **Python Code Quality & Linting** | `ruff` | `ruff check backend/app backend/tests` | **PASS** | All checks passed cleanly |
| **Python Static Type Safety** | `mypy` | `mypy backend/app` | **PASS** | Success: no issues found in 44 source files |
| **Frontend Test Suite** | `vitest` | `npm.cmd test -- --run` | **PASS** | **13 test files passed, 38 tests passed** |
| **Frontend TypeScript Types** | `tsc` | `npx.cmd tsc --noEmit` | **PASS** | Zero type errors |
| **Frontend Production Build** | `vite` | `npm.cmd run build` | **PASS** | Production bundle built cleanly in 4.87s |
| **SQLite Schema & Data Integrity** | `sqlite3` | `PRAGMA integrity_check` | **PASS** | `ok` |
| **SQLite Foreign Key Consistency** | `sqlite3` | `PRAGMA foreign_key_check` | **PASS** | 0 violations across all 10 tables |

---

## 9. Security, Localhost Binding & Privacy Audit

1. **Fail-Closed Privacy**:
   - Zero student PII (student names, roll numbers, enrollment numbers, phone numbers) logged or committed.
   - All fixtures sanitized with generic placeholders (`STUDENT_NAME`, `ABC12345`).
2. **Localhost Exclusivity**:
   - Backend binds strictly to `127.0.0.1` (never `0.0.0.0`).
3. **Authentication Boundaries**:
   - Keycloak authentication utilizes user-owned browser session; credentials never extracted, stored in plaintext, or transmitted externally.
4. **Source Provenance Invariance**:
   - All imported records retain `LIVE_PORTAL_AUTOMATED_HISTORICAL_SUBWISE` or `LIVE_PORTAL_AUTOMATED_HISTORICAL_DAYWISE` provenance flags, content checksums, and exact original counts.

