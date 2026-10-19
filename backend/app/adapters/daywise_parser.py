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


def parse_date_dmy(raw: str) -> Optional[date]:
    """Parse string containing DD/MM/YYYY into a date object."""
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    if not match:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return date(year, month, day)


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

        # 2. Locate timetable matrix
        table = self._find_daywise_table(soup)
        if not table:
            raise ParserError("Could not locate day-wise attendance matrix table")

        # 3. Parse date columns from thead
        date_cols = self._extract_date_columns(table)
        if not date_cols:
            raise ParserError("Found day-wise table but could not extract date columns")

        # 4. Parse time slot rows
        observations: list[ParsedObservationItem] = []
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody and isinstance(tbody, Tag) else table.find_all("tr")[1:]

        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells or len(cells) < 2:
                continue

            # First cell is time slot
            slot_raw = cells[0].get_text(separator=" ").strip()
            if "total" in slot_raw.lower():
                continue  # Skip totals row

            start_t, end_t, slot_label = parse_time_slot(slot_raw)

            # Map remaining cells to corresponding date columns
            for col_idx, att_date in date_cols.items():
                if col_idx >= len(cells):
                    continue

                cell = cells[col_idx]
                obs = self._parse_cell(cell, att_date, start_t, end_t, slot_label)
                if obs:
                    observations.append(obs)

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
            if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", text):
                return tbl
        return None

    def _extract_date_columns(self, table: Tag) -> dict[int, date]:
        """Map cell column index in row to the parsed calendar date."""
        thead = table.find("thead")
        header_rows = thead.find_all("tr") if thead and isinstance(thead, Tag) else table.find_all("tr")[:1]
        col_map: dict[int, date] = {}

        for tr in header_rows:
            cells = tr.find_all(["th", "td"])
            for idx, cell in enumerate(cells):
                d = parse_date_dmy(cell.get_text())
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
        if not cell_text:
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
        # Never automatically multiply lab attendance by two without explicit portal evidence.
        multiplier = 1
        explicit_mult_match = re.search(r"\(?\b(\d+)\s*(?:periods?|p)\b\)?", cell_text, re.I)
        if explicit_mult_match:
            try:
                val = int(explicit_mult_match.group(1))
                if 1 <= val <= 4:
                    multiplier = val
            except ValueError:
                pass

        # Extract course code (e.g. CSH301C)
        code_match = re.search(r"\b([A-Z]{2,4}\d{3}[A-Z]?)\b", cell_text)
        course_label = code_match.group(1) if code_match else None
        confidence = 1.0 if course_label else 0.0

        # Determine attendance status (P = Present, A = Absent)
        # Check explicit indicators
        has_p = bool(re.search(r"\bP\b", cell_text, re.I)) or "success" in str(cell.get("class", []))
        has_a = bool(re.search(r"\bA\b", cell_text, re.I)) or "danger" in str(cell.get("class", []))

        if has_p and not has_a:
            status = PeriodStatus.PRESENT
            delivered = multiplier
            attended = multiplier
        elif has_a:
            status = PeriodStatus.ABSENT
            delivered = multiplier
            attended = 0
        else:
            status = PeriodStatus.UNKNOWN
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
