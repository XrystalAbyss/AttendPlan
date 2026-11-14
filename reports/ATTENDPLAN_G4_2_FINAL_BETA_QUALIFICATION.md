# ATTENDPLAN — PHASE G.4.2 FINAL BETA QUALIFICATION REPORT

**Milestone:** Phase G.4.2  
**Target Release Candidate:** AttendPlan 0.1.0-beta.6  
**Active Git Branch:** `feature/g4-real-beta-recovery`  
**Base Branch:** `main` (`ad75bdc3d131ab582070d9a2f25447b96928ba10`)  
**Repository:** `https://github.com/XrystalAbyss/AttendPlan`  
**Date:** November 14, 2026  
**Auditor / Implementation:** Google Antigravity (Principal Desktop Release Engineer & Security Auditor)

---

## 1. Executive Summary & Mission Objectives

Phase G.4.2 delivers the final engineering qualification, hardening, and packaging of AttendPlan prior to merging into `main` and initiating real-user handoff.

Following the defect closures of Phase G.4.1, Phase G.4.2 focused on resolving remaining architectural edge cases and student usability hurdles:
1. **Atomic Performance Transactions:** Redesigned marks import into a caller-owned transaction with pre-consumption validation and complete rollback safety.
2. **Strict Type-3 Continuous Evaluation Scope:** Enforced rejection of all non-continuous-evaluation scopes (`exam_type != "3"`) across discovery, preview, validation, extraction, and persistence.
3. **Same-Instance Operation Authorization:** Hardened sensitive local operations (`/api/v1/startup/shutdown`, portal session disconnect, database backup export) with loopback verification, origin/referer port matching, and dynamic in-memory instance tokens.
4. **Simplified Student UI:** Removed the retired official-results dropdown, eliminated the misleading unverified GPA progression table, and elevated Continuous Internal Assessments into a prominent, first-class workflow card.
5. **Windows Packaging & Release Qualification:** Compiled `AttendPlan-0.1.0-beta.6-Setup.exe` with all prior binaries (`beta.1` through `beta.5`) strictly preserved and verified against the canonical release manifest.

---

## 2. Technical Architecture & Engineering Deliverables

### 2.1 Atomic Performance Import & Rollback Safety
- **Module:** `backend/app/services/performance_service.py` & `backend/app/api/performance_routes.py`
- **Design:** Previously, `capture_performance` claimed the preview job in the database before validating the underlying payload structure, and relied on multiple nested `commit()` calls.
- **Remediation:**
  1. `persist_performance()` accepts `commit: bool = True`. When `commit=False`, changes are flushed (`db.flush()`) into the caller's transaction without finalizing.
  2. In `capture_performance()`, extensive pre-consumption validation occurs **before** any database mutation: verifying `payload.view == "marks"`, `payload.exam_type == "3"`, `approval_id`, `exam_session`, term verification, job completion, 30-minute expiration, and payload fingerprint matching.
  3. Job claim (`state="APPROVED"`), snapshot persistence (`persist_performance(commit=False)`), and job detail redaction are performed within a single atomic block finalized by a single `db.commit()`.
  4. Any exception during this sequence triggers `db.rollback()`, ensuring the job remains `COMPLETED` and no partial or broken records persist.

### 2.2 Strict Type-3 Continuous Evaluation Scope
- **Modules:** `backend/app/adapters/performance_portal.py` & `backend/app/api/performance_routes.py`
- **Scope Contract:** Continuous internal evaluation in iCloudEMS is strictly categorized under `exam_type == "3"`.
- **Enforcement Layers:**
  - **Discovery:** `discover_scopes()` strictly filters options where `exam.get("value") == "3"`.
  - **Portal Validation:** `validate_scope()` raises `PortalSafetyError("UNSUPPORTED_EXAM_TYPE")` if `exam_type != "3"`.
  - **Extraction:** `extract_marks()` strictly asserts `exam_type == "3"`.
  - **API Validation:** `approval_scope()`, `performance_preview()`, and `capture_performance()` reject any `exam_type != "3"` with HTTP 400.

### 2.3 Defensible Same-Instance Operation Authorization
- **Modules:** `backend/launcher.py`, `backend/app/main.py`, `backend/app/api/startup_routes.py`, `backend/app/api/routes.py`, `frontend/src/App.tsx`, `frontend/src/components/SettingsView.tsx`
- **Threat Model:** A local script or browser tab running on an unauthorized local port (e.g. `http://localhost:9999`) attempting cross-origin requests to local API endpoints.
- **Implementation:**
  1. `backend/launcher.py` generates a cryptographically secure 128-bit hex token (`secrets.token_hex(16)`) at process start, bound to `app.state.instance_token`, `app.state.bound_port`, and `app.state.bound_host`.
  2. `LocalOriginSecurityMiddleware` in `backend/app/main.py` inspects both `Origin` and `Referer` headers for loopback hostnames AND restricts ports to authorized application ports (`bound_port`, `8000-8010`, `5173`, `4173`, `3000`).
  3. `verify_same_instance_authorization(request: Request)` verifies loopback caller host, rejects `sec-fetch-site == "cross-site"`, validates port boundaries, and validates the `X-AttendPlan-Instance` header matching `app.state.instance_token`.
  4. Endpoints protected: `/api/v1/startup/shutdown`, `/api/v1/portal/session/disconnect`, `/api/v1/auth/backup/export`.
  5. Desktop frontend captures `instance_token` via `/api/v1/startup/status` and attaches the authorization header to all sensitive mutations.
  6. Launcher shutdown cleanly calls `default_engine.dispose()`, closing SQLite connections and allowing WAL checkpoints to settle.

