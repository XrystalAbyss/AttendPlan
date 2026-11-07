# AttendPlan F2-E.1 audit and supervised pilot handoff

Date: 20 October 2026. Repository: `C:\Users\astra\Desktop\Project\AttendPlan`, branch `master`.

## Verdict

**Offline hardening verified; live historical pilot BLOCKED pending route and selector verification.** The prior F2-E report overstates discovery and runtime safety. This audit did not authenticate, connect to the live portal, run a real import, access the credential vault, commit, push, or start F3.

## Repository baseline

The initial Git state contained 25 modified tracked files and extensive untracked F2-B/F2-C/F2-D/F2-E work, including launchers, migrations, authentication, historical services, and tests. Those changes were retained. Git has no configured remote in the inspected configuration. The old report's clean-working-state claim is inaccurate. The attached final Git status identifies the actual working state; untracked files are not included in `git diff --stat`.

The repository AGENTS.md requires manual authentication, whereas existing login orchestration implements opt-in automated TOTP login. This audit preserved that existing code and the stored credential, but did not invoke it. Use manual private authentication for the proposed pilot.

## Data preservation

- Test runs set ATTENDPLAN_DB_PATH to a disposable workspace database before loading the app. Importing the database module otherwise initializes the default database.
- The live SQLite source was opened read-only and copied with SQLite's backup API, which includes committed WAL state consistently. Backup integrity_check returned `ok`.
- Private backup location: workspace `work/private-prepilot-backup.sqlite3`. This contains personal records: keep it local and out of Git and shared reports. It is not a deliverable attachment.
- No SQL migrations, deletes, resets, or test imports were applied to the live database. Existing Windows Credential Manager entries were neither read nor changed. No secret value was requested or inspected. No claim is made about vault contents or concurrent changes made by a running app.

## Changes applied

1. `backend/app/api/routes.py`: POST `/api/v1/demo/seed` now returns 403 unless ATTENDPLAN_ALLOW_SYNTHETIC_IMPORT is exactly `1`. The existing offline historical helper is a Python test utility, not an exposed historical import endpoint. GET sample remains an in-memory read. Normal runtime cannot seed through the demo endpoint.
2. The historical import endpoint now returns 409 by default. ATTENDPLAN_ENABLE_HISTORICAL_PILOT is an explicit maintenance gate, **not a declaration that live import is safe**. Even with it enabled, requests must contain exactly one term. Leave it unset until blockers below are fixed.
3. `historical_backfill_service.py`: unknown term keys no longer become guessed portal requests; the job fails before browser extraction. Day-wise authentication expiry and browser disconnection terminate the loop immediately and preserve committed batches.
4. `historical_discovery_service.py`: removed fabricated academic-year and Semester 5 fallbacks. Candidate dropdown combinations are NOT_CHECKED rather than AVAILABLE.
5. `backend/alembic/env.py`: explicit migration URLs take precedence over the runtime database environment setting. A test exposed that the previous order redirected migrations to the wrong database. First run: 152 passed, one migration failure, against an isolated disposable database. Fixed and rerun successfully.
6. Regression tests cover normal-runtime synthetic denial, default pilot denial, bulk rejection, unknown-key refusal, file-backed reopen/retry durability, and immediate session-expiry termination with subject records retained. Existing demo test explicitly opts into its disposable database.

## Historical routes and remaining blockers

These are findings from code inspection, not live portal verification:

