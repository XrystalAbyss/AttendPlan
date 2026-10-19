# AttendPlan F1 Attendance Observation Model

## 1. Domain Context & Timetable Matrix
In university ERP portals (specifically iCloudEMS `myattendance.php`), student attendance is structured as a two-dimensional timetable grid:
$$\text{Lecture Time Slots (Rows)} \times \text{Calendar Dates (Columns)}$$

Individual matrix cells contain textual indicators representing attendance status for that specific slot on that date.

---

## 2. Period Status & Evaluation Semantics

The AttendPlan observation model enforces strict semantic definitions for each cell value:

| Portal Symbol | Evaluated Enum | Delivered Count | Attended Count | Description |
| :--- | :--- | :--- | :--- | :--- |
| `P` | `PRESENT` | $1$ (Theory) / $2$ (Lab) | $1$ (Theory) / $2$ (Lab) | Verified student attendance |
| `A` | `ABSENT` | $1$ (Theory) / $2$ (Lab) | $0$ | Verified student absence |
| Blank / Empty | `NO_CLASS` | $0$ | $0$ | Unscheduled slot, holiday, or recess |
| Other / Unrecognized | `UNKNOWN` | $0$ | $0$ | Unverified indicator requiring audit |

### Critical Invariants:
1. **Empty Cells Invariant**:
   $$\text{Blank Cell} \neq \text{Absence}$$
   Empty cells MUST NEVER be evaluated as student absences. Marking an unscheduled slot as absent causes severe artificial deflation of attendance percentages.
2. **Distinct Domain States**:
   $$\text{UNKNOWN} \neq \text{ABSENT} \neq \text{NO\_CLASS}$$
   Non-attendance is only recorded when an affirmative `A` indicator exists in a scheduled period.
3. **Lab Multipliers**:
   Laboratory sessions represent multi-period blocks (standardly 2 periods). When a slot represents a lab session, both delivered and attended increments reflect 2 periods.

---

## 3. Course Mapping Confidence & Unmapped Observations

When extracting day-wise attendance, courses may or may not be explicitly designated in time slot headers:

1. **Explicit Match (`confidence = 1.0`)**: Slot header or row title clearly specifies the course code (e.g., `CSH301C - CAOR`). The observation is formally linked to the corresponding foreign key `Course.id`.
2. **Heuristic Match (`confidence = 0.8`)**: Matched via course short name or subject alias.
3. **Unmapped Observation (`confidence = 0.0`)**: Slot label does not provide an identifiable course code (e.g., `Period 1 (09:00 - 10:00)`).
   - In this state, `course_id` remains `NULL`.
   - The raw slot string is preserved in `source_period_identifier`.
   - The observation is fully aggregated into **Date-Wise, Weekday, and Monthly analytics**, but is **strictly prevented from fabricating course-level data**.

---

## 4. Deduplication & Canonical Checksum Invariance

Multiple imports of overlapping calendar ranges (e.g., importing October 1–15 and subsequently October 10–31) must never result in duplicate observation inflation:

1. **Observation Batch Checksum**:
   Calculated by normalizing all observation records into a canonical representation:
   $$\text{Entry} = \text{Date} \,\|\, \text{Slot} \,\|\, \text{CourseCode} \,\|\, \text{Delivered} \,\|\, \text{Attended} \,\|\, \text{Status}$$
   Sorted lexicographically and hashed with SHA-256. Row or column presentation order from the portal HTML does not alter the digest.
2. **Idempotent Ingestion**:
   If an observation batch with identical term ID and checksum has previously succeeded, `IngestionService` skips ingestion with outcome `DUPLICATE_SKIPPED`.
3. **Audit Trail**:
   All ingestion attempts log an immutable `IngestionEvent` record detailing the attempt timestamp, outcome, and affected batch/snapshot.
