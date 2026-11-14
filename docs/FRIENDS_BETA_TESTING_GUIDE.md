# AttendPlan — Supervised Friends-Beta Testing Guide (v0.1.0-beta.3)

Welcome to the private beta testing for **AttendPlan**!  
AttendPlan is an open-source, local-first attendance planning companion designed to help university students track their attendance, calculate safe bunks, and plan recovery periods to stay comfortably above the institutional 75% requirement.

---

## 1. Important Privacy & Security Commitments

Before you begin, here is our strict guarantee to you:

1. **Local-First & Private:** All attendance data and database files stay 100% on your own computer. AttendPlan never uploads your data to any remote cloud, analytics server, or third party.
2. **We Never See Your Passwords or OTPs:** You log in to the student ERP directly inside a standard Google Chrome window. AttendPlan **never** requests, reads, stores, or transmits your university password or Authenticator codes.
3. **No Automatic Historical Backfill:** AttendPlan only syncs the current active semester unless you explicitly choose to import past semesters.
4. **Instant Session Revocation:** You can disconnect or clear your login session at any time with a single click.

---

## 2. System Requirements

* **Operating System:** Windows 10 or Windows 11 (64-bit).
* **Browser:** Google Chrome (must be installed on your machine for the read-only portal sync).
* **Developer Tools Needed:** **None.** (You do *not* need Python, Node.js, Git, or VS Code).

---

## 3. Step-by-Step Testing Walkthrough

Follow this 12-step walkthrough to test AttendPlan and verify that it works properly on your computer.

### Step 1: Install AttendPlan
1. Download or copy `AttendPlan-0.1.0-beta.3-Setup.exe`.
2. *(Optional Integrity Check)* Verify its SHA-256 checksum:  
   `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5`
3. Double-click the installer.  
   *(If Windows SmartScreen appears because this is a private test build, click "More info" -> "Run anyway").*
4. Complete the installation. A desktop shortcut and Start Menu entry will be created.

### Step 2: Launch the Application
1. Launch **AttendPlan** from your desktop or Start Menu.
2. The application will start its local backend service and open the user interface at `http://127.0.0.1:8000` in your default browser.
3. On first launch, a fresh local database is automatically created in `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`.

### Step 3: Connect Your University Account
1. On the initial setup screen, click **"Connect Student Portal"**.
2. A clean, dedicated Chrome window will open showing the university iCloudEMS login page.
3. Enter your own university username, password, and Google Authenticator OTP manually.
4. Once you reach the main student dashboard, AttendPlan will detect that the session is active.

### Step 4: Authorize Initial Attendance Sync
1. Return to the AttendPlan window.
2. Click **"Sync Current Attendance"**.
3. AttendPlan will read your current term's attendance records in read-only mode and ingest them into your local database.
4. You will see an Ingestion Summary showing the courses discovered, total delivered periods, and total attended periods.

### Step 5: Verify Academic Totals Against Official Portal
1. Open your official portal attendance page side-by-side with AttendPlan.
2. Compare each subject:
   - Subject code & title
   - Delivered periods ($d$)
   - Attended periods ($a$)
   - Current percentage ($\% = 100 \times \frac{a}{d}$)
3. Confirm that the numbers match your university portal.

### Step 6: Test Bunk Margin & Recovery Simulation
1. Click on any course card or table row to open the course details.
2. Check the **Safe Bunk Margin** (how many classes you can miss while staying $\ge 75\%$).
3. If attendance is below 75%, check the **Consecutive Recovery Needed** (how many consecutive classes you must attend to regain 75%).
4. Use the **Scenario Simulator**:
   - Add $+1$ or $+2$ simulated absences and check the projected percentage.
   - Add $+2$ or $+3$ simulated attendances and verify the projected percentage.
   - Confirm that the mathematics updates smoothly.

### Step 7: Explore the Performance Tab
1. Click on the **Performance** tab in the navigation bar.
2. Review:
   - Overall aggregate attendance percentage (calculated as $\frac{\sum a_i}{\sum d_i}$, not an average of percentages).
   - Subject breakdown by safety tiers (Safe $\ge 75\%$, Warning $70-74\%$, Critical $< 70\%$).
   - Absence impact visualizers.

### Step 8: Verify Application Restart & Persistence
1. Close the AttendPlan browser tab.
2. Close AttendPlan from the system tray or close its console window.
3. Launch **AttendPlan** again from the Start Menu.
4. Verify that:
   - Your courses and attendance data load immediately without re-syncing.
   - Your local database persisted your data seamlessly.

### Step 9: Test Session Reconnection
1. After some time, or if your university session times out, click **"Sync"**.
2. If the session has expired, AttendPlan will clearly prompt you to reconnect.
3. Click **"Reconnect"**, solve the portal login in the Chrome window, and verify that sync resumes without losing your existing records.

### Step 10: Export a Database Backup
1. Go to **Settings** (gear icon) -> **Database & Storage**.
2. Click **"Export Database Backup"**.
3. Save the `.sqlite3` backup file to your preferred location (e.g. Documents).
4. Verify that the file was created and is non-empty.

### Step 11: Disconnect Browser Session
1. In **Settings** or on the Portal Status card, click **"Disconnect Session"**.
2. Verify that the dedicated Chrome profile closes and the connection status changes to "Disconnected".

### Step 12: Uninstall (Optional / Clean Cleanup)
1. If you wish to uninstall AttendPlan after testing:
   - Open Windows **Settings** -> **Apps** -> **Installed apps**.
   - Select **AttendPlan** -> **Uninstall**.
   - Choose whether to keep or remove your local database files.

---

## 4. Volunteer Feedback Template

Please fill out this quick feedback form and share it with the developer:

```text
==================================================
ATTENDPLAN VOLUNTEER FEEDBACK (BETA.3)
==================================================
Date of Test: 
Windows OS Version (e.g. Win 11 Home 23H2): 
Screen Resolution & Scaling (e.g. 1920x1080 125%): 

1. INSTALLATION & LAUNCH
- Did the installer run without errors? [Yes / No]
- Did the application open automatically? [Yes / No]
- Any issues with antivirus or Windows Defender? [Yes / No (Details if any)]: 

2. LOGIN & PORTAL CONNECTION
- Did the Chrome login window open smoothly? [Yes / No]
- Did AttendPlan detect your login after MFA? [Yes / No]
- Was the instructions on screen clear? [Yes / No]

3. ATTENDANCE ACCURACY
- Did all of your current courses appear? [Yes / No]
- Did the delivered / attended counts match your ERP? [Yes / No]
- Any course titles or codes that looked garbled or incomplete? [None / Details]: 

4. SIMULATION & MATHEMATICS
- Did safe bunk and recovery calculations make sense? [Yes / No]
- Did the scenario simulator update as expected? [Yes / No]

5. RELIABILITY & UX
- Did closing and restarting the app preserve your data? [Yes / No]
- Was navigation intuitive and responsive? [Yes / No]
- Any visual glitches, awkward text, or layout issues? [None / Details]: 

6. OVERALL VERDICT & SUGGESTIONS
- Would you use AttendPlan regularly for attendance tracking? [Yes / No]
- What is one thing you would improve? 
==================================================
```

Thank you for helping make AttendPlan better and safer for everyone!
