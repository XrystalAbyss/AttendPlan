import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Filter, Info, Sliders } from "lucide-react";
import { API_BASE } from "../api/attendance";

interface AssessmentItem {
  group: string;
  name: string;
  classification?: string;
  obtained: number | null;
  maximum: number | null;
  percentage?: number | null;
  status: string;
}

interface CourseMarks {
  course_code: string;
  course_name: string | null;
  internal: number | null;
  external: number | null;
  total: number | null;
  maximum: number | null;
  credits: number | null;
  grade: string | null;
  grade_point: number | null;
  result: string | null;
  percentage: number | null;
  assessments?: AssessmentItem[];
}

interface ResultView {
  courses: CourseMarks[];
  sgpa: number | null;
  cgpa: number | null;
  captured_at: string;
  provenance: string;
}

interface PerformanceData {
  terms: { term_key: string; views: Record<string, ResultView>; insights: string[] }[];
  discovered_terms: { term_key: string; label: string; selector_verified: boolean }[];
  note: string;
  live_capture_enabled: boolean;
}

interface ExamScope {
  exam_session: string;
  exam_session_label: string;
  exam_type: string;
  exam_type_label: string;
  division_id: string;
}

interface Preview {
  source_course_count?: number | null;
  approval_id: string;
  term_key: string;
  label: string;
  class_label: string;
  view: string;
  scope: string;
}

async function request<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(
    `${API_BASE}/api/v1/performance/${path}`,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "Performance request failed.");
  return data;
}

