import type React from "react";
import { AlertCircle, Database } from "lucide-react";
import type { DataProvenance } from "../types/attendance";

interface Props {
  provenance: DataProvenance;
  provenanceLabel: string;
  capturedAt: string;
  from_date?: string | null;
  to_date?: string | null;
}

export const ProvenanceBanner: React.FC<Props> = ({
  provenance,
  provenanceLabel,
  capturedAt,
  from_date,
  to_date,
}) => {
  const isSample = provenance === "SAMPLE_HISTORICAL";

  return (
    <div
      data-testid="provenance-banner"
      className={`border-b px-4 py-2.5 text-xs font-medium flex flex-wrap items-center justify-between gap-3 ${
        isSample
          ? "bg-amber-950/40 border-amber-800/60 text-amber-300"
          : "bg-slate-900 border-slate-800 text-slate-300"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`flex h-2 w-2 rounded-full ${
            isSample ? "bg-amber-400 animate-pulse" : "bg-emerald-400"
          }`}
        />
        <span className="font-semibold tracking-wide uppercase">
          {provenanceLabel}
        </span>
        <span className="text-slate-400">|</span>
        <span className="text-slate-400">
          {from_date && to_date ? `Reporting period: ${from_date} to ${to_date}` : "Reporting dates not supplied"}
        </span>
        <span className="text-slate-500 font-mono text-[10px]">
          (Snapshot: {capturedAt.slice(0, 10)})
        </span>
      </div>

      <div className="flex items-center gap-4 text-slate-400">
        <div className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span>{isSample ? "Sample fixture" : "Saved locally"}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
          <span>Read-only University Data</span>
        </div>
      </div>
    </div>
  );
};
