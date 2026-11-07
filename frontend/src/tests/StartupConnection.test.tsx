import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StartupConnection } from "../components/StartupConnection";

afterEach(() => vi.unstubAllGlobals());

function show() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <StartupConnection />
    </QueryClientProvider>
  );
}

describe("StartupConnection", () => {
  it("keeps saved data available and does not connect without opt-in", async () => {
    const fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        auto_connect: false,
        refresh_approved_scopes: false,
        auto_refresh_current_term: false,
        approved_scope_count: 0,
      }),
    });
    vi.stubGlobal("fetch", fetch);
    show();
    await screen.findByText(/The first one-semester import/);
    expect(screen.getByLabelText("Connect on opening AttendPlan")).not.toBeChecked();
    expect(screen.getByLabelText("Automatic current-semester refresh on opening")).not.toBeChecked();
    expect(screen.getByLabelText("Refresh previously approved scopes")).toBeDisabled();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("uses the background connect endpoint without calling import or vault endpoints", async () => {
    const fetch = vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      json: async () =>
        url.endsWith("settings")
          ? {
              auto_connect: true,
              refresh_approved_scopes: false,
              auto_refresh_current_term: false,
              approved_scope_count: 0,
            }
          : {
              state: "PREVIEW_READY",
              message: "Synthetic connection checked",
              running: false,
              refreshed_scopes: 0,
              discovered_terms: 5,
            },
    }));
    vi.stubGlobal("fetch", fetch);
    show();
    await screen.findByText("Synthetic connection checked");
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => url.endsWith("/connect"))).toBe(true));
    expect(fetch.mock.calls.every(([url]) => url.includes("/startup/"))).toBe(true);
    expect(screen.getByText(/5 semester\/class combinations/)).toBeInTheDocument();
  });

  it("triggers manual current-semester refresh when button is clicked", async () => {
    const fetch = vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      json: async () =>
        url.endsWith("settings")
          ? {
              auto_connect: false,
              refresh_approved_scopes: false,
              auto_refresh_current_term: false,
              approved_scope_count: 1,
              last_sync_time: "2026-10-28T14:00:00Z",
            }
          : url.endsWith("refresh-current")
          ? {
              state: "SYNC_COMPLETE",
              message: "Current semester synchronized successfully.",
              running: false,
              refreshed_scopes: 1,
              last_sync_time: "2026-10-28T14:15:00Z",
            }
          : {
              state: "UP_TO_DATE",
              message: "Attendance is up to date.",
              running: false,
              refreshed_scopes: 0,
              last_sync_time: "2026-10-28T14:00:00Z",
            },
    }));
    vi.stubGlobal("fetch", fetch);
    show();

    const refreshBtn = await screen.findByRole("button", { name: /Refresh Current Semester/i });
    expect(refreshBtn).toBeInTheDocument();
    await waitFor(() => expect(refreshBtn).toBeEnabled());
    fireEvent.click(refreshBtn);

    await waitFor(() =>
      expect(fetch.mock.calls.some(([url]) => url.endsWith("/refresh-current"))).toBe(true)
    );
  });

  it("automatically resumes current refresh when session transitions to AUTHENTICATED after ACTION_REQUIRED", async () => {
    let sessionAuthenticated = false;
    const fetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.endsWith("settings")) {
        return {
          ok: true,
          json: async () => ({
            auto_connect: true,
            refresh_approved_scopes: false,
            auto_refresh_current_term: true,
            approved_scope_count: 1,
            last_sync_time: null,
          }),
        };
      }
      if (url.endsWith("session/status")) {
        return {
          ok: true,
          json: async () => ({
            state: sessionAuthenticated ? "AUTHENTICATED" : "LOGIN_REQUIRED",
          }),
        };
      }
      if (url.endsWith("refresh-current")) {
        return {
          ok: true,
          json: async () => ({
            state: "SYNC_COMPLETE",
            message: "Refreshed after user login.",
            running: false,
            refreshed_scopes: 1,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          state: "ACTION_REQUIRED",
          message: "Login required in browser.",
          running: false,
          refreshed_scopes: 0,
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    show();

    await screen.findByText("Login required in browser.");

    // Simulate user completing login in Chrome
    sessionAuthenticated = true;

    // Verify refresh-current was automatically dispatched without manual button click
    await waitFor(
      () => expect(fetch.mock.calls.some(([url]) => url.endsWith("/refresh-current"))).toBe(true),
      { timeout: 3500 }
    );
  });
});
