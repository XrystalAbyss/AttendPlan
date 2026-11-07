import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HistoricalAttendanceView } from "../components/HistoricalAttendanceView";
import type { HistoricalDiscoveryResponse, TermCoverageResponse, TermAttendanceResponse } from "../types/attendance";

const MOCK_INVENTORY: HistoricalDiscoveryResponse = {
  terms: [
    {
      term_key: "2024-2025_s1_1050",
      academic_year: "2024-2025",
      semester_number: 1,
      class_identifier: "1050",
      display_label: "Semester 1 (2024-2025)",
      class_display_label: "B.Tech CSE AIML-Sem 1",
      status: "AVAILABLE",
      has_subject_summary: true,
      has_daywise_data: false,
      existing_courses_count: 3,
      existing_observations_count: 0,
      attended_sum: 82,
      delivered_sum: 94,
      percentage: 87.23,
      discovered_at: "2026-10-20T10:00:00Z",
      last_sync_timestamp: "2026-10-20T10:00:00Z",
      candidate_months: ["8", "9", "10", "11", "12"],
      candidate_month_labels: ["August", "September", "October", "November", "December"],
      estimated_requests: 6,
      coverage_state: "PARTIAL",
      reconciliation_verdict: "NOT_AVAILABLE",
      error_message: null,
    },
    {
      term_key: "2025-2026_s4_2140",
      academic_year: "2025-2026",
      semester_number: 4,
      class_identifier: "2140",
      display_label: "Semester 4 (2025-2026)",
      class_display_label: "B.Tech CSE AIML-Sem 4",
      status: "AVAILABLE",
      has_subject_summary: true,
      has_daywise_data: true,
      existing_courses_count: 7,
      existing_observations_count: 88,
      attended_sum: 160,
      delivered_sum: 191,
      percentage: 83.77,
      discovered_at: "2026-10-20T10:00:00Z",
      last_sync_timestamp: "2026-10-20T10:00:00Z",
      candidate_months: ["1", "2", "3", "4", "5"],
      candidate_month_labels: ["January", "February", "March", "April", "May"],
      estimated_requests: 6,
      coverage_state: "PARTIAL",
      reconciliation_verdict: "MATCHED",
      error_message: null,
    },
  ],
  discovered_years: ["2025-2026", "2024-2025"],
  total_terms_count: 2,
  available_terms_count: 2,
  imported_terms_count: 2,
  discovery_timestamp: "2026-10-20T10:00:00Z",
  provenance: "LOCAL_DATABASE",
};

const MOCK_COVERAGE: TermCoverageResponse = {
  term_id: "term-s4",
  academic_year: "2025-2026",
  semester_number: 4,
  class_identifier: "2140",
  coverage_state: "PARTIAL",
  has_subject_summary: true,
  subject_snapshot_count: 1,
  subject_courses_count: 7,
  candidate_months: ["1", "2", "3", "4", "5"],
  candidate_month_labels: ["January", "February", "March", "April", "May"],
  months_attempted: ["3"],
  months_completed: ["3"],
  unique_instructional_dates: 12,
  unique_instructional_periods: 88,
  mapped_periods: 88,
  unmapped_periods: 0,
  missing_or_unreported_periods: 12,
  source_errors_count: 0,
  reconciliation_verdict: "MATCHED",
  details: {},
};

const MOCK_ATTENDANCE: TermAttendanceResponse = {
  term_id: "term-s4",
  academic_year: "2025-2026",
  semester: 4,
  class_name: "B.Tech CSE AIML-Sem 4",
  snapshot_id: "snap-test-01",
  target_percentage: 75.0,
  provenance: "LOCAL_PERSISTED",
  captured_at: "2026-10-20T10:00:00Z",
  summary: {
    total_courses: 2,
    active_courses: 1,
    unrecorded_courses: 1,
    safe_courses: 1,
    at_risk_courses: 0,
    total_attended: 32,
    total_delivered: 36,
    overall_percentage: 88.89,
    overall_status: "SAFE",
  },
  courses: [
    {
      code: "CSH201C",
      name: "DATA STRUCTURES & ALGORITHMS",
      short_name: "DSA",
      faculty: "Dr. A. Sharma",
      credits: 4.0,
      is_lab: false,
      attended: 32,
      delivered: 36,
      percent: 88.89,
      status: "SAFE",
      can_skip: 6,
      must_attend: 0,
      margin_summary: "6 bunks available",
    },
    {
      code: "RDO102",
      name: "RESEARCH PROJECT-I",
      short_name: "RP-I",
      faculty: "Faculty Guide",
      credits: 1.0,
      is_lab: false,
      attended: 0,
      delivered: 0,
      percent: null,
      status: "UNRECORDED",
      can_skip: null,
      must_attend: null,
      margin_summary: "No sessions recorded",
    },
  ],
};

