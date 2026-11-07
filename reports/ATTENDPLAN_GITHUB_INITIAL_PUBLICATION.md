# AttendPlan — GitHub Source Control Publication & Release Audit

**Date:** 2026-11-07  
**Canonical Remote Repository:** `https://github.com/XrystalAbyss/AttendPlan`  
**Pushed Branch:** `main`  
**Initial Commit SHA:** `2c2d5e1ba50ed9f7789a0278dbf349712ad9bf1b`  
**Committer Identity:** `XrystalAbyss <184533436+XrystalAbyss@users.noreply.github.com>` (GitHub ID: 184533436)  
**Distribution State:** Supervised Friends Beta (Source Published, Binary Releases Staged Locally)

---

## 1. Executive Summary

Under explicit user authorization, the AttendPlan source code repository has been audited, sanitized, organized, and published to GitHub at [XrystalAbyss/AttendPlan](https://github.com/XrystalAbyss/AttendPlan) on branch `main`.

All non-negotiable security boundaries, quality gates, and data privacy invariants were verified prior to publication:
- **Zero Student PII**: No admission numbers, names, Aadhaar numbers, phone numbers, or unredacted institutional portal dumps exist in git history.
- **Zero Credentials / Tokens**: No passwords, OTP seeds, TOTP keys, session cookies, or authorization tokens are tracked.
- **Lightweight Repository**: Heavy binary installers (`release-candidates/*.exe`, ~81.6 MB each) are strictly ignored via `.gitignore`; only structured manifests and cryptographic checksums are tracked.
- **100% Quality Gates**: 342 backend Python tests, 38 frontend Vitest tests, 100% strict static typing (`mypy` / `tsc`), and zero lint errors.
- **Automated CI/CD**: Dual-job GitHub Actions workflow (`.github/workflows/ci.yml`) enforcing backend quality, frontend build integrity, and sanitization gates on every commit and pull request.

---

## 2. Remote State & Commit Verification

The remote repository state was audited using the GitHub API:

| Parameter | Value | Verification Source |
| :--- | :--- | :--- |
| **Repository URL** | `https://github.com/XrystalAbyss/AttendPlan.git` | Git Remote `origin` |
| **Default Branch** | `main` | GitHub API `list_branches` |
| **Live Commit SHA** | `2c2d5e1ba50ed9f7789a0278dbf349712ad9bf1b` | GitHub API `list_commits` |
| **Commit Message** | `feat: initial release of AttendPlan (v0.1.0-beta.3)` | Commit metadata |
| **Author / Committer** | `XrystalAbyss` (`184533436`) | Verified GitHub User |
| **Total Changed Files** | 338 files (43,920 insertions, 843 deletions) | `git diff --stat` |
| **Working Tree Status** | Clean (`nothing to commit, working tree clean`) | `git status` |

---

## 3. Security, Sanitization & Privacy Audit

### 3.1 Prohibited Data Pattern Scan
A pre-commit regex audit was executed across the entire repository to verify that prohibited student identifiers and session artifacts never enter source control:

| Prohibited Item | Pattern Scanned | Result | Status |
| :--- | :--- | :--- | :--- |
| **Student Admission No** | `[REDACTED_STUDENT_IDENTIFIER]` | 0 occurrences in source / fixtures | PASS |
| **Aadhaar Identity** | `[REDACTED_IDENTITY_NUMBER]` | 0 occurrences in source / fixtures | PASS |
| **Student Roll No** | `[REDACTED_STUDENT_ROLL_NO]` | 0 occurrences in source / fixtures | PASS |
| **Student Phone No** | `[REDACTED_STUDENT_PHONE]` | 0 occurrences in source / fixtures | PASS |
| **Student Name** | `[REDACTED_PERSONAL_NAME]` / `[REDACTED_PERSONAL_SURNAME]` | 0 occurrences in source / fixtures | PASS |
| **Anti-Tamper Script** | `logoutDueToTampering` | 0 occurrences in source / fixtures | PASS |
| **Analytics Trackers** | `GTM-57PQJ6N` / `UA-194952325` | 0 occurrences in source / fixtures | PASS |

### 3.2 Gitignore Containment Rules
The following items are strictly excluded from source control:
1. `reports/evidence/`: Excludes raw university portal DOM dumps containing student headers and demographic metadata.
2. `release-candidates/*.exe`: Excludes large binary Inno Setup installers (~81.6 MB), keeping repository clones fast and lightweight.
3. `*.sqlite3*`: Excludes all local personal SQLite databases, WAL files, and pre-migration backups.
4. `chrome-profile/` & `browser-profile/`: Excludes dedicated Chrome user data and CDP cookies.
5. `.env*`, `*.token`, `*.session`, `*.key`: Excludes environment secrets and tokens.

---

## 4. Verification & Quality Gates

All automated verification gates were executed and passed prior to publication:

```
========================================================================================
ATTENDPLAN VERIFICATION MATRIX (November 2026)
========================================================================================
Gate 1: Backend Domain & Unit Tests (pytest)        --> 342 PASSED (100%) in 37.18s
Gate 2: Security & Sanitization Audit (pytest)       --> 12 PASSED (100%) in 7.74s
Gate 3: Backend Python Static Typing (mypy)          --> 0 ISSUES across 47 source files
Gate 4: Backend Python Linting (ruff)                --> 0 ERRORS across app, tests, launcher
Gate 5: Frontend TypeScript Compilation (tsc)        --> 0 ERRORS (strict mode)
Gate 6: Frontend Component & View Tests (vitest)     --> 38 PASSED across 13 suites in 100s
Gate 7: Frontend Production Bundle (vite build)      --> BUILT in 28.88s (129.3 kB gzipped)
========================================================================================
TOTAL AUTOMATED TESTS: 380 PASSED (0 FAILURES, 0 WARNINGS)
========================================================================================
```

---

## 5. GitHub Actions Continuous Integration

The repository includes a dedicated CI pipeline configured in `.github/workflows/ci.yml`:
- **Read-Only Scope**: Strict `permissions: contents: read` prevents token elevation.
- **Job 1 (`backend-verification`)**: Runs on `windows-latest` with Python 3.12, verifying sanitization, Ruff linting, Mypy typing, and the complete 342-test Pytest suite.
- **Job 2 (`frontend-verification`)**: Runs on `ubuntu-latest` with Node.js 22, verifying Vitest tests, TypeScript compile check (`tsc --noEmit`), and production bundle build (`npm run build`).

---

## 6. Release Candidates & Release Manifests

Binary installer artifacts remain staged locally in `release-candidates/` with authoritative checksums tracked in source control:

| Candidate | Size (bytes) | SHA-256 Checksum | Inno Setup Version |
| :--- | :--- | :--- | :--- |
| **`AttendPlan-0.1.0-beta.1-Setup.exe`** | 81,630,124 | `1f4682055ce8c8e8d120a1ceb27ef3eeb5f2f42a59a93ae48aa829c53ae893fb` | Inno Setup 6 |
| **`AttendPlan-0.1.0-beta.2-Setup.exe`** | 81,636,792 | `f3ea329587a8100eeffea1fc5e6b1d4410a010d8a9df2735d4fa39a2f2679d39` | Inno Setup 6 |
| **`AttendPlan-0.1.0-beta.3-Setup.exe`** | 81,644,316 | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` | Inno Setup 6 |

---

## 7. Next Recommended Actions

1. **Tag Initial Beta**: Tag commit `2c2d5e1ba50ed9f7789a0278dbf349712ad9bf1b` with `v0.1.0-beta.3` when ready for private GitHub Release.
2. **Draft GitHub Release**: Upload `AttendPlan-0.1.0-beta.3-Setup.exe` as a release asset with its corresponding SHA-256 checksum once the user authorizes binary distribution.
3. **Branch Protection**: Consider configuring branch protection on `main` to require CI checks (`Backend Quality Gate`, `Frontend Quality Gate`) before merging future pull requests.
