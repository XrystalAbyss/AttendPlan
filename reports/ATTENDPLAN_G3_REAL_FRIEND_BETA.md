# AttendPlan — Phase G.3: Real Friends Beta & Academic Parity Protocol

**Document Reference:** `ATTENDPLAN_G3_REAL_FRIEND_BETA.md`  
**Phase:** G.3 Real Friends Beta, Clean-Machine Validation & Final Release Acceptance  
**Date:** 2026-11-07  
**Distribution State:** PRIVATE SUPERVISED TESTING ONLY  
**Current Gate Status:** `AWAITING_REAL_VOLUNTEER_TESTING`  

---

## 1. Participation & Execution Policy

In accordance with project quality invariants:
- **No Synthetic Fabrication:** We never claim real volunteer beta verification without actual human student participation.
- **Current Execution Status:** During this engineering phase, independent student volunteers are not present at the developer's workstation. Therefore, the real volunteer gate is formally classified as:
  ```
  AWAITING_REAL_VOLUNTEER_TESTING
  ```
- **Distribution Boundary:** The installer (`AttendPlan-0.1.0-beta.3-Setup.exe`) must be transferred directly by the developer to designated, consenting students via private file transfer. It must never be published to a public website or GitHub Release without supervision.

---

## 2. Supervised 20-Journey Testing Protocol

When conducting beta testing sessions with 1 or 2 consenting student volunteers, each volunteer must independently execute the following 20-step journey on their personal Windows laptop:

```
[Phase 1: Installation & Launch]
 1. Download & run AttendPlan-0.1.0-beta.3-Setup.exe without admin privileges.
 2. Observe SmartScreen notice; click 'More info' -> 'Run anyway'.
 3. Complete installation into %LOCALAPPDATA%\AttendPlan\app; observe automatic browser launch.
 4. Verify landing on http://127.0.0.1:8000/ with First-Run Onboarding display.

[Phase 2: Authentication & Connection]
 5. Read first-run privacy notice (Zero Cloud Transmission guarantee).
 6. Click 'Open Student Portal in Chrome' -> Dedicated isolated Chrome window opens.
 7. Volunteer enters their student mobile number, password, and 6-digit Authenticator OTP.
 8. Volunteer confirms their student dashboard is visible in Chrome.

[Phase 3: Current Attendance Sync]
 9. Volunteer returns to AttendPlan and clicks 'Start Initial Attendance Sync'.
10. System extracts current term attendance and renders personalized dashboard.
11. Volunteer compares displayed overall percentage against university ERP.
12. Volunteer compares individual course attended/delivered periods.

[Phase 4: Planning & Intelligence]
13. Volunteer inspects 'Safe to Miss' bunk margins and 'Classes Needed' recovery metrics.
14. Volunteer opens the 'What-If Attendance Simulator' for an at-risk course.
15. Volunteer opens the 'Attendance Explorer' and verifies period-by-period class history.
16. Volunteer tests semester navigation dropdown to inspect past completed semesters.

[Phase 5: Performance & Diagnostics]
17. Volunteer navigates to 'Performance' tab and observes unreleased marks status without error.
18. Volunteer navigates to 'Settings' and clicks 'Export Offline Backup' (verifies .sqlite3 created).
19. Volunteer clicks 'Disconnect Browser' (verifies dedicated Chrome closes cleanly).
20. Volunteer closes browser and terminal, reopens AttendPlan from Start Menu, and confirms instant cached load.
```

---

## 3. Academic Parity Verification Checklist

For each consenting volunteer, the developer guides them to verify mathematical parity between AttendPlan and their official university portal:

| Verification Item | Invariant Rule | Volunteer Verification Method |
| :--- | :--- | :--- |
| **Course Codes & Component Types** | Theory vs Lab (P/L) distinction must be accurate | Student visually checks course cards against ERP timetable |
| **Delivered / Attended Counts** | $0 \le a \le d$; unrecorded classes must be `--`, never 0% | Student checks periods against ERP subject-wise table |
| **Standard Percentage** | $\text{Percentage} = 100 \times \frac{a}{d}$ on exact rationals | Student compares AttendPlan calculation to official percentage |
| **Safe Bunk Margin** | $\lfloor a/0.75 - d \rfloor$ (zero-buffer subjects marked Caution) | Student verifies bunk count matches manual formula |
| **Consecutive Recovery Needed** | $\lceil (0.75d - a)/0.25 \rceil$ for courses below 75% | Student verifies classes needed matches manual formula |
| **Aggregate Percentage** | $\frac{\sum a_i}{\sum d_i}$, never the average of percentages | Student confirms overall percentage matches ERP aggregate |

---

## 4. Privacy & Consent Protocol

1. **Zero Credential Sharing:** The developer must **never** ask for, receive, or view the student's password, OTP, Authenticator secret, or cookies.
2. **Local Screen Verification:** The volunteer performs all verification directly on their own screen.
3. **Voluntary Issue Logging:** If an issue or calculation discrepancy arises, the student reports only sanitized field descriptions (e.g. *"Course CSE101 shows 14/18 periods on ERP but 12/16 in AttendPlan"*). Raw HTML portal dumps containing student names or roll numbers must **never** be collected.

