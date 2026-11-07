# ATTENDPLAN — EFFECTIVE ATTENDANCE LEDGER AUDIT
## Semester 5 Raw History vs. Canonical Effective Ledger Analysis
### Investigation of the 663/838 Day-Wise Figure & Discrepancy Resolution

**Audit Date:** 2026-11-01  
**Target Semester:** Semester 5 (AY 2026–2027, Class ID `2582`)  
**Database:** `C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3`  
**Integrity State:** Verified (`PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check = 0`)  

---

## 1. Executive Summary & Core Finding

During the Phase D.4 reporting audit, a naive SQL query was run against the `attendance_period_observations` table:
```sql
SELECT sum(attended_period_count), sum(delivered_period_count)
FROM attendance_period_observations o
JOIN attendance_observation_batches b ON o.observation_batch_id = b.id
WHERE b.academic_term_id = 'ed06cbda-281f-4c60-b7ed-849817ba47db';
```
This naive query reported **663 attended / 838 delivered** across 9 batches and 1,112 raw observation rows, in contrast to the official ERP Subject-Wise Summary of **265 attended / 322 delivered** (or 260/313 in an earlier snapshot).

### Definitive Root Cause:
The **663/838** figure was **NOT an analytics defect or portal inconsistency**, but an artifact of summing **raw historical ingestions** across repeated live sync jobs.
In the active semester (Semester 5), AttendPlan performs periodic background refreshes (Service A). Over the months of August, September, and October 2026, nine observation batches were recorded:
- **August 2026** was extracted twice: Batch `38dbce3b` (102/115) and refreshed Batch `20cab324` (104/116).
- **September 2026** was extracted twice: Batch `755fa74b` (81/96) and refreshed Batch `783331dc` (83/97).
- **October 2026** was extracted FIVE times progressively as new classes occurred throughout the month:
  - Batch `1614a4a6` (Oct 1–16): 47/68
  - Batch `339c6462` (Oct 1–16, duplicate sync): 47/68
  - Batch `93fa0690` (Oct 1–21): 48/69
  - Batch `6dba4b78` (Oct 1–28): 73/100
  - Batch `355dfb7a` (Oct 1–30): 78/109

Summing all 9 raw batches yields:
$$\text{Attended: } 47 + 47 + 81 + 102 + 48 + 73 + 83 + 104 + 78 = \mathbf{663}$$
$$\text{Delivered: } 68 + 68 + 96 + 115 + 69 + 100 + 97 + 116 + 109 = \mathbf{838}$$
$$\text{Raw Rows: } 88 + 88 + 128 + 152 + 96 + 136 + 128 + 152 + 144 = \mathbf{1,112}$$

When the canonical deduplication engine (`app.services.current_observations.latest_observations`) resolves these raw records into the **Effective Ledger**, the result across the term is:
$$\text{Effective Attended: } 104 (\text{Aug}) + 83 (\text{Sep}) + 78 (\text{Oct}) = \mathbf{265}$$
$$\text{Effective Delivered: } 116 (\text{Aug}) + 97 (\text{Sep}) + 109 (\text{Oct}) = \mathbf{322}$$
$$\text{Effective Ledger Percentage: } \frac{265}{322} = \mathbf{82.30\%}$$

This matches the official Subject-Wise Summary snapshot of October 30, 2026 ($265/322 = 82.30\%$) **EXACTLY TO THE PERIOD**.

---

## 2. Inventory of Semester 5 Observation Batches

| Batch ID | Created At (UTC) | Date Range | Checksum Prefix | Status | Raw Obs | Attended | Delivered | Effective Role |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `1614a4a6-89d0-427b-b97e-35cefebc4838` | 2026-10-19 17:41 | 2026-10-01 to 2026-10-16 | `655e0f322052` | UNKNOWN | 88 | 47 | 68 | Historical snapshot (Superseded) |
| `339c6462-7ab3-40c7-970e-feb5add7940e` | 2026-10-20 19:44 | 2026-10-01 to 2026-10-16 | `1d11ace6fe71` | UNKNOWN | 88 | 47 | 68 | Duplicate sync (Superseded) |
| `755fa74b-c2cd-4ee9-add2-0c844d76224f` | 2026-10-20 19:44 | 2026-09-01 to 2026-09-30 | `e9a43e61e2c7` | UNKNOWN | 128 | 81 | 96 | September snapshot (Superseded) |
| `38dbce3b-ccc2-4c04-9200-c2b228807e94` | 2026-10-20 19:45 | 2026-08-04 to 2026-08-31 | `96c2d9f99254` | UNKNOWN | 152 | 102 | 115 | August snapshot (Superseded) |
| `93fa0690-141c-4832-a6bf-d14df60f2829` | 2026-10-21 12:50 | 2026-10-01 to 2026-10-21 | `1bbdcddc2fec` | UNKNOWN | 96 | 48 | 69 | October progress (Superseded) |
| `6dba4b78-bb9e-403a-8539-83f048d28eb0` | 2026-10-28 16:01 | 2026-10-01 to 2026-10-28 | `e1345946cf42` | UNKNOWN | 136 | 73 | 100 | October progress (Superseded) |
| `783331dc-1062-4f0f-b82e-41bfd95a6f5c` | 2026-10-28 17:52 | 2026-09-01 to 2026-09-30 | `883a0f37a918` | UNKNOWN | 128 | 83 | 97 | **September LATEST Effective Batch** |
| `20cab324-6659-4804-8903-75ae01be7a47` | 2026-10-28 17:52 | 2026-08-04 to 2026-08-31 | `c81c914af105` | UNKNOWN | 152 | 104 | 116 | **August LATEST Effective Batch** |
| `355dfb7a-74d3-44fe-aa8f-126295a0b02c` | 2026-10-30 15:16 | 2026-10-01 to 2026-10-30 | `6cf37d75aa3c` | UNKNOWN | 144 | 78 | 109 | **October LATEST Effective Batch** |
| **TOTAL RAW / EFFECTIVE** | — | — | — | — | **1,112** | **663** | **838** | **Effective: 424 slots (265 / 322)** |

