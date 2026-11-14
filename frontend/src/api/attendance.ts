import type {
  AcademicHistoryResponse,
  AcademicTerm,
  AcademicTermDiscoveryResponse,
  AttendanceSnapshot,
  DayWiseDiscoveryResponse,
  HistoricalPlanResponse,
  MonthlyAnalyticsItem,
  OverallDiscoveryResponse,
  PortalSessionStatus,
  SnapshotListItem,
  SubjectAnalyticsResponse,
  SubjectWiseDiscoveryResponse,
  SyncDayWiseResponse,
  SyncJobResponse,
  SyncSubjectWiseResponse,
  TermAttendanceResponse,
  TermReconciliationResponse,
  WeekdayAnalyticsItem,
  AuthSettings,
  AuthSettingsUpdate,
  TotpStatusResponse,
  TotpInspectResponse,
  TotpEnrollmentMetadata,
  LoginOrchestrationResponse,
  HistoricalDiscoveryResponse,
  HistoricalPreviewResponse,
  TermCoverageResponse,
  TermCalendarConfig,
} from "../types/attendance";



export const API_BASE = "";

export async function fetchHealth(): Promise<{ status: string; app: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`);
  }
  return res.json();
}

export async function fetchSampleAttendance(targetPercentage: number = 75.0): Promise<AttendanceSnapshot> {
  const res = await fetch(`${API_BASE}/api/v1/attendance/sample?target=${targetPercentage}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch sample attendance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAcademicTerms(targetPercentage: number = 75.0): Promise<AcademicTerm[]> {
  const res = await fetch(`${API_BASE}/api/v1/terms?target=${targetPercentage}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch academic terms: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTermAttendance(
  termId: string,
  targetPercentage: number = 75.0
): Promise<TermAttendanceResponse> {
  const res = await fetch(`${API_BASE}/api/v1/terms/${termId}/attendance?target=${targetPercentage}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch term attendance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTermSnapshots(termId: string): Promise<SnapshotListItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/terms/${termId}/snapshots`);
  if (!res.ok) {
    throw new Error(`Failed to fetch term snapshots: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMonthlyAnalytics(termId: string): Promise<MonthlyAnalyticsItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/terms/${termId}/analytics/monthly`);
  if (!res.ok) {
    throw new Error(`Failed to fetch monthly analytics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchWeekdayAnalytics(termId: string): Promise<WeekdayAnalyticsItem[]> {
  const res = await fetch(`${API_BASE}/api/v1/terms/${termId}/analytics/weekday`);
  if (!res.ok) {
    throw new Error(`Failed to fetch weekday analytics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSubjectAnalytics(
  termId: string,
  targetPercentage: number = 75.0
): Promise<SubjectAnalyticsResponse> {
  const res = await fetch(`${API_BASE}/api/v1/terms/${termId}/analytics/subjects?target=${targetPercentage}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch subject analytics: ${res.statusText}`);
  }
  const data = await res.json();
  const normalize = (rows: {code: string; name: string; missed_periods?: number; absence_rate?: number; delivered_periods?: number}[], field: "missed_periods" | "absence_rate" | "delivered_periods") => rows.map(row => ({course_code: row.code, course_name: row.name, value: row[field] ?? 0}));
  return {...data, rankings: {
    by_absolute_missed: normalize(data.rankings.by_absolute_missed, "missed_periods"),
    by_missed_rate: normalize(data.rankings.by_missed_rate, "absence_rate"),
    by_total_delivered: normalize(data.rankings.by_total_delivered, "delivered_periods"),
  }};
}

export async function fetchAcademicHistory(
  targetPercentage: number = 75.0
): Promise<AcademicHistoryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/analytics/academic-history?target=${targetPercentage}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch academic history: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTermReconciliation(termId: string): Promise<TermReconciliationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/terms/${termId}/reconciliation`);
  if (!res.ok) {
    throw new Error(`Failed to fetch term reconciliation: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPortalSessionStatus(): Promise<PortalSessionStatus> {
  const res = await fetch(`${API_BASE}/api/v1/portal/session/status`);
  if (!res.ok) {
    throw new Error(`Failed to fetch portal session status: ${res.statusText}`);
  }
  return res.json();
}

export async function launchPortalBrowser(): Promise<PortalSessionStatus> {
  const res = await fetch(`${API_BASE}/api/v1/portal/session/launch`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Failed to launch dedicated browser: ${res.statusText}`);
  }
  return res.json();
}

export async function closePortalBrowser(): Promise<PortalSessionStatus> {
  const res = await fetch(`${API_BASE}/api/v1/portal/session/close`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Failed to close browser: ${res.statusText}`);
  }
  return res.json();
}

export async function discoverTerms(htmlContent?: string): Promise<AcademicTermDiscoveryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/discover/terms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html_content: htmlContent || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Term discovery failed: ${res.statusText}`);
  }
  return res.json();
}

export async function discoverSubjectWise(htmlContent?: string): Promise<SubjectWiseDiscoveryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/discover/subject-wise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html_content: htmlContent || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Subject-wise discovery failed: ${res.statusText}`);
  }
  return res.json();
}

export async function discoverDayWise(htmlContent?: string): Promise<DayWiseDiscoveryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/discover/day-wise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html_content: htmlContent || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Day-wise discovery failed: ${res.statusText}`);
  }
  return res.json();
}