export const PerformanceView: React.FC = () => {
  const client = useQueryClient();
  const [key, setKey] = useState("");
  const [view, setView] = useState("marks");
  const [examKey, setExamKey] = useState("");
  const [selectedSemesterFilter, setSelectedSemesterFilter] = useState<string>("ALL");

  const query = useQuery({
    queryKey: ["performance"],
    queryFn: () => request<PerformanceData>("overview"),
  });

  const scopes = useMutation({
    mutationFn: () =>
      request<{ scopes: ExamScope[] }>("discover-scopes", { term_key: key, view: "marks" }),
  });

  const selectedExam = scopes.data?.scopes.find(
    (s) => `${s.exam_session}:${s.exam_type}` === examKey
  );

  const scopeBody = {
    term_key: key,
    view,
    ...(view === "marks" && selectedExam
      ? {
          exam_session: selectedExam.exam_session,
          exam_type: selectedExam.exam_type,
          division_id: selectedExam.division_id,
        }
      : {}),
  };

  const preview = useMutation({
    mutationFn: () => request<Preview>("preview", scopeBody),
  });

  const capture = useMutation({
    mutationFn: () =>
      request("import", { ...scopeBody, approval_id: preview.data?.approval_id }),
    onSuccess: () => {
      preview.reset();
      client.invalidateQueries({ queryKey: ["performance"] });
    },
  });

  const display = (value: string | number | null) => value ?? "—";

  const allTerms = query.data?.terms ?? [];
  const filteredTerms =
    selectedSemesterFilter === "ALL"
      ? allTerms
      : allTerms.filter((t) => t.term_key === selectedSemesterFilter);

  return (
    <section className="performance-view space-y-6 text-slate-200">
      {/* 1. Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-slate-900/90 border border-slate-800 rounded-xl shadow-sm">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-100 m-0">
            Internal Assessments &amp; Continuous Evaluation
          </h2>
          <p className="text-xs text-slate-400 mt-1 m-0">
            Archived continuous evaluation assessments across 5 academic terms. Preserves authentic university scores.
          </p>
        </div>

        {/* Semester Filter Pills */}
        {allTerms.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-800/80 border border-slate-700/80 rounded-lg text-xs">
            <span className="text-slate-400 px-2 flex items-center gap-1 text-[11px] font-medium">
              <Filter className="w-3 h-3" /> Filter:
            </span>
            <button
              onClick={() => setSelectedSemesterFilter("ALL")}
              className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                selectedSemesterFilter === "ALL"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Semesters ({allTerms.length})
            </button>
            {allTerms.map((t) => {
              const label =
                query.data?.discovered_terms.find((d) => d.term_key === t.term_key)?.label ??
                t.term_key;
              const shortLabel = label.split(" (")[0] || label;
              return (
                <button
                  key={t.term_key}
                  onClick={() => setSelectedSemesterFilter(t.term_key)}
                  className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                    selectedSemesterFilter === t.term_key
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {shortLabel}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {query.isPending && (
        <div className="p-8 text-center text-slate-400 text-sm">
          Loading archived academic records...
        </div>
      )}

      {query.error && <p role="alert" className="text-rose-400 text-sm">{query.error.message}</p>}

      {query.data?.terms.length === 0 && (
        <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-xl space-y-2">
          <p className="text-sm font-medium text-slate-300 m-0">
            No marks or semester results have been imported. Attendance records are separate.
          </p>
          <p className="text-xs text-slate-400 m-0">
            Use the discovery flow below if you wish to review available university examination scopes.
          </p>
        </div>
      )}

      {/* 2. Semester Progression Summary Table */}
      {allTerms.length > 0 && (
        <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-xl space-y-3 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <caption className="text-left font-semibold text-slate-300 py-1.5 text-xs">
                Semester progression — portal-reported GPA
              </caption>
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th scope="col" className="text-left py-2 font-medium">Semester</th>
                  <th scope="col" className="text-center py-2 font-medium">Source view</th>
                  <th scope="col" className="text-center py-2 font-medium">SGPA</th>
                  <th scope="col" className="text-center py-2 font-medium">CGPA</th>
                </tr>
              </thead>
              <tbody>
                {allTerms.flatMap((t) =>
                  Object.entries(t.views).map(([name, result]) => (
                    <tr
                      key={`${t.term_key}-${name}`}
                      className="border-b border-slate-800/40 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-2.5 font-medium text-slate-200">
                        {query.data?.discovered_terms.find((d) => d.term_key === t.term_key)?.label ??
                          t.term_key}
                      </td>
                      <td className="text-center text-slate-400 font-mono text-[11px]">{name}</td>
                      <td className="text-center font-mono text-slate-400">{display(result.sgpa)}</td>
                      <td className="text-center font-mono text-slate-400">{display(result.cgpa)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. Detailed Course Performance Breakdown Cards per Semester */}
      <div className="space-y-5">
        {filteredTerms.map((t) => {
          const semLabel =
            query.data?.discovered_terms.find((d) => d.term_key === t.term_key)?.label ??
            t.term_key;
          const isSemester5 =
            t.term_key.includes("s5") || semLabel.includes("Sem 5") || semLabel.includes("Semester 5");

          return (
            <article
              className="border border-slate-800 rounded-xl bg-slate-900/90 p-5 space-y-4 shadow-sm"
              key={t.term_key}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-100 m-0">{semLabel}</h3>
                {isSemester5 && (
                  <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 inline-flex items-center gap-1 shadow-sm">
                    <Info className="w-3 h-3" /> Continuous Evaluation in Progress (4 Subjects Reported)
                  </span>
                )}
              </div>

              {/* Analytical insights */}
              {t.insights.length > 0 && (
                <div className="space-y-1.5 p-3 bg-slate-800/40 border border-slate-700/50 rounded-lg text-xs">
                  {t.insights.map((insight, index) => {
                    const isDeactivatedNote =
                      insight.includes("deactivated by COE Office") || insight.includes("WITHHELD");
                    return (
                      <p
                        key={index}
                        className={`m-0 leading-relaxed ${
                          isDeactivatedNote
                            ? "text-slate-400 text-[11px] italic"
                            : "text-indigo-200"
                        }`}
                      >
                        {isDeactivatedNote
                          ? "University report card portal route is currently deactivated by COE Office."
                          : insight}
                      </p>
                    );
                  })}
                </div>
              )}

              {/* Course Assessment Tables */}
              {Object.entries(t.views).map(([name, result]) => (
                <div key={name} className="overflow-x-auto space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-mono text-[11px]">
                      View: {name} &bull; {result.courses.length} courses
                    </span>
                    <p className="text-xs text-slate-400 m-0">
                      Captured {new Date(result.captured_at).toLocaleDateString()} &bull; {result.provenance}
                    </p>
                  </div>

                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 bg-slate-850/50">
                        {["Course", "Internal", "External", "Total", "Maximum", "Credits", "Grade", "Grade point", "Result", "Assessments"].map((h) => (
                          <th scope="col" className="text-left p-2.5 font-semibold text-slate-300" key={h}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.courses.map((c) => (
                        <tr
                          key={c.course_code}
                          className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                        >
                          <td className="p-2.5 font-medium text-slate-200 max-w-xs">
                            <span className="font-mono text-indigo-300 font-bold block">{c.course_code}</span>
                            <span className="text-[11px] text-slate-400 line-clamp-1">{c.course_name}</span>
                          </td>
                          {[c.internal, c.external, c.total, c.maximum, c.credits, c.grade, c.grade_point, c.result].map((value, i) => (
                            <td className="p-2.5 font-mono text-slate-300" key={i}>
                              {display(value)}
                            </td>
                          ))}
                          <td className="p-2.5">
                            {c.assessments && c.assessments.length > 0 ? (
                              <details className="group">
                                <summary className="cursor-pointer text-indigo-400 hover:text-indigo-300 font-medium text-[11px] list-none inline-flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-indigo-500 rounded px-1">
                                  <span>Assessment breakdown ({c.assessments.length})</span>
                                  <ChevronDown className="w-3 h-3 group-open:rotate-180 transition-transform" />
                                </summary>
                                <div className="mt-2 p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5 min-w-[280px] text-[11px] shadow-sm">
                                  {c.assessments.map((a, i) => (
                                    <div key={i} className="flex items-center justify-between gap-3 text-slate-300">
                                      <span className="truncate max-w-[150px]" title={`${a.group} · ${a.name}`}>
                                        {a.name}
                                      </span>
                                      <div className="flex items-center gap-1.5 flex-shrink-0 font-mono">
                                        <span className="font-bold text-slate-200">
                                          {display(a.obtained)}/{display(a.maximum)}
                                        </span>
                                        <span
                                          className={`text-[9px] px-1.5 py-0.5 rounded font-sans font-semibold ${
                                            a.status === "MASKED_BY_PORTAL"
                                              ? "bg-amber-950 text-amber-300 border border-amber-800"
                                              : a.status === "REPORTED"
                                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                              : "bg-slate-800 text-slate-400"
                                          }`}
                                        >
                                          {a.status}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </details>
                            ) : (
                              <span className="text-slate-500 font-mono">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </article>
          );
        })}
      </div>

      <p className="text-xs text-slate-500 pt-2">{query.data?.note}</p>

      {/* 4. Advanced / Developer Discovery & Scopes Disclosure (Preserves tests) */}
      <details open={allTerms.length === 0} className="border border-slate-800 rounded-xl bg-slate-900/60 p-4 space-y-3 text-xs">
        <summary className="cursor-pointer font-medium text-slate-400 hover:text-slate-200 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-slate-400" />
            Advanced: Raw Source Scope &amp; Discovery Controls
          </span>
          <span className="text-[11px] text-slate-500">Developer / Pilot tools</span>
        </summary>

        <div className="pt-3 space-y-3 border-t border-slate-800 text-slate-300">
          <p className="text-xs text-slate-400">
            Use your existing login setup privately, then discover terms in Historical Attendance. Preview one semester and one results view before approving an import.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2">
              Semester
              <select
                aria-label="Performance semester"
                className="bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-200 focus-visible:ring-2 focus-visible:ring-indigo-500"
                value={key}
                onChange={(e) => {
                  setKey(e.target.value);
                  preview.reset();
                  scopes.reset();
                  setExamKey("");
                }}
              >
                <option value="">Select a discovered semester</option>
                {query.data?.discovered_terms
                  .filter((t) => t.selector_verified)
                  .map((t, idx) => (
                    <option key={`${t.term_key}-${idx}`} value={t.term_key}>
                      {t.label}
                    </option>
                  ))}
              </select>
            </label>

            <label className="flex items-center gap-2">
              View
              <select
                aria-label="Performance view"
                className="bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-200 focus-visible:ring-2 focus-visible:ring-indigo-500"
                value={view}
                onChange={(e) => {
                  setView(e.target.value);
                  preview.reset();
                  scopes.reset();
                  setExamKey("");
                }}
              >
                <option value="marks">Subject marks</option>
                <option value="results">Semester results</option>
              </select>
            </label>

            {view === "marks" && (
              <div className="flex items-center gap-2">
                <button
                  className="border border-slate-700 rounded px-2.5 py-1 text-xs hover:bg-slate-800 disabled:opacity-40 cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500"
                  disabled={!key || scopes.isPending || capture.isPending}
                  onClick={() => {
                    preview.reset();
                    setExamKey("");
                    scopes.mutate();
                  }}
                >
                  Discover exam options
                </button>
                <select
                  aria-label="Performance exam scope"
                  className="bg-slate-900 border border-slate-700 rounded p-1.5 text-xs text-slate-200 focus-visible:ring-2 focus-visible:ring-indigo-500"
                  value={examKey}
                  onChange={(e) => {
                    setExamKey(e.target.value);
                    preview.reset();
                  }}
                >
                  <option value="">Select a verified exam session and type</option>
                  {scopes.data?.scopes.map((s) => (
                    <option key={`${s.exam_session}:${s.exam_type}`} value={`${s.exam_session}:${s.exam_type}`}>
                      {s.exam_session_label} · {s.exam_type_label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              className="border border-slate-700 rounded px-3 py-1 text-xs hover:bg-slate-800 disabled:opacity-40 cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500"
              disabled={!key || (view === "marks" && !selectedExam) || preview.isPending || capture.isPending}
              onClick={() => preview.mutate()}
            >
              Preview performance scope
            </button>

            {view === "results" && preview.data && (
              <button
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded px-3 py-1 text-xs font-semibold cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500"
                disabled={!query.data?.live_capture_enabled || capture.isPending}
                onClick={() => capture.mutate()}
              >
                Approve this performance import
              </button>
            )}
          </div>

          {!query.data?.live_capture_enabled && (
            <p className="text-xs text-slate-400">
              Live performance imports are disabled in this view. Archived records are read-only.
            </p>
          )}

          {preview.data && (
            <div className="p-3 bg-slate-800/80 border border-slate-700 rounded text-xs space-y-1">
              <p className="font-semibold text-slate-200 m-0">Preview Scope Approval</p>
              <p className="text-slate-300 m-0">
                Term: {preview.data.label} &bull; View: {preview.data.view}
              </p>
              <p className="text-slate-200 font-mono m-0">{preview.data.scope}</p>
            </div>
          )}
        </div>
      </details>
    </section>
  );
};
