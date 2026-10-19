import type {
  AcademicHistoryResponse,
  AcademicTerm,
  AcademicTermDiscoveryResponse,
  AttendanceSnapshot,
  DayWiseDiscoveryResponse,
  MonthlyAnalyticsItem,
  OverallDiscoveryResponse,
  PortalSessionStatus,
  SnapshotListItem,
  SubjectAnalyticsResponse,
  SubjectWiseDiscoveryResponse,
  TermAttendanceResponse,
  TermReconciliationResponse,
  WeekdayAnalyticsItem,
} from "../types/attendance";

const API_BASE = "http://127.0.0.1:8000";

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
  return res.json();
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
