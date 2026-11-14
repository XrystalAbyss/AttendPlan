import React, { useState } from "react";
import { QueryClient, QueryClientProvider, useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Shield } from "lucide-react";

import { WorkspaceNav, type WorkspaceTab, normalizeTab } from "./components/WorkspaceNav";
import { HomeView } from "./components/HomeView";
import { AttendanceView } from "./components/AttendanceView";
import { PerformanceView } from "./components/PerformanceView";
import { SettingsView } from "./components/SettingsView";
import { FirstRunOnboarding } from "./components/FirstRunOnboarding";
import { Header } from "./components/Header";
import { ProvenanceBanner } from "./components/ProvenanceBanner";
import { WhatIfSimulator } from "./components/WhatIfSimulator";
import { AttendanceExplorer } from "./components/AttendanceExplorer";
import { AuthenticationSettingsModal } from "./components/AuthenticationSettingsModal";

import {
  API_BASE,
  fetchAcademicTerms,
  fetchHealth,
  fetchTermAttendance,
} from "./api/attendance";
import type { CourseRecord } from "./types/attendance";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 60_000, // 1 minute fresh cache across tab switches
    },
  },
});

const AttendanceDashboard: React.FC = () => {
  const [detailCourse, setDetailCourse] = useState<CourseRecord | null>(null);
  const [targetPercentage, setTargetPercentage] = useState<number>(75);
  const [selectedTermId, setSelectedTermId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("home");
  const [selectedCourseForSimulation, setSelectedCourseForSimulation] = useState<CourseRecord | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);

  const handleExitApp = async () => {
    if (window.confirm("Exit AttendPlan? This will stop the local background server process.")) {
      try {
        await fetch(`${API_BASE}/api/v1/startup/shutdown`, { method: "POST" });
        alert("AttendPlan server has stopped. You can safely close this browser tab.");
      } catch {
        alert("AttendPlan server shutdown initiated.");
      }
    }
  };

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

  // 4. Startup & Session Status
  const startupStatusQuery = useQuery({
    queryKey: ["startup-status"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/startup/status`);
      if (!res.ok) return null;
      return res.json();
    },
    refetchInterval: 15000,
  });

  // Refresh Mutation
  const refreshMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/startup/refresh-current`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed to refresh attendance");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });

  const termAttendance = attendanceQuery.data;
  const isBackendHealthy = !!healthQuery.data && healthQuery.data.status === "healthy";
  const normalizedTab = normalizeTab(activeTab);

  return (
    <div className="attendplan-shell min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
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
        academicYear={termAttendance?.academic_year ?? "—"}
        semester={termAttendance?.semester ?? null}
        className={termAttendance?.class_name ?? (terms.length > 0 ? "Academic Roster" : "AttendPlan")}
        targetPercentage={targetPercentage}
        onTargetChange={setTargetPercentage}
        isBackendHealthy={isBackendHealthy}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onExit={handleExitApp}
      />

      {/* Authentication and Vault Settings Modal */}
      <AuthenticationSettingsModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onLoginSuccess={() => {
          queryClient.invalidateQueries();
        }}
      />

      {/* Main Workspace Area */}
      <main id="main-content" className="workspace-main flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Workspace Intro */}
        <div className="workspace-intro">
          <div>
            <p className="eyebrow">Your academic workspace</p>
            <h2>
              {
                {
                  home: "Attendance Overview",
                  attendance: "Attendance & Planning",
                  performance: "Performance",
                  settings: "Settings & Local Vault",
                }[normalizedTab]
              }
            </h2>
            <p>
              {
                {
                  home: "Instant standing, safe bunk margins, and quick class planning.",
                  attendance: "Subject rosters, 75% margins, simulation and attendance trends.",
                  performance: "Internal assessments, continuous evaluations, and midterm marks.",
                  settings: "Private local storage, university session and credential vault.",
                }[normalizedTab]
              }
            </p>
          </div>
          <span className="workspace-context">
            {terms.length} saved {terms.length === 1 ? "semester" : "semesters"}
            <span>Local records &bull; {targetPercentage}% subject target</span>
          </span>
        </div>

        {/* Primary Four-Destination Navigation */}
        <WorkspaceNav activeTab={activeTab} onChange={(tab) => setActiveTab(tab)} />

        {/* Handle Empty State: First-Run Onboarding */}
        {termsQuery.isLoading ? (
          <div className="h-96 flex flex-col items-center justify-center gap-3 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            <p className="text-sm">Loading academic terms from local database...</p>
          </div>
        ) : terms.length === 0 ? (
          <FirstRunOnboarding
            onComplete={() => {
              termsQuery.refetch();
              setActiveTab("home");
            }}
            onOpenAuthModal={() => setIsAuthModalOpen(true)}
          />
        ) : (
          <>
            {/* Tab 1: HOME */}
            {normalizedTab === "home" && (
              <HomeView
                termAttendance={termAttendance}
                terms={terms}
                currentTermId={currentTermId}
                targetPercentage={targetPercentage}
                onNavigate={(tab) => setActiveTab(tab)}
                onRefresh={() => refreshMutation.mutate()}
                isRefreshing={refreshMutation.isPending}
                refreshError={refreshMutation.error ? (refreshMutation.error as Error).message : null}
                lastSyncTime={startupStatusQuery.data?.last_sync_time}
                connectionState={startupStatusQuery.data?.state}
                onOpenCourseSimulation={(course) => setSelectedCourseForSimulation(course)}
                onOpenAuthModal={() => setIsAuthModalOpen(true)}
              />
            )}

            {/* Tab 2: ATTENDANCE */}
            {normalizedTab === "attendance" && (
              <AttendanceView
                terms={terms}
                selectedTermId={currentTermId}
                onSelectTerm={(id) => setSelectedTermId(id)}
                termAttendance={termAttendance}
                isLoading={attendanceQuery.isLoading}
                targetPercentage={targetPercentage}
                onOpenCourseDetail={(course) => setDetailCourse(course)}
                onOpenSimulation={(course) => setSelectedCourseForSimulation(course)}
              />
            )}

            {/* Tab 3: PERFORMANCE */}
            {normalizedTab === "performance" && <PerformanceView />}

            {/* Tab 4: SETTINGS */}
            {normalizedTab === "settings" && (
              <SettingsView
                onOpenAuthModal={() => setIsAuthModalOpen(true)}
                targetPercentage={targetPercentage}
                onTargetChange={setTargetPercentage}
              />
            )}
          </>
        )}

        {/* Course Detail Drawer (if open) */}
        {detailCourse && currentTermId && (
          <AttendanceExplorer
            targetPercentage={targetPercentage}
            key={`${currentTermId}:${detailCourse.code}`}
            termId={currentTermId}
            academicYear={termAttendance?.academic_year ?? ""}
            course={detailCourse}
            onClose={() => setDetailCourse(null)}
          />
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
              AttendPlan Local Architecture &bull; Credentials stay in your local vault &bull; Saved semester records
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
