# AttendPlan F2-E.1 — implementation and pilot approval packet

20 October 2026 · Repository: C:\Users\astra\Desktop\Project\AttendPlan · Branch: master

## Outcome

**Code and synthetic gates verified. Live portal compatibility remains pending a supervised pilot.** Historical discovery, preview, navigation and validation blockers have been repaired. Marks and semester results are now supported in a separate local dashboard and separately gated capture path. No live portal extraction, authentication, attendance import, marks import, migration against the real database, commit, push, or F3 work was performed.

The user confirms that saved mobile/TOTP automated login already works. That setup is preserved. The pilot should use the existing application login flow privately under user supervision; do not reset, re-enroll, read, print or modify the credential. Do not ask the user to provide the mobile number, seed, QR code, OTP, password, cookie or authentication token in chat.

## Attendance safety fixes

- Dependent discovery traverses observed year options, then observes semester options after the year reload, then class options after the semester reload. It verifies each selection, bounds traversal, paces selection operations, and restores the original filters. It does not make year/semester/class Cartesian products or invent missing options.
- Static supplied HTML proves only its single explicitly selected tuple and remains NOT_CHECKED. It cannot authorize live import.
- Successfully traversed selector tuples persist as metadata-only discovery records in the existing job table. Preview and import use the same persisted discovery after a session/engine restart. Discovery creates no attendance terms or records. AVAILABLE means the selector combination is available, not that archived attendance is guaranteed to exist.
- Attendance navigation uses exact same-origin menu paths from an allowlist. No direct-URL/referrer fallback, substring-host match, arbitrary browser-tab reuse, swallowed readiness timeout, or forced JavaScript click remains in the revised extractor.
- All requested filters must exist uniquely and select successfully. Selected values are checked again after dependent reloads and Search. Search form targets and returned routes are restricted. Unexpected origin, login/MFA screen, access denial, missing filter, or unsupported reload stops extraction.
- HTML parsing uses a serialization of actual live selected DOM values, because HTML selected attributes can be stale after JavaScript changes. Parsed payload identity and result identity must both match the requested term/class before persistence. Invalid/quarantined extraction and percentage discrepancies are rejected.
- The first public historical pilot is exactly one semester and one subject-summary operation. Day-wise requests and implicit month enumeration are rejected. The internal explicit-month path validates every observation against the requested YYYY-MM; normal pilot approval cannot activate it.
- A fresh preview issues a one-use, 30-minute approval reference bound to the exact semester and summary scope. Changed scope, unknown term, reuse, expiration, missing approval, or disabled runtime gate prevents import. This reference is an application preview identifier, not an authentication credential.
- Session expiry and validation failure stop the job immediately. Completed/failed batch counters persist on partial failure. Cancellation refreshes database state and is not overwritten by a later job-state update. Cancellation boundaries are between atomic operations; it does not interrupt a committed transaction or an in-flight browser operation.
- Shared browser mutex remains in use for historical discovery, historical import, and performance capture. Progress and cancel queries exclude discovery/preview metadata jobs. The first bounded summary import is synchronous; it does not claim to be a background worker or automatic restart/resume system. Retrying requires a fresh preview and uses durable deduplication.
- Coverage stays PARTIAL unless stronger evidence is available. A guessed month count or one observed timetable batch does not declare a semester complete. The historical UI resolves the exact class and real database term ID rather than guessing an ID or selecting another class.
- Synthetic demo seeding remains disabled in normal runtime. Both live pilot gates remain unset in this work.

## Marks and semester results

A new **Marks & Results** tab supports all semesters for which snapshots are imported. Attendance data is stored separately from immutable, term-scoped performance snapshots. The additive migration creates only the new performance table and does not rewrite attendance tables. It was tested against a disposable existing-attendance database; it was not run against the user's database.

Supported fields when explicitly present in recognized table headers:

- Course code/name, internal marks, external marks, total/maximum marks, credits, letter grade, grade points and result status.
- Explicitly labelled SGPA and CGPA. The current GPA parser recognizes labelled text such as `SGPA: 8.2`; unsupported layouts fail or leave unavailable fields unknown rather than guessing values.
- Per-semester strongest/weakest recorded percentages where total and maximum are both available, missing-result notices, and a cross-semester table of portal-reported SGPA/CGPA. Missing totals are excluded from percentage comparisons. No institutional pass threshold, grade scale, GPA formula or unpublished result is inferred.

Capturing marks and capturing semester results are separate scopes. A performance preview cannot authorize an attendance import and vice versa. Each performance approval is bound to one discovered term and either marks or results, has a 30-minute expiry, and is consumed once. Performance import has its own default-off gate, ATTENDPLAN_ENABLE_PERFORMANCE_PILOT.

The live adapter resolves recognized menu labels (Marks/Internal Marks/Subject Marks or Results/Semester Results/Exam Results/Examination Results) to actual same-origin student routes. It does not invent exam endpoint URLs. Requested filters, returned route, form target and parsed format must be verified. If the institution uses different labels, routes, controls or headers, the pilot will stop for a focused adapter update. **Actual marks availability for every semester is not yet verified.** Missing or archived terms remain missing; imported snapshots never imply complete career coverage.

