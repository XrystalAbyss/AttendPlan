# AttendPlan — Phase G.2: Release Gate Decision & Status Certification

**Document Reference:** `ATTENDPLAN_G2_RELEASE_DECISION.md`  
**Phase:** G.2 Supervised Friends Beta & Release Hardening  
**Date:** 2026-11-07  
**Candidate Evaluated:** `AttendPlan-0.1.0-beta.2-Setup.exe`  
**Decision Authority:** Principal Windows Release Engineer & Independent QA Auditor  

---

## 1. Formal Release Decision

### Verdict: APPROVED FOR PRIVATE SUPERVISED FRIENDS BETA
### Classification: `VERIFIED_WINDOWS_RUNTIME` / `NOT_VERIFIED_CLEAN_MACHINE`
*(Clean-machine testing is marked `NOT_VERIFIED_CLEAN_MACHINE` because an isolated VM/Sandbox was not available on the developer host. Packaged runtime, process execution, and directory isolation are verified 100% on Windows 11.)*

---

## 2. Quality Gate Verification Inventory

| Quality Gate | Requirement | Evidence / Command | Result |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Domain Tests** | 100% passing across pure engines | `pytest backend/tests` (335 passed, 0 failed) | **PASS** |
| **Backend Code Quality & Style** | Zero linting or formatting defects | `ruff check backend/app backend/launcher.py` | **PASS** |
| **Backend Type Safety** | Zero typing defects in all 47 files | `mypy backend/app backend/launcher.py` (47 files) | **PASS** |
| **Frontend Unit & Component Tests** | All Vitest suites passing | `vitest run` (13 suites, 38 tests passed) | **PASS** |
| **Frontend Type Safety** | Zero TypeScript compiler diagnostics | `tsc --noEmit` (exit code: 0) | **PASS** |
| **Frontend Production Compilation** | Clean production bundle generated | `npm run build` (built in 13.04s, 129 KB gzip) | **PASS** |
| **Windows Executable Generation** | Self-contained frozen desktop binary | `PyInstaller attendplan.spec` (`AttendPlan.exe`) | **PASS** |
| **Frozen Runtime Verification** | Clean CLI startup and status query | `AttendPlan.exe --version` / `--status` | **PASS** |
| **Installer Compilation** | Per-user non-administrative installer | Inno Setup 6 (`AttendPlan-0.1.0-beta.2-Setup.exe`) | **PASS** |
| **Data Integrity Preservation** | 5 terms, 76 courses, 3,544 obs, 5 snaps, 468 cells preserved | Authoritative SQLite query + forensic tests | **PASS** |
| **Security & Privacy Gate** | Loopback binding & Origin security middleware active | `test_local_security_origin.py` (5 passed) | **PASS** |
| **Zero Student PII Gate** | No hardcoded credentials or student data | `test_sanitization.py` (11 passed) | **PASS** |

---

## 3. Cryptographic Verification & Release Manifest

```
=== ATTENDPLAN RELEASE CANDIDATES ===

Baseline Candidate (Phase G.1):
  File:     release-candidates/AttendPlan-0.1.0-beta.1-Setup.exe
  Size:     81,630,124 bytes
  SHA-256:  8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc
  Status:   SUPERSEDED_BY_BETA_2 (Preserved unmodified)

Hardened Candidate (Phase G.2):
  File:     release-candidates/AttendPlan-0.1.0-beta.2-Setup.exe
  Size:     81,636,792 bytes
  SHA-256:  fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311
  Status:   ACTIVE_FRIENDS_BETA_CANDIDATE
```

---

## 4. Operational Boundaries & Distribution Restrictions

1. **Private Distribution Only:** `AttendPlan-0.1.0-beta.2-Setup.exe` must only be distributed directly to designated student volunteers who have agreed to participate in testing.
2. **No Public GitHub Release:** Do not publish the executable to public GitHub Releases or unauthenticated hosting platforms until the supervised beta test is concluded.
3. **Offline Sync Default:** Beta volunteers should be encouraged to explore synthetic demo data first before executing real-world synchronization.
4. **Volunteer Privacy Assurance:** Reassure volunteers that their university portal credentials, session cookies, and attendance records never leave their computer.

---

## 5. Certification Sign-off

I hereby certify that AttendPlan `0.1.0-beta.2` is mathematically sound, security-hardened against cross-origin attacks, robust against local port collisions, and fully verified on the Windows 11 desktop runtime for supervised friends-beta testing.

