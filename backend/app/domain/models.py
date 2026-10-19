"""Domain models, exceptions, and validation schemas for AttendPlan."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class InvalidAttendanceError(ValueError):
    """Raised when attendance counts violate fundamental mathematical domain bounds."""
    pass


class ParserError(RuntimeError):
    """Raised when the HTML parser encounters unrecoverable structural anomalies."""
    pass


class CourseStatus(str, Enum):
    SAFE = "SAFE"
    AT_RISK = "AT_RISK"
    UNRECORDED = "UNRECORDED"


class DataProvenance(str, Enum):
    LIVE_PORTAL = "LIVE_PORTAL"
    CACHED_LOCAL = "CACHED_LOCAL"
    SAMPLE_HISTORICAL = "SAMPLE_HISTORICAL"


class CourseRecord(BaseModel):
    """Validated academic course attendance record."""

    code: str = Field(..., description="Unique course code, e.g. CSH301C")
    name: str = Field(..., description="Full academic course title")
    short_name: str = Field(..., description="Short code / delivery tag, e.g. CAOR - PP")
    faculty: Optional[str] = Field(default=None, description="Faculty instructor name")
    credits: float = Field(default=1.0, ge=0.0, description="Academic credits")
    is_lab: bool = Field(default=False, description="Flag for practical laboratory course")
    attended: int = Field(..., ge=0, description="Count of attended periods")
    delivered: int = Field(..., ge=0, description="Count of delivered periods")
    percent: Optional[float] = Field(default=None, description="Computed percentage (or None if delivered == 0)")
    status: CourseStatus = Field(..., description="Status classification (SAFE, AT_RISK, UNRECORDED)")
    can_skip: Optional[int] = Field(default=None, ge=0, description="Safe bunk margin")
    must_attend: Optional[int] = Field(default=None, ge=0, description="Consecutive periods needed")
    margin_summary: str = Field(default="", description="Human-readable margin guidance")

    @model_validator(mode="after")
    def validate_invariants(self) -> CourseRecord:
        if self.attended > self.delivered:
            raise InvalidAttendanceError(
                f"Course {self.code}: attended ({self.attended}) cannot exceed delivered ({self.delivered})"
            )
        if self.delivered == 0 and self.status != CourseStatus.UNRECORDED:
            raise InvalidAttendanceError(
                f"Course {self.code}: delivered is 0, so status must be UNRECORDED, got {self.status}"
            )
        return self


class SnapshotDateRange(BaseModel):
    from_date: Optional[str] = Field(default=None, description="Start date of the attendance period (YYYY-MM-DD)")
    to_date: Optional[str] = Field(default=None, description="End date of the attendance period (YYYY-MM-DD)")


class SnapshotSummary(BaseModel):
    total_courses: int = Field(..., ge=0)
    active_courses: int = Field(..., ge=0)
    unrecorded_courses: int = Field(..., ge=0)
    safe_courses: int = Field(..., ge=0)
    at_risk_courses: int = Field(..., ge=0)
    total_attended: int = Field(..., ge=0)
    total_delivered: int = Field(..., ge=0)
    overall_percentage: Optional[float] = Field(default=None)
    overall_status: CourseStatus = Field(...)


class AttendanceSnapshot(BaseModel):
    """Complete snapshot of student attendance across all courses in a term."""

    id: str = Field(..., description="Unique snapshot identifier")
    academic_year: str = Field(..., description="e.g. 2026-2027")
    semester: int = Field(..., ge=1, le=12, description="Semester numeric, e.g. 5")
    class_name: str = Field(..., description="Academic class name, e.g. B.Tech CSE AIML-Sem 5")
    date_range: SnapshotDateRange = Field(default_factory=SnapshotDateRange)
    provenance: DataProvenance = Field(default=DataProvenance.SAMPLE_HISTORICAL)
    provenance_label: str = Field(default="SAMPLE / HISTORICAL FIXTURE")
    captured_at: str = Field(..., description="ISO 8601 UTC timestamp")
    target_percentage: float = Field(default=75.0, gt=0.0, lt=100.0)
    summary: SnapshotSummary = Field(...)
    courses: list[CourseRecord] = Field(default_factory=list)


class SimulationCourseInput(BaseModel):
    code: str
    attended: int = Field(..., ge=0)
    delivered: int = Field(..., ge=0)
    delta_attended: int = Field(default=0, ge=0)
    delta_missed: int = Field(default=0, ge=0)


class SimulationResultItem(BaseModel):
    code: str
    original_attended: int
    original_delivered: int
    original_percent: Optional[float]
    original_status: CourseStatus
    simulated_attended: int
    simulated_delivered: int
    simulated_percent: Optional[float]
    simulated_status: CourseStatus
    simulated_can_skip: Optional[int]
    simulated_must_attend: Optional[int]
    status_changed: bool
    summary: str


class SimulationRequest(BaseModel):
    target_percentage: float = Field(default=75.0, gt=0.0, lt=100.0)
    courses: list[SimulationCourseInput]


class SimulationResponse(BaseModel):
    target_percentage: float
    results: list[SimulationResultItem]
