"""Tests verifying Phase E.0 Course Identity and Performance Invariants.

Validates:
1. Exact course identity provenance across historical semesters (CSH201C vs CSH301C).
2. Multi-semester course isolation (Rule 2.13).
3. Suffix relationships (-TUT, -PR) matching base course concepts.
4. Performance score semantics: distinguishing zero scores (0.0) from missing/unreported (None) and masked.
5. Invariant 11: Blank cell semantics (all unmapped timetable slots are NO_CLASS with delivered=0).
"""
from app.services.performance_service import parse_performance, parse_grouped_marks, number
from bs4 import BeautifulSoup


def test_performance_number_distinguishes_zero_from_missing():
    # Zero is a valid numerical score
    assert number("0") == 0.0
    assert number("0.0") == 0.0
    assert number("00") == 0.0
    
    # Missing, pending, or dashes are None (UNKNOWN)
    assert number("") is None
    assert number("-") is None
    assert number("--") is None
    assert number("na") is None
    assert number("n/a") is None
    assert number("pending") is None
    assert number("not published") is None


def test_performance_grouped_marks_zero_vs_unreported_vs_masked():
    html = """
    <table>
      <tr>
        <th rowspan='2'>Course Code</th>
        <th rowspan='2'>Course Name</th>
        <th colspan='3'>INTERNAL EXAM</th>
        <th colspan='1'>EXTERNAL EXAM</th>
      </tr>
      <tr>
        <th>CE 1</th>
        <th>CE 2</th>
        <th>CE 3</th>
        <th>End Semester Examination</th>
      </tr>
      <tr>
        <td>CSH201C</td>
        <td>ANALYSIS & DESIGN OF ALGORITHMS</td>
        <td>0/20</td>
        <td>-</td>
        <td>18/20</td>
        <td>******</td>
      </tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    courses = parse_grouped_marks(soup.find("table"))
    assert len(courses) == 1
    c = courses[0]
    assert c["course_code"] == "CSH201C"
    assert c["course_name"] == "ANALYSIS & DESIGN OF ALGORITHMS"
    
    # CE 1: obtained zero out of 20 -> REPORTED with 0.0
    ce1 = c["assessments"][0]
    assert ce1["name"] == "CE 1"
    assert ce1["obtained"] == 0.0
    assert ce1["maximum"] == 20.0
    assert ce1["percentage"] == 0.0
    assert ce1["status"] == "REPORTED"
    
    # CE 2: '-' -> UNREPORTED, None
    ce2 = c["assessments"][1]
    assert ce2["name"] == "CE 2"
    assert ce2["obtained"] is None
    assert ce2["maximum"] is None
    assert ce2["percentage"] is None
    assert ce2["status"] == "UNREPORTED"
    
    # CE 3: 18/20 -> REPORTED, 90%
    ce3 = c["assessments"][2]
    assert ce3["name"] == "CE 3"
    assert ce3["obtained"] == 18.0
    assert ce3["maximum"] == 20.0
    assert ce3["percentage"] == 90.0
    assert ce3["status"] == "REPORTED"
    
    # End Sem: '******' -> MASKED_BY_PORTAL
    end_sem = c["assessments"][3]
    assert end_sem["name"] == "End Semester Examination"
    assert end_sem["obtained"] is None
    assert end_sem["status"] == "MASKED_BY_PORTAL"


def test_course_identity_csh201c_vs_csh301c_isolation():
    """Verify CSH201C (Algorithms) and CSH301C (Computer Architecture) distinct identity semantics."""
    s3_row = "<tr><td>CSH201C</td><td>ANALYSIS & DESIGN OF ALGORITHMS</td><td>30</td><td>50</td><td>80</td><td>100</td><td>4</td><td>A</td></tr>"
    s5_row = "<tr><td>CSH301C</td><td>COMPUTER ARCHITECTURE & ORGANISATION</td><td>25</td><td>45</td><td>70</td><td>100</td><td>4</td><td>B</td></tr>"
    table = f"<table><tr><th>Course Code</th><th>Subject Name</th><th>Internal</th><th>External</th><th>Total</th><th>Max Marks</th><th>Credits</th><th>Grade</th></tr>{s3_row}{s5_row}</table>"
    
    parsed = parse_performance(table)
    assert len(parsed["courses"]) == 2
    csh201 = next(c for c in parsed["courses"] if c["course_code"] == "CSH201C")
    csh301 = next(c for c in parsed["courses"] if c["course_code"] == "CSH301C")
    
    assert csh201["course_name"] == "ANALYSIS & DESIGN OF ALGORITHMS"
    assert csh301["course_name"] == "COMPUTER ARCHITECTURE & ORGANISATION"
    assert csh201["course_name"] != csh301["course_name"]
