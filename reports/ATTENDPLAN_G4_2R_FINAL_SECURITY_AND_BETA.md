# AttendPlan — Phase G.4.2R Security Hardening, Exit UX & Final Beta Qualification Report

**Date:** November 14, 2026  
**Phase:** G.4.2R (Production Same-Origin Enforcement, Exit UX, Storage Optimization, and v0.1.0-beta.7 Packaging)  
**Repository:** `C:\Users\astra\Desktop\Project\AttendPlan`  
**GitHub Pull Request:** [#1 (feature/g4-real-beta-recovery -> main)](https://github.com/XrystalAbyss/AttendPlan/pull/1)  

---

## 1. Executive Summary

Phase G.4.2R completes the security hardening, user exit reliability, storage optimization, and packaging qualification for AttendPlan:
1. **Production Same-Origin Enforcement**: Replaced broad static loopback CORS with strict dynamic origin enforcement (`LocalOriginSecurityMiddleware`). Unrelated local ports (e.g. `http://localhost:8001`) and external web domains are blocked with HTTP 403 and receive zero CORS headers.
2. **Status Token Exposure Closure**: `GET /api/v1/startup/status` strictly verifies `Origin` and `Referer` against dynamic application origins, preventing cross-origin browser contexts from reading `instance_token`.
3. **Deterministic Exit UX**: Refactored `handleExitApp` in `frontend/src/App.tsx` to verify server response status, gracefully handle authorization errors, and actively poll loopback status until port release is confirmed before advising browser closure.
4. **Local Storage Optimization**: Safely removed obsolete installer prototypes (`beta.1`, `beta.2`, `beta.3`) and cleaned regenerable PyInstaller build caches, reclaiming **285.34 MB** of disk space while preserving cryptographic provenance in `RELEASE_MANIFEST.json`.
5. **Packaged Candidate Qualification**: Rebuilt and qualified **`AttendPlan-0.1.0-beta.7-Setup.exe`** (SHA-256: `31f3a966681297b0959dd4fc9d10e04160a041d363aacc7750d3bbf1ed38c1d4`), with `beta.6` retained as the verified rollback candidate.

---

## 2. Threat Model & Same-Origin Architecture

### A. Honest Security Boundary & Threat Model
- **In-Scope Threat (Browser Cross-Origin Isolation)**:
  AttendPlan runs a local web server binding to `127.0.0.1`. If an authenticated student visits an external website or runs an unrelated local web application (e.g., on port 8001), malicious JavaScript executing in that browser tab could attempt cross-origin requests (`fetch`/`XMLHttpRequest`) to `http://127.0.0.1:8000/api/` to read attendance, extract instance tokens, or trigger server shutdown.
  *Remediation*: AttendPlan strictly validates `Sec-Fetch-Site`, `Origin`, and `Referer` headers at the middleware and route layer, rejecting non-matching origins with HTTP 403 Forbidden and withholding `Access-Control-Allow-Origin` headers.
- **Out-of-Scope Threat (Same-User Local Process Compromise)**:
  AttendPlan does **not** claim to defend against arbitrary native binaries or scripts executing under the same Windows user account. Any process running as the local user has access to loopback sockets, memory inspection, DPAPI master keys, and local files. Defense in depth focuses on web browser isolation and safe cryptographic storage.

### B. Dynamic Loopback Origin Binding
In `backend/app/main.py`:
- In **production** (`ATTENDPLAN_ENV` not set to `development`):
  Only the dynamically bound loopback origin is trusted:
  $$\text{Allowed Origins} = \left\{ \texttt{http://127.0.0.1:}\langle\text{bound\_port}\rangle, \texttt{http://localhost:}\langle\text{bound\_port}\rangle, \texttt{http://testserver} \right\}$$
- In **development** (`ATTENDPLAN_ENV=development`):
  Vite development servers (`5173`, `4173`, `3000`) are additionally permitted.
- `LocalOriginSecurityMiddleware`:
  1. Checks `Sec-Fetch-Site`: rejects `"cross-site"` immediately with HTTP 403.
  2. Checks `Origin`: rejects any origin not in allowed set with HTTP 403 and emits **no** CORS headers.
  3. Checks `Referer`: rejects any referer origin not in allowed set with HTTP 403.
  4. Preflight `OPTIONS`: verifies origin and emits CORS headers strictly to permitted origins; unauthorized preflights receive HTTP 403.
  5. Response: dynamically sets `Access-Control-Allow-Origin: <origin>` and `Vary: Origin` strictly for verified allowed origins.

---

## 3. Exit UX & Clean Shutdown Architecture

In `frontend/src/App.tsx`:
1. **Header Authorization**: When `instance_token` is present, it is sent via `X-AttendPlan-Instance`.
2. **Response Status Check**: `res.ok` is checked. If HTTP 403 or an error occurs, the user is alerted to the exact authorization error without displaying a false success message.
3. **Active Port-Release Verification**: The client polls `GET /api/v1/startup/status` up to 5 times at 600 ms intervals.
   - When connection is refused (network failure / `fetch` error) or `!res.ok`, the application alerts:
     > *"AttendPlan server has stopped cleanly and released port. You can safely close this browser tab."*
   - If the polling loop exhausts without connection refusal:
     > *"AttendPlan shutdown was requested. The background process is finalizing its exit."*
4. **Graceful Engine Shutdown**: The background launcher calls `default_engine.dispose()` prior to exit, ensuring SQLite WAL journals flush cleanly.

---

## 4. Test Suite & Verification Results

### A. Quality Gates
| Gate | Command | Result | Status |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Domain Tests** | `pytest backend/tests -q` | 355 passed in 32.27s | **PASSED** |
| **Sanitization & PII Audit** | `pytest backend/tests/test_sanitization.py -v` | 14 passed in 5.57s | **PASSED** |
| **Python Code Quality & Linting** | `ruff check backend/app backend/launcher.py backend/tests` | All checks passed | **PASSED** |
| **Python Static Typing** | `mypy backend/app backend/launcher.py` | 0 issues across 47 source files | **PASSED** |
| **Frontend Unit & Component Tests** | `npm --prefix frontend test -- --run` | 13 test files, 41 tests passed | **PASSED** |
| **Frontend TypeScript Typecheck** | `npm --prefix frontend run typecheck` | 0 type errors | **PASSED** |
| **Frontend Production Build** | `npm --prefix frontend run build` | Built cleanly in 9.28s | **PASSED** |

### B. Security Negative Tests Added (`backend/tests/test_launcher_and_shutdown.py`)
1. `test_shutdown_endpoint_security_and_trigger`: Validates loopback caller enforcement, cross-site rejection, instance token validation, and graceful shutdown trigger.
2. `test_status_endpoint_returns_instance_token`: Confirms status payload returns instance token for authorized same-instance callers.
3. `test_production_same_origin_security_and_cors_headers`:
   - Legitimate bound loopback origin (`127.0.0.1:8000`) succeeds and receives CORS headers.
   - Unrelated loopback port (`localhost:8001`) receives 403 Forbidden with zero CORS headers.
   - Cross-site request (`Sec-Fetch-Site: cross-site`) receives 403 Forbidden.
   - Mismatched Referer port (`localhost:8001`) receives 403 Forbidden.
   - Valid Referer (`127.0.0.1:8000`) succeeds.
   - Direct native calls without Origin/Referer succeed.
   - Dynamic port shift: setting `app.state.bound_port = 8005` permits `127.0.0.1:8005` and blocks `127.0.0.1:8000`.
   - OPTIONS preflight: permitted origin receives 200 with CORS headers; forbidden origin receives 403.
4. `test_development_mode_origin_allowlist`: Confirms Vite dev ports (`5173`) are blocked in production and permitted in development mode.
5. `test_sensitive_routes_reject_unrelated_origin`: Confirms `/api/v1/portal/session/disconnect` and `/api/v1/auth/backup/export` reject unrelated origin (`localhost:8001`).

---

## 5. Release Candidate Packaging & Provenance

### Active & Historical Binaries
| Version | Filename | Size (Bytes) | SHA-256 Checksum | Status |
| :--- | :--- | :--- | :--- | :--- |
| **0.1.0-beta.7** | `AttendPlan-0.1.0-beta.7-Setup.exe` | **81,704,034** | `31f3a966681297b0959dd4fc9d10e04160a041d363aacc7750d3bbf1ed38c1d4` | **ACTIVE FRIENDS-BETA CANDIDATE** |
| **0.1.0-beta.6** | `AttendPlan-0.1.0-beta.6-Setup.exe` | 81,653,549 | `c2d7a5274c72ff79f43a31b702e68eb0bcf96e7dc7417a6a4dd08191057d16cc` | **ROLLBACK CANDIDATE** |
| 0.1.0-beta.5 | `AttendPlan-0.1.0-beta.5-Setup.exe` | 81,653,350 | `ca31c1d34e8d902eaffbc0710e94bcdc6afe2baee77fe3611608cabe1e6d6aa8` | Superseded (Retained) |
| 0.1.0-beta.4 | `AttendPlan-0.1.0-beta.4-Setup.exe` | 81,650,698 | `160664cdb70f068f142c0611398b1f1bb579b38ee47dc2dc7d1bf7bd87df1486` | Superseded (Retained) |
| 0.1.0-beta.3 | `AttendPlan-0.1.0-beta.3-Setup.exe` | 81,644,316 | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` | Removed (Storage Optimization) |
| 0.1.0-beta.2 | `AttendPlan-0.1.0-beta.2-Setup.exe` | 81,636,792 | `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311` | Removed (Storage Optimization) |
| 0.1.0-beta.1 | `AttendPlan-0.1.0-beta.1-Setup.exe` | 81,630,124 | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` | Removed (Storage Optimization) |

---

## 6. Conclusion & Handoff Recommendation

AttendPlan `v0.1.0-beta.7` satisfies all technical criteria for supervised distribution to beta participants:
- Complete loopback browser protection with dynamic port binding and zero cross-origin token leaks.
- Reliable, verified application exit flow with SQLite WAL checkpoint completion.
- Reclaimed 285.34 MB of local storage while maintaining complete provenance tracking.
- All unit, integration, typing, linting, and build verification gates pass cleanly.
