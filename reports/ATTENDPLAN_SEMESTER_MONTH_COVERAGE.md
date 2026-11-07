# AttendPlan — Semester Month Coverage & Historical Scope Specification (Phase D)

**Milestone:** Phase D — Calendar-Aware Multi-Semester Historical Archive & Academic Marks Integration  
**Date:** 2026-10-29  
**Specification Owner:** Principal Software Architect & Academic Calendar Engineer  
**Database:** SQLite WAL `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`  
**Quality Status:** All 265 backend tests, 38 frontend tests (303 total automated tests) passed  

---

## 1. Executive Summary & Domain Invariants

Historically, multi-semester attendance extraction suffered from brute-force scanning: every calendar month (up to 24 months per academic year) was queried for every semester. This resulted in 107 monthly queries, of which 102 failed or returned unverified results simply because the university held no classes during summer recess (June/July), winter break (December), or outside that semester's teaching period.

Phase D establishes a **calendar-aware, bounded, deterministic academic calendar engine** (`AcademicTermCalendarService`):
1. **Semester Teaching Windows:** Odd semesters operate within Autumn sessions; even semesters operate within Spring sessions.
2. **Deterministic YearMonth Resolution:** Academic year `2025-2026` maps Semester 3 to `2025` (Autumn) and Semester 4 to `2026` (Spring). Cross-year month collisions are mathematically prevented.
3. **True Denominators:** Denominators represent actual candidate teaching months ($4$ for odd, $5$ for even), never an arbitrary 12-month calendar year.
4. **Distinction Between Processing and Coverage:** Completing the planned network requests (`IMPORT_PROCESSING_COMPLETE`) is strictly distinguished from institutional data completeness (`ACADEMIC_SOURCE_COVERAGE_COMPLETE`).
5. **Separation of Academic Marks:** Academic marks and sessional evaluations are term-scoped and evaluated independently of monthly attendance teaching windows.

---

## 2. Institutional Academic Calendar Rules

### A. Odd Semesters (Semesters 1, 3, 5, 7)
- **Session:** Autumn Academic Session
- **Target Calendar Year:** Academic Year Start Year (e.g. `2025` for `2025-2026`)
- **Default Teaching Months (4 months):**
  - August (`YYYY-08`)
  - September (`YYYY-09`)
  - October (`YYYY-10`)
  - November (`YYYY-11`)
- **Excluded Non-Teaching Months:**
  - June (`YYYY-06`): Summer recess
  - July (`YYYY-07`): Pre-term preparation / summer break
  - December (`YYYY-12`): End-semester university examinations / winter break

### B. Even Semesters (Semesters 2, 4, 6, 8)
- **Session:** Spring Academic Session
- **Target Calendar Year:** Academic Year End Year (e.g. `2026` for `2025-2026`)
- **Provisional Teaching Months (5 months):**
  - January (`YYYY-01`)
  - February (`YYYY-02`)
  - March (`YYYY-03`)
  - April (`YYYY-04`)
  - May (`YYYY-05` — candidate subject to portal calendar confirmation)
- **Excluded Non-Teaching Months:**
  - June (`YYYY-06`): Summer recess / semester transition
  - July (`YYYY-07`): Summer vacation
  - Previous Year Months (`(YYYY-1)-01` through `(YYYY-1)-12`): Strictly rejected

---

## 3. Discovered Semester Inventory & Bounded Teaching Scopes

Based on verified portal selector discovery and SQLite database inspection, the 5 registered semesters map to the following bounded scopes:

| Academic Year | Semester | Discovered Class ID | Class Label | Calendar Source | Status | Candidate Teaching Months | Max Requests |
|---|---|---|---|---|---|---|---|
| **2026–2027** | **Semester 5 (Active)** | `2582` | `B.Tech CSE AIML-Sem 5` | `VERIFIED_PORTAL_RECORDS` | `VERIFIED` | `2026-08`, `2026-09`, `2026-10` | 1 Summary + 3 Months = 4 |
| **2025–2026** | **Semester 4** | `2508` | `B.Tech CSE AIML-Sem 4` | `VERIFIED_PORTAL_RECORDS` | `VERIFIED` | `2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05` | 1 Summary + 5 Months = 6 |
| **2025–2026** | **Semester 3** | `1067` | `B.Tech CSE AIML-Sem 3` | `USER_CONFIGURED_DEFAULT` | `PROVISIONAL` | `2025-08`, `2025-09`, `2025-10`, `2025-11` | 1 Summary + 4 Months = 5 |
| **2024–2025** | **Semester 2** | `1048` | `B.Tech CSE AIML-Sem 2` | `USER_CONFIGURED_DEFAULT` | `PROVISIONAL` | `2025-01`, `2025-02`, `2025-03`, `2025-04`, `2025-05` | 1 Summary + 5 Months = 6 |
| **2024–2025** | **Semester 1** | `918` | `B.Tech CSE AIML-Sem 1` | `USER_CONFIGURED_DEFAULT` | `PROVISIONAL` | `2024-08`, `2024-09`, `2024-10`, `2024-11` | 1 Summary + 4 Months = 5 |
| **TOTAL** | **5 Semesters** | — | — | — | — | **21 Bounded Months** | **26 Requests Total** |

