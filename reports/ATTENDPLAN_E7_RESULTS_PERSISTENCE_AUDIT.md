# AttendPlan Phase E.7 Results Persistence & Data Integrity Audit
## Database Schema Validation, Deduplication, and Isolation Verification

**Date:** 2026-11-07  
**Database Path:** `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`  
**Pre-Pilot Backup:** `%LOCALAPPDATA%\AttendPlan\backups\attendplan_pre_phase_e7_backup_20261102_020215.sqlite3` (1,961,984 bytes)  
**Active Schema Revision:** `f2e2_official_results` (Upgraded from `f2e1_performance`)  

---

## 1. Complete Database Entity Accounting

| Entity / Table | Count Pre-E.7 | Count Post-E.7 | Net Delta | Verification Status |
| :--- | :---: | :---: | :---: | :--- |
| `academic_terms` | 5 | 5 | 0 | **Preserved** (Sem 1 to 5) |
| `courses` (Catalog) | 76 | 76 | 0 | **Preserved** (Isolated by term) |
| `attendance_snapshots` | 10 | 10 | 0 | **Preserved** (Pre-E.7 baseline intact) |
| `attendance_snapshot_rows` | 151 | 151 | 0 | **Preserved** (Pre-E.7 baseline intact) |
| `attendance_period_observations` | 3,544 | 3,544 | 0 | **Preserved** (Zero records dropped/overwritten) |
| `attendance_observation_batches` | 29 | 29 | 0 | **Preserved** (Pre-E.7 baseline intact) |
| `performance_snapshots` (Class A) | 5 | 5 | 0 | **Preserved** (5 terms, 55 courses, 468 cells) |
| `official_result_snapshots` (Class B) | 0 | 1 | +1 | **Committed** (Semester 4 WITHHELD snapshot) |
| `official_course_result_rows` | 0 | 0 | 0 | **Preserved** (0 fabricated rows) |

---

## 2. Ingested Checkpoint Details (Semester 4)

- **Snapshot ID:** `ee187733-e8c1-4d1c-91ec-5b6f876adfb3`
- **Term Key:** `2025-2026_s4_2508`
- **Academic Year:** `2025-2026`
- **Semester Number:** `4`
- **Class Identifier:** `2508`
- **Exam Session Label:** `Official Result Card (COE)`
- **Publication Status:** `WITHHELD`
- **SGPA / CGPA:** `NULL` / `NULL`
- **Credits Registered / Earned:** `NULL` / `NULL`
- **Total Points Secured:** `NULL`
- **Canonical SHA-256 Checksum:** `1a871792877ab96ef16e356bdaa350681e38799de556197d97371df2a3a7b180`
- **Provenance:** `LIVE_PORTAL`
- **Captured At:** `2026-11-07T09:10:17.988148`

---

## 3. Idempotency & Deduplication Audit

To verify idempotency, `persist_official_result` was executed a second time with identical data.
- **Result:** Returned `DUPLICATE_SKIPPED`.
- **Database Row Count:** Exactly 1 row remained in `official_result_snapshots`.
- **Integrity Status:** Checksum determinism guaranteed; no redundant records or duplicate entries created.

---

## 4. API Response Verification

### `GET /api/v1/performance/official-results`
```json
{
  "results": [
    {
      "snapshot_id": "ee187733-e8c1-4d1c-91ec-5b6f876adfb3",
      "term_key": "2025-2026_s4_2508",
      "academic_year": "2025-2026",
      "semester_number": 4,
      "class_identifier": "2508",
      "exam_session": null,
      "exam_session_label": "Official Result Card (COE)",
      "publication_status": "WITHHELD",
      "declaration_date": null,
      "credits_registered": null,
      "credits_earned": null,
      "total_points_secured": null,
      "sgpa": null,
      "cgpa": null,
      "checksum": "1a871792877ab96ef16e356bdaa350681e38799de556197d97371df2a3a7b180",
      "provenance": "LIVE_PORTAL",
      "captured_at": "2026-11-07T09:10:17.988148",
      "courses_count": 0,
      "courses": []
    }
  ],
  "total_terms_with_results": 1,
  "note": "Official University Results (Data Class B) are distinct from internal assessment marks."
}
```

### `GET /api/v1/performance/overview`
In `2025-2026_s4_2508`:
- `insights` includes: `"Official Results: WITHHELD by COE Office. This page has been deactivated by the COE Office.Kindly contact the COE Office for activation or further assistance."`
- `official_result` block surfaces `publication_status: "WITHHELD"`, `sgpa: null`, `cgpa: null`, and `institutional_notice`.
- Zero changes to the other 4 semester internal marks or attendance insights.

---

## 5. Non-Negotiable Invariants Compliance

- **No Overwrite of Class A Marks:** Verified. 5 snapshots, 55 courses, 468 cells remain byte-for-byte identical.
- **No Overwrite of Attendance Archive:** Verified. 3,544 observations, 76 courses remain byte-for-byte identical.
- **No Fake Grade Generation:** Verified. SGPA and CGPA remain `null`, and `official_course_result_rows` contains 0 rows.

