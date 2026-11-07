# AttendPlan Supervised Performance Pilot — Authorization Manifest
## Semester 3 Internal Academic Assessments Live Retrieval Scope

**Document ID**: `ATTENDPLAN_PERFORMANCE_IMPORT_MANIFEST`  
**Target Academic Term**: Academic Year 2025–2026, Semester 3 (Class ID 1067)  
**Status**: `AWAITING_USER_APPROVAL`  
**Safety Mode**: FAIL-CLOSED (Zero Live Extractions Executed Prior to Approval)  

---

## 1. Pilot Mission & Target Identification

This manifest defines the precise, auditable parameters for retrieving live academic performance records (internal continuous evaluations and mid-term marks) for Semester 3 from the university ERP portal (`mrei.icloudems.com`).

### Authorized Target Coordinates:
- **Academic Year**: `2025-2026`
- **Semester Number**: `3`
- **Class Identifier**: `1067` (`B.Tech CSE AIML-Sem 3`)
- **Division**: `A`
- **View Type**: `marks` (Internal Academic Assessments)
- **Target Term Key**: `2025-2026_s3_1067`

---

## 2. ERP Route & Expected Navigation Sequence

All network activity reuses the student's existing, authenticated Chrome CDP session on `127.0.0.1:9222`.

### Navigation Protocol:
1. **Menu Navigation**: Target page URL: `https://mrei.icloudems.com/corecampus/student/grades/new/myreportcard.php`.
2. **Route Verification**: Confirm DOM landed on `myreportcard.php` (never redirects to login or external domains).
3. **Filter Selection (Cascading)**:
   - `year`: Set to `2025-2026`.
   - `exam_session`: Query discovered options for 2025–2026 (e.g. Session `6161` *MRU-Odd-Semester-Dec-2025-2026-5041*).
   - `class`: Set to `1067` (`B.Tech CSE AIML-Sem 3`).
   - `division`: Set to `A`.
   - `exam_type`: Set to `3` (`INTERNAL EXAM`).
4. **Form Action Validation**: Confirm ancestor form action URL is strictly `https://mrei.icloudems.com/corecampus/student/grades/new/save/myreportcardSave.php` or `myreportcard.php`.
5. **Form Field Inspection**: Ensure zero editable marks inputs or file upload controls exist on the form.
6. **Report POST**: Trigger report query submit button.
7. **Response Verification**: Confirm response HTTP status `200 OK` and presence of table header `Subject Code`.

---

## 3. Strict Request Budget & Rate Limiting

| Step | Operation | Method & Route | Request Budget | Enforced Constraint |
| :---: | :--- | :--- | :---: | :--- |
| **1** | Scope Discovery | `POST /api/v1/performance/discover-scopes` | **1 request** | Enumerates available exam sessions for Sem 3 without importing marks. |
| **2** | Approval Preview | `POST /api/v1/performance/preview` | **1 request** | Generates an auditable `approval_id` tied to the discovered scope. |
| **3** | Report Capture | `POST /api/v1/performance/import` | **1 request** | Fetches the marks table and persists the immutable snapshot. |
| **TOTAL** | **Semester 3 Pilot Budget** | — | **Max 2 Live Portal Hits** | **Hard Stop. Zero additional requests.** |

- **Rate Limiting**: Minimum 3,000ms delay between dropdown triggers and navigation actions.
- **Response Timeout**: 15,000ms maximum wait for report response.
- **Zero Retries on Failure**: If any unexpected DOM change or HTTP error occurs, the job aborts immediately with `409 Conflict`.

---

## 4. Semester 3 Target Course Roster (16 Courses)

The parsed marks report rows must match the verified Semester 3 course roster:

