# AttendPlan — Phase G.3.1 Git History Rewrite Closure & Release Integrity Verification

**Date:** 2026-11-08  
**Canonical Remote Repository:** `https://github.com/XrystalAbyss/AttendPlan`  
**Remote Branch:** `refs/heads/main`  
**Original Contaminated HEAD:** `2900ed5d600e5a4c9b7cf220076564b05d626be5`  
**Rewritten Sanitized HEAD:** `02b2eb655b640e6a3801447da626c3366846b487`  
**Verification Verdict:** `HISTORY_REMEDIATED` · `REMOTE_VERIFIED` · `HASH_REGISTRY_RECONCILED` · `ZERO_PII_REACHABLE`  

---

## 1. Executive Summary

Under explicit repository owner authorization, the Git history of AttendPlan on `refs/heads/main` has been rewritten in an isolated clone, forensically audited, and pushed to GitHub via a guarded `git push --force-with-lease`.

All exposed literal personal identifiers and their corresponding unsalted SHA-256 digests were completely eradicated from all historical commits, blobs, and tree snapshots. All five logical commits were preserved, along with the full codebase, test suite, and release manifest integrity.

---

## 2. Remote State & Commit Lineage

### 2.1 Commit Lineage Mapping (Pre-Rewrite vs. Post-Rewrite)

All five logical commits in the repository ancestry were preserved in exact chronological order:

| Index | Original Commit SHA | Rewritten Commit SHA | Commit Message | Files Redacted |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `5948106ddc6a` | `d9e6d4d61562` | `chore: baseline F2-A state (...)` | `backend/tests/test_sanitization.py` (legacy admission number) |
| **2** | `2c2d5e1ba50e` | `dea39d9abec9` | `feat: initial release of AttendPlan (v0.1.0-beta.3)` | `backend/tests/test_sanitization.py` (prohibited strings array) |
| **3** | `a69386873cba` | `3207eb1df9f5` | `docs: add formal GitHub publication and release audit report` | `reports/ATTENDPLAN_GITHUB_INITIAL_PUBLICATION.md` (table patterns) |
| **4** | `67289b7fe12e` | `1338a7f5d553` | `fix: redact audit report pattern table and convert sanitization tests to one-way hash canaries` | `backend/tests/test_sanitization.py` (replaced real digests with synthetic canary digests) |
| **5** | `2900ed5d600e` | `02b2eb655b64` | `docs: add Phase G.3.1 privacy remediation and release integrity audit report` | Re-anchored to sanitized parent `1338a7f` |

### 2.2 Remote Verification via GitHub API
The live remote branch `main` was queried via the GitHub API:
- **Remote Branch Ref**: `refs/heads/main`
- **Head SHA**: `02b2eb655b640e6a3801447da626c3366846b487`
- **Verification Source**: `GET /repos/XrystalAbyss/AttendPlan/commits/main` -> HTTP 200 OK
- **Tags & Other Branches**: 0 tags, 0 other branches, 0 pull requests.

---

## 3. Pre-Rewrite Backups Verification

