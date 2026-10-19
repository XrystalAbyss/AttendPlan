import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchPortalSessionStatus,
  launchPortalBrowser,
  closePortalBrowser,
  discoverTerms,
  discoverSubjectWise,
  discoverDayWise,
  discoverOverall,
  seedDemoData,
} from "../api/attendance";
import type {
  AcademicTermDiscoveryResponse,
  DayWiseDiscoveryResponse,
  OverallDiscoveryResponse,
  PortalSessionState,
  SubjectWiseDiscoveryResponse,
} from "../types/attendance";
import {
  Compass,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  Power,
  Layers,
  Calendar,
  Table as TableIcon,
  Clock,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Upload,
  Database,
  Lock,
} from "lucide-react";

interface PortalDiscoveryViewProps {
  onRefreshTerms?: () => void;
}

export const PortalDiscoveryView: React.FC<PortalDiscoveryViewProps> = ({ onRefreshTerms }) => {
  const queryClient = useQueryClient();
  const [manualHtml, setManualHtml] = useState<string>("");
  const [useManualInput, setUseManualInput] = useState<boolean>(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  // Results state
  const [termsResult, setTermsResult] = useState<AcademicTermDiscoveryResponse | null>(null);
  const [subjectResult, setSubjectResult] = useState<SubjectWiseDiscoveryResponse | null>(null);
  const [daywiseResult, setDaywiseResult] = useState<DayWiseDiscoveryResponse | null>(null);
  const [overallResult, setOverallResult] = useState<OverallDiscoveryResponse | null>(null);

  // 1. Session Status Query
  const statusQuery = useQuery({
    queryKey: ["portal-session-status"],
    queryFn: fetchPortalSessionStatus,
    refetchInterval: (query) => {
      // Auto-poll every 3s while waiting for login or browser ready
      const state = query.state.data?.state;
      return state === "BROWSER_READY" || state === "LOGIN_REQUIRED" || state === "DISCOVERING"
        ? 3000
        : false;
    },
  });

  const session = statusQuery.data;
  const state: PortalSessionState = session?.state ?? "DISCONNECTED";

  // Mutations
  const launchMutation = useMutation({
    mutationFn: launchPortalBrowser,
    onSuccess: (data) => {
      queryClient.setQueryData(["portal-session-status"], data);
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const closeMutation = useMutation({
    mutationFn: closePortalBrowser,
    onSuccess: (data) => {
      queryClient.setQueryData(["portal-session-status"], data);
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const seedMutation = useMutation({
    mutationFn: seedDemoData,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["terms"] });
      if (onRefreshTerms) onRefreshTerms();
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const termsMutation = useMutation({
    mutationFn: () => discoverTerms(useManualInput && manualHtml.trim() ? manualHtml : undefined),
    onSuccess: (data) => {
      setTermsResult(data);
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const subjectMutation = useMutation({
    mutationFn: () => discoverSubjectWise(useManualInput && manualHtml.trim() ? manualHtml : undefined),
    onSuccess: (data) => {
      setSubjectResult(data);
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const daywiseMutation = useMutation({
    mutationFn: () => discoverDayWise(useManualInput && manualHtml.trim() ? manualHtml : undefined),
    onSuccess: (data) => {
      setDaywiseResult(data);
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const overallMutation = useMutation({
    mutationFn: () => discoverOverall(useManualInput && manualHtml.trim() ? manualHtml : undefined),
    onSuccess: (data) => {
      setOverallResult(data);
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const getStatusBadge = (s: PortalSessionState) => {
    switch (s) {
      case "AUTHENTICATED":
        return {
          bg: "bg-emerald-950/80 text-emerald-300 border-emerald-800",
          icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
          label: "AUTHENTICATED — READY FOR DISCOVERY",
        };
      case "LOGIN_REQUIRED":
        return {
          bg: "bg-amber-950/80 text-amber-300 border-amber-800",
          icon: <Lock className="w-4 h-4 text-amber-400" />,
          label: "LOGIN REQUIRED — COMPLETE KEYCLOAK & MFA IN BROWSER",
        };
      case "BROWSER_READY":
        return {
          bg: "bg-sky-950/80 text-sky-300 border-sky-800",
          icon: <Compass className="w-4 h-4 text-sky-400" />,
          label: "BROWSER READY — NAVIGATING TO PORTAL",
        };
      case "DISCOVERING":
        return {
          bg: "bg-indigo-950/80 text-indigo-300 border-indigo-800",
          icon: <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />,
          label: "DISCOVERING PORTAL VIEWS...",
        };
      case "SESSION_EXPIRED":
        return {
          bg: "bg-rose-950/80 text-rose-300 border-rose-800",
          icon: <AlertTriangle className="w-4 h-4 text-rose-400" />,
          label: "SESSION EXPIRED OR LOGGED OUT",
        };
      case "ERROR":
        return {
          bg: "bg-rose-950/80 text-rose-300 border-rose-800",
          icon: <ShieldAlert className="w-4 h-4 text-rose-400" />,
          label: "PORTAL CONNECTION ERROR",
        };
      default:
        return {
          bg: "bg-slate-900/80 text-slate-400 border-slate-800",
          icon: <Power className="w-4 h-4 text-slate-500" />,
          label: "DISCONNECTED — BROWSER NOT RUNNING",
        };
    }
  };

  const badge = getStatusBadge(state);

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
          <div>
            <div className="flex items-center gap-2">
              <Compass className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-semibold text-slate-100 m-0">
                iCloudEMS Portal Discovery (F2-A Guided Flow)
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 m-0">
              Authorized, read-only session inspection via dedicated Chrome loopback DevTools Protocol.
              Never stores OTPs, credentials, or session cookies.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold border ${badge.bg}`}
            >
              {badge.icon}
              {badge.label}
            </span>
            <button
              onClick={() => statusQuery.refetch()}
              disabled={statusQuery.isFetching}
              className="px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded inline-flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${statusQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Diagnostic Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 text-xs">
          <div className="bg-slate-950/60 p-3 rounded border border-slate-800/80">
            <span className="text-slate-500 block mb-1">Dedicated Chrome Profile</span>
            <code className="text-slate-300 break-all text-[11px]">
              {session?.profile_dir || "Local App Data (outside repo)"}
            </code>
          </div>
          <div className="bg-slate-950/60 p-3 rounded border border-slate-800/80">
            <span className="text-slate-500 block mb-1">CDP Loopback Endpoint</span>
            <code className="text-emerald-400 text-[11px]">
              {session?.cdp_url || "http://127.0.0.1:9222"} (Loopback only)
            </code>
          </div>
          <div className="bg-slate-950/60 p-3 rounded border border-slate-800/80">
            <span className="text-slate-500 block mb-1">Active Portal Tab URL</span>
            <span className="text-slate-300 truncate block text-[11px]" title={session?.current_url || "None"}>
              {session?.current_url || "No portal tab open"}
            </span>
          </div>
        </div>

        {/* Error Notification */}
        {discoveryError && (
          <div className="mt-4 p-3 bg-rose-950/50 border border-rose-800/80 rounded text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{discoveryError}</span>
          </div>
        )}

        {/* Guided Actions */}
        <div className="mt-5 flex flex-wrap items-center gap-3">
          {state === "DISCONNECTED" ? (
            <button
              onClick={() => launchMutation.mutate()}
              disabled={launchMutation.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded border border-indigo-500 inline-flex items-center gap-2 cursor-pointer shadow-sm transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              {launchMutation.isPending ? "Launching Dedicated Browser..." : "1. Launch Dedicated Chrome"}
            </button>
          ) : (
            <button
              onClick={() => closeMutation.mutate()}
              disabled={closeMutation.isPending}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs rounded border border-slate-700 inline-flex items-center gap-1.5 cursor-pointer"
            >
              <Power className="w-3.5 h-3.5 text-rose-400" />
              Close Dedicated Browser
            </button>
          )}

          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs rounded border border-slate-700 inline-flex items-center gap-1.5 cursor-pointer"
          >
            <Database className="w-3.5 h-3.5 text-indigo-400" />
            {seedMutation.isPending ? "Seeding..." : "Load Sample Historical Data (Demo)"}
          </button>

          <button
            onClick={() => setUseManualInput(!useManualInput)}
            className={`px-3 py-1.5 text-xs rounded border inline-flex items-center gap-1.5 cursor-pointer transition-colors ${
              useManualInput
                ? "bg-indigo-950 text-indigo-300 border-indigo-700 font-medium"
                : "bg-slate-800/60 text-slate-400 hover:text-slate-200 border-slate-700"
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            {useManualInput ? "Manual HTML Fallback (Active)" : "Use Manual HTML Fallback"}
          </button>
        </div>
      </div>

      {/* Manual HTML Fallback Box (if toggled) */}
      {useManualInput && (
        <div className="bg-slate-900/60 border border-indigo-800/60 rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-indigo-300 m-0 flex items-center gap-2">
              <Upload className="w-4 h-4 text-indigo-400" />
              Manual HTML Source Fallback (No Chrome / Anti-Tamper Bypass)
            </h3>
            <span className="text-xs text-slate-400">Supported offline method</span>
          </div>
          <p className="text-xs text-slate-400 m-0">
            Paste raw page HTML from the student portal below, or upload a saved <code>.html</code> file. Discovery
            adapters will execute deterministically without requiring a live browser connection.
          </p>
          <textarea
            value={manualHtml}
            onChange={(e) => setManualHtml(e.target.value)}
            placeholder="Paste raw <html>...</html> content here..."
            className="w-full h-32 bg-slate-950 border border-slate-800 rounded p-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>
      )}

      {/* Discovery Area Actions Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Area 1: Academic Terms Discovery */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-indigo-400 mb-2">
              <Calendar className="w-4 h-4" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 m-0">
                1. Term & Semester
              </h3>
            </div>
            <p className="text-xs text-slate-400 m-0">
              Discovers available academic years, semesters, and class mappings from portal select options.
            </p>
          </div>
          <button
            onClick={() => termsMutation.mutate()}
            disabled={termsMutation.isPending || (state !== "AUTHENTICATED" && !useManualInput)}
            className="mt-4 w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium text-slate-200 rounded border border-slate-700 inline-flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <Compass className={`w-3.5 h-3.5 ${termsMutation.isPending ? "animate-spin" : ""}`} />
            {termsMutation.isPending ? "Discovering..." : "Discover Terms"}
          </button>
        </div>

        {/* Area 2: Subject-Wise Attendance */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <TableIcon className="w-4 h-4" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 m-0">
                2. Subject-Wise
              </h3>
            </div>
            <p className="text-xs text-slate-400 m-0">
              Inspects <code>subwise_attendace_new.php</code> table headers, course codes, and row counts.
            </p>
          </div>
          <button
            onClick={() => subjectMutation.mutate()}
            disabled={subjectMutation.isPending || (state !== "AUTHENTICATED" && !useManualInput)}
            className="mt-4 w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium text-slate-200 rounded border border-slate-700 inline-flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <TableIcon className={`w-3.5 h-3.5 ${subjectMutation.isPending ? "animate-spin" : ""}`} />
            {subjectMutation.isPending ? "Discovering..." : "Discover Subject-Wise"}
          </button>
        </div>

        {/* Area 3: Day-Wise Attendance */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-amber-400 mb-2">
              <Clock className="w-4 h-4" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 m-0">
                3. Day-Wise Timetable
              </h3>
            </div>
            <p className="text-xs text-slate-400 m-0">
              Inspects <code>myattendance.php</code> date columns, time slots, P/A cells, and course toggle.
            </p>
          </div>
          <button
            onClick={() => daywiseMutation.mutate()}
            disabled={daywiseMutation.isPending || (state !== "AUTHENTICATED" && !useManualInput)}
            className="mt-4 w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium text-slate-200 rounded border border-slate-700 inline-flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <Clock className={`w-3.5 h-3.5 ${daywiseMutation.isPending ? "animate-spin" : ""}`} />
            {daywiseMutation.isPending ? "Discovering..." : "Discover Day-Wise"}
          </button>
        </div>

        {/* Area 4: Overall Attendance */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-sky-400 mb-2">
              <Layers className="w-4 h-4" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 m-0">
                4. Overall View
              </h3>
            </div>
            <p className="text-xs text-slate-400 m-0">
              Inspects <code>allSubject.php</code> macro filters, columns, and reported percentage.
            </p>
          </div>
          <button
            onClick={() => overallMutation.mutate()}
            disabled={overallMutation.isPending || (state !== "AUTHENTICATED" && !useManualInput)}
            className="mt-4 w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-medium text-slate-200 rounded border border-slate-700 inline-flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <Layers className={`w-3.5 h-3.5 ${overallMutation.isPending ? "animate-spin" : ""}`} />
            {overallMutation.isPending ? "Discovering..." : "Discover Overall"}
          </button>
        </div>
      </div>

      {/* Discovered Findings Cards */}
      {(termsResult || subjectResult || daywiseResult || overallResult) && (
        <div className="space-y-4 pt-2">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 m-0">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Discovered University Portal Evidence (Verified Read-Only Findings)
          </h3>

          {/* Terms Findings */}
          {termsResult && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-4 space-y-3">
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider block">
                Discovered Terms, Semesters & Classes
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 font-medium block mb-1">Academic Years Found:</span>
                  <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                    {termsResult.academic_years.map((y) => (
                      <li key={y.value}>
                        {y.label} {y.selected && <span className="text-emerald-400 text-[10px]">(Active)</span>}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <span className="text-slate-500 font-medium block mb-1">Semesters Available:</span>
                  <div className="flex flex-wrap gap-1">
                    {termsResult.semesters.map((s) => (
                      <span
                        key={s.value}
                        className={`px-2 py-0.5 rounded text-[11px] font-mono border ${
                          s.selected
                            ? "bg-indigo-950 text-indigo-300 border-indigo-700"
                            : "bg-slate-800 text-slate-400 border-slate-700"
                        }`}
                      >
                        Sem {s.label}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 font-medium block mb-1">Classes / Sections:</span>
                  <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                    {termsResult.classes.map((c) => (
                      <li key={c.value}>{c.label}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Subject-Wise Findings */}
          {subjectResult && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-4 space-y-2">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider block">
                Subject-Wise Table Architecture
              </span>
              <div className="flex flex-wrap gap-4 text-xs">
                <div>
                  <span className="text-slate-500 block">Table Found:</span>
                  <span className="font-semibold text-slate-200">
                    {subjectResult.table_found ? "YES" : "NO"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Rows Count:</span>
                  <span className="font-semibold text-slate-200">{subjectResult.record_count}</span>
                </div>
                <div className="flex-1">
                  <span className="text-slate-500 block">Header Columns:</span>
                  <span className="text-slate-300">{subjectResult.header_columns.join(" | ")}</span>
                </div>
              </div>
            </div>
          )}

          {/* Day-Wise Findings */}
          {daywiseResult && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-4 space-y-3">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider block">
                Day-Wise Timetable Structure
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block mb-1">Course Name Toggle:</span>
                  <span className="font-semibold text-slate-200">
                    {daywiseResult.has_course_name_toggle ? "PRESENT ON FORM" : "NOT VISIBLE"}
                  </span>
                  <span className="text-slate-500 block text-[11px] mt-1">
                    Mechanism: {daywiseResult.course_name_mapping_mechanism}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block mb-1">Discovered Time Slots:</span>
                  <div className="flex flex-wrap gap-1">
                    {daywiseResult.time_slots.slice(0, 4).map((s, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]"
                      >
                        {s}
                      </span>
                    ))}
                    {daywiseResult.time_slots.length > 4 && (
                      <span className="text-slate-500 text-[10px] self-center">
                        +{daywiseResult.time_slots.length - 4} more
                      </span>
                    )}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 block mb-1">Observed Status Markers:</span>
                  <span className="text-slate-200 font-mono">
                    {daywiseResult.sample_statuses_observed.join(", ") || "None"}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Overall Findings */}
          {overallResult && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-4 space-y-2">
              <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider block">
                Overall Attendance View (allSubject.php)
              </span>
              <div className="flex flex-wrap gap-4 text-xs">
                <div>
                  <span className="text-slate-500 block">View Present:</span>
                  <span className="font-semibold text-slate-200">{overallResult.view_found ? "YES" : "NO"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Filter Controls:</span>
                  <span className="text-slate-300">{overallResult.filter_controls.join(", ") || "None"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Columns:</span>
                  <span className="text-slate-300">{overallResult.displayed_columns.join(" | ") || "None"}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
