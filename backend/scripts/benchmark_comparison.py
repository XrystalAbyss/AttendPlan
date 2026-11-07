"""Phase F.2 Optimization Verification and Comparative Analysis Benchmark.

Executes identical test methodology as baseline:
- Measures API response times (median, p95, min, max across 10 samples)
- Measures SQLite query latencies
- Measures Playwright UI navigation & rendering
- Compares baseline vs optimized with absolute and percentage differences
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import get_default_db_path

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

        t0 = time.perf_counter()
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        cold_load_ms = (time.perf_counter() - t0) * 1000.0
        timings["cold_dashboard_load_ms"] = round(cold_load_ms, 2)

        page.wait_for_selector(".home-view", timeout=5000)

        t0 = time.perf_counter()
        page.locator("nav.workspace-nav button:has-text('Attendance')").click()
        page.wait_for_selector(".attendance-view", timeout=5000)
        timings["nav_to_attendance_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        selector = page.locator("select[aria-label='Saved semester']")
        t0 = time.perf_counter()
        selector.select_option(index=1)
        page.wait_for_timeout(50)
        timings["semester_switch_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        t0 = time.perf_counter()
        page.locator("button:has-text('Date-wise Calendar & Trends')").click()
        page.wait_for_selector(".attendance-explorer", timeout=5000)
        timings["calendar_toggle_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        t0 = time.perf_counter()
        page.locator("nav.workspace-nav button:has-text('Performance')").click()
        page.wait_for_selector(".performance-view", timeout=5000)
        timings["nav_to_performance_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        t0 = time.perf_counter()
        page.locator("nav.workspace-nav button:has-text('Home')").click()
        page.wait_for_selector(".home-view", timeout=5000)
        timings["nav_to_home_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        browser.close()
    return timings

def main():
    print("Measuring post-optimization metrics...")
    env = get_env_specs()
    api_latencies = measure_api_latencies(iterations=10)
    sqlite_latencies = measure_sqlite_latencies(iterations=10)
    ux_timings = measure_playwright_ux()

    optimized_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": env,
        "api_latencies": api_latencies,
        "sqlite_latencies": sqlite_latencies,
        "ux_timings": ux_timings,
    }

    repo_root = Path(__file__).resolve().parents[2]
    opt_file = repo_root / "reports" / "f2_optimized_benchmark.json"
    with open(opt_file, "w", encoding="utf-8") as f:
        json.dump(optimized_data, f, indent=2)

    # Load baseline
    base_file = repo_root / "reports" / "f2_baseline_benchmark.json"
    if base_file.exists():
        with open(base_file, "r", encoding="utf-8") as f:
            base_data = json.load(f)

        print("\n=======================================================")
        print("          PHASE F.2 BENCHMARK COMPARISON               ")
        print("=======================================================")
        print(f"{'Metric':<35} | {'Baseline Median':<15} | {'Optimized Median':<16} | {'Diff / Speedup':<15}")
        print("-" * 88)
        for name, opt_val in api_latencies.items():
            base_val = base_data.get("api_latencies", {}).get(name)
            if base_val:
                b_med = base_val["median_ms"]
                o_med = opt_val["median_ms"]
                diff = o_med - b_med
                pct = ((b_med - o_med) / b_med) * 100 if b_med > 0 else 0
                speedup = f"{b_med/o_med:.1f}x faster ({pct:+.1f}%)" if o_med < b_med else f"{diff:+.2f}ms"
                print(f"{name:<35} | {b_med:>12.2f} ms | {o_med:>13.2f} ms | {speedup:<15}")

        print("-" * 88)
        for name, opt_val in ux_timings.items():
            b_val = base_data.get("ux_timings", {}).get(name)
            if b_val:
                diff = opt_val - b_val
                pct = ((b_val - opt_val) / b_val) * 100 if b_val > 0 else 0
                speedup = f"{b_val/opt_val:.1f}x faster ({pct:+.1f}%)" if opt_val < b_val else f"{diff:+.2f}ms"
                print(f"{name:<35} | {b_val:>12.2f} ms | {opt_val:>13.2f} ms | {speedup:<15}")
        print("=======================================================\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())

