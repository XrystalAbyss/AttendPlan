# AttendPlan — Double-Click Windows Launchers Guide

AttendPlan provides two primary double-clickable Windows launchers located in the repository root. These launchers automate local startup while maintaining strict local-first security boundaries, process ownership tracking, and data integrity.

---

## The Two Primary Launchers

### Option A: Dedicated Browser Only
**File**: `Launch-Chrome.cmd`

- **Purpose**: Launches **only** the dedicated Chrome profile with loopback Chrome DevTools Protocol (CDP) enabled.
- **Components Started**: Dedicated Google Chrome browser only (FastAPI backend and React frontend do **NOT** start).
- **Target URL**: `https://mrei.icloudems.com/corecampus/index.php`
- **CDP Endpoint**: `127.0.0.1:9222`
- **User Data Directory**: `%LOCALAPPDATA%\AttendPlan\chrome-profile`
- **Behavior**:
  - Checks if an authorized AttendPlan Chrome instance is already running on port 9222.
  - If already running, reuses the existing instance without spawning duplicate windows or disrupting tabs.
  - Verifies CDP readiness via `/json/version`.
  - Exits the CMD window cleanly while leaving the browser running.

---

### Option B: Full Application Suite
**File**: `Launch-AttendPlan.cmd`

- **Purpose**: Starts the **complete** AttendPlan development application in a single double-click.
- **Components Started**:
  1. Dedicated Chrome Browser (`127.0.0.1:9222`)
  2. FastAPI Local Backend (`http://127.0.0.1:8000`)
  3. React/Vite Frontend Dev Server (`http://127.0.0.1:5173`)
  4. Automatically opens the AttendPlan dashboard tab in Chrome.
- **Startup Steps**:
  1. **[1/5] Checking environment**: Validates local Python venv (`backend\.venv`), Node modules (`frontend\node_modules`), and Chrome installation.
  2. **[2/5] Starting dedicated Chrome**: Starts or reuses the dedicated Chrome instance on port 9222.
  3. **[3/5] Starting backend**: Starts Uvicorn (`http://127.0.0.1:8000`) bound strictly to loopback; polls `/health` for application identity confirmation (`app: AttendPlan`).
  4. **[4/5] Starting frontend**: Starts Vite dev server (`http://127.0.0.1:5173`) with strict port enforcement (`--strictPort`).
  5. **[5/5] Opening dashboard**: Checks active Chrome tabs via CDP; opens `http://127.0.0.1:5173` if not already open (prevents tab duplication).

---

## Stopping AttendPlan Services

### Clean Shutdown Helper
- **From CMD / Explorer**: Run `scripts\Stop-AttendPlan.cmd`
- **From PowerShell**: Run `.\scripts\Stop-AttendPlan.ps1` or `.\Launch-AttendPlan.cmd -Stop`

### What Gets Stopped:
- The FastAPI backend process (tracked via `%LOCALAPPDATA%\AttendPlan\run\backend.pid`).
- The Vite frontend process (tracked via `%LOCALAPPDATA%\AttendPlan\run\frontend.pid`).

### What Remains Running:
- **Dedicated Google Chrome is preserved**: The browser remains open so that active university portal tabs, student login sessions, and MFA cookies are never abruptly terminated.

---

## Operational Scenarios & Troubleshooting

### 1. Second Launch / Duplicate Execution
- If `Launch-AttendPlan.cmd` is executed while services are already running, it:
  - Detects healthy backend on `http://127.0.0.1:8000/health`.
  - Detects running frontend on `http://127.0.0.1:5173`.
  - Reuses the existing processes without spawning duplicate instances.
  - Verifies or focuses the dashboard tab in Chrome.

### 2. Port Conflict Handling (8000 / 5173 / 9222)
- **Port 8000 (Backend)**: If an unrelated foreign process occupies port 8000, AttendPlan refuses to start, displays an actionable conflict error, and stops safely without killing the foreign process.
- **Port 5173 (Frontend)**: Vite is invoked with `--strictPort`. If port 5173 is occupied, Vite will not silently shift to 5174; the launcher reports the conflict and halts cleanly.
- **Port 9222 (CDP)**: The launcher inspects process command-line arguments to verify that port 9222 belongs to AttendPlan's dedicated profile. If occupied by an unrelated debugger, it alerts the user.

### 3. Missing Dependencies
- **Missing Backend Virtual Environment**:
  ```powershell
  cd backend
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  ```
- **Missing Frontend Node Modules**:
  ```powershell
  cd frontend
  npm install
  ```

---

## Data & Credential Locations

All persistent data resides strictly on the local machine outside the Git tree:

| Item | Physical Location | Security Description |
| :--- | :--- | :--- |
| **Dedicated Chrome Profile** | `%LOCALAPPDATA%\AttendPlan\chrome-profile\` | Dedicated user profile containing university cookies and portal sessions. Completely isolated from personal Chrome profile. |
| **Process Run Metadata** | `%LOCALAPPDATA%\AttendPlan\run\*.pid` | Ephemeral process ID files for backend and frontend lifecycle management. |
| **Application Settings** | `%LOCALAPPDATA%\AttendPlan\settings.json` | Stores user automation preferences and normalized mobile number (masked in API/logs). |
| **TOTP Secret Vault** | Windows Credential Manager | Stored securely under target `AttendPlan/iCloudEMS/TOTP` using DPAPI. Never stored in plaintext files or SQLite. |
| **Attendance Database** | `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3` | SQLite WAL database storing course catalog, subject-wise snapshots, and day-wise observations. |
