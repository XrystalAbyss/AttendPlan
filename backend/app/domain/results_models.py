"""Domain models, validation enums, and data integrity specifications for Official Academic Results.

Strictly separates Data Class B (Official Academic Results / Grade Cards) from
Data Class A (Internal Assessment Marks) and Data Class C (Derived Analytics).
All models are pure Python dataclasses with zero network or database dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Optional


class ResultPublicationStatus(str, Enum):
    """Official university publication lifecycle state for academic results."""

    PUBLISHED = "PUBLISHED"
    NOT_PUBLISHED = "NOT_PUBLISHED"
    WITHHELD = "WITHHELD"
    REVALUATION_PENDING = "REVALUATION_PENDING"
    REVISED = "REVISED"


class ResultProvenance(str, Enum):
    """Data provenance tracking origin of official results data."""

    LIVE_PORTAL_RESULT_CARD = "LIVE_PORTAL_RESULT_CARD"
    OFFLINE_TRANSCRIPT_AUDIT = "OFFLINE_TRANSCRIPT_AUDIT"
    VERIFIED_FIXTURE = "VERIFIED_FIXTURE"


class AcademicDataClass(str, Enum):
    """Boundary classification of academic data in AttendPlan."""

    CLASS_A_INTERNAL_MARKS = "CLASS_A_INTERNAL_MARKS"
    CLASS_B_OFFICIAL_RESULTS = "CLASS_B_OFFICIAL_RESULTS"
    CLASS_C_DERIVED_ANALYTICS = "CLASS_C_DERIVED_ANALYTICS"


@dataclass(frozen=True)
class OfficialCourseResult:
    """Official course performance entry from an institutional grade card."""

    course_code: str
    course_name: Optional[str]
    credits: Optional[float]
    grade: Optional[str]
    grade_point: Optional[float]
    internal_marks: Optional[float] = None
    external_marks: Optional[float] = None
    total_marks: Optional[float] = None
    result_status: Optional[str] = None  # e.g., PASS, FAIL, DETAINED, ABSENT

    def __post_init__(self) -> None:
        if not self.course_code or not self.course_code.strip():
            raise ValueError("course_code must not be empty")
        if self.credits is not None and self.credits < 0:
            raise ValueError(f"credits cannot be negative: {self.credits}")
        if self.grade_point is not None and (self.grade_point < 0 or self.grade_point > 10):
            raise ValueError(f"grade_point must be between 0.0 and 10.0: {self.grade_point}")


@dataclass(frozen=True)
class OfficialSemesterResult:
    """Official semester performance summary from an institutional grade card."""

    term_key: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str] = None
    exam_session: Optional[str] = None
    exam_session_label: Optional[str] = None
    sgpa: Optional[float] = None
    cgpa: Optional[float] = None
    credits_registered: Optional[float] = None
    credits_earned: Optional[float] = None
    total_points_secured: Optional[float] = None
    publication_status: ResultPublicationStatus = ResultPublicationStatus.NOT_PUBLISHED
    courses: list[OfficialCourseResult] = field(default_factory=list)
    declaration_date: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.term_key or not self.term_key.strip():
            raise ValueError("term_key must not be empty")
        if self.semester_number < 1 or self.semester_number > 12:
            raise ValueError(f"semester_number must be between 1 and 12: {self.semester_number}")
        if self.sgpa is not None and (self.sgpa < 0 or self.sgpa > 10):
            raise ValueError(f"sgpa must be between 0.0 and 10.0: {self.sgpa}")
        if self.cgpa is not None and (self.cgpa < 0 or self.cgpa > 10):
            raise ValueError(f"cgpa must be between 0.0 and 10.0: {self.cgpa}")
        if self.credits_registered is not None and self.credits_registered < 0:
            raise ValueError(f"credits_registered cannot be negative: {self.credits_registered}")
        if self.credits_earned is not None and self.credits_earned < 0:
            raise ValueError(f"credits_earned cannot be negative: {self.credits_earned}")


@dataclass(frozen=True)
class OfficialResultSnapshot:
    """Immutable snapshot container for official academic result cards with provenance."""

    term_key: str
    semester_result: OfficialSemesterResult
    checksum: str
    provenance: ResultProvenance = ResultProvenance.VERIFIED_FIXTURE
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_evidence: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def compute_canonical_checksum(cls, semester_result: OfficialSemesterResult) -> str:
        """Compute bit-for-bit canonical SHA-256 hash over deterministic sorted JSON representation."""
        data = {
            "term_key": semester_result.term_key,
            "academic_year": semester_result.academic_year,
            "semester_number": semester_result.semester_number,
            "class_identifier": semester_result.class_identifier,
            "exam_session": semester_result.exam_session,
            "exam_session_label": semester_result.exam_session_label,
            "sgpa": semester_result.sgpa,
            "cgpa": semester_result.cgpa,
            "credits_registered": semester_result.credits_registered,
            "credits_earned": semester_result.credits_earned,
            "total_points_secured": semester_result.total_points_secured,
            "publication_status": semester_result.publication_status.value,
            "declaration_date": semester_result.declaration_date,
            "courses": [
                {
                    "course_code": c.course_code,
                    "course_name": c.course_name,
                    "credits": c.credits,
                    "grade": c.grade,
                    "grade_point": c.grade_point,
                    "internal_marks": c.internal_marks,
                    "external_marks": c.external_marks,
                    "total_marks": c.total_marks,
                    "result_status": c.result_status,
                }
                for c in sorted(semester_result.courses, key=lambda x: x.course_code)
            ],
        }
        canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

