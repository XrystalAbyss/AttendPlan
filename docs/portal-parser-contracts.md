# AttendPlan — Portal DOM Parser Contracts (F2-B)

## 1. Subject-Wise Attendance Contract (`subwise_attendace_new.php`)

### Form Controls:
- **Academic Year Select**: Select element containing options like `<option value="2025-2026">2025-2026</option>`.
- **Semester Select**: Dynamic dropdown dependent on academic year. Contains semester options `1..8`.
- **Class Select**: Dynamic dropdown dependent on semester. Contains class mappings (e.g. `2582` -> `B.Tech CSE AIML-Sem 5`).
- **Submit / Search**: Form submission button triggering table render.

### Table Structure:
- Target table identified by semantic headers:
  `Course Code` | `Course Name` | `Course Category` | `Faculty Name` | `Attended` | `Delivered` | `Percentage`
- **Cell Extraction Rules**:
  - `course_code`: Clean string, uppercase alphanumeric (e.g. `23CS301`).
  - `course_name`: Official title (e.g. `Artificial Intelligence & Machine Learning`).
  - `attended_periods`: Non-negative integer $a \ge 0$.
  - `delivered_periods`: Non-negative integer $d \ge a$.
  - `portal_percent`: Displayed floating-point percentage string.
- **Validation Invariants**:
  - Domain validation: $0 \le a \le d$.
  - Percentage tolerance: Rational percentage $100 \times \frac{a}{d}$ compared against `portal_percent` within $\pm 0.5\%$.
  - Discrepancy > 0.5% triggers a warning and marks snapshot as quarantined.

---

## 2. Day-Wise Timetable Matrix Contract (`myattendance.php`)

### Form Controls:
- **Academic Year**: Dropdown matching active semester.
- **Semester**: Dropdown matching active semester.
- **Class**: Dropdown matching student section.
- **Month Select**: Dropdown with two-digit or single-digit month numbers (`01` through `12`).
- **Date Inputs**: Optional `From Date` and `To Date` boundary filters.
- **Show Course Name Checkbox**:
  - When checked, each period slot displays the course code / short name alongside or above the attendance marker.
  - Crucial for assigning period observations to specific academic catalog courses.
- **Search Button**: Fetches day-by-day timetable attendance grid.

### Matrix Layout:
- **Top Header**: Date columns formatted as `Day DD/MM` (e.g. `Mon 01/09`, `Tue 02/09`, `Wed 03/09`).
- **Left Column**: Time slot intervals (e.g., `08:10-09:00`, `09:00-09:50`, `09:50-10:40`, `10:40-11:30`, `12:20-13:10`, `13:10-14:00`, `14:00-14:50`, `14:50-15:40`).
- **Cells**:
  - `P`: Counted as Present ($a=1, d=1$).
  - `A`: Counted as Absent ($a=0, d=1$).
  - Blank / `-`: Counted as Unreported / No Class ($a=0, d=0, \text{PeriodStatus.NOT_REPORTED}$).
  - Multi-period laboratory slots: Evaluated per individual time slot column (never arbitrary $\times 2$ multiplier).
  - Course label: Extracted from cell text or child span when `Show Course Name` is active.

---

## 3. Discrepancy & Quarantine Policy
- **Quarantine**: If row totals do not equal extracted individual P/A counts or course mapping is contradictory, the batch is saved with a `QUARANTINED` flag.
- Never discard university data silently.
- Never manufacture absent or present records to force reconciliation.
