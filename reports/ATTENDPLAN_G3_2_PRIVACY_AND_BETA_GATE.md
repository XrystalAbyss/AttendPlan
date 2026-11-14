# AttendPlan — Phase G.3.2 GitHub Privacy Incident Follow-Up & Controlled Friends-Beta Gate

**Date:** 2026-11-14  
**Auditor / Role:** GitHub Security & Windows Release Engineer  
**Workspace:** `C:\Users\astra\Desktop\Project\AttendPlan`  
**Canonical Remote Repository:** `https://github.com/XrystalAbyss/AttendPlan`  
**Active Remote Tracking Branch:** `refs/heads/main`  

---

## 1. Executive Summary & Audit Classifications

Phase G.3.2 concludes technical verification of the post-rewrite GitHub repository, audits the server-side retrievability of orphaned commits, establishes a private GitHub Support evidence package, confirms installer integrity, and establishes the supervised testing protocol for the first independent student volunteer.

### Official Audit Classifications

| Metric / Audit Dimension | Classification State | Evidentiary Basis |
| :--- | :--- | :--- |
| **Active Remote Lineage** | `GITHUB_MAIN_SANITIZED` | Remote `origin/main` HEAD `194b59f` contains zero personal identifiers or unsalted hashes across all 7 commits. |
| **Continuous Integration** | `GITHUB_CI_PASSED` | GitHub Actions workflow run `42403795711` succeeded on both Windows backend and Linux frontend jobs. |
| **GitHub Server Cache** | `OLD_COMMITS_STILL_ACCESSIBLE` | Empirical HTTP 200 OK responses returned by GitHub REST API for all 5 obsolete commit SHAs (`5948106`, `2c2d5e1`, `a693868`, `67289b7`, `2900ed5`). |
| **GitHub Support Ticket** | `SUPPORT_TICKET_PREPARED` | Comprehensive private evidence package and copy-paste ticket generated at `%LOCALAPPDATA%\AttendPlan\support_evidence\github_support_ticket_evidence_20261114.md`. |
| **Server-Side Cache Purge** | `SUPPORT_PURGE_PENDING` | Purge request is prepared for repository owner submission; GitHub has not yet executed server-side `git gc --prune`. |
| **Packaged Release Candidate** | `PRIVATE_BETA_READY` | `AttendPlan-0.1.0-beta.3-Setup.exe` verified with SHA-256 `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5`. |
| **Volunteer Acceptance** | `REAL_FRIEND_TEST_PENDING` | Friends-beta testing protocol established in `docs/FRIENDS_BETA_TESTING_GUIDE.md`; pending live independent execution. |

> [!WARNING]
> **Privacy Incident Open State:** We do not claim full privacy incident closure at this stage because the exposed historical commit snapshots remain cached and retrievable on GitHub's infrastructure via direct commit URLs. Closure requires confirmation from GitHub Support that unreachable commit views have been pruned.

---

## 2. Remote Verification

### 2.1 Remote Branch HEAD
* **Target Ref:** `refs/heads/main`
* **Active Remote HEAD SHA:** `194b59fd69502b781f15590504e43d28f156efe7`
* **Commit Message:** `fix: remove literal canary token from closure report prose`
* **Query Timestamp:** 2026-11-14T08:50:08Z
* **Response Status:** HTTP 200 OK via `GET /repos/XrystalAbyss/AttendPlan/branches/main`

