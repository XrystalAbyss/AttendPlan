import { BookOpen, Home, Settings, TrendingUp } from "lucide-react";

export type WorkspaceTab =
  | "home"
  | "attendance"
  | "performance"
  | "settings"
  | "roster"
  | "analytics"
  | "historical"
  | "history"
  | "reconciliation"
  | "discovery";

const destinations = [
  { key: "home", label: "Home", icon: Home },
  { key: "attendance", label: "Attendance", icon: BookOpen },
  { key: "performance", label: "Performance", icon: TrendingUp },
  { key: "settings", label: "Settings", icon: Settings },
] as const;

export function normalizeTab(tab: WorkspaceTab): "home" | "attendance" | "performance" | "settings" {
  switch (tab) {
    case "home":
      return "home";
    case "performance":
      return "performance";
    case "settings":
    case "reconciliation":
    case "discovery":
      return "settings";
    case "attendance":
    case "roster":
    case "analytics":
    case "historical":
    case "history":
    default:
      return "attendance";
  }
}

export function WorkspaceNav({
  activeTab,
  onChange,
}: {
  activeTab: WorkspaceTab;
  onChange: (tab: WorkspaceTab) => void;
}) {
  const currentNormalized = normalizeTab(activeTab);

  return (
    <nav className="workspace-nav" aria-label="Dashboard views">
      {destinations.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          aria-current={currentNormalized === key ? "page" : undefined}
          onClick={() => onChange(key as WorkspaceTab)}
          className="cursor-pointer"
        >
          <Icon aria-hidden="true" size={16} />
          <span>{label}</span>
        </button>
      ))}
    </nav>
  );
}