// Mock API functions
vi.mock("../api/attendance", () => ({
  fetchHistoricalTerms: vi.fn().mockImplementation(() => Promise.resolve(MOCK_INVENTORY)),
  fetchAcademicTerms: vi.fn().mockImplementation(() =>
    Promise.resolve([
      {
        id: "term-s4",
        institution_key: "mrei",
        academic_year: "2025-2026",
        semester_number: 4,
        class_identifier: "2140",
        total_courses: 2,
        total_attended: 32,
        total_delivered: 36,
        overall_percentage: 88.89,
        overall_status: "SAFE",
        has_datewise_data: true,
      },
    ])
  ),
  discoverHistoricalTerms: vi.fn().mockImplementation(() => Promise.resolve(MOCK_INVENTORY)),

  previewHistoricalImport: vi.fn().mockImplementation(() =>
    Promise.resolve({
      selected_terms: MOCK_INVENTORY.terms,
      total_selected_terms: 2,
      total_estimated_requests: 12,
      estimated_pacing_seconds: 24.0,
      pacing_guidance: "Conservative pacing: 1.5s - 2.5s between requests to respect portal load limits.",
      requires_user_approval: true,
    })
  ),
  startHistoricalImport: vi.fn().mockImplementation(() =>
    Promise.resolve({
      id: "job-123",
      academic_term_id: "term-s4",
      source_scope: "HISTORICAL_MULTI_SEMESTER_BACKFILL",
      state: "SYNCING_SUBJECTS",
      current_step: "Extracting subject-wise roster...",
      start_timestamp: "2026-10-20T10:00:00Z",
      completion_timestamp: null,
      completed_batches: 0,
      failed_batches: 0,
      progress_total: 12,
      progress_current: 1,
      safe_diagnostic_message: null,
      details: null,
    })
  ),
  fetchHistoricalImportProgress: vi.fn().mockImplementation(() => Promise.resolve(null)),
  cancelHistoricalImport: vi.fn().mockImplementation(() => Promise.resolve(null)),
  fetchTermAttendance: vi.fn().mockImplementation(() => Promise.resolve(MOCK_ATTENDANCE)),
  fetchTermCoverage: vi.fn().mockImplementation(() => Promise.resolve(MOCK_COVERAGE)),
  fetchMonthlyAnalytics: vi.fn().mockImplementation(() =>
    Promise.resolve([
      {
        year: 2026,
        month: 3,
        month_label: "March 2026",
        delivered: 36,
        attended: 32,
        missed: 4,
        attendance_percentage: 88.89,
        absence_percentage: 11.11,
        observed_dates_count: 12,
        coverage: "COMPLETE",
      },
    ])
  ),
  fetchWeekdayAnalytics: vi.fn().mockImplementation(() =>
    Promise.resolve([
      {
        weekday_index: 0,
        weekday_name: "Monday",
        delivered: 8,
        attended: 7,
        missed: 1,
        absence_rate: 12.5,
        observed_teaching_dates: 4,
        coverage: "COMPLETE",
      },
    ])
  ),
}));

describe("HistoricalAttendanceView Component", () => {
  const createTestClient = () =>
    new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

  it("renders historical attendance header, actions, and discovered terms", async () => {
    const client = createTestClient();
    render(
      <QueryClientProvider client={client}>
        <HistoricalAttendanceView targetPercentage={75} />
      </QueryClientProvider>
    );

    expect(screen.getByText(/Historical Academic Attendance History/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Discover Terms/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Import Selected Terms/i })).toBeInTheDocument();


    await waitFor(() => {
      expect(screen.getByText("Semester 1 (2024-2025)")).toBeInTheDocument();
      expect(screen.getByText("Semester 4 (2025-2026)")).toBeInTheDocument();
    });
  });

  it("renders course roster with exact data and unrecorded courses as '--'", async () => {
    const client = createTestClient();
    render(
      <QueryClientProvider client={client}>
        <HistoricalAttendanceView targetPercentage={75} />
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByText("Semester 4 (2025-2026)"));
    await waitFor(() => {
      expect(screen.getByText("CSH201C")).toBeInTheDocument();
      expect(screen.getByText("DATA STRUCTURES & ALGORITHMS")).toBeInTheDocument();
      expect(screen.getByText("RDO102")).toBeInTheDocument();
      expect(screen.getByText("RESEARCH PROJECT-I")).toBeInTheDocument();
      // Unrecorded course percentage should display as '--', not '0%'
      expect(screen.getByText("--")).toBeInTheDocument();
    });
  });

  it("allows selecting one semester and triggering preview", async () => {
    const client = createTestClient();
    render(
      <QueryClientProvider client={client}>
        <HistoricalAttendanceView targetPercentage={75} />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Semester 1 (2024-2025)")).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole("checkbox");
    // Click checkbox for first term
    fireEvent.click(checkboxes[1]);

    const previewButton = screen.getByText(/Preview Import/i);
    fireEvent.click(previewButton);

    await waitFor(() => {
      expect(screen.getByText(/Pre-Sync Historical Workload Inspection/i)).toBeInTheDocument();
    });
  });
});
