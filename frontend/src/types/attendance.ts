export type CourseStatus = "SAFE" | "AT_RISK" | "UNRECORDED";

export type DataProvenance = "LIVE_PORTAL" | "CACHED_LOCAL" | "SAMPLE_HISTORICAL";

export type ReconciliationStatus = "MATCHED" | "DISCREPANCY" | "PARTIAL_COVERAGE" | "SCOPE_MISMATCH" | "INSUFFICIENT_DATA";

export interface CourseRecord {
  code: string;
  name: string;
  short_name: string;
  faculty: string | null;
  credits: number;
  is_lab: boolean;
  attended: number;
  delivered: number;
  percent: number | null;
  status: CourseStatus;
  can_skip: number | null;
  must_attend: number | null;
  margin_summary: string;
}

export interface SnapshotDateRange {
  from_date?: string | null;
  to_date?: string | null;
}

export interface SnapshotSummary {
  total_courses: number;
  active_courses: number;
  unrecorded_courses: number;
  safe_courses: number;
  at_risk_courses: number;
  total_attended: number;
  total_delivered: number;
  overall_percentage: number | null;
  overall_status: CourseStatus;
}

export interface AttendanceSnapshot {
  id: string;
  academic_year: string;
  semester: number;
  class_name: string;
  date_range: SnapshotDateRange;
  provenance: DataProvenance;
  provenance_label: string;
  captured_at: string;
  target_percentage: number;
  summary: SnapshotSummary;
  courses: CourseRecord[];
}

export interface AcademicTerm {
  id: string;
  institution_key: string;
  academic_year: string;
  semester_number: number;
  class_identifier: string | null;
  academic_start_date: string | null;
  academic_end_date: string | null;
  created_at: string;
  total_courses: number;
  total_attended: number;
  total_delivered: number;
  overall_percentage: number | null;
  overall_status: CourseStatus;
  has_datewise_data: boolean;
}

export interface TermAttendanceResponse {
  term_id: string;
  academic_year: string;
  semester: number;
  class_name: string | null;
  snapshot_id: string | null;
  captured_at: string;
  provenance: string;
  target_percentage: number;
  summary: SnapshotSummary;
  courses: CourseRecord[];
}

export interface SnapshotListItem {
  id: string;
  academic_term_id: string;
  source: string;
  captured_at: string;
  reporting_start_date: string | null;
  reporting_end_date: string | null;
  content_checksum: string;
  record_count: number;
}

export interface MonthlyAnalyticsItem {
  year: number;
  month: number;
  month_label: string;
  delivered: number;
  attended: number;
  missed: number;
  attendance_percentage: number | null;
  absence_percentage: number | null;
  observed_dates_count: number;
  coverage: string;
}

export interface WeekdayAnalyticsItem {
  weekday_index: number;
  weekday_name: string;
  delivered: number;
  attended: number;
  missed: number;
  absence_rate: number;
  observed_teaching_dates: number;
  coverage: string;
}

export interface SubjectAnalyticsItem {
  course_code: string;
  course_name: string;
  course_type: string;
  faculty_name: string | null;
  credits: number;
  attended: number;
  delivered: number;
  missed: number;
  percentage: number | null;
  status: CourseStatus;
  can_skip: number | null;
  must_attend: number | null;
  absence_contribution_percentage: number;
  margin_summary: string;
}

export interface RankingItem {
  course_code: string;
  course_name: string;
  value: number;
}

export interface SubjectAbsenceRankings {
  by_absolute_missed: RankingItem[];
  by_missed_rate: RankingItem[];
  by_total_delivered: RankingItem[];
}

export interface SubjectAnalyticsResponse {
  subjects: SubjectAnalyticsItem[];
  rankings: SubjectAbsenceRankings;
}

export interface CourseReconciliationItem {
  course_code: string;
  course_name: string;
  subject_wise_attended: number;
  subject_wise_delivered: number;
  day_wise_attended: number;
  day_wise_delivered: number;
  attended_diff: number;
  delivered_diff: number;
  status: string;
}

export interface TermReconciliationResponse {
  term_id: string;
  academic_year: string;
  semester_number: number;
  subject_wise_available: boolean;
  day_wise_available: boolean;
  latest_snapshot_id: string | null;
  latest_batch_id: string | null;
  subject_wise_total_attended: number;
  subject_wise_total_delivered: number;
  day_wise_total_attended: number;
  day_wise_total_delivered: number;
  total_unmapped_observations: number;
  coverage_start_date: string | null;
  coverage_end_date: string | null;
  reconciliation_status: ReconciliationStatus;
  status_explanation: string;
  course_breakdown: CourseReconciliationItem[];
}

export interface SemesterHistoricalItem {
  term_id: string;
  academic_year: string;
  semester_number: number;
  class_identifier: string | null;
  attended: number;
  delivered: number;
  missed: number;
  percentage: number | null;
  status: CourseStatus;
  courses_below_threshold: number;
  total_courses: number;
  has_datewise_history: boolean;
}

