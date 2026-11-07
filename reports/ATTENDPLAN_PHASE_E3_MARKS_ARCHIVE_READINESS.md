# AttendPlan — Phase E.3 Multi-Semester Academic Marks Archive Readiness

**Execution Mode**: STRICTLY OFFLINE PREPARATION — ZERO NEW UNIVERSITY PORTAL REQUESTS  
**Auditor**: Principal Software Architect & Academic Records Data Engineer  
**Date**: November 1, 2026  
**Status**: READINESS COMPLETE · AWAITING USER APPROVAL  

---

## 1. Executive Summary

Phase E.3 establishes complete offline architectural readiness for expanding AttendPlan's academic performance archive across all five undergraduate semesters (Semesters 1, 2, 3, 4, and 5).

Following the successful pilot and acceptance of Semester 3 internal marks in Phase E.2 / E.2.1, this phase defines the multi-semester source discovery rules, auditable request budgets, schema compatibility fixtures, revision policies, active-term handling, and security invariants required before any future live marks imports can be authorized.

### Core Achievements in Phase E.3:
1. **Zero University Portal Requests**: All research, inventory verification, test suite extension, and manifest drafting were executed strictly offline using retained local database records and synthetic fixtures.
2. **Database Integrity & WAL-Safe Backup**:
   - Checkpointed SQLite WAL: `[(0, 25, 25)]`.
   - Backup created outside Git: `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_e3_backup_20261101_231428.sqlite3` (1,888,256 bytes).
   - Database integrity confirmed: `PRAGMA integrity_check` $\to$ `ok`; `PRAGMA foreign_key_check` $\to$ 0 errors.
   - 100% preservation of all 5 academic terms, 76 courses, 9 attendance snapshots, 136 rows, 3,520 period observations, 28 batches, and both existing marks snapshots.
3. **Audit of Existing Performance Snapshots**:
   - **Semester 3** (`a9410bae-8496-4a0e-a64c-0880aa5cfbdb`): Verified existing source (`marks:6161:3:A`, checksum `bdae037d...`, 13 courses, 117 cells). Status: `VERIFIED_EXISTING_SNAPSHOT`. Do not refetch.
   - **Semester 4** (`03d1482b-c997-431f-bc88-071c3bb4c764`): Verified existing source (`marks:6424:3:A`, checksum `c237d695...`, 15 courses, 165 cells: 60 reported, 90 unreported, 15 masked). Status: `REUSE_EXISTING_SOURCE`.
4. **Pipeline Reuse Without Duplication**:
   - Confirmed the Semester 3 discovery $\to$ preview $\to$ single-use approval $\to$ zero-refetch import pipeline in `backend/app/adapters/performance_portal.py` and `backend/app/api/performance_routes.py` generalizes seamlessly across all 5 terms.
   - No second parser or duplicate ingestion pathway is required.
5. **Quality Gates Passed**:
   - Backend test suite: **297 passed** (0 failed).
   - Python linter (`ruff check`): Clean (0 issues).
   - Python typechecker (`mypy`): Clean (0 issues across 44 files).
   - Frontend test suite (`vitest`): **38 passed** (13 test files).
   - Frontend typecheck (`tsc --noEmit`): Clean (0 errors).
   - Frontend production build (`vite build`): Clean (15.01s).

---

## 2. Multi-Semester Archive Target Status

| Semester | Academic Year | Candidate Class ID | Target View | Status Label | Policy & Action |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Sem 1** | 2024–2025 | 918 | `marks:[session]:3:A` | `NOT_YET_IMPORTED` | Proposed historical internal marks import. Requires scoped session discovery. |
| **Sem 2** | 2024–2025 | 1048 | `marks:[session]:3:A` | `NOT_YET_IMPORTED` | Proposed historical internal marks import. Requires scoped session discovery. |
| **Sem 3** | 2025–2026 | 1067 | `marks:6161:3:A` | `VERIFIED_EXISTING_SNAPSHOT` | Fully accepted in Phase E.2.1 (`a9410bae...`). Immutable; do not refetch. |
| **Sem 4** | 2025–2026 | 2508 | `marks:6424:3:A` | `REUSE_EXISTING_SOURCE` | Existing snapshot (`03d1482b...`) preserved. Reused as verified source; revision optional. |
| **Sem 5** | 2026–2027 | 2582 | `marks:[session]:3:A` | `NOT_YET_IMPORTED` | Active ongoing term. Partial continuous evaluations expected. Explicit manual refresh only. |

---

## 3. Pre-Implementation Database Inventory

The production database at `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3` was inventoried using strictly read-only queries:

