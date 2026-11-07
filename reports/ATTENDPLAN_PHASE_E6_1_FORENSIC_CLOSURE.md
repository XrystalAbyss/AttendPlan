# ATTENDPLAN — PHASE E.6.1 FORENSIC CLOSURE REPORT
**Performance Matrix Forensic Reconciliation & Official Results Readiness Closure**  
**Execution Date:** November 2, 2026  
**Auditor:** Principal Data Integrity Auditor & Google Antigravity Flash 3.8  
**Operating Mode:** Strictly Offline Investigation & Regression Hardening  
**Status:** FULLY RECONCILED & CLOSED (0 BLOCKERS)

---

## 1. Final Authoritative Database Identity

The single active source-of-truth database for AttendPlan is:
- **Canonical Path:** `C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3`
- **File Size:** 1,961,984 bytes
- **SQLite Engine:** SQLite 3.x with Write-Ahead Logging (WAL) enabled
- **PRAGMA integrity_check:** `ok`
- **PRAGMA foreign_key_check:** `[]` (zero violations)
- **Pre-E.6.1 Consistent Backup:** `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_e6_1_backup_20261102_013252.sqlite3` (1,961,984 bytes, verified integrity `ok`, foreign keys `[]`).

---

## 2. Exact Five Snapshot Identifiers

The active database hosts exactly five immutable `performance_snapshots` records corresponding to the five academic terms:

| Semester | Academic Term Key | Snapshot UUID | View Tag | Exam Session | Division |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **Sem 1** | `2024-2025_s1_918` | `77d4702c-1e28-4ca7-95d5-329c7bba8d1d` | `marks:5764:3:A` | 5764 | A |
| **Sem 2** | `2024-2025_s2_1048` | `b15162ae-4a03-4e99-8155-c844fb328ea7` | `marks:5943:3:A` | 5943 | A |
| **Sem 3** | `2025-2026_s3_1067` | `a9410bae-8496-4a0e-a64c-0880aa5cfbdb` | `marks:6161:3:A` | 6161 | A |
| **Sem 4** | `2025-2026_s4_2508` | `03d1482b-c997-431f-bc88-071c3bb4c764` | `marks:6424:3:A` | 6424 | A |
| **Sem 5** | `2026-2027_s5_2582` | `e8a91033-b87c-42e0-9d42-6ff0d02c8bcf` | `marks:6732:3:A` | 6732 | A |

All five snapshots have `provenance = "LIVE_PORTAL"`.

---

## 3. Raw Source-Backed Per-Term Counts

Each snapshot payload was forensically inspected by directly querying SQLite JSON contents:

| Semester | Term Key | Source Courses | Assessment Columns | Total Cells | Courses List |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **Sem 1** | `2024-2025_s1_918` | 11 | 6 | 66 | `CDO103B`, `CHS103C`, `CSH101C`, `CSH102C`, `CSS104C`, `CSS104C-PR`, `CSW103C`, `MAH104C`, `MEW104C`, `PHH101C`, `PHH102C` |
| **Sem 2** | `2024-2025_s2_1048` | 12 | 9 | 108 | `CDO104B`, `CHH101C`, `CHH102C`, `CSH107C`, `CSH108C`, `CSH109C`, `CSH110C`, `CSS112C`, `ECH103C`, `ECH104C`, `HLS101C`, `MAH101C` |
| **Sem 3** | `2025-2026_s3_1067` | 13 | 9 | 117 | `CDO231`, `CSH201C`, `CSH202C`, `CSH203C`, `CSH204C`, `CSH205C`, `CSH206C`, `CSH207C`, `CSH208C`, `CSS210C`, `CSW209C`, `MAH204C`, `RDO201C` |
| **Sem 4** | `2025-2026_s4_2508` | 15 | 11 | 165 | `CDO232`, `CSH213C`, `CSH214C`, `CSH215C`, `CSH216C`, `CSH217C`, `CSH218C`, `CSH219C`, `CSW218C`, `ECH108C`, `ECH109C`, `LWS101C`, `MCS368C`, `RDO202C`, `RDO203C` |
| **Sem 5** | `2026-2027_s5_2582` | 4 | 3 | 12 | `CSH301C`, `CSH302C`, `CSH304C`, `CSH310C` |
| **Total** | **5 Snapshots** | **55** | | **468** | **Authoritative Archive** |

