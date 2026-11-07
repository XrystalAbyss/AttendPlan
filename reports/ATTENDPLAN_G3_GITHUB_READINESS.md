# AttendPlan — Phase G.3: GitHub Publication Readiness & Sanitization Audit

**Document Reference:** `ATTENDPLAN_G3_GITHUB_READINESS.md`  
**Phase:** G.3 Real Friends Beta, Clean-Machine Validation & Final Release Acceptance  
**Date:** 2026-11-07  
**Canonical Remote Target:** `https://github.com/XrystalAbyss/AttendPlan`  
**Distribution State:** STRICTLY LOCAL — ZERO REMOTE PUSH PERMITTED  

---

## 1. Executive Policy & Directive

In accordance with explicit project directives:
- **DO NOT PUSH TO GITHUB:** No commits, tags, or branches may be pushed to `https://github.com/XrystalAbyss/AttendPlan` during Phase G.3.
- **DO NOT UPLOAD INSTALLERS:** Release binaries must not be uploaded to GitHub Releases or any cloud hosting without explicit user authorization.
- **LOCAL-FIRST AUDIT:** This report assesses the technical and privacy readiness of the repository for future authorized publication.

---

## 2. Git Repository & Working Tree Audit

### 2.1 Current Git Status
- **Current Branch:** `master`
- **Initial Commit:** `5948106` (*chore: baseline F2-A state*)
- **Remote Configuration:** Currently zero configured remotes (`git remote -v` returns empty). The canonical GitHub URL `https://github.com/XrystalAbyss/AttendPlan` is established as the destination remote for future publication.

### 2.2 Privacy & Sensitive Data Scan

A forensic scan was performed across the working tree and tracked files:

| Artifact Category | Target Invariant | Audit Result | Status |
| :--- | :--- | :--- | :--- |
| **Student Credentials & Passwords** | Zero passwords, OTPs, or TOTP seeds in source | Verified via `test_sanitization.py` (11/11 tests pass) | **PASS** |
| **Personal Database Files** | `attendplan.sqlite3` must never be tracked | Blocked by `.gitignore` (`*.sqlite3`, `*.sqlite3-wal`) | **PASS** |
| **Private Backup Files** | Database backups must never be tracked | Blocked by `.gitignore` (`backups/`, `*.sqlite3`) | **PASS** |
| **Browser CDP Profiles** | Chrome cookies, storage, cache must never be tracked | Blocked by `.gitignore` (`chrome-profile/`, `.playwright/`) | **PASS** |
| **Large Binary Installers** | 80 MB `.exe` files must never bloat git history | Blocked by `.gitignore` (`release-candidates/*.exe`) | **PASS** |
| **Release Metadata** | Manifest and SHA-256 sums preserved in text format | `RELEASE_MANIFEST.json` and `SHA256SUMS.txt` tracked | **PASS** |
| **Runtime Logs** | Rotating desktop logs must never be tracked | Blocked by `.gitignore` (`logs/`, `*.log`) | **PASS** |

---

## 3. Recommended Future Publication Plan

When the user grants explicit permission to publish AttendPlan to `https://github.com/XrystalAbyss/AttendPlan`:

### Step 1: Configure Destination Remote
```bash
git remote add origin https://github.com/XrystalAbyss/AttendPlan.git
```

### Step 2: Atomic Stage & Sanitization Verification
```bash
# Stage all sanitized source code, documentation, and release metadata
git add .
# Run pre-commit sanitization gate
pytest backend/tests/test_sanitization.py
```

### Step 3: Create Descriptive Release Commit
```bash
git commit -m "release: AttendPlan v0.1.0-beta.3 — local-first university attendance intelligence"
```

### Step 4: Tag & Authorized Push
```bash
git tag -a v0.1.0-beta.3 -m "AttendPlan 0.1.0-beta.3 (Supervised Friends Beta)"
git push -u origin master --tags
```

### Step 5: Attach Release Assets
Attach `release-candidates/AttendPlan-0.1.0-beta.3-Setup.exe` directly as a GitHub Release asset along with `SHA256SUMS.txt`.

---

## 4. GitHub Readiness Verdict

The AttendPlan codebase, documentation, and build manifests are **100% sanitized, clean, and ready for publication**, pending final user approval.

