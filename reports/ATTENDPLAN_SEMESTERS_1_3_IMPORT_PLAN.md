# AttendPlan Semesters 1–3 Historical Import Plan

**Target Scope:** Multi-Semester Historical Archive Recovery  
**Target Semesters:** Semester 3 (2025–2026), Semester 2 (2024–2025), Semester 1 (2024–2025)  
**Status:** **`AWAITING_USER_APPROVAL`** (NO LIVE EXTRACTION HAS COMMENCED)  

---

## 1. Scope & Request Budget

The live historical archive will execute strictly within the following calendar-aware scope, capped at **16 report requests maximum**:

| Sequence | Academic Year | Semester | Portal Class ID | Class Description | Candidate Teaching Months | Subject Summary Requests | Day-Wise Month Requests | Total Requests |
| :---: | :---: | :---: | :---: | :--- | :--- | :---: | :---: | :---: |
| **Phase 1 (Recommended Pilot)** | **2025–2026** | **3** | `1067` | B.Tech CSE AIML-Sem 3 | `2025-08`, `2025-09`, `2025-10`, `2025-11` | 1 | 4 | **5** |
| **Phase 2** | **2024–2025** | **2** | `1048` | B.Tech CSE AIML-Sem 2 | `2025-01`, `2025-02`, `2025-03`, `2025-04`, `2025-05` | 1 | 5 | **6** |
| **Phase 3** | **2024–2025** | **1** | `918` | B.Tech CSE AIML-Sem 1 | `2024-08`, `2024-09`, `2024-10`, `2024-11` | 1 | 4 | **5** |
| **TOTAL** | — | — | — | — | — | **3** | **13** | **16** |

---

## 2. Safety Guarantees & Non-Negotiable Invariants

1. **Explicit Incremental Pacing**:
   - Each request will enforce a **1.5s to 2.5s polite pause** to prevent portal strain or throttling.
   - Zero parallel browser navigations; single-job mutex lock (`_SYNC_LOCK`) enforced.
2. **Term & Identity Verification**:
   - Before extracting any table, the portal's active dropdowns must be verified to match the target `academic_year`, `semester`, and `class_id`.
   - If dropdown reload fails or an unexpected class label appears, the scope will abort with `TERM_IDENTITY_UNVERIFIED`.
3. **Multi-Semester Isolation**:
   - Courses with identical course codes in earlier semesters (e.g. `RDO202C` in Sem 3 and Sem 4) will be isolated under their respective `academic_term_id` UUIDs.
4. **Zero Fabricated Attendance**:
   - Any difference between subject summaries and day-wise totals will be classified as `SOURCE_DISCREPANCY` with granular per-course delta tracking.
   - Blank timetable slots will remain `NOT_REPORTED` ($d=0, a=0$).
5. **Session Safety**:
   - Existing Chrome CDP session on `127.0.0.1:9222` will be reused.
   - Zero credentials, OTPs, or TOTP seeds will be read, requested, or logged.

---

## 3. Recommended Phasing & Execution Order

We strongly recommend executing **Semester 3 first** as an isolated pilot:

1. **Why Semester 3 First?**
   - Belongs to the same academic year (`2025–2026`) as Semester 4.
   - Requires only **5 requests total** (1 summary + 4 months: Aug, Sep, Oct, Nov 2025).
   - Allows verifying course name aliases and timetable geometry for the 2025–2026 odd term prior to touching 2024–2025 records.
2. **Execution Steps for Semester 3 Pilot:**
   - Step 1: Preflight backup check (`attendplan_pre_sem3_backup.sqlite3`).
   - Step 2: Navigate to `myattendance.php` and verify selector combo (`2025-2026` / `Sem 3` / `1067`).
   - Step 3: Extract subject-wise summary snapshot; create course roster.
   - Step 4: Sequentially extract day-wise reports for `2025-08`, `2025-09`, `2025-10`, `2025-11`.
   - Step 5: Ingest into SQLite transactionally with title-aware course reconciliation.
   - Step 6: Run `ReconciliationService.reconcile_term()`.
   - Step 7: Verify all quality gates remain green.

---

## 4. User Authorization Request

To proceed with live execution on the portal, please review and select an approval option:

- **Option A (Recommended):** Authorize the **Semester 3 Pilot Only** (5 requests maximum: 1 summary + 4 months: Aug, Sep, Oct, Nov 2025).
- **Option B:** Authorize the **Full Historical Scope** for Semesters 1, 2, and 3 (16 requests maximum: 3 summaries + 13 months across 2024–2025 and 2025–2026).
- **Option C:** Modify candidate months or pause historical extraction.

