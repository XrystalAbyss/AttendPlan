import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  AlertTriangle,
  RotateCcw,
  Check,
  X,
  Plus,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { API_BASE, fetchTermCalendars, updateTermCalendar, resetTermCalendar } from "../api/attendance";
import type { TermCalendarConfig } from "../types/attendance";

export { request };

interface PlannedTerm {
  term_key: string;
  year: string;
  semester: number;
  class_id?: string | null;
  class_label?: string | null;
  months: string[];
  calendar_source?: string;
  confidence_status?: string;
  start_date?: string | null;
  end_date?: string | null;
  excluded_months?: string[];
  approved_exceptional_months?: string[];
}

interface ScopeResult {
  term_key: string;
  scope?: string;
  month?: string;
  outcome: string;
  reason?: string;
  code?: string;
  courses?: number;
  period_records?: number;
  delivered?: number;
}

interface CoverageMetrics {
  total_planned_months: number;
  saved_months_count: number;
  empty_months_count: number;
  outside_calendar_count: number;
  unverified_months_count: number;
  processing_status: string;
  coverage_verdict: string;
}

interface Archive {
  id?: string;
  state: string;
  step?: string;
  completed: number;
  total: number;
  coverage_metrics?: CoverageMetrics;
  details: {
    terms?: PlannedTerm[];
    results?: ScopeResult[];
    cancel_requested?: boolean;
  };
}

