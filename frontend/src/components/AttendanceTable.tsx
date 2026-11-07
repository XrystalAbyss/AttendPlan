import {standing} from "../standing";
import React, { useState } from "react";
import {
  CheckCircle,
  AlertTriangle,
  MinusCircle,
  FlaskConical,
  BookOpen,
  SlidersHorizontal,
} from "lucide-react";
import type { CourseRecord } from "../types/attendance";

interface Props {
  courses: CourseRecord[];
  targetPercentage: number;
  onOpenCourse?: (course: CourseRecord) => void;
  onSelectCourseForSimulation: (course: CourseRecord) => void;
}

type FilterType = "ALL" | "CAUTION" | "AT_RISK" | "SAFE" | "UNRECORDED" | "LAB" | "THEORY";

export const AttendanceTable: React.FC<Props> = ({
  courses,
  targetPercentage,
  onSelectCourseForSimulation,
  onOpenCourse,
}) => {
  const [filter, setFilter] = useState<FilterType>("ALL");
  const [search, setSearch] = useState<string>("");

  const filteredCourses = courses.filter((c) => {
    // Filter by category
    if (filter === "AT_RISK" && standing(c).status !== "AT_RISK") return false;
    if (filter === "SAFE" && standing(c).status !== "SAFE") return false;
    if (filter === "UNRECORDED" && c.status !== "UNRECORDED") return false;
    if (filter === "CAUTION" && standing(c).status !== "CAUTION") return false;
    if (filter === "LAB" && !c.is_lab) return false;
    if (filter === "THEORY" && c.is_lab) return false;

    // Filter by search query
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchName = c.name.toLowerCase().includes(q);
      const matchCode = c.code.toLowerCase().includes(q);
      const matchShort = c.short_name.toLowerCase().includes(q);
      const matchFaculty = (c.faculty ?? "").toLowerCase().includes(q);
      return matchName || matchCode || matchShort || matchFaculty;
    }
    return true;
  });

  return (
    <div className="course-table-panel bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-sm">
      {/* Controls Bar: Filter Tabs & Search */}
      <div className="p-4 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-850 bg-slate-800/40">
        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {(
            [
              { key: "ALL", label: `All (${courses.length})` },
              { key: "CAUTION", label: `Caution (${courses.filter(c=>standing(c).status === "CAUTION").length})` },
              {
                key: "AT_RISK",
                label: `At Risk (${courses.filter((c) => standing(c).status === "AT_RISK").length})`,
                color: "text-rose-400 hover:bg-rose-950/40",
              },
              {
                key: "SAFE",
                label: `Safe (${courses.filter((c) => standing(c).status === "SAFE").length})`,
                color: "text-emerald-400 hover:bg-emerald-950/40",
              },
              {
                key: "UNRECORDED",
                label: `Unrecorded (${courses.filter((c) => c.status === "UNRECORDED").length})`,
              },
              {
                key: "LAB",
                label: `Labs (${courses.filter((c) => c.is_lab).length})`,
              },
              {
                key: "THEORY",
                label: `Theory (${courses.filter((c) => !c.is_lab).length})`,
              },
            ] as const
          ).map((item) => (
            <button
              key={item.key}
              aria-pressed={filter === item.key}
              onClick={() => setFilter(item.key)}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                filter === item.key
                  ? "bg-slate-700 text-slate-100 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search code, course, or faculty..."
            aria-label="Search courses"
            className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500 w-full sm:w-64"
          />
        </div>
      </div>

      {/* Table Element */}
      <div className="overflow-x-auto">
        <table className="data-table w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-800/60 text-slate-400 font-semibold uppercase tracking-wider">
              <th scope="col" className="py-3 px-4 w-28">Code</th>
              <th scope="col" className="py-3 px-4">Course Name &amp; Faculty</th>
              <th scope="col" className="py-3 px-3 text-center w-24">Type</th>
              <th scope="col" className="py-3 px-3 text-center w-16">Credit</th>
              <th scope="col" className="py-3 px-4 text-center w-28">Attended / Del</th>
              <th scope="col" className="py-3 px-4 w-44">Attendance %</th>
              <th scope="col" className="py-3 px-4 w-52">Action / Margin</th>
              <th scope="col" className="py-3 px-3 text-center w-20">Simulate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/80">
            {filteredCourses.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-400">
                  No courses match the current filter or search criteria.
                </td>
              </tr>
            ) : (
              filteredCourses.map((c) => {
                const isSafe = standing(c).status === "SAFE";
                const isRisk = standing(c).status === "AT_RISK";
                const isCaution = standing(c).status === "CAUTION";
                const isUnrecorded = c.status === "UNRECORDED";

                return (
                  <tr
                    key={c.code}
                    className="hover:bg-slate-800/40 transition-colors group"
                  >
                    {/* Course Code */}
                    <td className="py-3 px-4 align-top">
                      <span className="font-mono font-bold text-slate-200 bg-slate-800/90 border border-slate-700 px-2 py-0.5 rounded">
                        {c.code}
                      </span>
                      <div className="text-[10px] text-slate-400 mt-1 truncate" title={c.short_name}>
                        {c.short_name}
                      </div>
                    </td>

                    {/* Course Name & Faculty */}
                    <td className="py-3 px-4 align-top">
                      <div className="font-medium text-slate-200 leading-snug">
                        <button className="text-left underline decoration-dotted underline-offset-4 hover:text-indigo-300" onClick={() => onOpenCourse?.(c)}>{c.name}</button>
                      </div>
                      <div className="text-slate-400 text-[11px] mt-0.5">
                        {c.faculty ? `Faculty: ${c.faculty}` : "Faculty unassigned"}
                      </div>
                    </td>

                    {/* Course Type (Lab vs Theory) */}
                    <td className="py-3 px-3 align-top text-center">
                      {c.is_lab ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-cyan-950/40 text-cyan-400 border border-cyan-800/60">
                          <FlaskConical className="w-3 h-3" />
                          Lab
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                          <BookOpen className="w-3 h-3" />
                          Theory
                        </span>
                      )}
                    </td>

                    {/* Credits */}
                    <td className="py-3 px-3 align-top text-center font-mono text-slate-300">
                      {c.credits.toFixed(1)}
                    </td>

                    {/* Attended / Delivered */}
                    <td className="py-3 px-4 align-top text-center font-mono tabular-nums">
                      <span className="text-slate-200 font-semibold">{c.attended}</span>
                      <span className="text-slate-400 mx-1">/</span>
                      <span className="text-slate-400">{c.delivered}</span>
                    </td>

                    {/* Percentage & Visual Indicator */}
                    <td className="py-3 px-4 align-top">
                      <div className="flex items-center justify-between mb-1 font-mono">
                        <span
                          className={`font-bold ${
                            isSafe
                              ? "text-emerald-400"
                              : isRisk
                              ? "text-rose-400"
                              : "text-slate-400"
                          }`}
                        >
                          {c.percent !== null ? `${c.percent.toFixed(2)}%` : "Unknown"}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          Target {targetPercentage}%
                        </span>
                      </div>

                      {/* Progress Bar with 75% Threshold Marker Line */}
                      <div className="relative w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        {c.percent !== null && (
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              isSafe
                                ? "bg-emerald-500"
                                : isRisk
                                ? "bg-rose-500"
                                : "bg-slate-600"
                            }`}
                            style={{ width: `${Math.min(100, Math.max(0, c.percent))}%` }}
                          />
                        )}
                        {/* Target Marker at targetPercentage% */}
                        <div
                          className="absolute top-0 bottom-0 w-0.5 bg-amber-400/80 z-10"
                          style={{ left: `${targetPercentage}%` }}
                          title={`Target: ${targetPercentage}%`}
                        />
                      </div>
                    </td>

                    {/* Action / Margin Recommendation */}
                    <td className="py-3 px-4 align-top">
                      {isCaution && <div className="text-amber-300 border border-amber-700 rounded px-2 py-1 text-xs">Caution · 0 {c.is_lab ? "lab sessions" : "bunks"} left</div>}
                      {isSafe && (
                        <div className="inline-flex items-center gap-1.5 text-emerald-400 bg-emerald-950/40 border border-emerald-800/80 px-2.5 py-1 rounded-md text-[11px] font-medium">
                          <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>
                            {c.can_skip && c.can_skip > 0
                              ? `Safe to miss ${standing(c).bunks} ${c.is_lab ? "lab sessions (2 periods each)" : "periods"}`
                              : "On border (0 bunks left)"}
                          </span>
                        </div>
                      )}

                      {isRisk && (
                        <div className="inline-flex items-center gap-1.5 text-rose-400 bg-rose-950/40 border border-rose-800/80 px-2.5 py-1 rounded-md text-[11px] font-medium">
                          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>
                            Need {c.is_lab ? Math.ceil((c.must_attend ?? 0)/2) : c.must_attend} {c.is_lab ? "consecutive lab sessions (2 periods each)" : "consecutive periods"}
                          </span>
                        </div>
                      )}

                      {isUnrecorded && (
                        <div className="inline-flex items-center gap-1.5 text-slate-400 bg-slate-800/80 border border-slate-700 px-2.5 py-1 rounded-md text-[11px]">
                          <MinusCircle className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>Pending (0 delivered)</span>
                        </div>
                      )}
                    </td>

                    {/* Simulate Button */}
                    <td className="py-3 px-3 align-top text-center">
                      <button
                        onClick={() => onSelectCourseForSimulation(c)}
                        disabled={isUnrecorded}
                        title={isUnrecorded ? "Cannot simulate uncommenced courses" : `Simulate attendance for ${c.code}`}
                        className={`p-1.5 rounded transition-colors ${
                          isUnrecorded
                            ? "text-slate-600 cursor-not-allowed"
                            : "text-slate-400 hover:text-indigo-300 hover:bg-slate-800 cursor-pointer"
                        }`}
                      >
                        <SlidersHorizontal className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