## Verification evidence

Final full run:

| Gate | Result |
| --- | --- |
| Backend pytest | 192 passed, one existing Starlette/AnyIO deprecation warning |
| Mypy | Clean across 64 app/test source files; existing note about untyped test bodies |
| Ruff | All checks passed; whole backend also checked |
| Frontend tests | 26 passed across 8 files |
| Frontend typecheck | Passed |
| Production build | Passed, including TypeScript project build |
| Sanitization fixtures | Expanded to all HTML files in the test/app fixture directories |
| Source hygiene scan | 158 files scanned at time of scan; no known private identifier matches or tracked private database/raw-reference paths |
| SQLite preservation | Consistent local backup refreshed through read-only source connection; integrity_check = ok |

Tests cover dependent traversal/restoration, persisted discovery with no attendance creation, exact-scope approval/reuse refusal, origin/menu/filter failures, invalid/quarantined and mismatched payload rejection, wrong year/month rejection, day-wise expiry with committed summary and accurate counters, cross-session cancellation, file-backed reopen/retry deduplication, marks/result parsing and missing values, semester isolation, performance approval isolation, migration upgrade/downgrade and additive migration preservation, and UI preview/reset/default-off behavior.

Known-pattern scanning is not a universal proof of zero PII. No real credential values were inspected. All new academic test records are explicitly synthetic. Existing user changes remain in place; the working tree is still dirty and includes earlier untracked milestone files. See the accompanying Git status rather than interpreting a tracked diff as the full change list.

## Data and authentication preservation

Tests set ATTENDPLAN_DB_PATH to a disposable workspace path before application imports. The real source SQLite database was only opened read-only for its consistent backup. Private backup: workspace work/private-prepilot-backup.sqlite3; keep it local and out of Git and sharing. The backup contains personal attendance data and is deliberately not attached as a deliverable.

The authentication/vault/settings files were not edited in this continuation. Authentication tests use existing synthetic/mocked keyrings. The real Windows Credential Manager entry, saved mobile settings, dedicated Chrome profile and working automated login flow were not read, cleared or changed. No application process was launched against the real database.

## Concrete proposed pilot — awaiting approval

**Proposed target:** one historical Semester 4, only if that exact semester is offered by verified dependent portal selectors. Its academic year and class must come from those selectors, not the synthetic fixture's year/class. If absent, stop and let the user select another discovered historical semester. No real selector inventory was read during this work, so this packet does not invent an actual term key.

**Stage 1 — approval requested now:** use the existing private login setup under user supervision and run read-only portal navigation/selector discovery. This may persist selector metadata locally; it must not import attendance or results. Check the actual attendance and performance menu labels without collecting raw HTML, screenshots of authentication, credentials or session-bearing URLs. Return an exact semester/year/class and bounded preview for final approval. Keep both import gates disabled.

**Stage 2 — separate exact-preview approval:** one subject-wise attendance summary for that exact semester; no day-wise months or other semesters. Refresh the consistent backup, enable only the historical pilot gate for the supervised run, create the exact preview and explicitly approve it. Check course totals, class/term identity, local durability and active-semester invariance. Disable the gate after the run. No automatic retry or second import.

**Stage 3 — separate performance approvals for the same semester:** preview and approve Subject Marks once, then Semester Results once. Enable only the performance pilot gate during these supervised operations. Compare portal-reported marks/SGPA/CGPA with the stored result and inspect the insights. Stop on unsupported controls, access denial, unpublished results or parsing ambiguity; do not treat unknown values as zero. Disable the gate afterwards.

After each stage, report only sanitized scope, counts, validation and reconciliation outcomes. Other semesters, day-wise expansion, bulk imports, Git push and F3 require new authorization. Multi-semester capability is implemented; population and actual portal compatibility are deliberately awaiting these pilot checks.

## Sequential follow-on prompt

Continue AttendPlan from C:\Users\astra\Desktop\Project\AttendPlan using ATTENDPLAN_F2E1_READY_REPORT.md and the current Git state. The user confirms saved mobile/TOTP automated login works: preserve it and use the existing private app flow only under the user's supervision; never inspect or request real authentication values. The final offline gates were 192 backend and 26 frontend tests, typing/lint/build clean. No live access/import or real database migration has run. Preserve the private SQLite backup and every existing local change. If the user approves Stage 1, perform only same-origin read-only discovery with the existing authenticated session and prepare an exact one-semester subject-summary preview from actual year/semester/class options, preferably historical Semester 4 if offered. Keep imports disabled and ask for approval of that concrete preview. Then, only with separate authorization, run the bounded attendance pilot and separately preview/approve marks and semester results for that same term. Validate live formats rather than assuming synthetic fixture compatibility. Stop safely on denied/unsupported routes or mismatches, report sanitized evidence, and refresh tests for any adapter change. No bulk imports, push or F3.

