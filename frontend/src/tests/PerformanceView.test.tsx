import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PerformanceView } from "../components/PerformanceView";

afterEach(() => vi.unstubAllGlobals());

const baseData = {
  terms: [],
  discovered_terms: [
    { term_key: "synthetic_s4", label: "Synthetic Semester 4", selector_verified: true },
  ],
  note: "Only imported semesters are shown.",
  live_capture_enabled: true,
};

function renderComponent() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <PerformanceView />
    </QueryClientProvider>
  );
}

describe("PerformanceView", () => {
  it("shows the missing-data state without inventing results and includes action button", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => baseData }));
    renderComponent();

    expect(await screen.findByText(/No marks or semester results have been imported/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import Marks from University Portal" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview performance scope" })).toBeDisabled();
  });

  it("results view cannot trigger retrieval and never shows approval", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => baseData }));
    renderComponent();

    await screen.findByRole("option", { name: "Synthetic Semester 4" });
    fireEvent.change(screen.getByLabelText("Performance semester"), { target: { value: "synthetic_s4" } });
    fireEvent.change(screen.getByLabelText("Performance view"), { target: { value: "results" } });

    expect(screen.getByRole("status")).toHaveTextContent(/Official semester results live portal import has been retired/);
    expect(screen.getByRole("button", { name: "Preview performance scope" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Approve this performance import" })).not.toBeInTheDocument();
  });

  it("valid marks preview enables approval button and approving invokes import with approval_id", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith("discover-scopes")) {
        return {
          ok: true,
          json: async () => ({
            term_key: "synthetic_s4",
            scopes: [
              {
                exam_session: "2024-25_EVEN",
                exam_session_label: "2024-25 Even",
                exam_type: "3",
                exam_type_label: "Continuous Evaluation",
              },
            ],
          }),
        };
      }
      if (url.endsWith("preview")) {
        return {
          ok: true,
          json: async () => ({
            approval_id: "preview-job-uuid-123",
            term_key: "synthetic_s4",
            label: "Synthetic Semester 4",
            class_label: "B.Tech CSE Sem 4",
            view: "marks",
            exam_session: "2024-25_EVEN",
            exam_type: "3",
            source_course_count: 6,
            scope: "One semester only",
          }),
        };
      }
      if (url.endsWith("import")) {
        return {
          ok: true,
          json: async () => ({
            snapshot_id: "snap-456",
            term_key: "synthetic_s4",
            view: "marks:2024-25_EVEN:3:",
            provenance: "PORTAL_LIVE_VERIFIED",
          }),
        };
      }
      return { ok: true, json: async () => baseData };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderComponent();
    await screen.findByRole("option", { name: "Synthetic Semester 4" });

    // Select semester
    fireEvent.change(screen.getByLabelText("Performance semester"), { target: { value: "synthetic_s4" } });

    // Discover scopes
    fireEvent.click(screen.getByRole("button", { name: "Discover exam options" }));
    await screen.findByRole("option", { name: /Continuous Evaluation/ });

    // Select exam scope
    fireEvent.change(screen.getByLabelText("Performance exam scope"), {
      target: { value: "2024-25_EVEN:3" },
    });

    // Preview
    const previewBtn = screen.getByRole("button", { name: "Preview performance scope" });
    expect(previewBtn).not.toBeDisabled();
    fireEvent.click(previewBtn);

    // Verify preview and approval button
    expect(await screen.findByText("One semester only")).toBeInTheDocument();
    expect(screen.getByText(/Courses: 6/)).toBeInTheDocument();

    const approveBtn = screen.getByRole("button", { name: "Approve this performance import" });
    expect(approveBtn).toBeInTheDocument();
    expect(approveBtn).not.toBeDisabled();

    // Click approval
    fireEvent.click(approveBtn);

    await waitFor(() => {
      const importCall = fetchMock.mock.calls.find((call) => call[0].endsWith("import"));
      expect(importCall).toBeDefined();
      const body = JSON.parse(importCall[1].body);
      expect(body.approval_id).toBe("preview-job-uuid-123");
      expect(body.term_key).toBe("synthetic_s4");
      expect(body.view).toBe("marks");
      expect(body.exam_session).toBe("2024-25_EVEN");
      expect(body.exam_type).toBe("3");
    });
  });

  it("changing semester or exam scope invalidates approval", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith("discover-scopes")) {
        return {
          ok: true,
          json: async () => ({
            term_key: "synthetic_s4",
            scopes: [
              {
                exam_session: "2024-25_EVEN",
                exam_session_label: "2024-25 Even",
                exam_type: "3",
                exam_type_label: "Continuous Evaluation",
              },
            ],
          }),
        };
      }
      if (url.endsWith("preview")) {
        return {
          ok: true,
          json: async () => ({
            approval_id: "preview-job-uuid-123",
            term_key: "synthetic_s4",
            label: "Synthetic Semester 4",
            view: "marks",
            scope: "One semester only",
          }),
        };
      }
      return { ok: true, json: async () => baseData };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderComponent();
    await screen.findByRole("option", { name: "Synthetic Semester 4" });
    fireEvent.change(screen.getByLabelText("Performance semester"), { target: { value: "synthetic_s4" } });
    fireEvent.click(screen.getByRole("button", { name: "Discover exam options" }));
    await screen.findByRole("option", { name: /Continuous Evaluation/ });
    fireEvent.change(screen.getByLabelText("Performance exam scope"), {
      target: { value: "2024-25_EVEN:3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview performance scope" }));

    expect(await screen.findByRole("button", { name: "Approve this performance import" })).toBeInTheDocument();

    // Changing semester resets preview and removes approval button
    fireEvent.change(screen.getByLabelText("Performance semester"), { target: { value: "" } });
    expect(screen.queryByRole("button", { name: "Approve this performance import" })).not.toBeInTheDocument();
  });

  it("failed marks import displays actionable error message", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith("discover-scopes")) {
        return {
          ok: true,
          json: async () => ({
            term_key: "synthetic_s4",
            scopes: [
              {
                exam_session: "2024-25_EVEN",
                exam_session_label: "2024-25 Even",
                exam_type: "3",
                exam_type_label: "Continuous Evaluation",
              },
            ],
          }),
        };
      }
      if (url.endsWith("preview")) {
        return {
          ok: true,
          json: async () => ({
            approval_id: "preview-job-uuid-123",
            term_key: "synthetic_s4",
            label: "Synthetic Semester 4",
            view: "marks",
            scope: "One semester only",
          }),
        };
      }
      if (url.endsWith("import")) {
        return {
          ok: false,
          json: async () => ({ detail: "Preview expired or was already used." }),
        };
      }
      return { ok: true, json: async () => baseData };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderComponent();
    await screen.findByRole("option", { name: "Synthetic Semester 4" });
    fireEvent.change(screen.getByLabelText("Performance semester"), { target: { value: "synthetic_s4" } });
    fireEvent.click(screen.getByRole("button", { name: "Discover exam options" }));
    await screen.findByRole("option", { name: /Continuous Evaluation/ });
    fireEvent.change(screen.getByLabelText("Performance exam scope"), {
      target: { value: "2024-25_EVEN:3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview performance scope" }));

    const approveBtn = await screen.findByRole("button", { name: "Approve this performance import" });
    fireEvent.click(approveBtn);

    expect(await screen.findByRole("alert")).toHaveTextContent(/Preview expired or was already used/);
  });
});
