import React, { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, CheckCircle2, AlertTriangle, Clock, ShieldAlert } from "lucide-react";
import { API_BASE } from "../api/attendance";

export interface Preferences {
  auto_connect: boolean;
  refresh_approved_scopes: boolean;
  auto_refresh_current_term?: boolean;
  approved_scope_count: number;
  last_sync_time?: string | null;
}

export interface Connection {
  state: string;
  message: string;
  running: boolean;
  refreshed_scopes: number;
  discovered_terms?: number;
  performance?: Record<string, string>;
  last_sync_time?: string | null;
}

async function call<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1/startup/${path}`, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "Background connection is unavailable.");
  return data;
}

function formatSyncTime(isoString?: string | null): string {
  if (!isoString) return "Never";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export const StartupConnection: React.FC = () => {
  const client = useQueryClient();
  const hasTriggeredRef = useRef(false);

  const settings = useQuery({
    queryKey: ["startup-settings"],
    queryFn: () => call<Preferences>("settings"),
    retry: false,
  });

  const status = useQuery({
    queryKey: ["startup-status"],
    queryFn: () => call<Connection>("status"),
    enabled: !!settings.data?.auto_connect || !!settings.data?.auto_refresh_current_term,
    refetchInterval: (query) => (query.state.data as Connection | undefined)?.running ? 1500 : false,
  });

  const connect = useMutation({
    mutationFn: () => call<Connection>("connect", {}),
    onSuccess: (data) => client.setQueryData(["startup-status"], data),
  });

  const refreshCurrent = useMutation({
    mutationFn: () => call<Connection>("refresh-current", {}),
    onSuccess: (data) => client.setQueryData(["startup-status"], data),
  });

  const save = useMutation({
    mutationFn: (value: Preferences) => call<Preferences>("settings", value),
    onSuccess: (data) => client.setQueryData(["startup-settings"], data),
  });

  useEffect(() => {
    if (hasTriggeredRef.current || !settings.data) return;
    if (settings.data.auto_connect || settings.data.auto_refresh_current_term) {
      hasTriggeredRef.current = true;
      connect.mutate();
    }
  }, [settings.data?.auto_connect, settings.data?.auto_refresh_current_term]);

  // Gate B: If manual login is required, poll session status and resume refresh automatically once authenticated
  const sessionStatus = useQuery({
    queryKey: ["portal-session-status"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/portal/session/status`);
      if (!res.ok) return { state: "DISCONNECTED" };
      return res.json();
    },
    enabled: status.data?.state === "ACTION_REQUIRED",
    refetchInterval: status.data?.state === "ACTION_REQUIRED" ? 1000 : false,
  });

  useEffect(() => {
    if (status.data?.state === "ACTION_REQUIRED" && sessionStatus.data?.state === "AUTHENTICATED") {
      refreshCurrent.mutate();
    }
  }, [status.data?.state, sessionStatus.data?.state]);

  useEffect(() => {
    const s = status.data?.state;
    if (s && ["PREVIEW_READY", "SYNC_COMPLETE", "SYNC_PARTIAL", "UP_TO_DATE"].includes(s)) {
      for (const key of [
        "terms",
        "historical-terms",
        "academic-terms-historical",
        "performance",
        "term-attendance",
        "term-attendance-historical",
        "term-coverage",
        "monthly-analytics",
        "weekday-analytics",
        "subject-analytics",
        "reconciliation",
        "academic-history",
      ]) {
        client.invalidateQueries({ queryKey: [key] });
      }
    }
  }, [status.data?.state, client]);

  const state = status.data?.state ?? "IDLE";
  const isRunning = status.data?.running || refreshCurrent.isPending;
  const lastSync = status.data?.last_sync_time ?? settings.data?.last_sync_time;

  const renderBadge = () => {
    if (state === "SYNC_COMPLETE" || state === "UP_TO_DATE") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/70 text-emerald-400 border border-emerald-700/60">
          <CheckCircle2 className="w-3.5 h-3.5" />
          {state === "UP_TO_DATE" ? "Up to date" : "Current semester synchronized"}
        </span>
      );
    }
    if (state === "SYNC_PARTIAL") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/70 text-amber-400 border border-amber-700/60">
          <AlertTriangle className="w-3.5 h-3.5" />
          Partial sync (Summary updated)
        </span>
      );
    }
    if (state === "ACTION_REQUIRED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-950/70 text-orange-400 border border-orange-700/60">
          <ShieldAlert className="w-3.5 h-3.5" />
          Login required
        </span>
      );
    }
    if (state === "SYNC_FAILED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-950/70 text-rose-400 border border-rose-700/60">
          <AlertTriangle className="w-3.5 h-3.5" />
          Sync failed
        </span>
      );
    }
    if (isRunning) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-950/70 text-blue-400 border border-blue-700/60">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          {state.replaceAll("_", " ")}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
        Saved attendance available
      </span>
    );
  };

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-300 mb-5 shadow-sm" aria-label="Background portal connection">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <strong>Saved data stays available</strong>
          {renderBadge()}
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-400 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>Last sync: <strong>{formatSyncTime(lastSync)}</strong></span>
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-xs font-medium text-white transition-colors"
            disabled={isRunning || !settings.data}
            onClick={() => refreshCurrent.mutate()}
          >
            <RefreshCw className={`w-3 h-3 ${isRunning ? "animate-spin" : ""}`} />
            Refresh Current Semester
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-5 mt-3">
        <label className="flex gap-2 items-center cursor-pointer">
          <input
            type="checkbox"
            className="rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
            checked={settings.data?.auto_refresh_current_term ?? false}
            disabled={!settings.data || save.isPending}
            onChange={(e) =>
              settings.data &&
              save.mutate({
                ...settings.data,
                auto_refresh_current_term: e.target.checked,
              })
            }
          />
          Automatic current-semester refresh on opening
        </label>

        <label className="flex gap-2 items-center cursor-pointer">
          <input
            type="checkbox"
            className="rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
            checked={settings.data?.auto_connect ?? false}
            disabled={!settings.data || save.isPending}
            onChange={(e) =>
              settings.data &&
              save.mutate({
                ...settings.data,
                auto_connect: e.target.checked,
              })
            }
          />
          Connect on opening AttendPlan
        </label>

        <label className="flex gap-2 items-center cursor-pointer">
          <input
            type="checkbox"
            className="rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
            checked={settings.data?.refresh_approved_scopes ?? false}
            disabled={!settings.data?.approved_scope_count || save.isPending}
            onChange={(e) =>
              settings.data &&
              save.mutate({
                ...settings.data,
                refresh_approved_scopes: e.target.checked,
              })
            }
          />
          Refresh previously approved scopes
        </label>
      </div>

      <p className="mt-2.5 text-slate-400" role="status">
        {status.data?.message ??
          "Open your saved attendance immediately; portal connection can run in the background using your existing login setup."}
      </p>

      {status.data?.discovered_terms !== undefined && (
        <p className="mt-1 text-xs text-slate-400">{status.data.discovered_terms} semester/class combinations discovered.</p>
      )}

      {status.data?.performance && (
        <p className="text-xs text-slate-400">
          Marks: {status.data.performance.marks === "MENU_NOT_FOUND" ? "menu not found in this portal view" : "menu found; format needs verification"}. Results: {status.data.performance.results === "MENU_NOT_FOUND" ? "menu not found in this portal view" : "menu found; format needs verification"}.
        </p>
      )}

      {!settings.data?.approved_scope_count && (
        <p className="text-xs text-amber-300 mt-1">
          The first one-semester import needs your preview approval. No attendance or marks are imported by auto-connect.
        </p>
      )}

      {status.data?.refreshed_scopes ? (
        <p className="text-xs text-emerald-400 mt-1">{status.data.refreshed_scopes} approved scopes refreshed.</p>
      ) : null}

      {(settings.error || save.error || connect.error || refreshCurrent.error) && (
        <p role="alert" className="text-xs text-rose-400 mt-1.5 font-medium">
          {settings.error?.message ?? save.error?.message ?? connect.error?.message ?? refreshCurrent.error?.message}
        </p>
      )}
    </section>
  );
};
