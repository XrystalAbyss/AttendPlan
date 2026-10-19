"""Pydantic v2 schemas for AttendPlan F1 API requests and responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.db.enums import IngestionOutcome, ReconciliationStatus
from app.domain.models import CourseRecord, CourseStatus, SnapshotSummary


class AcademicTermResponse(BaseModel):
    id: str
    institution_key: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str] = None
    academic_start_date: Optional[date] = None
    academic_end_date: Optional[date] = None
    created_at: datetime
    total_courses: int = 0
    total_attended: int = 0
    total_delivered: int = 0
    overall_percentage: Optional[float] = None
    overall_status: CourseStatus = CourseStatus.UNRECORDED
    has_datewise_data: bool = False


class TermAttendanceResponse(BaseModel):
    term_id: str
    academic_year: str
    semester: int
    class_name: Optional[str]
    snapshot_id: Optional[str]
    captured_at: Optional[datetime]
    summary: SnapshotSummary
    courses: list[CourseRecord]


class SnapshotListItem(BaseModel):
    id: str
    academic_term_id: str
    source: str
    captured_at: datetime
    reporting_start_date: Optional[date]
    reporting_end_date: Optional[date]
    content_checksum: str
    record_count: int


class MonthlyAnalyticsItem(BaseModel):
    year: int
    month: int
    month_label: str
    delivered: int
    attended: int
    missed: int
    attendance_percentage: Optional[float]
    absence_percentage: Optional[float]
    observed_dates_count: int
    coverage: str


class WeekdayAnalyticsItem(BaseModel):
    weekday_index: int
    weekday_name: str
    delivered: int
    attended: int
    missed: int
    absence_rate: float
    observed_teaching_dates: int
    coverage: str


class DailyCourseItem(BaseModel):
    course_code: str
    slot_label: Optional[str]
    status: str
    attended: int
    delivered: int


class DailyAnalyticsItem(BaseModel):
    attendance_date: date
    weekday_name: str
    delivered: int
    attended: int
    missed: int
    percentage: Optional[float]
    courses: list[DailyCourseItem]
    coverage: str


class SubjectAnalyticsItem(BaseModel):
    course_code: str
    course_name: str
    course_type: str
    faculty_name: Optional[str]
    credits: float
    attended: int
    delivered: int
    missed: int
    percentage: Optional[float]
    status: CourseStatus
    can_skip: Optional[int]
    must_attend: Optional[int]
    absence_contribution_percentage: float
    margin_summary: str


class SubjectAbsenceRankingsResponse(BaseModel):
    by_absolute_missed: list[dict[str, Any]]
    by_missed_rate: list[dict[str, Any]]
    by_total_delivered: list[dict[str, Any]]


class SubjectAnalyticsResponse(BaseModel):
    subjects: list[SubjectAnalyticsItem]
    rankings: SubjectAbsenceRankingsResponse


class SemesterHistoricalItem(BaseModel):
    term_id: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str]
    attended: int
    delivered: int
    missed: int
    percentage: Optional[float]
    status: CourseStatus
    courses_below_threshold: int
    total_courses: int
    has_datewise_history: bool


class AcademicHistoryResponse(BaseModel):
    semesters: list[SemesterHistoricalItem]
    career_attended: int
    career_delivered: int
    career_percentage: Optional[float]
    career_status: CourseStatus


class CourseReconciliationItemResponse(BaseModel):
    course_code: str
    course_name: str
    subject_wise_attended: int
    subject_wise_delivered: int
    day_wise_attended: int
    day_wise_delivered: int
    attended_diff: int
    delivered_diff: int
    status: str


class TermReconciliationResponse(BaseModel):
    term_id: str
    academic_year: str
    semester_number: int
    subject_wise_available: bool
    day_wise_available: bool
    latest_snapshot_id: Optional[str]
    latest_batch_id: Optional[str]
    subject_wise_total_attended: int
    subject_wise_total_delivered: int
    day_wise_total_attended: int
    day_wise_total_delivered: int
    total_unmapped_observations: int
    coverage_start_date: Optional[date]
    coverage_end_date: Optional[date]
    reconciliation_status: ReconciliationStatus
    status_explanation: str
    course_breakdown: list[CourseReconciliationItemResponse]


class IngestionUploadResponse(BaseModel):
    type: str
    id: str
    term_id: str
    outcome: str
    details: dict[str, Any]


class IngestionEventResponse(BaseModel):
    id: str
    source: str
    academic_term_id: Optional[str]
    attempt_at: datetime
    outcome: IngestionOutcome
    safe_error_code: Optional[str]
    associated_snapshot_or_batch: Optional[str]


# -------------------------------------------------------------
# F2-A Portal Session & Discovery Schemas
# -------------------------------------------------------------

class PortalSessionStatusResponse(BaseModel):
    state: str
    browser_launched: bool
    cdp_port: int
    cdp_url: str
    current_url: Optional[str] = None
    page_title: Optional[str] = None
    profile_dir: str = ""
    details: str = ""
    manual_fallback_available: bool = True


class DiscoverRequest(BaseModel):
    html_content: Optional[str] = None


class TermOptionItem(BaseModel):
    value: str
    label: str
    selected: bool = False


class AcademicTermDiscoveryResponse(BaseModel):
    academic_years: list[TermOptionItem]
    semesters: list[TermOptionItem]
    classes: list[TermOptionItem]
    evidence: dict[str, Any]


class SubjectWiseDiscoveryResponse(BaseModel):
    table_found: bool
    header_columns: list[str]
    record_count: int
    date_range_detected: Optional[str] = None
    courses_found: list[dict[str, Any]]
    evidence: dict[str, Any]


class DayWiseDiscoveryResponse(BaseModel):
    table_found: bool
    date_columns: list[str]
    time_slots: list[str]
    has_course_name_toggle: bool
    course_name_mapping_mechanism: str
    sample_statuses_observed: list[str]
    evidence: dict[str, Any]


class OverallDiscoveryResponse(BaseModel):
    view_found: bool
    filter_controls: list[str]
    displayed_columns: list[str]
    macro_attendance_percentage: Optional[float] = None
    evidence: dict[str, Any]