| Course Code | Official Course Name | Component Type | Paired Entity / Isolation Rule |
| :--- | :--- | :---: | :--- |
| `CDO231` | PROFESSIONAL COMPETANCY ENHANCEMENT-I | THEORY | Standalone soft skill component. |
| `CSH201C` | ANALYSIS & DESIGN OF ALGORITHMS | THEORY | Theory component; distinct from CSH202C. |
| `CSH202C` | ANALYSIS & DESIGN OF ALGORITHMS LAB | LAB | Practical lab component; distinct from CSH201C. |
| `CSH203C` | DATABASE MANAGEMENT SYSTEMS | THEORY | Theory component; distinct from CSH204C. |
| `CSH204C` | DATABASE MANAGEMENT SYSTEMS LAB | LAB | Practical lab component; distinct from CSH203C. |
| `CSH205C` | OOPS USING JAVA | THEORY | Theory component; distinct from CSH206C. |
| `CSH206C` | OOPS USING JAVA LAB | LAB | Practical lab component; distinct from CSH205C. |
| `CSH207C` | ARTIFICIAL INTELLIGENCE | THEORY | Theory component; distinct from CSH208C. |
| `CSH208C` | ARTIFICIAL INTELLIGENCE LAB | LAB | Practical lab component; distinct from CSH207C. |
| `CSS210C` | ADVANCED PYTHON FOR AI | THEORY | Specialized domain course. |
| `CSW209C` | WEB DESIGNING-II | LAB | Practical workshop component. |
| `EDN248C` | UHV II/ SEEK | THEORY | Value education component. |
| `MAH204C` | DISCRETE MATHS | THEORY | Core mathematics component. |
| `MAH204C-TUT` | DISCRETE MATHS | TUTORIAL | Tutorial component; distinct from MAH204C. |
| `RDO201C` | SOCIAL INTERNSHIP-POST 2ND SEM | THEORY | Post-2nd sem internship evaluation. |
| `VAC-CS112` | MONGODB JAVA DEVELOPER PATH | THEORY | Value added course. |

---

## 5. Storage Destination & Immutability Rules

1. **Target Table**: `performance_snapshots` in `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`.
2. **Snapshot Deduplication**: The SHA-256 checksum is computed over the canonical, key-sorted parsed JSON payload. If an identical snapshot already exists, duplicate insertion is skipped (`DUPLICATE_SKIPPED`).
3. **Revision Preservation**: If an assessment score has changed or new tests are reported, a new snapshot record is inserted with its own unique UUID and capture timestamp. The previous snapshot is never overwritten.
4. **Isolation from Attendance**: Attendance tables (`attendance_snapshots`, `attendance_snapshot_rows`, `attendance_period_observations`, `attendance_observation_batches`) remain strictly read-only during this operation.
5. **Preservation of Semester 4 Baseline**: Existing Semester 4 snapshot `03d1482b-c997-431f-bc88-071c3bb4c764` (`marks:6424:3:A`) is completely preserved and untouched.

---

## 6. Preflight Backup Verification

- **Verified SQLite Backup**: `attendplan_pre_phase_e1_backup_20261101_204052.sqlite3`
- **Integrity Status**: `PRAGMA integrity_check = ok`
- **Foreign Key Status**: `PRAGMA foreign_key_check = []` (0 violations)
- **Backup Location**: `%LOCALAPPDATA%\AttendPlan\backups\` (outside Git repository)

---

## 7. Security Stop Conditions

The extraction workflow will halt immediately and commit zero records if ANY of the following occur:

1. Portal session is unauthenticated, expired, or demands credential entry.
2. Active student identity does not match the consented local student profile.
3. Available academic year or semester options do not contain 2025–2026 / Semester 3.
4. Class identifier 1067 is not listed or selectable.
5. Grouped marks table header does not match expected columns (`Subject Code`, `Subject Name`).
6. Any score exceeds maximum possible marks (e.g. obtained > max).
7. Concurrency lock `_SYNC_LOCK` is active (e.g. daily attendance sync running).
8. Any user cancellation or abort signal is received.

---

## 8. Checkpoint Decision

**Status**: `AWAITING_USER_APPROVAL`  

To proceed with this supervised pilot, please grant explicit approval for the Semester 3 internal assessment scope defined in this manifest.