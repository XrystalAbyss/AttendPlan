# AttendPlan

> **AttendPlan v0.1.0-beta.3 — Friends Beta & Packaging Release (November 2026)**  
> **Local-First University Attendance Intelligence Application**  
> Helping students manage a 75% subject-wise attendance requirement with exact mathematics, zero credential capture, and air-gapped local privacy.
>
> 🛡️ **Verified Quality Gates:** 342 Python unit & domain tests, 38 Vitest frontend tests, 74 API endpoints, 100% strict typing (`mypy` / `tsc`), zero student PII leaks, and standalone Windows Inno Setup installer.

---

## 1. Overview & Architecture
AttendPlan is an institutional attendance intelligence platform engineered for university students under strict attendance policies (such as the standard 75% threshold).

### Key Architectural Tenets
1. **Local-First & Air-Gapped**: The backend binds exclusively to `127.0.0.1` (loopback only). No student data, credentials, or telemetry ever leave the local machine.
2. **Read-Only ERP Interaction**: Reads iCloudEMS student portal data strictly in read-only mode via loopback Chrome DevTools Protocol (`127.0.0.1:9222`).
3. **Dedicated Chrome Profile**: Browser automation operates through an isolated Chrome profile stored outside the git repository at `%LOCALAPPDATA%\AttendPlan\chrome-profile`.
4. **No Credential Storage**: The student logs in manually in their own browser and completes university MFA (Google Authenticator). The application never requests, logs, or persists passwords, OTPs, or session tokens.
5. **Exact Rational Mathematics**: All percentage and margin calculations use exact rational arithmetic (`fractions.Fraction`), avoiding floating-point rounding inaccuracies.
6. **Multi-Semester Isolation**: Records across different academic semesters remain strictly isolated in the catalog and database.
7. **Clear Data Provenance**: Every screen clearly labels whether data is Live, Cached, or a Historical Sample Fixture.
8. **Dynamic Port Fallback**: Automatically discovers and binds to an available loopback port in the range 8000–8010 if port 8000 is occupied, with strict CORS synchronization.

---

## 2. Mathematical & Domain Invariants

Let $a$ = attended periods, $d$ = delivered periods, and $t$ = attendance target fraction (default $0.75$):
- **Domain Validity**: $0 \le a \le d$. Negative counts or $a > d$ raise `InvalidAttendanceError`.
- **Standard Ratio**: $\text{Percentage} = 100 \times \frac{a}{d}$ for $d > 0$.
- **Safe Missing Periods (Bunks)**: $\max(0, \lfloor a/t - d \rfloor)$.
- **Consecutive Recovery Needed**: $\max(0, \lceil (t \cdot d - a)/(1 - t) \rceil)$.
- **Unrecorded / Pending ($d = 0$)**: Percentage and margins are `None` (unknown), never assumed to be 0% or 100%.
- **Blank Cells**: Blank timetable cells evaluate as `PeriodStatus.NOT_REPORTED` ($d=0, a=0$). Never treated as absences.
- **Period Multiplier**: Independent 50-minute timetable rows have weight 1. Practical labs spanning two 50-minute rows count as 2 delivered periods, not 4.
- **Reconciliation Scope Invariant**: If day-wise observations cover a partial date subset of the term, reconciliation reports `SCOPE_MISMATCH`, never a false data discrepancy.
- **Aggregates**: Overall attendance across multiple courses is $\frac{\sum a_i}{\sum d_i}$, never the average of individual course percentages.

---

## 3. Repository Structure

