# AttendPlan Historical Term Reconciliation Specification

## 1. Overview & Purpose
In university ERP systems like iCloudEMS, student attendance is reported through two distinct modules:
1. **Subject-Wise Attendance**: Cumulative term totals ($a$ attended, $d$ delivered) per enrolled course.
2. **Day-Wise Attendance**: Granular daily timetable observations ($P$ present, $A$ absent, blank unreported) across specific calendar dates.

Because historical sync operations may collect day-wise records incrementally or over partial date ranges, a naive comparison would falsely flag partial records as university discrepancies.

AttendPlan implements **Term-Scoped Reconciliation** to evaluate provenance, compare delivered vs present+absent counts, and produce transparent, audit-ready verdicts.

---

## 2. Reconciliation Verdicts

| Verdict | Definition | Action Taken |
| :--- | :--- | :--- |
| `MATCHED` | Day-wise $(P + A)$ matches subject-wise delivered periods ($d$) exactly across all enrolled courses. | Full high-confidence analytics unlocked. |
| `SCOPE_MISMATCH` | Day-wise observations represent a partial calendar subset of the semester (e.g. 1 out of 5 months). Day-wise totals are less than subject totals. | System confirms scope disparity is expected. No error raised; UI displays informational notice explaining temporal boundary difference. |
| `PARTIAL_COVERAGE` | Day-wise data exists for some courses in the term but is absent for other courses. | Course-level status highlighted in audit table. |
| `SOURCE_DISCREPANCY` | Day-wise calendar coverage is ostensibly complete for the term, but total observed periods deviate unexpectedly from subject-wise delivered counts. | Discrepancy is preserved and reported as institutional data divergence; numbers are never altered to force a match. |
| `UNMAPPED_PERIODS` | Timetable cells exist for courses whose course codes or subject names cannot be resolved against the official term roster. | Unmapped periods are tallied and flagged rather than falsely attributed. |
| `NOT_AVAILABLE` | Either Subject-Wise summaries or Day-Wise observations are completely absent for this term. | Reconciliation is marked pending until both sources are imported. |

---

## 3. Reconciliation Algorithm & Mathematics

For a given academic term $T$:
1. Let $\mathcal{C}$ be the set of courses in $T$.
2. For each course $c \in \mathcal{C}$:
   - Subject summary: $a_c$ (attended), $d_c$ (delivered).
   - Day-wise observations: $p_c$ (present), $m_c$ (absent), $u_c$ (unreported).
   - Observed instructional delivery: $o_c = p_c + m_c$.
   - Course variance: $\Delta_c = d_c - o_c$.
3. Compute overall term metrics:
   $$D_{\text{subj}} = \sum_{c \in \mathcal{C}} d_c, \quad O_{\text{day}} = \sum_{c \in \mathcal{C}} o_c$$
4. **Scope Determination**:
   - If months completed < candidate months for $T$, and $0 < O_{\text{day}} < D_{\text{subj}}$, then:
     $$\text{Verdict} = \text{SCOPE\_MISMATCH}$$
   - If months completed == candidate months and $O_{\text{day}} = D_{\text{subj}}$, then:
     $$\text{Verdict} = \text{MATCHED}$$
   - If months completed == candidate months and $O_{\text{day}} \neq D_{\text{subj}}$, then:
     $$\text{Verdict} = \text{SOURCE\_DISCREPANCY}$$
   - If $O_{\text{day}} = 0$, then:
     $$\text{Verdict} = \text{NOT\_AVAILABLE}$$

---

## 4. UI Presentation & Provenance Integrity

In the frontend **Historical Attendance** and **Reconciliation** tabs:
- Each course displays:
  - Course Code & Name
  - Subject Summary ($a/d$ and rational percentage)
  - Day-Wise Observations ($P/A$ count)
  - Variance ($\Delta$)
  - Status Tag (`MATCHED`, `PARTIAL_TIMETABLE`, or `DISCREPANCY`)
- The summary banner displays the term-level verdict with a detailed narrative explaining the scope evidence.
- **Audit Rule**: AttendPlan never alters, smooths, or fakes numbers. If the university portal reports contradictory values, AttendPlan highlights the divergence for student awareness.