### Database Structure & Record Totals
- `academic_terms`: 5
- `courses`: 76 (across all 5 terms)
- `attendance_snapshots`: 9
- `attendance_snapshot_rows`: 136
- `attendance_period_observations`: 3,520
- `attendance_observation_batches`: 28
- `performance_snapshots`: 2
- `sync_jobs`: 88

### Verified Term Registry & Course Counts
1. **Semester 1** (AY 2024–2025, Class ID: `918`, `B.Tech CSE AIML-Sem 1`): **12 courses**
   - Roster: `CDO103B`, `CHS103C`, `CSH101C`, `CSH102C`, `CSS104C`, `CSS104C-PR`, `CSW103C`, `MAH104C`, `MAH104C-TUT`, `MEW104C`, `PHH101C`, `PHH102C`.
   - Aggregation: `MAH104C-TUT` continuous evaluations aggregated under `MAH104C`.
2. **Semester 2** (AY 2024–2025, Class ID: `1048`, `B.Tech CSE AIML-Sem 2`): **16 courses**
   - Roster: `CDO104B`, `CHH101C`, `CHH102C`, `CSH107C`, `CSH107C-TUT`, `CSH108C`, `CSH109C`, `CSH110C`, `CSS112C`, `ECH103C`, `ECH104C`, `HLS101C`, `HLS101C-PR`, `MAH101C`, `MAH101C-TUT`, `VAC-CS109`.
   - Aggregation: `CSH107C-TUT` under `CSH107C`; `MAH101C-TUT` under `MAH101C`; `VAC-CS109` external certification.
3. **Semester 3** (AY 2025–2026, Class ID: `1067`, `B.Tech CSE AIML-Sem 3`): **16 courses**
   - Roster: `CDO231`, `CSH201C`-`CSH208C`, `CSS210C`, `CSW209C`, `EDN248C`, `MAH204C`, `MAH204C-TUT`, `RDO201C`, `VAC-CS112`.
   - Reconciled marks courses: 13.
4. **Semester 4** (AY 2025–2026, Class ID: `2508`, `B.Tech CSE AIML-Sem 4`): **17 courses**
   - Roster: `CDO232`, `CSH213C`-`CSH220C`, `CSW218C`, `ECH108C`, `ECH109C`, `LWS101C`, `MCS368C`, `RDO202C`, `RDO203C`, `VAC-CS512`.
   - Reconciled marks courses: 15.
5. **Semester 5** (AY 2026–2027, Class ID: `2582`, `B.Tech CSE AIML-Sem 5`): **15 courses**
   - Roster: `CDO331`, `CSH301C`-`CSH305C`, `CSH310C`-`CSH312C`, `CSH318C`, `CSH319C`, `EDS240C`, `RDO202C`, `RDO204C`, `RDO301C`.
   - Active ongoing semester.

---

## 4. Reusable Pipeline Architecture

The marks ingestion architecture established in Phase E.1 and validated in Phase E.2 generalizes across all terms without structural modification:

```
[User UI Action]
      │
      ▼
1. Scoped Discovery: POST /api/v1/performance/discover-scopes (Term Key)
      │  └── Validates term exists & selector is verified
      │  └── Extracts exam_session options for that AY from portal DOM
      │  └── Records SyncJob(source_scope="PERFORMANCE_SCOPE_DISCOVERY")
      ▼
2. Scoped Preview: POST /api/v1/performance/preview (Term, Session, ExamType 3, Div A)
      │  └── Validates scope matches discovered options
      │  └── Extracts marks HTML, parses via parse_performance()
      │  └── Calculates source fingerprint SHA-256
      │  └── Holds payload in SyncJob(source_scope="PERFORMANCE_PILOT_PREVIEW")
      │  └── Returns preview metadata to user (zero DB snapshot written)
      ▼
[User Explicit Approval Required]
      │
      ▼
3. Zero-Refetch Import: POST /api/v1/performance/import (approval_id)
      │  └── Atomically claims preview token (COMPLETED -> APPROVED)
      │  └── Enforces 30-min window & exact scope match
      │  └── Reuses captured payload (ZERO NEW ERP REQUESTS)
      │  └── Persists immutable PerformanceSnapshot(checksum, payload)
      │  └── Scrubs captured_payload from SyncJob.details
      │  └── Returns snapshot_id & provenance
```

### Key Engineering Invariants Confirmed:
- **Zero Refetch during Import**: `capture_performance()` reads the parsed payload directly from `job.details["captured_payload"]`. The university ERP is never contacted a second time during approval.
- **Fail-Closed Concurrency**: Every operation requires acquiring `_SYNC_LOCK`. If the lock is held or fails, it releases cleanly in `finally`.
- **Atomic Single-Use Tokens**: The preview approval token cannot be replayed or substituted across terms.