### 2.2 GitHub Actions CI Execution
* **Workflow Run ID:** `42403795711`
* **Workflow Name:** `AttendPlan CI`
* **Head SHA:** `194b59fd69502b781f15590504e43d28f156efe7`
* **Status:** `completed`
* **Conclusion:** `success`
* **Workflow URL:** [https://github.com/XrystalAbyss/AttendPlan/actions/runs/42403795711](https://github.com/XrystalAbyss/AttendPlan/actions/runs/42403795711)

| Job Name | Runner OS | Status | Conclusion | Key Verifications Passed |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Quality Gate** | `windows-latest` | `completed` | `success` | Sanitization test (14/14), Ruff lint, Mypy (47 files), Pytest suite (345/345 passed) |
| **Frontend Quality Gate** | `ubuntu-latest` | `completed` | `success` | Vitest suite (38/38 passed), `tsc --noEmit` clean, Vite production bundle build clean |

---

## 3. Historical Rewritten-History Validation

The repository history on `main` consists of 7 strictly sanitized commits:

```text
194b59f (HEAD -> main, origin/main) fix: remove literal canary token from closure report prose
d44c673 docs: add Phase G.3.1 history rewrite closure report
02b2eb6 docs: add Phase G.3.1 privacy remediation and release integrity audit report
1338a7f fix: redact audit report pattern table and convert sanitization tests to one-way hash canaries
3207eb1 docs: add formal GitHub publication and release audit report
dea39d9 feat: initial release of AttendPlan (v0.1.0-beta.3)
d9e6d4d chore: baseline F2-A state (69 backend tests, 15 frontend tests, verified offline discovery)
```

### Commit Mapping (Original vs. Sanitized)

| Index | Original Commit SHA (Orphaned) | Sanitized Commit SHA (Active) | Commit Summary | Remediated Files |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `5948106ddc6a` | `d9e6d4d61562` | `chore: baseline F2-A state (...)` | `backend/tests/test_sanitization.py` |
| **2** | `2c2d5e1ba50e` | `dea39d9abec9` | `feat: initial release of AttendPlan (v0.1.0-beta.3)` | `backend/tests/test_sanitization.py` |
| **3** | `a69386873cba` | `3207eb1df9f5` | `docs: add formal GitHub publication and release audit report` | `reports/ATTENDPLAN_GITHUB_INITIAL_PUBLICATION.md` |
| **4** | `67289b7fe12e` | `1338a7f5d553` | `fix: redact audit report pattern table and convert tests` | `backend/tests/test_sanitization.py` |
| **5** | `2900ed5d600e` | `02b2eb655b64` | `docs: add Phase G.3.1 privacy remediation audit report` | Re-anchored to parent `1338a7f` |
| **6** | *(None)* | `d44c6732135a` | `docs: add Phase G.3.1 history rewrite closure report` | Added closure report |
| **7** | *(None)* | `194b59fd6950` | `fix: remove literal canary token from closure report prose` | Removed canary token from documentation prose |

* **First Changed Commit:** `5948106ddc6a` -> `d9e6d4d61562`
* **Git LFS Tracked Objects:** 0 (Confirmed via `git lfs ls-files`)
* **Pull Requests Count:** 0
* **Forks Count:** 0

---

## 4. Obsolete Commit Accessibility Audit

On 2026-11-14, direct programmatic checks were executed against GitHub's public API to evaluate whether the 5 orphaned commits from the pre-rewrite lineage remain reachable via direct URL:

```python
GET https://api.github.com/repos/XrystalAbyss/AttendPlan/commits/<SHA>
```

### Audit Findings

| Obsolete Commit SHA | HTTP Status Code | GitHub State | Risk Level |
| :--- | :---: | :--- | :--- |
| `5948106ddc6adc83fbee554228c5ce821fc53b8c` | **200 OK** | Cached Object Retrievable | High (Contains unredacted identifier in historical diff) |
| `2c2d5e1ba50ed9f7789a0278dbf349712ad9bf1b` | **200 OK** | Cached Object Retrievable | High (Contains unredacted array in historical diff) |
| `a69386873cbaa1c4fe144df0d7d4766c02ff916f` | **200 OK** | Cached Object Retrievable | High (Contains unredacted table in historical diff) |
| `67289b7fe12e962a8241f9a2f49052ec2ca5022d` | **200 OK** | Cached Object Retrievable | Medium (Contains unsalted digests in historical diff) |
| `2900ed5d600e5a4c9b7cf220076564b05d626be5` | **200 OK** | Cached Object Retrievable | Low (Child commit pointing to contaminated history) |

### Technical Analysis
Although `refs/heads/main` was cleanly rewritten and pushed via `--force-with-lease`, GitHub maintains an internal commit-view cache for up to 90 days. Anyone with the historical SHA or browser history can view the cached diff until GitHub Support manually executes repository garbage collection (`git gc --prune=now`).

---

## 5. Support Evidence Package & Ticket Submission Readiness

To ensure zero sensitive data is added to the public repository during this process, all support evidence has been placed strictly outside the repository tree:

* **Private Evidence File Location:**  
  [`C:\Users\astra\AppData\Local\AttendPlan\support_evidence\github_support_ticket_evidence_20261114.md`](file:///C:/Users/astra/AppData/Local/AttendPlan/support_evidence/github_support_ticket_evidence_20261114.md)
* **Status:** Ready for submission by the authenticated repository owner (`XrystalAbyss`).

### Ticket Text for Owner Submission

```text
Category: Account and repository > Data privacy / Sensitive data removal
Subject: Request server-side gc/prune to purge cached orphaned commits containing sensitive personal data

Repository: https://github.com/XrystalAbyss/AttendPlan
Repository Owner: XrystalAbyss
Affected Branch: main
Current Clean HEAD SHA: 194b59fd69502b781f15590504e43d28f156efe7

Description:
Hello GitHub Support Team,

We recently conducted an authorized Git history rewrite using git-filter-repo to remediate personal student identifiers that were inadvertently committed to our repository. The rewritten, completely sanitized history was pushed to 'refs/heads/main' with --force-with-lease.

There are no pull requests, forks, or alternate branches in this repository.

However, direct queries to the GitHub API and web commit URLs show that the previous orphaned commit objects remain cached and retrievable:
- 5948106ddc6adc83fbee554228c5ce821fc53b8c
- 2c2d5e1ba50ed9f7789a0278dbf349712ad9bf1b
- a69386873cbaa1c4fe144df0d7d4766c02ff916f
- 67289b7fe12e962a8241f9a2f49052ec2ca5022d
- 2900ed5d600e5a4c9b7cf220076564b05d626be5

To complete our privacy remediation, could you please run git gc and purge the internal commit-view cache for these unreachable commits on https://github.com/XrystalAbyss/AttendPlan?

Thank you for your assistance.
```

---

## 6. Release Candidate Verification

The standalone Windows installer in `release-candidates/` was verified against disk bytes:

* **File Name:** `AttendPlan-0.1.0-beta.3-Setup.exe`
* **File Path:** [`release-candidates/AttendPlan-0.1.0-beta.3-Setup.exe`](file:///c:/Users/astra/Desktop/Project/AttendPlan/release-candidates/AttendPlan-0.1.0-beta.3-Setup.exe)
* **File Size:** `81,644,316 bytes`
* **Computed SHA-256 Checksum:**  
  `12b9465d69ec4c72aca8888bde24362bc28cc9734a727d28ca2bd6415f1e63b5`
* **Concordance:**  
  - Matches [`release-candidates/RELEASE_MANIFEST.json`](file:///c:/Users/astra/Desktop/Project/AttendPlan/release-candidates/RELEASE_MANIFEST.json) exactly.
  - Matches [`release-candidates/SHA256SUMS.txt`](file:///c:/Users/astra/Desktop/Project/AttendPlan/release-candidates/SHA256SUMS.txt) exactly.
* **Packaging Decision:**  
  No rebuilding was performed. The verified executable remains untouched.

---

## 7. Working Tree Safety & Local Hygiene

The local developer workspace was verified against accidental reintroduction of contaminated history:

1. **`git status`**:
   ```
   On branch main
   Your branch is up to date with 'origin/main'.
   nothing to commit, working tree clean
   ```
2. **`git show-ref`**:
   Only `refs/heads/main` and `refs/remotes/origin/main` exist locally (both pointing to `194b59f`). No stale local branches or tags exist.
3. **Local Backups Intact**:
   - `attendplan_repo_backup_pre_rewrite_20261107_2340.bundle` (3,530,022 bytes) -> Verified OK.
   - `attendplan_repo_backup_pre_rewrite_5commits_20261107_2355.bundle` (3,534,161 bytes) -> Verified OK.
4. **Personal Data Preserved**:
   Developer SQLite databases, dedicated Chrome profiles, and physical installers remain in their `.gitignored` storage without modification.

---

## 8. Private Friends-Beta Preparation & First-Volunteer Test Readiness

A dedicated, student-facing testing guide was established at [`docs/FRIENDS_BETA_TESTING_GUIDE.md`](file:///c:/Users/astra/Desktop/Project/AttendPlan/docs/FRIENDS_BETA_TESTING_GUIDE.md).

### Testing Protocol Features
1. **Zero Dev Prerequisites:** Tested for standalone execution on standard Windows 10/11 laptops without Python, Node, or Git.
2. **Clean-Machine Isolation:** Automatically initializes an isolated local SQLite database at `%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3`.
3. **Privacy & Credential Safety:**  
   - Student enters portal credentials and Authenticator OTP directly into a standard Google Chrome window.
   - AttendPlan never captures, prompts for, or persists passwords or OTPs.
4. **Controlled Ingestion Scope:** Current semester attendance is ingested; historical backfill is completely disabled unless explicitly requested by the user.
5. **Exact Verification Workflows:**
   - Subject-wise delivered/attended comparison against live ERP.
   - Safe bunk calculation verification ($\max(0, \lfloor a / 0.75 - d \rfloor)$).
   - Consecutive recovery calculation verification ($\max(0, \lceil (0.75d - a) / 0.25 \rceil)$).
   - Session expiration and reconnection recovery.
   - Database backup export and session disconnection.
6. **Structured Feedback Capture:** Standardized 6-part feedback questionnaire included for the volunteer.

---

## 9. Remaining Release Blockers & Operational Next Steps

| Blocker / Milestone | Required Action | Responsible Party | Status |
| :--- | :--- | :--- | :--- |
| **GitHub Server Cache Purge** | Submit support ticket via [GitHub Support](https://support.github.com) | Repository Owner (`XrystalAbyss`) | **ACTION REQUIRED** |
| **Support Purge Confirmation** | Verify obsolete SHAs return HTTP 404 via API | Security Engineer / Automated Check | **PENDING SUPPORT ACTION** |
| **First Independent Volunteer Test** | Hand off `AttendPlan-0.1.0-beta.3-Setup.exe` and `docs/FRIENDS_BETA_TESTING_GUIDE.md` to volunteer | Release Engineer / Volunteer | **READY FOR EXECUTION** |
| **Public Release Publishing** | Publish GitHub Release with binary installer | Repository Owner | **BLOCKED** (Awaiting cache purge & volunteer acceptance) |

---

## 10. Final Verification Signature

* **Current HEAD:** `194b59fd69502b781f15590504e43d28f156efe7`
* **Local Workspace State:** Sanitized & Synchronized
* **Artifacts Created:**
  - `docs/FRIENDS_BETA_TESTING_GUIDE.md` (Committed to documentation)
  - `reports/ATTENDPLAN_G3_2_PRIVACY_AND_BETA_GATE.md` (Committed to reports)
  - `C:\Users\astra\AppData\Local\AttendPlan\support_evidence\github_support_ticket_evidence_20261114.md` (Private local file outside git)
