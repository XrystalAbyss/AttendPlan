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
