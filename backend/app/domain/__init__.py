"""Domain layer for AttendPlan."""

from app.domain.attendance_engine import (
    AttendanceCalculation,
    calculate_aggregate_metrics,
    calculate_course_metrics,
    simulate_period_change,
    to_target_fraction,
    validate_counts,
)
from app.domain.models import (
    AttendanceSnapshot,
    CourseRecord,
    CourseStatus,
    DataProvenance,
    InvalidAttendanceError,
    ParserError,
    SimulationCourseInput,
    SimulationRequest,
    SimulationResponse,
    SimulationResultItem,
    SnapshotDateRange,
    SnapshotSummary,
)

__all__ = [
    "AttendanceCalculation",
    "calculate_aggregate_metrics",
    "calculate_course_metrics",
    "simulate_period_change",
    "to_target_fraction",
    "validate_counts",
    "AttendanceSnapshot",
    "CourseRecord",
    "CourseStatus",
    "DataProvenance",
    "InvalidAttendanceError",
    "ParserError",
    "SimulationCourseInput",
    "SimulationRequest",
    "SimulationResponse",
    "SimulationResultItem",
    "SnapshotDateRange",
    "SnapshotSummary",
]
