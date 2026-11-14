import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FirstRunOnboarding } from "../components/FirstRunOnboarding";

afterEach(() => vi.unstubAllGlobals());

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe("FirstRunOnboarding and Recovery", () => {
  it("surfaces saved mobile number when has_saved_mobile is true", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes("/api/v1/auth/settings")) {
        return {
          ok: true,
          json: async () => ({
            has_saved_mobile: true,
            masked_mobile: "******9050",
            auto_mobile_autofill: false,
            auto_login_continuation: false,
            auto_totp_autofill: false,
            auto_totp_submit: false,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({}),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(
      <FirstRunOnboarding
        onComplete={() => {}}
        onOpenAuthModal={() => {}}
      />
    );

    // Initial step 1: Welcome
    expect(await screen.findByText("Welcome to AttendPlan")).toBeInTheDocument();
    const getStartedBtn = screen.getByText(/Configure Setup/i);
    fireEvent.click(getStartedBtn);

    // Step 2: Student Identity
    await screen.findByText("Saved Mobile Number Detected");
    expect(screen.getByText("******9050")).toBeInTheDocument();
    expect(screen.getByText("Continue with Saved Mobile")).toBeInTheDocument();
  });

  it("advances to next step when clicking Continue with Saved Mobile without re-entering", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes("/api/v1/auth/settings")) {
        return {
          ok: true,
          json: async () => ({
            has_saved_mobile: true,
            masked_mobile: "******9050",
            auto_mobile_autofill: false,
            auto_login_continuation: false,
            auto_totp_autofill: false,
            auto_totp_submit: false,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({}),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(
      <FirstRunOnboarding
        onComplete={() => {}}
        onOpenAuthModal={() => {}}
      />
    );

    // Step 1 -> Step 2
    fireEvent.click(await screen.findByText(/Configure Setup/i));

    // Step 2: Click Continue with Saved Mobile
    const continueBtn = await screen.findByText("Continue with Saved Mobile");
    fireEvent.click(continueBtn);

    // Should advance to Step 3: Authenticator & Multi-Factor Setup
    await screen.findByText(/Authenticator & Multi-Factor Setup/i);
    expect(screen.getByText(/Continue to Portal/i)).toBeInTheDocument();
  });

  it("displays settings unavailable alert and retry button when fetchAuthSettings fails", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes("/api/v1/auth/settings")) {
        return {
          ok: false,
          status: 500,
          json: async () => ({ detail: "Settings vault unreachable" }),
        };
      }
      return { ok: true, json: async () => ({}) };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(
      <FirstRunOnboarding
        onComplete={() => {}}
        onOpenAuthModal={() => {}}
      />
    );

    fireEvent.click(await screen.findByText(/Configure Setup/i));

    // Step 2 should display Settings Unavailable instead of empty input
    await screen.findByText("Local Settings Unavailable");
    expect(screen.getByText(/Could not verify existing authentication configuration/i)).toBeInTheDocument();
    expect(screen.getByText(/Retry Reading Settings/i)).toBeInTheDocument();
  });

  it("verifies read-back after saving mobile and advances on success", async () => {
    let saved = false;
    const fetchMock = vi.fn().mockImplementation(async (url: string, opts?: any) => {
      if (url.includes("/api/v1/auth/settings")) {
        if (opts?.method === "POST") {
          saved = true;
          return { ok: true, json: async () => ({}) };
        }
        return {
          ok: true,
          json: async () => ({
            has_saved_mobile: saved,
            masked_mobile: saved ? "******1234" : null,
            auto_mobile_autofill: false,
            auto_login_continuation: false,
            auto_totp_autofill: false,
            auto_totp_submit: false,
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    });
    vi.stubGlobal("fetch", fetchMock);

    renderWithClient(
      <FirstRunOnboarding
        onComplete={() => {}}
        onOpenAuthModal={() => {}}
      />
    );

    fireEvent.click(await screen.findByText(/Configure Setup/i));

    // Input mobile number
    const input = await screen.findByLabelText(/10-Digit Mobile Number/i);
    fireEvent.change(input, { target: { value: "9876541234" } });

    // Click Save & Continue
    const nextBtn = screen.getByText(/Save & Continue/i);
    fireEvent.click(nextBtn);

    // Should advance to Authenticator & Multi-Factor Setup
    await screen.findByText(/Authenticator & Multi-Factor Setup/i);
  });
});
