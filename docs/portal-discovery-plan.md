# AttendPlan F2-A Portal Discovery Specification & Exploration Findings

## 1. Scope, Purpose & Non-Negotiable Boundaries
This document details the discovered structure, authentication workflow, and verified findings for **iCloudEMS (CoreCampus)** student attendance synchronization in **Foundation 2 (F2-A)**.

### Non-Negotiable Operational Boundaries:
1. **Zero Credential or Session Persistence**:
   - The user must perform student portal login and MFA (Google Authenticator) manually in their own browser session.
   - Never store, prompt for, log, or persist OTP codes, TOTP seeds, passwords, session tokens, or browser cookies.
2. **Authorized Student Interfaces Only**:
   - Interact solely through authorized student-facing interfaces.
   - Never bypass anti-debugging, access controls, rate limits, or university security headers.
   - Stop immediately if authentication or authorization is denied.
3. **Dedicated Chrome Profile & Loopback Binding**:
   - Dedicated profile stored strictly outside the repository under the user's local application data directory (`%LOCALAPPDATA%\AttendPlan\chrome-profile`).
   - Chrome DevTools Protocol (CDP) binds strictly to loopback `127.0.0.1:9222`.
   - Never expose debug endpoints to the local network or connect to unrelated tabs.
4. **No Bulk Extraction in F2-A**:
   - F2-A is strictly limited to accuracy corrections and read-only schema/view discovery. Bulk historical multi-semester extraction is deferred to F2-B.

---

## 2. Authentication Workflow & Session Lifecycle

### User Authentication Journey:
1. **Portal Entrypoint**: `https://mrei.icloudems.com/corecampus/index.php`
2. **Keycloak Redirection**: User clicks "Keycloak Student Login" and is routed to the university identity provider (`auth.mrei.ac.in`).
3. **Primary Authentication**: User enters registered mobile number / institutional email and password.
4. **Multi-Factor Challenge (MFA)**: User enters their one-time passcode from Google Authenticator.
   - **AttendPlan Policy**: Automated filling or interception of MFA is strictly forbidden. The student completes this manually.
5. **Dashboard Landing**: Upon successful validation, Keycloak issues a session cookie and redirects the browser to `https://mrei.icloudems.com/corecampus/student_dashboard.php`.

### Session Liveness & State Machine:
```
+---------------+     Launch     +---------------+      Redirect      +----------------+
| DISCONNECTED  | -------------> | BROWSER_READY | -----------------> | LOGIN_REQUIRED |
+---------------+                +---------------+                    +----------------+
        ^                                                                      |
        |                                                                      | User Authenticates
        |                                                                      v (Manual Keycloak + MFA)
+---------------+      Session   +---------------+     Scan Views     +----------------+
|  TERMINATED   | <------------- |SESSION_EXPIRED| <----------------- | AUTHENTICATED  |
+---------------+       Timeout  +---------------+      (No Session)  +----------------+
                                                                               |
                                                                               | Read-only Discovery
                                                                               v
                                                                      +----------------+
                                                                      |DISCOVERY_COMPL |
                                                                      +----------------+
```

| State | Portal URL / DOM Evidence | Expected System Action |
| :--- | :--- | :--- |
| `DISCONNECTED` | Port 9222 not reachable. | Show "Launch Dedicated Chrome" button. |
| `BROWSER_READY` | Chrome launched, URL is loading or blank. | Wait for initial navigation to university portal. |
| `LOGIN_REQUIRED` | URL contains `keycloak`, `login`, or `index.php`. | Prompt user to complete login + Google Authenticator. |
| `AUTHENTICATED` | URL contains `student_dashboard.php` or student nav. | Enable discovery buttons; allow read-only scan. |
| `DISCOVERING` | Active adapter scanning DOM over CDP. | Display non-blocking discovery spinner. |
| `DISCOVERY_COMPLETE` | Adapter extracted schema and view statistics. | Display verified findings cards. |
| `SESSION_EXPIRED` | Redirected back to login or session timed out. | Indicate session expired; request manual re-login. |
| `ERROR` | Chrome executable missing or CDP port conflict. | Display diagnostic details; suggest manual HTML upload. |
| `MANUAL_IMPORT_AVAILABLE` | Offline fallback active. | Allow HTML file upload or raw HTML text paste. |

---

## 3. Discovered University Portal Views & Structural Evidence

### 3.1 Discovery Area 1 — Subject-Wise Attendance (`subwise_attendace_new.php`)
- **Navigation URL**: `/corecampus/student/attendance/subwise_attendace_new.php`
- **Selector Types & Controls**:
  - Academic Year: `<select name="aca" id="aca">`
  - Semester: `<select name="sem" id="sem">`
  - Class: `<select name="class" id="class">`
  - Search Trigger: Button `<button id="getattendance" type="submit">` or `#search`
- **Table Structure**:
  - Found under standard `.table` or `.table-bordered` class.
  - Columns observed: `S.No.`, `Course Title`, `Course Short Name`, `Course Code`, `Faculty Name`, `Credits`, `Attended/Delivered`, `Percentage`.
  - Attended/Delivered cell format: `17 / 19` (plain integer fraction separated by `/`).