---

## 4. Assessment Status Distribution

Across the 468 cells in the five snapshots:

| Term Key | REPORTED | UNREPORTED | MASKED_BY_PORTAL | ABSENT | WITHHELD | Total Persisted Cells |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `2024-2025_s1_918` | 48 | 18 | 0 | 0 | 0 | 66 |
| `2024-2025_s2_1048` | 57 | 51 | 0 | 0 | 0 | 108 |
| `2025-2026_s3_1067` | 64 | 53 | 0 | 0 | 0 | 117 |
| `2025-2026_s4_2508` | 59 | 91 | 15 | 0 | 0 | 165 |
| `2026-2027_s5_2582` | 10 | 2 | 0 | 0 | 0 | 12 |
| **Grand Total** | **238** | **215** | **15** | **0** | **0** | **468** |

**Accounting Equality Verified:**
$$\text{Total Classified Cells} = 238 + 215 + 15 = 468 = \text{Total Persisted Assessment Cells}$$

---

## 5. E.5 versus E.6 Discrepancy Root Cause

The forensic investigation traced the exact origin of the discrepancy:

1. **The Phase E.5 numbers:**
   - Semester 1: 11 courses, 66 cells
   - Semester 2: 12 courses, 108 cells
   - Semester 3: 13 courses, 117 cells
   - Semester 4: 15 courses, 165 cells
   - Semester 5: 4 courses, 12 cells
   - **Verdict:** These numbers are **100% accurate, bit-for-bit true**, directly reflecting the raw database snapshots in `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`.

2. **The Phase E.6 numbers:**
   - Semester 1: 12 courses, 108 cells
   - Semester 2: 12 courses, 96 cells
   - Semester 3: 11 courses, 110 cells
   - Semester 4: 11 courses, 88 cells
   - Semester 5: 9 courses, 66 cells
   - **Root Cause:** A **pure documentation fabrication / transcription error** committed during the writing of Phase E.6 markdown reports (`reports/ATTENDPLAN_OFFICIAL_RESULTS_SOURCE_MATRIX.md` and `reports/ATTENDPLAN_PHASE_E6_RESULTS_READINESS.md`).
   - The author of those markdown files did not execute database extraction queries. Instead, the author confused the 55 marks courses with catalog breakdowns, manually fabricated per-term partitions $(12, 12, 11, 11, 9)$, multiplied them by arbitrary column numbers to force the total to 468 $(108 + 96 + 110 + 88 + 66 = 468)$, and hallucinated fictitious SHA-256 prefixes (`9550e687...`, `a93b4976...`, `2a9db5c4...`, `00795493...`, `41b777a8...`).
   - **Database Status:** The active database was **never mutated**. The database at all times held the true Phase E.5 data.

---

## 6. Corrected Five-Semester Performance Matrix

The corrected, authoritative matrix reflecting actual SQLite data is now documented across all repository records:

| Semester | Academic Term Key | Catalog Courses | Marks Source Courses | Columns | Total Cells | REPORTED | UNREPORTED | MASKED |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | `2024-2025_s1_918` | 12 | 11 | 6 | 66 | 48 | 18 | 0 |
| **2** | `2024-2025_s2_1048` | 16 | 12 | 9 | 108 | 57 | 51 | 0 |
| **3** | `2025-2026_s3_1067` | 16 | 13 | 9 | 117 | 64 | 53 | 0 |
| **4** | `2025-2026_s4_2508` | 17 | 15 | 11 | 165 | 59 | 91 | 15 |
| **5** | `2026-2027_s5_2582` | 15 | 4 | 3 | 12 | 10 | 2 | 0 |
| **Total** | **5 Terms** | **76** | **55** | | **468** | **238** | **215** | **15** |

---

## 7. Reporting Code and Documentation Changes

