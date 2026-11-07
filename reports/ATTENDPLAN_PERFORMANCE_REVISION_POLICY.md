# AttendPlan — Academic Performance Revision & Lifecycle Policy

**Scope**: Policies for Masked Score Revisions (Semester 4) and Active-Term Progressive Publication (Semester 5)  
**Date**: November 1, 2026  
**Auditor**: Principal Academic Records Engineer  
**Status**: APPROVED POLICY SPECIFICATION  

---

## 1. Core Immutability Invariant

AttendPlan's database model stores performance data as discrete, timestamped snapshots (`PerformanceSnapshot` table).

1. **Snapshot Immutability**:
   Once stored, a `PerformanceSnapshot` row is cryptographically fingerprinted using SHA-256 over its canonical payload. A row is **never updated or overwritten in place**.
2. **Revision History via Append-Only Log**:
   If a new marks report is captured for an existing `(term_key, view)` tuple:
   - If the SHA-256 fingerprint matches an existing snapshot, the existing snapshot is returned (idempotent deduplication).
   - If the SHA-256 fingerprint differs (e.g. previously masked grades are now revealed, or active-term assessments have been added), a **new snapshot row** is inserted with an updated timestamp and provenance.
   - The UI displays the latest snapshot while retaining the full historical audit trail.

---

## 2. Semester 4 Masked Score Analysis & Revision Policy

### Current State Analysis
- **Snapshot ID**: `03d1482b-c997-431f-bc88-071c3bb4c764`
- **Term Key**: `2025-2026_s4_2508`
- **Storage View**: `marks:6424:3:A`
- **Checksum**: `c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d`
- **Captured At**: `2026-10-20 19:16:02.037487`
- **Cell Breakdown (165 Cells)**:
  - `REPORTED`: 60 cells (Midterms, CE 1 through CE 8, Viva)
  - `UNREPORTED`: 90 cells (Unapplicable continuous evaluation columns for specific courses)
  - `MASKED_BY_PORTAL`: **15 cells**

### Findings on Portal Masking
Every single course in Semester 4 (15 courses) has its `End Semester Examination` cell masked with an asterisk (`*`):
- `CDO232` (PCE-II): `*`
- `CSH213C` (Software Engineering): `*`
- `CSH215C` (Computer Networks): `*`
- `CSH217C` (Machine Learning): `*`
- `CSH219C` (Advanced Neural Networks): `*`
- etc.

Under iCloudEMS ERP configuration, universities mask end-semester scores in student internal reports prior to formal result declaration by the Controller of Examinations.

### Revision Policy for Semester 4
1. **Respect Source Masking**: AttendPlan never attempts to bypass portal masking, scrape hidden attributes, or fabricate masked scores.
2. **Existing Snapshot is Reused**: The existing snapshot is treated as a verified historical record reflecting the state on October 20, 2026.
3. **Optional User-Triggered Refresh**:
   - If the user suspects that the university has published or unmasked Semester 4 final scores, they may explicitly request a Semester 4 preview in a future phase.
   - If the newly extracted payload contains revealed scores, a new snapshot will be appended without destroying snapshot `03d1482b...`.
   - In Phase E.3, **no refresh request is permitted**.

---

## 3. Semester 5 Active-Term Progressive Publication Policy

Semester 5 (AY 2026–2027) is currently active and ongoing.

### Active Term Realities
In an active university semester, internal marks reports exhibit progressive publication:
- Early semester: Only `CE 1` or lab assessments may be posted.
- Mid semester: `Mid term examinations MRU` and `CE 2` posted; later CEs remain pending.
- Late semester: `CE 3` through `CE 6` posted; End Semester Examination remains unconducted or masked.

### Non-Negotiable Rules for Active Terms:
1. **Source Incompleteness is NOT an Import Failure**:
   A marks report with only 1 or 2 CEs per course is completely valid for an ongoing semester. AttendPlan accepts and preserves it with status `UNREPORTED` or `PENDING` for missing columns.
2. **No Zero Substitution**:
   Unposted evaluations must remain `None` / `null`. Substituting 0 for an unheld quiz or upcoming midterm would falsely collapse student analytics.
3. **Strict Decoupling from Startup Sync**:
   - Regular application launch syncs current-semester daily attendance only.
   - **Marks synchronization is never executed automatically on app launch**.
   - Current-term marks extraction must be an explicit, separate user action requiring individual preview and approval.
4. **Append-Only Versioning**:
   As new assignments and quizzes are graded throughout the semester, subsequent user-approved imports will create new snapshot revisions, allowing the student to track their continuous assessment progress over time.

---

## 4. Concurrency & Failure Recovery Invariants

1. **Daily Attendance Priority**:
   Attendance tracking is AttendPlan's primary operational function. Academic performance operations must never delay, block, or interfere with attendance imports.
2. **Lock Lifecycle**:
   All performance routes (`discover-scopes`, `preview`, `import`) acquire `_SYNC_LOCK`. The lock is released in a mandatory `finally:` block under all outcomes (success, network error, parsing error, or user cancellation).
3. **Atomic Database Transactions**:
   Snapshot insertion and sync job updates execute in atomic SQLAlchemy transactions. If parsing fails midway, database rollback is immediate and zero partial records are stored.

---

## 5. Summary Policy Table

| Term | Operational Status | Ingestion Policy | Revision Policy | Startup Sync |
| :---: | :---: | :--- | :--- | :---: |
| **Sem 1** | Completed Historical | Bounded 1-discovery, 1-import | Single immutable snapshot | Disabled |
| **Sem 2** | Completed Historical | Bounded 1-discovery, 1-import | Single immutable snapshot | Disabled |
| **Sem 3** | Completed Historical | Verified Existing Snapshot | Immutable; zero refetch | Disabled |
| **Sem 4** | Completed Historical | Reused Existing Snapshot | Masked cells retained; revision optional | Disabled |
| **Sem 5** | Active Ongoing | Progressive Partial Capture | Append-only multi-snapshot versioning | **Strictly Disabled** |

