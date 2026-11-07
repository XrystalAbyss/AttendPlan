"""Pydantic v2 schemas for AttendPlan F1 API requests and responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

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


# -------------------------------------------------------------
# F2-B Synchronization Schemas & Job State Machine
# -------------------------------------------------------------

class SyncJobResponse(BaseModel):
    id: str
    academic_term_id: Optional[str] = None
    source_scope: str
    state: str
    current_step: str
    start_timestamp: datetime
    completion_timestamp: Optional[datetime] = None
    completed_batches: int
    failed_batches: int
    progress_total: int
    progress_current: int
    safe_diagnostic_message: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class SyncSubjectWiseRequest(BaseModel):
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    class_id: Optional[str] = None
    persist: bool = True


class SyncSubjectWiseResponse(BaseModel):
    status: str
    snapshot_id: Optional[str] = None
    term_id: Optional[str] = None
    outcome: str
    record_count: int
    academic_year: str
    semester: int
    class_name: Optional[str] = None
    aggregate_percentage: Optional[float] = None
    validation: dict[str, Any]


class SyncDayWiseRequest(BaseModel):
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    class_id: Optional[str] = None
    month: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    show_course_name: bool = True
    persist: bool = True


class SyncDayWiseResponse(BaseModel):
    status: str
    batch_id: Optional[str] = None
    term_id: Optional[str] = None
    outcome: str
    coverage_start: date
    coverage_end: date
    total_observations: int
    total_present: int
    total_delivered: int
    unmapped_count: int
    validation: dict[str, Any]


class PilotSyncRequest(BaseModel):
    month: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    class_id: Optional[str] = None


class TermSyncScopeItem(BaseModel):
    academic_year: str
    semester: int
    class_identifier: Optional[str] = None
    candidate_months: list[str]
    candidate_month_labels: list[str]
    estimated_requests: int
    has_subject_snapshot: bool
    has_daywise_batches: bool
    existing_batches_count: int
    selected: bool


class HistoricalPlanResponse(BaseModel):
    discovered_academic_years: list[str]
    terms: list[TermSyncScopeItem]
    total_terms_count: int
    total_estimated_requests: int
    pacing_guidance: str


# -------------------------------------------------------------
# F2-C: TOTP Vault and Automated MFA Schemas
# -------------------------------------------------------------

class TotpCandidateResponse(BaseModel):
    candidate_id: str
    issuer: str
    masked_account: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"
    source_type: str = "STANDARD_TOTP"


class TotpInspectResponse(BaseModel):
    candidates: list[TotpCandidateResponse]
    total_found: int
    source_format: str


class TotpEnrollRequest(BaseModel):
    candidate_id: Optional[str] = None
    secret_base32: Optional[str] = None
    provisioning_input: Optional[str] = None
    issuer: Optional[str] = None
    account_label: Optional[str] = None
    auto_autofill_enabled: bool = False
    auto_submit_enabled: bool = False



class TotpVerifyRequest(BaseModel):
    code: str


class TotpVerifyResponse(BaseModel):
    valid: bool
    message: str


class TotpSettingsUpdateRequest(BaseModel):
    auto_autofill_enabled: Optional[bool] = None
    auto_submit_enabled: Optional[bool] = None


class TotpMfaAutofillRequest(BaseModel):
    force_submit: Optional[bool] = None


class TotpMfaAutofillResponse(BaseModel):
    success: bool
    submitted: bool
    redirected: bool
    message: str
    error: Optional[str] = None


# -------------------------------------------------------------
# F2-C Addendum: Persistent Identity & Login Orchestration
# -------------------------------------------------------------



class LoginOrchestrateRequest(BaseModel):
    force_submit: Optional[bool] = None


class LoginOrchestrationResponse(BaseModel):
    state: str
    step: str
    success: bool
    redirected: bool
    message: str
    current_url: Optional[str] = None
    has_saved_mobile: bool = False
    is_totp_enrolled: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------
# F2-E: Multi-Semester Historical Discovery & Backfill Schemas
# -------------------------------------------------------------


class HistoricalTermItemResponse(BaseModel):
    term_key: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str] = None
    display_label: str
    class_display_label: Optional[str] = None
    status: str
    has_subject_summary: bool = False
    has_daywise_data: bool = False
    existing_courses_count: int = 0
    existing_observations_count: int = 0
    attended_sum: int = 0
    delivered_sum: int = 0
    percentage: Optional[float] = None
    discovered_at: Optional[datetime] = None
    last_sync_timestamp: Optional[datetime] = None
    candidate_months: list[str] = Field(default_factory=list)
    candidate_month_labels: list[str] = Field(default_factory=list)
    estimated_requests: int = 1
    coverage_state: str
    reconciliation_verdict: str
    error_message: Optional[str] = None


class HistoricalDiscoveryResponse(BaseModel):
    terms: list[HistoricalTermItemResponse]
    discovered_years: list[str]
    total_terms_count: int
    available_terms_count: int
    imported_terms_count: int
    discovery_timestamp: datetime
    provenance: str


class HistoricalDiscoverRequest(BaseModel):
    html_content: Optional[str] = None


class HistoricalPreviewRequest(BaseModel):
    selected_term_keys: Optional[list[str]] = None


class HistoricalPreviewResponse(BaseModel):
    source_course_count: Optional[int] = None
    approval_id: Optional[str] = None
    selected_terms: list[HistoricalTermItemResponse]
    total_selected_terms: int
    total_estimated_requests: int
    estimated_pacing_seconds: float
    pacing_guidance: str
    requires_user_approval: bool = True


class HistoricalImportRequest(BaseModel):
    approval_id: Optional[str] = None
    selected_term_keys: list[str]
    import_daywise: bool = False
    max_months_per_term: Optional[int] = None


class TermCoverageResponse(BaseModel):
    term_id: str
    academic_year: str
    semester_number: int
    class_identifier: Optional[str] = None
    coverage_state: str
    has_subject_summary: bool
    subject_snapshot_count: int
    subject_courses_count: int
    candidate_months: list[str]
    candidate_month_labels: list[str]
    months_attempted: list[str]
    months_completed: list[str]
    unique_instructional_dates: int
    unique_instructional_periods: int
    mapped_periods: int
    unmapped_periods: int
    missing_or_unreported_periods: int
    source_errors_count: int
    reconciliation_verdict: str
    details: dict[str, Any] = Field(default_factory=dict)