export async function discoverOverall(htmlContent?: string): Promise<OverallDiscoveryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/discover/overall`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html_content: htmlContent || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Overall discovery failed: ${res.statusText}`);
  }
  return res.json();
}

export async function seedDemoData(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/demo/seed`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Failed to seed demo data: ${res.statusText}`);
  }
  return res.json();
}

export async function syncSubjectWiseLive(payload: {
  academic_year?: string;
  semester?: number;
  class_id?: string;
  persist?: boolean;
}): Promise<SyncSubjectWiseResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/sync/subject-wise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Subject-wise sync failed: ${res.statusText}`);
  }
  return res.json();
}

export async function syncDayWiseLive(payload: {
  academic_year?: string;
  semester?: number;
  class_id?: string;
  month?: string;
  from_date?: string;
  to_date?: string;
  show_course_name?: boolean;
  persist?: boolean;
}): Promise<SyncDayWiseResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/sync/day-wise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Day-wise sync failed: ${res.statusText}`);
  }
  return res.json();
}

export async function runPilotSync(payload: {
  academic_year?: string;
  semester?: number;
  class_id?: string;
  month?: string;
}): Promise<SyncJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/sync/pilot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Pilot sync failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchHistoricalPlan(): Promise<HistoricalPlanResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/sync/historical-plan`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch historical plan: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchLatestSyncJob(): Promise<SyncJobResponse | null> {
  const res = await fetch(`${API_BASE}/api/v1/portal/sync/jobs/latest`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch latest sync job: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSyncJob(jobId: string): Promise<SyncJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/sync/jobs/${jobId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch sync job ${jobId}: ${res.statusText}`);
  }
  return res.json();
}

export async function cancelSyncJob(jobId: string): Promise<SyncJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/portal/sync/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to cancel sync job: ${res.statusText}`);
  }
  return res.json();
}

// -------------------------------------------------------------
// F2-C: TOTP Vault, Persistent Mobile & Login Orchestrator
// -------------------------------------------------------------

export async function fetchAuthSettings(): Promise<AuthSettings> {
  const res = await fetch(`${API_BASE}/api/v1/auth/settings`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch auth settings: ${res.statusText}`);
  }
  return res.json();
}

export async function updateAuthSettings(payload: AuthSettingsUpdate): Promise<AuthSettings> {
  const res = await fetch(`${API_BASE}/api/v1/auth/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update auth settings: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTotpStatus(): Promise<TotpStatusResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/totp/status`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch TOTP status: ${res.statusText}`);
  }
  return res.json();
}

export async function inspectTotp(file?: File, provisioningInput?: string): Promise<TotpInspectResponse> {
  const formData = new FormData();
  if (file) {
    formData.append("file", file);
  }
  if (provisioningInput) {
    formData.append("provisioning_input", provisioningInput);
  }
  const res = await fetch(`${API_BASE}/api/v1/auth/totp/inspect`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to inspect TOTP: ${res.statusText}`);
  }
  return res.json();
}

