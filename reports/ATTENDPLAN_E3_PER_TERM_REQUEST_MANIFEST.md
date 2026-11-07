# AttendPlan — Multi-Semester Performance Request Manifest

**Document Scope**: Bounded, Auditable Per-Term Manifests for Semesters 1, 2, 3, 4, and 5  
**Audit Status**: OFFLINE READINESS VERIFIED  
**Date**: November 1, 2026  
**Execution State**: AWAITING USER APPROVAL  

---

## 1. Overview & Request Budget Rules

To guarantee strict compliance with AttendPlan's read-only portal policy and university server safety:
1. **Request Ceiling**: For any term not yet imported, AttendPlan permits at most:
   - **Maximum 1 Scoped Discovery Operation**: Retrieves valid `exam_session` options for that academic year from the portal's dropdown menu.
   - **Maximum 1 Marks Report Retrieval**: Submits the verified form filters and extracts the HTML report table.
2. **Zero Report Refetch**: The report captured during preview is stored in the local `SyncJob.details` and reused directly upon user approval. No second fetch is ever executed.
3. **Localhost Concurrency**: All operations acquire `_SYNC_LOCK`. If the lock cannot be acquired immediately, the operation aborts with HTTP 409.
4. **No Session Identifier Invention**: If an `exam_session` identifier is not already verified in the local database, it is marked as `DISCOVERY_REQUIRED`.

---

## 2. Per-Term Scope Manifests

### Scope 1: Semester 1 (AY 2024–2025)
- **Status**: `NOT_YET_IMPORTED`
- **Academic Year**: `2024-2025`
- **Semester**: `1`
- **Candidate Class ID**: `918` (`B.Tech CSE AIML-Sem 1`) (Verified from `HISTORICAL_SELECTOR_DISCOVERY`)
- **Expected Division**: `A`
- **Source Exam Type**: `3` (`INTERNAL EXAM`)
- **Source Exam Session**: `DISCOVERY_REQUIRED` (Cannot assume AY 2025–2026 sessions 6161 or 6424 apply to AY 2024–2025 Odd semester).
- **Storage View Identity**: `marks:[discovered_session]:3:A`
- **Expected Course Catalog (12 Courses)**:
  `CDO103B`, `CHS103C`, `CSH101C`, `CSH102C`, `CSS104C`, `CSS104C-PR`, `CSW103C`, `MAH104C`, `MAH104C-TUT`, `MEW104C`, `PHH101C`, `PHH102C`.
- **Known Aggregation Rules**:
  `MAH104C-TUT` continuous evaluations aggregated under lecture course `MAH104C` (`COMPONENT_AGGREGATED`).
- **Required User-Approved Portal Operations**:
  1. Discovery: Open `myreportcard.php`, select Year `2024-2025`, query available `exam_session` options.
  2. Preview: Select discovered session + Class `918` + Exam Type `3` + Division `A`, extract table.
  3. Import: Zero-refetch persistence of captured preview payload upon user confirmation.
- **Request Budget Ceiling**: 1 discovery request + 1 report retrieval request.
- **Stop Conditions**:
  - Class `918` not available under year `2024-2025`.
  - Division dropdown contains multiple options or differs from `A`.
  - Table parsing detects duplicate course codes or missing headers.
  - Portal session drops or redirects to login.

---

### Scope 2: Semester 2 (AY 2024–2025)
- **Status**: `NOT_YET_IMPORTED`
- **Academic Year**: `2024-2025`
- **Semester**: `2`
- **Candidate Class ID**: `1048` (`B.Tech CSE AIML-Sem 2`) (Verified from `HISTORICAL_SELECTOR_DISCOVERY`)
- **Expected Division**: `A`
- **Source Exam Type**: `3` (`INTERNAL EXAM`)
- **Source Exam Session**: `DISCOVERY_REQUIRED` (Cannot assume 2025–2026 Even semester session 6424 applies to 2024–2025).
- **Storage View Identity**: `marks:[discovered_session]:3:A`
- **Expected Course Catalog (16 Courses)**:
  `CDO104B`, `CHH101C`, `CHH102C`, `CSH107C`, `CSH107C-TUT`, `CSH108C`, `CSH109C`, `CSH110C`, `CSS112C`, `ECH103C`, `ECH104C`, `HLS101C`, `HLS101C-PR`, `MAH101C`, `MAH101C-TUT`, `VAC-CS109`.
- **Known Aggregation Rules**:
  - `CSH107C-TUT` aggregated under `CSH107C` (`COMPONENT_AGGREGATED`).
  - `MAH101C-TUT` aggregated under `MAH101C` (`COMPONENT_AGGREGATED`).
  - `VAC-CS109` (Data Analytics using Excel): external vendor certificate course (`SOURCE_COURSE_ABSENT`).
- **Required User-Approved Portal Operations**:
  1. Discovery: Open `myreportcard.php`, select Year `2024-2025`, query available `exam_session` options.
  2. Preview: Select discovered session + Class `1048` + Exam Type `3` + Division `A`, extract table.
  3. Import: Zero-refetch persistence of captured preview payload upon user confirmation.
- **Request Budget Ceiling**: 1 discovery request + 1 report retrieval request.
- **Stop Conditions**:
  - Class `1048` not available under year `2024-2025`.
  - Division differs from `A`.
  - Table width mismatch or unsupported structure.

---