---

## 5. Schema Compatibility & Parser Robustness

AttendPlan's table parser [`parse_grouped_marks`](file:///c:/Users/astra/Desktop/Project/AttendPlan/backend/app/services/performance_service.py) handles arbitrary column configurations dynamically:
- **Observed Column Counts**:
  - Semester 3: 9 columns (`CE`, `CE 2`, `Mid term examinations MRU`, `CE 3`, `CE 4`, `CE 6`, `CE 5`, `End Semester Examination`, `VIVA`).
  - Semester 4: 11 columns (`Mid term examinations MRU`, `CE`, `CE 2`, `CE 3`, `CE 4`, `CE 6`, `CE 7`, `CE 5`, `CE 8`, `VIVA`, `End Semester Examination`).
- **Synthetic Layouts Verified Offline**:
  - Semester 1 layout: 4 columns verified in `test_performance_multi_semester_readiness_e3.py`.
  - Semester 2 layout: 5 columns verified.
  - Semester 5 partial layout: Incomplete evaluations verified without error.
- **Value Semantics**:
  - Numeric ratios ($o/m$) parsed into float with derived percentage.
  - Unreported or blank cells preserved as `status="UNREPORTED"`, `obtained=None`, `maximum=None`.
  - Masked values (`*`) preserved as `status="MASKED_BY_PORTAL"`.
  - Zero is never substituted for missing marks.

---

## 6. Assessment Classification & Analytics Rules

AttendPlan maintains two strictly independent dimensions:

1. **Source Provenance**:
   - Identifies the official ERP source: Exam Type `3` (`INTERNAL EXAM`), Division `A`, Exam Session ID.
2. **Assessment Classification**:
   - `INTERNAL_CONTINUOUS_EVALUATION`: `CE`, `CE 2` – `CE 8`, lab continuous assessments.
   - `INTERNAL_MIDTERM`: Midterm examinations MRU, MST.
   - `PRACTICAL_ASSESSMENT`: Lab practical evaluations.
   - `VIVA`: Oral viva voce evaluations.
   - `END_SEMESTER_SOURCE_FIELD`: End Semester Examination columns appearing in internal reports.
   - `UNKNOWN_ASSESSMENT`: Unrecognized headers.

### Analytics Non-Negotiables:
- End-semester-labeled fields appearing in internal reports are **excluded** from continuous evaluation averages and rankings.
- No SGPA, CGPA, or official course final grades are synthesized from internal assessment tables.
- Official result cards and grade-point calculations remain a separate, future integration scope.

---

## 7. Quality Gates Verification

| Quality Gate | Tool / Command | Result | Pass Count |
| :--- | :--- | :---: | :---: |
| Backend Tests | `pytest backend/tests` | **PASS** | **297 passed** |
| Acceptance Tests (E.2.1) | `pytest backend/tests/test_performance_acceptance_e2_1.py` | **PASS** | **10 passed** |
| Multi-Semester Tests (E.3) | `pytest backend/tests/test_performance_multi_semester_readiness_e3.py` | **PASS** | **6 passed** |
| Python Linter | `ruff check backend/app backend/tests` | **PASS** | **0 issues** |
| Python Typechecker | `mypy backend/app` | **PASS** | **0 issues (44 files)** |
| Frontend Tests | `vitest run --run` | **PASS** | **38 passed (13 suites)** |
| Frontend Typechecker | `tsc --noEmit` | **PASS** | **0 errors** |
| Frontend Production Build | `npm run build` | **PASS** | **Clean (15.01s)** |
| Database Integrity | `PRAGMA integrity_check` | **PASS** | **ok** |

---

## 8. Summary of Accompanying Deliverables

1. [ATTENDPLAN_E3_PER_TERM_REQUEST_MANIFEST.md](file:///c:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_E3_PER_TERM_REQUEST_MANIFEST.md): Exact per-term source parameters, candidate class IDs, expected divisions, request ceilings, and stop conditions.
2. [ATTENDPLAN_PERFORMANCE_REVISION_POLICY.md](file:///c:/Users/astra/Desktop/Project/AttendPlan/reports/ATTENDPLAN_PERFORMANCE_REVISION_POLICY.md): Detailed revision policies for Semester 4 masked data and Semester 5 active-term progressive publication.

---

## 9. Conclusion & Checkpoint

Phase E.3 offline preparation is complete. All software, test fixtures, database invariants, and request budgets are verified.

**CURRENT STATE: AWAITING USER APPROVAL**  
No university portal requests will be executed without separate, explicit user authorization.

