# AttendPlan — Phase F.1 Product Stabilization Report
**Milestone:** Phase F.1 — Product Stabilization, UX Simplification & Friends-Beta Foundation  
**Date:** November 7, 2026  
**Status:** COMPLETE & VERIFIED  
**Agent:** Google Antigravity Flash 3.8  

---

## 1. Executive Summary & Product Direction Pivot

Following supervised execution in Phase E.7, the university's official **My Report Card** portal route was determined to be disabled by institutional administrative control (`WITHHELD by COE Office`). Concurrently, user guidance clarified the definitive product scope:

> **AttendPlan is NOT a university grade-card or transcript management system.**  
> Official examination result cards, letter grades, external marks scraping, and GPA calculations are de-prioritized.  
> AttendPlan's primary mission is **daily attendance intelligence, 75% margin tracking, skippable class calculations, and continuous internal evaluation marks**.

Phase F.1 transitions AttendPlan from an experimental engineering exploration harness into a streamlined, high-speed, institutional-grade product designed for regular, non-technical university students.

---

## 2. Core Architectural & UX Changes

### 2.1 Information Architecture Simplification (7 Tabs $\to$ 4 Primary Views)
Previously, the application exposed 7 sprawling views filled with developer debugging tools (`Current`, `Historical`, `Absences`, `Marks & Results`, `Analytics`, `Reconciliation`, `Settings`). 

This has been consolidated into **4 clear, student-centric primary destinations**:

1. **HOME (`HomeView`)**:
   - **Hero Attendance KPI**: High-impact display of current semester attendance %, progress meter relative to the mandatory 75% threshold, and standing status badge (`In Good Standing` / `Attention Required`).
   - **One-Click Quick Refresh**: Prominent top status bar with live spinning sync indicator and clear human status ("Attendance up to date", "Last updated Today at 3:45 PM").
   - **Skippable Classes & Margin Summary**: Instant visibility into safe bunks available without dropping below 75%, or consecutive classes needed to recover.
   - **Subjects Requiring Attention**: High-priority alert card detailing courses at or near the 75% danger zone with a direct "Plan Attendance" shortcut.

2. **ATTENDANCE (`AttendanceView`)**:
   - Seamlessly houses all attendance planning and analytics in one place.
   - Semester dropdown selector spanning all 5 locally stored semesters (Semesters 1 through 5).
   - Clean sub-view segmented control:
     - **Subject Roster & Planner**: Interactive roster table with real-time what-if simulations, exact rational margins, and lab period multipliers.
     - **Date-wise Calendar & Trends**: Integrated historical calendar view (`AbsenceExplorer`) and multi-dimensional monthly/day-of-week trends (`AbsenceAnalyticsView`).

3. **PERFORMANCE (`PerformanceView`)**:
   - Cleaned of developer-only manual approval forms, test payload buttons, and raw JSON dump controls (tucked safely into an advanced collapsed `<details>` disclosure).
   - Removed alarming "WITHHELD" alerts; replaced with a calm informational notice: *"University report card portal route is currently deactivated by COE Office."*
   - Clear semester filter pills (`All Semesters`, `Sem 1`, `Sem 2`, `Sem 3`, `Sem 4`, `Sem 5`).
   - Clean assessment drawers displaying Continuous Evaluation (CE) and Midterm marks directly from the source.
   - Transparent publication notices for Semester 5 indicating continuous evaluation is still in progress (4 subjects reported).

4. **SETTINGS (`SettingsView`)**:
   - University Portal connection credentials and masked mobile number configuration (`******9940`).
   - Automation preferences: automatic mobile number autofill, login continuation, and TOTP autofill toggles.
   - Dedicated Chrome profile launch and diagnostic tools.
   - Custom threshold selector (default 75%).
   - Local storage diagnostics and database backup details (`%LOCALAPPDATA%\AttendPlan`).

### 2.2 First-Run Onboarding Flow (`FirstRunOnboarding`)
For new student users opening AttendPlan for the first time with an empty database:
- A guided 4-step setup wizard introduces AttendPlan's local-first privacy model.
- Automatically verifies local Python/FastAPI backend health and Chrome CDP connectivity.
- Guides the student through their first portal sign-in.
- Performs the initial current-term discovery and sync with a single click, transitioning immediately into the dashboard upon completion.

---

## 3. Data Integrity & Preservation Invariants

| Term Key | Academic Year | Semester | Attendance Courses | Attendance Obs | Marks Courses | Marks Cells | Official Result Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `2024-2025_s1_918` | 2024–2025 | 1 | 12 | 682 | 11 | 66 | Not pursued (deactivated) |
| `2024-2025_s2_1048` | 2024–2025 | 2 | 16 | 772 | 12 | 108 | Not pursued (deactivated) |
| `2025-2026_s3_1067` | 2025–2026 | 3 | 16 | 948 | 13 | 117 | Not pursued (deactivated) |
| `2025-2026_s4_2508` | 2025–2026 | 4 | 17 | 1,003 | 15 | 165 | WITHHELD (archived) |
| `2026-2027_s5_2582` | 2026–2027 | 5 | 15 | 139 | 4 | 12 | In Progress (CE only) |
| **Total Archive** | **5 Semesters** | **All 5** | **76 courses** | **3,544 obs** | **55 courses** | **468 cells** | **100% Preserved** |

- **Pre-F.1 WAL-Safe Backup**: Created at `C:\Users\astra\AppData\Local\AttendPlan\backups\attendplan_pre_phase_f1_backup_20261107_153720.sqlite3` (1,998,848 bytes).
- **Zero Data Loss**: 100% of historical records, observations, and assessment cells verified intact across all 5 terms.
- **Strictly Offline**: 0 ERP network calls issued during migration, refactoring, and testing.

---

## 4. Verification & Quality Gates Summary

- **Backend Pytest Suite**: **327 passed, 0 failed** in 19.92 seconds.
- **Frontend Vitest Suite**: **38 passed, 0 failed** across 13 test files.
- **Python Typing (Mypy)**: **Success** — 0 issues across 46 source files.
- **Python Linting (Ruff)**: **All checks passed** (0 errors).
- **TypeScript & Vite Build**: **Clean build in 7.99s** (`dist/assets/index-DsH8SqIo.js` 406.14 kB).
- **Windows Human Acceptance Suite**: **24 passed, 0 failed** (0 ERP calls, 0 console errors).

