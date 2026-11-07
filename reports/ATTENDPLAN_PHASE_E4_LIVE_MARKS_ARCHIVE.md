# ATTENDPLAN — PHASE E.4 LIVE EXECUTION ARCHIVE REPORT
## Five-Semester Internal Marks Archive Completion

**Execution Agent:** Google Antigravity Flash 3.8  
**Date:** November 2, 2026  
**User Authorization:** Explicitly Granted for Semesters 1, 2, and 5  
**Preserved Baseline Snapshots:** Semester 3 (`a9410bae...`) and Semester 4 (`03d1482b...`)

---

## 1. Executive Summary

Phase E.4 has successfully achieved full **five-semester internal marks coverage** for AttendPlan. Through the student's authorized iCloudEMS portal session, live marks reports were retrieved, validated, and persisted for the three requested scopes:
1. **Semester 1 (AY 2024–2025, Class 918)**: Session `5764` (`MRU-Odd-Semester-Dec-2024-2025`), Exam Type `3` (`INTERNAL EXAM`), Division `A`.
2. **Semester 2 (AY 2024–2025, Class 1048)**: Session `5943` (`MRU-Even-Semester-May-2024-2025`), Exam Type `3` (`INTERNAL EXAM`), Division `A`.
3. **Semester 5 (AY 2026–2027, Class 2582)**: Session `6732` (`MRU-ODD-Semester-DEC-2026-2027-5056`), Exam Type `3` (`INTERNAL EXAM`), Division `A`.

All three scopes adhered strictly to the **zero-refetch protocol**: each semester executed exactly 1 discovery request and 1 preview retrieval request, followed by 0 network requests during persistence.

The two prior live snapshots (Semester 3 and Semester 4) remain 100% immutable and byte-for-byte identical to their pre-E.4 state.

---

## 2. Request Budget & Protocol Compliance

| Scope | Term Key | AY | Class ID | Exam Session ID & Label | Exam Type | Discovery Requests | Retrieval Requests | Import Refetches | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Scope A** | `2024-2025_s1_918` | 2024–2025 | 918 | 5764 (`MRU-Odd-Semester-Dec-2024-2025`) | 3 (`INTERNAL EXAM`) | 1 | 1 | 0 | **VERIFIED_LIVE** |
| **Scope B** | `2024-2025_s2_1048` | 2024–2025 | 1048 | 5943 (`MRU-Even-Semester-May-2024-2025`) | 3 (`INTERNAL EXAM`) | 1 | 1 | 0 | **VERIFIED_LIVE** |
| **Preserved** | `2025-2026_s3_1067` | 2025–2026 | 1067 | 6161 (`MRU-Odd-Semester-Dec-2025-2026-5041`) | 3 (`INTERNAL EXAM`) | 0 (pres.) | 0 (pres.) | 0 | **PRESERVED** |
| **Preserved** | `2025-2026_s4_2508` | 2025–2026 | 2508 | 6424 (`MRU-EVEN-Semester-MAY-2025-2026-5046`) | 3 (`INTERNAL EXAM`) | 0 (pres.) | 0 (pres.) | 0 | **PRESERVED** |
| **Scope C** | `2026-2027_s5_2582` | 2026–2027 | 2582 | 6732 (`MRU-ODD-Semester-DEC-2026-2027-5056`) | 3 (`INTERNAL EXAM`) | 1 | 1 | 0 | **VERIFIED_LIVE** |
| **Total** | | | | | | **3** | **3** | **0** | **100% Compliant** |

---

## 3. Five-Semester Performance Snapshot Registry

| Semester | Term Key | Snapshot UUID | View Tag | Checksum (SHA-256) | Courses | Total Cells | Reported Cells | Unreported Cells | Masked Cells |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Sem 1** | `2024-2025_s1_918` | `77d4702c-1e28-4ca7-95d5-329c7bba8d1d` | `marks:5764:3:A` | `d0bafbaefa6aa526dc05f4e1fa73c78c6bcc11ef624a8c77701232a34f23ea6c` | 11 | 66 | 48 | 18 | 0 |
| **Sem 2** | `2024-2025_s2_1048` | `b15162ae-4a03-4e99-8155-c844fb328ea7` | `marks:5943:3:A` | `c8110fdf0233baf2208c42c03c3e3c33e482daea97500694d453f1bd9cf64304` | 12 | 108 | 57 | 51 | 0 |
| **Sem 3** | `2025-2026_s3_1067` | `a9410bae-8496-4a0e-a64c-0880aa5cfbdb` | `marks:6161:3:A` | `bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee` | 13 | 117 | 64 | 53 | 0 |
| **Sem 4** | `2025-2026_s4_2508` | `03d1482b-c997-431f-bc88-071c3bb4c764` | `marks:6424:3:A` | `c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d` | 15 | 165 | 59 | 91 | 15 |
| **Sem 5** | `2026-2027_s5_2582` | `e8a91033-b87c-42e0-9d42-6ff0d02c8bcf` | `marks:6732:3:A` | `4e040f42019bea38cb883ec9161eb6658ec6e0183ff5f98ed41fe2d4606dec22` | 4 | 12 | 10 | 2 | 0 |
| **Total** | | | | | **55** | **468** | **238** | **215** | **15** |

---

## 4. Key Engineering Discoveries & Defensive Enhancements

1. **ERP Course Code Re-Use Disambiguation**:
   In Semester 1, the university ERP returned two entries with code `CSS104C`:
   - `CSS104C`: `DATA MODELLING - PP` (Theory)
   - `CSS104C`: `DATA MODELLING LAB - PR` (Practical / Lab)
   Previously, this triggered an unconditional `DUPLICATE_COURSE_CODE` error. The marks parser was updated to align with AttendPlan's established attendance adapter pattern (`html_parser.py`): multi-component courses sharing a code are systematically disambiguated to `{code}-PR` (or `{code}-TUT`), matching the database catalog record `CSS104C-PR`.
2. **Reconciliation Completeness**:
   Across all five academic terms, **0 unmapped source courses** exist (`unmapped_count == 0`). Every course present in any marks report matches an official catalog course.
3. **Session Discovery Parity Matching**:
   The automated scope discovery handler now enforces parity-aware session matching (`odd` vs `even` academic terms), preventing cross-semester session pollution in multi-session dropdowns.

---

## 5. Verification & Quality Gates

- **Backend Pytest**: 302 passed, 0 failed.
- **Python Linting (`ruff`)**: Clean, 0 errors.
- **Python Typing (`mypy`)**: Clean, 0 errors across 44 source files.
- **Frontend Vitest**: 38 passed across 13 test suites.
- **Frontend Build (`tsc -b && vite build`)**: Clean production bundle.
- **Database Consistency**:
  - `PRAGMA integrity_check` = `ok`
  - `PRAGMA foreign_key_check` = `[]`
  - WAL fully checkpointed: `(0, 90, 90)`
  - Verified post-execution backup: `attendplan_post_phase_e4_complete_backup_20261102_000644.sqlite3` (1,847,296 bytes).

