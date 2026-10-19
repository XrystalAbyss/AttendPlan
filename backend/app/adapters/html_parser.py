"""Resilient HTML parser for university ERP attendance tables.

Uses semantic header normalization rather than hardcoded column indices,
making it robust against ERP UI layout updates, whitespace variations,
and extra tables.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup, Tag

from app.domain.attendance_engine import calculate_aggregate_metrics, calculate_course_metrics
from app.domain.models import (
    AttendanceSnapshot,
    CourseRecord,
    CourseStatus,
    DataProvenance,
    InvalidAttendanceError,
    ParserError,
    SnapshotDateRange,
    SnapshotSummary,
)

# Canonical column alias mappings
HEADER_ALIASES: dict[str, str] = {
    # Course Name
    "course_name": "course_name",
    "course": "course_name",
    "subject_name": "course_name",
    "subject": "course_name",
    "course_title": "course_name",
    # Course Short Name
    "course_short_name": "course_short_name",
    "short_name": "course_short_name",
    "subject_short_name": "course_short_name",
    # Course Code
    "course_code": "course_code",
    "subject_code": "course_code",
    "code": "course_code",
    # Faculty Name
    "faculty_name": "faculty_name",
    "faculty": "faculty_name",
    "teacher": "faculty_name",
    "instructor": "faculty_name",
    # Credits
    "course_credit": "credits",
    "course_credits": "credits",
    "credit": "credits",
    "credits": "credits",
    "cr": "credits",
    # Attended / Delivered
    "attended_delivered": "attended_delivered",
    "attended_over_delivered": "attended_delivered",
    "att_del": "attended_delivered",
    "attendance": "attended_delivered",
    # Percent
    "percent": "percent",
    "percentage": "percent",
    "pct": "percent",
    # Serial number
    "sr_no": "sr_no",
    "s_no": "sr_no",
    "serial_no": "sr_no",
}


def normalize_header(raw: str) -> str:
    """Normalize raw header text to a canonical identifier.

    Strips punctuation, replaces non-alphanumeric runs with underscores,
    and maps through canonical aliases.
    """
    cleaned = html.unescape(raw).lower().strip()
    # Replace non-alphanumeric chars with underscore
    slug = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return HEADER_ALIASES.get(slug, slug)


def detect_is_lab(course_name: str, short_name: str, credits: float) -> bool:
    """Determine if a course is a laboratory/practical session.

    Heuristics:
    - course_name or short_name contains 'lab' or 'practical'
    - short_name ends with '- pr' (ERP convention: PP = Theory, PR = Practical)
    """
    n_lower = course_name.lower()
    s_lower = short_name.lower()

    if "lab" in n_lower or "practical" in n_lower:
        return True
    if "lab" in s_lower or "pr" in s_lower.split("-")[-1].strip().split():
        return True
    if s_lower.endswith("- pr") or s_lower.endswith("pr"):
        return True
    return False


def parse_date_dmy_to_iso(date_str: str) -> Optional[str]:
    """Parse 'DD/MM/YYYY' to 'YYYY-MM-DD'."""
    clean = date_str.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


class ERPAttendanceParser:
    """Resilient parser for iCloudEMS student attendance pages."""

    REQUIRED_COLUMNS = {"course_name", "course_code", "attended_delivered"}

    def __init__(self, target_percentage: float = 75.0, strict_validation: bool = True) -> None:
        self.target_percentage = target_percentage
        self.strict_validation = strict_validation

    def parse_html(
        self,
        html_content: str,
        provenance: DataProvenance = DataProvenance.SAMPLE_HISTORICAL,
        snapshot_id: str = "snap-sample-default",
    ) -> AttendanceSnapshot:
        """Parse raw or sanitized HTML and return a validated AttendanceSnapshot."""
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract Metadata from selectors or headers
        academic_year = self._extract_academic_year(soup) or "2026-2027"
        semester = self._extract_semester(soup) or 5
        class_name = self._extract_class_name(soup) or "B.Tech CSE AIML-Sem 5"
        date_range = self._extract_date_range(soup)

        # 2. Locate the attendance table
        table_tag, col_map = self._find_attendance_table(soup)
        if not table_tag or not col_map:
            raise ParserError("Could not locate a valid course attendance table in HTML document")

        # 3. Parse course rows
        courses = self._parse_table_rows(table_tag, col_map)
        if not courses:
            raise ParserError("Located attendance table but found 0 valid course rows")

        # 4. Compute aggregate statistics
        active_courses = [c for c in courses if c.delivered > 0]
        unrecorded_courses = [c for c in courses if c.delivered == 0]
        safe_courses = [c for c in courses if c.status == CourseStatus.SAFE]
        at_risk_courses = [c for c in courses if c.status == CourseStatus.AT_RISK]

        tot_att, tot_del, overall_pct, overall_status = calculate_aggregate_metrics(
            [(c.attended, c.delivered) for c in courses],
            target=self.target_percentage,
        )

        summary = SnapshotSummary(
            total_courses=len(courses),
            active_courses=len(active_courses),
            unrecorded_courses=len(unrecorded_courses),
            safe_courses=len(safe_courses),
            at_risk_courses=len(at_risk_courses),
            total_attended=tot_att,
            total_delivered=tot_del,
            overall_percentage=overall_pct,
            overall_status=overall_status,
        )

        provenance_label = (
            "LIVE PORTAL ATTENDANCE"
            if provenance == DataProvenance.LIVE_PORTAL
            else ("LOCAL CACHED ARCHIVE" if provenance == DataProvenance.CACHED_LOCAL else "SAMPLE / HISTORICAL FIXTURE")
        )

        return AttendanceSnapshot(
            id=snapshot_id,
            academic_year=academic_year,
            semester=semester,
            class_name=class_name,
            date_range=date_range,
            provenance=provenance,
            provenance_label=provenance_label,
            captured_at=datetime.now(timezone.utc).isoformat(),
            target_percentage=self.target_percentage,
            summary=summary,
            courses=courses,
        )

    def _extract_academic_year(self, soup: BeautifulSoup) -> Optional[str]:
        select = soup.find("select", attrs={"name": "acadyear"}) or soup.find("select", id="acadyear")
        if select and isinstance(select, Tag):
            opt = select.find("option", selected=True)
            if opt and opt.text.strip():
                return opt.text.strip()
        return None

    def _extract_semester(self, soup: BeautifulSoup) -> Optional[int]:
        select = soup.find("select", attrs={"name": re.compile(r"semNum")}) or soup.find("select", id="semNum")
        if select and isinstance(select, Tag):
            opt = select.find("option", selected=True)
            if opt and opt.text.strip():
                match = re.search(r"\d+", opt.text.strip())
                if match:
                    return int(match.group())
        return None

    def _extract_class_name(self, soup: BeautifulSoup) -> Optional[str]:
        select = soup.find("select", attrs={"name": re.compile(r"classid")}) or soup.find("select", id="classid")
        if select and isinstance(select, Tag):
            opt = select.find("option", selected=True)
            if opt and opt.text.strip():
                return opt.text.strip()
        return None

    def _extract_date_range(self, soup: BeautifulSoup) -> SnapshotDateRange:
        """Search text for patterns like 'Course Wise Attendance From 04/08/2026 to 27/11/2026'."""
        text = soup.get_text()
        match = re.search(
            r"from\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+to\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            text,
            re.IGNORECASE,
        )
        if match:
            f_date = parse_date_dmy_to_iso(match.group(1))
            t_date = parse_date_dmy_to_iso(match.group(2))
            return SnapshotDateRange(from_date=f_date, to_date=t_date)
        return SnapshotDateRange()

    def _find_attendance_table(self, soup: BeautifulSoup) -> tuple[Optional[Tag], dict[str, int]]:
        """Iterate all tables and identify the one with required semantic headers."""
        best_table: Optional[Tag] = None
        best_map: dict[str, int] = {}
        max_matches = 0

        for table in soup.find_all("table"):
            col_map = self._inspect_table_headers(table)
            # Check if all required semantic columns are present
            if self.REQUIRED_COLUMNS.issubset(col_map.keys()):
                match_count = len(col_map)
                if match_count > max_matches:
                    max_matches = match_count
                    best_table = table
                    best_map = col_map

        return best_table, best_map

    def _inspect_table_headers(self, table: Tag) -> dict[str, int]:
        """Examine thead or first tr for header cells and return normalized column map."""
        col_map: dict[str, int] = {}

        # Look in thead first
        header_rows: list[Tag] = []
        thead = table.find("thead")
        if thead and isinstance(thead, Tag):
            header_rows = list(thead.find_all("tr"))
        if not header_rows:
            header_rows = list(table.find_all("tr")[:2])

        for tr in header_rows:
            cells = tr.find_all(["th", "td"])
            for idx, cell in enumerate(cells):
                norm = normalize_header(cell.get_text())
                if norm:
                    col_map[norm] = idx

            # If we found our required columns, return
            if self.REQUIRED_COLUMNS.issubset(col_map.keys()):
                return col_map

        return col_map

    def _parse_table_rows(self, table: Tag, col_map: dict[str, int]) -> list[CourseRecord]:
        """Extract course records from table rows using col_map."""
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody and isinstance(tbody, Tag) else table.find_all("tr")

        courses: list[CourseRecord] = []
        att_del_re = re.compile(r"(\d+)\s*/\s*(\d+)")

        for tr in rows:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue

            # Check if row is a header or summary row
            row_text = tr.get_text().lower()
            if "total" in row_text or "grand total" in row_text or "total percentage" in row_text:
                continue
            if any(cell.name == "th" for cell in cells):
                continue

            # Need at least enough cells to cover mapped columns
            max_idx = max(col_map.values())
            if len(cells) <= max_idx:
                continue

            def get_val(col_name: str) -> str:
                idx = col_map.get(col_name)
                if idx is not None and idx < len(cells):
                    return html.unescape(cells[idx].get_text()).strip()
                return ""

            code = get_val("course_code")
            name = get_val("course_name")
            short_name = get_val("course_short_name") or name
            faculty = get_val("faculty_name") or None
            credits_str = get_val("credits")
            att_del_str = get_val("attended_delivered")

            # Must have non-empty course code and name
            if not code or not name:
                continue

            # Extract attended and delivered counts
            match = att_del_re.search(att_del_str)
            if not match:
                if self.strict_validation:
                    raise ParserError(f"Row for course {code} has invalid attendance format: '{att_del_str}'")
                continue

            attended = int(match.group(1))
            delivered = int(match.group(2))

            # Credits parsing
            credits = 1.0
            if credits_str:
                try:
                    credits = float(re.findall(r"[\d.]+", credits_str)[0])
                except (IndexError, ValueError):
                    credits = 1.0

            # Lab classification
            is_lab = detect_is_lab(name, short_name, credits)

            # Domain calculation
            try:
                calc = calculate_course_metrics(attended, delivered, target=self.target_percentage)
            except InvalidAttendanceError:
                if self.strict_validation:
                    raise
                continue

            record = CourseRecord(
                code=code,
                name=name,
                short_name=short_name,
                faculty=faculty,
                credits=credits,
                is_lab=is_lab,
                attended=attended,
                delivered=delivered,
                percent=calc.percent,
                status=calc.status,
                can_skip=calc.can_skip,
                must_attend=calc.must_attend,
                margin_summary=calc.margin_summary,
            )
            courses.append(record)

        return courses
