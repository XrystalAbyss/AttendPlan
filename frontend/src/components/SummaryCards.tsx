import React from "react";
import { CheckCircle2, AlertTriangle, HelpCircle, BarChart3 } from "lucide-react";
import type { SnapshotSummary } from "../types/attendance";

interface Props {
  summary: SnapshotSummary;
  targetPercentage: number;
}

export const SummaryCards: React.FC<Props> = ({ summary, targetPercentage }) => {
  const isOverallSafe = summary.overall_status === "SAFE";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Overall Attendance Metric */}
      <div className="bg-slate-850 bg-slate-800/60 border border-slate-700/80 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider">
            Overall Term Attendance
          </span>
          <BarChart3 className="w-4 h-4 text-slate-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-slate-100">
            {summary.overall_percentage !== null
              ? `${summary.overall_percentage.toFixed(2)}%`
              : "N/A"}
          </span>
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded border ${
              isOverallSafe
                ? "bg-emerald-950/60 text-emerald-400 border-emerald-800"
                : "bg-rose-950/60 text-rose-400 border-rose-800"
            }`}
          >
            {summary.overall_status}
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400 flex justify-between items-center">
          <span>
            Periods: <strong className="font-mono text-slate-200">{summary.total_attended}</strong> /{" "}
            <span className="font-mono">{summary.total_delivered}</span>
          </span>
          <span>Target: {targetPercentage}%</span>
        </div>
      </div>

      {/* Safe Subjects Card */}
      <div className="bg-slate-850 bg-slate-800/60 border border-slate-700/80 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider text-emerald-400">
            Compliant Courses
          </span>
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-emerald-400">
            {summary.safe_courses}
          </span>
          <span className="text-xs text-slate-400 font-mono">
            / {summary.active_courses} active
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400">
          Attendance currently meets or exceeds {targetPercentage}%.
        </div>
      </div>

      {/* At Risk Courses Card */}
      <div className="bg-slate-850 bg-slate-800/60 border border-slate-700/80 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider text-rose-400">
            Courses At Risk
          </span>
          <AlertTriangle className="w-4 h-4 text-rose-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-rose-400">
            {summary.at_risk_courses}
          </span>
          <span className="text-xs text-slate-400 font-mono">
            below {targetPercentage}%
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400">
          Immediate recovery required to clear institutional gate.
        </div>
      </div>

      {/* Unrecorded Courses Card */}
      <div className="bg-slate-850 bg-slate-800/60 border border-slate-700/80 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Unrecorded / Pending
          </span>
          <HelpCircle className="w-4 h-4 text-slate-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-slate-300">
            {summary.unrecorded_courses}
          </span>
          <span className="text-xs text-slate-400 font-mono">
            courses with 0/0
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400">
          Zero delivered periods; status mathematically pending.
        </div>
      </div>
    </div>
  );
};
