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
});
