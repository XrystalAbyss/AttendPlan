import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PortalDiscoveryView } from "../components/PortalDiscoveryView";

// Mock API functions
vi.mock("../api/attendance", () => ({
  fetchHistoricalTerms: vi.fn().mockResolvedValue({terms:[]}),
  fetchPortalSessionStatus: vi.fn().mockResolvedValue({
    state: "DISCONNECTED",
    browser_launched: false,
    cdp_port: 9222,
    cdp_url: "http://127.0.0.1:9222",
    current_url: null,
    page_title: null,
    profile_dir: "C:\\Users\\Mock\\AppData\\AttendPlan\\chrome-profile",
    details: "No browser session connected on loopback port 9222.",
    manual_fallback_available: true,
  }),
  launchPortalBrowser: vi.fn().mockResolvedValue({
    state: "BROWSER_READY",
    browser_launched: true,
    cdp_port: 9222,
    cdp_url: "http://127.0.0.1:9222",
  }),
  closePortalBrowser: vi.fn().mockResolvedValue({
    state: "DISCONNECTED",
    browser_launched: false,
  }),
  discoverTerms: vi.fn(),
  discoverSubjectWise: vi.fn(),
  discoverDayWise: vi.fn(),
  discoverOverall: vi.fn(),
  seedDemoData: vi.fn().mockResolvedValue({ outcome: "SUCCESS" }),
  fetchLatestSyncJob: vi.fn().mockResolvedValue(null),
  syncSubjectWiseLive: vi.fn(),
  syncDayWiseLive: vi.fn(),
  runPilotSync: vi.fn(),
  fetchHistoricalPlan: vi.fn().mockResolvedValue({
    discovered_academic_years: ["2025-2026", "2024-2025"],
    terms: [
      {
        academic_year: "2025-2026",
        semester: 5,
        class_identifier: "2582",
        candidate_months: ["08", "09", "10", "11", "12"],
        candidate_month_labels: ["Aug", "Sep", "Oct", "Nov", "Dec"],
        estimated_requests: 12,
        has_subject_snapshot: true,
        has_daywise_batches: true,
        existing_batches_count: 2,
        selected: true,
      },
    ],
    total_terms_count: 1,
    total_estimated_requests: 12,
    pacing_guidance: "Pause 1500ms between requests.",
  }),
  cancelSyncJob: vi.fn(),
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("PortalDiscoveryView Component", () => {
  it("renders portal discovery header, diagnostic panels, and initial disconnected state", async () => {
    renderWithClient(<PortalDiscoveryView />);

    expect(screen.getByText(/iCloudEMS Portal Discovery/i)).toBeInTheDocument();
    expect(screen.getByText(/Dedicated Chrome Profile/i)).toBeInTheDocument();
    expect(screen.getByText(/CDP Loopback Endpoint/i)).toBeInTheDocument();
    expect(screen.getByText(/127.0.0.1:9222/i)).toBeInTheDocument();

    const launchBtn = await screen.findByRole("button", { name: /Launch Dedicated Chrome/i });
    expect(launchBtn).toBeInTheDocument();
  });

  it("toggles manual HTML fallback input on button click", async () => {
    renderWithClient(<PortalDiscoveryView />);

    const fallbackToggle = screen.getByRole("button", { name: /Use Manual HTML Fallback/i });
    expect(fallbackToggle).toBeInTheDocument();

    // Click to activate manual input
    fireEvent.click(fallbackToggle);

    expect(await screen.findByPlaceholderText(/Paste raw <html>/i)).toBeInTheDocument();
    expect(screen.getByText(/Manual HTML Source Fallback/i)).toBeInTheDocument();
  });

  it("renders discovery area cards for Terms, Subject-Wise, Day-Wise, and Overall", () => {
    renderWithClient(<PortalDiscoveryView />);

    // Switch to DOM discovery subtab
    const discoveryTab = screen.getByRole("button", { name: /DOM Discovery/i });
    fireEvent.click(discoveryTab);

    expect(screen.getByText(/1. Term & Semester/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Subject-Wise/i)).toBeInTheDocument();
    expect(screen.getByText(/3. Day-Wise Timetable/i)).toBeInTheDocument();
    expect(screen.getByText(/4. Overall View/i)).toBeInTheDocument();
  });

  it("renders F2-B Live Synchronization Center cards and controls", () => {
    renderWithClient(<PortalDiscoveryView />);

    expect(screen.getByText(/Current-Semester Pilot Synchronization/i)).toBeInTheDocument();
    expect(screen.getByText(/Subject-Wise Attendance Live Extraction/i)).toBeInTheDocument();
    expect(screen.getByText(/Day-Wise Timetable Matrix Live Extraction/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Execute Current Semester Pilot Sync/i })).toBeInTheDocument();
  });

  it("renders F2-B Historical Sync Planner and displays generated multi-semester plan", async () => {
    renderWithClient(<PortalDiscoveryView />);

    // Switch to planner subtab
    const plannerTab = screen.getByRole("button", { name: /Historical Sync Planner/i });
    fireEvent.click(plannerTab);

    const generateBtn = screen.getByRole("button", { name: /Generate Multi-Semester Plan/i });
    expect(generateBtn).toBeInTheDocument();

    fireEvent.click(generateBtn);

    expect(await screen.findByText(/Discovered Academic Years/i)).toBeInTheDocument();
    expect(screen.getByText(/Total Estimated Requests/i)).toBeInTheDocument();
    expect(screen.getByText(/12 portal interactions/i)).toBeInTheDocument();
  });
});
