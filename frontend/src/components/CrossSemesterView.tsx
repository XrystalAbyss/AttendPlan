import React from "react";
import type { AcademicHistoryResponse } from "../types/attendance";
import { GraduationCap, CheckCircle2, AlertTriangle, Layers } from "lucide-react";

interface CrossSemesterViewProps {
  history: AcademicHistoryResponse | null;
  isLoading: boolean;
  onSelectTerm: (termId: string) => void;
}

export const CrossSemesterView: React.FC<CrossSemesterViewProps> = ({
  history,
  isLoading,
  onSelectTerm,
}) => {
  if (isLoading || !history) {
    return (
      <div className="p-12 text-center text-slate-400">
        <p className="text-sm">Aggregating cross-semester attendance history...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. Cumulative Career Stats */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-indigo-950/60 border border-indigo-800/60 rounded-md text-indigo-400">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 m-0">
              Cumulative Academic Career Attendance
            </h3>
            <p className="text-xs text-slate-400 m-0">
              Exact aggregate across all recorded semesters &bull; Pure rational ratio
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-md p-3.5 text-center">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
              Cumulative Percentage
            </span>
            <div className="text-2xl font-mono font-bold text-emerald-400 mt-1">
              {history.career_percentage !== null ? `${history.career_percentage.toFixed(2)}%` : "N/A"}
            </div>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-md p-3.5 text-center">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
              Career Attended
            </span>
            <div className="text-2xl font-mono font-bold text-slate-100 mt-1">
              {history.career_attended}
            </div>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-md p-3.5 text-center">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
              Career Delivered
            </span>
            <div className="text-2xl font-mono font-bold text-slate-100 mt-1">
              {history.career_delivered}
            </div>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-md p-3.5 text-center">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
              Compliance Status
            </span>
            <div className="mt-1 flex items-center justify-center gap-1.5">
              {history.career_status === "SAFE" ? (
                <span className="text-emerald-400 font-bold flex items-center gap-1 text-sm">
                  <CheckCircle2 className="w-4 h-4" /> SAFE (&ge; 75%)
                </span>
              ) : (
                <span className="text-rose-400 font-bold flex items-center gap-1 text-sm">
                  <AlertTriangle className="w-4 h-4" /> AT RISK (&lt; 75%)
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Chronological Semester Roster */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-3">
          <Layers className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-200 m-0">
            Recorded Academic Semesters ({history.semesters.length})
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="py-2.5 px-3">Academic Year</th>
                <th className="py-2.5 px-3">Semester</th>
                <th className="py-2.5 px-3">Class Identifier</th>
                <th className="py-2.5 px-3 text-center">Delivered</th>
                <th className="py-2.5 px-3 text-center">Attended</th>
                <th className="py-2.5 px-3 text-center">Semester %</th>
                <th className="py-2.5 px-3 text-center">Below 75%</th>
                <th className="py-2.5 px-3 text-center">Timetable History</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {history.semesters.map((s) => (
                <tr key={s.term_id} className="hover:bg-slate-850/50">
                  <td className="py-2.5 px-3 font-medium text-slate-200">{s.academic_year}</td>
                  <td className="py-2.5 px-3 font-semibold text-indigo-300">
                    Semester {s.semester_number}
                  </td>
                  <td className="py-2.5 px-3 text-slate-400 font-mono">
                    {s.class_identifier ?? "—"}
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono text-slate-200">{s.delivered}</td>
                  <td className="py-2.5 px-3 text-center font-mono text-emerald-400">{s.attended}</td>
                  <td className="py-2.5 px-3 text-center font-mono font-bold">
                    {s.percentage !== null ? (
                      <span className={s.status === "SAFE" ? "text-emerald-400" : "text-rose-400"}>
                        {s.percentage.toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-slate-500">Unrecorded</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-center font-mono">
                    {s.courses_below_threshold > 0 ? (
                      <span className="text-rose-400 font-semibold">
                        {s.courses_below_threshold} of {s.total_courses}
                      </span>
                    ) : (
                      <span className="text-emerald-400">0 of {s.total_courses}</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase ${
                        s.has_datewise_history
                          ? "bg-emerald-950/60 text-emerald-300 border-emerald-800"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}
                    >
                      {s.has_datewise_history ? "Available" : "Snapshot Only"}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => onSelectTerm(s.term_id)}
                      className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 hover:text-indigo-200 border border-slate-700 cursor-pointer"
                    >
                      View Roster
                    </button>
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