- Subject route: `/corecampus/student/attendance/subwise_attendace_new.php`; day-wise route: `/corecampus/student/attendance/myattendance.php`; overall route: `/corecampus/student/attendance/allSubject.php` on `https://mrei.icloudems.com`. Their live validity remains unverified.
- Discovery still forms a Cartesian product of academic years and semesters and associates the first class option. It does not establish dependent year -> semester -> class combinations. NOT_CHECKED makes uncertainty explicit but does not repair discovery.
- Live discovery captures current portal HTML, while preview/import resolve persisted inventory. Newly discovered, unpersisted historical selections cannot reliably reach preview/import. Unknown-key refusal deliberately fails closed here.
- Extractor filter selection is optional when controls are missing. It must require every requested filter, verify selected values after dependent reloads, and reject parsed year/semester/class mismatches before persistence. Extraction validation/quarantine must be enforced before ingestion.
- Navigation can fall back to direct URLs with a supplied referrer and tolerates readiness failures. Replace this with verified same-origin, read-only menu navigation and explicit access-denied/session-expiry stops. Do not bypass university access restrictions.
- Candidate months are hard-coded by odd/even semester; they are planning hints, not verified semester boundaries. A month count is insufficient proof of complete coverage. Verify requested/returned months and years and retain explicit scope.
- The import route runs synchronously. Browser progress/cancel behavior, ORM stale-state cancellation reads, concurrent job reservation, persisted counters after partial failure, and interrupted-job recovery require dedicated verification. Batch commits prove durability, not whole-job atomicity or reliable resume.
- Broad exceptions still include raw exception text in some diagnostics/logs. Redact URL queries/session-bearing text before a live pilot. Do not collect raw HTML, screenshots, cookies, or authentication values in shared evidence.
- Existing sanitization tests cover selected fixtures and known patterns, not a comprehensive guarantee of zero PII throughout all tracked and untracked source. Git tracks no database/raw dump/private-reference paths under the inspected patterns. A broader sanitized scan is required before any commit/publication.
- Git whitespace checking reports pre-existing trailing blank lines in several files. No runtime implication; they were not swept up in unrelated cleanup.

## Quality evidence

Final full quality run: **154 backend tests passed**, one Starlette/AnyIO deprecation warning; **24 frontend tests passed** across seven files; mypy clean across 59 source files; Ruff passed; frontend typecheck and production build passed. The production build includes `tsc -b`, which checks project references beyond the lightweight typecheck script.

File-backed test disposed the engine, reopened the same temporary SQLite file, verified persisted records, repeated the subject/day-wise imports, and asserted DUPLICATE_SKIPPED with unchanged observation counts. A separate synthetic expiry test verified exactly one failed day-wise attempt and retained subject records. This is not a forced power-loss or full live-job restart test.

F2-D launcher source was covered by the backend launcher tests. This session did not repeat the prior live Windows launcher/port-health claim or launch processes against the real database.

## Sequential supervised pilot protocol — do not execute until blockers are cleared

1. Finish the route, dependent-selector, identity-validation, scope, cancellation, redaction, and recovery repairs above using sanitized fixtures. Rerun the gates and refresh the private SQLite backup. Record pre-pilot per-term counts/checksums locally without exposing student identifiers.
2. Have the user open the dedicated browser and authenticate privately and manually. Never request an OTP, TOTP seed, QR code, password, cookie, token, or vault value. The agent must not observe the authentication screen. Confirm only that the attendance page is ready.
3. Under user supervision, verify read-only menu routes and one dependent year/semester/class combination. Record only sanitized route names, selector names, and success/failure. Stop on unexpected origin, access denial, missing control, or expiry.
4. Preview exactly one user-chosen historical semester. Confirm displayed labels and bounded scope. Begin with subject summary only; obtain the user's go-ahead on that concrete preview before importing. Do not infer term identity from semester sequence or old fixture labels.
5. Compare imported course totals against the visible portal summary, verify active-semester invariance and persistence after application restart, and repeat the same scope to verify deduplication. If approved, add one explicitly chosen day-wise month for that same semester and inspect reconciliation/coverage.
6. Stop after the pilot. Report discrepancies, scope, provenance, durability, and preserved baseline. Keep remaining semesters, bulk import, Git push, and F3 outside scope until separately authorized.

## Follow-on prompt

Continue AttendPlan F2-E.1 from the actual dirty repository at C:\Users\astra\Desktop\Project\AttendPlan. Read this audit and current AGENTS.md first. Preserve every existing change, the local SQLite database, and Windows Credential Manager TOTP; never request or inspect real secrets. Keep ATTENDPLAN_ALLOW_SYNTHETIC_IMPORT and ATTENDPLAN_ENABLE_HISTORICAL_PILOT unset during normal runtime. Sequentially repair dependent year/semester/class discovery and discovery-to-preview persistence; enforce required filters, same-origin menu navigation, returned identity and month validation, and quarantine before ingestion; verify cancellation/concurrency, partial-job counters and recovery; redact diagnostics and expand sanitization checks. Test with disposable file databases, including restart/retry and partial failure, then run all quality gates. Refresh a consistent private SQLite backup before live work. Only after these gates pass, prepare one concrete semester/scope preview for user-supervised manual private authentication and explicit pilot approval. Do not initiate authentication, real import, bulk work, Git push, or F3 automatically. Finish with verified evidence, remaining limits, and the next sequential prompt.
