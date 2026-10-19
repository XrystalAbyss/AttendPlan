---
name: release-verification
description: Quality gates, test execution, typing, linting, and build verification procedures for AttendPlan releases.
---

# Release Verification Skill

## Automated Verification Protocol

Before declaring any milestone or release ready, execute the complete quality suite using the unified script:
```powershell
powershell -ExecutionPolicy Bypass -File .\run-tests.ps1
```

### Quality Gates Breakdown:

#### Gate 1: Backend Domain, Database, Ingestion & API Tests
Run all backend tests with pytest:
```powershell
backend\.venv\Scripts\pytest backend/tests -v
```
- Benchmark: 49 passing tests across 9 test suites.
- Coverage: Exact mathematics, database persistence, foreign keys, multi-semester isolation, Alembic migrations, canonical checksums, HTML parsing, day-wise timetable parsing, pure analytics, reconciliation service, and REST API.

#### Gate 2: Static Type Checking
```powershell
backend\.venv\Scripts\mypy backend/app
```
- Benchmark: 0 issues found across 20 source files.

#### Gate 3: Code Linting
```powershell
backend\.venv\Scripts\ruff check backend/app backend/tests
```
- Benchmark: All checks passed.

#### Gate 4: Frontend Typecheck & Component Tests
```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run test
```
- Benchmark: `tsc --noEmit` exits with code 0; 12 Vitest tests pass across 4 test files.

#### Gate 5: Production Bundle Verification
```powershell
cd frontend
npm.cmd run build
```
- Benchmark: `tsc -b && vite build` completes cleanly with zero errors.

#### Gate 6: Privacy & Sanitization Check
Verify zero student PII, credentials, or cookies exist in tracked repositories:
```powershell
git status
```
Ensure `reference-private/`, `*.sqlite3`, and `.venv/` remain strictly ignored.
