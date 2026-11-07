# AttendPlan Historical Multi-Semester Backfill Architecture

## 1. Executive Summary
The Historical Backfill engine transforms AttendPlan from a single-semester tracker into a comprehensive university attendance repository covering Semesters 1 through 4 alongside current Semester 5 data.

The backfill is designed under five non-negotiable principles:
1. **Zero Credential Capture**: All authentication remains in the student's hands.
2. **Deterministic Two-Stage Extraction**: Subject-wise summary followed by day-wise period observations.
3. **Paced, Sequential Execution**: Strict 1.5s–2.5s pacing to respect ERP capacity.
4. **Multi-Semester Isolation**: Identical course codes across different semesters remain strictly separated.
5. **Idempotent Ingestion**: Repeated backfill runs update materialized views without inflating period counts or creating duplicate records.

---

## 2. Two-Stage Extraction Workflow

```
+--------------------------------------------------------------------------------+
|                        STAGE A: SUBJECT-WISE SUMMARY                           |
|  1. Select Academic Year -> 2. Select Semester -> 3. Select Class              |
|  4. Click Search -> 5. Wait for Table -> 6. Parse Canonical Columns            |
|  7. Validate 0 <= a <= d -> 8. Checksum & Snapshot -> 9. Upsert Courses         |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                         STAGE B: DAY-WISE HISTORY                              |
|  1. Navigate Day-Wise Page -> 2. Select Academic Year, Semester, Class         |
|  3. Determine Candidate Months (Aug-Nov for Odd, Jan-May for Even via AcademicTermCalendarService) |
|  4. Validate Month in Window (Reject Out-of-Window / Recess Months)            |
|  5. Fetch Timetable Matrix for Month -> 6. Exclude Header Rows (Timings)      |
|  7. Parse Observation Cells (P/A/Unreported) -> 8. Deduplicate SHA-256         |
|  9. Upsert Daywise Observations Scoped to Term                                 |
+--------------------------------------------------------------------------------+
```

### Phase D: Calendar-Aware Teaching Window Integration
In Phase D, `AcademicTermCalendarService` governs candidate month generation and request validation:
- **Odd Semesters (1, 3, 5, 7):** August through November of the start year (4 candidate months). Summer recess (June/July) and examination months (December) are excluded by default.
- **Even Semesters (2, 4, 6, 8):** January through May of the end year (5 candidate months). Previous calendar year months and summer vacation are strictly excluded.
- **Out-of-Window Prevention:** Any request outside the resolved candidate teaching window is classified as `OUTSIDE_CALENDAR_WINDOW` without issuing portal HTTP/CDP requests.
- **User Customization UI:** Students can view, add, or exclude specific teaching months per semester directly in `ArchiveSync.tsx`. Overrides take highest precedence (`USER_CONFIRMED`).

### Stage A: Subject-Wise Summary Extraction
For each selected term:
1. Form selector keys (`sel_academic_year`, `sel_sem`, `sel_class`).
2. Trigger the portal's Search action (`input[name="search"]`).
3. Await table element with selector `#sample_1` or table containing course headers.
4. Parse course rows using normalized headers:
   - Course Code, Course Name, Short Name, Faculty, Credits, Attended, Delivered, Percentage.
5. Apply Domain Invariant #1: Validate $0 \le a \le d$.
6. Domain Invariant #5: A course with $d = 0$ is classified as `UNRECORDED` (`None` / `null` percentage), never assumed to be 0% or 100%.
7. Store an immutable `attendance_snapshots` record and persist course records linked to `academic_term_id`.

### Stage B: Day-Wise History Extraction
For terms where day-wise historical attendance is accessible:
1. Navigate to the portal's Day-Wise attendance module (`dayWiseAttn.php`).
2. Set the term selectors.
3. Determine candidate calendar months:
   - **Odd Semesters (1, 3, 5)**: August, September, October, November, December.
   - **Even Semesters (2, 4)**: January, February, March, April, May.
4. For each candidate month, invoke search and parse the timetable matrix.
5. **Structural Header Exclusion**: Exclude non-instructional structural rows (such as rows containing `"Lecture Timings"`, day headers, or room labels).
6. **Observation Semantics**:
   - `P` / `Present` -> `PeriodStatus.PRESENT` ($a=1, d=1$).
   - `A` / `Absent` -> `PeriodStatus.ABSENT` ($a=0, d=1$).
   - Blank / whitespace -> `PeriodStatus.NOT_REPORTED` ($a=0, d=0$, Domain Invariant #11).
   - Explicit cancellation markers -> `PeriodStatus.NO_CLASS`.

---

## 3. Controlled Batching & Portal Safety Guardrails

- **Single Active Mutex (`_SYNC_LOCK`)**: A global threading lock prevents parallel portal requests. If an import is already executing, new import requests return `HTTP 409 Conflict`.
- **Configurable Pacing Delay**: Between consecutive month searches, the engine sleeps 1.5 to 2.5 seconds.
- **Session Expiry Detection**: The extractor monitors the browser URL and response content for login redirects (e.g. `auth.mrei.ac.in` or Keycloak login forms). If detected, the job transitions immediately to `SESSION_EXPIRED` without retrying blindly.
- **Graceful Cancellation**: At each stage boundary, `is_cancelled()` is checked. If the user clicks **Cancel Import**, extraction halts gracefully, preserving whatever partial terms were already saved.
- **No Anti-Bot Evasion**: AttendPlan operates strictly within the user's authentic browser context via loopback CDP. It never attempts to bypass CAPTCHA, scrape unauthorized endpoints, or bypass rate limits.

---

## 4. Multi-Semester Isolation & Data Integrity

### Domain Invariant #13: Multi-Semester Isolation
Students often repeat course codes across semesters (e.g., seminar courses, project courses, or common electives). AttendPlan prevents cross-term pollution by enforcing composite scoping:
- Courses are uniquely scoped by `(academic_term_id, course_code)`.
- Timetable periods are scoped by `(course_id, date, period_index)`.
- Materialized counts in `attendance_snapshots` belong strictly to their target `academic_term_id`.

### Idempotent Snapshot & Observation Deduplication
- **Canonical Checksum**: Before saving a snapshot, course rows are lexicographically sorted by course code. A canonical SHA-256 fingerprint is computed.
- **Duplicate Detection**: If a snapshot with identical fingerprint already exists for that term, AttendPlan marks the operation `DUPLICATE_SKIPPED`, avoiding redundant database writes.
- **Observation Upserts**: Period observations are upserted using SQLite primary key conflict resolution, ensuring existing observations are updated rather than duplicated.

---

## 5. Offline Simulation & Testing Harness

For continuous integration and offline verification, `HistoricalBackfillService.import_term_offline()` allows deterministic ingestion of synthetic HTML fixtures:
- `backend/tests/fixtures/synthetic_semester1_subjectwise.html`
- `backend/tests/fixtures/synthetic_semester2_subjectwise.html`
- `backend/tests/fixtures/synthetic_semester3_subjectwise.html`
- `backend/tests/fixtures/synthetic_semester4_subjectwise.html`
- `backend/tests/fixtures/synthetic_semester4_daywise.html`

This enables 100% offline verification of multi-term calculations, deduplication, and reconciliation without contacting live university servers.
