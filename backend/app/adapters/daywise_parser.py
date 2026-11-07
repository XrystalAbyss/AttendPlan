"""Resilient HTML parser for iCloudEMS Day-Wise Attendance (myattendance.php).

Parses the timetable matrix: Lecture Timing (rows) × Calendar Dates (columns).
Strictly adheres to period semantics:
- P -> PRESENT (delivered=1, attended=1)
- A -> ABSENT (delivered=1, attended=0)
- Blank/Empty -> NO_CLASS / UNKNOWN (delivered=0, attended=0; NEVER counted as absence)
- Lab blocks -> multi-period delivered counts (e.g. 2 periods)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup, Tag

from app.db.enums import BatchStatus, PeriodStatus
from app.domain.models import ParserError
from app.services.checksums import compute_observation_batch_checksum


@dataclass(frozen=True)
class ParsedObservationItem:
    """Individual parsed period observation from the day-wise table."""

    attendance_date: date
    slot_start_time: Optional[str]
    slot_end_time: Optional[str]
    source_period_identifier: Optional[str]
    source_course_label: Optional[str]
    status: PeriodStatus
    delivered_period_count: int
    attended_period_count: int
    course_mapping_confidence: float


@dataclass(frozen=True)
class ParsedDaywiseBatch:
    """Structured result of parsing a day-wise attendance page."""

    academic_year: str
    semester: int
    class_identifier: Optional[str]
    coverage_start_date: date
    coverage_end_date: date
    source_filter_metadata: dict[str, str]
    status: BatchStatus
    content_checksum: str
    observations: list[ParsedObservationItem]


NAME_TO_CODE_MAP: dict[str, str] = {
    # Semester 5 verified course name aliases
    "PROFESSIONAL COMPETANCY ENHANCEMENT": "CDO331",
    "COMPUTER ARCHITECTURE & ORGANISATION LAB": "CSH311C",
    "COMPUTER ARCHITECTURE & ORGANISATION": "CSH301C",
    "OPERATING SYSTEMS LAB": "CSH303C",
    "OPERATING SYSTEMS": "CSH302C",
    "ADVANCED JAVA LAB": "CSH305C",
    "ADVANCED JAVA": "CSH304C",
    "COMPUTER VISION & IMAGE PROCESSING LAB": "CSH319C",
    "COMPUTER VISION & IMAGE PROCESSING": "CSH318C",
    "INTRODUCTION TO NOSQL DATABASES LAB": "CSH312C",
    "INTRODUCTION TO NOSQL DATABASES": "CSH310C",
    "ESSENCE OF INDIAN TRADITIONAL KNOWLEDGE": "EDS240C",
    "RESEARCH & INNOVATION": "RDO202C",
    "INTERDISCIPLINARY PROJECT": "RDO301C",
    "TECHNICAL INTERNSHIP": "RDO204C",
    # Semester 4 verified course name aliases
    "PROFESSIONAL COMPETENCY ENHANCEMENT-II": "CDO232",
    "SOFTWARE ENGINEERING": "CSH213C",
    "SOFTWARE ENGINEERING LAB": "CSH214C",
    "COMPUTER NETWORKS": "CSH215C",
    "COMPUTER NETWORKS LAB": "CSH216C",
    "MACHINE LEARNING": "CSH217C",
    "MACHINE LEARNING LAB": "CSH218C",
    "ADVANCED NEURAL NETWORKS": "CSH219C",
    "ADVANCED NEURAL NETWORKS LAB": "CSH220C",
    "MOBILE APP DEVELOPMENT": "CSW218C",
    "DIGITAL ELECTRONICS": "ECH108C",
    "DIGITAL ELECTRONICS LAB": "ECH109C",
    "INDIAN CONSTITUTION": "LWS101C",
    "ENTREPRENEURSHIP": "MCS368C",
    "DESIGN THINKING": "RDO203C",
    "SPECIALIZED AI ASSOCIATE TRAINING": "VAC-CS512",
    # Semester 3 verified course name aliases
    "PROFESSIONAL COMPETANCY ENHANCEMENT-I (PP)": "CDO231",
    "PROFESSIONAL COMPETANCY ENHANCEMENT-I": "CDO231",
    "ANALYSIS & DESIGN OF ALGORITHMS (PP)": "CSH201C",
    "ANALYSIS & DESIGN OF ALGORITHMS": "CSH201C",
    "ANALYSIS & DESIGN OF ALGORITHMS LAB (PR)": "CSH202C",
    "ANALYSIS & DESIGN OF ALGORITHMS LAB": "CSH202C",
    "DATABASE MANAGEMENT SYSTEMS (PP)": "CSH203C",
    "DATABASE MANAGEMENT SYSTEMS": "CSH203C",
    "DATABASE MANAGEMENT SYSTEMS LAB (PR)": "CSH204C",
    "DATABASE MANAGEMENT SYSTEMS LAB": "CSH204C",
    "OOPS USING JAVA (PP)": "CSH205C",
    "OOPS USING JAVA": "CSH205C",
    "OOPS USING JAVA LAB (PR)": "CSH206C",
    "OOPS USING JAVA LAB": "CSH206C",
    "ARTIFICIAL INTELLIGENCE (PP)": "CSH207C",
    "ARTIFICIAL INTELLIGENCE": "CSH207C",
    "ARTIFICIAL INTELLIGENCE LAB (PR)": "CSH208C",
    "ARTIFICIAL INTELLIGENCE LAB": "CSH208C",
    "DISCRETE MATHS (PP)": "MAH204C",
    "DISCRETE MATHS (TUT)": "MAH204C-TUT",
    "WEB DESIGNING-II (PR)": "CSW209C",
    "WEB DESIGNING-II": "CSW209C",
    "ADVANCED PYTHON FOR AI (PP)": "CSS210C",
    "ADVANCED PYTHON FOR AI": "CSS210C",
    "MONGODB JAVA DEVELOPER PATH (PP)": "VAC-CS112",
    "MONGODB JAVA DEVELOPER PATH": "VAC-CS112",
    "UHV II/ SEEK (PP)": "EDN248C",
    "UHV II/ SEEK": "EDN248C",
    "SOCIAL INTERNSHIP-POST 2ND SEM (PP)": "RDO201C",
    "SOCIAL INTERNSHIP-POST 2ND SEM": "RDO201C",
    # Semester 2 verified course name aliases
    "CHEMISTRY-I (PP)": "CHH101C",
    "CHEMISTRY-I": "CHH101C",
    "CHEMISTRY-I LAB (PR)": "CHH102C",
    "CHEMISTRY-I LAB": "CHH102C",
    "CALCULUS & LINEAR ALGEBRA (PP)": "MAH101C",
    "CALCULUS & LINEAR ALGEBRA (TUT)": "MAH101C-TUT",
    "PROFESSIONAL ENGLISH (PP)": "HLS101C",
    "PROFESSIONAL ENGLISH LAB (PR)": "HLS101C-PR",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING (PP)": "ECH103C",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING": "ECH103C",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING LAB (PR)": "ECH104C",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING LAB": "ECH104C",
    "DATA STRUCTURES (PP)": "CSH107C",
    "DATA STRUCTURES (TUT)": "CSH107C-TUT",
    "DATA STRUCTURES LAB (PR)": "CSH108C",
    "DATA STRUCTURES LAB": "CSH108C",
    "PYTHON PROGRAMMING (PP)": "CSH109C",
    "PYTHON PROGRAMMING": "CSH109C",
    "PYTHON PROGRAMMING LAB (PR)": "CSH110C",
    "PYTHON PROGRAMMING LAB": "CSH110C",
    "PROFESSIONAL COMMUNICATION-II (PP)": "CDO104B",
    "PROFESSIONAL COMMUNICATION-II": "CDO104B",
    "DATA VISUALIZATION (PP)": "CSS112C",
    "DATA VISUALIZATION": "CSS112C",
    "DATA ANALYTICS USING EXCEL (PP)": "VAC-CS109",
    "DATA ANALYTICS USING EXCEL": "VAC-CS109",
    # Semester 1 verified course name aliases
    "PROFESSIONAL COMMUNICATION-I (PP)": "CDO103B",
    "PROFESSIONAL COMMUNICATION-I": "CDO103B",
    "PROGRAMMING FOR PROBLEM SOLVING USING C (PP)": "CSH101C",
    "PROGRAMMING FOR PROBLEM SOLVING USING C": "CSH101C",
    "PROGRAMMING FOR PROBLEM SOLVING USING C LAB (PR)": "CSH102C",
    "PROGRAMMING FOR PROBLEM SOLVING USING C LAB": "CSH102C",
    "ENVIRONMENTAL SCIENCE (PP)": "CHS103C",
    "ENVIRONMENTAL SCIENCE": "CHS103C",
    "QUANTUM MECHANICS FOR ENGINEERS (PP)": "PHH101C",
    "QUANTUM MECHANICS FOR ENGINEERS": "PHH101C",
    "QUANTUM MECHANICS FOR ENGINEERS LAB (PR)": "PHH102C",
    "QUANTUM MECHANICS FOR ENGINEERS LAB": "PHH102C",
    "WEB DESIGNING-I (PR)": "CSW103C",
    "WEB DESIGNING-I": "CSW103C",
    "DATA MODELLING (PP)": "CSS104C",
    "DATA MODELLING LAB (PR)": "CSS104C-PR",
    "COMPUTER AIDED DRAFTING (PR)": "MEW104C",
    "COMPUTER AIDED DRAFTING": "MEW104C",
    "PROBABILITY & STATISTICS (PP)": "MAH104C",
    "PROBABILITY & STATISTICS (TUT)": "MAH104C-TUT",
}


def parse_date_dmy(raw: str, default_start_year: int = 2026) -> Optional[date]:
    """Parse string containing DD/MM/YYYY or DD/MM into a date object."""
    match_full = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    if match_full:
        day, month, year = int(match_full.group(1)), int(match_full.group(2)), int(match_full.group(3))
        return date(year, month, day)

    match_short = re.search(r"^\s*(\d{1,2})[/-](\d{1,2})\s*$", raw)
    if match_short:
        day, month = int(match_short.group(1)), int(match_short.group(2))
        if 1 <= day <= 31 and 1 <= month <= 12:
            year = default_start_year if month >= 7 else default_start_year + 1
            return date(year, month, day)
    return None


def parse_time_slot(raw: str) -> tuple[Optional[str], Optional[str], str]:
    """Parse slot strings like '09:00 - 10:00' into start_time, end_time, and label."""
    cleaned = raw.strip()
    match = re.search(r"(\d{1,2}:\d{2})\s*(?:-|to)\s*(\d{1,2}:\d{2})", cleaned)
    if match:
        return match.group(1), match.group(2), cleaned
    return None, None, cleaned


class ERPDaywiseParser:
    """Parser for day-wise timetable attendance grids."""

    def parse_html(self, html_content: str) -> ParsedDaywiseBatch:
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Metadata from form controls
        acad_year = self._extract_select_value(soup, "acadyear") or "2026-2027"
        sem_num = int(self._extract_select_value(soup, "semNum") or "5")
        class_id = self._extract_select_value(soup, "classid")

        # Determine academic start year (e.g. 2026 from 2026-2027)
        year_match = re.search(r"(\d{4})", acad_year)
        start_year = int(year_match.group(1)) if year_match else 2026

        # 2. Locate timetable matrix
        table = self._find_daywise_table(soup)
        if not table:
            raise ParserError("Could not locate day-wise attendance matrix table")

        # 3. Parse date columns from thead or header row
        date_cols = self._extract_date_columns(table, default_start_year=start_year)
        if not date_cols:
            raise ParserError("Found day-wise table but could not extract date columns")

        # 4. Parse time slot rows
        observations: list[ParsedObservationItem] = []
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody and isinstance(tbody, Tag) else table.find_all("tr")[1:]

        occupied: dict[int, int] = {}
        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells or len(cells) < 2:
                continue

            # First cell is time slot
            slot_raw = cells[0].get_text(separator=" ").strip()
            slot_lower = slot_raw.lower()
            if (
                "total" in slot_lower
                or "lecture timing" in slot_lower
                or "lecture time" in slot_lower
                or "time slot" in slot_lower
                or (not any(c.isdigit() for c in slot_raw) and "timing" in slot_lower)
            ):
                continue  # Skip totals or duplicate structural header rows

            start_t, end_t, slot_label = parse_time_slot(slot_raw)

            active = {column: remaining for column, remaining in occupied.items() if remaining > 0}
            occupied = {column: remaining-1 for column, remaining in active.items() if remaining > 1}
            column = 1
            for cell in cells[1:]:
                while column in active:
                    column += 1
                att_date = date_cols.get(column)
                span = int(str(cell.get("rowspan", "1")))
                if span > 1:
                    occupied[column] = span-1
                if att_date:
                    obs = self._parse_cell(cell, att_date, start_t, end_t, slot_label)
                    if obs:
                        observations.append(obs)
                column += int(str(cell.get("colspan", "1")))

        if not observations:
            raise ParserError("Day-wise table parsed but 0 observations were recorded")

        # Coverage dates
        all_dates = [o.attendance_date for o in observations]
        coverage_start = min(all_dates)
        coverage_end = max(all_dates)

        # Canonical checksum
        checksum_tuples = [
            (
                o.attendance_date.isoformat(),
                o.slot_start_time,
                o.source_period_identifier,
                o.source_course_label,
                o.status.value,
                o.delivered_period_count,
                o.attended_period_count,
            )
            for o in observations
        ]
        checksum = compute_observation_batch_checksum(checksum_tuples)

        # Batch status: default to UNKNOWN unless confirmed
        batch_status = BatchStatus.UNKNOWN

        return ParsedDaywiseBatch(
            academic_year=acad_year,
            semester=sem_num,
            class_identifier=class_id,
            coverage_start_date=coverage_start,
            coverage_end_date=coverage_end,
            source_filter_metadata={"acadyear": acad_year, "sem": str(sem_num)},
            status=batch_status,
            content_checksum=checksum,
            observations=observations,
        )

    def _extract_select_value(self, soup: BeautifulSoup, name_sub: str) -> Optional[str]:
        select = soup.find("select", attrs={"name": re.compile(name_sub, re.I)}) or soup.find(
            "select", id=re.compile(name_sub, re.I)
        )
        if select and isinstance(select, Tag):
            opt = select.find("option", selected=True)
            if opt and opt.text.strip():
                return opt.text.strip()
        return None

    def _find_daywise_table(self, soup: BeautifulSoup) -> Optional[Tag]:
        # Search for table with date columns or daywise id
        daywise_tbl = soup.find("table", id=re.compile(r"daywise", re.I))
        if daywise_tbl and isinstance(daywise_tbl, Tag):
            return daywise_tbl

        for tbl in soup.find_all("table"):
            text = tbl.get_text()
            if "lecture timing" in text.lower():
                return tbl
            if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", text):
                return tbl
            if re.search(r"\b\d{1,2}[/-]\d{1,2}\b", text) and ("total" in text.lower() or "lecture" in text.lower()):
                return tbl
        return None

    def _extract_date_columns(self, table: Tag, default_start_year: int = 2026) -> dict[int, date]:
        """Map cell column index in row to the parsed calendar date."""
        thead = table.find("thead")
        header_rows = thead.find_all("tr") if thead and isinstance(thead, Tag) else table.find_all("tr")[:1]
        col_map: dict[int, date] = {}

        for tr in header_rows:
            cells = tr.find_all(["th", "td"])
            for idx, cell in enumerate(cells):
                txt = cell.get_text().strip()
                if "total" in txt.lower():
                    continue
                d = parse_date_dmy(txt, default_start_year=default_start_year)
                if d:
                    col_map[idx] = d

        return col_map

    def _parse_cell(
        self,
        cell: Tag,
        att_date: date,
        start_t: Optional[str],
        end_t: Optional[str],
        slot_label: str,
    ) -> Optional[ParsedObservationItem]:
        cell_text = cell.get_text(separator=" ").strip()
        if not cell_text and not cell.find(["span", "div"]):
            # Empty / blank cell -> NOT_REPORTED. Crucial invariant: never count as absence!
            return ParsedObservationItem(
                attendance_date=att_date,
                slot_start_time=start_t,
                slot_end_time=end_t,
                source_period_identifier=slot_label,
                source_course_label=None,
                status=PeriodStatus.NOT_REPORTED,
                delivered_period_count=0,
                attended_period_count=0,
                course_mapping_confidence=0.0,
            )

        # Check explicit cancellation / no-class indicators
        if re.search(r"\b(no\s*class|holiday|cancelled|suspended|off)\b", cell_text, re.I):
            return ParsedObservationItem(
                attendance_date=att_date,
                slot_start_time=start_t,
                slot_end_time=end_t,
                source_period_identifier=slot_label,
                source_course_label=None,
                status=PeriodStatus.NO_CLASS,
                delivered_period_count=0,
                attended_period_count=0,
                course_mapping_confidence=0.0,
            )

        # Multiplier: strictly 1 by default per independently observed timetable row cell.
        multiplier = 1
        explicit_mult_match = re.search(r"\(?\b(\d+)\s*(?:periods?|p)\b\)?", cell_text, re.I)
        if explicit_mult_match:
            try:
                val = int(explicit_mult_match.group(1))
                if 1 <= val <= 4:
                    multiplier = val
            except ValueError:
                pass

        # A merged cell spans multiple actual timetable periods; do not multiply
        # each separately listed lab row, which would count a two-row lab twice.
        span = int(str(cell.get("rowspan", "1")))
        if not explicit_mult_match and 1 < span <= 4:
            multiplier = span
        if not explicit_mult_match and span == 1 and re.search(r"\bLAB\b|\(PR\)", cell_text, re.I) and start_t and end_t:
            def hours(value: str) -> int:
                return int(value.split(":")[0])*60+int(value.split(":")[1])
            if 90 <= hours(end_t)-hours(start_t) <= 120:
                multiplier = 2

        # Extract course code (e.g. CSH301C) or label from subjectName div
        code_match = re.search(r"\b([A-Z]{2,4}\d{3}[A-Z]?|VAC-[A-Z0-9]+)\b", cell_text)
        course_label = code_match.group(1) if code_match else None

        if not course_label:
            subj_div = cell.find("div", class_=re.compile("subjectName", re.I)) or cell.find("div")
            if subj_div:
                subj_text = subj_div.get_text().strip()
                if subj_text:
                    raw_subj = subj_text.strip().upper()
                    norm_name = re.sub(r"\s*\((?:PP|PR|TH|IA|TUT)\)\s*", "", subj_text, flags=re.I).strip().upper()
                    if raw_subj in NAME_TO_CODE_MAP:
                        course_label = NAME_TO_CODE_MAP[raw_subj]
                    elif norm_name in NAME_TO_CODE_MAP:
                        course_label = NAME_TO_CODE_MAP[norm_name]
                    else:
                        course_label = subj_text

        confidence = 1.0 if course_label and re.match(r"^[A-Z0-9\-]+$", course_label) else (0.8 if course_label else 0.0)

        # Determine attendance status (P = Present, A = Absent)
        badge_p = bool(cell.find(class_=re.compile(r"badge.*success|text.*success", re.I)))
        badge_a = bool(cell.find(class_=re.compile(r"badge.*danger|text.*danger", re.I)))
        has_p = badge_p or bool(re.search(r"\bP\b", cell_text, re.I)) or "success" in str(cell.get("class", []))
        has_a = badge_a or bool(re.search(r"\bA\b", cell_text, re.I)) or "danger" in str(cell.get("class", []))

        if has_p and not has_a:
            status = PeriodStatus.PRESENT
            delivered = multiplier
            attended = multiplier
        elif has_a:
            status = PeriodStatus.ABSENT
            delivered = multiplier
            attended = 0
        else:
            status = PeriodStatus.NOT_REPORTED
            delivered = 0
            attended = 0

        return ParsedObservationItem(
            attendance_date=att_date,
            slot_start_time=start_t,
            slot_end_time=end_t,
            source_period_identifier=slot_label,
            source_course_label=course_label,
            status=status,
            delivered_period_count=delivered,
            attended_period_count=attended,
            course_mapping_confidence=confidence,
        )

