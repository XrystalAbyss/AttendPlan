import React, { useState, useEffect } from "react";
import {
  X,
  Smartphone,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  Play,
  RefreshCw,

  Eye,
  EyeOff,
  HelpCircle,
} from "lucide-react";
import {
  fetchAuthSettings,
  updateAuthSettings,
  fetchTotpStatus,
  inspectTotp,
  enrollTotp,
  enrollTotpImage,
  verifyTotp,
  deleteTotpEnrollment,
  orchestrateLogin,
  fetchLoginStatus,
} from "../api/attendance";
import type {
  AuthSettings,
  TotpStatusResponse,
  LoginOrchestrationResponse,
  TotpCandidate,
} from "../types/attendance";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess?: () => void;
}

export const AuthenticationSettingsModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onLoginSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<"mobile" | "totp" | "orchestrator">("mobile");
  const [settings, setSettings] = useState<AuthSettings | null>(null);
  const [totpStatus, setTotpStatus] = useState<TotpStatusResponse | null>(null);
  const [loginStatus, setLoginStatus] = useState<LoginOrchestrationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Mobile state
  const [mobileInput, setMobileInput] = useState("");
  const [isEditingMobile, setIsEditingMobile] = useState(false);

  // TOTP enrollment state
  const [enrollMethod, setEnrollMethod] = useState<"qr" | "secret" | "uri">("qr");
  const [secretInput, setSecretInput] = useState("");
  const [uriInput, setUriInput] = useState("");
  const [qrFile, setQrFile] = useState<File | null>(null);
  const [inspectedCandidates, setInspectedCandidates] = useState<TotpCandidate[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>("");
  const [totpAutofillOptIn, setTotpAutofillOptIn] = useState<boolean>(false);
  const [totpSubmitOptIn, setTotpSubmitOptIn] = useState<boolean>(false);
  const [testCodeInput, setTestCodeInput] = useState("");
  const [testCodeResult, setTestCodeResult] = useState<{ valid: boolean; message: string } | null>(null);
  const [showSecretInput, setShowSecretInput] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadAll();
    }
  }, [isOpen]);

  const loadAll = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [s, t, l] = await Promise.all([
        fetchAuthSettings(),
        fetchTotpStatus(),
        fetchLoginStatus().catch(() => null),
      ]);
      setSettings(s);
      setTotpStatus(t);
      if (l) setLoginStatus(l);
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to load authentication configuration.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveMobile = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    const cleaned = mobileInput.trim();
    if (!/^[6-9]\d{9}$/.test(cleaned.replace(/\D/g, ""))) {
      setErrorMsg("Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.");
      return;
    }
    try {
      const updated = await updateAuthSettings({ mobile_number: cleaned });
      setSettings(updated);
      setIsEditingMobile(false);
      setMobileInput("");
      setSuccessMsg("Mobile number saved securely to local configuration.");
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to update mobile number.");
    }
  };

  const handleClearMobile = async () => {
    if (!window.confirm("Remove saved mobile number? Automated first-factor login will be disabled.")) {
      return;
    }
    try {
      const updated = await updateAuthSettings({ clear_mobile: true });
      setSettings(updated);
      setIsEditingMobile(false);
      setSuccessMsg("Mobile number removed from local settings.");
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to clear mobile number.");
    }
  };

  const handleToggleSetting = async (field: keyof AuthSettings, val: boolean) => {
    try {
      const updated = await updateAuthSettings({ [field]: val });
      setSettings(updated);
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to update setting.");
    }
  };

  const handleInspectInput = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    setInspectedCandidates([]);
    setSelectedCandidateId("");
    try {
      let res;
      if (enrollMethod === "qr") {
        if (!qrFile) {
          setErrorMsg("Please select a QR screenshot or image file.");
          setLoading(false);
          return;
        }
        res = await inspectTotp(qrFile);
      } else if (enrollMethod === "uri") {
        if (!uriInput.trim()) {
          setErrorMsg("Please enter an otpauth:// or otpauth-migration:// URI.");
          setLoading(false);
          return;
        }
        res = await inspectTotp(undefined, uriInput.trim());
      } else {
        setLoading(false);
        return;
      }

      if (!res.candidates.length) {
        setErrorMsg("No valid TOTP accounts found in the provided payload.");
        return;
      }
      setInspectedCandidates(res.candidates);
      setSelectedCandidateId(res.candidates[0].candidate_id);
      setSuccessMsg(
        `Discovered ${res.candidates.length} account candidate${res.candidates.length > 1 ? "s" : ""}. Select an account and commit to vault.`
      );
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to inspect TOTP payload.");
    } finally {
      setLoading(false);
    }
  };

  const handleEnrollSecret = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    try {
      if (enrollMethod === "qr") {
        if (!qrFile) {
          setErrorMsg("Please select a QR code screenshot or image.");
          setLoading(false);
          return;
        }
        await enrollTotpImage(qrFile, {
          candidate_id: selectedCandidateId || undefined,
          auto_autofill_enabled: totpAutofillOptIn,
          auto_submit_enabled: totpSubmitOptIn,
        });
      } else if (enrollMethod === "secret") {
        const candidateSecret = secretInput.trim().replace(/[\s\-_]/g, "");
        if (!candidateSecret) {
          setErrorMsg("Please enter the authenticator secret key.");
          setLoading(false);
          return;
        }
        await enrollTotp({
          secret_base32: candidateSecret,
          issuer: "iCloudEMS",
          account_label: "student",
          auto_autofill_enabled: totpAutofillOptIn,
          auto_submit_enabled: totpSubmitOptIn,
        });
      } else if (enrollMethod === "uri") {
        const candidateUri = uriInput.trim();
        if (!candidateUri) {
          setErrorMsg("Please enter the otpauth:// or migration URI.");
          setLoading(false);
          return;
        }
        await enrollTotp({
          provisioning_input: candidateUri,
          candidate_id: selectedCandidateId || undefined,
          issuer: "iCloudEMS",
          account_label: "student",
          auto_autofill_enabled: totpAutofillOptIn,
          auto_submit_enabled: totpSubmitOptIn,
        });
      }

      const updatedStatus = await fetchTotpStatus();
      setTotpStatus(updatedStatus);
      setSecretInput("");
      setUriInput("");
      setQrFile(null);
      setInspectedCandidates([]);
      setSelectedCandidateId("");
      setSuccessMsg("Authenticator secret successfully enrolled into Windows Credential Manager!");
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to enroll authenticator.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    setTestCodeResult(null);
    if (!testCodeInput || testCodeInput.length !== 6) {
      setErrorMsg("Please enter a 6-digit test code.");
      return;
    }
    try {
      const res = await verifyTotp(testCodeInput);
      setTestCodeResult(res);
      if (res.valid) {
        setSuccessMsg("TOTP synchronization verified! Codes match active server time window.");
      } else {
        setErrorMsg("Code rejected. Please verify system clock time.");
      }
    } catch (e: any) {
      setErrorMsg(e.message || "Verification failed.");
    }
  };

  const handleDeleteTotp = async () => {
    if (!window.confirm("Are you sure you want to remove the authenticator secret from Windows Credential Manager?")) {
      return;
    }
    try {
      await deleteTotpEnrollment();
      const s = await fetchTotpStatus();
      setTotpStatus(s);
      setSuccessMsg("Authenticator secret removed from Windows vault.");
    } catch (e: any) {
      setErrorMsg(e.message || "Failed to remove authenticator.");
    }
  };

  const handleRunLogin = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);
    try {
      const res = await orchestrateLogin();
      setLoginStatus(res);
      if (res.success && res.state === "AUTHENTICATED") {
        setSuccessMsg("Automated login succeeded! Student portal session active.");
        if (onLoginSuccess) onLoginSuccess();
      } else if (res.state === "MANUAL_ACTION_REQUIRED") {
        setErrorMsg(res.message);
      } else if (!res.success) {
        setErrorMsg(res.message);
      }
    } catch (e: any) {
      setErrorMsg(e.message || "Login orchestration failed.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden text-slate-200">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Authentication & Identity Vault</h2>
              <p className="text-xs text-slate-400">
                Persistent local credentials and automated Keycloak login
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-900/50 px-6 pt-3 gap-2">
          <button
            onClick={() => setActiveTab("mobile")}
            className={`pb-3 px-3 text-sm font-medium border-b-2 flex items-center gap-2 transition ${
              activeTab === "mobile"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-slate-400 hover:text-slate-300"
            }`}
          >
            <Smartphone className="w-4 h-4" />
            Mobile Identity
          </button>
          <button
            onClick={() => setActiveTab("totp")}
            className={`pb-3 px-3 text-sm font-medium border-b-2 flex items-center gap-2 transition ${
              activeTab === "totp"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-slate-400 hover:text-slate-300"
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Google Authenticator Vault
          </button>
          <button
            onClick={() => setActiveTab("orchestrator")}
            className={`pb-3 px-3 text-sm font-medium border-b-2 flex items-center gap-2 transition ${
              activeTab === "orchestrator"
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-slate-400 hover:text-slate-300"
            }`}
          >
            <Play className="w-4 h-4" />
            Automated Login
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Alerts */}
          {errorMsg && (
            <div className="p-3 bg-red-950/40 border border-red-800/50 rounded-lg text-sm text-red-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-red-400" />
              <span>{errorMsg}</span>
            </div>
          )}
          {successMsg && (
            <div className="p-3 bg-emerald-950/40 border border-emerald-800/50 rounded-lg text-sm text-emerald-300 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0 text-emerald-400" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* TAB 1: MOBILE IDENTITY */}
          {activeTab === "mobile" && (
            <div className="space-y-4">
              <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Smartphone className="w-4 h-4 text-indigo-400" />
                    <span className="text-sm font-medium text-slate-200">Registered Student Mobile</span>
                  </div>
                  {settings?.has_saved_mobile ? (
                    <span className="px-2 py-0.5 text-xs bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 rounded font-mono">
                      {settings.masked_mobile}
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 text-xs bg-amber-900/40 border border-amber-700/50 text-amber-300 rounded">
                      Not Configured
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  The Keycloak student login form requires your registered 10-digit mobile number for First-Factor authentication.
                  Saved strictly in <code className="text-indigo-300 font-mono text-[11px]">%LOCALAPPDATA%\AttendPlan\settings.json</code>.
                </p>

                {(!settings?.has_saved_mobile || isEditingMobile) ? (
                  <div className="pt-2 flex flex-col gap-2">
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <span className="absolute left-3 top-2.5 text-sm text-slate-500 font-mono">+91</span>
                        <input
                          type="text"
                          placeholder="9876543210"
                          maxLength={10}
                          value={mobileInput}
                          onChange={(e) => setMobileInput(e.target.value.replace(/\D/g, ""))}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-12 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                        />
                      </div>
                      <button
                        onClick={handleSaveMobile}
                        disabled={loading || mobileInput.length !== 10}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
                      >
                        Save
                      </button>
                      {settings?.has_saved_mobile && (
                        <button
                          onClick={() => {
                            setIsEditingMobile(false);
                            setMobileInput("");
                          }}
                          className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm rounded-lg transition"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500">
                      Must be 10 digits starting with 6, 7, 8, or 9.
                    </span>
                  </div>
                ) : (
                  <div className="pt-2 flex items-center gap-3">
                    <button
                      onClick={() => setIsEditingMobile(true)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 underline font-medium"
                    >
                      Change Mobile Number
                    </button>
                    <span className="text-slate-600">•</span>
                    <button
                      onClick={handleClearMobile}
                      className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 font-medium"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Remove Number
                    </button>
                  </div>
                )}
              </div>

              {/* Automation Toggles */}
              <div className="p-4 bg-slate-800/40 border border-slate-700/40 rounded-xl space-y-3">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Mobile Login Automation Preferences
                </span>

                <div className="flex items-center justify-between pt-1">
                  <div>
                    <div className="text-sm text-slate-200">Automatic Mobile Autofill</div>
                    <div className="text-xs text-slate-400">
                      Pre-fill your mobile number whenever Keycloak presents the login prompt
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings?.auto_mobile_autofill ?? true}
                    onChange={(e) => handleToggleSetting("auto_mobile_autofill", e.target.checked)}
                    className="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer"
                  />
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                  <div>
                    <div className="text-sm text-slate-200">Automatic Form Continuation</div>
                    <div className="text-xs text-slate-400">
                      Automatically click submit on the mobile number stage to advance to MFA
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings?.auto_login_continuation ?? true}
                    onChange={(e) => handleToggleSetting("auto_login_continuation", e.target.checked)}
                    className="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: TOTP VAULT */}
          {activeTab === "totp" && (
            <div className="space-y-4">
              {/* Vault Security Status Card */}
              <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-medium text-slate-200">Windows Credential Manager</span>
                  </div>
                  <span className="px-2 py-0.5 text-xs bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 rounded font-mono">
                    {totpStatus?.vault_backend || "WinVaultKeyring"}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Authenticator secrets are isolated strictly inside your local Windows OS Credential Manager.
                  AttendPlan uses fail-closed security: secrets never touch SQLite, logs, or unencrypted storage.
                </p>

                {totpStatus?.is_enrolled ? (
                  <div className="pt-2 p-3 bg-slate-900/80 border border-slate-700 rounded-lg space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Enrolled Account:</span>
                      <span className="font-mono text-emerald-300 font-semibold">
                        {totpStatus.metadata?.masked_account}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Algorithm & Interval:</span>
                      <span className="text-slate-300 font-mono">
                        {totpStatus.metadata?.algorithm || "SHA1"} • 30s
                      </span>
                    </div>
                    <div className="pt-2 flex justify-end">
                      <button
                        onClick={handleDeleteTotp}
                        className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Remove Authenticator
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="pt-1">
                    <span className="text-xs text-amber-300 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      No authenticator secret is enrolled. Please enroll below to automate MFA.
                    </span>
                  </div>
                )}
              </div>

              {/* Enrollment / Test Section */}
              {totpStatus?.is_enrolled ? (
                /* Test Verification Card */
                <div className="p-4 bg-slate-800/40 border border-slate-700/40 rounded-xl space-y-3">
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Test Live Verification Code
                  </span>
                  <p className="text-xs text-slate-400">
                    Enter the current 6-digit code shown on your phone's Google Authenticator app to confirm drift synchronization.
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="123456"
                      maxLength={6}
                      value={testCodeInput}
                      onChange={(e) => setTestCodeInput(e.target.value.replace(/\D/g, ""))}
                      className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 font-mono tracking-widest text-center w-36"
                    />
                    <button
                      onClick={handleVerifyCode}
                      disabled={testCodeInput.length !== 6}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg transition"
                    >
                      Verify
                    </button>
                  </div>
                  {testCodeResult && (
                    <div
                      className={`text-xs p-2.5 rounded-lg border flex items-center gap-2 ${
                        testCodeResult.valid
                          ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
                          : "bg-red-950/40 border-red-800 text-red-300"
                      }`}
                    >
                      {testCodeResult.valid ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                      )}
                      <span>{testCodeResult.message}</span>
                    </div>
                  )}
                </div>

              ) : (
                /* Enrollment Inputs */
                <div className="p-4 bg-slate-800/40 border border-slate-700/40 rounded-xl space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Enroll Authenticator Secret
                    </span>
                    <div className="flex bg-slate-900 rounded-lg p-0.5 border border-slate-700 text-xs">
                      <button
                        onClick={() => {
                          setEnrollMethod("qr");
                          setInspectedCandidates([]);
                        }}
                        className={`px-2.5 py-1 rounded transition ${
                          enrollMethod === "qr" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        QR Image
                      </button>
                      <button
                        onClick={() => {
                          setEnrollMethod("secret");
                          setInspectedCandidates([]);
                        }}
                        className={`px-2.5 py-1 rounded transition ${
                          enrollMethod === "secret" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        Secret Key
                      </button>
                      <button
                        onClick={() => {
                          setEnrollMethod("uri");
                          setInspectedCandidates([]);
                        }}
                        className={`px-2.5 py-1 rounded transition ${
                          enrollMethod === "uri" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        URI / Export
                      </button>
                    </div>
                  </div>

                  {enrollMethod === "qr" && (
                    <div className="space-y-3">
                      <label className="text-xs text-slate-300">Offline Authenticator QR Image File</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/webp"
                          onChange={(e) => {
                            if (e.target.files?.[0]) {
                              setQrFile(e.target.files[0]);
                              setInspectedCandidates([]);
                            }
                          }}
                          className="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-slate-800 file:text-slate-300 hover:file:bg-slate-700 cursor-pointer"
                        />
                        <button
                          type="button"
                          onClick={handleInspectInput}
                          disabled={loading || !qrFile}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs text-slate-200 rounded-lg transition"
                        >
                          Inspect QR
                        </button>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Processed offline using OpenCV. Decoded images are never saved to disk or transmitted to remote servers.
                      </p>
                    </div>
                  )}

                  {enrollMethod === "secret" && (
                    <div className="space-y-2">
                      <label className="text-xs text-slate-300">Base32 Authenticator Secret Key</label>
                      <div className="relative">
                        <input
                          type={showSecretInput ? "text" : "password"}
                          placeholder="JBSWY3DPEHPK3PXP"
                          value={secretInput}
                          onChange={(e) => setSecretInput(e.target.value.toUpperCase())}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder-slate-500 pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowSecretInput(!showSecretInput)}
                          className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
                        >
                          {showSecretInput ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Provided by Keycloak when enrolling Google Authenticator. Spaces and dashes are cleaned automatically.
                      </p>
                    </div>
                  )}

                  {enrollMethod === "uri" && (
                    <div className="space-y-3">
                      <label className="text-xs text-slate-300">Authenticator Provisioning URI</label>
                      <div className="space-y-2">
                        <textarea
                          rows={2}
                          placeholder="otpauth://totp/... or otpauth-migration://offline?data=..."
                          value={uriInput}
                          onChange={(e) => {
                            setUriInput(e.target.value);
                            setInspectedCandidates([]);
                          }}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder-slate-500"
                        />
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={handleInspectInput}
                            disabled={loading || !uriInput.trim()}
                            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs text-slate-200 rounded-lg transition"
                          >
                            Inspect URI
                          </button>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Supports standard <code className="text-indigo-300">otpauth://totp/</code> and Google Authenticator multi-account migration exports.
                      </p>
                    </div>
                  )}

                  {/* Candidate Account Selector */}
                  {inspectedCandidates.length > 0 && (
                    <div className="p-3 bg-slate-900/90 border border-indigo-500/40 rounded-xl space-y-2">
                      <div className="text-xs font-semibold text-indigo-300">
                        Select Account to Enroll ({inspectedCandidates.length} found):
                      </div>
                      <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                        {inspectedCandidates.map((c) => (
                          <label
                            key={c.candidate_id}
                            className={`flex items-center justify-between p-2 rounded-lg border text-xs cursor-pointer transition ${
                              selectedCandidateId === c.candidate_id
                                ? "bg-indigo-950/60 border-indigo-500 text-white"
                                : "bg-slate-850 border-slate-700/60 text-slate-300 hover:border-slate-600"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <input
                                type="radio"
                                name="candidate_account"
                                value={c.candidate_id}
                                checked={selectedCandidateId === c.candidate_id}
                                onChange={() => setSelectedCandidateId(c.candidate_id)}
                                className="text-indigo-600"
                              />
                              <span className="font-mono text-emerald-300">{c.masked_account}</span>
                              <span className="text-[10px] text-slate-400">({c.issuer})</span>
                            </div>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {c.algorithm} • {c.period}s
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Explicit User Opt-In Toggles */}
                  <div className="p-3 bg-slate-900/60 border border-slate-700/50 rounded-lg space-y-2">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Automation Permissions (Explicit Opt-In)
                    </span>
                    <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={totpAutofillOptIn}
                        onChange={(e) => setTotpAutofillOptIn(e.target.checked)}
                        className="rounded text-indigo-600 bg-slate-950 border-slate-700"
                      />
                      <span>Auto-fill TOTP into Keycloak challenge</span>
                    </label>
                    <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={totpSubmitOptIn}
                        onChange={(e) => setTotpSubmitOptIn(e.target.checked)}
                        className="rounded text-indigo-600 bg-slate-950 border-slate-700"
                      />
                      <span>Auto-submit OTP form after filling</span>
                    </label>
                  </div>

                  <button
                    onClick={handleEnrollSecret}
                    disabled={loading || (enrollMethod === "qr" && !qrFile)}
                    className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
                  >
                    {loading ? "Enrolling..." : "Enroll Selected Account Into Windows Credential Manager"}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: ORCHESTRATOR */}
          {activeTab === "orchestrator" && (
            <div className="space-y-4">
              <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-200">Keycloak Authentication State</span>
                  <span
                    className={`px-2.5 py-0.5 text-xs rounded font-mono font-semibold ${
                      loginStatus?.state === "AUTHENTICATED"
                        ? "bg-emerald-900/40 border border-emerald-700/50 text-emerald-300"
                        : loginStatus?.state === "WAITING_FOR_TOTP" ||
                          loginStatus?.state === "ENTERING_MOBILE" ||
                          loginStatus?.state === "SUBMITTING_TOTP" ||
                          loginStatus?.state === "VERIFYING_SESSION" ||
                          loginStatus?.state === "SESSION_CHECKING"
                        ? "bg-indigo-900/40 border border-indigo-700/50 text-indigo-300"
                        : loginStatus?.state === "MANUAL_ACTION_REQUIRED" ||
                          loginStatus?.state === "SESSION_EXPIRED" ||
                          loginStatus?.state === "LOGIN_REQUIRED"
                        ? "bg-amber-900/40 border border-amber-700/50 text-amber-300"
                        : loginStatus?.state === "FAILED"
                        ? "bg-red-900/40 border border-red-700/50 text-red-300"
                        : "bg-slate-800 border border-slate-700 text-slate-300"
                    }`}
                  >
                    {loginStatus?.state || "UNKNOWN"}
                  </span>
                </div>

                <p className="text-xs text-slate-400">
                  {loginStatus?.message || "Ready to execute automated mobile and TOTP login sequence."}
                </p>

                <div className="pt-2 flex flex-col gap-2">
                  <button
                    onClick={handleRunLogin}
                    disabled={loading}
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-600/20"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Executing Login Sequence...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-white" />
                        Run Automated Login Sequence
                      </>
                    )}
                  </button>
                  <span className="text-[11px] text-slate-500 text-center">
                    Checks existing session $\to$ enters mobile $\to$ generates TOTP from vault $\to$ authenticates session.
                  </span>
                </div>
              </div>

              {/* Status checklist */}
              <div className="p-4 bg-slate-800/40 border border-slate-700/40 rounded-xl space-y-2 text-xs">
                <div className="flex items-center justify-between py-1">
                  <span className="text-slate-400">Persistent Mobile Identity:</span>
                  <span className={settings?.has_saved_mobile ? "text-emerald-400 font-mono" : "text-amber-400"}>
                    {settings?.has_saved_mobile ? settings.masked_mobile : "Not configured"}
                  </span>
                </div>
                <div className="flex items-center justify-between py-1 border-t border-slate-800">
                  <span className="text-slate-400">Windows TOTP Vault:</span>
                  <span className={totpStatus?.is_enrolled ? "text-emerald-400 font-mono" : "text-amber-400"}>
                    {totpStatus?.is_enrolled ? "Enrolled" : "Not enrolled"}
                  </span>
                </div>
                <div className="flex items-center justify-between py-1 border-t border-slate-800">
                  <span className="text-slate-400">Origin Allowlist Protection:</span>
                  <span className="text-emerald-400">Active (usermanagement.icloudems.com)</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-850 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 text-slate-500">
            <HelpCircle className="w-3.5 h-3.5" />
            Local-first privacy: Credentials never leave 127.0.0.1
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
