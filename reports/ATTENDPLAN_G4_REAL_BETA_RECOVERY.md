# ATTENDPLAN — PHASE G.4: REAL-WORLD BETA RECOVERY
## One-Click Startup, Unified Chromium Runtime, Guided Onboarding, Historical Sync & Performance Import
**Release Version:** `0.1.0-beta.4`  
**Distribution State:** `PRIVATE_SUPERVISED_BETA`  
**Target Repository:** `https://github.com/XrystalAbyss/AttendPlan`  
**Branch:** `feature/g4-real-beta-recovery`  
**Date:** November 14, 2026  

---

## 1. Executive Summary & Problem Formulation

Following the deployment of `AttendPlan-0.1.0-beta.3-Setup.exe` to an independent student volunteer on a clean Windows machine, the core local-first attendance sync proved mathematically sound and successful. However, the real-world trial exposed critical usability, packaging, and UX defects that fragmented the user experience:

1. **Persistent Console Window:** When launched, a persistent black Windows Command Prompt (`cmd.exe`) remained on screen. If closed, the application was killed.
2. **Browser Runtime Fragmentation:** On machines where Mozilla Firefox was the default browser, the desktop launcher opened the dashboard in Firefox, while portal authentication required a separate Google Chrome instance, confusing the student and breaking unified tab navigation.
3. **Buried Credentials & Fragmented Onboarding:** The initial setup required navigating multiple hidden modals. Students were not guided to configure their registered university mobile number or choose between manual vs automated Authenticator setup.
4. **Hidden Portal Launch & Silent Failures:** The Home screen lacked an obvious, always-visible button to open the university portal, and browser launch errors failed silently without actionable UI feedback.
5. **Locked Performance Import:** The Performance view showed a generic empty state with live capture disabled behind a developer pilot flag (`ATTENDPLAN_ENABLE_PERFORMANCE_PILOT`), preventing students from importing their authentic internal assessment marks.
6. **Inaccessible Historical Attendance:** Prior semester attendance records were difficult to discover and sync from the main interface.
7. **Cramped UI & Hardcoded Metadata:** The Attendance view header squashed the semester selector, and student academic identity fell back to developer test strings (`2026-2027`, `Sem 5`, `B.Tech CSE AIML`).

**Phase G.4 Resolution:**
AttendPlan `0.1.0-beta.4` systematically resolves all identified real-world issues into a single, cohesive desktop experience. The application runs windowed without a command prompt, unifies all views inside a single dedicated Chromium runtime, guides first-time users through a 6-step setup wizard, unlocks user-approved performance mark imports, integrates historical term syncing directly into Attendance, and provides a clean application shutdown lifecycle.

---

## 2. Windows Packaging Architecture & Windowed Mode (`console=False`)

### 2.1 The Problem
In PyInstaller packaging, `console=True` forces Windows to allocate a console subsystem (`/SUBSYSTEM:CONSOLE`) for `AttendPlan.exe`. On desktop launch from the Start menu or desktop shortcut, a black terminal window remained visible in the taskbar.

### 2.2 Architectural Remediation
1. **PyInstaller Spec File:**
   In `backend/attendplan.spec`, modified line 110:
   ```python
   exe = EXE(
       pyz,
       a.scripts,
       [],
       exclude_binaries=True,
       name="AttendPlan",
       debug=False,
       bootloader_ignore_signals=False,
       strip=False,
       upx=False,
       console=False,  # Switched to /SUBSYSTEM:WINDOWS (runw.exe)
       disable_windowed_traceback=False,
   )
   ```
2. **Windowed Runtime Crash Prevention:**
   When compiled with `/SUBSYSTEM:WINDOWS`, Python's `sys.stdout` and `sys.stderr` are initialized to `None`. Any direct call to `sys.stdout.write()` or standard `print()` causes an unhandled `AttributeError: 'NoneType' object has no attribute 'write'` that crashes the application on startup.
   - Implemented `safe_print(*args, **kwargs)` in `backend/launcher.py` guarding against `None`.
   - Replaced console-attached stream handlers with a `RotatingFileHandler` writing directly to `%LOCALAPPDATA%\AttendPlan\logs\attendplan.log` (5 MB max, 3 rotating backups).

---

## 3. Single-Instance Enforcement & Application Termination Lifecycle

