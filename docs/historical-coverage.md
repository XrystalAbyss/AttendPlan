# AttendPlan Historical Coverage Model

## 1. Principles of Historical Coverage
Archived university attendance data is inherently uneven:
- Completed semesters may retain full subject-wise summary totals while day-wise period records have been archived, purged, or restricted by the institution.
- In other terms, only specific months or instructional dates may be accessible.

AttendPlan's coverage engine ensures the system **never misrepresents partial data as complete** and never extrapolates period-level patterns from aggregate course totals alone.

---

## 2. Discrete Coverage States

| State | Definition | Analytical Permissibility |
| :--- | :--- | :--- |
| `NOT_IMPORTED` | Discovered in portal selectors, but no data has been saved locally. | No analytics available. |
| `DISCOVERED` | Selectors and candidate months identified; awaiting user sync authorization. | Shows estimated requests only. |
| `IN_PROGRESS` | Synchronizing currently active term data. | Displays live progress indicators. |
| `PARTIAL` | Contains subject summaries and/or a subset of candidate months. | Subject summaries displayed with explicit partial badges; period analytics restricted to captured date window. |
| `COMPLETE_FOR_REQUESTED_SCOPE` | Subject summary and all candidate months have been attempted and retrieved without unrecoverable errors. | Full subject and period analytics permitted. |
| `FAILED` | Sync halted due to unrecoverable portal, network, or authentication error. | Actionable error displayed with retry action. |
| `CANCELLED` | User cancelled sync before requested scope completed. | Preserves and displays partial records captured prior to cancellation. |

> [!CAUTION]
> **Single Month Rule**: Under no circumstances does AttendPlan mark a semester `COMPLETE` simply because one month (e.g. October) was downloaded. If only 1 out of 5 candidate months is present, the coverage state remains strictly `PARTIAL`.

---

## 3. Coverage Metrics Data Contract

Every term tracked by AttendPlan produces a comprehensive `TermCoverageReport`:

```python
class TermCoverageReport(BaseModel):
    term_id: str
    academic_year: str
    semester_number: int
    class_identifier: str
    coverage_state: CoverageState
    
    # Subject-Wise Metrics
    has_subject_summary: bool
    subject_snapshot_count: int
    subject_courses_count: int
    
    # Day-Wise Temporal Metrics
    candidate_months: List[str]          # All months expected for semester
    candidate_month_labels: List[str]
    months_attempted: List[str]          # Months requested from portal
    months_completed: List[str]          # Months successfully parsed
    
    # Period Observation Metrics
    unique_instructional_dates: int      # Count of calendar dates with classes
    unique_instructional_periods: int    # Total period slot observations
    mapped_periods: int                  # Observations matched to known courses
    unmapped_periods: int                # Observations with ambiguous or unknown course code
    missing_or_unreported_periods: int   # Blank cells (NOT_REPORTED)
    source_errors_count: int             # Extraction/parsing errors encountered
    
    # Reconciliation Link
    reconciliation_verdict: TermReconciliationVerdict
    details: Dict[str, Any]
```

---

## 4. Analytical Guardrails on Partial Coverage

1. **Explicit UI Badges**: If a semester has `coverage_state == "PARTIAL"`, the UI renders a visible amber `Partial Data` badge alongside the exact counts of completed vs candidate months.
2. **No Data Invention**: If day-wise data is missing for a month, AttendPlan never interpolates or fabricates absences for those dates.
3. **Absence Totals Qualification**: Absence counts are explicitly qualified as `"Recorded Absences (Captured Range)"` rather than definitive semester-long totals whenever day-wise coverage is partial.
4. **Scope-Separated Analytics**: The Monthly Breakdown and Weekday Breakdown charts only aggregate instructional dates that actually exist in the local SQLite database.

---

## 5. API Reference

| Endpoint | Method | Response Schema | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/terms/{term_id}/coverage` | `GET` | `TermCoverageResponse` | Fetches the full coverage audit report for a specific semester |

---

## 6. Phase D Coverage Refinements & True Denominators

### True Candidate Month Denominators
In Phase D, historical coverage denominators reflect the authentic candidate teaching window:
- Odd semesters have a denominator of **4 candidate months** (Aug–Nov).
- Even semesters have a provisional denominator of **5 candidate months** (Jan–May).
- Arbitrary 12-month calendar denominators are prohibited.

### Processing vs Academic Source Coverage Verdicts
The synchronization engine separates operational completion from institutional completeness:
1. `IMPORT_PROCESSING_COMPLETE`: All user-approved candidate month requests have executed to completion without active jobs pending.
2. `ACADEMIC_SOURCE_COVERAGE_COMPLETE`: In addition to processing completion, all candidate months returned valid periods without unresolved warning pages or extraction gaps. If any candidate month has unresolved errors, the term verdict is classified as `ACADEMIC_SOURCE_COVERAGE_PARTIAL`.

### Independent Academic Performance Coverage
Academic marks and continuous evaluations are tracked as independent term-scoped snapshots in `performance_snapshots` and are not bounded by monthly attendance windows. Sessional marks published outside the normal lecture calendar remain accessible without affecting attendance coverage calculations.
