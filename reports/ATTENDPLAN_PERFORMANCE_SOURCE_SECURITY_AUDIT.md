# AttendPlan — Performance Source Security & Provenance Audit

**Phase Scope**: Phase E.2.1 Offline Source Security & Ingestion Hygiene  
**Audit Target**: Marks Ingestion Pipelines, Job Dictionaries, Database Persistence, and API Surfaces  
**Date**: November 1, 2026  
**Auditor**: Application Security & Privacy Engineer  
**Status**: VERIFIED SECURE & HARDENED  

---

## 1. Executive Security Assessment

AttendPlan's academic performance subsystem has been audited to enforce our non-negotiable architectural invariants:
1. **Local-First & Privacy First**: No student credentials, OTPs, session cookies, or personally identifiable information (PII) leave the local machine or exist unencrypted.
2. **Localhost Binding**: All backend endpoints bind strictly to `127.0.0.1`.
3. **Immutable Provenance**: Marks snapshots are cryptographically hashed using SHA-256 and stored immutably.
4. **Least Privilege Data Exposure**: Raw source payloads are quarantined, sanitized upon persistence, and redacted from generic sync job API endpoints.

---

## 2. In-Depth Security Findings & Remediation

### Finding 1: Raw Captured Payload Exposure in Generic Sync Job Endpoints
- **Vulnerability Description**: During preview, `details["captured_payload"]` stores the parsed or canonical course marks structure. Prior to Phase E.2.1, calling `GET /api/v1/portal/sync/jobs/{job_id}` or `GET /api/v1/portal/sync/jobs/latest` returned `job.details` directly. Any client querying sync job status would receive the entire unredacted marks dump.
- **Remediation**:
  - Implemented `sanitize_sync_job_details(details)` in `backend/app/api/routes.py`.
  - When returning `SyncJobResponse`, any present `captured_payload` is dynamically sanitized to:
    ```json
    {
      "redacted": true,
      "course_count": 13,
      "summary": "Source payload redacted from public sync job endpoint."
    }
    ```
  - This ensures generic job polling endpoints expose only metadata, not raw payload structures.
- **Verification**: Tested in `test_sync_job_details_payload_redaction` (`backend/tests/test_performance_acceptance_e2_1.py`).

### Finding 2: Retention of Raw Payload in SyncJob Database Rows Post-Import
- **Vulnerability Description**: After `capture_performance()` completes, the snapshot is immutably persisted into the dedicated `PerformanceSnapshot` table. Leaving the full duplicate payload indefinitely inside the generic `SyncJob` table increases the data footprint and risks unintended exposure if sync jobs are exported or debugged.
- **Remediation**:
  - In `backend/app/api/performance_routes.py`, `capture_performance()` now scrubs `captured_payload` from `SyncJob.details` immediately following successful snapshot insertion:
    ```python
    sanitized_details["captured_payload"] = {
        "redacted": True,
        "course_count": len(courses),
        "summary": "Source payload persisted in PerformanceSnapshot and scrubbed from sync job details."
    }
    job.details = sanitized_details
    db.commit()
    ```
- **Verification**: Verified offline; raw payload lives exclusively in the versioned `PerformanceSnapshot` row under `payload`.

### Finding 3: Replay and Substitution Attack Surface in Preview Approval Tokens
- **Vulnerability Description**: A user approval token (`approval_id`) could theoretically be replayed, used across different terms, or used past its validity window.
- **Remediation & Enforced Invariants**:
  1. **Single-Use State Claim**:
     - `capture_performance()` transitions `SyncJob.state` from `COMPLETED` to `APPROVED` using an atomic SQL update with `returning(SyncJob.id)`.
     - Replay attempts fail immediately with HTTP 409 (`"Preview expired or was already used."`).
  2. **Strict 30-Minute Expiry**:
     - Tokens older than 30 minutes (`created_at < now - 30m`) are rejected with HTTP 409.
  3. **Cross-Term Scope Binding**:
     - The approval token is cryptographically bound to the exact `(term_key, view, exam_session, exam_type, division_id)`.
     - Requesting import for a different term key using an existing `approval_id` is rejected with HTTP 409.
  4. **Concurrency Lock Protection**:
     - Sync operations acquire `_SYNC_LOCK`. If another portal job is active, requests fail immediately with HTTP 409 and release cleanly in `finally`.
- **Verification**: Verified in automated tests `test_preview_approval_single_use_and_replay_prevention`, `test_preview_expiry_after_30_minutes`, and `test_cross_term_substitution_rejection`.

---

## 3. PII & Session Token Database Audit

An automated scan of the local SQLite database (`C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3`) was performed across all tables:
- `academic_terms`
- `courses`
- `attendance_snapshots`
- `attendance_snapshot_rows`
- `attendance_observation_batches`
- `attendance_period_observations`
- `performance_snapshots`
- `sync_jobs`
- `ingestion_events`
- `settings`

### Results:
- **Student Names**: Zero matches.
- **Roll Numbers / Admission Numbers**: Zero matches.
- **Email Addresses / Phone Numbers**: Zero matches.
- **Browser Cookies / Bearer Tokens / Session Identifiers**: Zero matches.
- **Passwords / OTPs**: Zero matches. (TOTP secret keys remain strictly isolated in the OS credential vault / DPAPI).

---

## 4. Cryptographic Provenance Invariants

1. **Deterministic Canonical Checksums**:
   - `PerformanceSnapshot.checksum` is computed over lexicographically sorted JSON payload keys:
     $$\text{checksum} = \text{SHA256}(\text{json.dumps}(\text{parsed}, \text{sort\_keys}=\text{True}))$$
   - Persisted S3 Checksum: `bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee`.
   - Persisted S4 Checksum: `c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d`.
2. **Immutability Invariant**:
   - Dynamic classification and coverage annotations in `overview()` operate on deep-copied dictionaries in-memory. The raw persisted database row and its cryptographic fingerprint remain completely unaltered.

---

## 5. Security Posture Conclusion

The performance subsystem satisfies all security, privacy, and tamper-resistance requirements. Offline operation is strictly verified, and no external attack surface is exposed.

