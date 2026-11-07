import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Database,
  Download,
  ExternalLink,
  KeyRound,
  LogOut,
  Server,
  Shield,
  Smartphone,
  Sliders,
  UserCheck,
} from "lucide-react";
import { API_BASE } from "../api/attendance";

interface AppSettingsResponse {
  has_saved_mobile: boolean;
  masked_mobile: string | null;
  auto_mobile_autofill: boolean;
  auto_login_continuation: boolean;
  auto_totp_autofill: boolean;
  auto_totp_submit: boolean;
}

interface TotpStatusResponse {
  is_enrolled: boolean;
  account_name: string | null;
  key_format: string | null;
  safe_backend: string;
}

interface PortalSessionStatus {
  cdp_reachable: boolean;
  active_tabs_count: number;
  current_url?: string | null;
  state: string;
}

interface StartupSettings {
  auto_connect: boolean;
  refresh_approved_scopes: boolean;
  auto_refresh_current_term?: boolean;
  approved_scope_count: number;
  last_sync_time?: string | null;
}

export const SettingsView: React.FC<{
  onOpenAuthModal: () => void;
  targetPercentage: number;
  onTargetChange: (t: number) => void;
}> = ({ onOpenAuthModal, targetPercentage, onTargetChange }) => {
  const queryClient = useQueryClient();
  const [mobileInput, setMobileInput] = useState("");
  const [isEditingMobile, setIsEditingMobile] = useState(false);
  const [backupMessage, setBackupMessage] = useState<string | null>(null);
  const [disconnectMessage, setDisconnectMessage] = useState<string | null>(null);

  // 1. Auth Settings Query
  const authSettings = useQuery<AppSettingsResponse>({
    queryKey: ["auth-settings"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/auth/settings`);
      if (!res.ok) throw new Error("Could not load authentication settings");
      return res.json();
    },
  });

  // 2. TOTP Status Query
  const totpStatus = useQuery<TotpStatusResponse>({
    queryKey: ["totp-status"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/auth/totp/status`);
      if (!res.ok) throw new Error("Could not load TOTP status");
      return res.json();
    },
  });

  // 3. Portal Session Status
  const portalSession = useQuery<PortalSessionStatus>({
    queryKey: ["portal-session-status"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/portal/session/status`);
      if (!res.ok) return { cdp_reachable: false, active_tabs_count: 0, state: "DISCONNECTED" };
      return res.json();
    },
    refetchInterval: 10000,
  });

  // 4. Startup Preferences Query
  const startupSettings = useQuery<StartupSettings>({
    queryKey: ["startup-settings"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/startup/settings`);
      if (!res.ok) throw new Error("Could not load startup settings");
      return res.json();
    },
  });

  // Mutations
  const updateAuthSettings = useMutation({
    mutationFn: async (payload: Partial<AppSettingsResponse> & { mobile_number?: string; clear_mobile?: boolean }) => {
      const res = await fetch(`${API_BASE}/api/v1/auth/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to save settings");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth-settings"] });
      setIsEditingMobile(false);
      setMobileInput("");
    },
  });

  const updateStartupSettings = useMutation({
    mutationFn: async (payload: Partial<StartupSettings>) => {
      const res = await fetch(`${API_BASE}/api/v1/startup/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to save startup settings");
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["startup-settings"] }),
  });

  const launchBrowser = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/portal/session/launch`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to launch dedicated browser");
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["portal-session-status"] }),
  });

  const exportBackup = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/auth/backup/export`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed to export backup");
      return data;
    },
    onSuccess: (data) => {
      setBackupMessage(`Backup saved: ${data.backup_filename} (${Math.round(data.backup_bytes / 1024)} KB)`);
      setTimeout(() => setBackupMessage(null), 6000);
    },
    onError: (err: any) => {
      setBackupMessage(`Backup failed: ${err.message}`);
    },
  });

  const disconnectSession = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/portal/session/disconnect`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed to disconnect session");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portal-session-status"] });
      setDisconnectMessage("Browser session disconnected and CDP freed.");
      setTimeout(() => setDisconnectMessage(null), 5000);
    },
  });

  return (
    <div className="settings-view max-w-4xl mx-auto space-y-6 text-slate-200">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-100 m-0">Settings &amp; Preferences</h2>
        <p className="text-xs text-slate-400 mt-1 m-0">
          Manage your university connection, private local vault, and application data.
        </p>
      </div>

      {/* Section 1: University Portal & Authentication */}
      <section className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-indigo-950/80 border border-indigo-800 text-indigo-400">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100 m-0">University Portal &amp; Session</h3>
              <p className="text-xs text-slate-400 m-0 mt-0.5">
                iCloudEMS / Keycloak student single sign-on
              </p>
            </div>
          </div>
          <span
            className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
              portalSession.data?.cdp_reachable
                ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                : "bg-slate-800 text-slate-400 border border-slate-700"
            }`}
          >
            {portalSession.data?.cdp_reachable ? "Browser Connected" : "Browser Offline"}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Mobile number setting */}
          <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Smartphone className="w-4 h-4 text-slate-400" />
                Student Mobile Number
              </span>
              {authSettings.data?.has_saved_mobile && !isEditingMobile && (
                <button
                  onClick={() => setIsEditingMobile(true)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer"
                >
                  Change
                </button>
              )}
            </div>

            {isEditingMobile || !authSettings.data?.has_saved_mobile ? (
              <div className="space-y-2">
                <input
                  type="tel"
                  placeholder="10-digit mobile (e.g. 9876543210)"
                  value={mobileInput}
                  onChange={(e) => setMobileInput(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
                />
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => updateAuthSettings.mutate({ mobile_number: mobileInput })}
                    disabled={updateAuthSettings.isPending || mobileInput.length < 10}
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-medium cursor-pointer inline-flex items-center gap-1"
                  >
                    Save Number
                  </button>
                  {isEditingMobile && (
                    <button
                      onClick={() => setIsEditingMobile(false)}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded text-xs cursor-pointer"
                    >
                      Cancel
                    </button>
                  )}
                  {authSettings.data?.has_saved_mobile && (
                    <button
                      onClick={() => updateAuthSettings.mutate({ clear_mobile: true })}
                      className="text-rose-400 hover:text-rose-300 text-xs ml-auto cursor-pointer"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-slate-200 text-sm">
                  {authSettings.data?.masked_mobile ?? "Not configured"}
                </span>
                <span className="text-emerald-400 text-xs flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Saved in local settings
                </span>
              </div>
            )}
            <p className="text-[11px] text-slate-400 m-0 leading-relaxed">
              Stored only on this computer in <code className="text-slate-300">%LOCALAPPDATA%\AttendPlan</code>. Never transmitted to third parties.
            </p>
          </div>

          {/* Browser & CDP controls */}
          <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Server className="w-4 h-4 text-slate-400" />
                Dedicated Browser Connection
              </span>
            </div>
            <p className="text-[11px] text-slate-400 m-0 leading-relaxed">
              AttendPlan uses an isolated, dedicated Google Chrome profile on loopback (127.0.0.1:9222) to communicate with iCloudEMS.
            </p>
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={() => launchBrowser.mutate()}
                disabled={launchBrowser.isPending || portalSession.data?.cdp_reachable}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 border border-slate-700 text-slate-200 text-xs font-medium rounded-lg inline-flex items-center gap-1.5 cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                {portalSession.data?.cdp_reachable ? "Browser Ready" : "Launch Dedicated Chrome"}
              </button>
              <button
                onClick={onOpenAuthModal}
                className="px-3 py-1.5 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/50 text-indigo-200 text-xs font-medium rounded-lg inline-flex items-center gap-1.5 cursor-pointer ml-auto"
              >
                <KeyRound className="w-3.5 h-3.5" />
                Authenticator Setup
              </button>
            </div>
          </div>
        </div>

        {/* Login Automation Toggles */}
        <div className="pt-2 border-t border-slate-800 space-y-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Login Automation Options
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <label className="flex items-start gap-2.5 p-2.5 bg-slate-800/40 rounded-lg cursor-pointer">
              <input
                type="checkbox"
                checked={authSettings.data?.auto_mobile_autofill ?? false}
                onChange={(e) => updateAuthSettings.mutate({ auto_mobile_autofill: e.target.checked })}
                className="mt-0.5"
              />
              <div>
                <span className="font-medium text-slate-200 block">Auto-fill student mobile number</span>
                <span className="text-[11px] text-slate-400">Fills your saved number into the login form</span>
              </div>
            </label>

            <label className="flex items-start gap-2.5 p-2.5 bg-slate-800/40 rounded-lg cursor-pointer">
              <input
                type="checkbox"
                checked={authSettings.data?.auto_totp_autofill ?? false}
                onChange={(e) => updateAuthSettings.mutate({ auto_totp_autofill: e.target.checked })}
                className="mt-0.5"
              />
              <div>
                <span className="font-medium text-slate-200 block">Auto-fill Authenticator TOTP</span>
                <span className="text-[11px] text-slate-400">Fills the 6-digit MFA code automatically</span>
              </div>
            </label>
          </div>
        </div>
      </section>

      {/* Section 2: Threshold & Sync Preferences */}
      <section className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-400">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 m-0">Attendance &amp; Sync Preferences</h3>
            <p className="text-xs text-slate-400 m-0 mt-0.5">Threshold calculation and automatic refresh</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-lg space-y-2">
            <label className="text-xs font-semibold text-slate-300 block">
              Default Attendance Target: {targetPercentage}%
            </label>
            <p className="text-[11px] text-slate-400 m-0">
              Institution standard is 75%. Calculations for safe bunks and recovery classes use this target.
            </p>
            <div className="pt-2">
              <select
                value={targetPercentage}
                onChange={(e) => onTargetChange(Number(e.target.value))}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono cursor-pointer"
              >
                <option value={75}>75% (University Institutional Threshold)</option>
                <option value={80}>80% (High Confidence Margin)</option>
                <option value={85}>85% (Scholarship &amp; Honor Standing)</option>
              </select>
            </div>
          </div>

          <div className="p-4 bg-slate-800/60 border border-slate-700/60 rounded-lg space-y-2">
            <span className="text-xs font-semibold text-slate-300 block">Background Refresh</span>
            <label className="flex items-start gap-2 text-xs pt-1 cursor-pointer">
              <input
                type="checkbox"
                checked={startupSettings.data?.auto_refresh_current_term ?? false}
                onChange={(e) => updateStartupSettings.mutate({ auto_refresh_current_term: e.target.checked })}
                className="mt-0.5"
              />
              <div>
                <span className="font-medium text-slate-200 block">Automatically sync current semester on launch</span>
                <span className="text-[11px] text-slate-400">
                  Fetches the latest attendance updates whenever the application opens
                </span>
              </div>
            </label>
          </div>
        </div>
      </section>

      {/* Section 3: Local Storage & Backups */}
      <section className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-slate-800 border border-slate-700 text-indigo-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100 m-0">Local Database &amp; Privacy</h3>
              <p className="text-xs text-slate-400 m-0 mt-0.5">
                Private offline SQLite storage (Zero Cloud Transmission)
              </p>
            </div>
          </div>
          <span className="text-xs text-emerald-400 flex items-center gap-1 font-mono">
            <Shield className="w-3.5 h-3.5" /> 100% Local-First
          </span>
        </div>

        <div className="p-4 bg-slate-800/40 border border-slate-700/60 rounded-lg space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Database location:</span>
            <code className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded font-mono text-[11px]">
              %LOCALAPPDATA%\AttendPlan\attendplan.sqlite3
            </code>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Backup folder:</span>
            <code className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded font-mono text-[11px]">
              %LOCALAPPDATA%\AttendPlan\backups\
            </code>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Security vault:</span>
            <span className="text-emerald-400 font-medium">
              Windows Credential Manager ({totpStatus.data?.is_enrolled ? "TOTP Enrolled" : "Not Enrolled"})
            </span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1">
          <div>
            <p className="text-xs text-slate-400 m-0">
              AttendPlan keeps WAL-safe offline snapshots before each major data synchronization.
            </p>
            {backupMessage && (
              <p className="text-xs text-emerald-400 font-medium m-0 mt-1">{backupMessage}</p>
            )}
          </div>
          <button
            onClick={() => exportBackup.mutate()}
            disabled={exportBackup.isPending}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 rounded-lg text-xs font-medium cursor-pointer inline-flex items-center gap-1.5 shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            {exportBackup.isPending ? "Creating Backup..." : "Export Offline Backup"}
          </button>
        </div>
      </section>

      {/* Section 4: Troubleshooting & Diagnostics */}
      <section className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-slate-800 border border-slate-700 text-amber-400">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 m-0">Troubleshooting &amp; Diagnostics</h3>
            <p className="text-xs text-slate-400 m-0 mt-0.5">Localhost daemons, network ports, and cache management</p>
          </div>
        </div>

        {disconnectMessage && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg text-xs text-emerald-300">
            {disconnectMessage}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 bg-slate-800/40 border border-slate-700/60 rounded-lg space-y-1.5">
            <span className="text-slate-400 font-medium block">Local Server Status:</span>
            <div className="flex items-center justify-between">
              <span className="text-slate-200 font-mono">
                {typeof window !== "undefined" && window.location.host ? window.location.host : "127.0.0.1:8000"} (FastAPI)
              </span>
              <span className="text-emerald-400 font-semibold">Active &bull; WAL</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-200 font-mono">127.0.0.1:9222 (Chrome CDP)</span>
              <span className={portalSession.data?.cdp_reachable ? "text-emerald-400 font-semibold" : "text-slate-500"}>
                {portalSession.data?.cdp_reachable ? "Reachable" : "Idle"}
              </span>
            </div>
          </div>

          <div className="p-3 bg-slate-800/40 border border-slate-700/60 rounded-lg flex flex-col justify-between gap-2">
            <div>
              <span className="text-slate-400 font-medium block">Session &amp; Cache Actions:</span>
              <p className="text-[11px] text-slate-400 m-0 mt-0.5">
                Manage active browser sessions and reset local application cache.
              </p>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={() => queryClient.invalidateQueries()}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 rounded text-xs font-medium cursor-pointer"
              >
                Refresh Cache
              </button>
              <button
                onClick={() => disconnectSession.mutate()}
                disabled={disconnectSession.isPending}
                className="px-3 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded text-xs font-medium cursor-pointer inline-flex items-center gap-1"
              >
                <LogOut className="w-3 h-3" />
                Disconnect Browser
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Section 5: About AttendPlan */}
      <section className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 space-y-2 text-xs text-slate-400">
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider m-0">About AttendPlan</h3>
        <p className="m-0 leading-relaxed">
          AttendPlan is a private, local-first university attendance intelligence application designed to help students track and plan their attendance under an institutional 75% requirement. Student credentials and attendance records never leave your local machine.
        </p>
        <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-800 text-[11px] text-slate-500">
          <span>Version: 0.1.0-beta.3 (Supervised Friends Beta)</span>
          <span>Security: DPAPI Credential Vault &bull; IPv4 Loopback Binding</span>
        </div>
      </section>
    </div>
  );
};

