"""Unit tests for Official Academic Results domain models (Phase E.6)."""
import pytest

from app.domain.results_models import (
    AcademicDataClass,
    OfficialCourseResult,
    OfficialResultSnapshot,
    OfficialSemesterResult,
    ResultPublicationStatus,
)


def test_official_course_result_validation():
    # Valid course result
    course = OfficialCourseResult(
        course_code="CSH201B",
        course_name="Data Structures",
        credits=4.0,
        grade="A+",
        grade_point=9.0,
        internal_marks=28.0,
        external_marks=62.0,
        total_marks=90.0,
        result_status="PASS",
    )
    assert course.course_code == "CSH201B"
    assert course.grade == "A+"
    assert course.grade_point == 9.0

    # Negative credits should raise ValueError
    with pytest.raises(ValueError, match="credits cannot be negative"):
        OfficialCourseResult(course_code="CSH201B", course_name="Data Structures", credits=-1.0, grade="A", grade_point=9.0)

    # Invalid grade point
    with pytest.raises(ValueError, match="grade_point must be between 0.0 and 10.0"):
        OfficialCourseResult(course_code="CSH201B", course_name="Data Structures", credits=4.0, grade="A", grade_point=11.5)

    # Empty course code
    with pytest.raises(ValueError, match="course_code must not be empty"):
        OfficialCourseResult(course_code="", course_name="Data Structures", credits=4.0, grade="A", grade_point=9.0)


def test_official_semester_result_validation():
    course1 = OfficialCourseResult(course_code="CSH201B", course_name="DS", credits=4.0, grade="A", grade_point=9.0)
    course2 = OfficialCourseResult(course_code="CSH202B", course_name="OS", credits=4.0, grade="B+", grade_point=8.0)

    sem_result = OfficialSemesterResult(
        term_key="2025-2026_s3_1067",
        academic_year="2025-2026",
        semester_number=3,
        class_identifier="1067",
        exam_session="DEC-2025",
        exam_session_label="Dec 2025 End Sem",
        sgpa=8.5,
        cgpa=8.4,
        credits_registered=24.0,
        credits_earned=24.0,
        total_points_secured=204.0,
        publication_status=ResultPublicationStatus.PUBLISHED,
        courses=[course1, course2],
        declaration_date="2026-01-15",
    )
    assert sem_result.sgpa == 8.5
    assert sem_result.cgpa == 8.4
    assert len(sem_result.courses) == 2

    # Invalid SGPA > 10.0
    with pytest.raises(ValueError, match="sgpa must be between 0.0 and 10.0"):
        OfficialSemesterResult(
            term_key="2025-2026_s3_1067",
            academic_year="2025-2026",
            semester_number=3,
            class_identifier="1067",
            exam_session="DEC-2025",
            exam_session_label="Dec 2025 End Sem",
            sgpa=10.5,
            cgpa=8.4,
            credits_registered=24.0,
            credits_earned=24.0,
            total_points_secured=204.0,
            publication_status=ResultPublicationStatus.PUBLISHED,
            courses=[],
        )

    # Invalid semester number
    with pytest.raises(ValueError, match="semester_number must be between 1 and 12"):
        OfficialSemesterResult(
            term_key="2025-2026_s0_1067",
            academic_year="2025-2026",
            semester_number=0,
            class_identifier="1067",
            exam_session="DEC-2025",
            exam_session_label="Dec 2025 End Sem",
            sgpa=8.0,
            cgpa=8.0,
            credits_registered=20.0,
            credits_earned=20.0,
            total_points_secured=160.0,
            publication_status=ResultPublicationStatus.PUBLISHED,
            courses=[],
        )


def test_canonical_checksum_determinism():
    c1 = OfficialCourseResult(course_code="CSH201B", course_name="DS", credits=4.0, grade="A", grade_point=9.0)
    c2 = OfficialCourseResult(course_code="AML201B", course_name="ML", credits=3.0, grade="A+", grade_point=10.0)

    # Order 1: c1 then c2
    sem1 = OfficialSemesterResult(
        term_key="2025-2026_s3_1067",
        academic_year="2025-2026",
        semester_number=3,
        class_identifier="1067",
        exam_session="DEC-2025",
        exam_session_label="Dec 2025",
        sgpa=9.4,
        cgpa=9.1,
        credits_registered=7.0,
        credits_earned=7.0,
        total_points_secured=66.0,
        publication_status=ResultPublicationStatus.PUBLISHED,
        courses=[c1, c2],
    )

    # Order 2: c2 then c1 (different insertion order)
    sem2 = OfficialSemesterResult(
        term_key="2025-2026_s3_1067",
        academic_year="2025-2026",
        semester_number=3,
        class_identifier="1067",
        exam_session="DEC-2025",
        exam_session_label="Dec 2025",
        sgpa=9.4,
        cgpa=9.1,
        credits_registered=7.0,
        credits_earned=7.0,
        total_points_secured=66.0,
        publication_status=ResultPublicationStatus.PUBLISHED,
        courses=[c2, c1],
    )

    hash1 = OfficialResultSnapshot.compute_canonical_checksum(sem1)
    hash2 = OfficialResultSnapshot.compute_canonical_checksum(sem2)

    # Sorting invariant: both must produce identical SHA-256 canonical hash
    assert hash1 == hash2
    assert len(hash1) == 64


def test_academic_data_class_separation():
    assert AcademicDataClass.CLASS_A_INTERNAL_MARKS.value == "CLASS_A_INTERNAL_MARKS"
    assert AcademicDataClass.CLASS_B_OFFICIAL_RESULTS.value == "CLASS_B_OFFICIAL_RESULTS"
    assert AcademicDataClass.CLASS_C_DERIVED_ANALYTICS.value == "CLASS_C_DERIVED_ANALYTICS"
