import React, { useState } from "react";
import type {
  MonthlyAnalyticsItem,
  SubjectAnalyticsResponse,
  WeekdayAnalyticsItem,
} from "../types/attendance";
import {
  CalendarDays,
  BarChart3,
  TrendingDown,
  Info,
} from "lucide-react";

interface AbsenceAnalyticsViewProps {
  monthly: MonthlyAnalyticsItem[];
  weekday: WeekdayAnalyticsItem[];
  subjects: SubjectAnalyticsResponse | null;
  isLoading: boolean;
}

export const AbsenceAnalyticsView: React.FC<AbsenceAnalyticsViewProps> = ({
  monthly,
  weekday,
  subjects,
  isLoading,
}) => {
  const [rankingTab, setRankingTab] = useState<"absolute" | "rate" | "delivered">("absolute");

  if (isLoading) {
    return (
      <div className="p-12 text-center text-slate-400">
        <p className="text-sm">Computing deterministic absence analytics...</p>
      </div>
    );
  }

  const hasDaywiseData = monthly.length > 0;

  return (
    <div className="space-y-6">
      {/* 1. Date-wise timetable notification if no day-wise observations */}
      {!hasDaywiseData && (
        <div className="p-4 bg-amber-950/30 border border-amber-800/60 rounded-lg flex items-start gap-3 text-amber-200">
          <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-semibold block text-amber-100">
              Date-Wise Observation History: Insufficient Timetable Observations
            </span>
            <p className="text-amber-300/90 leading-relaxed">
              No date-wise timetable observations (<code>myattendance.php</code>) have been ingested for this semester yet.
              Monthly and weekday patterns require verified date observations. Subject-wise analytics below are computed directly from the authoritative term snapshot.
            </p>
          </div>
        </div>
      )}

      {/* 2. Monthly Absence Breakdown */}
      {hasDaywiseData && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <CalendarDays className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200 m-0">
              Monthly Attendance & Absence Profile
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {monthly.map((m) => (
              <div
                key={`${m.year}-${m.month}`}
                className="bg-slate-800/70 border border-slate-700/60 rounded-md p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-slate-100">{m.month_label}</span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase ${
                      m.coverage === "COMPLETE"
                        ? "bg-emerald-950/60 text-emerald-300 border-emerald-800"
                        : "bg-amber-950/60 text-amber-300 border-amber-800"
                    }`}
                  >
                    {m.coverage}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="bg-slate-900/50 p-2 rounded">
                    <span className="text-slate-400 block text-[10px]">Delivered</span>
                    <span className="font-mono font-bold text-slate-200">{m.delivered}</span>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded">
                    <span className="text-slate-400 block text-[10px]">Attended</span>
                    <span className="font-mono font-bold text-emerald-400">{m.attended}</span>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded">
                    <span className="text-slate-400 block text-[10px]">Missed</span>
                    <span className="font-mono font-bold text-rose-400">{m.missed}</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Attendance:</span>
                    <span className="font-mono font-bold text-slate-200">
                      {m.attendance_percentage !== null ? `${m.attendance_percentage}%` : "N/A"}
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden flex">
                    <div
                      className="bg-emerald-500 h-2"
                      style={{ width: `${m.attendance_percentage ?? 0}%` }}
                    />
                    <div
                      className="bg-rose-500 h-2"
                      style={{ width: `${m.absence_percentage ?? 0}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-400 pt-1">
                    <span>Observed Dates: {m.observed_dates_count}</span>
                    <span className="text-rose-400 font-mono">Absence Rate: {m.absence_percentage}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Weekday Pattern Analysis */}
      {hasDaywiseData && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200 m-0">
              Weekday Absence Distribution (Asia/Kolkata Calendar)
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-7 gap-2">
            {weekday.map((w) => (
              <div
                key={w.weekday_index}
                className={`p-3 rounded-md border text-center space-y-2 ${
                  w.delivered > 0
                    ? "bg-slate-800/80 border-slate-700"
                    : "bg-slate-900/40 border-slate-800/50 text-slate-500"
                }`}
              >
                <span className="text-xs font-semibold block text-slate-200">{w.weekday_name}</span>
                {w.delivered > 0 ? (
                  <>
                    <div className="text-lg font-mono font-bold text-rose-400">
                      {w.absence_rate.toFixed(1)}%
                    </div>
                    <span className="text-[10px] text-slate-400 block">Absence Rate</span>
                    <div className="text-[11px] font-mono text-slate-300 pt-1 border-t border-slate-700/60">
                      {w.missed} / {w.delivered} missed
                    </div>
                    <span className="text-[10px] text-slate-400 block">
                      {w.observed_teaching_dates} teaching days
                    </span>
                  </>
                ) : (
                  <div className="py-4 text-xs text-slate-500">No scheduled periods</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Subject Absence Rankings (3 Distinct Dimensions) */}
      {subjects && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-rose-400" />
              <h3 className="text-sm font-semibold text-slate-200 m-0">
                Subject Absence Rankings
              </h3>
            </div>

            {/* Ranking Dimension Tabs */}
            <div className="inline-flex rounded-md bg-slate-800 p-1 border border-slate-700/80">
              <button
                onClick={() => setRankingTab("absolute")}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  rankingTab === "absolute"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                By Absolute Missed
              </button>
              <button
                onClick={() => setRankingTab("rate")}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  rankingTab === "rate"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                By Absence Rate (%)
              </button>
              <button
                onClick={() => setRankingTab("delivered")}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  rankingTab === "delivered"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                By Total Delivered
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-medium">
                  <th className="py-2.5 px-3 w-12">#</th>
                  <th className="py-2.5 px-3">Course Code</th>
                  <th className="py-2.5 px-3">Course Title</th>
                  <th className="py-2.5 px-3 text-right">
                    {rankingTab === "absolute"
                      ? "Periods Missed"
                      : rankingTab === "rate"
                      ? "Absence Rate (%)"
                      : "Total Delivered"}
                  </th>
                  <th className="py-2.5 px-3 text-right">Share of Term Absences</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {(rankingTab === "absolute"
                  ? subjects.rankings.by_absolute_missed
                  : rankingTab === "rate"
                  ? subjects.rankings.by_missed_rate
                  : subjects.rankings.by_total_delivered
                ).map((item, idx) => {
                  const subj = subjects.subjects.find((s) => s.course_code === item.course_code);
                  return (
                    <tr key={item.course_code} className="hover:bg-slate-850/50">
                      <td className="py-2.5 px-3 font-mono text-slate-500">{idx + 1}</td>
                      <td className="py-2.5 px-3 font-mono font-medium text-indigo-300">
                        {item.course_code}
                      </td>
                      <td className="py-2.5 px-3 text-slate-200 font-medium">{item.course_name}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-100">
                        {rankingTab === "absolute"
                          ? `${item.value} periods`
                          : rankingTab === "rate"
                          ? `${item.value.toFixed(2)}%`
                          : `${item.value} periods`}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-400">
                        {subj ? `${subj.absence_contribution_percentage}%` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
