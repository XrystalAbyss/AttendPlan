"""Tests for the resilient HTML ERP attendance parser.

Verifies:
1. Column header normalization and matching by semantic alias.
2. Accurate extraction of all 15 courses from the sanitized historical fixture.
3. Handling of 0/0 unrecorded courses.
4. Lab course detection heuristics.
5. Robustness against malformed rows, extra whitespace, and missing tables.
"""

from pathlib import Path
import pytest

from app.adapters.html_parser import ERPAttendanceParser, detect_is_lab, normalize_header
from app.domain.models import CourseStatus, ParserError

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_attendance.html"


class TestERPAttendanceParser:
    @pytest.fixture
    def sample_html(self) -> str:
        return FIXTURE_PATH.read_text(encoding="utf-8")

    def test_header_normalization(self) -> None:
        """Verify headers normalize consistently regardless of case, punctuation, or spaces."""
        assert normalize_header("Course Name") == "course_name"
        assert normalize_header("Course Short Name") == "course_short_name"
        assert normalize_header("Course Code") == "course_code"
        assert normalize_header("Faculty Name") == "faculty_name"
        assert normalize_header("Course Credit") == "credits"
        assert normalize_header("Attended/Delivered") == "attended_delivered"
        assert normalize_header("Attended / Delivered") == "attended_delivered"
        assert normalize_header("Percent") == "percent"
        assert normalize_header("Sr.No") == "sr_no"

    def test_parse_sample_fixture_all_15_rows(self, sample_html: str) -> None:
        """Confirm correct parsing of captured table headers and all 15 expected historical course rows."""
        parser = ERPAttendanceParser(target_percentage=75.0)
        snapshot = parser.parse_html(sample_html)

        # Basic metadata checks
        assert snapshot.academic_year == "2026-2027"
        assert snapshot.semester == 5
        assert snapshot.class_name == "B.Tech CSE AIML-Sem 5"
        assert snapshot.date_range.from_date == "2026-08-04"
        assert snapshot.date_range.to_date == "2026-11-27"

        # Row counts
        assert len(snapshot.courses) == 15
        assert snapshot.summary.total_courses == 15
        assert snapshot.summary.active_courses == 12  # 3 courses have 0/0: RDO202C, RDO301C, RDO204C
        assert snapshot.summary.unrecorded_courses == 3
        assert snapshot.summary.total_attended == 185
        assert snapshot.summary.total_delivered == 213
        assert snapshot.summary.overall_percentage == 86.85
        assert snapshot.summary.overall_status == CourseStatus.SAFE

        # Validate specific rows
        by_code = {c.code: c for c in snapshot.courses}

        # 1. CDO331: 36/40 (90.0%, Safe, can_skip=8)
        cdo = by_code["CDO331"]
        assert cdo.attended == 36
        assert cdo.delivered == 40
        assert cdo.percent == 90.0
        assert cdo.status == CourseStatus.SAFE
        assert cdo.can_skip == 8
        assert cdo.is_lab is False

        # 2. EDS240C: 3/5 (60.0%, At Risk, must_attend=3)
        eds = by_code["EDS240C"]
        assert eds.attended == 3
        assert eds.delivered == 5
        assert eds.percent == 60.0
        assert eds.status == CourseStatus.AT_RISK
        assert eds.must_attend == 3
        assert eds.is_lab is False

        # 3. RDO202C: 0/0 (Unrecorded, percent None)
        rdo = by_code["RDO202C"]
        assert rdo.attended == 0
        assert rdo.delivered == 0
        assert rdo.percent is None
        assert rdo.status == CourseStatus.UNRECORDED
        assert rdo.can_skip is None
        assert rdo.must_attend is None

        # 4. CSH301C: 17/19 (89.47%, Safe, can_skip=3)
        csh301 = by_code["CSH301C"]
        assert csh301.attended == 17
        assert csh301.delivered == 19
        assert csh301.percent == 89.47
        assert csh301.status == CourseStatus.SAFE
        assert csh301.can_skip == 3
        assert csh301.is_lab is False

        # 5. CSH311C: Lab, 10/14 (71.43%, At Risk, must_attend=2)
        csh311 = by_code["CSH311C"]
        assert csh311.attended == 10
        assert csh311.delivered == 14
        assert csh311.percent == 71.43
        assert csh311.status == CourseStatus.AT_RISK
        assert csh311.must_attend == 2
        assert csh311.is_lab is True

        # 6. CSH302C: 19/19 (100.0%, Safe, can_skip=6)
        csh302 = by_code["CSH302C"]
        assert csh302.attended == 19
        assert csh302.delivered == 19
        assert csh302.percent == 100.0
        assert csh302.status == CourseStatus.SAFE
        assert csh302.can_skip == 6
        assert csh302.is_lab is False

        # 14. CSH310C: 15/20 (75.0%, Safe, can_skip=0)
        csh310 = by_code["CSH310C"]
        assert csh310.attended == 15
        assert csh310.delivered == 20
        assert csh310.percent == 75.0
        assert csh310.status == CourseStatus.SAFE
        assert csh310.can_skip == 0
        assert csh310.must_attend == 0

    def test_lab_detection_heuristics(self) -> None:
        """Verify lab detection correctly identifies practicals."""
        assert detect_is_lab("COMPUTER ARCHITECTURE & ORGANISATION LAB", "CAOR - PR", 1.0) is True
        assert detect_is_lab("OPERATING SYSTEMS LAB", "OS LAB - PR", 1.0) is True
        assert detect_is_lab("ADVANCED JAVA", "JAVA - PP", 3.0) is False
        assert detect_is_lab("OPERATING SYSTEMS", "OS - PP", 3.0) is False

    def test_resilience_to_extra_tables_and_whitespace(self) -> None:
        """Parser must locate the attendance table even if preceded by other tables and whitespace."""
        html_with_distractions = """
        <html>
          <body>
            <table>
              <tr><td>User Info</td><td>Profile</td></tr>
            </table>
            <div style="padding: 20px;">
              <table>
                <thead>
                  <tr>
                    <th>  Course  Code </th>
                    <th> Course   Name </th>
                    <th> Attended / Delivered </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td> TEST101 </td>
                    <td> Software Architecture &amp; Design </td>
                    <td>   15 / 20   </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </body>
        </html>
        """
        parser = ERPAttendanceParser(target_percentage=75.0)
        snapshot = parser.parse_html(html_with_distractions)
        assert len(snapshot.courses) == 1
        course = snapshot.courses[0]
        assert course.code == "TEST101"
        assert course.name == "Software Architecture & Design"
        assert course.attended == 15
        assert course.delivered == 20
        assert course.percent == 75.0

    def test_raises_parser_error_when_no_valid_table_present(self) -> None:
        """Raise ParserError if document has no table with required headers."""
        empty_html = "<html><body><h1>No attendance here</h1></body></html>"
        parser = ERPAttendanceParser()
        with pytest.raises(ParserError, match="Could not locate a valid course attendance table"):
            parser.parse_html(empty_html)

    def test_handling_malformed_row(self) -> None:
        """Gracefully handle or reject malformed row with strict_validation setting."""
        malformed_html = """
        <table>
          <thead>
            <tr>
              <th>Course Code</th>
              <th>Course Name</th>
              <th>Attended/Delivered</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>CORRUPT</td>
              <td>Corrupt Course</td>
              <td>NOT_A_FRACTION</td>
            </tr>
          </tbody>
        </table>
        """
        # Strict mode raises ParserError
        parser_strict = ERPAttendanceParser(strict_validation=True)
        with pytest.raises(ParserError, match="invalid attendance format"):
            parser_strict.parse_html(malformed_html)

        # Lenient mode skips corrupt row and raises if 0 valid rows remain
        parser_lenient = ERPAttendanceParser(strict_validation=False)
        with pytest.raises(ParserError, match="found 0 valid course rows"):
            parser_lenient.parse_html(malformed_html)
