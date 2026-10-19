# AttendPlan F1 Analytics Specification

## 1. Domain Mathematics & Calculation Philosophy
AttendPlan computes all attendance analytics using pure, deterministic functions independent of database, framework, or UI dependencies. All threshold comparisons are executed on exact rational numbers (`fractions.Fraction` or exact integer math), never on pre-rounded UI strings.

Let:
- $a \in \mathbb{N}_0$: Attended periods.
- $d \in \mathbb{N}_0$: Delivered periods.
- $t \in (0, 1)$: Attendance target fraction (default $0.75$).

---

## 2. Analytical Dimensions & Mathematical Formulas

### 2.1 Course Metrics & Margins
1. **Attendance Percentage**:
   $$\text{Percentage} = 100 \times \frac{a}{d} \quad \text{for } d > 0$$
   For $d = 0$, percentage is **unknown (`None`)**, never assumed to be 0% or 100%.
2. **Safe Bunk Margin ($\text{can\_skip}$)**:
   $$\text{safe\_bunks} = \max\left(0, \left\lfloor \frac{a}{t} - d \right\rfloor\right)$$
3. **Consecutive Recovery Needed ($\text{must\_attend}$)**:
   $$\text{consecutive\_needed} = \max\left(0, \left\lceil \frac{t \cdot d - a}{1 - t} \right\rceil\right)$$
4. **Absence Contribution Percentage**:
   Measures a course's share of total semester missed periods:
   $$\text{Absence Share} = 100 \times \frac{d_i - a_i}{\sum (d_k - a_k)}$$

### 2.2 Monthly Attendance Analytics
Dated timetable observations are grouped strictly by $(year, month)$:
$$\text{Group}(y, m) = \{ \text{obs} \mid \text{obs.date.year} = y \land \text{obs.date.month} = m \}$$

- **Calendar Year Invariant**: The same month across different calendar years (e.g. October 2025 vs October 2026) remains **strictly separate**.
- **Coverage**: Marked `COMPLETE` if $\ge 10$ distinct teaching dates are observed; otherwise marked `PARTIAL`.
- **Monthly Absence Rate**:
  $$\text{Absence Rate} = 100 \times \frac{\sum_{\text{month}} (d_i - a_i)}{\sum_{\text{month}} d_i}$$

### 2.3 Weekday Absence Analytics
Grouped by weekday index $w \in \{0, \dots, 6\}$ (0 = Monday, 6 = Sunday) according to the **Asia/Kolkata** calendar timezone:
$$\text{Weekday Absence Rate}_w = 100 \times \frac{\sum_{w} (d_i - a_i)}{\sum_{w} d_i} \quad \text{for } \sum_{w} d_i > 0$$
Tracks the number of observed teaching dates for each weekday to evaluate pattern statistical significance.

### 2.4 Multi-Dimensional Subject Absence Rankings
To avoid deceptive single-metric biases, AttendPlan calculates 3 distinct subject rankings:
1. **Rank by Absolute Missed Periods**: Identifies subjects where the highest raw period count was lost.
2. **Rank by Missed Rate (%)**: Identifies subjects where the highest proportion of delivered periods was missed.
3. **Rank by Total Delivered Periods**: Identifies high-volume subjects with the greatest impact on aggregate graduation criteria.

### 2.5 Cross-Semester Career Analytics
$$\text{Semester Attendance} = 100 \times \frac{\sum_{\text{sem}} a_i}{\sum_{\text{sem}} d_i}$$
$$\text{Cumulative Career Attendance} = 100 \times \frac{\sum_{\text{all}} a_i}{\sum_{\text{all}} d_i}$$

**Core Invariant**: Never average course percentages to calculate semester attendance, and never average semester percentages to calculate career attendance.
