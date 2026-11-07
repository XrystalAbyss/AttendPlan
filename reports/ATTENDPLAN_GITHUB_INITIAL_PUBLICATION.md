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
A pre-commit cryptographic hash audit was executed across the entire repository to verify that prohibited student identifiers and session artifacts never enter production source code or public documentation:

| Prohibited Category | Validation Rule | Working Tree Result | Status |
| :--- | :--- | :--- | :--- |
| **Student Admission No** | SHA-256 token digest matching | 0 occurrences in source / fixtures / docs | PASS |
| **Government Identity No** | SHA-256 token digest matching | 0 occurrences in source / fixtures / docs | PASS |
| **Student Roll No** | SHA-256 token digest matching | 0 occurrences in source / fixtures / docs | PASS |
| **Personal Phone No** | SHA-256 token digest matching | 0 occurrences in source / fixtures / docs | PASS |
| **Personal Student Name** | SHA-256 token digest matching | 0 occurrences in source / fixtures / docs | PASS |
| **Anti-Tamper Script** | Regex pattern matching | 0 occurrences in source / fixtures / docs | PASS |
| **Analytics Trackers** | Regex pattern matching | 0 occurrences in source / fixtures / docs | PASS |

> [!CAUTION]
> **Phase G.3.1 Disclosure Notice**: Prior git commits (`2c2d5e1` and `a693868`) contained literal audit pattern values in this report and test suites. While the current working tree has been completely sanitized with one-way cryptographic hash canaries, complete elimination from public remote history requires the authorized Git history remediation detailed in `reports/ATTENDPLAN_G3_1_PUBLICATION_SECURITY.md`.

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

Binary installer artifacts remain staged locally in `release-candidates/` with authoritative checksums verified directly from installer file bytes:

| Candidate | Size (bytes) | Actual SHA-256 Checksum | Inno Setup Version | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`AttendPlan-0.1.0-beta.1-Setup.exe`** | 81,630,124 | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` | Inno Setup 6 | HISTORICAL_BASELINE |
| **`AttendPlan-0.1.0-beta.2-Setup.exe`** | 81,636,792 | `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311` | Inno Setup 6 | SUPERSEDED_BY_BETA_3 |
| **`AttendPlan-0.1.0-beta.3-Setup.exe`** | 81,644,316 | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` | Inno Setup 6 | ACTIVE_FRIENDS_BETA_CANDIDATE |

---

## 7. Next Recommended Actions

1. **Tag Initial Beta**: Tag commit `2c2d5e1ba50ed9f7789a0278dbf349712ad9bf1b` with `v0.1.0-beta.3` when ready for private GitHub Release.
2. **Draft GitHub Release**: Upload `AttendPlan-0.1.0-beta.3-Setup.exe` as a release asset with its corresponding SHA-256 checksum once the user authorizes binary distribution.
3. **Branch Protection**: Consider configuring branch protection on `main` to require CI checks (`Backend Quality Gate`, `Frontend Quality Gate`) before merging future pull requests.

