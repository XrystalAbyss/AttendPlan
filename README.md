# AttendPlan

> **Local-First University Attendance Intelligence Application**  
> Helping students manage a 75% subject-wise attendance requirement with exact mathematics, zero credential capture, and air-gapped local privacy.

---

## 1. Overview & Architecture
AttendPlan is an institutional attendance intelligence platform engineered for university students under strict attendance policies (such as the standard 75% threshold).

### Key Architectural Tenets
1. **Local-First & Air-Gapped**: The backend binds exclusively to `127.0.0.1`. No student data or credentials leave the local machine.
2. **Read-Only ERP Interaction**: Reads iCloudEMS student portal data strictly in read-only mode via loopback Chrome DevTools Protocol (`127.0.0.1:9222`).
3. **Dedicated Chrome Profile**: Browser automation operates through an isolated Chrome profile stored outside the git repository at `%LOCALAPPDATA%\AttendPlan\chrome-profile`.
4. **No Credential Storage**: The user logs in manually in their own browser and completes MFA (Google Authenticator). The application never requests, logs, or persists passwords, OTPs, or session tokens.
5. **Exact Rational Mathematics**: All percentage and margin calculations use exact rational arithmetic (`fractions.Fraction`), avoiding floating-point inaccuracies.
6. **Clear Data Provenance**: Every screen clearly labels whether data is Live, Cached, or a Historical Sample Fixture.

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
│   │   ├── domain/                # Pure attendance math & analytics engine
│   │   ├── adapters/              # PortalSessionManager, DOM parsers & discovery adapters
│   │   ├── db/                    # SQLAlchemy 2.0 models & SQLite session
│   │   ├── services/              # Ingestion, canonical checksums & reconciliation
│   │   └── api/                   # FastAPI routes (24 endpoints) & Pydantic schemas
│   ├── alembic/                   # Database migrations (SQLite batch mode)
│   ├── tests/                     # 69 Pytest suites (DB, analytics, discovery, API, sanitization)
│   └── requirements.txt           # Locked backend dependencies
├── frontend/                      # Vite + React 19 + TypeScript App
│   ├── src/
│   │   ├── components/            # Institutional UI: Table, Analytics, Reconciliation, Discovery
│   │   ├── types/                 # TypeScript data contracts
│   │   └── tests/                 # 15 Vitest component & view tests
│   └── package.json               # Locked frontend dependencies
├── docs/                          # Comprehensive Architectural & Contract Docs
│   ├── architecture.md            # Subsystems & privacy architecture
│   ├── data-contract.md           # Domain models, enums & discovery DTOs
│   ├── portal-discovery-plan.md   # F2-A exploration findings & F2-B roadmap
│   ├── test-strategy.md           # Multi-tiered verification matrix
│   └── roadmap.md                 # Milestone progression (F0 -> F4)
└── reference-private/             # Read-only legacy reference scripts and DOM captures
```

---

## 4. Getting Started

### 4.1 Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Google Chrome (installed at standard Windows location)

### 4.2 Running Backend
```powershell
.\run-backend.ps1
# Or manually:
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API runs on `http://127.0.0.1:8000` (docs at `http://127.0.0.1:8000/docs`).

### 4.3 Running Frontend
```powershell
.\run-frontend.ps1
# Or manually:
cd frontend
npm run dev
```
Dashboard runs on `http://localhost:5173`.

### 4.4 Running Test Suites
```powershell
.\run-tests.ps1
```
Executes:
1. Backend tests (`pytest`): 69 passed.
2. Static typing (`mypy`): 0 issues across 32 source files.
3. Linting (`ruff`): All checks passed.
4. Frontend tests (`vitest`): 15 passed across 5 test files.
5. Frontend production build (`tsc -b && vite build`): Succeeded cleanly.