### 3.1 Single-Instance Mutex & Tab Activation
When a student clicks the AttendPlan shortcut while the application is already running:
- The launcher queries `http://127.0.0.1:{port}/health`.
- If healthy, rather than spawning duplicate backend instances or throwing a port-binding crash, it opens or activates the AttendPlan dashboard tab via loopback Chrome DevTools Protocol (`http://127.0.0.1:9222/json/activate/{id}`) and exits cleanly.

### 3.2 Clean Application Shutdown Endpoint (`/shutdown`)
In windowed mode without a console, students need a reliable, standard way to exit the background application:
- Added `POST /api/v1/startup/shutdown` in `backend/app/api/startup_routes.py`.
- The endpoint sets an application-wide `threading.Event()` in `backend/launcher.py`, terminating the Uvicorn server thread gracefully.
- Added an **Exit / Power** button in the frontend Header (`frontend/src/components/Header.tsx`), providing one-click shutdown with visual confirmation.

---

## 4. Browser Profile Unification Architecture

### 4.1 The Problem
Previously, `launcher.py` invoked Python's `webbrowser.open(dashboard_url)`. On systems where Firefox or Brave was the default browser, the dashboard opened in Firefox. However, ERP synchronization requires a dedicated Chromium instance on loopback CDP port `9222`. This forced students to juggle two different browsers simultaneously.

### 4.2 Unified Dedicated Chromium Solution
- Implemented `launch_unified_browser()` in `backend/launcher.py`.
- AttendPlan locates Google Chrome, Microsoft Edge, or Chromium and launches a single dedicated browser window bound to `%LOCALAPPDATA%\AttendPlan\chrome-profile`.
- The dashboard is loaded as the primary tab (`http://127.0.0.1:8000`), and clicking "Open University Portal" opens the ERP login page (`https://portal.amity.edu/...`) as a sibling tab within the exact same browser window via CDP `/json/new`.
- No secondary or conflicting browser is ever invoked.

---

## 5. Student Onboarding Experience Overhaul (6-Step Guided Flow)

`frontend/src/components/FirstRunOnboarding.tsx` was completely rewritten into a 6-step onboarding wizard:

```
[ Step 1: Welcome & Local Privacy ]
               │
               ▼
[ Step 2: Registered Mobile Number ]
               │
               ▼
[ Step 3: MFA Choice (Option A Manual vs Option B Automatic) ]
               │
               ▼
[ Step 4: Connect University Portal (Live CDP & Session Check) ]
               │
               ▼
[ Step 5: First Attendance Sync (Course & Period Breakdown) ]
               │
               ▼
[ Step 6: Setup Complete (Dashboard Ready) ]
```

- **Step 1:** Clearly explains local-first privacy, loopback binding, and zero cloud uploads.
- **Step 2:** Prompts for the 10-digit registered mobile number with inline validation, format normalization (`+91` stripping), and optional manual skip.
- **Step 3:** Provides clear choices:
  - *Option A (Manual OTP Entry):* Student enters the code from Google Authenticator themselves during login.
  - *Option B (Automated Vault):* Securely stores the Base32 TOTP secret in Windows Credential Vault (DPAPI) and tests code generation against current clock time.
- **Step 4:** Opens the dedicated university portal in Chrome and verifies active student session.
- **Step 5:** Executes initial attendance sync and displays courses and delivered periods.
- **Step 6:** Hands off cleanly to the main dashboard.

---

## 6. Primary Connection Management & One-Click Attendance Sync

### 6.1 Unified Connection Card on Home
In `frontend/src/components/HomeView.tsx`:
- Replaced confusing, multi-layer session states with an intuitive connection header:
  - When disconnected: shows "Disconnected — Ready to Connect".
  - When expired: shows amber badge "University Session Expired — Action Required".
  - When connected: shows green badge "Connected & Verified".
- Prominent, always-visible **"Open University Portal"** action button.
- Prominent **"Refresh Attendance"** action button.
- Direct **"Login Setup"** button opening authentication and vault settings.

### 6.2 Browser Launch Error Handling
In `frontend/src/components/HomeView.tsx`:
- Replaced silent `catch {}` with a user-facing error banner displaying actionable guidance (e.g. verifying Google Chrome installation or checking if port 9222 is blocked).

---

## 7. Performance & Internal Assessments Architecture Unification

