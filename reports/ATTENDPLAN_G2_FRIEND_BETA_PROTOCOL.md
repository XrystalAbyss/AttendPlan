# AttendPlan — Supervised Friends Beta Protocol & Volunteer Guide

**Document Reference:** `ATTENDPLAN_G2_FRIEND_BETA_PROTOCOL.md`  
**Phase:** G.2 Supervised Friends Beta & Release Hardening  
**Target Release:** `AttendPlan-0.1.0-beta.2-Setup.exe`  
**Distribution State:** PRIVATE, SUPERVISED VOLUNTEER PARTICIPATION ONLY  

---

## 1. Welcome to the AttendPlan Friends Beta

Thank you for agreeing to test AttendPlan! AttendPlan is a 100% private, local-first attendance intelligence tool built specifically for students under university attendance regulations (75% threshold).

### What AttendPlan Does:
- **Tracks Attendance:** Computes your exact percentage, bunk margin (how many periods you can safely miss), and consecutive recovery classes needed.
- **Never Guesses or Fabricates:** Zero classes delivered ($0/0$) is treated as unrecorded, never 100% or 0%.
- **100% Private & Local:** Runs entirely on your personal machine (`127.0.0.1`). Your login credentials, session cookies, and attendance records are never sent to any external server or cloud.

---

## 2. Beta Testing Prerequisites

Before beginning the installation, ensure you have:
1. A 64-bit Windows laptop (Windows 10 or Windows 11).
2. Google Chrome installed in standard locations.
3. Your university iCloudEMS student portal login and Authenticator app (e.g. Google Authenticator) for your 2FA code.
4. **No development tools needed!** You do **not** need Python, Node.js, Git, or VS Code.

---

## 3. Step-by-Step Installation & First Run

### Step 1: Download & Install
1. Receive `AttendPlan-0.1.0-beta.2-Setup.exe` directly from the developer via private transfer.
2. Double-click the installer:
   - *Windows SmartScreen Notice:* Because this is a private beta without an expensive commercial EV certificate, Windows Defender SmartScreen may display: *"Windows protected your PC — Unknown publisher"*.
   - Click **"More info"** -> Click **"Run anyway"**.
3. The installer runs in user mode (`%LOCALAPPDATA%\AttendPlan\app`). No administrator password is required.
4. Leave the checkmark on *"Launch AttendPlan"* and click **Finish**.

### Step 2: First Launch & Browser Dashboard
1. AttendPlan will automatically start its local engine and open your default web browser to:
   ```
   http://127.0.0.1:8000/
   ```
2. You will be greeted by the **First-Run Onboarding** screen.

### Step 3: Choose Your Starting Option
You have two choices:
- **Option A (Instant Demo):** Click *"Load Sample Data"* to explore the dashboard immediately with an offline synthetic student dataset.
- **Option B (Real University Sync):** Follow the guided 3-step setup to connect your student portal:
  1. Click **"Open Student Portal in Chrome"**.
  2. A dedicated, private Google Chrome window will open to your university login page.
  3. Enter your student mobile number, password, and the 6-digit code from your Authenticator app.
  4. Once your student dashboard appears in Chrome, return to AttendPlan and click **"Start Initial Attendance Sync"**.
  5. AttendPlan will securely read your attendance data and display your personalized dashboard in seconds!

---

## 4. Exploration & Feature Testing Checklist

Please test the following core features during your beta session:

- [ ] **Home Dashboard:** Does your current semester attendance percentage and status badge match what you expect?
- [ ] **Safe Bunks & Recovery:** Does the "Safe to Miss" or "Classes Needed" guidance match your intuition?
- [ ] **What-If Attendance Simulator:** Click on any course to open the What-If simulator. Simulate attending or missing upcoming classes to see how your percentage adjusts.
- [ ] **Period Ledger & Daily Explorer:** In the Attendance tab, review your period-by-period class breakdown. Verify that holidays and cancelled periods are marked accurately.
- [ ] **Offline Backup Export:** Go to **Settings** -> Scroll down to **Local Data & Privacy** -> Click **"Export Offline Backup"**. Verify that a timestamped `.sqlite3` backup file is created in your backups folder.
- [ ] **Safe Disconnect:** In **Settings** -> **Troubleshooting & Diagnostics**, click **"Disconnect Browser"** to confirm that the Chrome session closes cleanly.
- [ ] **Application Restart:** Close your browser tab and terminal window. Reopen AttendPlan from your Windows Start Menu. Verify that your attendance data is still there instantly without needing to sign in again.

---

## 5. Reporting Feedback & Issues

If you encounter any issue, bug, or confusing screen:
1. Note the exact text of any error message shown.
2. Check the log file located at:
   ```
   %LOCALAPPDATA%\AttendPlan\logs\attendplan.log
   ```
3. Share your feedback directly with the project developer in our private chat.

Thank you for helping make AttendPlan reliable and easy to use for all students!

