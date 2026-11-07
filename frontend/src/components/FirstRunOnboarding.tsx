import React, { useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  GraduationCap,
  Loader2,
  RefreshCw,
  Shield,
} from "lucide-react";
import { API_BASE, seedDemoData } from "../api/attendance";

interface Props {
  onComplete: () => void;
  onOpenAuthModal?: () => void;
}

export const FirstRunOnboarding: React.FC<Props> = ({ onComplete }) => {
  const [step, setStep] = useState<number>(1);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

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
      setStep(4);
    } catch (err: any) {
      setSyncError(err.message ?? "Could not connect to university portal");
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div
      role="region"
      aria-label="First-run onboarding wizard"
      className="first-run-onboarding max-w-xl mx-auto my-8 p-6 sm:p-8 bg-slate-900/95 border border-slate-800 rounded-2xl shadow-xl text-slate-200 space-y-6"
    >
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="w-12 h-12 mx-auto rounded-xl bg-indigo-950/80 border border-indigo-700 flex items-center justify-center text-indigo-400">
          <GraduationCap className="w-7 h-7" />
        </div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100 m-0">Welcome to AttendPlan</h2>
        <p className="text-xs text-slate-400 max-w-sm mx-auto m-0">
          Your private, local-first university attendance planner. Never fall below the 75% requirement.
        </p>
      </div>

      {/* Progress dots */}
      <div className="flex items-center justify-center gap-2 pt-1">
        {[1, 2, 3, 4].map((s) => (
          <div
            key={s}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              step === s ? "w-8 bg-indigo-500" : step > s ? "w-3 bg-emerald-500" : "w-3 bg-slate-800"
            }`}
          />
        ))}
      </div>

      {/* Step 1: Privacy & Guarantee */}
      {step === 1 && (
        <div className="space-y-4 pt-2">
          <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-2.5">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
              <Shield className="w-4 h-4" />
              100% Local-First Privacy Guarantee
            </div>
            <ul className="text-xs text-slate-300 space-y-2 pl-4 list-disc m-0 leading-relaxed">
              <li>
                <strong>No Cloud Sync:</strong> All passwords, tokens, and attendance records stay strictly on your local PC in <code className="text-slate-200 bg-slate-900 px-1 py-0.5 rounded font-mono text-[11px]">%LOCALAPPDATA%\AttendPlan</code>.
              </li>
              <li>
                <strong>Zero Analytics:</strong> We never transmit your academic records, student identity, or usage data to external servers.
              </li>
              <li>
                <strong>Read-Only Access:</strong> AttendPlan never performs automated actions or edits in your student portal.
              </li>
            </ul>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={handleSeedDemo}
              disabled={isSeeding}
              className="text-xs text-slate-400 hover:text-slate-200 underline cursor-pointer"
            >
              {isSeeding ? "Loading sample..." : "Explore with sample offline data"}
            </button>
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              Get Started <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Environment Check & Browser */}
      {step === 2 && (
        <div className="space-y-4 pt-2">
          <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-3 text-xs">
            <span className="font-semibold text-slate-200 block">Step 1: Dedicated Browser</span>
            <p className="text-slate-300 leading-relaxed m-0">
              AttendPlan connects to iCloudEMS using an isolated Google Chrome window that runs strictly on your machine.
            </p>
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={async () => {
                  await fetch(`${API_BASE}/api/v1/portal/session/launch`, { method: "POST" });
                }}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Open Student Portal in Chrome
              </button>
            </div>
            <p className="text-[11px] text-slate-400 m-0">
              Sign in with your university credentials and Authenticator app in the Chrome window.
            </p>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(1)}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              &larr; Back
            </button>
            <button
              onClick={() => setStep(3)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer"
            >
              I am signed in &rarr;
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Initial Sync */}
      {step === 3 && (
        <div className="space-y-4 pt-2">
          <div className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl space-y-3 text-xs text-center">
            <div className="w-10 h-10 mx-auto rounded-full bg-indigo-950/80 border border-indigo-700 flex items-center justify-center text-indigo-400">
              <RefreshCw className={`w-5 h-5 ${isSyncing ? "animate-spin" : ""}`} />
            </div>
            <h3 className="text-sm font-semibold text-slate-100 m-0">Initial Attendance Import</h3>
            <p className="text-slate-300 leading-relaxed max-w-sm mx-auto m-0">
              AttendPlan will now read your active semester courses and calculate your exact 75% thresholds and skippable class margins.
            </p>

            {syncError && (
              <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-300 text-xs text-left">
                <strong>Sync Error:</strong> {syncError}. Ensure you are signed in to iCloudEMS in the open Chrome tab.
              </div>
            )}

            <button
              onClick={handleInitialSync}
              disabled={isSyncing}
              className="mt-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold inline-flex items-center gap-2 cursor-pointer shadow-md"
            >
              {isSyncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {isSyncing ? "Syncing Attendance..." : "Sync Current Semester Attendance"}
            </button>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setStep(2)}
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

      {/* Step 4: Completion */}
      {step === 4 && (
        <div className="space-y-4 pt-2 text-center">
          <div className="p-5 bg-emerald-950/40 border border-emerald-800/80 rounded-xl space-y-3">
            <div className="w-12 h-12 mx-auto rounded-full bg-emerald-900/60 border border-emerald-700 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-100 m-0">Setup Complete!</h3>
            <p className="text-xs text-slate-300 max-w-sm mx-auto m-0 leading-relaxed">
              Your current attendance is now saved securely in your private local database. You can track thresholds and simulate class schedules right away.
            </p>
          </div>

          <button
            onClick={onComplete}
            className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg inline-flex items-center justify-center gap-2 cursor-pointer shadow-md"
          >
            Launch AttendPlan Dashboard <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