Two independent, verified local backups are preserved in protected storage (`%LOCALAPPDATA%\AttendPlan\backups\`):

1. **`attendplan_repo_backup_pre_rewrite_20261107_2340.bundle`**:
   - Size: 3,530,022 bytes
   - Verification: `git bundle verify` -> OK (4 refs recorded)
2. **`attendplan_repo_backup_pre_rewrite_5commits_20261107_2355.bundle`**:
   - Size: 3,534,161 bytes
   - Verification: `git bundle verify` -> OK (contains full 5-commit pre-rewrite history)

*Notice: These bundles reside exclusively on local protected disk outside the repository tree and are strictly excluded from upload or network distribution.*

---

## 4. Remediation Architecture & Digest Purge

### 4.1 Plaintext and Digest Redaction Rules
To ensure complete non-reversibility, both the original literal identifiers and their unsalted SHA-256 digests were scrubbed from all historical commits:

| Category | Replaced Value in History | Replacement in History |
| :--- | :--- | :--- |
| **Student Admission No** | Plaintext admission id | `[REDACTED_STUDENT_IDENTIFIER]` |
| **Aadhaar Identity** | Plaintext 12-digit number | `[REDACTED_IDENTITY_NUMBER]` |
| **Student Roll No** | Plaintext roll number | `[REDACTED_STUDENT_ROLL_NO]` |
| **Personal Phone No** | Plaintext 10-digit number | `[REDACTED_STUDENT_PHONE]` |
| **Student Personal Name** | Plaintext first & last names | `[REDACTED_PERSONAL_NAME]` / `[REDACTED_PERSONAL_SURNAME]` |
| **Admission Query Token** | Base64 admission parameter | `[REDACTED_BASE64_ADMISSION_QUERY]` |
| **Reversible Canary Digests** | Unsalted SHA-256 hashes of real identifiers | One-way SHA-256 hashes of purely synthetic strings (`SYNTHETIC_CANARY_*`) |

### 4.2 Synthetic Canary Test Architecture
[`backend/tests/test_sanitization.py`](file:///c:/Users/astra/Desktop/Project/AttendPlan/backend/tests/test_sanitization.py) now operates with:
- Zero real student data or real-data digests.
- Canaries computed from synthetic canary strings.
- Active unit test (`test_synthetic_canary_detection_works`) confirming the detection engine trips on canaries.
- Regex pattern scanning for private keys, anti-tamper scripts, and analytics trackers across all code, reports, and documentation.
- Real-data audit scripts and exact reference lists maintained strictly offline in private scratch storage.

---

## 5. Forensic Scan Results

A comprehensive forensic audit of the rewritten repository was executed:

```
========================================================================================
FORENSIC REWRITTEN REPOSITORY AUDIT
========================================================================================
1. Historical Commit Log Scan (git log -p --all)     --> 0 VIOLATIONS FOUND
2. Total Logical Commits in Ancestry                 --> 5 COMMITS (100% PRESERVED)
3. Tracked Binary Installers (*.exe)                 --> 0 (Strictly .gitignored)
4. Tracked SQLite Databases (*.sqlite3)              --> 0 (Strictly .gitignored)
5. Tracked Browser Profiles (chrome-profile)         --> 0 (Strictly .gitignored)
6. Source Code Identity (backend/app, frontend/src)  --> 100% IDENTICAL TO PRE-REWRITE
7. Automated Pytest Test Suite                       --> 345 PASSED (100%)
8. Automated Vitest Test Suite                       --> 38 PASSED (100%)
9. Static Type Checking (mypy & tsc)                 --> 0 ERRORS across all files
========================================================================================
```

---

## 6. Guarded Remote Push Execution

The remote push was executed strictly in accordance with safety directives:
- **Command Used**:
  ```bash
  git push --force-with-lease=refs/heads/main:2900ed5d600e5a4c9b7cf220076564b05d626be5 origin HEAD:refs/heads/main
  ```
- **Execution Result**:
  ```
  To https://github.com/XrystalAbyss/AttendPlan.git
   + 2900ed5...02b2eb6 HEAD -> main (forced update)
  ```
- No blind `--force` or `--mirror` was used.
- No other refs, tags, or branches were touched.

---

## 7. Release Candidates & Checksums Concordance

Physical installer binaries on disk in `release-candidates/` remain 100% concordant with manifests and reports:

| Installer Binary | Byte Size | Physical SHA-256 Checksum | Manifest Status |
| :--- | :--- | :--- | :--- |
| **`AttendPlan-0.1.0-beta.1-Setup.exe`** | 81,630,124 | `8ca484102a83739165cae2f81c07b0448f987abb6708e47893d13c1d3adbdbcc` | 100% Match |
| **`AttendPlan-0.1.0-beta.2-Setup.exe`** | 81,636,792 | `fb21409f226415472e750d1b490ac2979e4f31d18227103b95fa31e777837311` | 100% Match |
| **`AttendPlan-0.1.0-beta.3-Setup.exe`** | 81,644,316 | `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5` | 100% Match |

---

## 8. GitHub Cache Remediation & Support Template

### 8.1 GitHub Internal Cache Behavior
Although the default branch `main` has been rewritten, GitHub’s server infrastructure retains unreachable / orphaned commits (`5948106`, `2c2d5e1`, `a693868`, `67289b7`, `2900ed5`) in its internal repository cache until standard background garbage collection runs (typically up to 90 days). Anyone with direct commit URLs could theoretically view cached snapshots until cached views are cleared.

### 8.2 GitHub Support Ticket Template
To request immediate purging of unreachable cached commits, submit a ticket via [GitHub Support](https://support.github.com):

```text
Subject: Request to clear cached orphan commits containing sensitive personal data

Repository: https://github.com/XrystalAbyss/AttendPlan
Affected Branch: main

Description:
We have completed an authorized Git history rewrite using git-filter-repo to remove 
inadvertently published personal student identifiers from our repository history on branch 'main'.
The rewritten branch has been pushed with --force-with-lease (new HEAD: 02b2eb655b640e6a3801447da626c3366846b487).

We kindly request that GitHub Support run git gc / prune to clear unreachable commit objects 
and purge the internal commit-view cache for the orphaned commit SHAs:
- 5948106ddc6adc83fbee554228c5ce821fc53b8c
- 2c2d5e1ba50ed9f7789a0278dbf349712ad9bf1b
- a69386873cbaa1c4fe144df0d7d4766c02ff916f
- 67289b7fe12e962a8241f9a2f49052ec2ca5022d
- 2900ed5d600e5a4c9b7cf220076564b05d626be5

Thank you for your assistance.
```

---

## 9. Local Repository Health & Tracking Restoration

The canonical local repository at `C:\Users\astra\Desktop\Project\AttendPlan` was cleanly reset to the new remote `origin/main` (`02b2eb6`):
- `git status` confirmed: `On branch main, Your branch is up to date with 'origin/main'. nothing to commit, working tree clean`.
- Untracked personal databases (`*.sqlite3`), dedicated Chrome profiles, and installer binaries remain completely undisturbed.
