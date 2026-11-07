# F2-E.1 current implementation status

Updated 21 October 2026. This page supersedes older milestone counts, assumed semester-month mappings, and authentication descriptions in the original README and architecture documents. It does not authorize live work.

- The app is local-first and contacts the university portal only through its portal features. It is not air-gapped.
- Existing user-opted-in login supports a locally saved mobile number and Windows Credential Manager TOTP. Secrets must never be requested, inspected or logged by a coding agent. The current takeover request requires a private supervised handoff before any new login or live import.
- Credential-backend validation now requires the native Windows implementation; arbitrary positive-priority or deceptively named backends are rejected. Automated tests substitute in-memory credential storage.
- Saved attendance, marks and results are independent datasets. Semester 4 has a previously approved 17-course attendance summary and 15-subject internal-marks capture. SGPA/CGPA and other semesters' performance are not verified.
- The previously approved attendance archive completed 107 report scopes: 3 month saves, 2 duplicate summaries and 102 unverified scopes. August–October 2026 are locally available. Older month failures and quarantined summaries remain explicit gaps, never fabricated absences.
- Archive scope comes from verified dependent selectors, with reviewed calendar-month candidates bounded by academic-year labels and today's date. Candidates do not establish the semester's actual teaching months. There is no universal odd/even month assumption in the archive planner.
- Source snapshots remain immutable. Analytics select the latest observation for a reported slot within the selected term, preventing repeated reports from inflating attendance.
- Display standing is Risk below exactly 75%, Caution at or above 75% when no complete class/lab session can be missed, and Safe otherwise. Zero delivered periods remain unrecorded. The backend's legacy mathematical SAFE status still means threshold-compliant; the UI computes Caution from exact counts.
- A two-period lab changes attended/delivered counts by +2/+2 when attended and 0/+2 when missed. Two separate one-period rows must not be doubled again.
- A single theme preference drives dark sepia, light sepia and system mode. Explicit themes ignore operating-system changes and persist across reloads.
- Synthetic seeding, the older one-semester import and performance capture remain disabled by default. The separate archive requires an explicit reviewed-plan approval. Restarted archive workers pause; resumption requires approval of the original scope and skips recorded checkpoints.
- Startup connection and refresh are separate opt-ins. Both are currently off for this supervised audit. No login is needed to use saved records.

Run the complete gates with `run-tests.ps1`. Test setup isolates SQLite/settings and prevents real CDP connections; authentication tests use only synthetic credentials. Migration tests upgrade/downgrade disposable databases. Unit and component passes do not establish live portal compatibility or complete historical coverage.

Do not commit, push, reset data, re-enroll the authenticator or start F3 without authorization. See the current `ATTENDPLAN_F2E1_CODEX_REPORT.md` for verification results and remaining blockers.
