import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Calendar } from "lucide-react";
import { AttendanceTable } from "./AttendanceTable";
import { SummaryCards } from "./SummaryCards";
import { SemesterSelector } from "./SemesterSelector";
import { AttendanceExplorer } from "./AttendanceExplorer";
import { AbsenceAnalyticsView } from "./AbsenceAnalyticsView";
import { standing } from "../standing";
import type { AcademicTerm, CourseRecord, TermAttendanceResponse } from "../types/attendance";
import { fetchMonthlyAnalytics, fetchSubjectAnalytics, fetchWeekdayAnalytics } from "../api/attendance";

interface Props {
  terms: AcademicTerm[];
  selectedTermId: string | null;
  onSelectTerm: (termId: string) => void;
  termAttendance: TermAttendanceResponse | null | undefined;
  isLoading?: boolean;
  targetPercentage: number;
  onOpenCourseDetail: (course: CourseRecord) => void;
  onOpenSimulation: (course: CourseRecord) => void;
}

export const AttendanceView: React.FC<Props> = ({
  terms,
  selectedTermId,
  onSelectTerm,
  termAttendance,
  targetPercentage,
  onOpenCourseDetail,
  onOpenSimulation,
}) => {
  const [subView, setSubView] = useState<"roster" | "calendar">("roster");

  // Fetch date-wise and analytics data if calendar sub-view is selected
  const monthlyQuery = useQuery({
    queryKey: ["monthly-analytics", selectedTermId],
    queryFn: () => (selectedTermId ? fetchMonthlyAnalytics(selectedTermId) : []),
    enabled: !!selectedTermId && subView === "calendar",
  });

  const weekdayQuery = useQuery({
    queryKey: ["weekday-analytics", selectedTermId],
    queryFn: () => (selectedTermId ? fetchWeekdayAnalytics(selectedTermId) : []),
    enabled: !!selectedTermId && subView === "calendar",
  });

  const subjectAnalyticsQuery = useQuery({
    queryKey: ["subject-analytics", selectedTermId, targetPercentage],
    queryFn: () => (selectedTermId ? fetchSubjectAnalytics(selectedTermId, targetPercentage) : null),
    enabled: !!selectedTermId && subView === "calendar",
  });

  const courses = termAttendance?.courses ?? [];
  const cautionCount = courses.filter((c) => standing(c).status === "CAUTION").length;

  return (
    <div className="attendance-view space-y-5">
      {/* Semester Selector Bar & Sub-view Switch */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-900/90 border border-slate-800 rounded-xl">
        <div className="flex-1 max-w-md">
          {terms.length > 0 && (
            <SemesterSelector
              terms={terms}
              selectedTermId={selectedTermId}
              onSelectTerm={onSelectTerm}
            />
          )}
        </div>

        {/* Sub-view toggle pills */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-800/80 border border-slate-700/80 rounded-lg">
          <button
            onClick={() => setSubView("roster")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer ${
              subView === "roster"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            Subject Roster &amp; Planner
          </button>
          <button
            onClick={() => setSubView("calendar")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer ${
              subView === "calendar"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            Date-wise Calendar &amp; Trends
          </button>
        </div>
      </div>

      {/* Primary Content Area */}
      {subView === "roster" ? (
        <div className="space-y-6">
          {termAttendance?.summary && (
            <SummaryCards
              cautionCount={cautionCount}
              summary={termAttendance.summary}
              targetPercentage={targetPercentage}
            />
          )}

          <AttendanceTable
            courses={courses}
            targetPercentage={targetPercentage}
            onOpenCourse={onOpenCourseDetail}
            onSelectCourseForSimulation={onOpenSimulation}
          />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Day-wise Calendar View */}
          <AttendanceExplorer
            targetPercentage={targetPercentage}
            key={selectedTermId}
            termId={selectedTermId ?? ""}
            academicYear={termAttendance?.academic_year ?? ""}
          />

          {/* Absence Trends & Weekday Distribution */}
          <AbsenceAnalyticsView
            monthly={monthlyQuery.data ?? []}
            weekday={weekdayQuery.data ?? []}
            subjects={subjectAnalyticsQuery.data ?? null}
            isLoading={monthlyQuery.isLoading || weekdayQuery.isLoading || subjectAnalyticsQuery.isLoading}
          />
        </div>
      )}
    </div>
  );
};

