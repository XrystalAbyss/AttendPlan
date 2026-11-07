import React from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  HelpCircle,
  KeyRound,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  UserCheck,
} from "lucide-react";
import { standing } from "../standing";
import { API_BASE } from "../api/attendance";
import type { AcademicTerm, CourseRecord, TermAttendanceResponse } from "../types/attendance";

interface Props {
  termAttendance: TermAttendanceResponse | null | undefined;
  terms: AcademicTerm[];
  currentTermId: string | null;
  targetPercentage: number;
  onNavigate: (tab: "home" | "attendance" | "performance" | "settings") => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  refreshError?: string | null;
  lastSyncTime?: string | null;
  connectionState?: string;
  onOpenCourseSimulation?: (course: CourseRecord) => void;
}

export const HomeView: React.FC<Props> = ({
  termAttendance,
  terms,
  currentTermId,
  targetPercentage,
  onNavigate,
  onRefresh,
  isRefreshing,
  refreshError,
  lastSyncTime,
  connectionState,
  onOpenCourseSimulation,
}) => {
  const currentTerm = terms.find((t) => t.id === currentTermId) ?? terms[0];
  const courses = termAttendance?.courses ?? [];
  const summary = termAttendance?.summary;

  // Compute overall standing & margins
  const overallPercentage = summary?.overall_percentage ?? null;
  const totalDelivered = summary?.total_delivered ?? 0;
  const totalAttended = summary?.total_attended ?? 0;

  // Course standing counts
  const cautionCourses: CourseRecord[] = [];
  const atRiskCourses: CourseRecord[] = [];
  const safeCourses: CourseRecord[] = [];
  const unrecordedCourses: CourseRecord[] = [];
  let totalSafeBunks = 0;
  let totalRecoveryNeeded = 0;

  for (const c of courses) {
    const s = standing(c);
    if (s.status === "AT_RISK") {
      atRiskCourses.push(c);
      if (c.must_attend && c.must_attend > 0) {
        totalRecoveryNeeded += c.must_attend;
      }
    } else if (s.status === "CAUTION") {
      cautionCourses.push(c);
    } else if (s.status === "SAFE") {
      safeCourses.push(c);
    } else if (s.status === "UNRECORDED" || c.status === "UNRECORDED") {
      unrecordedCourses.push(c);
    }
    if (s.bunks && s.bunks > 0) {
      totalSafeBunks += s.bunks;
    }
  }

  const attentionRequired = [...atRiskCourses, ...cautionCourses];
  const isSafe = overallPercentage !== null && overallPercentage >= targetPercentage;

  const formatLastSync = (iso?: string | null) => {
    if (!iso) return "Saved locally";
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const handleLaunchBrowser = async () => {
    try {
      await fetch(`${API_BASE}/api/v1/portal/session/launch`, { method: "POST" });
    } catch {
      // Ignore network errors in offline test mode
    }
  };

  return (
    <div className="home-view space-y-6">
      {/* 1. Quick Refresh & Sync Status Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-slate-900/90 border border-slate-800 rounded-xl shadow-sm">
        <div className="flex items-center gap-3">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isRefreshing
                ? "bg-amber-400 animate-ping"
                : connectionState === "ACTION_REQUIRED"
                ? "bg-amber-400"
                : "bg-emerald-400"
            }`}
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200">
                {isRefreshing
                  ? "Refreshing attendance..."
                  : connectionState === "ACTION_REQUIRED"
                  ? "Portal sign-in required"
                  : "Attendance up to date"}
              </span>
              <span className="text-slate-500 text-xs">&bull;</span>
              <span className="text-xs text-slate-400">
                Last updated {formatLastSync(lastSyncTime ?? termAttendance?.captured_at)}
              </span>
            </div>
            {refreshError && <p className="text-xs text-rose-400 mt-0.5">{refreshError}</p>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {connectionState === "ACTION_REQUIRED" ? (
            <button
              onClick={handleLaunchBrowser}
              className="px-3.5 py-1.5 bg-amber-600/30 hover:bg-amber-600/50 border border-amber-500/50 text-amber-200 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              <UserCheck className="w-3.5 h-3.5" />
              Sign in to Portal
            </button>
          ) : (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              {isRefreshing ? "Syncing..." : "Refresh Attendance"}
            </button>
          )}
        </div>
      </div>

      {/* 2. University Session Expiration Action Banner (if session expired) */}
      {connectionState === "ACTION_REQUIRED" && (
        <div className="p-4 bg-amber-950/40 border border-amber-800/80 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-sm">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-amber-900/60 border border-amber-700 text-amber-300 flex-shrink-0 mt-0.5">
              <KeyRound className="w-4 h-4" />
            </div>
            <div>
              <p className="font-semibold text-amber-200 m-0">University Session Expired</p>
              <p className="text-slate-300 mt-0.5 m-0 leading-relaxed">
                Your iCloudEMS session has expired. Open your dedicated Chrome window, log in with your university credentials and Authenticator code, then click Refresh.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handleLaunchBrowser}
              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-slate-950 font-semibold rounded-lg text-xs inline-flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open Portal in Chrome
            </button>
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              Retry Sync
            </button>
          </div>
        </div>
      )}

      {/* 3. Primary KPI Hero Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 p-6 bg-slate-900/90 border border-slate-800 rounded-xl space-y-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold tracking-wider uppercase text-indigo-400">
                Current Semester Overview
              </span>
              <h3 className="text-xl font-bold text-slate-100 mt-0.5">
                {currentTerm ? `Semester ${currentTerm.semester_number} · AY ${currentTerm.academic_year}` : "Attendance Standing"}
              </h3>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                isSafe
                  ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                  : "bg-rose-950/80 text-rose-300 border border-rose-800"
              }`}
            >
              {isSafe ? "In Good Standing" : "Attention Required"}
            </span>
          </div>

          <div className="flex items-baseline gap-4">
            <span className="text-5xl font-extrabold tracking-tight font-mono text-slate-100">
              {overallPercentage !== null ? `${overallPercentage.toFixed(1)}%` : "—"}
            </span>
            <div className="text-xs text-slate-400 space-y-0.5">
              <p className="m-0 font-medium">
                {totalAttended} attended of {totalDelivered} delivered periods
              </p>
              <p className="m-0 text-slate-500">Target threshold: {targetPercentage}%</p>
            </div>
          </div>

          {/* Progress bar vs 75% target line */}
          <div className="space-y-1.5">
            <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden relative">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isSafe ? "bg-emerald-500" : "bg-rose-500"
                }`}
                style={{ width: `${Math.min(100, Math.max(0, overallPercentage ?? 0))}%` }}
              />
              {/* 75% marker line */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-amber-400"
                style={{ left: `${targetPercentage}%` }}
                title={`${targetPercentage}% requirement threshold`}
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>0%</span>
              <span className="text-amber-400 font-semibold">{targetPercentage}% requirement</span>
              <span>100%</span>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed m-0">
            {overallPercentage !== null && overallPercentage >= targetPercentage ? (
              <>
                You are currently{" "}
                <strong className="text-emerald-300">
                  +{(overallPercentage - targetPercentage).toFixed(1)}%
                </strong>{" "}
                above the university 75% requirement. You have{" "}
                <strong className="text-indigo-300">{totalSafeBunks} safe periods</strong> available
                across your enrolled subjects.
              </>
            ) : overallPercentage !== null ? (
              <>
                You are currently{" "}
                <strong className="text-rose-400">
                  {(targetPercentage - overallPercentage).toFixed(1)}% below
                </strong>{" "}
                the required threshold. Focus on attending scheduled lectures for flagged courses to recover standing.
              </>
            ) : (
              "Loading attendance data..."
            )}
          </p>

          <p className="text-[11px] text-slate-500 italic m-0 pt-1 border-t border-slate-800/80">
            Note: University 75% attendance is strictly enforced course-by-course. Safe margins in one subject cannot be transferred to cover absences in another.
          </p>
        </div>

        {/* 4. Quick Highlights & Safe Margin Card */}
        <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-xl flex flex-col justify-between space-y-4 shadow-sm">
          <div className="space-y-4">
            <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">
              Attendance Planning Summary
            </span>

            <div className="space-y-2.5">
              {/* Safe to miss */}
              <div className="flex items-center justify-between p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-emerald-950/80 border border-emerald-800 text-emerald-400 rounded-md">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">Safe Periods to Skip</div>
                    <div className="text-[11px] text-slate-400">Total buffer above 75%</div>
                  </div>
                </div>
                <span className="text-xl font-bold font-mono text-emerald-400">{totalSafeBunks}</span>
              </div>

              {/* Needs attention */}
              <div className="flex items-center justify-between p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`p-2 rounded-md ${
                      attentionRequired.length > 0
                        ? "bg-amber-950/80 border border-amber-800 text-amber-400"
                        : "bg-slate-800 border border-slate-700 text-slate-400"
                    }`}
                  >
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">Needs Attention</div>
                    <div className="text-[11px] text-slate-400">Courses at or below 75%</div>
                  </div>
                </div>
                <span
                  className={`text-xl font-bold font-mono ${
                    attentionRequired.length > 0 ? "text-amber-400" : "text-slate-400"
                  }`}
                >
                  {attentionRequired.length}
                </span>
              </div>

              {/* Recovery required */}
              <div className="flex items-center justify-between p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`p-2 rounded-md ${
                      totalRecoveryNeeded > 0
                        ? "bg-rose-950/80 border border-rose-800 text-rose-400"
                        : "bg-slate-800 border border-slate-700 text-slate-400"
                    }`}
                  >
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">Recovery Classes</div>
                    <div className="text-[11px] text-slate-400">Consecutive needed to reach 75%</div>
                  </div>
                </div>
                <span
                  className={`text-xl font-bold font-mono ${
                    totalRecoveryNeeded > 0 ? "text-rose-400" : "text-slate-400"
                  }`}
                >
                  {totalRecoveryNeeded}
                </span>
              </div>

              {/* Unrecorded courses */}
              {unrecordedCourses.length > 0 && (
                <div className="flex items-center justify-between p-2.5 bg-slate-800/40 border border-slate-700/40 rounded-lg text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
                    <span>Unrecorded courses (0 delivered):</span>
                  </div>
                  <span className="font-mono font-semibold text-slate-300">{unrecordedCourses.length}</span>
                </div>
              )}
            </div>
          </div>

          <button
            onClick={() => onNavigate("attendance")}
            className="w-full py-2 px-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium rounded-lg inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
          >
            Open Full Attendance Roster
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 5. Attention Course Roster (If any at risk or near threshold) */}
      {attentionRequired.length > 0 ? (
        <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-xl space-y-3 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h4 className="text-sm font-semibold text-slate-200 m-0">
                Subjects Requiring Attention ({attentionRequired.length})
              </h4>
            </div>
            <button
              onClick={() => onNavigate("attendance")}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1 cursor-pointer"
            >
              View all {courses.length} courses <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {attentionRequired.map((course) => {
              const s = standing(course);
              return (
                <div
                  key={course.code}
                  className="p-3.5 bg-slate-800/60 border border-slate-700/60 rounded-lg flex flex-col justify-between gap-3 shadow-xs"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-slate-200">{course.code}</span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          s.status === "AT_RISK"
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : "bg-amber-950 text-amber-300 border border-amber-800"
                        }`}
                      >
                        {s.status === "AT_RISK" ? "AT RISK" : "CAUTION"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 line-clamp-1 m-0" title={course.name}>
                      {course.name}
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-slate-700/50 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-slate-300">
                        {course.attended}/{course.delivered} ({course.percent?.toFixed(1) ?? "—"}%)
                      </span>
                      {onOpenCourseSimulation && (
                        <button
                          onClick={() => onOpenCourseSimulation(course)}
                          className="text-indigo-400 hover:text-indigo-300 text-[11px] font-medium cursor-pointer"
                        >
                          Simulate &rarr;
                        </button>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 m-0 leading-tight">
                      {s.status === "AT_RISK" ? (
                        <span className="text-rose-400 font-medium">
                          Need {course.is_lab ? Math.ceil((course.must_attend ?? 0) / 2) : course.must_attend} {course.is_lab ? "lab sessions" : "consecutive classes"} to reach 75%
                        </span>
                      ) : (
                        <span className="text-amber-400 font-medium">
                          At threshold · 0 {course.is_lab ? "lab sessions" : "classes"} safe to miss
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : courses.length > 0 ? (
        <div className="p-4 bg-emerald-950/30 border border-emerald-900/60 rounded-xl flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-emerald-900/50 border border-emerald-700 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-emerald-300 m-0">All courses meeting attendance goals</p>
              <p className="text-[11px] text-emerald-400/80 m-0">
                Every enrolled course is at or above the 75% institutional requirement.
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate("attendance")}
            className="text-xs text-emerald-300 hover:text-white font-medium inline-flex items-center gap-1 cursor-pointer"
          >
            Review Roster <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      ) : null}

      {/* 6. Destination Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <div
          onClick={() => onNavigate("attendance")}
          className="p-4 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl transition-all cursor-pointer group flex flex-col justify-between space-y-3 shadow-xs"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-950/80 border border-indigo-800 text-indigo-400 rounded-lg group-hover:scale-105 transition-transform">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-100 m-0">Attendance Roster</h4>
              <p className="text-xs text-slate-400 m-0 mt-0.5">Subject breakdown &amp; simulator</p>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs text-indigo-400 font-medium">
            <span>Explore 5 Semesters</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>

        <div
          onClick={() => onNavigate("performance")}
          className="p-4 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl transition-all cursor-pointer group flex flex-col justify-between space-y-3 shadow-xs"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-950/80 border border-emerald-800 text-emerald-400 rounded-lg group-hover:scale-105 transition-transform">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-100 m-0">Internal Assessments</h4>
              <p className="text-xs text-slate-400 m-0 mt-0.5">Continuous evaluation marks</p>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs text-emerald-400 font-medium">
            <span>468 assessment scores</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>

        <div
          onClick={() => onNavigate("settings")}
          className="p-4 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl transition-all cursor-pointer group flex flex-col justify-between space-y-3 shadow-xs"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg group-hover:scale-105 transition-transform">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-100 m-0">Account &amp; Settings</h4>
              <p className="text-xs text-slate-400 m-0 mt-0.5">Credentials, sync &amp; backups</p>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Local security vault</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>
    </div>
  );
};
