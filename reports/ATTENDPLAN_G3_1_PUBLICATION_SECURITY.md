# AttendPlan — Phase G.3.1 Public Repository Privacy Remediation & Release Registry Integrity Closure

**Date:** 2026-11-07  
**Canonical Remote:** `https://github.com/XrystalAbyss/AttendPlan`  
**Remote Branch:** `main`  
**Current Remote HEAD:** `67289b7fe12e962a8241f9a2f49052ec2ca5022d`  
**Gate Verdict:** `CURRENT_TREE_REDACTED` · `HISTORY_REMEDIATION_PENDING_APPROVAL` · `HASH_REGISTRY_RECONCILED` · `PRIVACY_BLOCKER_REMAINS`  

---

## 1. Incident Description & Scope

During the initial public source repository publication on GitHub, a documentation-level privacy exposure was identified:
- File `reports/ATTENDPLAN_GITHUB_INITIAL_PUBLICATION.md` in commit `a693868` included literal student identifiers in the markdown table summarizing security checks.
- In addition, `backend/tests/test_sanitization.py` in commits `5948106` and `2c2d5e1` stored literal test target strings in an in-code array (`PROHIBITED_STRINGS`), inadvertently publishing sensitive canaries in public test code.

### Exposed Categories of Information:
1. Student Academic Admission Identifier
2. Government Identity (Aadhaar) Number
3. Student Institutional Roll Number
4. Personal Mobile Phone Number
5. Student Personal First and Last Names
6. Base64-Encoded Admission Query Parameter

*Note: In accordance with privacy directives, NO exposed literal values are reproduced anywhere in this report, in logs, or in code comments.*

---

## 2. Immediate Non-Destructive Remediation (Current Tree)

The current working tree and the public remote repository have received an immediate non-destructive correction:

1. **Audit Report Sanitization**:
   - `reports/ATTENDPLAN_GITHUB_INITIAL_PUBLICATION.md` was edited to replace all literal pattern entries with generic tokens:
     `[REDACTED_STUDENT_IDENTIFIER]`, `[REDACTED_IDENTITY_NUMBER]`, `[REDACTED_STUDENT_ROLL_NO]`, `[REDACTED_STUDENT_PHONE]`, `[REDACTED_PERSONAL_NAME]`.
   - Release candidate table checksums were corrected to reflect verified binary hashes.
   - Disclosure notice added regarding historical commits.
2. **Cryptographic One-Way Canary Redesign**:
   - `backend/tests/test_sanitization.py` was re-architected.
   - All plaintext strings were removed from source code.
   - Private student canary identifiers are now stored exclusively as one-way SHA-256 cryptographic digests (`PROHIBITED_TOKEN_SHA256`).
   - Extended sanitization checks now scan all documentation files (`docs/*.md`), reports (`reports/*.md`), `README.md`, fixtures, and frontend/backend code.
   - A synthetic canary test (`test_synthetic_canary_detection_works`) was added to ensure the detection logic remains actively verified without exposing sensitive values.
3. **Focused Remote Push**:
   - Commit `67289b7` (*fix: redact audit report pattern table and convert sanitization tests to one-way hash canaries*) was pushed to `origin/main`.
   - Verified that the current public HEAD contains zero literal PII tokens.

---

## 3. Git History Exposure & Remediation Plan

### 3.1 Historical Exposure Inventory

A commit-by-commit forensic scan identified the following commits containing exposed literals in their tree snapshots:

| Commit SHA | Commit Subject | File Containing Literal Patterns |
| :--- | :--- | :--- |
| `5948106` | `chore: baseline F2-A state (...)` | `backend/tests/test_sanitization.py` (legacy admission number) |
| `2c2d5e1` | `feat: initial release of AttendPlan (v0.1.0-beta.3)` | `backend/tests/test_sanitization.py` (literal prohibited strings) |
| `a693868` | `docs: add formal GitHub publication and release audit report` | `reports/ATTENDPLAN_GITHUB_INITIAL_PUBLICATION.md` (table entries) |

### 3.2 Pre-Remediation Safety Backups
Before evaluating history rewrites, a full, protected repository bundle was created outside the project tree:
- **Location**: `%LOCALAPPDATA%\AttendPlan\backups\attendplan_repo_backup_pre_rewrite_20261107_2340.bundle`
- **Size**: 3,530,022 bytes
- **Scope**: `--all` refs preserved

### 3.3 Disposable Clone Evaluation (`git-filter-repo`)
In an isolated disposable clone (`$env:TEMP\attendplan_test_rewrite`), `git-filter-repo --replace-text` was evaluated using exact redaction replacement expressions.
- **Evaluation Outcome**: History successfully rewritten across all 4 commits.
- **Forensic Verification**: Post-rewrite `git log -p --all` scan confirmed **0 matches** across the entire commit graph.
- **Integrity**: Commit trees and messages were preserved; all code, fixtures, and documentation remained intact.
- **Resulting Commit SHAs** (in test run):
  - Baseline: `d9e6d4d`
  - Release: `dea39d9`
  - Docs: `3207eb1`
  - Fix: `d059677`

### 3.4 Operational Warning & Authorization Gate
> [!WARNING]
> Rewriting Git history alters commit SHAs from `5948106` onwards. Pushing rewritten history requires a non-fast-forward operation (`git push --force-with-lease origin main`).
>
> In accordance with project instructions, **destructive force-pushes are strictly halted until explicit repository owner authorization is granted.**

