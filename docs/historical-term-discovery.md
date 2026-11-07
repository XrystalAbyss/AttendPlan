# AttendPlan Historical Term Discovery Specification

## 1. Overview & Objectives
AttendPlan's historical intelligence relies on discovering which historical academic years, semesters, and class mappings are actually accessible to an authenticated student inside iCloudEMS (CoreCampus).

Rather than guessing or hardcoding term codes, AttendPlan dynamically queries the real selectable options on the portal's attendance pages and compiles a verified term inventory.

---

## 2. Portal DOM Architecture & Selectors

On the portal's Subject-Wise Attendance page (`https://mrei.icloudems.com/corecampus/index.php`), three cascading dropdown elements define a student's term context:

1. **Academic Year (`select[name="sel_academic_year"]` or `#sel_academic_year`)**:
   - Contains values like `"15"`, `"14"`, `"13"`, etc.
   - Visible labels like `"2026-2027"`, `"2025-2026"`, `"2024-2025"`.
2. **Semester (`select[name="sel_sem"]` or `#sel_sem`)**:
   - Contains semester sequence numbers (e.g., `"1"`, `"2"`, `"3"`, `"4"`, `"5"`).
   - Display labels like `"Semester 1"`, `"Semester 2"`, etc.
3. **Class (`select[name="sel_class"]` or `#sel_class`)**:
   - Contains portal-internal class identifiers (e.g., `"1050"`, `"1410"`, `"1820"`, `"2140"`, `"2582"`).
   - Display labels like `"B.Tech CSE AIML-Sem 4"`, `"B.Tech CSE AIML-Sem 5"`.

---

## 3. Core Architectural Invariants

### 3.1 No Static Assumptions
- **Academic Year to Semester Mapping**: The system never assumes `Academic Year 2022-2023 = Semester 1`. Academic calendars vary by student lateral entry, change of branch, or university schedule revisions.
- **Semester Count**: The system never assumes every academic year has exactly two semesters (summer terms or special trimesters may exist).
- **Identifier Stability**: The system never assumes a class identifier remains constant across terms (e.g. Class `"2140"` for Semester 4 vs `"2582"` for Semester 5).
- **Selector Combinations**: Only combinations discoverable directly in the live portal DOM or confirmed in persistent local storage are presented as eligible candidates.

### 3.2 Formal Discovery Statuses
Each discovered term is assigned a discrete status:
- `AVAILABLE`: Valid academic year, semester, and class mappings discovered; verified to return active subject records.
- `EMPTY`: Term selectors exist, but querying returns 0 course rows (e.g. uncommenced term or withdrawn enrollment).
- `INACCESSIBLE`: Term appears in dropdowns but access is blocked by portal permissions or fee hold.
- `UNKNOWN`: Term partially detected, but class dropdown could not be resolved.
- `FAILED`: Request timed out, network reset, or DOM error occurred during discovery.
- `NOT_CHECKED`: Discovered as an option combination but live verification search has not yet been executed.

> [!IMPORTANT]
> A single failed portal request is **never** treated as proof that historical data does not exist. It is categorized as `FAILED` or `NOT_CHECKED`, enabling user-initiated retries.

---

## 4. Discovery Data Model

```python
class HistoricalTermInventoryItem(BaseModel):
    term_key: str                # Lexicographically unique: "{academic_year}_s{sem}_{class_id}"
    academic_year: str           # e.g., "2024-2025"
    semester_number: int         # 1..8
    class_identifier: str        # e.g., "1050"
    display_label: str           # e.g., "Semester 1 (2024-2025)"
    class_display_label: str     # e.g., "B.Tech CSE AIML-Sem 1"
    status: TermDiscoveryStatus  # AVAILABLE, EMPTY, INACCESSIBLE, etc.
    has_subject_summary: bool    # True if subject snapshot exists locally or remotely
    has_daywise_data: bool       # True if daywise observations exist locally or remotely
    existing_courses_count: int  # Number of courses already stored locally
    existing_observations_count: int # Number of period cells stored locally
    attended_sum: int            # Total periods attended locally
    delivered_sum: int           # Total periods delivered locally
    percentage: Optional[float]  # Local aggregate rational percentage
    discovered_at: datetime      # UTC timestamp of discovery
    last_sync_timestamp: Optional[datetime]
    candidate_months: List[str]  # Target month indices (e.g. ["8", "9", "10", "11", "12"])
    candidate_month_labels: List[str]
    estimated_requests: int      # 1 (subject) + N (months)
    coverage_state: CoverageState # COMPLETE, PARTIAL, NOT_IMPORTED
    reconciliation_verdict: TermReconciliationVerdict # MATCHED, SCOPE_MISMATCH, etc.
```

---

## 5. Live vs Offline Discovery Execution

1. **Live Discovery (`POST /api/v1/historical/discover`)**:
   - Queries loopback Playwright CDP session (`127.0.0.1:9222`).
   - If dedicated browser is authenticated, opens subject-wise attendance page.
   - Extracts all options from `sel_academic_year`, `sel_sem`, and `sel_class`.
   - Cross-references discovered terms with local SQLite database to compute current coverage.
2. **Offline Discovery Fallback**:
   - If the browser is disconnected or unauthenticated, AttendPlan serves the catalog of terms already stored in the local SQLite database.
   - Alternatively, students may upload raw HTML from the portal into `HistoricalDiscoveryService.discover_inventory_from_html()` for air-gapped discovery.

---

## 6. API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/historical/terms` | `GET` | Retrieves the current discovered term inventory and coverage summary |
| `/api/v1/historical/discover` | `POST` | Triggers active discovery via live browser CDP or local database scan |
| `/api/v1/historical/preview` | `POST` | Generates pre-import preview showing estimated requests and missing coverage |
