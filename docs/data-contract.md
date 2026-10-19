# AttendPlan Data Contracts & Schemas

## 1. Domain Entities & Schemas

### 1.1 Course Status Enum
```typescript
type CourseStatus = "SAFE" | "AT_RISK" | "UNRECORDED";
```
- `"SAFE"`: Attendance is at or above the threshold fraction ($a/d \ge 0.75$).
- `"AT_RISK"`: Attendance is strictly below the threshold fraction ($a/d < 0.75$).
- `"UNRECORDED"`: Zero lectures delivered ($d = 0$). Attendance ratio is mathematically undefined.

### 1.2 Period Observation Status Enum
```typescript
type PeriodStatus = "PRESENT" | "ABSENT" | "NO_CLASS" | "NOT_REPORTED";
```
- `"PRESENT"`: Confirmed lecture attendance ($d=1, a=1$).
- `"ABSENT"`: Confirmed lecture absence ($d=1, a=0$).
- `"NO_CLASS"`: Confirmed administrative cancellation or scheduled holiday ($d=0, a=0$).
- `"NOT_REPORTED"`: Blank or unscheduled timetable cell ($d=0, a=0$). Crucially never evaluated as an absence.

### 1.3 Data Coverage Status Enum
```typescript
type CoverageStatus = "COMPLETE" | "PARTIAL" | "UNKNOWN" | "UNAVAILABLE";
```
- `"COMPLETE"`: Verified calendar date coverage across the expected academic window.
- `"PARTIAL"`: Subset of dates observed.
- `"UNKNOWN"`: Source pagination or coverage window cannot be conclusively established.
- `"UNAVAILABLE"`: Zero lectures delivered in the timeframe.

### 1.4 Reconciliation Status Enum
```typescript
type ReconciliationStatus =
  | "MATCHED"
  | "DISCREPANCY"
  | "PARTIAL_COVERAGE"
  | "INSUFFICIENT_DATA"
  | "SCOPE_MISMATCH";
```
- `"MATCHED"`: Subject-wise snapshot and day-wise observation totals agree exactly.
- `"DISCREPANCY"`: Data variance detected across identical date coverage boundaries.
- `"PARTIAL_COVERAGE"`: Only one source (subject-wise or day-wise) has been ingested.
- `"INSUFFICIENT_DATA"`: Neither source has data recorded for the term.
- `"SCOPE_MISMATCH"`: Day-wise observations cover a narrower date window than the full-term subject-wise snapshot. Totals are non-comparable; this represents partial date window extraction rather than a data integrity discrepancy.

---

## 2. Portal Session & Discovery Schemas

### 2.1 Portal Session Status (`PortalSessionStatusResponse`)
```json
{
  "state": "DISCONNECTED | BROWSER_READY | LOGIN_REQUIRED | AUTHENTICATED | DISCOVERING | DISCOVERY_COMPLETE | SESSION_EXPIRED | ERROR",
  "browser_launched": false,
  "cdp_port": 9222,
  "cdp_url": "http://127.0.0.1:9222",
  "current_url": null,
  "page_title": null,
  "profile_dir": "C:\\Users\\...\\AppData\\Local\\AttendPlan\\chrome-profile",
  "details": "No browser session connected on loopback port 9222.",
  "manual_fallback_available": true
}
```

### 2.2 Academic Term Discovery Response (`AcademicTermDiscoveryResponse`)
```json
{
  "academic_years": [
    { "value": "2026-2027", "label": "2026-2027", "selected": true },
    { "value": "2025-2026", "label": "2025-2026", "selected": false }
  ],
  "semesters": [
    { "value": "5", "label": "5", "selected": true }
  ],
  "classes": [
    { "value": "2582", "label": "B.Tech CSE AIML-Sem 5", "selected": true }
  ],
  "evidence": {
    "academic_year_count": 2,
    "semester_count": 1,
    "class_count": 1
  }
}
```

### 2.3 Subject-Wise Discovery Response (`SubjectWiseDiscoveryResponse`)
```json
{
  "table_found": true,
  "header_columns": [
    "S.No.", "Course Name", "Course Short Name", "Course Code",
    "Faculty Name", "Course Credit", "Attended/Delivered", "Percent"
  ],
  "record_count": 15,
  "date_range_detected": "04/08/2026 to 27/11/2026",
  "courses_found": [...],
  "evidence": { "total_rows_found": 15 }
}
```

### 2.4 Day-Wise Discovery Response (`DayWiseDiscoveryResponse`)
```json
{
  "table_found": true,
  "date_columns": ["01/10/2026 (Thu)", "05/10/2026 (Mon)", ...],
  "time_slots": ["08:10 - 09:00", "09:00 - 09:50", "09:50 - 10:40", ...],
  "has_course_name_toggle": true,
  "course_name_mapping_mechanism": "INLINE_CELL_TEXT",
  "sample_statuses_observed": ["A", "P"],
  "evidence": { "time_slot_count": 8, "date_column_count": 22 }
}
```

### 2.5 Overall Attendance Discovery Response (`OverallDiscoveryResponse`)
```json
{
  "view_found": true,
  "filter_controls": ["aca", "sem", "class"],
  "displayed_columns": ["S.No.", "Course Code", "Course Title", "Attended / Delivered", "Attendance %"],
  "macro_attendance_percentage": 88.46,
  "evidence": { "filter_count": 3 }
}
```
