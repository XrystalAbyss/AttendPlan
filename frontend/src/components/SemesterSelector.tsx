import React from "react";
import type { AcademicTerm } from "../types/attendance";
import { Calendar, ChevronDown, CheckCircle2, AlertTriangle, HelpCircle } from "lucide-react";

interface SemesterSelectorProps {
  terms: AcademicTerm[];
  selectedTermId: string | null;
  onSelectTerm: (termId: string) => void;
}

export const SemesterSelector: React.FC<SemesterSelectorProps> = ({
  terms,
  selectedTermId,
  onSelectTerm,
}) => {
  if (terms.length === 0) {
    return null;
  }

  const selectedTerm = terms.find((t) => t.id === selectedTermId) ?? terms[0];

  return (
    <div className="semester-selector flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 p-3.5 rounded-lg">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-950/60 border border-indigo-800/60 rounded-md text-indigo-400">
          <Calendar className="w-5 h-5" />
        </div>
        <div>
          <span className="text-xs uppercase font-medium tracking-wider text-slate-400 block">
            Academic Term & Roster
          </span>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-sm font-semibold text-slate-100">
              {selectedTerm.academic_year} &bull; Semester {selectedTerm.semester_number}
            </span>
            {selectedTerm.class_identifier && (
              <span className="text-xs text-slate-400 font-mono bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/50">
                {selectedTerm.class_identifier}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto min-w-0">
        {selectedTerm.overall_percentage !== null ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-xs">
            {selectedTerm.overall_status === "SAFE" ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className="text-slate-300">Term Aggregate:</span>
            <span
              className={`font-mono font-bold ${
                selectedTerm.overall_status === "SAFE" ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {selectedTerm.overall_percentage.toFixed(2)}%
            </span>
            <span className="text-slate-400">
              ({selectedTerm.total_attended}/{selectedTerm.total_delivered})
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-400">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            <span>Unrecorded Term</span>
          </div>
        )}

        <div className="relative max-w-full">
          <select
            aria-label="Saved semester"
            value={selectedTerm.id}
            onChange={(e) => onSelectTerm(e.target.value)}
            className="max-w-full appearance-none bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-medium py-1.5 pl-3 pr-8 rounded border border-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
          >
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                {t.academic_year} — Sem {t.semester_number} ({t.total_courses} courses)
              </option>
            ))}
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>
    </div>
  );
};
