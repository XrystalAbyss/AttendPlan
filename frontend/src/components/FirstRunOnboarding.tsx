import React, { useState, useEffect } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  GraduationCap,
  KeyRound,
  Loader2,
  RefreshCw,
  Shield,
  Smartphone,
  Sparkles,
  Check,
} from "lucide-react";
import {
  API_BASE,
  fetchAuthSettings,
  updateAuthSettings,
  enrollTotp,
  verifyTotp,
  launchPortalBrowser,
  fetchPortalSessionStatus,
  orchestrateLogin,
  seedDemoData,
} from "../api/attendance";
import type { AuthSettings, PortalSessionStatus } from "../types/attendance";

interface Props {
  onComplete: () => void;
  onOpenAuthModal?: () => void;
}

export const FirstRunOnboarding: React.FC<Props> = ({ onComplete, onOpenAuthModal }) => {
  const [step, setStep] = useState<number>(1);

  // Saved settings state
  const [savedSettings, setSavedSettings] = useState<AuthSettings | null>(null);
  const [isEditingMobile, setIsEditingMobile] = useState(false);

  // Step 2: Mobile state
  const [mobileNumber, setMobileNumber] = useState("");
  const [rememberMobile, setRememberMobile] = useState(true);
  const [mobileError, setMobileError] = useState<string | null>(null);
  const [isSavingMobile, setIsSavingMobile] = useState(false);

  // Initial load of existing settings
  useEffect(() => {
    fetchAuthSettings()
      .then((s) => {
        setSavedSettings(s);
      })
      .catch(() => {});
  }, []);

  // Step 3: MFA Choice state
  const [mfaChoice, setMfaChoice] = useState<"manual" | "auto">("manual");
  const [totpSecret, setTotpSecret] = useState("");
  const [testTotpCode, setTestTotpCode] = useState("");
  const [isEnrollingTotp, setIsEnrollingTotp] = useState(false);
  const [totpEnrolled, setTotpEnrolled] = useState(false);
  const [totpError, setTotpError] = useState<string | null>(null);
  const [totpSuccess, setTotpSuccess] = useState<string | null>(null);

  // Step 4: Browser & Session state
  const [portalStatus, setPortalStatus] = useState<PortalSessionStatus | null>(null);
  const [isLaunchingBrowser, setIsLaunchingBrowser] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(false);
  const [browserError, setBrowserError] = useState<string | null>(null);
  const [isOrchestrating, setIsOrchestrating] = useState(false);

  // Step 5: Sync state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncSummary, setSyncSummary] = useState<{
    academic_year?: string;
    semester?: number;
    class_identifier?: string;
    total_courses?: number;
    total_delivered?: number;
    total_attended?: number;
    overall_percentage?: number;
  } | null>(null);

  // Demo fallback
  const [isSeeding, setIsSeeding] = useState(false);

  // Check portal status periodically on Step 4
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (step === 4) {
      checkSession();
      interval = setInterval(checkSession, 4000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [step]);

  const checkSession = async () => {
    setIsCheckingSession(true);
    try {
      const status = await fetchPortalSessionStatus();
      setPortalStatus(status);
    } catch {
      // Ignore network errors in polling
    } finally {
      setIsCheckingSession(false);
    }
  };

  const handleSaveMobile = async () => {
    if (savedSettings?.has_saved_mobile && !isEditingMobile) {
      setStep(3);
      return;
    }
    const cleaned = mobileNumber.trim();
    if (!cleaned) {
      if (savedSettings?.has_saved_mobile) {
        setStep(3);
        return;
      }
      setMobileError("Please enter your 10-digit registered mobile number.");
      return;
    }
    if (!/^[6-9]\d{9}$/.test(cleaned)) {
      setMobileError("Please enter a valid 10-digit Indian mobile number (e.g. 9876543210).");
      return;
    }
    setIsSavingMobile(true);
    setMobileError(null);
    try {
      await updateAuthSettings({
        mobile_number: cleaned,
        auto_mobile_autofill: rememberMobile,
      });
      const verified = await fetchAuthSettings();
      setSavedSettings(verified);
      setIsEditingMobile(false);
      setStep(3);
    } catch (err: any) {
      setMobileError(err.message || "Failed to save mobile settings.");
    } finally {
      setIsSavingMobile(false);
    }
  };

  const handleEnrollTotp = async () => {
    const cleaned = totpSecret.replace(/\s+/g, "").toUpperCase();
    if (!cleaned) {
      setTotpError("Please enter your Authenticator secret key.");
      return;
    }
    setIsEnrollingTotp(true);
    setTotpError(null);
    setTotpSuccess(null);
    try {
      await enrollTotp({
        secret_base32: cleaned,
        auto_autofill_enabled: true,
        auto_submit_enabled: false,
      });
      if (testTotpCode.trim()) {
        const verifyRes = await verifyTotp(testTotpCode.trim());
        if (!verifyRes.valid) {
          setTotpError("Secret saved, but test code did not verify. Check your time synchronization.");
          setIsEnrollingTotp(false);
          return;
        }
      }
      setTotpEnrolled(true);
      setTotpSuccess("Authenticator secret stored securely in your Windows Credential Vault!");
    } catch (err: any) {
      setTotpError(err.message || "Failed to enroll Authenticator secret.");
    } finally {
      setIsEnrollingTotp(false);
    }
  };

  const handleLaunchBrowser = async () => {
    setIsLaunchingBrowser(true);
    setBrowserError(null);
    try {
      const status = await launchPortalBrowser();
      setPortalStatus(status);
      if (status.state === "ERROR") {
        setBrowserError(status.details || "Could not launch Chrome. Ensure Google Chrome or Microsoft Edge is installed.");
      }
    } catch (err: any) {
      setBrowserError(err.message || "Could not launch dedicated browser.");
    } finally {
      setIsLaunchingBrowser(false);
    }
  };

  const handleAutoLogin = async () => {
    setIsOrchestrating(true);
    setBrowserError(null);
    try {
      const res = await orchestrateLogin();
      if (res.success && res.state === "AUTHENTICATED") {
        await checkSession();
      } else {
        setBrowserError(res.message || "Automated step completed. Please finish login in Chrome.");
      }
    } catch (err: any) {
      setBrowserError(err.message || "Login orchestration halted.");
    } finally {
      setIsOrchestrating(false);
      await checkSession();
    }
  };

  const handleInitialSync = async () => {
    setIsSyncing(true);
    setSyncError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/startup/refresh-current`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? "Failed to sync attendance");
      }
      setSyncSummary({
        academic_year: data.academic_year,
        semester: data.semester,
        class_identifier: data.class_identifier,
        total_courses: data.total_courses,
        total_delivered: data.total_delivered,
        total_attended: data.total_attended,
        overall_percentage: data.overall_percentage,
      });
      setStep(6);
    } catch (err: any) {
      setSyncError(err.message ?? "Could not connect to university portal");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSeedDemo = async () => {
    setIsSeeding(true);
    try {
      await seedDemoData();
      onComplete();
    } catch (err: any) {
      setSyncError(err.message ?? "Failed to load sample dataset");
    } finally {
      setIsSeeding(false);
    }
  };

  const isAuthenticated = portalStatus?.state === "AUTHENTICATED";

  return (
    <div
      role="region"
      aria-label="First-run onboarding wizard"
      className="first-run-onboarding max-w-xl mx-auto my-6 p-6 sm:p-8 bg-slate-900/95 border border-slate-800 rounded-2xl shadow-xl text-slate-200 space-y-6"
    >
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="w-12 h-12 mx-auto rounded-xl bg-indigo-950/80 border border-indigo-700 flex items-center justify-center text-indigo-400">
          <GraduationCap className="w-7 h-7" />
        </div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100 m-0">Welcome to AttendPlan</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto m-0">
          Local-first attendance intelligence. Calculate exact 75% thresholds, safe bunks, and recovery classes.
        </p>
      </div>

      {/* Progress dots (6 steps) */}
      <div className="flex items-center justify-center gap-1.5 pt-1">
        {[1, 2, 3, 4, 5, 6].map((s) => (
          <div
            key={s}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              step === s ? "w-8 bg-indigo-500" : step > s ? "w-3 bg-emerald-500" : "w-3 bg-slate-800"
            }`}
          />
        ))}
      </div>

      {/* ========================================================= */}
      {/* STEP 1: WELCOME & PRIVACY COMMITMENT                      */}
      {/* ========================================================= */}
      {step === 1 && (
        <div className="space-y-4 pt-1">
          <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-3">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
              <Shield className="w-4 h-4" />
              100% Local-First Privacy Guarantee
            </div>
            <ul className="text-xs text-slate-300 space-y-2 pl-4 list-disc m-0 leading-relaxed">
              <li>
                <strong>No Cloud Database:</strong> Your attendance records, tokens, and database stay strictly on your local PC in <code className="text-slate-200 bg-slate-900 px-1 py-0.5 rounded font-mono text-[11px]">%LOCALAPPDATA%\AttendPlan</code>.
              </li>
              <li>
                <strong>Zero Password Storage:</strong> AttendPlan never prompts for, stores, or transmits your university password or OTPs.
              </li>
              <li>
                <strong>Read-Only Access:</strong> We interact with the student portal strictly in read-only mode to calculate your margins.
              </li>
              <li>
                <strong>Dedicated Browser:</strong> Portal logins run in an isolated Chrome window bound strictly to loopback (<code className="text-slate-200 bg-slate-900 px-1 py-0.5 rounded font-mono text-[11px]">127.0.0.1</code>).
              </li>
            </ul>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={handleSeedDemo}
              disabled={isSeeding}
              className="text-xs text-slate-400 hover:text-slate-200 underline cursor-pointer"
            >
              {isSeeding ? "Loading demo..." : "Explore with sample offline data"}
            </button>
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors"
            >
              Configure Setup <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* STEP 2: REGISTERED MOBILE NUMBER                          */}
      {/* ========================================================= */}
      {step === 2 && (
        <div className="space-y-4 pt-1">
          <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-3 text-xs">
            <div className="flex items-center gap-2 text-indigo-300 font-semibold">
              <Smartphone className="w-4 h-4" />
              University Registered Mobile Number
            </div>
            <p className="text-slate-300 leading-relaxed m-0">
              Your university student portal (iCloudEMS Keycloak) uses your registered 10-digit mobile number as the username to send SMS OTPs or request Authenticator codes.
            </p>

            {savedSettings?.has_saved_mobile && !isEditingMobile ? (
              <div className="p-3.5 bg-emerald-950/40 border border-emerald-800/70 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-emerald-300 font-semibold text-xs">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Saved Mobile Number Detected
                  </span>
                  <span className="font-mono text-xs font-bold text-white bg-slate-900 px-2.5 py-1 rounded border border-emerald-900">
                    {savedSettings.masked_mobile}
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 m-0">
                  Your university mobile number is already configured in local storage (%LOCALAPPDATA%\AttendPlan\settings.json).
                </p>
                <button
                  type="button"
                  onClick={() => setIsEditingMobile(true)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 underline cursor-pointer pt-1"
                >
                  Change or use a different number
                </button>
              </div>
            ) : (
              <>
                <div className="space-y-1.5 pt-1">
                  <label htmlFor="mobile-input" className="block text-slate-400 font-medium">
                    10-Digit Mobile Number
                  </label>
                  <input
                    id="mobile-input"
                    type="tel"
                    maxLength={10}
                    placeholder="e.g. 9876543210"
                    value={mobileNumber}
                    onChange={(e) => {
                      setMobileNumber(e.target.value.replace(/\D/g, ""));
                      setMobileError(null);
                    }}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <label className="flex items-center gap-2 text-slate-300 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={rememberMobile}
                    onChange={(e) => setRememberMobile(e.target.checked)}
                    className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Remember mobile number locally for automated sign-in</span>
                </label>

                {isEditingMobile && savedSettings?.has_saved_mobile && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditingMobile(false);
                      setMobileNumber("");
                      setMobileError(null);
                    }}
                    className="text-xs text-slate-400 hover:text-slate-300 underline cursor-pointer"
                  >
                    Cancel and keep {savedSettings.masked_mobile}
                  </button>
                )}
              </>
            )}

            {mobileError && (
              <div className="p-2.5 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-300 text-xs">
                {mobileError}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(1)}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              &larr; Back
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setStep(3)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                Skip for manual login
              </button>
              <button
                onClick={handleSaveMobile}
                disabled={isSavingMobile}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors"
              >
                {isSavingMobile
                  ? "Saving..."
                  : savedSettings?.has_saved_mobile && !isEditingMobile
                  ? "Continue with Saved Mobile"
                  : "Save & Continue"}{" "}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* STEP 3: MFA CHOICE (MANUAL VS AUTOMATIC)                  */}
      {/* ========================================================= */}
      {step === 3 && (
        <div className="space-y-4 pt-1">
          <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-3 text-xs">
            <div className="flex items-center gap-2 text-indigo-300 font-semibold">
              <KeyRound className="w-4 h-4" />
              Authenticator &amp; Multi-Factor Setup
            </div>
            <p className="text-slate-300 leading-relaxed m-0">
              Choose how you would like to handle university 2-factor authentication:
            </p>

            {/* Option A: Manual */}
            <div
              onClick={() => setMfaChoice("manual")}
              className={`p-3 rounded-xl border transition-all cursor-pointer space-y-1.5 ${
                mfaChoice === "manual"
                  ? "bg-indigo-950/40 border-indigo-500/80 shadow-sm"
                  : "bg-slate-900/60 border-slate-700/60 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-100 flex items-center gap-1.5">
                  <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${mfaChoice === "manual" ? "border-indigo-400 bg-indigo-500 text-white" : "border-slate-600"}`}>
                    {mfaChoice === "manual" && <Check className="w-2.5 h-2.5" />}
                  </span>
                  Option A: Manual Authenticator Login (Recommended)
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-medium">
                  Zero Setup
                </span>
              </div>
              <p className="text-[11px] text-slate-300 m-0 pl-5 leading-relaxed">
                Log in normally in the dedicated Chrome window using your Authenticator app. No QR code or secret setup required.
              </p>
            </div>

            {/* Option B: Automatic */}
            <div
              onClick={() => setMfaChoice("auto")}
              className={`p-3 rounded-xl border transition-all cursor-pointer space-y-2 ${
                mfaChoice === "auto"
                  ? "bg-indigo-950/40 border-indigo-500/80 shadow-sm"
                  : "bg-slate-900/60 border-slate-700/60 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-100 flex items-center gap-1.5">
                  <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${mfaChoice === "auto" ? "border-indigo-400 bg-indigo-500 text-white" : "border-slate-600"}`}>
                    {mfaChoice === "auto" && <Check className="w-2.5 h-2.5" />}
                  </span>
                  Option B: Optional Automatic TOTP Login
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-medium">
                  Windows Vault
                </span>
              </div>
              <p className="text-[11px] text-slate-300 m-0 pl-5 leading-relaxed">
                Store your Authenticator secret locally in the encrypted Windows Credential Manager to allow one-click login.
              </p>

              {mfaChoice === "auto" && (
                <div className="pt-2 pl-5 space-y-2">
                  <div className="space-y-1">
                    <label className="text-[11px] text-slate-400 font-medium">
                      Base32 Secret Key (from your Authenticator setup screen):
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. JBSWY3DPEHPK3PXP"
                      value={totpSecret}
                      onChange={(e) => {
                        setTotpSecret(e.target.value);
                        setTotpError(null);
                      }}
                      className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-slate-100 font-mono text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      maxLength={6}
                      placeholder="Test 6-digit code"
                      value={testTotpCode}
                      onChange={(e) => setTestTotpCode(e.target.value.replace(/\D/g, ""))}
                      className="w-32 px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-slate-100 font-mono text-xs focus:outline-none focus:border-indigo-500"
                    />
                    <button
                      onClick={handleEnrollTotp}
                      disabled={isEnrollingTotp || !totpSecret.trim()}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-semibold inline-flex items-center gap-1 cursor-pointer"
                    >
                      {isEnrollingTotp ? "Verifying..." : "Save to Vault"}
                    </button>
                    {onOpenAuthModal && (
                      <button
                        onClick={onOpenAuthModal}
                        className="text-xs text-indigo-300 hover:text-white underline cursor-pointer ml-auto"
                      >
                        Upload QR Code
                      </button>
                    )}
                  </div>

                  {totpSuccess && (
                    <div className="p-2 bg-emerald-950/60 border border-emerald-800 rounded text-emerald-300 text-[11px] flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" /> {totpSuccess}
                    </div>
                  )}

                  {totpError && (
                    <div className="p-2 bg-rose-950/60 border border-rose-800 rounded text-rose-300 text-[11px]">
                      {totpError}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(2)}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              &larr; Back
            </button>
            <button
              onClick={() => setStep(4)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors"
            >
              Continue to Portal <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* STEP 4: CONNECT UNIVERSITY PORTAL                         */}
      {/* ========================================================= */}
      {step === 4 && (
        <div className="space-y-4 pt-1">
          <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-2">
                <ExternalLink className="w-4 h-4 text-indigo-400" />
                Connect University Portal
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1 ${
                  isAuthenticated
                    ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                    : "bg-amber-950 text-amber-300 border border-amber-800"
                }`}
              >
                {isAuthenticated ? "Authenticated" : "Login Required"}
              </span>
            </div>

            <p className="text-slate-300 leading-relaxed m-0">
              AttendPlan opens a dedicated, local Chrome browser window for you to sign in to iCloudEMS.
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button
                onClick={handleLaunchBrowser}
                disabled={isLaunchingBrowser}
                className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                {isLaunchingBrowser ? "Opening Chrome..." : "Open Portal in Dedicated Chrome"}
              </button>

              {mfaChoice === "auto" && totpEnrolled && (
                <button
                  onClick={handleAutoLogin}
                  disabled={isOrchestrating}
                  className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {isOrchestrating ? "Signing in..." : "Run Automated Login"}
                </button>
              )}

              <button
                onClick={checkSession}
                disabled={isCheckingSession}
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer ml-auto"
                title="Verify Session"
              >
                <RefreshCw className={`w-3 h-3 ${isCheckingSession ? "animate-spin" : ""}`} />
                Check Status
              </button>
            </div>

            {browserError && (
              <div className="p-2.5 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-300 text-xs">
                {browserError}
              </div>
            )}

            {isAuthenticated ? (
              <div className="p-3 bg-emerald-950/40 border border-emerald-800/80 rounded-lg text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>Portal session verified! You are ready to import attendance.</span>
              </div>
            ) : (
              <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg text-slate-400 text-[11px] leading-relaxed">
                Log in with your credentials and Google Authenticator in the opened Chrome window. AttendPlan will automatically detect when you reach the student dashboard.
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(3)}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              &larr; Back
            </button>
            <button
              onClick={async () => {
                if (isAuthenticated) {
                  setStep(5);
                  return;
                }
                setIsCheckingSession(true);
                try {
                  const status = await fetchPortalSessionStatus();
                  setPortalStatus(status);
                  if (status.state === "AUTHENTICATED") {
                    setStep(5);
                  } else {
                    setBrowserError("Portal login not detected yet. Please complete sign-in and Google Authenticator MFA in the opened Chrome window.");
                  }
                } catch {
                  setBrowserError("Could not reach local backend to verify portal session.");
                } finally {
                  setIsCheckingSession(false);
                }
              }}
              disabled={isCheckingSession}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors"
            >
              {isCheckingSession
                ? "Verifying..."
                : isAuthenticated
                ? "Proceed to Sync"
                : "Verify & Proceed to Sync"}{" "}
              &rarr;
            </button>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* STEP 5: FIRST ATTENDANCE SYNC                             */}
      {/* ========================================================= */}
      {step === 5 && (
        <div className="space-y-4 pt-1">
          <div className="p-5 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-3 text-xs text-center">
            <div className="w-10 h-10 mx-auto rounded-full bg-indigo-950/80 border border-indigo-700 flex items-center justify-center text-indigo-400">
              <RefreshCw className={`w-5 h-5 ${isSyncing ? "animate-spin" : ""}`} />
            </div>
            <h3 className="text-sm font-semibold text-slate-100 m-0">Synchronize Active Semester</h3>
            <p className="text-slate-300 leading-relaxed max-w-sm mx-auto m-0">
              AttendPlan will now read your active semester courses, delivered classes, and attendance records to calculate your 75% margins.
            </p>

            {syncError && (
              <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-300 text-xs text-left">
                <strong>Sync Notice:</strong> {syncError}. Ensure your university login session is active in the opened Chrome window.
              </div>
            )}

            <button
              onClick={handleInitialSync}
              disabled={isSyncing}
              className="mt-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold inline-flex items-center gap-2 cursor-pointer shadow-md transition-colors"
            >
              {isSyncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {isSyncing ? "Reading Attendance Records..." : "Sync Current Attendance"}
            </button>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(4)}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              &larr; Back
            </button>
            <button
              onClick={handleSeedDemo}
              disabled={isSeeding}
              className="text-xs text-slate-400 hover:text-slate-200 underline cursor-pointer"
            >
              Skip and load demo data
            </button>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* STEP 6: COMPLETION & DASHBOARD READY                      */}
      {/* ========================================================= */}
      {step === 6 && (
        <div className="space-y-4 pt-1 text-center">
          <div className="p-5 bg-emerald-950/40 border border-emerald-800/80 rounded-xl space-y-3">
            <div className="w-12 h-12 mx-auto rounded-full bg-emerald-900/60 border border-emerald-700 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-100 m-0">Attendance Synchronized!</h3>
            <p className="text-xs text-slate-300 max-w-sm mx-auto m-0 leading-relaxed">
              Your active semester attendance has been securely imported into your private local SQLite database.
            </p>

            {syncSummary && (
              <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-left text-xs space-y-1 font-mono text-slate-300 mt-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Academic Term:</span>
                  <span className="font-semibold text-slate-100">
                    {syncSummary.academic_year || "Current"} · Sem {syncSummary.semester || 1}
                  </span>
                </div>
                {syncSummary.class_identifier && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Class:</span>
                    <span className="text-slate-200">{syncSummary.class_identifier}</span>
                  </div>
                )}
                {syncSummary.total_courses !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Discovered Courses:</span>
                    <span className="text-slate-200">{syncSummary.total_courses} subjects</span>
                  </div>
                )}
                {syncSummary.overall_percentage !== undefined && (
                  <div className="flex justify-between pt-1 border-t border-slate-800 text-sm">
                    <span className="text-slate-300 font-sans font-semibold">Overall Attendance:</span>
                    <span className="font-bold text-emerald-400">
                      {syncSummary.overall_percentage.toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="space-y-2 pt-1">
            <button
              onClick={onComplete}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg inline-flex items-center justify-center gap-2 cursor-pointer shadow-md transition-colors"
            >
              Open AttendPlan Dashboard <ArrowRight className="w-4 h-4" />
            </button>
            <p className="text-[11px] text-slate-400 m-0">
              You can import previous semesters or Performance assessments at any time from the navigation tabs.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
