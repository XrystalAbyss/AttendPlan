import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchPortalSessionStatus,
  fetchHistoricalTerms,
  launchPortalBrowser,
  closePortalBrowser,
  discoverTerms,
  discoverSubjectWise,
  discoverDayWise,
  discoverOverall,
  seedDemoData,
  syncSubjectWiseLive,
  syncDayWiseLive,
  runPilotSync,
  fetchHistoricalPlan,
  fetchLatestSyncJob,
  cancelSyncJob,
  orchestrateLogin,
} from "../api/attendance";
import type {
  AcademicTermDiscoveryResponse,
  DayWiseDiscoveryResponse,
  HistoricalPlanResponse,
  OverallDiscoveryResponse,
  PortalSessionState,
  SubjectWiseDiscoveryResponse,
  SyncDayWiseResponse,
  SyncJobState,
  SyncSubjectWiseResponse,
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
  Play,
  StopCircle,
  Activity,
  ListChecks,
  KeyRound,
} from "lucide-react";


interface PortalDiscoveryViewProps {
  onRefreshTerms?: () => void;
  onOpenAuthModal?: () => void;
}

type SyncTab = "sync" | "planner" | "discovery" | "fallback";

export const PortalDiscoveryView: React.FC<PortalDiscoveryViewProps> = ({ onRefreshTerms, onOpenAuthModal }) => {
  const queryClient = useQueryClient();
  const [activeSubTab, setActiveSubTab] = useState<SyncTab>("sync");
  const [manualHtml, setManualHtml] = useState<string>("");
  const [useManualInput, setUseManualInput] = useState<boolean>(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  // Discovery results state
  const [termsResult, setTermsResult] = useState<AcademicTermDiscoveryResponse | null>(null);
  const [subjectResult, setSubjectResult] = useState<SubjectWiseDiscoveryResponse | null>(null);
  const [daywiseResult, setDaywiseResult] = useState<DayWiseDiscoveryResponse | null>(null);
  const [overallResult, setOverallResult] = useState<OverallDiscoveryResponse | null>(null);

  // Live Sync form states
  const [syncYear, setSyncYear] = useState<string>("");
  const [syncSemester, setSyncSemester] = useState<number>(0);
  const [syncClassId, setSyncClassId] = useState<string>("");
  const [syncMonth, setSyncMonth] = useState<string>("09");
  const [syncShowCourseName, setSyncShowCourseName] = useState<boolean>(true);

  // Live Sync results state
  const [subjectSyncResult, setSubjectSyncResult] = useState<SyncSubjectWiseResponse | null>(null);
  const [daywiseSyncResult, setDaywiseSyncResult] = useState<SyncDayWiseResponse | null>(null);
  const [historicalPlan, setHistoricalPlan] = useState<HistoricalPlanResponse | null>(null);

  const verifiedTermsQuery = useQuery({queryKey:["historical-terms"],queryFn:fetchHistoricalTerms});
  const scopeReady = !!syncYear && syncSemester > 0 && !!syncClassId;

  // 1. Session Status Query
  const statusQuery = useQuery({
    queryKey: ["portal-session-status"],
    queryFn: fetchPortalSessionStatus,
    refetchInterval: (query) => {
      const s = query.state.data?.state;
      return s === "BROWSER_READY" || s === "LOGIN_REQUIRED" || s === "DISCOVERING" ? 3000 : false;
    },
  });

  const session = statusQuery.data;
  const state: PortalSessionState = session?.state ?? "DISCONNECTED";

  // 2. Latest Sync Job Query
  const jobQuery = useQuery({
    queryKey: ["latest-sync-job"],
    queryFn: fetchLatestSyncJob,
    refetchInterval: (query) => {
      const s = query.state.data?.state;
      const activeStates: SyncJobState[] = [
        "DISCOVERING",
        "SYNCING_SUBJECTS",
        "SYNCING_DAYWISE",
        "VALIDATING",
        "PERSISTING",
        "RECONCILING",
      ];
      return s && activeStates.includes(s) ? 1500 : false;
    },
  });

  const latestJob = jobQuery.data;

  // Browser Actions
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

  const loginMutation = useMutation({
    mutationFn: () => orchestrateLogin(),
    onSuccess: (data) => {
      if (data.success && data.state === "AUTHENTICATED") {
        queryClient.invalidateQueries({ queryKey: ["portal-session-status"] });
        queryClient.invalidateQueries({ queryKey: ["terms"] });
        queryClient.invalidateQueries({ queryKey: ["term-attendance"] });
        if (onRefreshTerms) onRefreshTerms();
      }
      setDiscoveryError(data.success ? null : data.message);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const seedMutation = useMutation({

    mutationFn: seedDemoData,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["terms"] });
      queryClient.invalidateQueries({ queryKey: ["term-attendance"] });
      queryClient.invalidateQueries({ queryKey: ["reconciliation"] });
      if (onRefreshTerms) onRefreshTerms();
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  // Discovery Mutations
  const termsMutation = useMutation({
    mutationFn: () => discoverTerms(useManualInput && manualHtml.trim() ? manualHtml : undefined),
    onSuccess: (data) => {
      setTermsResult(data);
      if (data.academic_years.length > 0) setSyncYear(data.academic_years[0].value);
      if (data.semesters.length > 0) setSyncSemester(parseInt(data.semesters[0].value, 10) || 5);
      if (data.classes.length > 0) setSyncClassId(data.classes[0].value);
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

  // Live Sync Mutations
  const syncSubjectMutation = useMutation({
    mutationFn: (persist: boolean) =>
      syncSubjectWiseLive({
        academic_year: syncYear,
        semester: syncSemester,
        class_id: syncClassId,
        persist,
      }),
    onSuccess: (data) => {
      setSubjectSyncResult(data);
      setDiscoveryError(null);
      if (data.snapshot_id) {
        queryClient.invalidateQueries({ queryKey: ["terms"] });
        queryClient.invalidateQueries({ queryKey: ["term-attendance"] });
        queryClient.invalidateQueries({ queryKey: ["reconciliation"] });
        if (onRefreshTerms) onRefreshTerms();
      }
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const syncDaywiseMutation = useMutation({
    mutationFn: (persist: boolean) =>
      syncDayWiseLive({
        academic_year: syncYear,
        semester: syncSemester,
        class_id: syncClassId,
        month: syncMonth,
        show_course_name: syncShowCourseName,
        persist,
      }),
    onSuccess: (data) => {
      setDaywiseSyncResult(data);
      setDiscoveryError(null);
      if (data.batch_id) {
        queryClient.invalidateQueries({ queryKey: ["terms"] });
        queryClient.invalidateQueries({ queryKey: ["term-attendance"] });
        queryClient.invalidateQueries({ queryKey: ["reconciliation"] });
        queryClient.invalidateQueries({ queryKey: ["monthly-analytics"] });
        queryClient.invalidateQueries({ queryKey: ["weekday-analytics"] });
        if (onRefreshTerms) onRefreshTerms();
      }
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const pilotMutation = useMutation({
    mutationFn: () =>
      runPilotSync({
        academic_year: syncYear,
        semester: syncSemester,
        class_id: syncClassId,
        month: syncMonth,
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["latest-sync-job"], data);
      queryClient.invalidateQueries({ queryKey: ["terms"] });
      queryClient.invalidateQueries({ queryKey: ["term-attendance"] });
      queryClient.invalidateQueries({ queryKey: ["reconciliation"] });
      queryClient.invalidateQueries({ queryKey: ["monthly-analytics"] });
      queryClient.invalidateQueries({ queryKey: ["weekday-analytics"] });
      if (onRefreshTerms) onRefreshTerms();
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const planMutation = useMutation({
    mutationFn: fetchHistoricalPlan,
    onSuccess: (data) => {
      setHistoricalPlan(data);
      setDiscoveryError(null);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => cancelSyncJob(jobId),
    onSuccess: (data) => {
      queryClient.setQueryData(["latest-sync-job"], data);
    },
    onError: (err: Error) => setDiscoveryError(err.message),
  });

  const getStatusBadge = (s: PortalSessionState) => {
    switch (s) {
      case "AUTHENTICATED":
        return {
          bg: "bg-emerald-950/80 text-emerald-300 border-emerald-800",
          icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
          label: "AUTHENTICATED — READY FOR SYNC",
        };
      case "LOGIN_REQUIRED":
        return {
          bg: "bg-amber-950/80 text-amber-300 border-amber-800",
          icon: <Lock className="w-4 h-4 text-amber-400" />,
          label: "LOGIN REQUIRED — COMPLETE KEYCLOAK & MFA IN CHROME",
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

  const getJobBadge = (js: SyncJobState) => {
    switch (js) {
      case "COMPLETED":
        return "bg-emerald-950/90 text-emerald-300 border-emerald-700";
      case "FAILED":
      case "SESSION_EXPIRED":
        return "bg-rose-950/90 text-rose-300 border-rose-700";
      case "CANCELLED":
        return "bg-slate-800 text-slate-300 border-slate-700";
      default:
        return "bg-indigo-950/90 text-indigo-300 border-indigo-700 animate-pulse";
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
                iCloudEMS Portal Discovery & Synchronization Center (F2-B)
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 m-0">
              Live, privacy-preserving attendance synchronization using the student's authorized iCloudEMS session.
              Credentials and session cookies never leave your local machine.
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
              onClick={() => {
                statusQuery.refetch();
                jobQuery.refetch();
              }}
              disabled={statusQuery.isFetching}
              className="px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded inline-flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${statusQuery.isFetching ? "animate-spin" : ""}`} />
              Refresh Status
            </button>
          </div>
        </div>

        {/* Diagnostic Metadata Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 text-xs">
          <div className="bg-slate-950/60 p-3 rounded border border-slate-800/80">
            <span className="text-slate-500 block mb-1">Dedicated Chrome Profile</span>
            <code className="text-slate-300 break-all text-[11px]">
              {session?.profile_dir || "C:\\Users\\astra\\AppData\\Local\\AttendPlan\\chrome-profile"}
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
              {session?.current_url || "No active portal tab detected"}
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
              {launchMutation.isPending ? "Launching Dedicated Browser..." : "Launch Dedicated Chrome"}
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

          {state !== "DISCONNECTED" && state !== "AUTHENTICATED" && (
            <button
              onClick={() => loginMutation.mutate()}
              disabled={loginMutation.isPending}
              className="px-3.5 py-1.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-medium text-xs rounded border border-indigo-400/50 inline-flex items-center gap-1.5 cursor-pointer shadow-md transition-all"
            >
              <KeyRound className="w-3.5 h-3.5" />
              {loginMutation.isPending ? "Automating Login..." : "Run Automated Keycloak Login"}
            </button>
          )}

          {onOpenAuthModal && (
            <button
              onClick={onOpenAuthModal}
              className="px-3 py-1.5 bg-slate-800/90 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 inline-flex items-center gap-1.5 cursor-pointer transition-colors"
              title="Configure Student Mobile Identity and Windows TOTP Vault"
            >
              <KeyRound className="w-3.5 h-3.5 text-indigo-400" />
              Auth & Vault Settings
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

      {/* Subtab Navigation */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveSubTab("sync")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md inline-flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeSubTab === "sync"
              ? "bg-indigo-600 text-white"
              : "bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          Live Synchronization (Gates 2, 3 & 4)
        </button>
        <button
          onClick={() => setActiveSubTab("planner")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md inline-flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeSubTab === "planner"
              ? "bg-indigo-600 text-white"
              : "bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          }`}
        >
          <ListChecks className="w-3.5 h-3.5" />
          Historical Sync Planner (Gate 6)
        </button>
        <button
          onClick={() => setActiveSubTab("discovery")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-md inline-flex items-center gap-1.5 transition-colors cursor-pointer ${
            activeSubTab === "discovery"
              ? "bg-indigo-600 text-white"
              : "bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          }`}
        >
          <Compass className="w-3.5 h-3.5" />
          DOM Discovery & Verification (F2-A)
        </button>
      </div>

      {/* Tab 1: Live Synchronization */}
      {activeSubTab === "sync" && (
        <div className="space-y-6">
          {/* Active / Latest Job State Machine Card */}
          {latestJob && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Sync Job State Machine:
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-semibold border ${getJobBadge(latestJob.state)}`}
                  >
                    {latestJob.state}
                  </span>
                  <span className="text-xs text-slate-400">Step: {latestJob.current_step}</span>
                </div>
                {["DISCOVERING", "SYNCING_SUBJECTS", "SYNCING_DAYWISE", "VALIDATING", "PERSISTING", "RECONCILING"].includes(
                  latestJob.state
                ) && (
                  <button
                    onClick={() => cancelMutation.mutate(latestJob.id)}
                    disabled={cancelMutation.isPending}
                    className="px-2.5 py-1 bg-rose-950/80 hover:bg-rose-900 text-rose-300 text-xs rounded border border-rose-800 inline-flex items-center gap-1.5 cursor-pointer"
                  >
                    <StopCircle className="w-3.5 h-3.5" />
                    Cancel Sync
                  </button>
                )}
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Completed Batches: {latestJob.completed_batches} / {latestJob.progress_total}</span>
                  <span>Failed: {latestJob.failed_batches}</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className="bg-indigo-500 h-full transition-all duration-300"
                    style={{
                      width: `${
                        latestJob.progress_total > 0
                          ? Math.min(100, Math.round((latestJob.progress_current / latestJob.progress_total) * 100))
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>

              {latestJob.safe_diagnostic_message && (
                <p className="text-xs text-slate-300 m-0 bg-slate-950/60 p-2.5 rounded border border-slate-800 font-mono">
                  {latestJob.safe_diagnostic_message}
                </p>
              )}
            </div>
          )}

          {/* Gate 4: Current-Semester Pilot Synchronization */}
          <div className="bg-gradient-to-r from-indigo-950/40 via-slate-900/60 to-purple-950/30 border border-indigo-700/50 rounded-lg p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-indigo-300 m-0 flex items-center gap-2">
                  <Play className="w-4 h-4 text-indigo-400 fill-indigo-400" />
                  Current-Semester Pilot Synchronization (Gate 4)
                </h3>
                <p className="text-xs text-slate-400 mt-1 m-0">
                  Executes a bounded live sync: Subject-Wise Attendance snapshot + 1 month Day-Wise timetable +
                  transactional SQLite persistence + rational reconciliation.
                </p>
              </div>
              <button
                onClick={() => pilotMutation.mutate()}
                disabled={pilotMutation.isPending || state !== "AUTHENTICATED" || !scopeReady}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-xs rounded border border-indigo-500 inline-flex items-center gap-2 cursor-pointer shadow-md transition-colors shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${pilotMutation.isPending ? "animate-spin" : ""}`} />
                {pilotMutation.isPending ? "Running Pilot Sync..." : "Execute Current Semester Pilot Sync"}
              </button>
            </div>

            <label className="block text-sm">Verified semester scope
              <select aria-label="Verified sync semester" className="block bg-slate-950 border border-slate-700 rounded p-2 max-w-full mt-2" defaultValue="" onChange={e => {
                const term = verifiedTermsQuery.data?.terms.find(t=>t.term_key===e.target.value);
                setSyncYear(term?.academic_year ?? "");setSyncSemester(term?.semester_number ?? 0);setSyncClassId(term?.class_identifier ?? "");
              }}><option value="">Choose a discovered semester</option>{verifiedTermsQuery.data?.terms.filter(t=>t.status === "AVAILABLE").map(t=><option key={t.term_key} value={t.term_key}>{t.display_label}</option>)}</select>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Academic Year</label>
                <input
                  type="text"
                  value={syncYear}
                  onChange={(e) => setSyncYear(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Semester</label>
                <input
                  type="number"
                  value={syncSemester}
                  onChange={(e) => setSyncSemester(parseInt(e.target.value, 10) || 1)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Class ID</label>
                <input
                  type="text"
                  value={syncClassId}
                  onChange={(e) => setSyncClassId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Target Pilot Month</label>
                <select
                  value={syncMonth}
                  onChange={(e) => setSyncMonth(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-slate-200"
                >
                  <option value="08">August (08)</option>
                  <option value="09">September (09)</option>
                  <option value="10">October (10)</option>
                  <option value="11">November (11)</option>
                  <option value="12">December (12)</option>
                  <option value="01">January (01)</option>
                  <option value="02">February (02)</option>
                  <option value="03">March (03)</option>
                  <option value="04">April (04)</option>
                  <option value="05">May (05)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Gate 2: Subject-Wise Attendance Live Sync / Preview */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-emerald-300 m-0 flex items-center gap-2">
                  <TableIcon className="w-4 h-4 text-emerald-400" />
                  Subject-Wise Attendance Live Extraction (Gate 2)
                </h3>
                <p className="text-xs text-slate-400 mt-1 m-0">
                  Navigates to <code>subwise_attendace_new.php</code>, discovers dropdown dependencies, extracts course
                  roster, and validates rational percentages.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => syncSubjectMutation.mutate(false)}
                  disabled={syncSubjectMutation.isPending || state !== "AUTHENTICATED" || !scopeReady}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-xs rounded border border-slate-700 inline-flex items-center gap-1.5 cursor-pointer"
                >
                  Preview (Read-Only)
                </button>
                <button
                  onClick={() => syncSubjectMutation.mutate(true)}
                  disabled={syncSubjectMutation.isPending || state !== "AUTHENTICATED" || !scopeReady}
                  className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-xs rounded border border-emerald-600 inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <Database className="w-3.5 h-3.5" />
                  Sync & Persist Snapshot
                </button>
              </div>
            </div>

            {subjectSyncResult && (
              <div className="bg-slate-950/80 p-4 rounded border border-slate-800 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded font-semibold text-[11px] border ${
                        subjectSyncResult.status === "SUCCESS"
                          ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                          : "bg-amber-950 text-amber-300 border-amber-800"
                      }`}
                    >
                      {subjectSyncResult.status}
                    </span>
                    <span className="text-slate-300">
                      Outcome: <code className="text-indigo-300">{subjectSyncResult.outcome}</code>
                    </span>
                  </div>
                  <div className="text-slate-400">
                    Courses: <strong className="text-slate-200">{subjectSyncResult.record_count}</strong> | Aggregate
                    Attendance:{" "}
                    <strong className="text-emerald-400">
                      {subjectSyncResult.aggregate_percentage !== null
                        ? `${subjectSyncResult.aggregate_percentage.toFixed(2)}%`
                        : "N/A"}
                    </strong>
                  </div>
                </div>

                {subjectSyncResult.validation.warnings.length > 0 && (
                  <div className="text-xs text-amber-300 bg-amber-950/40 p-2.5 rounded border border-amber-800/60">
                    <span className="font-semibold block mb-1">Validation Warnings:</span>
                    <ul className="list-disc list-inside space-y-0.5">
                      {subjectSyncResult.validation.warnings.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Gate 3: Day-Wise Attendance Live Sync / Preview */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-amber-300 m-0 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-400" />
                  Day-Wise Timetable Matrix Live Extraction (Gate 3)
                </h3>
                <p className="text-xs text-slate-400 mt-1 m-0">
                  Navigates to <code>myattendance.php</code>, handles horizontal timetable scrolling, parses P/A cells,
                  reconstructs date context, and enables Show Course Name attribution.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => syncDaywiseMutation.mutate(false)}
                  disabled={syncDaywiseMutation.isPending || state !== "AUTHENTICATED" || !scopeReady}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-xs rounded border border-slate-700 inline-flex items-center gap-1.5 cursor-pointer"
                >
                  Preview (Read-Only)
                </button>
                <button
                  onClick={() => syncDaywiseMutation.mutate(true)}
                  disabled={syncDaywiseMutation.isPending || state !== "AUTHENTICATED" || !scopeReady}
                  className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-xs rounded border border-amber-600 inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <Database className="w-3.5 h-3.5" />
                  Sync & Persist Batch
                </button>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                <input
                  type="checkbox"
                  checked={syncShowCourseName}
                  onChange={(e) => setSyncShowCourseName(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-0"
                />
                <span>Enable Show Course Name Toggle</span>
              </label>
            </div>

            {daywiseSyncResult && (
              <div className="bg-slate-950/80 p-4 rounded border border-slate-800 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded font-semibold text-[11px] border ${
                        daywiseSyncResult.status === "SUCCESS"
                          ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                          : "bg-amber-950 text-amber-300 border-amber-800"
                      }`}
                    >
                      {daywiseSyncResult.status}
                    </span>
                    <span className="text-slate-300">
                      Outcome: <code className="text-indigo-300">{daywiseSyncResult.outcome}</code>
                    </span>
                  </div>
                  <div className="text-slate-400">
                    Coverage:{" "}
                    <strong className="text-slate-200">
                      {daywiseSyncResult.coverage_start} to {daywiseSyncResult.coverage_end}
                    </strong>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 block">Total Observations</span>
                    <span className="font-semibold text-slate-200">{daywiseSyncResult.total_observations}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 block">Periods Present</span>
                    <span className="font-semibold text-emerald-400">{daywiseSyncResult.total_present}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 block">Periods Delivered</span>
                    <span className="font-semibold text-slate-200">{daywiseSyncResult.total_delivered}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 block">Unmapped Periods</span>
                    <span className="font-semibold text-amber-400">{daywiseSyncResult.unmapped_count}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Historical Sync Planner */}
      {activeSubTab === "planner" && (
        <div className="space-y-5">
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-200 m-0 flex items-center gap-2">
                  <ListChecks className="w-4 h-4 text-indigo-400" />
                  Historical Multi-Semester Sync Planner (Gate 6)
                </h3>
                <p className="text-xs text-slate-400 mt-1 m-0">
                  Constructs a bounded, pacing-guided plan across discoverable terms. Estimates exact HTTP request counts
                  without recursive brute-forcing.
                </p>
              </div>
              <button
                onClick={() => planMutation.mutate()}
                disabled={planMutation.isPending}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-medium text-xs rounded border border-indigo-500 inline-flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${planMutation.isPending ? "animate-spin" : ""}`} />
                {planMutation.isPending ? "Analyzing Portal History..." : "Generate Multi-Semester Plan"}
              </button>
            </div>

            {historicalPlan && (
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block mb-1">Discovered Academic Years</span>
                    <span className="font-semibold text-indigo-300">
                      {historicalPlan.discovered_academic_years.join(", ")}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block mb-1">Total Terms in Scope</span>
                    <span className="font-semibold text-slate-200">{historicalPlan.total_terms_count} terms</span>
                  </div>
                  <div className="p-3 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block mb-1">Total Estimated Requests</span>
                    <span className="font-semibold text-emerald-400">
                      {historicalPlan.total_estimated_requests} portal interactions
                    </span>
                  </div>
                </div>

                <div className="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded text-xs text-indigo-200">
                  <strong className="block mb-1">Pacing & Safety Guidance:</strong>
                  {historicalPlan.pacing_guidance}
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="py-2 px-3 font-semibold">Year</th>
                        <th className="py-2 px-3 font-semibold">Semester</th>
                        <th className="py-2 px-3 font-semibold">Candidate Months</th>
                        <th className="py-2 px-3 font-semibold">Existing Batches</th>
                        <th className="py-2 px-3 font-semibold">Est. Requests</th>
                        <th className="py-2 px-3 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {historicalPlan.terms.map((t, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/40">
                          <td className="py-2.5 px-3 font-mono text-slate-300">{t.academic_year}</td>
                          <td className="py-2.5 px-3 text-slate-200 font-semibold">Semester {t.semester}</td>
                          <td className="py-2.5 px-3 text-slate-400">{t.candidate_month_labels.join(", ")}</td>
                          <td className="py-2.5 px-3 text-slate-300">{t.existing_batches_count} batches</td>
                          <td className="py-2.5 px-3 text-indigo-400 font-semibold">{t.estimated_requests} reqs</td>
                          <td className="py-2.5 px-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                              READY FOR SEQUENTIAL SYNC
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: DOM Discovery & Verification */}
      {activeSubTab === "discovery" && (
        <div className="space-y-4">
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
      )}
    </div>
  );
};
