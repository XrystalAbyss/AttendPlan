import React, { useState } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { Header } from "./components/Header";
import { ProvenanceBanner } from "./components/ProvenanceBanner";
import { SummaryCards } from "./components/SummaryCards";
import { AttendanceTable } from "./components/AttendanceTable";
import { WhatIfSimulator } from "./components/WhatIfSimulator";
import { SemesterSelector } from "./components/SemesterSelector";
import { AbsenceAnalyticsView } from "./components/AbsenceAnalyticsView";
import { ReconciliationView } from "./components/ReconciliationView";
import { CrossSemesterView } from "./components/CrossSemesterView";
import { PortalDiscoveryView } from "./components/PortalDiscoveryView";
import {
  fetchAcademicHistory,
  fetchAcademicTerms,
  fetchHealth,
  fetchMonthlyAnalytics,
  fetchSubjectAnalytics,
  fetchTermAttendance,
  fetchTermReconciliation,
  fetchTermSnapshots,
  fetchWeekdayAnalytics,
  seedDemoData,
} from "./api/attendance";
import type { CourseRecord } from "./types/attendance";
import {
  Loader2,
  RefreshCw,
  AlertCircle,
  Shield,
  BookOpen,
  BarChart2,
  GitCompare,
  GraduationCap,
  Compass,
  Database,
} from "lucide-react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

type DashboardTab = "roster" | "analytics" | "reconciliation" | "history" | "discovery";