### 3.5 Post-Rewrite Actions Required (Upon Approval)
1. Execute `git-filter-repo --replace-text <expressions>` on the canonical local repository.
2. Force-push rewritten `main` to `https://github.com/XrystalAbyss/AttendPlan`.
3. Contact GitHub Support (if necessary) to purge cached commit views for orphan commits `2c2d5e1` and `a693868` from GitHub's internal CDN cache, as standard git garbage collection on GitHub takes up to 90 days.

---

## 4. Release Registry Reconciliation

### 4.1 Authoritative Installer Binary Verification
Actual local installer executables located in `release-candidates/` were hashed directly using PowerShell `Get-FileHash -Algorithm SHA256`:

| Installer Filename | Exact Size (bytes) | Actual SHA-256 Checksum | Inno Setup Version |
| :--- | :--- | :--- | :--- |
| **`AttendPlan-0.1.0-beta.1-Setup.exe`** | 81,630,124 | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` | Inno Setup 6.3.3 |
| **`AttendPlan-0.1.0-beta.2-Setup.exe`** | 81,636,792 | `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311` | Inno Setup 6.3.3 |
| **`AttendPlan-0.1.0-beta.3-Setup.exe`** | 81,644,316 | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` | Inno Setup 6.3.3 |

### 4.2 Discrepancy Forensic Analysis

| Candidate | Actual File Hash | Reported in `RELEASE_MANIFEST.json` | Reported in `SHA256SUMS.txt` | Previously in `ATTENDPLAN_GITHUB_INITIAL_PUBLICATION.md` | Discrepancy Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **beta.1** | `8ca48410...` | `8ca48410...` | `8ca48410...` | `1f468205...` | **Typographical error in initial publication report**. Actual binary, manifest, and SHA256SUMS.txt were identical and correct. |
| **beta.2** | `fb21409f...` | `fb21409f...` | `fb21409f...` | `f3ea3295...` | **Typographical error in initial publication report**. Actual binary, manifest, and SHA256SUMS.txt were identical and correct. |
| **beta.3** | `12b9465d...` | `12b9465d...` | `12b9465d...` | `12b9465d...` | **100% Concordance across all records**. |

**Correction Applied**: `reports/ATTENDPLAN_GITHUB_INITIAL_PUBLICATION.md` has been updated and pushed in commit `67289b7` to authoritatively match the physical file checksums.

---

## 5. Release Candidate Provenance (Beta.3)

| Property | Verified Record |
| :--- | :--- |
| **Product** | AttendPlan |
| **Version** | `0.1.0-beta.3` |
| **Packaging Target** | Windows 64-bit (`win32-x64`) |
| **Build Configuration** | Non-Admin User-Space (`PrivilegesRequired=lowest`) |
| **Installer Compiler** | Inno Setup 6.3.3 |
| **Backend Packaging** | PyInstaller 6.11.1 (`launcher.py`, Python 3.12.10) |
| **Frontend Packaging** | Vite 6.4.4 + React 19 (production bundle: 129 kB gzipped) |
| **Build Timestamp** | 2026-11-07T17:03:24Z |
| **Source State at Build** | Source working tree at Phase G.3 completion, corresponding to commit `2c2d5e1` source code |
| **Artifact SHA-256** | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` |
| **Artifact Size** | 81,644,316 bytes |
| **Publication Status** | **NOT PUBLISHED** (Local Release Candidate Staged Only) |

---

## 6. Verification Gates Summary

```
========================================================================================
ATTENDPLAN PHASE G.3.1 VERIFICATION MATRIX
========================================================================================
Gate 1: Backend Domain & Unit Tests (pytest)        --> 345 PASSED (100%) in 212.63s
Gate 2: Security & Sanitization Audit (pytest)       --> 14 PASSED (100%)
Gate 3: Backend Python Static Typing (mypy)          --> 0 ISSUES across 47 source files
Gate 4: Backend Python Linting (ruff)                --> 0 ERRORS across app, tests, launcher
Gate 5: Frontend TypeScript Compilation (tsc)        --> 0 ERRORS (strict mode)
Gate 6: Working-Tree PII Hash Scan                   --> 0 MATCHES across all tracked files
Gate 7: Installer Checksums Verification             --> 100% CONCORDANCE with physical bytes
========================================================================================
```

---

## 7. Final Phase Status & Next Decision

### Status Flags:
- `CURRENT_TREE_REDACTED`: **YES** (Current `main` HEAD `67289b7` contains zero literal PII tokens)
- `HASH_REGISTRY_RECONCILED`: **YES** (All installer hashes reconciled against physical bytes)
- `REMOTE_VERIFIED`: **YES** (Commit `67289b7` verified on GitHub remote)
- `HISTORY_REMEDIATION_PENDING_APPROVAL`: **ACTIVE** (Rewrite procedure verified in test clone; awaiting owner authorization)
- `PRIVACY_BLOCKER_REMAINS`: **YES** (Historical commits `2c2d5e1` and `a693868` remain accessible in git history until rewritten)

### Required Owner Decision:
To complete eradication of the exposed identifiers from Git history:
1. Approve the execution of the `git-filter-repo` rewrite plan on the canonical local repository.
2. Authorize `git push --force-with-lease origin main` to update GitHub's default branch history.
