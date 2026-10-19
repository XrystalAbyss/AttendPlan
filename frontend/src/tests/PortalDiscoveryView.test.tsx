import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PortalDiscoveryView } from "../components/PortalDiscoveryView";

// Mock API functions
vi.mock("../api/attendance", () => ({
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

    expect(screen.getByText(/1. Term & Semester/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Subject-Wise/i)).toBeInTheDocument();
    expect(screen.getByText(/3. Day-Wise Timetable/i)).toBeInTheDocument();
    expect(screen.getByText(/4. Overall View/i)).toBeInTheDocument();
  });
});