- **Reporting Date Boundaries**: Typically embedded in page header subtitles (e.g. `04/08/2026 to 27/11/2026`).
- **Discovery Evidence Classification**: `VERIFIED OFFLINE` (via genuine portal DOM capture `att.html` and sanitized fixture).

### 3.2 Discovery Area 2 — Day-Wise Attendance Grid (`myattendance.php`)
- **Navigation URL**: `/corecampus/student/attendance/myattendance.php`
- **Form Controls**:
  - Academic Year: `<select name="acadyear" id="acadyear">`
  - Semester: `<select name="semNum[]" id="semNum">` (Multi-select array)
  - Class: `<select name="classid[]" id="classid">`
  - Month: `<select name="month" id="month">`
  - Date Range Inputs: `<input name="from_date" id="from_date">`, `<input name="to_date" id="to_date">`
  - Show Course Name Toggle: `<input type="checkbox" name="show_course_name" id="show_course_name">`
- **Timetable Matrix Layout**:
  - **Rows**: Explicit 50-minute timed lecture slots:
    `08:10–09:00`, `09:00–09:50`, `09:50–10:40`, `10:40–11:30`, `12:20–13:10`, `13:10–14:00`, `14:00–14:50`, `14:50–15:40`.
  - **Columns**: Calendar dates in `DD/MM/YYYY (Day)` format.
  - **Horizontal Overflow**: Rendered within a `.table-responsive` horizontal scrolling container.
- **Cell Status Indicators**:
  - `P` (Present): `<span class="text-success">P</span>`
  - `A` (Absent): `<span class="text-danger">A</span>`
  - Blank (`<td></td>`): Unscheduled slot or holiday. **Crucial Invariant**: Must be evaluated as `NOT_REPORTED` ($d=0, a=0$), never as an absence.
  - Explicit Cancellation: Cells containing text `Holiday`, `No Class`, `Cancelled` evaluate as `NO_CLASS` ($d=0, a=0$).
- **Course Name Attribution**:
  - When "Show Course Name" is active, course codes appear inline below the status badge: `<span class="text-success">P</span><br><small>CSH301C</small>`.
  - Practical laboratories spanning two consecutive 50-minute rows count as **1 period per row cell** (total 2 periods), eliminating the historical double-counting bug. Multipliers $>1$ apply strictly when an explicit portal marker (`[LAB 2P]`) is present in the markup.
- **Discovery Evidence Classification**: `VERIFIED OFFLINE` (via synthetic daywise fixture and DOM reverse engineering).

### 3.3 Discovery Area 3 — Overall Attendance (`allSubject.php`)
- **Navigation URL**: `/corecampus/student/attendance/allSubject.php`
- **Semantic Purpose**: Aggregate macroscopic view across all enrolled subjects.
- **Controls & Output**:
  - Semester dropdown filter.
  - Table displaying S.No, Course Code, Subject, Attended, Delivered, and aggregate percentage.
  - Macro Total row in table footer (`tfoot`).
- **Reconciliation Invariant**: The macro percentage reported by `allSubject.php` must be cross-checked against $\frac{\sum a_i}{\sum d_i}$ from subject-wise snapshots. If date scopes differ, status is flagged as `SCOPE_MISMATCH`.
- **Discovery Evidence Classification**: `VERIFIED OFFLINE` (via synthetic fixture and reverse engineering).

### 3.4 Discovery Area 4 — Historical Semesters
- **Academic Year Enumeration**: Accessible academic years (e.g. `2024-2025`, `2025-2026`, `2026-2027`) populate dynamically in `<select name="aca">`.
- **Semester Numeric Options**: Dependent on academic year; historically completed semesters remain accessible.
- **Milestone Boundary**: In F2-A, semester discovery is read-only inspection of available options. Bulk extraction across all historical combinations is deferred to F2-B.
- **Discovery Evidence Classification**: `INFERRED & VERIFIED OFFLINE`.

---

## 4. Manual HTML Fallback Guidance
If university anti-tamper shields prevent CDP connection or headless automation, AttendPlan provides a complete, supported manual fallback:
1. Open Google Chrome normally and log into `https://mrei.icloudems.com/corecampus/`.
2. Navigate to **Subject Wise Attendance** (`subwise_attendace_new.php`) or **Day Wise Attendance** (`myattendance.php`).
3. Press `Ctrl + S` to save the webpage as "Webpage, HTML Only" (`.html`).
4. In AttendPlan, switch to the **Portal Discovery** tab and click **Use Manual HTML Fallback**.
5. Paste the HTML or upload the file.
6. The system ingests and reconciles the records with 100% mathematical fidelity.

---

## 5. F2-B Synchronization Implementation Plan
Once live student session verification is confirmed with user participation:
1. **Incremental Snapshot Synchronization**: Query `subwise_attendace_new.php` for the active term and store an immutable snapshot with canonical checksum.
2. **Date-Window Day-Wise Fetch**: Iterate over months of the current semester, submitting form queries for `from_date` and `to_date` with `Show Course Name` checked.
3. **Automated Reconciliation**: Link day-wise period observations to catalog courses and compare date windows.
4. **Historical Term Archival**: Provide user-guided one-click archival of prior completed semesters.