### Scope 3: Semester 3 (AY 2025–2026)
- **Status**: `VERIFIED_EXISTING_SNAPSHOT`
- **Academic Year**: `2025-2026`
- **Semester**: `3`
- **Class ID**: `1067` (`B.Tech CSE AIML-Sem 3`)
- **Division**: `A`
- **Source Exam Session**: `6161` (`MRU-Odd-Semester-Dec-2025-2026-5041`)
- **Source Exam Type**: `3` (`INTERNAL EXAM`)
- **Storage View Identity**: `marks:6161:3:A`
- **Persisted Snapshot ID**: `a9410bae-8496-4a0e-a64c-0880aa5cfbdb`
- **Canonical SHA-256 Fingerprint**: `bdae037d0a8ca75ff95aa296c0a021de9bfa2881c18b14e4a02d1264f6b83bee`
- **Persisted Metrics**: 13 courses, 9 assessment columns, 117 total cells (64 reported, 53 unreported).
- **Execution Policy**:
  - **IMMUTABLE EXISTING SOURCE**.
  - **Zero portal requests authorized**.
  - **Do NOT refetch or overwrite**.

---

### Scope 4: Semester 4 (AY 2025–2026)
- **Status**: `REUSE_EXISTING_SOURCE`
- **Academic Year**: `2025-2026`
- **Semester**: `4`
- **Class ID**: `2508` (`B.Tech CSE AIML-Sem 4`)
- **Division**: `A`
- **Source Exam Session**: `6424` (`MRU-EVEN-Semester-MAY-2025-2026-5046`)
- **Source Exam Type**: `3` (`INTERNAL EXAM`)
- **Storage View Identity**: `marks:6424:3:A`
- **Persisted Snapshot ID**: `03d1482b-c997-431f-bc88-071c3bb4c764`
- **Canonical SHA-256 Fingerprint**: `c237d69522cd673de86bbf1dd518f3a08beda47c50ec5aba96209b21f4d8d25d`
- **Persisted Metrics**: 15 courses, 11 assessment columns, 165 total cells (60 reported, 90 unreported, 15 masked).
- **Execution Policy**:
  - **REUSE EXISTING SOURCE**.
  - Retain current snapshot immutably.
  - Future optional refresh may be proposed to check if the portal has unmasked previously withheld `*` end-semester cells, but no refresh is permitted in Phase E.3.

---

### Scope 5: Semester 5 (AY 2026–2027)
- **Status**: `NOT_YET_IMPORTED` (Active Ongoing Term)
- **Academic Year**: `2026-2027`
- **Semester**: `5`
- **Candidate Class ID**: `2582` (`B.Tech CSE AIML-Sem 5`) (Verified from `HISTORICAL_SELECTOR_DISCOVERY`)
- **Expected Division**: `A`
- **Source Exam Type**: `3` (`INTERNAL EXAM`)
- **Source Exam Session**: `DISCOVERY_REQUIRED` (Current active odd semester session identifier).
- **Storage View Identity**: `marks:[discovered_session]:3:A`
- **Expected Course Catalog (15 Courses)**:
  `CDO331`, `CSH301C`, `CSH302C`, `CSH303C`, `CSH304C`, `CSH305C`, `CSH310C`, `CSH311C`, `CSH312C`, `CSH318C`, `CSH319C`, `EDS240C`, `RDO202C`, `RDO204C`, `RDO301C`.
- **Active Term Dynamics**:
  - Incomplete continuous evaluation records are expected.
  - Midterm exams and end semester exams may be unconducted or pending.
  - Masked or blank entries must be preserved as `UNREPORTED` / `PENDING` without throwing validation errors.
  - **No auto-refresh on startup**: Marks updates must be triggered solely via explicit, manual user action.
- **Request Budget Ceiling**: 1 discovery request + 1 report retrieval request.

---

## 3. Summary Request Matrix

| Scope | Term Key | AY | Sem | Candidate Class | Exam Session | Type | Div | Max Portal Requests | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **S1** | `2024-2025_s1_918` | 2024–2025 | 1 | 918 | `DISCOVERY_REQUIRED` | 3 | A | 2 (1 disc + 1 ret) | `AWAITING_USER_APPROVAL` |
| **S2** | `2024-2025_s2_1048` | 2024–2025 | 2 | 1048 | `DISCOVERY_REQUIRED` | 3 | A | 2 (1 disc + 1 ret) | `AWAITING_USER_APPROVAL` |
| **S3** | `2025-2026_s3_1067` | 2025–2026 | 3 | 1067 | 6161 (Verified) | 3 | A | 0 (Preserved) | `VERIFIED_EXISTING_SNAPSHOT` |
| **S4** | `2025-2026_s4_2508` | 2025–2026 | 4 | 2508 | 6424 (Verified) | 3 | A | 0 (Preserved) | `REUSE_EXISTING_SOURCE` |
| **S5** | `2026-2027_s5_2582` | 2026–2027 | 5 | 2582 | `DISCOVERY_REQUIRED` | 3 | A | 2 (1 disc + 1 ret) | `AWAITING_USER_APPROVAL` |

---

## 4. Proposed Next Authorization Text

When ready to proceed to live execution in a future phase (e.g., Phase E.4), the user will be presented with the following explicit authorization prompt:

```markdown
I explicitly authorize AttendPlan to execute bounded academic marks discovery and preview
for:
1. Semester 1 (AY 2024-2025, Class 918, Internal Exam Type 3)
2. Semester 2 (AY 2024-2025, Class 1048, Internal Exam Type 3)
3. Semester 5 (AY 2026-2027, Class 2582, Internal Exam Type 3)

I confirm that:
- Maximum 1 discovery and 1 marks-report request per semester is permitted.
- Semester 3 existing snapshot (a9410bae...) will remain untouched.
- Semester 4 existing snapshot (03d1482b...) will remain untouched.
- No official result cards, grades, SGPA or CGPA will be fetched.
```

