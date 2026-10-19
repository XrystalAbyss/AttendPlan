---
name: portal-fixture-testing
description: Safe, privacy-preserving, and deterministic offline portal fixture extraction and test validation.
---

# Portal Fixture Testing Skill

## Principles of Fixture Management

### 1. Privacy First Sanitization
Portal HTML snapshots extracted from live student sessions contain private metadata. Before any fixture is committed or used in test suites:
- Strip student IDs, roll numbers, admission numbers (`admno`).
- Strip student names, email addresses, phone numbers.
- Strip session tokens, session query params (`?e=...`).
- Strip third-party tracking scripts (Google Tag Manager, Google Analytics, Firebase, AWS tokens).
- Strip client-side anti-debugging scripts and devtools hooks.
- Replace student identifiers with generic placeholders (e.g. `STUDENT_001`).
- All genuine raw portal captures must reside exclusively in `reference-private/`, which is permanently excluded via `.gitignore`.

### 2. Synthetic Day-Wise Timetable Fixtures
For date-wise timetable tests where genuine portal dumps are unavailable:
- Explicitly mark the fixture with `<!-- ATTENDPLAN SYNTHETIC TEST FIXTURE: FOR OFFLINE TESTING ONLY -->`.
- Never claim or label synthetic test data as real university observations.
- Structure must represent:
  - Header row with calendar dates (format: `DD/MM/YYYY`).
  - Rows representing lecture time slots (e.g. `09:00 - 10:00`, `10:00 - 11:00`, `11:00 - 01:00 (LAB)`).
  - Cells populated with `P`, `A`, or empty strings.
  - Multi-period lab blocks (typically 2-period rows).

### 3. Header-Driven Parsing
Do not rely on fixed column positions. Table columns may be reordered or added by the university ERP:
- Normalize header texts: lowercased, whitespace collapsed, punctuation removed.
- Match canonical header semantics:
  - Course Name: `course name`, `subject name`, `subject`
  - Course Short Name: `course short name`, `short name`
  - Course Code: `course code`, `subject code`
  - Faculty Name: `faculty name`, `teacher`
  - Credits: `course credit`, `credits`, `cr`
  - Attended/Delivered: `attended/delivered`, `attended / delivered`, `att/del`
  - Percentage: `percent`, `percentage`, `%`

### 4. Canonical Checksums & Deduplication
- Content checksums must be calculated independently of row order by sorting canonical entries prior to SHA-256 hashing.
- Duplicate imports must be detected and return `DUPLICATE_SKIPPED` without double-counting.
