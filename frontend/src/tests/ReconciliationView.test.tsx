import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReconciliationView } from "../components/ReconciliationView";
import type { SnapshotListItem, TermReconciliationResponse } from "../types/attendance";

const MOCK_RECONCILIATION: TermReconciliationResponse = {
  term_id: "term-1",
  academic_year: "2026-2027",
  semester_number: 5,
  subject_wise_available: true,
  day_wise_available: true,
  latest_snapshot_id: "snap-1",
  latest_batch_id: "batch-1",
  subject_wise_total_attended: 185,
  subject_wise_total_delivered: 213,
  day_wise_total_attended: 185,
  day_wise_total_delivered: 213,
  total_unmapped_observations: 0,
  coverage_start_date: "2026-08-01",
  coverage_end_date: "2026-10-15",
  reconciliation_status: "MATCHED",
  status_explanation: "Total delivered and attended periods across subject-wise and day-wise datasets match exactly.",
  course_breakdown: [
    {
      course_code: "CSH301C",
      course_name: "Computer Architecture",
      subject_wise_attended: 15,
      subject_wise_delivered: 20,
      day_wise_attended: 15,
      day_wise_delivered: 20,
      attended_diff: 0,
      delivered_diff: 0,
      status: "MATCHED",
    },
  ],
};

const MOCK_SNAPSHOTS: SnapshotListItem[] = [
  {
    id: "snap-1",
    academic_term_id: "term-1",
    source: "OFFLINE_SAMPLE_FIXTURE",
    captured_at: "2026-10-19T00:00:00Z",
    reporting_start_date: null,
    reporting_end_date: null,
    content_checksum: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
    record_count: 15,
  },
];

describe("ReconciliationView Component", () => {
  it("renders reconciliation status badge and explanation", () => {
    render(
      <ReconciliationView
        reconciliation={MOCK_RECONCILIATION}
        snapshots={MOCK_SNAPSHOTS}
        isLoading={false}
      />
    );

    expect(screen.getByText(/100% RECONCILED MATCH/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Total delivered and attended periods across subject-wise and day-wise datasets match exactly/i)
    ).toBeInTheDocument();
  });

  it("renders course breakdown and variance", () => {
    render(
      <ReconciliationView
        reconciliation={MOCK_RECONCILIATION}
        snapshots={MOCK_SNAPSHOTS}
        isLoading={false}
      />
    );

    expect(screen.getByText("CSH301C")).toBeInTheDocument();
    expect(screen.getByText("Computer Architecture")).toBeInTheDocument();
    expect(screen.getByText("0 / 0")).toBeInTheDocument();
  });

  it("renders immutable snapshots list with canonical checksum", () => {
    render(
      <ReconciliationView
        reconciliation={MOCK_RECONCILIATION}
        snapshots={MOCK_SNAPSHOTS}
        isLoading={false}
      />
    );

    expect(screen.getByText("snap-1")).toBeInTheDocument();
    expect(screen.getByText("OFFLINE_SAMPLE_FIXTURE")).toBeInTheDocument();
    expect(screen.getByText("15 courses")).toBeInTheDocument();
  });
});
