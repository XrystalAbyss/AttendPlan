import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchHistoricalTerms,
  fetchAcademicTerms,
  discoverHistoricalTerms,
  previewHistoricalImport,
  startHistoricalImport,
  fetchHistoricalImportProgress,
  cancelHistoricalImport,
  fetchTermAttendance,
  fetchTermCoverage,
  fetchMonthlyAnalytics,
  fetchWeekdayAnalytics,
} from "../api/attendance";

import type {
  SyncJobResponse,
} from "../types/attendance";
import {
  Calendar,
  Layers,
  Search,
  DownloadCloud,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Ban,
  Loader2,
  Sparkles,
  Info,
  ShieldCheck,
  BarChart2,
  FileText,
} from "lucide-react";

interface Props {
  targetPercentage: number;
}

export const HistoricalAttendanceView: React.FC<Props> = ({ targetPercentage }) => {
  const queryClient = useQueryClient();
  const [selectedTermKey, setSelectedTermKey] = useState<string | null>(null);
  const [selectedForImport, setSelectedForImport] = useState<string[]>([]);
  const importDaywise = false;
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // 1. Fetch Discovered & Persisted Terms
  const termsQuery = useQuery({
    queryKey: ["historical-terms"],
    queryFn: fetchHistoricalTerms,
  });

  const discoveredTerms = termsQuery.data?.terms ?? [];
  const activeTerm =
    discoveredTerms.find((t) => t.term_key === selectedTermKey) ??
    discoveredTerms.find((t) => t.has_subject_summary) ??
    discoveredTerms[0] ??
    null;

  // 2. Fetch all academic terms to resolve active term DB ID
  const allTermsQuery = useQuery({
    queryKey: ["academic-terms-historical", targetPercentage],
    queryFn: () => fetchAcademicTerms(targetPercentage),
  });

  const dbTerms = allTermsQuery.data ?? [];
  const matchedDbTerm = dbTerms.find(
    (t) =>
      activeTerm &&
      t.academic_year === activeTerm.academic_year &&
      t.semester_number === activeTerm.semester_number &&
      (t.class_identifier === activeTerm.class_identifier || t.class_identifier === activeTerm.class_display_label)
  );
  const currentDbTermId = matchedDbTerm?.id ?? null;

  // 3. Term Attendance Query for Active Term
  const termAttendanceQuery = useQuery({
    queryKey: ["term-attendance-historical", currentDbTermId, targetPercentage],
    queryFn: () => (currentDbTermId ? fetchTermAttendance(currentDbTermId, targetPercentage) : null),
    enabled: !!currentDbTermId && !!activeTerm?.has_subject_summary,
  });

  // 4. Term Coverage Query
  const termCoverageQuery = useQuery({
    queryKey: ["term-coverage", currentDbTermId],
    queryFn: () => (currentDbTermId ? fetchTermCoverage(currentDbTermId) : null),
    enabled: !!currentDbTermId,
  });

  // 5. Monthly & Weekday Analytics Queries
  const termAnalyticsQuery = useQuery({
    queryKey: ["term-monthly-weekday-historical", currentDbTermId],
    queryFn: async () => {
      if (!currentDbTermId || !activeTerm?.has_daywise_data) return { monthly: [], weekday: [] };
      const [m, w] = await Promise.all([
        fetchMonthlyAnalytics(currentDbTermId),
        fetchWeekdayAnalytics(currentDbTermId),
      ]);
      return { monthly: m, weekday: w };
    },
    enabled: !!currentDbTermId && !!activeTerm?.has_daywise_data,
  });


  // 5. Polling Active Sync Job Progress
  const jobProgressQuery = useQuery({
    queryKey: ["historical-import-progress"],
    queryFn: fetchHistoricalImportProgress,
    refetchInterval: (query) => {
      const data = query.state.data as SyncJobResponse | undefined;
      if (!data) return false;
      const activeStates = ["SYNCING_SUBJECTS", "SYNCING_DAYWISE", "PERSISTING", "RECONCILING", "IDLE"];
      return activeStates.includes(data.state) ? 2000 : false;
    },
    enabled: !!activeJobId,
  });

  // Mutations
  const discoverMutation = useMutation({
    mutationFn: () => discoverHistoricalTerms(),
    onSuccess: (data) => {
      setSelectedForImport([]);
      previewMutation.reset();
      queryClient.setQueryData(["historical-terms"], data);
      queryClient.invalidateQueries({ queryKey: ["historical-terms"] });
    },
  });

  const previewMutation = useMutation({
    mutationFn: (keys: string[]) => previewHistoricalImport(keys),
  });

  const importMutation = useMutation({
    mutationFn: ({ keys, daywise }: { keys: string[]; daywise: boolean }) =>
      startHistoricalImport(keys, daywise, undefined, previewMutation.data?.approval_id ?? undefined),
    onSuccess: (job) => {
      setActiveJobId(job.id);
      previewMutation.reset();
      queryClient.invalidateQueries({ queryKey: ["historical-terms"] });
      queryClient.invalidateQueries({ queryKey: ["academic-terms-historical"] });
      queryClient.invalidateQueries({ queryKey: ["historical-import-progress"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: cancelHistoricalImport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["historical-import-progress"] });
      queryClient.invalidateQueries({ queryKey: ["historical-terms"] });
    },
  });

  const handleToggleTermSelect = (key: string) => {
    previewMutation.reset();
    setSelectedForImport((prev) =>
      prev.includes(key) ? [] : [key]
    );
  };

  const coverage = termCoverageQuery.data;
  const attendance = termAttendanceQuery.data;
  const analytics = termAnalyticsQuery.data ?? { monthly: [], weekday: [] };
  const currentJob = jobProgressQuery.data;

  return (
    <div className="space-y-6" data-testid="historical-attendance-view">
      {activeTerm && !activeTerm.has_subject_summary && <div className="p-4 border border-amber-700 rounded text-amber-200 bg-amber-950/30">{activeTerm.display_label} is discovered but has not been imported. Select its checkbox and preview the exact scope before importing; no marks or attendance are being invented for this semester.</div>}
      {/* 1. Header & Live Sync Management Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 bg-indigo-950/60 border border-indigo-800/60 rounded-md text-indigo-400">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-100 m-0">
                  Historical Academic Attendance History
                </h2>
                <p className="text-xs text-slate-400 m-0">
                  One-semester pilot &bull; Verified portal filters &bull; Isolated term catalogs
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => discoverMutation.mutate()}
              disabled={discoverMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition cursor-pointer disabled:opacity-50"
            >
              {discoverMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
              ) : (
                <Search className="w-3.5 h-3.5 text-indigo-400" />
              )}
              Discover Terms
            </button>

            <button
              onClick={() => previewMutation.mutate(selectedForImport)}
              disabled={previewMutation.isPending || selectedForImport.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Preview Import ({selectedForImport.length})
            </button>

            <button
              onClick={() =>
                importMutation.mutate({ keys: selectedForImport, daywise: importDaywise })
              }
              disabled={importMutation.isPending || selectedForImport.length !== 1 || !previewMutation.data?.approval_id}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition cursor-pointer disabled:opacity-50"
            >
              {importMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <DownloadCloud className="w-3.5 h-3.5" />
              )}
              Import Selected Terms
            </button>
          </div>
        </div>

        {/* Sync Job Progress Notification Banner */}
        {currentJob && currentJob.state !== "IDLE" && (
          <div className="mt-4 p-4 rounded-md bg-slate-950 border border-indigo-900/60">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                <span className="text-xs font-semibold text-slate-200">
                  {currentJob.current_step}
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/50">
                  {currentJob.state}
                </span>
              </div>
              <button
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
                className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 font-medium cursor-pointer"
              >
                <Ban className="w-3.5 h-3.5" /> Cancel Sync
              </button>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-indigo-500 h-1.5 transition-all duration-300"
                style={{
                  width: `${
                    currentJob.progress_total > 0
                      ? Math.min(
                          100,
                          Math.round((currentJob.progress_current / currentJob.progress_total) * 100)
                        )
                      : 10
                  }%`,
                }}
              />
            </div>
            {currentJob.safe_diagnostic_message && (
              <p className="text-[11px] text-slate-400 mt-2 m-0">
                {currentJob.safe_diagnostic_message}
              </p>
            )}
          </div>
        )}

        {/* Import Preview Drawer / Box */}
        {previewMutation.data && (
          <div className="mt-4 p-4 rounded-md bg-indigo-950/30 border border-indigo-800/40 text-xs">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-slate-200 m-0 flex items-center gap-2">
                <Info className="w-4 h-4 text-indigo-400" /> Pre-Sync Historical Workload Inspection
              </h4>
              <span className="text-slate-400 font-mono">
                Pacing: ~{previewMutation.data.estimated_pacing_seconds.toFixed(0)}s conservative
              </span>
            </div>
            <p className="text-slate-300 m-0 mb-3">{previewMutation.data.pacing_guidance}</p>
            {previewMutation.data.source_course_count != null && <p className="text-emerald-300">Live source verified: {previewMutation.data.source_course_count} courses. Nothing imported yet.</p>}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px] uppercase">Selected Terms</span>
                <span className="font-mono font-bold text-slate-200 text-sm">
                  {previewMutation.data.total_selected_terms}
                </span>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px] uppercase">Portal Requests</span>
                <span className="font-mono font-bold text-indigo-400 text-sm">
                  {previewMutation.data.total_estimated_requests}
                </span>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px] uppercase">Sequential Mode</span>
                <span className="font-mono font-bold text-emerald-400 text-sm">1 Active Worker</span>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 block text-[10px] uppercase">User Approval</span>
                <span className="font-mono font-bold text-amber-400 text-sm">Required</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. Discovered Terms Selector Bar & Checkbox Inventory */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200 m-0">
              Select Academic Semester ({discoveredTerms.length} Discovered Terms)
            </h3>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={importDaywise}
                disabled
                className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-0"
              />
              <span>Subject-summary pilot only; day-wise requires separate approval</span>
            </label>
          </div>
        </div>

        {discoveredTerms.length === 0 ? (
          <div className="p-8 text-center text-slate-400 border border-dashed border-slate-800 rounded-md">
            <p className="text-xs m-0">
              No historical terms cataloged in local database. Click &ldquo;Discover Terms&rdquo; to query
              the portal selector options.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {discoveredTerms.map((t) => {
              const isSelected = activeTerm?.term_key === t.term_key;
              const isCheckedForImport = selectedForImport.includes(t.term_key);

              return (
                <div
                  key={t.term_key}
                  onClick={() => setSelectedTermKey(t.term_key)}
                  className={`p-3 rounded-md border text-xs cursor-pointer transition-all flex flex-col justify-between ${
                    isSelected
                      ? "bg-indigo-950/40 border-indigo-500 shadow-sm"
                      : "bg-slate-800/40 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-1 mb-2">
                    <div>
                      <div className="font-semibold text-slate-200">{t.display_label}</div>
                      <div className="text-[10px] text-slate-400">{t.academic_year}</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={isCheckedForImport}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => handleToggleTermSelect(t.term_key)}
                      title="Select for bulk historical import"
                      className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-0 cursor-pointer"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-400">Attendance:</span>
                      <span
                        className={`font-mono font-bold ${
                          t.percentage !== null
                            ? t.percentage >= targetPercentage
                              ? "text-emerald-400"
                              : "text-rose-400"
                            : "text-slate-500"
                        }`}
                      >
                        {t.percentage !== null ? `${t.percentage.toFixed(1)}%` : "Unrecorded"}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-slate-500">Coverage:</span>
                      <span
                        className={`font-mono px-1.5 py-0.5 rounded ${
                          t.coverage_state === "COMPLETE_FOR_REQUESTED_SCOPE"
                            ? "bg-emerald-950/70 text-emerald-300 border border-emerald-800/50"
                            : t.coverage_state === "PARTIAL"
                            ? "bg-amber-950/70 text-amber-300 border border-amber-800/50"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {t.coverage_state === "COMPLETE_FOR_REQUESTED_SCOPE"
                          ? "COMPLETE"
                          : t.coverage_state}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 3. Selected Semester Workspace (Summary + Coverage + Roster) */}
      {activeTerm && (
        <div className="space-y-6">
          {/* Historical Safety Notice */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-4 flex items-center gap-3 text-xs">
            <Info className="w-5 h-5 text-indigo-400 flex-shrink-0" />
            <div className="text-slate-300">
              <span className="font-semibold text-slate-200">
                Historical Term Record &bull; {activeTerm.display_label}:
              </span>{" "}
              Past semester records are immutable analytical archives. Invariant: Safe bunk margins
              cannot be retroactively applied or redeemed in completed terms.
            </div>
          </div>

          {/* Metric Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 text-center">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Recorded Attendance
              </span>
              <div className="text-2xl font-mono font-bold text-slate-100 mt-1">
                {activeTerm.attended_sum} / {activeTerm.delivered_sum}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">Delivered Periods</span>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 text-center">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Term Aggregate Percentage
              </span>
              <div
                className={`text-2xl font-mono font-bold mt-1 ${
                  activeTerm.percentage !== null
                    ? activeTerm.percentage >= targetPercentage
                      ? "text-emerald-400"
                      : "text-rose-400"
                    : "text-slate-500"
                }`}
              >
                {activeTerm.percentage !== null
                  ? `${activeTerm.percentage.toFixed(2)}%`
                  : "--"}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">
                Target: {targetPercentage}%
              </span>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 text-center">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Courses Cataloged
              </span>
              <div className="text-2xl font-mono font-bold text-slate-100 mt-1">
                {activeTerm.existing_courses_count}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">Subject Roster Count</span>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 text-center">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block">
                Compliance Status
              </span>
              <div className="mt-1 flex items-center justify-center gap-1.5">
                {activeTerm.percentage !== null ? (
                  activeTerm.percentage >= targetPercentage ? (
                    <span className="text-emerald-400 font-bold flex items-center gap-1 text-sm">
                      <CheckCircle2 className="w-4 h-4" /> SAFE (&ge; {targetPercentage}%)
                    </span>
                  ) : (
                    <span className="text-rose-400 font-bold flex items-center gap-1 text-sm">
                      <AlertTriangle className="w-4 h-4" /> AT RISK (&lt; {targetPercentage}%)
                    </span>
                  )
                ) : (
                  <span className="text-slate-400 text-sm font-medium">NO ATTENDANCE</span>
                )}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">
                Exact Rational Threshold
              </span>
            </div>
          </div>

          {/* 4. Import Coverage & Reconciliation Card */}
          {coverage && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-slate-200 m-0">
                    Data Coverage &amp; Source Provenance
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Reconciliation:</span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      coverage.reconciliation_verdict === "MATCHED"
                        ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        : coverage.reconciliation_verdict === "PARTIAL_COVERAGE"
                        ? "bg-amber-950 text-amber-300 border border-amber-800"
                        : "bg-slate-800 text-slate-400 border border-slate-700"
                    }`}
                  >
                    {coverage.reconciliation_verdict}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div className="bg-slate-800/40 p-3 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[11px]">Subject Summary</span>
                  <span className="font-semibold text-slate-200">
                    {coverage.has_subject_summary ? "Captured" : "Missing"} (
                    {coverage.subject_courses_count} courses)
                  </span>
                </div>

                <div className="bg-slate-800/40 p-3 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[11px]">Calendar Months</span>
                  <span className="font-semibold text-slate-200">
                    {coverage.months_completed.length} / {coverage.candidate_months.length} Completed
                  </span>
                </div>

                <div className="bg-slate-800/40 p-3 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[11px]">Instructional Dates</span>
                  <span className="font-semibold text-slate-200 font-mono">
                    {coverage.unique_instructional_dates} Teaching Days
                  </span>
                </div>

                <div className="bg-slate-800/40 p-3 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[11px]">Period Observations</span>
                  <span className="font-semibold text-slate-200 font-mono">
                    {coverage.mapped_periods} Mapped / {coverage.unmapped_periods} Unmapped
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* 5. Course-Wise Attendance Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-slate-200 m-0">
                  Course Roster &bull; {activeTerm.display_label}
                </h3>
              </div>
              <span className="text-xs text-slate-400">
                {attendance?.courses.length ?? 0} courses cataloged
              </span>
            </div>

            {!attendance || attendance.courses.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                <p className="text-sm m-0">
                  No courses recorded for this semester yet. Click &ldquo;Import Selected Terms&rdquo; to
                  retrieve historical attendance.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="px-4 py-3">Course Code</th>
                      <th className="px-4 py-3">Course Name</th>
                      <th className="px-4 py-3">Faculty</th>
                      <th className="px-4 py-3 text-center">Credits</th>
                      <th className="px-4 py-3 text-center">Attended</th>
                      <th className="px-4 py-3 text-center">Delivered</th>
                      <th className="px-4 py-3 text-center">Missed</th>
                      <th className="px-4 py-3 text-right">Percentage</th>
                      <th className="px-4 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {attendance.courses.map((c) => (
                      <tr key={c.code} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 font-mono font-medium text-indigo-400">
                          {c.code}
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-200">{c.name}</td>
                        <td className="px-4 py-3 text-slate-400">{c.faculty || "Not Listed"}</td>
                        <td className="px-4 py-3 text-center font-mono text-slate-300">
                          {c.credits}
                        </td>
                        <td className="px-4 py-3 text-center font-mono text-slate-200 font-bold">
                          {c.attended}
                        </td>
                        <td className="px-4 py-3 text-center font-mono text-slate-200 font-bold">
                          {c.delivered}
                        </td>
                        <td className="px-4 py-3 text-center font-mono text-rose-400">
                          {Math.max(0, c.delivered - c.attended)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono font-bold">
                          {c.percent !== null ? (
                            <span
                              className={
                                c.percent >= targetPercentage
                                  ? "text-emerald-400"
                                  : "text-rose-400"
                              }
                            >
                              {c.percent.toFixed(2)}%
                            </span>
                          ) : (
                            <span className="text-slate-500">--</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              c.status === "SAFE"
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                                : c.status === "AT_RISK"
                                ? "bg-rose-950 text-rose-300 border border-rose-800/60"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {c.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 6. Monthly & Weekday Absence Patterns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Monthly Breakdown */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
              <div className="flex items-center gap-2 mb-3">
                <Calendar className="w-4 h-4 text-indigo-400" />
                <h4 className="text-sm font-semibold text-slate-200 m-0">
                  Monthly Attendance Distribution
                </h4>
              </div>

              {analytics.monthly.length === 0 ? (
                <div className="p-6 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded">
                  No monthly calendar observations imported for this historical term.
                </div>
              ) : (
                <div className="space-y-2 text-xs">
                  {analytics.monthly.map((m) => (
                    <div
                      key={m.month_label}
                      className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded border border-slate-800"
                    >
                      <span className="font-medium text-slate-200">{m.month_label}</span>
                      <div className="flex items-center gap-3 font-mono">
                        <span className="text-slate-400">
                          {m.attended} / {m.delivered}
                        </span>
                        <span
                          className={`font-bold ${
                            m.attendance_percentage !== null &&
                            m.attendance_percentage >= targetPercentage
                              ? "text-emerald-400"
                              : "text-rose-400"
                          }`}
                        >
                          {m.attendance_percentage !== null
                            ? `${m.attendance_percentage.toFixed(1)}%`
                            : "--"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Weekday Breakdown */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
              <div className="flex items-center gap-2 mb-3">
                <BarChart2 className="w-4 h-4 text-indigo-400" />
                <h4 className="text-sm font-semibold text-slate-200 m-0">
                  Weekday Absence Distribution
                </h4>
              </div>

              {analytics.weekday.length === 0 ? (
                <div className="p-6 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded">
                  No weekday timetable observations imported for this historical term.
                </div>
              ) : (
                <div className="space-y-2 text-xs">
                  {analytics.weekday.map((w) => (
                    <div
                      key={w.weekday_name}
                      className="flex items-center justify-between p-2.5 bg-slate-800/40 rounded border border-slate-800"
                    >
                      <span className="font-medium text-slate-200">{w.weekday_name}</span>
                      <div className="flex items-center gap-3 font-mono">
                        <span className="text-slate-400">
                          {w.attended} / {w.delivered} periods
                        </span>
                        <span className="text-rose-400 font-bold">
                          {w.absence_rate.toFixed(1)}% missed
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