export interface AcademicHistoryResponse {
  semesters: SemesterHistoricalItem[];
  career_attended: number;
  career_delivered: number;
  career_percentage: number | null;
  career_status: CourseStatus;
}

export interface SimulationResultItem {
  code: string;
  original_attended: number;
  original_delivered: number;
  original_percent: number | null;
  original_status: CourseStatus;
  simulated_attended: number;
  simulated_delivered: number;
  simulated_percent: number | null;
  simulated_status: CourseStatus;
  simulated_can_skip: number | null;
  simulated_must_attend: number | null;
  status_changed: boolean;
  summary: string;
}

export interface SimulationResponse {
  target_percentage: number;
  results: SimulationResultItem[];
}

export type PortalSessionState =
  | "DISCONNECTED"
  | "BROWSER_READY"
  | "LOGIN_REQUIRED"
  | "AUTHENTICATED"
  | "DISCOVERING"
  | "DISCOVERY_COMPLETE"
  | "SESSION_EXPIRED"
  | "ERROR"
  | "MANUAL_IMPORT_AVAILABLE";

export interface PortalSessionStatus {
  state: PortalSessionState;
  browser_launched: boolean;
  cdp_port: number;
  cdp_url: string;
  current_url: string | null;
  page_title: string | null;
  profile_dir: string;
  details: string;
  manual_fallback_available: boolean;
}

export interface TermOptionItem {
  value: string;
  label: string;
  selected: boolean;
}

export interface AcademicTermDiscoveryResponse {
  academic_years: TermOptionItem[];
  semesters: TermOptionItem[];
  classes: TermOptionItem[];
  evidence: Record<string, unknown>;
}

export interface SubjectWiseDiscoveryResponse {
  table_found: boolean;
  header_columns: string[];
  record_count: number;
  date_range_detected: string | null;
  courses_found: Array<{ cells: string[]; first_cell: string }>;
  evidence: Record<string, unknown>;
}

export interface DayWiseDiscoveryResponse {
  table_found: boolean;
  date_columns: string[];
  time_slots: string[];
  has_course_name_toggle: boolean;
  course_name_mapping_mechanism: string;
  sample_statuses_observed: string[];
  evidence: Record<string, unknown>;
}

export interface OverallDiscoveryResponse {
  view_found: boolean;
  filter_controls: string[];
  displayed_columns: string[];
  macro_attendance_percentage: number | null;
  evidence: Record<string, unknown>;
}

export type SyncJobState =
  | "IDLE"
  | "LOGIN_REQUIRED"
  | "AUTHENTICATED"
  | "DISCOVERING"
  | "PREVIEW_READY"
  | "SYNCING_SUBJECTS"
  | "SYNCING_DAYWISE"
  | "VALIDATING"
  | "PERSISTING"
  | "RECONCILING"
  | "COMPLETED"
  | "PARTIALLY_COMPLETED"
  | "SESSION_EXPIRED"
  | "CANCELLED"
  | "FAILED";

export interface SyncJobResponse {
  id: string;
  academic_term_id: string | null;
  source_scope: string;
  state: SyncJobState;
  current_step: string;
  start_timestamp: string;
  completion_timestamp: string | null;
  completed_batches: number;
  failed_batches: number;
  progress_total: number;
  progress_current: number;
  safe_diagnostic_message: string | null;
  details: Record<string, any> | null;
}

export interface SyncSubjectWiseResponse {
  status: string;
  snapshot_id: string | null;
  term_id: string | null;
  outcome: string;
  record_count: number;
  academic_year: string;
  semester: number;
  class_name: string | null;
  aggregate_percentage: number | null;
  validation: {
    is_valid: boolean;
    percentage_deviations: Array<{ course: string; computed: number; displayed: number; diff: number }>;
    warnings: string[];
    quarantined: boolean;
    quarantine_reason: string | null;
  };
}

export interface SyncDayWiseResponse {
  status: string;
  batch_id: string | null;
  term_id: string | null;
  outcome: string;
  coverage_start: string;
  coverage_end: string;
  total_observations: number;
  total_present: number;
  total_delivered: number;
  unmapped_count: number;
  validation: {
    is_valid: boolean;
    course_attribution_active: boolean;
    warnings: string[];
    locally_computed: Record<string, any>;
  };
}

export interface TermSyncScopeItem {
  academic_year: string;
  semester: number;
  class_identifier: string | null;
  candidate_months: string[];
  candidate_month_labels: string[];
  estimated_requests: number;
  has_subject_snapshot: boolean;
  has_daywise_batches: boolean;
  existing_batches_count: number;
  selected: boolean;
}

export interface HistoricalPlanResponse {
  discovered_academic_years: string[];
  terms: TermSyncScopeItem[];
  total_terms_count: number;
  total_estimated_requests: number;
  pacing_guidance: string;
}