*Note: In contrast to the legacy 107 unconstrained request storm, the calendar engine limits all historical archive synchronization to exactly 26 total requests.*

---

## 4. Current Stored Database Baseline

Inspection of `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`:

### A. Academic Terms & Attendance Snapshots
1. **Semester 5 (2026–2027, ID `ed06cbda-...`):**
   - Active subject snapshot: `260` attended / `313` delivered (**`83.07%`**), 15 courses.
   - Day-wise period batches: August 2026 (152 obs), September 2026 (128 obs), October 2026 (136 obs).
   - Status: `CourseStatus.SAFE`.
2. **Semester 4 (2025–2026, ID `53d60f23-...`):**
   - Subject snapshot: `485` attended / `554` delivered (**`87.55%`**), 17 courses (`63ed56cc-...`).
   - Day-wise batches: 0 historical day-wise batches stored yet.
   - Status: `CourseStatus.SAFE`.
3. **Semesters 1, 2, 3:**
   - Discovered in portal selectors; no local attendance records stored yet.

### B. Stored Academic Performance Snapshots
- **Semester 4 (2025–2026):**
  - Snapshot ID: `576571fa-1f87-4b7b-8ff8-0b5cbeafb1c5`
  - Term Key: `2025-2026_s4_2508`
  - View: `marks:6424:3:A`
  - Provenance: `LIVE_PORTAL`
  - Stored Payload: 15 distinct courses with continuous internal assessments, practical evaluations, and sessional marks.
  - SGPA / CGPA: Unreported (`None`), preserved without fabrication.

---

## 5. Audit & Classification of Previous 102 Unverified Scopes

The previous archive job `281fd3ba-40fe-40db-b5ab-c3096b8deaee` attempted 107 operations, yielding 2 SUCCESS, 3 DUPLICATE_SKIPPED, and 102 UNVERIFIED. The causes have been classified:

```
Total Legacy Scopes: 107
├── SAVED_VERIFIED / DUPLICATE_SKIPPED: 5
└── UNVERIFIED (Flawed Execution): 102
    ├── WRONG_MONTH_FOR_TERM: 58 scopes
    │   └── e.g. Requesting 2026-10 for Sem 4, or 2026-05 for Sem 5
    ├── OUTSIDE_CALENDAR_WINDOW: 28 scopes
    │   └── e.g. June/July summer break months and December winter recess
    ├── NO_REPORTED_PERIODS (previously crashed by safety validator): 12 scopes
    └── WARNING_PAGE / SOURCE_UNAVAILABLE: 4 scopes
```

**Architectural Prevention in Phase D:**
1. `validate_month_in_window()` validates every YearMonth before dispatch. Out-of-window requests are assigned `OUTSIDE_CALENDAR_WINDOW` without issuing portal HTTP/CDP requests.
2. `make_plan()` constructs candidate months exclusively from the resolved teaching window.
3. Denominators count only planned teaching months ($4$ or $5$), preventing false coverage degradation.

---

## 6. Precedence Hierarchy for Calendar Resolution

When determining the candidate months for any semester, `AcademicTermCalendarService` evaluates:

```
[Level 1: USER_CONFIRMED]
    ↑ Overrides all defaults; set via "Edit Teaching Months" UI
[Level 2: OFFICIAL_ACADEMIC_CALENDAR]
    ↑ Institutional academic calendar notification / gazette
[Level 3: VERIFIED_PORTAL_RECORDS]
    ↑ Derived from date ranges in stored snapshots or observation batches
[Level 4: USER_CONFIGURED_DEFAULT]
    ↑ Odd (Aug-Nov) / Even (Jan-May) standard institutional windows
[Level 5: INFERRED_CANDIDATE]
    ↑ Provisional heuristic fallback
```

---

## 7. User-Supervised Live Historical Pilot Options

Before initiating multi-semester backfill, user approval is required for one scoped historical target:

### Recommended Pilot Target: Semester 4 (2025–2026)
- **Term Key:** `2025-2026_s4_2508`
- **Class Label:** `B.Tech CSE AIML-Sem 4`
- **Existing Coverage:** Subject summary (`485/554`, 17 courses) and internal marks (15 courses) already stored.
- **Missing Data:** Day-wise observation matrices for Spring 2026.
- **Requested Window:** Exactly 5 months (`2026-01`, `2026-02`, `2026-03`, `2026-04`, `2026-05`).
- **Safety Invariant:** Read-only access, sequential pacing (1.5s delay), zero cross-semester contamination with Semester 5.
