---
name: attendance-domain
description: Exact attendance mathematics, thresholds, margin calculations, and scenario simulation invariants for AttendPlan.
---

# Attendance Domain Skill

## Core Formulas & Invariants

All calculations must be performed using exact rational arithmetic (`fractions.Fraction`) before any display formatting.

### 1. Variables
- $a$: Attended periods ($a \in \mathbb{N}_0$)
- $d$: Delivered periods ($d \in \mathbb{N}_0$)
- $t$: Attendance target fraction ($0 < t < 1$, standard $t = 0.75$)
- $x$: Additional periods attended in simulation ($x \ge 0$)
- $y$: Additional periods missed in simulation ($y \ge 0$)

### 2. Validation Bounds
- $0 \le a \le d$.
- If $a > d$ or $a < 0$, raise `InvalidAttendanceError`.

### 3. Metric Calculations
- **When $d > 0$**:
  - Exact Percentage: $100 \times \frac{a}{d}$
  - Safe Missing Periods (Bunk Margin):
    $$\text{can\_skip} = \max\left(0, \left\lfloor \frac{a}{t} - d \right\rfloor\right)$$
  - Consecutive Periods Required:
    $$\text{must\_attend} = \max\left(0, \left\lceil \frac{t \cdot d - a}{1 - t} \right\rceil\right)$$
  - Status:
    - If $\frac{a}{d} \ge t$: `SAFE`
    - If $\frac{a}{d} < t$: `AT_RISK`
- **When $d = 0$**:
  - `percentage = None`
  - `can_skip = None`
  - `must_attend = None`
  - `status = UNRECORDED`

### 4. Date-Wise Timetable Observation Semantics
- Matrix grid: $\text{Lecture Slot} \times \text{Calendar Date}$.
- `P`: Present ($1$ period for theory, $2$ periods for lab block).
- `A`: Absent ($1$ period for theory, $2$ periods for lab block).
- **Blank / Empty Cell Invariant**: Empty cells represent unscheduled slots or holidays. Status is `NO_CLASS` ($d = 0, a = 0$). **Never evaluate an empty cell as an absence**.
- `UNKNOWN`: Unrecognized indicators. Must not be fabricated into course absence.

### 5. Multi-Course & Multi-Semester Aggregation
- Overall attendance for a semester is strictly:
  $$\frac{\sum_{\text{sem}} a_i}{\sum_{\text{sem}} d_i}$$
- Cumulative career attendance across all semesters is strictly:
  $$\frac{\sum_{\text{career}} a_i}{\sum_{\text{career}} d_i}$$
  **Never average course percentages or semester percentages directly.**

### 6. Analytics Invariants
- **Monthly Analytics**: Grouped by $(year, month)$. The same month in different calendar years (e.g. Oct 2025 vs Oct 2026) remains strictly separate.
- **Weekday Analytics**: Grouped by Monday through Sunday using Asia/Kolkata date properties.
- **Subject Rankings**: 3 separate dimensions (by absolute missed, by missed rate %, by total delivered) to measure distinct student behaviors.

### 7. Reconciliation Evaluation
- `MATCHED`: $\sum a_{\text{sub}} = \sum a_{\text{day}} \land \sum d_{\text{sub}} = \sum d_{\text{day}} \land \text{unmapped} = 0$.
- `PARTIAL_COVERAGE`: Only one source exists, or data matches after accounting for known unmapped periods.
- `DISCREPANCY`: Count divergence detected between sources.
- `INSUFFICIENT_DATA`: Neither source recorded. Never interpolate fictitious values.
