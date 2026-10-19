import React from "react";
import type { SnapshotListItem, TermReconciliationResponse } from "../types/attendance";
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ShieldCheck,
  Clock,
  Layers,
} from "lucide-react";

interface ReconciliationViewProps {
  reconciliation: TermReconciliationResponse | null;
  snapshots: SnapshotListItem[];
  isLoading: boolean;
}

export const ReconciliationView: React.FC<ReconciliationViewProps> = ({
  reconciliation,
  snapshots,
  isLoading,
}) => {
  if (isLoading || !reconciliation) {
    return (
      <div className="p-12 text-center text-slate-400">
        <p className="text-sm">Auditing source provenance and cross-dataset reconciliation...</p>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "MATCHED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300 text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            100% RECONCILED MATCH
          </span>
        );
      case "PARTIAL_COVERAGE":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-amber-950/70 border border-amber-800 text-amber-300 text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            PARTIAL SOURCE COVERAGE
          </span>
        );
      case "SCOPE_MISMATCH":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-sky-950/70 border border-sky-800 text-sky-300 text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            PARTIAL WINDOW (SCOPE MISMATCH)
          </span>
        );
      case "DISCREPANCY":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-rose-950/70 border border-rose-800 text-rose-300 text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" />
            SOURCE DIVERGENCE DETECTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs font-semibold">
            <HelpCircle className="w-3.5 h-3.5" />
            INSUFFICIENT DATA
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Reconciliation Status Card */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-5 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-950/60 border border-indigo-800/60 rounded-md text-indigo-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100 m-0">
                Source Reconciliation & Data Integrity
              </h3>
              <p className="text-xs text-slate-400 m-0">
                Comparing Authoritative Subject-Wise Totals against Date-Wise Timetable Observations
              </p>
            </div>
          </div>
          <div>{getStatusBadge(reconciliation.reconciliation_status)}</div>
        </div>

        <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded border border-slate-800/80 leading-relaxed font-mono">
          {reconciliation.status_explanation}
        </p>

        {/* Aggregate Comparison Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-md p-3.5 space-y-1">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">
              Subject-Wise Summary (subwise_attendace_new.php)
            </span>
            <div className="flex items-baseline justify-between pt-1">
              <span className="text-xs text-slate-300">Total Attended / Delivered:</span>
              <span className="font-mono text-sm font-bold text-slate-100">
                {reconciliation.subject_wise_total_attended} / {reconciliation.subject_wise_total_delivered}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 pt-1">
              Source Available:{" "}
              <span className={reconciliation.subject_wise_available ? "text-emerald-400 font-medium" : "text-rose-400 font-medium"}>
                {reconciliation.subject_wise_available ? "YES (Authoritative)" : "NO"}
              </span>
            </div>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-md p-3.5 space-y-1">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">
              Day-Wise Timetable (myattendance.php)
            </span>
            <div className="flex items-baseline justify-between pt-1">
              <span className="text-xs text-slate-300">Total Attended / Delivered:</span>
              <span className="font-mono text-sm font-bold text-slate-100">
                {reconciliation.day_wise_total_attended} / {reconciliation.day_wise_total_delivered}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 pt-1">
              Unmapped Observations:{" "}
              <span className="font-mono text-amber-400 font-semibold">
                {reconciliation.total_unmapped_observations} periods
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Course-by-Course Reconciliation Breakdown */}
      {reconciliation.course_breakdown.length > 0 && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200 m-0">
              Course-by-Course Discrepancy Breakdown
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-medium">
                  <th className="py-2.5 px-3">Course</th>
                  <th className="py-2.5 px-3 text-center">Subject-Wise (Att / Del)</th>
                  <th className="py-2.5 px-3 text-center">Day-Wise (Att / Del)</th>
                  <th className="py-2.5 px-3 text-center">Variance (Att / Del)</th>
                  <th className="py-2.5 px-3 text-right">Reconciliation Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {reconciliation.course_breakdown.map((c) => (
                  <tr key={c.course_code} className="hover:bg-slate-850/50">
                    <td className="py-2.5 px-3">
                      <span className="font-mono font-medium text-indigo-300 block">
                        {c.course_code}
                      </span>
                      <span className="text-slate-300 text-[11px]">{c.course_name}</span>
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono text-slate-200">
                      {c.subject_wise_attended} / {c.subject_wise_delivered}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono text-slate-200">
                      {c.day_wise_attended} / {c.day_wise_delivered}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono">
                      {c.attended_diff === 0 && c.delivered_diff === 0 ? (
                        <span className="text-emerald-400">0 / 0</span>
                      ) : (
                        <span className="text-rose-400 font-bold">
                          {c.attended_diff > 0 ? `+${c.attended_diff}` : c.attended_diff} /{" "}
                          {c.delivered_diff > 0 ? `+${c.delivered_diff}` : c.delivered_diff}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase ${
                          c.status === "MATCHED"
                            ? "bg-emerald-950/60 text-emerald-300 border-emerald-800"
                            : c.status === "NO_DAY_DATA"
                            ? "bg-slate-800 text-slate-400 border-slate-700"
                            : "bg-rose-950/60 text-rose-300 border-rose-800"
                        }`}
                      >
                        {c.status.replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. Immutable Historical Snapshots */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-200 m-0">
            Immutable Historical Snapshots ({snapshots.length})
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="py-2.5 px-3">Snapshot ID</th>
                <th className="py-2.5 px-3">Captured Timestamp</th>
                <th className="py-2.5 px-3">Source Provenance</th>
                <th className="py-2.5 px-3">Records</th>
                <th className="py-2.5 px-3 font-mono">Canonical SHA-256 Checksum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {snapshots.map((s) => (
                <tr key={s.id} className="hover:bg-slate-850/50">
                  <td className="py-2.5 px-3 font-mono font-medium text-slate-200">{s.id}</td>
                  <td className="py-2.5 px-3 text-slate-300">
                    {new Date(s.captured_at).toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-indigo-300 font-medium">{s.source}</td>
                  <td className="py-2.5 px-3 font-mono text-slate-200">{s.record_count} courses</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400 truncate max-w-xs">
                    {s.content_checksum}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