### 2.4 Simplified Student Performance UI
- **Module:** `frontend/src/components/PerformanceView.tsx`
- **Key Enhancements:**
  1. **Elevated Workflow:** "Import Continuous Internal Assessments" is now a prominent first-class card with clear step-by-step guidance (Select Semester -> Discover Scopes -> Select Exam Session -> Preview -> Approve & Import).
  2. **Removed Retired Controls:** Completely removed the obsolete "Semester results (Retired)" dropdown option, locking the view exclusively to Continuous Internal Assessments.
  3. **Eliminated Misleading GPA Table:** Removed the empty/unverified "Semester progression — portal-reported GPA" table. Students now see clear continuous evaluation cards displaying only genuine university marks.
  4. **Transparent Assessment Breakdown:** Preserved the expandable assessment breakdown drawer displaying individual components (Sessional 1, Sessional 2, Quizzes, Assignments) with clear `REPORTED` (emerald) and `MASKED_BY_PORTAL` (amber) status tags.

---

## 3. Release Candidate Registry & Checksum Manifest

All six distributed installer candidates remain preserved on disk in `release-candidates/` with zero overwrites:

| Candidate | Target Platform | Size (Bytes) | SHA-256 Checksum | Release Status |
| :--- | :--- | :--- | :--- | :--- |
| **`AttendPlan-0.1.0-beta.1-Setup.exe`** | `win32-x64` | 81,630,124 | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` | Historical Baseline |
| **`AttendPlan-0.1.0-beta.2-Setup.exe`** | `win32-x64` | 81,636,792 | `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311` | Superseded by beta.3 |
| **`AttendPlan-0.1.0-beta.3-Setup.exe`** | `win32-x64` | 81,644,316 | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` | Superseded by beta.4 |
| **`AttendPlan-0.1.0-beta.4-Setup.exe`** | `win32-x64` | 81,650,698 | `160664cdb70f068f142c0611398b1f1bb579b38ee47dc2dc7d1bf7bd87df1486` | Superseded by beta.5 |
| **`AttendPlan-0.1.0-beta.5-Setup.exe`** | `win32-x64` | 81,653,350 | `ca31c1d34e8d902eaffbc0710e94bcdc6afe2baee77fe3611608cabe1e6d6aa8` | Superseded by beta.6 |
| **`AttendPlan-0.1.0-beta.6-Setup.exe`** | `win32-x64` | 81,653,549 | `c2d7a5274c72ff79f43a31b702e68eb0bcf96e7dc7417a6a4dd08191057d16cc` | **Qualified Friends Beta** |

---

## 4. Quality Gates & Independent Verification Evidence

| Quality Gate | Tool / Runner | Result | Details |
| :--- | :--- | :--- | :--- |
| **Gate 1: Privacy & Sanitization** | `pytest test_sanitization.py` | **PASSED (14/14)** | Zero student PII, credentials, or session cookies in repository |
| **Gate 2: Backend Unit & Domain Tests** | `pytest backend/tests` | **PASSED (352/352)** | 100% pass across domain, math, adapter, service, and API tests |
| **Gate 3: Python Linting & Formatting** | `ruff check` | **PASSED** | Zero violations in `app`, `launcher.py`, and `tests` |
| **Gate 4: Backend Static Typecheck** | `mypy` | **PASSED** | 100% strict type safety across 47 source files |
| **Gate 5: Frontend Component & Unit Tests** | `vitest` | **PASSED (41/41)** | All 13 component and integration test suites passing |
| **Gate 6: Frontend Static Typecheck** | `tsc --noEmit` | **PASSED** | Zero TypeScript compiler errors |
| **Gate 7: Frontend Production Bundle** | `vite build` | **PASSED** | Clean production build (HTML, CSS, JS assets bundled) |
| **Gate 8: Installer Compilation** | Inno Setup 6.7.3 | **PASSED** | `AttendPlan-0.1.0-beta.6-Setup.exe` (81,653,549 bytes) |

---

## 5. Non-Negotiable Invariance & Data Safety Verification

1. **Local-First Binding:** Verified that all API routes, servers, and middleware bind strictly to loopback (`127.0.0.1`).
2. **Read-Only Portal Sync:** Verified zero credential persistence, zero automated MFA submission, and zero state modification on student ERP.
3. **Database Preservation:** Verified that the user's existing multi-semester SQLite database, attendance observations, and catalog records are unaffected.
4. **Git Hygiene:** Verified that binary installers (`*.exe`) remain strictly gitignored and excluded from version control tracking.
