# ATTENDPLAN — HISTORICAL GAP RECOVERY PLAN
## Narrowly Scoped Proposals for Unverified Historical Calendar Windows
### Semester 2 (January 2025) and Semester 3 (July 2025)

**Document Version:** 1.0  
**Audit Date:** 2026-11-01  
**Execution Boundary:** **AWAITING_USER_APPROVAL** (Zero Live Requests Executed)  
**Security Posture:** Read-Only, Localhost Bound (`127.0.0.1`), Strict Budget Controls  

---

## 1. Context & Motivation

Following the Phase D.4 recovery, all five semesters of the student's undergraduate program have verified subject-wise summary snapshots and multi-month day-wise observation ledgers in the local AttendPlan database.

However, detailed data integrity auditing in Phase D.5 identified two specific historical calendar windows where day-wise observation ledgers are narrower than the subject-wise reporting window:
1. **Semester 2 (January 2025)**: $\Delta = +85 \text{ attended} / +90 \text{ delivered}$
2. **Semester 3 (July 2025)**: $\Delta = +27 \text{ attended} / +27 \text{ delivered}$

In accordance with `AGENTS.md` rules and the explicit instructions of Phase D.5:
- **No live historical portal requests have been initiated.**
- **No synthetic attendance records have been fabricated.**
- Both windows are classified under precise integrity labels:
  - January 2025: `JANUARY_SOURCE_UNVERIFIED`
  - July 2025: `UNVERIFIED_JULY_DAYWISE_DATA` (or `INFERRED_OUT_OF_SCOPE_PERIODS`)

This document presents the technical analysis of both gaps and defines minimal, bounded, single-month recovery proposals for user consideration.

---

## 2. Semester 2 — January 2025 Investigation

### 2.1 Baseline & Evidence
- **Academic Year:** 2024–2025 | **Semester:** 2 | **Class ID:** 1048 (`B.Tech CSE AIML-Sem 2`)
- **Subject-Wise Summary:** 16 courses, 381 attended / 446 delivered ($85.43\%$).
- **Reporting Window in Summary Header:** `2025-01-13` to `2025-05-02`.
- **Saved Day-Wise Ledger:** February–May 2025 (4 batches, 430 observations, 296 attended / 356 delivered).
- **Unverified Gap:** 85 attended / 90 delivered (94.4% attendance).

### 2.2 Root Cause of January Omission
During Phase D.4, an automated day-wise request was dispatched for January 2025. The extraction aborted with:
`PortalSafetyError("FILTER_SELECTION_MISMATCH")`

Detailed code tracing in `live_portal_extractor.py` and `portal_safety.py` reveals:
1. On `myattendance.php`, selecting `<select name="month">` with value `"1"` (or `"01"`) triggers an asynchronous JavaScript `onchange` postback that populates `#from_date` and `#to_date`.
2. The safety control `portal_safety.choose(page, "month", candidates[0])` selects the option, waits for network idle, and re-reads `selected(page, "month")`.
3. If the portal's client-side script reloads the dropdown or resets the selection during the DOM update, `selected(page, "month")[0] != value` raises `FILTER_SELECTION_MISMATCH`.
4. Therefore, the portal was never actually queried for January timetable rows; the safety harness fail-closed before form submission.

### 2.3 Proposed Recovery Scope (Semester 2 — January 2025)
If approved by the user, a single live portal request will be executed:
- **Target URL:** `myattendance.php`
- **Filters:** Academic Year = `2024-2025`, Semester = `2`, Class ID = `1048`
- **Month:** `2025-01` (From: `2025-01-01` to `2025-01-31`)
- **Budget:** **1 portal request maximum**.
- **Pacing Delay:** 3.0 seconds.
- **Handling of Zero Classes:** If the portal returns `NO_REPORTED_PERIODS` (e.g., classes actually commenced in February in the portal's day-wise tracking system), the outcome will be recorded as `EMPTY_MONTH` without error.

---

## 3. Semester 3 — July 2025 Investigation

### 3.1 Baseline & Evidence
- **Academic Year:** 2025–2026 | **Semester:** 3 | **Class ID:** 1067 (`B.Tech CSE AIML-Sem 3`)
- **Subject-Wise Summary:** 16 courses, 400 attended / 463 delivered ($86.39\%$).
- **Reporting Window in Summary Header:** `2025-07-14` to `2025-11-22`.
- **Saved Day-Wise Ledger:** August–November 2025 (4 batches, 680 observations, 373 attended / 436 delivered).
- **Unverified Gap:** 27 attended / 27 delivered (100.0% attendance).

### 3.2 Root Cause of July Omission
July 2025 was **never requested** because:
1. The user's Phase D.4 authorization explicitly defined the approved candidate months as:
   `2025-08`, `2025-09`, `2025-10`, `2025-11`.
2. July 2025 was outside the approved 4-month scope.
3. AttendPlan strictly adhered to the authorized candidate months and did not exceed its request budget.

The course-level delta across the 10 courses with differences shows:
$$\text{CDO231: } +4/+4, \quad \text{CSH201C: } +4/+4, \quad \text{CSH202C: } +2/+2, \quad \text{CSH205C: } +3/+3, \quad \text{CSH206C: } +2/+2,$$
$$\text{CSH207C: } +1/+1, \quad \text{CSH208C: } +4/+4, \quad \text{CSS210C: } +3/+3, \quad \text{MAH204C: } +3/+3, \quad \text{MAH204C-TUT: } +1/+1$$
Sum = exactly 27 attended / 27 delivered.
While the mathematical correlation strongly suggests orientation/instruction between July 14 and July 31, 2025, **no local timetable slots exist for July 2025**.

### 3.3 Proposed Recovery Scope (Semester 3 — July 2025)
If approved by the user, a single live portal request will be executed:
- **Target URL:** `myattendance.php`
- **Filters:** Academic Year = `2025-2026`, Semester = `3`, Class ID = `1067`
- **Month:** `2025-07` (From: `2025-07-01` to `2025-07-31`)
- **Budget:** **1 portal request maximum**.
- **Pacing Delay:** 3.0 seconds.

---

## 4. Total Budget & Safety Controls

| Parameter | Proposal |
| :--- | :--- |
| **Total Live Requests** | **2 requests maximum** (1 for Jan 2025, 1 for July 2025) |
| **Authentication Mode** | Reuse existing authenticated Chrome CDP session on `127.0.0.1:9222` |
| **Credential Storage** | Zero password / OTP / cookie storage |
| **Database Safety** | Pre-execution WAL backup before each write |
| **Idempotence** | Skip ingestion if content checksum matches |
| **User Authorization** | Required before execution |