```
AttendPlan/
├── backend/                       # Python 3.12+ FastAPI Service
│   ├── app/
│   │   ├── domain/                # Pure attendance math, analytics, RFC 6238 TOTP & historical models
│   │   ├── adapters/              # PortalSessionManager, LivePortalExtractor, QRParser & discovery adapters
│   │   ├── db/                    # SQLAlchemy 2.0 models & SQLite session (including sync_jobs)
│   │   ├── services/              # Ingestion, HistoricalDiscovery, Backfill, Reconciliation, SyncJobs, Settings & TotpVault
│   │   └── api/                   # FastAPI routes (74 endpoints) & Pydantic schemas
│   ├── alembic/                   # Database migrations (SQLite batch mode)
│   ├── launcher.py                # Standalone PyInstaller backend entrypoint with dynamic port fallback
│   ├── tests/                     # 342 Pytest suites (DB, analytics, discovery, API, sanitization, sync, TOTP, historical)
│   └── requirements.txt           # Locked backend dependencies
├── frontend/                      # Vite + React 19 + TypeScript App
│   ├── src/
│   │   ├── components/            # Institutional UI: Table, Analytics, Reconciliation, Sync Center, Onboarding, Historical Attendance
│   │   ├── types/                 # TypeScript data contracts & domain models
│   │   └── tests/                 # 38 Vitest component & view tests
│   └── package.json               # Locked frontend dependencies
├── installer/                     # Inno Setup 6 packaging configuration
│   └── attendplan_setup.iss       # Windows per-user (non-admin) installer script
├── release-candidates/            # Manifest and SHA-256 sums for built release candidates
│   ├── RELEASE_MANIFEST.json      # Structured release metadata
│   └── SHA256SUMS.txt             # Authoritative release checksums
├── docs/                          # Comprehensive Architectural & Contract Docs
│   ├── architecture.md            # Subsystems & privacy architecture
│   ├── historical-term-discovery.md # Term selectors, inventory model, and validation
│   ├── historical-backfill.md     # Two-stage extraction, safety batching, and term isolation
│   ├── historical-coverage.md     # Coverage metrics, discrete states, and analytical guardrails
│   ├── historical-reconciliation.md # Term-scoped reconciliation and provenance audit
│   ├── local-totp-authentication.md # RFC 6238 TOTP engine and safety margins
│   ├── windows-credential-vault.md # Windows Credential Manager DPAPI isolation
│   ├── persistent-student-identity.md # Persistent local mobile number settings
│   ├── authenticator-enrollment.md # Student enrollment walkthrough & fallback procedures
│   ├── live-sync-architecture.md  # Live CDP extraction & session handling
│   ├── sync-job-state-machine.md  # 15-state SyncJob lifecycle
│   ├── portal-parser-contracts.md # DOM parser contracts & validation
│   ├── sync-troubleshooting.md    # Windows PowerShell & CDP troubleshooting
│   ├── data-contract.md           # Domain models, enums & discovery DTOs
│   ├── test-strategy.md           # Multi-tiered verification matrix
│   └── roadmap.md                 # Milestone progression (F0 -> G3)
├── reports/                       # Formal release audits, benchmarks & verification reports
├── scripts/                       # PowerShell management & launcher scripts
├── Launch-AttendPlan.cmd          # Developer complete application launcher
└── Launch-Chrome.cmd              # Developer dedicated Chrome browser launcher
```

---

## 4. Getting Started & Windows Launchers

### 4.1 Windows Installer (For Students)

For students and nontechnical users, download the latest packaged installer from the release assets:
- **Installer**: `AttendPlan-0.1.0-beta.3-Setup.exe`
- **Installation Scope**: Installs to `%LOCALAPPDATA%\Programs\AttendPlan` without requiring Windows administrator privileges.
- **Includes**: Standalone bundled Python backend executable and pre-built React frontend assets. No external Python, Node.js, or Git installation required.

### 4.2 Developer Execution

AttendPlan provides two double-clickable `.cmd` launchers in the repository root for developer execution:

| Launcher File | Primary Purpose | Started Components |
| :--- | :--- | :--- |
| **`Launch-AttendPlan.cmd`** | **Start Complete Application** | Starts Dedicated Chrome (`9222`), FastAPI Backend (`8000`), React/Vite Frontend (`5173`), and opens the dashboard tab. |
| **`Launch-Chrome.cmd`** | **Dedicated Browser Only** | Launches or reuses ONLY the dedicated Chrome profile on loopback CDP (`127.0.0.1:9222`) navigating to the university portal. Backend & frontend do NOT start. |

- **To Stop Services**: Double-click `scripts\Stop-AttendPlan.cmd` (cleanly stops backend and frontend while keeping dedicated Chrome and university tabs alive).
- **See Documentation**: [Windows Local Launchers Guide](docs/windows-local-launchers.md).

---

### 4.3 Running Verification & Quality Gates
```powershell
.\run-tests.ps1
```
Executes all quality gates:
1. Backend tests (`pytest`): 342 passed (100%).
2. Security & Sanitization (`pytest test_sanitization.py`): 0 PII leaks, 0 credentials.
3. Static typing (`mypy`): 0 issues across 47 source files.
4. Linting (`ruff`): All checks passed (0 errors).
5. Frontend typing (`tsc --noEmit`): 0 errors.
6. Frontend tests (`vitest`): 38 passed across 13 test files (100%).
7. Frontend production build (`npm run build`): Clean production bundle (129 kB gzipped).
Total automated tests: **380 passed**.
