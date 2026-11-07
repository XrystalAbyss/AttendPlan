# AttendPlan Historical Coverage Audit (Phase B)
**Date:** October 2026  
**Scope:** Historical Terms, Month Discovery, Marks Integration & Source Coverage Verification

---

## 1. Overview of Historical Scope

The university student portal (iCloudEMS) provides access to multiple academic terms and several reporting modalities. However, access to historical terms is not uniform across past years:
1. **Attendance Summaries:** Usually available for all registered semesters.
2. **Day-Wise Period Ledgers:** Selectable across dropdown months, but many historical calendar months return empty reports, administrative warnings, or unpopulated timetables.
3. **Academic Marks & Results:** Internal sessional and continuous assessment marks are published for certain terms (e.g. Semester 4), while final exam result sheets or grade cards may be unpopulated, withheld, or served on distinct unauthenticated portals.

In accordance with AttendPlan invariants:
- **No Fabrication:** Empty months are never treated as 100% absence.
- **Explicit Provenance:** Every imported snapshot preserves its raw HTML hash, capture timestamp, and extraction status.
- **Coverage Separation:** A term is not marked `COMPLETE` unless all declared source requirements are satisfied.

---

## 2. Term & Source Coverage Audit

| Term / Scope | Academic Year | Semester | Subject Summary Status | Day-Wise Period Status | Internal Marks Status | Exam Results Status | Verified Coverage Classification |
|---|---|---|---|---|---|---|---|
| **Semester 5 (Active)** | 2026–2027 | Sem 5 | **SAVED & ACTIVE** (Latest snapshot) | **SAVED** (Aug, Sep, Oct: 231/280 periods) | PENDING (Ongoing Term) | NOT_PUBLISHED | **CURRENT_ACTIVE_PARTIAL** |
| **Semester 4** | 2025–2026 | Sem 4 | **SAVED** (17 courses) | **PARTIAL** (Historical months) | **SAVED** (15 courses in snapshot) | NOT_AVAILABLE | **HISTORICAL_SAVED_WITH_MARKS** |
| **Semester 3** | 2025–2026 | Sem 3 | DISCOVERED | DISCOVERED | MENU_CHECKED | NOT_AVAILABLE | **SCOPE_DISCOVERED** |
| **Semester 2** | 2024–2025 | Sem 2 | DISCOVERED | DISCOVERED | MENU_CHECKED | NOT_AVAILABLE | **SCOPE_DISCOVERED** |
| **Semester 1** | 2024–2025 | Sem 1 | DISCOVERED | DISCOVERED | MENU_CHECKED | NOT_AVAILABLE | **SCOPE_DISCOVERED** |

---

## 3. Discovered Historical Flaw & Resolution

### The 99 Unverified Month Scopes Phenomenon
In previous audit reports (Phase A), an approved historical archive run of 107 report scopes yielded:
- 3 successful month batches
- 2 duplicate summaries skipped
- 102 unverified scopes (3 historical summaries and 99 month checks)

**Analysis of Failure Root Cause:**
The 99 historical month checks were previously failing due to `validate_result` in `backend/app/adapters/portal_safety.py`:
```python
if not dates or any(d.strftime("%Y-%m") != month for d in dates):
    raise PortalSafetyError("RETURNED_MONTH_SCOPE_MISMATCH")
```
When historical months with no scheduled classes (e.g. June/July summer break or pre-semester months) returned zero dated periods, `not dates` caused the safety validator to raise `RETURNED_MONTH_SCOPE_MISMATCH`. This crashed the extraction pipeline and caused the job coordinator to record the scope as `UNVERIFIED` rather than recognizing that the month was legitimately devoid of class meetings.

**Resolution:**
With `require_dates=False` now implemented in `portal_safety.py`, zero delivered periods in a requested month return a clean `NO_REPORTED_PERIODS` outcome without raising an exception. This allows the Historical Archive Backfill to complete cleanly without false error aborts.

---

## 4. Academic Marks & Results Integration

1. **Storage Isolation:**
   - Academic marks are persisted in the `performance_snapshots` table with distinct `subject_marks` JSON structures.
   - Separate from daily period ledgers to prevent cross-contamination between attendance percentages and assessment marks.
2. **Current Performance Snapshot:**
   - 1 immutable performance snapshot is durably stored in the SQLite database for Semester 4, containing 15 subjects with their respective continuous assessment and mid-term evaluations.
3. **Menu Discovery:**
   - The portal navigation inspector checks for links matching `["marks", "internal marks", "subject marks", "performances"]` and `["results", "semester results", "exam results", "examination results", "my report card"]`.
   - If found, it marks them as `MENU_FOUND_UNVERIFIED_FORMAT` until a preview validation run inspects the exact HTML table structure.

---

## 5. Controlled Backfill Strategy

To prevent portal flooding and protect student privacy:
1. **User-Authorized Preview:** Backfill operations require explicit user approval via `ArchiveSync.tsx`.
2. **Sequential Pacing:** Scopes are executed sequentially with random human-like pacing (1.5s–3.0s delay).
3. **Durable Checkpoints:** Every completed month or summary is written to SQLite immediately. If the job is paused or the browser closes, resuming picks up only the remaining unverified scopes.
4. **Decoupled from Service A:** Startup current-semester refresh runs independently and is never blocked by pending historical scopes.