---

## 3. Placeholder Course Remediation & Course-by-Course Parity

### The Defect:
On 2026-10-19 17:41:39, during the first automated day-wise sync of Semester 5, `daywise_parser` encountered timetable slots labeled `PROFESSIONAL COMPETANCY ENHANCEMENT-III (PP)`. Because the course alias mapping for Semester 5 was not yet bound and `(PP)` was not recognized as a lab code, the system auto-created a placeholder course entity:
- `id`: `ac528c68-f953-4924-8c6d-f1968597ac5e`
- `course_code`: `PROFESSIONAL COMPETANCY ENHANCEMENT-III (PP)`
- `course_name`: `Course PROFESSIONAL COMPETANCY ENHANCEMENT-III (PP)`
- Snapshot rows: `0`

When the official Subject-Wise Summary was ingested, it created the genuine course entity:
- `id`: `dfa27ba1-c811-401b-ac90-cafaa2344e15`
- `course_code`: `CDO331`
- `course_name`: `PROFESSIONAL COMPETANCY ENHANCEMENT-III`
- Snapshot rows: 49 attended / 61 delivered

This split caused 161 day-wise observations to remain linked to the placeholder `ac528c68` while `CDO331` appeared to have 0 day-wise periods, generating a false course-level discrepancy (+49/-49).

### Remediation Executed:
`backend/scripts/remediate_sem5_course_links.py` executed:
1. Re-pointed all 161 observations from `ac528c68` to `dfa27ba1` (`CDO331`) with `course_mapping_confidence = 1.0`.
2. Deleted the redundant placeholder course `ac528c68`.
3. Verified SQLite integrity (`ok`) and foreign keys (`0 violations`).

### Verified Course-Level Comparison Table (Semester 5):

| Course Code | Course Name | Subject-Wise Att / Del | Effective Day-Wise Att / Del | Status |
| :--- | :--- | :---: | :---: | :---: |
| `CDO331` | PROFESSIONAL COMPETANCY ENHANCEMENT-III | 49 / 61 | 49 / 61 | **MATCHED** |
| `CSH301C` | COMPUTER ARCHITECTURE & ORGANISATION | 26 / 32 | 26 / 32 | **MATCHED** |
| `CSH302C` | OPERATING SYSTEMS | 28 / 32 | 28 / 32 | **MATCHED** |
| `CSH303C` | OPERATING SYSTEMS LAB | 14 / 16 | 14 / 16 | **MATCHED** |
| `CSH304C` | ADVANCED JAVA | 27 / 31 | 27 / 31 | **MATCHED** |
| `CSH305C` | ADVANCED JAVA LAB | 18 / 22 | 18 / 22 | **MATCHED** |
| `CSH310C` | INTRODUCTION TO NOSQL DATABASES | 22 / 29 | 22 / 29 | **MATCHED** |
| `CSH311C` | COMPUTER ARCHITECTURE & ORG LAB | 16 / 20 | 16 / 20 | **MATCHED** |
| `CSH312C` | INTRODUCTION TO NOSQL DATABASES LAB | 16 / 20 | 16 / 20 | **MATCHED** |
| `CSH318C` | Computer Vision & Image Processing | 21 / 27 | 21 / 27 | **MATCHED** |
| `CSH319C` | Computer Vision & Image Processing LAB | 18 / 22 | 18 / 22 | **MATCHED** |
| `EDS240C` | ESSENCE OF INDIAN TRADITIONAL KNOWLEDGE | 10 / 10 | 10 / 10 | **MATCHED** |
| `RDO202C` | RESEARCH & INNOVATION | 0 / 0 | 0 / 0 | **MATCHED** |
| `RDO204C` | TECHNICAL INTERNSHIP-I | 0 / 0 | 0 / 0 | **MATCHED** |
| `RDO301C` | Interdisciplinary Project | 0 / 0 | 0 / 0 | **MATCHED** |
| **TOTAL** | **15 Courses** | **265 / 322 (82.30%)** | **265 / 322 (82.30%)** | **100% PARITY** |

---

## 4. Architectural Safeguards Verified

1. **`latest_observations` Resolution**:
   All public backend analytics endpoints (`get_monthly_analytics`, `get_weekday_analytics`, `get_daily_analytics`, `get_attendance_periods`, and `ReconciliationService`) strictly pass raw observation queries through `latest_observations(...)`. No public endpoint ever sums raw batches.
2. **Regression Test Enforcement**:
   - `test_effective_ledger_deduplication_prevents_raw_history_inflation` in `test_current_refresh.py` asserts that overlapping/duplicate batches of the same month never inflate attendance totals.
   - `test_current_month_rollover_november_2026` asserts that advancing the calendar month preserves prior monthly batches without inflation.