export async function enrollTotp(payload: {
  candidate_id?: string;
  secret_base32?: string;
  provisioning_input?: string;
  issuer?: string;
  account_label?: string;
  auto_autofill_enabled?: boolean;
  auto_submit_enabled?: boolean;
}): Promise<TotpEnrollmentMetadata> {
  const res = await fetch(`${API_BASE}/api/v1/auth/totp/enroll`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to enroll TOTP secret: ${res.statusText}`);
  }
  return res.json();
}

export async function enrollTotpImage(
  file: File,
  options?: {
    candidate_id?: string;
    auto_autofill_enabled?: boolean;
    auto_submit_enabled?: boolean;
  }
): Promise<TotpEnrollmentMetadata> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.candidate_id) formData.append("candidate_id", options.candidate_id);
  if (options?.auto_autofill_enabled !== undefined) {
    formData.append("auto_autofill_enabled", String(options.auto_autofill_enabled));
  }
  if (options?.auto_submit_enabled !== undefined) {
    formData.append("auto_submit_enabled", String(options.auto_submit_enabled));
  }

  const res = await fetch(`${API_BASE}/api/v1/auth/totp/enroll-image`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to enroll QR image: ${res.statusText}`);
  }
  return res.json();
}

export async function verifyTotp(code: string): Promise<{ valid: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/totp/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Verification failed: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteTotpEnrollment(): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/totp/enrollment`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to delete TOTP enrollment: ${res.statusText}`);
  }
  return res.json();
}

export async function orchestrateLogin(forceSubmit?: boolean): Promise<LoginOrchestrationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_submit: forceSubmit ?? null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Login orchestration failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchLoginStatus(): Promise<LoginOrchestrationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login/status`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch login status: ${res.statusText}`);
  }
  return res.json();
}

// -------------------------------------------------------------
// F2-E: Multi-Semester Historical Discovery & Backfill API
// -------------------------------------------------------------

export async function fetchHistoricalTerms(): Promise<HistoricalDiscoveryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/historical/terms`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch historical terms: ${res.statusText}`);
  }
  return res.json();
}

export async function discoverHistoricalTerms(htmlContent?: string): Promise<HistoricalDiscoveryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/historical/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html_content: htmlContent || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to discover terms: ${res.statusText}`);
  }
  return res.json();
}

export async function previewHistoricalImport(selectedTermKeys?: string[]): Promise<HistoricalPreviewResponse> {
  const res = await fetch(`${API_BASE}/api/v1/historical/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_term_keys: selectedTermKeys || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to preview import: ${res.statusText}`);
  }
  return res.json();
}

export async function startHistoricalImport(
  selectedTermKeys: string[],
  importDaywise: boolean = false,
  maxMonthsPerTerm?: number,
  approvalId?: string
): Promise<SyncJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/historical/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      approval_id: approvalId,
      selected_term_keys: selectedTermKeys,
      import_daywise: importDaywise,
      max_months_per_term: maxMonthsPerTerm || null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to start import: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchHistoricalImportProgress(): Promise<SyncJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/historical/import/progress`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch import progress: ${res.statusText}`);
  }
  return res.json();
}

export async function cancelHistoricalImport(): Promise<SyncJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/historical/import/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to cancel import: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTermCoverage(termId: string): Promise<TermCoverageResponse> {
  const res = await fetch(`${API_BASE}/api/v1/terms/${termId}/coverage`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch term coverage: ${res.statusText}`);
  }
  return res.json();
}




export async function fetchTermCalendars(): Promise<{ calendars: TermCalendarConfig[] }> {
  const res = await fetch(`${API_BASE}/api/v1/attendance-archive/calendars`);
  if (!res.ok) throw new Error("Failed to fetch term calendars");
  return res.json();
}

export async function updateTermCalendar(
  termKey: string,
  update: {
    candidate_months?: string[];
    excluded_months?: string[];
    approved_exceptional_months?: string[];
    notes?: string;
  }
): Promise<{ calendar: TermCalendarConfig }> {
  const res = await fetch(`${API_BASE}/api/v1/attendance-archive/calendars/${encodeURIComponent(termKey)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!res.ok) throw new Error("Failed to update term calendar");
  return res.json();
}

export async function resetTermCalendar(termKey: string): Promise<{ calendar: TermCalendarConfig }> {
  const res = await fetch(`${API_BASE}/api/v1/attendance-archive/calendars/${encodeURIComponent(termKey)}/reset`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to reset term calendar");
  return res.json();
}