async function request(path: string, body?: object): Promise<Archive> {
  const response = await fetch(`${API_BASE}/api/v1/attendance-archive/${path}`, {
    method: body !== undefined ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "Attendance sync unavailable");
  return data;
}

export function ArchiveSync() {
  const client = useQueryClient();
  const [editingTermKey, setEditingTermKey] = useState<string | null>(null);
  const [candidateMonthsInput, setCandidateMonthsInput] = useState<string[]>([]);
  const [excludedMonthsInput, setExcludedMonthsInput] = useState<string[]>([]);
  const [newMonthStr, setNewMonthStr] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["attendance-archive"],
    queryFn: () => request("status"),
    refetchInterval: 3000,
  });

  const calendarsQuery = useQuery({
    queryKey: ["term-calendars"],
    queryFn: fetchTermCalendars,
  });

  const plan = useMutation({
    mutationFn: () => request("plan", {}),
    onSuccess: (data) => {
      client.setQueryData(["attendance-archive"], data);
      client.invalidateQueries({ queryKey: ["term-calendars"] });
    },
  });

  const start = useMutation({
    mutationFn: () => request("start", { plan_id: query.data?.id, approved: true }),
    onSuccess: () => client.invalidateQueries(),
  });

  const resume = useMutation({
    mutationFn: () => request("resume", { plan_id: query.data?.id, approved: true }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["attendance-archive"] }),
  });

  const cancel = useMutation({
    mutationFn: () => request("cancel", {}),
  });

  const updateCalendarMut = useMutation({
    mutationFn: ({ termKey, payload }: { termKey: string; payload: Partial<TermCalendarConfig> }) =>
      updateTermCalendar(termKey, payload),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["term-calendars"] });
      setEditingTermKey(null);
      plan.mutate();
    },
    onError: (err: Error) => setEditError(err.message),
  });

  const resetCalendarMut = useMutation({
    mutationFn: (termKey: string) => resetTermCalendar(termKey),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["term-calendars"] });
      setEditingTermKey(null);
      plan.mutate();
    },
  });

  useEffect(() => {
    if (query.data?.completed) {
      for (const key of [
        "terms",
        "academic-terms-historical",
        "term-attendance",
        "monthly-analytics",
        "weekday-analytics",
        "subject-analytics",
        "period-ledger",
        "historical-terms",
        "reconciliation",
        "academic-history",
      ]) {
        client.invalidateQueries({ queryKey: [key] });
      }
    }
  }, [query.data?.completed, client]);

  const state = query.data?.state ?? "IDLE";
  const active = ["APPROVED", "CONNECTING", "SYNCING"].includes(state);
  const completed = state.startsWith("COMPLETED");
  const plannedTerms = query.data?.details?.terms ?? [];
  const results = query.data?.details?.results ?? [];
  const metrics = query.data?.coverage_metrics;

  const calendarsMap = new Map<string, TermCalendarConfig>();
  for (const c of calendarsQuery.data?.calendars ?? []) {
    calendarsMap.set(c.term_key, c);
    calendarsMap.set(`${c.academic_year}-S${c.semester_number}`, c);
    if (c.class_identifier) {
      calendarsMap.set(`${c.academic_year}_s${c.semester_number}_${c.class_identifier}`, c);
    }
  }

  const handleOpenEdit = (term: PlannedTerm) => {
    const cal = calendarsMap.get(term.term_key);
    setEditingTermKey(term.term_key);
    setCandidateMonthsInput(cal ? [...cal.candidate_months] : [...term.months]);
    setExcludedMonthsInput(cal ? [...cal.excluded_months] : term.excluded_months ?? []);
    setNewMonthStr("");
    setEditError(null);
  };

  const handleAddMonth = () => {
    const trimmed = newMonthStr.trim();
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(trimmed)) {
      setEditError("Month must be in YYYY-MM format (e.g. 2025-08)");
      return;
    }
    if (candidateMonthsInput.includes(trimmed)) {
      setEditError("Month is already in candidate list");
      return;
    }
    setCandidateMonthsInput([...candidateMonthsInput, trimmed].sort());
    setExcludedMonthsInput(excludedMonthsInput.filter((m) => m !== trimmed));
    setNewMonthStr("");
    setEditError(null);
  };

  const handleRemoveMonth = (month: string) => {
    setCandidateMonthsInput(candidateMonthsInput.filter((m) => m !== month));
    if (!excludedMonthsInput.includes(month)) {
      setExcludedMonthsInput([...excludedMonthsInput, month].sort());
    }
  };

  const handleRestoreMonth = (month: string) => {
    setExcludedMonthsInput(excludedMonthsInput.filter((m) => m !== month));
    if (!candidateMonthsInput.includes(month)) {
      setCandidateMonthsInput([...candidateMonthsInput, month].sort());
    }
  };

  const handleSaveCalendar = (termKey: string) => {
    updateCalendarMut.mutate({
      termKey,
      payload: {
        candidate_months: candidateMonthsInput,
        excluded_months: excludedMonthsInput,
      },
    });
  };

  return (
    <section className="border border-slate-700 rounded-lg bg-slate-900 p-4 space-y-4 text-slate-200" aria-label="Save semester and month attendance">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-semibold text-base flex items-center gap-2">
            <Calendar size={18} className="text-indigo-400" />
            Calendar-Aware Multi-Semester Historical Archive
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Read verified semesters and teaching period calendar months into local storage.
            Odd semesters default to Autumn (Aug–Nov); even semesters default to Spring (Jan–May).
            Out-of-window months (June/July/Dec) are not automatically scanned. Empty months are never counted as absence.
          </p>
        </div>
        {metrics && (
          <div className="text-right text-xs">
            <span
              className={`inline-block px-2 py-0.5 rounded font-mono font-semibold ${
                metrics.coverage_verdict === "ACADEMIC_SOURCE_COVERAGE_COMPLETE"
                  ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                  : "bg-amber-950 text-amber-300 border border-amber-800"
              }`}
            >
              {metrics.coverage_verdict === "ACADEMIC_SOURCE_COVERAGE_COMPLETE"
                ? "SOURCE COVERAGE COMPLETE"
                : "SOURCE COVERAGE PARTIAL"}
            </span>
          </div>
        )}
      </div>

      {/* Action Controls */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <button
          className="border border-slate-600 rounded px-3 py-1.5 text-xs font-medium hover:bg-slate-800 disabled:opacity-40"
          disabled={active || plan.isPending}
          onClick={() => plan.mutate()}
        >
          {plan.isPending ? "Generating plan..." : "Review calendar sync plan"}
        </button>

        {state === "PREVIEW_READY" && (
          <button
            className="bg-indigo-600 border border-indigo-500 rounded px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
            disabled={start.isPending}
            onClick={() => start.mutate()}
          >
            {start.isPending ? "Starting sync..." : "Save reviewed semesters & months"}
          </button>
        )}

        {active && (
          <button
            className="border border-red-700 bg-red-950/60 text-red-200 rounded px-3 py-1.5 text-xs font-medium hover:bg-red-900/60"
            onClick={() => cancel.mutate()}
          >
            Stop after current report
          </button>
        )}

        {["PAUSED", "ACTION_REQUIRED", "CANCELLED", "STOPPED"].includes(state) && (
          <button
            className="border border-amber-600 bg-amber-950 text-amber-200 rounded px-3 py-1.5 text-xs font-medium hover:bg-amber-900"
            disabled={resume.isPending}
            onClick={() => resume.mutate()}
          >
            {resume.isPending ? "Resuming..." : "Continue remaining approved reports"}
          </button>
        )}

        {completed && (
          <button
            className="border border-slate-600 rounded px-3 py-1.5 text-xs hover:bg-slate-800"
            onClick={() => client.invalidateQueries()}
          >
            Refresh saved views
          </button>
        )}
      </div>

      {/* Progress & State Banner */}
      <div className="bg-slate-950 border border-slate-800 rounded p-3 text-xs flex items-center justify-between">
        <div>
          <span className="font-semibold text-slate-300">{state.replaceAll("_", " ")}</span>
          <span className="text-slate-500 mx-2">·</span>
          <span>
            {query.data?.completed ?? 0} / {query.data?.total ?? 0} bounded requests completed
          </span>
          {query.data?.step && <p className="text-slate-400 mt-1 font-mono">{query.data.step}</p>}
        </div>
        {metrics && (
          <div className="flex gap-4 text-slate-400">
            <div>
              Planned: <strong className="text-slate-200">{metrics.total_planned_months}</strong>
            </div>
            <div>
              Saved: <strong className="text-emerald-400">{metrics.saved_months_count}</strong>
            </div>
            <div>
              Empty: <strong className="text-slate-300">{metrics.empty_months_count}</strong>
            </div>
            <div>
              Outside Window: <strong className="text-slate-500">{metrics.outside_calendar_count}</strong>
            </div>
            {metrics.unverified_months_count > 0 && (
              <div>
                Unverified: <strong className="text-amber-400">{metrics.unverified_months_count}</strong>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Planned Terms & Calendar Controls */}
      {plannedTerms.length > 0 && (
        <div className="space-y-3 pt-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Discovered Academic Semesters & Teaching Windows ({plannedTerms.length})
          </h3>
          <div className="grid gap-2">
            {plannedTerms.map((term) => {
              const cal = calendarsMap.get(term.term_key) ?? calendarsMap.get(`${term.year}-S${term.semester}`);
              const savedMonths = results
                .filter((r) => r.term_key === term.term_key && r.month && ["SUCCESS", "DUPLICATE_SKIPPED"].includes(r.outcome))
                .map((r) => r.month!);
              const emptyMonths = results
                .filter((r) => r.term_key === term.term_key && r.month && r.outcome === "NO_REPORTED_PERIODS")
                .map((r) => r.month!);
              const skippedMonths = results
                .filter((r) => r.term_key === term.term_key && r.month && r.outcome === "OUTSIDE_CALENDAR_WINDOW")
                .map((r) => r.month!);
              const summaryResult = results.find((r) => r.term_key === term.term_key && r.scope === "summary");

              const isEditing = editingTermKey === term.term_key;

              return (
                <div
                  key={term.term_key}
                  className="border border-slate-800 rounded bg-slate-950/70 p-3 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <strong className="text-sm font-semibold text-slate-100">
                        {term.year} · Semester {term.semester}
                      </strong>
                      <span className="text-slate-400">({term.class_label || term.class_id || "Class Default"})</span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-mono font-semibold ${
                          term.confidence_status === "VERIFIED"
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : term.confidence_status === "USER_CUSTOMIZED"
                            ? "bg-indigo-950 text-indigo-300 border border-indigo-800"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {term.confidence_status || "PROVISIONAL"}
                      </span>
                      <span className="text-slate-500 text-[10px]">Source: {term.calendar_source || cal?.source || "DEFAULT"}</span>
                    </div>
                    <button
                      className="border border-slate-700 hover:bg-slate-800 px-2.5 py-1 rounded text-xs flex items-center gap-1.5"
                      onClick={() => (isEditing ? setEditingTermKey(null) : handleOpenEdit(term))}
                    >
                      {isEditing ? (
                        <>
                          <ChevronUp size={12} /> Close
                        </>
                      ) : (
                        <>
                          <ChevronDown size={12} /> Edit Teaching Months
                        </>
                      )}
                    </button>
                  </div>

                  {/* Summary & Months Status */}
                  <div className="flex flex-wrap items-center gap-4 text-slate-400">
                    <div>
                      <span>Subject Summary: </span>
                      {summaryResult ? (
                        <strong className="text-emerald-400">
                          {summaryResult.outcome} ({summaryResult.courses ?? 0} courses)
                        </strong>
                      ) : (
                        <span className="text-slate-500">Scheduled in plan</span>
                      )}
                    </div>
                    <div>
                      <span>Planned Months ({term.months.length}): </span>
                      <span className="font-mono text-slate-200">{term.months.join(", ") || "None"}</span>
                    </div>
                    {savedMonths.length > 0 && (
                      <div>
                        <span>Saved: </span>
                        <span className="text-emerald-400 font-mono">{savedMonths.join(", ")}</span>
                      </div>
                    )}
                    {emptyMonths.length > 0 && (
                      <div>
                        <span>No Classes: </span>
                        <span className="text-slate-400 font-mono">{emptyMonths.join(", ")}</span>
                      </div>
                    )}
                    {skippedMonths.length > 0 && (
                      <div>
                        <span>Skipped (Outside Window): </span>
                        <span className="text-amber-500 font-mono">{skippedMonths.join(", ")}</span>
                      </div>
                    )}
                  </div>

                  {/* Inline Month Editor */}
                  {isEditing && (
                    <div className="mt-3 p-3 border border-indigo-900/60 rounded bg-indigo-950/20 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-indigo-300 flex items-center gap-1.5">
                          <ShieldCheck size={14} /> Customize Teaching Window for {term.year} Sem {term.semester}
                        </span>
                        <button
                          className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1"
                          onClick={() => resetCalendarMut.mutate(term.term_key)}
                          disabled={resetCalendarMut.isPending}
                        >
                          <RotateCcw size={12} /> Reset to Institutional Defaults
                        </button>
                      </div>

                      <div className="space-y-1">
                        <label className="text-[11px] text-slate-400">Candidate Teaching Months</label>
                        <div className="flex flex-wrap gap-1.5">
                          {candidateMonthsInput.map((m) => (
                            <span
                              key={m}
                              className="inline-flex items-center gap-1 bg-slate-800 border border-slate-700 rounded px-2 py-0.5 font-mono text-xs text-slate-200"
                            >
                              {m}
                              <button
                                type="button"
                                className="text-slate-400 hover:text-red-400 ml-1"
                                title="Exclude this month"
                                onClick={() => handleRemoveMonth(m)}
                              >
                                <X size={12} />
                              </button>
                            </span>
                          ))}
                        </div>
                      </div>

                      {excludedMonthsInput.length > 0 && (
                        <div className="space-y-1">
                          <label className="text-[11px] text-slate-400">Excluded Months</label>
                          <div className="flex flex-wrap gap-1.5">
                            {excludedMonthsInput.map((m) => (
                              <span
                                key={m}
                                className="inline-flex items-center gap-1 bg-slate-900 border border-slate-800 rounded px-2 py-0.5 font-mono text-xs text-slate-500 line-through"
                              >
                                {m}
                                <button
                                  type="button"
                                  className="text-slate-400 hover:text-emerald-400 ml-1"
                                  title="Restore month"
                                  onClick={() => handleRestoreMonth(m)}
                                >
                                  <Plus size={12} />
                                </button>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Add Custom Month Input */}
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          placeholder="YYYY-MM (e.g. 2025-12)"
                          value={newMonthStr}
                          onChange={(e) => setNewMonthStr(e.target.value)}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs font-mono text-slate-200 w-44"
                        />
                        <button
                          type="button"
                          className="border border-slate-700 bg-slate-800 hover:bg-slate-700 rounded px-2 py-1 text-xs"
                          onClick={handleAddMonth}
                        >
                          Add Month
                        </button>
                      </div>

                      {editError && <p className="text-red-400 text-xs">{editError}</p>}

                      <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                        <button
                          className="border border-slate-700 px-3 py-1 rounded text-xs hover:bg-slate-800"
                          onClick={() => setEditingTermKey(null)}
                        >
                          Cancel
                        </button>
                        <button
                          className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3 py-1 rounded text-xs flex items-center gap-1.5"
                          disabled={updateCalendarMut.isPending}
                          onClick={() => handleSaveCalendar(term.term_key)}
                        >
                          <Check size={12} /> Save Teaching Months
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Global Error Notice */}
      {(query.error || plan.error || start.error || cancel.error || resume.error) && (
        <div role="alert" className="p-3 bg-red-950/60 border border-red-800 rounded text-red-200 text-xs flex items-center gap-2">
          <AlertTriangle size={14} className="shrink-0" />
          <span>
            {query.error?.message ??
              plan.error?.message ??
              start.error?.message ??
              cancel.error?.message ??
              resume.error?.message}
          </span>
        </div>
      )}
    </section>
  );
}