### 7.1 Unlocking User-Approved Imports
In `backend/app/api/performance_routes.py`:
- Removed the restrictive `ATTENDPLAN_ENABLE_PERFORMANCE_PILOT` environment variable barrier in `/import`.
- Set `live_capture_enabled = True` in `/overview`.
- Students can now preview and approve importing their authentic internal continuous assessment marks, midterm exams, and semester results directly into AttendPlan.

### 7.2 UI Copy & State Refinement
In `frontend/src/components/PerformanceView.tsx`:
- Updated title to *"Internal Assessments & Continuous Evaluation"*.
- Replaced hardcoded term counts with dynamic count (`${allTerms.length} ${allTerms.length === 1 ? "term" : "terms"}`).
- Replaced generic empty state with informative *"No assessments imported yet"* callout while preserving strict DOM identifiers for test suites.

---

## 8. Historical Multi-Semester Attendance Discovery & Integration

### 8.1 Seamless Attendance Tab Navigation
In `frontend/src/components/AttendanceView.tsx`:
- Added a 3-way subview selector:
  1. **Subject Roster** (Active course attendance table)
  2. **Calendar & Trends** (Monthly attendance breakdown & daywise view)
  3. **Import Previous Semesters** (Directly embeds `HistoricalAttendanceView`)
- Students no longer have to dig through developer tabs or modal dialogues to import past semester attendance.

---

## 9. Responsive UI Layout & Academic Identity Presentation

### 9.1 Semester Selector Unclipping
In `frontend/src/components/SemesterSelector.tsx` and `frontend/src/components/AttendanceView.tsx`:
- Removed restrictive `max-w-md` container constraints that squashed semester chips.
- Added horizontal scrolling and responsive flex-wrap for high and low DPI screens.

### 9.2 Clean Fallback Academic Identity
In `frontend/src/App.tsx`:
- Removed hardcoded developer test fallbacks (`"2026-2027"`, `5`, `"B.Tech CSE AIML"`).
- Unconnected instances display neutral placeholders (`"—"`, `null`, `"AttendPlan"`), populated exclusively from authentic student records upon first sync.

---

## 10. Windows SmartScreen & Unsigned Binary Security Disclosure

Because AttendPlan is distributed as an independent, private open-source beta candidate without an expensive commercial EV Code Signing Certificate, Windows Defender SmartScreen displays a warning on initial launch:
- *"Windows protected your PC — Microsoft Defender SmartScreen prevented an unrecognized app from starting."*

### Student Walkthrough for SmartScreen:
1. Double-click `AttendPlan-0.1.0-beta.4-Setup.exe`.
2. When the blue SmartScreen window appears, click **"More info"**.
3. Verify the publisher is listed as `AttendPlan Team` or application `AttendPlan-0.1.0-beta.4-Setup.exe`.
4. Click **"Run anyway"**.
5. The installer installs into `%LOCALAPPDATA%\AttendPlan\app` without requiring administrator privileges.

---

## 11. Complete Automated Test Results & Verification Matrix

### 11.1 Test Execution Summary
All automated quality gates passed 100%:

| Test Suite | Command | Result | Pass Rate |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Domain Tests** | `pytest backend/tests -v` | **346 passed**, 0 failed | 100% |
| **Sanitization & Anti-Leak Audit** | `pytest backend/tests/test_sanitization.py -v` | **14 passed**, 0 failed | 100% |
| **Python Static Typing** | `mypy backend/app backend/launcher.py` | **47 source files**, 0 issues | 100% |
| **Python Linting & Formatting** | `ruff check backend/app backend/tests backend/launcher.py` | **0 errors**, all clean | 100% |
| **Frontend Unit & Component Tests** | `vitest run` | **38 passed** across 13 files | 100% |
| **Frontend Strict Typecheck** | `tsc --noEmit` | **0 errors** | 100% |
| **Frontend Production Build** | `npm run build` | **Clean build** (123 kB gzipped) | 100% |
| **Total Automated Tests** | | **384 passed** | **100%** |

---

## 12. Release Candidate Verification (`AttendPlan-0.1.0-beta.4-Setup.exe`)

