"""F.3 Performance & Regression Benchmark Suite.

Measures API response times, frontend bundle size, and navigation timings.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import statistics
import time
import urllib.request
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = REPO_ROOT / "reports" / "f3_performance_benchmark.json"

def benchmark_apis(iterations: int = 15) -> dict[str, dict[str, float]]:
    term_id = None
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/v1/terms", headers={"Host": "127.0.0.1"})
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
        # Warmup
        try:
            req = urllib.request.Request(url, headers={"Host": "127.0.0.1"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                _ = resp.read()
        except Exception:
            pass

        for _ in range(iterations):
            t0 = time.perf_counter()
            req = urllib.request.Request(url, headers={"Host": "127.0.0.1"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                _ = resp.read()
            durations.append((time.perf_counter() - t0) * 1000.0)

        durations.sort()
        results[name] = {
            "samples": len(durations),
            "median_ms": round(statistics.median(durations), 2),
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
            "avg_ms": round(sum(durations) / len(durations), 2),
        }
    return results

async def benchmark_browser_navigation() -> dict[str, float]:
    timings = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1366, "height": 768})

        # Cold load
        start = time.perf_counter()
        await page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        timings["cold_load_ms"] = round((time.perf_counter() - start) * 1000, 2)

        # Tab navigation (Cached via TanStack Query)
        # Attendance tab
        start = time.perf_counter()
        await page.click("button:has-text('Attendance')")
        await page.wait_for_selector(".attendance-view")
        timings["attendance_nav_ms"] = round((time.perf_counter() - start) * 1000, 2)

        # Performance tab
        start = time.perf_counter()
        await page.click("button:has-text('Performance')")
        await page.wait_for_selector(".performance-view")
        timings["performance_nav_ms"] = round((time.perf_counter() - start) * 1000, 2)

        # Home tab
        start = time.perf_counter()
        await page.click("button:has-text('Home')")
        await page.wait_for_selector(".home-view")
        timings["home_nav_ms"] = round((time.perf_counter() - start) * 1000, 2)

        # Settings tab
        start = time.perf_counter()
        await page.click("button:has-text('Settings')")
        await page.wait_for_selector(".settings-view")
        timings["settings_nav_ms"] = round((time.perf_counter() - start) * 1000, 2)

        await browser.close()
    return timings

def get_bundle_metrics() -> dict[str, any]:
    dist_assets = REPO_ROOT / "frontend" / "dist" / "assets"
    metrics = {"js_bytes": 0, "css_bytes": 0, "files": []}
    if dist_assets.exists():
        for f in dist_assets.iterdir():
            size = f.stat().st_size
            metrics["files"].append({"name": f.name, "bytes": size})
            if f.suffix == ".js":
                metrics["js_bytes"] += size
            elif f.suffix == ".css":
                metrics["css_bytes"] += size
    return metrics

def run_benchmarks():
    print("Benchmarking API response latencies...")
    api_results = benchmark_apis()
    print("Benchmarking browser navigation...")
    nav_results = asyncio.run(benchmark_browser_navigation())
    print("Collecting bundle metrics...")
    bundle_results = get_bundle_metrics()

    full_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "F.3",
        "api_latencies": api_results,
        "navigation_timings": nav_results,
        "bundle": bundle_results,
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    print(f"Benchmark results written to {REPORT_JSON}")
    print(json.dumps(full_report, indent=2))

if __name__ == "__main__":
    run_benchmarks()