// -------------------------------------------------------------
// F2-C: TOTP Vault & Persistent Mobile Identity Types
// -------------------------------------------------------------

export interface AuthSettings {
  has_saved_mobile: boolean;
  masked_mobile: string | null;
  auto_mobile_autofill: boolean;
  auto_login_continuation: boolean;
  auto_totp_autofill: boolean;
  auto_totp_submit: boolean;
}

export interface AuthSettingsUpdate {
  mobile_number?: string;
  clear_mobile?: boolean;
  auto_mobile_autofill?: boolean;
  auto_login_continuation?: boolean;
  auto_totp_autofill?: boolean;
  auto_totp_submit?: boolean;
}

export interface TotpEnrollmentMetadata {
  enrollment_id: string;
  issuer: string;
  masked_account: string;
  enrolled_at: string;
  digits: number;
  period: number;
  algorithm: string;
  auto_autofill_enabled: boolean;
  auto_submit_enabled: boolean;
}

export interface TotpStatusResponse {
  is_enrolled: boolean;
  vault_backend: string;
  is_secure_backend: boolean;
  metadata: TotpEnrollmentMetadata | null;
  clock_skew_seconds: number;
  auto_autofill_enabled: boolean;
  auto_submit_enabled: boolean;
  details: string;
}

export interface TotpCandidate {
  candidate_id: string;
  issuer: string;
  masked_account: string;
  digits: number;
  period: number;
  algorithm: string;
  source_type: string;
}

export interface TotpInspectResponse {
  candidates: TotpCandidate[];
  total_found: number;
  source_format: string;
}

export type LoginState =
  | "DISCONNECTED"
  | "SESSION_CHECKING"
  | "LOGIN_REQUIRED"
  | "ENTERING_MOBILE"
  | "WAITING_FOR_TOTP"
  | "SUBMITTING_TOTP"
  | "VERIFYING_SESSION"
  | "AUTHENTICATED"
  | "SESSION_EXPIRED"
  | "MANUAL_ACTION_REQUIRED"
  | "FAILED";

export interface LoginOrchestrationResponse {
  state: LoginState;
  step: string;
  success: boolean;
  redirected: boolean;
  message: string;
  current_url: string | null;
  has_saved_mobile: boolean;
  is_totp_enrolled: boolean;
  details: Record<string, any>;
}

// -------------------------------------------------------------
// F2-E: Multi-Semester Historical Types
// -------------------------------------------------------------

export interface HistoricalTermInventoryItem {
  term_key: string;
  academic_year: string;
  semester_number: number;
  class_identifier: string | null;
  display_label: string;
  class_display_label: string | null;
  status: string;
  has_subject_summary: boolean;
  has_daywise_data: boolean;
  existing_courses_count: number;
  existing_observations_count: number;
  attended_sum: number;
  delivered_sum: number;
  percentage: number | null;
  discovered_at: string | null;
  last_sync_timestamp: string | null;
  candidate_months: string[];
  candidate_month_labels: string[];
  estimated_requests: number;
  coverage_state: string;
  reconciliation_verdict: string;
  error_message: string | null;
}

export interface HistoricalDiscoveryResponse {
  terms: HistoricalTermInventoryItem[];
  discovered_years: string[];
  total_terms_count: number;
  available_terms_count: number;
  imported_terms_count: number;
  discovery_timestamp: string;
  provenance: string;
}

export interface HistoricalPreviewResponse {
  source_course_count?: number | null;
  approval_id?: string | null;
  selected_terms: HistoricalTermInventoryItem[];
  total_selected_terms: number;
  total_estimated_requests: number;
  estimated_pacing_seconds: number;
  pacing_guidance: string;
  requires_user_approval: boolean;
}

export interface TermCoverageResponse {
  term_id: string;
  academic_year: string;
  semester_number: number;
  class_identifier: string | null;
  coverage_state: string;
  has_subject_summary: boolean;
  subject_snapshot_count: number;
  subject_courses_count: number;
  candidate_months: string[];
  candidate_month_labels: string[];
  months_attempted: string[];
  months_completed: string[];
  unique_instructional_dates: number;
  unique_instructional_periods: number;
  mapped_periods: number;
  unmapped_periods: number;
  missing_or_unreported_periods: number;
  source_errors_count: number;
  reconciliation_verdict: string;
  details: Record<string, any>;
}




export interface TermCalendarConfig {
  term_key: string;
  academic_year: string;
  semester_number: number;
  class_identifier: string | null;
  start_date: string | null;
  end_date: string | null;
  candidate_months: string[];
  confirmed_months: string[];
  excluded_months: string[];
  approved_exceptional_months: string[];
  source: string;
  source_verification_timestamp: string | null;
  confidence_status: string;
  notes: string | null;
}
