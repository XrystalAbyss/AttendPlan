"""Database enumerations for AttendPlan schema."""

from enum import Enum


class CourseType(str, Enum):
    THEORY = "THEORY"
    LAB = "LAB"
    TUTORIAL = "TUTORIAL"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class PeriodStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    NO_CLASS = "NO_CLASS"
    NOT_REPORTED = "NOT_REPORTED"
    UNKNOWN = "UNKNOWN"


class BatchStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


class CoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


class IngestionOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DUPLICATE_SKIPPED = "DUPLICATE_SKIPPED"


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    DISCREPANCY = "DISCREPANCY"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