1. **Updated Documentation Files:**
   - [`reports/ATTENDPLAN_OFFICIAL_RESULTS_SOURCE_MATRIX.md`](file:///C:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_OFFICIAL_RESULTS_SOURCE_MATRIX.md): Corrected table values to true snapshot counts and SHA-256 hashes; updated status labels.
   - [`reports/ATTENDPLAN_PHASE_E6_RESULTS_READINESS.md`](file:///C:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_PHASE_E6_RESULTS_READINESS.md): Corrected Section 3 database table to reflect 76 catalog courses, 55 marks courses, 468 cells.
   - [`reports/ATTENDPLAN_E6_RESULTS_REQUEST_MANIFEST.md`](file:///C:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_E6_RESULTS_REQUEST_MANIFEST.md): Removed any assumed grade card URLs; labeled endpoints as candidate inspection paths.
   - Brain Artifact [`ATTENDPLAN_PHASE_E6_RESULTS_READINESS.md`](file:///C:/Users/astra/.gemini/antigravity/brain/c2b6efa0-7957-4019-8648-37074d0adfb4/ATTENDPLAN_PHASE_E6_RESULTS_READINESS.md): Synchronized with authoritative figures.
2. **Updated Verification Scripts:**
   - [`backend/scripts/verify_windows_human_acceptance.py`](file:///C:/Users/astra/Desktop/Project/AttendPlan/backend/scripts/verify_windows_human_acceptance.py): Added explicit request accounting (total intercepted, localhost count, external count, blocked count) and verified Semester 5's 4 source courses in DOM.
3. **New Regression Test Suite:**
   - [`backend/tests/test_performance_matrix_forensic_reconciliation_e6_1.py`](file:///C:/Users/astra/Desktop/Project/AttendPlan/backend/tests/test_performance_matrix_forensic_reconciliation_e6_1.py): 6 automated tests validating checksums, cell accounting, catalog vs source courses, no cross-term JOIN contamination, Semester 5 partial publication, and attendance preservation.

---

## 8. Snapshot Fingerprint Preservation

All five canonical SHA-256 fingerprints in `performance_snapshots` remain identical to their post-Phase E.4 acceptance baseline:

- **Sem 1:** `d0bafbaefa6aa526dc05f4e1fa73c78c6bcc11ef624a8c77701232a34f23ea6c`
- **Sem 2:** `c8110fdf0233baf2208c42c03c3e3c33e482daea97500694d453f1bd9cf64304`
- **Sem 3:** `bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee`
- **Sem 4:** `c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d`
- **Sem 5:** `4e040f42019bea38cb883ec9161eb6658ec6e0183ff5f98ed41fe2d4606dec22`

Bit-for-bit checksum verification: **100% UNCHANGED**.

---

## 9. Attendance Integrity Evidence

The attendance database assets are completely intact:
- **Academic Terms:** 5 terms (`academic_terms`)
- **Attendance Catalog Courses:** 76 courses (`courses`)
- **Attendance Snapshots:** 9 snapshots (`attendance_snapshots`)
- **Observation Batches:** 28 batches (`attendance_observation_batches`)
- **Period Observations:** 3,520 observations (`attendance_period_observations`)
  - Sem 1: 413 observations
  - Sem 2: 550 observations
  - Sem 3: 716 observations
  - Sem 4: 729 observations
  - Sem 5: 1,112 observations
- **Latest Snapshot Period Ratio:** 1,806 attended / 2,078 delivered (86.91%)
- **Attendance Mutation Check:** Zero rows modified, zero deletions, zero insertions.

---

## 10. Windows Launcher Verification Status

- **Tested Configuration:** Validated against active local development server processes (`uvicorn` FastAPI on port 8000, Vite dev server on port 5173).
- **Installer Status:** A packaged standalone Windows desktop launcher installer binary (`.exe` / `.msi`) was **not** tested or claimed. The application was verified in live Windows Chromium against local developer server runtimes.

---

## 11. Browser Acceptance Evidence Classification

The Playwright browser acceptance test (`verify_windows_human_acceptance.py`) executed under the following strict classification:
- **Backend/Frontend:** Started locally on `127.0.0.1:8000` and `127.0.0.1:5173`.
- **Browser Interaction:** Real Chromium browser launched via Playwright; interactive clicks, tab navigation, and select dropdown changes.
- **Data Source:** Real local saved SQLite database (`%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`).
- **Mocking:** **Zero mocks**. Real HTTP REST queries between React frontend and FastAPI backend.

---

## 12. Zero-ERP-Request Evidence

Audited network metrics from the Playwright acceptance harness:
- **Total Requests Intercepted:** 61 requests
- **Localhost Requests Allowed:** 61 requests (Vite assets, React components, FastAPI API endpoints)
- **External Requests Attempted:** 0
- **External Requests Blocked:** 0
- **Actual ERP Calls (`mrei.icloudems.com`):** Exactly 0
- **Console Errors:** Exactly 0

---

## 13. Domain-Model Readiness Status

The domain models in [`backend/app/domain/results_models.py`](file:///C:/Users/astra/Desktop/Project/AttendPlan/backend/app/domain/results_models.py) are:
- **`OfficialCourseResult`**: Validated with non-negative credits and grade points in $[0.0, 10.0]$.
- **`OfficialSemesterResult`**: Validated with SGPA/CGPA in $[0.0, 10.0]$ and semester in $[1, 12]$.
- **`OfficialResultSnapshot`**: Pure canonical SHA-256 checksumming over lexicographically sorted courses.
- **`ResultPublicationStatus`**: `PUBLISHED`, `NOT_PUBLISHED`, `WITHHELD`, `REVALUATION_PENDING`, `REVISED`.
- **Unit Test Coverage:** 100% passing across 4 unit tests in [`test_results_models.py`](file:///C:/Users/astra/Desktop/Project/AttendPlan/backend/tests/test_results_models.py).

---

## 14. Persistence, API, and Adapter Readiness Status

To avoid conflating domain schema creation with full system readiness, the operational status of Official Results layers is explicitly separated:
- **Domain Schema:** IMPLEMENTED & TESTED (Domain layer pure dataclasses).
- **Database Schema & Migrations:** NOT IMPLEMENTED (No dedicated Alembic migration for `official_results` tables; only `performance_snapshots` generic JSON table exists).
- **Backend API Endpoints:** NOT IMPLEMENTED (Only read-only preview/overview routes for internal marks are live).
- **Portal Source Adapter:** NOT IMPLEMENTED (No grade card or result card HTML parser implemented).
- **Local Source Fixtures:** NOT FETCHED (Zero official grade card documents exist offline).
- **Live Portal Access:** NOT FETCHED (Zero ERP requests executed).

---

## 15. Verified versus Assumed Publication States

All speculative labels (`Expected PUBLISHED`, `Expected NOT_PUBLISHED`) have been purged from documentation:
- **Semesters 1 through 4:** Labeled as `DISCOVERY_REQUIRED / NOT_FETCHED`. While these are completed historical terms, the actual presence, format, and availability of student grade sheets on iCloudEMS have **not** been discovered in a live portal session.
- **Semester 5:** Labeled as `NOT_DECLARED_BY_UNIVERSITY / NOT_FETCHED`. This is an active ongoing term where end-semester examinations have not concluded.

---

## 16. Full Regression Test Results

All quality gates passed cleanly:
1. **Pytest Backend Suite:**
   `pytest backend/tests`
   **Result:** 318 passed, 1 warning (deprecation in Starlette test client), 0 failures (47.38s).
2. **Ruff Linting:**
   `ruff check backend/app backend/tests`
   **Result:** All checks passed cleanly.
3. **Mypy Static Type Checking:**
   `mypy backend/app`
   **Result:** Success: no issues found in 45 source files.
4. **Vitest Frontend Suite:**
   `npm.cmd --prefix frontend test -- --run`
   **Result:** 13 test files passed, 38 tests passed, 0 failures (37.05s).
5. **Frontend Production Build:**
   `npm.cmd --prefix frontend run build`
   **Result:** Built cleanly in 18.73s (`dist/index.html`, `dist/assets/index-*.js`).
6. **SQLite Integrity & Foreign Keys:**
   `PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check = []`.

---

## 17. Remaining Blockers

**Zero Blockers.** The discrepancy is fully understood, root cause identified, documentation corrected, and regression tests added. No database mutation was required because the database at all times maintained the authoritative truth.

---

## 18. Next Exact Authorization Proposal

When the user chooses to proceed with official academic results:
- **Scope:** Authorize an interactive, read-only discovery of candidate results navigation paths on iCloudEMS.
- **Pilot Term:** Semester 3 (`2025-2026_s3_1067`) or Semester 1 (`2024-2025_s1_918`).
- **Condition:** No automatic data commitment. Display a staged dry-run preview card in the frontend for user inspection before any persistence occurs.

