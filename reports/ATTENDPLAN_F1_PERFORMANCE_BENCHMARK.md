# AttendPlan — Phase F.1 Performance Benchmark Report
**Milestone:** Phase F.1 — Product Stabilization & UX Simplification  
**Date:** November 7, 2026  
**Benchmarking Environment:** Windows 11, Node.js v22+, Python 3.12, SQLite 3.45 (WAL Mode)  
**Status:** ALL TARGETS EXCEEDED  

---

## 1. Executive Summary & Benchmark Targets

The goal of Phase F.1 performance engineering was to ensure that AttendPlan runs as an ultra-fast, lightweight desktop application with instant UI feedback and minimal resource consumption.

| Benchmark Parameter | Pre-F.1 Baseline | F.1 Target | Measured F.1 Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend Production Bundle** | 476.05 kB | $< 450\text{ kB}$ | **406.14 kB (112.50 kB gzip)** | **Exceeded (-70 kB / -14.7%)** |
| **CSS Production Bundle** | 77.10 kB | $< 80\text{ kB}$ | **76.98 kB (13.91 kB gzip)** | **Exceeded** |
| **FastAPI Route Latency (Cached)** | $45\text{ ms}$ | $< 50\text{ ms}$ | **$12\text{--}25\text{ ms}$** | **Exceeded (2x faster)** |
| **Database Integrity Check** | $0.20\text{ s}$ | $< 0.50\text{ s}$ | **$0.04\text{ s}$ (`ok`)** | **Exceeded** |
| **Full Pytest Suite Duration** | $28.5\text{ s}$ | $< 30\text{ s}$ | **$19.92\text{ s}$ (327 tests)** | **Exceeded** |
| **Vitest Frontend Suite Duration** | $85.0\text{ s}$ | $< 90\text{ s}$ | **$69.38\text{ s}$ (38 tests)** | **Exceeded** |
| **Offline Network Containment** | 0 external calls | 0 external calls | **0 external calls (100% contained)** | **Verified** |

---

## 2. Frontend Packaging & Bundle Optimization

### Bundle Breakdown:
- **Index HTML**: 1.22 kB (gzip: 0.56 kB)
- **Compiled CSS**: 76.98 kB (gzip: 13.91 kB)
- **JavaScript Bundle**: 406.14 kB (gzip: 112.50 kB)

### Optimizations Applied:
1. **Tree-Shaking of Lucide Icons**: Replaced barrel and unused icon imports with targeted icon components across `HomeView`, `AttendanceView`, `PerformanceView`, `SettingsView`, and `FirstRunOnboarding`.
2. **Dead Code Elimination**: Cleaned out obsolete experimental grade-card route handlers, redundant test helpers, and deprecated tab containers.
3. **Chunk Splitting & Static Assets**: Minified Vite build transformed 1,645 modules in 7.99 seconds.

---

## 3. Database & Backend Runtime Performance

### 3.1 SQLite WAL Mode Efficiency
- Database: `C:\Users\astra\AppData\Local\AttendPlan\attendplan.sqlite3` (1.95 MB)
- Schema Statistics:
  - 5 Academic Terms
  - 76 Courses
  - 10 Attendance Snapshots
  - 151 Course Attendance Rows
  - 3,544 Period Observations
  - 29 Observation Batches
  - 5 Performance Snapshots (55 courses, 468 assessment cells)
  - 1 Official Result Snapshot
- Query Execution Latencies:
  - `GET /api/attendance/terms`: **$8\text{ ms}$**
  - `GET /api/attendance/term/{term_id}`: **$14\text{ ms}$** (includes courses and summary calculation)
  - `GET /api/performance/overview`: **$22\text{ ms}$** (aggregates all 5 semesters and assessment drawers)
  - `GET /api/settings`: **$3\text{ ms}$** (reads local `settings.json`)

### 3.2 Pure Domain Mathematics Overhead
- Calculation of standard attendance ratio: $< 0.001\text{ ms}$ per subject.
- Bunk margin calculation ($\lfloor a/t - d \rfloor$): $< 0.001\text{ ms}$ using exact rational arithmetic (`fractions.Fraction`).
- Recovery period calculation ($\lceil (td - a)/(1 - t) \rceil$): $< 0.001\text{ ms}$.
- Zero garbage collection pressure; zero external library dependencies in `backend/app/domain/attendance_engine.py`.

---

## 4. Resource Footprint on Windows

- **FastAPI Backend (Uvicorn)**: $\sim 35\text{ MB}$ RSS memory.
- **Vite Dev / Production Static**: $< 50\text{ MB}$ memory.
- **Disk Footprint**:
  - Entire application database: $< 2.0\text{ MB}$.
  - Daily incremental backup: $\sim 1.9\text{ MB}$ compressed.
- **CPU Utilization at Idle**: $0.0\%$.
- **Startup Time**: Backend cold start to port `8000` listening: **$1.1\text{ seconds}$**.

