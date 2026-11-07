"""Phase F.2 Comprehensive Performance Benchmark & Metrics Collector.

Measures:
1. Environment & Hardware Specs
2. Local API latencies across multiple iterations (median & p95)
3. SQLite query latencies via raw DB engine
4. Playwright navigation and rendering timings (Home, Attendance, Performance, Semester switching, etc.)
5. Production bundle size breakdown
6. Process memory consumption (FastAPI, Node, Chrome)
"""
from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
import ctypes
from pathlib import Path
import subprocess
import urllib.request

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import build_sqlite_url, create_app_engine, get_default_db_path

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_env_specs():
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    ram_gb = round(stat.ullTotalPhys / (1024**3), 2)

    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "ram_gb": ram_gb,
        "python_version": platform.python_version(),
    }

def measure_api_latencies(iterations=10):
    # Fetch a valid term_id dynamically
    term_id = None
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/v1/terms")
        with urllib.request.urlopen(req, timeout=5) as resp:
            terms = json.loads(resp.read().decode())
            if terms and isinstance(terms, list):
                term_id = terms[0].get("id")
    except Exception as e:
        print(f"Failed to fetch initial term: {e}")

    endpoints = [
        ("GET /api/v1/terms", "http://127.0.0.1:8000/api/v1/terms"),
        ("GET /api/v1/performance/overview", "http://127.0.0.1:8000/api/v1/performance/overview"),
        ("GET /api/v1/auth/settings", "http://127.0.0.1:8000/api/v1/auth/settings"),
        ("GET /api/v1/startup/status", "http://127.0.0.1:8000/api/v1/startup/status"),
    ]
    if term_id:
        endpoints.insert(1, ("GET /api/v1/terms/{id}/attendance", f"http://127.0.0.1:8000/api/v1/terms/{term_id}/attendance"))
        endpoints.insert(2, ("GET /api/v1/terms/{id}/analytics/monthly", f"http://127.0.0.1:8000/api/v1/terms/{term_id}/analytics/monthly"))

    results = {}
    for name, url in endpoints:
        durations = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "AttendPlan-Benchmark"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp.read()
                durations.append((time.perf_counter() - t0) * 1000.0)
            except Exception as e:
                print(f"Error fetching {url}: {e}")
        if durations:
            durations.sort()
            p95_idx = int(0.95 * len(durations))
            p95_val = durations[min(p95_idx, len(durations) - 1)]
            results[name] = {
                "samples": len(durations),
                "median_ms": round(statistics.median(durations), 2),
                "p95_ms": round(p95_val, 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
            }
    return results

def measure_sqlite_latencies(iterations=10):
    import sqlite3
    db_path = get_default_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get term 5 id
    cur.execute("SELECT id FROM academic_terms ORDER BY id DESC LIMIT 1")
    term_row = cur.fetchone()
    term_id = term_row[0] if term_row else 1

    queries = [
        ("SELECT all terms", "SELECT * FROM academic_terms"),
        ("SELECT term courses", f"SELECT * FROM courses WHERE academic_term_id = '{term_id}'"),
        ("SELECT term observations", f"SELECT * FROM attendance_period_observations WHERE academic_term_id = '{term_id}'"),
        ("SELECT all performance snapshots", "SELECT * FROM performance_snapshots ORDER BY captured_at DESC"),
        ("SELECT count observations per course", "SELECT course_id, COUNT(*) FROM attendance_period_observations GROUP BY course_id"),
    ]

    results = {}
    for name, query in queries:
        durations = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            cur.execute(query)
            cur.fetchall()
            durations.append((time.perf_counter() - t0) * 1000.0)
        durations.sort()
        p95_idx = int(0.95 * len(durations))
        p95_val = durations[min(p95_idx, len(durations) - 1)]
        results[name] = {
            "samples": len(durations),
            "median_ms": round(statistics.median(durations), 3),
            "p95_ms": round(p95_val, 3),
            "min_ms": round(min(durations), 3),
            "max_ms": round(max(durations), 3),
        }
    conn.close()
    return results

def measure_playwright_ux():
    from playwright.sync_api import sync_playwright

    timings = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Cold navigation to frontend
        t0 = time.perf_counter()
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        cold_load_ms = (time.perf_counter() - t0) * 1000.0
        timings["cold_dashboard_load_ms"] = round(cold_load_ms, 2)

        # First meaningful content
        page.wait_for_selector(".home-view", timeout=5000)

        # 2. Navigation to Attendance view
        t0 = time.perf_counter()
        page.locator("nav.workspace-nav button:has-text('Attendance')").click()
        page.wait_for_selector(".attendance-view", timeout=5000)
        timings["nav_to_attendance_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # 3. Semester switching (select Sem 4)
        selector = page.locator("select[aria-label='Saved semester']")
        t0 = time.perf_counter()
        selector.select_option(index=1)
        page.wait_for_timeout(100)
        timings["semester_switch_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # 4. Toggle to Calendar & Trends
        t0 = time.perf_counter()
        page.locator("button:has-text('Date-wise Calendar & Trends')").click()
        page.wait_for_selector(".attendance-explorer", timeout=5000)
        timings["calendar_toggle_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # 5. Navigation to Performance view
        t0 = time.perf_counter()
        page.locator("nav.workspace-nav button:has-text('Performance')").click()
        page.wait_for_selector(".performance-view", timeout=5000)
        timings["nav_to_performance_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # 6. Expand assessment drawer
        drawers = page.locator("details summary:has-text('Assessment breakdown')")
        if drawers.count() > 0:
            t0 = time.perf_counter()
            drawers.first.click()
            page.wait_for_timeout(50)
            timings["assessment_drawer_expand_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # 7. Navigation back to Home
        t0 = time.perf_counter()
        page.locator("nav.workspace-nav button:has-text('Home')").click()
        page.wait_for_selector(".home-view", timeout=5000)
        timings["nav_to_home_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        browser.close()
    return timings

def measure_bundle_size():
    dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    results = {}
    if dist_dir.exists():
        for f in dist_dir.rglob("*"):
            if f.is_file():
                results[f.name] = {
                    "size_bytes": f.stat().st_size,
                    "size_kb": round(f.stat().st_size / 1024, 2),
                }
    return results

def measure_memory_usage():
    mem_info = {}
    try:
        output = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True)
        for line in output.strip().splitlines():
            parts = [p.strip('\"') for p in line.split('\",\"')]
            if len(parts) >= 5:
                name, pid, _, _, mem_str = parts[0].lower(), parts[1], parts[2], parts[3], parts[4]
                if any(k in name for k in ["python", "uvicorn", "node", "chrome"]):
                    # mem_str is e.g. "45,120 K"
                    cleaned_mem = mem_str.replace(" K", "").replace(",", "").replace(" ", "")
                    try:
                        mem_mb = round(int(cleaned_mem) / 1024, 2)
                        mem_info[f"{name}_{pid}"] = mem_mb
                    except ValueError:
                        pass
    except Exception as e:
        print(f"Error measuring memory: {e}")
    return mem_info

def main():
    print("Collecting environment specifications...")
    env = get_env_specs()

    print("Measuring local API latencies (10 iterations)...")
    api_latencies = measure_api_latencies(iterations=10)

    print("Measuring SQLite query latencies (10 iterations)...")
    sqlite_latencies = measure_sqlite_latencies(iterations=10)

    print("Measuring browser UX interaction latencies with Playwright...")
    ux_timings = measure_playwright_ux()

    print("Measuring production bundle sizes...")
    bundle_sizes = measure_bundle_size()

    print("Measuring process memory usage...")
    mem_usage = measure_memory_usage()

    benchmark_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": env,
        "api_latencies": api_latencies,
        "sqlite_latencies": sqlite_latencies,
        "ux_timings": ux_timings,
        "bundle_sizes": bundle_sizes,
        "memory_usage": mem_usage,
    }

    out_file = Path(__file__).resolve().parents[2] / "reports" / "f2_baseline_benchmark.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"\nBaseline benchmark written to: {out_file}")
    print(json.dumps(benchmark_data, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