const AttendanceDashboard: React.FC = () => {
  const [targetPercentage, setTargetPercentage] = useState<number>(75);
  const [selectedTermId, setSelectedTermId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DashboardTab>("roster");
  const [selectedCourseForSimulation, setSelectedCourseForSimulation] = useState<CourseRecord | null>(null);

  // 1. Health Query
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 15000,
  });

  // 2. Academic Terms Query
  const termsQuery = useQuery({
    queryKey: ["terms", targetPercentage],
    queryFn: () => fetchAcademicTerms(targetPercentage),
  });

  const terms = termsQuery.data ?? [];
  const currentTermId = selectedTermId ?? (terms.length > 0 ? terms[0].id : null);

  // 3. Term Attendance Query
  const attendanceQuery = useQuery({
    queryKey: ["term-attendance", currentTermId, targetPercentage],
    queryFn: () => (currentTermId ? fetchTermAttendance(currentTermId, targetPercentage) : null),
    enabled: !!currentTermId,
  });

  // 4. Monthly & Weekday Analytics Queries
  const monthlyQuery = useQuery({
    queryKey: ["monthly-analytics", currentTermId],
    queryFn: () => (currentTermId ? fetchMonthlyAnalytics(currentTermId) : []),
    enabled: !!currentTermId && activeTab === "analytics",
  });

  const weekdayQuery = useQuery({
    queryKey: ["weekday-analytics", currentTermId],
    queryFn: () => (currentTermId ? fetchWeekdayAnalytics(currentTermId) : []),
    enabled: !!currentTermId && activeTab === "analytics",
  });

  const subjectAnalyticsQuery = useQuery({
    queryKey: ["subject-analytics", currentTermId, targetPercentage],
    queryFn: () => (currentTermId ? fetchSubjectAnalytics(currentTermId, targetPercentage) : null),
    enabled: !!currentTermId && activeTab === "analytics",
  });

  // 5. Reconciliation & Snapshots Queries
  const reconciliationQuery = useQuery({
    queryKey: ["reconciliation", currentTermId],
    queryFn: () => (currentTermId ? fetchTermReconciliation(currentTermId) : null),
    enabled: !!currentTermId && activeTab === "reconciliation",
  });

  const snapshotsQuery = useQuery({
    queryKey: ["snapshots", currentTermId],
    queryFn: () => (currentTermId ? fetchTermSnapshots(currentTermId) : []),
    enabled: !!currentTermId && activeTab === "reconciliation",
  });

  // 6. Cross-Semester Academic History Query
  const historyQuery = useQuery({
    queryKey: ["academic-history", targetPercentage],
    queryFn: () => fetchAcademicHistory(targetPercentage),
    enabled: activeTab === "history",
  });

  const termAttendance = attendanceQuery.data;
  const isBackendHealthy = !!healthQuery.data && healthQuery.data.status === "healthy";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Provenance Banner */}
      {termAttendance && (
        <ProvenanceBanner
          provenance={termAttendance.provenance as any}
          provenanceLabel={
            termAttendance.provenance === "OFFLINE_SAMPLE_FIXTURE" || termAttendance.provenance === "AUTO_SEED_SAMPLE"
              ? "SAMPLE / HISTORICAL FIXTURE (OFFLINE DATA)"
              : "LOCAL PERSISTED DATA"
          }
          capturedAt={termAttendance.captured_at}
          from_date={null}
          to_date={null}
        />
      )}

      {/* Institutional Header */}
      <Header
        academicYear={termAttendance?.academic_year ?? "2026-2027"}
        semester={termAttendance?.semester ?? 5}
        className={termAttendance?.class_name ?? "B.Tech CSE AIML-Sem 5"}
        targetPercentage={targetPercentage}
        onTargetChange={setTargetPercentage}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main Workspace Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Semester Selector */}
        {terms.length > 0 && (
          <SemesterSelector
            terms={terms}
            selectedTermId={currentTermId}
            onSelectTerm={(id) => setSelectedTermId(id)}
          />
        )}

        {/* Institutional Tab Bar */}
        <div className="flex border-b border-slate-800 text-xs font-medium space-x-1">
          <button
            onClick={() => setActiveTab("roster")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 border-b-2 font-semibold cursor-pointer transition-colors ${
              activeTab === "roster"
                ? "border-indigo-500 text-indigo-400 bg-slate-900/40"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            Course Roster & Planner
          </button>
          <button
            onClick={() => setActiveTab("analytics")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 border-b-2 font-semibold cursor-pointer transition-colors ${
              activeTab === "analytics"
                ? "border-indigo-500 text-indigo-400 bg-slate-900/40"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <BarChart2 className="w-4 h-4" />
            Absence Analytics
          </button>
          <button
            onClick={() => setActiveTab("reconciliation")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 border-b-2 font-semibold cursor-pointer transition-colors ${
              activeTab === "reconciliation"
                ? "border-indigo-500 text-indigo-400 bg-slate-900/40"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <GitCompare className="w-4 h-4" />
            Source Reconciliation
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 border-b-2 font-semibold cursor-pointer transition-colors ${
              activeTab === "history"
                ? "border-indigo-500 text-indigo-400 bg-slate-900/40"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            Academic Career History
          </button>
          <button
            onClick={() => setActiveTab("discovery")}
            className={`inline-flex items-center gap-2 px-4 py-2.5 border-b-2 font-semibold cursor-pointer transition-colors ${
              activeTab === "discovery"
                ? "border-indigo-500 text-indigo-400 bg-slate-900/40"
                : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
            }`}
          >
            <Compass className="w-4 h-4" />
            Portal Discovery (F2-A)
          </button>
        </div>

        {/* Tab 1: Course Roster & Planner */}
        {activeTab === "roster" && (
          <>
            {termsQuery.isLoading ? (
              <div className="h-96 flex flex-col items-center justify-center gap-3 text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
                <p className="text-sm">Loading academic terms from local database...</p>
              </div>
            ) : terms.length === 0 ? (
              <div className="p-8 bg-slate-900/60 border border-slate-800 rounded-lg text-center flex flex-col items-center gap-4 max-w-xl mx-auto my-12">
                <div className="w-12 h-12 rounded-full bg-indigo-950/80 border border-indigo-700 flex items-center justify-center text-indigo-400">
                  <Compass className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100 m-0">No Academic Terms Ingested</h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-md m-0">
                    A newly installed AttendPlan database starts completely empty. Connect to the university portal to discover your terms or load the offline sample dataset.
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
                  <button
                    onClick={() => setActiveTab("discovery")}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded border border-indigo-500 inline-flex items-center gap-1.5 cursor-pointer shadow-sm"
                  >
                    <Compass className="w-4 h-4" />
                    Open Portal Discovery Flow
                  </button>
                  <button
                    onClick={async () => {
                      await seedDemoData();
                      termsQuery.refetch();
                    }}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded border border-slate-700 inline-flex items-center gap-1.5 cursor-pointer"
                  >
                    <Database className="w-3.5 h-3.5 text-indigo-400" />
                    Load Sample Historical Data
                  </button>
                </div>
              </div>
            ) : attendanceQuery.isLoading ? (
              <div className="h-96 flex flex-col items-center justify-center gap-3 text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
                <p className="text-sm">Loading attendance roster from local database...</p>
              </div>
            ) : attendanceQuery.isError ? (
              <div className="p-6 bg-rose-950/30 border border-rose-800/60 rounded-lg text-rose-300 flex flex-col items-center text-center gap-3">
                <AlertCircle className="w-8 h-8 text-rose-400" />
                <h2 className="text-base font-semibold m-0">Backend Connection Error</h2>
                <p className="text-xs text-rose-200 max-w-md m-0">
                  Could not load term attendance from{" "}
                  <code className="text-rose-100 bg-rose-900/60 px-1 py-0.5 rounded">
                    127.0.0.1:8000
                  </code>
                  . Please verify the backend service is running.
                </p>
                <button
                  onClick={() => attendanceQuery.refetch()}
                  className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded bg-rose-900/60 hover:bg-rose-800 border border-rose-700 text-rose-100 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Retry Connection
                </button>
              </div>
            ) : termAttendance ? (
              <>
                <SummaryCards summary={termAttendance.summary} targetPercentage={targetPercentage} />
                <AttendanceTable
                  courses={termAttendance.courses}
                  targetPercentage={targetPercentage}
                  onSelectCourseForSimulation={(course) => setSelectedCourseForSimulation(course)}
                />
              </>
            ) : null}
          </>
        )}

        {/* Tab 2: Absence Analytics */}
        {activeTab === "analytics" && (
          <AbsenceAnalyticsView
            monthly={monthlyQuery.data ?? []}
            weekday={weekdayQuery.data ?? []}
            subjects={subjectAnalyticsQuery.data ?? null}
            isLoading={monthlyQuery.isLoading || weekdayQuery.isLoading || subjectAnalyticsQuery.isLoading}
          />
        )}

        {/* Tab 3: Source Reconciliation & Snapshots */}
        {activeTab === "reconciliation" && (
          <ReconciliationView
            reconciliation={reconciliationQuery.data ?? null}
            snapshots={snapshotsQuery.data ?? []}
            isLoading={reconciliationQuery.isLoading || snapshotsQuery.isLoading}
          />
        )}

        {/* Tab 4: Academic Career History */}
        {activeTab === "history" && (
          <CrossSemesterView
            history={historyQuery.data ?? null}
            isLoading={historyQuery.isLoading}
            onSelectTerm={(termId) => {
              setSelectedTermId(termId);
              setActiveTab("roster");
            }}
          />
        )}

        {/* Tab 5: Portal Discovery (F2-A) */}
        {activeTab === "discovery" && (
          <PortalDiscoveryView onRefreshTerms={() => termsQuery.refetch()} />
        )}
      </main>

      {/* What-If Simulator Drawer */}
      <WhatIfSimulator
        course={selectedCourseForSimulation}
        targetPercentage={targetPercentage}
        onClose={() => setSelectedCourseForSimulation(null)}
      />

      {/* Institutional Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/60 px-6 py-4 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            <span>
              AttendPlan Local Architecture &bull; Zero external cookies or credentials stored &bull; F1 Multi-Semester Engine
            </span>
          </div>
          <div>
            <span>Read-only University ERP Integration &bull; Deterministic 75% Threshold Engine</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AttendanceDashboard />
    </QueryClientProvider>
  );
}