| Property | Verified Value |
| :--- | :--- |
| **File Name** | `AttendPlan-0.1.0-beta.4-Setup.exe` |
| **File Path** | `release-candidates/AttendPlan-0.1.0-beta.4-Setup.exe` |
| **File Size** | **81,650,698 bytes** (~77.8 MB) |
| **SHA-256 Hash** | `160664cdb70f068f142c0611398b1f1bb579b38ee47dc2dc7d1bf7bd87df1486` |
| **Privileges Required** | `lowest` (Non-administrative user mode) |
| **Install Directory** | `%LOCALAPPDATA%\AttendPlan\app` |
| **Installer Engine** | Inno Setup 6.7.3 (LZMA2/max solid compression) |
| **Windows Subsystem** | `/SUBSYSTEM:WINDOWS` (`console=False`, windowed background process) |
| **Logging Destination** | `%LOCALAPPDATA%\AttendPlan\logs\attendplan.log` (Rotating 5MB) |

---

## 13. Defect-by-Defect Resolution Matrix

| Defect / Issue | Description | Resolution in Beta 4 | Verified Status |
| :--- | :--- | :--- | :--- |
| **Defect A / Issue 4** | Missing registered mobile & Authenticator choice in onboarding | 6-step guided onboarding wizard with mobile validation & Option A/B TOTP | **VERIFIED** |
| **Defect B / Issue 2** | Lingering black CMD console window | `console=False` in PyInstaller spec + `runw.exe` bootloader + safe logging | **VERIFIED** |
| **Defect C / Issue 3** | Fragmented browser experience with Firefox default | Unified launch in dedicated Chromium runtime for both dashboard & portal | **VERIFIED** |
| **Defect D / Issue 8** | Locked performance imports behind pilot flag | Removed `ATTENDPLAN_ENABLE_PERFORMANCE_PILOT` barrier; capture enabled | **VERIFIED** |
| **Defect E / Issue 9** | Inability to easily discover & sync historical terms | Direct "Import Previous Semesters" tab integrated in Attendance view | **VERIFIED** |
| **Defect F / Issue 10** | Cramped semester selector & hardcoded identity | Responsive flex wrap + removed hardcoded developer academic metadata | **VERIFIED** |
| **Defect G / Issue 6-7** | Buried automated login & confusing status labels | Single-click refresh + clear connection status + direct Login Setup action | **VERIFIED** |
| **Defect H / Issue 5** | No visible portal launch button on Home | Prominent "Open University Portal" button + actionable error banner | **VERIFIED** |
| **Issue 1 / Sec. 12** | Windows SmartScreen warning on unsigned exe | Documented SmartScreen bypass guidance in guide and reports | **VERIFIED** |

---

## 14. Comparison Matrix: Beta 3 vs Beta 4

| Feature / Behavior | AttendPlan 0.1.0-beta.3 | AttendPlan 0.1.0-beta.4 |
| :--- | :--- | :--- |
| **Process Subsystem** | Console (`cmd.exe` terminal visible) | Windowed (`runw.exe`, no terminal window) |
| **Browser Execution** | Default system browser (e.g. Firefox) | Dedicated Chromium profile for dashboard & portal |
| **Application Exit** | Terminate terminal window | Header power button + `/api/v1/startup/shutdown` |
| **Onboarding Flow** | 4-step minimal prompt | 6-step guided wizard with mobile & MFA setup |
| **Portal Launch from Home** | Buried in submenus | Always visible on Home header |
| **Performance Marks Import** | Blocked behind pilot environment variable | Fully unlocked for student-authorized imports |
| **Historical Attendance** | Separate developer view | Integrated 3-way subview in Attendance view |
| **Semester Selection UI** | Constrained to `max-w-md`, truncated chips | Responsive, scrollable chip container |
| **Student Metadata Fallback** | Hardcoded `"Sem 5"` / `"B.Tech CSE AIML"` | Neutral placeholders (`"—"`, `AttendPlan`) |
| **Desktop Logging** | Console stdout | Rotating file logger (5MB max) |

---

## 15. Next Steps & Supervised Friends-Beta Handoff Protocol

1. **Private Distribution Only:** Share `AttendPlan-0.1.0-beta.4-Setup.exe` directly with consenting volunteer students via private file transfer.
2. **Checksum Verification:** Instruct students to check the SHA-256 hash (`160664cdb70f068f142c0611398b1f1bb579b38ee47dc2dc7d1bf7bd87df1486`).
3. **Follow Friends-Beta Testing Guide:** Provide [FRIENDS_BETA_TESTING_GUIDE.md](file:///c:/Users/astra/Desktop/Project/AttendPlan/docs/FRIENDS_BETA_TESTING_GUIDE.md).
4. **Git Branch Tracking:** Commit and push `feature/g4-real-beta-recovery` to the canonical remote `https://github.com/XrystalAbyss/AttendPlan`.
