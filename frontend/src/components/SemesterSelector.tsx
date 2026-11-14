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
    <div className="semester-selector flex flex-col md:flex-row items-start md:items-center justify-between gap-3 w-full">
      {/* Term Title & Class */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="p-2 bg-indigo-950/60 border border-indigo-800/60 rounded-lg text-indigo-400 flex-shrink-0">
          <Calendar className="w-5 h-5" />
        </div>
        <div className="min-w-0">
          <span className="text-[11px] uppercase font-semibold tracking-wider text-slate-400 block">
            Academic Term
          </span>
          <div className="flex flex-wrap items-center gap-2 mt-0.5">
            <span className="text-sm font-bold text-slate-100 whitespace-nowrap">
              AY {selectedTerm.academic_year} &bull; Semester {selectedTerm.semester_number}
            </span>
            {selectedTerm.class_identifier && (
              <span className="text-[11px] text-slate-300 font-mono bg-slate-800 px-2 py-0.5 rounded border border-slate-700/60 truncate max-w-[200px]" title={selectedTerm.class_identifier}>
                {selectedTerm.class_identifier}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Aggregate Badge & Dropdown */}
      <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
        {selectedTerm.overall_percentage !== null ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs">
            {selectedTerm.overall_status === "SAFE" ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
            )}
            <span className="text-slate-400 font-medium">Term:</span>
            <span
              className={`font-mono font-bold ${
                selectedTerm.overall_status === "SAFE" ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {selectedTerm.overall_percentage.toFixed(2)}%
            </span>
            <span className="text-slate-400 text-[11px]">
              ({selectedTerm.total_attended}/{selectedTerm.total_delivered})
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-400">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            <span>Unrecorded Term</span>
          </div>
        )}

        <div className="relative">
          <select
            aria-label="Saved semester"
            value={selectedTerm.id}
            onChange={(e) => onSelectTerm(e.target.value)}
            className="appearance-none bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-semibold py-1.5 pl-3 pr-8 rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer shadow-sm"
          >
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                Sem {t.semester_number} ({t.academic_year}) — {t.total_courses} courses
              </option>
            ))}
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>
    </div>
  );
};
