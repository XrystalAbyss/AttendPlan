# AttendPlan Design System

## 1. Design Philosophy
AttendPlan is designed as **institutional analytical software**. It avoids trendy, fleeting web gimmicks (such as neon glassmorphism, heavy decorative gradients, floating blur blobs, or generic AI illustrations) in favor of:
- **Maximum Data Density & Legibility**: Academic metrics should be readable at a glance.
- **Restrained Neutral Foundation**: Slate and zinc neutral surfaces establish a calm, professional hierarchy.
- **Semantic Color Meaning**: Colors are reserved strictly for communicating attendance state and warnings.
- **Explicit Provenance**: Every screen clearly states whether data is Live, Cached, or a Historical Sample.

---

## 2. Color Palette & Semantics

### 2.1 Neutrals
- **Background**: `#0F172A` (Slate 900) or `#F8FAFC` (Slate 50) for light mode.
- **Card / Surface**: `#1E293B` (Slate 800) / `#FFFFFF` (White).
- **Borders & Dividers**: `#334155` (Slate 700) / `#E2E8F0` (Slate 200).
- **Text Primary**: `#F8FAFC` (Slate 50) / `#0F172A` (Slate 900).
- **Text Muted**: `#94A3B8` (Slate 400) / `#64748B` (Slate 500).

### 2.2 Semantic States
| State | Tailwind Class | Color Tone | Hex | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Safe** | `text-emerald-400 bg-emerald-950/40 border-emerald-800` | Emerald | `#10B981` | $\ge 75\%$ target met. Bunks available. |
| **At Risk / Danger** | `text-rose-400 bg-rose-950/40 border-rose-800` | Rose / Coral | `#F43F5E` | $< 75\%$ target breached. Must attend lectures. |
| **Unrecorded** | `text-slate-400 bg-slate-800 border-slate-700` | Slate | `#64748B` | $0/0$ lectures delivered. Undefined margin. |
| **Provenance Sample** | `text-amber-400 bg-amber-950/40 border-amber-800` | Amber | `#F59E0B` | Historical / Sample fixture disclaimer badge. |

---

## 3. Typography Hierarchy
- **Primary Font**: Modern clean sans-serif (`Inter`, `ui-sans-serif`, system font stack).
- **Numbers / Metrics**: Tabular figures (`font-mono` / `tabular-nums`) for period fractions, percentages, and course codes to ensure tabular alignment.

---

## 4. UI Components

### 4.1 Provenance Banner
Always placed at the top of the application when viewing offline fixtures or test samples:
```tsx
<div className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-400">
  <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
  <span>SAMPLE / HISTORICAL FIXTURE — Fall 2026</span>
</div>
```

### 4.2 Status Pill
Distinct badge indicating whether a course is safe or below the threshold:
- **`Safe`**: Includes checkmark icon and count of allowable safe bunks.
- **`At Risk`**: Includes alert triangle and count of consecutive lectures needed.
- **`Unrecorded`**: Indicates lectures have not commenced or are pending record.

### 4.3 Attendance Table
- Left-aligned academic course details (code, title, faculty, credits).
- Monospace right-aligned counts (`attended / delivered`).
- Visual progress bar with a fixed marker indicator at the 75% threshold line.
- Plain text action recommendation: "Safe to skip 3" or "Attend 2 consecutive".
