import React from "react";
import {ThemeSwitch} from "./ThemeSwitch";
import { GraduationCap, Sliders, ShieldCheck, KeyRound, Power } from "lucide-react";

interface Props {
  academicYear: string;
  semester: number | null;
  className: string;
  targetPercentage: number;
  onTargetChange: (target: number) => void;
  isBackendHealthy: boolean;
  onOpenAuthModal?: () => void;
  onExit?: () => void;
}


export const Header: React.FC<Props> = ({
  academicYear,
  semester,
  className,
  targetPercentage,
  onTargetChange,
  isBackendHealthy,
  onOpenAuthModal,
  onExit,
}) => {

  return (
    <header className="app-header border-b border-slate-800 bg-slate-900/90 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Branding & Institutional Context */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-slate-800 border border-slate-700 text-indigo-400">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-100 m-0">
                AttendPlan
              </h1>
              <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-800 text-slate-400 border border-slate-700">
                Local dashboard
              </span>
            </div>
            <p className="text-xs text-slate-400 m-0 mt-0.5">
              Attendance &amp; academic insights
            </p>
          </div>
        </div>

        {/* Academic Meta & Controls */}
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="header-session bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-md flex items-center gap-2 text-slate-300">
            <span className="text-slate-400 font-medium">Session:</span>
            <span className="font-semibold text-slate-200">{academicYear}</span>
            <span className="text-slate-600">&bull;</span>
            <span className="text-slate-400 font-medium">Sem:</span>
            <span className="font-semibold text-slate-200">{semester ?? "—"}</span>
            <span className="text-slate-600">&bull;</span>
            <span className="font-medium text-slate-300 truncate max-w-[160px]" title={className}>
              {className}
            </span>
          </div>

          <ThemeSwitch />

          {/* Target Threshold Selector */}
          <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 px-3 py-1 rounded-md">
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <label htmlFor="target-select" className="text-slate-400 font-medium">
              Target:
            </label>
            <select
              id="target-select"
              value={targetPercentage}
              onChange={(e) => onTargetChange(Number(e.target.value))}
              aria-label="Target Attendance Threshold"
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono font-medium focus:outline-none focus:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500 cursor-pointer"
            >
              <option value={75}>75%</option>
              <option value={80}>80%</option>
              <option value={85}>85%</option>
            </select>
          </div>

          {/* Authentication & Identity Vault */}
          {onOpenAuthModal && (
            <button
              onClick={onOpenAuthModal}
              className="flex items-center gap-1.5 text-xs text-indigo-300 hover:text-white bg-indigo-950/40 hover:bg-indigo-900/50 border border-indigo-700/50 px-2.5 py-1 rounded-md transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              title="Configure Student Mobile Identity and Windows TOTP Vault"
            >
              <KeyRound className="w-3.5 h-3.5 text-indigo-400" />
              <span>Auth &amp; Vault</span>
            </button>
          )}

          {/* Backend Status */}

          <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-800/50 border border-slate-700/60 px-2.5 py-1 rounded-md">
            <ShieldCheck
              className={`w-3.5 h-3.5 ${
                isBackendHealthy ? "text-emerald-400" : "text-rose-400"
              }`}
            />
            <span>{isBackendHealthy ? "Connected" : "Offline"}</span>
          </div>

          {/* Exit AttendPlan */}
          {onExit && (
            <button
              onClick={onExit}
              className="flex items-center gap-1.5 text-xs text-rose-300 hover:text-white bg-rose-950/40 hover:bg-rose-900/50 border border-rose-800/50 px-2.5 py-1 rounded-md transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
              title="Stop AttendPlan Local Server"
            >
              <Power className="w-3.5 h-3.5 text-rose-400" />
              <span>Exit</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
