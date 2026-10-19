# AttendPlan Permanent Engineering & Quality Rules

## 1. Core Mission & Philosophy
AttendPlan is a local-first university attendance intelligence application designed to help students track and plan their attendance under an institutional 75% threshold requirement.
- **Local-First & Privacy First**: Student credentials, cookies, tokens, and attendance records never leave the user's local machine. The local backend binds strictly to `127.0.0.1`.
- **Institutional Quality**: The application must look, behave, and calculate like an institutional analytics tool—relying on exact mathematics, explicit data provenance, and strict schema validation.
- **Read-Only Portal Adapter**: We interact with iCloudEMS strictly in read-only mode. We never automate authentication, never store credentials or OTPs, and never bypass university security or anti-tamper controls.

---

## 2. Mathematical & Domain Invariants
All calculations must be deterministic, pure functions with zero browser or database dependencies.

Let:
- $a \in \mathbb{N}_0$: Attended periods.
- $d \in \mathbb{N}_0$: Delivered periods.
- $t \in (0, 1)$: Attendance target fraction (default $0.75$).
- $x \in \mathbb{N}_0$: Additional periods attended in simulation.
- $y \in \mathbb{N}_0$: Additional periods missed in simulation.

### Invariants:
1. **Range Bounds**: $0 \le a \le d$. Any record where $a < 0$ or $a > d$ violates domain validity and must raise a validation error.
2. **Standard Attendance Ratio**: $\text{Percentage} = 100 \times \frac{a}{d}$ for $d > 0$.
3. **Safe Missing Periods (Bunk Margin)**:
   $$\text{safe\_bunks} = \max\left(0, \left\lfloor \frac{a}{t} - d \right\rfloor\right)$$
4. **Consecutive Recovery Periods Needed**:
   $$\text{consecutive\_needed} = \max\left(0, \left\lceil \frac{t \cdot d - a}{1 - t} \right\rceil\right)$$
5. **Zero Delivered Periods ($d = 0$)**:
   Percentage, safe bunks, and consecutive needed are **unknown (`None` / `null`)**, never assumed to be 0% or 100%. A course with $0/0$ is unrecorded, not safe.
6. **Exact Rational Arithmetic**:
   All threshold comparisons (e.g. is attendance below 75%?) must be executed on exact rational numbers (`fractions.Fraction` or exact integer math), never on pre-rounded UI strings (e.g. `74.99%` is strictly `< 75%`).
7. **Simulation Ratio**:
   $$\text{Scenario Percentage} = 100 \times \frac{a + x}{d + x + y}$$
8. **Lab Period Multipliers**:
   Practical laboratory blocks must represent their exact scheduled period count (typically 2 periods per block). Never assume a meeting equals 1 period.
9. **Conservative Safety**:
   If any course on a given day has an unknown code, missing record, or unresolved period count, the system must **prevent declaring that day safe**.
10. **Aggregate Attendance**:
    Overall attendance across multiple courses is $\frac{\sum a_i}{\sum d_i}$, never the average of individual course percentages.
11. **Blank Cell Semantics**:
    Empty cells in a timetable matrix represent unscheduled periods or holidays (`NO_CLASS`, $d=0, a=0$). They must NEVER be evaluated as absences.
12. **Canonical Checksum Invariance**:
    Content checksums must be computed over lexicographically sorted entries. Input row presentation order must never alter the deduplication hash.
13. **Multi-Semester Isolation**:
    Courses with identical course codes in different semesters must remain strictly isolated in the catalog and database.

---

## 3. Security & Non-Negotiable Boundaries
1. **No Automated Login / No Credential Persistence**:
   - The user must perform student portal login and MFA (Google Authenticator) manually in their own browser.
   - Never request, prompt for, log, or store passwords, OTPs, TOTP seeds, session tokens, or browser cookies.
2. **Localhost Binding**:
   - The API server binds strictly to `127.0.0.1` (never `0.0.0.0`).
3. **No Fabricated Data**:
   - Never mock or fabricate attendance values in production codepaths.
   - Offline fixtures must be explicitly marked as `SAMPLE / HISTORICAL` or `SYNTHETIC TEST FIXTURE` with data provenance clearly indicated.
4. **Git & Repository Hygiene**:
   - Never commit raw portal dumps containing student names, roll numbers, admission numbers, phone numbers, or session hashes.
   - All fixtures used for testing must be thoroughly scrubbed and sanitized.

---

## 4. Software Architecture & Clean Separation
- `backend/app/domain/`: Pure domain models, pure mathematical calculation engine, pure analytics engine, custom errors.
- `backend/app/adapters/`: Portal DOM parsers (subject-wise and day-wise), fixture loader, data normalization.
- `backend/app/db/`: SQLAlchemy 2.0 declarative models, enums, SQLite WAL configuration.
- `backend/app/services/`: Ingestion service, canonical checksums, reconciliation service.
- `backend/app/api/`: FastAPI routes, request/response DTOs, dependency injection.
- `backend/alembic/`: Schema migrations with SQLite batch mode support.
- `frontend/`: React 19 with TypeScript, Tailwind CSS, Lucide icons, Vite.
- `docs/`: Living architectural, contract, and design system documentation.
- `.agents/`: Antigravity skills and permanent engineering rules.

---

## 5. Quality Gates & Release Verification
Before declaring any milestone or change ready:
1. Python unit & domain tests pass (`pytest`).
2. Python linting and typing pass (`ruff` / `flake8`, `mypy`).
3. Frontend typecheck passes (`tsc --noEmit`).
4. Frontend tests pass (`npm run test` / `vitest`).
5. Frontend production bundle builds cleanly (`npm run build`).
6. Sanitization checks verify zero student PII in tracked repositories.
