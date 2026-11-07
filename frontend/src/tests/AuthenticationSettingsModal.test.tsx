import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthenticationSettingsModal } from "../components/AuthenticationSettingsModal";


// Mock API client functions
vi.mock("../api/attendance", () => ({
  fetchAuthSettings: vi.fn().mockResolvedValue({
    has_saved_mobile: true,
    masked_mobile: "******3210",
    auto_mobile_autofill: true,
    auto_login_continuation: true,
    auto_totp_autofill: true,
    auto_totp_submit: true,
  }),
  updateAuthSettings: vi.fn().mockImplementation((payload) =>
    Promise.resolve({
      has_saved_mobile: !payload.clear_mobile,
      masked_mobile: payload.clear_mobile ? null : "******9999",
      auto_mobile_autofill: payload.auto_mobile_autofill ?? true,
      auto_login_continuation: payload.auto_login_continuation ?? true,
      auto_totp_autofill: true,
      auto_totp_submit: true,
    })
  ),
  fetchTotpStatus: vi.fn().mockResolvedValue({
    is_enrolled: true,
    vault_backend: "WinVaultKeyring",
    is_secure_backend: true,
    metadata: {
      enrollment_id: "test-uuid",
      issuer: "iCloudEMS",
      masked_account: "st***23",
      enrolled_at: "2026-10-19T10:00:00Z",
      digits: 6,
      period: 30,
      algorithm: "SHA1",
      auto_autofill_enabled: true,
      auto_submit_enabled: true,
    },
    clock_skew_seconds: 0.0,
    auto_autofill_enabled: true,
    auto_submit_enabled: true,
    details: "Enrolled for iCloudEMS (st***23).",
  }),
  inspectTotp: vi.fn().mockResolvedValue({
    candidates: [
      {
        candidate_id: "cand_0",
        issuer: "iCloudEMS",
        masked_account: "st***23",
        digits: 6,
        period: 30,
        algorithm: "SHA1",
        source_type: "STANDARD_TOTP",
      },
    ],
    total_found: 1,
    source_format: "STANDARD_TOTP",
  }),
  enrollTotp: vi.fn().mockResolvedValue({
    enrollment_id: "enrolled-uuid",
    issuer: "iCloudEMS",
    masked_account: "st***23",
    enrolled_at: "2026-10-19T10:00:00Z",
    digits: 6,
    period: 30,
    algorithm: "SHA1",
    auto_autofill_enabled: true,
    auto_submit_enabled: true,
  }),
  verifyTotp: vi.fn().mockResolvedValue({
    valid: true,
    message: "Verification successful. TOTP engine is synchronized.",
  }),
  deleteTotpEnrollment: vi.fn().mockResolvedValue({
    success: true,
    message: "Enrolled authenticator secret removed.",
  }),
  orchestrateLogin: vi.fn().mockResolvedValue({
    state: "AUTHENTICATED",
    step: "AUTHENTICATED_AND_VERIFIED",
    success: true,
    redirected: true,
    message: "Student dashboard session active.",
    current_url: "https://mrei.icloudems.com/corecampus/student/student_dashboard.php",
    has_saved_mobile: true,
    is_totp_enrolled: true,
    details: {},
  }),
  fetchLoginStatus: vi.fn().mockResolvedValue({
    state: "AUTHENTICATED",
    step: "AUTHENTICATED_AND_VERIFIED",
    success: true,
    redirected: true,
    message: "Active authenticated session.",
    current_url: "https://mrei.icloudems.com/corecampus/student/student_dashboard.php",
    has_saved_mobile: true,
    is_totp_enrolled: true,
    details: {},
  }),
}));

describe("AuthenticationSettingsModal", () => {
  it("renders modal header and navigation tabs when open", async () => {
    render(<AuthenticationSettingsModal isOpen={true} onClose={() => {}} />);

    expect(screen.getByText("Authentication & Identity Vault")).toBeInTheDocument();
    expect(screen.getByText("Mobile Identity")).toBeInTheDocument();
    expect(screen.getByText("Google Authenticator Vault")).toBeInTheDocument();
    expect(screen.getByText("Automated Login")).toBeInTheDocument();
    // Wait for the initial mocked requests before this test unmounts the view.
    expect(await screen.findByText("******3210")).toBeInTheDocument();
  });

  it("displays masked saved mobile number and automation preferences", async () => {
    render(<AuthenticationSettingsModal isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("******3210")).toBeInTheDocument();
      expect(screen.getByText("Automatic Mobile Autofill")).toBeInTheDocument();
      expect(screen.getByText("Automatic Form Continuation")).toBeInTheDocument();
    });
  });

  it("switches to Google Authenticator Vault tab and displays Windows Credential Manager status", async () => {
    render(<AuthenticationSettingsModal isOpen={true} onClose={() => {}} />);

    const totpTab = screen.getByText("Google Authenticator Vault");
    fireEvent.click(totpTab);

    await waitFor(() => {
      expect(screen.getByText("Windows Credential Manager")).toBeInTheDocument();
      expect(screen.getByText("WinVaultKeyring")).toBeInTheDocument();
      expect(screen.getByText("st***23")).toBeInTheDocument();
      expect(screen.getByText("Test Live Verification Code")).toBeInTheDocument();
    });
  });

  it("switches to Automated Login tab and displays login status badge", async () => {
    render(<AuthenticationSettingsModal isOpen={true} onClose={() => {}} />);

    const orchestratorTab = screen.getByText("Automated Login");
    fireEvent.click(orchestratorTab);

    await waitFor(() => {
      expect(screen.getByText("Keycloak Authentication State")).toBeInTheDocument();
      expect(screen.getByText("Run Automated Login Sequence")).toBeInTheDocument();
    });
  });
});
